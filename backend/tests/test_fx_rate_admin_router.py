"""fx_rate_admin ルーターのテスト。

背景（2026-10-01）:
  本番で GET /api/v1/fx-rate/{currency} が app.routers.invoices.fetch_fx_rate と
  app.routers.fx_rate_admin.get_fx_rate の2系統で同一パス衝突しており、先に登録された
  invoices 側が常に応答し、ADR-148 SSOT 読み取りエンドポイントが到達不能だった。
  読み取りパスを /api/v1/fx-rates/{currency} に変更して衝突を解消した。

検証項目:
  1. app.routes に (method, path) の重複が無いこと（"fx-rate" を含むパス全体）
  2. GET /api/v1/fx-rates/{currency} が fx_rate_admin.get_fx_rate に解決されること
  3. GET /api/v1/fx-rates/USD が public.app_fx_rates の値から rate_jpy を返すこと
  4. 行が存在しない場合は 404 を返すこと
  5. invoices.py 側の GET /api/v1/fx-rate/{currency} は変更されていないこと（rate フィールド）

実行:
    pytest backend/tests/test_fx_rate_admin_router.py -v
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException


def _make_mock_result(mapping_first_value=None):
    m = MagicMock()
    mappings_result = MagicMock()
    mappings_result.first.return_value = mapping_first_value
    m.mappings.return_value = mappings_result
    return m


class TestRouteCollision:
    def test_no_duplicate_method_path_among_fx_rate_routes(self):
        """app.routes 内で 'fx-rate' を含む (method, path) の組に重複が無いこと。"""
        from app.main import app

        seen: set[tuple[str, str]] = set()
        duplicates: list[tuple[str, str]] = []
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if not path or "fx-rate" not in path or not methods:
                continue
            for method in methods:
                key = (method, path)
                if key in seen:
                    duplicates.append(key)
                seen.add(key)

        assert duplicates == [], f"重複した (method, path) が見つかりました: {duplicates}"

    def test_fx_rates_path_resolves_to_fx_rate_admin_get_fx_rate(self):
        """GET /api/v1/fx-rates/{currency} が fx_rate_admin.get_fx_rate に解決されること。"""
        from app.main import app
        from app.routers.fx_rate_admin import get_fx_rate as expected_endpoint

        matched = [
            route
            for route in app.routes
            if getattr(route, "path", None) == "/api/v1/fx-rates/{currency}"
            and "GET" in (getattr(route, "methods", None) or set())
        ]
        assert len(matched) == 1, f"ルートが一意に解決できません: {matched}"
        assert matched[0].endpoint is expected_endpoint

    def test_invoices_fx_rate_path_unchanged(self):
        """invoices.py 側の GET /api/v1/fx-rate/{currency} は変更されていないこと。"""
        from app.main import app
        from app.routers.invoices import fetch_fx_rate as expected_endpoint

        matched = [
            route
            for route in app.routes
            if getattr(route, "path", None) == "/api/v1/fx-rate/{currency}"
            and "GET" in (getattr(route, "methods", None) or set())
        ]
        assert len(matched) == 1, f"ルートが一意に解決できません: {matched}"
        assert matched[0].endpoint is expected_endpoint


class TestGetFxRate:
    @pytest.mark.asyncio
    async def test_returns_rate_jpy_from_app_fx_rates(self):
        """public.app_fx_rates に行がある場合、rate_jpy を含むレスポンスを返す。"""
        from app.routers.fx_rate_admin import get_fx_rate

        now = datetime(2026, 10, 1, 6, 0, 0, tzinfo=timezone.utc)
        row = {
            "currency": "USD",
            "rate_jpy": 150.25,
            "fetched_at": now,
            "updated_at": now,
        }
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_make_mock_result(row))
        mock_user = MagicMock()

        result = await get_fx_rate(currency="USD", db=mock_db, _user=mock_user)

        assert result.currency == "USD"
        assert result.rate_jpy == 150.25
        assert result.fetched_at == now.isoformat()
        assert result.updated_at == now.isoformat()

    @pytest.mark.asyncio
    async def test_404_when_row_missing(self):
        """行が存在しない場合は 404 を返す。"""
        from app.routers.fx_rate_admin import get_fx_rate

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_make_mock_result(None))
        mock_user = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_fx_rate(currency="USD", db=mock_db, _user=mock_user)

        assert exc_info.value.status_code == 404
