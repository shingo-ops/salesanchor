"""v102 の件で「単位の語も状態の語も原文に無い」とき、買取価格との比で Sealed box / Case に決める（便BB）。

設計: docs/handoff/v102-buyback-unit/card-BB.md
物差し = 同じ商品の買取（種別 BOX・BOX_SHRINK。結び付き済みで、最近見えた行）の、行ごとの最新価格 price_s の中央値 m_bb。
r = 件の価格 ÷ m_bb。box_min <= r < box_max なら Sealed box / Box、r >= case_min なら Case / Case、それ以外は何もしない。
パック（Unsearched pack・Searched pack）はここでは決めない。
閾値と日数は public.tcg_distribution_settings の key（値はコードに書かない。1つでも無い・不正なら何もしない）。
状態・単位の名前は書かず、状態の code から line_conditions.unit_id → line_units で引く。
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

from app.services.gemini_raw_copy_v102_product_first import PRODUCT_KUBUN_SET
from app.services.gemini_raw_copy_v102_soldout_ref import condition_decided_by_word

logger = logging.getLogger(__name__)

SETTING_BOX_MIN = "unit_buyback_box_min"
SETTING_BOX_MAX = "unit_buyback_box_max"
SETTING_CASE_MIN = "unit_buyback_case_min"
SETTING_MAX_AGE_DAYS = "unit_buyback_max_age_days"
_SETTING_KEYS = [SETTING_BOX_MIN, SETTING_BOX_MAX, SETTING_CASE_MIN, SETTING_MAX_AGE_DAYS]

# 状態の code（line_conditions.code。名前・id は直書きしない）
CONDITION_CODE_BOX = "CN0003"  # 箱の既定の状態（単位は line_conditions.unit_id から引く）
CONDITION_CODE_CASE = "CN0001"  # ケースの状態

# 買取の種別（public.buyback_shop_products.product_type）。箱の相場に使う種別
BUYBACK_BOX_TYPES = ("BOX", "BOX_SHRINK")
# 買取の結び付き済み（product_matcher が自動 'auto'、画面の手動設定が 'manual'）
BUYBACK_MATCHED_STATUSES = ("auto", "manual")

# 要確認の理由のうち、状態・単位が決まったので外すもの（他の理由は残す）。
# unit_unknown は gemini_raw_copy_v101._REVIEW_UNIT_UNKNOWN と同じ値、condition_unknown は tcg_condition_review_svc.REASON_CONDITION_UNKNOWN と同じ値
REASONS_DROPPED_WHEN_DECIDED = frozenset({"unit_unknown", "condition_unknown"})
REASON_SEPARATOR = ","

BASIS_PREFIX = "BUYBACK"
_CONDITION_BASIS_MAX = 100  # analysis_results.condition_basis の幅（line_analysis_v102_svc._CONDITION_BASIS_MAX と同じ）
_FLAG_NOTE_PREFIX = "単品語あり・要確認("  # resolve_condition_v2 の flag_note。単品の語が原文にあった印
_UNIT_DEFAULT_PREFIX = "R4:単位既定"
_PRODUCT_KUBUN_DEFAULT_PREFIX = "R4c:商品分類既定>"
_EXCLUDED_EFFECT = "excluded"  # 配信しない件（Sold out 等）の status_effect

_SETTINGS_SQL = "SELECT key, value FROM public.tcg_distribution_settings WHERE key = ANY(:keys)"
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
    SELECT c.code, c.id, c.canonical, u.canonical
    FROM public.line_conditions c JOIN public.line_units u ON u.id = c.unit_id
    WHERE c.code = ANY(:codes) AND c.is_active = TRUE AND u.is_active = TRUE
"""


@dataclass(frozen=True)
class BuybackSettings:
    box_min: Decimal
    box_max: Decimal
    case_min: Decimal
    max_age_days: int


@dataclass(frozen=True)
class Target:
    """決める先の状態と単位。"""

    condition_id: int
    condition: str
    unit: str


def parse_settings(raw: Mapping[str, str]) -> BuybackSettings | None:
    """設定表の値 → BuybackSettings。key が無い・数でない・0 以下・box_min < box_max <= case_min でない・日数が 1 未満なら None。"""
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
    return BuybackSettings(box_min=box_min, box_max=box_max, case_min=case_min, max_age_days=days)


def decide_code(price: Decimal, market: Decimal, settings: BuybackSettings) -> tuple[str, Decimal] | None:
    """(CONDITION_CODE_BOX か CONDITION_CODE_CASE, r)。決められなければ None。"""
    if price <= 0 or market <= 0:
        return None
    ratio = price / market
    if settings.box_min <= ratio < settings.box_max:
        return CONDITION_CODE_BOX, ratio
    if ratio >= settings.case_min:
        return CONDITION_CODE_CASE, ratio
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


def is_candidate(item: Mapping[str, Any], values: Mapping[str, Any]) -> bool:
    """対象の件：商品が特定済み・価格あり・配信しない件でない・単位も状態も語が無い・分類がセット系でない。

    セット系は買取の箱の値段で Sealed box / Case に決めない（単位は Set、状態は既定の Sealed box）。
    """
    return (
        bool(values["pid_resolved"]) and values["product_id"] is not None and values["price_normalized"] is not None
        and values.get("bundle_size") is None
        and item.get("status_effect") != _EXCLUDED_EFFECT and item.get("product_category") != PRODUCT_KUBUN_SET
        and has_no_unit_and_condition_word(item)
    )


def load_settings(session: Session) -> BuybackSettings | None:
    rows = session.execute(text(_SETTINGS_SQL), {"keys": _SETTING_KEYS}).fetchall()
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


def load_targets(session: Session) -> dict[str, Target] | None:
    """状態 code → (状態 id・名前・単位の名前)。2つとも引けなければ None。"""
    codes = [CONDITION_CODE_BOX, CONDITION_CODE_CASE]
    rows = session.execute(text(_TARGETS_SQL), {"codes": codes}).fetchall()
    targets = {str(r[0]): Target(condition_id=int(r[1]), condition=str(r[2]), unit=str(r[3])) for r in rows}
    if any(code not in targets for code in codes):
        logger.warning("[buyback_unit] 状態 %s が引けないので、買取価格による単位・状態の判定をしません", ",".join(codes))
        return None
    return targets


def _drop_decided_reasons(reasons: str | None) -> tuple[str | None, bool]:
    kept = [r for r in (reasons or "").split(REASON_SEPARATOR) if r and r not in REASONS_DROPPED_WHEN_DECIDED]
    return (REASON_SEPARATOR.join(kept) if kept else None), bool(kept)


def with_decision(values: Mapping[str, Any], target: Target, ratio: Decimal, unit_ids: Mapping[str, Any]) -> dict[str, Any] | None:
    """決めた状態・単位を入れた新しい values。単位 id が引けなければ None（何もしない）。元は変えない。"""
    unit_id = unit_ids.get(target.unit)
    if unit_id is None:
        return None
    reasons, needs_review = _drop_decided_reasons(values["review_reasons"])
    basis = f"{BASIS_PREFIX}:{target.condition} r={ratio:.2f}"[:_CONDITION_BASIS_MAX]
    return {
        **values, "condition_id": target.condition_id, "condition_canonical": target.condition, "condition_basis": basis,
        "unit_id": int(unit_id), "unit_canonical": target.unit, "unit_resolved": True,
        "review_reasons": reasons, "needs_review": needs_review,
    }


def apply_buyback_units(
    session: Session, items: Sequence[Mapping[str, Any]], base_values: Sequence[dict], unit_ids: Mapping[str, Any],
    posted_at: datetime, skip: frozenset[int] = frozenset(),
) -> list[dict]:
    """base_values の対象の件に、買取価格で決めた状態・単位を入れた新しい一覧（同じ長さ・同じ順）。

    対象が無い・設定が無い/不正・買取が無い（古い）件は、元の values のまま。DB を読むのは対象があるときだけ。
    skip は決めない件の位置（人が状態を決めた件。人の判断を単位だけ上書きしない）。
    """
    positions = [i for i, (item, values) in enumerate(zip(items, base_values)) if i not in skip and is_candidate(item, values)]
    if not positions:
        return list(base_values)
    settings = load_settings(session)
    if settings is None:
        return list(base_values)
    medians = load_medians(session, [int(base_values[i]["product_id"]) for i in positions], settings.max_age_days, posted_at)
    targets = load_targets(session) if medians else None
    if not medians or targets is None:
        return list(base_values)
    out = list(base_values)
    for i in positions:
        market = medians.get(int(base_values[i]["product_id"]))
        decided = decide_code(Decimal(str(base_values[i]["price_normalized"])), market, settings) if market is not None else None
        if decided is None:
            continue
        code, ratio = decided
        target = targets[code]
        if (base_values[i]["condition_canonical"], base_values[i]["unit_canonical"]) == (target.condition, target.unit):
            continue  # 今の状態・単位と同じなら何も書かない（condition_basis は他の処理が読むので、値が変わらない件では変えない）
        replaced = with_decision(base_values[i], target, ratio, unit_ids)
        if replaced is not None:
            out[i] = replaced
    return out
