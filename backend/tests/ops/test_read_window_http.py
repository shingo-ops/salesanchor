"""ADR-1042 便1: HTTP 窓口 app.ops.read_window_http の単体テスト（DB はスタブ）。

K2（拒否される文は DB に届かない）・K3（鍵）・K4（秘密列）・K5（AUDIT 不可は結果なし）・K6（同時数）。
拒否例の正本は既存の test_readonly_query.REJECT（規則の正本は readonly_query.py）。ここには書かない。
"""

from __future__ import annotations

import threading

import pytest
from starlette.testclient import TestClient

from app.ops import read_window_http as rw

try:
    from tests.ops.test_readonly_query import REJECT
except ImportError:  # tests/ops に __init__.py が無い構成（rootdir が tests/ops）
    from test_readonly_query import REJECT

TOKEN = "test-token-value-0123456789"
URL = "/api/v1/ops/read-window/query"
GOOD = {rw.TOKEN_HEADER: TOKEN}


class FakeAudit:
    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(data)

    def close(self):
        pass


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = [(n,) for n in conn.names]

    def execute(self, sql):
        self.conn.executed.append(sql)

    def fetchmany(self, n):
        return self.conn.rows[:n]


class FakeConn:
    def __init__(self, names=("a",), rows=((1,),)):
        self.names, self.rows, self.executed = names, list(rows), []

    def set_session(self, readonly=False):
        pass

    def cursor(self):
        return FakeCursor(self)

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("READ_WINDOW_TOKEN", TOKEN)
    monkeypatch.setenv("AI_READER_DATABASE_URL", "postgresql://u:p@h/d")
    audit = FakeAudit()
    conns = []

    def connect(url):
        c = FakeConn()
        conns.append(c)
        return c

    monkeypatch.setattr(rw, "_connect", connect)
    monkeypatch.setattr(rw.readonly_query, "_open_audit", lambda path: audit)
    return TestClient(rw.app), audit, conns


def test_ok(env):
    client, audit, conns = env
    r = client.post(URL, content="SELECT 1", headers=GOOD)
    assert r.status_code == 200
    assert r.headers["x-read-window-rc"] == "0"
    assert r.headers["content-type"].startswith("text/tab-separated-values")
    assert r.text == "a\n1\n"
    assert any(b"via=https" in m for m in audit.sent)


@pytest.mark.parametrize(
    "headers,token_env",
    [
        ({}, TOKEN),
        ({rw.TOKEN_HEADER: "wrong"}, TOKEN),
        (GOOD, ""),
        ({"Authorization": f"Bearer {TOKEN}"}, TOKEN),
    ],
)
def test_unauthorized(env, monkeypatch, headers, token_env):
    client, _, conns = env
    monkeypatch.setenv("READ_WINDOW_TOKEN", token_env)
    r = client.post(URL, content="SELECT 1", headers=headers)
    assert r.status_code == 401
    assert r.text == "unauthorized"
    assert conns == []


def test_unset_token_is_401(env, monkeypatch):
    client, _, conns = env
    monkeypatch.delenv("READ_WINDOW_TOKEN")
    assert client.post(URL, content="SELECT 1", headers=GOOD).status_code == 401
    assert client.post(URL, content="SELECT 1", headers={rw.TOKEN_HEADER: ""}).status_code == 401
    assert conns == []


@pytest.mark.parametrize("sql", REJECT)
def test_rejected_before_db(env, sql):
    client, audit, conns = env
    r = client.post(URL, content=sql, headers=GOOD)
    assert r.status_code == 400
    assert r.headers["x-read-window-rc"] == "2"
    assert "AUDIT" not in r.text
    assert conns == []


def test_secret_column_redacted(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(rw, "_connect", lambda url: FakeConn(names=("id", "api_key"), rows=((1, "SECRETVAL"),)))
    r = client.post(URL, content="SELECT id, api_key FROM t", headers=GOOD)
    assert r.status_code == 200
    assert "<redacted>" in r.text
    assert "SECRETVAL" not in r.text


def test_audit_unavailable_503_no_body(env, monkeypatch):
    client, _, conns = env

    def boom(path):
        raise OSError("no socket")

    monkeypatch.setattr(rw.readonly_query, "_open_audit", boom)
    r = client.post(URL, content="SELECT 1", headers=GOOD)
    assert r.status_code == 503
    assert r.text == ""
    assert r.headers["x-read-window-rc"] == "5"
    assert conns == []


def test_audit_send_failure_503_no_result(env):
    client, audit, _ = env

    def fail(data):
        raise OSError("send")

    audit.send = fail
    r = client.post(URL, content="SELECT 1", headers=GOOD)
    assert r.status_code == 503
    assert r.text == ""


def test_db_error_400_without_audit_line(env, monkeypatch):
    client, _, _ = env

    def bad(url):
        raise RuntimeError("secret connection detail")

    monkeypatch.setattr(rw, "_connect", bad)
    r = client.post(URL, content="SELECT 1", headers=GOOD)
    assert r.status_code == 400
    assert r.headers["x-read-window-rc"] == "4"
    assert r.text.startswith("db error: RuntimeError")
    assert "AUDIT" not in r.text and "secret connection detail" not in r.text


def test_env_missing_503(env, monkeypatch):
    client, _, _ = env
    monkeypatch.delenv("AI_READER_DATABASE_URL")
    r = client.post(URL, content="SELECT 1", headers=GOOD)
    assert r.status_code == 503
    assert r.headers["x-read-window-rc"] == "3"


def test_second_concurrent_is_429(env, monkeypatch):
    client, _, _ = env
    entered, release = threading.Event(), threading.Event()

    def slow(url):
        entered.set()
        release.wait(5)
        return FakeConn()

    monkeypatch.setattr(rw, "_connect", slow)
    first = {}
    t = threading.Thread(target=lambda: first.update(r=client.post(URL, content="SELECT 1", headers=GOOD)))
    t.start()
    assert entered.wait(5)
    r2 = client.post(URL, content="SELECT 1", headers=GOOD)
    release.set()
    t.join(5)
    assert r2.status_code == 429
    assert r2.text == "busy"
    assert first["r"].status_code == 200
    monkeypatch.setattr(rw, "_connect", lambda url: FakeConn())
    assert client.post(URL, content="SELECT 1", headers=GOOD).status_code == 200


def test_too_large_413(env):
    client, _, conns = env
    r = client.post(URL, content="x" * (65 * 1024), headers=GOOD)
    assert r.status_code == 413
    assert conns == []


def test_get_is_405_and_other_path_404(env):
    client, _, _ = env
    assert client.get(URL, headers=GOOD).status_code == 405
    assert client.post("/other", content="SELECT 1", headers=GOOD).status_code == 404


# ── ADR-1052 段1: 相談係の容器の形（Authorization: Bearer・via=https-case）。既定は上の試験どおり今と同じ ──
CASE_ENV = {
    "READ_WINDOW_TOKEN_HEADER": "Authorization",
    "READ_WINDOW_TOKEN_PREFIX": "Bearer ",
    "READ_WINDOW_AUDIT_VIA": "https-case",
}


@pytest.fixture
def case_env(env, monkeypatch):
    for k, v in CASE_ENV.items():
        monkeypatch.setenv(k, v)
    return env


def test_default_window_rejects_bearer_only_and_accepts_custom_header(env):
    client, _, conns = env
    assert client.post(URL, content="SELECT 1", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 401
    assert conns == []
    assert client.post(URL, content="SELECT 1", headers=GOOD).status_code == 200


def test_case_window_accepts_bearer_only_and_records_https_case(case_env):
    client, audit, _ = case_env
    r = client.post(URL, content="SELECT 1", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert any(b"via=https-case" in m for m in audit.sent)
    assert not any(b"via=https " in m or b"via=https\n" in m for m in audit.sent)


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": TOKEN},  # Bearer なし
        {"Authorization": f"Basic {TOKEN}"},
        {"Authorization": "Bearer wrong"},
        {rw.TOKEN_HEADER: TOKEN},  # 旧ヘッダだけ
        {},
    ],
)
def test_case_window_unauthorized(case_env, headers):
    client, _, conns = case_env
    assert client.post(URL, content="SELECT 1", headers=headers).status_code == 401
    assert conns == []


def test_case_window_empty_token_is_401_for_everything(case_env, monkeypatch):
    client, _, conns = case_env
    monkeypatch.setenv("READ_WINDOW_TOKEN", "")
    for h in ({"Authorization": "Bearer "}, {"Authorization": "Bearer x"}, {rw.TOKEN_HEADER: ""}, {}):
        assert client.post(URL, content="SELECT 1", headers=h).status_code == 401
    assert conns == []


def test_empty_header_env_falls_back_to_default(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setenv("READ_WINDOW_TOKEN_HEADER", "")
    monkeypatch.setenv("READ_WINDOW_AUDIT_VIA", "")
    assert client.post(URL, content="SELECT 1", headers=GOOD).status_code == 200
