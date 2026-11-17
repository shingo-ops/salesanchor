"""ADR-1080: 秘書の返事の読み上げ（Google Cloud Text-to-Speech の Chirp 3: HD）。design.md §4-4。

月の字数を台帳で数える → 鍵と札 → Google へ 1 文ずつ頼む → 台帳に 1 行。文そのものは台帳にもログにも書かない（ADR-1056）。
Google を待つ間は DB の取引を持たない（呼び出し側が先に閉じる）。失敗は TtsError（status_code と code）で上げる。
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_budget import UsageCounts, record_usage_isolated
from app.services.secretary_voice import MONTHLY_CHAR_CAP, google_voice_name

logger = logging.getLogger(__name__)

TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
TTS_TIMEOUT_SECONDS = 10.0
TTS_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
KEY_FILE_ENV = "GOOGLE_TTS_SA_KEY_FILE"
_JST = ZoneInfo("Asia/Tokyo")

_credentials_cache: tuple[str, object] | None = None
_refresh_lock = asyncio.Lock()


class TtsError(Exception):
    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


def _month_start_jst() -> datetime:
    return datetime.now(_JST).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def read_month_total(db: AsyncSession) -> int:
    """日本時間の今月 1 日 0 時からの読み上げの字数の合計。読めなければ 503（Google を呼ばない）。"""
    try:
        result = await db.execute(
            text(
                "SELECT COALESCE(SUM(billed_characters), 0) FROM public.llm_usage_events "
                "WHERE purpose = 'secretary_tts' AND occurred_at >= :start"
            ),
            {"start": _month_start_jst()},
        )
        return int(result.scalar_one())
    except Exception as exc:  # noqa: BLE001
        logger.error("[secretary_tts] 月の字数を読めませんでした: kind=%s", type(exc).__name__)
        raise TtsError(503, "tts_usage_unreadable") from None


def check_monthly_cap(month_total: int, chars: int) -> None:
    if month_total + chars > MONTHLY_CHAR_CAP:
        raise TtsError(429, "tts_monthly_cap_reached")


def _credentials() -> object:
    """鍵ファイルから資格を作って持ち回す。未設定・読めない・鍵として読めないなら 503。"""
    global _credentials_cache
    path = os.getenv(KEY_FILE_ENV, "")
    if not path:
        raise TtsError(503, "tts_not_configured")
    if _credentials_cache is not None and _credentials_cache[0] == path:
        return _credentials_cache[1]
    try:
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(path, scopes=TTS_SCOPES)
    except Exception:  # noqa: BLE001
        raise TtsError(503, "tts_not_configured") from None
    _credentials_cache = (path, creds)
    return creds


async def _bearer_token() -> str:
    """札を返す。valid が偽のときだけ、同期の通信を別スレッドで取り直す（取り直しは 1 つずつ）。"""
    creds = _credentials()
    if not getattr(creds, "valid", False):
        async with _refresh_lock:
            if not getattr(creds, "valid", False):
                import google.auth.transport.requests as ga_requests

                try:
                    await asyncio.to_thread(creds.refresh, ga_requests.Request())  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    raise TtsError(502, "tts_upstream_failed") from None
    token = getattr(creds, "token", None)
    if not token:
        raise TtsError(502, "tts_upstream_failed")
    return str(token)


async def _call_google(token: str, payload: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=TTS_TIMEOUT_SECONDS) as client:
        return await client.post(TTS_URL, json=payload, headers={"Authorization": f"Bearer {token}"})


async def _record(voice: str, tenant_id: int, outcome: str, error_code: str | None, chars: int) -> None:
    await record_usage_isolated(
        purpose="secretary_tts",
        model=google_voice_name(voice),
        sdk="google-tts-rest",
        counts=UsageCounts(),
        outcome=outcome,
        error_code=error_code,
        tenant_id=tenant_id,
        billed_characters=chars,
    )


def _log(user_id: int, tenant_id: int, started: float, chars: int, result: str) -> None:
    logger.info(
        "assistant_speech user_id=%s tenant_id=%s chars=%s seconds=%.2f result=%s",
        user_id, tenant_id, chars, time.monotonic() - started, result,
    )  # fmt: skip


async def synthesize(*, text_in: str, voice: str, user_id: int, tenant_id: int) -> bytes:
    """文を声で MP3 にして返す。月の上限の判定は呼び出し側（check_monthly_cap）が先に行う。"""
    started = time.monotonic()
    chars = len(text_in)
    try:
        token = await _bearer_token()
    except TtsError as exc:
        if exc.code == "tts_upstream_failed":
            await _record(voice, tenant_id, "failed", "auth_failed", 0)
            _log(user_id, tenant_id, started, chars, "auth_failed")
        else:
            _log(user_id, tenant_id, started, chars, exc.code)
        raise

    payload = {
        "input": {"text": text_in},
        "voice": {"languageCode": "ja-JP", "name": google_voice_name(voice)},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    error_code: str | None = None
    audio = b""
    try:
        resp = await _call_google(token, payload)
    except httpx.TimeoutException:
        error_code = "timeout"
    except httpx.HTTPError:
        error_code = "http_error"
    else:
        if resp.status_code == 429:
            error_code = "rate_limited"
        elif resp.status_code in (401, 403):
            error_code = "auth_failed"
        elif resp.status_code >= 300:
            error_code = "http_error"
        else:
            try:
                audio = base64.b64decode(resp.json()["audioContent"], validate=True)
                if not audio:
                    raise ValueError("empty")
            except (KeyError, TypeError, ValueError, binascii.Error):
                error_code = "unreadable"

    if error_code is not None:
        await _record(voice, tenant_id, "failed", error_code, 0)
        _log(user_id, tenant_id, started, chars, error_code)
        raise TtsError(502, "tts_upstream_failed")

    await _record(voice, tenant_id, "ok", None, chars)
    _log(user_id, tenant_id, started, chars, "ok")
    return audio
