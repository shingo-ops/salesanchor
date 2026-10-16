"""build_distribution_rows の切り出し（ADR-1019 段2・設計 D3）の試験。DB は mock。

run_distribution の4つの早期 return は、切り出し前と同じ文言・同じ形・同じログ水準であること。
文言は切り出し前の実装の文字列をここに直書きして比べる。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import tcg_distribution_svc as svc

_RUN_ID = "11111111-0000-0000-0000-000000000001"
_STARTED = datetime(2026, 9, 4, 0, 59, 0, tzinfo=timezone.utc)


def _result(rows: list) -> MagicMock:
    res = MagicMock()
    res.mappings.return_value.all.return_value = rows
    return res


def _db(*results: list) -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_result(r) for r in results])
    return db


# 切り出し前の run_distribution が返していた文言（直書き）
_MSG_8 = (
    "安全装置 #8: 再解析未完了の runs が 1 件あります。"
    " 完了を待ってから配信を実行してください。"
    f"未完了: [{{'run_id': '{_RUN_ID}', 'started_at': '2026-09-04T00:59:00+00:00'}}]"
)
_MSG_8B = (
    "安全装置 #8b: 未完了の extraction_jobs が 3 件あります。"
    " 完了を待ってから配信を実行してください。内訳: {'pending': 2, 'running': 1}"
)
_MSG_UNSET = "max_age_hours 未設定のため配信しない"
_MSG_FETCH = "出力データ取得失敗: boom"
_EXPECTED_KEYS = {"run_id", "started_at", "output_count", "results", "errors"}


def _case_8():
    return _db([{"id": _RUN_ID, "started_at": _STARTED}]), {}, _MSG_8, logging.WARNING


def _case_8b():
    return _db([], [{"status": "pending", "cnt": 2}, {"status": "running", "cnt": 1}]), {}, _MSG_8B, logging.WARNING


def _case_unset():
    return _db([], []), {"settings": {}}, _MSG_UNSET, logging.ERROR


def _case_fetch_error():
    return (
        _db([], []),
        {"settings": {"max_age_hours": "48"}, "fetch_exc": RuntimeError("boom")},
        _MSG_FETCH,
        logging.ERROR,
    )


def _patches(opts: dict):
    patches = [
        patch.object(svc, "load_distribution_settings", new=AsyncMock(return_value=opts.get("settings", {}))),
    ]
    if "fetch_exc" in opts:
        patches.append(patch.object(svc, "fetch_output_rows", new=AsyncMock(side_effect=opts["fetch_exc"])))
    return patches


async def _call(fn, db, opts):
    ps = _patches(opts)
    for p in ps:
        p.start()
    try:
        return await fn(db)
    finally:
        for p in ps:
            p.stop()


@pytest.mark.parametrize(
    ("make_case", "kind"),
    [(_case_8, "hold"), (_case_8b, "hold"), (_case_unset, "unset"), (_case_fetch_error, "error")],
)
async def test_builder_kind_message_and_no_dist_log(make_case, kind, caplog):
    db, opts, message, _level = make_case()
    with caplog.at_level(logging.DEBUG):
        result = await _call(svc.build_distribution_rows, db, opts)
    assert result.kind == kind
    assert result.message == message
    assert result.rows == []
    assert [r for r in caplog.records if "[dist]" in r.getMessage()] == []


async def test_builder_ok_returns_fetch_rows_as_is(caplog):
    rows = [["a"] * 14, ["b"] * 14]
    fetch = AsyncMock(return_value=rows)
    db = _db([], [])
    with (
        patch.object(svc, "load_distribution_settings", new=AsyncMock(return_value={"max_age_hours": "48"})),
        patch.object(svc, "fetch_output_rows", new=fetch),
        caplog.at_level(logging.DEBUG),
    ):
        result = await svc.build_distribution_rows(db)
    assert result.kind == "ok" and result.rows is rows and result.message == ""
    fetch.assert_awaited_once_with(db, include_flag_single=False, max_age_hours=48)
    assert [r for r in caplog.records if "[dist]" in r.getMessage()] == []


@pytest.mark.parametrize("make_case", [_case_8, _case_8b, _case_unset, _case_fetch_error])
async def test_run_distribution_early_return_is_unchanged(make_case, caplog):
    db, opts, message, level = make_case()
    with caplog.at_level(logging.DEBUG):
        result = await _call(svc.run_distribution, db, opts)
    assert set(result) == _EXPECTED_KEYS
    assert result["run_id"] is None
    assert isinstance(result["started_at"], str) and result["started_at"]
    assert result["output_count"] == 0
    assert result["results"] == []
    assert result["errors"] == [{"target_id": None, "error": message}]
    dist_logs = [r for r in caplog.records if "[dist]" in r.getMessage()]
    assert len(dist_logs) == 1
    assert dist_logs[0].levelno == level


async def test_run_distribution_calls_build_distribution_rows():
    built = svc.DistributionRowsResult(kind="hold", rows=[], message="x")
    mock_build = AsyncMock(return_value=built)
    with patch.object(svc, "build_distribution_rows", new=mock_build):
        result = await svc.run_distribution(AsyncMock())
    mock_build.assert_awaited_once()
    assert result["errors"] == [{"target_id": None, "error": "x"}]
