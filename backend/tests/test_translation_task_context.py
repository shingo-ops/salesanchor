"""
ADR-110 翻訳バッチの tenant context 付与テスト。

目的:
  - translate_pending_messages が各 tenant ごとに context を設定する
  - translate_inbound の commit 後に reset_tenant_context を再適用する
  - tenant 処理後に clear_tenant_context で払い落とす
  - translate_inbound_message（単発 webhook）も context を設定・解除する (③-b(5))
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


@pytest.mark.asyncio
async def test_translate_pending_messages_sets_and_resets_tenant_context():
    from app.tasks.translation import _run_batch

    db = AsyncMock()

    tenants_result = MagicMock()
    tenants_result.fetchall.return_value = [(1,), (2,)]

    tenant1_rows = MagicMock()
    tenant1_rows.fetchall.return_value = [("m-1", "hello"), ("m-2", "world")]

    tenant2_rows = MagicMock()
    tenant2_rows.fetchall.return_value = [("m-3", "bonjour")]

    db.execute = AsyncMock(side_effect=[tenants_result, tenant1_rows, tenant2_rows])

    with (
        patch("app.database.AsyncSessionLocal") as mock_session_cls,
        patch(
            "app.services.message_translator.get_existing_inbound_translation_targets",
            new=AsyncMock(side_effect=[
                ({"en"}, "ja"),
                ({"en"}, "ja"),
                ({"en"}, "ja"),
            ]),
        ),
        patch(
            "app.services.message_translator.get_required_inbound_targets",
            new=MagicMock(return_value={"ja"}),
        ),
        patch(
            "app.services.message_translator.ensure_inbound_translations",
            new=AsyncMock(return_value={}),
        ) as mock_ensure,
        patch("app.tasks.translation.set_tenant_context", new=AsyncMock()) as mock_set,
        patch("app.tasks.translation.reset_tenant_context", new=AsyncMock()) as mock_reset,
        patch("app.tasks.translation.clear_tenant_context", new=AsyncMock()) as mock_clear,
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_cm

        result = await _run_batch()

    assert result == {"processed": 3, "skipped": 0, "failed": 0}
    mock_set.assert_has_awaits([call(db, 1), call(db, 2)])
    assert mock_reset.await_count == 3
    mock_reset.assert_has_awaits([call(db, 1), call(db, 1), call(db, 2)])
    assert mock_clear.await_count == 2
    mock_ensure.assert_has_awaits(
        [
            call(
                db=db,
                tenant_id=1,
                table_ref="tenant_001.message_translations",
                message_id="m-1",
                message_text="hello",
            ),
            call(
                db=db,
                tenant_id=1,
                table_ref="tenant_001.message_translations",
                message_id="m-2",
                message_text="world",
            ),
            call(
                db=db,
                tenant_id=2,
                table_ref="tenant_002.message_translations",
                message_id="m-3",
                message_text="bonjour",
            ),
        ]
    )

@pytest.mark.asyncio
async def test_translate_inbound_message_sets_and_clears_tenant_context():
    """_run_translate_inbound_message が set_tenant_context → ensure → clear_tenant_context を呼ぶ。

    ③-b(5) の前提: RLS 有効化後も単発 webhook 翻訳が正しく号室を名乗り、
    完了後にコンテキストを払い落とすことを保証する。
    """
    from unittest.mock import call

    from app.tasks.translation import _run_translate_inbound_message

    db = AsyncMock()

    fake_result = {"ja": MagicMock(cached=False, engine="gemini-2.5-flash", confidence=0.95, translated_text="テスト")}

    with (
        patch("app.database.AsyncSessionLocal") as mock_session_cls,
        patch(
            "app.services.message_translator.ensure_inbound_translations",
            new=AsyncMock(return_value=fake_result),
        ) as mock_ensure,
        patch("app.tasks.translation.set_tenant_context", new=AsyncMock()) as mock_set,
        patch("app.tasks.translation.clear_tenant_context", new=AsyncMock()) as mock_clear,
        patch("app.services.sse_pubsub.publish_inbox_update", new=AsyncMock()),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_cm

        result = await _run_translate_inbound_message(
            tenant_id=4,
            table_ref="meta_messages",
            message_id="msg-001",
            message_text="Good morning",
            target_language="ja",
        )

    # tenant context が ensure_inbound_translations より先に設定される
    mock_set.assert_awaited_once_with(db, 4)
    # ensure_inbound_translations が正しい table_ref（message_translations）で呼ばれる
    mock_ensure.assert_awaited_once_with(
        db=db,
        tenant_id=4,
        table_ref="tenant_004.message_translations",
        message_id="msg-001",
        message_text="Good morning",
    )
    # clear_tenant_context が finally で必ず呼ばれる
    mock_clear.assert_awaited_once_with(db)
    assert result["status"] == "ok"
    assert result["tenant_id"] == 4
