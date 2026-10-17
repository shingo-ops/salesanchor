"""ADR-1024 便3a: ai_ro ビュー生成と ai_reader の権限のテスト（実 PostgreSQL が必要）。

使い捨て DB を作り、migration 2 本（ai_reader ロール・ai_ro ビュー）を本物のファイルで適用して確かめる。
K6（秘密列が 0 本・public.users は直接読めない）/ K8（全スキーマの代表ビュー・行制限の扱い）/
K9（新しい表はビュー生成前は読めない）。
ai_reader はクラスタ共通のロールなので、このテストが作った場合だけ最後に消す。
パスワードは設定しない（SET ROLE で確かめる。ログインはしない）。
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
_ROLE_SQL = "20261017_130000_create_ai_reader_role.sql"
_VIEWS_SQL = "20261017_130100_create_ai_ro_views.sql"
_DENY_RE = re.compile(r"^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential")
_LEADS_COLUMNS = (
    "id",
    "name",
    "access_token",
    "api_key_encrypted",
    "client_secret",
    "private_key_pem",
    "credentials_json",
    "hash_value",
    "note",
)
_TENANTS = ("tenant_001", "tenant_003", "tenant_004", "tenant_005", "tenant_006")


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


def _make_table(cur, qualified_name, columns):
    """テスト用の空の表を作る。本番の表定義を写さず、列名と型だけから組み立てる
    （scripts/check_test_schema_dup.py は `CREATE TABLE ... AS` を複製とみなさない）。"""
    select_list = ", ".join(f"NULL::{typ} AS {name}" for name, typ in columns)
    cur.execute(f"CREATE TABLE {qualified_name} AS SELECT {select_list} WHERE false")


@pytest.fixture(scope="module")
def pg():
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    cur = control.cursor()
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ai_reader'")
    role_existed = cur.fetchone() is not None
    name = "ai_ro_" + uuid.uuid4().hex[:12]
    cur.execute(f'CREATE DATABASE "{name}"')
    conn = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
    conn.autocommit = True
    try:
        c = conn.cursor()
        _make_table(c, "public.users", [("id", "int"), ("email", "text"), ("password_hash", "text")])
        c.execute("INSERT INTO public.users VALUES (1, 'a@example.test', 'h')")
        _make_table(c, "public.only_secrets", [("password_hash", "text"), ("api_key", "text")])
        for i, t in enumerate(_TENANTS, start=1):
            c.execute(f"CREATE SCHEMA {t}")
            _make_table(
                c,
                f"{t}.leads",
                [(n, "int" if n == "id" else "text") for n in _LEADS_COLUMNS],
            )
            c.execute(f"INSERT INTO {t}.leads VALUES ({i}, 'n{i}', 't', 'k', 's', 'p', 'c', 'h', 'x')")
        # 行の制限(RLS)付きの表: ビューの持ち主の権限で制限が外れるか（recon U10）
        _make_table(c, "tenant_001.guarded", [("id", "int"), ("tenant_id", "int")])
        c.execute("INSERT INTO tenant_001.guarded VALUES (1, 1), (2, 2)")
        c.execute("ALTER TABLE tenant_001.guarded ENABLE ROW LEVEL SECURITY")
        c.execute("CREATE POLICY only_one ON tenant_001.guarded USING (tenant_id = 1)")
        for fname in (_ROLE_SQL, _VIEWS_SQL):
            c.execute((_MIGRATIONS_DIR / fname).read_text("utf-8"))
        yield conn
    finally:
        conn.close()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        if not role_existed:
            cur.execute("DROP ROLE IF EXISTS ai_reader")
        control.close()


def _rows(conn, sql, role=None):
    c = conn.cursor()
    try:
        if role:
            c.execute(f"SET ROLE {role}")
        c.execute(sql)
        return c.fetchall()
    finally:
        c.execute("RESET ROLE")


def test_no_denied_column_remains_in_ai_ro(pg):
    """K6: 拒否リストに当たる列が ai_ro に 0 本。"""
    names = [
        r[0]
        for r in _rows(
            pg,
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'ai_ro'"
            " UNION SELECT a.attname FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = 'ai_ro' AND a.attnum > 0 AND NOT a.attisdropped",
        )
    ]
    assert names, "ai_ro に列が 1 本も無い"
    assert [n for n in names if _DENY_RE.search(n.lower())] == []


def test_representative_view_for_public_and_every_tenant(pg):
    """K8: public と各テナントの代表が 1 本ずつある。表がすべて秘密列の表は作らない。"""
    views = {r[0] for r in _rows(pg, "SELECT viewname FROM pg_views WHERE schemaname = 'ai_ro'")}
    assert "public__users" in views
    for t in _TENANTS:
        assert f"{t}__leads" in views
    assert "public__only_secrets" not in views


def test_views_owned_by_executing_user_and_no_extra_grants(pg):
    owner = _rows(pg, "SELECT DISTINCT viewowner FROM pg_views WHERE schemaname = 'ai_ro'")
    me = _rows(pg, "SELECT current_user")[0][0]
    assert owner == [(me,)]
    attrs = _rows(
        pg,
        "SELECT rolsuper, rolbypassrls, rolcreatedb, rolcreaterole, rolreplication, rolconnlimit,"
        " rolpassword IS NULL FROM pg_authid WHERE rolname = 'ai_reader'",
    )
    assert attrs == [(False, False, False, False, False, 2, True)]
    assert _rows(pg, "SELECT pg_has_role('ai_reader', 'pg_read_all_data', 'MEMBER')") == [(False,)]


def test_ai_reader_cannot_read_public_users_directly(pg):
    """K6: public.users は直接読めない。ビュー経由は読める（秘密列なし）。"""
    import psycopg2

    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        _rows(pg, "SELECT * FROM public.users", role="ai_reader")
    rows = _rows(pg, "SELECT * FROM ai_ro.public__users", role="ai_reader")
    assert rows == [(1, "a@example.test")]


def test_view_owner_lifts_row_level_restriction(pg):
    """recon U10: ビューの持ち主の権限で行の制限が外れる（全行が見える）ことを実機で確認。"""
    rows = _rows(pg, "SELECT id FROM ai_ro.tenant_001__guarded ORDER BY id", role="ai_reader")
    assert rows == [(1,), (2,)]


def test_new_table_unreadable_until_views_are_rebuilt(pg):
    """K9: 新しい表はビュー生成の前は ai_reader で読めない。作り直すと読める。"""
    import psycopg2

    c = pg.cursor()
    _make_table(c, "tenant_003.brand_new", [("id", "int"), ("label", "text")])
    with pytest.raises(psycopg2.errors.UndefinedTable):
        _rows(pg, 'SELECT * FROM ai_ro."tenant_003__brand_new"', role="ai_reader")
    c.execute((_MIGRATIONS_DIR / _VIEWS_SQL).read_text("utf-8"))
    assert _rows(pg, 'SELECT * FROM ai_ro."tenant_003__brand_new"', role="ai_reader") == []


def test_ai_reader_role_migration_is_idempotent(pg):
    c = pg.cursor()
    c.execute((_MIGRATIONS_DIR / _ROLE_SQL).read_text("utf-8"))
    c.execute((_MIGRATIONS_DIR / _ROLE_SQL).read_text("utf-8"))
    cfg = _rows(
        pg,
        "SELECT unnest(rolconfig) FROM pg_db_role_setting s JOIN pg_roles r ON r.oid = s.setrole WHERE r.rolname = 'ai_reader' AND s.setdatabase = 0",
    )
    joined = " ".join(x[0] for x in cfg)
    assert "log_statement=all" in joined


def _rebuild_views(conn):
    c = conn.cursor()
    c.execute((_MIGRATIONS_DIR / _VIEWS_SQL).read_text("utf-8"))


def test_long_table_names_get_unique_short_views(pg):
    """F5: ビュー名が 63 バイトを超える 2 表（長い共通の先頭）も、別々の短い名前で両方作られる。"""
    long_prefix = "very_long_common_prefix_" + "x" * 24
    # 表名自体は 63 バイト以内、ビュー名（スキーマ名 + "__" + 表名）は 63 バイト超になる長さ
    t1, t2 = long_prefix + "_alpha", long_prefix + "_beta"
    c = pg.cursor()
    _make_table(c, f"tenant_004.{t1}", [("id", "int"), ("label", "text")])
    _make_table(c, f"tenant_004.{t2}", [("id", "int"), ("label", "text")])
    _rebuild_views(pg)
    names = [
        r[0]
        for r in _rows(
            pg, "SELECT viewname FROM pg_views WHERE schemaname = 'ai_ro' AND viewname LIKE 'tenant_004__very_long%'"
        )
    ]
    assert len(names) == 2 and len(set(names)) == 2
    assert all(len(n.encode("utf-8")) <= 63 for n in names)
    for n in names:
        assert _rows(pg, f'SELECT * FROM ai_ro."{n}"', role="ai_reader") == []
    # 63 バイト以下の名前は変わらない
    assert "tenant_004__leads" in {r[0] for r in _rows(pg, "SELECT viewname FROM pg_views WHERE schemaname = 'ai_ro'")}


def test_one_uncreatable_table_does_not_stop_other_views(pg):
    """F5: 名前が衝突して作れない表が 1 つあっても、他のビューは作られ、全体は成功する。"""
    c = pg.cursor()
    c.execute("CREATE SCHEMA tenant_009")
    c.execute("CREATE SCHEMA tenant_009__a")
    # どちらも ai_ro.tenant_009__a__b になる → 後から作る方が失敗する
    _make_table(c, "tenant_009.a__b", [("id", "int")])
    _make_table(c, "tenant_009__a.b", [("id", "int")])
    _make_table(c, "tenant_009.after_collision", [("id", "int")])
    _rebuild_views(pg)  # 例外にならない（COMMIT まで通る）
    views = {r[0] for r in _rows(pg, "SELECT viewname FROM pg_views WHERE schemaname = 'ai_ro'")}
    assert "tenant_009__a__b" in views
    assert "tenant_009__after_collision" in views
    assert "public__users" in views
    assert "tenant_001__leads" in views
    # ai_reader は作れた分を読める
    assert _rows(pg, "SELECT * FROM ai_ro.tenant_009__after_collision", role="ai_reader") == []
