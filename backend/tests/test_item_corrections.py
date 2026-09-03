"""
PARITY-03 Phase 3 Stage 3: 修正履歴保存 API テスト。

カバー:
  - 認証なし → 401/403
  - POST /tcg/items/{extraction_item_id}/corrections 正常系
  - human_value が空のフィールドはスキップ
  - fields が空のリストでも ok=True / saved=0 を返す
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_EXTRACTION_ITEM_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_SOURCE_MESSAGE_ID = "bbbbbbbb-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# 共通フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def super_admin_override():
    from app.main import app
    from app.auth.dependencies import require_super_admin

    async def _bypass():
        return type("User", (), {"email": "admin@example.com", "is_super_admin": True})()

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


# ---------------------------------------------------------------------------
# 認証なし → 401/403
# ---------------------------------------------------------------------------


async def test_save_corrections_requires_auth():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            f"/api/v1/tcg/items/{_EXTRACTION_ITEM_ID}/corrections",
            json={
                "source_message_id": _SOURCE_MESSAGE_ID,
                "fields": [{"field_name": "name", "system_value": "SV1a", "human_value": "SV1a 修正"}],
            },
        )
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 正常系: 非空フィールドが保存される
# ---------------------------------------------------------------------------


async def test_save_corrections_ok(super_admin_override):
    from app.main import app

    with patch(
        "app.routers.item_corrections.save_corrections",
        new=AsyncMock(return_value={"saved": 2}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                f"/api/v1/tcg/items/{_EXTRACTION_ITEM_ID}/corrections",
                json={
                    "source_message_id": _SOURCE_MESSAGE_ID,
                    "fields": [
                        {"field_name": "name", "system_value": "SV1a", "human_value": "SV1a 修正"},
                        {"field_name": "quantity", "system_value": "1", "human_value": "2"},
                    ],
                },
            )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["saved"] == 2


# ---------------------------------------------------------------------------
# 正常系: fields が空リスト → saved=0
# ---------------------------------------------------------------------------


async def test_save_corrections_empty_fields(super_admin_override):
    from app.main import app

    with patch(
        "app.routers.item_corrections.save_corrections",
        new=AsyncMock(return_value={"saved": 0}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                f"/api/v1/tcg/items/{_EXTRACTION_ITEM_ID}/corrections",
                json={
                    "source_message_id": _SOURCE_MESSAGE_ID,
                    "fields": [],
                },
            )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["saved"] == 0


# ---------------------------------------------------------------------------
# human_value が空のフィールドはルーターでフィルタされ、svc には渡らない
# ---------------------------------------------------------------------------


async def test_save_corrections_filters_empty_human_value(super_admin_override):
    from app.main import app

    captured: list[dict] = []

    async def _capture(db, *, extraction_item_id, source_message_id, fields, corrected_by):
        captured.extend(fields)
        return {"saved": len(fields)}

    with patch(
        "app.routers.item_corrections.save_corrections",
        new=_capture,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                f"/api/v1/tcg/items/{_EXTRACTION_ITEM_ID}/corrections",
                json={
                    "source_message_id": _SOURCE_MESSAGE_ID,
                    "fields": [
                        {"field_name": "name", "system_value": "SV1a", "human_value": "修正"},
                        {"field_name": "quantity", "system_value": "1", "human_value": ""},
                        {"field_name": "price", "system_value": "5000", "human_value": "   "},
                    ],
                },
            )
    assert r.status_code == 200
    # 空 / 空白のみは除外されるので name のみ残る
    assert len(captured) == 1
    assert captured[0]["field_name"] == "name"
