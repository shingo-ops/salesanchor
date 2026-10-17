"""
解析段の失敗を extraction_jobs.error_message に残し、1回だけ自動でやり直す（単体テスト）。

design: docs/handoff/analysis-failed-record/design.md
DB を使わず session.execute をモックして「どの SQL を何の引数で呼んだか」を検証する。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.tasks import tcg_extraction as te
from app.tasks import tcg_extraction_recovery as recovery

EJ = "11111111-1111-1111-1111-111111111111"


def _sqls(session):
    return [(str(c.args[0]), c.args[1] if len(c.args) > 1 else {}) for c in session.execute.call_args_list]


class TestT1AnalysisFailureRecorded:
    def _run(self, monkeypatch, analysis_side_effect):
        monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
        monkeypatch.setenv("TCG_AUTO_DISTRIBUTE", "1")
        session = MagicMock()
        recorder = MagicMock(id="att-1")
        with patch.object(te, "run_v102_extraction", return_value={"status": "done", "items_count": 3}), \
             patch.object(te, "run_v102_analysis", side_effect=analysis_side_effect), \
             patch.object(te, "_enqueue_auto_distribute") as dist:
            result = te._run_v102_extraction(session, EJ, recorder)
        return session, result, dist

    def test_analysis_exception_records_error_message_and_keeps_done(self, monkeypatch):
        session, result, dist = self._run(monkeypatch, RuntimeError("secret detail"))
        assert result["status"] == "done"
        assert result["analysis_stats"] == {"status": "error", "error_code": "ANALYSIS_FAILED"}
        sqls = _sqls(session)
        assert len(sqls) == 1
        sql, params = sqls[0]
        assert "SET error_message = :code" in sql and "status = 'done'" in sql
        assert "status =" not in sql.split("WHERE")[0]  # status は書き換えない
        assert params == {"code": "ANALYSIS_FAILED", "ej": EJ}
        assert "secret detail" not in str(sqls)  # 例外の中身は書かない
        session.rollback.assert_called()
        session.commit.assert_called_once()
        dist.assert_not_called()

    def test_record_write_failure_does_not_raise(self, monkeypatch):
        monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
        session = MagicMock()
        session.execute.side_effect = RuntimeError("db down")
        with patch.object(te, "run_v102_extraction", return_value={"status": "done", "items_count": 1}), \
             patch.object(te, "run_v102_analysis", side_effect=RuntimeError("x")):
            result = te._run_v102_extraction(session, EJ, MagicMock(id="a"))
        assert result["analysis_stats"]["error_code"] == "ANALYSIS_FAILED"

    def test_success_writes_nothing(self, monkeypatch):
        session, result, _ = self._run(monkeypatch, None)
        assert result["analysis_stats"] is not None
        assert _sqls(session) == []


class TestT2RecoveryRetry:
    def _session(self, ids, rowcounts=None):
        session = MagicMock()
        select = MagicMock()
        select.fetchall.return_value = [(i,) for i in ids]
        updates = [MagicMock(rowcount=(rowcounts or {}).get(i, 1)) for i in ids]
        session.execute.side_effect = [select, *updates]
        return session

    def test_select_conditions(self):
        session = self._session([])
        assert recovery.retry_analysis_failed_jobs(session) == []
        sql, params = _sqls(session)[0]
        assert "status = 'done'" in sql
        assert "error_message = 'ANALYSIS_FAILED'" in sql
        assert "prompt_version LIKE :prefix" in sql
        assert "extracted_at <" in sql
        assert params["prefix"] == "v102:%"
        assert params["min_age"] == 5
        assert params["max_retry"] == 20

    def test_marks_retried_then_enqueues_once(self):
        session = self._session([EJ])
        task = MagicMock()
        with patch.object(te, "v102_reanalyze_after_correction_task", task):
            assert recovery.retry_analysis_failed_jobs(session) == [EJ]
        sql, params = _sqls(session)[1]
        assert "SET error_message = 'ANALYSIS_FAILED_RETRIED'" in sql
        assert "error_message = 'ANALYSIS_FAILED'" in sql.split("WHERE")[1]
        assert params == {"ej": EJ}
        task.delay.assert_called_once_with(EJ)

    def test_second_run_does_not_enqueue(self):
        # 2回目の救済: SELECT は RETRIED を拾わないので 0 件 → delay されない
        session = self._session([])
        task = MagicMock()
        with patch.object(te, "v102_reanalyze_after_correction_task", task):
            assert recovery.retry_analysis_failed_jobs(session) == []
        task.delay.assert_not_called()

    def test_not_enqueued_when_update_hits_zero_rows(self):
        session = self._session([EJ], rowcounts={EJ: 0})
        task = MagicMock()
        with patch.object(te, "v102_reanalyze_after_correction_task", task):
            assert recovery.retry_analysis_failed_jobs(session) == []
        task.delay.assert_not_called()

    def test_delay_failure_does_not_raise(self):
        session = self._session([EJ])
        task = MagicMock()
        task.delay.side_effect = RuntimeError("redis down")
        with patch.object(te, "v102_reanalyze_after_correction_task", task):
            assert recovery.retry_analysis_failed_jobs(session) == []


class TestT3ReanalyzeClearsMark:
    def _call(self, prompt_version):
        session = MagicMock()
        session.execute.return_value.first.return_value = (prompt_version,)
        with patch.object(te, "_get_sync_session", return_value=session), \
             patch.object(te, "run_v102_analysis", return_value={"ok": 1}), \
             patch.object(te, "_publish_review_changed"), \
             patch.object(te, "schedule_distribution", return_value=False):
            result = te.reanalyze_v102_job(EJ)
        return session, result

    def test_success_clears_only_analysis_failed_marks(self):
        session, result = self._call("v102:raw_copy:abc")
        assert result["status"] == "reanalyzed"
        sql, params = _sqls(session)[1]
        assert "SET error_message = NULL" in sql
        assert "error_message IN ('ANALYSIS_FAILED', 'ANALYSIS_FAILED_RETRIED')" in sql
        assert params == {"ej": EJ}
        session.commit.assert_called_once()

    def test_failure_keeps_mark(self):
        session = MagicMock()
        session.execute.return_value.first.return_value = ("v102:x:y",)
        with patch.object(te, "_get_sync_session", return_value=session), \
             patch.object(te, "run_v102_analysis", side_effect=RuntimeError("boom")):
            try:
                te.reanalyze_v102_job(EJ)
            except RuntimeError:
                pass
        assert len(_sqls(session)) == 1  # prompt_version の SELECT のみ。クリア UPDATE は走らない
        session.commit.assert_not_called()

    def test_v6_job_is_skipped_without_update(self):
        session, result = self._call("v6-old")
        assert result["status"] == "skipped"
        assert len(_sqls(session)) == 1
