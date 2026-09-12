import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from device_session import AuthError, Session, VERIFY, private_write


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.transport = Mock()
        self.session = Session(self.base, self.transport, pause=lambda _: None)

    def tearDown(self):
        self.tmp.cleanup()

    def start(self):
        return 200, {'user_code': 'ABCD-EFGH', 'verification_uri': VERIFY}

    def test_approved_key_is_only_kept_on_device(self):
        self.transport.side_effect = [self.start(), (200, {'status': 'pending'}), (200, {'status': 'approved'})]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.session.connect()
        token = self.session.token()
        self.assertNotIn(token, output.getvalue())
        self.assertNotIn(token, json.dumps(self.transport.call_args_list[0].args))
        self.assertEqual((self.base/'device.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.transport.call_args.kwargs['token'], token)

    def test_pending_key_is_not_an_active_credential(self):
        self.transport.side_effect = [self.start(), (401, {})]
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(AuthError):
            self.session.connect()
        self.assertFalse((self.base/'device.json').exists())

    def test_existing_authorization_needs_no_new_registration(self):
        private_write(self.base/'device.json', {'token': 'sali1_'+'a'*43})
        self.transport.return_value = 200, {'status': 'approved'}
        with contextlib.redirect_stdout(io.StringIO()):
            self.session.connect()
        self.assertEqual(self.transport.call_count, 1)

    def test_offline_does_not_replace_existing_key(self):
        private_write(self.base/'device.json', {'token': 'sali1_'+'a'*43})
        before = (self.base/'device.json').read_bytes()
        self.transport.side_effect = AuthError('offline')
        with self.assertRaises(AuthError):
            self.session.connect()
        self.assertEqual((self.base/'device.json').read_bytes(), before)

    def test_wrong_approval_site_is_rejected(self):
        self.transport.return_value = 200, {'user_code': 'ABCD-EFGH', 'verification_uri': 'https://example.invalid'}
        with self.assertRaises(AuthError):
            self.session.connect()
        self.assertFalse((self.base/'device.json').exists())

    def test_permissions_and_key_shape(self):
        private_write(self.base/'device.json', {'token': 'sali1_'+'a'*43})
        (self.base/'device.json').chmod(0o644)
        with self.assertRaises(AuthError): self.session.token()
        private_write(self.base/'device.json', {'token': 'not-a-device-key'})
        with self.assertRaises(AuthError): self.session.token()

    def test_timeout_keeps_uploads_disabled(self):
        times = iter([0, 601])
        self.session.clock = lambda: next(times)
        self.transport.return_value = self.start()
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(AuthError):
            self.session.connect()
        self.assertFalse((self.base/'config.json').exists())
        self.assertFalse((self.base/'device.json').exists())
