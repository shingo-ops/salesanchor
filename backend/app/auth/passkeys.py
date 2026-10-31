"""パスキー（WebAuthn）の部品。ADR-1013 便5。

表 public.webauthn_credentials は生 SQL で読み書きする（self_tokens.py と同じ方針）。
口そのものは routers/auth.py に置き、ここには challenge の保管と options の組み立てだけを置く。
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.auth import self_tokens
from app.cache import get_redis

CHALLENGE_TTL_SECONDS = 300
MAX_PASSKEYS_PER_USER = 10
RP_NAME = "Sales Anchor"
LABEL_MAX = 64


def user_handle(user_id: int) -> bytes:
    """端末に持たせる利用者の識別子。メールは入れない（design.md:79）。"""
    return user_id.to_bytes(8, "big")


def _key(kind: str, owner: str, challenge_id: str) -> str:
    return f"passkey_chal:{kind}:{owner}:{challenge_id}"


async def store_challenge(kind: str, owner: str, challenge: bytes) -> str:
    """challenge を Redis に 300 秒だけ置き、challenge_id を返す。kind は reg か login。"""
    redis = get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="unavailable")
    challenge_id = secrets.token_urlsafe(24)
    await redis.set(_key(kind, owner, challenge_id), bytes_to_base64url(challenge), ex=CHALLENGE_TTL_SECONDS)
    return challenge_id


async def take_challenge(kind: str, owner: str, challenge_id: str) -> bytes | None:
    """challenge を 1 回で消しながら取り出す（design.md:80）。無ければ None。"""
    redis = get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="unavailable")
    value = await redis.getdel(_key(kind, owner, challenge_id))
    if value is None:
        return None
    return base64url_to_bytes(value)


def registration_options(user_id: int, email: str, existing: list[bytes]):
    # user_name に email を使うのは、端末の候補一覧で本人がどのアカウントかを見分けるため（U2）。
    # user handle には入れない。
    return generate_registration_options(
        rp_id=self_tokens.rp_id(),
        rp_name=RP_NAME,
        user_name=email,
        user_id=user_handle(user_id),
        user_display_name=email,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=c) for c in existing],
    )


def authentication_options():
    # allow_credentials は空にして、端末に候補を出させる（design.md:80）。
    return generate_authentication_options(
        rp_id=self_tokens.rp_id(),
        user_verification=UserVerificationRequirement.REQUIRED,
    )


def sign_count_rejected(stored: int, received: int) -> bool:
    """使用回数が戻った・止まったときに真（design.md:80。ライブラリと同じ式）。"""
    return (received > 0 or stored > 0) and received <= stored
