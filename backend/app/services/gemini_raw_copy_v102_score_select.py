"""試作版 v102：候補が複数残った件（ambiguous）で、「より詳しく当たった候補」を提案する。

PO 決定（2026-10-08）：選べた候補も商品は決めない。match_status は ambiguous・product_id は None のまま、
要確認（product_multiple）に提案（suggested_product_id）を添えて人が整備できるようにする。

規則（検証済みの試算 score-sim/v2 の S1・S4 と同じ）：
  S1：候補ごとに M（品番か記号が当たった＝1）、K（当たった検索ワードがある＝1）。点数 = M + K。最高点がちょうど1つならその候補。
  S4：S1 で決まらないとき、候補ごとの「当たった語の集合」（当たった検索ワードと当たった品番・記号を正規化したもの）を作る。
      候補 A の全語が候補 B のどれかの語の部分文字列なら「B は A を包む」。
      ほかの全候補を包み、自分は誰にも包まれない候補がちょうど1つならその候補。
  それ以外は決めない。
判定の言葉（商品名・作品名）は書かない。このモジュールは gemini_raw_copy_v101 から呼ばれる（v101 を import しない）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.extraction_judgement_svc import MatchResult, normalize_for_match

RULE_S1 = "S1"
RULE_S4 = "S4"
MATCH_STATUS_AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class CandidateScore:
    product_id: int
    m: int  # 品番か記号が当たった＝1
    k: int  # 当たった検索ワードがある＝1
    words: tuple[str, ...]  # 当たった語（正規化済み・並べ替え済み）

    @property
    def points(self) -> int:
        return self.m + self.k


@dataclass(frozen=True)
class ScoreDecision:
    rule: str
    product_id: int
    dropped: tuple[int, ...]
    scores: tuple[CandidateScore, ...]

    def as_dict(self) -> dict:
        """product_score 欄（根拠）。"""
        return {
            "rule": self.rule,
            "scores": {str(s.product_id): {"M": s.m, "K": s.k, "words": list(s.words)} for s in self.scores},
        }


def _score(product_id: int, match: MatchResult) -> CandidateScore:
    keywords = match.matched_keywords.get(product_id, ())
    code_values = match.code_hit_values.get(product_id, ()) if product_id in match.code_hits else ()
    words = {normalize_for_match(v) for v in (*keywords, *code_values)}
    words.discard("")
    return CandidateScore(
        product_id=product_id, m=1 if product_id in match.code_hits else 0, k=1 if keywords else 0,
        words=tuple(sorted(words)),
    )


def _covers(outer: CandidateScore, inner: CandidateScore) -> bool:
    """inner の全語が、outer のどれかの語の部分文字列。"""
    return all(any(w in o for o in outer.words) for w in inner.words)


def _only(items: Sequence[CandidateScore]) -> CandidateScore | None:
    return items[0] if len(items) == 1 else None


def _by_s1(scores: Sequence[CandidateScore]) -> CandidateScore | None:
    top = max(s.points for s in scores)
    return _only([s for s in scores if s.points == top])


def _by_s4(scores: Sequence[CandidateScore]) -> CandidateScore | None:
    winners = [
        s for s in scores
        if all(_covers(s, o) and not _covers(o, s) for o in scores if o is not s)
    ]
    return _only(winners)


def decide_by_score(match: MatchResult, product_entries: Sequence[object] | None = None) -> ScoreDecision | None:
    """ambiguous の照合結果に S1 → S4 を当てる。決まらなければ None。product_entries は将来の拡張用（今は使わない）。"""
    if match.status != MATCH_STATUS_AMBIGUOUS or len(match.candidates) < 2:
        return None
    scores = tuple(_score(c, match) for c in match.candidates)
    chosen, rule = _by_s1(scores), RULE_S1
    if chosen is None:
        chosen, rule = _by_s4(scores), RULE_S4
    if chosen is None:
        return None
    dropped = tuple(s.product_id for s in scores if s.product_id != chosen.product_id)
    return ScoreDecision(rule=rule, product_id=chosen.product_id, dropped=dropped, scores=scores)
