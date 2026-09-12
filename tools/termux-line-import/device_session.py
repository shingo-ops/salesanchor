"""Device-local, import-only API key. No passwords or Firebase tokens are used."""
import hashlib
import json
import os
import re
import secrets
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'https://api.salesanchor.jp/api/v1/tcg/line-devices'
SCOPE = 'line:import:android'
KEY = re.compile(r'^sali1_[A-Za-z0-9_-]{43}$')
CODE = re.compile(r'^[A-Z2-9]{4}-[A-Z2-9]{4}$')


class AuthError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def private_write(path, data):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.device-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def private_read(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise AuthError('端末認証ファイルの権限を600にしてください。')
    return json.loads(path.read_text())


def request(path, payload=None, token=None):
    if path not in ('/start', '/status'):
        raise AuthError('端末認可の接続先が不正です。')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(BASE + path, headers=headers,
                                 data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            return response.status, json.loads(response.read(16384))
    except urllib.error.HTTPError as error:
        error.close()
        return error.code, {}
    except (OSError, ValueError):
        raise AuthError('接続できません。原本と端末認証は保持しています。後で再試行してください。') from None


class Session:
    def __init__(self, base, transport=None, pause=None, clock=None):
        self.base = Path(base)
        self.transport = transport or request
        self.pause = pause or time.sleep
        self.clock = clock or time.monotonic

    def token(self):
        path = self.base / 'device.json'
        if not path.exists():
            raise AuthError('先に line-import connect で端末を認可してください。')
        token = private_read(path).get('token', '')
        if not isinstance(token, str) or not KEY.fullmatch(token):
            raise AuthError('端末認証が不正です。line-import connect で再認可してください。')
        return token

    def connect(self):
        active = self.base / 'device.json'
        if active.exists():
            code, data = self.transport('/status', token=self.token())
            if code == 200 and data.get('status') == 'approved':
                print('この端末は認可済みです。')
                return
            if code != 401:
                raise AuthError('既存の端末認可を確認できません。後で再試行してください。')
        token = 'sali1_' + secrets.token_urlsafe(32)
        # Save only locally before sending its hash to the registration API.
        candidate = self.base / 'device-pending.json'
        private_write(candidate, {'token': token})
        code, data = self.transport('/start', {'token_hash': hashlib.sha256(token.encode()).hexdigest(), 'name': 'Termux'})
        if code == 429:
            raise AuthError('端末登録の回数制限です。1時間後に再試行してください。')
        if code == 404:
            raise AuthError('端末認可APIが未導入です。反映後に再試行してください。')
        if code != 200 or not isinstance(data, dict) or not CODE.fullmatch(data.get('user_code', '')) or data.get('scope') != SCOPE:
            raise AuthError('端末登録を開始できませんでした。後で再試行してください。')
        print('端末登録を開始しました。管理者側の許可処理を待っています。', flush=True)
        print('端末コード: ' + data['user_code'], flush=True)
        deadline = self.clock() + 600
        while self.clock() < deadline:
            self.pause(5)
            code, reply = self.transport('/status', token=token)
            if code == 200 and reply.get('status') == 'approved':
                private_write(active, {'token': token})
                candidate.unlink(missing_ok=True)
                print('端末を認可しました。トークはまだ送信していません。', flush=True)
                return
            if code == 200 and reply.get('status') == 'pending':
                continue
            if code == 429:
                self.pause(10)
                continue
            raise AuthError('端末認可を確認できません。原本は保持しています。connectを再実行してください。')
        raise AuthError('端末認可の待機時間を過ぎました。connectを再実行してください。')
