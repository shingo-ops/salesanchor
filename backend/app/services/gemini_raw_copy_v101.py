"""Gemini 書き写し v10.1（比較試験用）。Gemini は商品ごとの行番号と価格・数量の文字だけを出す（ラベル無し）。

設計: docs/handoff/gemini-v101/design.md §3
行の役割（価格・名前・状態・発送）はシステムが原文とマスタで決める。v8〜v10 のファイルは変えない。
マスタ照合は既存の resolve_* をそのまま呼び、同じ処理を写さない。
このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services import gemini_raw_copy_v8 as v8
from app.services import gemini_raw_copy_v10 as v10
from app.services.extraction_judgement_svc import resolve_price_quantity
from app.services.tcg_analyzer_svc import resolve_condition_v2, resolve_status_v2, resolve_unit_v2
from app.services.tcg_empty_box_rules import EMPTY_CANONICAL, EMPTY_CODE

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_V101_PROMPT_NAME = "raw_copy_v101_a"
V101_PROMPT_NAME_RE = re.compile(r"^raw_copy_v101_[a-z0-9_]+$")  # パス区切りや「..」を通さない

_NONE = "none"
_FLAG_SINGLE = "FLAG_SINGLE"
_MIN_STATE_WORD_LEN = 2
_MAX_STATE_REMAINDER_LEN = 2
_DEFAULT_BASIS_RE = re.compile(r"R4:単位既定|R5:パック既定")
_BAD_CONDITIONS = frozenset({
    "Damaged case", "Damaged sealed box", "No shrink box", "Opened box", "Opened case", "Searched pack",
})
_GOOD_CONDITIONS = frozenset({"Sealed box", "Case", "Unsearched pack"})

ROLE_PRICE, ROLE_SHIP, ROLE_CONDITION, ROLE_STOCK, ROLE_NAME = "price", "ship", "condition", "stock", "name"
_SHIP_RE = re.compile(r"発送|出荷|入荷|発売|着")
_STOCK_START_RE = re.compile(r"^(?:残り|在庫|数量|単価)")
_SYMBOL_ONLY_RE = re.compile(r"[\W_]+")
_PRICE_SHAPE_RE = re.compile(r"[¥@]\s*¥?\d|\d[\d,]*\s*円")
_BARE_NUMBER_RE = re.compile(r"\d[\d,]{3,}")
_YEAR_RE = re.compile(r"(?:19|20)\d\d")
_DIGITS = "0-9"

_LINE_ARRAY = {"type": "array", "items": {"type": "integer"}}
V101_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"lines": _LINE_ARRAY, "price": {"type": "string"}, "quantity": {"type": "string"}},
                "required": ["lines", "price", "quantity"],
            },
        }
    },
    "required": ["items"],
}


def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def load_v101_prompt(name: str = DEFAULT_V101_PROMPT_NAME) -> str:
    """prompts/ の raw_copy_v101_<名前>.txt を読む。名前の形が違うときは ValueError。"""
    if not V101_PROMPT_NAME_RE.fullmatch(name):
        raise ValueError(f"v101 の指示書名は {V101_PROMPT_NAME_RE.pattern} の形だけ使えます: {name!r}")
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 受け取り（設計 §3-3）
# ---------------------------------------------------------------------------


def _shape_error(obj: object, max_line: int) -> str | None:
    if not isinstance(obj, dict):
        return "件がオブジェクトではない"
    for name in ("lines", "price", "quantity"):
        if name not in obj:
            return f"必須の欄がない: {name}"
    if not isinstance(obj["price"], str) or not isinstance(obj["quantity"], str):
        return "型が違う（文字列が必要）: price / quantity"
    if not isinstance(obj["lines"], list) or not all(v8._is_int(n) for n in obj["lines"]):
        return "型が違う（整数の配列が必要）: lines"
    if not obj["lines"]:
        return "lines が空"
    bad = next((n for n in obj["lines"] if not 1 <= n <= max_line), None)
    if bad is not None:
        return f"lines の行番号が範囲外: {bad}（1〜{max_line}）"
    return None


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", _nfkc(text))


def _first_line_containing(numbers: list[int], lines: list[str], needle: str) -> int | None:
    squashed = _squash(needle)
    if not squashed:
        return None
    return next((n for n in numbers if squashed in _squash(lines[n - 1])), None)


def _priced_line(numbers: list[int], lines: list[str], price: str) -> int | None:
    """price の文字を含む最初の行。「／」でつないだときは、つないだ形が無ければ最初の価格で探す。"""
    found = _first_line_containing(numbers, lines, price)
    if found is None and "／" in price:
        found = _first_line_containing(numbers, lines, price.split("／")[0])
    return found


def _unpriced_line(numbers: list[int], lines: list[str], quantity: str, status_entries: list[dict] | None) -> int:
    """価格が none の件：数量の文字か売り切れの言葉を含む最初の行。無ければ lines の最後の行。"""
    for n in numbers:
        text = lines[n - 1]
        has_quantity = quantity != _NONE and bool(_squash(quantity)) and _squash(quantity) in _squash(text)
        if has_quantity or _is_sold_out(text, status_entries):
            return n
    return numbers[-1]


def _is_sold_out(text: str, status_entries: list[dict] | None) -> bool:
    return bool(status_entries) and resolve_status_v2(text, status_entries)[1] == "excluded"


def _price_line(obj: dict, numbers: list[int], lines: list[str], status_entries: list[dict] | None) -> int | None:
    if obj["price"].strip().lower() != _NONE:
        return _priced_line(numbers, lines, obj["price"])
    return _unpriced_line(numbers, lines, obj["quantity"].strip(), status_entries)


def parse_v101_response(
    response_text: str, raw_text: str, *, status_entries: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """JSON を読み、件ごとに設計 §3-3 の検査をする。戻り値は (items, errors)。

    items のキーは lines（重複なし・昇順）, price, quantity, price_line。
    status_entries は価格が none の件の price_line（売り切れの言葉の行）を決めるのに使う（無ければ使わない）。
    """
    lines = raw_text.split("\n")
    objs, whole_errors = v8._load_items(response_text)
    if objs is None:
        return [], whole_errors

    items: list[dict] = []
    errors: list[dict] = []
    seen_price_lines: set[int] = set()
    for index, obj in enumerate(objs):
        reason = _shape_error(obj, len(lines))
        if reason is not None:
            errors.append({"index": index, "error": reason, "item": obj})
            continue
        numbers = sorted(set(obj["lines"]))
        price_line = _price_line(obj, numbers, lines, status_entries)
        if price_line is None:
            errors.append({"index": index, "error": "価格の行が見つからない", "item": obj})
            continue
        if price_line in seen_price_lines:
            errors.append({"index": index, "error": f"price_line {price_line} がほかの件と同じ", "item": obj})
            continue
        seen_price_lines.add(price_line)
        items.append({"lines": numbers, "price": obj["price"], "quantity": obj["quantity"], "price_line": price_line})
    return items, errors


# ---------------------------------------------------------------------------
# 材料（マスタから導く言葉）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class V101Context:
    cond_entries: list[dict]
    cond_canonical_to_uuid: dict
    unit_alias_to_info: dict
    status_entries: list[dict]
    order: str | None
    aliases: list[str]
    state_words: list[str]
    sold_out_words: list[str]


def _state_words(cond_entries: list[dict]) -> list[str]:
    """状態の行の判定に使う言葉（2文字以上・長いものから）。単品の言葉・空箱の言葉は使わない。"""
    words: set[str] = set()
    for e in cond_entries:
        if e.get("canonical") in (_FLAG_SINGLE, EMPTY_CANONICAL) or e.get("code") == EMPTY_CODE:
            continue
        if e.get("match_type", "KEYWORD") not in ("KEYWORD", "LITERAL"):
            continue
        for kw in (k.strip() for k in (e.get("search_kw") or "").split(",")):
            word = _nfkc(kw).lower()
            if len(word) >= _MIN_STATE_WORD_LEN and "空箱" not in word:
                words.add(word)
    return sorted(words, key=len, reverse=True)


def _sold_out_words(status_entries: list[dict]) -> list[str]:
    return [
        e["search_pattern"] for e in status_entries
        if e.get("effect") == "EXCLUDE" and e.get("match_type") == "LITERAL" and e.get("search_pattern")
    ]


def build_context(
    *, cond_entries: list[dict], cond_canonical_to_uuid: dict, unit_alias_to_info: dict,
    status_entries: list[dict], order: str | None,
) -> V101Context:
    return V101Context(
        cond_entries=cond_entries, cond_canonical_to_uuid=cond_canonical_to_uuid,
        unit_alias_to_info=unit_alias_to_info, status_entries=status_entries, order=order,
        aliases=v10._unit_aliases(unit_alias_to_info), state_words=_state_words(cond_entries),
        sold_out_words=_sold_out_words(status_entries),
    )


# ---------------------------------------------------------------------------
# 行の役割（設計 §3-4）
# ---------------------------------------------------------------------------


def _is_state_line(text: str, ctx: V101Context) -> bool:
    """状態の言葉を含み、その言葉・単位の別名・記号を除くと残りが2文字以下の行。"""
    rest = _nfkc(text).lower()
    found = False
    for word in ctx.state_words:
        if word in rest:
            found = True
            rest = rest.replace(word, "")
    if not found:
        return False
    for alias in sorted((_nfkc(a).lower() for a in ctx.aliases), key=len, reverse=True):
        rest = rest.replace(alias, "")
    return len(_SYMBOL_ONLY_RE.sub("", rest)) <= _MAX_STATE_REMAINDER_LEN


def _is_stock_line(text: str, ctx: V101Context) -> bool:
    stripped = _nfkc(text).strip().lower()
    if _STOCK_START_RE.match(stripped) or any(w and _nfkc(w).lower() == stripped for w in ctx.sold_out_words):
        return True
    unit_pattern = "|".join(re.escape(_nfkc(a).lower()) for a in ctx.aliases)
    return bool(unit_pattern) and bool(re.fullmatch(rf"[{_DIGITS},]+\s*(?:{unit_pattern})", stripped))


def line_role(text: str, ctx: V101Context, *, is_price_line: bool) -> str:
    """1行の役割。price → 在庫の言葉で始まる行（stock）→ ship → condition → stock → name の順に決める。"""
    if is_price_line:
        return ROLE_PRICE
    if _STOCK_START_RE.match(_nfkc(text).strip().lower()):
        return ROLE_STOCK
    if _SHIP_RE.search(_nfkc(text)):
        return ROLE_SHIP
    if _is_state_line(text, ctx):
        return ROLE_CONDITION
    if _is_stock_line(text, ctx):
        return ROLE_STOCK
    return ROLE_NAME


def assign_roles(items: list[dict], lines: list[str], ctx: V101Context) -> list[dict[int, str]]:
    """件ごとに、lines の各行の役割（行番号→役割）を返す。items と同じ順。"""
    return [
        {n: line_role(lines[n - 1], ctx, is_price_line=(n == item["price_line"])) for n in item["lines"]}
        for item in items
    ]


# ---------------------------------------------------------------------------
# 単位の位置（設計 §3-5 単位）
# ---------------------------------------------------------------------------


def _unit_position_ok(norm: str, start: int, end: int, alias_norm: str) -> bool:
    before, after = norm[:start], norm[end:]
    if re.match(r"[a-z]", alias_norm[:1]) and re.match(r"[a-z]", before[-1:]):
        return False
    if re.search(rf"[{_DIGITS}]\s*$", before):
        return True
    if re.match(rf"\s*[/@¥]\s*¥?[{_DIGITS}]", after):
        return True
    if re.match(rf"\s+[{_DIGITS}]", after) and (not before or re.match(r"[\s\W]", before[-1])):
        return True
    return bool(re.match(rf"[(][^)]*[)]\s*[@¥]\s*¥?[{_DIGITS}]", after))


def find_unit_alias(text: str, aliases: list[str]) -> str | None:
    """1行から単位の別名を探す。複数あれば行頭に近いもの、同じ位置なら長いもの。"""
    norm = _nfkc(text).lower()
    whole = _SYMBOL_ONLY_RE.sub("", norm)
    best: tuple[int, int, str] | None = None
    for alias in aliases:
        alias_norm = _nfkc(alias).lower()
        if whole == _SYMBOL_ONLY_RE.sub("", alias_norm) and whole:
            candidates = [(0, alias)]
        else:
            candidates = [
                (m.start(), alias) for m in re.finditer(re.escape(alias_norm), norm)
                if _unit_position_ok(norm, m.start(), m.end(), alias_norm)
            ]
        for start, name in candidates:
            key = (start, -len(alias_norm), name)
            if best is None or key < best:
                best = key
    return best[2] if best else None


# ---------------------------------------------------------------------------
# 件の材料（共有の行・その件だけの行・価格）
# ---------------------------------------------------------------------------


def _shared_line_numbers(items: list[dict]) -> set[int]:
    counts: dict[int, int] = {}
    for item in items:
        for n in item["lines"]:
            counts[n] = counts.get(n, 0) + 1
    return {n for n, c in counts.items() if c >= 2}


def _own_lines(item: dict, shared: set[int]) -> list[int]:
    """その件だけの行（価格の行は共有でも含める）。"""
    return [n for n in item["lines"] if n not in shared or n == item["price_line"]]


def _unit_of_line(text: str, ctx: V101Context) -> tuple[str | None, str]:
    alias = find_unit_alias(text, ctx.aliases)
    canonical, kubun, _resolved = resolve_unit_v2(alias or "", ctx.unit_alias_to_info)
    return canonical, kubun


def _price_of(text: str, item: dict, ctx: V101Context) -> int | float | None:
    return resolve_price_quantity(
        text, gemini_price=item["price"], gemini_quantity=item["quantity"],
        unit_aliases=set(ctx.unit_alias_to_info), order=ctx.order,
    ).price


# ---------------------------------------------------------------------------
# 迷う行の付け直し（設計 §3-4）
# ---------------------------------------------------------------------------


def _neighbors(lines: list[str]) -> tuple[dict[int, int | None], dict[int, int | None]]:
    """空でない行どうしの前・次（行番号→行番号）。"""
    filled = [n for n, t in enumerate(lines, 1) if t.strip()]
    prev = {n: (filled[i - 1] if i else None) for i, n in enumerate(filled)}
    nxt = {n: (filled[i + 1] if i + 1 < len(filled) else None) for i, n in enumerate(filled)}
    return prev, nxt


def _ambiguous_lines(items: list[dict], lines: list[str], ctx: V101Context) -> dict[int, str]:
    """迷う行（行番号→種類 ship / condition）。"""
    prev, nxt = _neighbors(lines)
    price_set = {it["price_line"] for it in items}
    used = {n for it in items for n in it["lines"]}
    found: dict[int, str] = {}
    for n in sorted(used):
        if n in price_set or prev.get(n) not in price_set or nxt.get(n) not in price_set:
            continue
        role = line_role(lines[n - 1], ctx, is_price_line=False)
        if role in (ROLE_SHIP, ROLE_CONDITION):
            found[n] = role
    return found


def _evidence(role: str, items: list[dict], lines: list[str], ambiguous: dict[int, str], ctx: V101Context) -> set[str]:
    """同じ種類の迷わない行の並び方の証拠（"above" = 次の価格の上に書く形、"below" = 前の価格の下に書く形）。"""
    prev, nxt = _neighbors(lines)
    price_set = {it["price_line"] for it in items}
    marks: set[str] = set()
    for n, text in enumerate(lines, 1):
        if n in ambiguous or n in price_set or not text.strip():
            continue
        if line_role(text, ctx, is_price_line=False) != role:
            continue
        before_is_price, after_is_price = prev.get(n) in price_set, nxt.get(n) in price_set
        if not before_is_price and after_is_price:
            marks.add("above")
        elif before_is_price and not after_is_price:
            marks.add("below")
    return marks


def _decide_by_price(
    line_no: int, upper: dict, lower: dict, lines: list[str], ctx: V101Context,
) -> tuple[dict, str] | None:
    """状態の行：上下の価格の行の単位が同じで価格が違うとき、状態の言葉で安い件・高い件を決める。"""
    up_unit, low_unit = (_unit_of_line(lines[it["price_line"] - 1], ctx)[0] for it in (upper, lower))
    up_price, low_price = (_price_of(lines[it["price_line"] - 1], it, ctx) for it in (upper, lower))
    if not up_unit or up_unit != low_unit or up_price is None or low_price is None or up_price == low_price:
        return None
    cheaper, pricier = (upper, lower) if up_price < low_price else (lower, upper)
    _canon, kubun = _unit_of_line(lines[upper["price_line"] - 1], ctx)
    text = lines[line_no - 1]
    canonical, _cid, basis = resolve_condition_v2(
        text, "", kubun, ctx.cond_entries, ctx.cond_canonical_to_uuid, raw_memo=text
    )
    if _DEFAULT_BASIS_RE.search(basis):
        return None
    if canonical in _BAD_CONDITIONS:
        return cheaper, "値段:状態の悪い言葉は安い件へ"
    if canonical in _GOOD_CONDITIONS:
        return pricier, "値段:状態の良い言葉は高い件へ"
    return None


def _decide_target(
    line_no: int, kind: str, upper: dict, lower: dict, marks: set[str], lines: list[str], ctx: V101Context,
) -> tuple[dict, str] | None:
    if marks == {"above"}:
        return lower, "並び方:同じ投稿の同じ種類の行は、価格の上に書く形"
    if marks == {"below"}:
        return upper, "並び方:同じ投稿の同じ種類の行は、価格の下に書く形"
    if kind == ROLE_CONDITION:
        return _decide_by_price(line_no, upper, lower, lines, ctx)
    return None


def reassign_ambiguous(
    items: list[dict], lines: list[str], ctx: V101Context,
) -> tuple[list[dict], dict[int, list[dict]], dict[int, list[dict]]]:
    """迷う行を決まりで付け直す。戻り値は (新しい items, 付け直しの記録, 要確認)。記録は items の添字ごと。

    items は変更しない（新しい辞書を返す）。決まらない行は Gemini の付け方のまま、要確認に入れる。
    """
    ambiguous = _ambiguous_lines(items, lines, ctx)
    prev, nxt = _neighbors(lines)
    by_price_line = {it["price_line"]: i for i, it in enumerate(items)}
    new_lines = [list(it["lines"]) for it in items]
    reassigned: dict[int, list[dict]] = {}
    review: dict[int, list[dict]] = {}
    for n, kind in sorted(ambiguous.items()):
        up_i, low_i = by_price_line[prev[n]], by_price_line[nxt[n]]
        marks = _evidence(kind, items, lines, ambiguous, ctx)
        decision = _decide_target(n, kind, items[up_i], items[low_i], marks, lines, ctx)
        holders = [i for i, ls in enumerate(new_lines) if n in ls]
        if decision is None:
            for i in holders:
                review.setdefault(i, []).append({"line": n, "kind": kind})
            continue
        target_i = by_price_line[decision[0]["price_line"]]
        if holders == [target_i]:
            continue
        record = {
            "line": n, "kind": kind, "reason": decision[1],
            "from_price_lines": [items[i]["price_line"] for i in holders], "to_price_line": items[target_i]["price_line"],
        }
        for i in holders:
            new_lines[i] = [x for x in new_lines[i] if x != n]
        new_lines[target_i] = sorted({*new_lines[target_i], n})
        for i in {*holders, target_i}:
            reassigned.setdefault(i, []).append(record)
    new_items = [{**it, "lines": new_lines[i]} for i, it in enumerate(items)]
    return new_items, reassigned, review


# ---------------------------------------------------------------------------
# 原文から取る（設計 §3-5）
# ---------------------------------------------------------------------------


_DROP_WORD_START_RE = re.compile(r"^(?:\d|数量|在庫|残り|単価)")


def _is_alias_word(word: str, ctx: V101Context) -> bool:
    norm = _nfkc(word).strip().lower()
    return any(norm == _nfkc(a).lower() for a in ctx.aliases)


def _is_dropped_word(word: str, ctx: V101Context) -> bool:
    """価格の行の残りの語のうち、必ず名前に足さない語（数量・在庫・完売の言葉・状態の語・発送の言葉を含む語）。"""
    norm = _nfkc(word).strip().lower()
    sold_out = {_nfkc(w).lower() for w in ctx.sold_out_words}
    return bool(
        _DROP_WORD_START_RE.match(norm) or norm in sold_out or _SHIP_RE.search(norm) or _is_state_line(word, ctx)
    )


def _price_line_name(text: str, owner: dict, ctx: V101Context, *, filtered: bool = True) -> str:
    """価格の行に残る商品名。価格・数量・単位の別名・在庫の言葉・完売の言葉・状態の言葉を含む括弧を除く。

    filtered のときは、残りを空白で語に分け、数量・在庫・単位だけ・完売の言葉・状態の語を除く。
    """
    def drop_state_bracket(m: re.Match) -> str:
        inner = _nfkc(m.group(1)).lower()
        return "" if any(w in inner for w in ctx.state_words) else m.group(0)

    text = v10._BRACKET_RE.sub(drop_state_bracket, text)
    for word in ctx.sold_out_words:
        text = text.replace(word, "")
    rest = v10._strip_price_line_name(text, owner, ctx.aliases)
    if not filtered:
        return rest
    words = [w for w in _ship_words_of(rest) if not _is_dropped_word(w, ctx)]
    if all(_is_alias_word(w, ctx) for w in words):  # 残りが単位の別名の語だけなら、それも除く
        return ""
    return " ".join(words)


def _is_heading_position(item: dict, roles: dict[int, str], line_no: int) -> bool:
    """price_line より前にあり、それより前にその件の名前の行が無い（見出しの位置にある）行。"""
    if line_no >= item["price_line"]:
        return False
    return not any(m < line_no and roles[m] == ROLE_NAME for m in item["lines"])


def _ship_words_of(line: str) -> list[str]:
    return [w for w in re.split(r"[\s　]+", line.strip()) if w]


def _name_parts(
    item: dict, roles: dict[int, str], lines: list[str], owners: dict[int, dict], ctx: V101Context,
) -> list[str]:
    parts: list[str] = []
    for n in item["lines"]:
        text, role = lines[n - 1], roles[n]
        owner = owners.get(n)
        if role == ROLE_PRICE or (role == ROLE_NAME and owner is not None):
            part = _price_line_name(text, owner or item, ctx)
        elif role == ROLE_NAME:
            part = text.strip(v10._EDGE_CHARS)
        elif role == ROLE_SHIP and _is_heading_position(item, roles, n):
            part = _split_ship(text, is_heading=True)[1].strip(v10._EDGE_CHARS)
        else:
            part = ""
        if part.strip():
            parts.append(part.strip())
    return parts


def _product_name(
    item: dict, roles: dict[int, str], lines: list[str], owners: dict[int, dict], ctx: V101Context,
) -> str:
    name = " ".join(_name_parts(item, roles, lines, owners, ctx))
    if name:
        return name
    unfiltered = _price_line_name(lines[item["price_line"] - 1], item, ctx, filtered=False)
    return unfiltered or lines[item["price_line"] - 1].strip()


def _is_alias_only_line(text: str, ctx: V101Context) -> bool:
    whole = _SYMBOL_ONLY_RE.sub("", _nfkc(text).lower())
    return bool(whole) and any(whole == _SYMBOL_ONLY_RE.sub("", _nfkc(a).lower()) for a in ctx.aliases)


def _find_unit(item: dict, roles: dict[int, str], shared: set[int], lines: list[str], ctx: V101Context) -> str | None:
    """price_line → 役割が在庫の行 → 行の全体が単位の別名だけの行、の順に探す。名前・状態・発送の行と共有の行は見ない。"""
    own = [n for n in _own_lines(item, shared) if n != item["price_line"]]
    order = [
        item["price_line"],
        *(n for n in own if roles[n] == ROLE_STOCK),
        *(n for n in own if roles[n] == ROLE_NAME and _is_alias_only_line(lines[n - 1], ctx)),
    ]
    for n in order:
        alias = find_unit_alias(lines[n - 1], ctx.aliases)
        if alias is not None:
            return alias
    return None


def _split_ship(line: str, *, is_heading: bool) -> tuple[str, str]:
    """発送の行から (発送の文字, 発送として取った部分を除いた残り) を返す。括弧は括弧ごと除く。"""
    for m in v10._BRACKET_RE.finditer(line):
        if v10._SHIP_WORD_RE.search(m.group(1)):
            rest = line[:m.start()] + line[m.end():]
            if rest.strip():
                return m.group(1).strip(), rest
            break
    if is_heading and len(_ship_words_of(line)) >= 2:
        for m in re.finditer(r"[^\s　]+", line):
            if v10._SHIP_WORD_RE.search(m.group()):
                start = m.start() + max(m.group().rfind(c) for c in "]）】)") + 1
                if start < m.end():
                    return line[start:m.end()], line[:start] + line[m.end():]
                return m.group(), line[:m.start()] + line[m.end():]
    return line.strip(), ""


def _ship_text(line: str, item: dict, is_price_line: bool, ctx: V101Context, *, is_heading: bool) -> str | None:
    if is_price_line:
        text, rest = _split_ship(line, is_heading=False)
        if rest:  # 発送の言葉を含む括弧があり、括弧の外にも文字がある
            return text
        return _ship_text_after_price(line, item, ctx) or _ship_text_before_price(line, item)
    return _split_ship(line, is_heading=is_heading)[0]


_SHIP_START_RE = re.compile(r"[0-9０-９]+\s*[/／]\s*[0-9０-９]+|[0-9０-９]+\s*月|発売|前日|当日|翌日|即日|入荷|発送|出荷")
_SHIP_END_RE = re.compile(r"数量|在庫|残り|単価|[@＠¥￥]|[0-9０-９]+\s*[@＠]")


def _ship_text_before_price(line: str, item: dict) -> str | None:
    """価格の行の、価格より前にある発送の文字（発送の言葉に関わる最初の位置から、数量・在庫・価格記号の手前まで）。"""
    price = item["price"]
    anchor = price if price in line else price.split("／")[0]
    head = line[:line.index(anchor)] if price and price.lower() != _NONE and anchor in line else line
    start = _SHIP_START_RE.search(head)
    if start is None:
        return None
    tail = head[start.start():]
    ends = [m.start() for m in _SHIP_END_RE.finditer(tail)]
    if item["quantity"] != _NONE and item["quantity"] in tail:
        ends.append(tail.index(item["quantity"]))
    text = tail[:min(ends)] if ends else tail
    text = text.strip(v10._EDGE_CHARS + "※")
    return text if text and v10._SHIP_WORD_RE.search(text) else None


def _ship_text_after_price(line: str, item: dict, ctx: V101Context) -> str | None:
    """価格の行の、価格より後ろの文字から、在庫・数量・数字＋単位・先頭の ※ を除いた発送の文字。"""
    price = item["price"]
    anchor = price if price in line else price.split("／")[0]
    if not price or price.lower() == _NONE or anchor not in line:
        return None
    after = v10._remove_stock_words(line[line.index(anchor) + len(anchor):], ctx.aliases)
    units = "|".join(re.escape(a) for a in ctx.aliases)
    if units:
        after = re.sub(rf"[{_DIGITS}０-９,，]+\s*(?:{units})", "", after, flags=re.IGNORECASE)
    after = after.replace(item["quantity"], "") if item["quantity"] != _NONE else after
    after = after.strip(v10._EDGE_CHARS + "※")
    return after if after and v10._SHIP_WORD_RE.search(after) else None


def _ship_for(item: dict, roles: dict[int, str], shared: set[int], lines: list[str], ctx: V101Context) -> str:
    def collect(numbers: list[int]) -> list[str]:
        texts = []
        for n in numbers:
            is_price = roles[n] == ROLE_PRICE
            if not v10._SHIP_WORD_RE.search(lines[n - 1]) or not (is_price or roles[n] == ROLE_SHIP):
                continue
            text = _ship_text(
                lines[n - 1], item, is_price, ctx, is_heading=_is_heading_position(item, roles, n)
            )
            if text:
                texts.append(text)
        return texts

    own = collect(_own_lines(item, shared))
    found = own or collect([n for n in item["lines"] if n in shared and n != item["price_line"]])
    return " / ".join(found) if found else _NONE


def _quantity_not_in_text(quantity: str, text: str) -> bool:
    """quantity の数字が、原文に独立した数として無いとき True（数字が無い quantity は False）。"""
    groups = re.findall(rf"[{_DIGITS}]+", _nfkc(quantity).replace(",", "")) if quantity != _NONE else []
    norm = _nfkc(text)
    return any(
        not re.search(rf"(?<![{_DIGITS}.])(?<![{_DIGITS}],){g}(?![{_DIGITS}])(?!,[{_DIGITS}])", norm) for g in groups
    )


def _extract_one(
    item: dict, roles: dict[int, str], lines: list[str], owners: dict[int, dict], shared: set[int],
    ctx: V101Context, *, reassigned: list[dict], review: list[dict],
) -> dict:
    block = "\n".join(lines[n - 1] for n in item["lines"])
    own_text = "\n".join(lines[n - 1] for n in _own_lines(item, shared))
    name = _product_name(item, roles, lines, owners, ctx)
    unit_canonical, kubun, _resolved = resolve_unit_v2(_find_unit(item, roles, shared, lines, ctx) or "", ctx.unit_alias_to_info)
    condition, _cond_id, basis = resolve_condition_v2(
        block, "", kubun, ctx.cond_entries, ctx.cond_canonical_to_uuid, raw_memo=block
    )
    status, effect = resolve_status_v2(block, ctx.status_entries, raw_memo=block)
    pq = resolve_price_quantity(
        own_text, gemini_price=item["price"], gemini_quantity=item["quantity"],
        unit_aliases=set(ctx.unit_alias_to_info), order=ctx.order, gemini_product_name=name,
    )
    return {
        "price_line": item["price_line"], "lines": list(item["lines"]), "roles": dict(roles),
        "raw_price": item["price"], "raw_quantity": item["quantity"],
        "name": name, "unit": unit_canonical or _NONE, "unit_kubun": kubun,
        "condition": condition or _NONE, "condition_basis": basis,
        "status": status, "status_effect": effect, "ship": _ship_for(item, roles, shared, lines, ctx),
        "price_normalized": pq.price, "quantity_normalized": pq.quantity, "price_reasons": list(pq.reasons),
        "quantity_not_in_text": _quantity_not_in_text(item["quantity"], block),
        "reassigned": reassigned, "review": review,
    }


def _is_price_shaped(text: str) -> bool:
    norm = _nfkc(text).strip()
    if _PRICE_SHAPE_RE.search(norm):
        return True
    return bool(_BARE_NUMBER_RE.fullmatch(norm)) and not _YEAR_RE.fullmatch(norm)


def _possible_missing_lines(items: list[dict], lines: list[str]) -> list[int]:
    """最初の件の最初の行から最後の件の最後の行までの間にある、price_line でない価格の形の行。"""
    if not items:
        return []
    first = min(n for it in items for n in it["lines"])
    last = max(n for it in items for n in it["lines"])
    price_set = {it["price_line"] for it in items}
    return [n for n in range(first, last + 1) if n not in price_set and _is_price_shaped(lines[n - 1])]


def extract_v101_items(
    items: list[dict], raw_text: str, *, cond_entries: list[dict], cond_canonical_to_uuid: dict,
    unit_alias_to_info: dict, status_entries: list[dict], order: str | None, reassign: bool,
) -> tuple[list[dict], dict]:
    """parse_v101_response が返した件ごとに、役割・商品名・単位・状態・ステータス・発送・価格数量を原文から取る。

    純粋関数。マスタは引数で受ける（読み込みは呼び出し側で1回だけ）。reassign で迷う行の付け直しを切り替える。
    戻り値は (件ごとの辞書, flags)。flags は possible_missing_item（行番号の一覧）。
    """
    ctx = build_context(
        cond_entries=cond_entries, cond_canonical_to_uuid=cond_canonical_to_uuid,
        unit_alias_to_info=unit_alias_to_info, status_entries=status_entries, order=order,
    )
    lines = raw_text.split("\n")
    adjusted, reassigned, review = reassign_ambiguous(items, lines, ctx) if reassign else (items, {}, {})
    roles = assign_roles(adjusted, lines, ctx)
    owners = {it["price_line"]: it for it in adjusted}
    shared = _shared_line_numbers(adjusted)
    extracted = [
        _extract_one(
            item, roles[i], lines, owners, shared, ctx,
            reassigned=reassigned.get(i, []), review=review.get(i, []),
        )
        for i, item in enumerate(adjusted)
    ]
    return extracted, {"possible_missing_item": _possible_missing_lines(adjusted, lines)}

