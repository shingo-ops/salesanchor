"""v102 の件で「単位の語も状態の語も原文に無い」とき、買取価格との比で Sealed box / Case に決める（便BB）。

設計: docs/handoff/v102-buyback-unit/card-BB.md
物差し = 同じ商品の買取（種別 BOX・BOX_SHRINK。結び付き済みで、最近見えた行）の、行ごとの最新価格 price_s の中央値 m_bb。
r = 件の価格 ÷ m_bb。box_min <= r < box_max なら Sealed box / Box、r >= case_min なら Case / Case、それ以外は何もしない。
pack_max（任意の設定）があれば r <= pack_max は Pack に決める（箱系の分類の行だけ）。
閾値と日数は public.tcg_distribution_settings の key（値はコードに書かない。必須の4つが1つでも無い・不正なら何もしない）。
状態・単位の名前は書かず、状態マスタ（line_conditions）の「種類の札」（condition_def_id）と群（value_group）から写し先の行を引く。
設計: docs/handoff/price-unit-decision/design.md（ADR-1036）
"""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.gemini_raw_copy_v102_product_first import (
    BOX_RECHECK_UNIT_KUBUNS,
    PRODUCT_KUBUN_BOX,
    PRODUCT_KUBUN_SET,
)
from app.services.gemini_raw_copy_v102_soldout_ref import condition_decided_by_word
from app.services.tcg_analyzer_svc import resolve_unit_v2

logger = logging.getLogger(__name__)

SETTING_BOX_MIN = "unit_buyback_box_min"
SETTING_BOX_MAX = "unit_buyback_box_max"
SETTING_CASE_MIN = "unit_buyback_case_min"
SETTING_MAX_AGE_DAYS = "unit_buyback_max_age_days"
SETTING_PACK_MAX = "unit_buyback_pack_max"  # 無くてもよい key。無ければ Pack を決めない
_SETTING_KEYS = [SETTING_BOX_MIN, SETTING_BOX_MAX, SETTING_CASE_MIN, SETTING_MAX_AGE_DAYS]  # 必須の key

# 値段で決める単位 → 状態マスタの群（line_conditions.value_group）
UNIT_BOX, UNIT_CASE, UNIT_PACK = "Box", "Case", "Pack"
_UNIT_GROUP = {UNIT_BOX: "box", UNIT_CASE: "case", UNIT_PACK: "pack"}
_GROUPS = tuple(_UNIT_GROUP.values())
# 状態の種類の札（public.condition_definitions.id）のうち、各群の「手を付けていない」既定として同一視するもの（2=未開封・7=未サーチ）
_DEFAULT_LABELS = frozenset({2, 7})
_KIND_DEFAULT = "default"
_REASON_MULTIPLE = "condition_multiple_candidates"

# 買取の種別（public.buyback_shop_products.product_type）。箱の相場に使う種別
BUYBACK_BOX_TYPES = ("BOX", "BOX_SHRINK")
# 買取の結び付き済み（product_matcher が自動 'auto'、画面の手動設定が 'manual'）
BUYBACK_MATCHED_STATUSES = ("auto", "manual")

# 要確認の理由のうち、状態・単位が決まったので外すもの（他の理由は残す）。
# unit_unknown は gemini_raw_copy_v101._REVIEW_UNIT_UNKNOWN と同じ値、condition_unknown は tcg_condition_review_svc.REASON_CONDITION_UNKNOWN と同じ値
REASONS_DROPPED_WHEN_DECIDED = frozenset({"unit_unknown", "condition_unknown", _REASON_MULTIPLE})
REASON_SEPARATOR = ","

BASIS_PREFIX = "BUYBACK"
BASIS_PRICE_SUFFIX = "|PRICE:①r="  # 語で決まった行の basis の後ろに足す印
_CONDITION_BASIS_MAX = 100  # analysis_results.condition_basis の幅（line_analysis_v102_svc._CONDITION_BASIS_MAX と同じ）
_FLAG_NOTE_PREFIX = "単品語あり・要確認("  # resolve_condition_v2 の flag_note。単品の語が原文にあった印
_UNIT_DEFAULT_PREFIX = "R4:単位既定"
_PRODUCT_KUBUN_DEFAULT_PREFIX = "R4c:商品分類既定>"
_EXCLUDED_EFFECT = "excluded"  # 配信しない件（Sold out 等）の status_effect

_SETTINGS_SQL = "SELECT key, value FROM public.tcg_distribution_settings WHERE key = ANY(:keys)"
_SETTINGS_READ_KEYS = [*_SETTING_KEYS, SETTING_PACK_MAX]
_MEDIAN_SQL = """
    SELECT sp.product_id AS product_id, percentile_cont(0.5) WITHIN GROUP (ORDER BY lp.price_s) AS median_price
    FROM public.buyback_shop_products sp
    JOIN LATERAL (
        SELECT l.price_s FROM public.buyback_price_logs l
        WHERE l.shop_product_id = sp.id
          AND l.fetched_at <= :posted_at AND l.fetched_at >= :posted_at - make_interval(days => :days)
        ORDER BY l.fetched_at DESC, l.id DESC LIMIT 1
    ) lp ON TRUE
    WHERE sp.product_id = ANY(:pids) AND sp.product_type = ANY(:types) AND sp.match_status = ANY(:statuses)
      AND lp.price_s IS NOT NULL AND lp.price_s > 0
    GROUP BY sp.product_id
"""
_TARGETS_SQL = """
    SELECT c.code, c.id, c.canonical, c.value_group, c.unit_id, c.condition_def_id, u.canonical
    FROM public.line_conditions c LEFT JOIN public.line_units u ON u.id = c.unit_id AND u.is_active = TRUE
    WHERE c.is_active = TRUE AND c.tenant_id IS NULL AND c.value_group = ANY(:groups)
"""


@dataclass(frozen=True)
class BuybackSettings:
    box_min: Decimal
    box_max: Decimal
    case_min: Decimal
    max_age_days: int
    pack_max: Decimal | None = None  # None = Pack を決めない


@dataclass(frozen=True)
class Target:
    """決める先の状態と単位。"""

    condition_id: int
    condition: str
    unit: str


@dataclass(frozen=True)
class ConditionMap:
    """状態マスタから読んだもの。

    targets: 群 → 種類（札。2・7 は _KIND_DEFAULT）→ 写し先の行（その種類の行がちょうど 1 行のものだけ）。使えない群は入れない。
    label_by_condition_id / label_by_code: 読んだ全行の札（札が空の行は None）。
    """

    targets: Mapping[str, Mapping[Any, Target]]
    label_by_condition_id: Mapping[int, int | None]
    label_by_code: Mapping[str, int | None]


def parse_settings(raw: Mapping[str, str]) -> BuybackSettings | None:
    """設定表の値 → BuybackSettings。必須 4 key が無い・数でない・0 以下・box_min < box_max <= case_min でない・日数が 1 未満なら None。
    pack_max は key が無ければ None（Pack を決めない）。あって 0 < pack_max < box_min でなければ設定全体を None。"""
    try:
        box_min = Decimal(str(raw[SETTING_BOX_MIN]).strip())
        box_max = Decimal(str(raw[SETTING_BOX_MAX]).strip())
        case_min = Decimal(str(raw[SETTING_CASE_MIN]).strip())
        days = int(str(raw[SETTING_MAX_AGE_DAYS]).strip())
    except (KeyError, InvalidOperation, ValueError):
        return None
    if not all(v.is_finite() for v in (box_min, box_max, case_min)):
        return None
    if box_min <= 0 or not box_min < box_max <= case_min or days < 1:
        return None
    pack_max: Decimal | None = None
    if SETTING_PACK_MAX in raw:  # key があるなら正しい値でなければならない（不正なら設定全体を不正とする）
        try:
            pack_max = Decimal(str(raw[SETTING_PACK_MAX]).strip())
        except InvalidOperation:
            return None
        if not pack_max.is_finite() or not 0 < pack_max < box_min:
            return None
    return BuybackSettings(box_min=box_min, box_max=box_max, case_min=case_min, max_age_days=days, pack_max=pack_max)


def decide_code(price: Decimal, market: Decimal, settings: BuybackSettings) -> tuple[str, Decimal] | None:
    """(単位の種類 UNIT_BOX・UNIT_CASE・UNIT_PACK, r)。決められなければ None。"""
    if price <= 0 or market <= 0:
        return None
    ratio = price / market
    if settings.pack_max is not None and ratio <= settings.pack_max:
        return UNIT_PACK, ratio
    if settings.box_min <= ratio < settings.box_max:
        return UNIT_BOX, ratio
    if ratio >= settings.case_min:
        return UNIT_CASE, ratio
    return None


def has_no_unit_and_condition_word(item: Mapping[str, Any]) -> bool:
    """件の行に単位の語も状態の語も無いか。

    単位: unit_basis の alias が None（find_unit_product_first が別名を見つけられなかった。状態から単位を決め直した件も含む）。
    状態: condition_basis が語で決まっていない既定（R4:単位既定… か R4c:商品分類既定>R4:単位既定…）。単品語の印が付いた件は語ありとする。
    """
    unit_basis = item.get("unit_basis")
    if not isinstance(unit_basis, Mapping) or unit_basis.get("alias") is not None:
        return False
    basis = str(item.get("condition_basis") or "")
    if basis.startswith(_FLAG_NOTE_PREFIX) or condition_decided_by_word(basis):
        return False
    rest = basis[len(_PRODUCT_KUBUN_DEFAULT_PREFIX):] if basis.startswith(_PRODUCT_KUBUN_DEFAULT_PREFIX) else basis
    return rest.startswith(_UNIT_DEFAULT_PREFIX)


def _unit_not_decided_by_word(item: Mapping[str, Any], unit_alias_to_info: Mapping[str, Any]) -> bool:
    """単位の語で Box／Case／Pack が決まっていないか（別名が無い、または別名の単位の区分が「条件つき」等）。"""
    unit_basis = item.get("unit_basis")
    if not isinstance(unit_basis, Mapping):
        return False
    alias = unit_basis.get("alias")
    return alias is None or resolve_unit_v2(alias, unit_alias_to_info)[1] in BOX_RECHECK_UNIT_KUBUNS


def _is_box_without_unit_word(item: Mapping[str, Any], unit_alias_to_info: Mapping[str, Any]) -> bool:
    return (
        item.get("product_category") == PRODUCT_KUBUN_BOX
        and not str(item.get("condition_basis") or "").startswith(_FLAG_NOTE_PREFIX)
        and _unit_not_decided_by_word(item, unit_alias_to_info)
    )


def is_candidate(item: Mapping[str, Any], values: Mapping[str, Any], unit_alias_to_info: Mapping[str, Any]) -> bool:
    """対象の件：商品が特定済み・価格あり・配信しない件でない・分類がセット系でない・まとめ売りでない、かつ
    (単位も状態も語が無い、または 箱系の分類で単位の語で決まっていない（「個」・無記入等）)。

    セット系は買取の箱の値段で Sealed box / Case に決めない（単位は Set、状態は既定の Sealed box）。
    """
    return (
        bool(values["pid_resolved"]) and values["product_id"] is not None and values["price_normalized"] is not None
        and values.get("bundle_size") is None
        and item.get("status_effect") != _EXCLUDED_EFFECT and item.get("product_category") != PRODUCT_KUBUN_SET
        and (has_no_unit_and_condition_word(item) or _is_box_without_unit_word(item, unit_alias_to_info))
    )


def load_settings(session: Session) -> BuybackSettings | None:
    rows = session.execute(text(_SETTINGS_SQL), {"keys": _SETTINGS_READ_KEYS}).fetchall()
    settings = parse_settings({str(r[0]): str(r[1]) for r in rows})
    if settings is None:
        logger.warning("[buyback_unit] 設定 %s が無いか不正なので、買取価格による単位・状態の判定をしません", ",".join(_SETTING_KEYS))
    return settings


def load_medians(session: Session, product_ids: Sequence[int], max_age_days: int, posted_at: datetime) -> dict[int, Decimal]:
    """商品ごとの買取の箱の価格の中央値（1回の SQL）。投稿日時より前・max_age_days 日以内の、店ごとに最新の値だけを使う。"""
    rows = session.execute(
        text(_MEDIAN_SQL),
        {"pids": sorted(set(product_ids)), "types": list(BUYBACK_BOX_TYPES), "statuses": list(BUYBACK_MATCHED_STATUSES), "days": max_age_days, "posted_at": posted_at},
    ).fetchall()
    return {int(r[0]): Decimal(str(r[1])) for r in rows}


def _kind(label: int | None) -> Any:
    return _KIND_DEFAULT if label in _DEFAULT_LABELS else label


def load_targets(session: Session) -> ConditionMap | None:
    """状態マスタ（群 box・case・pack の有効な共用行）を 1 回で読む。

    box・case の群は、unit_id が 1 種類（NULL なし）で既定（札 2・7）の行がちょうど 1 行のときだけ使える。どちらかが使えなければ None（便全体で何もしない）。
    pack の群は unit_id が 1 種類でなければ pack だけ使えない（box・case は決める）。
    """
    rows = session.execute(text(_TARGETS_SQL), {"groups": list(_GROUPS)}).fetchall()
    by_group: dict[str, list[tuple[Target | None, str, int | None, int | None]]] = {g: [] for g in _GROUPS}
    label_by_id: dict[int, int | None] = {}
    label_by_code: dict[str, int | None] = {}
    for code, cid, canonical, group, unit_id, def_id, unit_canonical in rows:
        label = int(def_id) if def_id is not None else None
        label_by_id[int(cid)] = label
        label_by_code[str(code)] = label
        if group in by_group:
            unit_key = int(unit_id) if unit_id is not None and unit_canonical is not None else None
            target = Target(condition_id=int(cid), condition=str(canonical), unit=str(unit_canonical)) if unit_key is not None else None
            by_group[str(group)].append((target, str(code), label, unit_key))
    targets: dict[str, dict[Any, Target]] = {}
    usable: dict[str, bool] = {}
    for group, members in by_group.items():
        unit_keys = {m[3] for m in members}
        by_label: dict[int | None, list[str]] = {}
        for _t, code, label, _u in members:
            by_label.setdefault(label, []).append(code)
        for label, codes in by_label.items():
            if label is not None and len(codes) >= 2:  # (a)
                logger.warning("[buyback_unit] 状態マスタの群 %s に札 %s の行が %d 行あります: %s", group, label, len(codes), ",".join(sorted(codes)))
        default_codes = [code for _t, code, label, _u in members if label in _DEFAULT_LABELS]
        if len(default_codes) != 1:  # (b)
            logger.warning("[buyback_unit] 状態マスタの群 %s の既定（札 2・7）の行が %d 行です（1 行であるべき）: %s", group, len(default_codes), ",".join(sorted(default_codes)))
        if len(unit_keys) >= 2:  # (c)
            logger.warning("[buyback_unit] 状態マスタの群 %s の unit_id が %d 種類あります（NULL を含む）: %s", group, len(unit_keys), ",".join(sorted(code for _t, code, _l, _u in members)))
        single_unit = len(unit_keys) == 1 and None not in unit_keys
        usable[group] = single_unit and (len(default_codes) == 1 or group == _UNIT_GROUP[UNIT_PACK])
        if single_unit:
            by_kind: dict[Any, list[Target]] = {}
            for target, _code, label, _u in members:
                if label is not None and target is not None:
                    by_kind.setdefault(_kind(label), []).append(target)
            targets[group] = {kind: ts[0] for kind, ts in by_kind.items() if len(ts) == 1}
    if not (usable[_UNIT_GROUP[UNIT_BOX]] and usable[_UNIT_GROUP[UNIT_CASE]]):
        logger.warning("[buyback_unit] 状態マスタの群 box・case のどちらかが使えない形なので、買取価格による単位・状態の判定をしません")
        return None
    return ConditionMap(
        targets={g: t for g, t in targets.items() if usable[g]}, label_by_condition_id=label_by_id, label_by_code=label_by_code,
    )


def _drop_decided_reasons(reasons: str | None) -> tuple[str | None, bool]:
    kept = [r for r in (reasons or "").split(REASON_SEPARATOR) if r and r not in REASONS_DROPPED_WHEN_DECIDED]
    return (REASON_SEPARATOR.join(kept) if kept else None), bool(kept)


def _has_droppable_reason(reasons: str | None) -> bool:
    return any(r in REASONS_DROPPED_WHEN_DECIDED for r in (reasons or "").split(REASON_SEPARATOR))


def _price_basis(values: Mapping[str, Any], ratio: Decimal) -> str:
    return f"{values['condition_basis']}{BASIS_PRICE_SUFFIX}{ratio:.2f}"[:_CONDITION_BASIS_MAX]


def with_decision(
    values: Mapping[str, Any], target: Target, ratio: Decimal, unit_ids: Mapping[str, Any], word_decided: bool = False,
) -> dict[str, Any] | None:
    """決めた状態・単位を入れた新しい values。単位 id が引けなければ None（何もしない）。元は変えない。

    word_decided（状態が語で決まった行）: basis は今の basis の後ろに |PRICE:①r=<比> を足す（先頭は変えない）。語なしの行は BUYBACK:<状態> r=<比>。
    """
    unit_id = unit_ids.get(target.unit)
    if unit_id is None:
        return None
    reasons, needs_review = _drop_decided_reasons(values["review_reasons"])
    basis = _price_basis(values, ratio) if word_decided else f"{BASIS_PREFIX}:{target.condition} r={ratio:.2f}"[:_CONDITION_BASIS_MAX]
    return {
        **values, "condition_id": target.condition_id, "condition_canonical": target.condition, "condition_basis": basis,
        "unit_id": int(unit_id), "unit_canonical": target.unit, "unit_resolved": True,
        "review_reasons": reasons, "needs_review": needs_review,
    }


def _current_kind(values: Mapping[str, Any], cmap: ConditionMap) -> Any:
    """今の状態の種類。(1) 語で決まっていない行は既定。(2) 語で決まった行は札から。引けなければ None（何もしない）。"""
    if not condition_decided_by_word(str(values.get("condition_basis") or "")):
        return _KIND_DEFAULT
    cid = values.get("condition_id")
    label = cmap.label_by_condition_id.get(int(cid)) if cid is not None else None
    return None if label is None else _kind(label)


def _review_code_kinds(item: Mapping[str, Any], cmap: ConditionMap) -> set[Any] | None:
    """item["review"] の condition_multiple_candidates の codes の種類。引けない code が 1 つでもあれば None。codes が無ければ空集合。"""
    kinds: set[Any] = set()
    for element in item.get("review") or []:
        if not isinstance(element, Mapping) or element.get("kind") != _REASON_MULTIPLE:
            continue
        for code in element.get("codes") or []:
            label = cmap.label_by_code.get(str(code))
            if label is None:
                return None
            kinds.add(_kind(label))
    return kinds


def decide_kind(item: Mapping[str, Any], values: Mapping[str, Any], cmap: ConditionMap) -> Any:
    """状態の種類（_KIND_DEFAULT か札）。決められなければ None（何もしない）。

    今の状態の種類と codes の種類を合わせて 1 つのときだけ。今の状態が「既定」で codes があるときは、既定を数えず codes の種類だけを使う（design.md B）。
    """
    current = _current_kind(values, cmap)
    if current is None:
        return None
    code_kinds = _review_code_kinds(item, cmap)
    if code_kinds is None:
        return None
    if not code_kinds:
        if _REASON_MULTIPLE in (values.get("review_reasons") or "").split(REASON_SEPARATOR):
            return None  # 理由があるのに codes が 1 つも取れない行は何もしない（理由も外さない）
        return current
    kinds = code_kinds if current == _KIND_DEFAULT else {*code_kinds, current}
    return next(iter(kinds)) if len(kinds) == 1 else None


def apply_buyback_units(
    session: Session, items: Sequence[Mapping[str, Any]], base_values: Sequence[dict], unit_ids: Mapping[str, Any],
    unit_alias_to_info: Mapping[str, Any], posted_at: datetime, skip: frozenset[int] = frozenset(),
) -> list[dict]:
    """base_values の対象の件に、買取価格で決めた状態・単位を入れた新しい一覧（同じ長さ・同じ順）。

    対象が無い・設定が無い/不正・買取が無い（古い）件は、元の values のまま。DB を読むのは対象があるときだけ。
    skip は決めない件の位置（人が状態を決めた件。人の判断を単位だけ上書きしない）。
    """
    positions = [i for i, (item, values) in enumerate(zip(items, base_values)) if i not in skip and is_candidate(item, values, unit_alias_to_info)]
    if not positions:
        return list(base_values)
    settings = load_settings(session)
    if settings is None:
        return list(base_values)
    medians = load_medians(session, [int(base_values[i]["product_id"]) for i in positions], settings.max_age_days, posted_at)
    cmap = load_targets(session) if medians else None
    if not medians or cmap is None:
        return list(base_values)
    out = list(base_values)
    for i in positions:
        values = base_values[i]
        market = medians.get(int(values["product_id"]))
        decided = decide_code(Decimal(str(values["price_normalized"])), market, settings) if market is not None else None
        if decided is None:
            continue
        unit, ratio = decided
        if unit == UNIT_PACK and items[i].get("product_category") != PRODUCT_KUBUN_BOX:
            continue  # Pack は箱系の分類の行だけ
        kind = decide_kind(items[i], values, cmap)
        target = cmap.targets.get(_UNIT_GROUP[unit], {}).get(kind) if kind is not None else None
        if target is None:
            continue
        word_decided = condition_decided_by_word(str(values.get("condition_basis") or ""))
        if (values["condition_canonical"], values["unit_canonical"]) == (target.condition, target.unit):
            if _has_droppable_reason(values["review_reasons"]):  # 値は同じ。外す理由だけ外す
                reasons, needs_review = _drop_decided_reasons(values["review_reasons"])
                out[i] = {**values, "review_reasons": reasons, "needs_review": needs_review,
                          **({"condition_basis": _price_basis(values, ratio)} if word_decided else {})}
            continue  # 外す理由が無ければ何も書かない（condition_basis は他の処理が読むので、値が変わらない件では変えない）
        replaced = with_decision(values, target, ratio, unit_ids, word_decided)
        if replaced is not None:
            out[i] = replaced
    return out
