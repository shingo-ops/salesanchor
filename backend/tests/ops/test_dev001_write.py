"""ADR-1093 便2: 書き込み台本 app.ops.dev001_write の単体テスト（DB 不要）。

語の許し・拒否、AUDIT の名乗り、result の文字、終了コード 3/5、SET LOCAL の 2 文、commit/rollback の順を確かめる。
"""

from __future__ import annotations

import io

import pytest

from app.ops import dev001_write as dw

URL = "postgresql://ai_dev001_writer:SUPERSECRETVALUE@db.example:5432/x"


class FakeAudit:
    def __init__(self, exc=None):
        self.sent = []
        self.closed = 0
        self.exc = exc

    def send(self, data):
        if self.exc:
            raise self.exc
        self.sent.append(data)

    def close(self):
        self.closed += 1


class FakeDbError(Exception):
    pgcode = "42501"


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self.rowcount = 0

    def execute(self, sql):
        self.conn.executed.append(sql)
        if sql == self.conn.raw and self.conn.exc:
            raise self.conn.exc
        if sql == self.conn.raw:
            if self.conn.names is not None:
                self.description = [(n,) for n in self.conn.names]
            self.rowcount = self.conn.rowcount

    def fetchmany(self, n):
        return self.conn.rows[:n]


class FakeConn:
    def __init__(self, raw, names=None, rows=(), rowcount=1, exc=None):
        self.raw = raw
        self.names, self.rows, self.rowcount, self.exc = names, list(rows), rowcount, exc
        self.executed = []
        self.events = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.events.append("commit")

    def rollback(self):
        self.events.append("rollback")

    def close(self):
        self.closed = True


def run(sql, conn=None, audit=None, monkeypatch=None):
    out, err = io.StringIO(), io.StringIO()
    audit = audit if audit is not None else FakeAudit()
    connect = (lambda url: conn) if conn is not None else None
    code = dw.main(stdin=io.StringIO(sql), stdout=out, stderr=err, connect=connect, audit=audit)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("AI_DEV001_WRITER_DATABASE_URL", URL)


ALLOWED = [
    "INSERT INTO leads (name) VALUES ('a')",
    "insert into leads (name) values ('a')",
    "UPDATE leads SET name = 'b' WHERE id = 1",
    "DELETE FROM leads WHERE id = 1",
    "SELECT 1",
    "WITH x AS (SELECT 1) SELECT * FROM x",
    "-- note\nUPDATE leads SET name = 'b'",
    "/* c */ DELETE FROM tenant_004.leads WHERE id = 1",  # スキーマ名では拒まない（DB の権限が断る）
    "UPDATE leads SET name = 'b';",
]

REJECT = [
    "",
    "   ",
    r"\c jarvis",
    "SET search_path = public",
    "set app.tenant_id = '4'",
    "RESET ALL",
    "reset app.tenant_id",
    "SELECT set_config('app.tenant_id', '4', false)",
    "SELECT pg_catalog . set_config('app.tenant_id','4',false)",
    "UPDATE leads SET name = set_config('x','y',false)",
    "DROP TABLE leads",
    "TRUNCATE leads",
    "CREATE TABLE x (a int)",
    "ALTER TABLE leads ADD COLUMN x int",
    "GRANT ALL ON leads TO public",
    "COPY leads TO STDOUT",
    "EXPLAIN SELECT 1",
    "SHOW search_path",
    "SELECT 1; SELECT 2",
    "DELETE FROM leads; DROP TABLE leads",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_check_sql_allows(sql):
    assert dw.check_sql(sql)


@pytest.mark.parametrize("sql", REJECT)
def test_check_sql_rejects(sql):
    with pytest.raises(dw.Rejected):
        dw.check_sql(sql)


def test_update_set_is_not_rejected_but_leading_set_is():
    dw.check_sql("UPDATE t SET a = 1")
    with pytest.raises(dw.Rejected):
        dw.check_sql("SET a = 1")


def test_audit_ident_is_writer_specific():
    assert dw.AUDIT_IDENT == "ai-dev001-writer-audit"


def test_rejected_returns_2_and_audits_rejected():
    audit = FakeAudit()
    code, out, err = run("DROP TABLE leads", audit=audit)
    assert code == 2
    assert out == ""
    assert len(audit.sent) == 1
    line = audit.sent[0].decode()
    assert "ai-dev001-writer-audit:" in line
    assert "result=rejected" in line
    assert audit.closed == 1


def test_rejected_with_audit_failure_returns_5():
    code, _, err = run("DROP TABLE leads", audit=FakeAudit(exc=OSError("x")))
    assert code == 5
    assert "audit send failed" in err


def test_audit_channel_unavailable_returns_5():
    out, err = io.StringIO(), io.StringIO()
    code = dw.main(stdin=io.StringIO("SELECT 1"), stdout=out, stderr=err, audit_path="/nonexistent/dev-log")
    assert code == 5
    assert "audit channel unavailable" in err.getvalue()


def test_success_runs_prelude_then_statement_then_audit_then_commit():
    sql = "UPDATE leads SET name = 'b' WHERE id = 1"
    conn = FakeConn(sql, rowcount=1)
    audit = FakeAudit()
    code, out, err = run(sql, conn=conn, audit=audit)
    assert code == 0
    assert conn.executed == [
        "SET LOCAL app.tenant_id = '1'",
        "SET LOCAL search_path = tenant_001, public",
        sql,
    ]
    assert conn.events == ["commit", "rollback"] and conn.closed
    assert "result=ok" in audit.sent[0].decode()
    assert "rows=1" in audit.sent[0].decode()
    assert "ai-dev001-writer-audit:" in audit.sent[0].decode()
    assert "SUPERSECRETVALUE" not in err + out


def test_success_with_audit_failure_rolls_back_and_returns_3():
    sql = "DELETE FROM leads WHERE id = 1"
    conn = FakeConn(sql)
    code, out, err = run(sql, conn=conn, audit=FakeAudit(exc=OSError("x")))
    assert code == 3
    assert "commit" not in conn.events
    assert conn.events[0] == "rollback"
    assert out == ""


def test_select_prints_tsv_and_redacts_secret_columns():
    sql = "SELECT id, api_key_hash FROM bots"
    conn = FakeConn(sql, names=("id", "api_key_hash"), rows=[(1, "zzz")])
    code, out, _ = run(sql, conn=conn)
    assert code == 0
    assert out == "id\tapi_key_hash\n1\t<redacted>\n"


def test_db_error_audits_db_error_kind_and_rolls_back():
    sql = "INSERT INTO tenant_004.leads (name) VALUES ('x')"
    conn = FakeConn(sql, exc=FakeDbError("permission denied"))
    audit = FakeAudit()
    code, out, err = run(sql, conn=conn, audit=audit)
    assert code == 4
    assert out == ""
    assert "result=db_error:FakeDbError" in audit.sent[0].decode()
    assert "commit" not in conn.events and "rollback" in conn.events
    assert "SUPERSECRETVALUE" not in err
    assert "permission denied" not in err  # メッセージ本文は出さない


def test_db_error_with_audit_failure_returns_5_and_still_rolls_back():
    sql = "INSERT INTO tenant_004.leads (name) VALUES ('x')"
    conn = FakeConn(sql, exc=FakeDbError("x"))
    code, _, _ = run(sql, conn=conn, audit=FakeAudit(exc=OSError("x")))
    assert code == 5
    assert "rollback" in conn.events and "commit" not in conn.events


def test_env_missing(monkeypatch):
    monkeypatch.delenv("AI_DEV001_WRITER_DATABASE_URL")
    audit = FakeAudit()
    code, _, err = run("SELECT 1", audit=audit)
    assert code == 6
    assert "result=env_missing" in audit.sent[0].decode()
    assert "AI_DEV001_WRITER_DATABASE_URL is not set" in err


def test_only_one_env_var_is_read():
    import inspect

    src = inspect.getsource(dw)
    assert src.count("os.environ.get(") == 1
    assert "AI_READER_DATABASE_URL" not in src.replace('"""', "").split("import hashlib")[1]
