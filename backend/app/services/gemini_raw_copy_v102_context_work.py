"""試作版 v102：作品をまたぐ曖昧な商品（ambiguous）を、前後の商品の作品で決める。

PO 決定（2026-10-08）：
  (a) 前と後ろが同じ作品のとき → 決める（競合の条件は見ない）
  (b) 片側だけ手がかりがあるとき → その作品の候補が1つで、落とす候補の作品がその投稿に無ければ決める
  (c) 前後2件ずつ見て最も多い作品が1つに決まるとき → (b) と同じ条件で決める
  それ以外 → 決めない（要確認に回す）

手がかりは1回目に作った件のうち match_status が matched で作品が分かる件だけ。
ここで決めた件は手がかりにしない（連鎖しない）。判定の言葉（作品名・商品名）は書かない。マスタ（product_entries）から引く。
このモジュールは gemini_raw_copy_v101 から呼ばれる（v101 を import しない）。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.services.extraction_judgement_svc import ProductEntry

# --- 決め方（rule）と決まらない理由（reason）。ここ1か所にまとめる -----------------------------
RULE_SAME_BOTH_SIDES = "a"
RULE_ONE_SIDE = "b"
RULE_MAJORITY = "c"

REASON_NO_CLUE = "no_clue"
REASON_TIE = "tie"
REASON_CLUE_WORK_CANDIDATES_0 = "clue_work_candidates_0"
REASON_CLUE_WORK_CANDIDATES_2PLUS = "clue_work_candidates_2plus"
REASON_COMPETITOR_WORK_IN_POST = "competitor_work_in_post"
REASON_NEIGHBORS_DIFFER_PREFIX = "neighbors_differ+"

MATCH_STATUS_AMBIGUOUS = "ambiguous"
MATCH_STATUS_MATCHED = "matched"
MATCH_STATUS_MATCHED_CONTEXT = "matched_context"

MAJORITY_WINDOW = 2  # (c) で前後それぞれ何件まで見るか


@dataclass(frozen=True)
class ContextClue:
    line: int
    product_id: int
    work_id: int


@dataclass(frozen=True)
class ContextDecision:
    """決まった件は rule・product_id・clues・dropped を持ち、reason は None。決まらない件は reason だけを持つ。"""

    rule: str | None
    product_id: int | None
    clues: tuple[ContextClue, ...]
    dropped: tuple[int, ...]
    reason: str | None

    @property
    def is_decided(self) -> bool:
        return self.product_id is not None


def _undecided(reason: str) -> ContextDecision:
    return ContextDecision(rule=None, product_id=None, clues=(), dropped=(), reason=reason)


def _clues_near(
    items: Sequence[Mapping], work_of: Mapping[int, int | None], index: int, side: int, limit: int,
) -> list[ContextClue]:
    """index の件から price_line の距離が近い順に、手がかりになる件を limit 件まで。side は -1（前）か 1（後）。"""
    price_line = items[index]["price_line"]
    ranked = sorted(
        (abs(it["price_line"] - price_line), i)
        for i, it in enumerate(items)
        if it.get("price_line") is not None and (it["price_line"] - price_line) * side > 0
    )
    clues: list[ContextClue] = []
    for _distance, i in ranked:
        item = items[i]
        work = work_of.get(item.get("product_id")) if item.get("match_status") == MATCH_STATUS_MATCHED else None
        if work is None:
            continue
        clues.append(ContextClue(line=item["price_line"], product_id=item["product_id"], work_id=work))
        if len(clues) == limit:
            break
    return clues


def _pick(
    work: int, candidates: Sequence[int], work_of: Mapping[int, int | None], post_works: set[int], *, check_competitor: bool,
) -> tuple[int | None, str | None]:
    """work の候補がちょうど1つならその商品ID。(商品ID, 決まらない理由)。"""
    same = sorted(c for c in candidates if work_of.get(c) == work)
    if not same:
        return None, REASON_CLUE_WORK_CANDIDATES_0
    if len(same) > 1:
        return None, REASON_CLUE_WORK_CANDIDATES_2PLUS
    if check_competitor and {work_of.get(c) for c in candidates if work_of.get(c) != work} & post_works:
        return None, REASON_COMPETITOR_WORK_IN_POST
    return same[0], None


def _decided(rule: str, chosen: int, candidates: Sequence[int], clues: Sequence[ContextClue]) -> ContextDecision:
    return ContextDecision(
        rule=rule, product_id=chosen, clues=tuple(clues), dropped=tuple(c for c in candidates if c != chosen), reason=None,
    )


def _decide_one(
    items: Sequence[Mapping], work_of: Mapping[int, int | None], post_works: set[int], index: int, candidates: Sequence[int],
) -> ContextDecision:
    before = _clues_near(items, work_of, index, -1, 1)
    after = _clues_near(items, work_of, index, 1, 1)
    both_sides = bool(before and after)
    if both_sides and before[0].work_id == after[0].work_id:
        chosen, _reason = _pick(before[0].work_id, candidates, work_of, post_works, check_competitor=False)
        if chosen is not None:
            return _decided(RULE_SAME_BOTH_SIDES, chosen, candidates, [*before, *after])
    if bool(before) != bool(after):
        chosen, _reason = _pick((before or after)[0].work_id, candidates, work_of, post_works, check_competitor=True)
        if chosen is not None:
            return _decided(RULE_ONE_SIDE, chosen, candidates, [*before, *after])
    near = [*_clues_near(items, work_of, index, -1, MAJORITY_WINDOW), *_clues_near(items, work_of, index, 1, MAJORITY_WINDOW)]
    if not near:
        return _undecided(REASON_NO_CLUE)
    ranked = Counter(c.work_id for c in near).most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return _undecided(REASON_TIE)
    chosen, reason = _pick(ranked[0][0], candidates, work_of, post_works, check_competitor=True)
    if chosen is not None:
        return _decided(RULE_MAJORITY, chosen, candidates, near)
    if both_sides and before[0].work_id != after[0].work_id:
        reason = f"{REASON_NEIGHBORS_DIFFER_PREFIX}{reason}"
    return _undecided(reason or REASON_NO_CLUE)


def decide_by_context(items: Sequence[Mapping], product_entries: Sequence[ProductEntry]) -> dict[int, ContextDecision]:
    """1投稿分の items（1回目の結果）→ 添字ごとの決定。対象でない件（候補が同じ作品だけの ambiguous など）は含めない。"""
    work_of = {p.id: p.work_id for p in product_entries}
    post_works = {
        work_of[it["product_id"]] for it in items
        if it.get("match_status") == MATCH_STATUS_MATCHED and work_of.get(it.get("product_id")) is not None
    }
    result: dict[int, ContextDecision] = {}
    for index, item in enumerate(items):
        if item.get("match_status") != MATCH_STATUS_AMBIGUOUS or item.get("price_line") is None:
            continue
        candidates = list(dict.fromkeys(item.get("match_candidates") or []))
        if len({work_of.get(c) for c in candidates} - {None}) < 2:
            continue
        result[index] = _decide_one(items, work_of, post_works, index, candidates)
    return result
