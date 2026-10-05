"""Gemini 書き写し v10（受け取り・原文からの取り出し）の単体試験。Gemini・DB は使わない。

設計: docs/handoff/gemini-v10/design.md §3-2・§3-3・§5-2
"""
from __future__ import annotations

import json

import pytest

from app.services import gemini_raw_copy_v10 as v10

_UNITS = {
    "BOX": ("BOX", "箱系"), "box": ("BOX", "箱系"), "ボックス": ("BOX", "箱系"),
    "カートン": ("カートン", "箱系大"), "パック": ("パック", "パック系"),
}
_COND = [
    {"cond_id": "c-nsb", "code": "CN0005", "canonical": "No shrink box", "priority": 3, "app_kubun": "箱系",
     "search_kw": "シュリ無し,シュリなし", "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT"},
]
_STATUS = [
    {"canonical": "sold_out", "search_pattern": "完売", "exclude_pattern": "", "priority": 1,
     "match_type": "LITERAL", "effect": "EXCLUDE"},
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99,
     "match_type": "DEFAULT", "effect": "OUTPUT"},
]


def _it(price_line, item_lines=None, *, price="1,000円", quantity="3", heading=(), shared=(), names=()):
    return {
        "price": price, "quantity": quantity, "price_line": price_line,
        "item_lines": list(item_lines if item_lines is not None else [price_line]),
        "heading_lines": list(heading), "shared_lines": list(shared), "name_lines": list(names),
    }


def _resp(*items):
    return json.dumps({"items": list(items)}, ensure_ascii=False)


def _parse(items, n_lines=10):
    raw = "\n".join(f"line{i}" for i in range(1, n_lines + 1))
    return v10.parse_v10_response(_resp(*items), raw)


def _extract(raw_text, items, order=None):
    parsed, errors = v10.parse_v10_response(_resp(*items), raw_text)
    assert errors == []
    return v10.extract_v10_items(
        parsed, raw_text, cond_entries=_COND, cond_canonical_to_uuid={}, unit_alias_to_info=_UNITS,
        status_entries=_STATUS, order=order,
    )


# ---------------------------------------------------------------------------
# 受け取り（設計 §3-2）
# ---------------------------------------------------------------------------


def test_accepts_valid_items_and_sorts_deduplicates_arrays():
    # Arrange
    item = _it(3, [4, 3, 3], heading=[2, 2], names=[2])
    # Act
    items, errors = _parse([item])
    # Assert
    assert errors == []
    assert items[0]["item_lines"] == [3, 4]
    assert items[0]["heading_lines"] == [2]
    assert set(items[0]) == {"price", "quantity", "price_line", "item_lines", "heading_lines", "shared_lines", "name_lines"}


@pytest.mark.parametrize("text", ["not json", "[]", '{"items": 1}'])
def test_unreadable_json_or_non_array_items_is_one_whole_error(text):
    items, errors = v10.parse_v10_response(text, "a\nb")
    assert items == []
    assert len(errors) == 1 and errors[0]["index"] is None


def test_missing_field_and_wrong_type_drop_the_item():
    good = _it(3)
    missing = {k: v for k, v in _it(5).items() if k != "shared_lines"}
    wrong_type = {**_it(7), "item_lines": "7"}
    bool_line = {**_it(9), "heading_lines": [True]}
    items, errors = _parse([good, missing, wrong_type, bool_line])
    assert len(items) == 1
    assert [e["index"] for e in errors] == [1, 2, 3]
    assert "shared_lines" in errors[0]["error"]


@pytest.mark.parametrize("field", ["item_lines", "heading_lines", "shared_lines", "name_lines"])
def test_line_number_out_of_range_drops_the_item(field):
    item = _it(3, [3])
    item[field] = [11] if field != "item_lines" else [3, 0]
    items, errors = _parse([item], n_lines=10)
    assert items == []
    assert "範囲外" in errors[0]["error"]


def test_price_line_out_of_range_drops_the_item():
    items, errors = _parse([_it(11, [11])], n_lines=10)
    assert items == [] and "範囲外" in errors[0]["error"]


def test_empty_item_lines_drops_the_item():
    items, errors = _parse([_it(3, [])])
    assert items == [] and "item_lines が空" in errors[0]["error"]


def test_price_line_not_in_item_lines_drops_the_item():
    items, errors = _parse([_it(3, [4])])
    assert items == [] and "item_lines に無い" in errors[0]["error"]


def test_overlapping_item_lines_keeps_first_and_drops_later():
    first, second = _it(3, [3, 4]), _it(5, [4, 5])
    items, errors = _parse([first, second])
    assert [i["price_line"] for i in items] == [3]
    assert errors[0]["index"] == 1 and "重なる" in errors[0]["error"]


def test_heading_and_shared_lines_may_be_shared_by_several_items():
    a = _it(4, heading=[2], shared=[3], names=[2])
    b = _it(6, heading=[2], shared=[3], names=[2])
    items, errors = _parse([a, b])
    assert errors == [] and len(items) == 2


def test_heading_overlapping_another_items_item_lines_drops_the_item():
    a = _it(4, [4])
    b = _it(6, [6], heading=[4])
    items, errors = _parse([a, b])
    assert [i["price_line"] for i in items] == [4]
    assert errors[0]["index"] == 1


def test_shared_overlapping_another_items_item_lines_drops_the_item():
    a = _it(4, [4], shared=[6])
    b = _it(6, [6])
    items, errors = _parse([a, b])
    assert [i["price_line"] for i in items] == [6]
    assert errors[0]["index"] == 0


def test_name_lines_may_point_to_previous_items_lines_carry_over():
    prev = _it(2, [2], names=[2])
    carry = _it(4, [4], names=[2, 4])
    items, errors = _parse([prev, carry])
    assert errors == []
    assert items[1]["name_lines"] == [2, 4]


def test_name_lines_to_other_lines_are_removed_and_item_is_kept():
    item = _it(4, [4], heading=[3], names=[3, 4, 9])
    items, errors = _parse([item])
    assert items[0]["name_lines"] == [3, 4]
    assert errors[0]["kept"] is True and errors[0]["index"] == 0 and "9" in errors[0]["error"]


def test_response_schema_has_required_fields_and_integer_arrays():
    item = v10.V10_RESPONSE_SCHEMA["properties"]["items"]["items"]
    assert set(item["required"]) == set(item["properties"])
    assert item["properties"]["item_lines"] == {"type": "array", "items": {"type": "integer"}}
    assert item["properties"]["price_line"] == {"type": "integer"}


# ---------------------------------------------------------------------------
# 原文から取る（設計 §3-3）
# ---------------------------------------------------------------------------


def test_name_from_heading_unit_after_digit_and_condition_none_when_not_written():
    raw = "■OP-07 500年後の未来\n12BOX@20,100円[通常品]"
    (r,) = _extract(raw, [_it(2, price="20,100円", quantity="12", heading=[1], names=[1])])
    assert r["name"] == "■OP-07 500年後の未来"
    assert r["unit"] == "BOX" and r["unit_kubun"] == "箱系"
    assert r["raw_price"] == "20,100円" and r["raw_quantity"] == "12"
    assert r["price_normalized"] == 20100 and r["quantity_normalized"] == 12


def test_name_in_price_line_keeps_digits_inside_the_name():
    raw = "OP-14 21,000円/3box"
    (r,) = _extract(raw, [_it(1, price="21,000円", quantity="3", names=[1])])
    assert r["name"] == "OP-14"
    assert r["unit"] == "BOX"


def test_name_keeps_151_when_quantity_is_elsewhere():
    raw = "ポケモンカード151 BOX @8,000円 ×20"
    (r,) = _extract(raw, [_it(1, price="8,000円", quantity="20", names=[1])])
    assert "151" in r["name"]
    assert r["name"].startswith("ポケモンカード151")


def test_vol2_style_name_continuation_in_price_line():
    raw = "●プレミアムバンダイ限定コレクション\nVol.2@3,500×40\nVol.1@3,000×50"
    items = [
        _it(2, price="3,500", quantity="40", heading=[1], names=[1, 2]),
        _it(3, price="3,000", quantity="50", heading=[1], names=[1, 3]),
    ]
    r = _extract(raw, items)
    assert r[0]["name"] == "●プレミアムバンダイ限定コレクション Vol.2"
    assert r[1]["name"] == "●プレミアムバンダイ限定コレクション Vol.1"


def test_name_carries_over_from_previous_items_price_line_op14_carton():
    raw = "OP-11 21,000円/3box\nカートン 250,000円/2カートン"
    items = [
        _it(1, price="21,000円", quantity="3", names=[1]),
        _it(2, price="250,000円", quantity="2", names=[1, 2]),
    ]
    r = _extract(raw, items)
    assert r[0]["name"] == "OP-11"
    assert r[1]["name"] == "OP-11 カートン"
    assert r[1]["unit"] == "カートン" and r[1]["unit_kubun"] == "箱系大"


def test_stock_words_and_symbols_are_removed_from_price_line_name():
    raw = "スペシャルBOX @¥13,000 在庫数5カートン"
    (r,) = _extract(raw, [_it(1, price="¥13,000", quantity="在庫数5", names=[1])])
    assert r["name"] == "スペシャルBOX"


def test_unit_directly_before_price_is_found():
    raw = "ストームエメラルダ\n　ボックス/¥13,000\n　残り200"
    (r,) = _extract(raw, [_it(2, [2, 3], price="¥13,000", quantity="残り200", heading=[1], names=[1])])
    assert r["unit"] == "BOX"


def test_unit_inside_a_word_not_next_to_digit_or_price_is_ignored():
    raw = "ボックス限定セット @500円"
    (r,) = _extract(raw, [_it(1, price="500円", quantity="none", names=[1])])
    assert r["unit"] == "none" and r["unit_kubun"] == ""


def test_shared_ship_line_applies_to_all_items_under_the_heading():
    raw = "\n".join(["●デュエル・マスターズ DM26-RP4", "【9/28発送】", "@80,000円/在庫数5カートン", "@3,000円/在庫数200BOX"])
    a = _it(3, price="80,000円", quantity="在庫数5", heading=[1], shared=[2], names=[1])
    b = _it(4, price="3,000円", quantity="在庫数200", heading=[1], shared=[2], names=[1])
    r = _extract(raw, [a, b])
    assert r[0]["ship"] == "【9/28発送】" and r[1]["ship"] == "【9/28発送】"
    assert r[0]["name"] == r[1]["name"] == "●デュエル・マスターズ DM26-RP4"


def test_ship_line_just_above_heading_in_item_lines():
    raw = "(12/7発送)\n▼デジモン ブースター BT-25\n@6,500円 ×300BOX"
    (r,) = _extract(raw, [_it(3, [1, 3], price="6,500円", quantity="300", heading=[2], names=[2])])
    assert r["ship"] == "(12/7発送)"  # 括弧の外に文字が無い行は、行の全体を取る
    assert r["name"] == "▼デジモン ブースター BT-25"


def test_ship_line_below_price_line_belongs_to_that_item():
    raw = "MEGAドリーム\n50box 11000円\n20日発送\n30box 10500円\n21日発送"
    a = _it(2, [2, 3], price="11000円", quantity="50", heading=[1], names=[1])
    b = _it(4, [4, 5], price="10500円", quantity="30", heading=[1], names=[1])
    r = _extract(raw, [a, b])
    assert r[0]["ship"] == "20日発送" and r[1]["ship"] == "21日発送"


def test_ship_in_brackets_with_outside_text_takes_the_bracket_content():
    raw = "商品A 【10/12発送】\n3BOX@1,000円"
    (r,) = _extract(raw, [_it(2, [2], price="1,000円", quantity="3", heading=[1], names=[1])])
    assert r["ship"] == "10/12発送"


def test_ship_in_price_line_takes_text_after_price():
    raw = "300BOX@1,500 10/3発送"
    (r,) = _extract(raw, [_it(1, price="1,500", quantity="300", names=[1])])
    assert r["ship"] == "10/3発送"


def test_ship_is_none_when_no_line_has_a_ship_word():
    (r,) = _extract("商品A\n3BOX@1,000円", [_it(2, price="1,000円", quantity="3", heading=[1], names=[1])])
    assert r["ship"] == "none"


def test_condition_from_item_line_without_shrink():
    raw = "ストームエメラルダ\n　ボックス/¥12,000\n　シュリ無し\n　残り170"
    (r,) = _extract(raw, [_it(2, [2, 3, 4], price="¥12,000", quantity="残り170", heading=[1], names=[1])])
    assert r["condition"] == "No shrink box"
    assert r["condition_basis"].startswith("R3")


def test_condition_falls_back_to_unit_default_when_not_written():
    (r,) = _extract("商品A\n3BOX@1,000円", [_it(2, price="1,000円", quantity="3", heading=[1], names=[1])])
    assert r["condition"] == "Sealed box"
    assert r["condition_basis"].endswith("R4:単位既定")


def test_status_sold_out_from_the_item_line():
    raw = "◆スカーレットex\n完売\nパック@150円"
    items = [
        _it(2, price="none", quantity="none", heading=[1], names=[1]),
        _it(3, price="150円", quantity="none", heading=[1], names=[1]),
    ]
    r = _extract(raw, items)
    assert (r[0]["status"], r[0]["status_effect"]) == ("sold_out", "excluded")
    assert (r[1]["status"], r[1]["status_effect"]) == ("active", None)
    assert r[0]["unit"] == "none" and r[1]["unit"] == "パック"


def test_price_quantity_uses_order_and_records_reasons():
    (r,) = _extract("商品A\n3BOX@1,000円", [_it(2, price="1,000円", quantity="3", heading=[1], names=[1])], order="price_first")
    assert r["price_normalized"] == 1000 and r["quantity_normalized"] == 3
    assert r["price_reasons"] == []


def test_output_has_the_documented_keys_in_items_order():
    raw = "商品A\n3BOX@1,000円\n商品B\n4BOX@2,000円"
    items = [
        _it(2, price="1,000円", quantity="3", heading=[1], names=[1]),
        _it(4, price="2,000円", quantity="4", heading=[3], names=[3]),
    ]
    r = _extract(raw, items)
    assert [x["price_line"] for x in r] == [2, 4]
    assert set(r[0]) == {
        "price_line", "item_lines", "heading_lines", "shared_lines", "name_lines", "raw_price", "raw_quantity",
        "name", "unit", "unit_kubun", "condition", "condition_basis", "status", "status_effect", "ship",
        "price_normalized", "quantity_normalized", "price_reasons",
    }


def test_prompt_file_loads():
    assert "行番号の担当" in v10.load_v10_prompt()
