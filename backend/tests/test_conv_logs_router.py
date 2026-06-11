"""SA-02 Stage 3: conv_logs ルーターの単体テスト。

検証項目:
  1. auto チャネルへの手動記録作成は 400 を返す
  2. unknown チャネルへの手動記録作成は 400 を返す
  3. 正常: manual チャネルで手動記録を作成できる（201 + id）
  4. 削除済みログの更新は 410 を返す
  5. 正常: 手動記録を論理削除できる（deleted_at が SET される）

実行:
    pytest backend/tests/test_conv_logs_router.py -v
"""
from __future__ import annotations

from datetime import datetime, timezone
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
async def test_create_conv_log_auto_channel_rejected():
    """auto チャネル（messenger等）への手動記録は 400 を返す。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import create_conv_log, ConvLogCreate

    mock_user = MagicMock()
    mock_user.id = 1

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_make_mock_result(
        [],
        first_value=(1, "messenger", "Messenger", "auto"),
    ))

    body = ConvLogCreate(
        channel_type="messenger",
        content_text="test",
        occurred_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
    )

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._get_channel_master", new=AsyncMock(
            return_value={"id": 1, "platform": "messenger", "display_name": "Messenger", "connection_type": "auto"}
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_conv_log(
                lead_id=10, body=body,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 400
    assert "自動連携チャネル" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_conv_log_unknown_channel_rejected():
    """存在しないチャネルへの手動記録は 400 を返す。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import create_conv_log, ConvLogCreate

    mock_user = MagicMock()
    mock_user.id = 1

    mock_db = AsyncMock()
    body = ConvLogCreate(
        channel_type="unknown_platform",
        content_text="test",
        occurred_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
    )

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._get_channel_master", new=AsyncMock(return_value=None)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_conv_log(
                lead_id=10, body=body,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_conv_log_manual_channel_success():
    """manual チャネル（phone等）への手動記録は 201 + id を返す。"""
    from app.routers.conv_logs import create_conv_log, ConvLogCreate

    mock_user = MagicMock()
    mock_user.id = 1

    mock_result = _make_mock_result([], scalar_value=99)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    body = ConvLogCreate(
        channel_type="phone",
        content_text="電話で確認",
        occurred_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
    )

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.reset_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._get_channel_master", new=AsyncMock(
            return_value={"id": 5, "platform": "phone", "display_name": "電話", "connection_type": "manual"}
        )),
        patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()),
        patch("app.routers.conv_logs._fire_translation", new=AsyncMock()),
    ):
        result = await create_conv_log(
            lead_id=10, body=body,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    assert result == {"id": 99}


@pytest.mark.asyncio
async def test_update_deleted_log_returns_410():
    """削除済みログの更新は 410 を返す。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import update_conv_log, ConvLogUpdate

    mock_user = MagicMock()
    mock_user.id = 1
    mock_db = AsyncMock()

    body = ConvLogUpdate(content_text="modified")

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._fetch_conv_log", new=AsyncMock(
            return_value={
                "id": 5, "lead_id": 10, "channel_type": "phone",
                "content_text": "old", "occurred_at": datetime(2026, 6, 11, tzinfo=timezone.utc),
                "deleted_at": datetime(2026, 6, 11, 12, tzinfo=timezone.utc),  # 削除済み
                "recorded_by_user_id": 1,
            }
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await update_conv_log(
                lead_id=10, log_id=5, body=body,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 410


@pytest.mark.asyncio
async def test_delete_conv_log_sets_deleted_at():
    """delete 呼び出しで deleted_at が UPDATE される（204 = None返却）。"""
    from app.routers.conv_logs import delete_conv_log

    mock_user = MagicMock()
    mock_user.id = 1
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_make_mock_result([]))
    mock_db.commit = AsyncMock()

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.reset_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._fetch_conv_log", new=AsyncMock(
            return_value={
                "id": 5, "lead_id": 10, "channel_type": "phone",
                "content_text": "some text",
                "occurred_at": datetime(2026, 6, 11, tzinfo=timezone.utc),
                "deleted_at": None,  # 未削除
                "recorded_by_user_id": 1,
            }
        )),
        patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()),
    ):
        result = await delete_conv_log(
            lead_id=10, log_id=5,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    # 204 No Content: None を返す
    assert result is None
    mock_db.execute.assert_called_once()
    # UPDATE 文が実行され now（deleted_at の値）パラメータが渡されている
    call_kwargs = mock_db.execute.call_args[0][1]  # positional second arg = params dict
    assert "now" in call_kwargs  # deleted_at = :now で渡される
    assert "id" in call_kwargs
