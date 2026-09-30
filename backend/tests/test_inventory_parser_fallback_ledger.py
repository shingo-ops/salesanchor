"""
ADR-1004: llm_usage_events 台帳への記録 — inventory_parser._maybe_apply_llm_fallback。

record_cost（tenant_llm_budgets 加算、既存動作は変えない）の隣で
record_usage_event(purpose='inventory_parse_fallback', ...) を1回呼ぶことを検証する。
discord_inbound_message_id が schedule_parse から parse_inventory_message まで
スレッドされることも確認する（inbound_writer.schedule_parse → parse_inventory_message
→ _maybe_apply_llm_fallback → record_usage_event）。

Mock 戦略: DB は AsyncMock、Gemini 呼び出しは inventory_parser_llm.parse_with_gemini を
monkeypatch（SQLite モック禁止条項の対象外: DB へは一切書き込まない、呼び出し引数のみ検証）。
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services import llm_budget
from app.services.inventory_parser import ParseResult, UnparsedLine, _maybe_apply_llm_fallback
from app.services.inventory_parser_llm import LLMParsedItem, LLMParseResult


def _base_result_with_unparsed() -> ParseResult:
    return ParseResult(
        items=[],
        excludes=[],
        unparsed=[UnparsedLine(line_no=1, raw_line="謎の行", reason="unmatched")],
        parse_engine="rule_v1",
    )


@pytest.fixture(autouse=True)
def _patch_budget_ok(monkeypatch):
    monkeypatch.setattr(llm_budget, "reset_monthly_if_needed", AsyncMock(return_value=False))
    monkeypatch.setattr(llm_budget, "check_budget", AsyncMock(return_value=llm_budget.BudgetStatus.UNDER))
    monkeypatch.setattr(llm_budget, "record_cost", AsyncMock(return_value=None))


class TestMaybeApplyLlmFallbackUsageLedger:
    @pytest.mark.asyncio
    async def test_records_usage_event_next_to_record_cost(self, monkeypatch):
        counts = llm_budget.UsageCounts(prompt_tokens=500, candidates_tokens=200)
        llm_result = LLMParseResult(
            items=[
                LLMParsedItem(
                    raw_line="謎の行", line_no=1, name="謎の商品", quantity=1, unit=None,
                    unit_price=None, condition=None, confidence=0.9,
                )
            ],
            input_tokens=500, output_tokens=200, model="gemini-3.1-flash-lite",
            usage_counts=counts,
        )
        import app.services.inventory_parser_llm as parser_llm_mod
        monkeypatch.setattr(parser_llm_mod, "parse_with_gemini", AsyncMock(return_value=llm_result))
        record_usage_event_mock = AsyncMock(return_value="usage-id-1")
        monkeypatch.setattr(llm_budget, "record_usage_event", record_usage_event_mock)

        db = AsyncMock()
        result = await _maybe_apply_llm_fallback(
            db=db,
            base_result=_base_result_with_unparsed(),
            tenant_id=6,
            rules=[],
            language="ja",
            discord_inbound_message_id=42,
        )

        assert result.parse_engine == "hybrid_rule_v1_llm_v1"
        record_usage_event_mock.assert_awaited_once()
        _, kwargs = record_usage_event_mock.call_args
        assert kwargs["purpose"] == "inventory_parse_fallback"
        assert kwargs["sdk"] == "google-generativeai"
        assert kwargs["tenant_id"] == 6
        assert kwargs["discord_inbound_message_id"] == 42
        assert kwargs["counts"] is counts

    @pytest.mark.asyncio
    async def test_discord_inbound_message_id_optional_none(self, monkeypatch):
        counts = llm_budget.UsageCounts(prompt_tokens=10, candidates_tokens=5)
        llm_result = LLMParseResult(
            items=[], input_tokens=10, output_tokens=5, model="gemini-3.1-flash-lite",
            usage_counts=counts,
        )
        import app.services.inventory_parser_llm as parser_llm_mod
        monkeypatch.setattr(parser_llm_mod, "parse_with_gemini", AsyncMock(return_value=llm_result))
        record_usage_event_mock = AsyncMock(return_value="usage-id-2")
        monkeypatch.setattr(llm_budget, "record_usage_event", record_usage_event_mock)

        db = AsyncMock()
        await _maybe_apply_llm_fallback(
            db=db, base_result=_base_result_with_unparsed(), tenant_id=6, rules=[], language="ja",
        )

        _, kwargs = record_usage_event_mock.call_args
        assert kwargs["discord_inbound_message_id"] is None

    @pytest.mark.asyncio
    async def test_record_usage_event_failure_does_not_break_merge(self, monkeypatch):
        """record_usage_event が例外を投げても解析結果は返す（record_cost と同じ扱い）。"""
        counts = llm_budget.UsageCounts(prompt_tokens=10, candidates_tokens=5)
        llm_result = LLMParseResult(
            items=[], input_tokens=10, output_tokens=5, model="gemini-3.1-flash-lite",
            usage_counts=counts,
        )
        import app.services.inventory_parser_llm as parser_llm_mod
        monkeypatch.setattr(parser_llm_mod, "parse_with_gemini", AsyncMock(return_value=llm_result))
        monkeypatch.setattr(
            llm_budget, "record_usage_event", AsyncMock(side_effect=RuntimeError("db down")),
        )

        db = AsyncMock()
        result = await _maybe_apply_llm_fallback(
            db=db, base_result=_base_result_with_unparsed(), tenant_id=6, rules=[], language="ja",
        )
        assert result.parse_engine == "hybrid_rule_v1_llm_v1"
