"""Gemini＝書き写し／システム＝判定 の判定係。純粋関数のみ、DB にも LLM にもアクセスしない。

設計: docs/handoff/gemini-extract-role-split/design.md §4・§5
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

# inventory_parser.py は scripts/check-condition-vocab.js の CODE_FILES に含まれ、
# 同ファイルを変更すると本PRと無関係な既存のレガシー語彙（shrink_yes等）の全文スキャンが
# 発火する。レガシー語彙移行は別テーマのため、公開名を追加する代わりに内部関数を直接importする。
from app.services.inventory_parser import _extract_offer_type_ship_timing as extract_offer_type_ship_timing

_KATAKANA_START = 0x30A1
_KATAKANA_END = 0x30F6
_KATAKANA_TO_HIRAGANA_OFFSET = 0x60


def normalize_for_match(text: str) -> str:
    """NFKC → 小文字化 → カタカナをひらがな化 → 空白除去 → 記号/句読点(P*/S*)除去。

    数字・英字は残す。
    """
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    converted = []
    for ch in normalized:
        cp = ord(ch)
        if _KATAKANA_START <= cp <= _KATAKANA_END:
            converted.append(chr(cp - _KATAKANA_TO_HIRAGANA_OFFSET))
        else:
            converted.append(ch)
    result = []
    for ch in converted:
        if ch.isspace():
            continue
        category = unicodedata.category(ch)
        if category[0] in ("P", "S"):
            continue
        result.append(ch)
    return "".join(result)


def block_text(raw_text: str, line_start: int, line_end: int) -> str:
    """行番号（1始まり・両端含む）で raw_text の一部を切り出す。範囲外は空文字。

    行番号の数え方は tcg_product_guards.work_heading_evidence
    (backend/app/services/tcg_product_guards.py:37-38: raw_text.split("\\n") を
    1始まり・両端含む [line_start, line_end] で検証) および
    tcg_analyzer_svc.resolve_work_evidence
    (backend/app/services/tcg_analyzer_svc.py:458-465: 同じく split("\\n") を
    1始まりで扱い lines[start - 1:end] で切り出す) と同じ方式に合わせている。
    """
    lines = raw_text.split("\n")
    if not (1 <= line_start <= line_end <= len(lines)):
        return ""
    return "\n".join(lines[line_start - 1:line_end])


@dataclass(frozen=True)
class ProductEntry:
    id: int
    product_code: str | None
    mark: str | None
    work_id: int | None
    search_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]


@dataclass(frozen=True)
class MatchResult:
    status: Literal["matched", "ambiguous", "unmatched"]
    product_id: int | None
    work_id: int | None
    candidates: tuple[int, ...]
    matched_keywords: Mapping[int, tuple[str, ...]]
    excluded_by: Mapping[int, tuple[str, ...]]
    basis: str
    reason: str


def _code_candidate_basis(product: ProductEntry, nb: str) -> str | None:
    """product_code または mark を正規化したもの（空でないもの）が nb に含まれれば 'RAWCODE'。"""
    for raw in (product.product_code, product.mark):
        if not raw:
            continue
        normalized = normalize_for_match(raw)
        if normalized and normalized in nb:
            return "RAWCODE"
    return None


def _keyword_matches(product: ProductEntry, nb: str) -> tuple[str, ...]:
    """search_keywords のうち、全トークンが nb に含まれるものを返す（当たった keyword 全部）。"""
    matched: list[str] = []
    for keyword in product.search_keywords:
        tokens = [normalize_for_match(word) for word in keyword.split(" ") if word]
        if tokens and all(token in nb for token in tokens):
            matched.append(keyword)
    return tuple(matched)


def _excluded_keywords(product: ProductEntry, nb: str) -> tuple[str, ...]:
    """exclude_keywords のうち、正規化したものが nb に含まれるものを返す。"""
    excluded: list[str] = []
    for keyword in product.exclude_keywords:
        normalized = normalize_for_match(keyword)
        if normalized and normalized in nb:
            excluded.append(keyword)
    return tuple(excluded)


def match_product(block: str, products: Sequence[ProductEntry]) -> MatchResult:
    nb = normalize_for_match(block)

    code_basis: dict[int, str] = {}
    matched_keywords: dict[int, tuple[str, ...]] = {}
    excluded_by: dict[int, tuple[str, ...]] = {}
    candidates: list[int] = []

    for product in products:
        basis = _code_candidate_basis(product, nb)
        keywords = _keyword_matches(product, nb)
        if basis is None and not keywords:
            continue
        if basis is not None:
            code_basis[product.id] = basis
        if keywords:
            matched_keywords[product.id] = keywords

        excluded = _excluded_keywords(product, nb)
        if excluded:
            excluded_by[product.id] = excluded
            continue

        candidates.append(product.id)

    if len(candidates) == 0:
        return MatchResult(
            status="unmatched",
            product_id=None,
            work_id=None,
            candidates=(),
            matched_keywords=matched_keywords,
            excluded_by=excluded_by,
            basis="",
            reason="一致する検索ワード・品番がない",
        )

    if len(candidates) >= 2:
        return MatchResult(
            status="ambiguous",
            product_id=None,
            work_id=None,
            candidates=tuple(candidates),
            matched_keywords=matched_keywords,
            excluded_by=excluded_by,
            basis="",
            reason=f"候補{len(candidates)}件：{'/'.join(str(c) for c in candidates)}",
        )

    product_id = candidates[0]
    product = next(p for p in products if p.id == product_id)
    if product_id in code_basis:
        basis = code_basis[product_id]
    else:
        basis = f"SK:{matched_keywords[product_id][0]}"

    return MatchResult(
        status="matched",
        product_id=product_id,
        work_id=product.work_id,
        candidates=(product_id,),
        matched_keywords=matched_keywords,
        excluded_by=excluded_by,
        basis=basis,
        reason="",
    )


def verify_copied(value: str, block: str) -> bool:
    if value is None or value.strip() == "" or value.strip().lower() == "none":
        return True

    nb_value = normalize_for_match(value)
    nb_block = normalize_for_match(block)
    if nb_value and nb_value in nb_block:
        return True

    value_digits = "".join(ch for ch in unicodedata.normalize("NFKC", value) if ch.isdigit())
    block_digits = "".join(ch for ch in unicodedata.normalize("NFKC", block) if ch.isdigit())
    if value_digits and value_digits in block_digits:
        return True

    return False


def ship_timing(block: str) -> tuple[str | None, str | None]:
    for line in block.split("\n"):
        result = extract_offer_type_ship_timing(line)
        if result != (None, None):
            return result
    return None, None


# ---------------------------------------------------------------------------
# 価格・数量の決定（design: docs/handoff/gemini-extract-role-split/price-qty-resolver-design.md §4-§5）
# ---------------------------------------------------------------------------

# 目印の語（この定数だけが正。単位の語は unit_aliases 引数で受け取りコードに書かない）。
_PRICE_SUFFIX_MARKERS = ("万円", "円", "万")
_PRICE_PREFIX_SYMBOLS = ("¥", "￥", "Y")
_PRICE_LABEL_MARKERS = ("単価", "価格")
_AT_MARKERS = ("@", "＠")
_QTY_LABEL_MARKERS = ("在庫数", "在庫", "残り", "残", "数量")

_MAN_MARKER = "万"
_MAN_MULTIPLIER = 10000
_LABEL_TAIL = r"(?:[（(][^）)]*[）)])?[：:\s]*$"
_NUMBER_RE = re.compile(r"\d+(?:[,，]\d+)*(?:\.\d+)?")
_VALID_COMMA_RE = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$|^\d+(?:\.\d+)?$")
_SEPARATOR_RE = re.compile(r"^\s*[@xX×]\s*$")
_HEAD_SEPARATOR_RE = re.compile(r"^\s*[xX×]\s*\d")
_SHAPE_MIN_PRICE_DIGITS = 4
_NO_VALUE_TEXTS = ("", "none")

_PRICE_LABEL_RE = re.compile("(?:" + "|".join(map(re.escape, _PRICE_LABEL_MARKERS)) + ")" + _LABEL_TAIL)
_QTY_LABEL_RE = re.compile("(?:" + "|".join(map(re.escape, _QTY_LABEL_MARKERS)) + ")" + _LABEL_TAIL)


def _nfkc(text: str | None) -> str:
    return unicodedata.normalize("NFKC", text or "")


_PRICE_SUFFIXES = tuple(_nfkc(s) for s in _PRICE_SUFFIX_MARKERS)
_PRICE_SYMBOLS = tuple(_nfkc(s) for s in _PRICE_PREFIX_SYMBOLS if s != "Y")
_AT_SIGNS = tuple(_nfkc(s) for s in _AT_MARKERS)


@dataclass(frozen=True)
class PriceQtyResult:
    price: float | None
    quantity: float | None
    basis: Literal["marker", "rule", "none"]
    reasons: tuple[str, ...]
    price_line: int | None
    quantity_line: int | None

    @property
    def needs_review(self) -> bool:
        return bool(self.reasons)


def order_from_pattern(order_pattern: str | None) -> Literal["price_first", "quantity_first"] | None:
    """extraction_order_pattern（JSON配列）から向きを読む。旧い略語・不正値は None。"""
    if not isinstance(order_pattern, str) or not order_pattern.strip():
        return None
    try:
        tokens = json.loads(order_pattern)
    except (ValueError, TypeError):
        return None
    if not isinstance(tokens, list) or "price" not in tokens or "quantity" not in tokens:
        return None
    return "price_first" if tokens.index("price") < tokens.index("quantity") else "quantity_first"


@dataclass(frozen=True)
class _Num:
    value: float
    digits: str  # 万を掛ける前の数字だけ
    start: int
    end: int
    line_no: int  # 1始まり（ブロック内）
    irregular: bool
    price_marked: bool
    qty_marked: bool
    has_comma: bool


def _only_digits(text: str | None) -> str:
    if text is None or text.strip().lower() in _NO_VALUE_TEXTS:
        return ""
    return "".join(ch for ch in _nfkc(text) if ch.isdigit())


def _digit_groups(text: str | None) -> tuple[str, ...]:
    """Gemini の書き写しに含まれる数値ごとの数字列（複数値なら複数）。"""
    if text is None or text.strip().lower() in _NO_VALUE_TEXTS:
        return ()
    return tuple(_only_digits(m.group(0)) for m in _NUMBER_RE.finditer(_nfkc(text)))


def _unit_after(after: str, aliases: Sequence[str]) -> bool:
    """直後（空白は許容）が単位の別名で、その直後が英字でないか。"""
    rest = after.lstrip(" \t").lower()
    for alias in aliases:
        if rest.startswith(alias) and not re.match(r"[A-Za-z]", rest[len(alias):len(alias) + 1]):
            return True
    return False


def _extract_line_numbers(line: str, line_no: int, aliases: Sequence[str]) -> list[_Num]:
    """1行から値を取り出す。品番の一部（OP-17・PSA10・30th）は取り出さない。"""
    nums: list[_Num] = []
    for m in _NUMBER_RE.finditer(line):
        before, after = line[: m.start()], line[m.end():]
        raw = m.group(0).replace("，", ",")
        head_y = bool(re.search(r"(?<![A-Za-z])Y\s*$", before))
        digit_x_before = bool(re.search(r"\d[xX]$", before))  # 数字に挟まれた x/X は区切り
        if not head_y and not digit_x_before and (re.search(r"[A-Za-z]$", before) or before.endswith("-")):
            continue
        is_unit = _unit_after(after, aliases)
        if (
            re.match(r"[A-Za-z]", after[:1])
            and not is_unit
            and not _HEAD_SEPARATOR_RE.match(after)
        ):
            continue
        has_man = after.startswith(_MAN_MARKER)
        value = float(raw.replace(",", ""))
        if is_unit and value == 1 and re.search(r"/\s*$", before):
            continue  # 「/1BOX」は単位あたりの価格の表記で、数量ではない
        if has_man:
            value *= _MAN_MULTIPLIER
        price_marked = (
            has_man
            or any(after.startswith(s) for s in _PRICE_SUFFIXES)
            or any(before.rstrip(" \t").endswith(s) for s in _PRICE_SYMBOLS)
            or head_y
            or bool(_PRICE_LABEL_RE.search(before))
        )
        qty_marked = is_unit or bool(_QTY_LABEL_RE.search(before))
        nums.append(
            _Num(
                value=value,
                digits=_only_digits(raw),
                start=m.start(),
                end=m.end(),
                line_no=line_no,
                irregular="," in raw and not _VALID_COMMA_RE.match(raw),
                price_marked=price_marked and not qty_marked,
                qty_marked=qty_marked,
                has_comma="," in raw,
            )
        )
    return nums


def _apply_at_marker(line: str, nums: list[_Num]) -> list[_Num]:
    """直前が @ で、同じ行に数量の目印が付いた別の数値があれば、その数値を価格とする。"""
    if not any(n.qty_marked for n in nums):
        return nums
    return [
        replace(n, price_marked=True)
        if not n.price_marked
        and not n.qty_marked
        and any(line[: n.start].rstrip(" \t").endswith(a) for a in _AT_SIGNS)
        else n
        for n in nums
    ]


def _mask_product_name(lines: list[tuple[int, str]], product_name: str | None) -> list[tuple[int, str]]:
    """商品名の文字列を空白に置き換え、商品名だけの行は対象から外す（商品名中の数を値にしない）。"""
    name = _nfkc(product_name).strip()
    if not name or name.lower() in _NO_VALUE_TEXTS:
        return lines
    name_compact = "".join(name.split())
    masked: list[tuple[int, str]] = []
    for no, text in lines:
        compact = "".join(text.split())
        if compact and compact in name_compact:
            continue
        masked.append((no, text.replace(name, " " * len(name))))
    return masked


def _unique(nums: list[_Num]) -> list[_Num]:
    seen: dict[float, _Num] = {}
    for n in nums:
        seen.setdefault(n.value, n)
    return list(seen.values())


def _copied_by_gemini(num: _Num, gemini_groups: tuple[str, ...]) -> bool:
    """Gemini がその側の値を書き写していて、数字列が一致するか（補完の条件）。"""
    return bool(gemini_groups) and _digits_agree(gemini_groups, num)


def _marker_candidates(
    per_line: list[list[_Num]], g_price: tuple[str, ...], g_qty: tuple[str, ...]
) -> tuple[list[_Num], list[_Num]]:
    prices = [n for nums in per_line for n in nums if n.price_marked]
    qtys = [n for nums in per_line for n in nums if n.qty_marked]
    for nums in per_line:
        unmarked = [n for n in nums if not n.price_marked and not n.qty_marked]
        has_p = any(n.price_marked for n in nums)
        has_q = any(n.qty_marked for n in nums)
        if len(unmarked) == 1 and has_p != has_q:
            filled_side, groups = (qtys, g_qty) if has_p else (prices, g_price)
            if _copied_by_gemini(unmarked[0], groups):
                filled_side.append(unmarked[0])
    return prices, qtys


def _rule_pairs(lines: list[tuple[int, str]], per_line: list[list[_Num]]) -> list[tuple[_Num, _Num]]:
    """目印のない 数値[@×x]数値 の並び。"""
    pairs: list[tuple[_Num, _Num]] = []
    for (_no, text), nums in zip(lines, per_line):
        plain = [n for n in nums if not n.price_marked and not n.qty_marked]
        for left, right in zip(plain, plain[1:]):
            if _SEPARATOR_RE.match(text[left.end:right.start]):
                pairs.append((left, right))
    return pairs


def _shape_conflict(price: _Num, qty: _Num) -> bool:
    """「4桁以上が価格」「カンマ付きが価格」のどちらかが、決めた向きと逆か。"""
    big_p, big_q = len(price.digits) >= _SHAPE_MIN_PRICE_DIGITS, len(qty.digits) >= _SHAPE_MIN_PRICE_DIGITS
    if big_p != big_q and big_q:
        return True
    return price.has_comma != qty.has_comma and qty.has_comma


def _digits_agree(gemini_groups: tuple[str, ...], chosen: _Num) -> bool:
    accepted = {chosen.digits}
    if chosen.value.is_integer():
        accepted.add(str(int(chosen.value)))
    return any(g in accepted for g in gemini_groups)


def resolve_price_quantity(
    block: str,
    *,
    gemini_price: str | None,
    gemini_quantity: str | None,
    unit_aliases: Iterable[str],
    order: Literal["price_first", "quantity_first"] | None,
    gemini_product_name: str | None = None,
) -> PriceQtyResult:
    """価格と数量をシステムが決め、Gemini の書き写しと検算する（純粋関数）。

    line 番号（price_line / quantity_line）はブロック内の1始まり。
    """
    g_price, g_qty = _digit_groups(gemini_price), _digit_groups(gemini_quantity)
    if not g_price and not g_qty:
        return PriceQtyResult(None, None, "none", (), None, None)

    aliases = sorted({_nfkc(a).lower() for a in unit_aliases if a and _nfkc(a).strip()}, key=len, reverse=True)
    lines = _mask_product_name(
        [(i + 1, _nfkc(t)) for i, t in enumerate(block.split("\n"))], gemini_product_name
    )
    target = [
        (no, t) for no, t in lines
        if any(g in _only_digits(t) for g in (*g_price, *g_qty))
    ]
    per_line = [_apply_at_marker(t, _extract_line_numbers(t, no, aliases)) for no, t in target]

    reasons: list[str] = []
    prices, qtys = _marker_candidates(per_line, g_price, g_qty)
    prices, qtys = _unique(prices), _unique(qtys)
    price: _Num | None = None
    qty: _Num | None = None
    basis: Literal["marker", "rule", "none"] = "none"

    if prices or qtys:
        basis = "marker"
        if len(prices) > 1 or len(qtys) > 1:
            reasons.append("multiple_values")
        price = prices[0] if len(prices) == 1 else None
        qty = qtys[0] if len(qtys) == 1 else None
    else:
        pairs = _rule_pairs(target, per_line)
        unique_pairs = {(a.value, b.value): (a, b) for a, b in pairs}
        if len(unique_pairs) > 1:
            reasons.append("multiple_values")
        elif len(unique_pairs) == 1 and order is None:
            reasons.append("no_order_rule")
        elif len(unique_pairs) == 1:
            left, right = next(iter(unique_pairs.values()))
            price, qty = (left, right) if order == "price_first" else (right, left)
            basis = "rule"
            if _shape_conflict(price, qty):
                reasons.append("rule_vs_shape")

    reasons.extend(_verify_reasons(price, qty, g_price, g_qty, reasons))
    return PriceQtyResult(
        price=price.value if price else None,
        quantity=qty.value if qty else None,
        basis=basis if (price or qty) else "none",
        reasons=tuple(dict.fromkeys(reasons)),
        price_line=price.line_no if price else None,
        quantity_line=qty.line_no if qty else None,
    )


def _verify_reasons(
    price: _Num | None, qty: _Num | None, g_price: tuple[str, ...], g_qty: tuple[str, ...], existing: list[str]
) -> list[str]:
    """検算: 桁区切り不正・Gemini との不一致・決められない。"""
    out: list[str] = []
    if any(n and n.irregular for n in (price, qty)):
        out.append("irregular_comma")
    price_differs = price is not None and (not g_price or not _digits_agree(g_price, price))
    qty_differs = qty is not None and (not g_qty or not _digits_agree(g_qty, qty))
    if price_differs or qty_differs:
        out.append("gemini_disagrees")
    explained = "multiple_values" in existing or "no_order_rule" in existing
    if not explained and ((g_price and price is None) or (g_qty and qty is None)):
        out.append("unresolved")
    return out
