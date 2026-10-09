"""試作版 v102：候補が複数残った件に「より詳しく当たった候補」を提案する処理の単体試験。

原文は社外秘のため使わない。商品名・言い回しはすべて作り例。DB には触れない（マスタは引数で渡す）。
PO 決定（2026-10-08）：選べても商品は決めない（ambiguous・product_id None のまま）。要確認 product_multiple に提案を添える。
"""
from __future__ import annotations

import json

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services.extraction_judgement_svc import ProductEntry, match_product
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.gemini_raw_copy_v102_score_select import RULE_S1, RULE_S4, decide_by_score

_UNITS = {"BOX": ("Box", "箱系"), "Box": ("Box", "箱系"), "piece": ("Piece", "単品系")}
_COND = [
    {
        "cond_id": "c-CN0003", "code": "CN0003", "canonical": "Sealed box", "priority": 4, "app_kubun": "箱系",
        "search_kw": "シュリンク付き", "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
    },
]
_STATUS = [
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99, "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_MASTERS = {"cond_entries": _COND, "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS, "status_entries": _STATUS}


def _p(pid, work, *kws, code=None, mark=None):
    return ProductEntry(id=pid, product_code=code, mark=mark, work_id=work, search_keywords=tuple(kws), exclude_keywords=())


def _match(text, products):
    return match_product(text, products, strict_codes=True)


# --- MatchResult.code_hits ----------------------------------------------------------------------


def test_code_hits_lists_products_whose_code_or_mark_hit_and_existing_fields_are_unchanged():
    products = (_p(1, 1, "名前甲", code="XYZ-100"), _p(2, 2, "名前甲"))
    match = _match("名前甲 XYZ-100", products)
    assert match.code_hits == (1,) and match.code_hit_values == {1: ("XYZ-100",)}
    assert match.status == "ambiguous" and match.candidates == (1, 2)
    assert match.matched_keywords == {1: ("名前甲",), 2: ("名前甲",)}


def test_code_hits_empty_when_no_code_hit():
    assert _match("名前甲", (_p(1, 1, "名前甲"),)).code_hits == ()


# --- S1 -----------------------------------------------------------------------------------------


def test_s1_decides_by_code_hit_difference():
    products = (_p(1, 1, "共通名", code="UA53BT"), _p(2, 2, "共通名"))
    decision = decide_by_score(_match("共通名 UA53BT", products), products)
    assert (decision.rule, decision.product_id, decision.dropped) == (RULE_S1, 1, (2,))
    assert decision.as_dict()["scores"]["1"]["M"] == 1 and decision.as_dict()["scores"]["2"] == {"M": 0, "K": 1, "words": ["共通名"]}


# --- S4 -----------------------------------------------------------------------------------------


def test_s4_decides_when_one_candidates_words_contain_the_others():
    products = (_p(1, 1, "1st Anniversary Set"), _p(2, 2, "1st"))
    decision = decide_by_score(_match("1st Anniversary Set", products), products)
    assert (decision.rule, decision.product_id, decision.dropped) == (RULE_S4, 1, (2,))


def test_s4_decides_with_code_word_contained_in_keyword():
    products = (_p(1, 1, "名前 SV2a 151", code=None), _p(2, 2, "SV2a"))
    decision = decide_by_score(_match("名前 SV2a 151", products), products)
    assert decision.rule == RULE_S4 and decision.product_id == 1


# --- 決めない -----------------------------------------------------------------------------------


def test_not_decided_when_words_do_not_contain_each_other():
    products = (_p(1, 1, "遊戯編"), _p(2, 2, "城之内編"), _p(3, 3, "海馬編"))
    assert decide_by_score(_match("遊戯編 城之内編 海馬編", products), products) is None


def test_not_decided_when_one_candidate_contains_only_one_of_two_others():
    products = (_p(1, 1, "30th CELEBRATION"), _p(2, 2, "30th エーフィ"), _p(3, 3, "30th ブラッキー"))
    assert decide_by_score(_match("30th CELEBRATION 30th エーフィ 30th ブラッキー", products), products) is None


def test_not_decided_when_same_points_and_unrelated_words():
    products = (_p(1, 1, "フュージョンワールド"), _p(2, 2, "メガブレイブ"))
    assert decide_by_score(_match("フュージョンワールド メガブレイブ", products), products) is None


def test_not_decided_when_not_ambiguous():
    products = (_p(1, 1, "名前甲"),)
    assert decide_by_score(_match("名前甲", products), products) is None


# --- 組み込み -----------------------------------------------------------------------------------

_PRODUCTS = (
    _p(21, 1, "作品ワン商品"), _p(22, 2, "作品ツー商品"),
    _p(31, 1, "共通商品", "共通甲商品"), _p(32, 2, "共通商品"),
    _p(41, 1, "詳しい名前 特別セット"), _p(42, 2, "詳しい名前"),
    _p(51, 1, "同点甲"), _p(52, 1, "同点乙"),
)
_KUBUN = {"21": "箱系", "22": "箱系", "31": "箱系", "32": "箱系", "41": "箱系", "42": "箱系", "51": "箱系", "52": "箱系"}
_NAME = {"W": "作品ワン商品", "X": "作品ツー商品", "A": "共通商品", "D": "詳しい名前 特別セット", "T": "同点甲 同点乙"}


def _masters():
    return ProductFirstMasters(product_entries=_PRODUCTS, product_kubun=_KUBUN, condition_unit={"Sealed box": "Box"}, ignore_phrases=())


def _rows(shape, masters="default"):
    raw = "\n".join(f"{_NAME[ch]} 3@1,500円" for ch in shape)
    items = [{"lines": [i + 1], "price": "1,500円", "quantity": "3"} for i in range(len(shape))]
    parsed, errors = v101.parse_v101_response(json.dumps({"items": items}, ensure_ascii=False), raw, status_entries=_STATUS)
    assert errors == []
    rows, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=_masters() if masters == "default" else masters,
        **_MASTERS,
    )
    return rows


def _multi(row):
    return [r for r in row["review"] if r["kind"] == pf.REVIEW_PRODUCT_MULTIPLE]


def test_decided_candidate_is_suggested_but_product_stays_undecided():
    row = _rows("D")[0]
    assert row["match_status"] == "ambiguous" and row["product_id"] is None
    (review,) = _multi(row)
    assert (review["suggested_product_id"], review["suggest_rule"], review["suggest_dropped"]) == (41, "S4", [42])
    assert review["candidates"] == [41, 42] and row["product_score"]["rule"] == "S4"
    assert set(row["product_score"]["scores"]) == {"41", "42"}
    assert "matched_score" not in json.dumps(row, ensure_ascii=False)


def test_undecided_candidate_has_no_suggestion_and_no_score():
    row = _rows("T")[0]
    assert row["match_status"] == "ambiguous"
    (review,) = _multi(row)
    assert "suggested_product_id" not in review and "suggest_rule" not in review and "product_score" not in row


def test_context_decided_row_stays_matched_context_without_suggestion():
    row = _rows("WD")[1]
    assert row["match_status"] == "matched_context" and row["product_id"] == 41
    assert "product_score" not in row and _multi(row) == []
    assert "suggested_product_id" not in json.dumps(row["review"])


def test_suggested_row_is_not_a_clue_for_neighbors():
    rows = _rows("DA")  # D は提案が付くが ambiguous のまま＝A の手がかりにならない
    assert rows[1]["match_status"] == "ambiguous"


def test_without_product_first_output_is_unchanged():
    row = _rows("D", masters=None)[0]
    assert "product_score" not in row and "product_id" not in row and _multi(row) == []
