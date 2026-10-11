"""試作版 v102：要確認の出どころ（source：system／gemini）を付ける処理の単体試験。Gemini・DB は使わない。

設計: docs/handoff/v102-review-source/design.md
守り手: この試験ファイル（source の付き方・元の dict を書き換えないこと・gemini_review 欄が変わらないこと）。
"""
from __future__ import annotations

import copy

import app.tools.prompt_ab as pab

_UNSURE = {"kind": "gemini_unsure", "line": 3, "candidates": [2, 4]}


def _fields(items: list[dict], post_review=None, unsure=None) -> dict:
    flags = {"gemini_review": unsure or []}
    if post_review is not None:
        flags["post_review"] = post_review
    return {"v102_items": items, "v102_flags": flags}


def _item(price_line, review=None, **extra) -> dict:
    base = {"price_line": price_line, "gemini_review": []}
    if review is not None:
        base["review"] = review
    return {**base, **extra}


def test_review_element_without_source_gets_system():
    # Arrange
    fields = _fields([_item(2, [{"line": 2, "kind": "unit_unknown"}])])
    # Act
    result = pab._with_review_sources(fields, [])
    # Assert
    assert result["v102_items"][0]["review"] == [{"line": 2, "kind": "unit_unknown", "source": "system"}]


def test_review_element_with_source_is_not_changed():
    fields = _fields([_item(2, [{"line": 2, "kind": "x", "source": "gemini"}])])
    result = pab._with_review_sources(fields, [])
    assert result["v102_items"][0]["review"] == [{"line": 2, "kind": "x", "source": "gemini"}]


def test_gemini_unsure_is_appended_as_gemini_to_items_whose_price_line_is_a_candidate_only():
    # Arrange
    fields = _fields(
        [_item(2, [{"kind": "a"}]), _item(4, []), _item(6, [{"kind": "b"}])], unsure=[_UNSURE])
    # Act
    result = pab._with_review_sources(fields, [_UNSURE])
    # Assert
    gemini = {"line": 3, "kind": "gemini_unsure", "candidates": [2, 4], "source": "gemini"}
    reviews = [it["review"] for it in result["v102_items"]]
    assert reviews == [[{"kind": "a", "source": "system"}, gemini], [gemini], [{"kind": "b", "source": "system"}]]


def test_gemini_review_field_of_item_and_flags_stay_as_they_were():
    fields = _fields([_item(2, [], gemini_review=[{"kind": "gemini_unsure", "line": 3}])], unsure=[_UNSURE])
    result = pab._with_review_sources(fields, [_UNSURE])
    assert result["v102_items"][0]["gemini_review"] == [{"kind": "gemini_unsure", "line": 3}]
    assert result["v102_flags"]["gemini_review"] == [_UNSURE]


def test_invalid_unsure_goes_to_post_review_as_system_and_marks_no_item():
    # Arrange
    invalid = {"kind": "gemini_unsure_invalid", "error": "unsure_not_list"}
    invalid_with_line = {"kind": "gemini_unsure_invalid", "error": "candidate_not_price_line", "line": 3, "candidates": [2, 3]}
    fields = _fields([_item(2, [])], post_review=[{"kind": "no_items"}], unsure=[invalid, invalid_with_line])
    # Act
    result = pab._with_review_sources(fields, [invalid, invalid_with_line])
    # Assert
    assert result["v102_flags"]["post_review"] == [
        {"kind": "no_items", "source": "system"},
        {"kind": "gemini_unsure_invalid", "error": "unsure_not_list", "source": "system"},
        {"kind": "gemini_unsure_invalid", "error": "candidate_not_price_line", "line": 3, "candidates": [2, 3], "source": "system"},
    ]
    assert result["v102_items"][0]["review"] == []


def test_post_review_element_with_source_is_not_changed():
    fields = _fields([], post_review=[{"kind": "x", "source": "gemini"}])
    assert pab._with_review_sources(fields, [])["v102_flags"]["post_review"] == [{"kind": "x", "source": "gemini"}]


def test_does_not_mutate_the_input():
    # Arrange
    fields = _fields([_item(2, [{"kind": "a"}])], post_review=[{"kind": "no_items"}], unsure=[_UNSURE])
    before = copy.deepcopy(fields)
    unsure_before = copy.deepcopy([_UNSURE])
    # Act
    pab._with_review_sources(fields, [_UNSURE])
    # Assert
    assert fields == before and [_UNSURE] == unsure_before


def test_without_unsure_only_source_is_added():
    # Arrange
    fields = _fields([_item(2, [{"line": 2, "kind": "a"}]), _item(4)], post_review=[{"kind": "no_items"}])
    # Act
    result = pab._with_review_sources(fields, [])
    # Assert
    stripped = copy.deepcopy(result)
    for it in stripped["v102_items"]:
        for r in it.get("review", []):
            r.pop("source")
    for r in stripped["v102_flags"]["post_review"]:
        r.pop("source")
    assert stripped == fields
    assert "review" not in result["v102_items"][1]


def test_flags_without_post_review_get_no_post_review_key():
    result = pab._with_review_sources(_fields([_item(2, [])]), [])
    assert "post_review" not in result["v102_flags"]
