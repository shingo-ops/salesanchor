"""
ADR-1004: GET /tcg/analysis-dashboard/llm-usage が public.llm_usage_events 台帳のみを
読むこと（extraction_attempts 等の旧列を参照しないこと）・SDK が値を返さない列は NULL の
まま伝播すること（0 と推測しないこと）・days の範囲チェック(1〜360)を検証する。

DB は AsyncMock で模擬し、get_llm_usage() を直接呼び出して SQL/値を検証する
（test_tcg_analysis_dashboard_cost_summary.py と同じ方式）。
days の範囲チェックだけは FastAPI の Query バリデーションを通す必要があるため、
実際の router を FastAPI app に include して httpx 経由で叩く
（test_tcg_extraction_record_api.py と同じ方式）。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.routers import tcg_analysis_dashboard as routes
from app.routers.tcg_analysis_dashboard import get_llm_usage


def _mock_db_with_sequenced_results(mapping_results: list[list[dict] | dict | None]) -> AsyncMock:
    """db.execute() を呼ぶたびに順番に用意した mappings 結果を返す AsyncMock。"""
    db = AsyncMock()
    executed_sql: list[str] = []

    async def _execute(stmt, params=None):
        executed_sql.append(str(stmt))
        value = mapping_results.pop(0)
        result = MagicMock()
        mappings_result = MagicMock()
        if isinstance(value, list):
            mappings_result.all = MagicMock(return_value=value)
        else:
            mappings_result.first = MagicMock(return_value=value)
        result.mappings = MagicMock(return_value=mappings_result)
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db._executed_sql = executed_sql
    return db


@pytest.mark.asyncio
async def test_llm_usage_reads_only_ledger_and_propagates_null():
    total_row = {
        "calls": 3,
        "prompt_tokens": 900,
        "cached_content_tokens": None,
        "candidates_tokens": 300,
        "thoughts_tokens": None,
        "tool_use_prompt_tokens": None,
        "total_tokens": None,
        "cost_usd": 0.002,
        "computed_total_tokens": 1200,
        "total_mismatch_calls": 0,
    }
    by_purpose_row = {
        "purpose": "line_extraction",
        "calls": 3,
        "prompt_tokens": 900,
        "cached_content_tokens": None,
        "candidates_tokens": 300,
        "thoughts_tokens": None,
        "tool_use_prompt_tokens": None,
        "total_tokens": None,
        "cost_usd": 0.002,
        "computed_total_tokens": 1200,
        "total_mismatch_calls": 0,
    }
    by_model_row = {"model": "gemini-3.1-flash-lite", "calls": 3, "cost_usd": 0.002}
    daily_row = {
        "date": "2026-10-01",
        "calls": 3,
        "cost_usd": 0.002,
        "prompt_tokens": 900,
        "candidates_tokens": 300,
        "thoughts_tokens": None,
    }
    daily_by_purpose_row = {
        "date": "2026-10-01",
        "purpose": "line_extraction",
        "cost_usd": 0.002,
        "calls": 3,
    }
    monthly_by_purpose_row = {
        "month": "2026-10",
        "purpose": "line_extraction",
        "calls": 3,
        "cost_usd": 0.002,
    }

    daily_requests_row = {
        "date": "2026-10-01",
        "attempts": 5,
        "completed": 3,
        "failed": 1,
    }
    daily_errors_row = {
        "date": "2026-10-01",
        "error_code": "TIMEOUT",
        "count": 1,
    }
    daily_by_model_row = {
        "date": "2026-10-01",
        "model": "gemini-3.1-flash-lite",
        "calls": 3,
        "prompt_tokens": 900,
        "output_tokens": 300,
        "cost_usd": 0.002,
    }

    db = _mock_db_with_sequenced_results(
        [
            total_row,
            [by_purpose_row],
            [by_model_row],
            [daily_row],
            [daily_by_purpose_row],
            [monthly_by_purpose_row],
            [daily_requests_row],
            [daily_errors_row],
            [daily_by_model_row],
        ]
    )

    result = await get_llm_usage(days=30, db=db, _admin=None)

    assert result.total.calls == 3
    assert result.total.prompt_tokens == 900
    # SDK が返さなかった値は 0 に丸めず NULL のまま
    assert result.total.thoughts_tokens is None
    assert result.total.cached_content_tokens is None
    assert result.total.tool_use_prompt_tokens is None
    assert result.total.total_tokens is None
    assert result.total.computed_total_tokens == 1200
    assert result.total.total_mismatch_calls == 0

    assert result.by_purpose[0].purpose == "line_extraction"
    assert result.by_purpose[0].thoughts_tokens is None
    assert result.by_purpose[0].computed_total_tokens == 1200
    assert result.by_purpose[0].total_mismatch_calls == 0

    assert result.by_model[0].model == "gemini-3.1-flash-lite"
    assert result.by_model[0].cost_usd == pytest.approx(0.002)

    assert result.daily[0].date == "2026-10-01"
    assert result.daily[0].thoughts_tokens is None

    assert result.daily_by_purpose[0].date == "2026-10-01"
    assert result.daily_by_purpose[0].purpose == "line_extraction"
    assert result.daily_by_purpose[0].calls == 3
    assert result.daily_by_purpose[0].cost_usd == pytest.approx(0.002)

    # month は 'YYYY-MM' 形式
    assert result.monthly_by_purpose[0].month == "2026-10"
    assert result.monthly_by_purpose[0].purpose == "line_extraction"
    assert result.monthly_by_purpose[0].calls == 3

    assert result.daily_requests[0].date == "2026-10-01"
    assert result.daily_requests[0].attempts == 5
    assert result.daily_requests[0].completed == 3
    assert result.daily_requests[0].failed == 1
    assert result.daily_requests[0].success_rate == pytest.approx(0.75)

    assert result.daily_errors[0].date == "2026-10-01"
    assert result.daily_errors[0].error_code == "TIMEOUT"
    assert result.daily_errors[0].count == 1

    assert result.daily_by_model[0].date == "2026-10-01"
    assert result.daily_by_model[0].model == "gemini-3.1-flash-lite"
    assert result.daily_by_model[0].prompt_tokens == 900
    assert result.daily_by_model[0].output_tokens == 300

    # 最初の6クエリ（既存のコスト系集計）は llm_usage_events のみを参照し、
    # extraction_attempts 等の旧列を読まない（ADR-1004）。
    original_sql = db._executed_sql[:6]
    assert len(original_sql) == 6
    for sql in original_sql:
        assert "llm_usage_events" in sql
        assert "extraction_attempts" not in sql
        assert "extraction_shadow_runs" not in sql

    # 追加した daily_requests / daily_errors は extraction_attempts を参照し、
    # daily_by_model は llm_usage_events を参照する（設計どおり）。
    assert len(db._executed_sql) == 9
    assert "extraction_attempts" in db._executed_sql[6]
    assert "extraction_attempts" in db._executed_sql[7]
    assert "llm_usage_events" in db._executed_sql[8]


@pytest.mark.asyncio
async def test_llm_usage_all_null_when_no_rows():
    empty_total = {
        "calls": 0,
        "prompt_tokens": None,
        "cached_content_tokens": None,
        "candidates_tokens": None,
        "thoughts_tokens": None,
        "tool_use_prompt_tokens": None,
        "total_tokens": None,
        "cost_usd": None,
        "computed_total_tokens": None,
        "total_mismatch_calls": 0,
    }
    db = _mock_db_with_sequenced_results([empty_total, [], [], [], [], [], [], [], []])

    result = await get_llm_usage(days=7, db=db, _admin=None)

    assert result.total.calls == 0
    assert result.total.cost_usd is None
    # 4項目すべて未報告のグループは computed_total_tokens も NULL のまま（0 と推測しない）
    assert result.total.computed_total_tokens is None
    assert result.total.total_mismatch_calls == 0
    assert result.by_purpose == []
    assert result.by_model == []
    assert result.daily == []
    assert result.daily_by_purpose == []
    assert result.monthly_by_purpose == []
    assert result.daily_requests == []
    assert result.daily_errors == []
    assert result.daily_by_model == []


@pytest.mark.asyncio
async def test_llm_usage_mismatch_calls_counted_when_total_tokens_disagrees():
    total_row = {
        "calls": 2,
        "prompt_tokens": 500,
        "cached_content_tokens": None,
        "candidates_tokens": 100,
        "thoughts_tokens": None,
        "tool_use_prompt_tokens": None,
        "total_tokens": 999,
        "cost_usd": 0.001,
        "computed_total_tokens": 600,
        "total_mismatch_calls": 1,
    }
    db = _mock_db_with_sequenced_results([total_row, [], [], [], [], [], [], [], []])

    result = await get_llm_usage(days=30, db=db, _admin=None)

    assert result.total.total_mismatch_calls == 1
    assert result.total.computed_total_tokens == 600
    assert result.total.total_tokens == 999


@pytest.mark.asyncio
async def test_daily_requests_success_rate_null_when_no_terminal_attempts():
    """completed=0 かつ failed=0（全件が処理中）のとき success_rate は NULL のまま（0除算を推測しない）。"""
    empty_total = {
        "calls": 0,
        "prompt_tokens": None,
        "cached_content_tokens": None,
        "candidates_tokens": None,
        "thoughts_tokens": None,
        "tool_use_prompt_tokens": None,
        "total_tokens": None,
        "cost_usd": None,
        "computed_total_tokens": None,
        "total_mismatch_calls": 0,
    }
    daily_requests_row = {
        "date": "2026-10-01",
        "attempts": 2,
        "completed": 0,
        "failed": 0,
    }
    db = _mock_db_with_sequenced_results(
        [empty_total, [], [], [], [], [], [daily_requests_row], [], []]
    )

    result = await get_llm_usage(days=7, db=db, _admin=None)

    assert result.daily_requests[0].attempts == 2
    assert result.daily_requests[0].completed == 0
    assert result.daily_requests[0].failed == 0
    assert result.daily_requests[0].success_rate is None


@pytest.mark.asyncio
async def test_daily_errors_maps_null_error_code_to_unknown():
    empty_total = {
        "calls": 0,
        "prompt_tokens": None,
        "cached_content_tokens": None,
        "candidates_tokens": None,
        "thoughts_tokens": None,
        "tool_use_prompt_tokens": None,
        "total_tokens": None,
        "cost_usd": None,
        "computed_total_tokens": None,
        "total_mismatch_calls": 0,
    }
    daily_errors_row = {
        "date": "2026-10-01",
        "error_code": "UNKNOWN",
        "count": 1,
    }
    db = _mock_db_with_sequenced_results(
        [empty_total, [], [], [], [], [], [], [daily_errors_row], []]
    )

    result = await get_llm_usage(days=7, db=db, _admin=None)

    assert result.daily_errors[0].error_code == "UNKNOWN"
    assert result.daily_errors[0].count == 1


@pytest.mark.asyncio
async def test_daily_by_model_output_tokens_null_when_all_null_in_group():
    """candidates_tokens / thoughts_tokens が両方とも全行 NULL のグループは output_tokens も NULL
    のまま（0 と推測しない。computed_total_tokens と同じパターン）。"""
    empty_total = {
        "calls": 0,
        "prompt_tokens": None,
        "cached_content_tokens": None,
        "candidates_tokens": None,
        "thoughts_tokens": None,
        "tool_use_prompt_tokens": None,
        "total_tokens": None,
        "cost_usd": None,
        "computed_total_tokens": None,
        "total_mismatch_calls": 0,
    }
    daily_by_model_row = {
        "date": "2026-10-01",
        "model": "gemini-3.1-flash-lite",
        "calls": 1,
        "prompt_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
    }
    db = _mock_db_with_sequenced_results(
        [empty_total, [], [], [], [], [], [], [], [daily_by_model_row]]
    )

    result = await get_llm_usage(days=7, db=db, _admin=None)

    assert result.daily_by_model[0].prompt_tokens is None
    assert result.daily_by_model[0].output_tokens is None


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [0, 361])
async def test_llm_usage_days_out_of_bounds_returns_422(days):
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[require_super_admin] = lambda: {"is_super_admin": True}
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/tcg/analysis-dashboard/llm-usage?days={days}")
    assert response.status_code == 422
