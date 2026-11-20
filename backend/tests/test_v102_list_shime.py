"""1行に品名を区切って並べて〆る投稿（規則14）の受け取り側の試験。

設計: docs/handoff/shime-bundle-close/design-oneline.md §3-2。商品・原文はすべて架空。
DB は使わない（T9 も _analysis_values・_apply_soldout_targets・_extra_targets の純粋な関数で確かめる）。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

import app.services.line_analysis_v102_svc as svc
from app.services import gemini_raw_copy_v101 as v101
from app.services import gemini_raw_copy_v102_soldout_ref as sr
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters

# ---------------------------------------------------------------------------
# 道具（既存の試験の同じ働きの物を写した）
# ---------------------------------------------------------------------------

_SOLD_WORDS = ["〆", "完売"]
_STATUS = [
    {"canonical": "Sold out", "search_pattern": "〆", "exclude_pattern": "", "priority": 1, "match_type": "LITERAL", "effect": "EXCLUDE"},
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99, "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_UNITS = {
    "BOX": ("Box", "箱系"), "Box": ("Box", "箱系"), "ボックス": ("Box", "箱系"), "piece": ("Piece", "単品系"),
    "ロット": ("Lot", "条件つき"),
}


def _cond(code, canonical, priority, app_kubun, search_kw):
    return {
        "cond_id": f"c-{code}", "code": code, "canonical": canonical, "priority": priority,
        "app_kubun": app_kubun, "search_kw": search_kw, "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
    }


_COND = [
    _cond("CN0008", "FLAG_SINGLE", 1, "枚系,単位不明", "PSA,SR"),
    _cond("CN0003", "Sealed box", 4, "箱系", "シュリンク付き"),
    _cond("CN0004", "Opened box", 5, "箱系", "開封"),
]
_MASTERS = {"cond_entries": _COND, "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS, "status_entries": _STATUS}
_SINGLE_ROWS = {"single": ({**_cond("CN0100", "Single", 1, "シングル系", ""), "value_group": "single"},)}


def _p(pid, work, *kws):
    return ProductEntry(id=pid, product_code=None, mark=None, work_id=work, search_keywords=tuple(kws), exclude_keywords=())


# 62（ファイブ）・63（ピヨピヨ商品）は名前で決まる箱系の商品。65 は 62 と同じ作品の別の商品、66 は 63 と同じ作品の別の商品
_PRODUCTS = (_p(62, 1, "ファイブ"), _p(63, 2, "ピヨピヨ商品"), _p(65, 1, "チガウモノ"), _p(66, 3, "ベツモノ"))
_KUBUN = {"62": "箱系", "63": "箱系", "65": "箱系", "66": "箱系"}
_MASTER = ProductFirstMasters(
    product_entries=_PRODUCTS, product_kubun=_KUBUN, condition_unit={"Sealed box": "Box"}, ignore_phrases=(),
)
T0 = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
_BOX, _CASE = "Sealed box", "Case"


def _post(message_id: str, raw: str = "x", hours_before: float = 1.0, stock=(), sold=()) -> sr.SoldoutRefPost:
    return sr.SoldoutRefPost(message_id, T0 - timedelta(hours=hours_before), raw, tuple(stock), tuple(sold))


def _si(lines, product_id: int, condition_id: int, canonical: str) -> sr.StockItem:
    return sr.StockItem(frozenset(lines), product_id, condition_id, canonical)


# A（62）・B（63）の両方に、〆の状態と違う在庫（Case）がある過去の投稿
_BOTH_STOCK = (_si([1], 62, 21, _CASE), _si([2], 63, 31, _CASE))


def _run(lines, posts, *, master=_MASTER, fixed=None, followup_ref=None, specs=None, masters=_MASTERS, sold_lines=None):
    """lines は原文の行。specs は行ごとの (price, quantity)（省略は全部 none none）。sold_lines は件の lines を差し替える {件の番号: [行番号]}。"""
    raw = "\n".join(lines)
    specs = specs or [("none", "none")] * len(lines)
    items = [{"lines": (sold_lines or {}).get(i, [i + 1]), "price": p, "quantity": q} for i, (p, q) in enumerate(specs)]
    parsed, errors = v101.parse_v101_response(json.dumps({"items": items}, ensure_ascii=False), raw, status_entries=_STATUS)
    assert errors == []
    rows, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=master,
        soldout_posts=posts, fixed_products=fixed, followup_ref=followup_ref, **masters,
    )
    return rows


def _pairs(row):
    return [(t["product_id"], t["condition_id"]) for t in row.get("soldout_targets", [])]


_LINE = "ファイブ、ピヨピヨ商品〆"
_PRICED = ("1,500円", "3")

# --- T1〜T5：split_list_shime（純粋な関数）---------------------------------------------------------


def _names(text: str):
    """区切りの文字に「品名A」「品名B」…が入っていれば、その商品 ID（A=1, B=2, …）。無ければ None。"""
    for k, ch in enumerate("ABCDEF", start=1):
        if f"品名{ch}" in text:
            return k
    return None


def _split(text: str, match=_names):
    return sr.split_list_shime(text, _SOLD_WORDS, match)


def test_t1_two_names_split_into_their_products():
    assert _split("品名A、品名B〆") == (1, 2)
    assert _split("品名A、品名B、品名C 完売") == (1, 2, 3)  # 〆の言葉は「完売」でも同じ


@pytest.mark.parametrize("sep", [",", "，", "/", "／"])
def test_t2_other_separators_work_the_same(sep):
    assert _split(f"品名A{sep}品名B〆") == (1, 2)


@pytest.mark.parametrize("sep", ["・", "&", "＆"])
def test_t2_middle_dot_and_ampersand_are_not_separators(sep):
    assert _split(f"品名A{sep}品名B〆") is None


def test_t2_six_parts_is_none_and_five_is_accepted():
    names = ["品名A", "品名B", "品名C", "品名D", "品名E", "品名F"]
    assert _split("、".join(names[:5]) + "〆") == (1, 2, 3, 4, 5)
    assert _split("、".join(names) + "〆") is None


def test_t3_a_part_that_matches_no_product_is_none():
    assert _split("パック、品名B〆") is None


def test_t4_the_same_product_twice_is_none():
    assert _split("品名A 未開封、品名A バラ〆") is None


def test_t5_a_digits_only_word_is_none():
    # 値段と数の並び。match が長さで別の商品を返しても、数字だけの語があれば None
    assert _split("1000、3 個〆", match=lambda s: len(s)) is None
    # 対照: 数字だけの語が無ければ、同じ match で組が返る
    assert _split("あいう、えおかき〆", match=lambda s: len(s)) == (3, 4)


# --- T6〜：_extract_v102（extract_v101_items の v102_fixes）----------------------------------------


def test_t6_the_ambiguous_one_line_shime_is_rebuilt_with_every_product_as_a_target():
    posts = (_post("p1", stock=_BOTH_STOCK),)
    row = _run([_LINE], posts)[0]
    assert row["match_status"] == "matched_list_shime" and row["product_id"] == 62
    assert row["soldout_target_basis"] == "SOLDOUT_LIST_SHIME"
    assert row["product_list_shime"] == {"separators": ["、"], "products": [62, 63]}
    assert _pairs(row) == [(62, 21), (63, 31)]  # A の相手が先頭、B が続く
    for t in row["soldout_targets"]:
        assert t["ref_message_id"] == "p1" and t["ref_line"] >= 1 and t["condition_id"]


def test_t7_the_rule_does_not_move_when_a_condition_fails():
    posts = (_post("p1", stock=_BOTH_STOCK),)
    baseline = _run([_LINE], posts)[0]
    assert baseline["match_status"] == "matched_list_shime"

    def unchanged(row):
        assert row["match_status"] != "matched_list_shime" and "soldout_target_basis" not in row

    unchanged(_run([f"{_LINE} 3@1,500円"], posts, specs=[_PRICED])[0])  # 価格がある
    unchanged(_run(["ファイブ、ピヨピヨ商品", "〆"], posts, specs=[("none", "none")], sold_lines={0: [1, 2]})[0])  # 2行ある
    unchanged(_run([_LINE], posts, fixed={0: 62})[0])  # 人が決めた商品がある
    unchanged(_run([_LINE], ())[0])  # soldout_posts が空


def test_t8_followup_and_context_work_decide_after_rule_14_but_rule_14_decides_first():
    posts = (_post("p1", stock=_BOTH_STOCK),)
    # 直前の投稿が A だけを含む（followup なら A に決まる形）
    followup = ("p0", "ファイブ ピヨピヨ 3@1,500円")  # 62 だけに決まる行（63 の語は「ピヨピヨ商品」）で、〆の行の語が全部当たる
    without = _run([_LINE], (), followup_ref=followup)[0]
    assert without["match_status"] == "matched_followup" and without["product_id"] == 62  # 11/16 の形（片方に決まる）
    row = _run([_LINE], posts, followup_ref=followup)[0]
    assert row["match_status"] == "matched_list_shime"
    assert row["product_id"] == _pairs(row)[0][0] == 62  # 書く行の商品は A の相手の先頭
    assert (63, 31) in _pairs(row)[1:]  # B の相手は2つ目以降
    # 前後の件の作品が A だけを指す（65 は A と同じ作品 1。B の作品は 2）形：_apply_context_work が A に決める
    around = ["チガウモノ 3@1,500円", _LINE, "チガウモノ 3@1,500円"]
    specs = [_PRICED, ("none", "none"), _PRICED]
    ctx_without = _run(around, (), specs=specs)[1]
    assert ctx_without["match_status"] == "matched_context" and ctx_without["product_id"] == 62
    ctx_row = _run(around, posts, specs=specs)[1]
    assert ctx_row["match_status"] == "matched_list_shime"
    assert ctx_row["product_id"] == _pairs(ctx_row)[0][0] == 62
    assert (63, 31) in _pairs(ctx_row)[1:]


_ITEM_MASTERS = {
    "cond_entries": _COND, "cond_canonical_to_uuid": {_BOX: "21", _CASE: "22"}, "ship_entries": [], "status_entries": _STATUS,
    "unit_alias_to_info": {"BOX": ("BOX", "箱系")},
}


def test_t9_the_saved_rows_resolve_the_head_product_and_leave_the_other_as_an_extra_target():
    posts = (_post("p1", stock=_BOTH_STOCK),)
    item = _run([_LINE], posts)[0]
    values = svc._analysis_values(item, _ITEM_MASTERS, {}, {})
    assert (values["product_id"], values["pid_resolved"], values["pid_basis"]) == (62, True, "V102:matched_list_shime")
    assert values["status"] == "Sold out"
    values = svc._apply_soldout_targets(values, item, None, {21: _CASE, 31: _CASE})
    assert (values["condition_id"], values["condition_basis"]) == (21, "SOLDOUT_LIST_SHIME")
    extra = svc._extra_targets(values, item, None)
    assert [(t["product_id"], t["condition_id"]) for t in extra] == [(63, 31)]
    # product_id が決まる状態の一覧に入っている（足し忘れると None・False で保存される）
    assert "matched_list_shime" in svc._RESOLVED_MATCH_STATUSES


def test_t10_only_the_product_that_has_stock_is_closed_and_none_means_unchanged():
    only_b = _run([_LINE], (_post("p1", stock=(_si([2], 63, 31, _CASE),)),))[0]
    assert only_b["match_status"] == "matched_list_shime" and only_b["product_id"] == 63
    assert _pairs(only_b) == [(63, 31)]
    only_a = _run([_LINE], (_post("p1", stock=(_si([1], 62, 21, _CASE),)),))[0]
    assert only_a["product_id"] == 62 and _pairs(only_a) == [(62, 21)]
    neither = _run([_LINE], (_post("p1", stock=(_si([1], 65, 41, _CASE),)),))[0]
    assert neither["match_status"] == "ambiguous" and "soldout_targets" not in neither


def test_t11_a_stock_of_the_same_state_as_the_shime_still_makes_the_target():
    # 〆の状態は Sealed box（単位の既定）。A の過去の在庫も Sealed box（規則12d で何も返らない形）
    same_state = (_si([1], 62, 21, _BOX), _si([2], 63, 31, _CASE))
    posts = (_post("p1", stock=same_state),)
    item = _run([_LINE], posts)[0]
    assert item["match_status"] == "matched_list_shime"
    assert _pairs(item) == [(62, 21), (63, 31)]
    shime_item = {"status_effect": "excluded", "status": "Sold out", "match_status": "matched", "product_id": 62,
                  "condition": _BOX, "condition_basis": "R4:単位既定"}
    assert sr.decide_soldout_inherit([shime_item], posts) == {}  # 規則12では空（12d）
    found = sr.list_shime_targets(62, [shime_item], 0, posts, None, box_rule=None, post_text="")
    assert [(t.product_id, t.condition_id) for t in found] == [(62, 21)]


def test_t12_a_condition_word_in_the_line_keeps_the_rule_off():
    posts = (_post("p1", stock=_BOTH_STOCK),)
    row = _run(["ファイブ シュリンク付き、ピヨピヨ商品 開封〆"], posts)[0]
    assert row["match_status"] != "matched_list_shime" and "soldout_target_basis" not in row


def test_t13_a_state_already_sold_in_a_newer_post_gives_no_target():
    newer = _post("p2", hours_before=0.5, sold=(sr.SoldItem(62, _BOX),))
    older = _post("p1", hours_before=1.0, stock=(_si([1], 62, 21, _BOX), _si([2], 63, 31, _CASE)))
    item = {"status_effect": "excluded", "status": "Sold out", "match_status": "matched", "product_id": 62,
            "condition": _BOX, "condition_basis": "R4:単位既定"}
    assert sr.list_shime_targets(62, [item], 0, (newer, older), None, box_rule=None, post_text="") == ()
    row = _run([_LINE], (newer, older))[0]
    assert row["match_status"] == "matched_list_shime" and row["product_id"] == 63
    assert _pairs(row) == [(63, 31)]  # A の相手は作らない


def test_t14_a_word_that_only_counts_after_the_box_recheck_keeps_the_rule_off():
    # 単位の区分が「条件つき」（ロット）。照合前は単位の既定でも、箱系の商品に決めた後は「開封」の語で状態が決まる
    posts = (_post("p1", stock=_BOTH_STOCK),)
    row = _run(["ファイブ、ピヨピヨ商品 開封 ロット〆"], posts)[0]
    assert row["match_status"] != "matched_list_shime" and "soldout_target_basis" not in row


def test_t15_a_stock_row_that_points_at_a_product_of_the_group_keeps_the_rule_off():
    posts = (_post("p1", stock=_BOTH_STOCK),)
    # 候補に A を含む在庫の件（完売でない件）
    lines = ["ファイブ 3@1,500円", _LINE]
    row = _run(lines, posts, specs=[_PRICED, ("none", "none")])[1]
    assert row["match_status"] != "matched_list_shime"
    # 候補を持たない unmatched の在庫の件が followup_ref で A に決まる形（単位の語を含む直前の投稿の行）
    # 在庫の行の「ボックス」は単位の語。直前の投稿の行には無いので、units を渡さないと決まらない（_apply_followup と同じ units を渡している証拠）
    followup = ("p0", "ファイブ ズッシリ 3@1,500円")
    stock_line = "ズッシリ ボックス 3@1,500円"
    specs = [_PRICED, ("none", "none")]
    no_followup = _run([stock_line, _LINE], posts, specs=specs)
    assert no_followup[0]["match_status"] == "unmatched" and no_followup[0]["match_candidates"] == []
    assert no_followup[1]["match_status"] == "matched_list_shime"  # 対照: followup_ref が無ければ規則14は動く
    rows = _run([stock_line, _LINE], posts, followup_ref=followup, specs=specs)
    assert rows[0]["match_status"] == "matched_followup" and rows[0]["product_id"] == 62
    assert rows[1]["match_status"] != "matched_list_shime" and "soldout_target_basis" not in rows[1]


def test_t16_a_single_product_decided_by_its_class_still_works_and_its_target_comes_from_single_stock():
    products = (_p(62, 1, "ファイブ"), _p(63, 2, "ピヨピヨ商品"))
    master = ProductFirstMasters(
        product_entries=products, product_kubun={"62": "シングル系", "63": "箱系"},
        condition_unit={"Sealed box": "Box"}, ignore_phrases=(), scoped_cond_entries=_SINGLE_ROWS,
    )
    posts = (_post("p1", stock=(_si([1], 62, 21, "Single"), _si([2], 63, 31, _CASE))),)
    row = _run([_LINE], posts, master=master)[0]
    assert row["match_status"] == "matched_list_shime" and row["product_id"] == 62
    assert row["condition_basis"] == "R7:単品既定"  # A の状態は行の語でなく商品の分類（単品既定）から決まった
    assert row["soldout_target_basis"] == "SOLDOUT_LIST_SHIME"
    assert _pairs(row) == [(62, 21), (63, 31)]  # A の相手は Single の在庫の行から作られる（2の2）
    built_basis = sr.is_kind_default_basis("R7:単品既定")
    assert built_basis is True and sr.is_kind_default_basis("R2:PSA") is False
    assert sr.is_kind_default_basis("単品語あり・要確認(x),R7:単品既定") is True
