"""試作版 v102：作品をまたぐ曖昧な商品を、前後の商品の作品で決める処理の単体試験。

原文は社外秘のため使わない。商品名・言い回しはすべて作り例。DB には触れない（マスタは引数で渡す）。
作品 1=W、2=X、3=Y。
"""
from __future__ import annotations

import json

import pytest

import app.services.gemini_raw_copy_v102_context_work as cw
import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters

_UNITS = {"BOX": ("Box", "箱系"), "Box": ("Box", "箱系"), "piece": ("Piece", "単品系")}


def _cond(code, canonical, priority, app_kubun, search_kw):
    return {
        "cond_id": f"c-{code}", "code": code, "canonical": canonical, "priority": priority,
        "app_kubun": app_kubun, "search_kw": search_kw, "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
    }


_COND = [
    _cond("CN0008", "FLAG_SINGLE", 1, "枚系,単位不明", "PSA,SR"),
    _cond("CN0003", "Sealed box", 4, "箱系", "シュリンク付き"),
]
_STATUS = [
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99, "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_MASTERS = {"cond_entries": _COND, "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS, "status_entries": _STATUS}


def _p(pid, work, *kws):
    return ProductEntry(id=pid, product_code=None, mark=None, work_id=work, search_keywords=tuple(kws), exclude_keywords=())


_PRODUCTS = (
    _p(21, 1, "作品ワン商品"), _p(22, 2, "作品ツー商品"), _p(23, 3, "作品スリー商品"),
    _p(31, 1, "共通商品", "共通甲商品"), _p(32, 2, "共通商品"), _p(33, 3, "共通甲商品"),
    _p(51, 1, "同作商品"), _p(52, 1, "同作商品"),
)
_KUBUN = {"21": "箱系", "22": "箱系", "23": "箱系", "31": "箱系", "32": "シングル系", "33": "シングル系", "51": "箱系", "52": "箱系"}
_NAME = {"W": "作品ワン商品", "X": "作品ツー商品", "Y": "作品スリー商品", "A": "共通商品", "B": "共通甲商品", "S": "同作商品"}


def _masters():
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun=_KUBUN, condition_unit={"Sealed box": "Box"}, ignore_phrases=(),
    )


def _rows(shape, product_first="default"):
    """shape は "WWAXW" のような並び。1文字が1行1件。"""
    raw = "\n".join(f"{_NAME[ch]} 3@1,500円" for ch in shape)
    items = [{"lines": [i + 1], "price": "1,500円", "quantity": "3"} for i in range(len(shape))]
    parsed, errors = v101.parse_v101_response(json.dumps({"items": items}, ensure_ascii=False), raw, status_entries=_STATUS)
    assert errors == []
    masters = _masters() if product_first == "default" else product_first
    rows, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=masters, **_MASTERS
    )
    return rows


def _kinds(row):
    return [r["kind"] for r in row["review"]]


def _multi(row):
    return [r for r in row["review"] if r["kind"] == pf.REVIEW_PRODUCT_MULTIPLE]


# --- (a) 前後が同じ作品 -----------------------------------------------------------------------


def test_rule_a_same_work_both_sides_decides_and_uses_chosen_products_category():
    row = _rows("WAW")[1]
    assert row["match_status"] == "matched_context" and row["product_id"] == 31
    assert row["product_context"]["rule"] == "a" and row["product_context"]["dropped"] == [32]
    assert [c["line"] for c in row["product_context"]["clues"]] == [1, 3]
    assert row["product_category"] == "箱系" and (row["unit"], row["condition"]) == ("Box", "Sealed box")
    assert _multi(row) == [] and "context_reason" not in str(row["review"])


def test_rule_a_decides_even_if_competitor_work_is_in_post():
    rows = _rows("WAWX")
    assert rows[1]["match_status"] == "matched_context" and rows[1]["product_id"] == 31 and rows[1]["product_context"]["rule"] == "a"


def test_rule_a_chosen_single_product_category_is_used():
    row = _rows("XAX")[1]
    assert row["product_id"] == 32 and row["product_category"] == "シングル系"


# --- (b) 片側だけ -----------------------------------------------------------------------------


def test_rule_b_one_side_decides_when_no_competitor_work_in_post():
    row = _rows("WA")[1]
    assert row["match_status"] == "matched_context" and row["product_id"] == 31 and row["product_context"]["rule"] == "b"


def test_rule_b_does_not_decide_when_competitor_work_is_in_post():
    rows = _rows("XWWA")
    row = rows[3]
    assert row["match_status"] == "ambiguous" and "product_context" not in row
    (review,) = _multi(row)
    assert review["context_reason"] == cw.REASON_COMPETITOR_WORK_IN_POST and review["candidates"] == [31, 32]


# --- (c) 前後2件ずつの多数決 -------------------------------------------------------------------


def test_rule_c_majority_decides_when_competitor_candidate_work_is_not_in_post():
    rows = _rows("WWBXW")  # B の候補は W と Y。前 W・W、後ろ X・W。多いのは W。Y は投稿に無い
    row = rows[2]
    assert row["match_status"] == "matched_context" and row["product_id"] == 31 and row["product_context"]["rule"] == "c"
    assert row["product_context"]["dropped"] == [33]


def test_rule_c_does_not_decide_when_competitor_work_is_in_post():
    rows = _rows("WWAXW")  # A の候補は W と X。X が投稿にある
    row = rows[2]
    assert row["match_status"] == "ambiguous"
    assert _multi(row)[0]["context_reason"] == cw.REASON_NEIGHBORS_DIFFER_PREFIX + cw.REASON_COMPETITOR_WORK_IN_POST


def test_tie_is_not_decided():
    row = _rows("WAX")[1]
    assert row["match_status"] == "ambiguous" and _multi(row)[0]["context_reason"] == cw.REASON_TIE


def test_no_clue_is_not_decided():
    row = _rows("AA")[0]
    assert _multi(row)[0]["context_reason"] == cw.REASON_NO_CLUE


def test_clue_work_without_candidate_is_not_decided():
    row = _rows("YAY")[1]  # 手がかりは Y。A の候補は W・X のみ
    assert _multi(row)[0]["context_reason"] == cw.REASON_CLUE_WORK_CANDIDATES_0


# --- 対象外・連鎖 -----------------------------------------------------------------------------


def test_ambiguous_with_candidates_of_one_work_is_left_alone():
    row = _rows("WSW")[1]
    assert row["match_status"] == "ambiguous" and "product_context" not in row
    assert "context_reason" not in str(row["review"]) and _multi(row)[0]["candidates"] == [51, 52]


def test_decided_item_is_not_a_clue_for_another_item():
    rows = _rows("WAB")
    assert rows[1]["product_context"]["rule"] == "b" and [c["line"] for c in rows[1]["product_context"]["clues"]] == [1]
    # B（3行目）の手がかりは 1 行目の W だけ。2行目で決めた A は手がかりにならない
    assert [c["line"] for c in rows[2]["product_context"]["clues"]] == [1]


def test_matched_items_are_unchanged_by_second_pass():
    with_ctx = _rows("WAW")
    assert with_ctx[0]["match_status"] == "matched" and "product_context" not in with_ctx[0]


# --- decide_by_context 単体 -------------------------------------------------------------------


def test_decide_by_context_returns_only_targets_and_reasons():
    first = [
        {"price_line": 1, "match_status": "matched", "product_id": 21, "match_candidates": [21]},
        {"price_line": 2, "match_status": "ambiguous", "product_id": None, "match_candidates": [31, 32]},
        {"price_line": 3, "match_status": "ambiguous", "product_id": None, "match_candidates": [51, 52]},
    ]
    result = cw.decide_by_context(first, _PRODUCTS)
    assert set(result) == {1} and result[1].product_id == 31 and result[1].rule == "b" and result[1].is_decided


# --- 呼び出し側の約束 -------------------------------------------------------------------------


def test_without_product_first_output_has_no_context_keys():
    rows = _rows("WAW", product_first=None)
    assert all("product_context" not in r and "match_status" not in r for r in rows)


@pytest.mark.parametrize("chosen", [None, 99, 21])
def test_chosen_product_id_not_among_candidates_or_not_ambiguous_changes_nothing(chosen):
    base = dict(
        item={"price_line": 1, "lines": [1]}, roles={}, lines=["共通商品 3@1,500円"], block="共通商品 3@1,500円", name="共通商品",
        aliases=(), unit_alias_to_info=_UNITS, cond_entries=_COND, cond_canonical_to_uuid={}, masters=_masters(),
        find_price_alias=lambda _t: None,
    )
    plain = pf.resolve_product_first(**base)
    given = pf.resolve_product_first(**base, chosen_product_id=chosen)
    assert plain == given and plain["match_status"] == "ambiguous"


def test_chosen_product_id_among_candidates_makes_it_matched():
    base = dict(
        item={"price_line": 1, "lines": [1]}, roles={}, lines=["共通商品 3@1,500円"], block="共通商品 3@1,500円", name="共通商品",
        aliases=(), unit_alias_to_info=_UNITS, cond_entries=_COND, cond_canonical_to_uuid={}, masters=_masters(),
        find_price_alias=lambda _t: None,
    )
    row = pf.resolve_product_first(**base, chosen_product_id=31)
    assert row["match_status"] == "matched" and row["product_id"] == 31 and row["product_category"] == "箱系"
    assert pf.REVIEW_PRODUCT_MULTIPLE not in [r["kind"] for r in row["review_extra"]]
