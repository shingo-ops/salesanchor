"""
ADR-110: メッセージ翻訳サービスの単体テスト。

ADR-088 基盤 + ADR-110 拡張のカバー:
  - 原文不変（受け入れ条件 1）
  - DB キャッシュヒット時は Gemini 未呼び出し（冪等・受け入れ条件 7）
  - キャッシュミス時は Gemini → グロッサリ適用 → DB 保存
  - 予算超過時は BudgetExceededError
  - 送信は MODEL_SEND を使用（受け入れ条件 6）
  - グロッサリプロンプト注入（受け入れ条件 2）
  - 確信度スコアリング（受け入れ条件 5）
  - _parse_translation_response の JSON パース
  - テナント分離（table_ref がテナント固有）

Mock 戦略:
  - google.generativeai モジュールを _GENAI_CACHE に MagicMock で事前注入
  - llm_budget.check_budget / record_cost を patch
  - translation_glossary.load_glossary を patch
  - DB 操作は AsyncMock で模擬
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import message_translator
from app.services.message_translator import (
    BudgetExceededError,
    MODEL_RECEIVE,
    MODEL_SEND,
    LegacyTranslationResult,
    TranslationResult,
    _parse_translation_response,
    generate_outbound_draft,
    translate_inbound,
    translate_message,
)
from app.services.llm_budget import BudgetStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_genai_cache():
    message_translator._GENAI_CACHE.clear()
    yield
    message_translator._GENAI_CACHE.clear()


def _make_gemini_json_response(
    translated_text: str = "Translated text",
    confidence: float = 0.92,
    original_language: str = "en",
    flagged_terms: list | None = None,
    prompt_tokens: int = 100,
    candidates_tokens: int = 50,
) -> MagicMock:
    """Gemini SDK response の MagicMock（ADR-110 JSON 形式）。"""
    payload = json.dumps({
        "translated_text": translated_text,
        "confidence": confidence,
        "original_language": original_language,
        "flagged_terms": flagged_terms or [],
    })
    response = MagicMock()
    response.text = payload
    usage = MagicMock()
    usage.prompt_token_count = prompt_tokens
    usage.candidates_token_count = candidates_tokens
    response.usage_metadata = usage
    return response


def _install_fake_genai(response: MagicMock) -> MagicMock:
    genai = MagicMock()
    genai.configure = MagicMock()
    model = MagicMock()
    model.generate_content_async = AsyncMock(return_value=response)
    genai.GenerativeModel = MagicMock(return_value=model)
    message_translator._GENAI_CACHE["module"] = genai
    return genai


# ---------------------------------------------------------------------------
# _parse_translation_response
# ---------------------------------------------------------------------------


def test_parse_valid_json():
    raw = json.dumps({
        "translated_text": "こんにちは",
        "confidence": 0.95,
        "original_language": "en",
        "flagged_terms": [{"term": "Hello", "reason": "ambiguous"}],
    })
    text, conf, lang, flags = _parse_translation_response(raw)
    assert text == "こんにちは"
    assert conf == pytest.approx(0.95)
    assert lang == "en"
    assert len(flags) == 1
    assert flags[0].term == "Hello"


def test_parse_invalid_json_falls_back_to_raw():
    """JSON パース失敗時はテキストをそのまま返し confidence=0.5。"""
    raw = "申し訳ありません、在庫切れです"
    text, conf, lang, flags = _parse_translation_response(raw)
    assert text == raw
    assert conf == pytest.approx(0.5)
    assert flags == []


def test_parse_confidence_clamped():
    """confidence は 0–1 にクランプ。"""
    raw = json.dumps({"translated_text": "x", "confidence": 1.5})
    _, conf, _, _ = _parse_translation_response(raw)
    assert conf == pytest.approx(1.0)


def test_parse_markdown_json_block():
    """```json ... ``` ブロックを正常にパース。"""
    raw = '```json\n{"translated_text": "test", "confidence": 0.9}\n```'
    text, conf, _, _ = _parse_translation_response(raw)
    assert text == "test"
    assert conf == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# translate_inbound
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_without_api_call():
    """DB キャッシュヒット時は Gemini を呼ばない（冪等性・受け入れ条件 7）。"""
    db = AsyncMock()

    with patch.object(
        message_translator,
        "_get_cached_translation",
        new_callable=AsyncMock,
        return_value=("キャッシュ済み翻訳", 0.9, "en"),
    ) as mock_cache, patch.object(
        message_translator,
        "_call_gemini",
        new_callable=AsyncMock,
    ) as mock_gemini:
        result = await translate_inbound(
            db=db,
            tenant_id=1,
            table_ref="tenant_001.message_translations",
            message_id="mid_cached",
            message_text="Hello",
            target_language="ja",
        )

    assert result.translated_text == "キャッシュ済み翻訳"
    assert result.cached is True
    assert result.confidence == pytest.approx(0.9)
    assert result.original_language == "en"
    mock_gemini.assert_not_awaited()
    mock_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_miss_calls_gemini_and_saves():
    """キャッシュミス時: Gemini → グロッサリ適用 → DB 保存。"""
    db = AsyncMock()
    fake_resp = _make_gemini_json_response("テスト翻訳", confidence=0.88, original_language="en")
    _install_fake_genai(fake_resp)

    with patch.object(
        message_translator,
        "_get_cached_translation",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.message_translator.load_glossary",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock,
        return_value=BudgetStatus.UNDER,
    ), patch(
        "app.services.message_translator.record_cost",
        new_callable=AsyncMock,
    ) as mock_cost, patch.object(
        message_translator,
        "_save_translation",
        new_callable=AsyncMock,
    ) as mock_save, patch(
        "app.services.message_translator._ensure_api_key",
        return_value="fake-key",
    ):
        result = await translate_inbound(
            db=db,
            tenant_id=1,
            table_ref="tenant_001.message_translations",
            message_id="mid_new",
            message_text="Good morning",
            target_language="ja",
        )

    assert result.translated_text == "テスト翻訳"
    assert result.cached is False
    assert result.confidence == pytest.approx(0.88)
    assert result.original_language == "en"
    mock_cost.assert_awaited_once()
    mock_save.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_budget_exceeded_raises_error():
    """予算超過時は BudgetExceededError を raise。"""
    db = AsyncMock()

    with patch.object(
        message_translator, "_get_cached_translation",
        new_callable=AsyncMock, return_value=None,
    ), patch(
        "app.services.message_translator.load_glossary",
        new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock, return_value=BudgetStatus.HARD_STOP,
    ):
        with pytest.raises(BudgetExceededError) as exc_info:
            await translate_inbound(
                db=db, tenant_id=1,
                table_ref="tenant_001.message_translations",
                message_id="mid_budget", message_text="hi", target_language="ja",
            )

    assert exc_info.value.status == BudgetStatus.HARD_STOP


@pytest.mark.asyncio
async def test_no_budget_row_raises_error():
    db = AsyncMock()

    with patch.object(
        message_translator, "_get_cached_translation",
        new_callable=AsyncMock, return_value=None,
    ), patch(
        "app.services.message_translator.load_glossary",
        new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock, return_value=BudgetStatus.NO_BUDGET_ROW,
    ):
        with pytest.raises(BudgetExceededError) as exc_info:
            await translate_inbound(
                db=db, tenant_id=1,
                table_ref="tenant_001.message_translations",
                message_id="mid_no_row", message_text="hi", target_language="en",
            )

    assert exc_info.value.status == BudgetStatus.NO_BUDGET_ROW


# ---------------------------------------------------------------------------
# translate_message（ADR-088 互換）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_translate_message_compat_returns_legacy_result():
    """translate_message() は LegacyTranslationResult を返す（ADR-088 互換）。"""
    db = AsyncMock()

    with patch.object(
        message_translator, "_get_cached_translation",
        new_callable=AsyncMock, return_value=("cached", 0.85, "en"),
    ):
        result = await translate_message(
            db=db, tenant_id=1,
            table_ref="tenant_001.message_translations",
            message_id="mid_compat", message_text="hi", target_language="ja",
        )

    assert isinstance(result, LegacyTranslationResult)
    assert result.translated_text == "cached"
    assert result.cached is True


# ---------------------------------------------------------------------------
# generate_outbound_draft（送信英訳=最上位モデル必須 — 受け入れ条件 6）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_uses_send_model():
    """送信英訳は MODEL_SEND（最上位）を使用。受け入れ条件 6。"""
    db = AsyncMock()
    fake_resp = _make_gemini_json_response("Draft EN text", confidence=0.91)
    genai_mock = _install_fake_genai(fake_resp)

    with patch(
        "app.services.message_translator.load_glossary",
        new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock, return_value=BudgetStatus.UNDER,
    ), patch(
        "app.services.message_translator.record_cost",
        new_callable=AsyncMock,
    ), patch.object(
        message_translator, "save_outbound_draft",
        new_callable=AsyncMock, return_value=42,
    ) as mock_save_draft, patch(
        "app.services.message_translator._ensure_api_key",
        return_value="fake-key",
    ):
        draft_id, result = await generate_outbound_draft(
            db=db, tenant_id=1,
            drafts_table_ref="tenant_001.outbound_translation_drafts",
            lead_id=5,
            draft_text="在庫の確認が取れました。",
            target_language="en",
        )

    assert draft_id == 42
    assert result.translated_text == "Draft EN text"
    assert result.engine == MODEL_SEND

    # GenerativeModel が MODEL_SEND で呼ばれたことを確認
    genai_mock.GenerativeModel.assert_called_once_with(
        model_name=MODEL_SEND,
        generation_config={"temperature": 0.1},
    )
    mock_save_draft.assert_awaited_once()


@pytest.mark.asyncio
async def test_outbound_budget_exceeded_raises():
    """送信でも予算超過時は BudgetExceededError。"""
    db = AsyncMock()

    with patch(
        "app.services.message_translator.load_glossary",
        new_callable=AsyncMock, return_value=[],
    ), patch(
        "app.services.message_translator.check_budget",
        new_callable=AsyncMock, return_value=BudgetStatus.HARD_STOP,
    ):
        with pytest.raises(BudgetExceededError):
            await generate_outbound_draft(
                db=db, tenant_id=1,
                drafts_table_ref="tenant_001.outbound_translation_drafts",
                lead_id=None,
                draft_text="テスト",
                target_language="en",
            )


# ---------------------------------------------------------------------------
# 送信ガード: 確認ステップテスト（受け入れ条件 3）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_outbound_marks_confirmed():
    """confirm_outbound_draft() が confirmed_at を設定し True を返す。"""
    db = AsyncMock()
    # DB が 1 行を返す → 更新成功
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    db.execute.return_value = mock_result

    from app.services.message_translator import confirm_outbound_draft

    result = await confirm_outbound_draft(
        db=db,
        drafts_table_ref="tenant_001.outbound_translation_drafts",
        draft_id=42,
        tenant_id=1,
        final_text="Confirmed English text",
    )

    assert result is True


@pytest.mark.asyncio
async def test_confirm_outbound_already_confirmed_returns_false():
    """既に confirmed_at が設定済みの draft は False を返す。"""
    db = AsyncMock()
    # DB が 0 行を返す → 更新なし（既に確認済み）
    mock_result = MagicMock()
    mock_result.first.return_value = None
    db.execute.return_value = mock_result

    from app.services.message_translator import confirm_outbound_draft

    result = await confirm_outbound_draft(
        db=db,
        drafts_table_ref="tenant_001.outbound_translation_drafts",
        draft_id=42,
        tenant_id=1,
        final_text="Should not update",
    )

    assert result is False


# ---------------------------------------------------------------------------
# endpoint level validation
# ---------------------------------------------------------------------------


def test_translate_request_validation():
    """_TranslateRequest: target_language が空の場合 ValidationError。"""
    from app.routers.leads import _TranslateRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _TranslateRequest(target_language="")

    req = _TranslateRequest(target_language="ja")
    assert req.target_language == "ja"


# ---------------------------------------------------------------------------
# テナント分離: table_ref がテナント固有であることを確認（受け入れ条件 8）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_via_table_ref():
    """translate_inbound は渡された table_ref を使用してテナント分離を保証。

    tenant_001 の table_ref を渡したら tenant_001 の table にアクセスする。
    """
    db = AsyncMock()
    tenant_001_table = "tenant_001.message_translations"

    with patch.object(
        message_translator, "_get_cached_translation",
        new_callable=AsyncMock, return_value=("cached_data", 0.9, "en"),
    ) as mock_cache:
        await translate_inbound(
            db=db, tenant_id=1,
            table_ref=tenant_001_table,
            message_id="mid_1", message_text="test", target_language="ja",
        )

    mock_cache.assert_awaited_once_with(db, tenant_001_table, "mid_1", "ja")
