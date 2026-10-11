"""Gemini 書き写し v10.1（受け取り・行の役割・付け直し・原文からの取り出し）の単体試験。Gemini・DB は使わない。

設計: docs/handoff/gemini-v101/design.md §3-3〜§3-5・§5-4
"""
from __future__ import annotations

import json

import pytest

from app.services import gemini_raw_copy_v101 as v101
from app.services.extraction_judgement_svc import PriceQtyResult

_UNITS = {
    "BOX": ("BOX", "箱系"), "box": ("BOX", "箱系"), "ボックス": ("BOX", "箱系"),
    "カートン": ("カートン", "箱系大"), "パック": ("パック", "パック系"),
    "ﾏｽﾀｰｶｰﾄﾝ": ("MasterCarton", "箱系大"), "セット": ("セット", "セット系"), "枚": ("枚", "単品系"),
    "case": ("Case", "箱系大"), "piece": ("Piece", "単品系"), "ケース": ("Case", "箱系大"),
}


def _cond(code, canonical, priority, app_kubun, search_kw):
    return {
        "cond_id": f"c-{code}", "code": code, "canonical": canonical, "priority": priority,
        "app_kubun": app_kubun, "search_kw": search_kw, "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
    }


_COND = [
    _cond("CN0100", "FLAG_SINGLE", 1, "箱系,箱系大", "PSA,SR"),
    _cond("CN0002", "Damaged sealed box", 2, "箱系", "ダメージ,難あり"),
    _cond("CN0005", "No shrink box", 3, "箱系", "シュリ無し,シュリなし"),
    _cond("CN0004", "Sealed box", 3, "箱系", "シュリンク付き,美品"),
    _cond("CN0009", "Unsearched pack", 3, "パック系", "未サーチ"),
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


def _it(lines, price, quantity="1"):
    return {"lines": list(lines), "price": price, "quantity": quantity}


def _resp(*items):
    return json.dumps({"items": list(items)}, ensure_ascii=False)


def _parse(raw, *items):
    return v101.parse_v101_response(_resp(*items), raw, status_entries=_STATUS)


def _extract(raw, *items, reassign=True, order=None):
    parsed, errors = _parse(raw, *items)
    assert errors == []
    return v101.extract_v101_items(parsed, raw, order=order, reassign=reassign, **_MASTERS)


def _ctx():
    return v101.build_context(order=None, **_MASTERS)


# ---------------------------------------------------------------------------
# 受け取り（設計 §3-3）
# ---------------------------------------------------------------------------


def test_price_line_is_first_line_containing_the_price_text_ignoring_spaces_and_width():
    raw = "商品A\n12BOX ＠ 20,100円\n残り3"
    items, errors = _parse(raw, _it([3, 2, 1, 2], "20,100円", "12"))
    assert errors == []
    assert items == [{"lines": [1, 2, 3], "price": "20,100円", "quantity": "12", "price_line": 2}]


def test_price_line_for_two_prices_joined_by_slash_uses_the_first_price():
    raw = "セット\n5000円 (1個 1,000円)"
    items, _ = _parse(raw, _it([1, 2], "5000円／1,000円", "5"))
    assert items[0]["price_line"] == 2


def test_price_none_uses_first_line_with_quantity_text():
    raw = "商品A\n在庫 残り3"
    items, _ = _parse(raw, _it([1, 2], "none", "残り3"))
    assert items[0]["price_line"] == 2


def test_price_none_uses_sold_out_word_line_when_quantity_is_none():
    raw = "◆スカーレット\n完売\nメモ"
    items, _ = _parse(raw, _it([1, 2, 3], "none", "none"))
    assert items[0]["price_line"] == 2


def test_price_none_without_clue_uses_last_line():
    raw = "商品A\nメモ1\nメモ2"
    items, _ = _parse(raw, _it([1, 2, 3], "none", "none"))
    assert items[0]["price_line"] == 3


def test_missing_price_line_drops_the_item():
    items, errors = _parse("商品A\n3BOX", _it([1, 2], "1,000円"))
    assert items == [] and "価格の行が見つからない" in errors[0]["error"]


def test_same_price_line_keeps_first_and_drops_later():
    raw = "商品A\n3BOX@1,000円"
    items, errors = _parse(raw, _it([1, 2], "1,000円"), _it([2], "1,000円"))
    assert len(items) == 1 and errors[0]["index"] == 1 and "同じ" in errors[0]["error"]


def test_shared_lines_between_items_are_accepted():
    raw = "見出し\n【9/28発送】\n@80,000円\n@3,000円"
    items, errors = _parse(raw, _it([1, 2, 3], "80,000円"), _it([1, 2, 4], "3,000円"))
    assert errors == [] and len(items) == 2


@pytest.mark.parametrize("bad_lines", [[], [0, 1], [1, 99], "1", [True], [1.5]])
def test_empty_or_out_of_range_or_wrong_type_lines_drop_the_item(bad_lines):
    items, errors = _parse("a\nb", {"lines": bad_lines, "price": "1", "quantity": "1"})
    assert items == [] and len(errors) == 1


def test_missing_field_and_wrong_price_type_drop_the_item():
    items, errors = v101.parse_v101_response(
        _resp({"lines": [1], "price": "1"}, {"lines": [1], "price": 5, "quantity": "1"}), "a\nb"
    )
    assert items == [] and [e["index"] for e in errors] == [0, 1]


@pytest.mark.parametrize("text", ["not json", "[]", '{"items": 1}'])
def test_unreadable_json_is_one_whole_error(text):
    items, errors = v101.parse_v101_response(text, "a")
    assert items == [] and len(errors) == 1 and errors[0]["index"] is None


def test_schema_requires_the_three_fields():
    item = v101.V101_RESPONSE_SCHEMA["properties"]["items"]["items"]
    assert set(item["required"]) == set(item["properties"]) == {"lines", "price", "quantity"}
    assert item["properties"]["lines"] == {"type": "array", "items": {"type": "integer"}}


def test_prompt_files_load_and_bad_names_are_rejected():
    assert "行番号の担当" in v101.load_v101_prompt()
    assert "行番号の担当" in v101.load_v101_prompt("raw_copy_v101_b")
    for bad in ("raw_copy_v9", "../raw_copy_v101_a", "raw_copy_v101_A"):
        with pytest.raises(ValueError):
            v101.load_v101_prompt(bad)


# ---------------------------------------------------------------------------
# 行の役割（設計 §3-4）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "role"),
    [
        ("10BOX@1,000円", "price"),
        ("【9/28発送】", "ship"),
        ("シュリ無し", "condition"),
        ("未サーチパック", "condition"),
        ("■[PSA10]SR保証", "name"),
        ("残り170", "stock"),
        ("在庫数5", "stock"),
        ("10BOX", "stock"),
        ("完売", "stock"),
        ("■OP-07 500年後の未来", "name"),
    ],
)
def test_line_role(text, role):
    assert v101.line_role(text, _ctx(), is_price_line=(role == "price")) == role


def test_state_line_with_extra_words_is_a_name_line():
    assert v101.line_role("シュリ無しのリーフレット付き豪華セット", _ctx(), is_price_line=False) == "name"


def test_price_line_wins_over_ship_word():
    assert v101.line_role("300BOX@1,500 10/3発送", _ctx(), is_price_line=True) == "price"


def test_assign_roles_returns_role_per_line_per_item():
    raw = "見出し\n【9/28発送】\n@80,000円"
    items, _ = _parse(raw, _it([1, 2, 3], "80,000円"))
    roles = v101.assign_roles(items, raw.split("\n"), _ctx())
    assert roles == [{1: "name", 2: "ship", 3: "price"}]


# ---------------------------------------------------------------------------
# 迷う行の付け直し（設計 §3-4）
# ---------------------------------------------------------------------------


def _reassign(raw, *items):
    parsed, errors = _parse(raw, *items)
    assert errors == []
    return v101.reassign_ambiguous(parsed, raw.split("\n"), _ctx())


# 並び方の証拠が「価格の上に書く」形の投稿（先頭の見出しの下に発送、2件目の発送は価格の上）
_RAW_ABOVE = "\n".join([
    "■A", "10/3発送", "300BOX@1,500",   # 1-3: 発送が価格の上（証拠: 上）
    "", "■B", "10/9発送", "200BOX@1,400",  # 5-7: 同じ
    "", "■C", "100BOX@900", "10/12発送", "50BOX@800",  # 9-12: 迷う行 11
])
# 証拠が「価格の下に書く」形
_RAW_BELOW = "\n".join([
    "■A", "300BOX@1,500", "10/3発送",       # 1-3: 証拠: 下
    "", "■B", "200BOX@1,400", "10/9発送",   # 5-7
    "", "■C", "100BOX@900", "10/12発送", "50BOX@800",  # 迷う行 11
])


def test_ambiguous_line_goes_to_next_item_when_all_evidence_is_written_above_the_price():
    items, reassigned, review = _reassign(
        _RAW_ABOVE, _it([9, 10, 11], "900"), _it([9, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"),
    )
    assert 11 in items[1]["lines"] and 11 not in items[0]["lines"]
    assert review == {} and reassigned[1][0]["from_price_lines"] == [10] and reassigned[1][0]["to_price_line"] == 12
    assert "上" in reassigned[1][0]["reason"]


def test_ambiguous_line_goes_to_previous_item_when_all_evidence_is_written_below_the_price():
    items, reassigned, _ = _reassign(
        _RAW_BELOW, _it([9, 10], "900"), _it([9, 11, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"),
    )
    assert 11 in items[0]["lines"] and 11 not in items[1]["lines"]
    assert reassigned[0][0]["to_price_line"] == 10 and "下" in reassigned[0][0]["reason"]


def test_no_change_and_no_record_when_gemini_already_agrees():
    items, reassigned, review = _reassign(
        _RAW_ABOVE, _it([9, 10], "900"), _it([9, 11, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"),
    )
    assert reassigned == {} and review == {} and 11 in items[1]["lines"]


def test_mixed_evidence_falls_to_price_rule_damaged_goes_to_cheaper_item():
    raw = "\n".join([
        "■A", "10/3発送", "300BOX@1,500", "", "■B", "200BOX@1,400", "10/9発送", "",  # 発送の証拠は上と下が混在
        "■C", "100BOX@900", "ダメージ有り", "50BOX@800",
    ])
    # 状態の行 11 は、証拠が無い（状態の迷わない行が無い）ので値段の決まりへ。安い件 = 800（price_line 12）
    items, reassigned, _ = _reassign(
        raw, _it([9, 10, 11], "900"), _it([9, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"),
    )
    assert 11 in items[1]["lines"] and "安い" in reassigned[1][0]["reason"]


def test_shrink_wrapped_goes_to_the_more_expensive_item():
    raw = "■C\n100BOX@900\nシュリンク付き\n50BOX@800"
    items, reassigned, _ = _reassign(raw, _it([1, 2, 3], "900"), _it([1, 4], "800"))
    assert 3 in items[0]["lines"] and reassigned == {} and items[1]["lines"] == [1, 4]


def test_shrink_wrapped_moves_to_pricier_item_when_gemini_put_it_with_the_cheaper_one():
    raw = "■C\n100BOX@900\nシュリンク付き\n50BOX@800"
    items, reassigned, _ = _reassign(raw, _it([1, 2], "900"), _it([1, 3, 4], "800"))
    assert 3 in items[0]["lines"] and 3 not in items[1]["lines"] and "高い" in reassigned[0][0]["reason"]


def test_price_rule_is_not_used_when_units_differ_and_line_goes_to_review():
    raw = "■C\n100BOX@900\nダメージ有り\n3カートン@800"
    items, reassigned, review = _reassign(raw, _it([1, 2, 3], "900"), _it([1, 4], "800"))
    assert reassigned == {} and items[0]["lines"] == [1, 2, 3]
    assert review == {0: [{"line": 3, "kind": "condition"}]}


def test_unresolved_ship_line_is_review_and_kept_as_gemini_wrote():
    raw = "■C\n100BOX@900\n10/12発送\n50BOX@800"
    items, reassigned, review = _reassign(raw, _it([1, 2, 3], "900"), _it([1, 4], "800"))
    assert items[0]["lines"] == [1, 2, 3] and reassigned == {} and review[0][0]["kind"] == "ship"


def test_reassign_off_keeps_gemini_lines_and_records_nothing():
    raw = "\n".join(_RAW_ABOVE.split("\n"))
    on = _extract(raw, _it([9, 10, 11], "900"), _it([9, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"))
    off = _extract(
        raw, _it([9, 10, 11], "900"), _it([9, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"),
        reassign=False,
    )
    assert on[0][0]["ship"] == "none" and on[0][1]["ship"] == "10/12発送"
    assert off[0][0]["ship"] == "10/12発送" and off[0][1]["ship"] == "none"
    assert all(r["reassigned"] == [] and r["review"] == [] for r in off[0])


def test_reassign_does_not_change_the_input_items():
    parsed, _ = _parse(_RAW_ABOVE, _it([9, 10, 11], "900"), _it([9, 12], "800"))
    before = json.dumps(parsed)
    v101.reassign_ambiguous(parsed, _RAW_ABOVE.split("\n"), _ctx())
    assert json.dumps(parsed) == before


# ---------------------------------------------------------------------------
# 名前（設計 §3-5）
# ---------------------------------------------------------------------------


def test_two_line_heading_is_joined_in_line_order():
    raw = "■ワンピースカード\n　ロマンスドーン\n12BOX@20,100円"
    (r,), _ = _extract(raw, _it([1, 2, 3], "20,100円", "12"))
    assert r["name"] == "■ワンピースカード ロマンスドーン"
    assert r["unit"] == "BOX" and r["price_normalized"] == 20100 and r["quantity_normalized"] == 12


def test_vol2_style_name_continues_in_price_line():
    raw = "●プレミアムバンダイ限定コレクション\nVol.2@3,500×40\nVol.1@3,000×50"
    r, _ = _extract(raw, _it([1, 2], "3,500", "40"), _it([1, 3], "3,000", "50"))
    assert r[0]["name"] == "●プレミアムバンダイ限定コレクション Vol.2"
    assert r[1]["name"] == "●プレミアムバンダイ限定コレクション Vol.1"


def test_op14_then_carton_line_takes_previous_line_as_name():
    raw = "OP-14 11,500円/5box\nカートン 160,000円/13カートン"
    r, _ = _extract(raw, _it([1], "11,500円", "5"), _it([1, 2], "160,000円", "13"))
    assert r[0]["name"] == "OP-14" and r[1]["name"] == "OP-14"  # 単位の別名だけの語は名前に足さない
    assert r[1]["unit"] == "カートン" and r[1]["quantity_normalized"] == 13


def test_digits_inside_the_name_are_kept():
    raw = "ポケモンカード151 BOX @8,000円 ×20"
    (r,), _ = _extract(raw, _it([1], "8,000円", "20"))
    assert r["name"].startswith("ポケモンカード151")


def test_sold_out_only_item_takes_the_heading_name_without_the_sold_out_word():
    raw = "◆スカーレットex\n完売\nパック@150円"
    r, _ = _extract(raw, _it([1, 2], "none", "none"), _it([1, 3], "150円", "none"))
    assert r[0]["name"] == "◆スカーレットex" and (r[0]["status"], r[0]["status_effect"]) == ("sold_out", "excluded")
    assert r[1]["status"] == "active" and r[1]["unit"] == "パック"


def test_name_falls_back_to_price_line_text_when_nothing_remains():
    (r,), _ = _extract("@1,000円", _it([1], "1,000円", "none"))
    assert r["name"] == "@1,000円"


# ---------------------------------------------------------------------------
# 単位（設計 §3-5）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("price_line", "price", "unit"),
    [
        ("パック 160円", "160円", "パック"),
        ("ﾏｽﾀｰｶｰﾄﾝ（7case入）＠420,000円", "420,000円", "MasterCarton"),
        ("12BOX@20,100円", "20,100円", "BOX"),
        ("ボックス/¥13,000", "¥13,000", "BOX"),
    ],
)
def test_unit_positions(price_line, price, unit):
    (r,), _ = _extract(f"商品\n{price_line}", _it([1, 2], price, "none"))
    assert r["unit"] == unit


def test_line_with_only_a_unit_word_gives_the_unit():
    (r,), _ = _extract("商品\nカートン\n@150,000円", _it([1, 2, 3], "150,000円", "none"))
    assert r["unit"] == "カートン"


def test_price_line_unit_wins_over_unit_in_description_line():
    raw = "商品\n特典カード4枚付き\n10セット@3,000円"
    (r,), _ = _extract(raw, _it([1, 2, 3], "3,000円", "10"))
    assert r["unit"] == "セット"


def test_unit_inside_a_product_name_before_digits_and_at_is_not_picked():
    raw = "ゴールデンボックス10@ 5,000円"
    (r,), _ = _extract(raw, _it([1], "5,000円", "none"))
    assert r["unit"] == "none"


def test_shared_lines_are_not_searched_for_unit():
    raw = "見出し\n3BOX\n@1,000円\n@2,000円"
    a, b = _extract(raw, _it([1, 2, 3], "1,000円", "none"), _it([1, 2, 4], "2,000円", "none"))[0]
    assert a["unit"] == "none" and b["unit"] == "none"


# ---------------------------------------------------------------------------
# 発送（設計 §3-5）
# ---------------------------------------------------------------------------


def test_ship_in_brackets_with_outside_text_takes_the_bracket_content():
    (r,), _ = _extract("商品A 【10/12発送】\n3BOX@1,000円", _it([1, 2], "1,000円", "3"))
    assert r["ship"] == "10/12発送"


def test_ship_after_price_in_price_line_drops_stock_and_leading_mark():
    (r,), _ = _extract("商品A\n@1,500円 在庫200※発売日発送", _it([1, 2], "1,500円", "在庫200"))
    assert r["ship"] == "発売日発送"


def test_ship_in_heading_line_takes_only_the_word_with_the_ship_word():
    (r,), _ = _extract("■スタートデッキ100 9月27までに発送\n300BOX@1,500", _it([1, 2], "1,500", "300"))
    assert r["ship"] == "9月27までに発送"


def test_two_ship_lines_of_one_item_are_joined_with_slash_in_line_order():
    raw = "商品A\n3BOX@1,000円\n20日発送\n発売日は後日"
    (r,), _ = _extract(raw, _it([1, 2, 3, 4], "1,000円", "3"))
    assert r["ship"] == "20日発送 / 発売日は後日"


def test_shared_ship_line_is_used_only_when_the_item_has_none_of_its_own():
    raw = "●DM26\n【9/28発送】\n@80,000円\n@3,000円\n10/1発送"
    a, b = _extract(raw, _it([1, 2, 3], "80,000円", "none"), _it([1, 2, 4, 5], "3,000円", "none"))[0]
    assert a["ship"] == "【9/28発送】" and b["ship"] == "10/1発送"


def test_ship_is_none_without_a_ship_line():
    (r,), _ = _extract("商品A\n3BOX@1,000円", _it([1, 2], "1,000円", "3"))
    assert r["ship"] == "none"


# ---------------------------------------------------------------------------
# 状態・印（設計 §3-5）
# ---------------------------------------------------------------------------


def test_condition_is_resolved_from_all_lines_of_the_item():
    raw = "ストーム\nボックス/¥12,000\nシュリ無し\n残り170"
    (r,), _ = _extract(raw, _it([1, 2, 3, 4], "¥12,000", "残り170"))
    assert r["condition"] == "No shrink box" and r["condition_basis"].startswith("R3")
    assert r["roles"] == {1: "name", 2: "price", 3: "condition", 4: "stock"}


def test_quantity_not_in_text_for_carton_with_invented_quantity():
    (r,), _ = _extract("カートン @150,000円", _it([1], "150,000円", "1"))
    assert r["quantity_not_in_text"] is True


def test_quantity_in_text_is_not_flagged():
    (r,), _ = _extract("12BOX@20,100円", _it([1], "20,100円", "12"))
    assert r["quantity_not_in_text"] is False
    (r,), _ = _extract("商品", _it([1], "none", "none"))
    assert r["quantity_not_in_text"] is False


def test_possible_missing_item_lists_price_shaped_lines_between_items():
    raw = "商品A\n3BOX@1,000円\n商品B\n5BOX@2,000円\n商品C\n7BOX@3,000円\n2025"
    _items, flags = _extract(raw, _it([1, 2], "1,000円", "3"), _it([5, 6], "3,000円", "7"))
    assert flags == {"possible_missing_item": [4]}


def test_possible_missing_item_ignores_year_only_and_lines_outside_the_items():
    raw = "2026\n商品A\n3BOX@1,000円\n2025\n商品B\n5BOX@2,000円\n@9,999円"
    _items, flags = _extract(raw, _it([2, 3], "1,000円", "3"), _it([5, 6], "2,000円", "5"))
    assert flags == {"possible_missing_item": []}


def test_output_has_the_documented_keys():
    (r,), flags = _extract("商品A\n3BOX@1,000円", _it([1, 2], "1,000円", "3"))
    assert set(r) == {
        "price_line", "lines", "roles", "raw_price", "raw_quantity", "name", "unit", "unit_kubun", "condition",
        "condition_basis", "status", "status_effect", "ship", "price_normalized", "quantity_normalized",
        "price_reasons", "quantity_not_in_text", "reassigned", "review",
    }
    assert set(flags) == {"possible_missing_item"}
    json.dumps(r, ensure_ascii=False)  # JSONL に書ける


def test_ship_line_after_price_keeps_the_whole_line_even_with_several_words():
    (r,), _ = _extract("100box 23000円\n17日発送　福岡", _it([1, 2], "23000円", "100"))
    assert r["ship"] == "17日発送　福岡"


def test_ship_line_in_heading_position_takes_only_the_word_with_ship_word_and_keeps_name():
    (r,), _ = _extract("・30th CELEBRATION 16日発送\n在庫300/23500円", _it([1, 2], "23500円", "在庫300"))
    assert r["ship"] == "16日発送" and "30th CELEBRATION" in r["name"]


def test_price_line_rest_drops_condition_word_and_quantity_with_unit():
    (r,), _ = _extract("アビスアイ\n7,000×20BOX シュリ無し", _it([1, 2], "7,000", "20"))
    assert r["name"] == "アビスアイ"


def test_price_line_rest_drops_quantity_word_starting_with_suuryou():
    (r,), _ = _extract("▪️頂上の決戦 OP-02\n27,000円 数量3箱", _it([1, 2], "27,000円", "数量3箱"))
    assert r["name"] == "▪️頂上の決戦 OP-02"


def test_unit_is_not_taken_from_a_name_line():
    raw = "・AR・CHR 100枚セット 被りなし\n在庫10/25000円"
    (r,), _ = _extract(raw, _it([1, 2], "25000円", "在庫10"))
    assert r["unit"] == "none"


def test_unit_is_not_taken_from_a_heading_line_with_a_unit_word():
    (r,), _ = _extract("◉ OP-12 カートン\n235000@1", _it([1, 2], "235000", "1"))
    assert r["unit"] == "none"


def test_unit_is_taken_from_a_stock_line():
    (r,), _ = _extract("商品\n@3,000円\n10BOX", _it([1, 2, 3], "3,000円", "10"))
    assert r["unit"] == "BOX"


def test_dai2dan_word_in_price_line_is_kept_in_the_name():
    raw = "●プレミアムバンダイ限定コレクション\n第2弾@3,500×40"
    (r,), _ = _extract(raw, _it([1, 2], "3,500", "40"))
    assert "第2弾" in r["name"]


def test_ship_before_price_in_price_line_without_spaces():
    (r,), _ = _extract("ハイペアリシティ発売日前日発送600@9900", _it([1], "9900", "600"))
    assert r["ship"] == "発売日前日発送"


def test_ship_before_price_stops_at_quantity_word():
    (r,), _ = _extract("✅発送日②（要相談）数量：1カートン　＠412,000", _it([1], "412,000", "1カートン"))
    assert r["ship"] == "発送日②（要相談）"


def test_stock_line_with_reirruka_word_is_not_a_ship_line():
    raw = "商品A\n3,000円\n残り334 再入荷しました⚡️"
    (r,), _ = _extract(raw, _it([1, 2, 3], "3,000円", "残り334"))
    assert r["ship"] == "none" and r["roles"][3] == "stock"


def test_unit_alias_word_is_kept_in_name_when_other_words_remain():
    (r,), _ = _extract("ONE PIECE × ROUND1 プロモパック 未開封 100@4000", _it([1], "4000", "100"))
    assert "ONE PIECE" in r["name"]


def test_price_line_word_with_ship_word_is_not_added_to_name():
    (r,), _ = _extract("商品A\nBOX特典 （9/18発送） 3,000円", _it([1, 2], "3,000円", "none"))
    assert "9/18" not in r["name"] and "BOX特典" in r["name"]


def test_heading_with_ship_bracket_keeps_other_words_and_bracket_is_removed_whole():
    raw = "◆ヴァイスシュヴァルツ ブースター anemoi（問屋品）（発送日要相談）\n54000円/ 1ケース"
    (r,), _ = _extract(raw, _it([1, 2], "54000円", "1ケース"))
    assert "anemoi" in r["name"] and "発送日要相談" not in r["name"]
    assert r["ship"] == "発送日要相談"


def test_name_keeps_word_starting_with_digit_like_30th():
    (r,), _ = _extract("30th CELEBRATION 24,200円/400box 発送日相談", _it([1], "24,200円", "400"))
    assert r["name"] == "30th CELEBRATION" and r["ship"] == "発送日相談"


def test_name_keeps_digit_only_name_that_is_not_the_quantity_or_price():
    (r,), _ = _extract("151 51,500円/2box", _it([1], "51,500円", "2"))
    assert r["name"] == "151"


def test_same_ship_sentence_on_two_lines_is_listed_once():
    raw = "商品A\n※発送日相談\n3BOX@1,000円\n※発送日相談"
    (r,), _ = _extract(raw, _it([1, 2, 3, 4], "1,000円", "3"))
    assert r["ship"] == "※発送日相談"


# ---------------------------------------------------------------------------
# v10.2 の確認と直し F1〜F6（設計: docs/handoff/gemini-v102/design.md §3-1・§5-3）
# ---------------------------------------------------------------------------


def _extract102(raw, *items, reassign=True):
    parsed, errors = _parse(raw, *items)
    assert errors == []
    return v101.extract_v101_items(parsed, raw, order=None, reassign=reassign, v102_fixes=True, **_MASTERS)


_CHILD_NAMES = ["キモリ", "アチャモ", "ミズゴロウ", "ナエトル", "ヒコザル", "ポッチャマ", "ツタージャ", "ポカブ", "ミジュマル"]


def _parent_children_post(parent="■ポケモンカード カードセット 発送日要相談"):
    lines = [parent]
    items = []
    for idx, child in enumerate(_CHILD_NAMES):
        heading_no = len(lines) + 1
        lines += [f"・カードセット {child}", "@4,500円"]
        items.append(_it([1, heading_no, heading_no + 1], "4,500円", "3"))
    return "\n".join(lines), items


def test_f1_removes_parent_heading_shared_by_nine_children_so_ship_is_none_and_name_is_child():
    # Arrange
    raw, items = _parent_children_post()
    # Act
    out, _flags = _extract102(raw, *items)
    # Assert
    assert len(out) == 9
    for child, one in zip(_CHILD_NAMES, out):
        assert 1 not in one["lines"]
        assert one["ship"] == "none"
        assert one["name"] == f"・カードセット {child}"
        assert [f["rule"] for f in one["fixes"]] == ["F1"] and one["fixes"][0]["line"] == 1


def test_f1_keeps_parent_heading_when_v102_fixes_is_false():
    raw, items = _parent_children_post()
    out, flags = _extract(raw, *items)
    assert all(1 in one["lines"] for one in out) and out[0]["ship"] != "none"
    assert all("fixes" not in one for one in out) and set(flags) == {"possible_missing_item"}


def test_f1_keeps_heading_without_ship_word_with_condition_and_carton_lines():
    raw = "【世界最強の戦士 OP-17】\n美品\n9個 16,300円\nカートン\n1個 248,000円"
    out, _ = _extract102(raw, _it([1, 2, 3], "16,300円", "9"), _it([1, 4, 5], "248,000円", "1"))
    assert all(1 in one["lines"] for one in out)
    assert [one["fixes"] for one in out] == [[], []]


def test_f1_keeps_heading_followed_by_empty_line_and_two_prices():
    raw = "◆30th CELEBRATION Booster BOX\n\n@28,000円\n在庫60※要相談\n\n@26,000円\n在庫200※発売日発送"
    out, _ = _extract102(raw, _it([1, 3, 4], "28,000円", "60"), _it([1, 6, 7], "26,000円", "200"))
    assert all(1 in one["lines"] for one in out) and all(one["fixes"] == [] for one in out)


def test_f1_keeps_heading_without_ship_word_with_two_quantity_prices():
    raw = "🌈UNION ARENA\nアイドルマスター\n1case＠77,000円\n陰の実力者\n10BOX＠115,000円"
    out, _ = _extract102(raw, _it([1, 2, 3], "77,000円", "1"), _it([1, 4, 5], "115,000円", "10"))
    assert all(1 in one["lines"] for one in out)


def test_f1_keeps_ship_line_shared_by_two_items_without_own_name_lines():
    raw = "商品見出し\n【9/28発送】\nA 80,000円\nB 3,000円"
    out, _ = _extract102(raw, _it([1, 2, 3], "80,000円", "1"), _it([1, 2, 4], "3,000円", "1"))
    assert all(2 in one["lines"] for one in out)
    assert [one["ship"] for one in out] == ["【9/28発送】", "【9/28発送】"]


def test_f1_keeps_ship_heading_when_only_some_items_have_own_name_line():
    raw = "【9/28発送】\n商品A\n@80,000円\n@3,000円"
    out, _ = _extract102(raw, _it([1, 2, 3], "80,000円", "1"), _it([1, 4], "3,000円", "1"))
    assert all(1 in one["lines"] for one in out)


def test_f2_prefixes_previous_price_line_name_when_name_is_only_units_and_quantity():
    raw = "OP-14  11,500円/5box\nカートン 160,000円/13カートン"
    out, _ = _extract102(raw, _it([1], "11,500円", "5"), _it([2], "160,000円", "13"))
    assert "OP-14" in out[1]["name"] and out[1]["name"].startswith("OP-14")
    assert out[0]["name"] == "OP-14"
    assert [f["rule"] for f in out[1]["fixes"]] == ["F2"] and out[0]["fixes"] == []


def test_f2_keeps_number_only_name_even_when_previous_line_is_a_price_line():
    raw = "OP-14  11,500円/5box\n151 51,500円/2box"
    out, _ = _extract102(raw, _it([1], "11,500円", "5"), _it([2], "51,500円", "2"))
    assert out[1]["name"] == "151" and out[1]["fixes"] == []


def test_f2_is_off_when_v102_fixes_is_false():
    raw = "OP-14  11,500円/5box\nカートン 160,000円/13カートン"
    out, _ = _extract(raw, _it([1], "11,500円", "5"), _it([2], "160,000円", "13"))
    assert "OP-14" not in out[1]["name"]


def test_f3_does_not_use_whole_bracket_line_as_name_when_another_name_line_exists():
    raw = "【ガンダムカードゲーム未開封BOX】\n・GD05 Freedom Ascension\n12BOX@8200円"
    out, _ = _extract102(raw, _it([1, 2, 3], "8200円", "12"))
    assert "【" not in out[0]["name"] and "ガンダム" not in out[0]["name"]
    assert out[0]["name"] == "・GD05 Freedom Ascension"
    assert [(f["rule"], f["line"]) for f in out[0]["fixes"]] == [("F3", 1)]


def test_f3_keeps_whole_bracket_line_when_it_is_the_only_name_line():
    raw = "【世界最強の戦士 OP-17】\n9個 16,300円"
    out, _ = _extract102(raw, _it([1, 2], "16,300円", "9"))
    assert "世界最強の戦士" in out[0]["name"] and out[0]["fixes"] == []


def test_f4_quantity_without_number_gives_none_normalized_and_flag():
    raw = "ワンピース ブースター\nカートン @150,000円"
    out, flags = _extract102(raw, _it([1, 2], "150,000円", "カートン"))
    assert out[0]["quantity_normalized"] is None
    assert flags["quantity_no_number"] == [2]
    assert "F4" in [f["rule"] for f in out[0]["fixes"]]


def test_f4_leaves_quantity_none_marker_and_numeric_quantity_alone():
    raw = "商品A\n3BOX@1,000円"
    out, flags = _extract102(raw, _it([1, 2], "1,000円", "3"))
    assert out[0]["quantity_normalized"] == 3 and flags["quantity_no_number"] == []


def test_f5_footer_line_after_last_price_line_is_not_name_and_is_flagged():
    raw = "商品A\n3BOX@1,000円\n・買取品"
    out, flags = _extract102(raw, _it([1, 2, 3], "1,000円", "3"))
    assert out[0]["name"] == "商品A"
    assert flags["possible_footer_line"] == [3]
    assert [(f["rule"], f["line"]) for f in out[0]["fixes"]] == [("F5", 3)]


def test_f5_possible_missing_item_does_not_pick_up_shipping_fee_line_after_last_price_line():
    raw = "商品A\n3BOX@1,000円\n送料 500円\n・買取品"
    out, flags = _extract102(raw, _it([1, 2, 4], "1,000円", "3"))
    assert flags["possible_missing_item"] == []
    _out101, flags101 = _extract(raw, _it([1, 2, 4], "1,000円", "3"))
    assert flags101["possible_missing_item"] == [3]
    assert out[0]["name"] == "商品A"


def test_f6_quantity_with_comma_is_found_in_text_with_comma():
    assert v101._quantity_not_in_text("2,000セット", "2,000セット @4,500", v102=True) is False


def test_f6_quantity_one_is_not_in_text_of_carton_with_price_only():
    assert v101._quantity_not_in_text("1", "カートン @150,000円", v102=True) is True


def test_f6_without_v102_flag_keeps_the_v101_judgement():
    assert v101._quantity_not_in_text("2,000セット", "2,000セット @4,500") is True  # v10.1 の誤検知（R6）はそのまま
    assert v101._quantity_not_in_text("2000セット", "2,000セット @4,500") is True


def test_v102_fixes_false_output_has_no_new_keys_and_is_unchanged_by_default():
    raw = "商品A\n3BOX@1,000円\n・買取品"
    parsed, _ = _parse(raw, _it([1, 2, 3], "1,000円", "3"))
    default = v101.extract_v101_items(parsed, raw, order=None, reassign=True, **_MASTERS)
    explicit = v101.extract_v101_items(parsed, raw, order=None, reassign=True, v102_fixes=False, **_MASTERS)
    assert default == explicit
    assert "fixes" not in default[0][0] and set(default[1]) == {"possible_missing_item"}


def test_v102_with_no_items_returns_empty_and_flags():
    out, flags = v101.extract_v101_items(
        [], "商品A", order=None, reassign=True, v102_fixes=True, **_MASTERS
    )
    assert out == [] and flags == {"possible_missing_item": [], "quantity_no_number": [], "possible_footer_line": []}


def test_f3_keeps_bracket_heading_when_the_only_other_name_line_is_two_chars():
    # Arrange
    raw = "【世界最強の戦士 OP-17】\n良品\n9個 16,300円"
    # Act
    out, _ = _extract102(raw, _it([1, 2, 3], "16,300円", "9"))
    # Assert
    assert "【世界最強の戦士 OP-17】" in out[0]["name"]
    assert all(f["rule"] != "F3" for f in out[0]["fixes"])


def test_f3_drops_bracket_heading_when_an_own_name_line_exists():
    # Arrange
    raw = "【シングルカード】\nマスターボールミラー151のみ\n300枚@1,600円"
    # Act
    out, _ = _extract102(raw, _it([1, 2, 3], "1,600円", "300"))
    # Assert
    assert "【シングルカード】" not in out[0]["name"]
    assert "マスターボールミラー151のみ" in out[0]["name"]


def test_f5_changes_only_name_and_roles_not_quantity_unit_state_ship_status_or_price():
    # Arrange（b1490145 の形：最後の price_line の後ろに「販売数量/300セット」。Gemini の quantity はその行）
    raw = "商品A 通常版\n（12月入荷予定）\n10セット/¥55,000\n販売数量/300セット"
    items = (_it([1, 2, 3, 4], "¥55,000", "販売数量/300セット"),)
    # Act
    out102, flags = _extract102(raw, *items)
    out101, _ = _extract(raw, *items)
    # Assert
    keys = ("quantity_normalized", "unit", "ship", "condition", "status", "price_normalized", "price_reasons")
    assert {k: out102[0][k] for k in keys} == {k: out101[0][k] for k in keys}
    assert out102[0]["quantity_normalized"] == 10
    assert flags["possible_footer_line"] == [4]
    assert "販売数量" in out101[0]["name"] and "販売数量" not in out102[0]["name"]


# ---------------------------------------------------------------------------
# 黙って消える件と印を要確認に回す（設計: docs/handoff/v102-no-silent-drop/design.md §3・§4）
# ---------------------------------------------------------------------------


def _parse_keep(raw, *items):
    return v101.parse_v101_response(_resp(*items), raw, status_entries=_STATUS, keep_rejected=True)


def _extract_keep(raw, *items, product_first=None, unit_alias_to_info=None, reassign=True, gemini_trust=False):
    parsed, errors = _parse_keep(raw, *items)
    masters = {**_MASTERS, "unit_alias_to_info": unit_alias_to_info or _UNITS}
    out, flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=reassign, v102_fixes=True, product_first=product_first,
        review_reasons=True, gemini_trust=gemini_trust, **masters,
    )
    return out, flags, errors


def _kinds(row):
    return [r["kind"] for r in row["review"]]


_DROP_RAW = "商品A\n3BOX@1,000円\n商品B\n2BOX@2,000円"


def _drop_items():
    return (
        _it([1, 2], "1,000円", "3"),          # 通常
        _it([3, 4], "9,999円", "2"),          # D2: 価格の文字が行に無い
        _it([1, 2], "1,000円", "3"),          # D3: 価格の行が1件目と同じ
        _it([], "1,000円", "3"),              # D1: lines が空
    )


def test_keep_rejected_keeps_d1_d2_d3_items_after_the_normal_ones_with_their_fields():
    # Arrange / Act
    items, errors = _parse_keep(_DROP_RAW, *_drop_items())
    # Assert
    assert [i.get("rejected") for i in items] == [None, "price_not_in_lines", "duplicate_price_line", "item_shape_invalid"]
    assert len(items) == 4 and len(errors) == 3
    d2, d3, d1 = items[1:]
    assert d2 == {"rejected": "price_not_in_lines", "gemini_index": 1, "lines": [3, 4], "price": "9,999円",
                  "quantity": "2", "price_line": None, "error": "価格の行が見つからない"}
    assert d3["gemini_index"] == 2 and d3["price_line"] == 2 and d3["lines"] == [1, 2]
    assert d1["gemini_index"] == 3 and d1["lines"] == [] and d1["price_line"] is None and "lines が空" in d1["error"]


def test_keep_rejected_lines_hold_only_in_range_integers_ascending_without_duplicates():
    items, _ = _parse_keep(_DROP_RAW, {"lines": [4, 2, 2, 99, "x"], "price": "1,000円", "quantity": "1"}, "not-a-dict")
    assert items[0]["lines"] == [2, 4] and items[0]["rejected"] == "item_shape_invalid"
    assert items[1] == {"rejected": "item_shape_invalid", "gemini_index": 1, "lines": [], "price": None,
                        "quantity": None, "price_line": None, "error": "件がオブジェクトではない"}


def test_keep_rejected_false_output_is_unchanged():
    # Arrange / Act
    default = _parse(_DROP_RAW, *_drop_items())
    explicit = v101.parse_v101_response(_resp(*_drop_items()), _DROP_RAW, status_entries=_STATUS, keep_rejected=False)
    # Assert
    assert default == explicit
    assert len(default[0]) == 1 and "rejected" not in default[0][0] and len(default[1]) == 3


def test_result_count_equals_gemini_count_and_each_rejected_item_has_a_review_kind():
    # Act
    out, flags, errors = _extract_keep(_DROP_RAW, *_drop_items())
    # Assert
    assert len(out) == 4 and len(errors) == 3
    normal, d2, d3, d1 = out
    assert "rejected" not in normal
    assert _kinds(d2) == ["price_not_in_lines"] and d2["review"][0]["field"] == "price" and d2["review"][0]["copied"] == "9,999円"
    assert _kinds(d3) == ["duplicate_price_line"] and d3["review"][0]["line"] == 2
    assert _kinds(d1) == ["item_shape_invalid"] and "lines が空" in d1["review"][0]["error"]
    assert d1["review"][0]["line"] is None and d2["review"][0]["line"] == 3
    assert (d2["rejected"], d2["gemini_index"], d2["raw_price"], d2["raw_quantity"], d2["lines"]) == (
        "price_not_in_lines", 1, "9,999円", "2", [3, 4])


def test_rejected_result_has_every_key_of_a_normal_item_and_does_not_join_the_normal_processing():
    # Act
    out, flags, _ = _extract_keep(_DROP_RAW, *_drop_items())
    # Assert
    assert all(set(out[0]) <= set(r) for r in out[1:])
    assert out[1]["name"] == "none" and out[1]["unit"] == "none" and out[1]["price_normalized"] is None
    assert out[1]["roles"] == {} and out[1]["review"] and out[1]["fixes"] == []
    plain, _ = _extract102(_DROP_RAW, _it([1, 2], "1,000円", "3"))
    # 便G：keep_rejected の経路は受理した件にも gemini_index を持たせる（件の対応付け用）。それ以外の欄は同じ
    assert {k: v for k, v in out[0].items() if k not in ("review", "gemini_index")} == {
        k: v for k, v in plain[0].items() if k != "review"}


def test_rejected_items_do_not_change_the_values_of_the_normal_items():
    # Arrange
    raw = "商品A\n3BOX@1,000円\n商品B\n2BOX@2,000円"
    only_normal, _ = _extract102(raw, _it([1, 2], "1,000円", "3"), _it([3, 4], "2,000円", "2"))
    # Act
    mixed, _, _ = _extract_keep(raw, _it([1, 2], "1,000円", "3"), _it([3, 4], "9,999円", "2"), _it([3, 4], "2,000円", "2"))
    # Assert
    strip = lambda rows: [{k: v for k, v in r.items() if k not in ("review", "gemini_index")} for r in rows]  # noqa: E731  便G：gemini_index は対応付け用
    assert strip([mixed[0], mixed[1]]) == strip(only_normal)


def test_half_width_slash_joined_prices_find_the_price_line_for_v102_only():
    # Arrange
    raw = "商品A\n3BOX@1,000円"
    item = _it([1, 2], "1,000円/2,000円", "3")
    # Act
    kept, kept_errors = _parse_keep(raw, item)
    old, old_errors = _parse(raw, item)
    full_width, full_errors = _parse(raw, _it([1, 2], "1,000円／2,000円", "3"))
    # Assert
    assert kept[0]["price_line"] == 2 and "rejected" not in kept[0] and kept_errors == []
    assert old == [] and len(old_errors) == 1  # v10.1 以前は今までどおり
    assert full_width[0]["price_line"] == 2 and full_errors == []


def test_unreadable_json_returns_the_whole_error_and_no_items_even_when_keeping():
    items, errors = v101.parse_v101_response("not json", "商品A", status_entries=_STATUS, keep_rejected=True)
    assert items == [] and len(errors) == 1


def test_quantity_no_number_mark_adds_a_kind_to_the_item_that_holds_the_line():
    # Arrange
    raw = "ワンピース ブースター\nカートン @150,000円"
    # Act
    out, flags, _ = _extract_keep(raw, _it([1, 2], "150,000円", "カートン"))
    # Assert
    assert flags["quantity_no_number"] == [2]
    assert {"line": 2, "kind": "quantity_no_number"} in out[0]["review"]


def test_footer_mark_adds_a_kind_to_the_item_and_post_review_has_no_orphan_footer():
    # Arrange
    raw = "商品A\n3BOX@1,000円\n・買取品"
    # Act
    out, flags, _ = _extract_keep(raw, _it([1, 2, 3], "1,000円", "3"))
    # Assert
    assert flags["possible_footer_line"] == [3]
    assert {"line": 3, "kind": "possible_footer_line"} in out[0]["review"]
    assert flags["post_review"] == []


def test_orphan_footer_line_and_missing_item_lines_go_to_post_review():
    # Act
    reasons = v101._post_review_reasons(
        item_count=2, flags={"possible_missing_item": [5], "quantity_no_number": [], "possible_footer_line": [7, 9]},
        owned_lines={7},
    )
    # Assert
    assert reasons == [
        {"kind": "possible_missing_item", "line": 5},
        {"kind": "possible_footer_line", "line": 9},
    ]


def test_possible_missing_item_line_goes_to_post_review():
    raw = "商品A\n3BOX@1,000円\n@500円\n商品B\n2BOX@2,000円"
    out, flags, _ = _extract_keep(raw, _it([1, 2], "1,000円", "3"), _it([4, 5], "2,000円", "2"))
    assert flags["possible_missing_item"] == [3]
    assert {"kind": "possible_missing_item", "line": 3} in flags["post_review"]


def test_no_gemini_items_gives_no_items_in_post_review_and_keeps_the_three_marks():
    out, flags, errors = _extract_keep("商品A")
    assert out == [] and errors == []
    assert flags["post_review"] == [{"kind": "no_items"}]
    assert flags["possible_missing_item"] == [] and flags["quantity_no_number"] == [] and flags["possible_footer_line"] == []


def test_all_items_rejected_is_not_no_items():
    out, flags, _ = _extract_keep("商品A", _it([], "1,000円", "3"))
    assert len(out) == 1 and out[0]["rejected"] == "item_shape_invalid"
    assert flags["post_review"] == []


def test_unit_none_item_gets_unit_unknown_and_unit_known_item_does_not():
    # Act
    out, _, _ = _extract_keep("商品A\n@1,000円\n商品B\n3BOX@2,000円", _it([1, 2], "1,000円", "3"), _it([3, 4], "2,000円", "3"))
    # Assert
    assert out[0]["unit"] == "none" and {"line": 2, "kind": "unit_unknown"} in out[0]["review"]
    assert out[1]["unit"] != "none" and "unit_unknown" not in _kinds(out[1])


def test_matched_product_without_category_gets_category_unknown():
    from app.services.extraction_judgement_svc import ProductEntry
    from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters

    # Arrange
    entry = ProductEntry(id=1, product_code=None, mark=None, work_id=1, search_keywords=("サンプル拡張",), exclude_keywords=())
    no_kubun = ProductFirstMasters(product_entries=(entry,), product_kubun={}, condition_unit={}, ignore_phrases=())
    with_kubun = ProductFirstMasters(product_entries=(entry,), product_kubun={"1": "箱系"}, condition_unit={}, ignore_phrases=())
    # Act
    unknown, _, _ = _extract_keep("サンプル拡張\n3@1,500円", _it([1, 2], "1,500円", "3"), product_first=no_kubun)
    known, _, _ = _extract_keep("サンプル拡張\n3@1,500円", _it([1, 2], "1,500円", "3"), product_first=with_kubun)
    # Assert
    assert unknown[0]["match_status"] == "matched" and unknown[0]["product_category"] == "不明"
    assert {"line": 2, "kind": "category_unknown"} in unknown[0]["review"]
    assert "category_unknown" not in _kinds(known[0])


def test_without_review_reasons_the_v102_output_has_no_new_keys():
    raw = "商品A\n3BOX@1,000円\n・買取品"
    out, flags = _extract102(raw, _it([1, 2, 3], "1,000円", "3"))
    assert set(flags) == {"possible_missing_item", "quantity_no_number", "possible_footer_line"}
    assert out[0]["review"] == []


def _qty_not_in_text_reasons(row):
    return [r for r in row["review"] if r["kind"] == "quantity_not_in_text"]


def test_quantity_not_in_text_adds_a_kind_with_field_and_copied():
    # Arrange
    raw = "商品A\n3BOX@1,000円"
    # Act
    out, _flags, _ = _extract_keep(raw, _it([1, 2], "1,000円", "30"))
    # Assert
    assert out[0]["quantity_not_in_text"] is True
    assert _qty_not_in_text_reasons(out[0]) == [{"kind": "quantity_not_in_text", "field": "quantity", "copied": "30"}]


def test_quantity_found_in_the_item_lines_has_no_quantity_not_in_text_kind():
    out, _flags, _ = _extract_keep("商品A\n3BOX@1,000円", _it([1, 2], "1,000円", "3"))
    assert out[0]["quantity_not_in_text"] is False and _qty_not_in_text_reasons(out[0]) == []


def test_quantity_none_has_no_quantity_not_in_text_kind():
    out, _flags, _ = _extract_keep("商品A\n3BOX@1,000円", _it([1, 2], "1,000円", "none"))
    assert _qty_not_in_text_reasons(out[0]) == []


def test_quantity_without_digits_has_only_quantity_no_number():
    out, _flags, _ = _extract_keep("ワンピース ブースター\nカートン @150,000円", _it([1, 2], "150,000円", "カートン"))
    assert "quantity_no_number" in _kinds(out[0]) and _qty_not_in_text_reasons(out[0]) == []


# ---------------------------------------------------------------------------
# 便PQ：v102 の価格・数量を Gemini の写しの数字で補う／補えないときは要確認
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("copied", "expected"),
    [
        ("42個", 42.0), ("在庫数：17", 17.0), ("￥8,500", 8500.0), ("１２BOX", 12.0), ("5/セット", 5.0),
        ("2万", None), ("3千円", None), ("1.5", None), ("10～20/セット", None), ("none", None), (None, None),
        ("カートン", None), ("1k", None),
    ],
)
def test_single_number(copied, expected):
    assert v101._single_number(copied) == expected


def _pq_row(raw, price, quantity, *, v102=True):
    items = (_it(list(range(1, len(raw.split("\n")) + 1)), price, quantity),)
    if v102:
        out, _flags, _ = _extract_keep(raw, *items)
        return out[0]
    parsed, errors = _parse(raw, *items)
    assert errors == []
    return v101.extract_v101_items(parsed, raw, order=None, reassign=True, **_MASTERS)[0][0]


def test_pq_bullet_stock_line_is_filled_from_the_copy():
    # Arrange
    raw = "■商品名：サンプルA\n■単価（税込）：￥8,500\n■在庫数：17"
    # Act
    row = _pq_row(raw, "￥8,500", "17")
    # Assert
    assert row["quantity_normalized"] == 17 and row["price_normalized"] == 8500
    assert "quantity_unresolved" not in _kinds(row) and "price_unresolved" not in _kinds(row)


def test_pq_two_counted_numbers_on_one_line_is_filled_from_the_copy():
    raw = "サンプルB\n数量：42個（注文6個単位）\n単価：6,000"
    row = _pq_row(raw, "6,000", "42個")
    assert row["quantity_normalized"] == 42 and row["price_normalized"] == 6000
    assert "quantity_unresolved" not in _kinds(row)


def test_pq_copy_number_not_in_the_text_is_not_adopted():
    raw = "サンプルC\n3BOX@1,000円"
    row = _pq_row(raw, "1,000円", "30")
    assert row["quantity_normalized"] == 3 and row["quantity_not_in_text"] is True
    assert "quantity_not_in_text" in _kinds(row) and "quantity_unresolved" not in _kinds(row)


def test_pq_unfillable_quantity_gets_quantity_unresolved():
    raw = "サンプルD\n数量：10枚 20枚\n単価：6,000"
    row = _pq_row(raw, "6,000", "10～20")
    assert row["quantity_normalized"] is None
    assert {"kind": "quantity_unresolved", "field": "quantity"} in row["review"]


def test_pq_unfillable_price_gets_price_unresolved():
    raw = "サンプルE\n2BOX\n価格：1000円 2000円"
    row = _pq_row(raw, "1000円／2000円", "2")
    assert row["price_normalized"] is None
    assert {"kind": "price_unresolved", "field": "price"} in row["review"]


def test_pq_fillable_price_is_filled_from_the_copy():
    raw = "■商品名：サンプルF\n■単価：￥8,500\n■在庫数：3個"
    row = _pq_row(raw, "￥8,500", "3個")
    assert row["price_normalized"] == 8500 and "price_unresolved" not in _kinds(row)


def test_pq_quantity_none_or_no_digit_gets_no_unresolved_kind():
    row = _pq_row("サンプルG\nカートン @150,000円", "150,000円", "カートン")
    assert "quantity_unresolved" not in _kinds(row)
    row = _pq_row("サンプルG\nカートン @150,000円", "150,000円", "none")
    assert "quantity_unresolved" not in _kinds(row)


@pytest.mark.parametrize(
    ("raw", "price", "quantity"),
    [
        ("■商品名：サンプルA\n■単価（税込）：￥8,500\n■在庫数：17", "￥8,500", "17"),
        ("サンプルB\n数量：42個（注文6個単位）\n単価：6,000", "6,000", "42個"),
        ("サンプルD\n数量：10枚 20枚\n単価：6,000", "6,000", "10～20"),
    ],
)
def test_pq_v101_path_is_unchanged(raw, price, quantity):
    # v102=False の結果は、補い・安全網の影響を受けない（price_normalized・quantity_normalized は原文からの取り出しだけ）
    from app.services.extraction_judgement_svc import resolve_price_quantity

    row = _pq_row(raw, price, quantity, v102=False)
    pq = resolve_price_quantity(
        raw, gemini_price=price, gemini_quantity=quantity, unit_aliases=set(_UNITS), order=None, gemini_product_name=row["name"],
    )
    assert (row["price_normalized"], row["quantity_normalized"]) == (pq.price, pq.quantity)
    assert "quantity_unresolved" not in str(row["review"])


# ---------------------------------------------------------------------------
# 便G：Gemini の抽出を採用し、システムは確認役（設計 docs/handoff/v102-prod-switch/design.md §16）
# 文はすべて合成。
# ---------------------------------------------------------------------------

_MIXED_EVIDENCE_RAW = "\n".join([
    "■A", "10/3発送", "300BOX@1,500", "", "■B", "200BOX@1,400", "10/9発送", "",
    "■C", "100BOX@900", "ダメージ有り", "50BOX@800",
])
_MIXED_EVIDENCE_ITEMS = (_it([9, 10, 11], "900"), _it([9, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"))


def _kinds_of(row):
    return [r["kind"] for r in row["review"]]


def test_a6_v102_keeps_the_gemini_assignment_of_an_ambiguous_line_but_v101_style_reassign_moves_it():
    # Arrange・Act：Gemini は状態の行 11 を 900 の件に付けた。付け直しの決まり（安い件へ）は 800 の件に動かす
    kept, _, _ = _extract_keep(_MIXED_EVIDENCE_RAW, *_MIXED_EVIDENCE_ITEMS, reassign=False, gemini_trust=True)
    moved, _, _ = _extract_keep(_MIXED_EVIDENCE_RAW, *_MIXED_EVIDENCE_ITEMS, reassign=True)
    # Assert
    assert kept[0]["condition"] == "Damaged sealed box" and kept[1]["condition"] != "Damaged sealed box"
    assert moved[1]["condition"] == "Damaged sealed box" and moved[0]["condition"] != "Damaged sealed box"
    assert 11 in kept[0]["lines"] and kept[0]["reassigned"] == [] and "ship" not in [r.get("kind") for r in kept[0]["review"]]


def test_a6_v101_without_v102_fixes_still_reassigns():
    out, _ = _extract(_MIXED_EVIDENCE_RAW, *_MIXED_EVIDENCE_ITEMS)  # v10.1 の経路（回帰）
    assert out[1]["condition"] == "Damaged sealed box" and out[0]["condition"] != "Damaged sealed box"


def test_a6_both_items_get_the_condition_when_gemini_put_the_line_in_both():
    items = (_it([9, 10, 11], "900"), _it([9, 11, 12], "800"), _it([1, 2, 3], "1,500"), _it([5, 6, 7], "1,400"))
    out, _, _ = _extract_keep(_MIXED_EVIDENCE_RAW, *items, reassign=False, gemini_trust=True)
    assert out[0]["condition"] == out[1]["condition"] == "Damaged sealed box"


def test_a7_v102_keeps_the_shared_ship_heading_in_lines_but_f1_still_removes_it_without_trust():
    raw, items = _parent_children_post()
    trusted, _, _ = _extract_keep(raw, *items, reassign=False, gemini_trust=True)
    removed, _, _ = _extract_keep(raw, *items)
    assert all(1 in one["lines"] for one in trusted) and all(one["fixes"] == [] for one in trusted)
    assert all(1 not in one["lines"] for one in removed) and [f["rule"] for f in removed[0]["fixes"]] == ["F1"]


def _stub_reread(monkeypatch, price, quantity):
    monkeypatch.setattr(
        v101, "resolve_price_quantity", lambda *a, **k: PriceQtyResult(price, quantity, "marker", (), 2, 2)
    )


def _trust_one(raw, price, quantity):
    out, _, _ = _extract_keep(raw, _it([1, 2], price, quantity), reassign=False, gemini_trust=True)
    return out[0]


def test_a11_gemini_numbers_are_adopted_and_no_reason_when_the_source_agrees():
    row = _trust_one("商品A\n3BOX@17,800円", "17,800円", "3")
    assert (row["price_normalized"], row["quantity_normalized"]) == (17800.0, 3.0)
    assert not {"price_source_mismatch", "quantity_source_mismatch"} & set(_kinds_of(row))


def test_a11_source_reread_that_differs_only_adds_reasons_and_never_changes_the_value(monkeypatch):
    _stub_reread(monkeypatch, 16000.0, 5.0)
    row = _trust_one("商品A\n3BOX@17,800円", "17,800円", "3")
    assert (row["price_normalized"], row["quantity_normalized"]) == (17800.0, 3.0)
    assert {"price_source_mismatch", "quantity_source_mismatch"} <= set(_kinds_of(row))


def test_a11_price_only_mismatch_and_quantity_only_mismatch_are_separate(monkeypatch):
    _stub_reread(monkeypatch, 16000.0, 3.0)
    kinds = _kinds_of(_trust_one("商品A\n3BOX@17,800円", "17,800円", "3"))
    assert "price_source_mismatch" in kinds and "quantity_source_mismatch" not in kinds
    _stub_reread(monkeypatch, 17800.0, 5.0)
    kinds = _kinds_of(_trust_one("商品A\n3BOX@17,800円", "17,800円", "3"))
    assert "quantity_source_mismatch" in kinds and "price_source_mismatch" not in kinds


def test_a11_no_reason_when_the_source_reread_is_none(monkeypatch):
    _stub_reread(monkeypatch, None, None)
    row = _trust_one("商品A\n3BOX@17,800円", "17,800円", "3")
    assert (row["price_normalized"], row["quantity_normalized"]) == (17800.0, 3.0)
    assert not {"price_source_mismatch", "quantity_source_mismatch"} & set(_kinds_of(row))


def test_a11_scale_word_in_the_copy_is_none_with_the_unresolved_reason():
    row = _trust_one("商品A\n1BOX@2万円", "2万円", "1")
    assert row["price_normalized"] is None and "price_unresolved" in _kinds_of(row)
    row = _trust_one("商品A\n2万BOX@1,000円", "1,000円", "2万")
    assert row["quantity_normalized"] is None and "quantity_unresolved" in _kinds_of(row)


def test_a11_two_numbers_in_the_copy_is_none_and_quantity_not_in_text_is_kept():
    row = _trust_one("商品A\n3BOX@1,000円", "1,000円", "3個+2個")
    assert row["quantity_normalized"] is None and "quantity_unresolved" in _kinds_of(row)
    row = _trust_one("商品A\n3BOX@1,000円", "1,000円", "7")
    assert row["quantity_normalized"] == 7.0 and "quantity_not_in_text" in _kinds_of(row)


def test_a11_without_trust_the_values_still_come_from_the_source_reread(monkeypatch):
    _stub_reread(monkeypatch, 16000.0, 5.0)
    out, _, _ = _extract_keep("商品A\n3BOX@17,800円", _it([1, 2], "17,800円", "3"))
    assert (out[0]["price_normalized"], out[0]["quantity_normalized"]) == (16000.0, 5.0)
    assert "price_source_mismatch" not in _kinds_of(out[0]) and "price_source_mismatch" not in out[0]


def test_a16_parse_gives_every_accepted_item_its_response_position_only_when_keep_rejected():
    raw = "商品A\n3BOX@1,000円\n商品B\n2BOX@2,000円"
    items = [_it([1, 2], "1,000円", "3"), _it([9], "9円", "1"), _it([3, 4], "2,000円", "2")]
    kept, _ = v101.parse_v101_response(_resp(*items), raw, status_entries=_STATUS, keep_rejected=True)
    plain, _ = v101.parse_v101_response(_resp(*items), raw, status_entries=_STATUS)
    assert [(it.get("rejected"), it["gemini_index"]) for it in kept] == [(None, 0), (None, 2), ("item_shape_invalid", 1)]
    assert all("gemini_index" not in it for it in plain)


def test_a16_gemini_index_survives_the_extraction_for_accepted_and_rejected_items():
    raw = "商品A\n3BOX@1,000円\n商品B\n2BOX@2,000円"
    out, _, _ = _extract_keep(
        raw, _it([1, 2], "1,000円", "3"), _it([9], "9円", "1"), _it([3, 4], "2,000円", "2"), reassign=False, gemini_trust=True
    )
    assert sorted(row["gemini_index"] for row in out) == [0, 1, 2]
    assert [row["gemini_index"] for row in out if not row.get("rejected")] == [0, 2]


@pytest.mark.parametrize("copied,expected", [
    ("100Pack", 100.0), ("500Packs", 500.0), ("2k", None), ("2K円", None), ("2 k", None),
    ("1.5万", None), ("Pack", None), ("3kg", 3.0),
])
def test_single_number_treats_k_as_a_scale_word_only_right_after_a_digit_without_a_letter_after(copied, expected):
    # 便G：Pack の k を千・k とみなして None にしていた不具合の修正
    assert v101._single_number(copied) == expected
