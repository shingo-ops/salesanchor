from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.condition_vocab import (
    CONDITION_VALUES,
    condition_axes,
    normalize_condition,
    unit_default_search_cond,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InventoryAxisProjection:
    seal: str | None = None
    search_cond: str | None = None
    grade: str | None = None
    damage: bool | None = None
    isolated: bool = False
    isolation_reason: str | None = None
    normalized_condition: str | None = None
    axes: dict[str, Any] = field(default_factory=dict)


def project_inventory_axes(condition: str | None, unit: str | None) -> InventoryAxisProjection:
    """condition + unit から新規軸へ安全に投影する。

    - bulk / unknown / 認識不能値は軸を埋めず隔離。
    - box / case は unit 由来の search_cond=unsearched を補完する。
    - condition 由来の search_cond があれば優先する。
    """

    normalized = normalize_condition(condition)
    if normalized is None:
        return InventoryAxisProjection(
            isolated=True,
            isolation_reason="missing_condition",
        )

    if normalized not in set(CONDITION_VALUES):
        return InventoryAxisProjection(
            isolated=True,
            isolation_reason=f"unrecognized_condition:{normalized}",
            normalized_condition=normalized,
        )

    if normalized in {"bulk", "unknown"}:
        return InventoryAxisProjection(
            isolated=True,
            isolation_reason=f"{normalized}_out_of_scope",
            normalized_condition=normalized,
        )

    axes = dict(condition_axes(normalized))
    default_search_cond = unit_default_search_cond(unit)
    if default_search_cond and "search_cond" not in axes:
        axes["search_cond"] = default_search_cond

    return InventoryAxisProjection(
        seal=axes.get("seal"),
        search_cond=axes.get("search_cond"),
        grade=axes.get("grade"),
        damage=axes.get("damage"),
        normalized_condition=normalized,
        axes=axes,
    )


def log_axis_isolation(
    *,
    logger_: logging.Logger,
    condition: str | None,
    unit: str | None,
    context: str,
    projection: InventoryAxisProjection,
) -> None:
    if not projection.isolated:
        return
    logger_.warning(
        "[inventory_axes] isolated condition for %s: condition=%r unit=%r reason=%s",
        context,
        condition,
        unit,
        projection.isolation_reason,
    )

