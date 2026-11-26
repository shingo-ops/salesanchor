"""GET・PUT /calendar/preferences の試験（schedule-settings 便3b・設計 §3-3・受入条件 B2・B3・B5・B6）。

受け口の関数を、db を擬似にして直接呼ぶ。本物の PostgreSQL での確かめは test_calendar_owner_preferences_pg.py。
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth.dependencies import get_current_tenant
from app.routers.calendar import (
    CalendarPreferences,
    get_calendar_preferences,
    put_calendar_preferences,
)

_DEFAULTS = {
    "default_view": "week",
    "week_start": 0,
    "event_minutes": 60,
    "auto_meet": False,
    "open_owners": "self",
    "open_team_id": None,
}


class _Result:
    def __init__(self, *, first=None):
        self._first = first

    def first(self):
        return self._first

    def mappings(self):
        return self


def _user(user_id: int = 101):
    return SimpleNamespace(id=user_id, email="owner@example.com")


@pytest.mark.asyncio
async def test_get_without_a_row_returns_todays_behavior():
    """B2: 行が無い人は 週・日曜・60 分・Meet なし・自分だけ。"""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result(first=None))

    result = await get_calendar_preferences(tenant_id=1, current_user=_user(), db=db)

    assert result.model_dump() == _DEFAULTS


@pytest.mark.asyncio
async def test_get_reads_only_my_row():
    """B3: 読むのは current_user.id の行だけ。"""
    saved = {
        "default_view": "month", "week_start": 1, "event_minutes": 30,
        "auto_meet": True, "open_owners": "team", "open_team_id": 4,
    }
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result(first=saved))

    result = await get_calendar_preferences(tenant_id=1, current_user=_user(101), db=db)

    assert result.model_dump() == saved
    statement, params = db.execute.call_args.args
    assert "WHERE staff_id = :uid" in statement.text
    assert params == {"uid": 101}


@pytest.mark.asyncio
async def test_put_stores_and_returns_the_values():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    db.commit = AsyncMock()
    body = CalendarPreferences(default_view="list", week_start=1, event_minutes=15, auto_meet=True, open_owners="all")

    with patch("app.routers.calendar.reset_tenant_context", new=AsyncMock()):
        result = await put_calendar_preferences(body=body, tenant_id=1, current_user=_user(101), db=db)

    assert result.model_dump() == {
        "default_view": "list", "week_start": 1, "event_minutes": 15,
        "auto_meet": True, "open_owners": "all", "open_team_id": None,
    }
    statement, params = db.execute.call_args.args
    # B3: 書く先の人は current_user.id だけ（本体に利用者の欄は無い）
    assert params["uid"] == 101
    assert "uid" not in CalendarPreferences.model_fields and "staff_id" not in CalendarPreferences.model_fields
    # B4: 色は SET の中に入れない
    assert "color_key" not in statement.text
    assert "ON CONFLICT (staff_id) DO UPDATE SET" in statement.text


@pytest.mark.asyncio
async def test_put_resets_tenant_context_after_commit():
    """ADR-072: commit の直後に reset_tenant_context。"""
    order: list[str] = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    db.commit = AsyncMock(side_effect=lambda: order.append("commit"))
    reset = AsyncMock(side_effect=lambda *a, **k: order.append("reset"))

    with patch("app.routers.calendar.reset_tenant_context", new=reset):
        await put_calendar_preferences(body=CalendarPreferences(), tenant_id=7, current_user=_user(), db=db)

    assert order == ["commit", "reset"]
    reset.assert_awaited_once_with(db, 7)


@pytest.mark.asyncio
async def test_put_team_with_an_unusable_team_is_422_invalid_team():
    """B6: 使っていない・無いチームは 422 invalid_team。保存はしない。"""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result(first=None))
    db.commit = AsyncMock()
    body = CalendarPreferences(open_owners="team", open_team_id=99)

    with pytest.raises(HTTPException) as exc_info:
        await put_calendar_preferences(body=body, tenant_id=1, current_user=_user(), db=db)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid_team"
    db.commit.assert_not_awaited()
    assert db.execute.await_count == 1  # チームの確認だけ。書き込みの SQL は流れない


@pytest.mark.asyncio
async def test_put_team_without_a_team_id_is_422_invalid_team():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result(first=None))
    db.commit = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await put_calendar_preferences(
            body=CalendarPreferences(open_owners="team", open_team_id=None), tenant_id=1, current_user=_user(), db=db
        )

    assert exc_info.value.detail == "invalid_team"


@pytest.mark.asyncio
async def test_put_team_with_an_active_team_keeps_the_team_id():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_Result(first=(1,)), _Result()])
    db.commit = AsyncMock()

    with patch("app.routers.calendar.reset_tenant_context", new=AsyncMock()):
        result = await put_calendar_preferences(
            body=CalendarPreferences(open_owners="team", open_team_id=4), tenant_id=1, current_user=_user(), db=db
        )

    assert result.open_owners == "team" and result.open_team_id == 4
    assert db.execute.call_args_list[1].args[1]["open_team_id"] == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["self", "all"])
async def test_put_non_team_mode_stores_a_null_team(mode):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    db.commit = AsyncMock()

    with patch("app.routers.calendar.reset_tenant_context", new=AsyncMock()):
        result = await put_calendar_preferences(
            body=CalendarPreferences(open_owners=mode, open_team_id=4), tenant_id=1, current_user=_user(), db=db
        )

    assert result.open_team_id is None
    assert db.execute.call_args.args[1]["open_team_id"] is None
    assert db.execute.await_count == 1  # team 以外はチームの確認をしない


@pytest.mark.parametrize(
    "bad",
    [
        {"default_view": "year"},
        {"week_start": 2},
        {"event_minutes": 50},
        {"open_owners": "x"},
    ],
)
def test_out_of_range_values_are_refused_by_the_model(bad):
    """B5: 範囲外はモデルの時点で ValidationError（FastAPI はこれを 422 にする）。"""
    with pytest.raises(ValidationError):
        CalendarPreferences(**bad)


def test_defaults_equal_todays_behavior():
    assert CalendarPreferences().model_dump() == _DEFAULTS


def test_get_depends_on_get_current_tenant():
    """テナントの表を読むため、get_current_tenant で search_path を設定させる。"""
    default = inspect.signature(get_calendar_preferences).parameters["tenant_id"].default
    assert default.dependency is get_current_tenant
