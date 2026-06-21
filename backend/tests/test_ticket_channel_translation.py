from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.discord_gateway import ticket_channel_writer
from app.tasks.translation import _run_batch, _run_translate_inbound_message, translate_inbound_message


class _DBContext:
    def __init__(self, session: AsyncMock) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@dataclass(frozen=True)
class _FakeAuthor:
    id: int
    display_name: str
    bot: bool = False


@dataclass(frozen=True)
class _FakeChannel:
    id: int


@dataclass(frozen=True)
class _FakeGuild:
    id: int


@dataclass(frozen=True)
class _FakeMessage:
    id: int
    content: str
    author: _FakeAuthor
    channel: _FakeChannel
    guild: _FakeGuild
    created_at: object | None = None
    webhook_id: object | None = None


def _mock_result(first_value):
    result = MagicMock()
    result.first.return_value = first_value
    return result


def test_translate_inbound_message_task_wrapper_runs_and_disposes_engine():
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock(return_value=None)
    with patch(
        "app.tasks.translation._run_translate_inbound_message",
        AsyncMock(return_value={"status": "ok"}),
    ) as run_mock, patch(
        "app.database.engine",
        fake_engine,
    ):
        result = translate_inbound_message(
            tenant_id=7,
            table_ref="meta_messages",
            message_id="mid-1",
            message_text="hello",
            target_language="ja",
        )

    assert result["status"] == "ok"
    run_mock.assert_awaited_once()
    fake_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_translation_task_translates_then_publishes():
    session = AsyncMock()

    translate_result = MagicMock(
        cached=False,
        engine="gemini-1.5-flash",
        confidence=0.97,
        translated_text="こんにちは",
    )

    with patch("app.database.AsyncSessionLocal", return_value=_DBContext(session)), patch(
        "app.services.message_translator.ensure_inbound_translations",
        AsyncMock(return_value={"en": translate_result}),
    ) as translate_mock, patch(
        "app.services.sse_pubsub.publish_inbox_update",
        AsyncMock(return_value=None),
    ) as publish_mock:
        result = await _run_translate_inbound_message(
            tenant_id=7,
            table_ref="meta_messages",
            message_id="mid-1",
            message_text="hello",
            target_language="ja",
        )

    assert result["status"] == "ok"
    translate_mock.assert_awaited_once()
    translate_kwargs = translate_mock.await_args.kwargs
    assert translate_kwargs["table_ref"] == "tenant_007.message_translations"
    assert translate_kwargs["message_id"] == "mid-1"
    publish_mock.assert_awaited_once_with(7)
    assert result["translated_text"] == "こんにちは"


@pytest.mark.asyncio
async def test_ticket_channel_message_enqueues_translation_task_after_save():
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((45, "1234567890", "Shingo")),
        _mock_result((1,)),
    ]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))

    message = _FakeMessage(
        id=1517435280951349311,
        content="Do you accept PayPal?",
        author=_FakeAuthor(id=1234567890, display_name="Shingo"),
        channel=_FakeChannel(id=1517435280951349310),
        guild=_FakeGuild(id=1),
    )

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch(
        "app.discord_gateway.ticket_channel_writer.enqueue_inbound_translation",
        MagicMock(return_value=True),
    ) as enqueue_mock:
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory,
            tenant_id=4,
            message=message,
        )

    assert handled is True
    assert session.commit.await_count == 1
    enqueue_mock.assert_called_once_with(
        "meta_messages",
        "1517435280951349311",
        "Do you accept PayPal?",
        tenant_id=4,
    )


@pytest.mark.asyncio
async def test_ticket_channel_outbound_is_ignored_without_commit_or_translation():
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((45, "1234567890", "Shingo")),
        _mock_result((1,)),
    ]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))

    message = _FakeMessage(
        id=1517435280951349312,
        content="Please check this order.",
        author=_FakeAuthor(id=9876543210, display_name="Staff"),
        channel=_FakeChannel(id=1517435280951349310),
        guild=_FakeGuild(id=1),
    )

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch(
        "app.discord_gateway.ticket_channel_writer.enqueue_inbound_translation",
        MagicMock(return_value=True),
    ) as enqueue_mock, patch(
        "app.services.sse_pubsub.publish_inbox_update",
        AsyncMock(return_value=None),
    ) as publish_mock:
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory,
            tenant_id=4,
            message=message,
        )

    assert handled is True
    assert session.commit.await_count == 0
    enqueue_mock.assert_not_called()
    publish_mock.assert_not_called()


@pytest.mark.asyncio
async def test_batch_skips_completed_messages_and_translates_only_missing():
    session = AsyncMock()
    tenants_result = MagicMock()
    tenants_result.fetchall.return_value = [(7,)]
    messages_result = MagicMock()
    messages_result.fetchall.return_value = [
        ("mid-ja", "こんにちは"),
        ("mid-en", "Hello stock"),
        ("mid-es", "Hola stock"),
    ]
    session.execute = AsyncMock(side_effect=[tenants_result, messages_result])

    missing_result = MagicMock(
        cached=False,
        engine="gemini-1.5-flash",
        confidence=0.97,
        translated_text="translated",
    )

    with patch("app.database.AsyncSessionLocal", return_value=_DBContext(session)), patch(
        "app.services.message_translator.get_existing_inbound_translation_targets",
        AsyncMock(side_effect=[
            ({"en"}, "ja"),
            ({"ja"}, "en"),
            ({"ja"}, "es"),
        ]),
    ), patch(
        "app.services.message_translator.ensure_inbound_translations",
        AsyncMock(return_value={"en": missing_result}),
    ) as ensure_mock:
        result = await _run_batch()

    assert result["processed"] == 1
    assert result["failed"] == 0
    assert ensure_mock.await_count == 1
    assert ensure_mock.await_args.kwargs["message_id"] == "mid-es"
