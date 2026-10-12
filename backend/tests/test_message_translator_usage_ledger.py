"""
ADR-1004: llm_usage_events 台帳への記録 — message_translator の3経路。

purpose の内訳:
  - translation_inbound: translate_inbound() の初回呼び出し
  - translation_inbound_escalation: 低確信度/長文でのエスカレート呼び出し
  - translation_outbound: generate_outbound_draft()

record_cost（tenant_llm_budgets 加算、既存動作は変えない）の隣で
record_usage_event を1回ずつ呼ぶことを検証する。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services import message_translator
from app.services.llm_budget import BudgetStatus
from app.services.message_translator import (
    MODEL_RECEIVE,
    MODEL_SEND,
    generate_outbound_draft,
    translate_inbound,
)
from tests.test_message_translator import _install_fake_genai, _make_gemini_json_response


@pytest.fixture(autouse=True)
def reset_genai_cache():
    message_translator._GENAI_CACHE.clear()
    yield
    message_translator._GENAI_CACHE.clear()


@pytest.mark.asyncio
async def test_translate_inbound_records_usage_event_with_message_id():
    db = AsyncMock()
    fake_resp = _make_gemini_json_response("テスト翻訳", confidence=0.95, original_language="en")
    _install_fake_genai(fake_resp)

    with patch.object(
        message_translator, "_get_cached_translation", new_callable=AsyncMock, return_value=None,
    ), patch(
        "app.services.message_translator.load_glossary", new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.services.message_translator.reset_monthly_if_needed", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock, return_value=BudgetStatus.UNDER,
    ), patch(
        "app.services.message_translator.record_cost", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator.record_usage_event", new_callable=AsyncMock,
    ) as mock_usage_event, patch.object(
        message_translator, "_save_translation", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator._ensure_api_key", return_value="fake-key",
    ):
        await translate_inbound(
            db=db, tenant_id=1, table_ref="tenant_001.message_translations",
            message_id="mid_ledger_1", message_text="Good morning", target_language="ja",
        )

    # 高確信度 (0.95) & 短文 → エスカレートなし → translation_inbound のみ1回
    mock_usage_event.assert_awaited_once()
    _, kwargs = mock_usage_event.call_args
    assert kwargs["purpose"] == "translation_inbound"
    assert kwargs["model"] == MODEL_RECEIVE
    assert kwargs["sdk"] == "google-generativeai"
    assert kwargs["tenant_id"] == 1
    assert kwargs["source_ref"] == "mid_ledger_1"
    assert kwargs["counts"].prompt_tokens == 100


@pytest.mark.asyncio
async def test_translate_inbound_escalation_records_second_usage_event(monkeypatch):
    db = AsyncMock()
    # デフォルト設定では MODEL_RECEIVE == MODEL_SEND のためエスカレートが起きない
    # （`model != MODEL_SEND` ガード）。テストでは明示的に分ける。
    monkeypatch.setattr(message_translator, "MODEL_SEND", "gemini-2.5-pro")
    # 低確信度で1回目 → エスカレート判定発火
    low_conf_resp = _make_gemini_json_response("下訳", confidence=0.10, original_language="en")
    escalated_resp = _make_gemini_json_response("上訳", confidence=0.95, original_language="en")
    genai = _install_fake_genai(low_conf_resp)
    genai.GenerativeModel.return_value.generate_content_async = AsyncMock(
        side_effect=[low_conf_resp, escalated_resp]
    )

    with patch.object(
        message_translator, "_get_cached_translation", new_callable=AsyncMock, return_value=None,
    ), patch(
        "app.services.message_translator.load_glossary", new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.services.message_translator.reset_monthly_if_needed", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock, return_value=BudgetStatus.UNDER,
    ), patch(
        "app.services.message_translator.record_cost", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator.record_usage_event", new_callable=AsyncMock,
    ) as mock_usage_event, patch.object(
        message_translator, "_save_translation", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator._ensure_api_key", return_value="fake-key",
    ):
        await translate_inbound(
            db=db, tenant_id=1, table_ref="tenant_001.message_translations",
            message_id="mid_ledger_2", message_text="Good morning", target_language="ja",
        )

    assert mock_usage_event.await_count == 2
    purposes = [call.kwargs["purpose"] for call in mock_usage_event.await_args_list]
    assert purposes == ["translation_inbound", "translation_inbound_escalation"]
    assert mock_usage_event.await_args_list[1].kwargs["model"] == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_generate_outbound_draft_records_usage_event_with_lead_id():
    db = AsyncMock()
    fake_resp = _make_gemini_json_response("Draft EN text", confidence=0.91)
    _install_fake_genai(fake_resp)

    with patch(
        "app.services.message_translator.load_glossary", new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.services.message_translator.reset_monthly_if_needed", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock, return_value=BudgetStatus.UNDER,
    ), patch(
        "app.services.message_translator.record_cost", new_callable=AsyncMock,
    ), patch(
        "app.services.message_translator.record_usage_event", new_callable=AsyncMock,
    ) as mock_usage_event, patch.object(
        message_translator, "save_outbound_draft", new_callable=AsyncMock, return_value=42,
    ), patch(
        "app.services.message_translator._ensure_api_key", return_value="fake-key",
    ):
        await generate_outbound_draft(
            db=db, tenant_id=1, drafts_table_ref="tenant_001.outbound_translation_drafts",
            lead_id=777, draft_text="こんにちは",
        )

    mock_usage_event.assert_awaited_once()
    _, kwargs = mock_usage_event.call_args
    assert kwargs["purpose"] == "translation_outbound"
    assert kwargs["model"] == MODEL_SEND
    assert kwargs["source_ref"] == "777"
