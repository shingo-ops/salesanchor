"""Gemini 書き写し v8（比較試験用）。

設計: docs/handoff/gemini-v8/design.md §2〜§5
本番（v7: gemini_extraction_svc.call_gemini_raw_copy）と旧方式（v6）は変えない。
このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
既存の関数・定数は import して使い、複製しない。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded

from app.services import gemini_extraction_svc as _gem
from app.services import llm_budget

logger = logging.getLogger(__name__)

# 試験のあいだはこのファイルが正本。採用が決まったら DB（extraction_prompt_config）へ移し、ファイルは削除する。
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "raw_copy_v8.txt"

_REQUIRED_STR_FIELDS = ("product_name", "price", "unit", "quantity", "state", "ship", "multi_note")
_REQUIRED_INT_FIELDS = ("source_line_start", "source_line_end")
_NULLABLE_INT_FIELDS = ("heading_line_start", "heading_line_end")

V8_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "price": {"type": "string"},
                    "unit": {"type": "string"},
                    "quantity": {"type": "string"},
                    "state": {"type": "string"},
                    "ship": {"type": "string"},
                    "source_line_start": {"type": "integer"},
                    "source_line_end": {"type": "integer"},
                    "heading_line_start": {"type": ["integer", "null"]},
                    "heading_line_end": {"type": ["integer", "null"]},
                    "multi_note": {"type": "string"},
                },
                "required": [
                    *_REQUIRED_STR_FIELDS[:6], *_REQUIRED_INT_FIELDS, *_NULLABLE_INT_FIELDS, "multi_note",
                ],
            },
        }
    },
    "required": ["items"],
}

_USAGE_ATTRS = (
    "prompt_token_count", "cached_content_token_count", "candidates_token_count",
    "thoughts_token_count", "tool_use_prompt_token_count", "total_token_count",
)


def load_v8_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 前処理
# ---------------------------------------------------------------------------


def keep_chars_from_links(knowledge_links: list[dict] | None) -> set[str]:
    """その仕入元の block_delimiter の pattern に含まれる文字（絵文字削除から守る文字）。"""
    chars: set[str] = set()
    for lnk in knowledge_links or []:
        if lnk.get("category") == "block_delimiter":
            chars.update(lnk.get("pattern") or "")
    return chars


def format_prompt_input_v8(raw_text: str, keep_chars: set[str]) -> str:
    """[L0001] 行テキスト 形式に変換する。絵文字は _EMOJI_RE と同じ範囲で消すが keep_chars は残す。

    行の数と [L0001] の書式は既存の annotate_lines と同じ。
    """
    cleaned = _gem._EMOJI_RE.sub(
        lambda m: "".join(ch for ch in m.group(0) if ch in keep_chars), raw_text
    )
    annotated = _gem.annotate_lines(cleaned)
    return "\n".join(f'[{item["id"]}] {item["text"]}' for item in annotated)


def build_supplier_note_v8(supplier_context: dict | None, knowledge_links: list[dict] | None) -> str:
    """v7 と同じ並び・文言の仕入元ルール。ただしデフォルト単位は入れない（設計 §1 ②）。

    既存の _build_supplier_context_note を（変更せずに）呼び、extraction_default_unit だけ
    除いた写しの辞書を渡す。knowledge_links は block_delimiter のみ、ship_format は末尾に足す（v7 と同じ）。
    """
    ctx = {k: v for k, v in (supplier_context or {}).items() if k != "extraction_default_unit"}
    filtered_links = [lnk for lnk in (knowledge_links or []) if lnk.get("category") == "block_delimiter"]
    note = _gem._build_supplier_context_note(ctx, knowledge_links=filtered_links)

    ship_format = ctx.get("extraction_ship_format")
    if ship_format:
        ship_line = f"- 発送日フォーマット: {ship_format}"
        note = f"{note}\n{ship_line}" if note else f"【仕入元固有の抽出ルール】\n{ship_line}"
    return note


def build_prompt_v8(
    raw_text: str, *, prompt_text: str, supplier_context: dict | None, knowledge_links: list[dict] | None
) -> str:
    note = build_supplier_note_v8(supplier_context, knowledge_links)
    section = f"\n{note}\n" if note else ""
    prompt_input = format_prompt_input_v8(raw_text, keep_chars_from_links(knowledge_links))
    return f"{prompt_text}{section}\n原文:\n{prompt_input}"


# ---------------------------------------------------------------------------
# Gemini 呼び出し
# ---------------------------------------------------------------------------


def usage_to_dict(usage: object) -> dict:
    """usage_metadata を dict にする。dict にできなければ取れた属性だけを使い、取れなかった名前を記録する。"""
    if usage is None:
        return {"_missing_attrs": list(_USAGE_ATTRS)}
    dump = getattr(usage, "model_dump", None)
    if callable(dump):
        try:
            result = dump(mode="json")
            if isinstance(result, dict):
                return result
        except Exception:  # noqa: BLE001
            logger.warning("[gemini_v8] usage_metadata.model_dump failed; falling back to attributes")
    raw: dict[str, Any] = {}
    missing: list[str] = []
    for name in _USAGE_ATTRS:
        value = getattr(usage, name, None)
        if value is None:
            missing.append(name)
        else:
            raw[name] = value
    raw["_missing_attrs"] = missing
    return raw


def _split_parts(response: object) -> tuple[str, list[str]]:
    """(thought ではない部分の連結, thought 部分のテキストのリスト)。"""
    answer: list[str] = []
    thoughts: list[str] = []
    found = False
    for cand in getattr(response, "candidates", None) or []:
        parts = getattr(getattr(cand, "content", None), "parts", None) or []
        for part in parts:
            found = True
            text = getattr(part, "text", None) or ""
            (thoughts if getattr(part, "thought", False) else answer).append(text)
    if not found:
        return getattr(response, "text", "") or "", []
    return "".join(answer), thoughts


def call_gemini_raw_copy_v8(
    raw_text: str, *,
    prompt_text: str,
    supplier_context: dict | None,
    knowledge_links: list[dict] | None,
    thinking_level: str | None,
    include_thoughts: bool,
    use_schema: bool,
    temperature: float | None,
) -> dict:
    """v8 を呼ぶ。config は None でない引数だけを入れる（temperature 未指定なら既定の 1.0）。

    Returns: {"response_text", "thought_summaries", "usage_raw", "usage_counts"}
    Raises: RuntimeError（API 呼び出し失敗）
    """
    from google.genai import types as genai_types  # type: ignore[import-untyped]

    full_prompt = build_prompt_v8(
        raw_text, prompt_text=prompt_text, supplier_context=supplier_context, knowledge_links=knowledge_links
    )

    config_kwargs: dict[str, Any] = {}
    if temperature is not None:
        config_kwargs["temperature"] = temperature
    if use_schema:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_json_schema"] = V8_RESPONSE_SCHEMA
    thinking_kwargs: dict[str, Any] = {"include_thoughts": include_thoughts}
    if thinking_level is not None:
        thinking_kwargs["thinking_level"] = thinking_level
    config_kwargs["thinking_config"] = genai_types.ThinkingConfig(**thinking_kwargs)

    client = _gem._get_genai_client()
    logger.info("[gemini_v8] calling Gemini, model=%s text_len=%d", _gem._GEMINI_MODEL, len(raw_text))
    try:
        response = client.models.generate_content(
            model=_gem._GEMINI_MODEL,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(**config_kwargs),
        )
    except SoftTimeLimitExceeded:
        raise
    except Exception as exc:
        raise RuntimeError(f"Gemini v8 API 呼び出し失敗: {_gem._safe_error_message(exc)}") from exc

    response_text, thought_summaries = _split_parts(response)
    usage = getattr(response, "usage_metadata", None)
    return {
        "response_text": response_text,
        "thought_summaries": thought_summaries,
        "usage_raw": usage_to_dict(usage),
        "usage_counts": llm_budget.usage_counts_from(usage),
    }


# ---------------------------------------------------------------------------
# 受け取り後の検査（設計 §5）
# ---------------------------------------------------------------------------


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_fields(obj: object) -> str | None:
    """必須の欄と型の検査。違反があれば理由を返す。"""
    if not isinstance(obj, dict):
        return "件がオブジェクトではない"
    for name in (*_REQUIRED_STR_FIELDS, *_REQUIRED_INT_FIELDS, *_NULLABLE_INT_FIELDS):
        if name not in obj:
            return f"必須の欄がない: {name}"
    for name in _REQUIRED_STR_FIELDS:
        if not isinstance(obj[name], str):
            return f"型が違う（文字列が必要）: {name}"
    for name in _REQUIRED_INT_FIELDS:
        if not _is_int(obj[name]):
            return f"型が違う（整数が必要）: {name}"
    for name in _NULLABLE_INT_FIELDS:
        if obj[name] is not None and not _is_int(obj[name]):
            return f"型が違う（整数か null が必要）: {name}"
    return None


def _span_error(start: int, end: int, max_line: int, label: str) -> str | None:
    if start < 1 or end > max_line or start > end:
        return f"{label}が範囲外: {start}-{end}（1〜{max_line} かつ開始<=終了）"
    return None


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _to_item(obj: dict) -> dict:
    return {
        "raw_product_name": obj["product_name"], "raw_price": obj["price"], "raw_unit": obj["unit"],
        "raw_quantity": obj["quantity"], "raw_state": obj["state"], "raw_ship": obj["ship"],
        "raw_multi": obj["multi_note"],
        "line_start": obj["source_line_start"], "line_end": obj["source_line_end"],
        "heading_line_start": obj["heading_line_start"], "heading_line_end": obj["heading_line_end"],
    }


def _validate_one(index: int, obj: object, max_line: int) -> tuple[dict | None, dict | None]:
    reason = _check_fields(obj)
    if reason is None:
        assert isinstance(obj, dict)
        reason = _span_error(obj["source_line_start"], obj["source_line_end"], max_line, "範囲")
        has_heading = obj["heading_line_start"] is not None and obj["heading_line_end"] is not None
        if reason is None and (obj["heading_line_start"] is None) != (obj["heading_line_end"] is None):
            reason = "見出しの範囲が片方だけ null"
        if reason is None and has_heading:
            reason = _span_error(obj["heading_line_start"], obj["heading_line_end"], max_line, "見出しの範囲")
    if reason is not None:
        return None, {"index": index, "error": reason, "item": obj}
    return _to_item(obj), None


def parse_v8_response(response_text: str, raw_text: str) -> tuple[list[dict], list[dict]]:
    """JSON を読み、件ごとに設計 §5 の検査をする。

    戻り値: (items, errors)。items は v7 の parse_raw_copy_response と同じキー。
    errors: [{"index": 件の番号 or None, "error": 理由, "item": 元の件}, ...]
    JSON として読めない・items 配列がない場合は、全体を1つのエラー（index=None）にする。
    """
    max_line = len(raw_text.split("\n"))
    try:
        data = json.loads(response_text)
    except (json.JSONDecodeError, TypeError) as exc:
        return [], [{"index": None, "error": f"JSON として読めない: {exc}", "item": None}]
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return [], [{"index": None, "error": "JSON に items 配列がない", "item": None}]

    errors: list[dict] = []
    candidates: list[tuple[int, dict]] = []
    for index, obj in enumerate(data["items"]):
        item, err = _validate_one(index, obj, max_line)
        if err is not None:
            errors.append(err)
        else:
            assert item is not None
            candidates.append((index, item))

    headings = [
        (it["heading_line_start"], it["heading_line_end"])
        for _, it in candidates if it["heading_line_start"] is not None
    ]
    accepted: list[dict] = []
    spans: list[tuple[int, int]] = []
    for index, item in candidates:
        span = (item["line_start"], item["line_end"])
        if any(_overlaps(span, h) for h in headings):
            errors.append({"index": index, "error": f"範囲が見出しの範囲と重なる: {span}", "item": item})
        elif any(_overlaps(span, other) for other in spans):
            errors.append({"index": index, "error": f"範囲がほかの件と重なり: {span}", "item": item})
        else:
            accepted.append(item)
            spans.append(span)
    errors.sort(key=lambda e: (e["index"] is None, e["index"] or 0))
    return accepted, errors
