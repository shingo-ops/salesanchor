"""ADR-1025 便2: 自動セッション用の口 3 つのテスト（DB はモック）。"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_KEY = "agent-key-for-test"
_BASE = "/api/v1/ops/error-reports/ER-000001"
_MOD = "app.routers.ops_error_reports"
_REPORTED = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


def _report(status="open"):
    return {
        "id": "dddddddd-0000-0000-0000-000000000001", "report_code": "ER-000001",
        "extraction_item_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "extraction_job_id": "bbbbbbbb-0000-0000-0000-000000000001",
        "status": status, "reported_at": _REPORTED,
    }


@pytest.fixture(autouse=True)
def _key_env(monkeypatch):
    monkeypatch.setenv("ERROR_REPORT_AGENT_TOKEN", _KEY)


@pytest.fixture(autouse=True)
def _db_override():
    from app.database import get_db
    from app.main import app

    async def _fake_db():
        yield MagicMock(execute=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())

    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.pop(get_db, None)


@contextmanager
def _patched(report=None, prompt_version="v102:test"):
    with patch(f"{_MOD}.set_operator_context", new=AsyncMock()), \
         patch(f"{_MOD}.reset_operator_context", new=AsyncMock()), \
         patch(f"{_MOD}._load_report", new=AsyncMock(side_effect=_loader(report))), \
         patch(f"{_MOD}._prompt_version", new=AsyncMock(return_value=prompt_version)):
        yield


def _loader(report):
    from fastapi import HTTPException

    async def _load(db, code):
        if report is None:
            raise HTTPException(404, "Report not found")
        return report

    return _load


async def _call(method: str, path: str = "", *, key: str | None = _KEY, json=None):
    from app.main import app

    headers = {"Authorization": f"Bearer {key}"} if key is not None else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, _BASE + path, headers=headers, json=json)


async def test_no_key_401():
    assert (await _call("GET", key=None)).status_code == 401


async def test_wrong_key_401():
    assert (await _call("GET", key="wrong")).status_code == 401


async def test_unset_key_env_401_even_with_plausible_key(monkeypatch):
    monkeypatch.delenv("ERROR_REPORT_AGENT_TOKEN", raising=False)
    assert (await _call("GET", key=_KEY)).status_code == 401
    monkeypatch.setenv("ERROR_REPORT_AGENT_TOKEN", "")
    assert (await _call("GET", key="")).status_code == 401


async def test_super_admin_login_alone_401():
    from app.auth.dependencies import get_current_user, require_super_admin
    from app.main import app

    async def _admin():
        return type("User", (), {"email": "admin@example.com", "is_super_admin": True})()

    app.dependency_overrides[get_current_user] = _admin
    app.dependency_overrides[require_super_admin] = _admin
    try:
        assert (await _call("GET", key="login-jwt-token")).status_code == 401
        assert (await _call("POST", "/events", key="login-jwt-token", json={"kind": "cause", "actor": "a"})).status_code == 401
        assert (await _call("POST", "/reanalyze", key="login-jwt-token")).status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_super_admin, None)


async def test_unknown_report_404():
    with _patched(report=None):
        assert (await _call("GET")).status_code == 404
        assert (await _call("POST", "/events", json={"kind": "cause", "actor": "a"})).status_code == 404
        assert (await _call("POST", "/reanalyze")).status_code == 404


async def test_get_returns_detail():
    fields = [{"field_name": "quantity", "system_value": 2, "expected_value": 3, "expected_missing_product": False}]
    event = {"at": _REPORTED, "actor": "u", "kind": "created", "payload": {}}

    def _result(rows):
        r = MagicMock()
        r.mappings.return_value.all.return_value = rows
        return r

    db = MagicMock(execute=AsyncMock(side_effect=[_result(fields), _result([event])]))
    from app.database import get_db
    from app.main import app

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    with _patched(report=_report()), \
         patch(f"{_MOD}._read_system_values", new=AsyncMock(return_value={"quantity": 2})):
        r = await _call("GET")
    assert r.status_code == 200
    body = r.json()
    assert body["report"]["report_code"] == "ER-000001"
    assert body["fields"][0]["expected_value"] == 3
    assert body["current_values"] == {"quantity": 2}
    assert body["prompt_version"] == "v102:test"
    assert body["events"][0]["kind"] == "created"


@pytest.mark.parametrize("body", [
    {"kind": "created", "actor": "a", "payload": {}},
    {"kind": "verified", "actor": "a", "payload": {}},
    {"kind": "cause", "actor": "", "payload": {}},
])
async def test_events_invalid_kind_or_actor_422(body):
    with _patched(report=_report()):
        assert (await _call("POST", "/events", json=body)).status_code == 422


async def test_events_payload_over_8192_bytes_422():
    with _patched(report=_report()):
        r = await _call("POST", "/events", json={"kind": "action", "actor": "a", "payload": {"x": "a" * 9000}})
    assert r.status_code == 422


@pytest.mark.parametrize("status", ["resolved", "cancelled"])
async def test_closed_report_409(status):
    with _patched(report=_report(status)):
        assert (await _call("POST", "/events", json={"kind": "cause", "actor": "a"})).status_code == 409
        assert (await _call("POST", "/reanalyze")).status_code == 409


async def test_events_ok_201_and_open_becomes_working():
    from app.database import get_db
    from app.main import app

    db = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=7)))

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    with _patched(report=_report("open")):
        r = await _call("POST", "/events", json={"kind": "cause", "actor": "agent", "payload": {"why": "x"}})
    assert r.status_code == 201
    assert r.json() == {"id": 7}
    sqls = [str(c.args[0]) for c in db.execute.call_args_list]
    assert any("SET status = 'working'" in s for s in sqls)
    db.commit.assert_awaited()


async def test_reanalyze_not_v102_409():
    with _patched(report=_report(), prompt_version="v6:old"):
        r = await _call("POST", "/reanalyze")
    assert r.status_code == 409
    assert r.json()["detail"] == "not_v102"


async def test_reanalyze_ok_202_and_task_enqueued():
    task = MagicMock()
    with _patched(report=_report(), prompt_version="v102:test"), \
         patch("app.tasks.tcg_extraction.error_report_reanalyze_and_verify_task", new=task):
        r = await _call("POST", "/reanalyze")
    assert r.status_code == 202
    task_id = r.json()["task_id"]
    task.apply_async.assert_called_once()
    assert task.apply_async.call_args.kwargs["task_id"] == task_id
    assert task.apply_async.call_args.kwargs["args"] == [_report()["id"]]
