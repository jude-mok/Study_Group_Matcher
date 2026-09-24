import os
import sys
import socket
import unittest
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

for key, value in {'SUPABASE_URL':'https://test.invalid','SUPABASE_KEY':'test-only','SUPABASE_SERVICE_ROLE_KEY':'test-only','SUPABASE_JWT_SECRET':'test-only','CORS_ORIGINS':'http://localhost:5173'}.items():
    os.environ[key] = value
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fake_supabase import Store
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.database import get_supabase, get_supabase_admin
from app.routers import chat
from app.tasks import meeting_expiry


class APIIntegration(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(socket.socket, 'connect', side_effect=AssertionError('External network forbidden')))
        self.db = Store()
        self.public = Store()
        self.public.rows = self.db.rows
        self.public.auth.accounts = self.db.auth.accounts
        self.public.auth.tokens = self.db.auth.tokens
        app.dependency_overrides[get_supabase] = lambda:self.public
        app.dependency_overrides[get_supabase_admin] = lambda:self.db
        self.addCleanup(app.dependency_overrides.clear)
        self.stack.enter_context(patch.object(chat, 'get_supabase_admin', return_value=self.db))
        self.stack.enter_context(patch.object(meeting_expiry, 'get_supabase_admin', return_value=self.db))
        self.stack.enter_context(patch.object(meeting_expiry, 'start_scheduler'))
        self.stack.enter_context(patch.object(meeting_expiry, 'stop_scheduler'))
        self.client = self.stack.enter_context(TestClient(app, raise_server_exceptions=False))
        self.a, self.b, self.c = [self.register(x) for x in ('alpha','bravo','charlie')]
        self.course = self.req('POST','/courses/',self.a,body={'course_code':'CSCI-UA 102','course_name':'Data Structures'},status=201)

    def req(self, method, path, who=None, body=None, status=200):
        kwargs = {'headers':{'Authorization':'Bearer '+who['access_token']}} if who else {}
        if body is not None:kwargs['json']=body
        r = self.client.request(method,path,**kwargs)
        self.assertEqual(r.status_code,status, f'{method} {path}: {r.status_code} {r.text[:250]}')
        return r.json() if r.content else None

    def register(self, name):
        data={'name':name,'nyu_email':name+'@nyu.edu','nyu_id':name,'password':'test-password-only','major':'CS','academic_standing':2,'work_willingness':8,'avg_gpa':3.7,'preferred_location':'Bobst','time_preference':'morning'}
        self.req('POST','/auth/signup',body=data,status=201)
        return self.req('POST','/auth/login',body={'nyu_email':data['nyu_email'],'password':data['password']})

    def group(self, capacity=3):
        return self.req('POST','/study-groups/',self.a,{'course_id':self.course['id'],'name':'Integration group','max_members':capacity},201)

    def room(self, members=True):
        g=self.group()
        if members:self.req('POST',f"/study-groups/{g['id']}/join",self.b,status=201)
        room=self.req('GET','/rooms',self.a)[0]
        return g,room

    def times(self):
        start=datetime.now(timezone.utc)+timedelta(days=2)
        return {'start_time':start.isoformat(),'end_time':(start+timedelta(hours=1)).isoformat()}

    def proposal(self, room):
        return self.req('POST','/meetings/proposals',self.a,{'room_id':room['id'],**self.times()},201)

    def test_health_and_openapi(self):
        self.assertEqual(self.req('GET','/health'),{'status':'healthy'})
        self.req('GET','/')
        self.assertIn('/meetings/votes',self.req('GET','/openapi.json')['paths'])

    def test_cors(self):
        for origin, expected in [('http://localhost:5173',200),('https://untrusted.invalid',400)]:
            with self.subTest(origin=origin):
                r=self.client.options('/users/me',headers={'Origin':origin,'Access-Control-Request-Method':'GET'})
                self.assertEqual(r.status_code,expected)

    def test_protected_routes_require_auth(self):
        for path in ['/users/me','/user-courses/','/study-groups/me','/study-groups/recommend','/rooms','/schedules/me','/meetings/proposals/missing','/auth/verify-email-status']:
            with self.subTest(path=path):self.req('GET',path,status=403)

    def test_invalid_token_rejected(self):
        self.req('GET','/users/me',{'access_token':'invalid'},status=401)

    def test_signup_validation_no_secret_echo(self):
        r=self.client.post('/auth/signup',json={'password':'do-not-echo-this'})
        self.assertEqual(r.status_code,422)
        self.assertNotIn('do-not-echo-this',r.text)

    def test_signup_duplicate_email_and_id(self):
        data={**self.a['user'],'password':'test-password-only'}
        self.req('POST','/auth/signup',body=data,status=409)
        data['nyu_email']='different@nyu.edu'
        self.req('POST','/auth/signup',body=data,status=409)

    def test_signup_non_nyu_rejected(self):
        self.req('POST','/auth/signup',body={**self.a['user'],'nyu_email':'person@example.com','password':'test-password-only'},status=422)

    def test_login_wrong_password(self):
        self.req('POST','/auth/login',body={'nyu_email':'alpha@nyu.edu','password':'wrong'},status=401)

    def test_refresh_preserves_identity(self):
        result=self.req('POST','/auth/refresh',body={'refresh_token':self.a['refresh_token']})
        self.assertEqual(result['user']['id'],self.a['user']['id'])
        self.req('POST','/auth/refresh',body={'refresh_token':'invalid'},status=401)

    def test_logout_response(self):
        self.req('POST','/auth/logout',self.a)

    def test_profile_read_update_isolation(self):
        self.req('PUT','/users/me',self.a,{'name':'Changed'})
        self.assertEqual(self.req('GET','/users/me',self.a)['name'],'changed')
        self.assertEqual(self.req('GET','/users/me',self.b)['name'],'bravo')
        self.req('GET','/users/'+self.a['user']['id'],self.b)
        self.req('PUT','/users/me',self.a,{},400)
        self.req('PUT','/users/me',self.a,{'avg_gpa':8},422)

    def test_course_search_normalization_duplicate(self):
        self.assertEqual(self.course['course_code'],'CSCI-UA102')
        self.req('POST','/courses/',self.a,body={'course_code':' CSCI-UA 102 ','course_name':'dup'},status=409)
        self.assertEqual(len(self.req('GET','/courses/search?course_code=CSCI-UA%20102')),1)
        self.req('GET',f"/courses/{self.course['id']}")
        self.req('GET','/courses/search?course_code=%20',status=400)

    def test_enrollment_lifecycle_and_isolation(self):
        data={'course_id':self.course['id'],'term':'Fall','year':2026}
        self.req('POST','/user-courses/',self.a,data,201)
        self.req('POST','/user-courses/',self.a,data,409)
        self.assertEqual(len(self.req('GET','/user-courses/',self.a)),1)
        self.assertEqual(self.req('GET','/user-courses/',self.b),[])
        path=f"/user-courses/?course_id={self.course['id']}"
        self.req('DELETE',path,self.a,status=204)
        self.req('DELETE',path,self.a,status=404)

    def test_group_creation_metadata_and_room(self):
        g=self.group()
        self.assertEqual(g['admin_id'],self.a['user']['id'])
        self.assertEqual(g['current_members'],1)
        self.assertEqual(self.req('GET','/study-groups/me',self.a)[0]['id'],g['id'])
        self.assertEqual(self.req('GET',f"/study-groups/course/{self.course['id']}",self.a)[0]['id'],g['id'])
        self.req('GET','/study-groups/search?name=Integration',self.a)
        r=self.req('GET','/rooms',self.a)[0]
        self.req('POST','/rooms',self.a,{'group_id':g['id']},201)
        self.assertEqual(len(self.db.rows['chat_rooms']),1)
        self.assertEqual(r['group_id'],g['id'])

    def test_join_duplicate_capacity_and_leave(self):
        g=self.group(2); path=f"/study-groups/{g['id']}"
        self.req('POST',path+'/join',self.b,status=201)
        self.req('POST',path+'/join',self.b,status=409)
        self.req('POST',path+'/join',self.c,status=400)
        self.assertEqual(len(self.req('GET',path+'/members',self.a)),2)
        self.req('DELETE',path+'/leave',self.b,status=204)
        self.assertEqual(self.req('GET','/rooms',self.b),[])
        self.req('GET',path+'/members',self.b,status=403)
        self.req('DELETE',path+'/leave',self.b,status=404)

    def test_kick_and_admin_permissions(self):
        g,r=self.room();p=f"/study-groups/{g['id']}"
        self.req('GET',p+'/requests',self.b,status=403)
        self.req('DELETE',p+'/members/'+self.a['user']['id'],self.a,status=400)
        self.req('DELETE',p+'/members/'+self.b['user']['id'],self.a)
        self.req('GET',f"/rooms/{r['id']}/messages",self.b,status=403)
        self.req('DELETE',p+'/members/'+self.b['user']['id'],self.a,status=404)

    def test_recommendations_course_membership_and_capacity(self):
        g=self.group(2)
        self.assertEqual(self.req('GET','/study-groups/recommend',self.b),[])
        self.req('POST','/user-courses/',self.b,{'course_id':self.course['id'],'term':'Fall','year':2026},201)
        rec=self.req('GET','/study-groups/recommend',self.b)[0]
        self.assertEqual(rec['id'],g['id']);self.assertEqual(rec['match_score'],100)
        self.assertEqual(sum(rec['score_breakdown'].values()),100)
        self.req('POST',f"/study-groups/{g['id']}/join",self.c,status=201)
        self.assertEqual(self.req('GET','/study-groups/recommend',self.b),[])

    def test_schedule_crud_and_permissions(self):
        s=self.req('POST','/schedules/',self.a,{'title':'Read',**self.times()},201);path='/schedules/'+s['id']
        self.req('GET',path,self.a);self.req('GET',path,self.b,status=403)
        self.req('PUT',path,self.b,{'title':'Hijack'},403)
        self.req('DELETE',path,self.b,status=403)
        self.req('PUT',path,self.a,{'title':'Review'})
        self.assertEqual(len(self.req('GET','/schedules/me',self.a)),1)
        self.req('DELETE',path,self.a,status=204);self.req('GET',path,self.a,status=404)

    def test_schedule_invalid_range(self):
        t=self.times();t['end_time']=t['start_time']
        self.req('POST','/schedules/',self.a,{'title':'Bad',**t},400)

    def test_schedule_partial_update_validates_existing_range(self):
        s=self.req('POST','/schedules/',self.a,{'title':'Read',**self.times()},201)
        self.req('PUT','/schedules/'+s['id'],self.a,{'end_time':s['start_time']},400)
        self.req('PUT','/schedules/'+s['id'],self.a,{},400)

    def test_group_schedule_access(self):
        g,r=self.room();data={'title':'Group',**self.times(),'group_id':g['id']}
        self.req('POST','/schedules/',self.c,data,403)
        s=self.req('POST','/schedules/',self.a,data,201)
        self.req('GET','/schedules/'+s['id'],self.b)
        self.assertEqual(len(self.req('GET','/schedules/group/'+g['id'],self.b)),1)
        self.req('GET','/schedules/group/'+g['id'],self.c,status=403)

    def test_meeting_vote_upsert_confirmation_and_calendar(self):
        g,r=self.room();p=self.proposal(r)
        self.req('POST','/meetings/votes',self.c,{'proposal_id':p['id'],'vote':True},403)
        for vote in [False,True,True]:self.req('POST','/meetings/votes',self.a,{'proposal_id':p['id'],'vote':vote})
        self.assertEqual(len(self.db.rows['meeting_votes']),1)
        self.req('POST','/meetings/votes',self.b,{'proposal_id':p['id'],'vote':True})
        results=self.req('GET','/meetings/results/'+r['id'],self.a)
        self.assertEqual(len(results),1);self.assertEqual(results[0]['confirmation_type'],'unanimous')
        self.assertEqual(len(self.req('GET','/schedules/group/'+g['id'],self.b)),1)
        self.assertEqual(self.req('GET','/meetings/proposals/'+r['id'],self.a),[])
        self.req('POST','/meetings/votes',self.b,{'proposal_id':p['id'],'vote':True},400)
        self.assertEqual(len(self.db.rows['schedule']),1)

    def test_proposal_admin_limit_and_expired_vote(self):
        g,r=self.room()
        self.req('POST','/meetings/proposals',self.b,{'room_id':r['id'],**self.times()},403)
        for _ in range(3):self.proposal(r)
        self.req('POST','/meetings/proposals',self.a,{'room_id':r['id'],**self.times()},400)
        p=self.db.rows['meeting_proposals'][0];p['expires_at']='2000-01-01T00:00:00+00:00'
        self.req('POST','/meetings/votes',self.a,{'proposal_id':p['id'],'vote':True},400)

    def test_expiry_selects_highest_vote_and_is_repeatable(self):
        import asyncio
        g,r=self.room();p=self.proposal(r);q=self.proposal(r)
        self.req('POST','/meetings/votes',self.a,{'proposal_id':q['id'],'vote':True})
        for row in self.db.rows['meeting_proposals']:row['expires_at']='2000-01-01T00:00:00+00:00'
        asyncio.run(meeting_expiry.check_expired_proposals())
        asyncio.run(meeting_expiry.check_expired_proposals())
        self.assertEqual(len(self.db.rows['meeting_results']),1)
        self.assertEqual(self.db.rows['meeting_results'][0]['proposal_id'],q['id'])
        self.assertEqual(len(self.db.rows['schedule']),1)

    def test_websocket_broadcast_persistence_and_pagination(self):
        g,r=self.room();url='/ws/rooms/'+r['id']+'?token='
        with self.client.websocket_connect(url+self.a['access_token']) as a, self.client.websocket_connect(url+self.b['access_token']) as b:
            a.send_json({'content':'  first  '})
            first=a.receive_json();self.assertEqual(b.receive_json(),first)
            self.assertEqual(first['content'],'first')
            b.send_json({'content':'second'})
            second=a.receive_json();self.assertEqual(b.receive_json(),second)
        path='/rooms/'+r['id']+'/messages'
        self.assertEqual(len(self.req('GET',path,self.a)),2)
        self.assertEqual(self.req('GET',path+'?limit=1',self.a)[0]['content'],'second')
        self.assertEqual(self.req('GET',path+'?before='+second['created_at'].replace('+','%2B'),self.a)[0]['content'],'first')
        self.req('GET',path+'?limit=0',self.a,status=422)

    def test_websocket_rejects_bad_token_and_nonmember(self):
        g,r=self.room()
        for token,code in [('invalid',4001),(self.c['access_token'],4003)]:
            with self.subTest(code=code), self.assertRaises(WebSocketDisconnect) as raised:
                with self.client.websocket_connect('/ws/rooms/'+r['id']+'?token='+token):pass
            self.assertEqual(raised.exception.code,code)

    def test_account_delete_revokes_profile(self):
        self.req('DELETE','/users/me',self.c,status=204)
        self.req('GET','/users/me',self.c,status=401)
        self.assertNotIn(self.c['user']['id'],self.db.auth.accounts)

    # Desired security/invariant behavior; do not mark xfail or weaken assertions.
    def test_security_course_creation_requires_authentication(self):
        r=self.client.post('/courses/',json={'course_code':'UNAUTH','course_name':'Unauthorized'})
        self.assertIn(r.status_code,(401,403))

    def test_security_email_status_uses_request_identity(self):
        result=self.req('GET','/auth/verify-email-status',self.a)
        self.assertEqual(result['email'],self.a['user']['nyu_email'])

    def test_security_password_reset_requires_recovery_identity(self):
        r=self.client.post('/auth/password-reset/confirm',json={'new_password':'attacker-password'})
        self.assertIn(r.status_code,(401,403))
        self.assertNotEqual(self.db.auth.accounts[self.c['user']['id']]['password'],'attacker-password')

    def test_security_profile_password_changes_only_caller(self):
        self.req('PUT','/users/me',self.a,{'password':'new-alpha-password'})
        self.assertEqual(self.db.auth.accounts[self.a['user']['id']]['password'],'new-alpha-password')
        self.assertEqual(self.db.auth.accounts[self.c['user']['id']]['password'],'test-password-only')

    def test_accept_request_cannot_exceed_capacity(self):
        g=self.group(2)
        self.req('POST',f"/study-groups/{g['id']}/join",self.b,status=201)
        request=self.db.table('group_join_requests').insert({'study_group_id':g['id'],'user_id':self.c['user']['id'],'status':'pending'}).execute().data[0]
        r=self.client.post(f"/study-groups/{g['id']}/requests/{request['id']}/accept",headers={'Authorization':'Bearer '+self.a['access_token']})
        self.assertIn(r.status_code,(400,409))

    def test_schedule_mixed_timezone_returns_client_error(self):
        times=self.times();times['end_time']=times['end_time'].replace('+00:00','')
        r=self.client.post('/schedules/',json={'title':'Timezone mismatch',**times},headers={'Authorization':'Bearer '+self.a['access_token']})
        self.assertIn(r.status_code,(400,422))

    def test_removed_member_cannot_send_on_existing_socket(self):
        g,r=self.room()
        with self.client.websocket_connect('/ws/rooms/'+r['id']+'?token='+self.b['access_token']) as ws:
            self.req('DELETE',f"/study-groups/{g['id']}/members/{self.b['user']['id']}",self.a)
            with self.assertRaises(WebSocketDisconnect):
                ws.receive_json()
        self.assertFalse(any(m['content']=='must not persist' for m in self.db.rows['messages']))


    def test_pending_request_accept_decline_and_replay(self):
        g=self.group(3);base=f"/study-groups/{g['id']}/requests"
        def pending(who):
            return self.db.table('group_join_requests').insert({'study_group_id':g['id'],'user_id':who['user']['id'],'status':'pending'}).execute().data[0]
        b=pending(self.b);c=pending(self.c)
        self.assertEqual(len(self.req('GET',base,self.a)),2)
        self.req('POST',base+'/'+b['id']+'/accept',self.b,status=403)
        self.req('POST',base+'/'+b['id']+'/accept',self.a)
        self.req('POST',base+'/'+b['id']+'/accept',self.a,status=404)
        self.assertEqual(len(self.req('GET','/rooms',self.b)),1)
        self.req('POST',base+'/'+c['id']+'/decline',self.a)
        self.assertEqual(self.req('GET',base,self.a),[])
        self.assertEqual(self.req('GET','/rooms',self.c),[])

    def test_missing_resources_and_nonmember_room_creation(self):
        self.req('GET','/users/missing',self.a,status=404)
        self.req('POST','/study-groups/missing/join',self.a,status=404)
        self.req('POST','/meetings/votes',self.a,{'proposal_id':'missing','vote':True},404)
        g=self.group()
        self.req('POST','/rooms',self.b,{'group_id':g['id']},403)

    def test_meeting_confirmation_broadcast(self):
        g,r=self.room();p=self.proposal(r)
        with self.client.websocket_connect('/ws/rooms/'+r['id']+'?token='+self.a['access_token']) as ws:
            self.req('POST','/meetings/votes',self.a,{'proposal_id':p['id'],'vote':True})
            self.assertEqual(ws.receive_json()['type'],'vote_update')
            self.req('POST','/meetings/votes',self.b,{'proposal_id':p['id'],'vote':True})
            self.assertEqual(ws.receive_json()['type'],'vote_update')
            self.assertEqual(ws.receive_json()['type'],'meeting_confirmed')

    def test_password_reset_request_generic_response(self):
        a=self.req('POST','/auth/password-reset/request',body={'email':'alpha@nyu.edu'})
        b=self.req('POST','/auth/password-reset/request',body={'email':'unknown@nyu.edu'})
        self.assertEqual(a,b)

    def test_authenticated_user_enumeration_requires_login(self):
        self.req('GET','/users/'+self.a['user']['id'],status=403)

    def test_delete_account_removes_membership_and_personal_data(self):
        g,r=self.room()
        self.req('POST','/schedules/',self.b,{'title':'Private',**self.times()},201)
        self.req('POST','/user-courses/',self.b,{'course_id':self.course['id'],'term':'Fall','year':2026},201)
        self.req('DELETE','/users/me',self.b,status=204)
        for table,key in [('room_members','user_id'),('user_study_groups','user_id'),('schedule','created_by'),('user_courses','user_id')]:
            self.assertFalse(any(row[key]==self.b['user']['id'] for row in self.db.rows[table]))


    def test_password_reset_valid_bearer_updates_only_identity(self):
        self.req('POST','/auth/password-reset/confirm',self.a,{'new_password':'changed-password'})
        self.assertEqual(self.db.auth.accounts[self.a['user']['id']]['password'],'changed-password')
        self.assertEqual(self.db.auth.accounts[self.c['user']['id']]['password'],'test-password-only')
        self.req('POST','/auth/password-reset/confirm',{'access_token':'invalid'},{'new_password':'changed-password'},401)

    def test_leave_closes_existing_socket(self):
        g,r=self.room()
        with self.client.websocket_connect('/ws/rooms/'+r['id']+'?token='+self.b['access_token']) as ws:
            self.req('DELETE',f"/study-groups/{g['id']}/leave",self.b,status=204)
            with self.assertRaises(WebSocketDisconnect):ws.receive_json()

    def test_membership_is_rechecked_before_message_write(self):
        g,r=self.room()
        with self.client.websocket_connect('/ws/rooms/'+r['id']+'?token='+self.b['access_token']) as ws:
            self.db.table('room_members').delete().eq('room_id',r['id']).eq('user_id',self.b['user']['id']).execute()
            ws.send_json({'content':'blocked'})
            with self.assertRaises(WebSocketDisconnect):ws.receive_json()
        self.assertFalse(self.db.rows['messages'])

    def test_meeting_requires_timezone(self):
        g,r=self.room();t=self.times();t['start_time']=t['start_time'].replace('+00:00','')
        self.req('POST','/meetings/proposals',self.a,{'room_id':r['id'],**t},422)
