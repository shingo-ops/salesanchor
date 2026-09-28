"""Gemini＝書き写し／システム＝判定 の判定係。純粋関数のみ、DB にも LLM にもアクセスしない。

設計: docs/handoff/gemini-extract-role-split/design.md §4・§5
"""
from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
