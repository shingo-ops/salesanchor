"""試作版 v102（商品を先に決めて、単位 → 状態 → 状態から単位 を出す流れ）の単体試験。

設計: docs/handoff/prototype-v102-product-first/design.md
原文は社外秘のため使わない。商品名・言い回しはすべて作り例。DB には触れない（マスタは引数で渡す）。
"""
from __future__ import annotations

import json
from datetime import date
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


def _extract(raw, *items, phrases=(), product_first="default", units=None):
    """v102 の経路で取り出す。product_first="default" は作り例のマスタ、None は渡さない（v10.2 のまま）。"""
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": list(items)}, ensure_ascii=False), raw, status_entries=_STATUS
    )
    assert errors == []
    masters = _pf(phrases) if product_first == "default" else product_first
    given = {**_MASTERS, "unit_alias_to_info": units} if units is not None else _MASTERS
    extracted, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=masters, **given
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


# --- 条件つきの単位は、ほかの行に決まった単位があればそちらを採る ----------------------------------------


def test_conditional_unit_on_price_line_yields_to_carton_on_another_line():
    row = _one("サンプル拡張\n1個 248,000円\nカートン", _it([1, 2, 3], "248,000円", "1"))
    assert (row["condition"], row["unit"]) == ("Case", "Case")
    basis = row["unit_basis"]
    assert basis["alias"] == "カートン" and basis["line"] == 3
    assert basis["overridden_alias"] == "個" and basis["override_reason"] == pf.REASON_COUNTER_OVERRIDDEN


def test_conditional_unit_alone_keeps_the_box_from_condition():
    row = _one("サンプル拡張\n1個 9,000円", _it([1, 2], "9,000円", "1"))
    assert (row["condition"], row["unit"]) == ("Sealed box", "Box")
    assert "override_reason" not in row["unit_basis"] and row["unit_basis"]["from_condition"] == "Sealed box"


def test_conditional_unit_is_kept_when_no_other_line_has_a_decided_unit():
    row = _one("サンプルカード\n3個@500円\nほにゃらら", _it([1, 2], "500円", "3"))
    assert row["unit"] == "個" and "override_reason" not in row["unit_basis"]


# --- 区切りは、文字の種類が変わる所でもよい -------------------------------------------------------

_PACK_UNITS = {**_UNITS, "パック": ("Pack", "パック系")}
_BARA = {**_PACK_UNITS, "バラパック": ("Pack", "パック系")}


def test_alias_next_to_other_script_is_taken():
    row = _one("バラパック買取品 3@1,000", _it([1], "1,000", "3"), units=_BARA)
    assert row["unit"] == "Pack" and row["unit_basis"]["alias"] == "バラパック"


def test_alias_missing_from_master_leaves_unit_none():
    row = _one("バラパック買取品 3@1,000", _it([1], "1,000", "3"), units=_UNITS)
    assert row["unit"] == "none"


def test_alias_inside_same_script_run_is_not_taken():
    row = _one("バラパック買取品 3@1,000", _it([1], "1,000", "3"), units=_PACK_UNITS)
    assert row["unit"] == "none"


@pytest.mark.parametrize("line, alias, expected", [
    ("バラパック買取品", "バラパック", True),
    ("プレミアムトレーナーボックス", "ボックス", False),
    ("ONE PIECE", "piece", True),
    ("onepiece", "piece", False),
    ("abcBOX", "box", False),
    ("ほにゃ個", "個", True),
    ("ほにゃらら個", "ほにゃ", False),
    ("カートン2", "カートン", True),
    ("2カートン", "カートン", True),
])
def test_boundary_candidates_by_script(line, alias, expected):
    assert bool(pf.boundary_candidates(line, [alias])) is expected


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


# --- 商品が決まらないときの要確認の理由 ---------------------------------------------------------


def _kinds(row):
    return [r["kind"] for r in row["review"]]


def test_unmatched_product_adds_product_not_in_master_review():
    row = _one("ほにゃらら 100@1400", _it([1], "1400", "100"))
    assert {"line": 1, "kind": pf.REVIEW_PRODUCT_NOT_IN_MASTER} in row["review"]


def test_ambiguous_product_adds_product_multiple_review_with_candidate_ids():
    row = _one("サンプル拡張 OP-14\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert row["match_status"] == "ambiguous" and row["match_candidates"] == [1, 2]
    assert {"line": 2, "kind": pf.REVIEW_PRODUCT_MULTIPLE, "candidates": [1, 2]} in row["review"]


def test_matched_with_boundary_dropped_keeps_record_without_product_boundary_review():
    products = (
        ProductEntry(id=1, product_code=None, mark=None, work_id=1, search_keywords=("サンプル拡張",), exclude_keywords=()),
        ProductEntry(id=9, product_code=None, mark=None, work_id=1, search_keywords=("ab",), exclude_keywords=()),
    )
    masters = ProductFirstMasters(
        product_entries=products, product_kubun={"1": "箱系", "9": "箱系"}, condition_unit=_CONDITION_UNIT, ignore_phrases=(),
    )
    row = _one("サンプル拡張 xabx\n3@1,500円", _it([1, 2], "1,500円", "3"), product_first=masters)
    assert row["match_status"] == "matched" and row["product_id"] == 1
    assert "product_boundary" not in _kinds(row)
    assert row["match_boundary_dropped"] == [9]


def test_matched_without_boundary_dropped_has_no_product_review():
    row = _one("サンプル拡張\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert row["match_status"] == "matched"
    assert not {pf.REVIEW_PRODUCT_NOT_IN_MASTER, pf.REVIEW_PRODUCT_MULTIPLE, "product_boundary"} & set(_kinds(row))
    assert row["match_boundary_dropped"] == []


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

    def execute(stmt, params=None):
        sql = str(stmt)
        calls.append(sql)
        rows = (
            [] if "type_master" in sql else [(7, date(2026, 10, 16))] if "release_date" in sql
            else [("Set",)] if "line_units" in sql and "line_conditions" not in sql
            else [("Sealed box", "Box")] if "line_conditions" in sql else [("ONE PIECE",)]
        )
        return SimpleNamespace(fetchall=lambda: rows)

    session = MagicMock()
    session.execute.side_effect = execute
    masters = pf.load_product_first_masters(session)
    assert masters.condition_unit == {"Sealed box": "Box"} and masters.ignore_phrases == ("ONE PIECE",)
    assert any("line_unit_ignore_phrases" in c and "is_active = TRUE" in c for c in calls)
    assert masters.product_release == {"7": date(2026, 10, 16)} and masters.posted_date is None


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


# --- 状態を決められなかった件は Error（便ER） ---------------------------------------------------

_ERROR_ROW = _cond("CN0012", "Error", 99, "", "")
_ERROR_ROW["effect"] = "EXCLUDE"


@pytest.fixture
def with_error_row(monkeypatch):
    monkeypatch.setitem(_MASTERS, "cond_entries", [*_COND, _ERROR_ROW])


def test_final_fallback_becomes_error_with_condition_unknown_review(with_error_row):
    row = _one("ほにゃらら 100@1400", _it([1], "1400", "100"))
    assert row["condition"] == "Error"
    assert row["condition_basis"] == "R4:単位既定:単位不明"  # basis は変えない（集計と〆の引き継ぎが読む）
    assert {"line": 1, "kind": "condition_unknown"} in row["review"]


def test_final_fallback_becomes_error_even_when_product_and_unit_are_known(with_error_row):
    row = _one("サンプルカード 3 piece @1,500円", _it([1], "1,500円", "3"))
    assert row["product_id"] == 3 and row["unit"] == "Piece"
    assert row["condition"] == "Error" and row["condition_basis"].endswith("単位不明")
    assert {"line": 1, "kind": "condition_unknown"} in row["review"]


def test_single_decided_by_word_stays_flag_single(with_error_row):
    row = _one("サンプルカード PSA 3@1,500円", _it([1], "1,500円", "3"))
    assert row["condition"] == pf.FLAG_SINGLE_CANONICAL and row["condition_basis"].startswith("R1:")
    assert all(r["kind"] != "condition_unknown" for r in row["review"])


def test_error_row_is_not_matched_by_any_text(with_error_row):
    row = _one("サンプル拡張 Error\n3@1,500円", _it([1, 2], "1,500円", "3"))
    assert row["condition"] == "Sealed box"


def test_without_error_row_it_falls_back_to_unknown_condition():
    row = _one("サンプルカード 3 piece @1,500円", _it([1], "1,500円", "3"))
    assert row["condition"] == pf.CONDITION_UNKNOWN
    assert {"line": 1, "kind": "condition_unknown"} in row["review"]


def test_shared_resolve_condition_v2_is_unchanged_by_the_error_row():
    """v6・v10.1・shadow が使う resolve_condition_v2 は Error を返さない（最終フォールバックは従来どおり FLAG_SINGLE）。"""
    from app.services.tcg_analyzer_svc import resolve_condition_v2
    entries = [*_COND, _ERROR_ROW]
    canonical, _cid, basis = resolve_condition_v2("ほにゃらら", "", "", entries, {})
    assert canonical == "FLAG_SINGLE" and basis.endswith("単位不明")
    assert resolve_condition_v2("ほにゃらら", "", "", _COND, {}) == (canonical, _cid, basis)  # Error の行の有無で結果が変わらない


# --- バルク系で状態語が無いとき Bulk（ADR-1021・便1） -------------------------------------------
# マスタの Bulk 行は search_kw が空の KEYWORD 行（どの文にも当たらない）。値は docs/handoff/g28-bulk-price/data/commit.sql と同じ

_BULK_ROW = {
    "cond_id": "c-CN0014", "code": "CN0014", "canonical": "Bulk", "priority": 10,
    "app_kubun": "", "search_kw": "", "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
}
_ERROR_ROW = {**_BULK_ROW, "cond_id": "c-CN0012", "code": "CN0012", "canonical": "Error", "priority": 99, "effect": "EXCLUDE"}
_BULK_COND = [*_COND, _BULK_ROW, _ERROR_ROW]
_BULK_PRODUCTS = (
    ProductEntry(id=11, product_code=None, mark=None, work_id=1, search_keywords=("バルクA",), exclude_keywords=()),
    ProductEntry(id=12, product_code=None, mark=None, work_id=1, search_keywords=("シングルB",), exclude_keywords=()),
    ProductEntry(id=13, product_code=None, mark=None, work_id=1, search_keywords=("箱C",), exclude_keywords=()),
    ProductEntry(id=14, product_code=None, mark=None, work_id=1, search_keywords=("セットD",), exclude_keywords=()),
)
_BULK_KUBUN = {"11": "バルク系", "12": "シングル系", "13": "箱系", "14": "セット系"}


def _bulk_row(raw, price="500円", cond_entries=None):
    masters = ProductFirstMasters(
        product_entries=_BULK_PRODUCTS, product_kubun=_BULK_KUBUN, condition_unit=_CONDITION_UNIT, ignore_phrases=(),
    )
    given = {**_MASTERS, "cond_entries": _BULK_COND if cond_entries is None else cond_entries}
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": [_it([1, 2], price, "3")]}, ensure_ascii=False), raw, status_entries=_STATUS
    )
    assert errors == []
    (row,) = v101.extract_v101_items(parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=masters, **given)[0]
    return row


def test_bulk_product_without_condition_word_is_bulk_r6():
    row = _bulk_row("バルクA\n3@500円")
    assert row["product_category"] == "バルク系"
    assert (row["condition"], row["condition_basis"]) == ("Bulk", pf.BASIS_BULK_DEFAULT) and pf.BASIS_BULK_DEFAULT == "R6:バルク既定"
    assert all(r["kind"] != "condition_unknown" for r in row["review"])


def test_bulk_product_with_condition_word_is_unchanged():
    row = _bulk_row("バルクA PSA\n3@500円")
    assert row["condition"] == "FLAG_SINGLE" and row["condition_basis"].startswith("R1:")


@pytest.mark.parametrize("raw,kubun", [
    ("シングルB\n3@500円", "シングル系"), ("箱C\n3@500円", "箱系"), ("セットD\n3@500円", "セット系"),
])
def test_non_bulk_kubun_without_condition_word_is_unchanged(raw, kubun):
    with_bulk = _bulk_row(raw)
    without_bulk = _bulk_row(raw, cond_entries=[*_COND, _ERROR_ROW])  # Bulk 行が無いマスタ（今の本番）
    assert with_bulk["product_category"] == kubun
    assert with_bulk["condition"] != "Bulk"
    assert (with_bulk["condition"], with_bulk["condition_basis"]) == (without_bulk["condition"], without_bulk["condition_basis"])


def test_no_product_without_condition_word_is_unchanged_error():
    row = _bulk_row("ほにゃらら\n3@500円")
    assert row["product_category"] == "不明" and row["condition"] == "Error"
    assert "condition_unknown" in [r["kind"] for r in row["review"]]


def test_single_product_flag_single_stays_error_not_bulk():
    row = _bulk_row("シングルB\n3@500円")
    assert row["condition"] == "Error"


def test_bulk_row_is_not_created_without_master_row_falls_back_to_error():
    row = _bulk_row("バルクA\n3@500円", cond_entries=[*_COND, _ERROR_ROW])
    assert row["condition"] == "Error"


def test_bulk_master_row_values_never_match_any_block():
    """search_kw が空の KEYWORD 行は、どの block にも当たらない（resolve_condition_v2 が Bulk を返さない）。"""
    from app.services.tcg_analyzer_svc import resolve_condition_v2

    assert _BULK_ROW["match_type"] == "KEYWORD" and _BULK_ROW["search_kw"] == "" and _BULK_ROW["priority"] > 0
    for block in ("", "Bulk", "バルク", "PSA 100枚", "通常品", "未開封", "状態A-", "枚 単品 SR"):
        for kubun in ("", "枚系", "単位不明", "箱系", "箱系大", "パック系", "条件つき", "単品系"):
            cond, _cid, _basis = resolve_condition_v2(block, "", kubun, _BULK_COND, {}, raw_memo=block)
            assert cond != "Bulk"


# --- 状態の価値順（ADR-1023）-----------------------------------------------------------------


def test_resolve_condition_picks_lowest_value_state_when_several_words_hit():
    """「美品」（傷あり）と「シュリンク無し」の両方に当たるとき、v102 は価値の低い No shrink box を採る。"""
    def vr(code, canonical, priority, app_kubun, kw, group, rank):
        return {**_cond(code, canonical, priority, app_kubun, kw), "value_group": group, "value_rank": rank}

    entries = [
        vr("CN0004", "Damaged sealed box", 2, "箱系", "潰れ,美品", "box", 2),
        vr("CN0005", "No shrink box", 3, "", "シュリンク無し", "box", 3),
        vr("CN0003", "Sealed box", 4, "箱系", "シュリンク付き", "box", 1),
    ]
    cond, basis, reviews = pf._resolve_condition("シュリンク無し美品", "箱系", "箱系", entries, {})
    assert cond == "No shrink box" and basis == "R3:シュリンク無し"


# --- 区分ごとに取れる単位の表（ADR-1041 便1。合成のデータ） --------------------------------------

_KUBUN_TABLE = {
    "箱系": frozenset({"Box", "Case", "Pack", "MasterCarton"}),
    "プロモパック系": frozenset({"Booklet", "Pack"}),
    "ブックレット系": frozenset({"Booklet"}),
}
_KUBUN_UNITS = {
    **_UNITS, "セット": ("Set", "複合"), "Set": ("Set", "複合"), "Pack": ("Pack", "パック系"), "Booklet": ("Booklet", "冊子系"),
    "MasterCarton": ("MasterCarton", "箱系大"),
}
_STATE_UNITS = {**_CONDITION_UNIT, "未開封": "Pack", "With booklet": "Booklet"}


def _kmasters(table=_KUBUN_TABLE, condition_unit=None):
    base = _pf()
    return ProductFirstMasters(**{**base.__dict__, "kubun_allowed_units": table, "condition_unit": condition_unit or _STATE_UNITS})


def _fix(kubun, unit, condition, *, table=_KUBUN_TABLE, unit_kubun="複合"):
    return pf._fix_unit_by_kubun(
        unit=unit, unit_kubun=unit_kubun, unit_basis={"line": 1}, product_kubun=kubun, product_id=1, condition=condition,
        masters=_kmasters(table), unit_alias_to_info=_KUBUN_UNITS,
    )


def test_kubun_table_box_with_set_is_replaced_by_state_unit_box_a():
    unit, unit_kubun, basis, reviews = _fix("箱系", "Set", "Sealed box")
    assert (unit, unit_kubun, reviews) == ("Box", "箱系", [])
    assert basis == {"line": 1, "kubun_unit_fix": "a", "kubun_unit_from": "Set"}


def test_kubun_table_box_with_set_end_to_end_becomes_box():
    masters = ProductFirstMasters(**{**_pf().__dict__, "kubun_allowed_units": _KUBUN_TABLE})
    row = _one("サンプル拡張\n3セット@1,500円", _it([1, 2], "1,500円", "3"), product_first=masters, units=_KUBUN_UNITS)
    assert (row["condition"], row["unit"], row["unit_kubun"]) == ("Sealed box", "Box", "箱系")
    assert row["unit_basis"]["kubun_unit_fix"] == "a" and row["unit_basis"]["kubun_unit_from"] == "Set"
    plain = _one("サンプル拡張\n3セット@1,500円", _it([1, 2], "1,500円", "3"), units=_KUBUN_UNITS)
    assert plain["unit"] == "Set" and "kubun_unit_fix" not in plain["unit_basis"]


def test_kubun_table_box_with_mastercarton_is_unchanged():
    unit, unit_kubun, basis, reviews = _fix("箱系", "MasterCarton", "Sealed box", unit_kubun="箱系大")
    assert (unit, unit_kubun, basis, reviews) == ("MasterCarton", "箱系大", {"line": 1}, [])


def test_kubun_table_promo_pack_with_case_and_state_pack_is_replaced_a():
    unit, unit_kubun, basis, reviews = _fix("プロモパック系", "Case", "未開封", unit_kubun="箱系大")
    assert (unit, unit_kubun, reviews) == ("Pack", "パック系", [])
    assert basis["kubun_unit_fix"] == "a" and basis["kubun_unit_from"] == "Case"


def test_kubun_table_box_with_booklet_and_state_unit_not_allowed_adds_unit_unknown_b():
    unit, unit_kubun, basis, reviews = _fix("箱系", "Booklet", "With booklet", unit_kubun="冊子系")
    assert (unit, unit_kubun) == ("Booklet", "冊子系")
    assert basis == {"line": 1, "kubun_unit_fix": "b"} and reviews == [{"kind": "unit_unknown"}]


def test_kubun_table_box_with_booklet_and_no_state_unit_is_b():
    unit, _k, basis, reviews = _fix("箱系", "Booklet", "none-such", unit_kubun="冊子系")
    assert unit == "Booklet" and basis["kubun_unit_fix"] == "b" and reviews == [{"kind": "unit_unknown"}]


@pytest.mark.parametrize(
    "kubun,unit", [("セット系", "Set"), ("箱系", None), ("箱系", ""), ("シングル系", "個"), ("不明", "Set")]
)
def test_kubun_table_unlisted_kubun_or_empty_unit_is_unchanged(kubun, unit):
    assert _fix(kubun, unit, "Sealed box") == (unit, "複合", {"line": 1}, [])


@pytest.mark.parametrize(
    "kubun,unit,cond",
    [("箱系", "Set", "Sealed box"), ("箱系", "MasterCarton", "Sealed box"), ("プロモパック系", "Case", "未開封"),
     ("箱系", "Booklet", "With booklet"), ("セット系", "Set", "Sealed box"), ("箱系", None, "Sealed box")],
)
def test_kubun_table_empty_table_changes_nothing(kubun, unit, cond):
    assert _fix(kubun, unit, cond, table={}) == (unit, "複合", {"line": 1}, [])


def test_kubun_table_empty_table_end_to_end_equals_plain():
    plain = _one("サンプル拡張\n3セット@1,500円", _it([1, 2], "1,500円", "3"), units=_KUBUN_UNITS)
    given = _one("サンプル拡張\n3セット@1,500円", _it([1, 2], "1,500円", "3"), units=_KUBUN_UNITS,
                 product_first=ProductFirstMasters(**{**_pf().__dict__, "kubun_allowed_units": {}}))
    assert plain == given


def test_kubun_table_unregistered_unit_word_is_replaced_like_any_other_a():
    unit, unit_kubun, basis, reviews = _fix("箱系", "謎の単位", "Sealed box", unit_kubun="不明")
    assert (unit, unit_kubun, reviews) == ("Box", "箱系", [])
    assert basis["kubun_unit_fix"] == "a" and basis["kubun_unit_from"] == "謎の単位"
    unit, unit_kubun, basis, reviews = _fix("箱系", "謎の単位", "With booklet", unit_kubun="不明")
    assert (unit, unit_kubun, reviews) == ("謎の単位", "不明", [{"kind": "unit_unknown"}]) and basis["kubun_unit_fix"] == "b"


def test_kubun_table_logs_one_info_line_each_without_source_text(caplog):
    with caplog.at_level("INFO", logger=pf.logger.name):
        _fix("箱系", "Set", "Sealed box")
        _fix("箱系", "Booklet", "With booklet", unit_kubun="冊子系")
        _fix("箱系", "Box", "Sealed box")  # 表にある単位：ログなし
    lines = [r.getMessage() for r in caplog.records if "kubun_unit_fix" in r.getMessage()]
    assert len(lines) == 2
    assert "fix=a" in lines[0] and "kubun=箱系" in lines[0] and "from=Set" in lines[0] and "to=Box" in lines[0] and "product_id=1" in lines[0]
    assert "fix=b" in lines[1] and "from=Booklet" in lines[1] and "to=Booklet" in lines[1]


_OK_JSON = json.dumps({"箱系": ["Box", "Case"], "ブックレット系": ["Booklet"]}, ensure_ascii=False)
_VALID_KUBUNS = {"箱系", "プロモパック系", "ブックレット系", "セット系"}
_VALID_UNITS = {"Box", "Case", "Pack", "Booklet", "MasterCarton", "Set"}


def test_validate_kubun_allowed_units_accepts_a_good_value():
    table = pf.validate_kubun_allowed_units(_OK_JSON, _VALID_KUBUNS, _VALID_UNITS)
    assert table == {"箱系": frozenset({"Box", "Case"}), "ブックレット系": frozenset({"Booklet"})}


@pytest.mark.parametrize(
    "raw",
    [None, "{not json", "[]", json.dumps({"箱系": "Box"}), json.dumps({"箱系": []}), json.dumps({"箱系": [1]}),
     json.dumps({"知らない区分": ["Box"]}, ensure_ascii=False), json.dumps({"箱系": ["知らない単位"]}, ensure_ascii=False)],
)
def test_validate_kubun_allowed_units_bad_value_gives_empty_table_and_warning(raw, caplog):
    with caplog.at_level("WARNING", logger=pf.logger.name):
        assert pf.validate_kubun_allowed_units(raw, _VALID_KUBUNS, _VALID_UNITS) == {}
    warnings = [r for r in caplog.records if r.levelname == "WARNING" and "kubun_unit_fix" in r.getMessage()]
    assert len(warnings) == 1 and "知らない" not in warnings[0].getMessage()


def test_loader_reads_kubun_allowed_units_through_validation(monkeypatch):
    monkeypatch.setattr(pf, "load_product_entries", lambda s: list(_PRODUCTS))
    monkeypatch.setattr(pf, "load_product_kubun_type_map", lambda s: dict(_PRODUCT_KUBUN))

    def execute(stmt, params=None):
        sql = str(stmt)
        rows = (
            [] if "type_master" in sql or "release_date" in sql else [(_OK_JSON,)] if "tcg_distribution_settings" in sql
            else [(k,) for k in sorted(_VALID_KUBUNS)] if "tcg_product_categories" in sql
            else [("Sealed box", "Box")] if "line_conditions" in sql
            else [(u,) for u in sorted(_VALID_UNITS)] if "line_units" in sql and "code = " not in sql
            else [("Set",)] if "line_units" in sql else [("ONE PIECE",)]
        )
        return SimpleNamespace(fetchall=lambda: rows)

    session = MagicMock()
    session.execute.side_effect = execute
    masters = pf.load_product_first_masters(session)
    assert masters.kubun_allowed_units["箱系"] == frozenset({"Box", "Case"})


def test_validate_kubun_allowed_units_empty_object_is_rollback_value_without_warning(caplog):
    with caplog.at_level("WARNING", logger=pf.logger.name):
        assert pf.validate_kubun_allowed_units("{}", _VALID_KUBUNS, _VALID_UNITS) == {}
    assert [r for r in caplog.records if r.levelname == "WARNING"] == []
