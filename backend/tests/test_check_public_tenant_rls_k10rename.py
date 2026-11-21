"""ADR-1063 便5（K8）: public の tenant_id 付きで RLS の無い表を見つける点検の試験（実 PostgreSQL が必要）。

使い捨ての DB を作り、その中に見本の表を作って確かめる。終わったら DB ごと消す。
R1: tenant_id 付き・RLS なしの表は見つかり、許可一覧に無ければ 1（落ちる見本）。
R2: 同じ表に RLS を付けると見つからず 0（通る見本）。
R3: 許可一覧に理由付きで入っていれば 0。
R4: 許可一覧の理由が空なら 1。
R5: --report-only なら見つけても 0。
R6: tenant_id の無い表・public 以外の表は数えない。
"""

from __future__ import annotations

import importlib.util
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from tests.conftest import (
    RLS_PROBE_NO_TENANT_DDL,
    RLS_PROBE_OTHER_SCHEMA_DDL,
    RLS_PROBE_TABLE_DDL,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_public_tenant_rls.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("check_public_tenant_rls", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


@pytest.fixture()
def conn():
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    name = f"rls_check_{uuid.uuid4().hex[:12]}"
    control.cursor().execute(f'CREATE DATABASE "{name}"')
    c = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
    c.autocommit = True
    try:
        yield c
    finally:
        c.close()
        control.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        control.close()


def _exec(conn, sql: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql)


def test_r1_table_without_rls_fails(conn):
    mod = _load_script()
    _exec(conn, RLS_PROBE_TABLE_DDL)
    assert mod.find_tables_without_rls(conn) == ["ci_rls_probe"]
    assert mod.run(conn, {}, report_only=False) == 1


def test_r2_rls_enabled_passes(conn):
    mod = _load_script()
    _exec(conn, RLS_PROBE_TABLE_DDL)
    _exec(conn, "ALTER TABLE public.ci_rls_probe ENABLE ROW LEVEL SECURITY")
    assert mod.find_tables_without_rls(conn) == []
    assert mod.run(conn, {}, report_only=False) == 0


def test_r3_allowlisted_with_reason_passes(conn):
    mod = _load_script()
    _exec(conn, RLS_PROBE_TABLE_DDL)
    assert mod.run(conn, {"ci_rls_probe": "試験用の理由"}, report_only=False) == 0


def test_r4_blank_reason_fails(conn):
    mod = _load_script()
    assert mod.run(conn, {"ci_rls_probe": "   "}, report_only=False) == 1
    assert mod.run(conn, {"ci_rls_probe": ""}, report_only=True) == 1


def test_r5_report_only_does_not_fail(conn):
    mod = _load_script()
    _exec(conn, RLS_PROBE_TABLE_DDL)
    assert mod.run(conn, {}, report_only=True) == 0


def test_r6_only_public_tables_with_tenant_id(conn):
    mod = _load_script()
    _exec(conn, RLS_PROBE_NO_TENANT_DDL)
    _exec(conn, "CREATE SCHEMA ci_other")
    _exec(conn, RLS_PROBE_OTHER_SCHEMA_DDL)
    assert mod.find_tables_without_rls(conn) == []
