import unittest
from unittest.mock import patch
from types import SimpleNamespace
import test_api_integration as fixtures
from app.routers import auth


class PasswordRecovery(unittest.TestCase):
    setUp = fixtures.APIIntegration.setUp
    req = fixtures.APIIntegration.req
    register = fixtures.APIIntegration.register

    def test_email_redirect_and_generic_response(self):
        redirect = 'https://web.example/?reset=1'
        with patch.object(auth, 'get_settings', return_value=SimpleNamespace(password_reset_redirect_url=redirect)):
            with patch.object(self.public.auth, 'reset_password_email') as send:
                first = self.req('POST', '/auth/password-reset/request', body={'email':'alpha@nyu.edu'})
                second = self.req('POST', '/auth/password-reset/request', body={'email':'unknown@nyu.edu'})
                self.assertEqual(first, second)
                send.assert_called_with('unknown@nyu.edu', {'redirect_to':redirect})

    def test_recovery_token_updates_owner_and_allows_new_login(self):
        owner_id = self.a['user']['id']
        self.db.auth.tokens['test-recovery-token'] = owner_id
        self.req('POST', '/auth/password-reset/confirm', {'access_token':'test-recovery-token'}, {'new_password':'new-test-password'})
        self.assertEqual(self.db.auth.accounts[owner_id]['password'], 'new-test-password')
        self.assertEqual(self.db.auth.accounts[self.b['user']['id']]['password'], 'test-password-only')
        self.req('POST', '/auth/login', body={'nyu_email':'alpha@nyu.edu', 'password':'new-test-password'})
        self.req('POST', '/auth/password-reset/confirm', {'access_token':'invalid'}, {'new_password':'new-test-password'}, status=401)
