"""ADR-1093 便2: ai_dev001_writer ロールの権限のテスト（実 PostgreSQL が必要）。

design.md §6 の K1・K2・K3(a)(b)(c)(d)・K4・K5 と、§3-2 の規則 E（public に何も付けずに外部キーのある表へ足せるか）・
規則 B の 6 表への INSERT を、使い捨て DB で確かめる。
順番は design §7 のとおり「backend/app/services/tenant.py のテナント作成で tenant_001・tenant_004 を作る →
この migration を流す → SET ROLE ai_dev001_writer で K の文を流す」。
期待する数は migration の SQL を写さず、pg_catalog と DENY_COLUMN_RE（Python）から別に数える。
測った生の値は -s で標準出力に出る（docs/handoff/dev-tenant001-writer/bin2-measure.md に写した）。
ロールはクラスタ共通。別の係が使っている途中で消すと落ちるため、試験では消さない（権限は使い捨て DB と一緒に消える）。
パスワードは設定しない（SET ROLE で確かめる。ログインはしない）。
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from app.ops.readonly_query import DENY_COLUMN_RE
from tests.rls_bootstrap import bootstrap_tenant_schema

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_MIGRATION = Path(__file__).resolve().parents[3] / "migrations" / "20261130_100000_create_ai_dev001_writer_role.sql"
_ROLE = "ai_dev001_writer"
_PREFIX = "SET LOCAL app.tenant_id = '1'; SET LOCAL search_path = tenant_001, public; "


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


def _asyncpg_url(url: str, dbname: str) -> str:
    return _psycopg_url(url, dbname).replace("postgresql://", "postgresql+asyncpg://", 1)


@pytest.fixture(scope="module")
def pg():
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    cur = control.cursor()
    name = "dev001w_" + uuid.uuid4().hex[:12]
    cur.execute(f'CREATE DATABASE "{name}"')
    conn = None
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        async def _bootstrap():
            eng = create_async_engine(_asyncpg_url(ADMIN_PG_URL, name))
            try:
                await bootstrap_tenant_schema(eng, 1)
                await bootstrap_tenant_schema(eng, 4)
            finally:
                await eng.dispose()

        asyncio.run(_bootstrap())
        conn = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
        conn.autocommit = True
        conn.cursor().execute(_MIGRATION.read_text("utf-8"))
        yield conn
    finally:
        if conn is not None:
            conn.close()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        control.close()


def _fetch(conn, sql, params=None):
    c = conn.cursor()
    c.execute(sql, params)
    return c.fetchall()


def _as_writer(conn, statements):
    """ai_dev001_writer として、台本と同じ 2 文を入れた transaction で statements を順に流す。必ず rollback。
    成功なら None、DB エラーなら sqlstate を返す（最初のエラーで止める）。"""
    import psycopg2

    c = conn.cursor()
    c.execute("BEGIN")
    try:
        c.execute(f"SET LOCAL ROLE {_ROLE}")
        c.execute("SET LOCAL app.tenant_id = '1'")
        c.execute("SET LOCAL search_path = tenant_001, public")
        for sql in statements:
            c.execute(sql)
        return None
    except psycopg2.Error as e:
        return e.pgcode
    finally:
        c.execute("ROLLBACK")


def _secret_tables(conn, schema="tenant_001"):
    """秘密の列を持つ表 → その表の (秘密の列, 秘密でない列) を、Python の DENY_COLUMN_RE で別に数える。"""
    rows = _fetch(
        conn,
        "SELECT c.relname, a.attname FROM pg_class c JOIN pg_attribute a ON a.attrelid = c.oid"
        " WHERE c.relnamespace = %s::regnamespace AND c.relkind IN ('r','p') AND a.attnum > 0 AND NOT a.attisdropped"
        " ORDER BY c.relname, a.attnum",
        (schema,),
    )
    out: dict[str, tuple[list[str], list[str]]] = {}
    for table, col in rows:
        sec, safe = out.setdefault(table, ([], []))
        (sec if DENY_COLUMN_RE.search(col.lower()) else safe).append(col)
    return out


def _acl_rows(conn, where_extra="", kind="relacl"):
    """ai_dev001_writer が相手の権限の行を aclexplode で数える（grantor ごとに行が出る）。"""
    return _fetch(
        conn,
        {
            "relacl": "SELECT n.nspname, c.relname, c.relkind, x.privilege_type FROM pg_class c"
            " JOIN pg_namespace n ON n.oid = c.relnamespace, aclexplode(c.relacl) x",
            "attacl": "SELECT n.nspname, c.relname, a.attname, x.privilege_type FROM pg_attribute a"
            " JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace,"
            " aclexplode(a.attacl) x",
            "nspacl": "SELECT n.nspname, x.privilege_type FROM pg_namespace n, aclexplode(n.nspacl) x",
        }[kind]
        + f" WHERE x.grantee = '{_ROLE}'::regrole {where_extra}",
    )


# ---------------------------------------------------------------- 準備の確認


def test_role_attributes_and_settings(pg):
    attrs = _fetch(
        pg,
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolconnlimit, rolconfig"
        " FROM pg_roles WHERE rolname = %s",
        (_ROLE,),
    )[0]
    assert attrs[:7] == (True, False, False, False, False, False, 2)
    assert sorted(attrs[7]) == sorted(
        [
            "log_statement=all",
            "statement_timeout=60s",
            "lock_timeout=1s",
            "idle_in_transaction_session_timeout=60s",
        ]
    )
    # 合言葉は入れない
    assert _fetch(pg, "SELECT rolpassword FROM pg_authid WHERE rolname = %s", (_ROLE,)) == [(None,)]


# ---------------------------------------------------------------- K1


def test_k1_insert_update_delete_in_tenant_001(pg):
    lead_ins = "INSERT INTO leads (customer_name) VALUES ('dev001-k1') RETURNING id"
    assert _as_writer(pg, [lead_ins]) is None, "leads に INSERT できない（必須列は別に調べる）"
    assert (
        _as_writer(
            pg,
            [
                lead_ins,
                "UPDATE leads SET customer_name = 'dev001-k1-b' WHERE customer_name = 'dev001-k1'",
                "DELETE FROM leads WHERE customer_name = 'dev001-k1-b'",
            ],
        )
        is None
    )


# ---------------------------------------------------------------- K2


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO tenant_004.leads (customer_name) VALUES ('x')",
        "UPDATE tenant_004.leads SET customer_name = 'x'",
        "DELETE FROM tenant_004.leads",
    ],
)
def test_k2_tenant_004_is_refused_by_db(pg, sql):
    assert _as_writer(pg, [sql]) == "42501"


# ---------------------------------------------------------------- K3


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO public.tenants (id, tenant_code) VALUES (9999, 'x')",
        "UPDATE public.tenants SET tenant_name = 'x'",
        "DELETE FROM public.tenants",
        "INSERT INTO tenant_001.tenant_meta_config (tenant_id) VALUES (1)",
        "UPDATE tenant_001.tenant_meta_config SET tenant_id = 1",
        "DELETE FROM tenant_001.tenant_meta_config",
    ],
)
def test_k3a_public_and_meta_config_are_refused(pg, sql):
    assert _as_writer(pg, [sql]) == "42501"


def test_k3b_secret_column_cannot_be_written_or_returned(pg):
    assert _as_writer(pg, ["UPDATE staff SET avatar_token = 'x'"]) == "42501"
    assert _as_writer(pg, ["DELETE FROM staff RETURNING *"]) == "42501"


def test_k3c_cannot_create_in_public_or_database(pg):
    assert _fetch(pg, "SELECT has_schema_privilege(%s, 'public', 'CREATE')", (_ROLE,)) == [(False,)]
    assert _fetch(pg, "SELECT has_database_privilege(%s, current_database(), 'CREATE')", (_ROLE,)) == [(False,)]
    assert _fetch(pg, "SELECT has_schema_privilege(%s, 'tenant_001', 'CREATE')", (_ROLE,)) == [(False,)]


def test_k3d_no_security_definer_function_executable_except_triggers(pg):
    rows = _fetch(
        pg,
        "SELECT p.oid::regprocedure::text FROM pg_proc p WHERE p.prosecdef AND p.prorettype <> 'trigger'::regtype"
        " AND has_function_privilege(%s, p.oid, 'EXECUTE')",
        (_ROLE,),
    )
    print("K3d executable SECURITY DEFINER non-trigger functions:", rows)
    assert rows == []


# ---------------------------------------------------------------- 規則 E・K4


def test_rule_e_and_k4_public_fk_table_accepts_a_row_with_zero_public_privileges(pg):
    """public に何も付けないまま、public を参照する外部キーを持つ表（companies.status → public.customer_statuses）に 1 行足せる。"""
    stmts = [
        "INSERT INTO leads (customer_name) VALUES ('dev001-k4')",
        "INSERT INTO companies (company_code, lead_id, name, status)"
        " SELECT 'DEV001-K4', id, 'dev001-k4', 'active' FROM leads WHERE customer_name = 'dev001-k4'",
    ]
    result = _as_writer(pg, stmts)
    print("RULE_E companies INSERT (public FK, public privileges 0) ->", result or "OK")
    assert result is None
    kinds = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
    granted = 0
    for k in kinds:
        n = _fetch(
            pg,
            "SELECT count(*) FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r','p')"
            f" AND has_table_privilege(%s, c.oid, '{k}')",
            (_ROLE,),
        )[0][0]
        print(f"K4 public tables where {k} is true:", n)
        granted += n
    assert granted == 0
    assert _fetch(pg, "SELECT has_schema_privilege(%s, 'public', 'USAGE')", (_ROLE,)) == [
        (True,)
    ]  # PUBLIC から受け継ぐ


def test_rule_b_secret_tables_insert_outcomes(pg):
    """規則 B の表それぞれに、秘密でない列だけで INSERT を試す。生の結果を出す。権限エラー（42501）は出ない。"""
    for table, (secret, safe) in sorted(_secret_tables(pg).items()):
        if not secret or table == "tenant_meta_config":
            continue
        cols = ", ".join(safe)
        defaults = ", ".join("DEFAULT" for _ in safe)
        result = _as_writer(pg, [f"INSERT INTO {table} ({cols}) VALUES ({defaults})"])
        print(f"RULE_B INSERT {table} (secret cols {secret}, safe cols {len(safe)}) ->", result or "OK")
        assert result != "42501"
        assert (
            _as_writer(
                pg, [f"INSERT INTO {table} ({', '.join(secret)}) VALUES ({', '.join('DEFAULT' for _ in secret)})"]
            )
            == "42501"
        )


# ---------------------------------------------------------------- K5


def test_k5_acl_counts_match_expected(pg):
    tables = _secret_tables(pg)
    meta = "tenant_meta_config"
    secret_tables = {t for t, (s, _) in tables.items() if s and t != meta}
    plain_tables = {t for t, (s, _) in tables.items() if not s and t != meta}
    safe_cols_total = sum(len(tables[t][1]) for t in secret_tables)
    seqs = _fetch(
        pg, "SELECT count(*) FROM pg_class WHERE relnamespace = 'tenant_001'::regnamespace AND relkind = 'S'"
    )[0][0]
    grantors = _fetch(
        pg,
        "SELECT DISTINCT x.grantor FROM pg_class c, aclexplode(c.relacl) x WHERE x.grantee = %s::regrole",
        (_ROLE,),
    )
    assert len(grantors) == 1

    # (i) スキーマ
    nsp = _acl_rows(pg, kind="nspacl")
    print("K5(i) nspacl rows:", nsp)
    assert nsp == [("tenant_001", "USAGE")]

    # (ii) 表（relkind r・p）
    rel = [r for r in _acl_rows(pg, "AND c.relkind IN ('r','p')") if r[0] == "tenant_001"]
    print(
        "K5(ii) relacl rows:",
        len(rel),
        "tables:",
        len({r[1] for r in rel}),
        "plain",
        len(plain_tables),
        "secret",
        len(secret_tables),
    )
    assert len(rel) == len(plain_tables) * 4 + len(secret_tables)
    assert len({r[1] for r in rel}) == len(plain_tables) + len(secret_tables)
    assert not any(r[1] == meta for r in rel)
    assert {r[3] for r in rel if r[1] in secret_tables} == {"DELETE"}

    # (iii) 列
    att = [r for r in _acl_rows(pg, "AND a.attnum > 0 AND NOT a.attisdropped", kind="attacl") if r[0] == "tenant_001"]
    print("K5(iii) attacl rows:", len(att), "safe cols:", safe_cols_total)
    assert len(att) == safe_cols_total * 3
    for table, (secret, _) in tables.items():
        for col in secret:
            assert not any(r[1] == table and r[2] == col for r in att)
    assert not any(r[1] == meta for r in att)

    # (iv) 連番
    seq = [r for r in _acl_rows(pg, "AND c.relkind = 'S'") if r[0] == "tenant_001"]
    print("K5(iv) sequences acl rows:", len(seq), "sequences:", seqs)
    assert len(seq) == seqs
    assert {r[3] for r in seq} == {"USAGE"}

    # (v) tenant_001 以外は 0 行
    assert [r for r in _acl_rows(pg) if r[0] != "tenant_001"] == []
    assert [r for r in _acl_rows(pg, "AND a.attnum > 0", kind="attacl") if r[0] != "tenant_001"] == []
    assert [r for r in _acl_rows(pg, kind="nspacl") if r[0] != "tenant_001"] == []


# ---------------------------------------------------------------- 冪等・規則 D・属性違いで止まる


def _acl_snapshot(pg):
    return (
        sorted(map(str, _acl_rows(pg)))
        + sorted(map(str, _acl_rows(pg, kind="attacl")))
        + sorted(map(str, _acl_rows(pg, kind="nspacl")))
    )


def test_migration_is_idempotent(pg):
    before = _acl_snapshot(pg)
    pg.cursor().execute(_MIGRATION.read_text("utf-8"))
    assert _acl_snapshot(pg) == before


def test_migration_skips_when_tenant_001_is_absent():
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    name = "dev001e_" + uuid.uuid4().hex[:12]
    control.cursor().execute(f'CREATE DATABASE "{name}"')
    try:
        conn = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
        conn.autocommit = True
        conn.cursor().execute(_MIGRATION.read_text("utf-8"))
        conn.close()
    finally:
        control.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        control.close()


def test_migration_stops_when_role_has_unexpected_attributes(pg):
    import psycopg2

    pg.cursor().execute(f"ALTER ROLE {_ROLE} CREATEDB")
    try:
        with pytest.raises(psycopg2.Error) as ei:
            pg.cursor().execute(_MIGRATION.read_text("utf-8"))
        assert "unexpected attributes" in str(ei.value)
    finally:
        pg.cursor().execute(f"ALTER ROLE {_ROLE} NOCREATEDB")
