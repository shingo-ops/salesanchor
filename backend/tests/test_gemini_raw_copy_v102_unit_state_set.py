"""v102 の「状態の単位を優先」と分類「セット系」（便SU）の試験。DB なし。原文は社外秘のため使わず、作り例のみ。

設計: docs/handoff/v102-unit-state-set/card-SU.md
"""
from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services import v102_buyback_unit_svc as bb
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from tests.test_gemini_raw_copy_v102_product_first import _COND, _STATUS, _UNITS, _cond, _it

_UNITS_SU = {**_UNITS, "パック": ("Pack", "パック系"), "セット": ("Set", "複合"), "Set": ("Set", "複合")}
_COND_SU = [*_COND, _cond("CN0006", "Opened box", 3, "", "開封済み"), _cond("CN0009", "Opened pack", 3, "パック系", "パック開封")]
_MASTERS = {
    "cond_entries": _COND_SU, "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS_SU, "status_entries": _STATUS,
}
_PRODUCTS = (
    ProductEntry(id=1, product_code=None, mark=None, work_id=1, search_keywords=("サンプル拡張",), exclude_keywords=()),
    ProductEntry(id=5, product_code=None, mark=None, work_id=1, search_keywords=("サンプルセット",), exclude_keywords=()),
)
_CONDITION_UNIT = {"Sealed box": "Box", "Opened box": "Box", "Case": "Case", "Opened pack": "Pack"}


def _masters(kubun_of_5="セット系", condition_unit=None, set_unit="Set"):
    kubun = {"1": "箱系", "5": kubun_of_5}
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun=kubun, ignore_phrases=(),
        condition_unit=_CONDITION_UNIT if condition_unit is None else condition_unit, set_unit=set_unit,
    )


def _one(raw, item, masters):
    parsed, errors = v101.parse_v101_response(json.dumps({"items": [item]}, ensure_ascii=False), raw, status_entries=_STATUS)
    assert errors == []
    extracted, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=masters, **_MASTERS
    )
    (row,) = extracted
    return row


def _box(raw, quantity="1", masters=None):
    return _one(raw, _it([1, 2], "1,500円", quantity), masters or _masters())


def _set(raw, quantity="1", masters=None):
    return _one(raw, _it([1, 2], "1,500円", quantity), masters or _masters())


# --- 1-1 状態の単位を優先 -----------------------------------------------------------------------


def test_opened_box_word_overrides_pack_unit_to_box():
    row = _box("サンプル拡張 開封済み\n3パック@1,500円", "3")
    assert (row["condition"], row["unit"]) == ("Opened box", "Box")
    assert row["condition_basis"].startswith("R3:")
    assert row["unit_basis"]["from_condition"] == "Opened box" and row["unit_basis"]["reason"] == pf.UNIT_BASIS_STATE_WORD


def test_opened_box_word_overrides_conditional_unit_ko_to_box_when_product_is_unknown():
    row = _box("未登録の品 開封済み\n10個@1,500円", "10")
    assert row["product_category"] == "不明"
    assert (row["condition"], row["unit"]) == ("Opened box", "Box")
    assert row["unit_basis"]["reason"] == pf.UNIT_BASIS_STATE_WORD


def test_box_product_with_conditional_unit_ko_still_becomes_box_by_the_existing_rule():
    row = _box("サンプル拡張 開封済み\n10個@1,500円", "10")
    assert (row["condition"], row["unit"]) == ("Opened box", "Box")


def test_default_state_r4_with_pack_unit_is_not_changed():
    row = _box("サンプル拡張\n3パック@1,500円", "3")
    assert row["condition_basis"].startswith("R5")
    assert row["unit"] == "Pack" and "reason" not in row["unit_basis"]


def test_state_unit_equal_to_current_unit_is_not_changed():
    row = _box("サンプル拡張 開封済み\n3BOX@1,500円", "3")
    assert (row["condition"], row["unit"]) == ("Opened box", "Box")
    assert "reason" not in row["unit_basis"] and "from_condition" not in row["unit_basis"]


def test_state_without_unit_in_masters_is_not_changed():
    row = _box("サンプル拡張 開封済み\n3パック@1,500円", "3", _masters(condition_unit={"Sealed box": "Box"}))
    assert row["unit"] == "Pack" and "reason" not in row["unit_basis"]


# --- 1-2 分類セット系 ---------------------------------------------------------------------------


def test_set_category_without_unit_and_state_word_is_set_and_sealed_box():
    row = _set("サンプルセット\n@1,500円", "none")
    assert (row["condition"], row["unit"]) == ("Sealed box", "Set")
    assert row["product_category"] == "セット系" and row["unit_basis"][pf.UNIT_BASIS_FROM_CATEGORY] == "セット系"
    assert "from_condition" not in row["unit_basis"]


def test_set_category_with_set_count_unit_is_set_and_sealed_box():
    row = _set("サンプルセット\n200セット@1,500円", "200")
    assert (row["condition"], row["unit"]) == ("Sealed box", "Set")


def test_set_category_with_written_box_unit_keeps_box():
    row = _set("サンプルセット\n50BOX@1,500円", "50")
    assert (row["condition"], row["unit"]) == ("Sealed box", "Box")
    assert pf.UNIT_BASIS_FROM_CATEGORY not in row["unit_basis"]


def test_set_category_with_state_word_keeps_set_unit():
    row = _set("サンプルセット 開封済み\n@1,500円", "none")
    assert (row["condition"], row["unit"]) == ("Opened box", "Set")


def test_set_category_with_state_word_and_pack_unit_is_not_overridden():
    row = _set("サンプルセット 開封済み\n3パック@1,500円", "3")
    assert (row["condition"], row["unit"]) == ("Opened box", "Pack")


def test_box_category_without_unit_keeps_unit_from_condition():
    row = _box("サンプル拡張\n@1,500円", "none")
    assert (row["condition"], row["unit"]) == ("Sealed box", "Box")
    assert row["unit_basis"]["from_condition"] == "Sealed box"


def test_without_set_row_in_masters_set_category_falls_back_to_condition_unit():
    row = _set("サンプルセット\n@1,500円", "none", _masters(set_unit=None))
    assert (row["condition"], row["unit"]) == ("Sealed box", "Box")


# --- 1-4 分類の行が無い（セット系に属する商品が無い）とき -----------------------------------------


def test_product_not_in_set_category_behaves_as_before():
    row = _set("サンプルセット\n@1,500円", "none", _masters(kubun_of_5="シングル系"))
    assert row["product_category"] == "シングル系" and row["unit"] != "Set"


# --- ローダー -------------------------------------------------------------------------------------


def test_loader_reads_set_unit_by_code(monkeypatch):
    monkeypatch.setattr(pf, "load_product_entries", lambda s: list(_PRODUCTS))
    monkeypatch.setattr(pf, "load_product_kubun_type_map", lambda s: {"1": "箱系"})
    calls = []

    def execute(stmt, params=None):
        sql = str(stmt)
        calls.append((sql, params))
        rows = (
            [] if "type_master" in sql else [("Set",)] if "line_units" in sql and "code" in sql
            else [("Sealed box", "Box")] if "line_conditions" in sql else []
        )
        return SimpleNamespace(fetchall=lambda: rows)

    session = MagicMock()
    session.execute.side_effect = execute
    masters = pf.load_product_first_masters(session)
    assert masters.set_unit == "Set"
    assert any(p == {"code": pf.UNIT_SET_CODE} for _s, p in calls) and pf.UNIT_SET_CODE == "UN0005"


# --- 1-3 便BB の対象外 ---------------------------------------------------------------------------


def _bb_item(category):
    return {
        "unit_basis": {"alias": None}, "condition_basis": "R4:単位既定", "status_effect": "included",
        "product_category": category,
    }


_BB_VALUES = {"pid_resolved": True, "product_id": 1, "price_normalized": Decimal("1000")}


def test_buyback_skips_set_category():
    assert bb.is_candidate(_bb_item("セット系"), _BB_VALUES, {}) is False


def test_buyback_still_targets_box_category():
    assert bb.is_candidate(_bb_item("箱系"), _BB_VALUES, {}) is True


def test_dataclass_default_keeps_old_constructor_working():
    m = ProductFirstMasters(product_entries=(), product_kubun={}, condition_unit={}, ignore_phrases=())
    assert replace(m).set_unit is None
