"""v102 の件の「単位と価格が相場と合わない」を要確認にする（便UP）。単位・価格は書き換えない。

設計: docs/handoff/v102-unit-price-check/card-UP.md
相場 = 同じ商品の v102 の現行行（価格あり・単位あり・今の投稿とは別の投稿。要確認の行も入れる）の、単位ごとの価格の中央値。
要確認の行を除かないのは、この確認自体が要確認にした行が相場から外れ、再解析のたびに結果が揺れるのを防ぐため（中央値と投稿数の最小で外れ値には強い）。
件の単位 U・価格 p について、相場 m(U) とずれが倍率を超え、かつ別の単位 V の相場の方が p に近いときだけ unit_price_mismatch を付ける。
倍率と最小の投稿数は public.tcg_distribution_settings の key（値はコードに書かない。key が無い・不正なら何もしない）。
"""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

REASON_UNIT_PRICE_MISMATCH = "unit_price_mismatch"
SETTING_RATIO = "unit_price_check_ratio"
SETTING_MIN_POSTS = "unit_price_check_min_posts"
SETTING_SINGLE_RATIO = "unit_price_check_single_ratio"  # 規則B（任意）。key が無ければ規則Bは働かない
_ENGINE_LIKE = "v102%"


@dataclass(frozen=True)
class CheckSettings:
    ratio: Decimal  # 相場とのずれの倍率の上限（これを超えたら疑う）
    min_posts: int  # 相場に使う、別々の投稿の数の最小
    single_ratio: Decimal | None = None  # 規則B: 比べる別単位の相場が無いとき、価格が相場のこの倍率以上（高い側だけ）なら疑う。None なら規則Bは働かない


@dataclass(frozen=True)
class MarketEntry:
    median: Decimal
    posts: int


@dataclass(frozen=True)
class Candidate:
    """判定の対象 1 件。key は呼び出し側が件を見分ける印。"""

    key: int
    product_id: int
    unit: str
    price: Decimal


Market = Mapping[int, Mapping[str, MarketEntry]]  # product_id → 単位 → 相場

_SETTINGS_SQL = "SELECT key, value FROM {schema}.tcg_distribution_settings WHERE key = ANY(:keys)"
_MARKET_SQL = """
    SELECT ar.product_id AS product_id, ar.unit_canonical AS unit,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY ar.price_normalized) AS median_price,
           count(DISTINCT md5(sm.raw_text)) AS posts
    FROM {schema}.analysis_results ar
    JOIN {schema}.extraction_items ei ON ei.id = ar.extraction_item_id
    JOIN {schema}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id
    WHERE ar.product_id = ANY(:pids) AND ar.engine_version LIKE :engine AND ar.is_current IS TRUE
      AND ar.price_normalized IS NOT NULL AND ar.unit_canonical IS NOT NULL
      AND ar.bundle_size IS NULL
      AND (ar.price_basis IS NULL OR ar.price_basis NOT LIKE 'INHERIT:%')
      AND ej.source_message_id != CAST(:smid AS uuid)
      AND md5(sm.raw_text) != COALESCE((SELECT md5(raw_text) FROM {schema}.source_messages WHERE id = CAST(:smid AS uuid)), '')
    GROUP BY ar.product_id, ar.unit_canonical
"""


def parse_settings(raw: Mapping[str, str]) -> CheckSettings | None:
    """設定表の値 → CheckSettings。key が無い・数でない・倍率が 1 以下・投稿数が 1 未満なら None（確認をしない）。"""
    try:
        ratio = Decimal(str(raw[SETTING_RATIO]).strip())
        min_posts = int(str(raw[SETTING_MIN_POSTS]).strip())
    except (KeyError, InvalidOperation, ValueError):
        return None
    if not ratio.is_finite() or ratio <= 1 or min_posts < 1:
        return None
    return CheckSettings(ratio=ratio, min_posts=min_posts, single_ratio=_parse_single_ratio(raw))


def _parse_single_ratio(raw: Mapping[str, str]) -> Decimal | None:
    """規則Bの倍率。key が無い・数でない・1 以下なら None（規則Bは働かない。規則Aは働く）。"""
    if SETTING_SINGLE_RATIO not in raw:
        return None
    try:
        value = Decimal(str(raw[SETTING_SINGLE_RATIO]).strip())
    except InvalidOperation:
        logger.warning("[unit_price_check] %s が数でないので、規則Bは働きません", SETTING_SINGLE_RATIO)
        return None
    return value if value.is_finite() and value > 1 else None


def load_settings(session: Session, schema: str) -> CheckSettings | None:
    rows = session.execute(
        text(_SETTINGS_SQL.format(schema=schema)), {"keys": [SETTING_RATIO, SETTING_MIN_POSTS, SETTING_SINGLE_RATIO]}
    ).fetchall()
    settings = parse_settings({str(r[0]): str(r[1]) for r in rows})
    if settings is None:
        logger.warning("[unit_price_check] 設定 %s・%s が無いか不正なので、単位と価格の確認をしません", SETTING_RATIO, SETTING_MIN_POSTS)
    return settings


def load_market(session: Session, schema: str, product_ids: Sequence[int], source_message_id: str) -> dict[int, dict[str, MarketEntry]]:
    """商品ごと・単位ごとの相場を 1 回の SQL で引く。今の投稿（同じ source_message・同じ原文）の行は含めない。"""
    if not product_ids:
        return {}
    rows = session.execute(
        text(_MARKET_SQL.format(schema=schema)),
        {"pids": sorted(set(product_ids)), "engine": _ENGINE_LIKE, "smid": source_message_id},
    ).fetchall()
    market: dict[int, dict[str, MarketEntry]] = {}
    for row in rows:
        market.setdefault(int(row[0]), {})[str(row[1])] = MarketEntry(median=Decimal(str(row[2])), posts=int(row[3]))
    return market


def _ratio(price: Decimal, median: Decimal) -> Decimal:
    return max(price, median) / min(price, median)


def is_unit_price_mismatch(candidate: Candidate, market: Market, settings: CheckSettings) -> bool:
    """件の単位の相場とずれが倍率を超え、別の単位の相場の方が近いか。比べる材料が足りなければ False。"""
    if candidate.price <= 0:
        return False
    usable = {
        unit: entry
        for unit, entry in market.get(candidate.product_id, {}).items()
        if entry.posts >= settings.min_posts and entry.median > 0
    }
    own = usable.get(candidate.unit)
    if own is None:
        return False
    own_ratio = _ratio(candidate.price, own.median)
    if own_ratio <= settings.ratio:
        return False
    others = [entry for unit, entry in usable.items() if unit != candidate.unit]
    if not others:  # 規則B: 比べる別単位の相場が無い
        # 高い側だけ（価格が相場の single_ratio 倍以上）。安い側はセール・状態差があり得るので付けない
        return settings.single_ratio is not None and candidate.price >= own.median * settings.single_ratio
    return any(_ratio(candidate.price, entry.median) < own_ratio for entry in others)


def find_mismatches(session: Session, schema: str, candidates: Sequence[Candidate], source_message_id: str) -> frozenset[int]:
    """candidates のうち unit_price_mismatch を付ける件の key。設定が無い・不正、または対象が無ければ空（DB も読まない）。"""
    if not candidates:
        return frozenset()
    settings = load_settings(session, schema)
    if settings is None:
        return frozenset()
    market = load_market(session, schema, [c.product_id for c in candidates], source_message_id)
    return frozenset(c.key for c in candidates if is_unit_price_mismatch(c, market, settings))
