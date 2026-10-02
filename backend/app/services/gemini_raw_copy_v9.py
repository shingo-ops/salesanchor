"""Gemini 書き写し v9（比較試験用）。

設計: docs/handoff/gemini-v9/design.md §3〜§5
v8（gemini_raw_copy_v8.py・raw_copy_v8.txt）の挙動は変えない。v8 の関数・定数は import して使い、複製しない。
このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
"""

from __future__ import annotations

import copy
import unicodedata
from pathlib import Path
from typing import Any

from app.services import gemini_raw_copy_v8 as v8

# 試験のあいだはこのファイルが正本。採用が決まったら DB（extraction_prompt_config）へ移す。
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "raw_copy_v9.txt"

# (値の欄, 行番号の欄)
_LINE_FIELDS = (("state", "state_line"), ("ship", "ship_line"))
_NONE = "none"


def _build_v9_schema() -> dict[str, Any]:
    """V8_RESPONSE_SCHEMA を書き換えずに写し、state_line・ship_line を足す。"""
    schema = copy.deepcopy(v8.V8_RESPONSE_SCHEMA)
    item = schema["properties"]["items"]["items"]
    for _, line_field in _LINE_FIELDS:
        item["properties"][line_field] = {"type": ["integer", "null"]}
        item["required"].append(line_field)
    return schema


V9_RESPONSE_SCHEMA: dict[str, Any] = _build_v9_schema()


def load_v9_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """照合用：NFKC で正規化し、空白を除く。"""
    s = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in s if not ch.isspace())


def _line_field_type_error(obj: dict) -> str | None:
    """state_line・ship_line の有無と型の検査。違反があれば理由を返す。"""
    for _, line_field in _LINE_FIELDS:
        if line_field not in obj:
            return f"必須の欄がない: {line_field}"
        value = obj[line_field]
        if value is not None and not v8._is_int(value):
            return f"型が違う（整数か null が必要）: {line_field}"
    return None


def _same_line_heading_to_null(item: dict) -> dict:
    """見出しの範囲が自分の範囲と同じなら（商品名と価格が同じ行）、見出しを null にした写しを返す。"""
    if (item["heading_line_start"], item["heading_line_end"]) == (item["line_start"], item["line_end"]):
        return {**item, "heading_line_start": None, "heading_line_end": None}
    return item


def _check_line_field(
    value: str, line_no: int | None, lines: list[str], label: str
) -> tuple[str, int | None, str | None]:
    """(値, 行番号, 理由)。理由があるときは、確かめられない値を none にして返す。"""
    if _norm(value) in ("", _NONE):
        if line_no is not None:
            return value, None, f"{label} が none なのに行番号がある: {line_no}"
        return value, None, None
    if line_no is None:
        return _NONE, None, f"{label} に値があるのに行番号が null"
    if not 1 <= line_no <= len(lines):
        return _NONE, None, f"{label} の行番号が範囲外: {line_no}（1〜{len(lines)}）"
    if _norm(value) not in _norm(lines[line_no - 1]):
        return _NONE, None, f"{label} の文字が {line_no} 行目に無い"
    return value, line_no, None


def _attach_line_fields(index: int, obj: dict, item: dict, lines: list[str], errors: list[dict]) -> dict:
    """state・ship を行番号の行と照合し、raw_state_line・raw_ship_line を足した写しを返す。

    値を空にしたときは、件を残したまま errors に kept=True で理由を足す。
    """
    updates: dict[str, Any] = {}
    for field, line_field in _LINE_FIELDS:
        value, line_no, reason = _check_line_field(obj[field], obj[line_field], lines, field)
        updates[f"raw_{field}"] = value
        updates[f"raw_{line_field}"] = line_no
        if reason is not None:
            errors.append({"index": index, "error": f"値を空にした（件は残す）: {reason}", "item": obj, "kept": True})
    return {**item, **updates}


def parse_v9_response(response_text: str, raw_text: str) -> tuple[list[dict], list[dict]]:
    """v8 の検査に、設計 §5 の I-1〜I-3 を足したもの。

    戻り値は parse_v8_response と同じ (items, errors)。items のキーは v8 のキーに
    raw_state_line・raw_ship_line を足したもの。件を残して値だけ空にしたときの errors には kept=True が付く。
    """
    lines = raw_text.split("\n")
    objs, whole_errors = v8._load_items(response_text)
    if objs is None:
        return [], whole_errors

    errors: list[dict] = []
    candidates: list[tuple[int, dict]] = []
    for index, obj in enumerate(objs):
        item, err = v8._validate_one(index, obj, len(lines))
        if err is None:
            reason = _line_field_type_error(obj)
            if reason is not None:
                err = {"index": index, "error": reason, "item": obj}
        if err is not None:
            errors.append(err)
            continue
        assert item is not None
        item = _same_line_heading_to_null(item)
        item = _attach_line_fields(index, obj, item, lines, errors)
        candidates.append((index, item))

    accepted = v8._accept_non_overlapping(candidates, errors)
    errors.sort(key=lambda e: (e["index"] is None, e["index"] or 0))
    return accepted, errors
