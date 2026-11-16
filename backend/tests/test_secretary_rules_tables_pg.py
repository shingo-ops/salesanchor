"""秘書の決まり帳の2表と使いみち secretary_regression の DB の試験（ADR-1077 便1。design.md §4・§6 の①）。

PG（CI の使い捨て DB。pg fixture。書き込みはアプリの役割 salesanchor_app）: 列の名前・RLS の 4 マス・運営の文脈・
文脈なし・DELETE の権限なし・CHECK・使いみちの CHECK。表は本物の migration を流して作る。
テストデータはすべて架空。使い捨ての DB は試験の後に fixture が DB ごと消す。
"""

from __future__ import annotations

import os

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

needs_ci_pg = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true" or not os.getenv("RLS_TEST_DATABASE_URL"),
    reason="Disposable CI PostgreSQL service and app role required",
)

NEW_MIGRATION = "20261113_100000_create_secretary_rules.sql"

RULES_COLUMNS = {
    "id", "tenant_id", "status", "rule_text", "source_text", "source_kind", "source_reply",
    "created_by", "decided_by", "created_at", "decided_at",
}  # fmt: skip
CHECKS_COLUMNS = {
    "id", "tenant_id", "started_by", "sdk", "model", "rules_count", "status", "ok", "ng", "unmeasured",
    "total", "started_at", "progress_at", "finished_at",
}  # fmt: skip
PURPOSES = (
    "line_extraction", "line_extraction_shadow", "inventory_parse_fallback", "translation_inbound",
    "translation_inbound_escalation", "translation_outbound", "secretary_intent", "secretary_regression",
)  # fmt: skip

INSERT_RULE = (
    "INSERT INTO public.secretary_rules (tenant_id, status, rule_text, created_by, decided_at) "
    "VALUES (%s, %s, %s, %s, %s)"
)
INSERT_CHECK = (
    "INSERT INTO public.secretary_rule_checks (tenant_id, sdk, model, rules_count, total) "
    "VALUES (%s, 'sdk-x', 'model-x', 0, 1)"
)


def _app_conn(conn):
    """アプリの役割 salesanchor_app で同じ使い捨て DB へつなぐ。"""
    app_url = make_url(os.environ["RLS_TEST_DATABASE_URL"]).set(database=conn.info.dbname)
    return psycopg2.connect(
        dbname=app_url.database, host=app_url.host, port=app_url.port,
        user=app_url.username, password=app_url.password,
    )  # fmt: skip


def _setup(conn):
    """管理者の接続で、新しい migration を 2 回流し（冪等）、会社 999・998 と利用者を各社 1 人ずつ用意する。"""
    cur = conn.cursor()
    sql_text = (MIGRATIONS / NEW_MIGRATION).read_text()
    cur.execute(sql_text)
    cur.execute(sql_text)
    cur.execute(
        "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name) "
        "VALUES (998, 'tenant_998', 'Test Tenant B', 'Test Tenant B') ON CONFLICT (id) DO NOTHING"
    )
    cur.execute(
        "INSERT INTO public.users (id, tenant_id, username, email, full_name, role) "
        "VALUES (998, 998, 'testuser998', 'test998@example.com', 'Test User B', 'admin') ON CONFLICT (id) DO NOTHING"
    )
    return cur


def _seed(cur):
    """管理者（RLS を通らない）で、2 社 × 2 状態（approved・candidate）の決まりと、1 社 1 行の試しを入れる。"""
    for tenant_id in (999, 998):
        cur.execute(INSERT_RULE, (tenant_id, "approved", "fake rule", tenant_id, "2026-11-12T00:00:00Z"))
        cur.execute(INSERT_RULE, (tenant_id, "candidate", "fake candidate", tenant_id, None))
        cur.execute(INSERT_CHECK, (tenant_id,))


def _ctx(acur, *, tenant=None, operator=False):
    if tenant is not None:
        acur.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant),))
    if operator:
        acur.execute("SELECT set_config('app.is_operator', 'true', true)")


def _count(acur, table, where="true"):
    acur.execute(f"SELECT count(*) FROM public.{table} WHERE {where}")
    return acur.fetchone()[0]


def _columns(cur, table):
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return {r[0] for r in cur.fetchall()}


@needs_ci_pg
def test_tables_and_columns_match_design(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    assert _columns(cur, "secretary_rules") == RULES_COLUMNS
    assert len(RULES_COLUMNS) == 11
    assert _columns(cur, "secretary_rule_checks") == CHECKS_COLUMNS
    assert len(CHECKS_COLUMNS) == 14


@needs_ci_pg
def test_rls_four_cells(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    app_conn = _app_conn(conn)
    try:
        acur = app_conn.cursor()
        acur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        assert acur.fetchone() == (False, False)
        app_conn.rollback()

        _ctx(acur, tenant=999)
        assert _count(acur, "secretary_rules") == 2
        assert _count(acur, "secretary_rules", "tenant_id = 998") == 0
        assert _count(acur, "secretary_rule_checks") == 1
        assert _count(acur, "secretary_rule_checks", "tenant_id = 998") == 0
        acur.execute("UPDATE public.secretary_rules SET rule_text = 'x' WHERE tenant_id = 998")
        assert acur.rowcount == 0
        acur.execute("UPDATE public.secretary_rule_checks SET ok = 0 WHERE tenant_id = 998")
        assert acur.rowcount == 0
        acur.execute("UPDATE public.secretary_rules SET rule_text = 'y' WHERE tenant_id = 999")
        assert acur.rowcount == 2
        app_conn.rollback()

        _ctx(acur, tenant=999)
        with pytest.raises(psycopg2.Error) as exc_info:
            acur.execute(INSERT_RULE, (998, "candidate", "x", 998, None))
        assert exc_info.value.pgcode == "42501"
        app_conn.rollback()

        _ctx(acur, tenant=999)
        with pytest.raises(psycopg2.Error) as exc_info:
            acur.execute(INSERT_CHECK, (998,))
        assert exc_info.value.pgcode == "42501"
        app_conn.rollback()

        _ctx(acur, tenant=999)
        acur.execute(INSERT_RULE, (999, "candidate", "own", 999, None))
        assert acur.rowcount == 1
        acur.execute(INSERT_CHECK, (999,))
        assert acur.rowcount == 1
        app_conn.rollback()
    finally:
        app_conn.close()


@needs_ci_pg
def test_operator_context_reads_all(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    app_conn = _app_conn(conn)
    try:
        acur = app_conn.cursor()
        _ctx(acur, operator=True)
        assert _count(acur, "secretary_rules") == 4
        assert _count(acur, "secretary_rule_checks") == 2
        app_conn.rollback()
    finally:
        app_conn.close()


@needs_ci_pg
def test_no_context_sees_nothing(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    app_conn = _app_conn(conn)
    try:
        acur = app_conn.cursor()
        assert _count(acur, "secretary_rules") == 0
        assert _count(acur, "secretary_rule_checks") == 0
        app_conn.rollback()
        with pytest.raises(psycopg2.Error) as exc_info:
            acur.execute(INSERT_RULE, (999, "candidate", "x", 999, None))
        assert exc_info.value.pgcode == "42501"
        app_conn.rollback()
        with pytest.raises(psycopg2.Error) as exc_info:
            acur.execute(INSERT_CHECK, (999,))
        assert exc_info.value.pgcode == "42501"
        app_conn.rollback()
    finally:
        app_conn.close()


@needs_ci_pg
def test_app_role_cannot_delete(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    _seed(cur)
    app_conn = _app_conn(conn)
    try:
        acur = app_conn.cursor()
        for table in ("secretary_rules", "secretary_rule_checks"):
            _ctx(acur, tenant=999)
            with pytest.raises(psycopg2.Error) as exc_info:
                acur.execute(f"DELETE FROM public.{table} WHERE tenant_id = 999")
            assert exc_info.value.pgcode == "42501", table
            app_conn.rollback()
    finally:
        app_conn.close()


@needs_ci_pg
def test_checks(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    ts = "2026-11-12T00:00:00Z"
    bad_rules = [
        ("status other", (999, "other", "x", 999, ts)),
        ("approved blank text", (999, "approved", "   ", 999, ts)),
        ("rule_text 151 chars", (999, "candidate", "a" * 151, 999, None)),
        ("candidate with decided_at", (999, "candidate", "x", 999, ts)),
        ("approved without decided_at", (999, "approved", "x", 999, None)),
    ]
    for label, params in bad_rules:
        with pytest.raises(psycopg2.Error) as exc_info:
            cur.execute(INSERT_RULE, params)
        assert exc_info.value.pgcode == "23514", label
    with pytest.raises(psycopg2.Error) as exc_info:
        cur.execute(
            "INSERT INTO public.secretary_rules (tenant_id, status, rule_text, created_by, source_kind) "
            "VALUES (999, 'candidate', 'x', 999, 'other')"
        )
    assert exc_info.value.pgcode == "23514", "source_kind other"
    with pytest.raises(psycopg2.Error) as exc_info:
        cur.execute(
            "INSERT INTO public.secretary_rule_checks (tenant_id, sdk, model, rules_count, total, ok, ng, unmeasured) "
            "VALUES (999, 'sdk-x', 'model-x', 0, 1, 1, 1, 0)"
        )
    assert exc_info.value.pgcode == "23514", "counts over total"
    with pytest.raises(psycopg2.Error) as exc_info:
        cur.execute(
            "INSERT INTO public.secretary_rule_checks (tenant_id, sdk, model, rules_count, total, status) "
            "VALUES (999, 'sdk-x', 'model-x', 0, 1, 'done')"
        )
    assert exc_info.value.pgcode == "23514", "done without finished_at"


@needs_ci_pg
def test_purpose_check_has_secretary_regression(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _setup(conn)
    query = (
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = 'public.llm_usage_events'::regclass AND conname = 'llm_usage_events_purpose_check'"
    )
    cur.execute(query)
    first = cur.fetchone()[0]
    for purpose in PURPOSES:
        assert f"'{purpose}'" in first, purpose
    cur.execute((MIGRATIONS / NEW_MIGRATION).read_text())
    cur.execute(query)
    assert cur.fetchone()[0] == first
