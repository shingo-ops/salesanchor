"""
一時的に断られた解析の自動送り直し（単体テスト）。

design: docs/handoff/api-error-auto-retry/design.md（受け入れ基準 T1〜T9）
Gemini 呼び出し・time.sleep・time.monotonic・DB はすべて mock。実際には待たない。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import SoftTimeLimitExceeded

from app.services import line_analysis_v102_svc as svc
from app.services.tcg_extraction_record_svc import RecordError
from app.tasks import tcg_extraction_recovery as recovery

EJ = "11111111-1111-1111-1111-111111111111"
EJ2 = "22222222-2222-2222-2222-222222222222"


def _sqls(session):
    return [(str(c.args[0]), c.args[1] if len(c.args) > 1 else {}) for c in session.execute.call_args_list]


# ---------------------------------------------------------------------------
# すぐの送り直し（_call_gemini）
# ---------------------------------------------------------------------------


class _Env:
    """_call_gemini を mock だらけで呼ぶ小道具。"""

    def __init__(self, side_effect, monotonic=None):
        self.side_effect = side_effect
        self.monotonic = monotonic
        self.recorder = MagicMock()
        self.session = MagicMock()
        self.sleep = MagicMock()
        self.gemini = MagicMock(side_effect=side_effect)

    def run(self):
        ctx = MagicMock()
        patches = [
            patch.object(svc, "call_gemini_raw_copy_v8", self.gemini),
            patch.object(svc, "build_prompt_v8", return_value="p"),
            patch.object(svc, "without_legacy_supplier_fields", return_value={}),
            patch.object(svc, "effective_new_system_rules", return_value=[]),
            patch.object(svc.time, "sleep", self.sleep),
        ]
        if self.monotonic is not None:
            patches.append(patch.object(svc.time, "monotonic", side_effect=self.monotonic))
        for p in patches:
            p.start()
        try:
            return svc._call_gemini(self.session, ctx, "prompt", EJ, self.recorder)
        finally:
            for p in reversed(patches):
                p.stop()


def _http(code):
    return RuntimeError(f"{code} Service Unavailable. {{'error': 'overloaded'}}")


class TestT1ImmediateRetrySucceeds:
    def test_503_then_success(self):
        env = _Env([_http(503), {"ok": 1}])
        assert env.run() == {"ok": 1}
        env.recorder.record_error_detail.assert_not_called()
        env.sleep.assert_called_once_with(2)
        assert env.gemini.call_count == 2


class TestT2RetriesExhausted:
    def test_503_three_times_raises_api_error(self):
        env = _Env([_http(503), _http(503), _http(503)])
        with pytest.raises(RecordError) as ei:
            env.run()
        assert str(ei.value) == "API_ERROR" or getattr(ei.value, "code", None) == "API_ERROR"
        assert [c.args[0] for c in env.sleep.call_args_list] == [2, 8]
        assert env.gemini.call_count == 3
        env.recorder.record_error_detail.assert_called_once()
        detail = env.recorder.record_error_detail.call_args.args[0]
        assert detail["raw"].endswith("(HTTP 503)")


class TestT3NotRetried:
    @pytest.mark.parametrize(
        "exc",
        [
            RuntimeError("400 Bad Request"),
            RuntimeError("402 Payment Required"),
            RuntimeError("Deadline exceeded: timeout"),
            RuntimeError("connection reset"),
        ],
    )
    def test_single_call_then_api_error(self, exc):
        env = _Env([exc])
        with pytest.raises(RecordError):
            env.run()
        env.sleep.assert_not_called()
        assert env.gemini.call_count == 1
        env.recorder.record_error_detail.assert_called_once()

    def test_is_transient_http(self):
        for code in (429, 500, 502, 503, 504):
            assert svc._is_transient_http(_http(code))
        for code in (400, 402, 403, 501):
            assert not svc._is_transient_http(_http(code))
        assert not svc._is_transient_http(RuntimeError("timeout"))


class TestT4TimeBudget:
    def test_no_retry_after_90_seconds(self):
        # 開始 0 秒 → 断られた時点で 91 秒
        env = _Env([_http(503)], monotonic=[0.0, 91.0])
        with pytest.raises(RecordError):
            env.run()
        env.sleep.assert_not_called()
        assert env.gemini.call_count == 1

    def test_retry_within_budget(self):
        env = _Env([_http(503), {"ok": 1}], monotonic=[0.0, 30.0])
        assert env.run() == {"ok": 1}
        env.sleep.assert_called_once_with(2)


class TestT5SoftTimeLimitAndBeforeSend:
    def test_soft_time_limit_propagates_without_retry(self):
        env = _Env([SoftTimeLimitExceeded()])
        with pytest.raises(SoftTimeLimitExceeded):
            env.run()
        env.sleep.assert_not_called()
        env.recorder.record_error_detail.assert_not_called()

    def test_before_send_once_even_with_retries(self):
        env = _Env([_http(503), _http(503), {"ok": 1}])
        env.run()
        env.recorder.before_send.assert_called_once()
        env.session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 数分後の送り直し（retry_transient_api_error_jobs / _run_recovery）
# ---------------------------------------------------------------------------


def _session(ids, rowcounts=None, errors=None):
    session = MagicMock()
    select = MagicMock()
    select.fetchall.return_value = [(i,) for i in ids]
    effects = [select]
    for i in ids:
        if errors and i in errors:
            effects.append(errors[i])
            continue
        effects.append(MagicMock())  # items の削除
        effects.append(MagicMock(rowcount=(rowcounts or {}).get(i, 1)))  # pending に戻す UPDATE
    session.execute.side_effect = effects
    return session


class TestT6SelectConditions:
    def test_select_conditions(self):
        session = _session([])
        assert recovery.retry_transient_api_error_jobs(session) == []
        sql, params = _sqls(session)[0]
        for fragment in (
            "ej.status = 'error'",
            "ej.error_message = 'API_ERROR'",
            "ej.prompt_version LIKE :prefix",
            "ej.created_at > NOW()",
            "sm.is_active = TRUE",
            "sm.superseded_by IS NULL",
            "latest_attempt.phase = 'failed'",
            "latest_attempt.finished_at < NOW()",
            "'gemini_rate_limit', 'gemini_timeout'",
            "= 'gemini_http_error'",
            "LIMIT :max_retry",
            "< :max_attempts",
        ):
            assert fragment in sql, fragment
        for code in (429, 500, 502, 503, 504):
            assert f"LIKE '%(HTTP {code})'" in sql
        assert params == {
            "prefix": "v102:%",
            "lookback_hours": 24,
            "min_age": 5,
            "max_attempts": 3,
            "max_retry": 20,
        }


class TestT7ResetOrder:
    def test_delete_items_before_update_and_collects_id(self):
        session = _session([EJ])
        assert recovery.retry_transient_api_error_jobs(session) == [EJ]
        sqls = _sqls(session)
        assert "extraction_items" in sqls[1][0] and sqls[1][0].lstrip().startswith("DELETE")
        update_sql, update_params = sqls[2]
        assert "SET status = 'pending'" in update_sql
        assert "status = 'error'" in update_sql.split("WHERE")[1]
        assert "error_message = 'API_ERROR'" in update_sql.split("WHERE")[1]
        assert update_params == {"ej": EJ}
        session.commit.assert_called_once()

    def test_zero_rows_not_collected(self):
        session = _session([EJ], rowcounts={EJ: 0})
        assert recovery.retry_transient_api_error_jobs(session) == []
        session.rollback.assert_called()
        session.commit.assert_not_called()


class TestT8DedupAndFailureIsolation:
    def test_one_failure_does_not_stop_others(self):
        session = _session([EJ, EJ2], errors={EJ: RuntimeError("db down")})
        assert recovery.retry_transient_api_error_jobs(session) == [EJ2]
        session.rollback.assert_called()

    def _run(self, stale, api_error):
        engine = MagicMock()
        reenqueue = MagicMock(return_value=object())
        result_dict = {"enqueued": 1, "skipped": 0}

        async def fake_reenqueue(ids):
            reenqueue(ids)
            return result_dict

        with patch.object(recovery, "_get_sync_engine", return_value=engine), \
             patch.object(recovery, "sessionmaker", return_value=MagicMock()), \
             patch.object(recovery, "recover_stale_running_jobs", return_value=[]), \
             patch.object(recovery, "find_stale_pending_job_ids", return_value=stale), \
             patch.object(recovery, "retry_analysis_failed_jobs", return_value=[]), \
             patch.object(recovery, "retry_transient_api_error_jobs", return_value=api_error), \
             patch.object(recovery, "_reenqueue_stale_pending_jobs", fake_reenqueue):
            result = recovery._run_recovery()
        return result, reenqueue

    def test_overlapping_ids_enqueued_once_in_order(self):
        _, reenqueue = self._run([EJ, EJ2], [EJ2, "33333333-3333-3333-3333-333333333333"])
        reenqueue.assert_called_once_with([EJ, EJ2, "33333333-3333-3333-3333-333333333333"])

    def test_no_ids_no_enqueue(self):
        _, reenqueue = self._run([], [])
        reenqueue.assert_not_called()


class TestT9RunRecoveryResult:
    def test_result_keys(self):
        result, _ = TestT8DedupAndFailureIsolation()._run([EJ], [EJ2])
        assert result["api_error_retry_count"] == 1
        for key in (
            "recovered_running_count", "recovered_running_ids", "stale_pending_count", "stale_pending_ids",
            "reenqueued", "reenqueue_skipped", "analysis_retry_count",
        ):
            assert key in result
        assert result["stale_pending_ids"] == [EJ]
