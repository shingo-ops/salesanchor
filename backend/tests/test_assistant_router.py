"""ADR-1056 段2: POST /api/v1/assistant/messages の試験（SQLite・容器は httpx をモック）。

容器の 200 の答えは secretary-agent/fixtures/ の見本をそのまま返させる（形の食い違いを試験で見つける）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.auth.dependencies import get_current_user, require_super_admin
from app.routers import assistant
from app.services.ai_assignment import AiAssignment
from app.services.llm_budget import UsageCounts

FIXTURES = Path(__file__).resolve().parents[2] / "secretary-agent" / "fixtures"
_RealAsyncClient = httpx.AsyncClient
URL = "/api/v1/assistant/messages"
SECRET_TEXT = "ひみつの依頼文ZZZ請求書をお願い"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def allowed(client, monkeypatch):
    """会社の入口・super admin の守りを通す（権限は conftest が全付与）。

    試験の DB（SQLite）に担当表は無いので、担当の読み取りは claude・sonnet を返す偽物に、
    使用の記録は AsyncMock に差し替える（試験からは assistant.record_usage_isolated で見る）。
    """

    async def _assignment(db, job_key):
        assert job_key == "secretary_intent"
        return AiAssignment("claude", "sonnet")

    monkeypatch.setattr(assistant, "get_ai_assignment", _assignment)
    monkeypatch.setattr(assistant, "record_usage_isolated", AsyncMock())
    # ADR-1077 便2b: 決まり帳は SQLite に無いので、承認済みの決まりの読み取りは「0 件」を返す偽物にする
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(return_value=[]))

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
        (502, {"code": "cli_failed"}, 502, "agent_failed"),
        (502, {"code": "tool_used"}, 502, "agent_failed"),
        (502, {"code": "auth_failed"}, 503, "auth_failed"),
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
    assert resp.json()["detail"] == {"code": "agent_failed"}
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=cli_failed" in lines[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_code,expected_status,expected_detail,expected_log",
    [
        ("auth_failed", 503, "auth_failed", "code=auth_failed"),
        ("unreadable", 502, "unreadable", "code=unreadable"),
    ],
)
async def test_agent_502_codes_are_logged(
    allowed, monkeypatch, caplog, agent_code, expected_status, expected_detail, expected_log
):
    _mock_agent(monkeypatch, _respond(502, {"code": agent_code}))
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == expected_status
    assert resp.json()["detail"] == {"code": expected_detail}
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert expected_log in lines[0]


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


# ---- ADR-1058 秘1: 担当表のモデルと使用の記録 ---------------------------------


@pytest.mark.asyncio
async def test_agent_receives_model_from_assignment(allowed, monkeypatch):
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json=_fixture("envelope-invoice.json"))

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    assert sent["model"] == "sonnet"
    assert sent["text"] == "請求書"


async def _raise_db_down(db, job_key):
    raise RuntimeError("db down")


async def _gemini_assignment(db, job_key):
    # 秘書の容器が無い provider（ADR-1058 段3 で codex は secretary-codex に送るようになった）
    return AiAssignment("gemini", "gemini-x")


@pytest.mark.asyncio
@pytest.mark.parametrize("reader", [_raise_db_down, _gemini_assignment])
async def test_assignment_read_failure_is_503_without_agent_or_ledger(allowed, monkeypatch, caplog, reader):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=_fixture("envelope-invoice.json"))

    _mock_agent(monkeypatch, handler)
    monkeypatch.setattr(assistant, "get_ai_assignment", reader)
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await allowed.post(URL, json={"text": "a"})
    assert len(calls) == 0
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "not_ready"}
    assert assistant.record_usage_isolated.await_count == 0
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=not_ready" in lines[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["envelope-invoice.json", "envelope-event.json", "envelope-unknown.json"])
async def test_ledger_ok_row_for_each_fixture(allowed, monkeypatch, name):
    _mock_agent(monkeypatch, _respond(200, _fixture(name)))
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 200, resp.text
    assert assistant.record_usage_isolated.await_count == 1
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert kwargs["purpose"] == "secretary_intent"
    assert kwargs["model"] == "sonnet"
    assert kwargs["sdk"] == "claude-code"
    assert kwargs["outcome"] == "ok"
    assert kwargs["error_code"] is None
    assert kwargs["tenant_id"] == 999
    assert kwargs["counts"] == UsageCounts()


def _assert_failed_row(expected_error_code: str) -> None:
    assert assistant.record_usage_isolated.await_count == 1
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert kwargs["outcome"] == "failed"
    assert kwargs["error_code"] == expected_error_code
    assert kwargs["purpose"] == "secretary_intent"
    assert kwargs["sdk"] == "claude-code"
    assert kwargs["model"] == "sonnet"
    assert kwargs["tenant_id"] == 999


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_status,agent_body,expected_error_code",
    [
        (503, {"code": "not_ready"}, "not_ready"),
        (429, {"code": "busy"}, "busy"),
        (504, {"code": "timeout"}, "timeout"),
        (502, {"code": "cli_failed"}, "other"),
        (502, {"code": "tool_used"}, "tool_used"),
        (502, {"code": "auth_failed"}, "auth_failed"),
        (502, {"code": "unreadable"}, "unreadable"),
        (200, {"kind": "invoice"}, "unreadable"),
    ],
)
async def test_ledger_failed_row_for_agent_failures(
    allowed, monkeypatch, agent_status, agent_body, expected_error_code
):
    _mock_agent(monkeypatch, _respond(agent_status, agent_body))
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code >= 400
    _assert_failed_row(expected_error_code)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc,expected_error_code",
    [
        (httpx.ConnectError("refused"), "not_ready"),
        (httpx.ReadTimeout("slow"), "timeout"),
    ],
)
async def test_ledger_failed_row_for_transport_errors(allowed, monkeypatch, exc, expected_error_code):
    def handler(request):
        raise exc

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code >= 400
    _assert_failed_row(expected_error_code)


def test_ledger_unit_mapping():
    from app.services.llm_budget import USAGE_ERROR_CODES

    assert assistant._ledger_error_code("cli_failed") == "other"
    assert assistant._ledger_error_code("agent_failed") == "other"
    assert assistant._ledger_error_code("tool_used") == "tool_used"
    assert assistant._ledger_error_code("auth_failed") == "auth_failed"
    assert assistant._LEDGER_ERROR_CODES <= USAGE_ERROR_CODES


# ---- ADR-1058 段3: ChatGPT の容器（secretary-codex） ------------------------------


def _codex_envelope(**over) -> dict:
    env = _fixture("envelope-invoice.json")
    env.pop("total_cost_usd", None)
    env["usage"] = {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 5, "reasoning_output_tokens": 3}
    env["error_events"] = 1
    env.update(over)
    return env


@pytest.fixture
def codex(allowed, monkeypatch):
    async def _assignment(db, job_key):
        return AiAssignment("codex", "gpt-5.6-luna")

    monkeypatch.setattr(assistant, "get_ai_assignment", _assignment)
    monkeypatch.setattr(assistant, "SECRETARY_AGENT_URL", "http://agent.test")
    monkeypatch.setattr(assistant, "SECRETARY_CODEX_URL", "http://codex.test")
    return allowed


def test_agent_url_mapping(monkeypatch):
    monkeypatch.setattr(assistant, "SECRETARY_AGENT_URL", "http://agent.test")
    monkeypatch.setattr(assistant, "SECRETARY_CODEX_URL", "http://codex.test")
    assert assistant.agent_url("claude") == "http://agent.test"
    assert assistant.agent_url("codex") == "http://codex.test"
    assert assistant.agent_url("gemini") is None
    assert assistant._sdk_for("claude") == "claude-code"
    assert assistant._sdk_for("codex") == "codex-cli"


@pytest.mark.asyncio
async def test_codex_goes_to_codex_container_with_model(codex, monkeypatch):
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        sent["url"] = str(request.url)
        return httpx.Response(200, json=_codex_envelope())

    _mock_agent(monkeypatch, handler)
    resp = await codex.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    assert sent["url"] == "http://codex.test/intent"
    assert sent["model"] == "gpt-5.6-luna"
    assert resp.json()["draft"]["company_name"] == "サンプル商事"


@pytest.mark.asyncio
async def test_claude_still_goes_to_agent_container(allowed, monkeypatch):
    monkeypatch.setattr(assistant, "SECRETARY_AGENT_URL", "http://agent.test")
    monkeypatch.setattr(assistant, "SECRETARY_CODEX_URL", "http://codex.test")
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["url"] = str(request.url)
        return httpx.Response(200, json=_fixture("envelope-invoice.json"))

    _mock_agent(monkeypatch, handler)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 200, resp.text
    assert sent["url"] == "http://agent.test/intent"


@pytest.mark.asyncio
async def test_codex_ledger_ok_row_has_usage(codex, monkeypatch):
    _mock_agent(monkeypatch, _respond(200, _codex_envelope()))
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 200, resp.text
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert kwargs["sdk"] == "codex-cli"
    assert kwargs["model"] == "gpt-5.6-luna"
    assert kwargs["outcome"] == "ok"
    assert kwargs["counts"] == UsageCounts(
        prompt_tokens=10, cached_content_tokens=2, candidates_tokens=5, thoughts_tokens=3
    )


@pytest.mark.asyncio
async def test_codex_usage_nulls_stay_null(codex, monkeypatch):
    usage = {"input_tokens": None, "cached_input_tokens": None, "output_tokens": None, "reasoning_output_tokens": None}
    _mock_agent(monkeypatch, _respond(200, _codex_envelope(usage=usage)))
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 200, resp.text
    assert assistant.record_usage_isolated.await_args.kwargs["counts"] == UsageCounts()


@pytest.mark.asyncio
async def test_codex_tool_used_is_recorded(codex, monkeypatch, caplog):
    _mock_agent(monkeypatch, _respond(502, {"code": "tool_used"}))
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 502
    assert resp.json()["detail"] == {"code": "agent_failed"}
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert (kwargs["outcome"], kwargs["error_code"], kwargs["sdk"]) == ("failed", "tool_used", "codex-cli")
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=tool_used" in lines[0]


@pytest.mark.asyncio
async def test_codex_log_has_error_events_without_text(codex, monkeypatch, caplog):
    _mock_agent(monkeypatch, _respond(200, _codex_envelope(error_events=2)))
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await codex.post(URL, json={"text": SECRET_TEXT})
    assert resp.status_code == 200, resp.text
    lines = [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]
    assert len(lines) == 1
    assert "code=ok" in lines[0] and "error_events=2" in lines[0] and "total_cost_usd=-" in lines[0]
    assert SECRET_TEXT not in "\n".join(r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "label,over",
    [
        ("usage extra key", {"usage": {"input_tokens": 1, "cache_write_input_tokens": 0}}),
        ("usage negative", {"usage": {"input_tokens": -1}}),
        ("usage string", {"usage": {"input_tokens": "5"}}),
        ("usage float", {"usage": {"input_tokens": 1.5}}),
        ("usage bool", {"usage": {"input_tokens": True}}),
        ("error_events negative", {"error_events": -1}),
        ("error_events string", {"error_events": "1"}),
    ],
)
async def test_codex_bad_envelope_is_unreadable(codex, monkeypatch, label, over):
    _mock_agent(monkeypatch, _respond(200, _codex_envelope(**over)))
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 502, label
    assert resp.json()["detail"] == {"code": "unreadable"}
    assert assistant.record_usage_isolated.await_args.kwargs["error_code"] == "unreadable"


@pytest.mark.asyncio
async def test_codex_unreachable_is_not_ready(codex, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    _mock_agent(monkeypatch, handler)
    resp = await codex.post(URL, json={"text": "a"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "not_ready"}
    kwargs = assistant.record_usage_isolated.await_args.kwargs
    assert (kwargs["error_code"], kwargs["sdk"]) == ("not_ready", "codex-cli")
