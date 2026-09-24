from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from uuid import uuid4
import re
from supabase_auth.errors import AuthApiError


def now():
    return datetime.now(timezone.utc).isoformat()


class Auth:
    def __init__(self):
        self.accounts = {}
        self.tokens = {}
        self.session_user = None
        self.admin = self

    def create_user(self, data):
        uid = str(uuid4())
        self.accounts[uid] = dict(data, id=uid, email_confirmed_at=now() if data.get('email_confirm') else None)
        return NS(user=NS(**self.accounts[uid]))

    def delete_user(self, uid):
        self.accounts.pop(uid, None)
        self.tokens = {k: v for k, v in self.tokens.items() if v != uid}

    def session(self, uid):
        token, refresh = 'access-'+str(uuid4()), 'refresh-'+str(uuid4())
        self.tokens[token] = self.tokens[refresh] = uid
        self.session_user = uid
        return NS(user=NS(**self.accounts[uid]), session=NS(access_token=token, refresh_token=refresh, expires_at=2000000000))

    def sign_in_with_password(self, data):
        for uid, account in self.accounts.items():
            if account['email'] == data['email'] and account['password'] == data['password']:
                return self.session(uid)
        raise AuthApiError('Invalid credentials', 400, 'invalid_credentials')

    def get_user(self, token=None):
        uid = self.tokens.get(token) if token else self.session_user
        if uid not in self.accounts:
            raise ValueError('Invalid token')
        return NS(user=NS(**self.accounts[uid]))

    def refresh_session(self, token):
        uid = self.tokens.get(token)
        return self.session(uid) if uid else NS(user=None, session=None)

    def update_user_by_id(self, uid, data):
        self.accounts[uid].update(data)
        return NS(user=NS(**self.accounts[uid]))

    def sign_out(self, jwt=None):
        self.session_user = None

    def reset_password_email(self, email):
        pass  # No email is ever sent by these tests.

    def update_user(self, data):
        if not self.session_user:
            raise ValueError('No session')
        self.accounts[self.session_user].update(data)
        return NS(user=NS(**self.accounts[self.session_user]))


class Store:
    def __init__(self):
        self.rows = defaultdict(list)
        self.auth = Auth()

    def table(self, name):
        return Query(self, name)


class Query:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self.filters, self.columns = [], '*'
        self.action, self.payload = 'select', None
        self.sort, self.maximum, self.one = None, None, False

    def select(self, columns='*', **kwargs):
        self.columns = columns
        return self

    def eq(self, key, val):
        self.filters.append(lambda r: r.get(key) == val)
        return self

    def neq(self, key, val):
        self.filters.append(lambda r: r.get(key) != val)
        return self

    def in_(self, key, val):
        self.filters.append(lambda r: r.get(key) in val)
        return self

    def is_(self, key, val):
        assert val == 'null'
        return self.eq(key, None)

    def lt(self, key, val):
        self.filters.append(lambda r: r[key] < val)
        return self

    def gt(self, key, val):
        self.filters.append(lambda r: r[key] > val)
        return self

    def ilike(self, key, val):
        pattern = re.escape(val).replace('%', '.*').replace('_', '.')
        self.filters.append(lambda r: re.fullmatch(pattern, r[key], re.I) is not None)
        return self

    def order(self, key, desc=False):
        self.sort = (key, desc)
        return self

    def limit(self, n):
        self.maximum = n
        return self

    def single(self):
        self.one = True
        return self

    def insert(self, data):
        self.action, self.payload = 'insert', data
        return self

    def update(self, data):
        self.action, self.payload = 'update', data
        return self

    def delete(self):
        self.action = 'delete'
        return self

    def upsert(self, data, on_conflict):
        self.action, self.payload, self.conflict = 'upsert', data, on_conflict.split(',')
        return self

    def execute(self):
        table = self.store.rows[self.name]
        matched = [r for r in table if all(f(r) for f in self.filters)]
        if self.action == 'upsert':
            found = next((r for r in table if all(r[k] == self.payload[k] for k in self.conflict)), None)
            if found is not None:
                found.update(self.payload)
                return NS(data=[deepcopy(found)], count=1)
            self.action = 'insert'
        if self.action == 'insert':
            matched = []
            for payload in self.payload if isinstance(self.payload, list) else [self.payload]:
                row = dict(id=len(table)+1 if self.name == 'courses' else str(uuid4()), created_at=now(), updated_at=now())
                if self.name == 'meeting_proposals': row['is_confirmed'] = False
                if self.name == 'meeting_results': row['confirmed_at'] = now()
                if self.name == 'schedule': row['group_id'] = None
                row.update(deepcopy(payload))
                table.append(row)
                matched.append(row)
        elif self.action == 'update':
            for row in matched: row.update(deepcopy(self.payload))
        elif self.action == 'delete':
            self.store.rows[self.name] = [r for r in table if r not in matched]
        count = len(matched)
        if self.sort: matched = sorted(matched, key=lambda r:r[self.sort[0]], reverse=self.sort[1])
        if self.maximum is not None: matched = matched[:self.maximum]
        result = deepcopy(matched)
        for row in result:
            if 'users(' in self.columns:
                row['users'] = next((deepcopy(u) for u in self.store.rows['users'] if u['id']==row['user_id']), None)
            if 'chat_rooms(' in self.columns:
                row['chat_rooms'] = next((deepcopy(r) for r in self.store.rows['chat_rooms'] if r['id']==row['room_id']), None)
            if 'user_study_groups(count)' in self.columns:
                row['user_study_groups'] = [{'count':sum(m['study_group_id']==row['id'] for m in self.store.rows['user_study_groups'])}]
            if 'meeting_proposals(' in self.columns:
                row['meeting_proposals'] = next((deepcopy(p) for p in self.store.rows['meeting_proposals'] if p['id']==row['proposal_id']), None)
        return NS(data=(result[0] if result else None) if self.one else result, count=count)
