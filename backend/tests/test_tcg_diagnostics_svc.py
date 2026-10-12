"""
retry_extraction: job_ids 件数上限ガードのテスト。

背景（design.md 参照）:
  job_ids 指定時の SELECT は `LIMIT _MAX_JOBS`（=50）のみで ORDER BY が無いため、
  51件以上を渡すと LIMIT であふれた分が enqueued にも skipped にも数えられず
  黙って落ちる。retry_extraction の冒頭で件数超過を ValueError として明示的に
  弾くようにした。

カバー:
  - T1: job_ids が 51件のとき ValueError になる
  - T2: job_ids が 50件のときは従来どおり処理される（DB・Celery はモック）
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio


def _make_row(job_id: str, source_message_id: str, status: str) -> MagicMock:
    row = MagicMock()
    row.id = job_id
    row.source_message_id = source_message_id
    row.status = status
    return row


async def test_retry_extraction_raises_value_error_when_job_ids_exceed_max():
    """T1: job_ids が 51件（_MAX_JOBS 超過）のとき ValueError になること。DB・Celery には到達しない。"""
    from app.services.tcg_diagnostics_svc import _MAX_JOBS, retry_extraction

    job_ids = [f"job-{i:03d}" for i in range(_MAX_JOBS + 1)]
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    with pytest.raises(ValueError) as exc_info:
        await retry_extraction(mock_db, job_ids=job_ids, scope=None)

    assert str(_MAX_JOBS + 1) in str(exc_info.value)
    assert str(_MAX_JOBS) in str(exc_info.value)
    mock_db.execute.assert_not_awaited()


async def test_retry_extraction_processes_exactly_max_jobs():
    """T2: job_ids が 50件（_MAX_JOBS ちょうど）のときは従来どおり処理されること。"""
    from app.services.tcg_diagnostics_svc import _MAX_JOBS, retry_extraction

    job_ids = [f"job-{i:03d}" for i in range(_MAX_JOBS)]
    rows = [_make_row(jid, f"sm-{i:03d}", "error") for i, jid in enumerate(job_ids)]

    mock_select_result = MagicMock()
    mock_select_result.fetchall.return_value = rows

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_select_result)
    mock_db.commit = AsyncMock()

    mock_task = MagicMock()
    mock_task.apply_async = MagicMock()

    with patch(
        "app.tasks.tcg_extraction.extract_source_message_task",
        mock_task,
    ):
        result = await retry_extraction(mock_db, job_ids=job_ids, scope=None)

    assert result == {"enqueued": _MAX_JOBS, "skipped": 0}
    assert mock_task.apply_async.call_count == _MAX_JOBS
