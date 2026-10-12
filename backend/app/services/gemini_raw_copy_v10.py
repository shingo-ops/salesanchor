"""Gemini 書き写し v10（比較試験用）。Gemini は行番号と価格・数量の文字だけを出し、ほかはシステムが原文から取る。

設計: docs/handoff/gemini-v10/design.md §3
v8・v9 のファイルは変えない。マスタ照合は既存の resolve_* をそのまま呼び、同じ処理を写さない。
このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services import gemini_raw_copy_v8 as v8
from app.services.extraction_judgement_svc import resolve_price_quantity
from app.services.tcg_analyzer_svc import resolve_condition_v2, resolve_status_v2, resolve_unit_v2

# 試験のあいだはこのファイルが正本。採用が決まったら DB（extraction_prompt_config）へ移す。
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "raw_copy_v10.txt"

_NONE = "none"
_STR_FIELDS = ("price", "quantity")
_LINE_LIST_FIELDS = ("item_lines", "heading_lines", "shared_lines", "name_lines")

_LINE_ARRAY = {"type": "array", "items": {"type": "integer"}}
V10_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "price": {"type": "string"},
                    "quantity": {"type": "string"},
                    "price_line": {"type": "integer"},
                    "item_lines": _LINE_ARRAY,
                    "heading_lines": _LINE_ARRAY,
                    "shared_lines": _LINE_ARRAY,
                    "name_lines": _LINE_ARRAY,
                },
                "required": ["price", "quantity", "price_line", *_LINE_LIST_FIELDS],
            },
        }
    },
    "required": ["items"],
}


def load_v10_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 受け取り（設計 §3-2）
# ---------------------------------------------------------------------------


def _is_line_list(value: object) -> bool:
    return isinstance(value, list) and all(v8._is_int(v) for v in value)


def _shape_error(obj: object, max_line: int) -> str | None:
    """欄・型・行番号の範囲・item_lines と price_line の関係の検査。違反があれば理由を返す。"""
    if not isinstance(obj, dict):
        return "件がオブジェクトではない"
    for name in (*_STR_FIELDS, "price_line", *_LINE_LIST_FIELDS):
        if name not in obj:
            return f"必須の欄がない: {name}"
    for name in _STR_FIELDS:
        if not isinstance(obj[name], str):
            return f"型が違う（文字列が必要）: {name}"
    if not v8._is_int(obj["price_line"]):
        return "型が違う（整数が必要）: price_line"
    for name in _LINE_LIST_FIELDS:
        if not _is_line_list(obj[name]):
            return f"型が違う（整数の配列が必要）: {name}"
    for name in ("price_line", *_LINE_LIST_FIELDS):
        values = [obj[name]] if name == "price_line" else obj[name]
        bad = next((n for n in values if not 1 <= n <= max_line), None)
        if bad is not None:
            return f"{name} の行番号が範囲外: {bad}（1〜{max_line}）"
    if not obj["item_lines"]:
        return "item_lines が空"
    if obj["price_line"] not in obj["item_lines"]:
        return f"price_line {obj['price_line']} が item_lines に無い"
    return None


def _normalized(obj: dict) -> dict:
    """配列を重複なし・昇順にした件の写し。"""
    return {
        "price": obj["price"], "quantity": obj["quantity"], "price_line": obj["price_line"],
        **{name: sorted(set(obj[name])) for name in _LINE_LIST_FIELDS},
    }


def _drop_item_line_overlaps(candidates: list[tuple[int, dict]], errors: list[dict]) -> list[tuple[int, dict]]:
    """item_lines が先に出た件と重なる件を捨てる（先に出た件を残す）。"""
    used: set[int] = set()
    kept: list[tuple[int, dict]] = []
    for index, item in candidates:
        overlap = used & set(item["item_lines"])
        if overlap:
            errors.append({"index": index, "error": f"item_lines がほかの件と重なる: {sorted(overlap)}", "item": item})
            continue
        used.update(item["item_lines"])
        kept.append((index, item))
    return kept


def _drop_shared_overlaps(candidates: list[tuple[int, dict]], errors: list[dict]) -> list[tuple[int, dict]]:
    """heading_lines・shared_lines がほかの件の item_lines と重なる件を捨てる。"""
    kept: list[tuple[int, dict]] = []
    for index, item in candidates:
        others = set().union(*(o["item_lines"] for j, o in candidates if j != index))
        overlap = others & (set(item["heading_lines"]) | set(item["shared_lines"]))
        if overlap:
            errors.append({
                "index": index, "item": item,
                "error": f"heading_lines・shared_lines がほかの件の item_lines と重なる: {sorted(overlap)}",
            })
            continue
        kept.append((index, item))
    return kept


def _restrict_name_lines(candidates: list[tuple[int, dict]], objs: list, errors: list[dict]) -> list[dict]:
    """name_lines を、自分の行・見出し・共有の行・ほかの件の item_lines だけにする（外した行は errors に kept=True）。"""
    result: list[dict] = []
    for index, item in candidates:
        others = set().union(*(o["item_lines"] for j, o in candidates if j != index))
        allowed = set(item["item_lines"]) | set(item["heading_lines"]) | set(item["shared_lines"]) | others
        dropped = [n for n in item["name_lines"] if n not in allowed]
        if dropped:
            errors.append({
                "index": index, "item": objs[index], "kept": True,
                "error": f"name_lines から外した（件は残す）: {dropped} は使ってよい行ではない",
            })
            item = {**item, "name_lines": [n for n in item["name_lines"] if n in allowed]}
        result.append(item)
    return result


def parse_v10_response(response_text: str, raw_text: str) -> tuple[list[dict], list[dict]]:
    """JSON を読み、件ごとに設計 §3-2 の検査をする。戻り値は parse_v8_response と同じ形の (items, errors)。

    items のキーは price, quantity, price_line, item_lines, heading_lines, shared_lines, name_lines。
    件を残して一部だけ直したときの errors には kept=True が付く。
    """
    max_line = len(raw_text.split("\n"))
    objs, whole_errors = v8._load_items(response_text)
    if objs is None:
        return [], whole_errors

    errors: list[dict] = []
    candidates: list[tuple[int, dict]] = []
    for index, obj in enumerate(objs):
        reason = _shape_error(obj, max_line)
        if reason is not None:
            errors.append({"index": index, "error": reason, "item": obj})
            continue
        candidates.append((index, _normalized(obj)))

    candidates = _drop_item_line_overlaps(candidates, errors)
    candidates = _drop_shared_overlaps(candidates, errors)
    accepted = _restrict_name_lines(candidates, objs, errors)
    errors.sort(key=lambda e: (e["index"] is None, e["index"] or 0))
    return accepted, errors


# ---------------------------------------------------------------------------
# 原文から取る（設計 §3-3）。すべて純粋関数。
# ---------------------------------------------------------------------------

_DIGIT = "0-9０-９"
_AT_MARKS = "@＠"
_TIMES = "×xX＊"
_EDGE_CHARS = " \t　/／:：×"
_SHIP_WORD_RE = re.compile(r"発送|出荷|入荷|発売|着")
_BRACKET_RE = re.compile(r"[(（【\[]([^)）】\]]*)[)）】\]]")
_STOCK_WORD_RE = re.compile(rf"(?:在庫数|在庫|残り)\s*[{_DIGIT},，]*")
_SYMBOLS_RE = re.compile(r"[@＠¥￥円]")
_TIMES_NEXT_TO_DIGIT_RE = re.compile(rf"(?<=[{_DIGIT}])[×xX](?![A-Za-z])|(?<![A-Za-z])[×xX](?=[{_DIGIT}])")
_PRICE_FOLLOWS = rf"\s*[/／{_AT_MARKS}¥￥]\s*[¥￥]?[{_DIGIT}]"


def _unit_aliases(unit_alias_to_info: dict) -> list[str]:
    """単位の別名（長いものから）。"""
    return sorted((a for a in unit_alias_to_info if a and a.strip()), key=len, reverse=True)


def _starts_with_alias(text: str, pos: int, aliases: list[str]) -> str | None:
    lowered = text.lower()
    return next((a for a in aliases if lowered.startswith(a.lower(), pos)), None)


def _quantity_neighbor_strength(text: str, start: int, end: int, aliases: list[str]) -> int:
    """数量の文字のすぐ隣に 単位・× があれば 2、@ があれば 1、無ければ 0。"""
    before, after = text[:start].rstrip(), text[end:].lstrip()
    if _starts_with_alias(text, end, aliases) or after[:1] in tuple(_TIMES) or before[-1:] in tuple(_TIMES):
        return 2
    if after[:1] in tuple(_AT_MARKS) or before[-1:] in tuple(_AT_MARKS):
        return 1
    return 0


def _is_inside_digit_run(text: str, start: int, end: int, needle: str) -> bool:
    before, after = text[start - 1:start], text[end:end + 1]
    starts_digit = bool(re.match(rf"[{_DIGIT}]", needle[:1]))
    ends_digit = bool(re.match(rf"[{_DIGIT}]", needle[-1:]))
    return (starts_digit and bool(re.match(rf"[{_DIGIT},，.]", before))) or (
        ends_digit and bool(re.match(rf"[{_DIGIT}]", after))
    )


def _remove_first(text: str, needle: str) -> str:
    if needle and needle != _NONE and needle in text:
        i = text.index(needle)
        return text[:i] + text[i + len(needle):]
    return text


def _remove_price(text: str, price: str) -> str:
    """price の文字（最初の1か所）を除く。「／」でつないだ2つの価格は、つないだ形が無ければ別々に除く。"""
    if price in text:
        return _remove_first(text, price)
    for part in price.split("／"):
        text = _remove_first(text, part.strip())
    return text


def _remove_quantity(text: str, quantity: str, aliases: list[str]) -> str:
    """quantity の文字を、単位・×・@ のすぐ隣にある1か所だけ除く。続く単位の別名（1か所）も除く。"""
    if not quantity or quantity == _NONE:
        return text
    spans = [m.span() for m in re.finditer(re.escape(quantity), text)]
    spans = [(s, e) for s, e in spans if not _is_inside_digit_run(text, s, e, quantity)]
    best = max(spans, key=lambda se: (_quantity_neighbor_strength(text, *se, aliases), -se[0]), default=None)
    if best is None or _quantity_neighbor_strength(text, *best, aliases) == 0:
        return text
    start, end = best
    alias = _starts_with_alias(text, end, aliases)
    return text[:start] + text[end + (len(alias) if alias else 0):]


def _remove_stock_words(text: str, aliases: list[str]) -> str:
    """「残り」「在庫」「在庫数」と、そのすぐ後ろの数字・単位を除く。"""
    out, pos = [], 0
    for m in _STOCK_WORD_RE.finditer(text):
        out.append(text[pos:m.start()])
        end = m.end()
        alias = _starts_with_alias(text, end, aliases)
        pos = end + (len(alias) if alias else 0)
    out.append(text[pos:])
    return "".join(out)


def _strip_price_line_name(text: str, owner: dict, aliases: list[str]) -> str:
    """価格の行から、価格・数量・単位・記号などを除いた商品名の部分（設計 §3-3 商品名）。"""
    text = _remove_price(text, owner["price"])
    text = _remove_quantity(text, owner["quantity"], aliases)
    text = _remove_stock_words(text, aliases)
    text = _SYMBOLS_RE.sub("", text)
    text = _TIMES_NEXT_TO_DIGIT_RE.sub("", text)
    return text.strip(_EDGE_CHARS)


def _product_name(item: dict, lines: list[str], owner_by_price_line: dict[int, dict], aliases: list[str]) -> str:
    parts: list[str] = []
    for no in item["name_lines"]:
        text = lines[no - 1]
        owner = owner_by_price_line.get(no)
        text = _strip_price_line_name(text, owner, aliases) if owner is not None else text.strip(_EDGE_CHARS)
        if text:
            parts.append(text)
    return " ".join(parts)


def _find_unit(item_lines_text: list[str], aliases: list[str]) -> str | None:
    """件の行から、数字の直後、または直後に価格が続く位置にある単位の別名（最も前のもの、同じ位置なら長いもの）。"""
    for text in item_lines_text:
        lowered = text.lower()
        best: tuple[int, str] | None = None
        for alias in aliases:
            a = alias.lower()
            for m in re.finditer(re.escape(a), lowered):
                if _unit_position_ok(lowered, m.start(), m.end(), a) and (best is None or m.start() < best[0]):
                    best = (m.start(), alias)
        if best is not None:
            return best[1]
    return None


def _unit_position_ok(lowered: str, start: int, end: int, alias: str) -> bool:
    if re.match(r"[a-z]", alias[:1]) and re.match(r"[a-z]", lowered[start - 1:start]):
        return False
    if re.search(rf"[{_DIGIT}]\s*$", lowered[:start]):
        return True
    return bool(re.match(_PRICE_FOLLOWS, lowered[end:]))


def _ship_text(line: str, price_line: int | None, line_no: int, price: str) -> str:
    """発送の語を含む行から、発送の文字を取る（設計 §3-3 発送）。"""
    for m in _BRACKET_RE.finditer(line):
        if _SHIP_WORD_RE.search(m.group(1)):
            outside = (line[:m.start()] + line[m.end():]).strip()
            if outside:
                return m.group(1).strip()
            break
    if line_no == price_line and price and price != _NONE and price in line:
        after = line[line.index(price) + len(price):].strip(_EDGE_CHARS)
        if after:
            return after
    return line.strip()


def _find_ship(item: dict, lines: list[str]) -> str:
    for name in ("item_lines", "heading_lines", "shared_lines"):
        for no in item[name]:
            if _SHIP_WORD_RE.search(lines[no - 1]):
                return _ship_text(lines[no - 1], item["price_line"], no, item["price"])
    return _NONE


def _block_text(item: dict, lines: list[str]) -> str:
    numbers = sorted(set(item["item_lines"]) | set(item["heading_lines"]) | set(item["shared_lines"]))
    return "\n".join(lines[n - 1] for n in numbers)


def _extract_one(
    item: dict, lines: list[str], owner_by_price_line: dict[int, dict], *, cond_entries: list[dict],
    cond_canonical_to_uuid: dict, unit_alias_to_info: dict, status_entries: list[dict], order: str | None,
    aliases: list[str],
) -> dict:
    own_text = [lines[n - 1] for n in item["item_lines"]]
    block = _block_text(item, lines)
    name = _product_name(item, lines, owner_by_price_line, aliases)

    unit_alias = _find_unit(own_text, aliases)
    unit_canonical, kubun, _resolved = resolve_unit_v2(unit_alias or "", unit_alias_to_info)
    condition, _cond_id, basis = resolve_condition_v2(
        block, "", kubun, cond_entries, cond_canonical_to_uuid, raw_memo=block
    )
    status, effect = resolve_status_v2(block, status_entries, raw_memo=block)
    pq = resolve_price_quantity(
        "\n".join(own_text), gemini_price=item["price"], gemini_quantity=item["quantity"],
        unit_aliases=set(unit_alias_to_info), order=order, gemini_product_name=name,
    )
    return {
        **{k: item[k] for k in ("price_line", *_LINE_LIST_FIELDS)},
        "raw_price": item["price"], "raw_quantity": item["quantity"],
        "name": name, "unit": unit_canonical or _NONE, "unit_kubun": kubun,
        "condition": condition or _NONE, "condition_basis": basis,
        "status": status, "status_effect": effect, "ship": _find_ship(item, lines),
        "price_normalized": pq.price, "quantity_normalized": pq.quantity, "price_reasons": list(pq.reasons),
    }


def extract_v10_items(
    items: list[dict], raw_text: str, *, cond_entries: list[dict], cond_canonical_to_uuid: dict,
    unit_alias_to_info: dict, status_entries: list[dict], order: str | None,
) -> list[dict]:
    """parse_v10_response が返した件ごとに、商品名・単位・状態・ステータス・発送・価格数量を原文の行から取る。

    純粋関数。マスタは引数で受ける（読み込みは呼び出し側で1回だけ）。items の順番のまま返す。
    """
    lines = raw_text.split("\n")
    owner_by_price_line = {it["price_line"]: it for it in items}
    aliases = _unit_aliases(unit_alias_to_info)
    return [
        _extract_one(
            item, lines, owner_by_price_line, cond_entries=cond_entries,
            cond_canonical_to_uuid=cond_canonical_to_uuid, unit_alias_to_info=unit_alias_to_info,
            status_entries=status_entries, order=order, aliases=aliases,
        )
        for item in items
    ]
