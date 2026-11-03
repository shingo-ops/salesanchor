"""ADR-1058 段2: AI の担当の画面の API の試験（DB 不要。担当表の読み書きは差し替える）。

K10（スーパー管理だけ）・判定の順 404 → 409 → 422・K11（switchable）・ログインの○×・K4（鍵とメールが出ない）。
本物の DB での切り替えと履歴（K9）は tests/ops/test_ai_job_assignments_db.py。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.routers import super_admin_ai_jobs as mod
from app.services.ai_assignment import (
    AiChoice,
    AiChoiceMismatch,
    AiJobHistoryRow,
    AiJobNotFound,
    AiJobNotWired,
    AiJobRow,
)
from app.services.llm_budget import USAGE_SDKS, USAGE_SDKS_BY_PROVIDER

_JOB_KEYS = [
    "line_extraction",
    "secretary_intent",
    "translation_inbound",
    "translation_inbound_escalation",
    "translation_outbound",
]

_FAKE_GEMINI_KEY = "AIza" + "x" * 35

_K4_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\."),
    re.compile(r"refresh_token"),
    re.compile(r"access_token"),
]


class _FakeDb:
    def __init__(self):
        self.commit = AsyncMock()


def _user(*, super_admin: bool, role: str) -> User:
    """role は試験の読みやすさのための名前だけ（User に role の列は無い。判定は is_super_admin だけ）。"""
    return User(
        id=7,
        tenant_id=1,
        username=f"u7-{role}",
        email="u7@example.test",
        full_name="担当者",
        is_super_admin=super_admin,
    )


def _app(db: _FakeDb, user: User | None) -> FastAPI:
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/v1")

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _jobs() -> list[AiJobRow]:
    rows = []
    for i, key in enumerate(_JOB_KEYS, start=1):
        if key == "secretary_intent":
            rows.append(AiJobRow(key, i, "claude", "sonnet", (AiChoice(i, "claude", "sonnet"),)))
        else:
            rows.append(
                AiJobRow(key, i, "gemini", "gemini-3.1-flash-lite", (AiChoice(i, "gemini", "gemini-3.1-flash-lite"),))
            )
    return rows


def _stats(**over) -> dict:
    base = {
        "last_ok_at": None,
        "count_24h": 0,
        "failed_24h": 0,
        "newest_error_code": None,
        "last_error_code": None,
        "last_error_at": None,
    }
    base.update(over)
    return base


@pytest.fixture()
def wired(monkeypatch):
    """担当表の読み書き・使用の記録・容器の /health を差し替える。"""
    monkeypatch.setenv("GEMINI_API_KEY", _FAKE_GEMINI_KEY)
    monkeypatch.setattr(mod, "list_ai_jobs", AsyncMock(return_value=_jobs()))
    monkeypatch.setattr(mod, "_usage_stats", AsyncMock(return_value=_stats()))
    monkeypatch.setattr(mod, "_secretary_agent_ready", AsyncMock(return_value=True))
    change = AsyncMock(return_value=True)
    monkeypatch.setattr(mod, "change_ai_assignment", change)
    history = AsyncMock(
        return_value=[
            AiJobHistoryRow(
                "secretary_intent",
                "claude",
                "sonnet",
                "claude",
                "sonnet",
                "担当者",
                7,
                datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc),
            )
        ]
    )
    monkeypatch.setattr(mod, "list_ai_job_history", history)
    return {"change": change, "history": history}


# --- K10: スーパー管理だけ ---------------------------------------------------------


@pytest.mark.asyncio
async def test_k10_tenant_admin_gets_403(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=False, role="admin"))) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == 403, r.text
    wired["change"].assert_not_awaited()


@pytest.mark.asyncio
async def test_k10_general_user_gets_403(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=False, role="staff"))) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == 403, r.text
    wired["change"].assert_not_awaited()


@pytest.mark.asyncio
async def test_k10_no_login_gets_401(wired):
    db = _FakeDb()
    async with _client(_app(db, None)) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == 401, r.text
    wired["change"].assert_not_awaited()


@pytest.mark.asyncio
async def test_get_routes_are_super_admin_only(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=False, role="admin"))) as c:
        r1 = await c.get("/api/v1/super-admin/ai-jobs")
        r2 = await c.get("/api/v1/super-admin/ai-jobs/history")
    assert (r1.status_code, r2.status_code) == (403, 403)


# --- PUT の失敗の返事（判定の順は本物の DB の試験で見る） -----------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (AiJobNotFound("nope"), 404, "not_found"),
        (AiJobNotWired("line_extraction"), 409, "not_wired"),
        (AiChoiceMismatch(99), 422, "choice_mismatch"),
    ],
)
async def test_put_errors_have_code_and_do_not_commit(wired, exc, status, code):
    wired["change"].side_effect = exc
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 1})
    assert r.status_code == status, r.text
    assert r.json() == {"detail": {"code": code}}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_success_commits_and_returns_get_row_shape(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        put = await c.put("/api/v1/super-admin/ai-jobs/secretary_intent", json={"choice_id": 2})
        got = await c.get("/api/v1/super-admin/ai-jobs")
    assert put.status_code == 200, put.text
    wired["change"].assert_awaited_once_with(db, "secretary_intent", 2, 7)
    db.commit.assert_awaited_once()
    row = next(j for j in got.json()["jobs"] if j["job_key"] == "secretary_intent")
    assert set(put.json()) == set(row)
    assert put.json()["job_key"] == "secretary_intent"


# --- K11: switchable ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_k11_only_secretary_is_switchable(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    assert r.status_code == 200, r.text
    jobs = r.json()["jobs"]
    assert sorted(j["job_key"] for j in jobs) == _JOB_KEYS
    assert {j["job_key"]: j["switchable"] for j in jobs} == {k: k == "secretary_intent" for k in _JOB_KEYS}
    assert all(j["login_refreshed_at"] is None for j in jobs)


# --- ログインの○×（design.md §6 の①②③） ------------------------------------------


@pytest.mark.parametrize(
    ("provider", "newest", "key", "ready", "expected"),
    [
        ("gemini", None, True, None, (True, None)),
        ("gemini", "auth_failed", True, None, (False, "auth_failed")),
        ("gemini", None, False, None, (False, "key_missing")),
        ("gemini", "auth_failed", False, None, (False, "auth_failed")),
        ("gemini", "timeout", True, None, (True, None)),
        ("claude", None, False, True, (True, None)),
        ("claude", None, True, False, (False, "not_ready")),
        ("claude", "auth_failed", True, False, (False, "auth_failed")),
        ("codex", None, False, False, (False, "not_ready")),
    ],
)
def test_login_state(provider, newest, key, ready, expected):
    assert mod._login_state(provider, newest, key, ready) == expected


@pytest.mark.asyncio
async def test_secretary_row_is_not_ready_when_agent_is_down(wired, monkeypatch):
    monkeypatch.setattr(mod, "_secretary_agent_ready", AsyncMock(return_value=False))
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    row = next(j for j in r.json()["jobs"] if j["job_key"] == "secretary_intent")
    assert (row["login_ok"], row["login_reason"]) == (False, "not_ready")


@pytest.mark.asyncio
async def test_gemini_rows_are_key_missing_without_key(wired, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        r = await c.get("/api/v1/super-admin/ai-jobs")
    rows = [j for j in r.json()["jobs"] if j["provider"] == "gemini"]
    assert len(rows) == 4
    assert all((j["login_ok"], j["login_reason"]) == (False, "key_missing") for j in rows)


@pytest.mark.asyncio
async def test_agent_health_unreachable_is_false(monkeypatch):
    """容器に届かない時は例外を出さず False（2 秒の打ち切りと同じ扱い）。"""
    monkeypatch.setattr(mod, "SECRETARY_AGENT_URL", "http://127.0.0.1:9")
    assert await mod._secretary_agent_ready() is False


def test_usage_sdks_belong_to_exactly_one_provider():
    """USAGE_SDKS のどの値もどれか1つの provider に属する（design.md §6 の①）。"""
    for sdk in USAGE_SDKS:
        owners = [p for p, sdks in USAGE_SDKS_BY_PROVIDER.items() if sdk in sdks]
        assert len(owners) == 1, (sdk, owners)
    assert set().union(*USAGE_SDKS_BY_PROVIDER.values()) == set(USAGE_SDKS)
    assert set(USAGE_SDKS_BY_PROVIDER) == {"gemini", "codex", "claude"}


# --- 履歴 -------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_limit_default_and_bounds(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        ok = await c.get("/api/v1/super-admin/ai-jobs/history")
        low = await c.get("/api/v1/super-admin/ai-jobs/history?limit=0")
        high = await c.get("/api/v1/super-admin/ai-jobs/history?limit=201")
    assert ok.status_code == 200, ok.text
    wired["history"].assert_awaited_once_with(db, 50)
    assert (low.status_code, high.status_code) == (422, 422)
    item = ok.json()["items"][0]
    assert item["old"] == {"provider": "claude", "model": "sonnet"}
    assert item["changed_by_name"] == "担当者"
    assert item["changed_by_id"] == 7


# --- K4: 鍵・メールが出ない -------------------------------------------------------------


@pytest.mark.asyncio
async def test_k4_responses_have_no_secret_or_email(wired):
    db = _FakeDb()
    async with _client(_app(db, _user(super_admin=True, role="admin"))) as c:
        jobs = await c.get("/api/v1/super-admin/ai-jobs")
        history = await c.get("/api/v1/super-admin/ai-jobs/history")
    for r in (jobs, history):
        assert r.status_code == 200, r.text
        for pattern in _K4_PATTERNS:
            assert pattern.search(r.text) is None, (pattern.pattern, r.text)
