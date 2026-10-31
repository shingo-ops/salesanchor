"""ADR-1052 段2: ops_case（相談係の件・申請・値を 1 回だけ返す関数）のテスト（実 PostgreSQL が必要）。

使い捨て DB を作り、migration を本物のファイルで適用して SET ROLE で確かめる。
T2   : 許可されていない申請（pending・denied）では値が出ない。
T3   : 別の件の札・期限切れの札では値が出ない。
T4   : 期限を過ぎた許可では値が出ない。
T5   : 許可にない列・秘密列・拒否表・主キーが 2 列の表では、許可済みの行でも値が出ない。
T5b  : 型に合わない行のキーは read_failed になり、エラーの文にキーの値が入らない。
T6   : ai_unmask・ai_reader 等の権限の境目。
T6c  : 許可した行は 1 回だけ返り、COMMIT の後に記録が 1 つ増える。
T6b  : 2 回目は断られ、同時の 2 本のうち 1 本だけ値が返る。
ロール・rolconfig・is_denied_source・権限の付け直し（2 回目は 0・拒否表に足すと外れる・1 回目が 5 秒以内）。
クラスタ共通のロールは、このテストが作った場合だけ最後に消す。パスワードは設定しない（SET ROLE で確かめる）。
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
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
_INCIDENTS_SQL = "20261016_100000_create_ops_incident_tables.sql"
_AI_READER_SQL = "20261017_130000_create_ai_reader_role.sql"
_META_SQL = "20261024_100000_create_ai_cloud_meta.sql"
_ROLE_SQL = "20261024_100100_create_ai_reader_cloud_role.sql"
_CREATE_SQL = "20261024_100300_create_ai_cloud_views.sql"
_CASE_SQL = "20261031_200000_create_ops_case.sql"

_ROLES = (
    "ai_unmask",
    "ai_unmask_owner",
    "ai_reader_cloud",
    "ai_reader",
    "salesanchor_app",
    "aic_owner",
    "aic_nobody",
)
_MARKS = {"not_found", "ticket", "status", "expired", "used", "view", "source", "column", "key", "read_failed"}

_RAW_NAME = "ひみつの名前 raw-customer-name"
_RAW_EMAIL = "alice-very-secret@example.test"


def _psycopg_url(url: str, dbname: str | None = None) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if dbname:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(path="/" + dbname))
    return url


def _read(fname: str) -> str:
    return (_MIGRATIONS_DIR / fname).read_text("utf-8")


def _hash(ticket: str) -> str:
    return hashlib.sha256(ticket.encode("utf-8")).hexdigest()


class _Cluster:
    """クラスタ共通のロールを、このテストが作った場合だけ消すための記録。"""

    def __init__(self, control):
        self.control = control
        cur = control.cursor()
        self.existed = {}
        for r in _ROLES:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (r,))
            self.existed[r] = cur.fetchone() is not None

    def cleanup(self):
        import psycopg2

        cur = self.control.cursor()
        for r in _ROLES:
            if not self.existed[r]:
                try:
                    cur.execute(f"DROP ROLE IF EXISTS {r}")
                except psycopg2.Error:
                    pass


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


def _make_table(cur, ddl):
    cur.execute(ddl)


def _prepare(conn):
    """前提: ai_reader・ai_reader_cloud・salesanchor_app・ops_incidents・非 superuser の表の持ち主。"""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app'")
    if cur.fetchone() is None:
        cur.execute("CREATE ROLE salesanchor_app NOLOGIN NOSUPERUSER NOBYPASSRLS")
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aic_owner'")
    if cur.fetchone() is None:
        cur.execute("CREATE ROLE aic_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aic_nobody'")
    if cur.fetchone() is None:
        cur.execute("CREATE ROLE aic_nobody NOLOGIN NOSUPERUSER NOBYPASSRLS")
    cur.execute(_read(_AI_READER_SQL))
    cur.execute(_read(_ROLE_SQL))
    cur.execute(_read(_INCIDENTS_SQL))


@pytest.fixture(scope="module")
def pg(cluster):
    """ふつうの表・uuid の主キーのテナントの表・拒否表・秘密列を持つ表・主キー 2 列の表を持つ DB に、本物の migration を流す。"""
    name, conn = _new_db(cluster.control, "ops_case")
    try:
        _prepare(conn)
        c = conn.cursor()
        c.execute(f'GRANT CREATE ON DATABASE "{name}" TO aic_owner')
        c.execute("ALTER SCHEMA public OWNER TO aic_owner")
        c.execute("SET ROLE aic_owner")
        c.execute("CREATE TABLE public.plain_demo (id integer PRIMARY KEY, memo text, email text)")
        c.execute("INSERT INTO public.plain_demo VALUES (1, 'memo-1', %s), (2, 'memo-2', 'b@example.test')", (_RAW_EMAIL,))
        c.execute("CREATE TABLE public.text_pk (code text PRIMARY KEY, memo text)")
        c.execute("INSERT INTO public.text_pk VALUES ('k-1', 'text-memo')")
        c.execute("CREATE TABLE public.has_secret (id integer PRIMARY KEY, memo text, api_token text)")
        c.execute("INSERT INTO public.has_secret VALUES (1, 'm', 'tok-very-secret')")
        c.execute("CREATE TABLE public.two_pk (a integer, b integer, memo text, PRIMARY KEY (a, b))")
        c.execute("INSERT INTO public.two_pk VALUES (1, 1, 'two-pk-memo')")
        c.execute("CREATE SCHEMA tenant_001")
        c.execute("CREATE TABLE tenant_001.leads (id uuid PRIMARY KEY, customer_name text, email text)")
        c.execute(
            "INSERT INTO tenant_001.leads VALUES ('11111111-1111-1111-1111-111111111111', %s, %s),"
            " ('22222222-2222-2222-2222-222222222222', 'other', 'other@example.test')",
            (_RAW_NAME, _RAW_EMAIL),
        )
        # deny_tables にある名前（秘密列は無い＝拒否表だけで断られる）
        c.execute("CREATE TABLE tenant_001.viewer_accounts (id integer PRIMARY KEY, note text)")
        c.execute("INSERT INTO tenant_001.viewer_accounts VALUES (1, 'viewer-note')")
        c.execute("ANALYZE")
        c.execute(_read(_META_SQL))
        c.execute(_read(_CREATE_SQL))
        c.execute("RESET ROLE")
        t0 = time.monotonic()
        c.execute(_read(_CASE_SQL))
        conn_elapsed = time.monotonic() - t0
        print(f"[ops_case migration 1 回目の所要] {conn_elapsed:.3f} 秒")
        yield conn
    finally:
        conn.close()
        cur = cluster.control.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def _one(conn, sql, params=None):
    c = conn.cursor()
    c.execute(sql, params)
    return c.fetchone()[0]


def _as(conn, role, sql, params=None):
    """role に SET ROLE して 1 文流し、結果の全行を返す（失敗は例外のまま。RESET ROLE は必ず行う）。"""
    c = conn.cursor()
    try:
        c.execute(f"SET ROLE {role}")
        c.execute(sql, params)
        return c.fetchall() if c.description else []
    finally:
        c.execute("RESET ROLE")


def _denied(conn, role, sql, params=None):
    """42501（権限・断り）で失敗することを確かめ、エラーの短い文を返す。"""
    import psycopg2

    with pytest.raises(psycopg2.Error) as ei:
        _as(conn, role, sql, params)
    assert ei.value.pgcode == "42501", f"{role}: 42501 でなく {ei.value.pgcode}"
    return ei.value.diag.message_primary or ""


class _Case:
    """件 1 つ（札つき）。申請は make_request で作る。"""

    def __init__(self, conn):
        self.conn = conn
        self.ticket = "ticket-" + uuid.uuid4().hex
        c = conn.cursor()
        c.execute(
            "INSERT INTO public.ops_incidents (fingerprint, starts_at, alertname, status, first_notified_at,"
            " last_notified_at) VALUES (%s, now(), 'test', 'firing', now(), now()) RETURNING id",
            (uuid.uuid4().hex,),
        )
        self.incident_id = c.fetchone()[0]
        c.execute(
            "INSERT INTO ops_case.cases (incident_id, ticket_hash, ticket_expires_at)"
            " VALUES (%s, %s, now() + interval '1 hour')",
            (self.incident_id, _hash(self.ticket)),
        )

    def make_request(self, view, columns, keys, status="approved", expires="now() + interval '5 minutes'"):
        c = self.conn.cursor()
        if status == "approved":
            c.execute(
                "INSERT INTO ops_case.unmask_requests (incident_id, view_name, column_names, row_keys, reason,"
                " status, decided_by, approved_minutes, expires_at) VALUES (%s, %s, %s, %s, %s, 'approved',"
                f" 'test', 5, {expires}) RETURNING id",
                (self.incident_id, view, columns, keys, "調査のために値を確かめる必要がある（試験）"),
            )
        else:
            c.execute(
                "INSERT INTO ops_case.unmask_requests (incident_id, view_name, column_names, row_keys, reason,"
                " status) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (self.incident_id, view, columns, keys, "調査のために値を確かめる必要がある（試験）", status),
            )
        return c.fetchone()[0]


def _fetch(conn, request_id, ticket):
    return _as(conn, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(request_id), ticket))[0][0]


def _reads(conn, request_id=None):
    if request_id is None:
        return _one(conn, "SELECT count(*) FROM ops_case.unmask_reads")
    return _one(conn, "SELECT count(*) FROM ops_case.unmask_reads WHERE request_id = %s", (str(request_id),))


def _read_count(conn, request_id):
    return _one(conn, "SELECT read_count FROM ops_case.unmask_requests WHERE id = %s", (str(request_id),))


# ---------------------------------------------------------------------------------------------------
# 前提の確認
# ---------------------------------------------------------------------------------------------------
def test_views_and_grants_are_ready(pg):
    """ai_cloud のビューが作られ、拒否に当たらない表にだけ ai_unmask_owner の SELECT が付いている。"""
    assert _one(pg, "SELECT count(*) FROM pg_views WHERE schemaname = 'ai_cloud'") >= 6
    for tbl, want in (
        ("public.plain_demo", True),
        ("public.text_pk", True),
        ("tenant_001.leads", True),
        ("public.has_secret", False),
        ("public.two_pk", True),
        ("tenant_001.viewer_accounts", False),
    ):
        got = _one(
            pg,
            "SELECT EXISTS (SELECT 1 FROM pg_class c, aclexplode(c.relacl) a WHERE c.oid = %s::regclass"
            " AND a.grantee = (SELECT oid FROM pg_roles WHERE rolname = 'ai_unmask_owner')"
            " AND a.privilege_type = 'SELECT')",
            (tbl,),
        )
        assert got is want, f"{tbl}: ai_unmask_owner の SELECT が {got}（期待 {want}）"


# ---------------------------------------------------------------------------------------------------
# T2〜T5b
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("status", ["pending", "denied"])
def test_t2_not_approved_returns_nothing(pg, status):
    case = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo"], ["1"], status=status)
    before = _reads(pg)
    msg = _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket))
    assert msg == "status"
    assert _reads(pg) == before
    assert _read_count(pg, rid) == 0


def test_t2_unknown_request(pg):
    case = _Case(pg)
    assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(uuid.uuid4()), case.ticket)) == "not_found"


def test_t3_other_case_ticket_and_expired_ticket(pg):
    case = _Case(pg)
    other = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo"], ["1"])
    before = _reads(pg)
    assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), other.ticket)) == "ticket"
    assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), "")) == "ticket"
    assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, NULL)", (str(rid),)) == "ticket"
    pg.cursor().execute(
        "UPDATE ops_case.cases SET ticket_expires_at = now() - interval '1 second' WHERE incident_id = %s",
        (case.incident_id,),
    )
    assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket)) == "ticket"
    assert _reads(pg) == before
    assert _read_count(pg, rid) == 0


def test_t4_expired_approval(pg):
    case = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo"], ["1"], expires="now() - interval '1 second'")
    before = _reads(pg)
    assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket)) == "expired"
    assert _reads(pg) == before


@pytest.mark.parametrize(
    "view,columns,keys",
    [
        ("public__plain_demo", ["no_such_column"], ["1"]),  # ビューに無い列
        ("public__has_secret", ["memo"], ["1"]),  # 秘密列を持つ表は、秘密でない列だけでも断る
        ("public__has_secret", ["api_token"], ["1"]),  # 秘密列そのもの
        ("tenant_001__viewer_accounts", ["note"], ["1"]),  # 拒否表（秘密列は無い）
        ("public__two_pk", ["memo"], ["1"]),  # 主キーが 2 列
        ("public__not_a_view", ["memo"], ["1"]),  # ai_cloud に無いビュー
    ],
)
def test_t5_forbidden_requests_return_nothing_even_if_approved(pg, view, columns, keys):
    case = _Case(pg)
    rid = case.make_request(view, columns, keys)
    before = _reads(pg)
    msg = _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket))
    assert msg in _MARKS - {"read_failed"}
    assert _reads(pg) == before
    assert _read_count(pg, rid) == 0


def test_t5b_wrong_key_type_is_read_failed_without_value(pg):
    case = _Case(pg)
    rid = case.make_request("tenant_001__leads", ["customer_name"], ["abc"])
    import psycopg2

    before = _reads(pg)
    with pytest.raises(psycopg2.Error) as ei:
        _as(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket))
    assert ei.value.pgcode == "42501"
    assert ei.value.diag.message_primary == "read_failed"
    for part in (ei.value.diag.message_primary, ei.value.diag.message_detail, ei.value.diag.message_hint,
                 ei.value.diag.context, str(ei.value)):
        assert "abc" not in (part or "")
    assert _reads(pg) == before
    assert _read_count(pg, rid) == 0


# ---------------------------------------------------------------------------------------------------
# T6c・T6b
# ---------------------------------------------------------------------------------------------------
def test_t6c_approved_rows_are_returned_once_and_recorded(pg):
    import psycopg2

    case = _Case(pg)
    rid = case.make_request(
        "tenant_001__leads",
        ["customer_name", "email"],
        ["11111111-1111-1111-1111-111111111111"],
    )
    before = _reads(pg)
    out = _fetch(pg, rid, case.ticket)
    assert out["request_id"] == str(rid)
    assert out["row_count"] == 1
    assert len(out["rows"]) == 1, "0 件でなく行が返る"
    row = out["rows"][0]
    assert row["customer_name"] == _RAW_NAME and row["email"] == _RAW_EMAIL
    # COMMIT の後に、別の接続で記録が 1 つ増え、read_count=1 になっている
    other = psycopg2.connect(_psycopg_url(ADMIN_PG_URL, pg.info.dbname))
    other.autocommit = True
    try:
        assert _reads(other) == before + 1
        assert _reads(other, rid) == 1
        assert _read_count(other, rid) == 1
        got = _one(other, "SELECT column_names::text FROM ops_case.unmask_reads WHERE request_id = %s", (str(rid),))
        assert "customer_name" in got and _RAW_NAME not in got, "記録は列の名前だけで値は入らない"
    finally:
        other.close()


def test_t6c_integer_and_text_keys(pg):
    case = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo", "email"], ["1", "2", "99"])
    out = _fetch(pg, rid, case.ticket)
    assert out["row_count"] == 2
    assert {r["__key"] for r in out["rows"]} == {1, 2}
    rid2 = case.make_request("public__text_pk", ["memo"], ["k-1"])
    assert _fetch(pg, rid2, case.ticket)["rows"][0]["memo"] == "text-memo"


def test_t6b_second_read_is_refused(pg):
    case = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo"], ["1"])
    assert _fetch(pg, rid, case.ticket)["row_count"] == 1
    assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket)) == "used"
    assert _read_count(pg, rid) == 1
    assert _reads(pg, rid) == 1


def test_t6b_two_concurrent_reads_only_one_succeeds(pg):
    import psycopg2

    case = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo"], ["1"])
    dsn = _psycopg_url(ADMIN_PG_URL, pg.info.dbname)
    first = psycopg2.connect(dsn)  # 取引を開けたままにする
    first.autocommit = False
    second = psycopg2.connect(dsn)
    second.autocommit = True
    result: dict = {}
    try:
        c1 = first.cursor()
        c1.execute("SET ROLE ai_unmask")
        c1.execute("SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket))
        result["first"] = c1.fetchone()[0]  # COMMIT の前

        def run_second():
            try:
                c2 = second.cursor()
                c2.execute("SET ROLE ai_unmask")
                c2.execute("SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket))
                result["second"] = c2.fetchone()[0]
            except psycopg2.Error as e:
                result["second_err"] = (e.pgcode, e.diag.message_primary)

        th = threading.Thread(target=run_second)
        th.start()
        time.sleep(0.5)  # 2 本目は 1 本目の COMMIT を待っている
        assert th.is_alive(), "2 本目は 1 本目の COMMIT を待つ"
        first.commit()
        th.join(timeout=10)
        assert not th.is_alive()
    finally:
        first.close()
        second.close()
    assert result["first"]["row_count"] == 1
    assert "second" not in result
    assert result["second_err"] == ("42501", "used")
    assert _read_count(pg, rid) == 1
    assert _reads(pg, rid) == 1


# ---------------------------------------------------------------------------------------------------
# T6 権限の境目
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM public.plain_demo",
        "SELECT * FROM tenant_001.leads",
        "SELECT * FROM ops_case.cases",
        "SELECT * FROM ops_case.reports",
        "SELECT * FROM ops_case.unmask_requests",
        "SELECT * FROM ops_case.unmask_reads",
        "SELECT * FROM ops_case.audits",
        "SELECT * FROM ops_case.deny_tables",
        "SELECT * FROM ai_cloud_meta.build_columns",
        "SELECT ops_case.is_denied_source('public.plain_demo')",
        "SELECT ops_case.grant_unmask_owner()",
    ],
)
def test_t6_ai_unmask_has_no_direct_access(pg, sql):
    _denied(pg, "ai_unmask", sql)


@pytest.mark.parametrize("role", ["ai_reader", "ai_reader_cloud", "salesanchor_app", "aic_nobody"])
def test_t6_other_roles_cannot_run_the_functions(pg, role):
    case = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo"], ["1"])
    _denied(pg, role, "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket))
    _denied(pg, role, "SELECT ops_case.grant_unmask_owner()")
    assert _read_count(pg, rid) == 0


def test_t6_public_has_no_execute(pg):
    for sig in ("ops_case.unmask_fetch(uuid,text)", "ops_case.grant_unmask_owner()", "ops_case.is_denied_source(text)"):
        n = _one(
            pg,
            "SELECT count(*) FROM pg_proc p, aclexplode(p.proacl) a WHERE p.oid = %s::regprocedure AND a.grantee = 0",
            (sig,),
        )
        assert n == 0, f"{sig}: PUBLIC に実行権限がある"
    assert _one(pg, "SELECT has_function_privilege('ai_unmask', 'ops_case.unmask_fetch(uuid,text)', 'EXECUTE')") is True
    for role in ("ai_reader", "ai_reader_cloud", "salesanchor_app"):
        assert _one(pg, f"SELECT has_function_privilege('{role}', 'ops_case.unmask_fetch(uuid,text)', 'EXECUTE')") is False


def test_t6_owner_has_no_privilege_on_denied_tables(pg):
    for tbl in ("tenant_001.viewer_accounts", "public.has_secret"):
        assert _one(pg, "SELECT has_table_privilege('ai_unmask_owner', %s, 'SELECT')", (tbl,)) is False
        # PUBLIC への付与も無い
        n = _one(
            pg,
            "SELECT count(*) FROM pg_class c, aclexplode(c.relacl) a WHERE c.oid = %s::regclass AND a.grantee = 0",
            (tbl,),
        )
        assert n == 0


def test_t6_app_cannot_change_read_count(pg):
    case = _Case(pg)
    rid = case.make_request("public__plain_demo", ["memo"], ["1"])
    _denied(pg, "salesanchor_app", "UPDATE ops_case.unmask_requests SET read_count = 1 WHERE id = %s", (str(rid),))
    _denied(pg, "salesanchor_app", "DELETE FROM ops_case.cases WHERE incident_id = %s", (case.incident_id,))
    _denied(pg, "salesanchor_app", "TRUNCATE ops_case.unmask_reads")


def test_app_privileges_for_backend(pg):
    """backend の接続（salesanchor_app）が ops_case の表と is_denied_source に届く（スキーマの USAGE がある）。"""
    assert _as(pg, "salesanchor_app", "SELECT count(*) FROM ops_case.cases")[0][0] == 0  # 旗が無いので RLS で 0 行
    assert _as(pg, "salesanchor_app", "SELECT ops_case.is_denied_source('public.plain_demo')")[0][0] is False
    assert _as(pg, "salesanchor_app", "SELECT ops_case.is_denied_source('tenant_001.viewer_accounts')")[0][0] is True
    assert _as(pg, "salesanchor_app", "SELECT count(*) FROM ai_cloud_meta.build_columns")[0][0] > 0
    # 運用者の旗が立った取引では、件の行を作れる
    c = pg.cursor()
    c.execute("SET ROLE salesanchor_app")
    try:
        c.execute("BEGIN")
        c.execute("SELECT set_config('app.is_operator', 'true', true)")
        c.execute(
            "INSERT INTO public.ops_incidents (fingerprint, starts_at, alertname, status, first_notified_at,"
            " last_notified_at) VALUES (%s, now(), 'app', 'firing', now(), now()) RETURNING id",
            (uuid.uuid4().hex,),
        )
        iid = c.fetchone()[0]
        c.execute("INSERT INTO ops_case.cases (incident_id) VALUES (%s)", (iid,))
        c.execute("SELECT count(*) FROM ops_case.cases WHERE incident_id = %s", (iid,))
        assert c.fetchone()[0] == 1
        c.execute("ROLLBACK")
    finally:
        c.execute("RESET ROLE")


# ---------------------------------------------------------------------------------------------------
# ロール・rolconfig
# ---------------------------------------------------------------------------------------------------
def test_role_attributes_and_settings(pg):
    owner = pg.cursor()
    owner.execute(
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolconnlimit"
        " FROM pg_roles WHERE rolname = 'ai_unmask_owner'"
    )
    assert owner.fetchone() == (False, False, False, False, False, True, -1)
    owner.execute(
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolconnlimit"
        " FROM pg_roles WHERE rolname = 'ai_unmask'"
    )
    assert owner.fetchone() == (True, False, False, False, False, False, 2)
    owner.execute(
        "SELECT s.setconfig FROM pg_db_role_setting s JOIN pg_roles r ON r.oid = s.setrole"
        " WHERE r.rolname = 'ai_unmask' AND s.setdatabase = 0"
    )
    conf = set(owner.fetchone()[0])
    for want in ("log_statement=none", "log_min_error_statement=panic", "log_min_duration_statement=-1"):
        assert want in conf, f"{want} が無い: {sorted(conf)}"
    assert not any(x.startswith("default_transaction_read_only") for x in conf)
    # 関数の持ち主・SECURITY DEFINER・固定の設定
    owner.execute(
        "SELECT r.rolname, p.prosecdef, p.proconfig FROM pg_proc p JOIN pg_roles r ON r.oid = p.proowner"
        " WHERE p.oid = 'ops_case.unmask_fetch(uuid,text)'::regprocedure"
    )
    rolname, prosecdef, proconfig = owner.fetchone()
    assert rolname == "ai_unmask_owner" and prosecdef is True
    assert any(x.startswith("search_path=") for x in proconfig) and "lock_timeout=2s" in proconfig


@pytest.mark.parametrize(
    "role,alter",
    [
        ("ai_unmask_owner", "LOGIN"),
        ("ai_unmask_owner", "NOBYPASSRLS"),
        ("ai_unmask", "BYPASSRLS"),
        ("ai_unmask", "CONNECTION LIMIT 5"),
        ("ai_unmask", "NOLOGIN"),
    ],
)
def test_migration_stops_when_same_name_role_has_other_attributes(pg, role, alter):
    import psycopg2

    c = pg.cursor()
    restore = {
        ("ai_unmask_owner", "LOGIN"): "NOLOGIN",
        ("ai_unmask_owner", "NOBYPASSRLS"): "BYPASSRLS",
        ("ai_unmask", "BYPASSRLS"): "NOBYPASSRLS",
        ("ai_unmask", "CONNECTION LIMIT 5"): "CONNECTION LIMIT 2",
        ("ai_unmask", "NOLOGIN"): "LOGIN",
    }[(role, alter)]
    c.execute(f"ALTER ROLE {role} {alter}")
    try:
        with pytest.raises(psycopg2.Error) as ei:
            c.execute(_read(_CASE_SQL))
        assert "unexpected attributes" in str(ei.value)
    finally:
        c.execute(f"ALTER ROLE {role} {restore}")


def test_migration_is_idempotent(pg):
    pg.cursor().execute(_read(_CASE_SQL))
    pg.cursor().execute(_read(_CASE_SQL))
    assert _one(pg, "SELECT count(*) FROM ops_case.deny_tables") == 10
    assert _one(pg, "SELECT ops_case.grant_unmask_owner()") == 0


# ---------------------------------------------------------------------------------------------------
# is_denied_source・権限の付け直し
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "source,want",
    [
        ("tenant_001.viewer_accounts", True),  # deny_tables の名前
        ("public.has_secret", True),  # 秘密列（excluded）を持つ表
        ("public.plain_demo", False),
        ("tenant_001.leads", False),
        ("public.no_such_table", True),  # 解けない名前
        ("plain_demo", True),  # スキーマ無しは解けない
        ("", True),
    ],
)
def test_is_denied_source(pg, source, want):
    assert _one(pg, "SELECT ops_case.is_denied_source(%s)", (source,)) is want


def test_is_denied_source_null_is_denied(pg):
    assert _one(pg, "SELECT ops_case.is_denied_source(NULL)") is True


def test_deny_tables_has_ten_names(pg):
    c = pg.cursor()
    c.execute("SELECT table_name FROM ops_case.deny_tables")
    got = {r[0] for r in c.fetchall()}
    assert got == {
        "users", "viewer_accounts", "auth_events", "auth_refresh_tokens", "password_reset_tokens",
        "registration_tokens", "viewer_login_events", "viewer_login_tokens", "webauthn_credentials",
        "tenant_carrier_credentials",
    }  # fmt: skip


def _owner_can_select(conn, tbl):
    return _one(
        conn,
        "SELECT EXISTS (SELECT 1 FROM pg_class c, aclexplode(c.relacl) a WHERE c.oid = %s::regclass"
        " AND a.grantee = (SELECT oid FROM pg_roles WHERE rolname = 'ai_unmask_owner')"
        " AND a.privilege_type = 'SELECT')",
        (tbl,),
    )


def test_grant_unmask_owner_first_run_is_fast_and_second_is_zero(pg):
    c = pg.cursor()
    # 付いている権限を全部外した状態から、1 回目の所要を測る
    c.execute("REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM ai_unmask_owner")
    c.execute("REVOKE SELECT ON ALL TABLES IN SCHEMA tenant_001 FROM ai_unmask_owner")
    t0 = time.monotonic()
    first = _one(pg, "SELECT ops_case.grant_unmask_owner()")
    elapsed = time.monotonic() - t0
    print(f"[grant_unmask_owner 1 回目の所要] {elapsed:.3f} 秒（付けた表の数 {first}）")
    assert elapsed < 5
    assert first >= 4  # plain_demo・text_pk・two_pk・tenant_001.leads
    assert _owner_can_select(pg, "public.plain_demo") is True
    assert _owner_can_select(pg, "tenant_001.viewer_accounts") is False
    assert _owner_can_select(pg, "public.has_secret") is False
    assert _one(pg, "SELECT ops_case.grant_unmask_owner()") == 0


def test_grant_unmask_owner_revokes_when_table_is_added_to_deny_tables(pg):
    c = pg.cursor()
    assert _owner_can_select(pg, "public.text_pk") is True
    c.execute("INSERT INTO ops_case.deny_tables (table_name, reason) VALUES ('text_pk', '試験')")
    try:
        assert _one(pg, "SELECT ops_case.grant_unmask_owner()") == 1
        assert _owner_can_select(pg, "public.text_pk") is False
        case = _Case(pg)
        rid = case.make_request("public__text_pk", ["memo"], ["k-1"])
        assert _denied(pg, "ai_unmask", "SELECT ops_case.unmask_fetch(%s, %s)", (str(rid), case.ticket)) == "source"
    finally:
        c.execute("DELETE FROM ops_case.deny_tables WHERE table_name = 'text_pk'")
        assert _one(pg, "SELECT ops_case.grant_unmask_owner()") == 1
    assert _owner_can_select(pg, "public.text_pk") is True


# ---------------------------------------------------------------------------------------------------
# HTTP 口 unmask_http の通し（実 DB。ロール ai_unmask に切り替えた接続で関数を呼ぶ）
# ---------------------------------------------------------------------------------------------------
def test_unmask_http_end_to_end_with_real_db(pg, monkeypatch):
    import psycopg2
    from starlette.testclient import TestClient

    from app.ops import unmask_http as uh

    class _Audit:
        def __init__(self):
            self.sent = []

        def send(self, data):
            self.sent.append(data.decode("utf-8"))

        def close(self):
            pass

    audit = _Audit()
    dsn = _psycopg_url(ADMIN_PG_URL, pg.info.dbname)

    def connect(_url):
        conn = psycopg2.connect(dsn, options="-c role=ai_unmask")
        return conn

    monkeypatch.setenv("CASE_AGENT_TOKEN", "case-agent-token-e2e")
    monkeypatch.setenv("AI_UNMASK_DATABASE_URL", "postgresql://unused")
    monkeypatch.setattr(uh, "_connect", connect)
    monkeypatch.setattr(uh.readonly_query, "_open_audit", lambda path: audit)
    client = TestClient(uh.app)

    case = _Case(pg)
    rid = case.make_request("tenant_001__leads", ["customer_name"], ["11111111-1111-1111-1111-111111111111"])
    headers = {"Authorization": "Bearer case-agent-token-e2e", "X-Case-Ticket": case.ticket}
    r = client.post("/ops/unmask/read", json={"request_id": str(rid)}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["rows"][0]["customer_name"] == _RAW_NAME
    assert _read_count(pg, rid) == 1
    assert _RAW_NAME not in "".join(audit.sent) and case.ticket not in "".join(audit.sent)
    # 2 回目は 403 used。値は出ない
    r2 = client.post("/ops/unmask/read", json={"request_id": str(rid)}, headers=headers)
    assert r2.status_code == 403 and r2.json() == {"error": "used"}
    # 別の札は 403 ticket
    bad = client.post(
        "/ops/unmask/read", json={"request_id": str(rid)}, headers={**headers, "X-Case-Ticket": "wrong-ticket"}
    )
    assert bad.status_code == 403 and bad.json() == {"error": "ticket"}
    # 型に合わない行のキーは 403 read_failed で、キーの値が応答に入らない
    rid3 = case.make_request("tenant_001__leads", ["customer_name"], ["abc"])
    r3 = client.post("/ops/unmask/read", json={"request_id": str(rid3)}, headers=headers)
    assert r3.status_code == 403 and r3.json() == {"error": "read_failed"} and "abc" not in r3.text
    assert _read_count(pg, rid3) == 0
