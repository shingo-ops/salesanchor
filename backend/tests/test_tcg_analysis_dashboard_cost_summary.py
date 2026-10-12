"""
ADR-1004: GET /tcg/analysis-dashboard/cost-summary が llm_usage_events 台帳から
読むこと（input_bytes/3 推定を使わないこと）を検証する。

DB は AsyncMock で模擬し、get_cost_summary() を FastAPI ルーティング経由ではなく
直接呼び出す（Depends はただのデフォルト引数なので素の関数呼び出しで検証できる。
test_tcg_extraction_record_api.py と違い認可ロジックはここでは対象外）。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.routers.tcg_analysis_dashboard import get_cost_summary


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
async def test_cost_summary_reads_llm_usage_events_not_input_bytes_estimate():
    daily_row = {
        "date": "2026-09-30", "total_calls": 5, "success_calls": 4,
        "input_tokens": 1000, "output_tokens": 300, "cost_usd": 0.001,
    }
    supplier_row = {
        "supplier_name": "テスト仕入元", "total_calls": 5,
        "input_tokens": 1000, "output_tokens": 300, "cost_usd": 0.001, "avg_items": 2.0,
    }
    total_row = {"calls": 5, "input_tokens": 1000, "output_tokens": 300, "cost_usd": 0.001}
    budget_row = {"monthly_budget_usd": 10.0, "current_month_usd": 1.5}

    db = _mock_db_with_sequenced_results([[daily_row], [supplier_row], total_row, budget_row])

    result = await get_cost_summary(days=7, db=db, _admin=None)

    assert result.daily[0].input_tokens == 1000
    assert result.daily[0].output_tokens == 300
    assert result.total.cost_usd == pytest.approx(0.001)
    assert result.budget.monthly_budget_usd == 10.0

    # input_bytes/3 の推定計算式が残っていないこと（台帳読み取りへの完全移行）
    for sql in db._executed_sql:
        assert "input_bytes / 3" not in sql
    # daily/by_supplier/total すべてが llm_usage_events を参照していること
    assert sum("llm_usage_events" in sql for sql in db._executed_sql) == 3
