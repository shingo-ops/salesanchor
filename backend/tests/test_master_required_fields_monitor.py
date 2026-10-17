"""ADR-1020 便4c: 共用商品の必須項目の週次件数通知の単体テスト。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.schedules import crontab

from app.tasks.master_required_fields_monitor import _FIELDS, build_message

_ZERO = {f: 0 for f in _FIELDS}


def test_build_message_all_zero_is_ok_and_shows_marks():
    msg = build_message({**_ZERO, "new_rows": 3}, [("mark", 5), ("name_en", 5)])
    lines = msg.split("\n")
    assert lines[0].startswith("✅")
    assert "共用商品 3 件" in lines[0]
    assert "mark 5" in lines[2] and "name_en 5" in lines[2]


def test_build_message_with_ng_is_warning():
    msg = build_message({**_ZERO, "new_rows": 4, "work_id": 2}, [])
    lines = msg.split("\n")
    assert lines[0].startswith("⚠️")
    assert "work_id 2" in lines[1]


def test_build_message_no_marks():
    msg = build_message({**_ZERO, "new_rows": 0}, [])
    assert "0 件" in msg.split("\n")[2]


@pytest.mark.asyncio
async def test_run_report_posts_once():
    from app.tasks.master_required_fields_monitor import _run_report

    db = AsyncMock()
    count_result = MagicMock()
    count_result.mappings.return_value.one.return_value = {**_ZERO, "new_rows": 1}
    marks_result = MagicMock()
    marks_result.all.return_value = [("mark", 5)]
    db.execute = AsyncMock(side_effect=[count_result, marks_result])
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=db)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.database.AsyncSessionLocal", return_value=session_cm), \
         patch("app.tasks.master_required_fields_monitor._post_discord", new_callable=AsyncMock) as post:
        result = await _run_report()

    post.assert_awaited_once()
    assert "ADR-1020" in post.await_args.args[0].split("\n")[0]
    assert result["marks"] == [("mark", 5)]


def test_beat_schedule_registered_monday_9():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["report-master-required-fields-weekly"]
    assert entry["task"] == "app.tasks.master_required_fields_monitor.report_master_required_fields"
    import importlib
    importlib.import_module("app.tasks.master_required_fields_monitor")
    assert entry["task"] in celery_app.tasks
    sched = entry["schedule"]
    assert isinstance(sched, crontab)
    assert sched._orig_hour == 9 and sched._orig_minute == 0 and str(sched._orig_day_of_week) == "1"
