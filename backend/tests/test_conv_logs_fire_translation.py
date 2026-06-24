"""
conv_logs._fire_translation のテスト。

テスト一覧:
  - test_fire_translation_sets_tenant_context_before_ensure: ③-b(6) RLS コンテキスト順序
  - test_fire_translation_skips_outbound: outbound では ensure_inbound_translations を呼ばない
  - test_fire_translation_fires_for_inbound: inbound では従来どおり翻訳が発火する
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


@pytest.mark.asyncio
async def test_fire_translation_skips_outbound():
    """outbound を渡すと ensure_inbound_translations が呼ばれない（早期リターン）。

    バグC-1 修正: outbound は inbound 専用翻訳 API を呼ばない。
    DB への書き戻し（translated_text / original_language）も発生しない。
    """
    from app.routers.conv_logs import _fire_translation

    db = AsyncMock()

    with patch(
        "app.routers.conv_logs.set_tenant_context",
        new=AsyncMock(),
    ) as mock_set:
        with patch(
            "app.services.message_translator.ensure_inbound_translations",
            new=AsyncMock(),
        ) as mock_ensure:
            await _fire_translation(
                db=db, tenant_id=4, log_id=99, content_text="Hello", direction="outbound"
            )

    mock_ensure.assert_not_awaited()
    mock_set.assert_not_awaited()
    db.execute.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_fire_translation_fires_for_inbound():
    """inbound を渡すと ensure_inbound_translations が従来どおり呼ばれる。

    バグC-1 修正後も inbound 挙動が壊れていないことを確認。
    """
    from app.routers.conv_logs import _fire_translation

    db = AsyncMock()

    fake_result = MagicMock(
        translated_text="Hello",
        original_language="en",
        confidence=0.90,
    )

    with (
        patch(
            "app.routers.conv_logs.set_tenant_context",
            new=AsyncMock(),
        ),
        patch(
            "app.services.message_translator.ensure_inbound_translations",
            new=AsyncMock(return_value={"ja": fake_result}),
        ) as mock_ensure,
        patch(
            "app.routers.conv_logs.reset_tenant_context",
            new=AsyncMock(),
        ),
    ):
        await _fire_translation(
            db=db, tenant_id=4, log_id=10, content_text="Hello", direction="inbound"
        )

    mock_ensure.assert_awaited_once()
    db.execute.assert_called_once()
    db.commit.assert_called_once()
