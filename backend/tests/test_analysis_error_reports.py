"""
ADR-1025 便1: 解析の誤り報告 API のテスト。

カバー:
  - 認証なし → 401/403、super admin 以外 → 403
  - field_name の重複 → 422、候補にない unit → 422、メモの無効な語 → 422
  - 正しい入力 → 201 と report_code の形（ER-＋6桁）
  - Discord 未設定でも 201（notified=false）
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_ITEM_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_URL = f"/api/v1/tcg/items/{_ITEM_ID}/error-reports"
_SVC = "app.services.analysis_error_report_svc"


@pytest.fixture
def super_admin_override():
    from app.auth.dependencies import require_super_admin
    from app.main import app

    async def _bypass():
        return type("User", (), {"email": "admin@example.com", "is_super_admin": True})()

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


@pytest.fixture
def non_super_admin_override():
    from app.auth.dependencies import get_current_user
    from app.main import app

    async def _user():
        return type("User", (), {"email": "user@example.com", "is_super_admin": False})()

    app.dependency_overrides[get_current_user] = _user
    yield
    app.dependency_overrides.pop(get_current_user, None)


async def _post(body: dict):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(_URL, json=body)


def _found_item():
    from app.services.v102_human_decisions_svc import JobOfItem

    return AsyncMock(return_value=JobOfItem("bbbbbbbb-0000-0000-0000-000000000001", "v102:test", "cccccccc-0000-0000-0000-000000000001"))


async def test_requires_auth():
    r = await _post({"fields": [{"field_name": "quantity", "expected_value": 3}]})
    assert r.status_code in (401, 403)


async def test_non_super_admin_forbidden(non_super_admin_override):
    r = await _post({"fields": [{"field_name": "quantity", "expected_value": 3}]})
    assert r.status_code == 403


async def test_duplicate_field_name_422(super_admin_override):
    r = await _post({"fields": [
        {"field_name": "quantity", "expected_value": 3},
        {"field_name": "quantity", "expected_value": 4},
    ]})
    assert r.status_code == 422


async def test_empty_fields_422(super_admin_override):
    r = await _post({"fields": []})
    assert r.status_code == 422


async def test_unknown_unit_422(super_admin_override):
    with patch(f"{_SVC}.find_job_of_item", new=_found_item()), \
         patch(f"{_SVC}._unit_and_status_choices", new=AsyncMock(return_value={"units": ["BOX"], "statuses": ["Sold out"]})):
        r = await _post({"fields": [{"field_name": "unit", "expected_value": "存在しない単位"}]})
    assert r.status_code == 422


async def test_invalid_note_label_422(super_admin_override):
    with patch(f"{_SVC}.find_job_of_item", new=_found_item()), \
         patch(f"{_SVC}._note_labels", new=AsyncMock(return_value={"未開封"})):
        r = await _post({"fields": [{"field_name": "note", "expected_value": ["未開封", "無効な語"]}]})
    assert r.status_code == 422


async def test_item_not_found_404(super_admin_override):
    with patch(f"{_SVC}.find_job_of_item", new=AsyncMock(return_value=None)):
        r = await _post({"fields": [{"field_name": "quantity", "expected_value": 3}]})
    assert r.status_code == 404


async def test_ok_returns_201_and_code(super_admin_override, monkeypatch):
    from app.services.analysis_error_report_svc import CreatedReport

    created = CreatedReport(report_id="dddddddd-0000-0000-0000-000000000001", report_code="ER-000001",
                            field_names=["quantity", "price"])
    monkeypatch.setenv("ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK", "https://discord.example/webhook")
    with patch("app.routers.analysis_error_reports.create_report", new=AsyncMock(return_value=created)), \
         patch(f"{_SVC}._record_notify_result", new=AsyncMock()), \
         patch("app.services.discord_notifier.httpx.AsyncClient") as client_cls:
        resp = client_cls.return_value.__aenter__.return_value.post
        resp.return_value = type("R", (), {"status_code": 200, "json": lambda self: {"id": "123"}})()
        r = await _post({"fields": [
            {"field_name": "quantity", "expected_value": 3},
            {"field_name": "price", "expected_value": 1200},
        ]})
        sent = resp.call_args
    assert r.status_code == 201
    body = r.json()
    import re

    assert re.fullmatch(r"ER-\d{6}", body["report_code"])
    assert body["notified"] is True
    assert "wait=true" in sent.args[0]
    assert sent.kwargs["json"]["content"] == "誤り報告 ER-000001 項目: 数量, 価格"


async def test_discord_unset_still_201(super_admin_override, monkeypatch):
    from app.services.analysis_error_report_svc import CreatedReport

    created = CreatedReport(report_id="dddddddd-0000-0000-0000-000000000001", report_code="ER-000002",
                            field_names=["quantity"])
    monkeypatch.delenv("ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK", raising=False)
    record = AsyncMock()
    with patch("app.routers.analysis_error_reports.create_report", new=AsyncMock(return_value=created)), \
         patch(f"{_SVC}._record_notify_result", new=record):
        r = await _post({"fields": [{"field_name": "quantity", "expected_value": 3}]})
    assert r.status_code == 201
    assert r.json() == {"report_code": "ER-000002", "notified": False}
    assert record.call_args.args[3] == "webhook_not_configured"
