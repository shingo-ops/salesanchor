import logging
import secrets
import string

from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)

PASSWORD_SYMBOLS = "!@#$%^&*-_=+"
_PASSWORD_ALPHABET = string.ascii_letters + string.digits + PASSWORD_SYMBOLS


def set_tenant_claim(firebase_uid: str, tenant_id: int) -> None:
    """FirebaseユーザーにカスタムクレームとしてテナントIDを設定する。"""
    firebase_auth.set_custom_user_claims(firebase_uid, {"tenant_id": tenant_id})


def generate_password(length: int = 16) -> str:
    """英大小・数字・記号を各1文字以上含む長さ length のランダムパスワードを生成する。

    暗号学的に安全な secrets モジュールを使用。文字種が4カテゴリ揃わないとリトライする。
    """
    if length < 4:
        raise ValueError("length must be >= 4 to satisfy character class requirements")
    while True:
        pw = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in PASSWORD_SYMBOLS for c in pw)
        ):
            return pw
