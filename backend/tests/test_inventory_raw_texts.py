"""在庫表スライドの原文タブ API（GET /inventory/raw-texts）の試験。PostgreSQL 不要（DB は偽物）。原文・値はすべて架空。

B1: products.view が無いと 403・有ると 200
B2: 配信行（dist_base）に入る ID だけを問い合わせ、返らなければ 404
B3: 返すキーは4つだけ
B4: 0 件と 51 件は 422
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.models import User

_URL = "/api/v1/inventory/raw-texts"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, stmt, params=None):
        self.calls.append((str(stmt), dict(params or {})))
        return _Result(self.rows)


def _user() -> User:
    user = User()
    user.id = 321
    user.tenant_id = 6
    user.is_super_admin = False
    user.role = "sales"
    user.is_active = True
    return user


@asynccontextmanager
async def _client(*, perms: frozenset[str], db: _FakeDb | None = None):
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app

    fake = db or _FakeDb([])

    async def _db():
        yield fake

    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_tenant] = lambda: 6
    app.dependency_overrides[get_current_user] = _user
    try:
        with patch("app.auth.dependencies.load_user_permissions", AsyncMock(return_value=perms)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


def _ids(n: int) -> list[tuple[str, str]]:
    return [("extraction_item_ids", str(uuid4())) for _ in range(n)]


def _settings(value: dict):
    from app.routers import inventory_offers as io

    return patch.object(io, "load_distribution_settings", AsyncMock(return_value=value))


@pytest.mark.asyncio
async def test_b1_forbidden_without_products_view() -> None:
    async with _client(perms=frozenset({"customers.view"})) as client:
        res = await client.get(_URL, params=_ids(1))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_b1_allowed_with_products_view() -> None:
    item = str(uuid4())
    db = _FakeDb([{"extraction_item_id": item, "raw_text": "架空の原文", "line_start": 2, "line_end": 3}])
    async with _client(perms=frozenset({"products.view"}), db=db) as client:
        with _settings({"max_age_hours": "48"}):
            res = await client.get(_URL, params=[("extraction_item_ids", item)])
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_b2_query_is_limited_to_distribution_rows() -> None:
    item = str(uuid4())
    db = _FakeDb([{"extraction_item_id": item, "raw_text": "架空", "line_start": None, "line_end": None}])
    async with _client(perms=frozenset({"products.view"}), db=db) as client:
        with _settings({"max_age_hours": "48"}):
            res = await client.get(_URL, params=[("extraction_item_ids", item)])
    assert res.status_code == 200
    sql, params = db.calls[0]
    assert "dist_base AS (" in sql and "item_key = ANY(:raw_item_ids)" in sql
    assert params["raw_item_ids"] == [item] and params["max_age_hours"] == 48


@pytest.mark.asyncio
async def test_b2_not_found_when_no_distribution_row_matches() -> None:
    async with _client(perms=frozenset({"products.view"}), db=_FakeDb([])) as client:
        with _settings({"max_age_hours": "48"}):
            res = await client.get(_URL, params=_ids(2))
    assert res.status_code == 404
    assert res.json() == {"detail": "not_found"}


@pytest.mark.asyncio
async def test_b2_not_found_when_window_unset() -> None:
    db = _FakeDb([])
    async with _client(perms=frozenset({"products.view"}), db=db) as client:
        with _settings({}):
            res = await client.get(_URL, params=_ids(1))
    assert res.status_code == 404
    assert db.calls == []


@pytest.mark.asyncio
async def test_b3_returns_only_four_keys() -> None:
    item = str(uuid4())
    db = _FakeDb([{
        "extraction_item_id": item, "raw_text": "架空", "line_start": 1, "line_end": 2,
        "gemini": "x", "system_review_detail": "y", "provider": "z",
    }])
    async with _client(perms=frozenset({"products.view"}), db=db) as client:
        with _settings({"max_age_hours": "48"}):
            res = await client.get(_URL, params=[("extraction_item_ids", item)])
    body = res.json()
    assert set(body) == {"items"}
    assert set(body["items"][0]) == {"extraction_item_id", "raw_text", "line_start", "line_end"}


@pytest.mark.asyncio
@pytest.mark.parametrize("n", [0, 51])
async def test_b4_count_out_of_range_is_422(n: int) -> None:
    async with _client(perms=frozenset({"products.view"})) as client:
        res = await client.get(_URL, params=_ids(n))
    assert res.status_code == 422
