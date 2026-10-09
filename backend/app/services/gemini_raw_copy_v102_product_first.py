"""試作版 v102：商品を先に特定し、商品の分類をもとに「単位 → 状態 → 状態から単位」を決める流れ。

設計: docs/handoff/prototype-v102-product-first/design.md
判定の言葉（状態名・単位名・作品名）はここに書かない。マスタ（表）から読む。
区分の値（箱系・不明など）だけは、マスタの値を比べるため定数にまとめる（下の定数のコメントを参照）。
このモジュールは gemini_raw_copy_v101 から呼ばれる（v101 を import しない）。本番の解析（v6）・試運転は呼ばない。
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from dataclasses import replace as dataclass_replace
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.extraction_judgement_svc import (
    MatchResult,
    ProductEntry,
    _code_candidate_basis,
    _excluded_keywords,
    _keyword_matches,
    fold_for_match,
    match_product,
    normalize_for_match,
    product_match_text,
)
from app.services.extraction_shadow_svc import load_product_entries
from app.services.gemini_raw_copy_v102_score_select import ScoreDecision, decide_by_score
from app.services.tcg_analyzer_svc import (
    _entry_hit,
    app_kubun_matches,
    load_product_kubun_type_map,
    resolve_condition_v2,
    resolve_unit_v2,
)

logger = logging.getLogger(__name__)

# --- 区分の値（マスタの値。比較に使うので、ここ1か所にまとめる） -------------------------------
# public.tcg_product_categories.kubun_type（商品の分類）の値
PRODUCT_KUBUN_BOX = "箱系"
# 商品を特定できない・分類が無いときの、この道具の出力用の値（マスタの値ではない）
PRODUCT_KUBUN_UNKNOWN = "不明"
# public.line_units.kubun（単位の区分）の値。resolve_condition_v2 に渡す値と、resolve_unit_v2 が返す値
UNIT_KUBUN_BOX = "箱系"  # 商品が箱系のとき、状態の判定に渡す単位区分（tcg_analyzer_svc.py の R4c と同じ値）
UNIT_KUBUN_EMPTY = ""  # 単位が無い（resolve_unit_v2 の空）
UNIT_KUBUN_UNKNOWN = "不明"  # 単位の別名が未登録（resolve_unit_v2 の未知語）
UNIT_KUBUN_CONDITIONAL = "条件つき"
UNIT_KUBUN_COMPOUND = "複合"
UNIT_KUBUN_QUANTITY_ONLY = "数量専用"
# 商品が箱系のとき、単位の区分がこれなら単位では箱か決まらない（状態を箱系でやり直す）
BOX_RECHECK_UNIT_KUBUNS = frozenset({
    UNIT_KUBUN_EMPTY, UNIT_KUBUN_UNKNOWN, UNIT_KUBUN_CONDITIONAL, UNIT_KUBUN_COMPOUND, UNIT_KUBUN_QUANTITY_ONLY,
})
# 商品が不明のとき、単位の区分がこれなら「単位既定の落ち先」を要確認にする
UNKNOWN_PRODUCT_UNIT_KUBUNS = frozenset({UNIT_KUBUN_EMPTY, UNIT_KUBUN_UNKNOWN})
# 箱系の商品で、単位がこの区分なら単位を状態から決め直す（単位の候補が1つに決まらない区分）
UNIT_KUBUN_REPLACEABLE_FOR_BOX = UNIT_KUBUN_CONDITIONAL

# --- この道具が決める出力の言葉（マスタの値ではない） ------------------------------------------
NONE_VALUE = "none"
FLAG_SINGLE_CANONICAL = "FLAG_SINGLE"  # resolve_condition_v2 が返す単品の印（tcg_analyzer_svc.py の R4b）
CONDITION_UNKNOWN = "不明"
REVIEW_CONDITION_UNKNOWN = "condition_unknown"
REVIEW_MULTIPLE_CANDIDATES = "condition_multiple_candidates"
# 商品が決まらないときの要確認の理由（試運転 extraction_shadow_svc.py の要確認と同じ判定・同じ意味）
REVIEW_PRODUCT_NOT_IN_MASTER = "product_not_in_master"  # マスタに該当なし（unmatched）
REVIEW_PRODUCT_MULTIPLE = "product_multiple"  # 候補が2件以上（ambiguous）
BASIS_UNIT_UNKNOWN = "R4:単位既定:単位不明"  # resolve_condition_v2 の basis の一部（tcg_analyzer_svc.py の R4b）
REASON_KEYWORD_RANGE = "product_keyword_range"
REASON_IGNORE_PHRASE = "ignore_phrase"
REASON_COUNTER_OVERRIDDEN = "counter_overridden"  # 最初の「条件つき」の別名より、ほかの行の決まった単位を採った
# 区切りの判定で使う文字の種類。unicodedata の文字名の先頭の語で分ける（長音「ー」の名前は KATAKANA-HIRAGANA で始まるのでカタカナ）
SCRIPT_NAME_PREFIXES = ("LATIN", "HIRAGANA", "KATAKANA", "CJK")

_SYMBOL_ONLY_RE = re.compile(r"[\W_]+")
_LINE_ORDER_ROLES = ("stock", "name")  # 価格の行のあと、この順に見る（その他の行は最後）


@dataclass(frozen=True)
class ProductFirstMasters:
    """商品を先に決める流れに要るマスタ（読み取り専用）。"""

    product_entries: tuple[ProductEntry, ...]
    product_kubun: Mapping[str, str]  # 商品ID（文字列）→ 商品の分類（tcg_product_categories.kubun_type）
    condition_unit: Mapping[str, str]  # 状態の名前 → 対象の単位の名前（line_conditions.unit_id → line_units.canonical）
    ignore_phrases: tuple[str, ...]  # 単位にしない言い回し（有効なもの。空でもよい）
    # 形G2 の照合に使う索引（型番を外す前の商品と中分類の印）。None のときは product_entries から印なしで作る
    g2_index: G2Index | None = None


_CONDITION_UNIT_SQL = """
    SELECT c.canonical, u.canonical
    FROM public.line_conditions c
    JOIN public.line_units u ON u.id = c.unit_id
    WHERE c.is_active = TRUE AND u.is_active = TRUE
"""
_IGNORE_PHRASES_SQL = """
    SELECT phrase FROM public.line_unit_ignore_phrases WHERE is_active = TRUE ORDER BY id
"""


_NAME_ONLY_WORKS_SQL = "SELECT id FROM public.type_master WHERE match_by_code = FALSE"


def apply_name_only_works(entries: Sequence[ProductEntry], name_only_work_ids: frozenset[int]) -> tuple[ProductEntry, ...]:
    """型番で決めない中分類（印 match_by_code = FALSE）の商品から、品番・マーク・それと同じ検索ワードを外す（純粋関数）。

    同じ検索ワード：normalize_for_match した語全体が、有効な全商品（全作品）の品番またはマークの正規化値と一致する検索ワード。
    印のない中分類の商品・除外ワードは変えない。印の中分類が無ければ entries と同じ内容を返す。
    """
    if not name_only_work_ids:
        return tuple(entries)
    code_values = {
        normalize_for_match(raw) for e in entries for raw in (e.product_code, e.mark) if raw
    }
    code_values.discard("")
    return tuple(
        dataclass_replace(
            e, product_code=None, mark=None,
            search_keywords=tuple(k for k in e.search_keywords if normalize_for_match(k) not in code_values),
        ) if e.work_id in name_only_work_ids else e
        for e in entries
    )


_CODE_ONLY_OFF_WORKS_SQL = "SELECT id FROM public.type_master WHERE match_by_code = TRUE AND code_only_match = FALSE"


@dataclass(frozen=True)
class G2Index:
    """形G2 の照合に使う、商品と中分類の印（読み取り専用）。

    entries：型番を外す前の商品。name_only_work_ids：名前だけ（match_by_code = FALSE）の中分類。
    code_only_off_work_ids：型番は絞り込みだけ（match_by_code = TRUE かつ code_only_match = FALSE）の中分類。
    name_entries：全作品の型番・型番語を外した商品（名前の候補を作るため）。base_entries：名前だけの中分類の型番を外した商品
    （記録の欄を作るため。今の match_product の入力と同じ）。code_values：全商品の品番・マークの正規化値。
    """

    entries: tuple[ProductEntry, ...]
    name_only_work_ids: frozenset[int]
    code_only_off_work_ids: frozenset[int]
    name_entries: tuple[ProductEntry, ...]
    base_entries: tuple[ProductEntry, ...]
    code_values: frozenset[str]


def build_g2_index(
    entries: Sequence[ProductEntry], name_only_work_ids: frozenset[int], code_only_off_work_ids: frozenset[int],
) -> G2Index:
    """G2Index を作る（純粋関数）。作品のない商品は、型番語を外す対象に含めない。"""
    all_work_ids = frozenset(e.work_id for e in entries if e.work_id is not None)
    code_values = {normalize_for_match(raw) for e in entries for raw in (e.product_code, e.mark) if raw}
    code_values.discard("")
    return G2Index(
        entries=tuple(entries),
        name_only_work_ids=name_only_work_ids,
        code_only_off_work_ids=code_only_off_work_ids,
        name_entries=apply_name_only_works(entries, all_work_ids),
        base_entries=apply_name_only_works(entries, name_only_work_ids),
        code_values=frozenset(code_values),
    )


@dataclass(frozen=True)
class _G2Hit:
    name_hit: bool  # 型番語を除いた検索ワードに当たった
    code_hit: bool  # 品番・マーク、または型番語の検索ワードに当たった（名前だけの中分類は常に False）
    any_hit: bool  # 品番・マーク・検索ワードのどれかに当たった
    excluded: bool  # 除外ワードに当たった


def _g2_hits(block: str, index: G2Index) -> dict[int, _G2Hit]:
    """商品ごとの当たり方（当たり方・除外ワードの当たり方は match_product と同じ関数）。どれかに当たった商品だけ返す。"""
    nb = normalize_for_match(block)
    folded = fold_for_match(block)
    hits: dict[int, _G2Hit] = {}
    for entry, name_entry in zip(index.entries, index.name_entries, strict=True):
        name_hit = bool(_keyword_matches(name_entry, nb, folded, True))
        basis = _code_candidate_basis(entry, nb, folded, True) is not None
        keywords = _keyword_matches(entry, nb, folded, True)
        if not (basis or keywords or name_hit):
            continue
        code_keyword = any(normalize_for_match(k) in index.code_values for k in keywords)
        hits[entry.id] = _G2Hit(
            name_hit=name_hit,
            code_hit=False if entry.work_id in index.name_only_work_ids else (basis or code_keyword),
            any_hit=basis or bool(keywords),
            excluded=bool(_excluded_keywords(entry, nb, folded, True)),
        )
    return hits


def _g2_candidates(hits: Mapping[int, _G2Hit], index: G2Index) -> tuple[int, ...]:
    """形G2 の候補。名前の候補があればそれ（2つ以上なら型番が当たったものに絞る）。無ければ、型番だけでも決めてよい作品の商品。"""
    work_of = {e.id: e.work_id for e in index.entries}
    names = sorted(pid for pid, h in hits.items() if h.name_hit and not h.excluded)
    if names:
        narrowed = [pid for pid in names if hits[pid].code_hit] if len(names) >= 2 else []
        return tuple(narrowed or names)
    no_code_only = index.name_only_work_ids | index.code_only_off_work_ids
    return tuple(sorted(
        pid for pid, h in hits.items() if h.any_hit and not h.excluded and work_of[pid] not in no_code_only
    ))


def match_product_g2(block: str, index: G2Index) -> MatchResult:
    """試作版 v102 の商品照合（形G2）。候補の数で matched / ambiguous / unmatched。記録の欄は match_product と同じ形。

    名前の候補 N：型番語を除いた検索ワードに当たり、除外ワードに当たらない商品（全作品）。
    N が2つ以上：型番が当たった商品に絞る（当たり0なら N のまま。名前だけの中分類は型番を持たない扱い）。N が1つ：その商品。
    N が0：型番だけでも決めてよい中分類の商品で、型番が当たり除外ワードに当たらないもの。
    """
    candidates = _g2_candidates(_g2_hits(block, index), index)
    base = match_product(block, index.base_entries, strict_codes=True)
    if not candidates:
        return dataclass_replace(
            base, status="unmatched", product_id=None, work_id=None, candidates=(), basis="",
            reason="一致する検索ワード・品番がない",
        )
    if len(candidates) >= 2:
        return dataclass_replace(
            base, status="ambiguous", product_id=None, work_id=None, candidates=candidates, basis="",
            reason=f"候補{len(candidates)}件：{'/'.join(str(c) for c in candidates)}",
        )
    product_id = candidates[0]
    keywords = base.matched_keywords.get(product_id, ())
    basis = "RAWCODE" if product_id in base.code_hit_values else f"SK:{keywords[0] if keywords else ''}"
    work_id = next(e.work_id for e in index.entries if e.id == product_id)
    return dataclass_replace(
        base, status="matched", product_id=product_id, work_id=work_id, candidates=candidates, basis=basis, reason="",
    )


def load_product_first_masters(session: Session) -> ProductFirstMasters:
    """商品・商品の分類・状態ごとの単位・単位にしない言い回しを読む（読み取りのみ）。商品・分類・状態の単位が空なら止める。

    商品は、型番で決めない中分類（type_master.match_by_code = FALSE）の分だけ、品番・マーク・型番と同じ検索ワードを外す。
    型番は絞り込みだけの中分類（match_by_code = TRUE かつ code_only_match = FALSE）の id も読み、形G2 の照合に渡す。
    """
    name_only = frozenset(int(r[0]) for r in session.execute(text(_NAME_ONLY_WORKS_SQL)).fetchall())
    code_only_off = frozenset(int(r[0]) for r in session.execute(text(_CODE_ONLY_OFF_WORKS_SQL)).fetchall())
    source_entries = tuple(load_product_entries(session))
    entries = apply_name_only_works(source_entries, name_only)
    kubun_map = dict(load_product_kubun_type_map(session))
    cond_unit = {str(r[0]): str(r[1]) for r in session.execute(text(_CONDITION_UNIT_SQL)).fetchall()}
    phrases = tuple(str(r[0]) for r in session.execute(text(_IGNORE_PHRASES_SQL)).fetchall() if r[0])
    g2_index = build_g2_index(source_entries, name_only, code_only_off)
    masters = ProductFirstMasters(entries, kubun_map, cond_unit, phrases, g2_index)
    check_product_first_masters(masters)
    return masters


def check_product_first_masters(masters: ProductFirstMasters) -> None:
    """空のマスタで黙って続けない。単位にしない言い回しだけは、まだ登録が無くてもよい。"""
    empty = [
        name for name, value in (
            ("商品", masters.product_entries), ("商品の分類", masters.product_kubun), ("状態ごとの単位", masters.condition_unit),
        ) if not value
    ]
    if empty:
        raise ValueError(f"マスタが空です: {', '.join(empty)}")


# ---------------------------------------------------------------------------
# 単位の別名を探す
# ---------------------------------------------------------------------------


def _low(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").lower()


def _is_letter(ch: str) -> bool:
    return unicodedata.category(ch).startswith("L")  # 英字・かな・カナ・漢字・長音。数字・記号・空白は含まない


def _script(ch: str) -> str | None:
    """文字の種類（SCRIPT_NAME_PREFIXES のどれか）。数字・記号・空白・上記以外の文字は None。"""
    if not _is_letter(ch):
        return None
    name = unicodedata.name(ch, "")
    return next((prefix for prefix in SCRIPT_NAME_PREFIXES if name.startswith(prefix)), None)


def _edge_blocks(neighbor: str, edge: str) -> bool:
    """別名の端の文字（edge）の隣（neighbor）が、同じ種類の文字（または種類を決められない文字）なら True＝採らない。"""
    if not neighbor or not _is_letter(neighbor):
        return False
    neighbor_script, edge_script = _script(neighbor), _script(edge)
    return neighbor_script is None or edge_script is None or neighbor_script == edge_script


def _boundary_ok(norm: str, start: int, end: int) -> bool:
    before = norm[start - 1] if start > 0 else ""
    after = norm[end] if end < len(norm) else ""
    return not _edge_blocks(before, norm[start]) and not _edge_blocks(after, norm[end - 1])


def boundary_candidates(line: str, aliases: Sequence[str]) -> list[tuple[int, int, str, str]]:
    """区切りの照合。別名の前後が 行の端・空白・記号・数字 のものを (開始, 終了, 別名, 正規化した行) で返す。先頭に近い順・長い順。"""
    norm = _low(line)
    whole = _SYMBOL_ONLY_RE.sub("", norm)
    found: list[tuple[int, int, str, str]] = []
    for alias in aliases:
        alias_norm = _low(alias)
        if whole and whole == _SYMBOL_ONLY_RE.sub("", alias_norm):
            found.append((0, len(alias_norm), alias, norm))
            continue
        for m in re.finditer(re.escape(alias_norm), norm):
            if _boundary_ok(norm, m.start(), m.end()):
                found.append((m.start(), m.end(), alias, norm))
    found.sort(key=lambda c: (c[0], -(c[1] - c[0]), c[2]))
    return found


def _ranges(norm: str, patterns: Sequence[re.Pattern[str]]) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for p in patterns for m in p.finditer(norm)]


def _inside(ranges: Sequence[tuple[int, int]], start: int, end: int) -> bool:
    return any(rs <= start and end <= re_ for rs, re_ in ranges)


def _keyword_patterns(match: MatchResult) -> list[re.Pattern[str]]:
    """照合で当たった商品の検索ワードを、空白で分けた語ごとの正規表現にする。"""
    words = [_low(w) for kws in match.matched_keywords.values() for kw in kws for w in kw.split(" ") if w]
    return [re.compile(re.escape(w)) for w in words if w]


def _phrase_patterns(phrases: Sequence[str]) -> list[re.Pattern[str]]:
    """単位にしない言い回しを、正規化して、空白は0個以上を許す正規表現にする。"""
    patterns = []
    for phrase in phrases:
        tokens = [re.escape(t) for t in _low(phrase).split() if t]
        if tokens:
            patterns.append(re.compile(r"\s*".join(tokens)))
    return patterns


def line_search_order(item: Mapping[str, Any], roles: Mapping[int, str]) -> list[int]:
    """価格の行 → 在庫の行 → 名前の行 → その他の行、の順に行番号を並べる（重複なし）。"""
    price_line = item["price_line"]
    rest = [n for n in item["lines"] if n != price_line]
    order = [price_line]
    for role in _LINE_ORDER_ROLES:
        order += [n for n in rest if roles.get(n) == role]
    order += [n for n in rest if roles.get(n) not in _LINE_ORDER_ROLES]
    return list(dict.fromkeys(order))


def _find_in_line(
    n: int, item: Mapping[str, Any], roles: Mapping[int, str], lines: Sequence[str], aliases: Sequence[str],
    patterns: tuple[list[re.Pattern[str]], list[re.Pattern[str]]], find_price_alias: Callable[[str], str | None],
    excluded: list[dict],
) -> tuple[str, dict] | None:
    """1行から単位の別名を探す。見つかれば (別名, unit_basis)。除外した別名は excluded に足す。"""
    keyword_patterns, phrase_patterns = patterns
    line = lines[n - 1]
    role = roles.get(n, "")
    if n == item["price_line"]:
        alias = find_price_alias(line)
        if alias is not None:
            return alias, {"line": n, "role": role, "match": "position", "alias": alias, "excluded": excluded}
    for start, end, alias, norm in boundary_candidates(line, aliases):
        reason = None
        if _inside(_ranges(norm, keyword_patterns), start, end):
            reason = REASON_KEYWORD_RANGE
        elif _inside(_ranges(norm, phrase_patterns), start, end):
            reason = REASON_IGNORE_PHRASE
        if reason:
            excluded.append({"line": n, "role": role, "alias": alias, "reason": reason})
            continue
        return alias, {"line": n, "role": role, "match": "boundary", "alias": alias, "excluded": excluded}
    return None


def find_unit_product_first(
    item: Mapping[str, Any], roles: Mapping[int, str], lines: Sequence[str], aliases: Sequence[str],
    match: MatchResult, phrases: Sequence[str], find_price_alias: Callable[[str], str | None],
    unit_alias_to_info: Mapping[str, Any],
) -> tuple[str | None, dict]:
    """単位の別名を探す。戻り値は (別名, unit_basis)。最初に見つかったものを採る。

    価格の行は今の位置の条件（find_price_alias）を先に使い、見つからなければ区切りの照合。ほかの行は区切りの照合。
    区切りの照合で当たった別名は、照合で当たった商品の検索ワードの語の中、または単位にしない言い回しの中なら採らない。
    最初に見つかった別名の単位区分が「条件つき」のときだけ、残りの行も探し続け、「条件つき」以外の単位が
    見つかればそちらを採る（見つからなければ最初の「条件つき」を採る）。
    """
    patterns = (_keyword_patterns(match), _phrase_patterns(phrases))
    excluded: list[dict] = []
    first: tuple[str, dict] | None = None
    for n in line_search_order(item, roles):
        found = _find_in_line(n, item, roles, lines, aliases, patterns, find_price_alias, excluded)
        if found is None:
            continue
        if first is None:
            if resolve_unit_v2(found[0], unit_alias_to_info)[1] != UNIT_KUBUN_REPLACEABLE_FOR_BOX:
                return found
            first = found
        elif resolve_unit_v2(found[0], unit_alias_to_info)[1] != UNIT_KUBUN_REPLACEABLE_FOR_BOX:
            return found[0], {**found[1], "overridden_alias": first[0], "override_reason": REASON_COUNTER_OVERRIDDEN}
    if first is not None:
        return first
    return None, {"line": None, "role": "", "match": "", "alias": None, "excluded": excluded}


# ---------------------------------------------------------------------------
# 商品 → 単位 → 状態 → 状態から単位
# ---------------------------------------------------------------------------


def _match_summary(match: MatchResult, masters: ProductFirstMasters) -> tuple[int | None, str]:
    """(商品ID, 商品の分類)。特定できない・分類が無いときは分類を「不明」にする。"""
    if match.status != "matched" or match.product_id is None:
        return None, PRODUCT_KUBUN_UNKNOWN
    return match.product_id, masters.product_kubun.get(str(match.product_id)) or PRODUCT_KUBUN_UNKNOWN


def _product_reviews(match: MatchResult, score: ScoreDecision | None = None) -> list[dict]:
    """商品が決まらないときの要確認の理由の一覧（状態・単位・商品の値は変えない）。

    境界で他の候補が消えて決まったとき（boundary_dropped）は要確認にしない。控えは match_boundary_dropped に残る。
    """
    if match.status == "unmatched":
        return [{"kind": REVIEW_PRODUCT_NOT_IN_MASTER}]
    if match.status == "ambiguous":
        suggestion = (
            {"suggested_product_id": score.product_id, "suggest_rule": score.rule, "suggest_dropped": list(score.dropped)}
            if score is not None else {}
        )
        return [{"kind": REVIEW_PRODUCT_MULTIPLE, "candidates": list(match.candidates), **suggestion}]
    return []


def _resolve_condition(
    block: str, product_kubun: str, unit_kubun: str, cond_entries: list[dict], cond_canonical_to_uuid: dict,
) -> tuple[str | None, str, list[dict]]:
    """(状態, basis, 要確認の理由の一覧 [{"kind": ..., ...}])。"""
    if product_kubun == PRODUCT_KUBUN_BOX and unit_kubun in BOX_RECHECK_UNIT_KUBUNS:
        cond, _cid, basis = resolve_condition_v2(block, "", UNIT_KUBUN_BOX, cond_entries, cond_canonical_to_uuid, raw_memo=block)
        codes = _other_kubun_hits(block, UNIT_KUBUN_BOX, cond_entries)
        reviews = [{"kind": REVIEW_MULTIPLE_CANDIDATES, "codes": codes}] if codes else []
        return cond, basis, reviews
    cond, _cid, basis = resolve_condition_v2(block, "", unit_kubun, cond_entries, cond_canonical_to_uuid, raw_memo=block)
    if product_kubun == PRODUCT_KUBUN_UNKNOWN and unit_kubun in UNKNOWN_PRODUCT_UNIT_KUBUNS \
            and cond == FLAG_SINGLE_CANONICAL and BASIS_UNIT_UNKNOWN in basis:
        return CONDITION_UNKNOWN, basis, [{"kind": REVIEW_CONDITION_UNKNOWN}]
    return cond, basis, []


def _other_kubun_hits(block: str, supplied_kubun: str, cond_entries: Sequence[dict]) -> list[str]:
    """補った区分と適用区分が違う状態の行のうち、文字に当たる行の code。

    適用区分が空の行（どの区分にも当てはまる）と、単品の行（FLAG_SINGLE）は対象にしない。
    """
    text_combined = f"{block} "
    return [
        e["code"] for e in cond_entries
        if (e.get("app_kubun") or "").strip()
        and e.get("canonical") != FLAG_SINGLE_CANONICAL
        and not app_kubun_matches(e["app_kubun"], supplied_kubun)
        and _entry_hit(e, text_combined)[0]
    ]


def _fixed_match(match: MatchResult, fixed_product_id: int | None, masters: ProductFirstMasters) -> MatchResult | None:
    """人が決めた商品で matched にした照合結果。指定なし・商品が有効な商品の一覧に無いときは None（固定しない）。"""
    if fixed_product_id is None:
        return None
    work_of = {p.id: p.work_id for p in masters.product_entries}
    if fixed_product_id not in work_of:
        logger.warning("[product_first] 固定の商品 id=%s が有効な商品の一覧に無いため固定しません", fixed_product_id)
        return None
    return dataclass_replace(
        match, status="matched", product_id=fixed_product_id, work_id=work_of[fixed_product_id],
        candidates=(fixed_product_id,), boundary_dropped=(),
    )


def resolve_product_first(
    *, item: Mapping[str, Any], roles: Mapping[int, str], lines: Sequence[str], block: str, name: str,
    aliases: Sequence[str], unit_alias_to_info: dict, cond_entries: list[dict], cond_canonical_to_uuid: dict,
    masters: ProductFirstMasters, find_price_alias: Callable[[str], str | None], chosen_product_id: int | None = None,
    fixed_product_id: int | None = None,
) -> dict:
    """1件の商品・単位・状態を、商品を先に決める流れで出す。

    chosen_product_id：商品が ambiguous で、その候補に含まれるときだけ、その商品に決めた扱いにする（前後の商品の作品で決めた結果）。
    それ以外のときは無視する。
    fixed_product_id：人が決めた商品。指定時は照合の結果に関わらずその商品で matched にする（chosen_product_id より優先）。
    商品が有効な商品の一覧に無ければ固定しない。None のときの結果は変わらない。
    """
    match_text, _source = product_match_text(block, "", name)
    g2_index = masters.g2_index or build_g2_index(masters.product_entries, frozenset(), frozenset())
    match = match_product_g2(match_text, g2_index)
    fixed_match = _fixed_match(match, fixed_product_id, masters)
    if fixed_match is not None:
        match = fixed_match
    elif match.status == "ambiguous" and chosen_product_id is not None and chosen_product_id in match.candidates:
        work_of = {p.id: p.work_id for p in masters.product_entries}
        match = dataclass_replace(match, status="matched", product_id=chosen_product_id, work_id=work_of.get(chosen_product_id))
    score = decide_by_score(match, masters.product_entries)
    product_id, product_kubun = _match_summary(match, masters)
    alias, unit_basis = find_unit_product_first(
        item, roles, lines, aliases, match, masters.ignore_phrases, find_price_alias, unit_alias_to_info
    )
    unit, unit_kubun, _resolved = resolve_unit_v2(alias or "", unit_alias_to_info)
    condition, basis, reviews = _resolve_condition(block, product_kubun, unit_kubun, cond_entries, cond_canonical_to_uuid)
    replace = unit is None or (product_kubun == PRODUCT_KUBUN_BOX and unit_kubun == UNIT_KUBUN_REPLACEABLE_FOR_BOX)
    from_condition = masters.condition_unit.get(condition or "") if replace else None
    if from_condition:
        unit, unit_kubun, _resolved = resolve_unit_v2(from_condition, unit_alias_to_info)
        unit_basis = {**unit_basis, "from_condition": condition}
    return {
        "product_id": product_id, "product_category": product_kubun, "match_status": match.status,
        "match_candidates": list(match.candidates),
        "match_boundary_dropped": list(match.boundary_dropped),
        "unit": unit or NONE_VALUE, "unit_kubun": unit_kubun, "unit_basis": unit_basis,
        "condition": condition or NONE_VALUE, "condition_basis": basis,
        "review_extra": [*_product_reviews(match, score), *reviews],
        "score_decision": score,
    }
