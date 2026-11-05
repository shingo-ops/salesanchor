"""gemini_route（Gemini への道の自動切り替え）の試験。ADR-1062。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from google.genai import errors as genai_errors

from app.services import gemini_route

LOCATION_MSG = "User location is not supported for the API use."
LOCATION_REASON = f"400 FAILED_PRECONDITION: {LOCATION_MSG}"


def _api_error(code: int, status: str, message: str):
    return genai_errors.APIError(code, {"error": {"code": code, "status": status, "message": message}})


def _location_error():
    return _api_error(400, "FAILED_PRECONDITION", LOCATION_MSG)


@pytest.fixture(autouse=True)
def _reset_route_state(monkeypatch):
    monkeypatch.delenv("GEMINI_PROXY_URL", raising=False)
    gemini_route.reset_state()
    yield
    gemini_route.reset_state()


def _failing_client(exc):
    client = MagicMock()
    client.models.generate_content.side_effect = exc
    client.aio.models.generate_content = AsyncMock(side_effect=exc)
    return client


def _ok_client(result="OK"):
    client = MagicMock()
    client.models.generate_content.return_value = result
    client.aio.models.generate_content = AsyncMock(return_value=result)
    return client


def _call(client):
    return gemini_route.generate_content_routed(client, model="m", contents="c", config="cfg")


# T1
def test_t1_direct_first_location_refusal_switches_to_relay(monkeypatch):
    second = _ok_client("RELAY_OK")
    with patch.object(gemini_route, "build_client", return_value=second) as build, \
            patch.object(gemini_route, "_count_switch") as count:
        result = _call(_failing_client(_location_error()))
    assert result == "RELAY_OK"
    build.assert_called_once_with(gemini_route.ROUTE_RELAY)
    count.assert_called_once_with("direct", "relay")
    assert gemini_route.first_route() == gemini_route.ROUTE_RELAY


# T2
@pytest.mark.parametrize(
    "exc",
    [httpx.ConnectError("x"), httpx.ProxyError("x"), httpx.ConnectTimeout("x")],
)
def test_t2_relay_first_unreachable_switches_to_direct(monkeypatch, exc):
    monkeypatch.setenv("GEMINI_PROXY_URL", "http://relay.example:18888")
    assert gemini_route.first_route() == gemini_route.ROUTE_RELAY
    with patch.object(gemini_route, "build_client", return_value=_ok_client("DIRECT_OK")) as build, \
            patch.object(gemini_route, "_count_switch"):
        result = _call(_failing_client(exc))
    assert result == "DIRECT_OK"
    build.assert_called_once_with(gemini_route.ROUTE_DIRECT)


# T3
@pytest.mark.asyncio
async def test_t3_async_location_refusal_switches_to_relay(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    first = _failing_client(_location_error())
    second = _ok_client("RELAY_OK")
    with patch.object(gemini_route, "build_client", side_effect=[first, second]) as build, \
            patch.object(gemini_route, "_count_switch") as count:
        result = await gemini_route.agenerate_content_routed(model="m", contents="c", config="cfg")
    assert result == "RELAY_OK"
    assert [c.args[0] for c in build.call_args_list] == [gemini_route.ROUTE_DIRECT, gemini_route.ROUTE_RELAY]
    count.assert_called_once_with("direct", "relay")
    assert gemini_route.first_route() == gemini_route.ROUTE_RELAY


# T4
@pytest.mark.parametrize(
    "exc",
    [
        _api_error(400, "INVALID_ARGUMENT", "API key not valid"),
        _api_error(429, "RESOURCE_EXHAUSTED", "quota"),
        _api_error(503, "UNAVAILABLE", "overloaded"),
        httpx.ReadTimeout("slow"),
        ValueError("bad"),
    ],
)
def test_t4_other_errors_do_not_switch(exc):
    with patch.object(gemini_route, "build_client") as build:
        with pytest.raises(type(exc)) as ei:
            _call(_failing_client(exc))
    assert ei.value is exc
    build.assert_not_called()


# T5
def test_t5_failure_reason_unwraps_chain_and_redacts():
    api_err = _location_error()
    try:
        try:
            raise api_err
        except Exception as inner:
            raise RuntimeError("Gemini v8 API 呼び出し失敗: (HTTP 400)") from inner
    except RuntimeError as wrapped:
        assert gemini_route.failure_reason(wrapped) == LOCATION_REASON

    leaked = RuntimeError("fail url=https://x/?key=abc&y=1 and AIzaSyA1234567890abcdefgh")
    reason = gemini_route.failure_reason(leaked)
    assert "key=abc" not in reason
    assert "AIzaSyA1234567890abcdefgh" not in reason
    assert "key=(省略)" in reason
    assert "(APIキー省略)" in reason

    assert len(gemini_route.failure_reason(RuntimeError("x" * 400))) == gemini_route.REASON_MAX_CHARS == 300


# T6 / T6b: 実物の google.genai.Client に届かない中継を渡す
def _real_client_unreachable():
    from google import genai
    from google.genai import types

    proxy = "http://127.0.0.1:9"
    return genai.Client(
        api_key="dummy",
        http_options=types.HttpOptions(client_args={"proxy": proxy}, async_client_args={"proxy": proxy}),
    )


def _type_chain(exc):
    return " <- ".join(f"{type(e).__module__}.{type(e).__name__}" for e in gemini_route._exception_chain(exc))


def test_t6_real_sync_client_unreachable_relay_is_route_unreachable(capsys):
    client = _real_client_unreachable()
    with pytest.raises(Exception) as ei:
        client.models.generate_content(model="gemini-3.5-flash-lite", contents="hi")
    print("T6 chain:", _type_chain(ei.value))
    assert gemini_route.is_route_unreachable(ei.value), _type_chain(ei.value)


@pytest.mark.asyncio
async def test_t6b_real_async_client_unreachable_relay_is_route_unreachable():
    client = _real_client_unreachable()
    print("T6b aiohttp importable:", gemini_route.aiohttp is not None)
    with pytest.raises(Exception) as ei:
        await client.aio.models.generate_content(model="gemini-3.5-flash-lite", contents="hi")
    print("T6b chain:", _type_chain(ei.value), "| msg:", str(ei.value)[:200])
    assert gemini_route.is_route_unreachable(ei.value), _type_chain(ei.value)


# T7
def test_t7_second_failure_propagates_with_context():
    first_exc = _location_error()
    second_exc = _location_error()
    with patch.object(gemini_route, "build_client", return_value=_failing_client(second_exc)) as build, \
            patch.object(gemini_route, "_count_switch") as count:
        with pytest.raises(genai_errors.APIError) as ei:
            _call(_failing_client(first_exc))
    assert ei.value is second_exc
    assert ei.value.__context__ is first_exc
    build.assert_called_once()
    count.assert_not_called()
    assert gemini_route.first_route() == gemini_route.ROUTE_DIRECT


# T8
def test_t8_sticky_route_expires(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(gemini_route.time, "monotonic", lambda: now[0])
    gemini_route.remember(gemini_route.ROUTE_RELAY)
    assert gemini_route.first_route() == gemini_route.ROUTE_RELAY
    now[0] += gemini_route.STICKY_SECONDS
    assert gemini_route.first_route() == gemini_route.preferred_route() == gemini_route.ROUTE_DIRECT


# T10
def test_t10_no_direct_generate_content_in_target_files():
    services = Path(__file__).resolve().parent.parent / "app" / "services"
    for name in ("gemini_extraction_svc.py", "gemini_raw_copy_v8.py", "message_translator.py"):
        body = (services / name).read_text(encoding="utf-8")
        assert "client.models.generate_content(" not in body, name
        assert "generate_content_async" not in body, name
