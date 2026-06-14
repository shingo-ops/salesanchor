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
        patch("app.routers.conv_logs._get_company_id_for_lead", new=AsyncMock(return_value=None)),
        patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()),
        patch("app.routers.conv_logs._fire_translation", new=AsyncMock()),
    ):
        result = await create_conv_log(
            lead_id=10, body=body,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    assert result == {"id": 99}


@pytest.mark.asyncio
async def test_create_conv_log_company_id_in_insert():
    """deals に company_id がある lead の手動記録では INSERT に company_id が含まれる。"""
    from app.routers.conv_logs import create_conv_log, ConvLogCreate

    mock_user = MagicMock()
    mock_user.id = 1

    mock_result = _make_mock_result([], scalar_value=200)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    body = ConvLogCreate(
        channel_type="phone",
        content_text="確認電話",
        occurred_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
    )

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.reset_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._get_channel_master", new=AsyncMock(
            return_value={"id": 5, "platform": "phone", "display_name": "電話", "connection_type": "manual"}
        )),
        patch("app.routers.conv_logs._get_company_id_for_lead", new=AsyncMock(return_value=42)),
        patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()) as mock_audit,
        patch("app.routers.conv_logs._fire_translation", new=AsyncMock()),
    ):
        result = await create_conv_log(
            lead_id=10, body=body,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    assert result == {"id": 200}
    # INSERT の params に company_id=42 が含まれていることを確認
    insert_call_params = mock_db.execute.call_args[0][1]
    assert insert_call_params["company_id"] == 42
    # audit log の new_data にも company_id が含まれること
    audit_new_data = mock_audit.call_args[1]["new_data"]
    assert audit_new_data["company_id"] == 42


@pytest.mark.asyncio
async def test_create_conv_log_no_company_id_does_not_error():
    """deals に案件がない lead でも 500 にならず 201 で返る。company_id は None。"""
    from app.routers.conv_logs import create_conv_log, ConvLogCreate

    mock_user = MagicMock()
    mock_user.id = 1

    mock_result = _make_mock_result([], scalar_value=201)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    body = ConvLogCreate(
        channel_type="phone",
        content_text="案件なし lead へのログ",
        occurred_at=datetime(2026, 6, 11, tzinfo=timezone.utc),
    )

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.reset_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._get_channel_master", new=AsyncMock(
            return_value={"id": 5, "platform": "phone", "display_name": "電話", "connection_type": "manual"}
        )),
        patch("app.routers.conv_logs._get_company_id_for_lead", new=AsyncMock(return_value=None)),
        patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()),
        patch("app.routers.conv_logs._fire_translation", new=AsyncMock()),
    ):
        result = await create_conv_log(
            lead_id=99, body=body,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    assert result == {"id": 201}
    insert_call_params = mock_db.execute.call_args[0][1]
    assert insert_call_params["company_id"] is None


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


@pytest.mark.asyncio
async def test_create_conv_log_duplicate_returns_409():
    """重複チェック: 同一内容が近接日時に存在する場合 409 を返す。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import create_conv_log, ConvLogCreate

    mock_user = MagicMock()
    mock_user.id = 1

    # 重複行を返す mock: first() が (existing_id, existing_occurred_at) を返す
    dup_occurred = datetime(2026, 6, 11, 10, 0, tzinfo=timezone.utc)
    mock_dup_result = _make_mock_result([], first_value=(42, dup_occurred))
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_dup_result)

    body = ConvLogCreate(
        channel_type="phone",
        content_text="重複テスト内容",
        occurred_at=datetime(2026, 6, 11, 10, 30, tzinfo=timezone.utc),
    )

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._get_channel_master", new=AsyncMock(
            return_value={"id": 5, "platform": "phone", "display_name": "電話", "connection_type": "manual"}
        )),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await create_conv_log(
                lead_id=10, body=body,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "DUPLICATE_CONV_LOG"
    assert exc_info.value.detail["existing_id"] == 42


@pytest.mark.asyncio
async def test_create_conv_log_force_skips_duplicate_check():
    """allow_duplicate=True の場合、重複チェックをスキップして 201 を返す。"""
    from app.routers.conv_logs import create_conv_log, ConvLogCreate

    mock_user = MagicMock()
    mock_user.id = 1

    mock_result = _make_mock_result([], scalar_value=100)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    body = ConvLogCreate(
        channel_type="phone",
        content_text="強制保存テスト",
        occurred_at=datetime(2026, 6, 11, 10, 30, tzinfo=timezone.utc),
        allow_duplicate=True,
    )

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs.reset_tenant_context", new=AsyncMock()),
        patch("app.routers.conv_logs._get_channel_master", new=AsyncMock(
            return_value={"id": 5, "platform": "phone", "display_name": "電話", "connection_type": "manual"}
        )),
        patch("app.routers.conv_logs._get_company_id_for_lead", new=AsyncMock(return_value=None)),
        patch("app.routers.conv_logs.record_audit_log", new=AsyncMock()),
        patch("app.routers.conv_logs._fire_translation", new=AsyncMock()),
    ):
        result = await create_conv_log(
            lead_id=10, body=body,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    # 重複チェックをスキップして INSERT が実行され 201 が返る
    assert result == {"id": 100}
    # execute は INSERT のみ（重複チェック SELECT なし）
    mock_db.execute.assert_called_once()


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
    ):
        result = await create_channel_master(
            body=body,
            current_user=mock_user, tenant_id=1, db=mock_db,
        )

    assert result == {"id": 77}
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_deactivate_auto_channel_returns_400():
    """DELETE /admin/channel-masters/{id}: auto チャネルは削除不可（400）。"""
    from fastapi import HTTPException
    from app.routers.conv_logs import deactivate_channel_master

    mock_user = MagicMock()
    mock_user.id = 1

    # auto チャネルを返す mock
    mock_result = _make_mock_result([], first_value=(3, "auto"))
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with (
        patch("app.routers.conv_logs.set_tenant_context", new=AsyncMock()),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await deactivate_channel_master(
                master_id=3,
                current_user=mock_user, tenant_id=1, db=mock_db,
            )
    assert exc_info.value.status_code == 400
    assert "自動連携チャネル" in str(exc_info.value.detail)
