import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from client import ENDPOINT, Outbox
from firebase_session import (
    MFA,
    REFRESH,
    SIGN_IN,
    AuthError,
    Session,
    private_write,
    request,
)

KEY = 'AIza' + 'a' * 35


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / 'firebase.json').write_text(json.dumps({'api_key': KEY}))
        self.verify = Mock()
        self.transport = Mock(return_value={'idToken': 'id-test', 'refreshToken': 'refresh-test', 'expiresIn': '3600'})
        self.session = Session(self.base, self.transport, self.verify)

    def tearDown(self):
        self.tmp.cleanup()

    def test_password_not_saved_and_access_checked(self):
        self.session.login('test@example.invalid', 'synthetic-password')
        self.verify.assert_called_once_with('id-test')
        self.assertEqual(self.transport.call_args.args[0], SIGN_IN)
        stored = (self.base / 'session.json').read_text()
        self.assertNotIn('synthetic-password', stored)
        self.assertNotIn('test@example.invalid', stored)
        self.assertEqual((self.base / 'session.json').stat().st_mode & 0o777, 0o600)

    def test_valid_cached_token_does_not_refresh(self):
        self.session.login('e', 'p')
        self.transport.reset_mock()
        self.assertEqual(self.session.token(), 'id-test')
        self.transport.assert_not_called()

    def test_expiring_token_rotates_both_tokens(self):
        private_write(self.base / 'session.json', {'id_token': 'old-id', 'refresh_token': 'old-refresh', 'expires_at': time.time()+30})
        self.transport.return_value = {'id_token': 'new-id', 'refresh_token': 'new-refresh', 'expires_in': '3600'}
        self.assertEqual(self.session.token(), 'new-id')
        self.assertEqual(self.transport.call_args.args, (REFRESH, KEY, {'grant_type': 'refresh_token', 'refresh_token': 'old-refresh'}))
        self.assertEqual(json.loads((self.base / 'session.json').read_text())['refresh_token'], 'new-refresh')

    def test_failed_refresh_keeps_saved_session(self):
        original = {'id_token': 'old', 'refresh_token': 'renewal', 'expires_at': 0}
        private_write(self.base / 'session.json', original)
        self.transport.side_effect = AuthError('offline')
        with self.assertRaises(AuthError):
            self.session.token()
        self.assertEqual(json.loads((self.base / 'session.json').read_text()), original)

    def test_mfa_challenge_does_not_save_password_or_code(self):
        self.transport.side_effect = [
            {'mfaPendingCredential': 'pending', 'mfaInfo': [{'mfaEnrollmentId': 'factor', 'totpInfo': {}}]},
            {'idToken': 'mfa-id', 'refreshToken': 'mfa-refresh'}]
        self.session.login('e', 'secret-pass', lambda: '123456')
        self.assertEqual(self.transport.call_args.args, (MFA, KEY, {
            'mfaPendingCredential': 'pending', 'mfaEnrollmentId': 'factor',
            'totpVerificationInfo': {'verificationCode': '123456'}}))
        self.verify.assert_called_once_with('mfa-id')
        stored = (self.base / 'session.json').read_text()
        self.assertNotIn('123456', stored)
        self.assertNotIn('pending', stored)

    def test_no_supported_factor_leaves_session_absent(self):
        self.transport.return_value = {'mfaPendingCredential': 'pending', 'mfaInfo': [{'phoneInfo': 'redacted'}]}
        with self.assertRaises(AuthError):
            self.session.login('e', 'p')
        self.assertFalse((self.base / 'session.json').exists())

    def test_permission_failure_does_not_overwrite_existing_session(self):
        private_write(self.base / 'session.json', {'preserve': True})
        self.verify.side_effect = AuthError('forbidden')
        with self.assertRaises(AuthError):
            self.session.login('e', 'p')
        self.assertEqual(json.loads((self.base / 'session.json').read_text()), {'preserve': True})

    def test_bad_response_does_not_create_session(self):
        self.transport.return_value = {'idToken': 'id', 'refreshToken': ''}
        with self.assertRaises(AuthError):
            self.session.login('e', 'p')
        self.assertFalse((self.base / 'session.json').exists())

    def test_world_readable_session_rejected(self):
        private_write(self.base / 'session.json', {'expires_at': 0})
        (self.base / 'session.json').chmod(0o644)
        with self.assertRaises(AuthError):
            self.session.token()
        self.transport.assert_not_called()

    def test_symlink_session_rejected(self):
        private_write(self.base / 'target', {'expires_at': 0})
        (self.base / 'session.json').symlink_to(self.base / 'target')
        with self.assertRaises(AuthError):
            self.session.token()

    def test_noninteractive_login_rejects_before_password_prompt(self):
        with patch('firebase_session.sys.stdin.isatty', return_value=False), patch('firebase_session.getpass.getpass') as prompt:
            with self.assertRaises(AuthError):
                self.session.interactive_login()
            prompt.assert_not_called()

    def test_referrer_restriction_does_not_echo_remote_secrets(self):
        import io
        import urllib.error

        from firebase_session import auth_failure
        body = {'error': {'message': 'sensitive-account-and-key', 'details': [
            {'reason': 'API_KEY_HTTP_REFERRER_BLOCKED'}]}}
        err = urllib.error.HTTPError('https://example.invalid', 403, 'Forbidden', {},
                                     io.BytesIO(json.dumps(body).encode()))
        text = str(auth_failure(err))
        err.close()
        self.assertIn('API_KEY_HTTP_REFERRER_BLOCKED', text)
        self.assertNotIn('sensitive-account-and-key', text)

    def test_blocked_public_config_stops_before_password(self):
        from firebase_session import PROJECT
        self.transport.side_effect = AuthError('restricted')
        with patch('firebase_session.sys.stdin.isatty', return_value=True), patch('firebase_session.secret_prompt') as password, patch('builtins.input') as email:
            with self.assertRaises(AuthError):
                self.session.interactive_login()
            password.assert_not_called()
            email.assert_not_called()
        self.assertEqual(self.transport.call_args.args[0], PROJECT)

    def test_unknown_error_body_is_not_shown(self):
        import io
        import urllib.error

        from firebase_session import auth_failure
        err = urllib.error.HTTPError('https://example.invalid', 400, 'Bad Request', {},
                                     io.BytesIO(b'{"error":{"message":"private-value"}}'))
        self.assertNotIn('private-value', str(auth_failure(err)))
        err.close()

    def test_password_echo_fallback_is_blocked(self):
        import getpass

        from firebase_session import secret_prompt
        with patch('firebase_session.getpass.getpass', side_effect=getpass.GetPassWarning):
            with self.assertRaises(AuthError):
                secret_prompt('password: ')

    def test_network_host_cannot_be_overridden(self):
        with self.assertRaises(AuthError):
            request('https://example.invalid', KEY, {})

    def test_expired_auth_prevents_upload_and_preserves_queue(self):
        source = self.base / 'talk.txt'
        source.write_text('2026/9/12(土)\n12:00\tA\tbody')
        box = Outbox(self.base)
        try:
            box.enqueue(source)
            (self.base/'config.json').write_text(json.dumps({'enabled': True, 'endpoint': ENDPOINT}))
            upload = Mock()
            with patch('client.Session.token', side_effect=AuthError('expired')):
                with self.assertRaises(AuthError):
                    box.send(upload)
            upload.assert_not_called()
            self.assertEqual(box.status(), {'queued': 1})
            self.assertEqual(len(list((self.base/'originals').glob('*.txt'))), 1)
        finally:
            box.db.close()


if __name__ == '__main__':
    unittest.main()
