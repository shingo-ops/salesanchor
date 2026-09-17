#!/usr/bin/env python3
"""LINE Android export outbox. No credentials or message bodies are logged."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
import urllib.error
import urllib.request
import uuid

from android_parser import parse_android_export
from device_session import AuthError, Session

ENDPOINT = 'https://api.salesanchor.jp/api/v1/tcg/line-devices/import'
MAX_BYTES = 10 * 1024 * 1024

TERMUX_NOTIFICATION = '/data/data/com.termux/files/usr/bin/termux-notification'
TERMUX_JOB_SCHEDULER = '/data/data/com.termux/files/usr/bin/termux-job-scheduler'
NOTIFY_PROGRESS = 4201
NOTIFY_STALL = 4202
JOB_ID = 4201

ORIGINAL_RE = re.compile(r'^[0-9a-f]{64}\.txt$')
RECEIVED_RE = re.compile(r'^received-[A-Za-z0-9]{10}$')
JST = timezone(timedelta(hours=9))
NINETY_DAYS = 90 * 86400

# Actions whose failures are recorded under a specific stage by main()'s generic
# handler; anything not listed falls back to 'unknown'. 'enqueue' is intentionally
# absent: Outbox.enqueue() already records its own parse/store failure before
# re-raising, so recording again here would duplicate the event.
_EXCEPTION_STAGE = {'send': 'send', 'cleanup': 'cleanup', 'check': 'check'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def termux_notify(nid, title, content):
    try:
        result = subprocess.run(
            [TERMUX_NOTIFICATION, '--id', str(nid), '-t', title, '-c', content, '--alert-once'],
            timeout=10, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


class Outbox:
    def __init__(self, base, clock=time.time, notifier=None):
        self.base = Path(base)
        self.base.mkdir(mode=0o700, parents=True, exist_ok=True)
        (self.base / 'originals').mkdir(mode=0o700, exist_ok=True)
        self.clock = clock
        self.notifier = notifier or termux_notify
        self.db = sqlite3.connect(self.base / 'outbox.sqlite3')
        self.db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            digest TEXT PRIMARY KEY, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            retry_at REAL NOT NULL DEFAULT 0, job_id TEXT, response TEXT, error TEXT)''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, at REAL NOT NULL, digest TEXT, stage TEXT NOT NULL,
            result TEXT NOT NULL, reason TEXT, http_code INTEGER, elapsed_seconds REAL,
            detected_by TEXT)''')
        existing = {row[1] for row in self.db.execute('PRAGMA table_info(jobs)')}
        for column in ('received_at', 'last_attempt_at', 'finished_at'):
            if column not in existing:
                self.db.execute(f'ALTER TABLE jobs ADD COLUMN {column} REAL')

    # -- history -----------------------------------------------------------

    def record(self, stage, result, digest=None, reason=None, http_code=None,
               elapsed=None, detected_by=None):
        with self.db:
            self.db.execute(
                'INSERT INTO events (at,digest,stage,result,reason,http_code,elapsed_seconds,detected_by) '
                'VALUES (?,?,?,?,?,?,?,?)',
                (self.clock(), digest, stage, result, reason, http_code, elapsed, detected_by))

    def _notify(self, nid, title, content, digest=None):
        try:
            ok = self.notifier(nid, title, content)
        except Exception:
            ok = False
        if not ok:
            self.record('notify', 'failed', digest=digest)

    def history(self, limit=20):
        rows = self.db.execute(
            'SELECT at, stage, result, reason, http_code, elapsed_seconds, detected_by '
            'FROM events ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        lines = []
        for at, stage, result, reason, http_code, elapsed, detected_by in rows:
            when = datetime.fromtimestamp(at, JST).strftime('%Y-%m-%d %H:%M:%S')
            lines.append('{} {} {} {} {} {} {}'.format(
                when, stage, result, reason or '',
                http_code if http_code is not None else '',
                f'{elapsed:.1f}s' if elapsed is not None else '', detected_by or ''))
        return lines

    def prune(self):
        cutoff = self.clock() - NINETY_DAYS
        with self.db:
            self.db.execute('DELETE FROM events WHERE at < ?', (cutoff,))
            rows = self.db.execute('SELECT digest, received_at, finished_at FROM jobs').fetchall()
            for digest, received_at, finished_at in rows:
                basis = finished_at if finished_at is not None else received_at
                if basis is None or basis >= cutoff:
                    continue
                if (self.base / 'originals' / (digest + '.txt')).exists():
                    continue
                self.db.execute('DELETE FROM jobs WHERE digest=?', (digest,))

    # -- config --------------------------------------------------------------

    def _load_config(self):
        path = self.base / 'config.json'
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def set_stall(self, seconds):
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise ValueError('詰まり判定時間は正の整数（秒）で指定してください')
        config = self._load_config()
        config['stall_seconds'] = seconds
        (self.base / 'config.json').write_text(json.dumps(config))

    # -- intake ----------------------------------------------------------------

    def enqueue(self, path, detected_by='share'):
        self.record('received', 'ok', detected_by=detected_by)
        try:
            with Path(path).open('rb') as f:
                raw = f.read(MAX_BYTES + 1)
        except OSError:
            reason = 'ファイルを読み込めません'
            self.record('parse', 'failed', reason=reason, detected_by=detected_by)
            self._notify(NOTIFY_PROGRESS, 'LINE取込：失敗', f'{reason}（原本は保持）')
            raise
        try:
            if len(raw) > MAX_BYTES:
                raise ValueError('ファイルは10MiB以下にしてください')
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                raise ValueError('文字コードを確認してください（UTF-8を想定）') from None
            try:
                messages = parse_android_export(text)
            except ValueError:
                raise ValueError('LINEのトーク履歴の形式を確認してください') from None
        except ValueError as error:
            reason = str(error)
            self.record('parse', 'failed', reason=reason, detected_by=detected_by)
            self._notify(NOTIFY_PROGRESS, 'LINE取込：失敗', f'{reason}（原本は保持）')
            raise
        digest = hashlib.sha256(raw).hexdigest()
        target = self.base / 'originals' / (digest + '.txt')
        try:
            if target.exists():
                if target.read_bytes() != raw:
                    raise ValueError('保存済み原本の整合性エラー')
            else:
                temporary = target.with_name('.' + uuid.uuid4().hex)
                try:
                    with temporary.open('xb') as f:
                        f.write(raw)
                        f.flush()
                        os.fsync(f.fileno())
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
        except (OSError, ValueError) as error:
            reason = str(error) if isinstance(error, ValueError) else '原本の保存に失敗しました'
            self.record('store', 'failed', digest=digest, reason=reason, detected_by=detected_by)
            self._notify(NOTIFY_PROGRESS, 'LINE取込：失敗', f'{reason}（原本は保持）')
            raise
        now = self.clock()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO jobs (digest,state) VALUES (?,?)', (digest, 'queued'))
            self.db.execute('UPDATE jobs SET received_at=? WHERE digest=?', (now, digest))
        self.record('store', 'ok', digest=digest, detected_by=detected_by)
        self.supersede_and_cleanup(digest)
        return {'digest': digest, 'messages': len(messages), 'bytes': len(raw)}

    def supersede_and_cleanup(self, digest):
        now = self.clock()
        rows = self.db.execute(
            "SELECT digest FROM jobs WHERE digest<>? AND state IN ('queued','retry','auth_required')",
            (digest,)).fetchall()
        if rows:
            with self.db:
                self.db.execute(
                    "UPDATE jobs SET state='superseded', finished_at=? "
                    "WHERE digest<>? AND state IN ('queued','retry','auth_required')",
                    (now, digest))
            for (old_digest,) in rows:
                self.record('cleanup', 'superseded', digest=old_digest)
        self.remove_old_files(keep_digest=digest)

    def remove_old_files(self, keep_digest, inbox=None, keep_inbox=None, dry_run=False):
        targets = []
        keep_name = keep_digest + '.txt'
        originals = self.base / 'originals'
        if originals.is_dir():
            for entry in sorted(originals.iterdir()):
                if entry.name == keep_name:
                    continue
                if not ORIGINAL_RE.fullmatch(entry.name):
                    continue
                if entry.is_symlink() or not entry.is_file():
                    continue
                targets.append(entry)
        if inbox is not None:
            inbox = Path(inbox)
            keep_resolved = keep_inbox.resolve() if keep_inbox is not None else None
            if inbox.is_dir():
                for entry in sorted(inbox.iterdir()):
                    if not RECEIVED_RE.fullmatch(entry.name):
                        continue
                    if entry.is_symlink() or not entry.is_dir():
                        continue
                    if keep_resolved is not None and entry.resolve() == keep_resolved:
                        continue
                    targets.append(entry)
        if dry_run:
            return targets
        removed = []
        for entry in targets:
            try:
                if entry.is_dir():
                    children = list(entry.iterdir())
                    if any(child.is_symlink() or not child.is_file() for child in children):
                        self.record('cleanup', 'skipped', reason=f'{entry.name}に想定外の中身')
                        continue
                    for child in children:
                        child.unlink()
                    entry.rmdir()
                else:
                    entry.unlink()
            except OSError:
                self.record('cleanup', 'skipped', reason=f'{entry.name}を削除できません')
                continue
            removed.append(entry)
        if removed:
            self.record('cleanup', 'deleted', reason=f'{len(removed)}件')
        return removed

    # -- status ----------------------------------------------------------------

    def status(self):
        counts = dict(self.db.execute('SELECT state, COUNT(*) FROM jobs GROUP BY state'))
        row = self.db.execute(
            'SELECT state, received_at FROM jobs WHERE received_at IS NOT NULL '
            'ORDER BY received_at DESC LIMIT 1').fetchone()
        if row is None:
            latest = None
        else:
            state, received_at = row
            latest = {
                'state': state,
                'received_at': datetime.fromtimestamp(received_at, JST).strftime('%Y-%m-%d %H:%M:%S'),
                'elapsed_minutes': int((self.clock() - received_at) // 60),
            }
        stall_seconds = self._load_config().get('stall_seconds')
        if isinstance(stall_seconds, bool) or not isinstance(stall_seconds, int) or stall_seconds <= 0:
            stall_seconds = '未設定（計測後に設定）'
        counts['latest'] = latest
        counts['stall_seconds'] = stall_seconds
        return counts

    # -- sending ----------------------------------------------------------------

    def send(self, transport=None, force=False, detected_by='share'):
        # Deployment must be confirmed explicitly; do not post to the old PC API.
        config = self._load_config()
        if config.get('endpoint') != ENDPOINT or config.get('enabled') is not True:
            raise ValueError('Android専用APIの導入確認後に送信を有効にしてください')
        token = Session(self.base).token()
        transport = transport or post
        rows = self.db.execute(
            "SELECT digest,attempts FROM jobs WHERE state IN ('queued','retry','auth_required') "
            "AND (retry_at <= ? OR ?)", (self.clock(), int(force))).fetchall()
        for digest, attempts in rows:
            raw = (self.base / 'originals' / (digest + '.txt')).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('原本の整合性エラー。送信を停止しました')
            start = self.clock()
            # Crash after POST leaves 'retry': identical raw file is resent; the server
            # must serialize and deduplicate by its Android-specific content key.
            with self.db:
                self.db.execute(
                    "UPDATE jobs SET state='retry', attempts=?, retry_at=?, last_attempt_at=? WHERE digest=?",
                    (attempts + 1, start + 60, start, digest))
            self.record('send', 'started', digest=digest, detected_by=detected_by)
            code, response = transport(raw, token)
            elapsed = self.clock() - start
            state, error, job_id = 'retry', '通信結果を確認できません', None
            data = None
            try:
                data = json.loads(response)
            except (ValueError, TypeError):
                pass
            if code in (401, 403):
                state, error = 'auth_required', '端末の再認可または権限確認が必要です'
            elif code == 404:
                state, error = 'retry', 'Android専用APIが未導入です'
            elif code in (400, 413, 415, 422):
                state, error = 'rejected', 'ファイル形式またはAPI仕様の確認が必要です'
            elif code == 200 and isinstance(data, dict):
                if (data.get('status') in ('imported', 'already_imported')
                        and data.get('review_status') in ('ok', 'pending_review')
                        and isinstance(data.get('import_job_id'), str)
                        and data['import_job_id']):
                    state = 'pending_review' if data['review_status'] == 'pending_review' else 'accepted'
                    job_id, error = data['import_job_id'], None
            event_reason = '通信できません（圏外・タイムアウト等）' if code == 0 else error
            # Only expected response fields; never persist an arbitrary HTML/error body.
            safe = {key: data.get(key) for key in ('status', 'review_status', 'message_count',
                    'provider_count', 'unresolved_count', 'skipped_message_count', 'import_job_id')
                    } if isinstance(data, dict) and state in ('accepted', 'pending_review') else None
            now = self.clock()
            finished_at = now if state in ('accepted', 'pending_review', 'rejected') else None
            with self.db:
                self.db.execute(
                    'UPDATE jobs SET state=?, retry_at=?, job_id=?, response=?, error=?, finished_at=? '
                    'WHERE digest=?',
                    (state, now + min(3600, 30 * 2 ** min(attempts, 7)), job_id, json.dumps(safe), error,
                     finished_at, digest))
            self.record('send', state, digest=digest, reason=event_reason, http_code=code,
                        elapsed=elapsed, detected_by=detected_by)
            self._send_result_notification(state, digest, safe, error)
            if code in (401, 403, 404):
                break
        return self.status()

    def _send_result_notification(self, state, digest, safe, error):
        if state == 'accepted':
            count = safe.get('message_count') if safe else None
            content = f'投稿{count}件' if count is not None else '投稿完了'
            self._notify(NOTIFY_PROGRESS, 'LINE取込：取り込み完了', content, digest=digest)
        elif state == 'pending_review':
            count = safe.get('unresolved_count') if safe else None
            content = (f'取引先確認待ち{count}件。PC画面で確認してください' if count is not None
                       else '取引先確認待ち。PC画面で確認してください')
            self._notify(NOTIFY_PROGRESS, 'LINE取込：取り込み完了（確認待ち）', content, digest=digest)
        elif state == 'rejected':
            self._notify(NOTIFY_PROGRESS, 'LINE取込：失敗', f'{error}（原本は保持。再送しません）', digest=digest)
        elif state == 'auth_required':
            self._notify(NOTIFY_PROGRESS, 'LINE取込：失敗', f'{error}（原本は保持。再認可が必要です）', digest=digest)
        else:
            self._notify(NOTIFY_PROGRESS, 'LINE取込：失敗',
                        f'{error}（原本は保持。次の点検で自動再送します）', digest=digest)

    # -- periodic check ----------------------------------------------------------

    def check(self, transport=None):
        self.prune()
        if (self.base / 'config.json').exists() and (self.base / 'device.json').exists():
            try:
                self.send(transport=transport, force=False, detected_by='check')
            except (ValueError, AuthError, OSError, sqlite3.Error, KeyError, TypeError, EOFError) as error:
                reason = str(error)
                self.record('check', 'failed', reason=reason, detected_by='check')
                self._notify(NOTIFY_PROGRESS, 'LINE取込：失敗', f'{reason}（原本は保持）')
        self._check_stall()

    def _check_stall(self):
        stall_seconds = self._load_config().get('stall_seconds')
        if isinstance(stall_seconds, bool) or not isinstance(stall_seconds, int) or stall_seconds <= 0:
            return
        now = self.clock()
        rows = self.db.execute(
            "SELECT digest, received_at, attempts FROM jobs WHERE state IN ('queued','retry','auth_required') "
            "AND received_at IS NOT NULL AND ? - received_at >= ?", (now, stall_seconds)).fetchall()
        for digest, received_at, attempts in rows:
            last_event = self.db.execute(
                'SELECT stage, result FROM events WHERE digest=? ORDER BY id DESC LIMIT 1',
                (digest,)).fetchone()
            if last_event is None:
                stage_label = '不明'
            elif last_event[0] == 'send' and last_event[1] == 'started':
                stage_label = '送信中に中断'
            else:
                stage_label = last_event[0]
            reason_row = self.db.execute(
                'SELECT reason FROM events WHERE digest=? AND reason IS NOT NULL ORDER BY id DESC LIMIT 1',
                (digest,)).fetchone()
            reason = reason_row[0] if reason_row else '不明'
            minutes = int((now - received_at) // 60)
            received_label = datetime.fromtimestamp(received_at, JST).strftime('%H:%M')
            content = (f'{received_label}から{minutes}分未完了／段階:{stage_label}／理由:{reason}／'
                       f'再送{attempts}回／点検で検知')
            self._notify(NOTIFY_STALL, 'LINE取込：詰まり', content, digest=digest)
            self.record('check', 'stalled', digest=digest, reason=reason,
                        elapsed=now - received_at, detected_by='check')


def post(raw, token):
    boundary = 'line-' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="window_hours"\r\n\r\n0\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="android-talk.txt"\r\n'
            'Content-Type: text/plain; charset=utf-8\r\n\r\n').encode() + raw + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(ENDPOINT, data=body,
              headers={'Authorization': 'Bearer ' + token,
                       'Content-Type': 'multipart/form-data; boundary=' + boundary}, method='POST')
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=60) as response:
            return response.status, response.read(131072).decode('utf-8', errors='replace')
    except urllib.error.HTTPError as error:
        return error.code, ''
    except (OSError, urllib.error.URLError, TimeoutError):
        return 0, ''


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', default=str(Path.home() / '.local/state/line-android-import'))
    parser.add_argument('--inbox', default=None)
    parser.add_argument('--keep-inbox', default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('action', choices=['enqueue', 'send', 'status', 'enable', 'connect', 'login',
                                            'check', 'history', 'cleanup', 'set-stall', 'schedule'])
    parser.add_argument('file', nargs='?')
    args = parser.parse_args()
    outbox = Outbox(args.state_dir)
    inbox_path = Path(args.inbox) if args.inbox else Path(args.state_dir).parent / 'inbox'
    with (outbox.base / 'lock').open('a') as lock:
        if args.action == 'check':
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                outbox.db.close()
                return 0
        else:
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if args.action == 'enqueue':
                if not args.file:
                    raise ValueError('ファイルを指定してください')
                result = outbox.enqueue(args.file)
                keep_inbox = Path(args.keep_inbox) if args.keep_inbox else None
                outbox.remove_old_files(result['digest'], inbox=inbox_path, keep_inbox=keep_inbox)
                print(json.dumps(result, ensure_ascii=False))
                if (outbox.base / 'config.json').exists() and (outbox.base / 'device.json').exists():
                    try:
                        print(json.dumps(outbox.send(), ensure_ascii=False))
                    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, EOFError) as error:
                        # Setup failures before any POST must still reach the user and the history.
                        reason = str(error) if isinstance(error, ValueError) else type(error).__name__
                        outbox.record('send', 'failed', reason=reason, detected_by='share')
                        outbox._notify(NOTIFY_PROGRESS, 'LINE取込：失敗',
                                       f'{reason}（原本は保持。次の点検で自動再送します）')
                        raise
                else:
                    print('原本を保存しました。API導入・認証設定後に送信できます。')
            elif args.action == 'send':
                print(json.dumps(outbox.send(force=True, detected_by='manual'), ensure_ascii=False))
            elif args.action == 'status':
                print(json.dumps(outbox.status(), ensure_ascii=False))
            elif args.action in ('connect', 'login'):
                Session(outbox.base).connect()
            elif args.action == 'enable':
                config = outbox._load_config()
                config['enabled'] = True
                config['endpoint'] = ENDPOINT
                (outbox.base / 'config.json').write_text(json.dumps(config))
                print('Android専用APIへの送信を有効にしました。')
            elif args.action == 'check':
                outbox.check()
            elif args.action == 'history':
                limit = int(args.file) if args.file else 20
                for line in outbox.history(limit):
                    print(line)
            elif args.action == 'cleanup':
                row = outbox.db.execute(
                    'SELECT digest FROM jobs ORDER BY received_at IS NULL, received_at DESC, '
                    'rowid DESC LIMIT 1').fetchone()
                if row is None:
                    print('対象がありません。')
                else:
                    removed = outbox.remove_old_files(row[0], inbox=inbox_path, dry_run=args.dry_run)
                    for entry in removed:
                        print(str(entry))
                    verb = '削除対象です（--dry-runのため未削除）' if args.dry_run else '削除しました'
                    print(f'{len(removed)}件が{verb}。')
            elif args.action == 'set-stall':
                if not args.file:
                    raise ValueError('秒数を指定してください')
                outbox.set_stall(int(args.file))
                print('詰まり判定時間を設定しました。')
            elif args.action == 'schedule':
                result = subprocess.run(
                    [TERMUX_JOB_SCHEDULER, '--job-id', str(JOB_ID), '--period-ms', '900000',
                     '--persisted', 'true', '--script', str(Path.home() / 'bin/line-import-check')],
                    timeout=20, capture_output=True, text=True)
                print(result.stdout.strip() or f'登録結果コード: {result.returncode}')
        except AuthError as error:
            if args.action != 'enqueue':
                outbox.record(_EXCEPTION_STAGE.get(args.action, 'unknown'), 'failed', reason=str(error))
            print(str(error), file=sys.stderr)
            return 1
        except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, EOFError) as error:
            if args.action != 'enqueue':
                outbox.record(_EXCEPTION_STAGE.get(args.action, 'unknown'), 'failed',
                              reason=type(error).__name__)
            print('処理を完了できませんでした。原本は保持されています。形式・認証・設定を確認してください。',
                  file=sys.stderr)
            return 1
        finally:
            outbox.db.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
