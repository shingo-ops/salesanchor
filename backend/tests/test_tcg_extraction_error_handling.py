"""
抽出エラー一覧の対応状況（handling_status）マッピングの単体テスト。

design: docs/handoff/extraction-error-handling-status/design.md §3, §7 (T1, T5)
DB不要。extraction_jobs.status → handling_status の SSOT 対応表のみを検証する。
"""
from __future__ import annotations

import logging

import pytest

from app.routers.tcg_analysis_dashboard import (
    _STATUS_TO_HANDLING,
    _handling_status,
    _job_statuses_for_handling,
)
from app.services.tcg_diagnostics_svc import _ELIGIBLE_STATUSES


@pytest.mark.parametrize(
    "job_status,expected",
    [
        ("error", "unhandled"),
        ("pending", "in_progress"),
        ("running", "in_progress"),
        ("done", "resolved"),
        ("empty", "resolved"),
        ("filtered", "resolved"),
    ],
)
def test_handling_status_matches_design_table(job_status, expected):
    """design §3 の対応表と一致すること（6状態すべて）。"""
    assert _handling_status(job_status) == expected


def test_unknown_status_defaults_to_unhandled_and_warns(caplog):
    """表にない状態は unhandled に入り、logger.warning が出ること。"""
    with caplog.at_level(logging.WARNING, logger="app.routers.tcg_analysis_dashboard"):
        result = _handling_status("some_future_status")
    assert result == "unhandled"
    assert any("some_future_status" in record.getMessage() for record in caplog.records)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_job_statuses_for_handling_round_trips_the_table():
    """逆引き（handling_status → job_status 一覧）が対応表と一致すること。"""
    assert set(_job_statuses_for_handling("unhandled")) == {"error"}
    assert set(_job_statuses_for_handling("in_progress")) == {"pending", "running"}
    assert set(_job_statuses_for_handling("resolved")) == {"done", "empty", "filtered"}
    # 対応表に載っている全 job_status が、いずれかの handling_status に一度だけ現れる
    all_job_statuses = [s for statuses in (
        _job_statuses_for_handling("unhandled"),
        _job_statuses_for_handling("in_progress"),
        _job_statuses_for_handling("resolved"),
    ) for s in statuses]
    assert sorted(all_job_statuses) == sorted(_STATUS_TO_HANDLING.keys())


def test_retry_eligible_statuses_is_error_only():
    """design §5: job_ids 指定時に受け付ける状態は 'error' だけ（pending/running は不可）。"""
    assert _ELIGIBLE_STATUSES == frozenset({"error"})
