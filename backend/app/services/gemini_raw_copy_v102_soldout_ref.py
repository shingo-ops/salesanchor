"""試作版 v102：〆（完売）の件の商品を、同じ仕入元の過去48時間の投稿の在庫の行から決める（純粋関数。DB を持たない）。

規則は docs/handoff/v102-shime-inventory-ref/design.md §2（規則1〜7）と docs/handoff/v102-shime-multi-targets/design.md §2（規則8〜11）。
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
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters, WorkName, match_text_g2

MATCH_STATUS_MATCHED_SOLDOUT_REF = "matched_soldout_ref"

_UNDECIDED_STATUSES = ("unmatched", "ambiguous")
_EXCLUDED = "excluded"


@dataclass(frozen=True)
class StockItem:
    """参照する投稿の保存済みの解析結果の1件：その件の行番号と、決まった (商品, 状態)（完売の相手の元）。"""

    lines: frozenset[int]
    product_id: int
    condition_id: int


@dataclass(frozen=True)
class SoldoutTarget:
    """完売の相手（商品×状態）と、その根拠（参照した在庫の投稿と行番号）。"""

    product_id: int
    condition_id: int
    ref_message_id: str
    ref_line: int


@dataclass(frozen=True)
class SoldoutRefPost:
    """参照する過去の投稿（同じ仕入元・今の投稿より前・48時間以内）。stock_items はその投稿の最新の job の保存済みの解析結果（'Sold out' でない件）。"""

    message_id: str
    posted_at: datetime
    raw_text: str
    stock_items: tuple[StockItem, ...] = ()


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
    """product_id は完売の相手があるとき targets[0].product_id。targets が空なら商品だけ決めた（状態は〆の行の文字から）。"""

    product_id: int
    ref_message_id: str
    ref_line: int
    tokens: tuple[str, ...]
    targets: tuple[SoldoutTarget, ...] = ()


@dataclass(frozen=True)
class _Rules:
    """件ごとに変わらない判定の材料。"""

    units: frozenset[str]
    plural_words: Sequence[str]
    sold_out_words: Sequence[str]
    posts: Sequence[SoldoutRefPost]
    works: Sequence[WorkName]
    product_works: Mapping[int, int]


def _nfkc_lower(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def _has_sold_word(text: str, sold_out_words: Sequence[str]) -> bool:
    folded = _nfkc_lower(text)
    return any(w and _nfkc_lower(w) in folded for w in sold_out_words)


def _strip_words(text: str, words: Sequence[str]) -> str:
    """NFKC にした text から words（〆の言葉・複数を指す言葉）を取り除く（長い言葉から先に。大文字小文字は問わない）。"""
    stripped = unicodedata.normalize("NFKC", text)
    for word in sorted((_nfkc_lower(w) for w in words if w), key=len, reverse=True):
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


def _texts_hit_all(codes: Sequence[str], names: Sequence[str], folded: str, normalized: str) -> bool:
    """規則6：語が全て1つの行の文字に当たる（型番は厳格パターン、名前は部分一致＝#4090 `_hits` と同じ当て方）。語が0なら True。"""
    for code in codes:
        pattern = _strict_code_pattern(code)
        if pattern is None or not pattern[1].search(folded):
            return False
    return all(name in normalized for name in names)


def _row_hits_all(codes: Sequence[str], names: Sequence[str], row: RefRow) -> bool:
    return _texts_hit_all(codes, names, row.folded, row.normalized)


def _has_any(text: str, words: Sequence[str]) -> bool:
    folded = unicodedata.normalize("NFKC", text)
    return any(w and unicodedata.normalize("NFKC", w) in folded for w in words)


def _matched_works(text: str, works: Sequence[WorkName]) -> dict[int, tuple[str, ...]]:
    """規則9：件の文字（normalize_for_match）に名前が含まれる中分類（中分類 ID → 含まれた名前）。"""
    normalized = normalize_for_match(text)
    found: dict[int, tuple[str, ...]] = {}
    for work in works:
        hits = tuple(n for n in (normalize_for_match(x) for x in work.names) if n and n in normalized)
        if hits:
            found[work.work_id] = (*found.get(work.work_id, ()), *hits)
    return found


def _clue_tokens(text: str, rules: _Rules, work_names: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """規則5・8・9：〆の言葉と複数を指す言葉を取り除いて語を取り、単位・数字だけの語と作品名と同じ名前の語を外す。"""
    codes, names = extract_tokens(_strip_words(text, [*rules.sold_out_words, *rules.plural_words]))
    return (
        tuple(w for w in codes if _is_clue(w, rules.units)),
        tuple(n for n in names if _is_clue(n, rules.units) and n not in work_names),
    )


def _hit_rows(rows: Sequence[RefRow], codes: Sequence[str], names: Sequence[str], work_id: int | None, rules: _Rules) -> list[RefRow]:
    """最初に当たる投稿（新しい順で最初）の当たり行。作品名の〆では、商品の中分類がその中分類の行だけ。"""
    candidates = [r for r in rows if (work_id is None or rules.product_works.get(r.product_id) == work_id) and _row_hits_all(codes, names, r)]
    if not candidates:
        return []
    first = min(r.post_index for r in candidates)
    return [r for r in candidates if r.post_index == first]


def _has_unresolved_clue_line(
    post: SoldoutRefPost | None, resolved_lines: frozenset[int], codes: Sequence[str], names: Sequence[str], sold_out_words: Sequence[str],
) -> bool:
    """規則10：その投稿に、〆の言葉を含まず、語が全て当たるのに商品が決まらない行があるか。"""
    if post is None:
        return False
    for line_no, line in enumerate(post.raw_text.split("\n"), start=1):
        if line_no in resolved_lines or not line.strip() or _has_sold_word(line, sold_out_words):
            continue
        if _texts_hit_all(codes, names, fold_for_match(line), normalize_for_match(line)):
            return True
    return False


def _targets_of(stock: Sequence[RefRow], post: SoldoutRefPost | None) -> tuple[SoldoutTarget, ...] | None:
    """規則11：在庫の行ごとに、その行番号を含み商品が同じ保存済みの件の (商品, 状態)（行の順、重複は最初だけ）。

    相手が見つからない在庫の行が1つでもあれば None。
    """
    found: dict[tuple[int, int], SoldoutTarget] = {}
    for row in sorted(stock, key=lambda r: r.order):
        pairs = [
            (it.product_id, it.condition_id)
            for it in (post.stock_items if post is not None else ())
            if row.line_no in it.lines and it.product_id == row.product_id
        ]
        if not pairs:
            return None
        for product_id, condition_id in pairs:
            found.setdefault((product_id, condition_id), SoldoutTarget(product_id, condition_id, row.message_id, row.line_no))
    return tuple(found.values())


def _decide_one(
    row: Mapping[str, Any], lines: Sequence[str], rows: Sequence[RefRow], sold: frozenset[int], rules: _Rules,
) -> SoldoutRefDecision | None:
    text = "\n".join(lines[n - 1] for n in row.get("lines", []) if 1 <= n <= len(lines))
    is_plural = _has_any(text, rules.plural_words)  # 規則8：複数を指す言葉
    found = _matched_works(text, rules.works) if is_plural else {}
    if len(found) >= 2:
        return None  # 規則9：含まれる中分類が2つ以上
    work_id, work_names = next(iter(found.items()), (None, ()))
    codes, names = _clue_tokens(text, rules, work_names)
    if work_id is None and not codes and not names:
        return None  # 規則5・9：作品名の〆でなく、残った語が0
    hits = _hit_rows(rows, codes, names, work_id, rules)
    stock = [r for r in hits if not r.is_sold and r.order not in sold]
    products = {r.product_id for r in stock}
    if not products or (not is_plural and len(products) != 1):
        return None  # 規則10：0（すでに〆）、複数語なしで2つ以上
    post = rules.posts[hits[0].post_index] if hits[0].post_index < len(rules.posts) else None
    if is_plural and work_id is None and _has_unresolved_clue_line(
        post, frozenset(r.line_no for r in rows if r.post_index == hits[0].post_index), codes, names, rules.sold_out_words,
    ):
        return None  # 規則10：語が当たるのに商品が決まらない行がある
    if row.get("match_status") == "ambiguous" and not products <= set(row.get("match_candidates") or []):
        return None  # 規則7・10：候補に無い商品が混ざる
    targets = _targets_of(stock, post)
    if targets is None and is_plural:
        return None  # 規則11：複数語で、相手が見つからない在庫の行がある
    return _decision(stock, targets or (), (*codes, *names))


def _decision(stock: Sequence[RefRow], targets: tuple[SoldoutTarget, ...], tokens: tuple[str, ...]) -> SoldoutRefDecision:
    """相手があれば先頭の相手の商品・根拠、無ければ最初の在庫の行の商品・根拠（商品は1つだけ。規則10）。"""
    first = min(stock, key=lambda r: r.order)
    if targets:
        return SoldoutRefDecision(targets[0].product_id, targets[0].ref_message_id, targets[0].ref_line, tokens, targets)
    return SoldoutRefDecision(first.product_id, first.message_id, first.line_no, tokens)


def decide_soldout_ref(
    extracted: Sequence[Mapping[str, Any]], lines: Sequence[str], rows: Sequence[RefRow],
    *, units: frozenset[str] = frozenset(), plural_words: Sequence[str] = (), sold_out_words: Sequence[str] = (),
    posts: Sequence[SoldoutRefPost] = (), works: Sequence[WorkName] = (), product_works: Mapping[int, int] | None = None,
) -> dict[int, SoldoutRefDecision]:
    """〆で商品が決まらない件のうち、過去の投稿の在庫の行で商品（と完売の相手）が決まる件（添字 → 決定）。それ以外の件は触らない。

    posts は build_ref_rows に渡したのと同じ並び（新しい順。RefRow.post_index がその添字）、product_works は商品 ID → 中分類 ID。
    """
    targets = soldout_targets(extracted)
    if not rows or not targets:
        return {}
    sold = _already_sold(rows)
    rules = _Rules(units, plural_words, sold_out_words, posts, works, product_works or {})
    decisions = {i: _decide_one(extracted[i], lines, rows, sold, rules) for i in targets}
    return {i: d for i, d in decisions.items() if d is not None}
