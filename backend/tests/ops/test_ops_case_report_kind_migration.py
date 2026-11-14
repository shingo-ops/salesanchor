"""ADR-1012 段階4 便2a: 報告の種類（kind）の移行のテスト（実 PostgreSQL が必要）。

使い捨て DB を作り、本物の移行ファイルを流して確かめる（test_ops_case_db.py の作り方をまねる）。
- 新しいファイルを 2 回流しても失敗しない
- kind を書かずに入れた報告は investigation になる
- 同じ件に investigation の 2 通目は一意で断られる（古い一意でも新しい一意でも断られる）
- kind に決まりの外の値は断られる
- 出来事の表に kind case_report・actor case_agent の行が入る。決まりの外は断られる
- 2 つの決まりが VALID
- 古い一意（incident_id だけの一意）がまだ 1 つある
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from tests.conftest import (
    OPS_CASE_HAS_SECRET_DDL,
    OPS_CASE_PLAIN_DEMO_DDL,
    OPS_CASE_SMALL_PK_DDL,
    OPS_CASE_TENANT_LEADS_NO_EMAIL_DDL,
    OPS_CASE_TENANT_VIEWER_ACCOUNTS_DDL,
    OPS_CASE_TWO_PK_DDL,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
_INCIDENTS_SQL = "20261016_100000_create_ops_incident_tables.sql"
_CASE_SQL = "20261031_210000_create_ops_case.sql"
_KIND_SQL = "20261113_200000_add_ops_case_report_kind.sql"

_ROLES = ("ai_unmask", "ai_unmask_owner", "ai_reader_cloud", "ai_reader", "salesanchor_app", "aic_owner")


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


def _read(fname: str) -> str:
    return (_MIGRATIONS_DIR / fname).read_text("utf-8")


@pytest.fixture(scope="module")
def pg():
    """前提の移行（出来事の表・相談係の表）を流した使い捨て DB。クラスタ共通のロールは、この試験が作った場合だけ消す。"""
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    cc = control.cursor()
    existed = {}
    for r in _ROLES:
        cc.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (r,))
        existed[r] = cc.fetchone() is not None
    name = f"ops_case_kind_{uuid.uuid4().hex[:12]}"
    cc.execute(f'CREATE DATABASE "{name}"')
    conn = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
    conn.autocommit = True
    try:
        c = conn.cursor()
        c.execute("SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app'")
        if c.fetchone() is None:
            c.execute("CREATE ROLE salesanchor_app NOLOGIN NOSUPERUSER NOBYPASSRLS")
        c.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aic_owner'")
        if c.fetchone() is None:
            c.execute("CREATE ROLE aic_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
        c.execute(_read("20261017_130000_create_ai_reader_role.sql"))
        c.execute(_read("20261024_100100_create_ai_reader_cloud_role.sql"))
        c.execute(_read(_INCIDENTS_SQL))
        c.execute(f'GRANT CREATE ON DATABASE "{name}" TO aic_owner')
        c.execute("ALTER SCHEMA public OWNER TO aic_owner")
        c.execute("SET ROLE aic_owner")
        c.execute(OPS_CASE_PLAIN_DEMO_DDL)
        c.execute(OPS_CASE_SMALL_PK_DDL)
        c.execute(OPS_CASE_HAS_SECRET_DDL)
        c.execute(OPS_CASE_TWO_PK_DDL)
        c.execute("CREATE SCHEMA tenant_001")
        c.execute(OPS_CASE_TENANT_LEADS_NO_EMAIL_DDL)
        c.execute(OPS_CASE_TENANT_VIEWER_ACCOUNTS_DDL)
        c.execute(_read("20261024_100000_create_ai_cloud_meta.sql"))
        c.execute(_read("20261024_100300_create_ai_cloud_views.sql"))
        c.execute("RESET ROLE")
        c.execute(_read(_CASE_SQL))
        yield conn
    finally:
        conn.close()
        cc.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        for r in _ROLES:
            if not existed[r]:
                try:
                    cc.execute(f"DROP ROLE IF EXISTS {r}")
                except psycopg2.Error:
                    pass
        control.close()


@pytest.fixture(scope="module")
def migrated(pg):
    """新しい移行を 1 回目に流す（既存の行が無い表の上）。"""
    pg.cursor().execute(_read(_KIND_SQL))
    return pg


def _new_case(conn) -> str:
    c = conn.cursor()
    c.execute(
        "INSERT INTO public.ops_incidents (fingerprint, starts_at, alertname, status, first_notified_at,"
        " last_notified_at) VALUES (%s, now(), 'test', 'firing', now(), now()) RETURNING id",
        (uuid.uuid4().hex,),
    )
    iid = c.fetchone()[0]
    c.execute("INSERT INTO ops_case.cases (incident_id) VALUES (%s)", (iid,))
    return str(iid)


def test_migration_runs_twice(migrated):
    migrated.cursor().execute(_read(_KIND_SQL))
    migrated.cursor().execute(_read(_KIND_SQL))


def test_kind_defaults_to_investigation(migrated):
    iid = _new_case(migrated)
    c = migrated.cursor()
    c.execute("INSERT INTO ops_case.reports (incident_id, status) VALUES (%s, 'reported') RETURNING kind", (iid,))
    assert c.fetchone()[0] == "investigation"


def test_second_investigation_is_rejected(migrated):
    import psycopg2

    iid = _new_case(migrated)
    c = migrated.cursor()
    c.execute("INSERT INTO ops_case.reports (incident_id, status) VALUES (%s, 'reported')", (iid,))
    with pytest.raises(psycopg2.errors.UniqueViolation):
        c.execute("INSERT INTO ops_case.reports (incident_id, kind, status) VALUES (%s, 'investigation', 'reported')", (iid,))
    # 古い一意（incident_id だけ）でも、新しい一意（incident_id, kind）でも断られる
    c.execute("SELECT count(*) FROM ops_case.reports WHERE incident_id = %s", (iid,))
    assert c.fetchone()[0] == 1


def test_kind_outside_rule_is_rejected(migrated):
    import psycopg2

    iid = _new_case(migrated)
    c = migrated.cursor()
    with pytest.raises(psycopg2.errors.CheckViolation):
        c.execute("INSERT INTO ops_case.reports (incident_id, kind, status) VALUES (%s, 'other', 'reported')", (iid,))


def test_events_accept_case_report_and_reject_outside_values(migrated):
    import psycopg2

    iid = _new_case(migrated)
    c = migrated.cursor()
    c.execute(
        "INSERT INTO public.ops_incident_events (incident_id, kind, actor, detail)"
        " VALUES (%s, 'case_report', 'case_agent', '{\"report_id\": \"x\"}') RETURNING kind, actor",
        (iid,),
    )
    assert c.fetchone() == ("case_report", "case_agent")
    with pytest.raises(psycopg2.errors.CheckViolation):
        c.execute(
            "INSERT INTO public.ops_incident_events (incident_id, kind, actor) VALUES (%s, 'other', 'case_agent')",
            (iid,),
        )
    with pytest.raises(psycopg2.errors.CheckViolation):
        c.execute(
            "INSERT INTO public.ops_incident_events (incident_id, kind, actor) VALUES (%s, 'case_report', 'other')",
            (iid,),
        )


def test_event_constraints_are_valid(migrated):
    c = migrated.cursor()
    c.execute(
        "SELECT conname, convalidated FROM pg_constraint"
        " WHERE conrelid = 'public.ops_incident_events'::regclass"
        " AND conname IN ('ops_incident_events_kind_check', 'ops_incident_events_actor_check')"
    )
    rows = dict(c.fetchall())
    assert rows == {"ops_incident_events_kind_check": True, "ops_incident_events_actor_check": True}


def test_old_single_column_unique_still_exists(migrated):
    c = migrated.cursor()
    c.execute(
        "SELECT count(*) FROM pg_constraint con"
        " WHERE con.conrelid = 'ops_case.reports'::regclass AND con.contype = 'u'"
        " AND con.conkey = ARRAY[(SELECT a.attnum FROM pg_attribute a"
        "   WHERE a.attrelid = 'ops_case.reports'::regclass AND a.attname = 'incident_id')]::int2[]"
    )
    assert c.fetchone()[0] == 1
    c.execute(
        "SELECT count(*) FROM pg_constraint WHERE conrelid = 'ops_case.reports'::regclass"
        " AND conname = 'reports_incident_id_kind_key' AND contype = 'u'"
    )
    assert c.fetchone()[0] == 1
