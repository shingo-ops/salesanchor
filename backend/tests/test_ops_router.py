"""保守 API（ADR-1012 段階2 便B）の試験。実 PostgreSQL（アプリのロール）で口を叩く。"""
from __future__ import annotations

import os
import types
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.ops_control_lock import ops_control_lock
from tests.rls_bootstrap import _apply_migration, public_bootstrap_lock

ADMIN_PG_URL = (
    os.getenv("RLS_ADMIN_DATABASE_URL")
    or os.getenv("TEST_PG_URL")
)
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason=(
            "実 PostgreSQL 環境が必要 "
            "(RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。"
        ),
    ),
    pytest.mark.asyncio,
]

_MIGRATION = "20261016_100000_create_ops_incident_tables.sql"
_BASE = "/api/v1/ops"


class _Env:
    def __init__(self, admin_engine, app_engine, client, ingest_token, api_token):
        self.admin_engine = admin_engine
        self.app_engine = app_engine
        self.client = client
        self.ingest_token = ingest_token
        self.api_token = api_token
        self.fingerprints: list[str] = []

    def new_fingerprint(self) -> str:
        fp = "test-ops-api-" + uuid.uuid4().hex
        self.fingerprints.append(fp)
        return fp

    def ingest_headers(self):
        return {"Authorization": f"Bearer {self.ingest_token}"}

    def api_headers(self):
        return {"Authorization": f"Bearer {self.api_token}"}

    async def admin_fetch(self, sql: str, params: dict | None = None):
        from sqlalchemy import text

        async with self.admin_engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            return [dict(r) for r in result.mappings().all()]


def _alert(fingerprint: str, *, status="firing", starts_at=None, ends_at=None, **extra_labels):
    starts_at = starts_at or datetime(2026, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
    alert = {
        "status": status,
        "labels": {"alertname": "TestAlert", "severity": "warning", **extra_labels},
        "annotations": {"summary": "test"},
        "startsAt": starts_at.isoformat(),
        "fingerprint": fingerprint,
    }
    if ends_at is not None:
        alert["endsAt"] = ends_at.isoformat()
    return alert


def _payload(*alerts):
    return {"receiver": "ops-test", "status": "firing", "groupKey": "g", "alerts": list(alerts)}


@pytest_asyncio.fixture
async def env(monkeypatch):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import get_db
    from app.main import app

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    async with public_bootstrap_lock(admin_engine):
        await _apply_migration(admin_engine, _MIGRATION)

    ingest_token = "test-ingest-" + uuid.uuid4().hex
    api_token = "test-api-" + uuid.uuid4().hex
    monkeypatch.setenv("OPS_INGEST_TOKEN", ingest_token)
    monkeypatch.setenv("OPS_API_TOKEN", api_token)

    factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            holder = _Env(admin_engine, app_engine, client, ingest_token, api_token)
            yield holder
    finally:
        app.dependency_overrides.clear()
        async with admin_engine.begin() as conn:
            for fp in holder.fingerprints:
                await conn.execute(
                    text(
                        "DELETE FROM public.ops_incident_events WHERE incident_id IN "
                        "(SELECT id FROM public.ops_incidents WHERE fingerprint = :fp)"
                    ),
                    {"fp": fp},
                )
                await conn.execute(
                    text(
                        "UPDATE public.ops_incidents SET recurrence_of = NULL "
                        "WHERE fingerprint = :fp"
                    ),
                    {"fp": fp},
                )
                await conn.execute(
                    text("DELETE FROM public.ops_incidents WHERE fingerprint = :fp"),
                    {"fp": fp},
                )
        await admin_engine.dispose()
        await app_engine.dispose()


async def _clear_control(env: _Env):
    from sqlalchemy import text

    async with env.admin_engine.begin() as conn:
        await conn.execute(text("DELETE FROM public.ops_control WHERE id = 1"))


async def _incidents(env: _Env, fp: str):
    return await env.admin_fetch(
        "SELECT * FROM public.ops_incidents WHERE fingerprint = :fp ORDER BY starts_at",
        {"fp": fp},
    )


async def _events(env: _Env, incident_id):
    return await env.admin_fetch(
        "SELECT * FROM public.ops_incident_events WHERE incident_id = :id ORDER BY occurred_at",
        {"id": incident_id},
    )


async def test_ingest_creates_incident_and_event(env):
    fp = env.new_fingerprint()
    resp = await env.client.post(
        f"{_BASE}/alertmanager", json=_payload(_alert(fp)), headers=env.ingest_headers()
    )
    assert resp.status_code == 200
    assert resp.json() == {"received": 1, "created": 1, "updated": 0}

    rows = await _incidents(env, fp)
    assert len(rows) == 1
    assert rows[0]["notify_count"] == 1
    assert rows[0]["status"] == "firing"
    events = await _events(env, rows[0]["id"])
    assert len(events) == 1
    assert events[0]["kind"] == "notified"
    assert events[0]["actor"] == "alertmanager"


async def test_ingest_same_alert_twice_merges(env):
    fp = env.new_fingerprint()
    body = _payload(_alert(fp))
    for _ in range(2):
        resp = await env.client.post(
            f"{_BASE}/alertmanager", json=body, headers=env.ingest_headers()
        )
        assert resp.status_code == 200
    assert resp.json() == {"received": 1, "created": 0, "updated": 1}

    rows = await _incidents(env, fp)
    assert len(rows) == 1
    assert rows[0]["notify_count"] == 2
    assert len(await _events(env, rows[0]["id"])) == 2


async def test_ingest_resolved_sets_resolved_at(env):
    fp = env.new_fingerprint()
    starts = datetime(2026, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
    ends = starts + timedelta(minutes=5)
    await env.client.post(
        f"{_BASE}/alertmanager",
        json=_payload(_alert(fp, starts_at=starts)),
        headers=env.ingest_headers(),
    )
    resp = await env.client.post(
        f"{_BASE}/alertmanager",
        json=_payload(_alert(fp, status="resolved", starts_at=starts, ends_at=ends)),
        headers=env.ingest_headers(),
    )
    assert resp.status_code == 200
    rows = await _incidents(env, fp)
    assert len(rows) == 1
    assert rows[0]["status"] == "resolved"
    assert rows[0]["resolved_at"] == ends


async def test_ingest_recurrence_links_previous(env):
    fp = env.new_fingerprint()
    first = datetime(2026, 10, 16, 0, 0, 0, tzinfo=timezone.utc)
    second = first + timedelta(hours=1)
    for starts in (first, second):
        resp = await env.client.post(
            f"{_BASE}/alertmanager",
            json=_payload(_alert(fp, starts_at=starts)),
            headers=env.ingest_headers(),
        )
        assert resp.status_code == 200
    rows = await _incidents(env, fp)
    assert len(rows) == 2
    assert rows[0]["recurrence_of"] is None
    assert rows[1]["recurrence_of"] == rows[0]["id"]


async def test_ingest_rejects_missing_wrong_or_empty_token(env, monkeypatch):
    fp = env.new_fingerprint()
    body = _payload(_alert(fp))
    resp = await env.client.post(f"{_BASE}/alertmanager", json=body)
    assert resp.status_code == 401
    resp = await env.client.post(
        f"{_BASE}/alertmanager", json=body, headers=env.api_headers()
    )
    assert resp.status_code == 401

    monkeypatch.setenv("OPS_INGEST_TOKEN", "")
    for token in ("", "anything", env.ingest_token):
        resp = await env.client.post(
            f"{_BASE}/alertmanager",
            json=body,
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )
        assert resp.status_code == 401
    assert await _incidents(env, fp) == []


async def test_ingest_payload_limits_return_413(env):
    fp = env.new_fingerprint()
    big = _alert(fp)
    big["annotations"] = {"summary": "x" * 300000}
    resp = await env.client.post(
        f"{_BASE}/alertmanager", json=_payload(big), headers=env.ingest_headers()
    )
    assert resp.status_code == 413
    assert await _incidents(env, fp) == []

    alerts = []
    for _ in range(101):
        alerts.append(_alert(env.new_fingerprint()))
    resp = await env.client.post(
        f"{_BASE}/alertmanager", json=_payload(*alerts), headers=env.ingest_headers()
    )
    assert resp.status_code == 413
    for a in alerts:
        assert await _incidents(env, a["fingerprint"]) == []


async def test_reader_rejects_ingest_token_and_empty_env(env, monkeypatch):
    resp = await env.client.get(
        f"{_BASE}/incidents", headers={"Authorization": f"Bearer {env.ingest_token}"}
    )
    assert resp.status_code == 401

    monkeypatch.setenv("OPS_API_TOKEN", "")
    resp = await env.client.get(
        f"{_BASE}/incidents", headers={"Authorization": f"Bearer {env.api_token}"}
    )
    assert resp.status_code == 401


async def test_list_and_detail_with_ops_token(env):
    fp = env.new_fingerprint()
    await env.client.post(
        f"{_BASE}/alertmanager", json=_payload(_alert(fp)), headers=env.ingest_headers()
    )
    resp = await env.client.get(
        f"{_BASE}/incidents?limit=100", headers=env.api_headers()
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    mine = [i for i in items if i["fingerprint"] == fp]
    assert len(mine) == 1

    resp = await env.client.get(
        f"{_BASE}/incidents/{mine[0]['id']}", headers=env.api_headers()
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident"]["fingerprint"] == fp
    assert len(data["events"]) == 1

    resp = await env.client.get(
        f"{_BASE}/incidents/{uuid.uuid4()}", headers=env.api_headers()
    )
    assert resp.status_code == 404


async def test_annotate_updates_allowed_fields_only(env):
    fp = env.new_fingerprint()
    await env.client.post(
        f"{_BASE}/alertmanager", json=_payload(_alert(fp)), headers=env.ingest_headers()
    )
    row = (await _incidents(env, fp))[0]

    resp = await env.client.post(
        f"{_BASE}/incidents/{row['id']}/events",
        json={
            "kind": "annotated",
            "note": "memo",
            "fields": {"root_cause": "disk full", "fix_pr": 4400},
        },
        headers=env.api_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["updated_fields"] == ["fix_pr", "root_cause"]

    after = (await _incidents(env, fp))[0]
    assert after["root_cause"] == "disk full"
    assert after["fix_pr"] == 4400
    events = await _events(env, row["id"])
    assert [e["kind"] for e in events].count("annotated") == 1

    resp = await env.client.post(
        f"{_BASE}/incidents/{row['id']}/events",
        json={"kind": "annotated", "fields": {"status": "resolved"}},
        headers=env.api_headers(),
    )
    assert resp.status_code == 422
    assert (await _incidents(env, fp))[0]["status"] == "firing"


async def test_halt_with_ops_token_resume_requires_super_admin(env, monkeypatch):
    async def make_user(is_super_admin: bool):
        async def fake_get_current_user(request, cred, db):
            return types.SimpleNamespace(id=777, is_super_admin=is_super_admin)

        monkeypatch.setattr("app.routers.ops.get_current_user", fake_get_current_user)

    user_headers = {"Authorization": "Bearer login-token-" + uuid.uuid4().hex}
    async with ops_control_lock(env.admin_engine):
        try:
            resp = await env.client.post(
                f"{_BASE}/control/halt", json={"reason": "test halt"}, headers=env.api_headers()
            )
            assert resp.status_code == 200
            assert resp.json()["halt_all"] is True
            assert resp.json()["changed_by"] == "ops_token"

            resp = await env.client.post(
                f"{_BASE}/control/resume", json={"reason": "test"}, headers=env.api_headers()
            )
            assert resp.status_code == 403

            await make_user(False)
            resp = await env.client.post(
                f"{_BASE}/control/resume", json={"reason": "test"}, headers=user_headers
            )
            assert resp.status_code == 403

            await make_user(True)
            resp = await env.client.post(
                f"{_BASE}/control/resume", json={"reason": "test resume"}, headers=user_headers
            )
            assert resp.status_code == 200
            assert resp.json()["halt_all"] is False
            assert resp.json()["changed_by"] == "super_admin:777"

            resp = await env.client.get(f"{_BASE}/control", headers=env.api_headers())
            assert resp.status_code == 200
            assert resp.json()["halt_all"] is False
        finally:
            await _clear_control(env)


async def test_ingest_continues_while_halted(env):
    fp = env.new_fingerprint()
    async with ops_control_lock(env.admin_engine):
        try:
            resp = await env.client.post(
                f"{_BASE}/control/halt", json={"reason": "test halt"}, headers=env.api_headers()
            )
            assert resp.status_code == 200
            resp = await env.client.post(
                f"{_BASE}/alertmanager",
                json=_payload(_alert(fp)),
                headers=env.ingest_headers(),
            )
            assert resp.status_code == 200
            assert len(await _incidents(env, fp)) == 1
        finally:
            await _clear_control(env)


async def test_rows_invisible_without_operator_flag_after_request(env):
    from sqlalchemy import text

    fp = env.new_fingerprint()
    resp = await env.client.post(
        f"{_BASE}/alertmanager", json=_payload(_alert(fp)), headers=env.ingest_headers()
    )
    assert resp.status_code == 200
    assert len(await _incidents(env, fp)) == 1

    async with env.app_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT count(*) FROM public.ops_incidents WHERE fingerprint = :fp"),
            {"fp": fp},
        )
        assert result.scalar_one() == 0
