from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.routers import calendar as calendar_router


def _mock_user(user_id: int = 1):
    return SimpleNamespace(id=user_id, email=f"user{user_id}@example.com", role="staff")


@pytest.mark.asyncio
async def test_calendar_events_other_user_requires_staff_view():
    app = FastAPI()
    app.include_router(calendar_router.router, prefix="/api/v1")

    async def override_get_db():
        yield AsyncMock()

    async def override_get_current_user():
        return _mock_user(1)

    async def override_get_current_tenant():
        return 999

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    with patch("app.routers.calendar.load_user_permissions", AsyncMock(return_value=set())):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/api/v1/calendar/events?start=2026-06-01T00:00:00Z&end=2026-06-30T23:59:59Z&user_id=2"
            )

    assert res.status_code == 403, res.text
    assert "他担当の予定を閲覧する権限がありません" in res.json()["detail"]


@pytest.mark.asyncio
async def test_calendar_events_other_user_allowed_for_staff_view():
    app = FastAPI()
    app.include_router(calendar_router.router, prefix="/api/v1")

    async def override_get_db():
        yield AsyncMock()

    async def override_get_current_user():
        return _mock_user(1)

    async def override_get_current_tenant():
        return 999

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    list_events_mock = AsyncMock(return_value=[{"id": 1}])
    with (
        patch("app.routers.calendar.load_user_permissions", AsyncMock(return_value={"staff.view"})),
        patch("app.routers.calendar.cal_svc.list_events", list_events_mock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/api/v1/calendar/events?start=2026-06-01T00:00:00Z&end=2026-06-30T23:59:59Z&user_id=2"
            )

    assert res.status_code == 200, res.text
    assert res.json() == {"events": [{"id": 1}]}
    list_events_mock.assert_awaited_once()
    kwargs = list_events_mock.await_args.kwargs
    assert kwargs["calendar_type"] == "personal"
    assert kwargs["user_id"] == 2
