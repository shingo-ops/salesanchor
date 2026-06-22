from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from app.services.condition_vocab import (
    CONDITION_VALUES,
    axes_to_aggkey,
    condition_axes,
    normalize_condition,
    VER41_TO_CONDITION,
    VER41_TO_UNIT,
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


@dataclass(frozen=True)
class InventoryConditionResolution:
    """condition / 軸列から読み手が使う値を 1 か所で解決する。"""

    condition: str | None = None
    aggkey: str | None = None
    raw_condition: str | None = None
    unit: str | None = None
    seal: str | None = None
    search_cond: str | None = None
    grade: str | None = None
    damage: bool | None = None
    axes_present: bool = False


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
    if unit is not None and str(unit).strip().lower() in {"box", "case"} and "search_cond" not in axes:
        axes["search_cond"] = "unsearched"

    return InventoryAxisProjection(
        seal=axes.get("seal"),
        search_cond=axes.get("search_cond"),
        grade=axes.get("grade"),
        damage=axes.get("damage"),
        normalized_condition=normalized,
        axes=axes,
    )


def _get_value(source: Mapping[str, Any] | Any, keys: tuple[str, ...]) -> Any:
    if isinstance(source, Mapping):
        for key in keys:
            if key in source:
                value = source[key]
                if value not in (None, ""):
                    return value
    else:
        for key in keys:
            if hasattr(source, key):
                value = getattr(source, key)
                if value not in (None, ""):
                    return value
    return None


def _normalize_bool_axis(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    lowered = str(value).strip().lower()
    if lowered in {"true", "t", "1", "yes", "y"}:
        return True
    if lowered in {"false", "f", "0", "no", "n"}:
        return False
    return None


def resolve_condition_resolution(source: Mapping[str, Any] | Any) -> InventoryConditionResolution:
    raw_condition = normalize_condition(_get_value(source, ("condition", "Condition")))
    unit = _get_value(source, ("unit", "Unit"))
    seal = _get_value(source, ("seal", "Seal"))
    search_cond = _get_value(source, ("search_cond", "searchCond", "Search Cond"))
    grade = _get_value(source, ("grade", "Grade"))
    damage = _normalize_bool_axis(_get_value(source, ("damage", "Damage")))

    axes_present = any(value is not None for value in (seal, search_cond, grade, damage))
    aggkey = None
    if axes_present:
        aggkey = axes_to_aggkey(
            unit=unit,
            seal=seal,
            search_cond=search_cond,
            grade=grade,
            damage=damage,
        )

    resolved = aggkey if aggkey is not None else raw_condition
    return InventoryConditionResolution(
        condition=resolved,
        aggkey=resolved,
        raw_condition=raw_condition,
        unit=None if unit is None else str(unit),
        seal=None if seal is None else str(seal),
        search_cond=None if search_cond is None else str(search_cond),
        grade=None if grade is None else str(grade),
        damage=damage,
        axes_present=axes_present,
    )


def resolve_condition_view(source: Mapping[str, Any] | Any) -> str | None:
    return resolve_condition_resolution(source).condition


def resolve_aggkey(source: Mapping[str, Any] | Any) -> str | None:
    return resolve_condition_resolution(source).aggkey


def build_condition_filter_clause(
    values: Iterable[str],
    *,
    condition_column: str = "i.condition",
    unit_column: str = "COALESCE(NULLIF(i.unit, ''), p.unit)",
    seal_column: str = "i.seal",
    search_cond_column: str = "i.search_cond",
    grade_column: str = "i.grade",
    damage_column: str = "i.damage",
    param_prefix: str = "cond",
) -> tuple[str | None, dict[str, Any]]:
    """condition/condition_in を軸優先の WHERE 句へ変換する。

    ver4.1 表記は軸に翻訳しつつ、並行期間の安全網として condition 列の
    直接比較も OR で残す。current condition のみの値は condition 列で受ける。
    """

    clauses: list[str] = []
    params: dict[str, Any] = {}

    for idx, raw_value in enumerate(values):
        token = str(raw_value).strip()
        if not token:
            continue

        label_condition = VER41_TO_CONDITION.get(token)
        label_unit = VER41_TO_UNIT.get(token)
        current_condition = normalize_condition(token)
        if current_condition is None:
            current_condition = label_condition

        part_clauses: list[str] = []
        if label_condition is not None:
            part_clauses.append(f"{condition_column} = :{param_prefix}{idx}_condition")
            params[f"{param_prefix}{idx}_condition"] = label_condition

        if label_unit is not None and label_condition is not None:
            axes = condition_axes(label_condition)
            part_clauses.append(f"{unit_column} = :{param_prefix}{idx}_unit")
            params[f"{param_prefix}{idx}_unit"] = label_unit
            if seal := axes.get("seal"):
                part_clauses.append(f"{seal_column} = :{param_prefix}{idx}_seal")
                params[f"{param_prefix}{idx}_seal"] = seal
            if search_cond := axes.get("search_cond"):
                part_clauses.append(f"{search_cond_column} = :{param_prefix}{idx}_search_cond")
                params[f"{param_prefix}{idx}_search_cond"] = search_cond
            if grade := axes.get("grade"):
                part_clauses.append(f"{grade_column} = :{param_prefix}{idx}_grade")
                params[f"{param_prefix}{idx}_grade"] = grade
            if "damage" in axes:
                part_clauses.append(f"{damage_column} = :{param_prefix}{idx}_damage")
                params[f"{param_prefix}{idx}_damage"] = bool(axes["damage"])

        if current_condition is not None and label_condition is None:
            part_clauses.append(f"{condition_column} = :{param_prefix}{idx}_current")
            params[f"{param_prefix}{idx}_current"] = current_condition

        if part_clauses:
            clauses.append("(" + " OR ".join(dict.fromkeys(part_clauses)) + ")")

    if not clauses:
        return None, {}
    return " OR ".join(clauses), params


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
