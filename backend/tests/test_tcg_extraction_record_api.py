"""Authorization and input contracts on the real diagnostics router; no Gemini."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.routers import tcg_diagnostics as routes


@pytest.mark.asyncio
@pytest.mark.parametrize("role,expected", [(None, 401), (False, 403), (True, 200)])
@pytest.mark.parametrize("detail", [False, True])
async def test_attempts_require_actual_super_admin_dependency(monkeypatch, role, expected, detail):
    app = FastAPI()
    app.include_router(routes.router)

    async def user():
        if role is None:
            raise HTTPException(status_code=401)
        return SimpleNamespace(is_super_admin=role)

    async def db():
        yield AsyncMock()

    reader = AsyncMock(return_value={"attempts": []})
    monkeypatch.setattr(routes, "read_attempts", reader)
    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[get_db] = db
    path = f"/tcg/diagnostics/extraction-jobs/{uuid4()}/attempts"
    if detail:
        path += f"/{uuid4()}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
    assert response.status_code == expected
    if expected == 200:
        assert response.headers["cache-control"] == "no-store"
        reader.assert_awaited_once()
    else:
        reader.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["?limit=0", "?limit=101", "?offset=-1", "/not-a-uuid"])
async def test_pagination_and_ids_validated_before_query(monkeypatch, suffix):
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=True)
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    reader = AsyncMock()
    monkeypatch.setattr(routes, "read_attempts", reader)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/tcg/diagnostics/extraction-jobs/{uuid4()}/attempts{suffix}")
    assert response.status_code == 422
    reader.assert_not_awaited()
