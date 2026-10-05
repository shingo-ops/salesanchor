"""Gemini 書き写し v10.1（受け取り・行の役割・付け直し・原文からの取り出し）の単体試験。Gemini・DB は使わない。

設計: docs/handoff/gemini-v101/design.md §3-3〜§3-5・§5-4
"""
from __future__ import annotations

import json

import pytest

from app.services import gemini_raw_copy_v101 as v101

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
