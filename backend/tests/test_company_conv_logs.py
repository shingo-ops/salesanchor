"""SA-02 Stage 4: 会社別会話ログ API の単体テスト。

検証項目:
  1. 通常取得: company_id に紐づく deleted_at IS NULL のログが返る
  2. contact_id フィルタが SQL パラメータに渡る
  3. deleted_at IS NULL フィルタが SQL に含まれる
"""
from __future__ import annotations
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


@pytest.mark.asyncio
async def test_list_company_conv_logs_returns_logs():
    """company_id に紐づく会話ログが返る。"""
    from app.routers.companies import list_company_conv_logs

    mock_user = MagicMock()
    mock_user.id = 1

    # 1件のログを返す mock
    occurred = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc)
    mock_row = (42, 5, None, "phone", "inbound", "テスト内容", None, occurred, 1, "田中 太郎")
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.routers.companies.set_tenant_context", new=AsyncMock()),
        patch("app.routers.companies.reset_tenant_context", new=AsyncMock()),
    ):
        result = await list_company_conv_logs(
            company_id=10,
            contact_id=None,
            limit=100,
            current_user=mock_user,
            tenant_id=1,
            db=mock_db,
        )

    assert len(result) == 1
    assert result[0]["id"] == 42
    assert result[0]["channel_type"] == "phone"
    assert result[0]["contact_display_name"] == "田中 太郎"
    assert result[0]["occurred_at"] == occurred.isoformat()


@pytest.mark.asyncio
async def test_list_company_conv_logs_contact_filter():
    """contact_id フィルタが SQL クエリパラメータに渡される。"""
    from app.routers.companies import list_company_conv_logs

    mock_user = MagicMock()
    mock_user.id = 1

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.routers.companies.set_tenant_context", new=AsyncMock()),
        patch("app.routers.companies.reset_tenant_context", new=AsyncMock()),
    ):
        await list_company_conv_logs(
            company_id=10,
            contact_id=5,
            limit=100,
            current_user=mock_user,
            tenant_id=1,
            db=mock_db,
        )

    # execute が呼ばれ、contact_id=5 がパラメータに含まれる
    call_args = mock_db.execute.call_args[0][1]
    assert call_args.get("contact_id") == 5


@pytest.mark.asyncio
async def test_list_company_conv_logs_deleted_at_filter():
    """SQL クエリに deleted_at IS NULL フィルタが含まれる。"""
    from app.routers.companies import list_company_conv_logs
    from sqlalchemy import text as sa_text  # noqa: F401

    mock_user = MagicMock()
    mock_user.id = 1

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.routers.companies.set_tenant_context", new=AsyncMock()),
        patch("app.routers.companies.reset_tenant_context", new=AsyncMock()),
    ):
        await list_company_conv_logs(
            company_id=10,
            contact_id=None,
            limit=100,
            current_user=mock_user,
            tenant_id=1,
            db=mock_db,
        )

    # SQL テキストに deleted_at IS NULL が含まれる
    sql_text = str(mock_db.execute.call_args[0][0])
    assert "deleted_at IS NULL" in sql_text
