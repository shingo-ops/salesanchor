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
from dataclasses import dataclass, field
from dataclasses import replace as dataclass_replace
from datetime import date
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
from app.services.gemini_raw_copy_v102_score_select import ScoreDecision, decide_by_score
from app.services.tcg_analyzer_svc import (
    SCOPED_VALUE_GROUPS,
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
PRODUCT_KUBUN_BULK = "バルク系"  # 状態語が無いとき、状態を Bulk（配信可）にする（ADR-1021）
PRODUCT_KUBUN_SINGLE = "シングル系"  # 状態を single 群の行（PSA10 等）で判定し、語が無ければ Single にする（ADR-1031）
PRODUCT_KUBUN_PROMO_PACK = "プロモパック系"  # 状態を promo_pack 群の行で判定し、語が無ければ 未開封 にする（ADR-1031）
PRODUCT_KUBUN_SET = "セット系"  # 単位の語が無ければ単位を Set にし、状態は箱系と同じく既定で Sealed box にする
PRODUCT_KUBUN_SUPPLY = "サプライ系"  # 状態を supply 群の行で判定し、語が無ければ Supply にする。単位は状態の単位（Bag）にそろえる（ADR-1035 追補）
PRODUCT_KUBUN_BOOKLET = "ブックレット系"  # 状態を booklet 群の行で判定し、語が無ければ With booklet にする（ADR-1035）
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
# 箱系の商品で、単位がこの区分なら単位を状態から決め直す（単位の候補が1つに決まらない区分）
UNIT_KUBUN_REPLACEABLE_FOR_BOX = UNIT_KUBUN_CONDITIONAL
# 状態の既定を箱系でやり直す商品の分類（単位が決め手にならないとき、語が無ければ Sealed box になる）
PRODUCT_KUBUNS_DEFAULTING_TO_BOX = frozenset({PRODUCT_KUBUN_BOX, PRODUCT_KUBUN_SET})

# 単位 Set の行の code（public.line_units.code。名前は masters から code で引く）
UNIT_SET_CODE = "UN0005"
# 状態が原文の語で決まったことを示す basis の接頭辞（tcg_analyzer_svc.resolve_condition_v2 の R1〜R3）。R4 以降は既定
_STATE_WORD_BASIS_RE = re.compile(r"^R[123]:")
UNIT_BASIS_STATE_WORD = "state_word"  # unit_basis の from_condition に添える理由
UNIT_BASIS_FROM_CATEGORY = "from_category"  # 分類から単位を決めたときの unit_basis のキー

# --- この道具が決める出力の言葉（マスタの値ではない） ------------------------------------------
NONE_VALUE = "none"
FLAG_SINGLE_CANONICAL = "FLAG_SINGLE"  # resolve_condition_v2 が返す単品の印（tcg_analyzer_svc.py の R4b）
CONDITION_UNKNOWN = "不明"
# 状態を決められなかった件に付ける状態「Error」の code（名前は masters から code で引く。effect='EXCLUDE' = 配信しない）
CONDITION_ERROR_CODE = "CN0012"
# バルク系で状態語が無いときの状態「Bulk」の code（名前は masters から code で引く。effect='OUTPUT' = 配信する）
CONDITION_BULK_CODE = "CN0014"
VALUE_GROUP_SINGLE = "single"
VALUE_GROUP_PROMO_PACK = "promo_pack"
VALUE_GROUP_BOOKLET = "booklet"
VALUE_GROUP_SUPPLY = "supply"
CONDITION_SINGLE_DEFAULT = "Single"  # シングル系で状態語が無いときの状態名（single 群の行。search_kw 空）
CONDITION_PROMO_PACK_DEFAULT = "未開封"  # プロモパック系で状態語が無いときの状態名（promo_pack 群の行。search_kw 空）
CONDITION_BOOKLET_DEFAULT = "With booklet"  # ブックレット系で状態語が無いときの状態名（booklet 群の行。search_kw 空）
CONDITION_SUPPLY_DEFAULT = "Supply"  # サプライ系で状態語が無いときの状態名（supply 群の行。search_kw 空）
BASIS_SINGLE_DEFAULT = "R7:単品既定"  # R4 で始めない（買取換算の候補に入れないため。BASIS_BULK_DEFAULT と同じ扱い）
BASIS_PROMO_PACK_DEFAULT = "R8:プロモパック既定"
BASIS_BOOKLET_DEFAULT = "R9:ブックレット既定"  # R4 で始めない（R6〜R8 と同じ扱い）
BASIS_SUPPLY_DEFAULT = "R10:サプライ既定"  # R4 で始めない（ADR-1021）
BASIS_BULK_DEFAULT = "R6:バルク既定"  # R4 で始めない（買取換算の候補に入れないため。v102_buyback_unit_svc.is_candidate）
REVIEW_CONDITION_UNKNOWN = "condition_unknown"
REVIEW_MULTIPLE_CANDIDATES = "condition_multiple_candidates"
# 商品が決まらないときの要確認の理由（旧試運転の要確認と同じ判定・同じ意味）
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
class WorkName:
    """有効な中分類（type_master）の名前（name_ja・name_en。空は除く）。〆の件の作品名の判定に使う（soldout_ref が import する側）。"""

    work_id: int
    names: tuple[str, ...]


@dataclass(frozen=True)
class ProductFirstMasters:
    """商品を先に決める流れに要るマスタ（読み取り専用）。"""

    product_entries: tuple[ProductEntry, ...]
    product_kubun: Mapping[str, str]  # 商品ID（文字列）→ 商品の分類（tcg_product_categories.kubun_type）
    condition_unit: Mapping[str, str]  # 状態の名前 → 対象の単位の名前（line_conditions.unit_id → line_units.canonical）
    ignore_phrases: tuple[str, ...]  # 単位にしない言い回し（有効なもの。空でもよい）
    # 形G2 の照合に使う索引（型番を外す前の商品と中分類の印）。None のときは product_entries から印なしで作る
    g2_index: G2Index | None = None
    # 直前の投稿から商品を決めない言葉（複数を指す言葉）。knowledge_rules の category=followup_plural_word。空なら働かない
    followup_plural_words: tuple[str, ...] = ()
    # 〆の件の作品名の判定に使う有効な中分類の名前（type_master is_active = TRUE）。空なら作品名の〆は働かない
    work_names: tuple[WorkName, ...] = ()
    # 単位 Set の名前（line_units.code = UNIT_SET_CODE の canonical）。None なら分類「セット系」の単位決めは働かない
    set_unit: str | None = None
    # 商品ID（文字列）→ 発売日（products.release_date。NULL は入れない）。予約の手がかり（便PO）が使う。空なら発売日の規則は働かない
    product_release: Mapping[str, date] = field(default_factory=dict)
    # 今の投稿の投稿日（line_posted_at の JST の日付）。run_v102_analysis が job ごとに足す。None なら日付の規則は働かない
    posted_date: date | None = None
    # ADR-1031：value_group が single / promo_pack の状態の行（群名 → 行）。通常の cond_entries には入れない。空なら働かない
    scoped_cond_entries: Mapping[str, tuple[dict, ...]] = field(default_factory=dict)


_RELEASE_DATE_SQL = """
    SELECT id, release_date FROM public.products WHERE is_active = TRUE AND release_date IS NOT NULL
"""
_CONDITION_UNIT_SQL = """
    SELECT c.canonical, u.canonical
    FROM public.line_conditions c
    JOIN public.line_units u ON u.id = c.unit_id
    WHERE c.is_active = TRUE AND u.is_active = TRUE
"""
_SET_UNIT_SQL = "SELECT canonical FROM public.line_units WHERE code = :code AND is_active = TRUE"
_IGNORE_PHRASES_SQL = """
    SELECT phrase FROM public.line_unit_ignore_phrases WHERE is_active = TRUE ORDER BY id
"""


_FOLLOWUP_PLURAL_WORDS_SQL = """
    SELECT pattern FROM public.knowledge_rules
    WHERE category = 'followup_plural_word' AND pattern_type = 'substring' AND is_active = TRUE
    ORDER BY priority, id
"""
_WORK_NAMES_SQL = """
    SELECT id, name_ja, name_en FROM public.type_master WHERE is_active = TRUE ORDER BY id
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
    # 状態マスタ（public.conditions）の合図の語（正規化済み）。除外ワードの一致が、これより長い合図の語に収まるときは無視する。空なら従来どおり
    cond_terms: tuple[str, ...] = ()


def with_cond_terms(masters: ProductFirstMasters, cond_terms: tuple[str, ...]) -> ProductFirstMasters:
    """masters の形G2 の索引に合図の語を持たせた複製を返す（元は変えない）。cond_terms が空なら masters をそのまま返す。"""
    if not cond_terms:
        return masters
    index = masters.g2_index or build_g2_index(masters.product_entries, frozenset(), frozenset())
    return dataclass_replace(masters, g2_index=dataclass_replace(index, cond_terms=cond_terms))


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
            excluded=bool(_excluded_keywords(entry, nb, folded, True, index.cond_terms)),
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
    base = match_product(block, index.base_entries, strict_codes=True, cond_terms=index.cond_terms)
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


def match_text_g2(match_text: str, masters: ProductFirstMasters):
    """照合文を形G2 で照合する（resolve_product_first と直前の投稿の参照行の作成が同じ部品を使う）。"""
    g2_index = masters.g2_index or build_g2_index(masters.product_entries, frozenset(), frozenset())
    return match_product_g2(match_text, g2_index)


def _load_work_names(session: Session) -> tuple[WorkName, ...]:
    """有効な中分類の名前。name_ja・name_en が NULL・空なら除き、名前が1つも無い中分類は入れない。"""
    found = []
    for work_id, name_ja, name_en in session.execute(text(_WORK_NAMES_SQL)).fetchall():
        names = tuple(str(n) for n in (name_ja, name_en) if n and str(n).strip())
        if names:
            found.append(WorkName(int(work_id), names))
    return tuple(found)


def load_product_entries(session: Session) -> list[ProductEntry]:
    """判定用の商品リストを読む（public.products の有効な全件）。

    design.md §4-1: 対象は public.products の有効な全件（解析用の別マスタは作らない）。
    """
    rows = session.execute(
        text(
            """
            SELECT p.id, p.product_code, p.mark, p.work_id,
                   (SELECT COALESCE(array_agg(k.keyword ORDER BY k.position, k.keyword), ARRAY[]::text[])
                    FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_keywords,
                   (SELECT COALESCE(array_agg(k.keyword ORDER BY k.position, k.keyword), ARRAY[]::text[])
                    FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_keywords
            FROM public.products p
            WHERE p.is_active = TRUE
            """
        )
    ).fetchall()
    return [
        ProductEntry(
            id=int(r[0]),
            product_code=r[1],
            mark=r[2],
            work_id=int(r[3]) if r[3] is not None else None,
            search_keywords=tuple(r[4] or ()),
            exclude_keywords=tuple(r[5] or ()),
        )
        for r in rows
    ]


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
    plural_words = tuple(str(r[0]) for r in session.execute(text(_FOLLOWUP_PLURAL_WORDS_SQL)).fetchall() if r[0])
    work_names = _load_work_names(session)
    set_rows = session.execute(text(_SET_UNIT_SQL), {"code": UNIT_SET_CODE}).fetchall()
    set_unit = str(set_rows[0][0]) if set_rows and set_rows[0][0] else None
    release = {str(r[0]): r[1] for r in session.execute(text(_RELEASE_DATE_SQL)).fetchall()}
    masters = ProductFirstMasters(
        entries, kubun_map, cond_unit, phrases, g2_index, plural_words, work_names, set_unit, product_release=release
    )
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


def _error_condition(cond_entries: list[dict]) -> str | None:
    """状態「Error」の名前（masters の code で引く）。行が無ければ None。"""
    return next((e["canonical"] for e in cond_entries if e["code"] == CONDITION_ERROR_CODE), None)


def _bulk_condition(cond_entries: list[dict]) -> str | None:
    """状態「Bulk」の名前（masters の code で引く）。行が無ければ None。"""
    return next((e["canonical"] for e in cond_entries if e["code"] == CONDITION_BULK_CODE), None)


def _undecided_condition(cond: str | None, basis: str, cond_entries: list[dict]) -> tuple[str | None, list[dict]]:
    """最終フォールバック（FLAG_SINGLE かつ basis が単位不明）なら状態を Error にして理由 condition_unknown を付ける。

    語で決まった FLAG_SINGLE（basis R1:…）は対象外。Error の行が masters に無いときは「不明」（安全側）。
    """
    if cond != FLAG_SINGLE_CANONICAL or BASIS_UNIT_UNKNOWN not in basis:
        return cond, []
    return (_error_condition(cond_entries) or CONDITION_UNKNOWN), [{"kind": REVIEW_CONDITION_UNKNOWN}]


_KUBUN_TO_VALUE_GROUP = {
    PRODUCT_KUBUN_SINGLE: (VALUE_GROUP_SINGLE, CONDITION_SINGLE_DEFAULT, BASIS_SINGLE_DEFAULT),
    PRODUCT_KUBUN_PROMO_PACK: (VALUE_GROUP_PROMO_PACK, CONDITION_PROMO_PACK_DEFAULT, BASIS_PROMO_PACK_DEFAULT),
    PRODUCT_KUBUN_BOOKLET: (VALUE_GROUP_BOOKLET, CONDITION_BOOKLET_DEFAULT, BASIS_BOOKLET_DEFAULT),
    PRODUCT_KUBUN_SUPPLY: (VALUE_GROUP_SUPPLY, CONDITION_SUPPLY_DEFAULT, BASIS_SUPPLY_DEFAULT),
}


def _resolve_scoped_condition(
    block: str, product_kubun: str, group_entries: Sequence[dict], cond_canonical_to_uuid: dict,
) -> tuple[str | None, str, list[dict]]:
    """シングル系・プロモパック系の状態（ADR-1031）。その群の行だけで判定し、語が当たらなければ既定の状態にする。

    2つ以上の行が当たったとき、シングル系は価値の低い方（resolve_condition_v2 の prefer_lowest_value）。
    プロモパック系は同じく低い方を採りつつ、要確認 REVIEW_MULTIPLE_CANDIDATES を付ける。
    """
    _group, default_condition, default_basis = _KUBUN_TO_VALUE_GROUP[product_kubun]
    entries = list(group_entries)
    cond, _cid, basis = resolve_condition_v2(
        block, "", product_kubun, entries, cond_canonical_to_uuid, raw_memo=block, prefer_lowest_value=True
    )
    if cond == FLAG_SINGLE_CANONICAL and BASIS_UNIT_UNKNOWN in basis:
        return default_condition, default_basis, []
    reviews: list[dict] = []
    if product_kubun == PRODUCT_KUBUN_PROMO_PACK:
        text_combined = f"{block} "
        codes = [
            e["code"] for e in entries
            if app_kubun_matches(e.get("app_kubun") or "", product_kubun) and _entry_hit(e, text_combined)[0]
        ]
        if len(codes) >= 2:
            reviews = [{"kind": REVIEW_MULTIPLE_CANDIDATES, "codes": codes}]
    return cond, basis, reviews


def _resolve_condition(
    block: str, product_kubun: str, unit_kubun: str, cond_entries: list[dict], cond_canonical_to_uuid: dict,
    scoped_cond_entries: Mapping[str, Sequence[dict]] | None = None,
) -> tuple[str | None, str, list[dict]]:
    """(状態, basis, 要確認の理由の一覧 [{"kind": ..., ...}])。

    シングル系・プロモパック系は、その群の行が masters にあるときだけ群の行で判定する（ADR-1031）。行が無い間は今と同じ。
    """
    scoped = _KUBUN_TO_VALUE_GROUP.get(product_kubun)
    if scoped is not None and scoped_cond_entries and scoped_cond_entries.get(scoped[0]):
        return _resolve_scoped_condition(block, product_kubun, scoped_cond_entries[scoped[0]], cond_canonical_to_uuid)
    if product_kubun in PRODUCT_KUBUNS_DEFAULTING_TO_BOX and unit_kubun in BOX_RECHECK_UNIT_KUBUNS:
        cond, _cid, basis = resolve_condition_v2(block, "", UNIT_KUBUN_BOX, cond_entries, cond_canonical_to_uuid, raw_memo=block, prefer_lowest_value=True)
        codes = _other_kubun_hits(block, UNIT_KUBUN_BOX, cond_entries)
        reviews = [{"kind": REVIEW_MULTIPLE_CANDIDATES, "codes": codes}] if codes else []
        cond, undecided = _undecided_condition(cond, basis, cond_entries)
        return cond, basis, [*reviews, *undecided]
    cond, _cid, basis = resolve_condition_v2(block, "", unit_kubun, cond_entries, cond_canonical_to_uuid, raw_memo=block, prefer_lowest_value=True)
    # バルク系で状態語が無い（FLAG_SINGLE かつ単位不明の既定）なら Bulk。語で決まった行（R1:PSA 等）は変えない
    bulk = _bulk_condition(cond_entries)
    if (
        product_kubun == PRODUCT_KUBUN_BULK and bulk is not None
        and cond == FLAG_SINGLE_CANONICAL and BASIS_UNIT_UNKNOWN in basis
    ):
        return bulk, BASIS_BULK_DEFAULT, []
    cond, undecided = _undecided_condition(cond, basis, cond_entries)
    return cond, basis, undecided


def _other_kubun_hits(block: str, supplied_kubun: str, cond_entries: Sequence[dict]) -> list[str]:
    """補った区分と適用区分が違う状態の行のうち、文字に当たる行の code。

    適用区分が空の行（どの区分にも当てはまる）と、単品の行（FLAG_SINGLE）は対象にしない。
    """
    text_combined = f"{block} "
    return [
        e["code"] for e in cond_entries
        if (e.get("app_kubun") or "").strip()
        and e.get("value_group") not in SCOPED_VALUE_GROUPS
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


def _resolve_unit_from_state(
    *, unit: str | None, unit_kubun: str, unit_basis: dict, product_kubun: str, condition: str | None, basis: str,
    masters: ProductFirstMasters, unit_alias_to_info: dict,
) -> tuple[str | None, str, dict]:
    """(単位, 単位の区分, unit_basis)。分類と状態から単位を決め直す。

    セット系：単位の語が無ければ単位 Set（状態の単位では置き換えない）。書かれた単位はそのまま。
    サプライ系：状態の単位があれば、書かれた単位（「100枚入」の枚など）に関わらず状態の単位（Bag）にする。
    それ以外：単位が無い・箱系で「条件つき」なら状態の単位。状態が原文の語（R1〜R3）で決まり、その状態の単位が今の単位と違えば、
    状態の単位を優先する（理由 state_word）。
    """
    if product_kubun == PRODUCT_KUBUN_SET:
        if unit is None and masters.set_unit:
            set_unit, set_kubun, _resolved = resolve_unit_v2(masters.set_unit, unit_alias_to_info)
            return set_unit, set_kubun, {**unit_basis, UNIT_BASIS_FROM_CATEGORY: PRODUCT_KUBUN_SET}
        if unit is not None:
            return unit, unit_kubun, unit_basis
    if product_kubun == PRODUCT_KUBUN_SUPPLY:
        supply_unit = masters.condition_unit.get(condition or "")
        if supply_unit:
            new_unit, new_kubun, _resolved = resolve_unit_v2(supply_unit, unit_alias_to_info)
            return new_unit, new_kubun, {**unit_basis, "from_condition": condition, "reason": "supply_kubun"}
    replace = unit is None or (product_kubun == PRODUCT_KUBUN_BOX and unit_kubun == UNIT_KUBUN_REPLACEABLE_FOR_BOX)
    from_condition = masters.condition_unit.get(condition or "")
    if not from_condition:
        return unit, unit_kubun, unit_basis
    if replace:
        new_unit, new_kubun, _resolved = resolve_unit_v2(from_condition, unit_alias_to_info)
        return new_unit, new_kubun, {**unit_basis, "from_condition": condition}
    if product_kubun != PRODUCT_KUBUN_SET and _STATE_WORD_BASIS_RE.match(basis or "") and from_condition != unit:
        new_unit, new_kubun, _resolved = resolve_unit_v2(from_condition, unit_alias_to_info)
        return new_unit, new_kubun, {**unit_basis, "from_condition": condition, "reason": UNIT_BASIS_STATE_WORD}
    return unit, unit_kubun, unit_basis


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
    match = match_text_g2(match_text, masters)
    fixed_match = _fixed_match(match, fixed_product_id, masters)
    if fixed_match is not None:
        match = fixed_match
    elif match.status in ("ambiguous", "unmatched") and chosen_product_id is not None and (
        match.status == "unmatched" or chosen_product_id in match.candidates  # unmatched は直前の投稿で決めた商品（matched_followup）
    ):
        work_of = {p.id: p.work_id for p in masters.product_entries}
        match = dataclass_replace(match, status="matched", product_id=chosen_product_id, work_id=work_of.get(chosen_product_id))
    score = decide_by_score(match, masters.product_entries)
    product_id, product_kubun = _match_summary(match, masters)
    alias, unit_basis = find_unit_product_first(
        item, roles, lines, aliases, match, masters.ignore_phrases, find_price_alias, unit_alias_to_info
    )
    unit, unit_kubun, _resolved = resolve_unit_v2(alias or "", unit_alias_to_info)
    condition, basis, reviews = _resolve_condition(
        block, product_kubun, unit_kubun, cond_entries, cond_canonical_to_uuid, masters.scoped_cond_entries
    )
    unit, unit_kubun, unit_basis = _resolve_unit_from_state(
        unit=unit, unit_kubun=unit_kubun, unit_basis=unit_basis, product_kubun=product_kubun, condition=condition,
        basis=basis, masters=masters, unit_alias_to_info=unit_alias_to_info,
    )
    return {
        "product_id": product_id, "product_category": product_kubun, "match_status": match.status,
        "match_candidates": list(match.candidates),
        "match_boundary_dropped": list(match.boundary_dropped),
        "unit": unit or NONE_VALUE, "unit_kubun": unit_kubun, "unit_basis": unit_basis,
        "condition": condition or NONE_VALUE, "condition_basis": basis,
        "review_extra": [*_product_reviews(match, score), *reviews],
        "score_decision": score,
    }
