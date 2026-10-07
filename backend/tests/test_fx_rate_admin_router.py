"""fx_rate_admin ルーターのテスト。

背景（2026-10-01）:
  本番で GET /api/v1/fx-rate/{currency} が app.routers.invoices.fetch_fx_rate と
  app.routers.fx_rate_admin.get_fx_rate の2系統で同一パス衝突しており、先に登録された
  invoices 側が常に応答し、ADR-148 SSOT 読み取りエンドポイントが到達不能だった。
  読み取りパスを /api/v1/fx-rates/{currency} に変更して衝突を解消した。

背景（2026-10-03 追記・PR-B）:
  読み取り/書き込み先を public.app_fx_rates から public.app_fx_rate_history（追記専用・
  履歴テーブル）に切替えた。レスポンス形状（FxRateResponse）は維持し、updated_at は
  履行テーブルの created_at を転用する。

検証項目:
  1. app.routes に (method, path) の重複が無いこと（"fx-rate" を含むパス全体）
  2. GET /api/v1/fx-rates/{currency} が fx_rate_admin.get_fx_rate に解決されること
  3. GET /api/v1/fx-rates/USD が public.app_fx_rate_history の最新行から rate_jpy を返すこと
  4. 行が存在しない場合は 404 を返すこと
  5. invoices.py 側の GET /api/v1/fx-rate/{currency} は変更されていないこと（rate フィールド）

実行:
    pytest backend/tests/test_fx_rate_admin_router.py -v
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


def _make_mock_result(mapping_first_value=None):
    m = MagicMock()
    mappings_result = MagicMock()
    mappings_result.first.return_value = mapping_first_value
    m.mappings.return_value = mappings_result
    return m


def _make_mock_postgresql_db() -> MagicMock:
    """`MagicMock(spec=AsyncSession)` で postgresql dialect を模擬した db を作る。

    `app.auth.dependencies._dialect_supports_search_path` は
    `db.get_bind().dialect.name` を見て postgresql かどうかを判定する
    （backend/tests/test_adr072_phase_2_reset_rollout.py の sqlite 版と同じパターン）。
    `spec=AsyncSession` を使うことで `get_bind`（AsyncSession 上は同期メソッド）が
    coroutine ではなく実値を返すようにする。素の `AsyncMock()` では `get_bind()` が
    await されない coroutine を返してしまい、dialect 判定が常に False に落ちて
    `set_operator_context`/`reset_operator_context` の SET 文が発行されない。
    """
    mock_db = MagicMock(spec=AsyncSession)
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_db.get_bind.return_value = mock_bind
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    return mock_db


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
    async def test_returns_rate_jpy_from_app_fx_rate_history(self):
        """public.app_fx_rate_history に行がある場合、最新行の rate_jpy を含むレスポンスを返す。

        updated_at は履行テーブルの created_at（挿入時刻）を転用する。fetched_at と
        created_at に別の値を与えて、取り違えていないことを検証する。
        """
        from app.routers.fx_rate_admin import get_fx_rate

        fetched = datetime(2026, 10, 1, 6, 0, 0, tzinfo=timezone.utc)
        created = datetime(2026, 10, 1, 6, 0, 5, tzinfo=timezone.utc)
        row = {
            "currency": "USD",
            "rate_jpy": 150.25,
            "fetched_at": fetched,
            "created_at": created,
        }
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_make_mock_result(row))
        mock_user = MagicMock()

        result = await get_fx_rate(currency="USD", db=mock_db, _user=mock_user)

        assert result.currency == "USD"
        assert result.rate_jpy == 150.25
        assert result.fetched_at == fetched.isoformat()
        assert result.updated_at == created.isoformat()

        executed_sql = str(mock_db.execute.call_args.args[0])
        assert "app_fx_rate_history" in executed_sql
        assert "ORDER BY fetched_at DESC" in executed_sql
        assert "app_fx_rates" not in executed_sql

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


class TestRefreshFxRate:
    @pytest.mark.asyncio
    async def test_refresh_appends_to_history_and_returns_latest_row(self):
        """手動更新は app_fx_rate_history に追記し、再 SELECT した最新行を返す。

        db.execute() の呼び出し順は
        [SET app.is_operator='true', INSERT, SET app.is_operator='', SELECT]
        の4回（2026-10-03 追記: set_operator_context/reset_operator_context を
        INSERT の前後に追加したため、旧2回から増えた）。
        """
        from app.routers.fx_rate_admin import refresh_fx_rate

        fetched = datetime(2026, 10, 3, 9, 0, 0, tzinfo=timezone.utc)
        created = datetime(2026, 10, 3, 9, 0, 1, tzinfo=timezone.utc)
        row_after_insert = {
            "currency": "USD",
            "rate_jpy": 151.0,
            "fetched_at": fetched,
            "created_at": created,
        }

        mock_db = _make_mock_postgresql_db()
        set_op_result = MagicMock()
        insert_result = MagicMock()
        reset_op_result = MagicMock()
        select_result = _make_mock_result(row_after_insert)
        mock_db.execute = AsyncMock(
            side_effect=[set_op_result, insert_result, reset_op_result, select_result]
        )

        with patch(
            "app.services.fx_rate.get_fx_rate",
            return_value={"currency": "USD", "rate": 151.0, "fetched_at": fetched},
        ):
            result = await refresh_fx_rate(db=mock_db)

        assert result.rate_jpy == 151.0
        assert result.updated_at == created.isoformat()

        executed_sqls = [str(call.args[0]) for call in mock_db.execute.call_args_list]
        assert len(executed_sqls) == 4
        assert "SET app.is_operator = 'true'" in executed_sqls[0]
        assert "INSERT INTO public.app_fx_rate_history" in executed_sqls[1]
        assert "ON CONFLICT (currency, fetched_at) DO NOTHING" in executed_sqls[1]
        assert "app_fx_rates" not in executed_sqls[1]
        assert "SET app.is_operator = ''" in executed_sqls[2]
        assert "SELECT" in executed_sqls[3]
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_resets_operator_context_even_if_insert_raises(self):
        """INSERT が例外を投げても finally で reset_operator_context が呼ばれること
        （コネクションプール汚染防止、backend/app/auth/dependencies.py:437-451 と同方針）。"""
        from app.routers.fx_rate_admin import refresh_fx_rate

        fetched = datetime(2026, 10, 3, 9, 0, 0, tzinfo=timezone.utc)
        mock_db = _make_mock_postgresql_db()

        set_op_result = MagicMock()
        reset_op_result = MagicMock()

        async def _execute_side_effect(stmt, *args, **kwargs):
            sql = str(stmt)
            if "INSERT INTO" in sql:
                raise RuntimeError("db write failed")
            if "SET app.is_operator = 'true'" in sql:
                return set_op_result
            if "SET app.is_operator = ''" in sql:
                return reset_op_result
            raise AssertionError(f"unexpected SQL: {sql}")

        mock_db.execute = AsyncMock(side_effect=_execute_side_effect)

        with patch(
            "app.services.fx_rate.get_fx_rate",
            return_value={"currency": "USD", "rate": 151.0, "fetched_at": fetched},
        ):
            with pytest.raises(RuntimeError):
                await refresh_fx_rate(db=mock_db)

        executed_sqls = [str(call.args[0]) for call in mock_db.execute.call_args_list]
        assert "SET app.is_operator = 'true'" in executed_sqls[0]
        assert "INSERT INTO" in executed_sqls[1]
        # 例外後も finally で reset が呼ばれていること
        assert any("SET app.is_operator = ''" in sql for sql in executed_sqls[2:])
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_503_when_external_api_fails(self):
        """外部 API が None を返した場合は 503。operator コンテキストにも触れない。"""
        from app.routers.fx_rate_admin import refresh_fx_rate

        mock_db = _make_mock_postgresql_db()

        with patch("app.services.fx_rate.get_fx_rate", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_fx_rate(db=mock_db)

        assert exc_info.value.status_code == 503
        mock_db.execute.assert_not_called()
