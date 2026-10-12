"""
spec.md v1.1 Sprint 4 / F4 / AC4.3 + AC4.4: LLM budget サービスの単体テスト。

feedback_evaluator_gap_2026_05_15.md の「SQLite モック禁止条項」に照らし、
budget の Decimal 演算 / 月初リセット境界判定 / hard_stop 判定は **実 PostgreSQL の
NUMERIC 列挙動と一致する Python 側ロジック** をテストする。

DB 入出力経路は test_inventory_parser_llm.py 側で実 Postgres で検証する
(本ファイルは pure 関数 + asyncpg-shape の round-trip を最小限に確認)。

Mock 戦略:
  - sqlalchemy.ext.asyncio.AsyncSession を unittest.mock.AsyncMock で代用
  - SQL は文字列等価ではなく「呼ばれた回数 / 引数 / 戻り値」を確認
  - 実 NUMERIC quantize は Python Decimal で再現 (NUMERIC(10,4) round-half-up)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.llm_budget import (
    LLM_PRICING,
    BudgetStatus,
    UsageCounts,
    calculate_cost,
    calculate_usage_cost,
    check_budget,
    record_cost,
    record_usage_event,
    record_usage_event_sync,
    reset_monthly_if_needed,
    usage_counts_from,
)

# ---------------------------------------------------------------------------
# calculate_cost (pure, no DB)
# ---------------------------------------------------------------------------


class TestCalculateCost:
    def test_zero_tokens_returns_zero(self) -> None:
        assert calculate_cost(0, 0) == Decimal("0")

    def test_input_only_default_model(self) -> None:
        # 1M input tokens * $0.30 = $0.30
        cost = calculate_cost(1_000_000, 0)
        assert cost == Decimal("0.30")

    def test_output_only_default_model(self) -> None:
        # 1M output tokens * $2.50 = $2.50
        cost = calculate_cost(0, 1_000_000)
        assert cost == Decimal("2.50")

    def test_typical_inventory_message(self) -> None:
        # 2000 input + 800 output (typical 1 メッセージ)
        # 2000 * 0.30e-6 = 0.00060 + 800 * 2.50e-6 = 0.00200 → 0.00260
        cost = calculate_cost(2000, 800)
        assert cost == Decimal("0.002600")  # Decimal precise

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown LLM model"):
            calculate_cost(100, 100, model="claude-opus-99")

    def test_pricing_table_present(self) -> None:
        # Gemini 2.5 Flash の単価が定義されていること (AC4.2)
        assert "gemini-2.5-flash" in LLM_PRICING
        pricing = LLM_PRICING["gemini-2.5-flash"]
        assert pricing["input_per_token"] > 0
        assert pricing["output_per_token"] > 0
        # 出力 > 入力 (Gemini の料金構造、回帰防止)
        assert pricing["output_per_token"] > pricing["input_per_token"]


# ---------------------------------------------------------------------------
# Mock DB helpers
# ---------------------------------------------------------------------------


def _make_mock_db_with_row(row: dict | None) -> AsyncMock:
    """AsyncSession を mock。execute() の戻り値で row を返す。"""
    db = AsyncMock()
    result_mock = MagicMock()
    mappings_mock = MagicMock()
    mappings_mock.first = MagicMock(return_value=row)
    result_mock.mappings = MagicMock(return_value=mappings_mock)
    db.execute = AsyncMock(return_value=result_mock)
    return db


# ---------------------------------------------------------------------------
# check_budget
# ---------------------------------------------------------------------------


class TestCheckBudget:
    @pytest.mark.asyncio
    async def test_no_row_returns_no_budget_row(self) -> None:
        db = _make_mock_db_with_row(None)
        status = await check_budget(db, tenant_id=999)
        assert status == BudgetStatus.NO_BUDGET_ROW

    @pytest.mark.asyncio
    async def test_under_budget(self) -> None:
        db = _make_mock_db_with_row({
            "tenant_id": 6,
            "monthly_budget_usd": Decimal("5.00"),
            "current_month_usd": Decimal("0.50"),
            "last_reset_at": datetime.now(timezone.utc),
            "hard_stop": True,
            "notify_admin": True,
        })
        assert await check_budget(db, tenant_id=6) == BudgetStatus.UNDER

    @pytest.mark.asyncio
    async def test_over_budget_with_hard_stop(self) -> None:
        db = _make_mock_db_with_row({
            "tenant_id": 6,
            "monthly_budget_usd": Decimal("0.01"),
            "current_month_usd": Decimal("0.05"),
            "last_reset_at": datetime.now(timezone.utc),
            "hard_stop": True,
            "notify_admin": True,
        })
        # AC4.3: hard_stop=true で予算超過 → HARD_STOP
        assert await check_budget(db, tenant_id=6) == BudgetStatus.HARD_STOP

    @pytest.mark.asyncio
    async def test_over_budget_without_hard_stop_returns_soft(self) -> None:
        db = _make_mock_db_with_row({
            "tenant_id": 6,
            "monthly_budget_usd": Decimal("0.01"),
            "current_month_usd": Decimal("0.05"),
            "last_reset_at": datetime.now(timezone.utc),
            "hard_stop": False,
            "notify_admin": True,
        })
        assert await check_budget(db, tenant_id=6) == BudgetStatus.OVER_SOFT

    @pytest.mark.asyncio
    async def test_zero_budget_treated_as_unlimited(self) -> None:
        """monthly_budget_usd = 0 は「未設定」扱い (実装上 UNDER で API 呼ばないことが多い)。
        ロジック: 0 > 0 が False なので超過判定が走らず UNDER 返却。
        呼び出し側で 0 を「LLM 無効」運用とする想定。
        """
        db = _make_mock_db_with_row({
            "tenant_id": 6,
            "monthly_budget_usd": Decimal("0.00"),
            "current_month_usd": Decimal("0.00"),
            "last_reset_at": datetime.now(timezone.utc),
            "hard_stop": True,
            "notify_admin": True,
        })
        # 0 予算 / 0 使用は UNDER (実運用は NO_BUDGET_ROW 同等を期待するが、
        # row 自体は存在するので UNDER。これは spec の予算未設定運用と矛盾しないため OK)
        assert await check_budget(db, tenant_id=6) == BudgetStatus.UNDER


# ---------------------------------------------------------------------------
# reset_monthly_if_needed
# ---------------------------------------------------------------------------


class TestResetMonthlyIfNeeded:
    @pytest.mark.asyncio
    async def test_no_row_returns_false_no_reset(self) -> None:
        db = _make_mock_db_with_row(None)
        assert await reset_monthly_if_needed(db, tenant_id=999) is False
        # SELECT のみ、UPDATE は呼ばれない
        assert db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_same_month_no_reset(self) -> None:
        now = datetime(2026, 5, 15, tzinfo=timezone.utc)
        db = _make_mock_db_with_row({
            "tenant_id": 6,
            "monthly_budget_usd": Decimal("5.00"),
            "current_month_usd": Decimal("0.50"),
            "last_reset_at": datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc),
            "hard_stop": True,
            "notify_admin": True,
        })
        assert await reset_monthly_if_needed(db, tenant_id=6, now=now) is False

    @pytest.mark.asyncio
    async def test_previous_month_triggers_reset(self) -> None:
        """AC4.4: 月初の last_reset_at が変わると current_month_usd が 0 にリセット。"""
        now = datetime(2026, 6, 2, tzinfo=timezone.utc)
        db = _make_mock_db_with_row({
            "tenant_id": 6,
            "monthly_budget_usd": Decimal("5.00"),
            "current_month_usd": Decimal("3.50"),
            "last_reset_at": datetime(2026, 5, 10, tzinfo=timezone.utc),
            "hard_stop": True,
            "notify_admin": True,
        })
        assert await reset_monthly_if_needed(db, tenant_id=6, now=now) is True
        # SELECT + UPDATE で 2 回
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_year_boundary_triggers_reset(self) -> None:
        now = datetime(2027, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        db = _make_mock_db_with_row({
            "tenant_id": 6,
            "monthly_budget_usd": Decimal("5.00"),
            "current_month_usd": Decimal("4.99"),
            "last_reset_at": datetime(2026, 12, 31, 23, 0, 0, tzinfo=timezone.utc),
            "hard_stop": True,
            "notify_admin": True,
        })
        assert await reset_monthly_if_needed(db, tenant_id=6, now=now) is True


# ---------------------------------------------------------------------------
# record_cost
# ---------------------------------------------------------------------------


class TestRecordCost:
    @pytest.mark.asyncio
    async def test_records_cost_with_correct_amount(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        cost = await record_cost(db, tenant_id=6, input_tokens=2000, output_tokens=800)
        # 2000 * 0.30e-6 + 800 * 2.50e-6 = 0.000600 + 0.002000 = 0.002600
        assert cost == Decimal("0.0026")  # NUMERIC(10,4) で 0.0026 に丸まる
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_zero_tokens_zero_cost(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        cost = await record_cost(db, tenant_id=6, input_tokens=0, output_tokens=0)
        assert cost == Decimal("0.0000")
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_high_volume_accumulation(self) -> None:
        """5M input + 5M output で 1.50 + 12.50 = 14.00 USD"""
        db = AsyncMock()
        db.execute = AsyncMock()
        cost = await record_cost(db, tenant_id=6, input_tokens=5_000_000, output_tokens=5_000_000)
        assert cost == Decimal("14.0000")


# ---------------------------------------------------------------------------
# ADR-1004: llm_usage_events 台帳 — usage_counts_from (pure, no DB)
# ---------------------------------------------------------------------------


class TestUsageCountsFrom:
    def test_none_usage_returns_all_none(self) -> None:
        counts = usage_counts_from(None)
        assert counts == UsageCounts()
        assert counts.prompt_tokens is None
        assert counts.total_tokens is None

    def test_reads_all_six_fields(self) -> None:
        usage = MagicMock(spec=[
            "prompt_token_count", "cached_content_token_count", "candidates_token_count",
            "thoughts_token_count", "tool_use_prompt_token_count", "total_token_count",
        ])
        usage.prompt_token_count = 1000
        usage.cached_content_token_count = 50
        usage.candidates_token_count = 100
        usage.thoughts_token_count = 40
        usage.tool_use_prompt_token_count = 5
        usage.total_token_count = 1195
        counts = usage_counts_from(usage)
        assert counts == UsageCounts(
            prompt_tokens=1000, cached_content_tokens=50, candidates_tokens=100,
            thoughts_tokens=40, tool_use_prompt_tokens=5, total_tokens=1195,
        )

    def test_missing_attr_is_none_not_zero(self) -> None:
        # 旧 SDK は thoughts_token_count 属性自体を持たない場合がある
        usage = MagicMock(spec=["prompt_token_count", "candidates_token_count"])
        usage.prompt_token_count = 250
        usage.candidates_token_count = 80
        counts = usage_counts_from(usage)
        assert counts.prompt_tokens == 250
        assert counts.candidates_tokens == 80
        assert counts.thoughts_tokens is None
        assert counts.cached_content_tokens is None

    def test_none_attr_value_stays_none(self) -> None:
        usage = MagicMock(spec=["prompt_token_count", "thoughts_token_count"])
        usage.prompt_token_count = 100
        usage.thoughts_token_count = None
        counts = usage_counts_from(usage)
        assert counts.prompt_tokens == 100
        assert counts.thoughts_tokens is None

    def test_zero_is_preserved_not_treated_as_none(self) -> None:
        usage = MagicMock(spec=["prompt_token_count", "candidates_token_count"])
        usage.prompt_token_count = 0
        usage.candidates_token_count = 0
        counts = usage_counts_from(usage)
        assert counts.prompt_tokens == 0
        assert counts.candidates_tokens == 0


# ---------------------------------------------------------------------------
# calculate_usage_cost (pure, no DB)
# ---------------------------------------------------------------------------


class TestCalculateUsageCost:
    def test_prompt_candidates_and_thoughts_included(self) -> None:
        # design.md 受入条件: prompt=1000, candidates=100, thoughts=50, model=gemini-3.1-flash-lite
        # 1000 * 0.25e-6 + 150 * 1.50e-6 = 0.00025 + 0.000225 = 0.000475
        counts = UsageCounts(prompt_tokens=1000, candidates_tokens=100, thoughts_tokens=50)
        cost = calculate_usage_cost(counts, model="gemini-3.1-flash-lite")
        assert cost == Decimal("1000") * Decimal("0.25") / Decimal("1000000") + Decimal("150") * Decimal("1.50") / Decimal("1000000")

    def test_unknown_model_returns_none(self) -> None:
        counts = UsageCounts(prompt_tokens=100, candidates_tokens=50)
        assert calculate_usage_cost(counts, model="claude-opus-99") is None

    def test_all_none_counts_returns_none(self) -> None:
        counts = UsageCounts()
        assert calculate_usage_cost(counts, model="gemini-3.1-flash-lite") is None

    def test_none_treated_as_zero_when_partial(self) -> None:
        # prompt のみ分かっている場合、candidates/thoughts は 0 扱い
        counts = UsageCounts(prompt_tokens=1_000_000)
        cost = calculate_usage_cost(counts, model="gemini-3.1-flash-lite")
        assert cost == Decimal("0.25")

    def test_thoughts_only_still_computes(self) -> None:
        counts = UsageCounts(candidates_tokens=None, thoughts_tokens=1_000_000)
        cost = calculate_usage_cost(counts, model="gemini-3.1-flash-lite")
        assert cost == Decimal("1.50")


# ---------------------------------------------------------------------------
# record_usage_event_sync / record_usage_event
# ---------------------------------------------------------------------------


class TestRecordUsageEvent:
    def test_sync_unknown_purpose_raises(self) -> None:
        session = MagicMock()
        with pytest.raises(ValueError, match="unknown llm_usage_events purpose"):
            record_usage_event_sync(
                session, purpose="not_a_real_purpose", model="gemini-3.1-flash-lite",
                sdk="google-genai", counts=UsageCounts(),
            )
        session.execute.assert_not_called()

    def test_sync_unknown_sdk_raises(self) -> None:
        session = MagicMock()
        with pytest.raises(ValueError, match="unknown llm_usage_events sdk"):
            record_usage_event_sync(
                session, purpose="line_extraction", model="gemini-3.1-flash-lite",
                sdk="not_a_real_sdk", counts=UsageCounts(),
            )
        session.execute.assert_not_called()

    def test_sync_inserts_one_row_with_expected_columns(self) -> None:
        session = MagicMock()
        counts = UsageCounts(prompt_tokens=1000, candidates_tokens=100, thoughts_tokens=50)
        row_id = record_usage_event_sync(
            session, purpose="line_extraction", model="gemini-3.1-flash-lite",
            sdk="google-genai", counts=counts, extraction_attempt_id="attempt-1",
        )
        session.execute.assert_called_once()
        args, kwargs = session.execute.call_args
        params = args[1]
        assert params["id"] == row_id
        assert params["purpose"] == "line_extraction"
        assert params["extraction_attempt_id"] == "attempt-1"
        assert params["prompt_tokens"] == 1000
        assert params["candidates_tokens"] == 100
        assert params["thoughts_tokens"] == 50
        assert params["cost_usd"] is not None

    def test_sync_no_usage_no_cost_still_inserts_null_cost(self) -> None:
        session = MagicMock()
        record_usage_event_sync(
            session, purpose="line_extraction_shadow", model="gemini-3.1-flash-lite",
            sdk="google-genai", counts=UsageCounts(), extraction_shadow_run_id="run-1",
        )
        _, kwargs_or_args = session.execute.call_args
        params = session.execute.call_args[0][1]
        assert params["cost_usd"] is None
        assert params["prompt_tokens"] is None

    @pytest.mark.asyncio
    async def test_async_inserts_one_row(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        counts = UsageCounts(prompt_tokens=500, candidates_tokens=200)
        row_id = await record_usage_event(
            db, purpose="inventory_parse_fallback", model="gemini-3.1-flash-lite",
            sdk="google-generativeai", counts=counts, tenant_id=6,
            discord_inbound_message_id=42,
        )
        db.execute.assert_called_once()
        params = db.execute.call_args[0][1]
        assert params["id"] == row_id
        assert params["tenant_id"] == 6
        assert params["discord_inbound_message_id"] == 42
        assert params["purpose"] == "inventory_parse_fallback"
