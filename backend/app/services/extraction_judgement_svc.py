"""Gemini＝書き写し／システム＝判定 の判定係。純粋関数のみ、DB にも LLM にもアクセスしない。

設計: docs/handoff/gemini-extract-role-split/design.md §4・§5
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Literal

from app.services.offer_type_ship_timing import extract_offer_type_ship_timing

_KATAKANA_START = 0x30A1
_KATAKANA_END = 0x30F6
_KATAKANA_TO_HIRAGANA_OFFSET = 0x60


def fold_for_match(text: str) -> str:
    """NFKC → 小文字化 → カタカナをひらがな化。空白と記号は消さない。"""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return "".join(
        chr(ord(ch) - _KATAKANA_TO_HIRAGANA_OFFSET) if _KATAKANA_START <= ord(ch) <= _KATAKANA_END else ch
        for ch in normalized
    )


def normalize_for_match(text: str) -> str:
    """NFKC → 小文字化 → カタカナをひらがな化 → 空白除去 → 記号/句読点(P*/S*)除去。

    数字・英字は残す。
    """
    result = []
    for ch in fold_for_match(text):
        if ch.isspace():
            continue
        category = unicodedata.category(ch)
        if category[0] in ("P", "S"):
            continue
        result.append(ch)
    return "".join(result)


_SHORT_VALUE_MAX_LEN = 2
_VALUE_CACHE_SIZE = 16384


@lru_cache(maxsize=_VALUE_CACHE_SIZE)
def _normalize_value(text: str) -> str:
    """商品マスタの値（品番・記号・検索ワード・除外ワード）の正規化。同じ値を何度も正規化しないための記憶。"""
    return normalize_for_match(text)


def _needs_boundary(normalized: str) -> bool:
    """2文字以下、または数字だけの値は、語の境界があるときだけ当たりとする。"""
    return len(normalized) <= _SHORT_VALUE_MAX_LEN or normalized.isdigit()


# 数字だけの値は、金額の一部（1,151 / @151 / ¥151 / 151,000 / 151円）では境界ありとしない
_PRICE_LEFT_GUARD = r"(?<![0-9][,.])(?<![@¥$])"
_PRICE_RIGHT_GUARD = r"(?![,.][0-9])(?!円)"


def has_word_boundary(folded_text: str, value: str) -> bool:
    """fold_for_match 済みの文字列の中に、前後が英字・数字でない（または端の）value があるか。

    value が数字だけのときは、金額の一部になっている出現も除く。
    """
    needle = fold_for_match(value).strip()
    if not needle:
        return False
    left, right = r"(?<![a-z0-9])", r"(?![a-z0-9])"
    if needle.isdigit():
        left, right = left + _PRICE_LEFT_GUARD, right + _PRICE_RIGHT_GUARD
    return re.search(left + re.escape(needle) + right, folded_text) is not None


def has_left_word_boundary(folded_text: str, value: str) -> bool:
    """fold_for_match 済みの文字列の中に、直前が英字・数字でない（または先頭の）value の出現が1つでもあるか。右側は条件にしない。"""
    needle = fold_for_match(value).strip()
    if not needle:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(needle), folded_text) is not None


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


_NO_NAME_VALUES = frozenset({"none"})


def product_match_text(block: str, heading: str, raw_product_name: str | None) -> tuple[str, str]:
    """照合に使う文字列と、商品名の出どころ（BLOCK / HEADING / NONE）を返す。

    Gemini が写した商品名は、ブロックか見出しの原文に実際に書かれている場合だけ足す
    （原文に無い名前は足さない）。
    """
    name = (raw_product_name or "").strip()
    if not name or name.lower() in _NO_NAME_VALUES:
        return block, "NONE"
    normalized_name = normalize_for_match(name)
    if not normalized_name:
        return block, "NONE"
    if normalized_name in normalize_for_match(block):
        return f"{block}\n{name}", "BLOCK"
    if normalized_name in normalize_for_match(heading):
        return f"{block}\n{name}", "HEADING"
    return block, "NONE"


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
    boundary_dropped: tuple[int, ...] = ()
    # 品番・記号（product_code・mark）が当たった商品の id と、当たった値（試作版 v102 の点数づけが読む）
    code_hits: tuple[int, ...] = ()
    code_hit_values: Mapping[int, tuple[str, ...]] = field(default_factory=dict)


# 品番らしい値の厳格な照合（strict_codes=True）で、値の文字の間・前後に許す区切り文字。
# 半角・全角空白、ハイフン類、中黒、下線、ピリオド、アポストロフィ類。改行は含めない。
_CODE_SEPARATOR_CHARS = (
    " \u3000-\u2010\u2011\u2013\u2014\u2015\u30fc\u2212\u30fb_.'\u2019\u2018\u00b4\u0301`"
)
_CODE_SEPARATOR_RE = "[" + "".join(re.escape(ch) for ch in _CODE_SEPARATOR_CHARS) + "]*"
# 型番の直後が「ハイフン類＋数字」（例 EB02-003 の -003＝カード番号）のときは、その型番には当てない。
_CODE_HYPHEN_CHARS = "-‐‑–—―−ー"
_CODE_NOT_BEFORE_HYPHEN_DIGIT_RE = "(?![" + "".join(re.escape(ch) for ch in _CODE_HYPHEN_CHARS) + "][0-9])"
# 値の中に記号（区切り集合外の P*/S*）があった隙間で許す文字：改行類（\n \r \v \f NEL LS PS）以外の非単語文字と下線（かな・漢字・英数字は含まない）。
_SYMBOL_GAP_RE = r"(?:[^\w\n\r\x0b\x0c\x85\u2028\u2029]|_)*"
# 区切り文字のうち normalize_for_match で消えずに nb に残るもの（ー と結合アクセント U+0301）。事前絞り込みで除く。
_NB_SEPARATORS_REMOVED = {ord("ー"): None, 0x0301: None}
_ALNUM_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789")
_LETTER_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz")
_CODE_PATTERN_CACHE_SIZE = 16384


def _is_code_char(ch: str) -> bool:
    """品番らしい値に含めてよい文字：英数字、区切り文字、記号（P*/S*。normalize_for_match が取り除く文字）。"""
    return ch in _ALNUM_CHARS or ch in _CODE_SEPARATOR_CHARS or unicodedata.category(ch)[0] in ("P", "S")


@lru_cache(maxsize=_CODE_PATTERN_CACHE_SIZE)
def _strict_code_pattern(raw: str) -> tuple[str, re.Pattern[str]] | None:
    """品番らしい値なら（英数字だけ並べた文字列, 区切りを許す正規表現）を返す。品番らしくなければ None。

    品番らしい値：fold_for_match 後の文字が英字・数字・区切り文字・記号(P*/S*)だけで、英字を1つ以上含み、
    英数字が3文字以上（2文字以下・数字だけの値は既存の規則のまま）。値の先頭より前・末尾より後ろの記号はパターンに入れない。
    値の中で記号があった隙間だけ、原文の記号・空白を許す（記号のない隙間は区切り文字だけを許す）。
    値の直後が「ハイフン類＋数字」（カード番号の形。例 EB02-003）のときは当たらない（_CODE_NOT_BEFORE_HYPHEN_DIGIT_RE）。
    """
    folded = fold_for_match(raw)
    if not all(_is_code_char(ch) for ch in folded):
        return None
    alnum = "".join(ch for ch in folded if ch in _ALNUM_CHARS)
    if len(alnum) <= _SHORT_VALUE_MAX_LEN or alnum.isdigit() or not any(ch in _LETTER_CHARS for ch in alnum):
        return None
    parts: list[str] = []
    gap_has_symbol = False
    for ch in folded:
        if ch in _ALNUM_CHARS:
            if parts:
                parts.append(_SYMBOL_GAP_RE if gap_has_symbol else _CODE_SEPARATOR_RE)
            parts.append(re.escape(ch))
            gap_has_symbol = False
        elif ch not in _CODE_SEPARATOR_CHARS:
            gap_has_symbol = True
    pattern = re.compile(r"(?<![a-z0-9])" + "".join(parts) + r"(?![a-z0-9])" + _CODE_NOT_BEFORE_HYPHEN_DIGIT_RE)
    return alnum, pattern


def _strict_code_hits(raw: str, nb: str, folded: str) -> bool | None:
    """品番らしい値が、原文の書き方のまま前後が区切られて当たるか。品番らしくない値は None（既存の規則で判定する）。"""
    compiled = _strict_code_pattern(raw)
    if compiled is None:
        return None
    alnum, pattern = compiled
    if alnum not in nb and alnum not in nb.translate(_NB_SEPARATORS_REMOVED):
        return False
    return pattern.search(folded) is not None


def _value_hits(raw: str, nb: str, folded: str | None, strict_codes: bool = False) -> bool:
    """raw を正規化したものが nb に含まれるか。folded を渡すと、短い値・数字だけの値は境界も条件にする。

    strict_codes=True（folded も必要）のときは、品番らしい値は原文の書き方のまま前後が区切られているときだけ当たりとする。
    """
    if strict_codes and folded is not None:
        strict_result = _strict_code_hits(raw, nb, folded)
        if strict_result is not None:
            return strict_result
    normalized = _normalize_value(raw)
    if not normalized or normalized not in nb:
        return False
    if folded is not None and _needs_boundary(normalized):
        return has_word_boundary(folded, raw)
    return True


def _code_candidate_basis(
    product: ProductEntry, nb: str, folded: str | None = None, strict_codes: bool = False
) -> str | None:
    """product_code または mark を正規化したもの（空でないもの）が nb に含まれれば 'RAWCODE'。

    folded（fold_for_match 済みの照合文字列）を渡すと、短い値・数字だけの値は語の境界も条件にする。
    """
    for raw in (product.product_code, product.mark):
        if raw and _value_hits(raw, nb, folded, strict_codes):
            return "RAWCODE"
    return None


def _keyword_matches(
    product: ProductEntry, nb: str, folded: str | None = None, strict_codes: bool = False
) -> tuple[str, ...]:
    """search_keywords のうち、全トークンが nb に含まれるものを返す（当たった keyword 全部）。

    folded を渡すと、短い・数字だけのトークンは語の境界も条件にする。
    """
    matched: list[str] = []
    for keyword in product.search_keywords:
        words = [word for word in keyword.split(" ") if word]
        # 正規化すると空になるトークン（記号だけ等）は従来どおり「含まれる」扱い
        if words and all(not _normalize_value(word) or _value_hits(word, nb, folded, strict_codes) for word in words):
            matched.append(keyword)
    return tuple(matched)


def build_cond_terms(cond_entries: Sequence[dict]) -> tuple[str, ...]:
    """状態マスタ（public.conditions）の合図の語を、照合と同じ正規化にしたタプルで返す（長い順・重複なし）。

    対象は match_type が KEYWORD / LITERAL の行の search_kw（カンマ区切り）だけ。REGEX / DEFAULT は語として扱えないので入れない。
    """
    terms: set[str] = set()
    for entry in cond_entries:
        if entry.get("match_type", "KEYWORD") not in _COND_TERM_TYPES:
            continue
        for raw in (entry.get("search_kw") or "").split(","):
            normalized = _normalize_value(raw.strip())
            if normalized:
                terms.add(normalized)
    return tuple(sorted(terms, key=lambda t: (-len(t), t)))


_COND_TERM_TYPES = frozenset({"KEYWORD", "LITERAL"})
_FOLDED_GAP = r"(?:[^\w]|_)*"


@lru_cache(maxsize=_VALUE_CACHE_SIZE)
def _folded_term_pattern(normalized: str) -> re.Pattern[str]:
    """正規化済みの語の文字の間に、nb で消える文字（空白・記号）を許す正規表現。folded（空白と記号が残る文字列）用。"""
    return re.compile(_FOLDED_GAP.join(re.escape(ch) for ch in normalized))


def _blank_spans(text: str, spans: Sequence[tuple[int, int]]) -> str:
    """spans の範囲を同じ長さの空白に置き換える（位置は変えない）。"""
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            chars[i] = " "
    return "".join(chars)


def _mask_contained(
    normalized: str, nb: str, folded: str | None, cond_terms: Sequence[str]
) -> tuple[str, str | None]:
    """除外語（正規化済み）の一致箇所のうち、より長い合図の語の一致箇所に完全に収まるものを空白にした (nb, folded) を返す。

    合図の語は、除外語より正規化後の長さが長く、除外語を含むものだけが対象。nb は文字列の位置、folded は記号・空白を許す位置で探す。
    """
    nb_spans: list[tuple[int, int]] = []
    fo_spans: list[tuple[int, int]] = []
    size = len(normalized)
    inner = re.compile("(?=" + re.escape(normalized) + ")")
    inner_folded = _folded_term_pattern(normalized)
    for cue in cond_terms:
        if len(cue) <= size or normalized not in cue:
            continue
        offsets = [m.start() for m in inner.finditer(cue)]
        for m in re.finditer("(?=" + re.escape(cue) + ")", nb):
            nb_spans.extend((m.start() + o, m.start() + o + size) for o in offsets)
        if folded is not None:
            for m in _folded_term_pattern(cue).finditer(folded):
                sub = folded[m.start():m.end()]
                fo_spans.extend((m.start() + i.start(), m.start() + i.end()) for i in inner_folded.finditer(sub))
    if not nb_spans and not fo_spans:
        return nb, folded
    return _blank_spans(nb, nb_spans), (_blank_spans(folded, fo_spans) if folded is not None else None)


def _exclude_hit(keyword: str, nb: str, folded: str | None, strict_codes: bool) -> bool:
    """除外ワード1つが nb（folded）に当たるか。"""
    if strict_codes and folded is not None:
        strict_result = _strict_code_hits(keyword, nb, folded)
        if strict_result is not None:
            return strict_result
    normalized = _normalize_value(keyword)
    if not normalized or normalized not in nb:
        return False
    if folded is not None and _needs_boundary(normalized) and not has_left_word_boundary(folded, keyword):
        return False
    return True


def _excluded_keywords(
    product: ProductEntry,
    nb: str,
    folded: str | None = None,
    strict_codes: bool = False,
    cond_terms: Sequence[str] = (),
) -> tuple[str, ...]:
    """exclude_keywords のうち、正規化したものが nb に含まれるものを返す。

    strict_codes=True（folded も必要）のときは、品番らしい除外ワードは前後が区切られているときだけ当たりとする。

    cond_terms（正規化済みの状態の合図の語。既定は空＝従来どおり）を渡すと、除外ワードの一致箇所が、それより長い合図の語
    （例：除外ワード AR・合図の語 ARパック）の一致箇所に完全に収まるときだけ、その一致を無視する。
    無視されない一致が1つでも残れば、従来どおり除外する。
    """
    excluded: list[str] = []
    for keyword in product.exclude_keywords:
        if not _exclude_hit(keyword, nb, folded, strict_codes):
            continue
        if cond_terms:
            normalized = _normalize_value(keyword)
            if normalized:
                nb_masked, folded_masked = _mask_contained(normalized, nb, folded, cond_terms)
                if (nb_masked is not nb or folded_masked is not folded) and not _exclude_hit(
                    keyword, nb_masked, folded_masked, strict_codes
                ):
                    continue
        excluded.append(keyword)
    return tuple(excluded)


def _is_candidate(product: ProductEntry, nb: str, folded: str | None, cond_terms: Sequence[str] = ()) -> bool:
    """コード・検索ワードのどちらかに当たり、除外ワードに当たらないか。"""
    if _code_candidate_basis(product, nb, folded) is None and not _keyword_matches(product, nb, folded):
        return False
    return not _excluded_keywords(product, nb, cond_terms=cond_terms)


def match_product(
    block: str, products: Sequence[ProductEntry], *, strict_codes: bool = False, cond_terms: Sequence[str] = ()
) -> MatchResult:
    """strict_codes=True（試作版 v102 だけが使う）：品番・記号・検索ワードの品番らしい値は、原文の書き方のまま前後が区切られているときだけ当たり。

    cond_terms：除外ワードの一致が状態の合図の語に収まるときは無視する（`_excluded_keywords` を参照。既定は空＝従来どおり）。
    """
    nb = normalize_for_match(block)
    folded = fold_for_match(block)

    code_basis: dict[int, str] = {}
    matched_keywords: dict[int, tuple[str, ...]] = {}
    excluded_by: dict[int, tuple[str, ...]] = {}
    candidates: list[int] = []
    boundary_dropped: list[int] = []
    code_hit_values: dict[int, tuple[str, ...]] = {}

    for product in products:
        basis = _code_candidate_basis(product, nb, folded, strict_codes)
        keywords = _keyword_matches(product, nb, folded, strict_codes)
        if basis is None and not keywords:
            # 境界の条件が無ければ候補になっていた商品を控える
            if _is_candidate(product, nb, None, cond_terms):
                boundary_dropped.append(product.id)
            continue
        if basis is not None:
            code_basis[product.id] = basis
            code_hit_values[product.id] = tuple(
                raw for raw in (product.product_code, product.mark) if raw and _value_hits(raw, nb, folded, strict_codes)
            )
        if keywords:
            matched_keywords[product.id] = keywords

        excluded = _excluded_keywords(product, nb, folded, strict_codes, cond_terms)
        if excluded:
            excluded_by[product.id] = excluded
            continue

        candidates.append(product.id)

    dropped = tuple(boundary_dropped)
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
            boundary_dropped=dropped,
            code_hits=tuple(code_hit_values),
            code_hit_values=code_hit_values,
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
            boundary_dropped=dropped,
            code_hits=tuple(code_hit_values),
            code_hit_values=code_hit_values,
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
        boundary_dropped=dropped,
        code_hits=tuple(code_hit_values),
        code_hit_values=code_hit_values,
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


_HEAD_Y_RE = re.compile(r"(?<![A-Za-z])Y\s*$")
_DIGIT_X_BEFORE_RE = re.compile(r"\d[xX]$")


def is_tagged_number(text: str, start: int) -> bool:
    """text の start から始まる数字が、英字か「-」の直後にあって数えない数字か（PSA8 の 8・品番の一部など）。

    Y の直後（Y100,000）と、数字に挟まれた x/X（3x100）は数える。
    原文から値段を読む処理（_extract_line_numbers）と、Gemini の値段の写しを読む処理
    （gemini_raw_copy_v101._single_price_number）が同じ規則を使うための1か所。ここを変えると両方が変わる。
    """
    before = text[:start]
    if _HEAD_Y_RE.search(before) or _DIGIT_X_BEFORE_RE.search(before):
        return False
    return bool(re.search(r"[A-Za-z]$", before)) or before.endswith("-")


def _extract_line_numbers(line: str, line_no: int, aliases: Sequence[str]) -> list[_Num]:
    """1行から値を取り出す。品番の一部（OP-17・PSA10・30th）は取り出さない。"""
    nums: list[_Num] = []
    for m in _NUMBER_RE.finditer(line):
        before, after = line[: m.start()], line[m.end():]
        raw = m.group(0).replace("，", ",")
        head_y = bool(_HEAD_Y_RE.search(before))
        if is_tagged_number(line, m.start()):
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
) -> tuple[list[_Num], list[_Num], list[_Num]]:
    """(価格の候補, 数量の候補, 数量を目印なしの数値で補ったもの) を返す。"""
    prices = [n for nums in per_line for n in nums if n.price_marked]
    qtys = [n for nums in per_line for n in nums if n.qty_marked]
    qty_filled: list[_Num] = []
    for nums in per_line:
        unmarked = [n for n in nums if not n.price_marked and not n.qty_marked]
        has_p = any(n.price_marked for n in nums)
        has_q = any(n.qty_marked for n in nums)
        if len(unmarked) == 1 and has_p != has_q:
            filled_side, groups = (qtys, g_qty) if has_p else (prices, g_price)
            if _copied_by_gemini(unmarked[0], groups):
                filled_side.append(unmarked[0])
                if has_p:
                    qty_filled.append(unmarked[0])
    return prices, qtys, qty_filled


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
    prices, qtys, qty_filled = _marker_candidates(per_line, g_price, g_qty)
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
        if qty is not None and any(qty is f for f in qty_filled):
            reasons.append("quantity_unmarked")
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
