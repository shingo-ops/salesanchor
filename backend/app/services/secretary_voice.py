"""ADR-1080: 秘書の声の一覧の正本と、本人の声の読み書き（design.md §4-1・§4-3-1）。

声の一覧と既定はこのファイル 1 か所だけに書く（DB には値の決まりを付けない）。
読み書きは生の SQL で public.users.secretary_voice を扱う（言語 locale と同じ。models.py は触らない）。
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import clear_tenant_context, set_tenant_context

logger = logging.getLogger(__name__)

SECRETARY_VOICES: tuple[str, ...] = ("Aoede", "Charon", "Erinome", "Zubenelgenubi")
DEFAULT_SECRETARY_VOICE = "Charon"
TTS_LANGUAGE_CODE = "ja-JP"
MONTHLY_CHAR_CAP = 900_000  # 無料枠 100 万字の 9 割で止める
MAX_CHARS_PER_REQUEST = 300


def resolve_voice(stored: str | None) -> str:
    """DB の値が一覧に無い・空なら既定を返す。"""
    return stored if stored in SECRETARY_VOICES else DEFAULT_SECRETARY_VOICE


def google_voice_name(voice: str) -> str:
    return f"{TTS_LANGUAGE_CODE}-Chirp3-HD-{voice}"


class VoiceNotSaved(Exception):
    """声の UPDATE が 1 行に当たらなかった（行ごとの守りで 0 行になった等）。"""


async def read_voice(db: AsyncSession, user_id: int) -> str:
    """本人の声を読む（users の読みは全行可）。未選択・一覧に無い値は既定。"""
    result = await db.execute(
        text("SELECT secretary_voice FROM public.users WHERE id = :uid"),
        {"uid": user_id},
    )
    return resolve_voice(result.scalar_one_or_none())


async def save_voice(db: AsyncSession, *, user_id: int, tenant_id: int, voice: str) -> None:
    """本人の声だけを書く。会社の文脈 → UPDATE → 文脈を戻す → commit の順（行ごとの守りのため）。

    書いた行が 1 でなければ commit せず巻き戻して VoiceNotSaved を上げる。commit の後に db は使わない。
    """
    await set_tenant_context(db, tenant_id)
    result = await db.execute(
        text("UPDATE public.users SET secretary_voice = :v WHERE id = :uid"),
        {"v": voice, "uid": user_id},
    )
    await clear_tenant_context(db)
    if result.rowcount != 1:
        await db.rollback()
        raise VoiceNotSaved(f"rowcount={result.rowcount}")
    await db.commit()
