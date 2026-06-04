"""
ADR-107 §13 安全装置 — Celery タスク `run_priority_scoring_check` のユニットテスト。

Celery ブローカー・psycopg2・scripts/ モジュールはすべてモック。
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from unittest.mock import MagicMock, patch, call
from types import SimpleNamespace

import pytest

from app.tasks.priority_scoring_check import (
    _dispatch_notifications,
    _notify_task_failure,
    run_priority_scoring_check,
)


# ---------------------------------------------------------------------------
# ヘルパー: CheckResult スタブ
# ---------------------------------------------------------------------------

def _ok(name: str) -> SimpleNamespace:
    return SimpleNamespace(ok=True, name=name, message="ok", details={})


def _fail(name: str, details: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(ok=False, name=name, message="failed", details=details or {})


# ---------------------------------------------------------------------------
# _dispatch_notifications
# ---------------------------------------------------------------------------

class TestDispatchNotifications:
    """_NOTIFIER_AVAILABLE フラグと通知関数の振り分けテスト。"""

    def test_skips_when_notifier_unavailable(self):
        module = MagicMock()
        module._NOTIFIER_AVAILABLE = False
        failed = [_fail("data_volume")]

        # 通知関数は呼ばれない
        _dispatch_notifications(module, 1, failed)
        module.notify_priority_data_insufficient.assert_not_called()

    def test_dispatches_data_volume(self):
        mock_notify = MagicMock(return_value=None)  # sync stub
        module = SimpleNamespace(
            _NOTIFIER_AVAILABLE=True,
            notify_priority_data_insufficient=mock_notify,
            notify_priority_drift_detected=None,
            notify_priority_calibration_failed=None,
        )
        r = _fail("data_volume", {"message_count": 5, "deal_count": 2})

        with patch("app.tasks.priority_scoring_check.asyncio.run") as mock_run:
            _dispatch_notifications(module, 2, [r])
        mock_run.assert_called_once()

    def test_dispatches_drift(self):
        mock_notify = MagicMock(return_value=None)
        module = SimpleNamespace(
            _NOTIFIER_AVAILABLE=True,
            notify_priority_data_insufficient=None,
            notify_priority_drift_detected=mock_notify,
            notify_priority_calibration_failed=None,
        )
        r = _fail("drift", {"max_shift_pp": 25.0, "worst_tier": "top"})

        with patch("app.tasks.priority_scoring_check.asyncio.run") as mock_run:
            _dispatch_notifications(module, 3, [r])
        mock_run.assert_called_once()

    def test_dispatches_calibration_freshness(self):
        mock_notify = MagicMock(return_value=None)
        module = SimpleNamespace(
            _NOTIFIER_AVAILABLE=True,
            notify_priority_data_insufficient=None,
            notify_priority_drift_detected=None,
            notify_priority_calibration_failed=mock_notify,
        )
        r = _fail("calibration_freshness")

        with patch("app.tasks.priority_scoring_check.asyncio.run") as mock_run:
            _dispatch_notifications(module, 4, [r])
        mock_run.assert_called_once()

    def test_unknown_check_name_does_not_raise(self):
        """known でない check name は無視されること（例外なし）。"""
        module = SimpleNamespace(
            _NOTIFIER_AVAILABLE=True,
            notify_priority_data_insufficient=None,
            notify_priority_drift_detected=None,
            notify_priority_calibration_failed=None,
        )
        r = _fail("unknown_check")
        _dispatch_notifications(module, 5, [r])  # 例外なし

    def test_asyncio_run_exception_is_swallowed(self):
        """通知関数が例外を送出してもタスクが停止しないこと。"""
        module = SimpleNamespace(
            _NOTIFIER_AVAILABLE=True,
            notify_priority_data_insufficient=MagicMock(return_value=None),
            notify_priority_drift_detected=None,
            notify_priority_calibration_failed=None,
        )
        r = _fail("data_volume", {})

        with patch(
            "app.tasks.priority_scoring_check.asyncio.run",
            side_effect=RuntimeError("network error"),
        ):
            _dispatch_notifications(module, 6, [r])  # 例外なし


# ---------------------------------------------------------------------------
# _notify_task_failure
# ---------------------------------------------------------------------------

class TestNotifyTaskFailure:
    def test_calls_discord_notifier(self):
        with patch(
            "app.tasks.priority_scoring_check.asyncio.run"
        ) as mock_run, patch(
            "app.services.discord_notifier.notify_priority_calibration_failed",
            new=MagicMock(return_value=None),
        ):
            _notify_task_failure("some error")
        mock_run.assert_called_once()

    def test_import_error_is_swallowed(self):
        """discord_notifier がインポート不可でも例外を握り潰すこと。"""
        with patch.dict("sys.modules", {"app.services.discord_notifier": None}):
            _notify_task_failure("import failure")  # 例外なし


# ---------------------------------------------------------------------------
# run_priority_scoring_check (Celery タスク本体)
# ---------------------------------------------------------------------------

def _make_module_stub(results_per_tenant: list) -> MagicMock:
    """check_priority_scoring_state モジュールのスタブを返す。"""
    module = MagicMock()
    module._NOTIFIER_AVAILABLE = False
    module.run_all_checks = MagicMock(side_effect=lambda cur, tid: results_per_tenant)
    return module


def _make_psycopg2_mock(tenant_rows: list[dict]):
    """psycopg2 コネクション + カーソルのスタブを返す。"""
    cur = MagicMock()
    cur.fetchall.return_value = tenant_rows
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def _make_psycopg2_module_mock(tenant_rows: list[dict], conn_mock=None):
    """psycopg2 モジュールスタブと接続スタブを返す。"""
    cur = MagicMock()
    cur.fetchall.return_value = tenant_rows
    conn = conn_mock or MagicMock()
    conn.cursor.return_value = cur
    conn.autocommit = True

    mock_psycopg2 = MagicMock()
    mock_psycopg2.connect.return_value = conn
    mock_psycopg2.extras.RealDictCursor = object
    return mock_psycopg2, conn, cur


def _make_spec_stub(module: MagicMock):
    spec = MagicMock()
    spec.loader = MagicMock()
    spec.loader.exec_module = MagicMock()
    return spec


class TestRunPriorityScoringCheck:

    def test_all_tenants_all_ok(self):
        """全テナントのチェックが通過した場合、ok=True が返ること。"""
        module = _make_module_stub([_ok("calibration_freshness"), _ok("data_volume")])
        mock_psycopg2, conn, cur = _make_psycopg2_module_mock([{"id": 1}, {"id": 2}])
        spec = _make_spec_stub(module)

        import sys
        fake_modules = {
            "psycopg2": mock_psycopg2,
            "psycopg2.extras": mock_psycopg2.extras,
        }

        with patch("importlib.util.spec_from_file_location", return_value=spec), \
             patch("importlib.util.module_from_spec", return_value=module), \
             patch.dict(sys.modules, fake_modules), \
             patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"}):

            result = run_priority_scoring_check.run(tenant_id=None)

        assert result["ok"] is True
        assert result["checked_tenants"] == 2
        assert result["failed_checks"] == []

    def test_single_tenant_with_failure(self):
        """指定テナントでチェック失敗が発生した場合、failed_checks にエントリが入ること。"""
        module = _make_module_stub([_ok("data_volume"), _fail("drift", {"max_shift_pp": 30.0, "worst_tier": "top"})])
        mock_psycopg2, conn, cur = _make_psycopg2_module_mock([])
        spec = _make_spec_stub(module)

        import sys
        fake_modules = {
            "psycopg2": mock_psycopg2,
            "psycopg2.extras": mock_psycopg2.extras,
        }

        with patch("importlib.util.spec_from_file_location", return_value=spec), \
             patch("importlib.util.module_from_spec", return_value=module), \
             patch.dict(sys.modules, fake_modules), \
             patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"}):

            result = run_priority_scoring_check.run(tenant_id=7)

        assert result["ok"] is False
        assert result["checked_tenants"] == 1
        assert any("drift" in fc for fc in result["failed_checks"])

    def test_missing_database_url_raises(self):
        """DATABASE_URL が空の場合 RuntimeError が発生し、リトライされること。"""
        import sys
        module = MagicMock()
        spec = _make_spec_stub(module)
        mock_psycopg2 = MagicMock()
        fake_modules = {"psycopg2": mock_psycopg2, "psycopg2.extras": mock_psycopg2.extras}

        with patch("importlib.util.spec_from_file_location", return_value=spec), \
             patch("importlib.util.module_from_spec", return_value=module), \
             patch.dict(sys.modules, fake_modules), \
             patch.dict(os.environ, {"DATABASE_URL": ""}), \
             patch.object(run_priority_scoring_check, "retry", side_effect=RuntimeError("retry")):
            with pytest.raises(RuntimeError):
                run_priority_scoring_check.run()

    def test_script_not_found_raises(self):
        """spec_from_file_location が None を返した場合 RuntimeError が発生すること。"""
        import sys
        mock_psycopg2 = MagicMock()
        fake_modules = {"psycopg2": mock_psycopg2, "psycopg2.extras": mock_psycopg2.extras}

        with patch("importlib.util.spec_from_file_location", return_value=None), \
             patch.dict(sys.modules, fake_modules), \
             patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"}), \
             patch.object(run_priority_scoring_check, "retry", side_effect=RuntimeError("retry")):
            with pytest.raises(RuntimeError):
                run_priority_scoring_check.run()


# ---------------------------------------------------------------------------
# beat_schedule 登録確認
# ---------------------------------------------------------------------------

class TestBeatScheduleRegistration:
    def test_monthly_check_in_beat_schedule(self):
        """priority-scoring-monthly-check が beat_schedule に登録されていること。"""
        from app.celery_app import celery_app
        assert "priority-scoring-monthly-check" in celery_app.conf.beat_schedule

    def test_monthly_check_task_name(self):
        """タスク名が正しいこと。"""
        from app.celery_app import celery_app
        entry = celery_app.conf.beat_schedule["priority-scoring-monthly-check"]
        assert entry["task"] == "app.tasks.priority_scoring_check.run_priority_scoring_check"

    def test_priority_scoring_check_in_include(self):
        """priority_scoring_check モジュールが include リストにあること。"""
        from app.celery_app import celery_app
        assert "app.tasks.priority_scoring_check" in celery_app.conf.include
