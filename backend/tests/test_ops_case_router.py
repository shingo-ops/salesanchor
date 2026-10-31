"""ADR-1052 段2: 相談係の件の口 8 つの試験（実 PostgreSQL が必要）。

使い捨て DB に本物の migration を流し、アプリのロール（salesanchor_app）で口を叩く。
鍵の取り違え・件の札・報告・申請の検査と上限・判断・DB の失敗（503）を確かめる。
クラスタ共通のロールは、この試験が作った場合だけ最後に消す。
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = [
    pytest.mark.skipif(not ADMIN_PG_URL, reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。"),
    pytest.mark.asyncio,
]

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
_ROLES = ("ai_unmask", "ai_unmask_owner", "ai_reader_cloud", "ai_reader", "salesanchor_app", "aic_owner")
_BASE = "/api/v1/ops/case"
_VIEW_OK = "public__plain_demo"
_AGENT_KEY = "agent-key-" + uuid.uuid4().hex
_ADMIN_KEY = "admin-key-" + uuid.uuid4().hex


def _psycopg_url(dbname: str | None = None) -> str:
    url = ADMIN_PG_URL.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


def _asyncpg_url(dbname: str) -> str:
    return _psycopg_url(dbname).replace("postgresql://", "postgresql+asyncpg://", 1)


def _read(fname: str) -> str:
    return (_MIGRATIONS_DIR / fname).read_text("utf-8")


class _Env:
    def __init__(self, admin, client, dbname):
        self.admin = admin  # psycopg2（superuser・autocommit）
        self.client = client
        self.dbname = dbname

    def one(self, sql, params=None):
        c = self.admin.cursor()
        c.execute(sql, params)
        return c.fetchone()[0]

    def rows(self, sql, params=None):
        c = self.admin.cursor()
        c.execute(sql, params)
        return c.fetchall()

    def new_incident(self) -> str:
        c = self.admin.cursor()
        c.execute(
            "INSERT INTO public.ops_incidents (fingerprint, starts_at, alertname, status, first_notified_at,"
            " last_notified_at) VALUES (%s, now(), 'test', 'firing', now(), now()) RETURNING id::text",
            (uuid.uuid4().hex,),
        )
        return c.fetchone()[0]

    async def new_case(self) -> tuple[str, str]:
        """件と札を作る（口 1 を通す）。(incident_id, ticket)"""
        iid = self.new_incident()
        resp = await self.client.post(f"{_BASE}/{iid}/ticket", headers=admin())
        assert resp.status_code == 200, resp.text
        return iid, resp.json()["ticket"]


def admin(extra=None):
    return {"Authorization": f"Bearer {_ADMIN_KEY}", **(extra or {})}


def agent(ticket=None, extra=None):
    h = {"Authorization": f"Bearer {_AGENT_KEY}", **(extra or {})}
    if ticket is not None:
        h["X-Case-Ticket"] = ticket
    return h


def _good_body(**kw):
    body = {
        "view_name": _VIEW_OK,
        "column_names": ["memo"],
        "row_keys": ["1"],
        "reason": "障害の調べのために該当の行の値を確かめる必要がある",
    }
    body.update(kw)
    return body


@pytest_asyncio.fixture
async def env(monkeypatch):
    import psycopg2
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import get_db
    from app.main import app

    control = psycopg2.connect(_psycopg_url())
    control.autocommit = True
    cur = control.cursor()
    existed = {}
    for r in _ROLES:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (r,))
        existed[r] = cur.fetchone() is not None
    dbname = f"ops_case_router_{uuid.uuid4().hex[:12]}"
    cur.execute(f'CREATE DATABASE "{dbname}"')
    admin_conn = psycopg2.connect(_psycopg_url(dbname))
    admin_conn.autocommit = True
    a = admin_conn.cursor()
    a.execute("SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app'")
    if a.fetchone() is None:
        a.execute("CREATE ROLE salesanchor_app NOLOGIN NOSUPERUSER NOBYPASSRLS")
    a.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aic_owner'")
    if a.fetchone() is None:
        a.execute("CREATE ROLE aic_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
    a.execute(_read("20261017_130000_create_ai_reader_role.sql"))
    a.execute(_read("20261024_100100_create_ai_reader_cloud_role.sql"))
    a.execute(_read("20261016_100000_create_ops_incident_tables.sql"))
    a.execute(f'GRANT CREATE ON DATABASE "{dbname}" TO aic_owner')
    a.execute("ALTER SCHEMA public OWNER TO aic_owner")
    a.execute("SET ROLE aic_owner")
    a.execute("CREATE TABLE public.plain_demo (id integer PRIMARY KEY, memo text, email text)")
    a.execute("CREATE TABLE public.small_pk (id smallint PRIMARY KEY, memo text)")
    a.execute("CREATE TABLE public.has_secret (id integer PRIMARY KEY, memo text, api_token text)")
    a.execute("CREATE TABLE public.two_pk (a integer, b integer, memo text, PRIMARY KEY (a, b))")
    a.execute("CREATE SCHEMA tenant_001")
    a.execute("CREATE TABLE tenant_001.leads (id uuid PRIMARY KEY, customer_name text)")
    a.execute("CREATE TABLE tenant_001.viewer_accounts (id integer PRIMARY KEY, note text)")
    a.execute(_read("20261024_100000_create_ai_cloud_meta.sql"))
    a.execute(_read("20261024_100300_create_ai_cloud_views.sql"))
    a.execute("RESET ROLE")
    a.execute(_read("20261031_210000_create_ops_case.sql"))

    # backend の接続は salesanchor_app（接続のとき role を切り替える。パスワードを持たない試験 DB 用）
    engine = create_async_engine(_asyncpg_url(dbname), echo=False, connect_args={"server_settings": {"role": "salesanchor_app"}})
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setenv("CASE_AGENT_TOKEN", _AGENT_KEY)
    monkeypatch.setenv("CASE_ADMIN_TOKEN", _ADMIN_KEY)
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield _Env(admin_conn, client, dbname)
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
        admin_conn.close()
        cur.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
        for r in _ROLES:
            if not existed[r]:
                try:
                    cur.execute(f"DROP ROLE IF EXISTS {r}")
                except psycopg2.Error:
                    pass
        control.close()


# ---------------------------------------------------------------------------------------------------
# 鍵
# ---------------------------------------------------------------------------------------------------
_ADMIN_CALLS = [
    ("post", "/{iid}/ticket", None),
    ("get", "/pending", None),
    ("post", "/unmask-requests/{rid}/decision", {"decision": "denied", "reason": "x"}),
    ("post", "/audits", {"findings": []}),
    ("get", "/audit-inputs", None),
]
_AGENT_CALLS = [
    ("post", "/{iid}/report", {"status": "reported"}),
    ("post", "/{iid}/unmask-requests", None),
    ("get", "/unmask-requests/{rid}", None),
]


def _url(path):
    iid = str(uuid.uuid4())
    return _BASE + path.format(iid=iid, rid=iid)


async def _call(env, method, path, body, headers):
    kwargs = {"headers": headers}
    if body is not None or method == "post":
        kwargs["json"] = body if body is not None else _good_body()
    return await getattr(env.client, method)(_url(path), **kwargs)


@pytest.mark.parametrize("method,path,body", _ADMIN_CALLS)
async def test_admin_routes_reject_missing_wrong_and_agent_key(env, method, path, body):
    assert (await _call(env, method, path, body, {})).status_code == 401
    assert (await _call(env, method, path, body, {"Authorization": "Bearer nope"})).status_code == 401
    assert (await _call(env, method, path, body, {"Authorization": f"Bearer {_AGENT_KEY}"})).status_code == 401  # 取り違え


@pytest.mark.parametrize("method,path,body", _AGENT_CALLS)
async def test_agent_routes_reject_missing_wrong_and_admin_key(env, method, path, body):
    assert (await _call(env, method, path, body, {})).status_code == 401
    assert (await _call(env, method, path, body, {"Authorization": "Bearer nope"})).status_code == 401
    assert (await _call(env, method, path, body, {"Authorization": f"Bearer {_ADMIN_KEY}", "X-Case-Ticket": "t"})).status_code == 401


@pytest.mark.parametrize("method,path,body", _ADMIN_CALLS + _AGENT_CALLS)
async def test_empty_keys_reject_everyone(env, monkeypatch, method, path, body):
    monkeypatch.setenv("CASE_AGENT_TOKEN", "")
    monkeypatch.setenv("CASE_ADMIN_TOKEN", "")
    for key in ("", "x", _AGENT_KEY, _ADMIN_KEY):
        h = {"Authorization": f"Bearer {key}", "X-Case-Ticket": "t"} if key else {}
        assert (await _call(env, method, path, body, h)).status_code == 401


@pytest.mark.parametrize("method,path,body", _ADMIN_CALLS + _AGENT_CALLS)
async def test_identical_keys_reject_both_gates(env, monkeypatch, caplog, method, path, body):
    same = "same-key-" + uuid.uuid4().hex
    monkeypatch.setenv("CASE_AGENT_TOKEN", same)
    monkeypatch.setenv("CASE_ADMIN_TOKEN", same)
    with caplog.at_level(logging.ERROR):
        r = await _call(env, method, path, body, {"Authorization": f"Bearer {same}", "X-Case-Ticket": "t"})
    assert r.status_code == 401
    assert same not in caplog.text
    assert "keys identical" in caplog.text


# ---------------------------------------------------------------------------------------------------
# 件の札
# ---------------------------------------------------------------------------------------------------
async def test_ticket_unknown_incident_is_404_and_ticket_is_shown_once(env):
    r = await env.client.post(f"{_BASE}/{uuid.uuid4()}/ticket", headers=admin())
    assert r.status_code == 404
    iid, ticket = await env.new_case()
    stored = env.one("SELECT ticket_hash FROM ops_case.cases WHERE incident_id = %s", (iid,))
    assert stored == hashlib.sha256(ticket.encode()).hexdigest() and ticket not in stored
    exp = env.one("SELECT ticket_expires_at FROM ops_case.cases WHERE incident_id = %s", (iid,))
    delta = exp - datetime.now(timezone.utc)
    assert timedelta(hours=23) < delta <= timedelta(hours=24, seconds=5)


async def test_new_ticket_invalidates_previous(env):
    iid, ticket = await env.new_case()
    r = await env.client.post(f"{_BASE}/{iid}/ticket", headers=admin())
    ticket2 = r.json()["ticket"]
    assert ticket2 != ticket
    assert (await env.client.post(f"{_BASE}/{iid}/unmask-requests", json=_good_body(), headers=agent(ticket))).status_code == 403
    assert (await env.client.post(f"{_BASE}/{iid}/unmask-requests", json=_good_body(), headers=agent(ticket2))).status_code == 200


async def test_ticket_mismatch_other_case_expired_and_unknown_incident_are_403(env):
    iid, ticket = await env.new_case()
    other_iid, other_ticket = await env.new_case()
    body = {"status": "reported"}
    url = f"{_BASE}/{iid}/report"
    assert (await env.client.post(url, json=body, headers=agent())).status_code == 403  # 札なし
    assert (await env.client.post(url, json=body, headers=agent("wrong"))).status_code == 403
    assert (await env.client.post(url, json=body, headers=agent(other_ticket))).status_code == 403  # 別の件の札
    assert (await env.client.post(f"{_BASE}/{uuid.uuid4()}/report", json=body, headers=agent(ticket))).status_code == 403  # 件なし
    env.admin.cursor().execute("UPDATE ops_case.cases SET ticket_expires_at = now() - interval '1 second' WHERE incident_id = %s", (iid,))
    assert (await env.client.post(url, json=body, headers=agent(ticket))).status_code == 403  # 期限切れ
    assert env.one("SELECT count(*) FROM ops_case.reports WHERE incident_id = %s", (iid,)) == 0
    assert other_iid != iid


# ---------------------------------------------------------------------------------------------------
# 報告
# ---------------------------------------------------------------------------------------------------
async def test_report_once_then_409_and_oversize_413(env):
    iid, ticket = await env.new_case()
    url = f"{_BASE}/{iid}/report"
    body = {"status": "reported", "summary": "要約", "evidence": {"k": [1, 2]}, "proposal": {"a": "b"}}
    r = await env.client.post(url, json=body, headers=agent(ticket))
    assert r.status_code == 200, r.text
    assert (await env.client.post(url, json=body, headers=agent(ticket))).status_code == 409
    assert env.one("SELECT count(*) FROM ops_case.reports WHERE incident_id = %s", (iid,)) == 1
    iid2, ticket2 = await env.new_case()
    big = {"status": "reported", "summary": "a" * 4000, "cause": "b" * 4000, "evidence": ["c" * 1000] * 30}
    r = await env.client.post(f"{_BASE}/{iid2}/report", json=big, headers=agent(ticket2))
    assert r.status_code == 413
    assert env.one("SELECT count(*) FROM ops_case.reports WHERE incident_id = %s", (iid2,)) == 0
    bad = await env.client.post(f"{_BASE}/{iid2}/report", json={"status": "weird"}, headers=agent(ticket2))
    assert bad.status_code == 422 and "weird" not in bad.text


# ---------------------------------------------------------------------------------------------------
# 申請
# ---------------------------------------------------------------------------------------------------
async def test_request_accepted_dedupes_and_returns_only_id_and_status(env):
    iid, ticket = await env.new_case()
    r = await env.client.post(
        f"{_BASE}/{iid}/unmask-requests",
        json=_good_body(column_names=["memo", "memo", "email"], row_keys=["1"] * 21),  # 重複は 1 つに数える
        headers=agent(ticket),
    )
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"id", "status"} and r.json()["status"] == "pending"
    cols, keys, status = env.rows(
        "SELECT column_names, row_keys, status FROM ops_case.unmask_requests WHERE id = %s", (r.json()["id"],)
    )[0]
    assert cols == ["memo", "email"] and keys == ["1"] and status == "pending"


@pytest.mark.parametrize(
    "label,body",
    [
        ("reason19", _good_body(reason="あ" * 19)),
        ("columns6", _good_body(column_names=[f"c{i}" for i in range(6)])),
        ("rows21", _good_body(row_keys=[str(i) for i in range(21)])),
        ("excluded_column", _good_body(view_name="public__has_secret", column_names=["api_token"])),
        ("table_with_secret_column", _good_body(view_name="public__has_secret", column_names=["memo"])),
        ("deny_table", _good_body(view_name="tenant_001__viewer_accounts", column_names=["note"])),
        ("two_pk", _good_body(view_name="public__two_pk", column_names=["memo"])),
        ("no_such_column", _good_body(column_names=["nope"])),
        ("no_such_view", _good_body(view_name="public__nope")),
        ("uuid_abc", _good_body(view_name="tenant_001__leads", column_names=["customer_name"], row_keys=["abc"])),
        ("uuid_upper", _good_body(view_name="tenant_001__leads", column_names=["customer_name"], row_keys=["11111111-1111-1111-1111-11111111111A"])),
        ("int_1x", _good_body(row_keys=["1x"])),
        ("int_overflow", _good_body(row_keys=["2147483648"])),
        ("smallint_overflow", _good_body(view_name="public__small_pk", column_names=["memo"], row_keys=["40000"])),
        ("bigint_digits", _good_body(row_keys=["1" * 20])),
    ],
)
async def test_request_validation_returns_422_without_creating_a_row(env, label, body):
    iid, ticket = await env.new_case()
    r = await env.client.post(f"{_BASE}/{iid}/unmask-requests", json=body, headers=agent(ticket))
    assert r.status_code == 422, f"{label}: {r.status_code} {r.text}"
    assert env.one("SELECT count(*) FROM ops_case.unmask_requests WHERE incident_id = %s", (iid,)) == 0
    for secret in ("1x", "abc", "api_token", "2147483648"):
        if secret in str(body):
            assert secret not in r.text or label in ("excluded_column",), f"{label}: 入力がそのまま返った"


async def test_valid_boundaries_are_accepted(env):
    iid, ticket = await env.new_case()
    ok = await env.client.post(
        f"{_BASE}/{iid}/unmask-requests",
        json=_good_body(view_name="public__small_pk", column_names=["memo"], row_keys=["32767", "-32768"]),
        headers=agent(ticket),
    )
    assert ok.status_code == 200, ok.text


async def test_third_request_is_refused_with_auto_limit_row(env):
    iid, ticket = await env.new_case()
    url = f"{_BASE}/{iid}/unmask-requests"
    assert (await env.client.post(url, json=_good_body(), headers=agent(ticket))).status_code == 200
    assert (await env.client.post(url, json=_good_body(row_keys=["2"]), headers=agent(ticket))).status_code == 200
    r = await env.client.post(url, json=_good_body(row_keys=["3"]), headers=agent(ticket))
    assert r.status_code == 409
    row = env.rows(
        "SELECT status, decided_by, decision_reason FROM ops_case.unmask_requests WHERE incident_id = %s"
        " AND decided_by = 'auto:limit'",
        (iid,),
    )
    assert row == [("denied", "auto:limit", "limit")]
    # 4 本目も 409。自動で断った行は増えない（24 時間に 1 行）
    assert (await env.client.post(url, json=_good_body(row_keys=["4"]), headers=agent(ticket))).status_code == 409
    assert env.one("SELECT count(*) FROM ops_case.unmask_requests WHERE incident_id = %s AND decided_by = 'auto:limit'", (iid,)) == 1
    pend = (await env.client.get(f"{_BASE}/pending", headers=admin())).json()
    assert iid in {x["incident_id"] for x in pend["auto_denied"]}


async def test_get_request_only_for_its_own_case(env):
    iid, ticket = await env.new_case()
    _other_iid, other_ticket = await env.new_case()
    rid = (await env.client.post(f"{_BASE}/{iid}/unmask-requests", json=_good_body(), headers=agent(ticket))).json()["id"]
    r = await env.client.get(f"{_BASE}/unmask-requests/{rid}", headers=agent(ticket))
    assert r.status_code == 200
    assert set(r.json()) == {"id", "status", "expires_at", "read_count", "decision_reason"}
    assert r.json()["status"] == "pending" and r.json()["read_count"] == 0
    assert (await env.client.get(f"{_BASE}/unmask-requests/{rid}", headers=agent(other_ticket))).status_code == 403
    assert (await env.client.get(f"{_BASE}/unmask-requests/{rid}", headers=agent())).status_code == 403
    assert (await env.client.get(f"{_BASE}/unmask-requests/{uuid.uuid4()}", headers=agent(ticket))).status_code == 403


# ---------------------------------------------------------------------------------------------------
# 判断・点検
# ---------------------------------------------------------------------------------------------------
async def _pending_request(env):
    iid, ticket = await env.new_case()
    rid = (await env.client.post(f"{_BASE}/{iid}/unmask-requests", json=_good_body(), headers=agent(ticket))).json()["id"]
    return iid, ticket, rid


async def test_decision_approved_sets_expiry_from_backend_time(env):
    _iid, ticket, rid = await _pending_request(env)
    pend = (await env.client.get(f"{_BASE}/pending", headers=admin())).json()["pending"]
    mine = [p for p in pend if p["id"] == rid][0]
    assert mine["row_count"] == 1 and mine["column_names"] == ["memo"] and "row_keys" not in mine
    before = datetime.now(timezone.utc)
    r = await env.client.post(
        f"{_BASE}/unmask-requests/{rid}/decision", json={"decision": "approved", "reason": "確かめた", "minutes": 5}, headers=admin()
    )
    after = datetime.now(timezone.utc)
    assert r.status_code == 200, r.text
    status, decided_by, minutes, expires = env.rows(
        "SELECT status, decided_by, approved_minutes, expires_at FROM ops_case.unmask_requests WHERE id = %s", (rid,)
    )[0]
    assert (status, decided_by, minutes) == ("approved", "agent-console", 5)
    assert before + timedelta(minutes=5) - timedelta(seconds=2) <= expires <= after + timedelta(minutes=5) + timedelta(seconds=2)
    # 2 回目は 409
    again = await env.client.post(
        f"{_BASE}/unmask-requests/{rid}/decision", json={"decision": "denied", "reason": "x"}, headers=admin()
    )
    assert again.status_code == 409
    got = await env.client.get(f"{_BASE}/unmask-requests/{rid}", headers=agent(ticket))
    assert got.json()["status"] == "approved"


async def test_decision_validation(env):
    _iid, _t, rid = await _pending_request(env)
    url = f"{_BASE}/unmask-requests/{rid}/decision"
    assert (await env.client.post(url, json={"decision": "approved", "reason": "x", "minutes": 16}, headers=admin())).status_code == 422
    assert (await env.client.post(url, json={"decision": "approved", "reason": "x", "minutes": 0}, headers=admin())).status_code == 422
    assert (await env.client.post(url, json={"decision": "approved", "reason": "x"}, headers=admin())).status_code == 422
    assert (await env.client.post(url, json={"decision": "denied", "reason": "x", "minutes": 3}, headers=admin())).status_code == 422
    assert (await env.client.post(url, json={"decision": "maybe", "reason": "x"}, headers=admin())).status_code == 422
    assert (await env.client.post(url, json={"decision": "denied", "reason": ""}, headers=admin())).status_code == 422
    assert env.one("SELECT status FROM ops_case.unmask_requests WHERE id = %s", (rid,)) == "pending"
    nf = await env.client.post(
        f"{_BASE}/unmask-requests/{uuid.uuid4()}/decision", json={"decision": "denied", "reason": "x"}, headers=admin()
    )
    assert nf.status_code == 404
    ok = await env.client.post(url, json={"decision": "denied", "reason": "不要"}, headers=admin())
    assert ok.status_code == 200
    assert env.rows("SELECT status, expires_at FROM ops_case.unmask_requests WHERE id = %s", (rid,)) == [("denied", None)]


async def test_audits_and_audit_inputs(env):
    r = await env.client.post(f"{_BASE}/audits", json={"findings": [{"k": "v"}, {"k": "w"}]}, headers=admin())
    assert r.status_code == 200 and r.json()["finding_count"] == 2
    assert env.one("SELECT finding_count FROM ops_case.audits WHERE id = %s", (r.json()["id"],)) == 2
    big = await env.client.post(f"{_BASE}/audits", json={"findings": ["x" * 1000] * 70}, headers=admin())
    assert big.status_code == 413
    assert (await env.client.post(f"{_BASE}/audits", json={"nope": 1}, headers=admin())).status_code == 422
    await _pending_request(env)
    inputs = await env.client.get(f"{_BASE}/audit-inputs", headers=admin())
    assert inputs.status_code == 200, inputs.text
    data = inputs.json()
    assert data["days"] == 7 and data["requests_by_status"].get("pending", 0) >= 1
    assert set(data["build_log"]) == {"ok", "failed", "latest"}
    assert (await env.client.get(f"{_BASE}/audit-inputs?days=0", headers=admin())).status_code == 422


# ---------------------------------------------------------------------------------------------------
# DB の失敗
# ---------------------------------------------------------------------------------------------------
async def test_db_failure_returns_503_without_details(env, monkeypatch, caplog):
    from sqlalchemy.exc import OperationalError

    iid, ticket = await env.new_case()

    async def boom(*_a, **_k):
        raise OperationalError("SELECT secret_table", {"v": "secret-value"}, Exception("secret-detail 12345"))

    with monkeypatch.context() as m, caplog.at_level(logging.DEBUG):
        m.setattr("app.routers.ops_case._check_request_content", boom)
        r = await env.client.post(f"{_BASE}/{iid}/unmask-requests", json=_good_body(), headers=agent(ticket))
    assert r.status_code == 503
    assert r.json() == {"detail": "OPS_CASE_UNAVAILABLE"}
    for leak in ("secret_table", "secret-value", "secret-detail", ticket, _AGENT_KEY, "障害の調べ"):
        assert leak not in r.text and leak not in caplog.text, f"{leak!r} が漏れた"
    assert "ops_case unmask_request db_error sqlstate=" in caplog.text
    # 次の要求は普通に通る（接続に運用者の旗が残らない）
    ok = await env.client.post(f"{_BASE}/{iid}/unmask-requests", json=_good_body(), headers=agent(ticket))
    assert ok.status_code == 200


async def test_db_failure_in_ticket_check_returns_503(env, monkeypatch):
    from sqlalchemy.exc import OperationalError

    iid, ticket = await env.new_case()

    async def boom(*_a, **_k):
        raise OperationalError("SELECT x", {}, Exception("detail"))

    monkeypatch.setattr("app.routers.ops_case._verify_ticket", boom)
    r = await env.client.post(f"{_BASE}/{iid}/report", json={"status": "reported"}, headers=agent(ticket))
    assert r.status_code == 503 and r.json() == {"detail": "OPS_CASE_UNAVAILABLE"}
