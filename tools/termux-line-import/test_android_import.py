import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from android_parser import AndroidExportError, parse_android_export
from client import ENDPOINT, Outbox

SAMPLE = '[LINE] test\r\n保存日時: test\r\n\r\n2026/9/12(土)\r\n12:00\t姓 名\t商品A\r\n\r\n商品B\t注記\r\n12:01\t別の人\t末尾\r\n'


class ParserTests(unittest.TestCase):
    def test_multiline_and_sender_spaces(self):
        result = parse_android_export(SAMPLE)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['display_name'], '姓 名')
        self.assertEqual(result[0]['body'], '商品A\n\n商品B\t注記')
        self.assertEqual(result[-1]['body'], '末尾')
        self.assertEqual(result[0]['timestamp'], '2026-09-12 12:00:00')

    def test_bom(self):
        self.assertEqual(parse_android_export('\ufeff' + SAMPLE), parse_android_export(SAMPLE))

    def test_system_record_is_not_supplier(self):
        result = parse_android_export(SAMPLE + '12:02\t参加しました\n')
        self.assertTrue(result[-1]['is_system_event'])
        self.assertEqual(result[-1]['display_name'], '')

    def test_literal_quotes_not_csv(self):
        result = parse_android_export('2026/9/12(土)\n1:02\tA\t"引用\n続き"')
        self.assertEqual(result[0]['body'], '"引用\n続き"')

    def test_empty_pc_and_invalid_dates_rejected(self):
        for value in ['', '2026.09.12 土曜日\n12:00 A text',
                      '2026/2/30(月)\n12:00\tA\tB',
                      '2026/9/12(土)\n24:01\tA\tB',
                      '2026/9/12(土)\n12:01\t\tB']:
            with self.subTest(value=value), self.assertRaises(AndroidExportError):
                parse_android_export(value)

    def test_headerless_content_after_date_rejected(self):
        with self.assertRaises(AndroidExportError):
            parse_android_export('2026/9/12(土)\nmissing header\n12:00\tA\tB')


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.txt'
        self.source.write_bytes(SAMPLE.encode())
        self.outbox = Outbox(self.root / 'state')
        self.outbox.enqueue(self.source)
        (self.outbox.base / 'config.json').write_text(json.dumps({'enabled':True,'endpoint':ENDPOINT}))
        from device_session import private_write
        private_write(self.outbox.base / 'device.json', {'token': 'sali1_' + 'a' * 43})

    def tearDown(self):
        self.outbox.db.close()
        self.tmp.cleanup()

    def result(self, **extra):
        return 200, json.dumps(dict(status='imported',review_status='ok',import_job_id='test-job', **extra))

    def test_original_and_duplicate(self):
        self.outbox.enqueue(self.source)
        self.assertEqual(self.outbox.status(), {'queued':1})
        copy = next((self.outbox.base/'originals').glob('*.txt'))
        self.assertEqual(copy.read_bytes(), self.source.read_bytes())

    def test_pending_review_is_not_accepted(self):
        result = self.outbox.send(lambda raw, token:(200,json.dumps({'status':'imported','review_status':'pending_review','import_job_id':'test-job'})))
        self.assertEqual(result, {'pending_review':1})

    def test_accepted_not_resent(self):
        calls=[]
        def transport(raw, token):
            calls.append(raw)
            return self.result()
        self.outbox.send(transport)
        self.outbox.send(transport, force=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], self.source.read_bytes())

    def test_network_retry(self):
        self.assertEqual(self.outbox.send(lambda *_:(0,'')), {'retry':1})
        self.assertEqual(self.outbox.send(lambda *_:self.result(),force=True), {'accepted':1})

    def test_auth_error_retains_original(self):
        self.assertEqual(self.outbox.send(lambda *_:(401,'')), {'auth_required':1})
        self.assertEqual(len(list((self.outbox.base/'originals').glob('*.txt'))),1)

    def test_bad_success_is_not_accepted(self):
        self.assertEqual(self.outbox.send(lambda *_:(200,'{"success":true}')), {'retry':1})

    def test_missing_api_not_pc_fallback(self):
        self.assertEqual(self.outbox.send(lambda *_:(404,'')), {'retry':1})

    def test_rejected_not_resent(self):
        self.assertEqual(self.outbox.send(lambda *_:(422,'')), {'rejected':1})
        self.assertEqual(self.outbox.send(lambda *_:self.result(),force=True), {'rejected':1})

    def test_tampered_original_blocks_upload(self):
        next((self.outbox.base/'originals').glob('*.txt')).write_text('changed')
        with self.assertRaises(ValueError):
            self.outbox.send(lambda *_:self.result())

    def test_wrong_destination_blocks_upload(self):
        (self.outbox.base/'config.json').write_text(json.dumps({'enabled':True,'endpoint':'https://example.org'}))
        with self.assertRaises(ValueError):
            self.outbox.send(lambda *_:self.result())


if __name__ == '__main__':
    unittest.main()
