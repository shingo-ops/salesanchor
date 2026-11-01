"""予備の合言葉（ADR-1055 D14）。1人10個・1回ずつ使える。

1個 = 見出し4文字 + 本体10文字（Crockford base32・本体は50ビット）。見せる形は ABCD-EFGHJ-KMNPQ。
DB には見出し（その人の中で一意）と、本体の argon2（既存の hash_password）だけを置く。生の値は保存しない・ログに出さない。
照合は見出しで1件に絞ってから argon2 を1回だけ。
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password, verify_password

CODE_COUNT = 10
HEAD_LEN = 4
BODY_LEN = 10
# Crockford base32（I・L・O・U を使わない）
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ALIASES = {"O": "0", "I": "1", "L": "1"}


def _random_chars(n: int) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


def format_code(head: str, body: str) -> str:
    return f"{head}-{body[:5]}-{body[5:]}"


def normalize(code: str | None) -> tuple[str, str] | None:
    """入力を (見出し, 本体) にする。形が合わなければ None。大文字小文字・ハイフン・空白は無視し、O/I/L は 0/1 とみなす。"""
    if not code:
        return None
    cleaned = "".join(ch for ch in code.upper() if ch not in "-_ \t\r\n")
    cleaned = "".join(_ALIASES.get(ch, ch) for ch in cleaned)
    if len(cleaned) != HEAD_LEN + BODY_LEN or any(ch not in _ALPHABET for ch in cleaned):
        return None
    return cleaned[:HEAD_LEN], cleaned[HEAD_LEN:]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def generate(db: AsyncSession, user_id: int) -> list[str]:
    """10個作る。古い未使用は無効にする（行は消さない）。生の値はここで返す1回きり。commit は呼び出し側。"""
    now = _now()
    await db.execute(
        text(
            "UPDATE public.user_recovery_codes SET revoked_at = :now "
            "WHERE user_id = :uid AND used_at IS NULL AND revoked_at IS NULL"
        ),
        {"now": now, "uid": user_id},
    )
    heads: set[str] = set()
    while len(heads) < CODE_COUNT:
        heads.add(_random_chars(HEAD_LEN))
    shown: list[str] = []
    for head in sorted(heads):
        body = _random_chars(BODY_LEN)
        code_hash = await asyncio.to_thread(hash_password, body)
        await db.execute(
            text(
                "INSERT INTO public.user_recovery_codes (user_id, code_id, code_hash, created_at) "
                "VALUES (:uid, :cid, :h, :now)"
            ),
            {"uid": user_id, "cid": head, "h": code_hash, "now": now},
        )
        shown.append(format_code(head, body))
    return shown


async def verify(db: AsyncSession, user_id: int, code: str | None, request_id: str | None = None) -> int | None:
    """合えば使用済みにして行の id を返す。合わなければ None。

    見出しで1件に絞ってから argon2 を1回だけ行う。見出しが無い・形が違うときも同じ重さの照合を1回行う
    （合う・合わないの時間の差を小さくする）。commit は呼び出し側。
    """
    parsed = normalize(code)
    row = None
    if parsed is not None:
        head, body = parsed
        row = (
            await db.execute(
                text(
                    "SELECT id, code_hash FROM public.user_recovery_codes "
                    "WHERE user_id = :uid AND code_id = :cid AND used_at IS NULL AND revoked_at IS NULL"
                ),
                {"uid": user_id, "cid": head},
            )
        ).first()
    else:
        body = ""
    ok = await asyncio.to_thread(verify_password, row.code_hash if row else None, body)
    if not ok or row is None:
        return None
    used = (
        await db.execute(
            text(
                "UPDATE public.user_recovery_codes SET used_at = :now, used_request_id = :rid "
                "WHERE id = :id AND used_at IS NULL AND revoked_at IS NULL RETURNING id"
            ),
            {"now": _now(), "rid": request_id, "id": row.id},
        )
    ).first()
    return int(used[0]) if used else None


async def remaining(db: AsyncSession, user_id: int) -> int:
    """使える（未使用・有効）合言葉の残り数。"""
    return int(
        (
            await db.execute(
                text(
                    "SELECT count(*) FROM public.user_recovery_codes "
                    "WHERE user_id = :uid AND used_at IS NULL AND revoked_at IS NULL"
                ),
                {"uid": user_id},
            )
        ).scalar_one()
    )
