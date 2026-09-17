import fcntl
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

from android_parser import AndroidExportError, parse_android_export
import client as client_module
from client import ENDPOINT, NOTIFY_PROGRESS, NOTIFY_STALL, Outbox

SAMPLE = '[LINE] test\r\n保存日時: test\r\n\r\n2026/9/12(土)\r\n12:00\t姓 名\t商品A\r\n\r\n商品B\t注記\r\n12:01\t別の人\t末尾\r\n'


class FakeClock:
    def __init__(self, start=1_700_000_000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeNotifier:
    """Stand-in for termux_notify. ok=True/False controls the return value;
    set ok to an Exception instance to simulate the notifier raising."""

    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []

    def __call__(self, nid, title, content):
        self.calls.append((nid, title, content))
        if isinstance(self.ok, Exception):
            raise self.ok
        return self.ok


class ParserTests(unittest.TestCase):
    def test_multiline_and_sender_spaces(self):
        result = parse_android_export(SAMPLE)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['display_name'], '姓 名')
        self.assertEqual(result[0]['body'], '商品A\n\n商品B\t注記')
        self.assertEqual(result[-1]['body'], '末尾')
        self.assertEqual(result[0]['timestamp'], '2026-09-12 12:00:00')

    def test_bom(self):
        self.assertEqual(parse_android_export('﻿' + SAMPLE), parse_android_export(SAMPLE))

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
        self.clock = FakeClock()
        self.notifier = FakeNotifier()
        self.outbox = Outbox(self.root / 'state', clock=self.clock, notifier=self.notifier)
        self.outbox.enqueue(self.source)
        (self.outbox.base / 'config.json').write_text(json.dumps({'enabled': True, 'endpoint': ENDPOINT}))
        from device_session import private_write
        private_write(self.outbox.base / 'device.json', {'token': 'sali1_' + 'a' * 43})

    def tearDown(self):
        self.outbox.db.close()
        self.tmp.cleanup()

    def result(self, **extra):
        return 200, json.dumps(dict(status='imported', review_status='ok', import_job_id='test-job', **extra))

    def counts(self, status):
        """Strip the newly-added 'latest'/'stall_seconds' keys so older
        assertions about plain state counts still read cleanly."""
        return {k: v for k, v in status.items() if k not in ('latest', 'stall_seconds')}

    # -- pre-existing behaviour (kept, adapted to the enlarged status() dict) --

    def test_original_and_duplicate(self):
        self.outbox.enqueue(self.source)
        self.assertEqual(self.counts(self.outbox.status()), {'queued': 1})
        copy = next((self.outbox.base / 'originals').glob('*.txt'))
        self.assertEqual(copy.read_bytes(), self.source.read_bytes())

    def test_pending_review_is_not_accepted(self):
        result = self.outbox.send(lambda raw, token: (200, json.dumps(
            {'status': 'imported', 'review_status': 'pending_review', 'import_job_id': 'test-job'})))
        self.assertEqual(self.counts(result), {'pending_review': 1})

    def test_accepted_not_resent(self):
        calls = []

        def transport(raw, token):
            calls.append(raw)
            return self.result()

        self.outbox.send(transport)
        self.outbox.send(transport, force=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], self.source.read_bytes())

    def test_network_retry(self):
        self.assertEqual(self.counts(self.outbox.send(lambda *_: (0, ''))), {'retry': 1})
        self.assertEqual(self.counts(self.outbox.send(lambda *_: self.result(), force=True)), {'accepted': 1})

    def test_auth_error_retains_original(self):
        self.assertEqual(self.counts(self.outbox.send(lambda *_: (401, ''))), {'auth_required': 1})
        self.assertEqual(len(list((self.outbox.base / 'originals').glob('*.txt'))), 1)

    def test_bad_success_is_not_accepted(self):
        self.assertEqual(self.counts(self.outbox.send(lambda *_: (200, '{"success":true}'))), {'retry': 1})

    def test_missing_api_not_pc_fallback(self):
        self.assertEqual(self.counts(self.outbox.send(lambda *_: (404, ''))), {'retry': 1})

    def test_rejected_not_resent(self):
        self.assertEqual(self.counts(self.outbox.send(lambda *_: (422, ''))), {'rejected': 1})
        self.assertEqual(self.counts(self.outbox.send(lambda *_: self.result(), force=True)), {'rejected': 1})

    def test_tampered_original_blocks_upload(self):
        next((self.outbox.base / 'originals').glob('*.txt')).write_text('changed')
        with self.assertRaises(ValueError):
            self.outbox.send(lambda *_: self.result())

    def test_wrong_destination_blocks_upload(self):
        (self.outbox.base / 'config.json').write_text(json.dumps({'enabled': True, 'endpoint': 'https://example.org'}))
        with self.assertRaises(ValueError):
            self.outbox.send(lambda *_: self.result())

    # -- notifications and history -------------------------------------------------

    def test_success_events_and_notification(self):
        self.outbox.send(lambda *_: self.result(message_count=3))
        stages = [(row[0], row[1]) for row in
                  self.outbox.db.execute('SELECT stage, result FROM events ORDER BY id')]
        self.assertIn(('received', 'ok'), stages)
        self.assertIn(('store', 'ok'), stages)
        self.assertIn(('send', 'started'), stages)
        self.assertIn(('send', 'accepted'), stages)
        self.assertEqual(len(self.notifier.calls), 1)
        _, title, content = self.notifier.calls[0]
        self.assertIn('取り込み完了', title)
        self.assertIn('3件', content)

    def test_pending_review_notification(self):
        self.outbox.send(lambda *_: (200, json.dumps({
            'status': 'imported', 'review_status': 'pending_review',
            'import_job_id': 'job', 'unresolved_count': 2})))
        self.assertEqual(len(self.notifier.calls), 1)
        nid, title, content = self.notifier.calls[0]
        self.assertEqual(nid, NOTIFY_PROGRESS)
        self.assertIn('確認待ち', title)
        self.assertIn('2件', content)

    def test_network_failure_reason_and_notification(self):
        self.outbox.send(lambda *_: (0, ''))
        reasons = [row[0] for row in self.outbox.db.execute(
            "SELECT reason FROM events WHERE stage='send' AND result='retry'")]
        self.assertTrue(any('通信できません' in (reason or '') for reason in reasons))
        self.assertEqual(len(self.notifier.calls), 1)
        self.assertIn('失敗', self.notifier.calls[0][1])

    def test_notify_failure_is_recorded_but_does_not_block_send(self):
        self.notifier.ok = False
        result = self.outbox.send(lambda *_: self.result())
        self.assertEqual(self.counts(result), {'accepted': 1})
        failed = self.outbox.db.execute(
            "SELECT 1 FROM events WHERE stage='notify' AND result='failed'").fetchall()
        self.assertTrue(failed)

    def test_notify_exception_is_recorded_but_does_not_block_send(self):
        self.notifier.ok = RuntimeError('boom')
        result = self.outbox.send(lambda *_: self.result())
        self.assertEqual(self.counts(result), {'accepted': 1})
        failed = self.outbox.db.execute(
            "SELECT 1 FROM events WHERE stage='notify' AND result='failed'").fetchall()
        self.assertTrue(failed)

    # -- single-original retention -------------------------------------------------

    def test_second_enqueue_supersedes_first_and_cleans_inbox(self):
        first_digest = self.outbox.db.execute('SELECT digest FROM jobs').fetchone()[0]
        inbox = self.root / 'inbox'
        first_dir = inbox / 'received-AAAAAAAAAA'
        first_dir.mkdir(parents=True)
        (first_dir / 'talk.txt').write_bytes(self.source.read_bytes())
        second_dir = inbox / 'received-BBBBBBBBBB'
        second_dir.mkdir(parents=True)
        second_source = self.root / 'second.txt'
        second_source.write_bytes((SAMPLE + '12:05\t別の人\t追加\n').encode())
        (second_dir / 'talk.txt').write_bytes(second_source.read_bytes())

        result = self.outbox.enqueue(second_source)
        self.outbox.remove_old_files(result['digest'], inbox=inbox, keep_inbox=second_dir)

        states = dict(self.outbox.db.execute('SELECT digest, state FROM jobs'))
        self.assertEqual(states[first_digest], 'superseded')
        self.assertEqual(states[result['digest']], 'queued')
        self.assertFalse((self.outbox.base / 'originals' / (first_digest + '.txt')).exists())
        self.assertTrue((self.outbox.base / 'originals' / (result['digest'] + '.txt')).exists())
        self.assertFalse(first_dir.exists())
        self.assertTrue(second_dir.exists())

    def test_remove_old_files_skips_unexpected_entries(self):
        originals = self.outbox.base / 'originals'
        keep_digest = self.outbox.db.execute('SELECT digest FROM jobs').fetchone()[0]
        stray_file = originals / 'not-a-digest.txt'
        stray_file.write_text('x')
        real_old = originals / (('0' * 64) + '.txt')
        real_old.write_text('y')
        link_name = originals / (('1' * 64) + '.txt')
        try:
            link_name.symlink_to(real_old)
        except (OSError, NotImplementedError):
            self.skipTest('この環境ではシンボリックリンクを作成できません')

        inbox = self.root / 'inbox'
        messy_dir = inbox / 'received-CCCCCCCCCC'
        messy_dir.mkdir(parents=True)
        (messy_dir / 'sub').mkdir()

        dry = self.outbox.remove_old_files(keep_digest, inbox=inbox, dry_run=True)
        self.assertTrue(stray_file.exists())
        self.assertTrue(link_name.is_symlink())
        self.assertTrue(messy_dir.exists())
        self.assertIn(real_old, dry)

        removed = self.outbox.remove_old_files(keep_digest, inbox=inbox)
        self.assertTrue(stray_file.exists(), '名前規則外は消さない')
        # real_old (a legitimate target) is removed, but the symlink entry
        # itself (never a target because is_symlink() excludes it) stays;
        # it is left dangling, which is expected since we never follow links.
        self.assertTrue(link_name.is_symlink(), 'シンボリックリンク自体は消さない')
        self.assertTrue(messy_dir.exists(), 'サブディレクトリ入りは消さない')
        self.assertFalse(real_old.exists())
        self.assertIn(real_old, removed)

    # -- periodic check: stall detection ---------------------------------------------

    def _mark_stalled(self, attempts=1):
        digest = self.outbox.db.execute('SELECT digest FROM jobs').fetchone()[0]
        now = self.clock()
        with self.outbox.db:
            # retry_at far in the future so check()'s own resend attempt (which would
            # otherwise hit the real network transport) finds nothing to do.
            self.outbox.db.execute(
                "UPDATE jobs SET state='retry', attempts=?, retry_at=?, received_at=? WHERE digest=?",
                (attempts, now + 10 ** 9, now, digest))
        self.outbox.record('send', 'retry', digest=digest,
                            reason='通信できません（圏外・タイムアウト等）')
        return digest

    def test_check_no_stall_notification_when_unset(self):
        self._mark_stalled()
        self.clock.advance(10000)
        self.outbox.check()
        self.assertFalse(any(call[0] == NOTIFY_STALL for call in self.notifier.calls))

    def test_check_no_stall_notification_before_threshold(self):
        self.outbox.set_stall(600)
        self._mark_stalled()
        self.clock.advance(100)
        self.outbox.check()
        self.assertFalse(any(call[0] == NOTIFY_STALL for call in self.notifier.calls))

    def test_check_stall_notification_after_threshold(self):
        self.outbox.set_stall(600)
        self._mark_stalled(attempts=3)
        self.clock.advance(700)
        self.outbox.check()
        stall_calls = [call for call in self.notifier.calls if call[0] == NOTIFY_STALL]
        self.assertEqual(len(stall_calls), 1)
        _, title, content = stall_calls[0]
        self.assertIn('詰まり', title)
        self.assertIn('分', content)
        self.assertIn('再送3回', content)
        self.assertIn('通信できません', content)

    def test_check_resends_due_retry_job_as_check(self):
        self.outbox.send(lambda *_: (0, ''))
        self.clock.advance(120)
        self.outbox.check(transport=lambda *_: self.result())
        state = self.outbox.db.execute('SELECT state FROM jobs').fetchone()[0]
        self.assertEqual(state, 'accepted')
        detected = self.outbox.db.execute(
            "SELECT 1 FROM events WHERE stage='send' AND detected_by='check'").fetchall()
        self.assertTrue(detected)

    # -- prune -------------------------------------------------------------------

    def test_prune_removes_old_events_keeps_recent(self):
        self.outbox.record('send', 'accepted', digest='old')
        old_time = self.clock() - 91 * 86400
        with self.outbox.db:
            self.outbox.db.execute(
                "UPDATE events SET at=? WHERE stage='send' AND result='accepted' AND digest='old'", (old_time,))
        self.outbox.record('send', 'accepted', digest='new')
        self.outbox.prune()
        remaining = [row[0] for row in self.outbox.db.execute(
            "SELECT digest FROM events WHERE stage='send' AND result='accepted'")]
        self.assertNotIn('old', remaining)
        self.assertIn('new', remaining)

    def test_prune_removes_old_finished_jobs_without_original(self):
        digest = 'f' * 64
        now = self.clock()
        with self.outbox.db:
            self.outbox.db.execute(
                'INSERT INTO jobs (digest,state,finished_at) VALUES (?,?,?)',
                (digest, 'accepted', now - 91 * 86400))
        self.outbox.prune()
        row = self.outbox.db.execute('SELECT 1 FROM jobs WHERE digest=?', (digest,)).fetchone()
        self.assertIsNone(row)

    # -- schema migration ----------------------------------------------------------

    def test_opens_legacy_schema_and_adds_columns(self):
        legacy_root = self.root / 'legacy'
        legacy_root.mkdir()
        (legacy_root / 'originals').mkdir()
        db = sqlite3.connect(legacy_root / 'outbox.sqlite3')
        db.execute('''CREATE TABLE jobs (
            digest TEXT PRIMARY KEY, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            retry_at REAL NOT NULL DEFAULT 0, job_id TEXT, response TEXT, error TEXT)''')
        db.execute("INSERT INTO jobs (digest, state) VALUES ('abc', 'queued')")
        db.commit()
        db.close()
        legacy = Outbox(legacy_root)
        try:
            columns = {row[1] for row in legacy.db.execute('PRAGMA table_info(jobs)')}
            self.assertTrue({'received_at', 'last_attempt_at', 'finished_at'} <= columns)
            self.assertEqual(dict(legacy.db.execute('SELECT digest, state FROM jobs')), {'abc': 'queued'})
        finally:
            legacy.db.close()

    # -- config merging ------------------------------------------------------------

    def test_set_stall_preserves_other_keys(self):
        self.outbox.set_stall(900)
        config = json.loads((self.outbox.base / 'config.json').read_text())
        self.assertEqual(config['enabled'], True)
        self.assertEqual(config['endpoint'], ENDPOINT)
        self.assertEqual(config['stall_seconds'], 900)

    def test_enable_preserves_stall_seconds(self):
        self.outbox.set_stall(300)
        self.outbox.db.close()
        argv = ['client.py', '--state-dir', str(self.outbox.base), 'enable']
        with mock.patch.object(sys, 'argv', argv):
            client_module.main()
        config = json.loads((self.outbox.base / 'config.json').read_text())
        self.assertEqual(config.get('stall_seconds'), 300)
        self.assertTrue(config.get('enabled'))
        self.assertEqual(config.get('endpoint'), ENDPOINT)
        # Reopen so tearDown's close() call still targets a live connection.
        self.outbox.db = sqlite3.connect(self.outbox.base / 'outbox.sqlite3')

    # -- check locking ---------------------------------------------------------------

    def test_check_returns_zero_when_locked(self):
        self.outbox.db.close()
        lock_path = self.outbox.base / 'lock'
        with lock_path.open('a') as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            argv = ['client.py', '--state-dir', str(self.outbox.base), 'check']
            with mock.patch.object(sys, 'argv', argv):
                code = client_module.main()
            self.assertEqual(code, 0)
        # Reopen so tearDown's close() call still targets a live connection.
        self.outbox.db = sqlite3.connect(self.outbox.base / 'outbox.sqlite3')

    def test_enqueue_send_setup_failure_is_notified_and_recorded(self):
        self.outbox.db.close()
        (self.outbox.base / 'config.json').write_text(json.dumps({'enabled': False}))
        notifier = FakeNotifier()
        argv = ['client.py', '--state-dir', str(self.outbox.base), 'enqueue', str(self.source)]
        with mock.patch.object(sys, 'argv', argv), \
                mock.patch.object(client_module, 'termux_notify', notifier):
            code = client_module.main()
        self.assertEqual(code, 1)
        self.assertEqual(notifier.calls[-1][:2], (NOTIFY_PROGRESS, 'LINE取込：失敗'))
        self.outbox.db = sqlite3.connect(self.outbox.base / 'outbox.sqlite3')
        row = self.outbox.db.execute(
            "SELECT result, reason FROM events WHERE stage='send' ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(row[0], 'failed')
        self.assertIn('Android専用API', row[1])


if __name__ == '__main__':
    unittest.main()
