"""在庫オファーの集計層。

PR-2': ver4.1 の 2 系統集計を再現し、Series × Condition(/Note) 単位で
最良 1 件を選ぶ純粋ロジックを提供する。
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class AggregationRule:
    condition: str
    price_tolerance: int
    stock_tolerance: int


@dataclass(frozen=True, slots=True)
class AggregationOffer:
    row_id: int | None
    product_id: int | None
    supplier_id: int | None
    supplier_name: str | None
    series: str
    condition: str
    quantity: int
    unit_price: int
    status: str
    product_name: str | None = None
    name_en: str | None = None
    category: str | None = None
    mark: str | None = None
    unit: str | None = None
    offer_type: str | None = None
    ship_timing: str | None = None
    tcg_type: str | None = None
    offered_at: datetime | None = None
    release_date: date | None = None
    note_ja: str | None = None
    note_en: str | None = None


@dataclass(frozen=True, slots=True)
class AggregationResult:
    row_id: int | None
    product_id: int | None
    supplier_id: int | None
    supplier_name: str | None
    series: str
    condition: str
    quantity: int
    unit_price: int
    status: str
    reason_category: str
    reason: str
    product_name: str | None = None
    name_en: str | None = None
    category: str | None = None
    mark: str | None = None
    unit: str | None = None
    offer_type: str | None = None
    ship_timing: str | None = None
    tcg_type: str | None = None
    offered_at: datetime | None = None
    release_date: date | None = None
    note_ja: str | None = None
    note_en: str | None = None


DEFAULT_AGGREGATION_RULES: tuple[AggregationRule, ...] = (
    AggregationRule(condition="Case", price_tolerance=1000, stock_tolerance=5),
    AggregationRule(condition="Sealed box", price_tolerance=100, stock_tolerance=30),
    AggregationRule(condition="Damaged sealed box", price_tolerance=100, stock_tolerance=10),
    AggregationRule(condition="No shrink box", price_tolerance=100, stock_tolerance=5),
)


def _coerce_int(value: Any) -> int:
    if value is None:
        raise ValueError("numeric field is required")
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid numeric field")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    return int(Decimal(str(value)))


def _get_value(source: Mapping[str, Any] | Any, keys: Sequence[str]) -> Any:
    if isinstance(source, Mapping):
        for key in keys:
            if key in source and source[key] not in (None, ""):
                return source[key]
    else:
        for key in keys:
            if hasattr(source, key):
                value = getattr(source, key)
                if value not in (None, ""):
                    return value
    return None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return _coerce_int(value)
    except (TypeError, ValueError):
        return None


def _optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip() or None


def _parse_date(value: Any) -> date | None:
    text_value = _optional_text(value)
    if text_value is None:
        return None
    for fmt in (
        "%Y/%m/%d",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(text_value, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text_value)
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    text_value = _optional_text(value)
    if text_value is None:
        return None
    for fmt in (
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(text_value, fmt)
            return parsed
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text_value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_status(value: Any) -> str:
    raw = _optional_text(value) or "unknown"
    normalized = raw.strip().lower().replace(" ", "_")
    return {
        "in_stock": "In Stock",
        "pre_order": "Pre-order",
        "pre-order": "Pre-order",
        "out_of_stock": "Out of Stock",
        "reserved": "Reserved",
        "archived": "Archived",
    }.get(normalized, raw)


def _normalize_condition_for_output(value: Any) -> str:
    raw = _optional_text(value) or ""
    lowered = raw.lower()
    mapping = {
        "case": "Case",
        "sealed box": "Sealed box",
        "sealed_box": "Sealed box",
        "damaged sealed box": "Damaged sealed box",
        "damaged box": "Damaged sealed box",
        "no shrink box": "No shrink box",
        "no_shrink_box": "No shrink box",
        "unsearched pack": "Unsearched pack",
        "flag_single": "FLAG_SINGLE",
    }
    return mapping.get(lowered, raw)


def _normalize_offer(source: Mapping[str, Any] | Any) -> AggregationOffer:
    series = _get_value(
        source,
        (
            "series",
            "Series",
            "product_name",
            "Product Name",
            "name_ja",
            "name",
            "related_series",
            "required_output_value",
            "Japanese Title",
        ),
    )
    condition = _normalize_condition_for_output(_get_value(source, ("condition", "Condition")))
    quantity = _get_value(source, ("quantity", "Quantity"))
    unit_price = _get_value(source, ("unit_price", "Unit Price"))
    status = _normalize_status(_get_value(source, ("status", "Status")))
    supplier_name = _get_value(source, ("supplier_name", "provider", "supplier", "提供者"))
    note_ja = _optional_text(_get_value(source, ("note_ja", "notes_ja", "Note_JA", "note", "memo")))
    note_en = _optional_text(_get_value(source, ("note_en", "notes_en", "Note_EN")))

    if series is None:
        raise ValueError("series is required")
    if not condition:
        raise ValueError("condition is required")

    return AggregationOffer(
        row_id=_optional_int(_get_value(source, ("id", "row_id"))),
        product_id=_optional_int(_get_value(source, ("product_id",))),
        supplier_id=_optional_int(_get_value(source, ("supplier_id",))),
        supplier_name=None if supplier_name is None else str(supplier_name),
        series=str(series),
        condition=str(condition),
        quantity=_coerce_int(quantity),
        unit_price=_coerce_int(unit_price),
        status=str(status),
        product_name=_optional_text(_get_value(source, ("product_name", "name", "Japanese Title"))),
        name_en=_optional_text(_get_value(source, ("name_en",))),
        category=_optional_text(_get_value(source, ("category", "Category", "Categoly"))),
        mark=_optional_text(_get_value(source, ("mark",))),
        unit=_optional_text(_get_value(source, ("unit",))),
        offer_type=_optional_text(_get_value(source, ("offer_type",))),
        ship_timing=_optional_text(_get_value(source, ("ship_timing",))),
        tcg_type=_optional_text(_get_value(source, ("tcg_type",))),
        offered_at=_parse_datetime(_get_value(source, ("offered_at", "offeredAt"))),
        release_date=_parse_date(_get_value(source, ("release_date", "Release Date", "releaseDate"))),
        note_ja=note_ja,
        note_en=note_en,
    )


def _rule_map(rules: Iterable[AggregationRule]) -> dict[str, AggregationRule]:
    return {rule.condition: rule for rule in rules}


def _is_note_group(offer: AggregationOffer) -> bool:
    return bool((offer.note_ja or "").strip()) and bool((offer.condition or "").strip())


def _pick_best_offer(
    offers: Sequence[tuple[int, AggregationOffer]],
    rule: AggregationRule | None,
) -> tuple[AggregationOffer, str, str]:
    sorted_by_price = sorted(
        offers,
        key=lambda item: (
            item[1].unit_price,
            -item[1].quantity,
            item[1].supplier_name or "",
            item[0],
        ),
    )
    _, cheapest = sorted_by_price[0]

    if rule is not None:
        within_tolerance = [
            item
            for item in sorted_by_price
            if item[1].unit_price - cheapest.unit_price <= rule.price_tolerance
            and item[1].quantity - cheapest.quantity >= rule.stock_tolerance
            and item[1].quantity > cheapest.quantity
        ]
        if within_tolerance:
            selected = sorted(
                within_tolerance,
                key=lambda item: (
                    -item[1].quantity,
                    item[1].unit_price,
                    item[1].supplier_name or "",
                    item[0],
                ),
            )[0][1]
            price_diff = selected.unit_price - cheapest.unit_price
            qty_diff = selected.quantity - cheapest.quantity
            return (
                selected,
                "stock_priority",
                f"在庫優先（価格差{price_diff}円 / 許容{rule.price_tolerance}円以内, 数量差{qty_diff}）",
            )

    return cheapest, "lowest_price", "最安値のため採用"


def aggregate_inventory_offers(
    offers: Iterable[Mapping[str, Any] | Any],
    rules: Iterable[AggregationRule] = DEFAULT_AGGREGATION_RULES,
) -> list[AggregationResult]:
    """Series × Condition(/Note) で 1 件に集約する純粋関数."""

    track1_grouped: OrderedDict[tuple[str, str], list[tuple[int, AggregationOffer]]] = OrderedDict()
    track2_grouped: OrderedDict[tuple[str, str, str], list[tuple[int, AggregationOffer]]] = OrderedDict()
    track1_conditions = {"Case", "Sealed box", "Damaged sealed box", "No shrink box"}
    for idx, source in enumerate(offers):
        offer = _normalize_offer(source)
        if _is_note_group(offer):
            key = (offer.series, offer.condition, offer.note_ja or "")
            track2_grouped.setdefault(key, []).append((idx, offer))
        elif offer.condition in track1_conditions:
            key = (offer.series, offer.condition)
            track1_grouped.setdefault(key, []).append((idx, offer))

    rule_by_condition = _rule_map(rules)
    ranked_results: list[tuple[bool, int, int, AggregationResult]] = []

    def _append_result(selected: AggregationOffer, reason_category: str, reason: str) -> None:
        sequence = len(ranked_results)
        ranked_results.append(
            (
                selected.release_date is None,
                -(selected.release_date.toordinal() if selected.release_date else 0),
                sequence,
                AggregationResult(
                    row_id=selected.row_id,
                    product_id=selected.product_id,
                    supplier_id=selected.supplier_id,
                    supplier_name=selected.supplier_name,
                    series=selected.series,
                    condition=selected.condition,
                    quantity=selected.quantity,
                    unit_price=selected.unit_price,
                    status=selected.status,
                    product_name=selected.product_name,
                    name_en=selected.name_en,
                    category=selected.category,
                    mark=selected.mark,
                    unit=selected.unit,
                    offer_type=selected.offer_type,
                    ship_timing=selected.ship_timing,
                    tcg_type=selected.tcg_type,
                    offered_at=selected.offered_at,
                    release_date=selected.release_date,
                    note_ja=selected.note_ja,
                    note_en=selected.note_en,
                    reason_category=reason_category,
                    reason=reason,
                ),
            )
        )

    for (_series, condition), items in track1_grouped.items():
        selected, reason_category, reason = _pick_best_offer(items, rule_by_condition.get(condition))
        _append_result(selected, reason_category, reason)

    for (_series, condition, _note_ja), items in track2_grouped.items():
        sorted_by_price = sorted(
            items,
            key=lambda item: (
                item[1].unit_price,
                -item[1].quantity,
                item[1].supplier_name or "",
                item[0],
            ),
        )
        selected = sorted_by_price[0][1]
        _append_result(selected, "lowest_price", "最安値のため採用")

    return [item[3] for item in ranked_results]


async def load_aggregation_rules(db: AsyncSession) -> list[AggregationRule]:
    """DB から集計ルールを読み込む（読み取り専用）。"""

    result = await db.execute(
        text(
            "SELECT condition, price_tolerance, stock_tolerance "
            "FROM public.inventory_aggregation_rules "
            "ORDER BY id ASC"
        )
    )
    return [
        AggregationRule(
            condition=row["condition"],
            price_tolerance=int(row["price_tolerance"]),
            stock_tolerance=int(row["stock_tolerance"]),
        )
        for row in result.mappings().all()
    ]


__all__ = [
    "AggregationOffer",
    "AggregationResult",
    "AggregationRule",
    "DEFAULT_AGGREGATION_RULES",
    "aggregate_inventory_offers",
    "load_aggregation_rules",
]
