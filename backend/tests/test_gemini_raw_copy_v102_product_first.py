"""試作版 v102（商品を先に決めて、単位 → 状態 → 状態から単位 を出す流れ）の単体試験。

設計: docs/handoff/prototype-v102-product-first/design.md
原文は社外秘のため使わない。商品名・言い回しはすべて作り例。DB には触れない（マスタは引数で渡す）。
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.tools import prompt_ab as pab

_UNITS = {
    "BOX": ("Box", "箱系"), "box": ("Box", "箱系"), "Box": ("Box", "箱系"),
    "カートン": ("Case", "箱系大"), "Case": ("Case", "箱系大"),
    "piece": ("Piece", "単品系"), "Piece": ("Piece", "単品系"),
    "個": ("個", "条件つき"),
}


def _cond(code, canonical, priority, app_kubun, search_kw):
    return {
        "cond_id": f"c-{code}", "code": code, "canonical": canonical, "priority": priority,
        "app_kubun": app_kubun, "search_kw": search_kw, "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
    }


_COND = [
    _cond("CN0008", "FLAG_SINGLE", 1, "枚系,単位不明", "PSA,SR"),
    _cond("CN0002", "Damaged case", 2, "箱系大", "難あり"),
    _cond("CN0004", "Damaged sealed box", 2, "箱系", "難あり,ダメージ"),
    _cond("CN0003", "Sealed box", 4, "箱系", "シュリンク付き"),
    _cond("CN0001", "Case", 4, "箱系大", "通常品"),
    _cond("CN0010", "Searched pack", 2, "パック系", "サーチ済"),
]
_STATUS = [
    {"canonical": "sold_out", "search_pattern": "完売", "exclude_pattern": "", "priority": 1,
     "match_type": "LITERAL", "effect": "EXCLUDE"},
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99,
     "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_MASTERS = {
    "cond_entries": _COND, "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS, "status_entries": _STATUS,
}
_PRODUCTS = (
    ProductEntry(id=1, product_code=None, mark=None, work_id=1, search_keywords=("サンプル拡張",), exclude_keywords=()),
    ProductEntry(id=2, product_code=None, mark=None, work_id=1, search_keywords=("OP-14",), exclude_keywords=()),
    ProductEntry(id=3, product_code=None, mark=None, work_id=1, search_keywords=("サンプルカード",), exclude_keywords=()),
    ProductEntry(id=4, product_code=None, mark=None, work_id=1, search_keywords=("ONE PIECE DAY25",), exclude_keywords=()),
)
_PRODUCT_KUBUN = {"1": "箱系", "2": "箱系", "3": "シングル系", "4": "シングル系"}
_CONDITION_UNIT = {"Sealed box": "Box", "Damaged sealed box": "Box", "Case": "Case", "Damaged case": "Case"}


def _pf(phrases=()):
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun=_PRODUCT_KUBUN, condition_unit=_CONDITION_UNIT, ignore_phrases=tuple(phrases),
    )


def _it(lines, price, quantity="1"):
    return {"lines": list(lines), "price": price, "quantity": quantity}


def _extract(raw, *items, phrases=(), product_first="default"):
    """v102 の経路で取り出す。product_first="default" は作り例のマスタ、None は渡さない（v10.2 のまま）。"""
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": list(items)}, ensure_ascii=False), raw, status_entries=_STATUS
    )
    assert errors == []
    masters = _pf(phrases) if product_first == "default" else product_first
    extracted, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=masters, **_MASTERS
    )
    return extracted


def _one(raw, *items, **kw):
    (row,) = _extract(raw, *items, **kw)
    return row


# --- 状態と単位（商品が箱系） -----------------------------------------------------------------


def test_box_product_without_unit_is_sealed_box_and_box():
    row = _one("サンプル拡張\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert (row["condition"], row["unit"]) == ("Sealed box", "Box")
    assert row["product_id"] == 1 and row["product_category"] == "箱系" and row["match_status"] == "matched"


def test_box_product_with_shrink_word_and_no_unit_is_sealed_box_and_box():
    row = _one("サンプル拡張 シュリンク付き\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert (row["condition"], row["unit"]) == ("Sealed box", "Box")


def test_box_product_with_damage_word_and_conditional_unit_is_damaged_sealed_box_and_box():
    row = _one("サンプル拡張 難あり\n3個@1,500円", _it([1, 2], "1,500円", "3"))
    assert (row["condition"], row["unit"]) == ("Damaged sealed box", "Box")


def test_conditional_unit_on_single_product_is_kept():
    row = _one("サンプルカード\n3個@500円", _it([1, 2], "500円", "3"))
    assert row["unit"] == "個"


# --- カートン（名前の行・価格の行） -----------------------------------------------------------


def test_carton_on_name_line_is_case_and_case():
    row = _one("OP-14 カートン\n2@160,000円", _it([1, 2], "160,000円", "2"))
    assert (row["condition"], row["unit"]) == ("Case", "Case")
    assert row["unit_basis"]["match"] == "boundary" and row["unit_basis"]["line"] == 1


def test_carton_on_price_line_is_case_and_case():
    row = _one("【カートン】 OP-14 3@160000", _it([1], "160000", "3"))
    assert (row["condition"], row["unit"]) == ("Case", "Case")
    assert row["unit_basis"]["alias"] == "カートン"


def test_unit_after_digit_still_uses_position_rule_on_price_line():
    row = _one("サンプルカード 100piece/10,000円", _it([1], "10,000円", "100"))
    assert row["unit"] == "Piece" and row["unit_basis"]["match"] == "position"


# --- 単位にしない言い回し・検索ワードの範囲 ---------------------------------------------------


_PHRASE_RAW = "ONE PIECE ほにゃらら 100@1400"


def test_alias_inside_ignore_phrase_is_not_taken():
    row = _one(_PHRASE_RAW, _it([1], "1400", "100"), phrases=("ONE PIECE",))
    assert row["unit"] == "none"
    excluded = row["unit_basis"]["excluded"]
    assert excluded and {e["alias"].lower() for e in excluded} == {"piece"}
    assert {(e["line"], e["role"], e["reason"]) for e in excluded} == {(1, "price", pf.REASON_IGNORE_PHRASE)}


def test_alias_is_taken_when_ignore_phrase_table_is_empty():
    row = _one(_PHRASE_RAW, _it([1], "1400", "100"), phrases=())
    assert row["unit"] == "Piece" and row["unit_basis"]["match"] == "boundary"


def test_ignore_phrase_allows_zero_or_more_spaces_and_width_differences():
    row = _one("ＯＮＥPIECE ほにゃらら 100@1400", _it([1], "1400", "100"), phrases=("ONE PIECE",))
    assert row["unit"] == "none"


def test_alias_inside_matched_product_keyword_is_not_taken():
    row = _one("ONE PIECE DAY25 3@1,000", _it([1], "1,000", "3"))
    assert row["product_id"] == 4 and row["unit"] == "none"
    assert row["unit_basis"]["excluded"][0]["reason"] == pf.REASON_KEYWORD_RANGE


# --- 商品も単位も不明 -------------------------------------------------------------------------


def test_unknown_product_and_unit_is_unknown_condition_with_review_reason():
    row = _one("ほにゃらら 100@1400", _it([1], "1400", "100"))
    assert row["product_category"] == "不明" and row["match_status"] == "unmatched" and row["product_id"] is None
    assert row["condition"] == pf.CONDITION_UNKNOWN != pf.FLAG_SINGLE_CANONICAL
    assert {"line": 1, "kind": "condition_unknown"} in row["review"]


def test_unknown_condition_review_reason_is_not_added_to_known_rows():
    row = _one("サンプル拡張\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert all(r["kind"] != "condition_unknown" for r in row["review"])


# --- 補った区分と別の区分の状態にも当たる（2候補以上） ------------------------------------------


def test_box_condition_with_pack_word_stays_box_and_adds_multiple_candidates_review():
    row = _one("サンプル拡張 シュリンク付き サーチ済\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert (row["condition"], row["unit"]) == ("Sealed box", "Box")
    assert {"line": 2, "kind": pf.REVIEW_MULTIPLE_CANDIDATES, "codes": ["CN0010"]} in row["review"]


def test_multiple_candidates_ignores_single_rule_and_rows_without_kubun():
    row = _one("サンプル拡張 SR\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert all(r["kind"] != pf.REVIEW_MULTIPLE_CANDIDATES for r in row["review"])


# --- 完売・記録 -------------------------------------------------------------------------------


def test_sold_out_row_gets_unit_and_condition_with_same_flow_and_keeps_status():
    row = _one("サンプル拡張 完売\n@1,500円", _it([1, 2], "1,500円", "none"))
    assert row["status"] == "sold_out" and (row["condition"], row["unit"]) == ("Sealed box", "Box")


def test_record_has_product_and_basis_fields():
    row = _one("サンプル拡張\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert {"product_id", "product_category", "match_status", "match_candidates", "unit_basis", "condition_basis"} <= set(row)
    assert row["unit_basis"]["from_condition"] == "Sealed box"


# --- 渡さないとき・マスタの検査 ---------------------------------------------------------------


def test_without_product_first_output_is_the_v102_one_and_has_no_new_keys():
    row = _one("サンプル拡張\n3@1,500円", _it([1, 2], "1,500円", "3"), product_first=None)
    assert "product_id" not in row and "unit_basis" not in row


def test_v101_output_is_unchanged_even_if_product_first_is_passed():
    parsed, _ = v101.parse_v101_response(
        json.dumps({"items": [_it([1, 2], "1,500円", "3")]}, ensure_ascii=False), "サンプル拡張\n3@1,500円", status_entries=_STATUS
    )
    raw = "サンプル拡張\n3@1,500円"
    plain, _f = v101.extract_v101_items(parsed, raw, order=None, reassign=True, **_MASTERS)
    given, _f = v101.extract_v101_items(parsed, raw, order=None, reassign=True, product_first=_pf(), **_MASTERS)
    assert plain == given


@pytest.mark.parametrize("empty", ["product_entries", "product_kubun", "condition_unit"])
def test_empty_master_stops_with_error(empty):
    base = _pf()
    broken = ProductFirstMasters(**{**base.__dict__, empty: type(getattr(base, empty))()})
    with pytest.raises(ValueError, match="マスタが空です"):
        pf.check_product_first_masters(broken)


def test_empty_ignore_phrases_is_allowed():
    pf.check_product_first_masters(_pf(phrases=()))


# --- 読み込み（DB は差し替え） ----------------------------------------------------------------


def test_loader_reads_condition_units_and_active_ignore_phrases(monkeypatch):
    monkeypatch.setattr(pf, "load_product_entries", lambda s: list(_PRODUCTS))
    monkeypatch.setattr(pf, "load_product_kubun_type_map", lambda s: dict(_PRODUCT_KUBUN))
    calls = []

    def execute(stmt):
        sql = str(stmt)
        calls.append(sql)
        rows = [("Sealed box", "Box")] if "line_conditions" in sql else [("ONE PIECE",)]
        return SimpleNamespace(fetchall=lambda: rows)

    session = MagicMock()
    session.execute.side_effect = execute
    masters = pf.load_product_first_masters(session)
    assert masters.condition_unit == {"Sealed box": "Box"} and masters.ignore_phrases == ("ONE PIECE",)
    assert any("line_unit_ignore_phrases" in c and "is_active = TRUE" in c for c in calls)


def test_loader_stops_when_condition_units_are_empty(monkeypatch):
    monkeypatch.setattr(pf, "load_product_entries", lambda s: list(_PRODUCTS))
    monkeypatch.setattr(pf, "load_product_kubun_type_map", lambda s: dict(_PRODUCT_KUBUN))
    session = MagicMock()
    session.execute.return_value = SimpleNamespace(fetchall=lambda: [])
    with pytest.raises(ValueError, match="状態ごとの単位"):
        pf.load_product_first_masters(session)


def test_prompt_ab_loads_product_first_only_when_asked(monkeypatch):
    sentinel = _pf()
    monkeypatch.setattr(pab, "load_condition_entries", lambda s: [])
    monkeypatch.setattr(pab, "load_status_master", lambda s: [])
    monkeypatch.setattr(pab, "load_lookup_maps", lambda s: (None, None, None, None, {}, {}))
    monkeypatch.setattr(pab, "load_product_first_masters", lambda s: sentinel)
    assert "product_first" not in pab._load_v10_masters(MagicMock())
    assert pab._load_v10_masters(MagicMock(), product_first=True)["product_first"] is sentinel
