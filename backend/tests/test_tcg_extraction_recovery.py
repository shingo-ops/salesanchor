"""
抽出ジョブの停滞回収タスクの単体テスト。

design: docs/handoff/extraction-job-recovery/design.md §C (T1〜T4)

DB を使わず session.execute をモックして、
「何件・どの ID を対象にしたか」「retry_extraction をどう呼ぶか」だけを検証する。
実データでの閾値挙動（15分未満は対象外・15分以上は対象）は
backend/tests/test_tcg_extraction_recovery_pg.py（CI 限定）で検証する。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks import tcg_extraction_recovery as recovery


class TestConstants:
    def test_stale_thresholds_are_15_minutes(self):
        """しきい値が15分であること（design.md §B の根拠: time_limit=330秒の倍以上）"""
        assert recovery.STALE_RUNNING_MINUTES == 15
        assert recovery.STALE_PENDING_MINUTES == 15

    def test_max_recover_per_run_is_50(self):
        """1回の上限が50件であること（retry_extraction 内部の _MAX_JOBS=50 と一致）"""
        assert recovery.MAX_RECOVER_PER_RUN == 50


class TestRecoverStaleRunningJobs:
    def test_no_rows_returns_empty_and_skips_update(self):
        """対象が無ければ UPDATE も commit も呼ばない（T1: 15分未満は触らない）"""
        session = MagicMock()
        session.execute.return_value.fetchall.return_value = []

        result = recovery.recover_stale_running_jobs(session)

        assert result == []
        assert session.execute.call_count == 1  # SELECT のみ
        session.commit.assert_not_called()

    def test_stale_rows_are_updated_to_pending(self):
        """対象ジョブが running→pending に更新されること（T2）"""
        job_id_1, job_id_2 = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
        session = MagicMock()
        select_result = MagicMock()
        select_result.fetchall.return_value = [(job_id_1,), (job_id_2,)]
        session.execute.side_effect = [select_result, MagicMock()]

        result = recovery.recover_stale_running_jobs(session)

        assert result == [job_id_1, job_id_2]
        assert session.execute.call_count == 2  # SELECT + UPDATE
        update_call = session.execute.call_args_list[1]
        update_sql = str(update_call.args[0])
        update_params = update_call.args[1]
        assert "UPDATE" in update_sql
        assert "status = 'pending'" in update_sql
        assert "status = 'running'" in update_sql
        assert update_params["ids"] == [job_id_1, job_id_2]
        session.commit.assert_called_once()

    def test_select_uses_stale_running_minutes_and_max_recover(self):
        """SELECT に STALE_RUNNING_MINUTES・MAX_RECOVER_PER_RUN が渡ること（T1/T3）"""
        session = MagicMock()
        session.execute.return_value.fetchall.return_value = []

        recovery.recover_stale_running_jobs(session)

        select_call = session.execute.call_args_list[0]
        params = select_call.args[1]
        assert params["stale_minutes"] == recovery.STALE_RUNNING_MINUTES
        assert params["max_recover"] == recovery.MAX_RECOVER_PER_RUN


class TestFindStalePendingJobIds:
    def test_no_rows_returns_empty(self):
        """対象が無ければ空リスト（T1）"""
        session = MagicMock()
        session.execute.return_value.fetchall.return_value = []

        result = recovery.find_stale_pending_job_ids(session)

        assert result == []

    def test_returns_job_ids_in_order(self):
        """対象ジョブの ID を古い順のまま返すこと"""
        job_id = "33333333-3333-3333-3333-333333333333"
        session = MagicMock()
        session.execute.return_value.fetchall.return_value = [(job_id,)]

        result = recovery.find_stale_pending_job_ids(session)

        assert result == [job_id]

    def test_select_uses_stale_pending_minutes_and_max_recover(self):
        """SELECT に STALE_PENDING_MINUTES・MAX_RECOVER_PER_RUN が渡ること（T1/T3）"""
        session = MagicMock()
        session.execute.return_value.fetchall.return_value = []

        recovery.find_stale_pending_job_ids(session)

        select_call = session.execute.call_args_list[0]
        params = select_call.args[1]
        assert params["stale_minutes"] == recovery.STALE_PENDING_MINUTES
        assert params["max_recover"] == recovery.MAX_RECOVER_PER_RUN


class TestReenqueuePending:
    async def test_empty_job_ids_skips_retry_extraction(self):
        """job_ids が空なら retry_extraction を呼ばない"""
        result = await recovery._reenqueue_pending([])
        assert result == {"enqueued": 0, "skipped": 0}

    async def test_calls_retry_extraction_with_scope_pending(self):
        """既存の retry_extraction(scope="pending") をそのまま呼ぶこと（新規ロジックを増やさない）"""
        mock_retry = AsyncMock(return_value={"enqueued": 3, "skipped": 0})
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.services.tcg_diagnostics_svc.retry_extraction", mock_retry), \
             patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine), \
             patch("sqlalchemy.ext.asyncio.async_sessionmaker") as mock_sessionmaker:
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__.return_value = MagicMock()
            mock_session_ctx.__aexit__.return_value = False
            mock_sessionmaker.return_value = MagicMock(return_value=mock_session_ctx)

            result = await recovery._reenqueue_pending(["job-1"])

        assert result == {"enqueued": 3, "skipped": 0}
        mock_retry.assert_called_once()
        _, kwargs = mock_retry.call_args
        assert kwargs["job_ids"] is None
        assert kwargs["scope"] == "pending"
        mock_engine.dispose.assert_called_once()


class TestCeleryTaskRegistration:
    def test_task_is_registered_in_beat_schedule(self):
        """beat_schedule に10分ごとで登録されていること（T4）"""
        from app.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "recover-stale-extraction-jobs" in schedule
        entry = schedule["recover-stale-extraction-jobs"]
        assert entry["task"] == "tcg.recover_stale_extraction_jobs"
        assert entry["schedule"] == 600.0

    def test_task_module_registered_in_include(self):
        """タスクモジュールが celery_app の include に登録されていること"""
        from app.celery_app import celery_app

        assert "app.tasks.tcg_extraction_recovery" in celery_app.conf.include
