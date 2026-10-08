"""Gemini 書き写し v10.1（比較試験用）。Gemini は商品ごとの行番号と価格・数量の文字だけを出す（ラベル無し）。

設計: docs/handoff/gemini-v101/design.md §3
      docs/handoff/gemini-v102/design.md §3-1（v10.2: extract_v101_items の v102_fixes。F1〜F6）
行の役割（価格・名前・状態・発送）はシステムが原文とマスタで決める。v8〜v10 のファイルは変えない。
マスタ照合は既存の resolve_* をそのまま呼び、同じ処理を写さない。
このモジュールは比較試験の道具（app/tools/prompt_ab.py）専用で、本番の経路からは呼ばれない。
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services import gemini_raw_copy_v8 as v8
from app.services import gemini_raw_copy_v10 as v10
from app.services.extraction_judgement_svc import resolve_price_quantity
from app.services.gemini_raw_copy_v102_context_work import (
    MATCH_STATUS_MATCHED,
    MATCH_STATUS_MATCHED_CONTEXT,
    decide_by_context,
)
from app.services.gemini_raw_copy_v102_product_first import (
    PRODUCT_KUBUN_UNKNOWN,
    REVIEW_PRODUCT_MULTIPLE,
    ProductFirstMasters,
    resolve_product_first,
)
from app.services.tcg_analyzer_svc import resolve_condition_v2, resolve_status_v2, resolve_unit_v2
from app.services.tcg_empty_box_rules import EMPTY_CANONICAL, EMPTY_CODE

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_V101_PROMPT_NAME = "raw_copy_v101_a"
DEFAULT_V102_PROMPT_NAME = "raw_copy_v101_e"  # v10.2 の既定（PO 採用確定 2026-10-07）
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
ROLE_IGNORED = "ignored"  # v10.2 の F3・F5 が名前にも発送にも使わないと決めた行
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


def _priced_line(numbers: list[int], lines: list[str], price: str, *, half_width_slash: bool = False) -> int | None:
    """price の文字を含む最初の行。「／」でつないだときは、つないだ形が無ければ最初の価格で探す。

    half_width_slash（試作版 v102 の keep_rejected のとき）は、半角「/」でつないだときも同じに探す。
    """
    found = _first_line_containing(numbers, lines, price)
    separators = "／/" if half_width_slash else "／"
    if found is None and any(sep in price for sep in separators):
        found = _first_line_containing(numbers, lines, re.split(f"[{separators}]", price)[0])
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


def _price_line(
    obj: dict, numbers: list[int], lines: list[str], status_entries: list[dict] | None, *, half_width_slash: bool = False,
) -> int | None:
    if obj["price"].strip().lower() != _NONE:
        return _priced_line(numbers, lines, obj["price"], half_width_slash=half_width_slash)
    return _unpriced_line(numbers, lines, obj["quantity"].strip(), status_entries)


REJECTED_SHAPE, REJECTED_PRICE, REJECTED_DUPLICATE = "item_shape_invalid", "price_not_in_lines", "duplicate_price_line"


def _rejected_entry(kind: str, index: int, obj: object, error: str, max_line: int, price_line: int | None = None) -> dict:
    """落とした件の記録（keep_rejected のとき）。lines は範囲内の整数だけ・重複なし・昇順。"""
    raw_lines = obj.get("lines") if isinstance(obj, dict) else None
    numbers = (
        sorted({n for n in raw_lines if v8._is_int(n) and 1 <= n <= max_line}) if isinstance(raw_lines, list) else []
    )
    price = obj.get("price") if isinstance(obj, dict) else None
    quantity = obj.get("quantity") if isinstance(obj, dict) else None
    return {
        "rejected": kind, "gemini_index": index, "lines": numbers,
        "price": price if isinstance(price, str) else None, "quantity": quantity if isinstance(quantity, str) else None,
        "price_line": price_line, "error": error,
    }


def parse_v101_response(
    response_text: str, raw_text: str, *, status_entries: list[dict] | None = None, keep_rejected: bool = False,
) -> tuple[list[dict], list[dict]]:
    """JSON を読み、件ごとに設計 §3-3 の検査をする。戻り値は (items, errors)。

    items のキーは lines（重複なし・昇順）, price, quantity, price_line。
    status_entries は価格が none の件の price_line（売り切れの言葉の行）を決めるのに使う（無ければ使わない）。
    keep_rejected（試作版 v102）が True のときだけ、落とす件（形の違反・価格の行なし・価格の行が重複）を捨てずに、
    rejected・gemini_index などを付けて items の後ろに足し、半角「/」でつないだ価格も最初の価格で探す。
    False のときの出力は変えない。
    """
    lines = raw_text.split("\n")
    objs, whole_errors = v8._load_items(response_text)
    if objs is None:
        return [], whole_errors

    items: list[dict] = []
    rejected: list[dict] = []
    errors: list[dict] = []
    seen_price_lines: set[int] = set()
    for index, obj in enumerate(objs):
        reason = _shape_error(obj, len(lines))
        if reason is not None:
            errors.append({"index": index, "error": reason, "item": obj})
            rejected.append(_rejected_entry(REJECTED_SHAPE, index, obj, reason, len(lines)))
            continue
        numbers = sorted(set(obj["lines"]))
        price_line = _price_line(obj, numbers, lines, status_entries, half_width_slash=keep_rejected)
        if price_line is None:
            errors.append({"index": index, "error": "価格の行が見つからない", "item": obj})
            rejected.append(_rejected_entry(REJECTED_PRICE, index, obj, "価格の行が見つからない", len(lines)))
            continue
        if price_line in seen_price_lines:
            message = f"price_line {price_line} がほかの件と同じ"
            errors.append({"index": index, "error": message, "item": obj})
            rejected.append(_rejected_entry(REJECTED_DUPLICATE, index, obj, message, len(lines), price_line))
            continue
        seen_price_lines.add(price_line)
        items.append({"lines": numbers, "price": obj["price"], "quantity": obj["quantity"], "price_line": price_line})
    return ([*items, *rejected] if keep_rejected else items), errors


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
    product_first: ProductFirstMasters | None = None  # 試作版 v102 の商品先行の流れ。None なら v10.1・v10.2 のまま


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
    status_entries: list[dict], order: str | None, product_first: ProductFirstMasters | None = None,
) -> V101Context:
    return V101Context(
        cond_entries=cond_entries, cond_canonical_to_uuid=cond_canonical_to_uuid,
        unit_alias_to_info=unit_alias_to_info, status_entries=status_entries, order=order,
        aliases=v10._unit_aliases(unit_alias_to_info), state_words=_state_words(cond_entries),
        sold_out_words=_sold_out_words(status_entries), product_first=product_first,
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


_DROP_WORD_START_RE = re.compile(r"^(?:数量|在庫|残り|単価)")


def _is_alias_word(word: str, ctx: V101Context) -> bool:
    norm = _nfkc(word).strip().lower()
    return any(norm == _nfkc(a).lower() for a in ctx.aliases)


def _digit_groups(text: str) -> set[str]:
    return set(re.findall(r"\d+", _nfkc(text).replace(",", "")))


def _is_quantity_word(norm: str, owner: dict, ctx: V101Context) -> bool:
    """「数字＋単位の別名」だけの語（先頭の / は許す）、または数字だけで owner の quantity・price の数字と同じ語。"""
    units = "|".join(re.escape(_nfkc(a).lower()) for a in ctx.aliases)
    if units and re.fullmatch(rf"/?[\d,]+(?:{units})", norm):
        return True
    return bool(re.fullmatch(r"[\d,]+", norm)) and norm.replace(",", "") in (
        _digit_groups(owner["quantity"]) | _digit_groups(owner["price"])
    )


def _is_dropped_word(word: str, owner: dict, ctx: V101Context) -> bool:
    """価格の行の残りの語のうち、必ず名前に足さない語（数量・在庫・完売の言葉・状態の語・発送の言葉を含む語）。"""
    norm = _nfkc(word).strip().lower()
    sold_out = {_nfkc(w).lower() for w in ctx.sold_out_words}
    return bool(
        not _SYMBOL_ONLY_RE.sub("", norm) or _DROP_WORD_START_RE.match(norm) or norm in sold_out or _SHIP_RE.search(norm)
        or _is_quantity_word(norm, owner, ctx) or _is_state_line(word, ctx)
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
    words = [w for w in _ship_words_of(rest) if not _is_dropped_word(w, owner, ctx)]
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
    unique = list({_squash(t): t for t in reversed(found)}.values())[::-1]  # 同じ文は1つにする（先に出たもの）
    return " / ".join(unique) if unique else _NONE


def _quantity_not_in_text(quantity: str, text: str, *, v102: bool = False) -> bool:
    """quantity の数字が、原文に独立した数として無いとき True（数字が無い quantity は False）。

    v102（設計 v10.2 F6）のときは、原文の数字の間のカンマも除いて比べる（「2,000」と「2000」は同じ数）。
    """
    groups = re.findall(rf"[{_DIGITS}]+", _nfkc(quantity).replace(",", "")) if quantity != _NONE else []
    norm = _nfkc(text)
    if v102:
        norm = re.sub(rf"(?<=[{_DIGITS}]),(?=[{_DIGITS}])", "", norm)
    return any(
        not re.search(rf"(?<![{_DIGITS}.])(?<![{_DIGITS}],){g}(?![{_DIGITS}])(?!,[{_DIGITS}])", norm) for g in groups
    )


def _product_first_fields(
    item: dict, roles: dict[int, str], lines: list[str], block: str, name: str, ctx: V101Context,
    chosen_product_id: int | None = None,
) -> dict | None:
    """試作版 v102：商品を先に決める流れの結果。マスタが渡されていないとき（v10.2 までの呼び出し）は None。"""
    if ctx.product_first is None:
        return None
    return resolve_product_first(
        item=item, roles=roles, lines=lines, block=block, name=name, aliases=ctx.aliases,
        unit_alias_to_info=ctx.unit_alias_to_info, cond_entries=ctx.cond_entries,
        cond_canonical_to_uuid=ctx.cond_canonical_to_uuid, masters=ctx.product_first,
        find_price_alias=lambda text: find_unit_alias(text, ctx.aliases), chosen_product_id=chosen_product_id,
    )


def _extract_one(
    item: dict, roles: dict[int, str], lines: list[str], owners: dict[int, dict], shared: set[int],
    ctx: V101Context, *, reassigned: list[dict], review: list[dict], v102: bool = False, name_prefix: str = "",
    name_roles: dict[int, str] | None = None, chosen_product_id: int | None = None,
) -> dict:
    """chosen_product_id（試作版 v102）：前後の商品の作品で決めた商品。ambiguous の候補にあるときだけ使う。
    name_roles（v10.2 F5）：名前の取り出しだけに使う役割。None なら roles と同じ。数量・単位・状態・発送・ステータス・価格（価格数量の判定に渡す名前を含む）は roles を使う。"""
    shown_roles = name_roles if name_roles is not None else roles
    block = "\n".join(lines[n - 1] for n in item["lines"])
    own_text = "\n".join(lines[n - 1] for n in _own_lines(item, shared))
    name = _product_name(item, shown_roles, lines, owners, ctx)
    calc_name = name if shown_roles is roles else _product_name(item, roles, lines, owners, ctx)
    if name_prefix:
        name = f"{name_prefix} {name}"
        calc_name = f"{name_prefix} {calc_name}"
    product_first = (
        _product_first_fields(item, roles, lines, block, calc_name, ctx, chosen_product_id) if v102 else None
    )
    if product_first is not None:
        unit_canonical, kubun, condition, basis = (
            product_first["unit"], product_first["unit_kubun"], product_first["condition"], product_first["condition_basis"]
        )
        review = [*review, *({"line": item["price_line"], **r} for r in product_first["review_extra"])]
    else:
        unit_canonical, kubun, _resolved = resolve_unit_v2(_find_unit(item, roles, shared, lines, ctx) or "", ctx.unit_alias_to_info)
        condition, _cond_id, basis = resolve_condition_v2(
            block, "", kubun, ctx.cond_entries, ctx.cond_canonical_to_uuid, raw_memo=block
        )
    status, effect = resolve_status_v2(block, ctx.status_entries, raw_memo=block)
    pq = resolve_price_quantity(
        own_text, gemini_price=item["price"], gemini_quantity=item["quantity"],
        unit_aliases=set(ctx.unit_alias_to_info), order=ctx.order, gemini_product_name=calc_name,
    )
    extra = (
        {k: product_first[k] for k in ("product_id", "product_category", "match_status", "match_candidates", "unit_basis")}
        if product_first is not None else {}
    )
    return {
        **extra,
        "price_line": item["price_line"], "lines": list(item["lines"]), "roles": dict(shown_roles),
        "raw_price": item["price"], "raw_quantity": item["quantity"],
        "name": name, "unit": unit_canonical or _NONE, "unit_kubun": kubun,
        "condition": condition or _NONE, "condition_basis": basis,
        "status": status, "status_effect": effect, "ship": _ship_for(item, roles, shared, lines, ctx),
        "price_normalized": pq.price, "quantity_normalized": pq.quantity, "price_reasons": list(pq.reasons),
        "quantity_not_in_text": _quantity_not_in_text(item["quantity"], block, v102=v102),
        "reassigned": reassigned, "review": review,
    }


def _is_price_shaped(text: str) -> bool:
    norm = _nfkc(text).strip()
    if _PRICE_SHAPE_RE.search(norm):
        return True
    return bool(_BARE_NUMBER_RE.fullmatch(norm)) and not _YEAR_RE.fullmatch(norm)


def _possible_missing_lines(items: list[dict], lines: list[str], *, until_last_price_line: bool = False) -> list[int]:
    """最初の件の最初の行から最後の件の最後の行までの間にある、price_line でない価格の形の行。

    until_last_price_line（v10.2 F5）のときは、終わりを最後の price_line にする（末尾の連絡の行を含めない）。
    """
    if not items:
        return []
    first = min(n for it in items for n in it["lines"])
    last = max(it["price_line"] for it in items) if until_last_price_line else max(n for it in items for n in it["lines"])
    price_set = {it["price_line"] for it in items}
    return [n for n in range(first, last + 1) if n not in price_set and _is_price_shaped(lines[n - 1])]


# ---------------------------------------------------------------------------
# v10.2 の確認と直し（設計 docs/handoff/gemini-v102/design.md §3-1。v102_fixes のときだけ）
# ---------------------------------------------------------------------------

_F1_SHIP_RE = re.compile(r"発送|出荷|入荷|発売")
_F1_MIN_NAME_LEN = 3
_WHOLE_BRACKET_RE = re.compile(r"^(?:【[^】]*】|━.*━)$")
_STOCK_WORD_START_RE = re.compile(r"^(?:数量|在庫|残り|単価|残[\d,])")
_WORD_SPLIT_RE = re.compile(r"[\s　/／]+")


def _fix(rule: str, line: int, detail: str) -> dict:
    return {"rule": rule, "line": line, "detail": detail}


def _is_own_name_line(item: dict, roles: dict[int, str], n: int, shared: set[int], lines: list[str], ctx: V101Context) -> bool:
    """F1 の「自分だけの名前の行」：共有でなく、空でなく、役割が名前で、記号を除いて3文字以上、単位の別名だけでなく、発送の言葉が無い。"""
    text = lines[n - 1]
    return bool(
        n not in shared and text.strip() and roles[n] == ROLE_NAME
        and len(_SYMBOL_ONLY_RE.sub("", _nfkc(text))) >= _F1_MIN_NAME_LEN
        and not _is_alias_only_line(text, ctx) and not _F1_SHIP_RE.search(_nfkc(text))
    )


def _apply_f1(
    items: list[dict], roles: list[dict[int, str]], lines: list[str], ctx: V101Context,
) -> tuple[list[dict], dict[int, list[dict]]]:
    """F1 親の見出しを外す。発送の言葉のある共有の行 X を、全部の件に自分だけの名前の行（X の後ろ・価格の行の前）があるとき外す。"""
    shared = _shared_line_numbers(items)
    price_set = {it["price_line"] for it in items}
    removed: dict[int, list[int]] = {}
    for x in sorted(shared - price_set):
        if not _F1_SHIP_RE.search(_nfkc(lines[x - 1])):
            continue
        holders = [i for i, it in enumerate(items) if x in it["lines"]]
        if all(
            any(x < m < items[i]["price_line"] and _is_own_name_line(items[i], roles[i], m, shared, lines, ctx)
                for m in items[i]["lines"])
            for i in holders
        ):
            removed[x] = holders
    new_items = [{**it, "lines": [n for n in it["lines"] if n not in removed]} for it in items]
    fixes: dict[int, list[dict]] = {}
    for x, holders in removed.items():
        for i in holders:
            fixes.setdefault(i, []).append(_fix("F1", x, "親の見出しを件の lines から外した"))
    return new_items, fixes


def _has_other_name_line(
    item: dict, roles: dict[int, str], x: int, shared: set[int], lines: list[str], ctx: V101Context,
) -> bool:
    """F3 の「ほかに名前の行がある」：x 以外に、F1 と同じ定義の「自分だけの名前の行」（_is_own_name_line）がある。"""
    return any(m != x and _is_own_name_line(item, roles, m, shared, lines, ctx) for m in item["lines"])


def _apply_f3(
    items: list[dict], roles: list[dict[int, str]], lines: list[str], ctx: V101Context,
) -> tuple[list[dict[int, str]], dict[int, list[dict]]]:
    """F3 まとめ書きの行（全体が【…】か━…━の、役割が名前の行）は、ほかに名前の行があれば名前に使わない。

    役割が発送の行（例：【9/28発送】）は対象にしない（共有の発送の行を残すため）。
    """
    new_roles: list[dict[int, str]] = []
    fixes: dict[int, list[dict]] = {}
    shared = _shared_line_numbers(items)
    for i, (item, role_map) in enumerate(zip(items, roles)):
        updated = dict(role_map)
        for n in item["lines"]:
            if role_map[n] == ROLE_NAME and _WHOLE_BRACKET_RE.match(lines[n - 1].strip()) and _has_other_name_line(
                item, role_map, n, shared, lines, ctx
            ):
                updated[n] = ROLE_IGNORED
                fixes.setdefault(i, []).append(_fix("F3", n, "まとめ書きの行を名前に使わない"))
        new_roles.append(updated)
    return new_roles, fixes


def _apply_f5(
    items: list[dict], roles: list[dict[int, str]],
) -> tuple[list[dict[int, str]], dict[int, list[dict]], list[int]]:
    """F5 最後の price_line より後ろの行で、役割が名前のものは名前に使わない。戻り値の最後は possible_footer_line。"""
    last_price_line = max(it["price_line"] for it in items)
    new_roles: list[dict[int, str]] = []
    fixes: dict[int, list[dict]] = {}
    footer: set[int] = set()
    for i, (item, role_map) in enumerate(zip(items, roles)):
        updated = dict(role_map)
        for n in item["lines"]:
            if n > last_price_line and role_map[n] == ROLE_NAME:
                updated[n] = ROLE_IGNORED
                footer.add(n)
                fixes.setdefault(i, []).append(_fix("F5", n, "最後の price_line より後ろの行を名前に使わない"))
        new_roles.append(updated)
    return new_roles, fixes, sorted(footer)


def _is_empty_name(name: str, ctx: V101Context) -> bool:
    """記号・単位の別名だけの語・「数字＋単位」の語・在庫の言葉を除くと空になる名前。"""
    units = "|".join(re.escape(_nfkc(a).lower()) for a in ctx.aliases)
    for word in _WORD_SPLIT_RE.split(name):
        norm = _nfkc(word).strip().lower()
        if not _SYMBOL_ONLY_RE.sub("", norm) or _STOCK_WORD_START_RE.match(norm) or _is_alias_word(norm, ctx):
            continue
        if units and re.fullmatch(rf"[\d,]+(?:{units})", norm):
            continue
        return False
    return True


def _f2_prefixes(
    items: list[dict], roles: list[dict[int, str]], lines: list[str], owners: dict[int, dict], shared: set[int],
    ctx: V101Context,
) -> dict[int, tuple[str, dict]]:
    """F2 名前の無い件（名前が空になる）の price_line のすぐ前の行が、名前の行を持たないほかの件の price_line なら、その件の名前を前に付ける。"""
    prev, _nxt = _neighbors(lines)
    by_price_line = {it["price_line"]: i for i, it in enumerate(items)}
    found: dict[int, tuple[str, dict]] = {}
    for i, item in enumerate(items):
        before = prev.get(item["price_line"])
        j = by_price_line.get(before) if before is not None else None
        if j is None or not _is_empty_name(_product_name(item, roles[i], lines, owners, ctx), ctx):
            continue
        other = items[j]
        if any(roles[j][n] == ROLE_NAME for n in other["lines"] if n != other["price_line"]):
            continue
        prefix = _price_line_name(lines[before - 1], other, ctx)
        if prefix:
            found[i] = (prefix, _fix("F2", item["price_line"], f"名前の前に行 {before} の名前「{prefix}」を付けた"))
    return found


def _has_no_digit(quantity: str) -> bool:
    return quantity.strip().lower() != _NONE and not re.search(rf"[{_DIGITS}]", _nfkc(quantity))


def _apply_context_work(extracted: list[dict], build: Callable[[int, int | None], dict], product_entries) -> list[dict]:
    """試作版 v102 の2回目：ambiguous を前後の商品の作品で決める。決めた件は決めた商品で作り直し、決まらない件は要確認に理由を足す。"""
    result = list(extracted)
    for i, decision in decide_by_context(extracted, product_entries).items():
        if not decision.is_decided:
            result[i] = {
                **extracted[i],
                "review": [
                    {**r, "context_reason": decision.reason} if r["kind"] == REVIEW_PRODUCT_MULTIPLE else r
                    for r in extracted[i]["review"]
                ],
            }
            continue
        result[i] = {
            **build(i, decision.product_id),
            "match_status": MATCH_STATUS_MATCHED_CONTEXT,
            "product_context": {
                "rule": decision.rule,
                "clues": [{"line": c.line, "product_id": c.product_id, "work_id": c.work_id} for c in decision.clues],
                "dropped": list(decision.dropped),
            },
        }
    return result


_REVIEW_QUANTITY_NO_NUMBER, _REVIEW_FOOTER = "quantity_no_number", "possible_footer_line"
_REVIEW_UNIT_UNKNOWN, _REVIEW_CATEGORY_UNKNOWN = "unit_unknown", "category_unknown"
_POST_NO_ITEMS, _POST_MISSING_ITEM = "no_items", "possible_missing_item"
_NORMAL_ROW_NONE_FIELDS = ("name", "unit", "unit_kubun", "condition", "condition_basis", "status", "status_effect", "ship")


def _rejected_row(rejected: dict, ctx: V101Context) -> dict:
    """落とした件を、通常の件と同じ欄名を持つ件にする（値は none・None・空。要確認の理由だけ持つ）。"""
    kind = rejected["rejected"]
    first_line = rejected["price_line"] or (rejected["lines"][0] if rejected["lines"] else None)
    detail: dict = {"error": rejected["error"]} if kind == REJECTED_SHAPE else {}
    if kind == REJECTED_PRICE:
        detail = {"field": "price", "copied": rejected["price"]}
    extra = (
        {"product_id": None, "product_category": _NONE, "match_status": _NONE, "match_candidates": [], "unit_basis": _NONE}
        if ctx.product_first is not None else {}
    )
    return {
        **extra,
        "price_line": rejected["price_line"], "lines": list(rejected["lines"]), "roles": {},
        "raw_price": rejected["price"], "raw_quantity": rejected["quantity"],
        **dict.fromkeys(_NORMAL_ROW_NONE_FIELDS, _NONE),
        "price_normalized": None, "quantity_normalized": None, "price_reasons": [], "quantity_not_in_text": None,
        "reassigned": [], "review": [{"line": first_line, "kind": kind, **detail}], "fixes": [],
        "rejected": kind, "gemini_index": rejected["gemini_index"],
    }


def _item_reasons(row: dict, no_number: list[int], footer: list[int]) -> list[dict]:
    """通常の件に足す要確認の理由（印の行を持つ件・単位なし・分類「不明」）。"""
    owned = {*row["lines"], row["price_line"]}
    reasons = [{"line": n, "kind": _REVIEW_QUANTITY_NO_NUMBER} for n in no_number if n in owned]
    reasons += [{"line": n, "kind": _REVIEW_FOOTER} for n in footer if n in owned]
    if row["unit"] == _NONE:
        reasons.append({"line": row["price_line"], "kind": _REVIEW_UNIT_UNKNOWN})
    if row.get("match_status") == MATCH_STATUS_MATCHED and row.get("product_category") == PRODUCT_KUBUN_UNKNOWN:
        reasons.append({"line": row["price_line"], "kind": _REVIEW_CATEGORY_UNKNOWN})
    return reasons


def _post_review_reasons(*, item_count: int, flags: dict, owned_lines: set[int]) -> list[dict]:
    """投稿ごとの要確認の理由：件が0・件の抜けの疑いの行・どの件にも属さない末尾の行。"""
    reasons: list[dict] = [] if item_count else [{"kind": _POST_NO_ITEMS}]
    reasons += [{"kind": _POST_MISSING_ITEM, "line": n} for n in flags["possible_missing_item"]]
    reasons += [{"kind": _REVIEW_FOOTER, "line": n} for n in flags["possible_footer_line"] if n not in owned_lines]
    return reasons


def _extract_v102(
    items: list[dict], lines: list[str], ctx: V101Context, reassigned: dict[int, list[dict]], review: dict[int, list[dict]],
    *, rejected: list[dict] | None = None, review_reasons: bool = False,
) -> tuple[list[dict], dict]:
    """extract_v101_items の v102_fixes 版。F1（lines）→ 役割の付け直し → F3 → F5 → F2（名前）→ 取り出し（F6）→ F4 の順に当てる。

    rejected（落とした件）は通常の処理に入れず、結果の最後に足す。review_reasons のときだけ、要確認の理由を足す。
    """
    rejected_rows = [_rejected_row(r, ctx) for r in rejected or []]
    if not items:
        empty: dict = {"possible_missing_item": [], "quantity_no_number": [], "possible_footer_line": []}
        if review_reasons:
            empty["post_review"] = _post_review_reasons(item_count=len(rejected_rows), flags=empty, owned_lines=set())
        return rejected_rows, empty
    items, f1_fixes = _apply_f1(items, assign_roles(items, lines, ctx), lines, ctx)
    roles = assign_roles(items, lines, ctx)
    roles, f3_fixes = _apply_f3(items, roles, lines, ctx)
    name_roles, f5_fixes, footer_lines = _apply_f5(items, roles)
    owners = {it["price_line"]: it for it in items}
    shared = _shared_line_numbers(items)
    f2 = _f2_prefixes(items, name_roles, lines, owners, shared, ctx)

    def build(i: int, chosen_product_id: int | None = None) -> dict:
        item = items[i]
        one = _extract_one(
            item, roles[i], lines, owners, shared, ctx, reassigned=reassigned.get(i, []), review=review.get(i, []),
            v102=True, name_prefix=f2[i][0] if i in f2 else "", name_roles=name_roles[i], chosen_product_id=chosen_product_id,
        )
        fixes = [*f1_fixes.get(i, []), *([f2[i][1]] if i in f2 else []), *f3_fixes.get(i, [])]
        if _has_no_digit(item["quantity"]):
            one = {**one, "quantity_normalized": None}
            fixes.append(_fix("F4", item["price_line"], "数量に数字が無いので quantity_normalized を None にした"))
        return {**one, "fixes": [*fixes, *f5_fixes.get(i, [])]}

    extracted = [build(i) for i in range(len(items))]
    no_number = [it["price_line"] for it in items if _has_no_digit(it["quantity"])]
    if ctx.product_first is not None:
        extracted = _apply_context_work(extracted, build, ctx.product_first.product_entries)
    flags = {
        "possible_missing_item": _possible_missing_lines(items, lines, until_last_price_line=True),
        "quantity_no_number": no_number, "possible_footer_line": footer_lines,
    }
    if review_reasons:
        extracted = [{**row, "review": [*row["review"], *_item_reasons(row, no_number, footer_lines)]} for row in extracted]
        owned = {n for row in [*extracted, *rejected_rows] for n in row["lines"]}
        flags = {**flags, "post_review": _post_review_reasons(
            item_count=len(extracted) + len(rejected_rows), flags=flags, owned_lines=owned)}
    return [*extracted, *rejected_rows], flags


def extract_v101_items(
    items: list[dict], raw_text: str, *, cond_entries: list[dict], cond_canonical_to_uuid: dict,
    unit_alias_to_info: dict, status_entries: list[dict], order: str | None, reassign: bool,
    v102_fixes: bool = False, product_first: ProductFirstMasters | None = None, review_reasons: bool = False,
) -> tuple[list[dict], dict]:
    """parse_v101_response が返した件ごとに、役割・商品名・単位・状態・ステータス・発送・価格数量を原文から取る。

    純粋関数。マスタは引数で受ける（読み込みは呼び出し側で1回だけ）。reassign で迷う行の付け直しを切り替える。
    戻り値は (件ごとの辞書, flags)。flags は possible_missing_item（行番号の一覧）。
    v102_fixes が True のときだけ、設計 v10.2 の F1〜F6 を当てる（件に fixes、flags に quantity_no_number・possible_footer_line）。
    False のときの出力は v10.1 のまま変えない。
    product_first（試作版 v102）は v102_fixes が True のときだけ使う。渡すと、商品を先に決めて単位・状態を出す流れになり、
    件に product_id・product_category・match_status・match_candidates・unit_basis が付く。None なら v10.2 のまま。
    review_reasons（v102_fixes のときだけ）：件の review に印・単位なし・分類「不明」の理由を足し、flags に post_review を足す。
    items に parse_v101_response(keep_rejected=True) の落とした件（rejected 付き）が入っていれば、結果の最後に足す。
    """
    ctx = build_context(
        cond_entries=cond_entries, cond_canonical_to_uuid=cond_canonical_to_uuid,
        unit_alias_to_info=unit_alias_to_info, status_entries=status_entries, order=order,
        product_first=product_first if v102_fixes else None,
    )
    lines = raw_text.split("\n")
    rejected = [it for it in items if "rejected" in it] if v102_fixes else []
    kept = [it for it in items if "rejected" not in it] if v102_fixes else items
    adjusted, reassigned, review = reassign_ambiguous(kept, lines, ctx) if reassign else (kept, {}, {})
    if v102_fixes:
        return _extract_v102(adjusted, lines, ctx, reassigned, review, rejected=rejected, review_reasons=review_reasons)
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

