"""Gemini 書き写し v9（比較試験用）の単体試験。

設計: docs/handoff/gemini-v9/design.md §3〜§5
"""

from __future__ import annotations

import json
from pathlib import Path

import app.services.gemini_raw_copy_v8 as v8
import app.services.gemini_raw_copy_v9 as v9

_LINES = [f"line{i}" for i in range(1, 11)]
_LINES[4] = "シュリなし 【大阪発送】"
_RAW = "\n".join(_LINES)  # 10 行（5 行目だけ状態と発送を含む）


def _item(start, end, h_start=None, h_end=None, **over):
    base = {
        "product_name": "P",
        "price": "100円",
        "unit": "BOX",
        "quantity": "1",
        "state": "none",
        "ship": "none",
        "source_line_start": start,
        "source_line_end": end,
        "heading_line_start": h_start,
        "heading_line_end": h_end,
        "multi_note": "none",
        "state_line": None,
        "ship_line": None,
    }
    return {**base, **over}


def _resp(*items):
    return json.dumps({"items": list(items)}, ensure_ascii=False)


def _valid_state_ship(**over):
    return _item(5, 5, state="シュリなし", state_line=5, ship="【大阪発送】", ship_line=5, **over)


def test_accepts_valid_state_and_ship_with_line_numbers():
    # Arrange
    response = _resp(_valid_state_ship())
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert errors == []
    assert items[0]["raw_state_line"] == 5 and items[0]["raw_ship_line"] == 5
    assert items[0]["raw_state"] == "シュリなし" and items[0]["raw_ship"] == "【大阪発送】"


def test_same_line_heading_is_kept_and_heading_becomes_null():
    # Arrange
    response = _resp(_item(3, 3, 3, 3))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert errors == []
    assert len(items) == 1
    assert items[0]["heading_line_start"] is None and items[0]["heading_line_end"] is None


def test_partial_overlap_with_own_heading_is_still_dropped_like_v8():
    # Arrange
    response = _resp(_item(2, 4, 2, 2))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert items == []
    assert len(errors) == 1 and "重なる" in errors[0]["error"]


def test_same_line_heading_is_not_used_for_overlap_check_with_other_items():
    # Arrange
    response = _resp(_item(3, 3, 3, 3), _item(5, 5))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert errors == []
    assert len(items) == 2


def test_state_line_string_drops_item_with_type_error():
    # Arrange
    response = _resp(_item(5, 5, state_line="5"))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert items == []
    assert len(errors) == 1 and "型が違う" in errors[0]["error"]


def test_missing_state_line_field_drops_item():
    # Arrange
    obj = _item(5, 5)
    del obj["state_line"]
    # Act
    items, errors = v9.parse_v9_response(_resp(obj), _RAW)
    # Assert
    assert items == []
    assert "必須の欄がない: state_line" in errors[0]["error"]


def test_state_none_with_line_number_keeps_item_and_nulls_line():
    # Arrange
    response = _resp(_item(5, 5, state="none", state_line=5))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert len(items) == 1 and items[0]["raw_state_line"] is None
    assert len(errors) == 1 and errors[0]["kept"] is True


def test_state_value_without_line_number_blanks_value_and_keeps_item():
    # Arrange
    response = _resp(_item(5, 5, state="シュリなし", state_line=None))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert len(items) == 1 and items[0]["raw_state"] == "none"
    assert len(errors) == 1 and errors[0]["kept"] is True


def test_ship_line_out_of_range_blanks_value_and_keeps_item():
    # Arrange
    response = _resp(_item(5, 5, ship="【大阪発送】", ship_line=11))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert len(items) == 1 and items[0]["raw_ship"] == "none"
    assert len(errors) == 1 and errors[0]["kept"] is True and "範囲外" in errors[0]["error"]


def test_state_not_found_on_the_named_line_blanks_value_and_keeps_item():
    # Arrange
    response = _resp(_item(5, 5, state="未開封", state_line=5))
    # Act
    items, errors = v9.parse_v9_response(response, _RAW)
    # Assert
    assert len(items) == 1 and items[0]["raw_state"] == "none"
    assert len(errors) == 1 and errors[0]["kept"] is True and "5 行目に無い" in errors[0]["error"]


def test_fullwidth_and_whitespace_differences_match_after_nfkc_and_value_is_kept():
    # Arrange
    raw = "\n".join(["a", "b", "c", "d", "ＡＢＣ シュリなし 【大阪発送】", "f", "g", "h", "i", "j"])
    response = _resp(_item(5, 5, state="シュリ なし", state_line=5, ship="ABC", ship_line=5))
    # Act
    items, errors = v9.parse_v9_response(response, raw)
    # Assert
    assert errors == []
    assert items[0]["raw_state"] == "シュリ なし" and items[0]["raw_state_line"] == 5
    assert items[0]["raw_ship"] == "ABC" and items[0]["raw_ship_line"] == 5


def test_broken_json_is_single_whole_error_like_v8():
    # Act
    items, errors = v9.parse_v9_response("{not json", _RAW)
    # Assert
    assert items == []
    assert len(errors) == 1 and errors[0]["index"] is None
    assert errors == v8.parse_v8_response("{not json", _RAW)[1]


def test_v9_schema_has_line_fields_and_v8_schema_is_unchanged():
    # Arrange
    v9_item = v9.V9_RESPONSE_SCHEMA["properties"]["items"]["items"]
    v8_item = v8.V8_RESPONSE_SCHEMA["properties"]["items"]["items"]
    # Assert
    for name in ("state_line", "ship_line"):
        assert name in v9_item["properties"] and name in v9_item["required"]
        assert name not in v8_item["properties"] and name not in v8_item["required"]


def test_v9_prompt_file_exists_has_key_terms_and_differs_from_v8():
    # Arrange
    prompts = Path(v9.__file__).resolve().parent.parent / "prompts"
    v9_text = (prompts / "raw_copy_v9.txt").read_text(encoding="utf-8")
    v8_text = (prompts / "raw_copy_v8.txt").read_text(encoding="utf-8")
    # Assert
    for term in ("state_line", "ship_line", "【大阪発送】", "◆ニンジャスピナー"):
        assert term in v9_text
    assert v9_text != v8_text
    assert v9.load_v9_prompt() == v9_text


def _raw_with(overrides: dict[int, str]) -> str:
    lines = [f"line{i}" for i in range(1, 11)]
    for line_no, text in overrides.items():
        lines[line_no - 1] = text
    return "\n".join(lines)


def test_state_line_inside_other_items_heading_blanks_state_and_keeps_both_items():
    # Arrange
    raw = _raw_with({2: "◆A", 5: "◆B(シュリなし)"})
    item_a = _item(3, 3, 2, 2, state="シュリなし", state_line=5)
    item_b = _item(6, 6, 5, 5)
    # Act
    items, errors = v9.parse_v9_response(_resp(item_a, item_b), raw)
    # Assert
    assert len(items) == 2
    assert items[0]["raw_state"] == "none" and items[0]["raw_state_line"] is None
    assert len(errors) == 1 and errors[0]["kept"] is True and "自分の範囲・見出しの外" in errors[0]["error"]


def test_state_line_on_own_heading_is_kept():
    # Arrange
    raw = _raw_with({2: "◆A(シュリなし)"})
    item_a = _item(3, 3, 2, 2, state="シュリなし", state_line=2)
    # Act
    items, errors = v9.parse_v9_response(_resp(item_a), raw)
    # Assert
    assert items[0]["raw_state"] == "シュリなし" and items[0]["raw_state_line"] == 2
    assert [e for e in errors if e.get("kept")] == []


def test_ship_line_inside_other_items_range_blanks_ship():
    # Arrange
    raw = _raw_with({2: "◆A", 7: "【大阪発送】B 5@100円"})
    item_a = _item(3, 3, 2, 2, ship="【大阪発送】", ship_line=7)
    item_b = _item(7, 7)
    # Act
    items, errors = v9.parse_v9_response(_resp(item_a, item_b), raw)
    # Assert
    assert len(items) == 2
    assert items[0]["raw_ship"] == "none" and items[0]["raw_ship_line"] is None
    assert len(errors) == 1 and errors[0]["kept"] is True and "ほかの件の範囲・見出しの中" in errors[0]["error"]


def test_ship_line_above_item_owned_by_nobody_is_kept():
    # Arrange
    raw = _raw_with({1: "【大阪発送】", 2: "◆A"})
    item_a = _item(3, 3, 2, 2, ship="【大阪発送】", ship_line=1)
    # Act
    items, errors = v9.parse_v9_response(_resp(item_a), raw)
    # Assert
    assert items[0]["raw_ship"] == "【大阪発送】" and items[0]["raw_ship_line"] == 1
    assert [e for e in errors if e.get("kept")] == []


def test_ship_line_below_item_owned_by_nobody_blanks_ship():
    # Arrange
    raw = _raw_with({2: "◆A", 9: "・17時までのご注文で当日発送"})
    item_a = _item(3, 3, 2, 2, ship="当日発送", ship_line=9)
    # Act
    items, errors = v9.parse_v9_response(_resp(item_a), raw)
    # Assert
    assert items[0]["raw_ship"] == "none" and items[0]["raw_ship_line"] is None
    assert len(errors) == 1 and errors[0]["kept"] is True and "自分の件より下にある" in errors[0]["error"]
