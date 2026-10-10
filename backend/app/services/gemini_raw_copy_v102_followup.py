"""試作版 v102：同じ仕入元が分けて送った投稿の商品を、直前の投稿で商品が決まった行から決める（純粋関数。DB を持たない）。

規則は docs/handoff/v102-followup-post-ref/design.md §2。
直前の投稿を読む処理（1時間以内・10行以下の条件）は line_analysis_v102_svc.load_followup_reference が持つ。
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.services.extraction_judgement_svc import _strict_code_pattern, fold_for_match, normalize_for_match
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters, match_text_g2

MATCH_STATUS_MATCHED_FOLLOWUP = "matched_followup"

_UNDECIDED_STATUSES = ("unmatched", "ambiguous")
_CODE_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_.'・][a-z0-9]+)*")
_NAME_TOKEN_RE = re.compile(r"[ァ-ヴー]{4,}|[一-龥々]{4,}|[A-Za-zＡ-Ｚａ-ｚ]{4,}")
_MIN_NAME_LEN = 4


@dataclass(frozen=True)
class RefLine:
    """直前の投稿の、商品が1つに決まった行。number は空行込みの行番号（1 始まり）。"""

    number: int
    folded: str
    normalized: str
    product_id: int


@dataclass(frozen=True)
class FollowupDecision:
    product_id: int
    ref_line: int
    tokens: tuple[str, ...]


def build_reference_lines(ref_text: str, masters: ProductFirstMasters) -> tuple[RefLine, ...]:
    """直前の投稿の各行のうち、v102 と同じ商品照合で商品が1つに決まる行。"""
    found: list[RefLine] = []
    for number, line in enumerate(ref_text.split("\n"), start=1):
        if not line.strip():
            continue
        match = match_text_g2(line, masters)
        if match.status == "matched" and match.product_id is not None:
            found.append(RefLine(number, fold_for_match(line), normalize_for_match(line), int(match.product_id)))
    return tuple(found)


def extract_tokens(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(型番の語, 名前の語)。型番は fold 後の語のうち厳格パターンになるもの、名前は normalize 後に4文字以上の語。"""
    codes = [w for w in _CODE_TOKEN_RE.findall(fold_for_match(text)) if _strict_code_pattern(w) is not None]
    names = [n for n in (normalize_for_match(w) for w in _NAME_TOKEN_RE.findall(text)) if len(n) >= _MIN_NAME_LEN]
    return tuple(dict.fromkeys(codes)), tuple(dict.fromkeys(names))


def unit_words(unit_alias_to_info: Mapping[str, Any]) -> frozenset[str]:
    """単位マスタ（load_lookup_maps の unit_alias_to_info）の別名・canonical を fold_for_match した集合。一覧は複製せず、渡されたものを使う。"""
    words = set()
    for alias, info in unit_alias_to_info.items():
        words.add(fold_for_match(str(alias)))
        words.add(fold_for_match(str(info[0])))
    return frozenset(w for w in words if w)


def _is_clue(word: str, units: frozenset[str]) -> bool:
    """規則7：数字だけの語・単位の語は手がかりにしない。"""
    folded = fold_for_match(word)
    return not folded.isdigit() and folded not in units


def _hits(codes: Sequence[str], names: Sequence[str], refs: Sequence[RefLine]) -> dict[int, list[tuple[int, str]]]:
    """商品 ID → [(参照行の番号, 当たった語)]。"""
    found: dict[int, list[tuple[int, str]]] = {}
    for ref in refs:
        for code in codes:
            pattern = _strict_code_pattern(code)
            if pattern is not None and pattern[1].search(ref.folded):
                found.setdefault(ref.product_id, []).append((ref.number, code))
        for name in names:
            if name in ref.normalized:
                found.setdefault(ref.product_id, []).append((ref.number, name))
    return found


def _decide_one(
    row: Mapping[str, Any], lines: Sequence[str], refs: Sequence[RefLine], units: frozenset[str], plural_words: Sequence[str],
) -> FollowupDecision | None:
    text = "\n".join(lines[n - 1] for n in row.get("lines", []) if 1 <= n <= len(lines))
    folded_text = unicodedata.normalize("NFKC", text)
    if any(w and unicodedata.normalize("NFKC", w) in folded_text for w in plural_words):
        return None  # 規則9：複数を指す言葉
    codes, names = extract_tokens(text)
    codes = tuple(w for w in codes if _is_clue(w, units))
    names = tuple(n for n in names if _is_clue(n, units))
    if not codes and not names:
        return None  # 規則7：残った語が0
    hits = _hits(codes, names, refs)
    if len(hits) != 1:
        return None
    (product_id, evidence), = hits.items()
    if {t for _, t in evidence} != {*codes, *names}:
        return None  # 規則8：直前の投稿の参照行に当たらない語がある
    if row.get("match_status") == "ambiguous" and product_id not in (row.get("match_candidates") or []):
        return None
    return FollowupDecision(
        product_id=product_id, ref_line=min(n for n, _ in evidence), tokens=tuple(dict.fromkeys(t for _, t in evidence)),
    )


def decide_followup(
    extracted: Sequence[Mapping[str, Any]], lines: Sequence[str], refs: Sequence[RefLine],
    *, units: frozenset[str] = frozenset(), plural_words: Sequence[str] = (),
) -> dict[int, FollowupDecision]:
    """unmatched / ambiguous の件のうち、直前の投稿の参照行で商品が1つに決まる件（添字 → 決定）。matched の件は触らない。"""
    if not refs:
        return {}
    decisions = {
        i: _decide_one(row, lines, refs, units, plural_words)
        for i, row in enumerate(extracted)
        if row.get("match_status") in _UNDECIDED_STATUSES and not row.get("rejected")
    }
    return {i: d for i, d in decisions.items() if d is not None}
