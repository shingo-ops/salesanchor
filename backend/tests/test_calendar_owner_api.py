from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.routers.calendar import list_calendar_owners, update_calendar_owner


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
        result = await update_calendar_owner(7, body, tenant_id=1, user=_mock_user(), db=db)

    assert result.color == "#abcdef"
    assert result.is_visible is True
    assert result.share_mode == "edit"
    assert result.is_self is True
    assert "INSERT INTO calendar_owner_settings" in db.execute.call_args_list[2].args[0].text
