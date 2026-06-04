from __future__ import annotations

"""
ADR-110: 会話ログ翻訳サブシステム — コアサービス。

ADR-088 基盤を拡張:
  - グロッサリ適用（専門用語・商品名・スラング の正確な訳 / 原語保持）
  - 確信度スコアリング（0–1）
  - モデル戦略:
      受信和訳 = TRANSLATION_MODEL_RECEIVE（既定: gemini-2.5-flash、安い）
                 低確信度 / 長文 → TRANSLATION_MODEL_SEND にエスカレート
      送信英訳 = TRANSLATION_MODEL_SEND（既定: gemini-2.5-pro、最上位必須）
  - 送信下訳の生成（保存・表示のみ。送信はしない）
  - 冪等: DB キャッシュヒットで API 呼ばない
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.inventory_parser_llm import (
    LLMConfigError,
    LLMParseError,
)
from app.services.llm_budget import BudgetStatus, check_budget, record_cost
from app.services.translation_glossary import GlossaryEntry, format_glossary_for_prompt, load_glossary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (env override 可能。方針は固定: 送信=最上位必須)
# ---------------------------------------------------------------------------

MODEL_RECEIVE: str = os.getenv("TRANSLATION_MODEL_RECEIVE", "gemini-2.5-flash")
MODEL_SEND: str = os.getenv("TRANSLATION_MODEL_SEND", "gemini-2.5-pro")
CONF_THRESHOLD_RECEIVE: float = float(
    os.getenv("TRANSLATION_CONFIDENCE_THRESHOLD_RECEIVE", "0.70")
)
CONF_THRESHOLD_SEND: float = float(
    os.getenv("TRANSLATION_CONFIDENCE_THRESHOLD_SEND", "0.85")
)
# 長文エスカレート閾値（受信のみ）
_LONG_TEXT_CHARS: int = int(os.getenv("TRANSLATION_LONG_TEXT_CHARS", "800"))


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlaggedTerm:
    """低確信度の語句。"""
    term: str
    reason: str


@dataclass(frozen=True)
class TranslationResult:
    """translate_inbound() / generate_outbound_draft() の戻り値。"""

    translated_text: str
    cached: bool
    engine: str
    confidence: float             # 0.0–1.0
    original_language: str | None  # 判定言語 "en", "zh", etc.
    flagged_terms: list[FlaggedTerm]


# ---------------------------------------------------------------------------
# Gemini SDK lazy init (ADR-088 パターン踏襲)
# ---------------------------------------------------------------------------

_GENAI_CACHE: dict[str, Any] = {}


def _get_genai_module() -> Any:
    if "module" not in _GENAI_CACHE:
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
        except ImportError as exc:
            raise LLMConfigError(
                "google-generativeai がインストールされていません。"
            ) from exc
        _GENAI_CACHE["module"] = genai
    return _GENAI_CACHE["module"]


def _ensure_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise LLMConfigError("GEMINI_API_KEY が未設定です。翻訳機能は無効化されます。")
    return key


# ---------------------------------------------------------------------------
# DB cache (inbound translations)
# ---------------------------------------------------------------------------


async def _get_cached_translation(
    db: AsyncSession,
    table_ref: str,
    message_id: str,
    target_language: str,
) -> tuple[str, float | None, str | None] | None:
    """キャッシュ済み翻訳を返す。(translated_text, confidence, original_language) or None."""
    result = await db.execute(
        text(
            f"SELECT translated_text, confidence, original_language "
            f"FROM {table_ref} "
            "WHERE message_id = :message_id AND target_language = :target_language"
        ),
        {"message_id": message_id, "target_language": target_language},
    )
    row = result.first()
    if row:
        return str(row[0]), row[1], row[2]
    return None


async def _save_translation(
    db: AsyncSession,
    table_ref: str,
    message_id: str,
    target_language: str,
    translated_text: str,
    engine: str,
    confidence: float,
    original_language: str | None,
) -> None:
    """翻訳結果を DB キャッシュに保存 (ON CONFLICT で冪等)。"""
    await db.execute(
        text(
            f"INSERT INTO {table_ref} "
            "(message_id, target_language, translated_text, engine, confidence, original_language) "
            "VALUES (:message_id, :target_language, :translated_text, :engine, :confidence, :original_language) "
            "ON CONFLICT (message_id, target_language) DO UPDATE "
            "SET translated_text = :translated_text, engine = :engine, "
            "    confidence = :confidence, original_language = :original_language"
        ),
        {
            "message_id": message_id,
            "target_language": target_language,
            "translated_text": translated_text,
            "engine": engine,
            "confidence": confidence,
            "original_language": original_language,
        },
    )


# ---------------------------------------------------------------------------
# Outbound draft DB ops
# ---------------------------------------------------------------------------


async def save_outbound_draft(
    db: AsyncSession,
    drafts_table_ref: str,
    tenant_id: int,
    lead_id: int | None,
    original_text: str,
    draft_text: str,
    confidence: float,
    flagged_terms: list[FlaggedTerm],
    model: str,
) -> int:
    """送信下訳を DB に保存して draft_id を返す。"""
    result = await db.execute(
        text(
            f"INSERT INTO {drafts_table_ref} "
            "(tenant_id, lead_id, original_text, draft_text, confidence, flagged_terms, model) "
            "VALUES (:tenant_id, :lead_id, :original_text, :draft_text, "
            "        :confidence, :flagged_terms, :model) "
            "RETURNING id"
        ),
        {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "original_text": original_text,
            "draft_text": draft_text,
            "confidence": confidence,
            "flagged_terms": json.dumps(
                [{"term": f.term, "reason": f.reason} for f in flagged_terms]
            ),
            "model": model,
        },
    )
    row = result.first()
    assert row is not None
    return int(row[0])


async def confirm_outbound_draft(
    db: AsyncSession,
    drafts_table_ref: str,
    draft_id: int,
    tenant_id: int,
    final_text: str,
) -> bool:
    """送信下訳を「人が確認済み」にマーク。

    Returns True if updated, False if not found.
    確認済みの draft は再確認不可（confirmed_at IS NULL チェック）。
    """
    result = await db.execute(
        text(
            f"UPDATE {drafts_table_ref} "
            "SET confirmed_at = NOW(), final_text = :final_text "
            "WHERE id = :draft_id AND tenant_id = :tenant_id AND confirmed_at IS NULL "
            "RETURNING id"
        ),
        {"draft_id": draft_id, "tenant_id": tenant_id, "final_text": final_text},
    )
    return result.first() is not None


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_inbound_prompt(
    message_text: str,
    target_language: str,
    glossary_entries: Sequence[GlossaryEntry],
) -> str:
    """受信メッセージ翻訳プロンプト。グロッサリ注入 + structured JSON 出力。"""
    glossary_block = format_glossary_for_prompt(glossary_entries)
    lang_label = "Japanese" if target_language == "ja" else target_language

    parts = [
        "You are a professional translator specializing in e-commerce and trading card games (TCG).",
        f"Translate the following message to {lang_label}.",
        "Preserve the tone and nuance of the original.",
    ]
    if glossary_block:
        parts.append("")
        parts.append(glossary_block)

    parts += [
        "",
        "Respond ONLY with a JSON object in exactly this format (no markdown, no extra text):",
        '{"translated_text": "...", "confidence": 0.95, "original_language": "en", "flagged_terms": []}',
        "",
        "Rules:",
        '- "confidence": float 0.0-1.0 (how confident you are in the translation accuracy)',
        '- "original_language": ISO 639-1 code of the detected source language (e.g. "en", "zh", "ko")',
        '- "flagged_terms": list of {"term": "...", "reason": "..."} for terms you are uncertain about',
        "",
        "Message to translate:",
        message_text,
    ]
    return "\n".join(parts)


def _build_outbound_prompt(
    draft_text: str,
    target_language: str,
    glossary_entries: Sequence[GlossaryEntry],
) -> str:
    """送信英訳プロンプト（担当者の日本語下書き → 相手言語）。"""
    glossary_block = format_glossary_for_prompt(glossary_entries)
    lang_label = "English" if target_language == "en" else target_language

    parts = [
        "You are a professional business translator for a Japanese TCG (trading card game) exporter.",
        f"Translate the following Japanese message to {lang_label} for sending to an overseas buyer.",
        "Maintain professional business tone. Be precise with product names and technical terms.",
    ]
    if glossary_block:
        parts.append("")
        parts.append(glossary_block)

    parts += [
        "",
        "Respond ONLY with a JSON object in exactly this format (no markdown, no extra text):",
        '{"translated_text": "...", "confidence": 0.95, "flagged_terms": []}',
        "",
        "Rules:",
        '- "confidence": float 0.0-1.0 (how confident you are in the translation quality)',
        '- "flagged_terms": list of {"term": "...", "reason": "..."} for ambiguous or uncertain terms',
        "  (include any terms where you had to make a judgment call or are unsure of context)",
        "",
        "Japanese message to translate:",
        draft_text,
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Gemini API call
# ---------------------------------------------------------------------------


async def _call_gemini(
    prompt: str,
    model_name: str,
) -> tuple[str, int, int]:
    """Gemini API を呼び出してテキストと token 使用量を返す。

    Returns:
        (response_text, input_tokens, output_tokens)
    """
    api_key = _ensure_api_key()
    genai = _get_genai_module()
    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.1},
        )
        if hasattr(model, "generate_content_async"):
            response = await model.generate_content_async(prompt)
        else:
            import asyncio
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, model.generate_content, prompt)
    except Exception as exc:
        logger.exception("[message_translator] Gemini call failed (model=%s): %s", model_name, exc)
        raise LLMParseError(f"Gemini API 呼び出し失敗: {exc}") from exc

    text_payload = getattr(response, "text", "") or ""
    if not text_payload:
        raise LLMParseError("Gemini 応答が空でした")

    usage = getattr(response, "usage_metadata", None)
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    return text_payload.strip(), input_tokens, output_tokens


def _parse_translation_response(
    response_text: str,
    threshold: float,
) -> tuple[str, float, str | None, list[FlaggedTerm]]:
    """Gemini JSON レスポンスをパース。

    Returns: (translated_text, confidence, original_language, flagged_terms)
    """
    try:
        raw = response_text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("[message_translator] JSON parse failed: %s / raw=%r", exc, response_text[:200])
        return response_text.strip(), 0.5, None, []

    translated_text = str(data.get("translated_text", "")).strip()
    if not translated_text:
        raise LLMParseError("翻訳結果が空でした")

    confidence_raw = data.get("confidence", 0.8)
    try:
        confidence = float(confidence_raw)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.8

    original_language = data.get("original_language")
    if original_language:
        original_language = str(original_language).strip().lower()[:10]

    flagged_raw = data.get("flagged_terms", [])
    flagged_terms: list[FlaggedTerm] = []
    if isinstance(flagged_raw, list):
        for item in flagged_raw:
            if isinstance(item, dict):
                term = str(item.get("term", "")).strip()
                reason = str(item.get("reason", "")).strip()
                if term:
                    flagged_terms.append(FlaggedTerm(term=term, reason=reason))

    return translated_text, confidence, original_language, flagged_terms


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


async def translate_inbound(
    db: AsyncSession,
    tenant_id: int,
    table_ref: str,
    message_id: str,
    message_text: str,
    target_language: str = "ja",
) -> TranslationResult:
    """受信メッセージを和訳する。

    キャッシュヒットなら Gemini を呼ばない（冪等）。
    低確信度または長文は上位モデルにエスカレート。

    Args:
        table_ref: tenant-prefixed message_translations table
        message_id: meta_messages.message_id（キャッシュキー）
    """
    # 1. DB キャッシュ確認
    cached = await _get_cached_translation(db, table_ref, message_id, target_language)
    if cached is not None:
        translated_text, confidence, original_language = cached
        logger.info("[translator] cache hit: message_id=%s lang=%s", message_id, target_language)
        return TranslationResult(
            translated_text=translated_text,
            cached=True,
            engine="cached",
            confidence=confidence if confidence is not None else 1.0,
            original_language=original_language,
            flagged_terms=[],
        )

    # 2. グロッサリロード
    glossary = await load_glossary(db, tenant_id, language_pair="en->ja")

    # 3. 初回呼び出し: 安いモデル
    model = MODEL_RECEIVE
    budget_status = await check_budget(db, tenant_id)
    if budget_status in (BudgetStatus.HARD_STOP, BudgetStatus.NO_BUDGET_ROW):
        raise BudgetExceededError(budget_status)

    prompt = _build_inbound_prompt(message_text, target_language, glossary)
    response_text, in_tokens, out_tokens = await _call_gemini(prompt, model)
    await record_cost(db, tenant_id, in_tokens, out_tokens, model=model)

    translated_text, confidence, original_language, flagged_terms = _parse_translation_response(
        response_text, CONF_THRESHOLD_RECEIVE
    )

    # 4. エスカレート: 低確信度 or 長文
    is_long = len(message_text) > _LONG_TEXT_CHARS
    if (confidence < CONF_THRESHOLD_RECEIVE or is_long) and model != MODEL_SEND:
        logger.info(
            "[translator] escalate to %s (conf=%.2f, long=%s): message_id=%s",
            MODEL_SEND, confidence, is_long, message_id,
        )
        budget_status2 = await check_budget(db, tenant_id)
        if budget_status2 not in (BudgetStatus.HARD_STOP, BudgetStatus.NO_BUDGET_ROW):
            prompt2 = _build_inbound_prompt(message_text, target_language, glossary)
            resp2, in2, out2 = await _call_gemini(prompt2, MODEL_SEND)
            await record_cost(db, tenant_id, in2, out2, model=MODEL_SEND)
            t2, c2, ol2, ft2 = _parse_translation_response(resp2, CONF_THRESHOLD_RECEIVE)
            if c2 > confidence:
                translated_text, confidence, original_language, flagged_terms = t2, c2, ol2, ft2
                model = MODEL_SEND

    # 5. DB キャッシュ保存
    await _save_translation(
        db, table_ref, message_id, target_language,
        translated_text, model, confidence, original_language,
    )
    await db.commit()

    logger.info(
        "[translator] inbound done: message_id=%s conf=%.2f model=%s",
        message_id, confidence, model,
    )
    return TranslationResult(
        translated_text=translated_text,
        cached=False,
        engine=model,
        confidence=confidence,
        original_language=original_language,
        flagged_terms=flagged_terms,
    )


async def generate_outbound_draft(
    db: AsyncSession,
    tenant_id: int,
    drafts_table_ref: str,
    lead_id: int | None,
    draft_text: str,
    target_language: str = "en",
) -> tuple[int, TranslationResult]:
    """担当者の日本語下書きを相手言語の下訳に変換して保存。

    送信はしない。draft_id と TranslationResult を返す。
    送信英訳は常に最上位モデル（MODEL_SEND）を使用。

    Returns:
        (draft_id, TranslationResult)
    """
    glossary = await load_glossary(db, tenant_id, language_pair="ja->en")

    budget_status = await check_budget(db, tenant_id)
    if budget_status in (BudgetStatus.HARD_STOP, BudgetStatus.NO_BUDGET_ROW):
        raise BudgetExceededError(budget_status)

    # 送信英訳は常に最上位モデル（固定方針）
    model = MODEL_SEND
    prompt = _build_outbound_prompt(draft_text, target_language, glossary)
    response_text, in_tokens, out_tokens = await _call_gemini(prompt, model)
    await record_cost(db, tenant_id, in_tokens, out_tokens, model=model)

    translated_text, confidence, _, flagged_terms = _parse_translation_response(
        response_text, CONF_THRESHOLD_SEND
    )

    draft_id = await save_outbound_draft(
        db=db,
        drafts_table_ref=drafts_table_ref,
        tenant_id=tenant_id,
        lead_id=lead_id,
        original_text=draft_text,
        draft_text=translated_text,
        confidence=confidence,
        flagged_terms=flagged_terms,
        model=model,
    )
    await db.commit()

    logger.info(
        "[translator] outbound draft: draft_id=%s conf=%.2f model=%s",
        draft_id, confidence, model,
    )
    return draft_id, TranslationResult(
        translated_text=translated_text,
        cached=False,
        engine=model,
        confidence=confidence,
        original_language="ja",
        flagged_terms=flagged_terms,
    )


# ---------------------------------------------------------------------------
# ADR-088 互換: translate_message（既存呼び出し元向け）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegacyTranslationResult:
    """ADR-088 互換戻り値。"""
    translated_text: str
    cached: bool
    engine: str


async def translate_message(
    db: AsyncSession,
    tenant_id: int,
    table_ref: str,
    message_id: str,
    message_text: str,
    target_language: str,
) -> LegacyTranslationResult:
    """ADR-088 互換エントリポイント。leads.py から呼ばれる。translate_inbound() に委譲。"""
    result = await translate_inbound(
        db=db,
        tenant_id=tenant_id,
        table_ref=table_ref,
        message_id=message_id,
        message_text=message_text,
        target_language=target_language,
    )
    return LegacyTranslationResult(
        translated_text=result.translated_text,
        cached=result.cached,
        engine=result.engine,
    )


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BudgetExceededError(Exception):
    def __init__(self, status: BudgetStatus) -> None:
        self.status = status
        super().__init__(f"LLM budget exceeded: {status.value}")


__all__ = [
    "BudgetExceededError",
    "CONF_THRESHOLD_RECEIVE",
    "CONF_THRESHOLD_SEND",
    "FlaggedTerm",
    "LegacyTranslationResult",
    "MODEL_RECEIVE",
    "MODEL_SEND",
    "TranslationResult",
    "confirm_outbound_draft",
    "generate_outbound_draft",
    "translate_inbound",
    "translate_message",
]
