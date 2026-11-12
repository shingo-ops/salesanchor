"""区分「シングルセット系」（ADR-1031 What 6・ADR-1027 追記 2026-11-11）の試験。DB なし。原文は作り例のみ。

設計: docs/handoff/single-set-category/design.md 便1・受入 K1a〜K1c
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services import line_analysis_v102_svc as svc
from app.services import v102_buyback_unit_svc as bb
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.v102_bundle_svc import KIND_DECIDED
from tests.test_adr1031_single_promo_pack import _COND, _SINGLE, _STATUS
from tests.test_v102_unit_price_check import _MASTERS as _WRITE_MASTERS
from tests.test_v102_unit_price_check import _WriteSession

SS, S, SET = pf.PRODUCT_KUBUN_SINGLE_SET, pf.PRODUCT_KUBUN_SINGLE, pf.PRODUCT_KUBUN_SET
_UNITS = {
    "枚": ("Piece", "枚系"), "piece": ("Piece", "単品系"), "Piece": ("Piece", "単品系"),
    "セット": ("Set", "複合"), "Set": ("Set", "複合"), "Box": ("Box", "箱系"),
}
_PRODUCTS = (
    ProductEntry(id=7, product_code=None, mark=None, work_id=1, search_keywords=("作りまとめ",), exclude_keywords=()),
)
_REPO = Path(svc.__file__).resolve().parents[3]


def _masters(kubun=SS, set_unit="Set"):
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun={"7": kubun}, condition_unit={"Sealed box": "Box"}, ignore_phrases=(),
        scoped_cond_entries={"single": _SINGLE}, set_unit=set_unit,
    )


def _one(text, line2="3@500円", quantity="3", masters=None):
    raw = f"{text}\n{line2}"
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": [{"lines": [1, 2], "price": "500円", "quantity": quantity}]}, ensure_ascii=False),
        raw, status_entries=_STATUS,
    )
    assert errors == []
    (row,), _f = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=masters or _masters(),
        cond_entries=_COND, cond_canonical_to_uuid={}, unit_alias_to_info=_UNITS, status_entries=_STATUS,
    )
    return row


def _unit(unit, unit_kubun, kubun=SS, set_unit="Set"):
    return pf._resolve_unit_from_state(
        unit=unit, unit_kubun=unit_kubun, unit_basis={"alias": unit}, product_kubun=kubun, condition="Single",
        basis=pf.BASIS_SINGLE_DEFAULT, masters=_masters(kubun, set_unit), unit_alias_to_info=_UNITS,
    )


# --- 表（区分の置き場は 1 か所） -------------------------------------------------------------------


def test_tables_treat_single_set_like_single():
    assert SS == "シングルセット系"
    assert pf._KUBUN_TO_VALUE_GROUP[SS] == pf._KUBUN_TO_VALUE_GROUP[S]
    assert pf._KUBUN_MATCHED_AS == {SS: S}
    assert svc._SCOPED_GROUP_OF_KUBUN[SS] == pf.VALUE_GROUP_SINGLE
    assert SS not in pf.PRODUCT_KUBUNS_DEFAULTING_TO_BOX


# --- K1a 判定の段 -------------------------------------------------------------------------------


def test_k1a_without_unit_word_is_set_and_single_r7():
    row = _one("作りまとめ")
    assert row["product_category"] == SS
    assert (row["condition"], row["condition_basis"], row["unit"]) == ("Single", "R7:単品既定", "Set")
    assert row["unit_basis"][pf.UNIT_BASIS_FROM_CATEGORY] == SS
    assert pf.UNIT_BASIS_SINGLE_SET_FROM not in row["unit_basis"]


def test_k1a_piece_count_in_parentheses_is_still_set():
    row = _one("作りまとめ (12枚)")
    assert (row["condition"], row["unit"]) == ("Single", "Set")


def test_k1a_written_set_unit_is_set():
    row = _one("作りまとめ", line2="3セット@500円")
    assert (row["condition"], row["unit"]) == ("Single", "Set")
    assert pf.UNIT_BASIS_SINGLE_SET_FROM not in row["unit_basis"]


def test_k1a_psa10_word_is_psa10():
    assert _one("作りまとめ PSA10")["condition"] == "PSA10"


def test_k1a_unit_rule_piece_becomes_set_and_keeps_the_written_unit():
    assert _unit("Piece", "枚系") == (
        "Set", "複合", {"alias": "Piece", pf.UNIT_BASIS_FROM_CATEGORY: SS, pf.UNIT_BASIS_SINGLE_SET_FROM: "Piece"},
    )


def test_k1a_unit_rule_no_unit_and_set_unit_do_not_add_the_written_unit():
    assert _unit(None, "") == ("Set", "複合", {"alias": None, pf.UNIT_BASIS_FROM_CATEGORY: SS})
    assert _unit("Set", "複合") == ("Set", "複合", {"alias": "Set", pf.UNIT_BASIS_FROM_CATEGORY: SS})


def test_k1a_without_set_unit_in_masters_is_same_as_single():
    for unit, unit_kubun in (("Piece", "枚系"), (None, "")):
        assert _unit(unit, unit_kubun, set_unit=None) == _unit(unit, unit_kubun, kubun=S, set_unit=None)


def test_k1a_single_unit_is_unchanged():
    assert _unit("Piece", "枚系", kubun=S) == ("Piece", "枚系", {"alias": "Piece"})


def test_k1a_set_category_is_unchanged():
    row = _one("作りまとめ", masters=_masters(SET))
    assert (row["condition"], row["unit"]) == ("Sealed box", "Set")


# --- K1b 書き込みの段（本物の _write_results） ---------------------------------------------------

_RAW = "【見出し】\n作りまとめ 100枚セット\n5セット@26,000円"
_W_MASTERS = {**_WRITE_MASTERS, "product_first": _masters(), "unit_alias_to_info": _UNITS}


def _written(kubun):
    item = {
        "unit": "Set", "product_id": 1, "match_status": "matched", "condition": "Single",
        "condition_basis": pf.BASIS_SINGLE_DEFAULT, "price_normalized": 26000, "quantity_normalized": 5,
        "product_category": kubun, "unit_basis": {"alias": None},
    }
    rows = [SimpleNamespace(id="row0", gemini_index=0, source_lines=[2, 3], line_start=2, line_end=3, raw_price=None)]
    session = _WriteSession([], [])
    svc._write_results(
        session, "job1", {"v102_items": [{"lines": [2, 3], "gemini_index": 0, **item}], "v102_flags": {}},
        rows, _W_MASTERS, {"Piece": 12, "Set": 13}, None, _RAW,
    )
    (row,) = [p for sql, p in session.calls if "INSERT INTO public.analysis_results" in sql]
    return item, row


def test_k1b_single_set_is_not_read_as_bundle():
    _item, row = _written(SS)
    assert (row["unit_canonical"], row["bundle_size"]) == ("Set", None)
    assert (row["price_normalized"], row["quantity_normalized"]) == (26000, 5)
    assert row["review_reasons"] is None


def test_k1b_single_set_condition_id_is_from_single_group():
    _item, row = _written(SS)
    assert row["condition_id"] == svc._scoped_condition_id("Single", S, _W_MASTERS)


def test_k1b_set_and_single_still_read_as_bundle():
    for kubun in (SET, S):
        _item, row = _written(kubun)
        assert (row["unit_canonical"], row["bundle_size"]) == ("Piece", 100)


def test_k1b_single_set_is_not_a_buyback_candidate():
    item, _row = _written(SS)
    values = {"pid_resolved": True, "product_id": 1, "price_normalized": 26000, "bundle_size": None}
    assert bb.is_candidate(item, values, _UNITS) is False


# --- K1c 当て直しの台本と精度試験の変換器 ----------------------------------------------------------


def _replay_module():
    spec = importlib.util.spec_from_file_location("bundle_replay_single_set", _REPO / "scripts" / "dev" / "bundle_replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # `if __name__ == "__main__"` のため main は走らない
    return module


def test_k1c_replay_constant_matches_product_first():
    assert _replay_module()._SINGLE_SET_KUBUN == SS


def test_k1c_replay_row_skips_single_set_and_keeps_others():
    m = _replay_module()
    unit_words, set_words = m.split_unit_words({"枚": "Piece", "セット": "Set", "set": "Set"})
    base = {"body": "作りまとめ 100枚セット / 5セット@26,000円", "price_normalized": "26000", "quantity_normalized": "5", "price_basis": ""}
    assert m.replay_row({**base, "kubun_type": SS}, unit_words, set_words) == (None, None, False)
    before, res, is_bulk = m.replay_row({**base, "kubun_type": SET}, unit_words, set_words)
    assert is_bulk is False and (res.kind, res.n) == (KIND_DECIDED, 100) and (before.kind, before.n) == (KIND_DECIDED, 100)


def test_k1c_reads_bundle_is_false_only_for_single_set():
    assert svc._reads_bundle({"product_category": SS}) is False
    for kubun in (SET, S, pf.PRODUCT_KUBUN_BULK, pf.PRODUCT_KUBUN_BOX, None):
        assert svc._reads_bundle({"product_category": kubun}) is True


def test_k1c_fhd_snapshot_uses_reads_bundle():
    text = (_REPO / "scripts" / "accuracy" / "llm_compare" / "fhd_snapshot.py").read_text(encoding="utf-8")
    assert "S._reads_bundle(" in text
