"""試作版 v102：〆（完売）の件の商品を、同じ仕入元の過去48時間の投稿の在庫の行から決める（純粋関数。DB を持たない）。

規則は docs/handoff/v102-shime-inventory-ref/design.md §2。
過去の投稿を読む処理（同じ仕入元・48時間以内）は line_analysis_v102_svc.load_soldout_ref_posts が持つ。
語の取り出しと当て方は gemini_raw_copy_v102_followup（#4090）と同じ部品を使う。
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.services.extraction_judgement_svc import _strict_code_pattern, fold_for_match, normalize_for_match
from app.services.gemini_raw_copy_v102_followup import _is_clue, extract_tokens
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters, match_text_g2

MATCH_STATUS_MATCHED_SOLDOUT_REF = "matched_soldout_ref"

_UNDECIDED_STATUSES = ("unmatched", "ambiguous")
_EXCLUDED = "excluded"


@dataclass(frozen=True)
class SoldoutRefPost:
    """参照する過去の投稿（同じ仕入元・今の投稿より前・48時間以内）。"""

    message_id: str
    posted_at: datetime
    raw_text: str


@dataclass(frozen=True)
class RefRow:
    """参照する投稿の、商品が1つに決まった行。post_index は新しい順の添字（0 が最新）、order は時刻の古い順の通し番号。"""

    post_index: int
    message_id: str
    line_no: int
    product_id: int
    folded: str
    normalized: str
    is_sold: bool
    order: int


@dataclass(frozen=True)
class SoldoutRefDecision:
    product_id: int
    ref_message_id: str
    ref_line: int
    tokens: tuple[str, ...]


def _nfkc_lower(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def _has_sold_word(text: str, sold_out_words: Sequence[str]) -> bool:
    folded = _nfkc_lower(text)
    return any(w and _nfkc_lower(w) in folded for w in sold_out_words)


def _strip_sold_words(text: str, sold_out_words: Sequence[str]) -> str:
    """NFKC にした text から〆の言葉を取り除く（長い言葉から先に。大文字小文字は問わない）。"""
    stripped = unicodedata.normalize("NFKC", text)
    for word in sorted((_nfkc_lower(w) for w in sold_out_words if w), key=len, reverse=True):
        stripped = re.sub(re.escape(word), "", stripped, flags=re.IGNORECASE)
    return stripped


def soldout_targets(extracted: Sequence[Mapping[str, Any]]) -> list[int]:
    """規則1：〆で商品が決まっていない件の添字（落とした件は除く）。"""
    return [
        i for i, row in enumerate(extracted)
        if row.get("status_effect") == _EXCLUDED and row.get("match_status") in _UNDECIDED_STATUSES and not row.get("rejected")
    ]


def build_ref_rows(
    posts: Sequence[SoldoutRefPost], masters: ProductFirstMasters, sold_out_words: Sequence[str],
) -> tuple[RefRow, ...]:
    """規則3：posts（新しい順）の各行のうち、v102 と同じ商品照合で商品が1つに決まる行。〆の言葉を含む行は is_sold。

    戻り値は時刻の古い順（同じ投稿の中は行順）で、order はその通し番号。
    """
    rows: list[RefRow] = []
    for post_index in range(len(posts) - 1, -1, -1):
        post = posts[post_index]
        for line_no, line in enumerate(post.raw_text.split("\n"), start=1):
            if not line.strip():
                continue
            match = match_text_g2(line, masters)
            if match.status == "matched" and match.product_id is not None:
                rows.append(RefRow(
                    post_index, post.message_id, line_no, int(match.product_id), fold_for_match(line), normalize_for_match(line),
                    _has_sold_word(line, sold_out_words), len(rows),
                ))
    return tuple(rows)


def _already_sold(rows: Sequence[RefRow]) -> frozenset[int]:
    """規則4：同じ商品の〆の行が後ろにある在庫の行の order（商品単位の消し込み）。"""
    last_sold: dict[int, int] = {}
    for row in rows:
        if row.is_sold:
            last_sold[row.product_id] = max(row.order, last_sold.get(row.product_id, -1))
    return frozenset(r.order for r in rows if not r.is_sold and last_sold.get(r.product_id, -1) > r.order)


def _row_hits_all(codes: Sequence[str], names: Sequence[str], row: RefRow) -> bool:
    """規則6：語が全て1つの参照行に当たる（型番は厳格パターン、名前は部分一致＝#4090 `_hits` と同じ当て方）。"""
    for code in codes:
        pattern = _strict_code_pattern(code)
        if pattern is None or not pattern[1].search(row.folded):
            return False
    return all(name in row.normalized for name in names)


def _decide_one(
    row: Mapping[str, Any], lines: Sequence[str], rows: Sequence[RefRow], sold: frozenset[int],
    units: frozenset[str], plural_words: Sequence[str], sold_out_words: Sequence[str],
) -> SoldoutRefDecision | None:
    text = "\n".join(lines[n - 1] for n in row.get("lines", []) if 1 <= n <= len(lines))
    folded_text = unicodedata.normalize("NFKC", text)
    if any(w and unicodedata.normalize("NFKC", w) in folded_text for w in plural_words):
        return None  # 規則5：複数を指す言葉
    codes, names = extract_tokens(_strip_sold_words(text, sold_out_words))
    codes = tuple(w for w in codes if _is_clue(w, units))
    names = tuple(n for n in names if _is_clue(n, units))
    if not codes and not names:
        return None  # 規則5：残った語が0
    hit_posts = sorted({r.post_index for r in rows if _row_hits_all(codes, names, r)})
    if not hit_posts:
        return None
    hits = [r for r in rows if r.post_index == hit_posts[0] and _row_hits_all(codes, names, r)]  # 最初に当たる投稿で止める
    stock = [r for r in hits if not r.is_sold and r.order not in sold]
    products = {r.product_id for r in stock}
    if len(products) != 1:
        return None  # 規則6：0（すでに〆）または2つ以上
    (product_id,) = products
    if row.get("match_status") == "ambiguous" and product_id not in (row.get("match_candidates") or []):
        return None  # 規則7
    first = min(stock, key=lambda r: r.order)
    return SoldoutRefDecision(product_id, first.message_id, first.line_no, (*codes, *names))


def decide_soldout_ref(
    extracted: Sequence[Mapping[str, Any]], lines: Sequence[str], rows: Sequence[RefRow],
    *, units: frozenset[str] = frozenset(), plural_words: Sequence[str] = (), sold_out_words: Sequence[str] = (),
) -> dict[int, SoldoutRefDecision]:
    """〆で商品が決まらない件のうち、過去の投稿の在庫の行で商品が1つに決まる件（添字 → 決定）。それ以外の件は触らない。"""
    targets = soldout_targets(extracted)
    if not rows or not targets:
        return {}
    sold = _already_sold(rows)
    decisions = {i: _decide_one(extracted[i], lines, rows, sold, units, plural_words, sold_out_words) for i in targets}
    return {i: d for i, d in decisions.items() if d is not None}
