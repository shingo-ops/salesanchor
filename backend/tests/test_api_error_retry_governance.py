"""
解析の送り直しを続ける仕組み（諦めた分の知らせ・月曜の数）の単体テスト。

design: docs/handoff/api-error-retry-governance/design.md（受入条件 T1〜T7）
DB・Redis・Discord はすべて偽物。
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from celery.schedules import crontab

from app.celery_app import celery_app
from app.tasks import api_error_retry_weekly as weekly
from app.tasks import tcg_extraction_recovery as recovery

EJ = "11111111-1111-1111-1111-111111111111"
EJ2 = "22222222-2222-2222-2222-222222222222"
NOW = datetime(2026, 10, 29, 0, 0, tzinfo=timezone.utc)


def _row(job_id=EJ, provider="仕入元A", code="503"):
    return {"id": job_id, "created_at": NOW, "reject_code": code, "provider": provider}


def _session_with(rows):
    session = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = [(r["id"], r["created_at"], r["reject_code"], r["provider"]) for r in rows]
    session.execute.return_value = result
    return session


class TestT1T2FindSql:
    def test_params_and_conditions(self):
        session = _session_with([])
        assert recovery.find_given_up_api_error_jobs(session) == []
        sql = str(session.execute.call_args.args[0])
        params = session.execute.call_args.args[1]
        assert ">= :max_attempts" in sql
        assert ":lookback_hours" in sql
        assert params["max_attempts"] == 3
        assert params["lookback_hours"] == 24
        assert params["window_hours"] == 48
        assert "ej.status = 'error'" in sql
        assert "ej.error_message = 'API_ERROR'" in sql
        for code in (429, 500, 502, 503, 504):
            assert f"LIKE '%(HTTP {code})'" in sql
        assert "HTTP 400" not in sql
        assert ":min_age" not in sql

    def test_rows_are_returned_as_dicts(self):
        rows = recovery.find_given_up_api_error_jobs(_session_with([_row()]))
        assert rows == [_row()]


def _redis(existing=()):
    client = MagicMock()
    client.exists.side_effect = lambda key: key in existing
    return client


def _notify(rows, *, url="https://example.invalid/hook", client=None, sent=True):
    post = AsyncMock(return_value=sent)
    with patch("app.services.discord_notifier._get_webhook_url", return_value=url), \
         patch("app.services.discord_notifier._post_discord_webhook", post), \
         patch.object(recovery, "_get_redis", return_value=client), \
         patch.object(recovery, "find_given_up_api_error_jobs", return_value=rows):
        return recovery.notify_given_up_api_error_jobs(MagicMock()), post


class TestT3Notify:
    def test_already_notified_job_is_skipped(self):
        client = _redis({f"{recovery.API_ERROR_GIVEN_UP_REDIS_PREFIX}{EJ}"})
        count, post = _notify([_row(EJ)], client=client)
        assert count == 0
        post.assert_not_called()
        client.set.assert_not_called()

    def test_send_failure_does_not_set_keys(self):
        client = _redis()
        count, post = _notify([_row(EJ)], client=client, sent=False)
        assert count == 0
        post.assert_called_once()
        client.set.assert_not_called()

    def test_success_sets_all_keys_with_ttl(self):
        client = _redis()
        count, post = _notify([_row(EJ), _row(EJ2)], client=client)
        assert count == 2
        post.assert_called_once()
        keys = {c.args[0] for c in client.set.call_args_list}
        assert keys == {f"{recovery.API_ERROR_GIVEN_UP_REDIS_PREFIX}{EJ}", f"{recovery.API_ERROR_GIVEN_UP_REDIS_PREFIX}{EJ2}"}
        assert all(c.kwargs["ex"] == 7 * 24 * 60 * 60 for c in client.set.call_args_list)


class TestT4Resilience:
    def test_empty_url_returns_zero(self):
        count, post = _notify([_row()], url=None, client=_redis())
        assert count == 0
        post.assert_not_called()

    def test_redis_none_returns_zero(self):
        count, post = _notify([_row()], client=None)
        assert count == 0
        post.assert_not_called()

    def test_find_exception_returns_zero(self):
        with patch("app.services.discord_notifier._get_webhook_url", return_value="https://example.invalid/h"), \
             patch.object(recovery, "_get_redis", return_value=_redis()), \
             patch.object(recovery, "find_given_up_api_error_jobs", side_effect=RuntimeError("db down")):
            assert recovery.notify_given_up_api_error_jobs(MagicMock()) == 0

    def test_run_recovery_result_has_keys(self):
        async def fake_reenqueue(ids):
            return {"enqueued": 0, "skipped": 0}

        with patch.object(recovery, "_get_sync_engine", return_value=MagicMock()), \
             patch.object(recovery, "sessionmaker", return_value=MagicMock()), \
             patch.object(recovery, "recover_stale_running_jobs", return_value=[]), \
             patch.object(recovery, "find_stale_pending_job_ids", return_value=[]), \
             patch.object(recovery, "retry_analysis_failed_jobs", return_value=[]), \
             patch.object(recovery, "retry_transient_api_error_jobs", return_value=[EJ]), \
             patch.object(recovery, "notify_given_up_api_error_jobs", return_value=2), \
             patch.object(recovery, "_reenqueue_stale_pending_jobs", fake_reenqueue):
            result = recovery._run_recovery()
        assert result["api_error_retry_count"] == 1
        assert result["given_up_notified"] == 2


class TestT5WeeklyMessage:
    def test_given_up_one_is_attention(self):
        assert weekly.build_message({"transient_jobs": 1, "recovered_jobs": 0, "given_up_jobs": 1}).startswith("⚠️ 要調査")

    def test_transient_20_is_attention(self):
        assert weekly.build_message({"transient_jobs": 20, "recovered_jobs": 20, "given_up_jobs": 0}).startswith("⚠️ 要調査")

    def test_transient_19_is_ok(self):
        assert weekly.build_message({"transient_jobs": 19, "recovered_jobs": 19, "given_up_jobs": 0}).startswith("✅")

    def test_zero_message_is_built(self):
        msg = weekly.build_message({})
        assert msg.startswith("✅")
        assert "0 件" in msg


class TestT6Beat:
    def test_beat_entry(self):
        entry = celery_app.conf.beat_schedule["report-api-error-retry-weekly"]
        assert entry["task"] == "app.tasks.api_error_retry_weekly.report_api_error_retry_weekly"
        expected = crontab(hour=9, minute=10, day_of_week=1)
        assert entry["schedule"] == expected


class TestT7GivenUpMessage:
    def test_limit_and_rest(self):
        rows = [_row(str(i), provider=f"店{i}") for i in range(11)]
        msg = recovery.build_given_up_message(rows)
        lines = msg.split("\n")
        assert "11 件" in lines[0]
        assert sum(1 for line in lines if line.startswith("・")) == 10
        assert "ほか 1 件" in lines
        assert lines[-1] == "要確認の画面で手でやり直してください。"
        assert "断られ方 503" in lines[1]
        assert "2026-10-29 09:00" in lines[1]


class TestT8T9T10WeeklySql:
    def test_no_string_concat_interval(self):
        sql = str(weekly._COUNT_SQL)
        assert "|| '" not in sql
        assert "make_interval(days => :days)" in sql
        assert "make_interval(hours => :lookback_hours)" in sql

    def test_params(self):
        params = weekly._params()
        assert params["prefix"].endswith("%")
        assert params["days"] == 7
        assert params["max_attempts"] == 3
        assert params["lookback_hours"] == 24

    def test_compiles_with_asyncpg_dialect_and_given_up_conditions(self):
        from sqlalchemy.dialects.postgresql import asyncpg

        compiled = str(weekly._COUNT_SQL.compile(dialect=asyncpg.dialect()))
        assert "sm.superseded_by IS NULL" in compiled
        assert "sm.is_active = TRUE" in compiled
        assert "latest.phase = 'failed'" in compiled


class TestT11RunReport:
    def test_run_report_sends_built_message(self):
        counts = {"transient_jobs": 3, "recovered_jobs": 2, "given_up_jobs": 1}
        result = MagicMock()
        result.mappings.return_value.one.return_value = counts
        db = MagicMock()
        db.execute = AsyncMock(return_value=result)
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=db)
        session_cm.__aexit__ = AsyncMock(return_value=False)
        post = AsyncMock(return_value=True)
        with patch("app.database.AsyncSessionLocal", return_value=session_cm), \
             patch.object(weekly, "_get_webhook_url", return_value="https://example.invalid/hook"), \
             patch.object(weekly, "_post_discord_webhook", post):
            out = asyncio.run(weekly._run_report())
        post.assert_called_once()
        assert post.call_args.args[1] == weekly.build_message(counts)
        assert out == {"counts": counts, "sent": True}
