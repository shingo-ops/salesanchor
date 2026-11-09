"""連絡手段の名簿（channel_masters）API の単体テスト。

検証項目:
  1. 正常: 手動チャネルを追加できる
  2. 同じ platform の追加は 409 を返す
  3. auto チャネルの無効化は 400 を返す
  4. 共有チャネルの無効化は 403 を返す
  5. 他テナントのチャネルの無効化は 404 を返す

実行:
    pytest backend/tests/test_conv_logs_router.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_result(rows: list, scalar_value=None, first_value=None):
    m = MagicMock()
    m.fetchall.return_value = rows
    m.scalar_one.return_value = scalar_value
    m.scalar_one_or_none.return_value = scalar_value
    m.first.return_value = first_value
    return m


# ---------------------------------------------------------------------------
# テスト共通: router を直接呼ぶスタイル（httpx + app での統合テストは CI 用）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_channel_master_creates_manual_channel():
    """POST /admin/channel-masters: 手動チャネルが追加される。"""
    from app.routers.conv_logs import create_channel_master, ChannelMasterCreate

    mock_user = MagicMock()
    mock_user.id = 1

    mock_result = _make_mock_result([], scalar_value=77)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    body = ChannelMasterCreate(platform="whatsapp_personal", display_name="WhatsApp（個人）")

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.reset_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.channel_masters.get_channel", new=AsyncMock(return_value=None)),
    ):
        result = await create_channel_master(
            body=body,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    assert result == {"id": 77}
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_channel_master_duplicate_platform_returns_409():
    """POST /admin/channel-masters: 共用か自社に同じ platform が既にあれば 409。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import create_channel_master, ChannelMasterCreate

    mock_user = MagicMock()
    mock_user.id = 1
    mock_db = AsyncMock()
    body = ChannelMasterCreate(platform="whatsapp", display_name="WhatsApp")

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.channel_masters.get_channel", new=AsyncMock(
            return_value={"id": 12, "platform": "whatsapp", "is_shared": True}
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_channel_master(
                body=body,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 409
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_auto_channel_returns_400():
    """DELETE /admin/channel-masters/{id}: auto チャネルは削除不可（400）。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import deactivate_channel_master

    mock_user = MagicMock()
    mock_user.id = 1
    mock_db = AsyncMock()

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.channel_masters.get_channel_by_id", new=AsyncMock(
            return_value={"id": 3, "connection_type": "auto", "is_shared": True}
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await deactivate_channel_master(
                master_id=3,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 400
    assert "自動連携チャネル" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_deactivate_shared_channel_returns_403():
    """DELETE /admin/channel-masters/{id}: 共用の手入力チャネルは消せない（403）。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import deactivate_channel_master

    mock_user = MagicMock()
    mock_user.id = 1
    mock_db = AsyncMock()

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.channel_masters.get_channel_by_id", new=AsyncMock(
            return_value={"id": 10, "connection_type": "manual", "is_shared": True}
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await deactivate_channel_master(
                master_id=10,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 403
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_other_tenant_channel_returns_404():
    """DELETE /admin/channel-masters/{id}: 他社の行は見えず 404。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import deactivate_channel_master

    mock_user = MagicMock()
    mock_user.id = 1
    mock_db = AsyncMock()

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.channel_masters.get_channel_by_id", new=AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await deactivate_channel_master(
                master_id=999,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 404
