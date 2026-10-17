"""ADR-1024 便3a: 読み取り台本 app.ops.readonly_query の単体テスト（DB 不要）。

K2・K13・K18 のうち、台本の中で確かめられる部分。
"""

from __future__ import annotations

import io

import pytest

from app.ops import readonly_query as rq

SECRET_URL = "postgresql://ai_reader:SUPERSECRETVALUE@db.example:5432/x"


def run(sql, connect=None):
    out, err = io.StringIO(), io.StringIO()
    code = rq.main(stdin=io.StringIO(sql), stdout=out, stderr=err, connect=connect)
    return code, out.getvalue(), err.getvalue()


class FakeCursor:
    def __init__(self, names, rows, executed):
        self.description = [(n,) for n in names] if names is not None else None
        self._rows = rows
        self._executed = executed

    def execute(self, sql):
        self._executed.append(sql)

    def fetchmany(self, n):
        return self._rows[:n]


class FakeConn:
    def __init__(self, names=("a",), rows=((1,),)):
        self.executed = []
        self.readonly = None
        self.rolled_back = False
        self.closed = False
        self._names, self._rows = names, list(rows)

    def set_session(self, readonly=False):
        self.readonly = readonly

    def cursor(self):
        return FakeCursor(self._names, self._rows, self.executed)

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


REJECT = [
    r"\c jarvis",
    r"\! ls",
    "SELECT 1; SELECT 2",
    "DELETE FROM x",
    "INSERT INTO x VALUES (1)",
    "UPDATE x SET a = 1",
    "DROP TABLE x",
    "WITH x AS (DELETE FROM y RETURNING *) SELECT * FROM x",
    "SELECT set_config('statement_timeout','0',false)",
    "SELECT pg_catalog.set_config('statement_timeout','0',false)",
    "SET statement_timeout=0",
    "SELECT 1 /* c */ ; SET statement_timeout=0",
    "SELECT pg_sleep(100)",
    "COPY x TO PROGRAM 'ls'",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT lo_import('/etc/passwd')",
    "EXPLAIN ANALYZE SELECT 1",
    "EXPLAIN (ANALYZE) SELECT 1",
    "EXPLAIN INSERT INTO x VALUES (1)",
    "-- c\n\\c jarvis",
]


@pytest.mark.parametrize("sql", REJECT)
def test_rejected_with_exit_2(sql, monkeypatch):
    monkeypatch.setenv("AI_READER_DATABASE_URL", SECRET_URL)
    called = []
    code, out, err = run(sql, connect=lambda u: called.append(u))
    assert code == 2
    assert called == []
    assert out == ""


PASS = [
    "SELECT 1",
    "WITH a AS (SELECT 1) SELECT * FROM a",
    "SHOW server_version",
    "EXPLAIN SELECT 1",
    "SELECT 1;",
    "-- limit=10\nSELECT 1",
    "SELECT ';' AS semi",
]


@pytest.mark.parametrize("sql", PASS)
def test_allowed_pass_the_check(sql):
    rq.check_sql(sql)


def test_oversize_rejected(monkeypatch):
    monkeypatch.setenv("AI_READER_DATABASE_URL", SECRET_URL)
    code, _, _ = run("SELECT '" + "a" * (64 * 1024) + "'", connect=lambda u: None)
    assert code == 2


def test_env_missing_exit_3_and_database_url_not_used(monkeypatch):
    monkeypatch.delenv("AI_READER_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)
    monkeypatch.setenv("ADMIN_DATABASE_URL", SECRET_URL)
    called = []
    code, out, err = run("SELECT 1", connect=lambda u: called.append(u))
    assert code == 3
    assert called == []
    assert "SUPERSECRETVALUE" not in out + err


def test_success_readonly_session_timeout_and_rollback(monkeypatch):
    monkeypatch.setenv("AI_READER_DATABASE_URL", SECRET_URL)
    conn = FakeConn(names=("a", "b"), rows=[(1, "x\ty\nz")])
    seen = []

    def connect(url):
        seen.append(url)
        return conn

    code, out, err = run("SELECT 1", connect=connect)
    assert code == 0
    assert seen == [SECRET_URL]
    assert conn.readonly is True
    assert conn.executed[0].startswith("SET LOCAL statement_timeout")
    assert conn.rolled_back and conn.closed
    assert out == "a\tb\n1\tx\\ty\\nz\n"
    assert "SUPERSECRETVALUE" not in out + err
    assert "AUDIT" in err


def test_db_error_does_not_leak_connection_string(monkeypatch):
    monkeypatch.setenv("AI_READER_DATABASE_URL", SECRET_URL)

    def connect(url):
        raise RuntimeError("could not connect using " + url)

    code, out, err = run("SELECT 1", connect=connect)
    assert code == 4
    assert "SUPERSECRETVALUE" not in out + err


def test_denied_column_values_are_redacted(monkeypatch):
    monkeypatch.setenv("AI_READER_DATABASE_URL", SECRET_URL)
    conn = FakeConn(names=("id", "password_hash", "API_KEY"), rows=[(1, "h", "k")])
    code, out, _ = run("SELECT 1", connect=lambda u: conn)
    assert code == 0
    assert out == "id\tpassword_hash\tAPI_KEY\n1\t<redacted>\t<redacted>\n"


def test_default_limit_200_and_truncation_note(monkeypatch):
    monkeypatch.setenv("AI_READER_DATABASE_URL", SECRET_URL)
    conn = FakeConn(rows=[(i,) for i in range(500)])
    code, out, err = run("SELECT 1", connect=lambda u: conn)
    assert code == 0
    assert len(out.splitlines()) == 1 + 200
    assert "打ち切り" in err


def test_limit_comment_capped_at_5000(monkeypatch):
    monkeypatch.setenv("AI_READER_DATABASE_URL", SECRET_URL)
    assert rq.parse_limit("-- limit=10000\nSELECT 1") == 5000
    assert rq.parse_limit("-- limit=10\nSELECT 1") == 10
    assert rq.parse_limit("SELECT 1") == 200
    conn = FakeConn(rows=[(i,) for i in range(6000)])
    code, out, _ = run("-- limit=10000\nSELECT 1", connect=lambda u: conn)
    assert code == 0
    assert len(out.splitlines()) == 1 + 5000


def test_source_does_not_spawn_or_read_ssh_command():
    import inspect

    src = inspect.getsource(rq)
    code_only = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert "os.system(" not in code_only
    assert "import subprocess" not in code_only
    assert "SSH_ORIGINAL_COMMAND" not in code_only.split('"""', 2)[-1]
    assert code_only.count("os.environ.get(") == 1
