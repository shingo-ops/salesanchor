"""fx_rate_updater Celery タスクのテスト（ADR-148 2026-10-03 追記・PR-B）。

public.app_fx_rates への UPSERT を廃止し、public.app_fx_rate_history への追記
（INSERT ... ON CONFLICT (currency, fetched_at) DO NOTHING）に切替えたことを検証する。

DB は sessionmaker をモックして検証する（実 DB 接続・Celery ブローカー不要）。
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_sessionmaker_factory():
    """sessionmaker(bind=engine) の戻り値（呼び出すと session のコンテキストマネージャを返す
    callable）を模擬する。呼び出された SQL を記録するため、session をテストから参照できるよう
    に返す。
    """
    mock_session = MagicMock()
    mock_session.execute = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    mock_sessionmaker_factory = MagicMock(return_value=mock_session)
    mock_sessionmaker_cls = MagicMock(return_value=mock_sessionmaker_factory)
    return mock_sessionmaker_cls, mock_session


class TestUpdateUsdJpyRate:
    def test_task_name_registered(self):
        from app.tasks.fx_rate_updater import update_usd_jpy_rate

        assert update_usd_jpy_rate.name == "app.tasks.fx_rate_updater.update_usd_jpy_rate"

    def test_success_inserts_into_history_with_on_conflict_do_nothing(self):
        """成功時: public.app_fx_rate_history への INSERT（ON CONFLICT (currency, fetched_at)
        DO NOTHING）を発行し、public.app_fx_rates は一切参照しないこと。"""
        from app.tasks.fx_rate_updater import update_usd_jpy_rate

        fetched_at = datetime(2026, 10, 3, 6, 0, 0, tzinfo=timezone.utc)
        mock_sessionmaker_cls, mock_session = _make_mock_sessionmaker_factory()

        with patch(
            "app.services.fx_rate.get_fx_rate",
            return_value={"currency": "USD", "rate": 150.25, "fetched_at": fetched_at},
        ), patch("app.tasks.fx_rate_updater._get_sync_engine", return_value=MagicMock()), patch(
            "app.tasks.fx_rate_updater.sessionmaker", mock_sessionmaker_cls
        ):
            update_usd_jpy_rate()

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

        executed_sqls = [str(call.args[0]) for call in mock_session.execute.call_args_list]
        assert any("SET app.is_operator = 'true'" in sql for sql in executed_sqls)
        insert_sqls = [sql for sql in executed_sqls if "INSERT INTO" in sql]
        assert len(insert_sqls) == 1
        assert "public.app_fx_rate_history" in insert_sqls[0]
        assert "ON CONFLICT (currency, fetched_at) DO NOTHING" in insert_sqls[0]
        assert "app_fx_rates" not in insert_sqls[0]
        # app_fx_rates は PR-B 以降どこからも参照しない
        assert all("app_fx_rates" not in sql or "app_fx_rate_history" in sql for sql in executed_sqls)

    def test_none_snapshot_is_non_fatal_and_skips_db(self):
        """get_fx_rate が None を返した場合（外部API障害）: DB に触れず正常終了する。"""
        from app.tasks.fx_rate_updater import update_usd_jpy_rate

        mock_engine_getter = MagicMock()
        with patch("app.services.fx_rate.get_fx_rate", return_value=None), patch(
            "app.tasks.fx_rate_updater._get_sync_engine", mock_engine_getter
        ):
            update_usd_jpy_rate()  # 例外を投げないこと

        mock_engine_getter.assert_not_called()

    def test_exception_from_get_fx_rate_is_non_fatal(self):
        """get_fx_rate が例外を投げた場合も non-fatal（タスクは正常終了する）。"""
        from app.tasks.fx_rate_updater import update_usd_jpy_rate

        with patch(
            "app.services.fx_rate.get_fx_rate", side_effect=ConnectionError("timeout")
        ):
            update_usd_jpy_rate()  # 例外を再 raise しない

    def test_duplicate_fetched_at_does_not_raise(self):
        """(currency, fetched_at) が既存行と重複する場合も ON CONFLICT DO NOTHING により
        例外を投げない（DB 層の重複キーエラーをモックで再現し、タスク内の except で rollback
        されるのではなく、SQL 自体が ON CONFLICT で解決する前提を明示する回帰テスト）。"""
        from app.tasks.fx_rate_updater import update_usd_jpy_rate

        fetched_at = datetime(2026, 10, 3, 6, 0, 0, tzinfo=timezone.utc)
        mock_sessionmaker_cls, mock_session = _make_mock_sessionmaker_factory()

        with patch(
            "app.services.fx_rate.get_fx_rate",
            return_value={"currency": "USD", "rate": 150.25, "fetched_at": fetched_at},
        ), patch("app.tasks.fx_rate_updater._get_sync_engine", return_value=MagicMock()), patch(
            "app.tasks.fx_rate_updater.sessionmaker", mock_sessionmaker_cls
        ):
            update_usd_jpy_rate()

        # ON CONFLICT DO NOTHING がSQL文に含まれているため、重複挿入でも DB 側で
        # エラーにならない前提（本テストは SQL 文の存在のみを保証する。実際の重複挙動は
        # CI の migration-test / 本番で検証）。
        insert_sqls = [
            str(call.args[0])
            for call in mock_session.execute.call_args_list
            if "INSERT INTO" in str(call.args[0])
        ]
        assert "DO NOTHING" in insert_sqls[0]
