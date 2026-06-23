"""
conv_logs._fire_translation の tenant context 付与テスト（③-b(6)）。

目的:
  - _fire_translation は reset_tenant_context 後に呼ばれるため、
    RLS 有効化後に message_translations へアクセスする前に
    set_tenant_context で号室を再設定することを保証する。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_fire_translation_sets_tenant_context_before_ensure():
    """_fire_translation が ensure_inbound_translations より先に set_tenant_context を呼ぶ。

    ③-b(6): reset_tenant_context 後の RLS バイパスを防ぐため、
    _fire_translation の try ブロック先頭で号室を再設定することを確認する。
    """
    from app.routers.conv_logs import _fire_translation

    db = AsyncMock()

    fake_result = MagicMock(
        translated_text="翻訳済みテキスト",
        original_language="en",
        confidence=0.95,
    )

    call_order: list[str] = []

    async def mock_set_tenant_context(db_, tid):
        call_order.append("set_tenant_context")

    async def mock_ensure(**kwargs):
        call_order.append("ensure_inbound_translations")
        return {"ja": fake_result}

    async def mock_reset_tenant_context(db_, tid):
        call_order.append("reset_tenant_context")

    with (
        patch(
            "app.routers.conv_logs.set_tenant_context",
            new=AsyncMock(side_effect=mock_set_tenant_context),
        ) as mock_set,
        patch(
            "app.services.message_translator.ensure_inbound_translations",
            new=AsyncMock(side_effect=mock_ensure),
        ) as mock_ensure_patch,
        patch(
            "app.routers.conv_logs.reset_tenant_context",
            new=AsyncMock(side_effect=mock_reset_tenant_context),
        ) as mock_reset,
    ):
        await _fire_translation(db=db, tenant_id=4, log_id=42, content_text="Hello")

    # set_tenant_context が ensure_inbound_translations より先に呼ばれている
    assert call_order[0] == "set_tenant_context", (
        f"set_tenant_context が先に呼ばれていない: {call_order}"
    )
    assert "ensure_inbound_translations" in call_order
    mock_set.assert_awaited_once_with(db, 4)
    mock_reset.assert_awaited_once_with(db, 4)
    # DB に translated_text が書き戻されること
    db.execute.assert_called_once()
    db.commit.assert_called_once()
