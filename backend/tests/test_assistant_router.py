"""ADR-1056 段2: POST /api/v1/assistant/messages の試験（SQLite・容器は httpx をモック）。

容器の 200 の答えは secretary-agent/fixtures/ の見本をそのまま返させる（形の食い違いを試験で見つける）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.auth.dependencies import get_current_user, require_super_admin
from app.routers import assistant

FIXTURES = Path(__file__).resolve().parents[2] / "secretary-agent" / "fixtures"
_RealAsyncClient = httpx.AsyncClient
URL = "/api/v1/assistant/messages"
SECRET_TEXT = "ひみつの依頼文ZZZ請求書をお願い"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def allowed(client):
    """会社の入口・super admin の守りを通す（権限は conftest が全付与）。"""

    from app.main import app

    async def _ok_feature():
        return None

    async def _super_admin():
        return await app.dependency_overrides[get_current_user]()

    app.dependency_overrides[assistant._feature_secretary_chat] = _ok_feature
    app.dependency_overrides[require_super_admin] = _super_admin
    yield client


def _mock_agent(monkeypatch, handler):
    def factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(assistant.httpx, "AsyncClient", factory)


def _respond(status: int, body=None):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body if body is not None else {})

    return handler


# ---- 守り -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_feature_is_403(client):
    from app.main import app

    async def _no_feature():
        raise HTTPException(status_code=403, detail="機能が無効です: secretary_chat")

    app.dependency_overrides[assistant._feature_secretary_chat] = _no_feature
    resp = await client.post(URL, json={"text": "a"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_not_super_admin_is_403(client):
    from app.main import app

    async def _ok_feature():
        return None

    app.dependency_overrides[assistant._feature_secretary_chat] = _ok_feature
    # require_super_admin は上書きしない: モックユーザーは is_super_admin が偽
    resp = await client.post(URL, json={"text": "a"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_missing_permission_is_403(allowed, monkeypatch):
    async def _only_view(db, tenant_id, user_id):
        return {"customers.view"}

    monkeypatch.setattr("app.auth.dependencies.load_user_permissions", _only_view)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_text_length_is_validated(allowed):
    assert (await allowed.post(URL, json={"text": ""})).status_code == 422
    assert (await allowed.post(URL, json={"text": "あ" * 1001})).status_code == 422


# ---- 成功 -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invoice_fixture(allowed, monkeypatch):
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        sent["url"] = str(request.url)
        return httpx.Response(200, json=_fixture("envelope-invoice.json"))

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["kind"] == "invoice"
    d = data["draft"]
    assert d["company_name"] == "サンプル商事"
    assert d["currency"] == "JPY"
    assert d["items"][0] == {"product_name": "ポケモンカード BOX", "quantity": 3, "unit_price": 5000.0}
    assert d["items"][1]["unit_price"] is None
    assert d["due_date"] == "2026-11-30"
    assert data["candidates"] == {"companies": [], "contacts": []}
    assert sent["url"].endswith("/intent")
    assert sent["text"] == "請求書"
    assert sent["now"].endswith("+09:00")


@pytest.mark.asyncio
async def test_event_fixture_end_defaults_to_start_plus_one_hour(allowed, monkeypatch):
    _mock_agent(monkeypatch, _respond(200, _fixture("envelope-event.json")))
    resp = await allowed.post(URL, json={"text": "予定"})
    assert resp.status_code == 200, resp.text
    d = resp.json()["draft"]
    assert d["start"] == "2026-11-02T15:00:00+09:00"
    assert d["end"] == "2026-11-02T16:00:00+09:00"
    assert d["calendar_type"] == "personal"
    assert d["is_all_day"] is False


@pytest.mark.asyncio
async def test_unknown_fixture(allowed, monkeypatch):
    _mock_agent(monkeypatch, _respond(200, _fixture("envelope-unknown.json")))
    resp = await allowed.post(URL, json={"text": "?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "unknown"
    assert data["draft"] == {"reply": _fixture("envelope-unknown.json")["intent"]["reply"]}
    assert data["candidates"] == {"companies": [], "contacts": []}


# ---- 失敗の返し方 -----------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_status,agent_body,expected_status,expected_code",
    [
        (503, {"code": "not_ready"}, 503, "not_ready"),
        (429, {"code": "busy"}, 429, "busy"),
        (504, {"code": "timeout"}, 504, "timeout"),
        (502, {"code": "cli_failed"}, 502, "unreadable"),
        (502, {"code": "unreadable"}, 502, "unreadable"),
    ],
)
async def test_agent_failures(allowed, monkeypatch, agent_status, agent_body, expected_status, expected_code):
    _mock_agent(monkeypatch, _respond(agent_status, agent_body))
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == expected_status
    assert resp.json()["detail"] == {"code": expected_code}


@pytest.mark.asyncio
async def test_connection_refused_is_503(allowed, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "not_ready"}


@pytest.mark.asyncio
async def test_httpx_timeout_is_504(allowed, monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("slow")

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 504
    assert resp.json()["detail"] == {"code": "timeout"}


def _with(base: str, mutate) -> dict:
    env = _fixture(base)
    mutate(env)
    return env


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "label,envelope",
    [
        ("extra field in envelope", _with("envelope-unknown.json", lambda e: e.update(extra=1))),
        ("extra field in intent", _with("envelope-unknown.json", lambda e: e["intent"].update(extra=1))),
        ("invoice kind but invoice null", _with("envelope-invoice.json", lambda e: e["intent"].update(invoice=None))),
        (
            "invoice kind with event value",
            _with("envelope-invoice.json", lambda e: e["intent"].update(event=_fixture("envelope-event.json")["intent"]["event"])),
        ),
        ("quantity 0", _with("envelope-invoice.json", lambda e: e["intent"]["invoice"]["items"][0].update(quantity=0))),
        ("event start unreadable", _with("envelope-event.json", lambda e: e["intent"]["event"].update(start="あした"))),
        ("event end unreadable", _with("envelope-event.json", lambda e: e["intent"]["event"].update(end="のちほど"))),
        (
            "event end before start",
            _with("envelope-event.json", lambda e: e["intent"]["event"].update(end="2026-11-02T14:00:00+09:00")),
        ),
        ("not an envelope", {"kind": "invoice"}),
    ],
)
async def test_unreadable_answers_are_502(allowed, monkeypatch, label, envelope):
    _mock_agent(monkeypatch, _respond(200, envelope))
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 502, label
    assert resp.json()["detail"] == {"code": "unreadable"}


# ---- ログ ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cli_failed_is_logged_as_cli_failed(allowed, monkeypatch, caplog):
    _mock_agent(monkeypatch, _respond(502, {"code": "cli_failed"}))
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"code": "unreadable"}
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=cli_failed" in lines[0]


@pytest.mark.asyncio
async def test_log_has_one_line_without_text_or_answer(allowed, monkeypatch, caplog):
    env = _fixture("envelope-invoice.json")
    _mock_agent(monkeypatch, _respond(200, env))
    with caplog.at_level(logging.INFO):
        resp = await allowed.post(URL, json={"text": SECRET_TEXT})
    assert resp.status_code == 200
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=ok" in lines[0]
    assert "total_cost_usd=0.0123" in lines[0]
    assert "tenant_id=999" in lines[0] and "user_id=999" in lines[0]
    everything = "\n".join(r.getMessage() for r in caplog.records)
    assert SECRET_TEXT not in everything
    assert "サンプル商事" not in everything


# ---- K5: 何も作らない --------------------------------------------------------


async def _count(db, table: str):
    exists = (
        await db.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"), {"n": table})
    ).first()
    if not exists:
        return None  # SQLite の試験用スキーマに無い表（口はそもそも触らない）
    return (await db.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar_one()


@pytest.mark.asyncio
async def test_nothing_is_created(allowed, db_session, monkeypatch):
    before = {t: await _count(db_session, t) for t in ("invoices", "invoice_items", "calendar_events")}
    for name in ("envelope-invoice.json", "envelope-event.json", "envelope-unknown.json"):
        _mock_agent(monkeypatch, _respond(200, _fixture(name)))
        assert (await allowed.post(URL, json={"text": "a"})).status_code == 200
    after = {t: await _count(db_session, t) for t in ("invoices", "invoice_items", "calendar_events")}
    assert before == after
    assert before["invoices"] is not None
