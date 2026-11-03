from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from fastapi import HTTPException

from app.routers.calendar import (
    SyncModeBody,
    UpdateEventBody,
    delete_event,
    update_event,
    list_calendar_owners,
    update_calendar_owner,
    update_sync_mode,
)


class _QueryResult:
    def __init__(self, *, first=None, all_rows=None):
        self._first = first
        self._all_rows = all_rows or []

    def first(self):
        return self._first

    def all(self):
        return self._all_rows

    def mappings(self):
        return self


def _mock_user(user_id: int = 101, email: str = "owner@example.com"):
    return SimpleNamespace(id=user_id, email=email)


@pytest.mark.asyncio
async def test_list_calendar_owners_limits_non_manager_to_self():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _QueryResult(first={"id": 7, "tenant_id": 1, "user_id": 101, "staff_code": "A01", "surname_jp": "山田", "given_name_jp": "太郎", "primary_email": "owner@example.com"}),
            _QueryResult(all_rows=[
                {"id": 7, "user_id": 101, "staff_code": "A01", "surname_jp": "山田", "given_name_jp": "太郎", "primary_email": "owner@example.com", "color": None, "is_visible": None, "share_mode": None},
            ]),
        ]
    )

    with patch("app.routers.calendar.load_user_permissions", new=AsyncMock(return_value=set())):
        result = await list_calendar_owners(tenant_id=1, user=_mock_user(), db=db)

    assert result.can_manage_others is False
    assert result.current_staff_id == 7
    assert result.owners[0].is_self is True
    assert result.owners[0].name == "山田 太郎"
    assert result.owners[0].color == "#1a73e8"


@pytest.mark.asyncio
async def test_list_calendar_owners_manager_sees_others():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _QueryResult(first={"id": 7, "tenant_id": 1, "user_id": 101, "staff_code": "A01", "surname_jp": "山田", "given_name_jp": "太郎", "primary_email": "owner@example.com"}),
            _QueryResult(all_rows=[
                {"id": 7, "user_id": 101, "staff_code": "A01", "surname_jp": "山田", "given_name_jp": "太郎", "primary_email": "owner@example.com", "color": "#111111", "is_visible": True, "share_mode": "edit"},
                {"id": 8, "user_id": 202, "staff_code": "B02", "surname_jp": "佐藤", "given_name_jp": "花子", "primary_email": "other@example.com", "color": "#222222", "is_visible": False, "share_mode": "view"},
            ]),
        ]
    )

    with patch("app.routers.calendar.load_user_permissions", new=AsyncMock(return_value={"staff.view"})):
        result = await list_calendar_owners(tenant_id=1, user=_mock_user(), db=db)

    assert result.can_manage_others is True
    assert [owner.staff_code for owner in result.owners] == ["A01", "B02"]
    assert result.owners[1].is_self is False
    assert result.owners[1].share_mode == "view"


@pytest.mark.asyncio
async def test_update_calendar_owner_requires_staff_view():
    db = AsyncMock()

    with patch("app.routers.calendar.load_user_permissions", new=AsyncMock(return_value=set())):
        with pytest.raises(Exception) as exc_info:
            await update_calendar_owner(7, SimpleNamespace(color="#123456", is_visible=True, share_mode="view"), tenant_id=1, user=_mock_user(), db=db)

    assert getattr(exc_info.value, "status_code", None) == 403


@pytest.mark.asyncio
async def test_update_calendar_owner_updates_only_provided_fields():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _QueryResult(first=(1,)),
            _QueryResult(first={"id": 7, "tenant_id": 1, "user_id": 101, "staff_code": "A01", "surname_jp": "山田", "given_name_jp": "太郎", "primary_email": "owner@example.com"}),
            _QueryResult(first=None),
            _QueryResult(first={"id": 7, "user_id": 101, "staff_code": "A01", "surname_jp": "山田", "given_name_jp": "太郎", "primary_email": "owner@example.com", "color": "#abcdef", "is_visible": True, "share_mode": "edit"}),
        ]
    )

    body = SimpleNamespace(color="#abcdef", is_visible=True, share_mode="edit")
    with patch("app.routers.calendar.load_user_permissions", new=AsyncMock(return_value={"staff.view"})):
        result = await update_calendar_owner(101, body, tenant_id=1, user=_mock_user(), db=db)

    assert result.color == "#abcdef"
    assert result.is_visible is True
    assert result.share_mode == "edit"
    assert result.is_self is True
    assert "INSERT INTO calendar_owner_settings" in db.execute.call_args_list[2].args[0].text
    # ADR-1008 P2: パス引数は users.id。名簿は user_id で引き、設定の staff_id 列には users.id を入れる
    assert db.execute.call_args_list[0].args[1] == {"user_id": 101}
    assert db.execute.call_args_list[2].args[1]["staff_id"] == 101


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["bidirectional", "read_only"])
async def test_update_sync_mode_accepts_inbound_modes_and_registers_webhook(mode):
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    with patch("app.routers.calendar.reset_tenant_context", AsyncMock()), patch(
        "app.services.google_webhook.register_webhook",
        AsyncMock(return_value={"channel_id": "c"}),
    ) as reg, patch("app.services.google_webhook.stop_webhook", AsyncMock()) as stop, patch(
        "app.tasks.google_calendar_sync.sync_google_calendar_tenant.delay"
    ) as delay:
        result = await update_sync_mode(
            body=SyncModeBody(sync_mode=mode), tenant_id=1, user=_mock_user(), db=db
        )
    assert result == {"sync_mode": mode}
    reg.assert_called_once()
    stop.assert_not_called()
    delay.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_update_sync_mode_write_only_stops_webhook():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    with patch("app.routers.calendar.reset_tenant_context", AsyncMock()), patch(
        "app.services.google_webhook.register_webhook", AsyncMock()
    ) as reg, patch("app.services.google_webhook.stop_webhook", AsyncMock()) as stop:
        result = await update_sync_mode(
            body=SyncModeBody(sync_mode="write_only"), tenant_id=1, user=_mock_user(), db=db
        )
    assert result == {"sync_mode": "write_only"}
    stop.assert_called_once()
    reg.assert_not_called()


@pytest.mark.asyncio
async def test_update_sync_mode_none():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    with patch("app.routers.calendar.reset_tenant_context", AsyncMock()), patch(
        "app.services.google_webhook.stop_webhook", AsyncMock()
    ):
        result = await update_sync_mode(
            body=SyncModeBody(sync_mode="none"), tenant_id=1, user=_mock_user(), db=db
        )
    assert result == {"sync_mode": "none"}


# ---- 便1: 「自分だけ」予定の守り（design.md §13-5） ----


def _event_db(created_by, calendar_type, owner):
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=_QueryResult(first=(created_by, calendar_type, owner)))
    return db


@pytest.mark.asyncio
@pytest.mark.parametrize("is_admin", [False, True])
async def test_patch_other_users_personal_event_is_404(is_admin):
    db = _event_db(created_by=202, calendar_type="personal", owner=202)
    with patch("app.routers.calendar.get_user_system_keys", new=AsyncMock(return_value=[])), patch(
        "app.routers.calendar.is_tenant_admin", return_value=is_admin
    ), patch("app.routers.calendar.cal_svc.update_event", new=AsyncMock()) as upd:
        with pytest.raises(HTTPException) as exc:
            await update_event(9, UpdateEventBody(title="x"), tenant_id=1, user=_mock_user(101), db=db)
    assert exc.value.status_code == 404
    upd.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("is_admin", [False, True])
async def test_delete_other_users_personal_event_is_404(is_admin):
    db = _event_db(created_by=202, calendar_type="personal", owner=202)
    with patch("app.routers.calendar.get_user_system_keys", new=AsyncMock(return_value=[])), patch(
        "app.routers.calendar.is_tenant_admin", return_value=is_admin
    ), patch("app.routers.calendar.cal_svc.delete_event", new=AsyncMock()) as dele:
        with pytest.raises(HTTPException) as exc:
            await delete_event(9, tenant_id=1, user=_mock_user(101), db=db)
    assert exc.value.status_code == 404
    dele.assert_not_called()


@pytest.mark.asyncio
async def test_non_owner_cannot_change_calendar_type():
    # 共有の予定を作った人（created_by=101）だが、持ち主（user_id）は 202
    db = _event_db(created_by=101, calendar_type="shared", owner=202)
    with patch("app.routers.calendar.get_user_system_keys", new=AsyncMock(return_value=[])), patch(
        "app.routers.calendar.is_tenant_admin", return_value=False
    ), patch("app.routers.calendar.cal_svc.update_event", new=AsyncMock()) as upd:
        with pytest.raises(HTTPException) as exc:
            await update_event(9, UpdateEventBody(calendar_type="personal"), tenant_id=1, user=_mock_user(101), db=db)
    assert exc.value.status_code == 403
    upd.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_type,expect_user_id", [("personal", 101), ("shared", None)])
async def test_owner_can_switch_calendar_type(new_type, expect_user_id):
    old = "shared" if new_type == "personal" else "personal"
    db = _event_db(created_by=101, calendar_type=old, owner=101)
    with patch("app.routers.calendar.get_user_system_keys", new=AsyncMock(return_value=[])), patch(
        "app.routers.calendar.is_tenant_admin", return_value=False
    ), patch("app.routers.calendar.cal_svc.update_event", new=AsyncMock(return_value={"id": 9})) as upd:
        result = await update_event(9, UpdateEventBody(calendar_type=new_type), tenant_id=1, user=_mock_user(101), db=db)
    assert result == {"id": 9}
    payload = upd.call_args.kwargs["payload"]
    assert payload["calendar_type"] == new_type
    assert payload.get("user_id") == expect_user_id


@pytest.mark.asyncio
async def test_invalid_calendar_type_is_422():
    db = _event_db(created_by=101, calendar_type="shared", owner=101)
    with patch("app.routers.calendar.get_user_system_keys", new=AsyncMock(return_value=[])), patch(
        "app.routers.calendar.is_tenant_admin", return_value=False
    ):
        with pytest.raises(HTTPException) as exc:
            await update_event(9, UpdateEventBody(calendar_type="secret"), tenant_id=1, user=_mock_user(101), db=db)
    assert exc.value.status_code == 422
