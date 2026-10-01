"""
services/discord_webhook_sender.py の単体テスト（ADR-159 便B）。

カバー:
- 名前検証（1〜80 文字・discord / clyde 拒否・前後空白除去）
- webhook 作成（name="Sales Anchor"・avatar なし・Bot 認証）と暗号化保管（平文が DB に無い）
- 実行（username / avatar_url / wait=true・avatar なしなら avatar_url を省略・画像は multipart）
- 404 で保管行を消して作り直し 1 回だけ再送
- 429 / 5xx / ネットワークエラーは 1 回だけ再試行・retry_after が大きければ待たず失敗
- 作成 403 → WebhookPermissionError
- 失敗時に Bot 名義の送信（/channels/{id}/messages）を一切呼ばない
- token がログに出ない
"""
from __future__ import annotations

import json
import logging
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import httpx
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import text

from app.services import discord_webhook_sender as sender
from app.services import encryption

_REAL_ASYNC_CLIENT = httpx.AsyncClient
_TOKEN = "WEBHOOK-SECRET-TOKEN-xyz"
_CHANNEL = "555000111"

@pytest_asyncio.fixture
async def db(db_session):
    """conftest.py の setup_test_db が作る discord_channel_webhooks を使う。"""
    yield db_session


@pytest.fixture(autouse=True)
def env(monkeypatch):
    encryption.reset_cache()
    monkeypatch.setenv("METADATA_FERNET_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "bot-token-test")
    yield
    encryption.reset_cache()


@pytest.fixture
def sleeps(monkeypatch):
    calls: list[float] = []

    async def fake_sleep(sec):
        calls.append(sec)

    monkeypatch.setattr(sender.asyncio, "sleep", fake_sleep)
    return calls


class Recorder:
    """httpx.MockTransport のハンドラ。URL パスごとに応答キューを持つ。"""

    def __init__(self, routes: dict[str, list]):
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        key = "webhook_exec" if "/webhooks/" in path else "webhook_create" if path.endswith("/webhooks") else "bot_send"
        queue = self.routes.get(key, [])
        if not queue:
            raise AssertionError(f"unexpected request: {request.method} {path}")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def count(self, key: str) -> int:
        return sum(
            1 for r in self.requests
            if ("webhook_exec" == key and "/webhooks/" in r.url.path)
            or ("webhook_create" == key and r.url.path.endswith("/webhooks"))
            or ("bot_send" == key and r.url.path.endswith("/messages"))
        )


def _install(monkeypatch, recorder: Recorder) -> None:
    monkeypatch.setattr(
        sender.httpx, "AsyncClient",
        lambda **kw: _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(recorder), **kw),
    )


def _created():
    return httpx.Response(201, json={"id": "wh1", "token": _TOKEN})


def _ok(msg_id="msg-1"):
    return httpx.Response(200, json={"id": msg_id})


async def _send(db, **kw):
    params = dict(tenant_id=7, channel_id=_CHANNEL, username="Shingo", content="hello")
    params.update(kw)
    return await sender.send_as_staff(db, **params)


async def _rows(db):
    return (await db.execute(text("SELECT webhook_id, webhook_token_encrypted FROM discord_channel_webhooks"))).all()


# ---------------------------------------------------------------------------
# 名前検証
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["", "   ", "x" * 81, "Discord", "myDISCORDbot", "Clyde", "xClydex"])
def test_validate_username_rejects(name):
    with pytest.raises(sender.StaffNameInvalidError):
        sender.validate_username(name)


@pytest.mark.parametrize("name,expected", [("Shingo", "Shingo"), ("  Shingo  ", "Shingo"), ("x" * 80, "x" * 80)])
def test_validate_username_accepts(name, expected):
    assert sender.validate_username(name) == expected


@pytest.mark.asyncio
async def test_invalid_name_makes_no_http_call(db, monkeypatch):
    rec = Recorder({})
    _install(monkeypatch, rec)
    with pytest.raises(sender.StaffNameInvalidError):
        await _send(db, username="Discord Support")
    assert rec.requests == []


# ---------------------------------------------------------------------------
# 作成・保管・実行
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_creates_webhook_stores_encrypted_and_sends(db, monkeypatch):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [_ok("m42")]})
    _install(monkeypatch, rec)

    msg_id = await _send(db, avatar_url="https://api.example/api/public/staff-avatars/t.webp")

    assert msg_id == "m42"
    create_req, exec_req = rec.requests
    assert create_req.headers["Authorization"] == "Bot bot-token-test"
    assert json.loads(create_req.content) == {"name": "Sales Anchor"}  # avatar 指定なし
    assert exec_req.url.params["wait"] == "true"
    assert "Authorization" not in exec_req.headers  # webhook 実行は Bot 認証ではなく URL 内 token
    assert json.loads(exec_req.content) == {
        "username": "Shingo",
        "avatar_url": "https://api.example/api/public/staff-avatars/t.webp",
        "content": "hello",
    }
    rows = await _rows(db)
    assert len(rows) == 1 and rows[0][0] == "wh1"
    assert _TOKEN not in rows[0][1]  # 平文は DB に無い
    assert encryption.decrypt(rows[0][1]) == _TOKEN


@pytest.mark.asyncio
async def test_avatar_url_omitted_when_none(db, monkeypatch):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [_ok()]})
    _install(monkeypatch, rec)
    await _send(db, avatar_url=None)
    assert "avatar_url" not in json.loads(rec.requests[1].content)


@pytest.mark.asyncio
async def test_reuses_stored_webhook(db, monkeypatch):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [_ok("a"), _ok("b")]})
    _install(monkeypatch, rec)
    await _send(db)
    await _send(db)
    assert rec.count("webhook_create") == 1
    assert rec.count("webhook_exec") == 2


@pytest.mark.asyncio
async def test_image_sent_as_multipart(db, monkeypatch):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [_ok("img1")]})
    _install(monkeypatch, rec)
    f = sender.OutboundFile(filename="a.png", data=b"\x89PNGdata", content_type="image/png")

    msg_id = await _send(db, content=None, file=f, avatar_url=None)

    assert msg_id == "img1"
    exec_req = rec.requests[1]
    assert exec_req.headers["content-type"].startswith("multipart/form-data")
    body = exec_req.content
    assert b'name="payload_json"' in body and b'"username": "Shingo"' in body
    assert b'name="files[0]"; filename="a.png"' in body and b"\x89PNGdata" in body
    assert b"avatar_url" not in body


# ---------------------------------------------------------------------------
# 404 → 作り直し
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recreates_once_on_404_and_resends(db, monkeypatch):
    rec = Recorder({
        "webhook_create": [_created(), httpx.Response(201, json={"id": "wh2", "token": "NEW-TOKEN"})],
        "webhook_exec": [_ok("first")],
    })
    _install(monkeypatch, rec)
    await _send(db)  # 保管済みにする
    rec.routes["webhook_exec"] = [httpx.Response(404, json={"message": "Unknown Webhook"}), _ok("second")]

    assert await _send(db) == "second"

    assert rec.count("webhook_create") == 2
    rows = await _rows(db)
    assert len(rows) == 1 and rows[0][0] == "wh2"
    assert encryption.decrypt(rows[0][1]) == "NEW-TOKEN"


@pytest.mark.asyncio
async def test_second_404_after_recreate_fails_without_bot_fallback(db, monkeypatch):
    rec = Recorder({
        "webhook_create": [_created()],
        "webhook_exec": [httpx.Response(404, json={})],
    })
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)  # 作成直後の 404 は作り直さない
    assert rec.count("bot_send") == 0


@pytest.mark.asyncio
async def test_401_also_triggers_recreate(db, monkeypatch):
    rec = Recorder({
        "webhook_create": [_created(), _created()],
        "webhook_exec": [_ok("a")],
    })
    _install(monkeypatch, rec)
    await _send(db)
    rec.routes["webhook_exec"] = [httpx.Response(401, json={}), _ok("b")]
    assert await _send(db) == "b"


# ---------------------------------------------------------------------------
# 再試行
# ---------------------------------------------------------------------------


# 自動再送は「Discord がメッセージを作っていないと確実に言える場合」だけ（顧客への二重送信を防ぐ）


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [500, 502, 503])
async def test_5xx_is_not_retried_and_never_uses_bot(db, monkeypatch, sleeps, status):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [httpx.Response(status), _ok("dup")]})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert rec.count("webhook_exec") == 1  # 送られたかもしれないので再送しない
    assert rec.count("bot_send") == 0
    assert sleeps == []


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [httpx.ReadTimeout("t"), httpx.WriteTimeout("t"), httpx.RemoteProtocolError("t")])
async def test_error_after_request_sent_is_not_retried(db, monkeypatch, sleeps, exc):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [exc, _ok("dup")]})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert rec.count("webhook_exec") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [httpx.ConnectTimeout("t"), httpx.ConnectError("t")])
async def test_connect_failure_is_retried_once_then_succeeds(db, monkeypatch, sleeps, exc):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [exc, _ok("ok")]})
    _install(monkeypatch, rec)
    assert await _send(db) == "ok"
    assert rec.count("webhook_exec") == 2


@pytest.mark.asyncio
async def test_connect_failure_twice_raises_send_error(db, monkeypatch, sleeps):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [httpx.ConnectError("t"), httpx.ConnectError("t")]})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert rec.count("webhook_exec") == 2


# ---------------------------------------------------------------------------
# 想定外の応答（500 にせず WebhookSendError）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    httpx.Response(200, content=b"<html>not json</html>"),
    httpx.Response(200, json={"no_id": 1}),
    httpx.Response(200, json=["list"]),
])
async def test_malformed_execute_response_raises_send_error(db, monkeypatch, bad):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [bad]})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    httpx.Response(201, content=b"not json"),
    httpx.Response(201, json={"id": "wh1"}),
    httpx.Response(201, json={"token": "t"}),
])
async def test_malformed_create_response_raises_send_error_and_stores_nothing(db, monkeypatch, bad):
    rec = Recorder({"webhook_create": [bad]})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert await _rows(db) == []
    assert rec.count("webhook_exec") == 0


@pytest.mark.asyncio
async def test_429_small_retry_after_waits_and_retries(db, monkeypatch, sleeps):
    rec = Recorder({
        "webhook_create": [_created()],
        "webhook_exec": [httpx.Response(429, json={"retry_after": 0.5}), _ok("ok")],
    })
    _install(monkeypatch, rec)
    assert await _send(db) == "ok"
    assert sleeps == [0.5]


@pytest.mark.asyncio
async def test_429_large_retry_after_fails_without_waiting(db, monkeypatch, sleeps):
    rec = Recorder({
        "webhook_create": [_created()],
        "webhook_exec": [httpx.Response(429, json={"retry_after": 60})],
    })
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert sleeps == []
    assert rec.count("webhook_exec") == 1


@pytest.mark.asyncio
async def test_4xx_other_than_gone_is_not_retried(db, monkeypatch, sleeps):
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [httpx.Response(400, json={})]})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert rec.count("webhook_exec") == 1


# ---------------------------------------------------------------------------
# 権限・設定
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_403_raises_permission_error(db, monkeypatch):
    rec = Recorder({"webhook_create": [httpx.Response(403, json={"message": "Missing Permissions"})]})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookPermissionError):
        await _send(db)
    assert rec.count("webhook_exec") == 0 and rec.count("bot_send") == 0
    assert await _rows(db) == []


@pytest.mark.asyncio
async def test_missing_bot_token_raises_send_error(db, monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN")
    rec = Recorder({})
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert rec.requests == []


@pytest.mark.asyncio
async def test_undecryptable_row_is_replaced(db, monkeypatch):
    await db.execute(text(
        "INSERT INTO discord_channel_webhooks (tenant_id, channel_id, webhook_id, webhook_token_encrypted) "
        "VALUES (7, :c, 'old', 'not-a-fernet-token')"
    ), {"c": _CHANNEL})
    await db.commit()
    rec = Recorder({"webhook_create": [_created()], "webhook_exec": [_ok("ok")]})
    _install(monkeypatch, rec)
    assert await _send(db) == "ok"
    assert (await _rows(db))[0][0] == "wh1"


# ---------------------------------------------------------------------------
# token がログに出ない
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_never_logged(db, monkeypatch, sleeps, caplog):
    caplog.set_level(logging.DEBUG)
    rec = Recorder({
        "webhook_create": [_created()],
        "webhook_exec": [httpx.ConnectTimeout("t"), httpx.Response(500)],
    })
    _install(monkeypatch, rec)
    with pytest.raises(sender.WebhookSendError):
        await _send(db)
    assert _TOKEN not in caplog.text
    assert "bot-token-test" not in caplog.text


@pytest.mark.parametrize("name", ["httpx", "httpcore", "httpcore.http11", "httpcore.connection", "httpx._client"])
def test_token_redacted_for_httpx_and_httpcore_child_loggers(caplog, name):
    caplog.set_level(logging.DEBUG)
    url = f"https://discord.com/api/v10/webhooks/123/{_TOKEN}?wait=true"
    logging.getLogger(name).info("HTTP Request: POST %s", url)
    assert _TOKEN not in caplog.text
    assert "/webhooks/123/***" in caplog.text


def test_malformed_log_call_from_httpx_logger_does_not_raise():
    # 引数の個数が合わない（getMessage が TypeError になる）記録でも、呼び出し元に例外を投げない
    record = logging.getLogger("httpcore.http11").makeRecord(
        "httpcore.http11", logging.INFO, __file__, 1, "bad %s %s", ("x",), None,
    )
    assert record.msg == "bad %s %s" and record.args == ("x",)  # 失敗時は記録を変えない
