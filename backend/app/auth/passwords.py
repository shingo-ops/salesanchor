"""パスワードのハッシュ化と照合（Argon2id）。ADR-1013 便2。

パラメータは OWASP 推奨値（m=19456, t=2, p=1）。
照合は CPU を使うため、async 側からは asyncio.to_thread で呼ぶこと。
"""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

# 存在しない人・停止中の人でも同じ時間をかけるためのダミー（import 時に 1 回だけ作る）
_DUMMY_HASH = _HASHER.hash(secrets.token_urlsafe(16))


def hash_password(plain: str) -> str:
    return _HASHER.hash(plain)


def verify_password(stored_hash: str | None, plain: str) -> bool:
    """一致したときだけ True。hash が None や壊れていても例外は出さず False。"""
    if stored_hash is None:
        try:
            _HASHER.verify(_DUMMY_HASH, plain)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            pass
        return False
    try:
        return bool(_HASHER.verify(stored_hash, plain))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _HASHER.check_needs_rehash(stored_hash)
