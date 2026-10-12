"""試作版 v102：Gemini の unsure（上下どちらの件か決まらない行）の受け取りの単体試験。Gemini・DB は使わない。

設計: docs/handoff/v102-gemini-unsure/design.md
守り手: この試験ファイル（unsure を捨てないこと・v101 の出力と スキーマが変わらないこと）。
"""
from __future__ import annotations

import copy
import json

import pytest

from app.services import gemini_raw_copy_v101 as v101

LINE_COUNT = 10
PRICE_LINES = {2, 4, 6}


def _resp(unsure, items=None) -> str:
    body = {"items": items if items is not None else []}
    if unsure is not _MISSING:
        body["unsure"] = unsure
    return json.dumps(body, ensure_ascii=False)


_MISSING = object()


def _parse(unsure):
    return v101.parse_v102_unsure(_resp(unsure), LINE_COUNT, PRICE_LINES)


def test_valid_unsure_becomes_gemini_unsure_with_sorted_unique_candidates():
    # Arrange
    unsure = [{"line": 3, "candidates": [4, 2, 4]}]
    # Act
    result = _parse(unsure)
    # Assert
    assert result == [{"kind": "gemini_unsure", "line": 3, "candidates": [2, 4]}]


def test_several_valid_elements_keep_their_order():
    result = _parse([{"line": 3, "candidates": [2, 4]}, {"line": 5, "candidates": [4, 6]}])
    assert [r["line"] for r in result] == [3, 5] and {r["kind"] for r in result} == {"gemini_unsure"}


@pytest.mark.parametrize("unsure", [_MISSING, [], None])
def test_no_or_empty_unsure_gives_empty_list(unsure):
    assert _parse(unsure) == []


@pytest.mark.parametrize("text", ["not json", "[]", '{"items": 1}', "", None])
def test_unreadable_response_gives_empty_list(text):
    assert v101.parse_v102_unsure(text, LINE_COUNT, PRICE_LINES) == []


@pytest.mark.parametrize("unsure", ["x", 1, {"line": 3, "candidates": [2, 4]}])
def test_unsure_not_a_list_is_one_invalid_record(unsure):
    assert _parse(unsure) == [{"kind": "gemini_unsure_invalid", "error": "unsure_not_list"}]


@pytest.mark.parametrize(
    ("element", "expected"),
    [
        ("text", {"error": "not_object"}),
        ([3, [2, 4]], {"error": "not_object"}),
        ({"line": "3", "candidates": [2, 4]}, {"error": "line_not_int"}),
        ({"line": True, "candidates": [2, 4]}, {"error": "line_not_int"}),
        ({"candidates": [2, 4]}, {"error": "line_not_int"}),
        ({"line": 0, "candidates": [2, 4]}, {"error": "line_out_of_range", "line": 0}),
        ({"line": 11, "candidates": [2, 4]}, {"error": "line_out_of_range", "line": 11}),
        ({"line": 3, "candidates": "2,4"}, {"error": "candidates_not_list", "line": 3}),
        ({"line": 3}, {"error": "candidates_not_list", "line": 3}),
        ({"line": 3, "candidates": [2, "4"]}, {"error": "candidate_not_int", "line": 3, "candidates": [2]}),
        ({"line": 3, "candidates": [2, 3]}, {"error": "candidate_not_price_line", "line": 3, "candidates": [2, 3]}),
        ({"line": 3, "candidates": [2, 99]}, {"error": "candidate_not_price_line", "line": 3, "candidates": [2, 99]}),
        ({"line": 3, "candidates": [2]}, {"error": "candidates_too_few", "line": 3, "candidates": [2]}),
        ({"line": 3, "candidates": [2, 2]}, {"error": "candidates_too_few", "line": 3, "candidates": [2]}),
        ({"line": 3, "candidates": []}, {"error": "candidates_too_few", "line": 3, "candidates": []}),
    ],
)
def test_each_invalid_element_gets_its_error_code(element, expected):
    # Act
    result = _parse([element])
    # Assert
    assert result == [{"kind": "gemini_unsure_invalid", **expected}]


def test_invalid_element_does_not_hide_the_valid_one_next_to_it():
    result = _parse(["x", {"line": 3, "candidates": [2, 4]}])
    assert [r["kind"] for r in result] == ["gemini_unsure_invalid", "gemini_unsure"]


def test_invalid_records_carry_no_raw_text():
    # Arrange: 原文の文字（文字列の値）を載せない（ADR-014・ADR-027）
    secret = "SECRET-RAW-LINE"
    result = _parse([{"line": secret, "candidates": [secret]}, {"line": 3, "candidates": [2, secret]}, secret])
    # Assert
    assert secret not in json.dumps(result, ensure_ascii=False)


def test_v102_schema_adds_unsure_and_keeps_items_definition_of_v101():
    # Arrange
    v101_schema, v102_schema = v101.V101_RESPONSE_SCHEMA, v101.V102_RESPONSE_SCHEMA
    # Assert
    assert v102_schema["properties"]["items"] == v101_schema["properties"]["items"]
    assert v102_schema["required"] == v101_schema["required"] == ["items"]
    assert v102_schema["properties"]["unsure"] == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"line": {"type": "integer"}, "candidates": {"type": "array", "items": {"type": "integer"}}},
            "required": ["line", "candidates"],
        },
    }
    assert set(v102_schema["properties"]) == {"items", "unsure"}


def test_v101_schema_is_not_changed_by_building_the_v102_schema():
    assert set(v101.V101_RESPONSE_SCHEMA["properties"]) == {"items"}
    assert v101.V102_RESPONSE_SCHEMA is not v101.V101_RESPONSE_SCHEMA
    snapshot = copy.deepcopy(v101.V101_RESPONSE_SCHEMA)
    v101.V102_RESPONSE_SCHEMA["properties"]["items"]["items"]["required"].append("x")  # 浅いコピーなら元に届く
    try:
        assert v101.V101_RESPONSE_SCHEMA == snapshot
    finally:
        v101.V102_RESPONSE_SCHEMA["properties"]["items"]["items"]["required"].remove("x")


def test_parse_v101_response_ignores_unsure_so_v101_output_is_unchanged():
    # Arrange
    items = [{"lines": [1, 2], "price": "1,000円", "quantity": "3"}]
    raw = "商品A\n3BOX@1,000円"
    with_unsure = v101.parse_v101_response(_resp([{"line": 1, "candidates": [2, 3]}], items), raw)
    without = v101.parse_v101_response(_resp(_MISSING, items), raw)
    # Assert
    assert with_unsure == without
