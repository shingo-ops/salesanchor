from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.inbound_translation import enqueue_inbound_translation


def test_enqueue_inbound_translation_calls_delay_with_expected_args():
    delay_mock = MagicMock(return_value=None)

    with patch("app.tasks.translation.translate_inbound_message.delay", delay_mock):
        result = enqueue_inbound_translation(
            "meta_messages",
            "mid-1",
            "hello",
            tenant_id=7,
        )

    assert result is True
    delay_mock.assert_called_once_with(
        tenant_id=7,
        table_ref="meta_messages",
        message_id="mid-1",
        message_text="hello",
        target_language="ja",
    )


def test_enqueue_inbound_translation_swallows_enqueue_errors():
    with patch(
        "app.tasks.translation.translate_inbound_message.delay",
        side_effect=RuntimeError("redis down"),
    ):
        result = enqueue_inbound_translation(
            "meta_messages",
            "mid-2",
            "hello",
            tenant_id=7,
        )

    assert result is False
