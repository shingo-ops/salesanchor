"""試作版 v102：見出しの直下の発送の行を、自分の発送の行を持つ2件目以降の件にも入れたときの要確認。

設計: docs/handoff/v102-heading-ship-review/design.md。例文はすべて作った文。Gemini・DB は使わない。
"""
from __future__ import annotations

import copy
import json

from app.services import gemini_raw_copy_v101 as v101

_UNITS = {"BOX": ("BOX", "箱系"), "セット": ("セット", "セット系")}
_STATUS = [
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99,
     "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_MASTERS = {"cond_entries": [], "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS, "status_entries": _STATUS}
_KIND = "heading_ship_with_own_ship"

# 1 見出し / 2 発送A / 3 価格1 / 4 発送B / 5 発送C / 6 価格2
_RAW = "【サンプル商品】\n発送:12月\n3BOX@1,000円\n発送:1月\n発送:2月\n2BOX@2,000円"


def _it(lines, price, quantity="1"):
    return {"lines": list(lines), "price": price, "quantity": quantity}


def _run(raw, *items, review_reasons=True):
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": list(items)}, ensure_ascii=False), raw, status_entries=_STATUS, keep_rejected=True)
    assert errors == []
    return v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, review_reasons=review_reasons, **_MASTERS)


def _kinds(row):
    return [r["kind"] for r in row["review"]]


def _heading(row):
    return [r for r in row["review"] if r["kind"] == _KIND]


def test_marks_second_item_that_took_the_heading_ship_line_and_has_its_own_ship_lines():
    out, _ = _run(_RAW, _it([1, 2, 3], "1,000円", "3"), _it([1, 2, 4, 5, 6], "2,000円", "2"))
    assert out[0]["roles"][2] == "ship"
    assert _heading(out[0]) == []
    assert _heading(out[1]) == [{"line": 2, "kind": _KIND, "own_lines": [4, 5]}]


def test_does_not_mark_when_second_item_did_not_take_the_heading_ship_line():
    out, _ = _run(_RAW, _it([1, 2, 3], "1,000円", "3"), _it([1, 4, 5, 6], "2,000円", "2"))
    assert _heading(out[0]) == [] and _heading(out[1]) == []


def test_does_not_mark_when_second_item_has_no_own_ship_line():
    raw = "【サンプル商品】\n【発送】12月\n3BOX@1,000円\n2BOX@2,000円"
    out, _ = _run(raw, _it([1, 2, 3], "1,000円", "3"), _it([1, 2, 4], "2,000円", "2"))
    assert out[1]["roles"][2] == "ship"
    assert _heading(out[0]) == [] and _heading(out[1]) == []


def test_does_not_mark_when_the_group_has_only_one_item():
    out, _ = _run(_RAW, _it([1, 2, 3], "1,000円", "3"))
    assert _heading(out[0]) == []


def test_does_not_mark_when_the_ship_text_is_on_the_price_line():
    raw = "【サンプル商品】\n3BOX@1,000円 12月発送\n発送:1月\n2BOX@2,000円"
    out, _ = _run(raw, _it([1, 2], "1,000円", "3"), _it([1, 2, 3, 4], "2,000円", "2"))
    assert out[0]["roles"][2] == "price"
    assert _heading(out[1]) == []


def test_keeps_existing_review_items_first_appends_new_one_last_and_does_not_mutate_input():
    parsed, _ = v101.parse_v101_response(
        json.dumps({"items": [_it([1, 2, 3], "1,000円", "3"), _it([1, 2, 4, 5, 6], "2,000円", "2")]}, ensure_ascii=False),
        _RAW, status_entries=_STATUS, keep_rejected=True)
    out, _ = v101.extract_v101_items(
        parsed, _RAW, order=None, reassign=True, v102_fixes=True, review_reasons=True, **_MASTERS)
    base = [r for r in out[1]["review"] if r["kind"] != _KIND]
    assert out[1]["review"][-1]["kind"] == _KIND
    assert out[1]["review"][:len(base)] == base
    rows = copy.deepcopy(out)
    before = copy.deepcopy(rows)
    v101._heading_ship_reasons(rows)
    assert rows == before


def test_review_reasons_false_output_has_no_new_kind():
    out, flags = _run(_RAW, _it([1, 2, 3], "1,000円", "3"), _it([1, 2, 4, 5, 6], "2,000円", "2"), review_reasons=False)
    assert all(_KIND not in _kinds(row) for row in out) and "post_review" not in flags
    assert [row["review"] for row in out] == [[], []]


def test_does_not_mark_when_only_the_heading_line_itself_has_the_ship_role():
    raw = "◆サンプルBOX 発売日発送\n3BOX@1,000円\n発送:1月\n2BOX@2,000円"
    out, _ = _run(raw, _it([1, 2], "1,000円", "3"), _it([1, 3, 4], "2,000円", "2"))
    assert out[1]["roles"][1] == "ship"
    assert _heading(out[0]) == [] and _heading(out[1]) == []


_RAW3 = "【サンプル商品】\n発送:12月\n3BOX@1,000円\n発送:1月\n2BOX@2,000円\n1BOX@3,000円"


def _row(lines, price_line, ship_lines):
    roles = {n: "ship" if n in ship_lines else "name" for n in lines}
    roles[price_line] = "price"
    return {"lines": list(lines), "price_line": price_line, "roles": roles, "review": []}


def test_ship_line_also_in_third_item_is_not_counted_as_own_line_of_second_item():
    # 1 見出し / 2 発送A / 3 価格1 / 4 発送B（件2と件3の両方の lines）/ 5 価格2 / 6 価格3
    # （_run 経由では F1 が件3から行4を外すため、行を直接組んで関数だけを試す）
    rows = [_row([1, 2, 3], 3, {2}), _row([1, 2, 4, 5], 5, {2, 4}), _row([1, 4, 6], 6, {4})]
    assert v101._heading_ship_reasons(rows) == [[], [], []]


def test_ship_line_only_in_second_item_is_counted_as_own_line_with_three_items():
    out, _ = _run(_RAW3, _it([1, 2, 3], "1,000円", "3"), _it([1, 2, 4, 5], "2,000円", "2"), _it([1, 6], "3,000円", "1"))
    assert _heading(out[1]) == [{"line": 2, "kind": _KIND, "own_lines": [4]}]
    assert _heading(out[0]) == [] and _heading(out[2]) == []


def test_rejected_rows_are_neither_grouped_nor_counted_as_other_items_lines():
    out, _ = _run(_RAW, _it([1, 2, 3], "1,000円", "3"), _it([1, 2, 4, 5, 6], "2,000円", "2"))
    rejected = {"rejected": "price_not_in_lines", "lines": [1, 4, 5], "price_line": None, "roles": {}, "review": []}
    with_rejected = v101._heading_ship_reasons([*out, rejected])
    assert with_rejected[:2] == v101._heading_ship_reasons(out)
    assert with_rejected[2] == [] and with_rejected[1][0]["own_lines"] == [4, 5]
