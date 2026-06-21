"""受信翻訳の標準 enqueue 入口。"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def enqueue_inbound_translation(
    table_ref: str,
    message_id: str,
    message_text: str,
    *,
    tenant_id: int,
    target_language: str = "ja",
) -> bool:
    """受信翻訳 Celery タスクを enqueue する薄いラッパ。"""
    try:
        from app.tasks.translation import translate_inbound_message

        translate_inbound_message.delay(
            tenant_id=tenant_id,
            table_ref=table_ref,
            message_id=message_id,
            message_text=message_text,
            target_language=target_language,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[inbound_translation] enqueue failed tenant=%s table=%s msg=%s: %s",
            tenant_id,
            table_ref,
            message_id,
            exc,
            exc_info=True,
        )
        return False
