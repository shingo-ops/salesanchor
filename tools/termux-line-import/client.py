#!/usr/bin/env python3
"""LINE Android export outbox. No credentials or message bodies are logged."""
import argparse
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid

from android_parser import parse_android_export

ENDPOINT = 'https://api.salesanchor.jp/api/v1/tcg/line-import/android'
MAX_BYTES = 10 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Outbox:
    def __init__(self, base):
        self.base = Path(base)
        self.base.mkdir(mode=0o700, parents=True, exist_ok=True)
        (self.base / 'originals').mkdir(mode=0o700, exist_ok=True)
        self.db = sqlite3.connect(self.base / 'outbox.sqlite3')
        self.db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            digest TEXT PRIMARY KEY, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            retry_at REAL NOT NULL DEFAULT 0, job_id TEXT, response TEXT, error TEXT)''')

    def enqueue(self, path):
        with Path(path).open('rb') as f:
            raw = f.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('ファイルは10MiB以下にしてください')
        messages = parse_android_export(raw.decode('utf-8-sig'))
        digest = hashlib.sha256(raw).hexdigest()
        target = self.base / 'originals' / (digest + '.txt')
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
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO jobs (digest,state) VALUES (?,?)',
                            (digest, 'queued'))
        return {'digest': digest, 'messages': len(messages), 'bytes': len(raw)}

    def status(self):
        return dict(self.db.execute('SELECT state, COUNT(*) FROM jobs GROUP BY state'))

    def send(self, transport=None, force=False):
        # Deployment must be confirmed explicitly; do not post to the old PC API.
        config = json.loads((self.base / 'config.json').read_text())
        if config.get('endpoint') != ENDPOINT or config.get('enabled') is not True:
            raise ValueError('Android専用APIの導入確認後に送信を有効にしてください')
        token_file = self.base / 'token.txt'
        if token_file.stat().st_mode & 0o077:
            raise ValueError('認証ファイルの権限を600にしてください')
        token = token_file.read_text().strip()
        if not token or '\n' in token or '\r' in token:
            raise ValueError('認証情報を端末内で設定してください')
        transport = transport or post
        rows = self.db.execute("SELECT digest,attempts FROM jobs WHERE state IN ('queued','retry','auth_required') AND (retry_at <= ? OR ?)",
                               (time.time(), int(force))).fetchall()
        for digest, attempts in rows:
            raw = (self.base / 'originals' / (digest + '.txt')).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('原本の整合性エラー。送信を停止しました')
            # Crash after POST leaves 'retry': identical raw file is resent; the server
            # must serialize and deduplicate by its Android-specific content key.
            with self.db:
                self.db.execute("UPDATE jobs SET state='retry', attempts=?, retry_at=? WHERE digest=?",
                                (attempts + 1, time.time() + 60, digest))
            code, response = transport(raw, token)
            state, error, job_id = 'retry', '通信結果を確認できません', None
            data = None
            try:
                data = json.loads(response)
            except (ValueError, TypeError):
                pass
            if code in (401, 403):
                state, error = 'auth_required', 'ログイン更新または権限確認が必要です'
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
            # Only expected response fields; never persist an arbitrary HTML/error body.
            safe = {key: data.get(key) for key in ('status','review_status','message_count',
                    'provider_count','unresolved_count','skipped_message_count','import_job_id')} if isinstance(data, dict) and state in ('accepted','pending_review') else None
            with self.db:
                self.db.execute('UPDATE jobs SET state=?, retry_at=?, job_id=?, response=?, error=? WHERE digest=?',
                                (state, time.time() + min(3600, 30 * 2 ** min(attempts, 7)),
                                 job_id, json.dumps(safe), error, digest))
            if code in (401, 403, 404):
                break
        return self.status()


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
    parser.add_argument('action', choices=['enqueue', 'send', 'status', 'set-token', 'enable'])
    parser.add_argument('file', nargs='?')
    args = parser.parse_args()
    outbox = Outbox(args.state_dir)
    with (outbox.base / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if args.action == 'enqueue':
                if not args.file:
                    raise ValueError('ファイルを指定してください')
                print(json.dumps(outbox.enqueue(args.file), ensure_ascii=False))
                if (outbox.base / 'config.json').exists() and (outbox.base / 'token.txt').exists():
                    print(json.dumps(outbox.send(), ensure_ascii=False))
                else:
                    print('原本を保存しました。API導入・認証設定後に送信できます。')
            elif args.action == 'send':
                print(json.dumps(outbox.send(force=True), ensure_ascii=False))
            elif args.action == 'status':
                print(json.dumps(outbox.status(), ensure_ascii=False))
            elif args.action == 'set-token':
                token = getpass.getpass('MFA認証済みFirebase IDトークン（非表示）: ').strip()
                if not token or any(c.isspace() for c in token):
                    raise ValueError('認証情報が空、または形式が不正です')
                f = outbox.base / 'token.txt'
                f.write_text(token)
                f.chmod(0o600)
                print('端末内に保存しました。期限切れ時は再設定が必要です。')
            elif args.action == 'enable':
                (outbox.base / 'config.json').write_text(json.dumps({'enabled':True,'endpoint':ENDPOINT}))
                print('Android専用APIへの送信を有効にしました。')
        except (ValueError, OSError, sqlite3.Error):
            print('処理を完了できませんでした。原本は保持されています。形式・認証・設定を確認してください。', file=sys.stderr)
            return 1
        finally:
            outbox.db.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
