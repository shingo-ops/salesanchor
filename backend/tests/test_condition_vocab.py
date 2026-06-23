from __future__ import annotations

from app.services.condition_vocab import (
    GRADE_VALUES,
    LEGACY_CONDITION_TO_CURRENT,
    axes_to_aggkey,
    condition_axes,
    condition_is_canonical,
    normalize_condition,
    unit_default_search_cond,
)
from app.services.inventory_axes import (
    build_condition_filter_clause,
    project_inventory_axes,
    resolve_aggkey,
    resolve_condition_view,
)


def test_legacy_opened_maps_to_unknown() -> None:
    assert LEGACY_CONDITION_TO_CURRENT["opened"] == "unknown"
    assert normalize_condition("opened") == "unknown"
    assert condition_is_canonical("opened") is True


def test_bulk_is_not_a_grade_value() -> None:
    assert "bulk" not in GRADE_VALUES


def test_bulk_is_excluded_from_axes() -> None:
    assert condition_axes("bulk") == {}


def test_box_and_case_default_to_unsearched() -> None:
    assert unit_default_search_cond("box") == "unsearched"
    assert unit_default_search_cond("case") == "unsearched"


def test_other_units_do_not_force_search_cond() -> None:
    assert unit_default_search_cond("pack") is None
    assert unit_default_search_cond("piece") is None
    assert unit_default_search_cond(None) is None


def test_packaging_units_default_search_cond_is_applied_in_projection() -> None:
    sealed_box = project_inventory_axes("sealed", "box")
    damaged_case = project_inventory_axes("damage", "case")
    assert sealed_box.search_cond == "unsearched"
    assert damaged_case.search_cond == "unsearched"
    assert damaged_case.seal == "sealed"
    assert damaged_case.damage is True


def test_bulk_projection_isolated_without_axes() -> None:
    projection = project_inventory_axes("bulk", "box")
    assert projection.isolated is True
    assert projection.seal is None
    assert projection.search_cond is None
    assert projection.grade is None


def test_axes_to_aggkey_round_trips_ver41_keys_and_excludes_pack() -> None:
    assert (
        axes_to_aggkey(
            unit="box",
            seal="shrink",
            search_cond="unsearched",
            damage=False,
        )
        == "Sealed box"
    )
    assert (
        axes_to_aggkey(
            unit="box",
            seal="no_shrink",
            search_cond="unsearched",
            damage=False,
        )
        == "No shrink box"
    )
    assert (
        axes_to_aggkey(
            unit="box",
            seal="sealed",
            search_cond="unsearched",
            damage=True,
        )
        == "Damaged sealed box"
    )
    assert (
        axes_to_aggkey(
            unit="case",
            seal="sealed",
            search_cond="unsearched",
            damage=False,
        )
        == "Case"
    )
    assert axes_to_aggkey(unit="pack", search_cond="unsearched") is None
    assert axes_to_aggkey(unit="bulk", seal="sealed", damage=False) is None


def test_resolve_condition_view_prefers_axes_and_falls_back_to_raw_condition() -> None:
    with_axes = {
        "condition": "unknown",
        "unit": "box",
        "seal": "shrink",
        "search_cond": "unsearched",
        "grade": None,
        "damage": False,
    }
    fallback_only = {"raw_condition": "unknown"}

    assert resolve_condition_view(with_axes) == "Sealed box"
    assert resolve_aggkey(with_axes) == "Sealed box"
    assert resolve_condition_view(fallback_only) == "unknown"
    assert resolve_aggkey(fallback_only) == "unknown"


def test_condition_filter_clause_translates_ver41_labels_to_axes_only() -> None:
    clause, params = build_condition_filter_clause(
        ["Sealed box", "Case", "Unsearched pack"]
    )

    assert clause is not None
    assert clause == (
        "(COALESCE(NULLIF(i.unit, ''), p.unit) = :cond0_unit AND i.seal = :cond0_seal "
        "AND i.damage = :cond0_damage) OR "
        "(COALESCE(NULLIF(i.unit, ''), p.unit) = :cond1_unit AND i.seal = :cond1_seal "
        "AND i.damage = :cond1_damage) OR "
        "(COALESCE(NULLIF(i.unit, ''), p.unit) = :cond2_unit AND i.search_cond = :cond2_search_cond "
        "AND i.damage = :cond2_damage)"
    )
    assert params["cond0_unit"] == "box"
    assert params["cond0_seal"] == "shrink"
    assert params["cond0_damage"] is False

    assert params["cond1_unit"] == "case"
    assert params["cond1_seal"] == "sealed"
    assert params["cond1_damage"] is False

    assert params["cond2_unit"] == "pack"
    assert params["cond2_search_cond"] == "unsearched"
    assert params["cond2_damage"] is False


def test_condition_filter_clause_keeps_sealed_box_grouped_and_excludes_unit_only_matches() -> None:
    clause, params = build_condition_filter_clause(["Sealed box"])

    assert clause is not None
    assert clause == (
        "(COALESCE(NULLIF(i.unit, ''), p.unit) = :cond0_unit AND i.seal = :cond0_seal "
        "AND i.damage = :cond0_damage)"
    )
    assert " OR COALESCE(NULLIF(i.unit, ''), p.unit) = :cond0_unit" not in clause
    assert params["cond0_unit"] == "box"
    assert params["cond0_seal"] == "shrink"
    assert params["cond0_damage"] is False


def test_condition_filter_clause_translates_current_condition_to_axes() -> None:
    clause, params = build_condition_filter_clause(["sealed"])

    assert clause is not None
    assert clause == "(i.seal = :cond0_seal AND i.damage = :cond0_damage)"
    assert params["cond0_seal"] == "sealed"
    assert params["cond0_damage"] is False
    assert "i.condition" not in clause


def test_condition_filter_clause_rejects_out_of_scope_tokens() -> None:
    clause, params = build_condition_filter_clause(["bulk"])

    assert clause == "(FALSE)"
    assert params == {}
