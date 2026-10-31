"""ADR-1052 段1: 相談係用の伏せたビュー ai_cloud のテスト（実 PostgreSQL が必要）。

使い捨て DB を作り、migration を本物のファイルで適用して確かめる。
T1・T1b: ai_reader_cloud で ai_cloud をいろいろな読み方で読んでも、伏せた列の元の値が出ない。
T10   : 分類表の見張り（CI）。分類の無い「そのまま」でない型の列・理由なしの allow を落とす。
T10b  : 属性違いの同名ロールがある状態でロールの migration を流すと止まる。
M8    : 権限（ai_reader_cloud は ai_cloud だけ。ai_reader は meta を読める。build_views はだれにも付けない）。
ai_reader / ai_reader_cloud はクラスタ共通のロールなので、このテストが作った場合だけ最後に消す。
パスワードは設定しない（SET ROLE で確かめる。ログインはしない）。
"""

from __future__ import annotations

import asyncio
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
_AI_READER_SQL = "20261017_130000_create_ai_reader_role.sql"
_META_SQL = "20261024_100000_create_ai_cloud_meta.sql"
_ROLE_SQL = "20261024_100100_create_ai_reader_cloud_role.sql"
_CREATE_SQL = "20261024_100300_create_ai_cloud_views.sql"
_DROP_SQL = "20261024_100200_drop_ai_cloud_views.sql"
_DENY_RE = re.compile(r"^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential")
_NAME_RE = re.compile(
    r"(name|email|mail|phone|tel|fax|addr|zip|postal|message|text|body|note|comment|memo|sender|display|contact"
    r"|line_id|wa_id|birthday|payload|snapshot|raw|data|values|identity|span)"
)
_COPY_RE = re.compile(r"(_bak_|_backup|baseline_)")
# そのまま出す型（pg_type.typname）。enum（typtype='e'）も含む
_PASS_TYPES = {
    "int2", "int4", "int8", "numeric", "float4", "float8", "bool", "date",
    "time", "timetz", "timestamp", "timestamptz", "interval", "uuid",
}  # fmt: skip

_RAW_EMAIL = "alice-very-secret@example.test"
_RAW_PHONE = "090-1234-5678"
_RAW_NOTE = "ひみつのメモ secret memo"
_RAW_ZIP = "123-4567"


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


def _read(fname: str) -> str:
    return (_MIGRATIONS_DIR / fname).read_text("utf-8")


def _make_table(cur, qualified_name, columns):
    """テスト用の空の表を作る（列名と型だけから組み立てる。本番の表定義は写さない）。"""
    select_list = ", ".join(f"NULL::{typ} AS {name}" for name, typ in columns)
    cur.execute(f"CREATE TABLE {qualified_name} AS SELECT {select_list} WHERE false")


class _Cluster:
    """クラスタ共通のロールを、このテストが作った場合だけ消すための記録。"""

    def __init__(self, control):
        self.control = control
        cur = control.cursor()
        self.existed = {}
        for r in ("ai_reader", "ai_reader_cloud", "aic_owner"):
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (r,))
            self.existed[r] = cur.fetchone() is not None

    def cleanup(self):
        cur = self.control.cursor()
        for r in ("ai_reader_cloud", "ai_reader", "aic_owner"):
            if not self.existed[r]:
                cur.execute(f"DROP ROLE IF EXISTS {r}")


def _new_db(control, prefix):
    import psycopg2

    name = f"{prefix}_{uuid.uuid4().hex[:12]}"
    cur = control.cursor()
    cur.execute(f'CREATE DATABASE "{name}"')
    conn = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, name))
    conn.autocommit = True
    return name, conn


@pytest.fixture(scope="module")
def cluster():
    import psycopg2

    control = psycopg2.connect(_psycopg_url(ADMIN_PG_URL))
    control.autocommit = True
    c = _Cluster(control)
    try:
        yield c
    finally:
        c.cleanup()
        control.close()


def _prepare_roles(conn):
    """ai_reader（既存の migration）と、表の持ち主になる非 superuser（RLS を越えることの確認用）を用意する。"""
    cur = conn.cursor()
    cur.execute(_read(_AI_READER_SQL))
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aic_owner'")
    if cur.fetchone() is None:
        cur.execute("CREATE ROLE aic_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
    cur.execute(_read(_ROLE_SQL))


@pytest.fixture(scope="module")
def pg(cluster):
    """小さな表の DB。持ち主は非 superuser の aic_owner。T1・T1b・M8 が使う。"""
    name, conn = _new_db(cluster.control, "ai_cloud")
    try:
        _prepare_roles(conn)
        c = conn.cursor()
        c.execute(f'GRANT CREATE ON DATABASE "{name}" TO aic_owner')
        c.execute("ALTER SCHEMA public OWNER TO aic_owner")
        c.execute("SET ROLE aic_owner")
        _make_table(
            c,
            "public.pii_demo",
            [
                ("id", "int"),
                ("email", "text"),
                ("phone_number", "text"),
                ("note", "varchar(40)"),
                ("tags", "text[]"),
                ("matrix", "int[][]"),
                ("payload", "jsonb"),
                ("payload_json", "json"),
                ("amount", "numeric"),
                ("born", "date"),
                ("raw_bytes", "bytea"),
                ("ip", "inet"),
                ("access_token", "text"),
            ],
        )
        c.execute(
            "INSERT INTO public.pii_demo (id, email, phone_number, note, tags, matrix, payload, payload_json,"
            " amount, born, raw_bytes, ip, access_token)"
            " VALUES (1, %s, %s, %s, ARRAY[%s, 'b'], ARRAY[[1,2],[3,4]], %s::jsonb, %s::json, 12.5,"
            " '2000-01-01', 'abc'::bytea, '10.0.0.1', 'tok-secret'),"
            " (2, NULL, '', NULL, NULL, NULL, 'null'::jsonb, NULL, NULL, NULL, NULL, NULL, NULL),"
            " (3, 'x', 'x', 'x', '{}', '{}', '[1,2]'::jsonb, '\"str\"'::json, 1, NULL, NULL, NULL, NULL),"
            " (4, 'x', 'x', 'x', '{}', '{}', '42'::jsonb, '7'::json, 1, NULL, NULL, NULL, NULL)",
            (_RAW_EMAIL, _RAW_PHONE, _RAW_NOTE, _RAW_EMAIL, '{"owner": "' + _RAW_EMAIL + '", "k": 2}', '{"a": 1}'),
        )
        # 分類表にある名前の表（suppliers.postal_code は mask_bare・default_language は allow）
        _make_table(
            c,
            "public.suppliers",
            [("id", "int"), ("name", "text"), ("postal_code", "text"), ("default_language", "text")],
        )
        c.execute("INSERT INTO public.suppliers VALUES (1, %s, %s, 'ja')", (_RAW_NOTE, _RAW_ZIP))
        # 全部が秘密列の表・写しの表・テナントの表（RLS つき）
        _make_table(c, "public.only_secrets", [("password_hash", "text"), ("api_key", "text")])
        _make_table(c, "public.pii_demo_backup_old", [("id", "int"), ("email", "text")])
        c.execute("CREATE SCHEMA ai_ro")  # 今の読む窓口のスキーマ（ai_reader_cloud が読めないことの確認用）
        c.execute("CREATE SCHEMA tenant_001")
        _make_table(c, "tenant_001.leads", [("id", "int"), ("customer_name", "text"), ("email", "text")])
        c.execute("INSERT INTO tenant_001.leads VALUES (1, %s, %s)", (_RAW_NOTE, _RAW_EMAIL))
        _make_table(c, "tenant_001.guarded", [("id", "int"), ("tenant_id", "int"), ("memo", "text")])
        c.execute("INSERT INTO tenant_001.guarded VALUES (1, 1, 'm1'), (2, 2, 'm2')")
        c.execute("ALTER TABLE tenant_001.guarded ENABLE ROW LEVEL SECURITY")
        c.execute("CREATE POLICY only_one ON tenant_001.guarded USING (tenant_id = 1)")
        c.execute("ANALYZE")
        c.execute("RESET ROLE")
        c.execute("SET ROLE aic_owner")
        c.execute(_read(_META_SQL))
        c.execute(_read(_CREATE_SQL))
        c.execute("RESET ROLE")
        yield conn
    finally:
        conn.close()
        cur = cluster.control.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def _rows(conn, sql, role=None, params=None):
    c = conn.cursor()
    try:
        if role:
            c.execute(f"SET ROLE {role}")
        c.execute(sql, params)
        return c.fetchall()
    finally:
        c.execute("RESET ROLE")


def _cloud(conn, sql, params=None):
    return _rows(conn, sql, role="ai_reader_cloud", params=params)


def _flat(rows):
    return repr(rows)


_RAW_VALUES = (_RAW_EMAIL, _RAW_PHONE, _RAW_NOTE, _RAW_ZIP, "tok-secret", "abc")


def _assert_no_raw(text_):
    for raw in _RAW_VALUES:
        assert raw not in text_, f"元の値が出た: {raw!r}"


def test_view_built_and_logged(pg):
    """ビューができ、build_log の最新が ok=t・failed_count=0。全部が秘密列の表と写しの表は作られない。"""
    views = {r[0] for r in _rows(pg, "SELECT viewname FROM pg_views WHERE schemaname = 'ai_cloud'")}
    assert {"public__pii_demo", "public__suppliers", "tenant_001__leads", "tenant_001__guarded"} <= views
    assert "public__only_secrets" not in views
    assert "public__pii_demo_backup_old" not in views
    ok, failed, n = _rows(
        pg, "SELECT ok, failed_count, view_count FROM ai_cloud_meta.build_log ORDER BY built_at DESC LIMIT 1"
    )[0]
    assert ok is True and failed == 0 and n == len(views)


def test_t1_masked_values_and_shapes(pg):
    """T1: 伏せた形（長さと種類だけ）。秘密列は列ごと無い。数や日付はそのまま。"""
    rows = _cloud(pg, "SELECT id, email, phone_number, tags, matrix, payload, payload_json FROM ai_cloud.public__pii_demo ORDER BY id")
    r1 = rows[0]
    assert r1[1] == f"masked:len={len(_RAW_EMAIL)}:ascii"
    assert r1[2] == f"masked:len={len(_RAW_PHONE)}:ascii"
    assert r1[3] == "masked:array:n=2"
    assert r1[4] == "masked:array:n=4"  # 多次元でも全要素の数
    jlen = [
        _rows(pg, f"SELECT char_length(payload::text) FROM public.pii_demo WHERE id = {i}", role="aic_owner")[0][0]
        for i in (1, 2, 3, 4)
    ]
    assert r1[5] == f"masked:json:len={jlen[0]}:keys=2"
    assert r1[6] == "masked:json:len=8:keys=1"
    # NULL は NULL、空文字は空文字
    assert rows[1][1] is None and rows[1][2] == ""
    # 配列・文字・数・null の json で落ちない（最上位のキーは object のときだけ数える）
    assert rows[1][5] == f"masked:json:len={jlen[1]}:keys=0"
    assert rows[2][5] == f"masked:json:len={jlen[2]}:keys=0" and rows[2][6] == "masked:json:len=5:keys=0"
    assert rows[3][5] == f"masked:json:len={jlen[3]}:keys=0" and rows[3][6] == "masked:json:len=1:keys=0"
    # そのままの型
    amount, born = _cloud(pg, "SELECT amount, born FROM ai_cloud.public__pii_demo WHERE id = 1")[0]
    assert float(amount) == 12.5 and str(born) == "2000-01-01"
    cols = {r[0] for r in _rows(pg, "SELECT column_name FROM information_schema.columns WHERE table_schema = 'ai_cloud'")}
    assert "access_token" not in cols and "password_hash" not in cols
    # 多バイトの形
    assert _cloud(pg, "SELECT name FROM ai_cloud.public__suppliers")[0][0].startswith("masked:len=")
    assert "mixed" in _cloud(pg, "SELECT name FROM ai_cloud.public__suppliers")[0][0]


def test_t1_classification_applied(pg):
    """分類表の mask_bare は masked だけ。allow はそのまま。分類の無い text は伏せる。"""
    postal, lang = _cloud(pg, "SELECT postal_code, default_language FROM ai_cloud.public__suppliers")[0]
    assert postal == "masked"
    assert lang == "ja"
    assert _cloud(pg, "SELECT customer_name FROM ai_cloud.tenant_001__leads")[0][0].startswith("masked:len=")


def test_t1_read_paths_do_not_leak(pg):
    """T1: 別名・式・連結・substring・md5・length・to_json・UNION・型変換のエラーで読んでも元の値が出ない。"""
    queries = [
        "SELECT email AS x FROM ai_cloud.public__pii_demo",
        "SELECT upper(email), lower(phone_number), email || '/' || phone_number FROM ai_cloud.public__pii_demo",
        "SELECT substring(email, 1, 5), left(email, 3), right(email, 3), md5(email), length(email) FROM ai_cloud.public__pii_demo",
        "SELECT to_json(t), row_to_json(t)::text, t::text FROM ai_cloud.public__pii_demo t",
        "SELECT email FROM ai_cloud.public__pii_demo UNION SELECT note FROM ai_cloud.public__pii_demo",
        "SELECT * FROM ai_cloud.public__pii_demo WHERE email LIKE '%alice%'",
        "SELECT * FROM ai_cloud.public__pii_demo WHERE phone_number = '090-1234-5678'",
        "SELECT count(*) FROM ai_cloud.public__pii_demo WHERE email LIKE 'alice%'",
        "SELECT string_agg(email, ',') FROM ai_cloud.public__pii_demo",
        "SELECT payload::text, payload_json::text FROM ai_cloud.public__pii_demo",
    ]
    out = []
    for q in queries:
        out.append(_flat(_cloud(pg, q)))
    _assert_no_raw("\n".join(out))
    # LIKE で元の値は当たらない
    assert _cloud(pg, "SELECT count(*) FROM ai_cloud.public__pii_demo WHERE email LIKE 'alice%'")[0][0] == 0
    # 型変換のエラーに元の値が出ない
    import psycopg2

    c = pg.cursor()
    c.execute("SET ROLE ai_reader_cloud")
    try:
        for q in (
            "SELECT email::int FROM ai_cloud.public__pii_demo WHERE id = 1",
            "SELECT (email::text)::numeric FROM ai_cloud.public__pii_demo WHERE id = 1",
            "SELECT note::date FROM ai_cloud.public__pii_demo WHERE id = 1",
        ):
            with pytest.raises(psycopg2.Error) as ei:
                c.execute(q)
            _assert_no_raw(str(ei.value))
    finally:
        c.execute("RESET ROLE")


def test_t1b_statistics_and_explain_do_not_leak(pg):
    """T1b: pg_stats・pg_stats_ext・pg_stats_ext_exprs・EXPLAIN (VERBOSE) から元の値が出ない。"""
    out = []
    for q in (
        "SELECT * FROM pg_stats WHERE schemaname IN ('public', 'tenant_001', 'ai_cloud')",
        "SELECT * FROM pg_stats_ext",
        "SELECT * FROM pg_stats_ext_exprs",
    ):
        out.append(_flat(_cloud(pg, q)))
    out.append(_flat(_cloud(pg, "EXPLAIN (VERBOSE) SELECT * FROM ai_cloud.public__pii_demo WHERE email = 'zzz-not-the-value'")))
    out.append(_flat(_cloud(pg, "EXPLAIN (VERBOSE, ANALYZE) SELECT email, note FROM ai_cloud.public__pii_demo")))
    _assert_no_raw("\n".join(out))
    # 元の表の統計は ai_reader_cloud には見えない（列の SELECT 権限が無い）
    assert _cloud(pg, "SELECT count(*) FROM pg_stats WHERE schemaname = 'public' AND tablename = 'pii_demo'")[0][0] == 0


def test_c_view_owner_passes_rls_like_ai_ro(pg):
    """§3(c): 持ち主（非 superuser・FORCE なし）のビューは tenant の RLS を越える。ai_cloud も同じ。"""
    owner_rows = _rows(pg, "SELECT count(*) FROM tenant_001.guarded", role="aic_owner")[0][0]
    cloud_rows = _cloud(pg, "SELECT count(*) FROM ai_cloud.tenant_001__guarded")[0][0]
    print(f"RLS: owner(table)={owner_rows} ai_cloud(view)={cloud_rows}")
    assert owner_rows == 2  # 持ち主は RLS の対象外（FORCE なし）
    assert cloud_rows == 2


def test_m8_privileges(pg):
    """M8（受入）: ai_reader_cloud は ai_cloud だけ。ai_reader は meta を読める。build_views はだれにも付けない。"""
    one = lambda sql: _rows(pg, sql)[0][0]  # noqa: E731
    assert one("SELECT has_schema_privilege('ai_reader_cloud', 'ai_ro', 'USAGE')") is False
    assert one("SELECT has_schema_privilege('ai_reader_cloud', 'ai_cloud_meta', 'USAGE')") is False
    assert one("SELECT has_schema_privilege('ai_reader_cloud', 'ai_cloud', 'USAGE')") is True
    assert one("SELECT has_schema_privilege('ai_reader', 'ai_cloud_meta', 'USAGE')") is True
    assert one("SELECT has_function_privilege('ai_reader', 'ai_cloud_meta.build_views()', 'EXECUTE')") is False
    assert one("SELECT has_function_privilege('ai_reader_cloud', 'ai_cloud_meta.build_views()', 'EXECUTE')") is False
    for t in ("column_class", "build_log", "build_columns"):
        assert one(f"SELECT has_table_privilege('ai_reader', 'ai_cloud_meta.{t}', 'SELECT')") is True
        assert one(f"SELECT has_table_privilege('ai_reader_cloud', 'ai_cloud_meta.{t}', 'SELECT')") is False
    n = one(
        "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
        " WHERE c.relkind IN ('r', 'p') AND (n.nspname = 'public' OR n.nspname LIKE 'tenant\\_%')"
        " AND has_table_privilege('ai_reader_cloud', c.oid, 'SELECT')"
    )
    assert n == 0
    # ロールの属性は ai_reader と同じ（pg_roles。rolconfig を含む）
    attrs = "rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolconnlimit, rolcanlogin"
    a = _rows(pg, f"SELECT {attrs} FROM pg_roles WHERE rolname = 'ai_reader'")[0]
    b = _rows(pg, f"SELECT {attrs} FROM pg_roles WHERE rolname = 'ai_reader_cloud'")[0]
    assert a == b
    cfg = sorted(_rows(pg, "SELECT unnest(rolconfig) FROM pg_roles WHERE rolname = 'ai_reader_cloud'"))
    assert cfg == sorted(_rows(pg, "SELECT unnest(rolconfig) FROM pg_roles WHERE rolname = 'ai_reader'"))
    assert ("log_statement=all",) in cfg
    # 直接は読めない
    import psycopg2

    for sql in (
        "SELECT * FROM public.pii_demo",
        "SELECT * FROM ai_cloud_meta.column_class",
        "SELECT * FROM ai_cloud_meta.build_columns",
        "SELECT ai_cloud_meta.build_views()",
    ):
        c = pg.cursor()
        c.execute("SET ROLE ai_reader_cloud")
        try:
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                c.execute(sql)
        finally:
            c.execute("RESET ROLE")


def test_m8_acceptance_masks_counted(pg):
    """§5「伏せてある」①②③: mask 系でない pass は allow か「そのまま」の型だけ。viewdef の 'masked の数 = mask 系の列数。"""
    pass_bad = _rows(
        pg,
        "SELECT count(*) FROM ai_cloud_meta.build_columns WHERE mode = 'pass' AND coalesce(class, '') <> 'allow'"
        " AND split_part(source_type, '(', 1) NOT IN ('smallint', 'integer', 'bigint', 'numeric', 'real',"
        " 'double precision', 'boolean', 'date', 'time without time zone', 'time with time zone',"
        " 'timestamp without time zone', 'timestamp with time zone', 'interval', 'uuid')",
        role="ai_reader",
    )[0][0]
    assert pass_bad == 0
    mismatch = _rows(
        pg,
        "SELECT v.view_name, (length(pg_get_viewdef(c.oid)) - length(replace(pg_get_viewdef(c.oid), '''masked', ''))) / 7 AS n,"
        " (SELECT count(*) FROM ai_cloud_meta.build_columns b WHERE b.view_name = v.view_name AND b.mode IN ('mask', 'mask_bare')) AS m"
        " FROM (SELECT DISTINCT view_name FROM ai_cloud_meta.build_columns) v"
        " JOIN pg_class c ON c.relname = v.view_name"
        " AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'ai_cloud')",
        role="ai_reader",
    )
    assert mismatch
    assert [r for r in mismatch if r[1] != r[2]] == []


# ---------------------------------------------------------------- T10b


def test_t10b_role_with_other_attributes_stops_migration(pg):
    """T10b: 属性違いの同名ロール（BYPASSRLS つき）がある状態でロールの migration を流すと止まり、属性は書き換えない。
    ロールの属性は pg_roles で測る（rolconfig を含む）。属性を変えるので superuser が要る（要らなければ skip）。"""
    import psycopg2

    c = pg.cursor()
    c.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
    if not c.fetchone()[0]:
        pytest.skip("ロールの属性を変えるには superuser が要る")
    c.execute("ALTER ROLE ai_reader_cloud BYPASSRLS")
    try:
        with pytest.raises(psycopg2.Error) as ei:
            c.execute(_read(_ROLE_SQL))
        assert "unexpected attributes" in str(ei.value)
        # 属性は書き換えられていない（止まっただけ）
        assert _rows(pg, "SELECT rolbypassrls FROM pg_roles WHERE rolname = 'ai_reader_cloud'")[0][0] is True
    finally:
        c.execute("ALTER ROLE ai_reader_cloud NOBYPASSRLS")
    # 元に戻せば通る
    c.execute(_read(_ROLE_SQL))
    assert _rows(pg, "SELECT rolbypassrls FROM pg_roles WHERE rolname = 'ai_reader_cloud'")[0][0] is False


def test_role_migration_is_idempotent(pg):
    """同じ属性なら何度流しても通り、drop → create もできる（デプロイの毎回の実行）。"""
    c = pg.cursor()
    c.execute(_read(_ROLE_SQL))
    c.execute(_read(_DROP_SQL))
    assert _rows(pg, "SELECT count(*) FROM pg_namespace WHERE nspname = 'ai_cloud'")[0][0] == 0
    c.execute(_read(_CREATE_SQL))
    assert _rows(pg, "SELECT count(*) FROM pg_namespace WHERE nspname = 'ai_cloud'")[0][0] == 1
    assert _cloud(pg, "SELECT count(*) FROM ai_cloud.public__pii_demo")[0][0] == 4
    # meta の migration も冪等（分類表の中身は消えない）
    n0 = _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0]
    c.execute(_read(_META_SQL))
    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1035


# ---------------------------------------------------------------- T10（CI の見張り）


def _classification_gaps(conn):
    """分類の漏れを返す。対象は public と tenant_* の全部の表（写しの表を除く）の全列のうち、秘密列の deny に当たらないもの。

    - 「そのまま」でない型の列に column_class の行が無い
    - 正規表現（_NAME_RE）に当たる列は型を問わず行が要る
    - allow で reason が空
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT n.nspname, c.relname, a.attname, ty.typname, ty.typtype"
        " FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
        " JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped"
        " JOIN pg_type ty ON ty.oid = a.atttypid"
        " WHERE c.relkind IN ('r', 'p') AND (n.nspname = 'public' OR n.nspname LIKE 'tenant\\_%')"
    )
    cols = cur.fetchall()
    cur.execute("SELECT schema_pattern, table_name, column_name, class, reason FROM ai_cloud_meta.column_class")
    cls = {(r[0], r[1], r[2]): (r[3], r[4]) for r in cur.fetchall()}
    gaps = []
    for sch, rel, col, typname, typtype in cols:
        if _COPY_RE.search(rel):
            continue
        if _DENY_RE.search(col.lower()):
            continue
        key = ("public" if sch == "public" else "tenant_*", rel, col)
        row = cls.get(key)
        passes = (typtype == "b" and typname in _PASS_TYPES) or typtype == "e"
        if (not passes) and row is None:
            gaps.append((sch, rel, col, typname, "分類なし"))
        elif _NAME_RE.search(col) and row is None:
            gaps.append((sch, rel, col, typname, "名前の見張りに当たるが分類なし"))
        elif row is not None and row[0] == "allow" and not row[1].strip():
            gaps.append((sch, rel, col, typname, "allow の理由が空"))
    return gaps


def test_t10_classification_covers_real_shaped_tables(cluster):
    """T10: 本番の形の表（tenant の型紙 + public の表）の全列に、必要な分類の行がある。"""
    from sqlalchemy.ext.asyncio import create_async_engine

    name, conn = _new_db(cluster.control, "ai_cloud_t10")
    try:
        c = conn.cursor()
        c.execute(_read(_AI_READER_SQL))
        c.execute(_read(_ROLE_SQL))
        c.execute(_read(_META_SQL))
        url = _psycopg_url(ADMIN_PG_URL, name).replace("postgresql://", "postgresql+asyncpg://", 1)
        # public / tenant の表は、既存の試験と同じ本番 migration 順の作り方（tests/rls_bootstrap.py）で作る
        from tests.rls_bootstrap import bootstrap_tenant_schema

        async def build():
            eng = create_async_engine(url)
            try:
                await bootstrap_tenant_schema(eng, 1)
            finally:
                await eng.dispose()

        asyncio.run(build())
        c.execute(_read(_CREATE_SQL))
        tenant_schemas = _rows(conn, "SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant\\_%'")
        assert tenant_schemas, "tenant_* のスキーマが作れていない"
        # 試験の足場（tests/rls_bootstrap.py）だけにある列。本番には無い（2026-10-31 04:09 JST に reader の道で確認、
        # AUDIT sha=a40f10a0a8a5。本番の suppliers は public.suppliers だけで分類表に 25 行ある）。
        # docs/handoff/cloud-case-ai/stage1-h-decision.md §1
        scaffold_only = {
            ("public", "tenants", "company_name"),
            ("public", "users", "firebase_uid"),
            *(
                ("tenant_001", "suppliers", col)
                for col in ("supplier_code", "name", "contact_name", "email", "phone", "address", "notes")
            ),
        }
        gaps = [g for g in _classification_gaps(conn) if g[:3] not in scaffold_only]
        print(f"T10 gaps={len(gaps)}")
        for g in gaps:
            print("T10 GAP", g)
        assert gaps == []
    finally:
        conn.close()
        cur = cluster.control.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def test_t10_detects_added_columns(pg):
    """T10 の足した場合の試し: 分類の無い text 列・理由なしの allow・phone_number bigint を足すと落ちる。
    deny に当たる text 列（x_token_encrypted）を分類なしで足しても落ちない。"""
    c = pg.cursor()
    c.execute("SET ROLE aic_owner")
    try:
        base = len(_classification_gaps(pg))
        c.execute("ALTER TABLE public.suppliers ADD COLUMN memo2 text")
        assert len(_classification_gaps(pg)) == base + 1
        c.execute("ALTER TABLE public.suppliers ADD COLUMN phone_number bigint")
        gaps = _classification_gaps(pg)
        assert any(g[2] == "phone_number" and g[3] == "int8" for g in gaps)
        assert len(gaps) == base + 2
        c.execute("ALTER TABLE public.suppliers ADD COLUMN x_token_encrypted text")
        assert len(_classification_gaps(pg)) == base + 2
    finally:
        c.execute("RESET ROLE")


def test_allow_without_reason_is_rejected_by_table(pg):
    """分類表自身も、理由なしの allow を入れさせない（CHECK）。"""
    import psycopg2

    c = pg.cursor()
    with pytest.raises(psycopg2.errors.CheckViolation):
        c.execute(
            "INSERT INTO ai_cloud_meta.column_class (schema_pattern, table_name, column_name, class, reason)"
            " VALUES ('public', 'zz_demo', 'zz_col', 'allow', '')"
        )
