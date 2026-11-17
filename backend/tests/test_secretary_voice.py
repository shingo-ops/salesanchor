"""ADR-1080 便1: 秘書の声の保存と読み上げの口の試験（DB なし・Google は偽物）。V6・V7・V8 と口の単体。

試験の DB（SQLite）には users.secretary_voice の列が無いので、read_voice・save_voice・月の合計は偽物に差し替える。
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app.auth.dependencies import get_current_user, require_super_admin
from app.routers import assistant
from app.services import secretary_tts
from app.services.secretary_voice import (
    SECRETARY_VOICES,
    VoiceNotSaved,
    google_voice_name,
    resolve_voice,
)

REPO = Path(__file__).resolve().parents[2]
VOICE_URL = "/api/v1/assistant/voice"
SPEECH_URL = "/api/v1/assistant/speech"
AUDIO = b"ID3fake-mp3-bytes"


# --- V6: 翻訳キー ----------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["ja", "en"])
def test_v6_voice_names_exist_in_locales(lang):
    data = json.loads((REPO / f"frontend/src/locales/{lang}.json").read_text(encoding="utf-8"))
    names = data["secretary"]["voice"]["name"]
    for voice in SECRETARY_VOICES:
        assert isinstance(names.get(voice), str) and names[voice].strip(), (lang, voice)


# --- resolve_voice ---------------------------------------------------------------------------


@pytest.mark.parametrize("stored", [None, "", "Nope", "charon"])
def test_resolve_voice_falls_back_to_charon(stored):
    assert resolve_voice(stored) == "Charon"


@pytest.mark.parametrize("voice", SECRETARY_VOICES)
def test_resolve_voice_keeps_listed(voice):
    assert resolve_voice(voice) == voice


def test_google_voice_name():
    assert google_voice_name("Charon") == "ja-JP-Chirp3-HD-Charon"


# --- 口の準備 --------------------------------------------------------------------------------


@pytest.fixture
def allowed(client, monkeypatch):
    from app.main import app

    async def _ok_feature():
        return None

    async def _super_admin():
        return await app.dependency_overrides[get_current_user]()

    app.dependency_overrides[assistant._feature_secretary_chat] = _ok_feature
    app.dependency_overrides[require_super_admin] = _super_admin
    monkeypatch.setattr(assistant, "read_voice", AsyncMock(return_value="Aoede"))
    monkeypatch.setattr(assistant, "save_voice", AsyncMock(return_value=None))
    monkeypatch.setattr(secretary_tts, "read_month_total", AsyncMock(return_value=0))
    monkeypatch.setattr(secretary_tts, "record_usage_isolated", AsyncMock())
    monkeypatch.setattr(secretary_tts, "_bearer_token", AsyncMock(return_value="tok"))
    yield client


def _google_ok():
    body = {"audioContent": base64.b64encode(AUDIO).decode()}
    return AsyncMock(return_value=httpx.Response(200, json=body))


# --- V8: 守り --------------------------------------------------------------------------------

ENDPOINTS = [
    ("get", VOICE_URL, None),
    ("put", VOICE_URL, {"voice": "Aoede"}),
    ("post", SPEECH_URL, {"text": "こんにちは"}),
]


async def _send(client, method, url, body):
    if body is None:
        return await getattr(client, method)(url)
    return await getattr(client, method)(url, json=body)


@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", ENDPOINTS)
async def test_v8_no_feature_is_403(client, method, url, body):
    from app.main import app

    async def _no_feature():
        raise HTTPException(status_code=403, detail="機能が無効です: secretary_chat")

    app.dependency_overrides[assistant._feature_secretary_chat] = _no_feature
    assert (await _send(client, method, url, body)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", ENDPOINTS)
async def test_v8_not_super_admin_is_403(client, method, url, body):
    from app.main import app

    async def _ok_feature():
        return None

    app.dependency_overrides[assistant._feature_secretary_chat] = _ok_feature
    assert (await _send(client, method, url, body)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("held", [{"customers.view"}, {"invoices.create"}])
@pytest.mark.parametrize("method,url,body", ENDPOINTS)
async def test_v8_missing_permission_is_403(allowed, monkeypatch, held, method, url, body):
    async def _only(db, tenant_id, user_id):
        return held

    monkeypatch.setattr("app.auth.dependencies.load_user_permissions", _only)
    assert (await _send(allowed, method, url, body)).status_code == 403


# --- GET / PUT -------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_voice(allowed):
    resp = await allowed.get(VOICE_URL)
    assert resp.status_code == 200
    assert resp.json() == {"voices": list(SECRETARY_VOICES), "default": "Charon", "selected": "Aoede"}


@pytest.mark.asyncio
async def test_put_voice_saves_and_returns_written_value(allowed):
    resp = await allowed.put(VOICE_URL, json={"voice": "Erinome"})
    assert resp.status_code == 200
    assert resp.json()["selected"] == "Erinome"
    assert assistant.save_voice.await_args.kwargs["voice"] == "Erinome"


@pytest.mark.asyncio
async def test_put_voice_unlisted_is_422(allowed):
    resp = await allowed.put(VOICE_URL, json={"voice": "Nope"})
    assert resp.status_code == 422
    assert assistant.save_voice.await_count == 0


@pytest.mark.asyncio
async def test_put_voice_not_saved_is_500(allowed, monkeypatch):
    monkeypatch.setattr(assistant, "save_voice", AsyncMock(side_effect=VoiceNotSaved("rowcount=0")))
    resp = await allowed.put(VOICE_URL, json={"voice": "Aoede"})
    assert resp.status_code == 500
    assert resp.json()["detail"] == {"code": "voice_not_saved"}


# --- POST /speech ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_speech_success(allowed, monkeypatch):
    google = _google_ok()
    monkeypatch.setattr(secretary_tts, "_call_google", google)
    text = "こんにちは。" * 3  # 18 字
    resp = await allowed.post(SPEECH_URL, json={"text": text})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.headers["cache-control"] == "no-store"
    assert resp.content == AUDIO
    payload = google.await_args.args[1]
    assert payload["voice"]["name"] == "ja-JP-Chirp3-HD-Aoede"  # 声は DB の値（画面は送らない）
    kwargs = secretary_tts.record_usage_isolated.await_args.kwargs
    assert kwargs["purpose"] == "secretary_tts" and kwargs["sdk"] == "google-tts-rest"
    assert kwargs["outcome"] == "ok" and kwargs["billed_characters"] == len(text)
    assert kwargs["model"] == "ja-JP-Chirp3-HD-Aoede"
    assert secretary_tts.record_usage_isolated.await_count == 1


@pytest.mark.asyncio
async def test_speech_closes_transaction_before_google(allowed, monkeypatch, db_session):
    order: list[str] = []
    real_rollback = db_session.rollback

    async def _rollback():
        order.append("rollback")
        return await real_rollback()

    async def _google(token, payload):
        order.append("google")
        return httpx.Response(200, json={"audioContent": base64.b64encode(AUDIO).decode()})

    monkeypatch.setattr(db_session, "rollback", _rollback)
    monkeypatch.setattr(secretary_tts, "_call_google", _google)
    resp = await allowed.post(SPEECH_URL, json={"text": "はい"})
    assert resp.status_code == 200
    assert order == ["rollback", "google"]


@pytest.mark.asyncio
async def test_v7_cap_reached_is_429_and_no_google(allowed, monkeypatch):
    google = _google_ok()
    monkeypatch.setattr(secretary_tts, "_call_google", google)
    monkeypatch.setattr(secretary_tts, "read_month_total", AsyncMock(return_value=899_990))
    resp = await allowed.post(SPEECH_URL, json={"text": "あ" * 20})
    assert resp.status_code == 429
    assert resp.json()["detail"] == {"code": "tts_monthly_cap_reached"}
    assert google.await_count == 0
    assert secretary_tts.record_usage_isolated.await_count == 0


@pytest.mark.asyncio
async def test_v7_cap_boundary_exactly_at_cap_passes(allowed, monkeypatch):
    monkeypatch.setattr(secretary_tts, "_call_google", _google_ok())
    monkeypatch.setattr(secretary_tts, "read_month_total", AsyncMock(return_value=899_980))
    resp = await allowed.post(SPEECH_URL, json={"text": "あ" * 20})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_v7_total_unreadable_is_503_and_no_google(allowed, monkeypatch, db_session):
    google = _google_ok()
    monkeypatch.setattr(secretary_tts, "_call_google", google)
    # 合計を読む本物の関数を、失敗する db で流す
    monkeypatch.undo()  # 偽物を外し、本物の関数を使う（守りの上書きは残る）
    monkeypatch.setattr(assistant, "read_voice", AsyncMock(return_value="Charon"))
    monkeypatch.setattr(secretary_tts, "_call_google", google)
    monkeypatch.setattr(db_session, "execute", AsyncMock(side_effect=RuntimeError("boom")))
    resp = await allowed.post(SPEECH_URL, json={"text": "はい"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "tts_usage_unreadable"}
    assert google.await_count == 0


@pytest.mark.asyncio
async def test_not_configured_is_503_without_google_or_ledger(allowed, monkeypatch):
    monkeypatch.undo()  # 偽物を外し、本物の関数を使う（守りの上書きは残る）
    google = _google_ok()
    ledger = AsyncMock()
    monkeypatch.setattr(assistant, "read_voice", AsyncMock(return_value="Charon"))
    monkeypatch.setattr(secretary_tts, "read_month_total", AsyncMock(return_value=0))
    monkeypatch.setattr(secretary_tts, "_call_google", google)
    monkeypatch.setattr(secretary_tts, "record_usage_isolated", ledger)
    monkeypatch.delenv("GOOGLE_TTS_SA_KEY_FILE", raising=False)
    resp = await allowed.post(SPEECH_URL, json={"text": "はい"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "tts_not_configured"}
    assert google.await_count == 0
    assert ledger.await_count == 0


@pytest.mark.asyncio
async def test_unreadable_key_file_is_not_configured(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not a key")
    monkeypatch.setattr(secretary_tts, "_credentials_cache", None)
    monkeypatch.setenv("GOOGLE_TTS_SA_KEY_FILE", str(bad))
    with pytest.raises(secretary_tts.TtsError) as ei:
        await secretary_tts._bearer_token()
    assert (ei.value.status_code, ei.value.code) == (503, "tts_not_configured")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "google,code",
    [
        (AsyncMock(return_value=httpx.Response(500, text="x")), "http_error"),
        (AsyncMock(return_value=httpx.Response(429, text="x")), "rate_limited"),
        (AsyncMock(return_value=httpx.Response(403, text="x")), "auth_failed"),
        (AsyncMock(side_effect=httpx.ReadTimeout("t")), "timeout"),
        (AsyncMock(side_effect=httpx.ConnectError("c")), "http_error"),
        (AsyncMock(return_value=httpx.Response(200, json={"audioContent": "!!"})), "unreadable"),
        (AsyncMock(return_value=httpx.Response(200, json={})), "unreadable"),
    ],
)
async def test_google_failure_is_502_and_ledger_failed(allowed, monkeypatch, google, code):
    monkeypatch.setattr(secretary_tts, "_call_google", google)
    resp = await allowed.post(SPEECH_URL, json={"text": "はい"})
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"code": "tts_upstream_failed"}
    kwargs = secretary_tts.record_usage_isolated.await_args.kwargs
    assert kwargs["outcome"] == "failed" and kwargs["error_code"] == code and kwargs["billed_characters"] == 0


@pytest.mark.asyncio
async def test_token_failure_is_502_and_ledger_auth_failed(allowed, monkeypatch):
    monkeypatch.setattr(
        secretary_tts, "_bearer_token", AsyncMock(side_effect=secretary_tts.TtsError(502, "tts_upstream_failed"))
    )
    resp = await allowed.post(SPEECH_URL, json={"text": "はい"})
    assert resp.status_code == 502
    assert secretary_tts.record_usage_isolated.await_args.kwargs["error_code"] == "auth_failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "   \n", "あ" * 301])
async def test_speech_input_is_422(allowed, text):
    assert (await allowed.post(SPEECH_URL, json={"text": text})).status_code == 422


@pytest.mark.asyncio
async def test_speech_does_not_log_text(allowed, monkeypatch, caplog):
    monkeypatch.setattr(secretary_tts, "_call_google", _google_ok())
    secret = "ひみつの文ZZZ"
    with caplog.at_level("DEBUG"):
        await allowed.post(SPEECH_URL, json={"text": secret})
    assert secret not in caplog.text


# --- 待ちで止めない ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_refresh_does_not_block_loop(monkeypatch):
    class _SlowCreds:
        valid = False
        token = "tok"

        def refresh(self, request):
            time.sleep(0.3)
            self.valid = True

    monkeypatch.setattr(secretary_tts, "_credentials", lambda: _SlowCreds())
    monkeypatch.setattr(secretary_tts, "_call_google", _google_ok())
    monkeypatch.setattr(secretary_tts, "record_usage_isolated", AsyncMock())

    stop = asyncio.Event()

    async def _ticker() -> int:
        n = 0
        while not stop.is_set():
            await asyncio.sleep(0.01)
            n += 1
        return n

    async def _run():
        try:
            return await secretary_tts.synthesize(text_in="はい", voice="Charon", user_id=1, tenant_id=1)
        finally:
            stop.set()

    ticks, audio = await asyncio.gather(_ticker(), _run())
    assert audio == AUDIO
    assert ticks >= 10

