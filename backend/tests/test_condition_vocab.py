from __future__ import annotations

from app.services.condition_vocab import (
    LEGACY_CONDITION_TO_CURRENT,
    unit_default_search_cond,
)


def test_legacy_opened_maps_to_unknown() -> None:
    assert LEGACY_CONDITION_TO_CURRENT["opened"] == "unknown"


def test_box_and_case_default_to_unsearched() -> None:
    assert unit_default_search_cond("box") == "unsearched"
    assert unit_default_search_cond("case") == "unsearched"


def test_other_units_do_not_force_search_cond() -> None:
    assert unit_default_search_cond("pack") is None
    assert unit_default_search_cond("piece") is None
    assert unit_default_search_cond(None) is None

