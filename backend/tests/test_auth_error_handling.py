import asyncio
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import test_api_integration  # Configure offline environment before importing the app.
from app.routers import auth
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError


class AuthErrorHandling(unittest.TestCase):
    def test_login_only_invalid_credentials_becomes_401(self):
        for error, expected in [
            (AuthApiError('invalid', 400, 'invalid_credentials'), 401),
            (RuntimeError('network failure'), 500),
            (AuthApiError('provider error', 500, None), 500),
        ]:
            with self.subTest(expected=expected), patch('app.services.utils.logger'):
                client = Mock()
                client.auth.sign_in_with_password.side_effect = error
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(auth.login(NS(nyu_email='test@nyu.edu', password='test-secret'), client, Mock()))
                self.assertEqual(raised.exception.status_code, expected)

    def test_login_missing_session_is_logged(self):
        client = Mock()
        client.auth.sign_in_with_password.return_value = NS(session=None)
        with self.assertLogs(auth.logger, level='ERROR') as logs:
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(auth.login(NS(nyu_email='test@nyu.edu', password='test-secret'), client, Mock()))
        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn('login.auth_response_missing_session', logs.output[0])
        self.assertNotIn('test-secret', ''.join(logs.output))

    def test_signup_rolls_back_both_failure_types(self):
        user = NS(**dict.fromkeys(['nyu_email', 'nyu_id', 'name', 'major', 'minor', 'academic_standing', 'work_willingness', 'preferred_location', 'time_preference', 'avg_gpa']))
        for error in [HTTPException(500, 'save failed'), RuntimeError('save failed')]:
            for cleanup_fails in [False, True]:
                with self.subTest(error=type(error).__name__, cleanup_fails=cleanup_fails):
                    client = Mock()
                    if cleanup_fails:
                        client.auth.admin.delete_user.side_effect = RuntimeError('cleanup failed')
                    with patch.object(auth, '_ensure_user_not_exist'), patch.object(auth, '_create_user_credential', return_value=NS(user=NS(id='created-id'))), patch.object(auth, 'create_user_in_db', side_effect=error), patch.object(auth, 'logger') as logger:
                        with self.assertRaises(type(error)) as raised:
                            asyncio.run(auth.signup.__wrapped__(user, client))
                    self.assertIs(raised.exception, error)
                    client.auth.admin.delete_user.assert_called_once_with('created-id')
                    if cleanup_fails:
                        self.assertTrue(any(call.args[0].startswith('signup.rollback_failed') for call in logger.error.call_args_list))

    def test_signup_missing_user_is_logged(self):
        client = Mock()
        client.auth.admin.create_user.return_value = NS(user=None)
        with self.assertLogs(auth.logger, level='ERROR'):
            with self.assertRaises(HTTPException) as raised:
                auth._create_user_credential(NS(nyu_email='test@nyu.edu', password='test-secret', name='Test'), client)
        self.assertEqual(raised.exception.status_code, 502)
