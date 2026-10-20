"""部屋へのお知らせ（ADR-1019 段10 便2）。PG 不要の部分: 送信関数・文面・分岐。"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.discord_gateway import viewer_bot_texts as t
from app.services import viewer_room_notice as n

JST_END = datetime(2026, 11, 3, 14, 59, 59, tzinfo=timezone.utc)  # JST 11/3 23:59:59


async def test_send_success_posts_expected_json(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "x")
    mock = AsyncMock(return_value={"id": "1"})
    with patch.object(n, "discord_api_request", new=mock):
        assert await n.send_room_notice("123", "こんにちは") is True
    kw = mock.await_args.kwargs
    assert kw["method"] == "POST" and kw["path"] == "/channels/123/messages"
    assert kw["json"] == {"content": "こんにちは", "allowed_mentions": {"parse": []}}
    assert kw["max_retries"] == 1


async def test_send_exception_returns_false_and_logs_no_body(monkeypatch, caplog):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "x")
    with patch.object(n, "discord_api_request", new=AsyncMock(side_effect=RuntimeError("boom"))):
        assert await n.send_room_notice("123", "秘密の本文") is False
    assert "秘密の本文" not in caplog.text and "123" in caplog.text


async def test_send_without_token_returns_false(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    mock = AsyncMock()
    with patch.object(n, "discord_api_request", new=mock):
        assert await n.send_room_notice("123", "x") is False
    mock.assert_not_awaited()


def test_texts_exact():
    assert t.NOTICE_EXTENDED.format(until_date="11月3日") == "お試し期間を 11月3日 まで延長しました😊"
    assert t.NOTICE_ACTIVATED == "本登録が完了しました。引き続きご利用ください😊"
    assert t.NOTICE_SUSPENDED == "ご利用を停止しました。ご不明な点は、この部屋でお知らせください。"


def test_notice_text_by_action():
    item = {"trial_expires_at": JST_END}
    assert n.notice_text("extend", item) == "お試し期間を 11月3日 まで延長しました😊"
    assert n.notice_text("activate", item) == t.NOTICE_ACTIVATED
    assert n.notice_text("suspend", item) == t.NOTICE_SUSPENDED
    assert n.notice_text("unsuspend", item) is None


@pytest.mark.parametrize(
    "action,channel,ok,expected",
    [
        ("suspend", "55", True, "sent"),
        ("suspend", "55", False, "failed"),
        ("activate", None, True, "no_room"),
        ("unsuspend", "55", True, None),
    ],
)
async def test_notify_status_change(action, channel, ok, expected):
    item = {"discord_channel_id": channel, "trial_expires_at": JST_END}
    send = AsyncMock(return_value=ok)
    with patch.object(n, "send_room_notice", new=send):
        status, text = await n.notify_status_change(action, item)
    assert status == expected
    assert (text is None) == (expected is None)
    if expected in ("sent", "failed"):
        send.assert_awaited_once_with("55", text)
    else:
        send.assert_not_awaited()
