"""ADR-1077 便2b: 決まり帳の口と、秘書の口が承認済みの決まりを容器へ送ることの試験（SQLite・design.md §3・§5・§11）。

決まり帳の読み書き（app/services/secretary_rules.py）は AsyncMock に差し替える。本物の PostgreSQL での試験は
tests/test_secretary_rules_service_pg.py。容器は httpx をモックする（tests/test_assistant_router.py と同じ道具）。
テストデータはすべて架空。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app.routers import assistant
from app.services.secretary_rules import RuleNotFound, RulesFull, RuleWrongStatus, SecretaryRule
from tests.test_assistant_router import _fixture, _mock_agent, _respond
from tests.test_assistant_router import allowed as allowed  # noqa: F401  fixture

URL = "/api/v1/assistant/messages"
RULES_URL = "/api/v1/assistant/rules"
WRITERS = ("add_approved_rule", "add_candidate", "approve_candidate", "reject_candidate", "remove_rule")
_T = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)


def _rule(**over) -> SecretaryRule:
    base = {
        "id": 5,
        "status": "approved",
        "rule_text": "決まり",
        "source_text": None,
        "source_kind": None,
        "source_reply": None,
        "created_at": _T,
        "decided_at": _T,
    }
    base.update(over)
    return SecretaryRule(**base)


def _capture(monkeypatch) -> dict:
    """容器へ送られた生のバイト・読んだ JSON・Content-Type を残す（容器は unknown の見本を返す）。"""
    sent: dict = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["calls"] += 1
        sent["raw"] = request.content
        sent["body"] = json.loads(request.content)
        sent["content_type"] = request.headers.get("content-type")
        return httpx.Response(200, json=_fixture("envelope-unknown.json"))

    _mock_agent(monkeypatch, handler)
    return sent


def _writers(monkeypatch) -> dict:
    mocks = {name: AsyncMock() for name in WRITERS}
    for name, mock in mocks.items():
        monkeypatch.setattr(assistant, name, mock)
    return mocks


def _log_lines(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if "assistant_message" in r.getMessage()]


# ---- 秘書の口が決まりを送る（design.md §3・R4・R5）-------------------------------------


@pytest.mark.asyncio
async def test_approved_rules_are_sent_in_order(allowed, monkeypatch):
    reader = AsyncMock(return_value=["一つ目の決まり", "二つ目の決まり"])
    monkeypatch.setattr(assistant, "list_approved_rule_texts", reader)
    sent = _capture(monkeypatch)
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    assert sent["body"]["rules"] == ["一つ目の決まり", "二つ目の決まり"]
    assert set(sent["body"]) == {"text", "now", "model", "rules"}
    assert "一つ目の決まり".encode("utf-8") in sent["raw"]
    assert sent["content_type"] == "application/json"
    reader.assert_awaited_once()
    assert reader.await_args.args[1] == 999


@pytest.mark.asyncio
async def test_no_rules_sends_empty_list(allowed, monkeypatch):
    sent = _capture(monkeypatch)
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    assert sent["body"]["rules"] == []


@pytest.mark.asyncio
async def test_too_long_is_413_without_agent_or_ledger(allowed, monkeypatch, caplog):
    # 絵文字（1 字 4 バイト）で決まり 20 件 × 150 字＋文 1000 字 → 16,000 バイトを超える
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(return_value=["😀" * 150] * 20))
    sent = _capture(monkeypatch)
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await allowed.post(URL, json={"text": "😀" * 1000})
    assert resp.status_code == 413
    assert resp.json()["detail"] == {"code": "rules_too_long"}
    assert sent["calls"] == 0
    assert assistant.record_usage_isolated.await_count == 0
    lines = _log_lines(caplog)
    assert len(lines) == 1
    assert "code=rules_too_long" in lines[0]


@pytest.mark.asyncio
async def test_japanese_full_rules_fit(allowed, monkeypatch):
    # 日本語（1 字 3 バイト）で決まり 20 件 × 150 字＋文 1000 字は 15,000 バイトに収まり送られる
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(return_value=["あ" * 150] * 20))
    sent = _capture(monkeypatch)
    resp = await allowed.post(URL, json={"text": "あ" * 1000})
    assert resp.status_code == 200, resp.text
    assert sent["calls"] == 1
    assert len(sent["raw"]) <= assistant.AGENT_BODY_MAX_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize("delta, expected", [(0, 200), (-1, 413)])
async def test_size_boundary(allowed, monkeypatch, delta, expected):
    sent = _capture(monkeypatch)
    limit = len(assistant._agent_payload("a", "sonnet", [])) + delta
    monkeypatch.setattr(assistant, "AGENT_BODY_MAX_BYTES", limit)
    resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == expected, resp.text
    if expected == 200:
        assert len(sent["raw"]) == limit
    else:
        assert sent["calls"] == 0


@pytest.mark.asyncio
async def test_rules_read_failure_is_503_without_agent_or_ledger(allowed, monkeypatch, caplog):
    monkeypatch.setattr(assistant, "list_approved_rule_texts", AsyncMock(side_effect=RuntimeError("db down")))
    sent = _capture(monkeypatch)
    with caplog.at_level(logging.INFO, logger=assistant.logger.name):
        resp = await allowed.post(URL, json={"text": "a"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == {"code": "not_ready"}
    assert sent["calls"] == 0
    assert assistant.record_usage_isolated.await_count == 0
    lines = _log_lines(caplog)
    assert len(lines) == 1
    assert "code=rules_unreadable" in lines[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["envelope-invoice.json", "envelope-event.json", "envelope-unknown.json"])
async def test_agent_answer_never_writes_rules(allowed, monkeypatch, name):
    # R1: AI の答えだけでは決まり帳に行が増えない
    writers = _writers(monkeypatch)
    _mock_agent(monkeypatch, _respond(200, _fixture(name)))
    resp = await allowed.post(URL, json={"text": "請求書"})
    assert resp.status_code == 200, resp.text
    for mock in writers.values():
        assert mock.await_count == 0


# ---- 守り（R6: 新しい口すべてで同じ 4 つ）----------------------------------------------

ENDPOINTS = [
    ("get", RULES_URL + "?status=approved", None),
    ("post", RULES_URL, {"rule_text": "決まり"}),
    ("post", RULES_URL + "/feedback", {"source_text": "元の文", "source_kind": "invoice"}),
    ("post", RULES_URL + "/5/approve", {"rule_text": "決まり"}),
    ("post", RULES_URL + "/5/reject", None),
    ("post", RULES_URL + "/5/remove", None),
    ("post", URL, {"text": "a"}),
]


async def _call(client, method: str, url: str, body):
    if method == "get":
        return await client.get(url)
    if body is None:
        return await client.post(url)
    return await client.post(url, json=body)


@pytest.mark.asyncio
@pytest.mark.parametrize("method, url, body", ENDPOINTS)
async def test_not_super_admin_is_403_everywhere(client, monkeypatch, method, url, body):
    from app.main import app

    async def _ok_feature():
        return None

    app.dependency_overrides[assistant._feature_secretary_chat] = _ok_feature
    monkeypatch.setattr(assistant, "list_rules", AsyncMock())
    writers = _writers(monkeypatch)
    # require_super_admin は上書きしない: モックユーザーは is_super_admin が偽
    resp = await _call(client, method, url, body)
    assert resp.status_code == 403
    assert assistant.list_rules.await_count == 0
    for mock in writers.values():
        assert mock.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("method, url, body", ENDPOINTS)
async def test_no_feature_is_403_everywhere(client, method, url, body):
    from app.main import app

    async def _no_feature():
        raise HTTPException(status_code=403, detail="機能が無効です: secretary_chat")

    app.dependency_overrides[assistant._feature_secretary_chat] = _no_feature
    resp = await _call(client, method, url, body)
    assert resp.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("method, url, body", ENDPOINTS)
async def test_missing_permission_is_403_everywhere(allowed, monkeypatch, method, url, body):
    async def _only_view(db, tenant_id, user_id):
        return {"customers.view"}

    monkeypatch.setattr("app.auth.dependencies.load_user_permissions", _only_view)
    resp = await _call(allowed, method, url, body)
    assert resp.status_code == 403


# ---- POST /assistant/rules（案の「承認」）----------------------------------------------


@pytest.mark.asyncio
async def test_post_rule_adds_approved(allowed, monkeypatch):
    add = AsyncMock(return_value=_rule(rule_text="決まり"))
    monkeypatch.setattr(assistant, "add_approved_rule", add)
    resp = await allowed.post(RULES_URL, json={"rule_text": "  決まり  "})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["id"] == 5 and data["status"] == "approved" and data["rule_text"] == "決まり"
    assert add.await_args.args[1:] == (999, 999, "決まり")


@pytest.mark.asyncio
async def test_post_rule_full_is_409(allowed, monkeypatch):
    monkeypatch.setattr(assistant, "add_approved_rule", AsyncMock(side_effect=RulesFull()))
    resp = await allowed.post(RULES_URL, json={"rule_text": "決まり"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == {"code": "rules_full"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"rule_text": ""},
        {"rule_text": "   "},
        {"rule_text": "あ" * 151},
        {"rule_text": "a\tb"},
        {"rule_text": "a\x00b"},
        {"rule_text": "a\rb"},
        {"rule_text": "決まり", "extra": 1},
        {},
    ],
)
async def test_post_rule_rejects_bad_text(allowed, monkeypatch, body):
    add = AsyncMock(return_value=_rule())
    monkeypatch.setattr(assistant, "add_approved_rule", add)
    resp = await allowed.post(RULES_URL, json=body)
    assert resp.status_code == 422
    assert add.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("rule_text", ["あ" * 150, "一行目\n二行目"])
async def test_post_rule_accepts_full_length_and_newline(allowed, monkeypatch, rule_text):
    add = AsyncMock(return_value=_rule(rule_text=rule_text))
    monkeypatch.setattr(assistant, "add_approved_rule", add)
    resp = await allowed.post(RULES_URL, json={"rule_text": rule_text})
    assert resp.status_code == 201, resp.text
    assert add.await_args.args[3] == rule_text


# ---- POST /assistant/rules/feedback（答えの「違う」）------------------------------------


@pytest.mark.asyncio
async def test_feedback_adds_candidate(allowed, monkeypatch):
    add = AsyncMock(
        return_value=_rule(
            status="candidate",
            rule_text="",
            source_text="元の文",
            source_kind="event",
            source_reply="答え",
            decided_at=None,
        )
    )
    monkeypatch.setattr(assistant, "add_candidate", add)
    resp = await allowed.post(
        RULES_URL + "/feedback",
        json={"source_text": "元の文", "source_kind": "event", "source_reply": "答え"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "candidate" and data["decided_at"] is None
    assert add.await_args.args[1:] == (999, 999, "", "元の文", "event", "答え")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "over",
    [
        {"source_text": ""},
        {"source_text": "あ" * 1001},
        {"source_text": "a\x00b"},
        {"source_kind": "other"},
        {"source_reply": "あ" * 201},
        {"source_reply": "a\x00b"},
        {"rule_text": "a\x07b"},
        {"rule_text": "あ" * 151},
        {"extra": 1},
    ],
)
async def test_feedback_rejects_bad_body(allowed, monkeypatch, over):
    add = AsyncMock(return_value=_rule(status="candidate", decided_at=None))
    monkeypatch.setattr(assistant, "add_candidate", add)
    body = {"source_text": "元の文", "source_kind": "invoice"}
    body.update(over)
    resp = await allowed.post(RULES_URL + "/feedback", json=body)
    assert resp.status_code == 422
    assert add.await_count == 0


# ---- GET /assistant/rules?status=（R3）--------------------------------------------------


@pytest.mark.asyncio
async def test_list_rules(allowed, monkeypatch):
    lister = AsyncMock(return_value=[_rule(id=1), _rule(id=2)])
    monkeypatch.setattr(assistant, "list_rules", lister)
    for status in ("approved", "candidate"):
        resp = await allowed.get(RULES_URL, params={"status": status})
        assert resp.status_code == 200, resp.text
        assert [r["id"] for r in resp.json()["rules"]] == [1, 2]
        assert lister.await_args.args[1:] == (999, status)


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{"status": "rejected"}, {"status": "removed"}, {}])
async def test_list_rules_rejects_other_status(allowed, monkeypatch, params):
    lister = AsyncMock(return_value=[])
    monkeypatch.setattr(assistant, "list_rules", lister)
    resp = await allowed.get(RULES_URL, params=params)
    assert resp.status_code == 422
    assert lister.await_count == 0


# ---- 承認・捨てる・外す ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, service",
    [("approve", "approve_candidate"), ("reject", "reject_candidate"), ("remove", "remove_rule")],
)
@pytest.mark.parametrize(
    "exc, status_code, code",
    [(RuleNotFound(5), 404, "rule_not_found"), (RuleWrongStatus("removed"), 409, "wrong_status")],
)
async def test_decide_errors(allowed, monkeypatch, action, service, exc, status_code, code):
    monkeypatch.setattr(assistant, service, AsyncMock(side_effect=exc))
    body = {"rule_text": "決まり"} if action == "approve" else None
    resp = await _call(allowed, "post", f"{RULES_URL}/5/{action}", body)
    assert resp.status_code == status_code
    assert resp.json()["detail"] == {"code": code}


@pytest.mark.asyncio
async def test_approve_ok_and_full(allowed, monkeypatch):
    approve = AsyncMock(return_value=_rule(rule_text="決まり"))
    monkeypatch.setattr(assistant, "approve_candidate", approve)
    resp = await allowed.post(RULES_URL + "/5/approve", json={"rule_text": " 決まり "})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"
    assert approve.await_args.args[1:] == (999, 5, 999, "決まり")

    monkeypatch.setattr(assistant, "approve_candidate", AsyncMock(side_effect=RulesFull()))
    resp = await allowed.post(RULES_URL + "/5/approve", json={"rule_text": "決まり"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == {"code": "rules_full"}


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [None, {"rule_text": ""}])
async def test_approve_needs_text(allowed, monkeypatch, body):
    approve = AsyncMock(return_value=_rule())
    monkeypatch.setattr(assistant, "approve_candidate", approve)
    resp = await _call(allowed, "post", RULES_URL + "/5/approve", body)
    assert resp.status_code == 422
    assert approve.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action, service, status",
    [("reject", "reject_candidate", "rejected"), ("remove", "remove_rule", "removed")],
)
async def test_reject_and_remove_ok(allowed, monkeypatch, action, service, status):
    mock = AsyncMock(return_value=_rule(status=status))
    monkeypatch.setattr(assistant, service, mock)
    resp = await allowed.post(f"{RULES_URL}/5/{action}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == status
    assert mock.await_args.args[1:] == (999, 5, 999)
