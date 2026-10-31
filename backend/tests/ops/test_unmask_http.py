"""ADR-1052 段2: HTTP 口 app.ops.unmask_http の単体テスト（DB はスタブ。実 DB での通しは test_ops_case_db.py）。

鍵・札・体の大きさ・request_id の形・印の返し方・503 の決まり・記録（/dev/log の印）に秘密が入らないこと。
"""

from __future__ import annotations

import json
import uuid

import pytest
from starlette.testclient import TestClient

from app.ops import unmask_http as uh

TOKEN = "case-agent-token-0123456789"
TICKET = "ticket-abcdefghijklmnopqrstuvwxyz"
URL = "/ops/unmask/read"
RID = str(uuid.uuid4())
GOOD_HEADERS = {"Authorization": f"Bearer {TOKEN}", "X-Case-Ticket": TICKET}
SECRET_VALUE = "ひみつの値 raw-secret-value"
MARKS = sorted(uh.MARKS)


class _Diag:
    def __init__(self, message):
        self.message_primary = message


class PgError(Exception):
    """psycopg2.Error の代わり（pgcode と diag だけ持つ）。"""

    def __init__(self, pgcode, message="", text="エラーの文: SELECT secret FROM t WHERE k='abc'"):
        super().__init__(text)
        self.pgcode = pgcode
        self.diag = _Diag(message)


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        self.conn.executed.append((sql, params))
        if self.conn.fetch_error is not None:
            raise self.conn.fetch_error

    def fetchone(self):
        return (self.conn.result,)


class FakeConn:
    def __init__(self, result=None, fetch_error=None, commit_error=None):
        self.result = result
        self.fetch_error = fetch_error
        self.commit_error = commit_error
        self.executed = []
        self.autocommit = True
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class FakeAudit:
    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(data.decode("utf-8"))

    def close(self):
        pass


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("CASE_AGENT_TOKEN", TOKEN)
    monkeypatch.setenv("AI_UNMASK_DATABASE_URL", "postgresql://u:p@h/d")
    audit = FakeAudit()
    conns: list[FakeConn] = []
    holder = {"conn": lambda: FakeConn(result={"request_id": RID, "rows": [{"memo": SECRET_VALUE}], "row_count": 1})}

    def connect(url):
        c = holder["conn"]()
        conns.append(c)
        return c

    monkeypatch.setattr(uh, "_connect", connect)
    monkeypatch.setattr(uh.readonly_query, "_open_audit", lambda path: audit)
    client = TestClient(uh.app)
    return client, audit, conns, holder


def _post(client, headers=GOOD_HEADERS, body=None, raw=None):
    if raw is not None:
        return client.post(URL, content=raw, headers=headers)
    return client.post(URL, json={"request_id": RID} if body is None else body, headers=headers)


# --- 鍵・札 -------------------------------------------------------------------------------------------
def test_no_header_no_bearer_wrong_key_no_ticket_are_401(env):
    client, _audit, conns, _h = env
    assert _post(client, headers={}).status_code == 401
    assert _post(client, headers={"X-Case-Ticket": TICKET}).status_code == 401
    assert _post(client, headers={"Authorization": f"Basic {TOKEN}", "X-Case-Ticket": TICKET}).status_code == 401
    assert _post(client, headers={"Authorization": "Bearer wrong", "X-Case-Ticket": TICKET}).status_code == 401
    assert _post(client, headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 401  # 札なし
    assert _post(client, headers={"Authorization": f"Bearer {TOKEN}", "X-Case-Ticket": ""}).status_code == 401
    assert conns == [], "鍵・札が無いときは DB に届かない"


def test_empty_key_rejects_everyone(env, monkeypatch):
    client, _audit, conns, _h = env
    monkeypatch.setenv("CASE_AGENT_TOKEN", "")
    for h in ({}, {"Authorization": "Bearer ", "X-Case-Ticket": TICKET}, {"Authorization": "Bearer x", "X-Case-Ticket": TICKET}):
        assert _post(client, headers=h).status_code == 401
    monkeypatch.delenv("CASE_AGENT_TOKEN")
    assert _post(client).status_code == 401
    assert conns == []


# --- 道・体 ---------------------------------------------------------------------------------------------
def test_other_paths_and_methods_are_404(env):
    client, *_ = env
    assert client.post("/", headers=GOOD_HEADERS).status_code == 404
    assert client.post("/ops/unmask/other", headers=GOOD_HEADERS, json={"request_id": RID}).status_code == 404
    assert client.get(URL, headers=GOOD_HEADERS).status_code == 404
    assert client.put(URL, headers=GOOD_HEADERS, json={"request_id": RID}).status_code == 404
    assert client.post("/api/v1/ops/read-window/query", headers=GOOD_HEADERS, content="select 1").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"request_id": "not-a-uuid"},
        {"request_id": RID.upper()},
        {"request_id": 123},
        {"request_id": None},
        {},
        {"request_id": RID, "extra": 1},
        [RID],
        "text",
    ],
)
def test_bad_request_id_is_400(env, body):
    client, _audit, conns, _h = env
    assert _post(client, body=body).status_code == 400
    assert conns == []


def test_invalid_json_is_400_and_oversize_is_413(env):
    client, _audit, conns, _h = env
    assert _post(client, raw=b"{not json").status_code == 400
    assert _post(client, raw=b"\xff\xfe").status_code == 400
    assert _post(client, raw=b'{"request_id": "' + b"a" * 5000 + b'"}').status_code == 413
    assert conns == []


# --- 成功・断り ----------------------------------------------------------------------------------------
def test_success_returns_value_after_commit_and_records_without_secrets(env):
    client, audit, conns, _h = env
    r = _post(client)
    assert r.status_code == 200
    assert r.json() == {"request_id": RID, "rows": [{"memo": SECRET_VALUE}], "row_count": 1}
    conn = conns[0]
    assert conn.autocommit is False and conn.commits == 1 and conn.closed
    assert len(conn.executed) == 1
    sql, params = conn.executed[0]
    assert sql == "SELECT ops_case.unmask_fetch(%s, %s)" and params == (RID, TICKET)
    assert len(audit.sent) == 1
    line = audit.sent[0]
    assert "via=https-case-unmask" in line and f"request_id={RID}" in line and "rows=1" in line and "result=ok" in line
    for secret in (SECRET_VALUE, TICKET, TOKEN):
        assert secret not in line


@pytest.mark.parametrize("mark", MARKS)
def test_function_refusal_is_403_with_mark_only(env, mark):
    client, audit, conns, holder = env
    holder["conn"] = lambda: FakeConn(fetch_error=PgError("42501", mark))
    r = _post(client)
    assert r.status_code == 403
    assert r.json() == {"error": mark}
    assert SECRET_VALUE not in r.text and TICKET not in r.text and "SELECT" not in r.text
    assert conns[0].rollbacks == 1 and conns[0].commits == 0
    assert f"result=denied:{mark}" in audit.sent[0] and "sqlstate=42501" in audit.sent[0]


def test_unknown_42501_message_is_not_returned(env):
    client, audit, conns, holder = env
    holder["conn"] = lambda: FakeConn(fetch_error=PgError("42501", "permission denied for table secret_table"))
    r = _post(client)
    assert r.status_code == 503 and r.json() == {"error": "unavailable"}
    assert "secret_table" not in r.text and "secret_table" not in audit.sent[0]


@pytest.mark.parametrize("state", ["57014", "55P03", "08006", "40001", "XX000", ""])
def test_other_db_failures_are_503_without_value(env, state):
    client, audit, conns, holder = env
    holder["conn"] = lambda: FakeConn(fetch_error=PgError(state or None, "x"))
    r = _post(client)
    assert r.status_code == 503 and r.json() == {"error": "unavailable"}
    assert "abc" not in r.text and "SELECT" not in r.text
    assert "abc" not in audit.sent[0] and "SELECT" not in audit.sent[0]
    if state:
        assert f"sqlstate={state}" in audit.sent[0]


def test_commit_failure_is_503_and_value_is_not_returned(env):
    client, audit, conns, holder = env
    holder["conn"] = lambda: FakeConn(
        result={"request_id": RID, "rows": [{"memo": SECRET_VALUE}], "row_count": 1},
        commit_error=PgError("08006", "connection lost"),
    )
    r = _post(client)
    assert r.status_code == 503 and r.json() == {"error": "unavailable"}
    assert SECRET_VALUE not in r.text
    assert SECRET_VALUE not in "".join(audit.sent)


def test_connect_failure_and_missing_url_are_503(env, monkeypatch):
    client, audit, _conns, _h = env

    def broken(url):
        raise PgError("08001", "could not connect", text="could not connect to server: password=hunter2")

    monkeypatch.setattr(uh, "_connect", broken)
    r = _post(client)
    assert r.status_code == 503 and "hunter2" not in r.text and "hunter2" not in "".join(audit.sent)
    monkeypatch.setenv("AI_UNMASK_DATABASE_URL", "")
    assert _post(client).status_code == 503


def test_audit_socket_unavailable_returns_nothing_and_does_not_touch_db(env, monkeypatch):
    client, _audit, conns, _h = env

    def fail(path):
        raise OSError("no socket")

    monkeypatch.setattr(uh.readonly_query, "_open_audit", fail)
    r = _post(client)
    assert r.status_code == 503 and SECRET_VALUE not in r.text
    assert conns == []


def test_jsonb_string_result_is_parsed(env):
    client, _audit, _conns, holder = env
    holder["conn"] = lambda: FakeConn(result=json.dumps({"request_id": RID, "rows": [], "row_count": 0}))
    r = _post(client)
    assert r.status_code == 200 and r.json()["row_count"] == 0
