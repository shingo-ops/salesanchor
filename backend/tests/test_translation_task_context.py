"""
ADR-110 翻訳バッチの tenant context 付与テスト。

目的:
  - translate_pending_messages が各 tenant ごとに context を設定する
  - translate_inbound の commit 後に reset_tenant_context を再適用する
  - tenant 処理後に clear_tenant_context で払い落とす
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
