"""Device-local Firebase email/password login. Never log credentials or responses."""
import getpass
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

SIGN_IN = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword'
MFA = 'https://identitytoolkit.googleapis.com/v2/accounts/mfaSignIn:finalize'
REFRESH = 'https://securetoken.googleapis.com/v1/token'
CHECK = 'https://api.salesanchor.jp/api/v1/tcg/line-import/pending'


class AuthError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def private_write(path, data):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.auth-')
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
        raise AuthError('認証ファイルの権限を600にしてください。')
    return json.loads(path.read_text())


def request(endpoint, key, payload):
    if endpoint not in (SIGN_IN, MFA, REFRESH):
        raise AuthError('認証先が不正です。')
    encoded = (urllib.parse.urlencode(payload).encode() if endpoint == REFRESH
               else json.dumps(payload).encode())
    content_type = ('application/x-www-form-urlencoded' if endpoint == REFRESH
                    else 'application/json')
    req = urllib.request.Request(endpoint + '?key=' + urllib.parse.quote(key, safe=''),
                                 data=encoded, headers={'Content-Type': content_type})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            data = json.loads(response.read(1024 * 1024))
        if not isinstance(data, dict):
            raise AuthError('認証応答を確認できません。')
        return data
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise AuthError('認証回数の制限です。時間をおいて再試行してください。') from None
        raise AuthError('認証できません。入力・認証コード・プロジェクト設定を確認して再ログインしてください。') from None
    except (OSError, ValueError):
        raise AuthError('認証通信に失敗しました。保存済み原本は保持されています。') from None


def check_access(token):
    req = urllib.request.Request(CHECK, headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            if response.status != 200:
                raise AuthError('Sales Anchorの権限確認に失敗しました。')
            # Do not read, print or persist the list of import jobs.
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise AuthError('Sales Anchorが認証を拒否しました。MFAと管理者権限を確認してください。') from None
        raise AuthError('Sales Anchorの接続を確認できません。後で再ログインしてください。') from None
    except OSError:
        raise AuthError('Sales Anchorに接続できません。後で再ログインしてください。') from None


def secret_prompt(message):
    # getpass normally falls back to echoing input if terminal control fails.
    # Refuse that fallback instead of exposing a password or MFA code.
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            return getpass.getpass(message)
        except getpass.GetPassWarning:
            raise AuthError('非表示入力を開始できません。Termux本体の新しいセッションで実行してください。') from None


class Session:
    def __init__(self, base, transport=None, verify=None):
        self.base = Path(base)
        self.transport = transport or request
        self.verify = verify or check_access

    def key(self):
        config = json.loads((self.base / 'firebase.json').read_text())
        key = config.get('api_key', '')
        if not isinstance(key, str) or not re.fullmatch(r'AIza[\w-]{35}', key):
            raise AuthError('端末のFirebase公開設定を確認してください。')
        return key

    def save(self, data, refresh=False):
        token = data.get('id_token' if refresh else 'idToken')
        renewal = data.get('refresh_token' if refresh else 'refreshToken')
        if any(not isinstance(s, str) or not s or any(c.isspace() for c in s)
               for s in (token, renewal)):
            raise AuthError('認証応答が不正です。再ログインしてください。')
        # MFA finalize omits expiresIn. An immediate refresh supplies server expiry.
        ttl = int(data.get('expires_in' if refresh else 'expiresIn', 0))
        if ttl < 0 or ttl > 86400:
            raise AuthError('認証期限を確認できません。')
        private_write(self.base / 'session.json',
                      {'id_token': token, 'refresh_token': renewal,
                       'expires_at': time.time() + ttl})
        return token

    def login(self, email, password, code_prompt=None, factor_prompt=None):
        key = self.key()
        result = self.transport(SIGN_IN, key, {'email': email, 'password': password,
                                              'returnSecureToken': True})
        if result.get('mfaPendingCredential'):
            factors = [f for f in result.get('mfaInfo', [])
                       if isinstance(f, dict) and 'totpInfo' in f and f.get('mfaEnrollmentId')]
            if not factors:
                raise AuthError('この端末用コマンドは認証アプリのMFAに対応しています。SMS等の場合は追加対応が必要です。')
            index = 0 if len(factors) == 1 else int(factor_prompt(len(factors))) - 1
            if not 0 <= index < len(factors):
                raise AuthError('認証アプリの番号が不正です。')
            code = code_prompt()
            if not re.fullmatch(r'[0-9]{6}', code):
                raise AuthError('認証アプリの6桁コードを入力してください。')
            result = self.transport(MFA, key, {
                'mfaPendingCredential': result['mfaPendingCredential'],
                'mfaEnrollmentId': factors[index]['mfaEnrollmentId'],
                'totpVerificationInfo': {'verificationCode': code}})
        token = result.get('idToken')
        if not isinstance(token, str) or not token or any(c.isspace() for c in token):
            raise AuthError('ログインが完了していません。ブラウザーでの追加認証が必要な可能性があります。')
        self.verify(token)
        self.save(result)

    def token(self):
        path = self.base / 'session.json'
        if not path.exists():
            legacy = self.base / 'token.txt'
            if legacy.is_symlink() or legacy.stat().st_mode & 0o077:
                raise AuthError('認証ファイルの権限を600にしてください。')
            token = legacy.read_text().strip()
            if not token or any(c.isspace() for c in token):
                raise AuthError('端末内でログインしてください。')
            return token
        data = private_read(path)
        if float(data['expires_at']) > time.time() + 120:
            token = data['id_token']
            if not isinstance(token, str) or not token or any(c.isspace() for c in token):
                raise AuthError('保存済み認証情報が不正です。再ログインしてください。')
            return token
        result = self.transport(REFRESH, self.key(), {
            'grant_type': 'refresh_token', 'refresh_token': data['refresh_token']})
        return self.save(result, refresh=True)

    def interactive_login(self):
        if not sys.stdin.isatty():
            raise AuthError('Termux本体のターミナルで line-import login を実行してください。')
        self.key()  # Fail before prompting if device configuration is missing.
        email = input('Sales Anchorのメールアドレス: ').strip()
        password = secret_prompt('パスワード（非表示・保存しません）: ')
        if not email or not password:
            raise AuthError('メールアドレスとパスワードを入力してください。')
        self.login(email, password,
                   code_prompt=lambda: secret_prompt('認証アプリの6桁コード（非表示）: ').strip(),
                   factor_prompt=lambda count: input(f'登録済み認証アプリの番号（1〜{count}）: '))
        print('端末のログインと取り込み権限を確認しました。トークはまだ送信していません。')
