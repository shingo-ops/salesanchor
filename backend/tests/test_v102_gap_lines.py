"""v102 の間の行の検知（段1）の単体試験。DB なし・Gemini なし。商品・原文はすべて架空。

設計: docs/handoff/v102-gap-detect-record/design.md §3 PR②。
"""
from __future__ import annotations

from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.v102_gap_lines import (
    CLASS_GAP,
    CLASS_PRE,
    CLASS_SPAN,
    CLASS_TRAIL,
    CLASS_USED,
    accepted_items,
    build_gap_detail,
    classify_lines,
    gap_name_candidates,
    gap_price_qty_lines,
    has_money,
    has_q,
    to_stored_detail,
)


def entry(product_id: int, *keywords: str) -> ProductEntry:
    return ProductEntry(
        id=product_id, product_code=None, mark=None, work_id=1, search_keywords=tuple(keywords), exclude_keywords=(),
    )


def masters(*entries: ProductEntry) -> ProductFirstMasters:
    return ProductFirstMasters(product_entries=tuple(entries), product_kubun={}, condition_unit={}, ignore_phrases=())


def item(
    index: int, lines: list[int], price_line: int, *, price: str | None = "1,000円", quantity: str | None = "2",
    status: str = "unmatched", name: str | None = None, rejected: str | None = None,
) -> dict:
    out = {
        "gemini_index": index, "lines": lines, "price_line": price_line, "raw_price": price, "raw_quantity": quantity,
        "match_status": status, "name": name,
    }
    return {**out, "rejected": rejected} if rejected else out


# --- 分類 -------------------------------------------------------------------------------------------


def test_classify_splits_unused_lines_into_pre_gap_span_trail_and_skips_empty_lines():
    lines = ["前書き", "品A", "100円", "間の行", "", "品B", "途中の行", "200円", "品C", "300円", "末尾の行"]
    items = [
        item(1, [6, 8], 8),
        item(3, [9, 10], 10),
        item(0, [2, 3], 3),
        item(2, [4], 4, rejected="price_not_in_lines"),  # 落とした件は数えない：4 行目は gap のまま
    ]

    classes = classify_lines(accepted_items(items), lines)

    assert {n: c for n, (c, _k) in classes.items()} == {
        1: CLASS_PRE, 2: CLASS_USED, 3: CLASS_USED, 4: CLASS_GAP, 6: CLASS_USED, 7: CLASS_SPAN, 8: CLASS_USED,
        9: CLASS_USED, 10: CLASS_USED, 11: CLASS_TRAIL,
    }
    assert classes[1][1] == 0 and classes[4][1] == 1 and classes[7][1] == 2  # 直後の件の位置（最初の行の順）


def test_accepted_items_drops_rejected_and_orders_by_first_line():
    items = [item(1, [5, 6], 6), item(0, [2, 3], 3), item(2, [8], 8, rejected="duplicate_price_line")]

    assert [it["gemini_index"] for it in accepted_items(items)] == [0, 1]


# --- T1：gap の行だけ、価格と数量の形を見る ----------------------------------------------------------


def test_t1_counts_only_gap_lines_with_price_and_quantity_shape():
    lines = [
        "1,200円 ×3",  # pre：数えない（recon §3：誤報だけだった）
        "品A", "100円 ×1",  # 件1（2-3）
        "1,500円 ×2",  # gap：数える
        "2,000円",  # gap だが数量の形が無い
        "品B", "300円 ×1",  # 件2（6-7）。5 行目の後
        "980円 ×5",  # trail：数えない
    ]
    items = [item(0, [2, 3], 3), item(1, [6, 7], 7)]

    assert gap_price_qty_lines(accepted_items(items), lines) == [4]


def test_t1_ignores_span_lines_inside_an_item():
    lines = ["品A", "1,500円 ×2", "100円 ×1", "品B", "200円 ×1"]
    items = [item(0, [1, 3], 3), item(1, [4, 5], 5)]

    assert gap_price_qty_lines(accepted_items(items), lines) == []


def test_money_and_quantity_shapes_follow_the_measured_expressions():
    assert has_money("1,500円") and has_money("12000") and not has_money("2026") and not has_money("品名")
    assert has_q("3box") and has_q("x3") is False  # 「x3」は数字の前に数字が無いので x の形に当たらない
    assert has_q("5 x 3") and has_q("在庫 2") and has_q("100@3")


# --- T2/H2：見出し側の語で補える件 -------------------------------------------------------------------


def test_t2_base_shop_type_matches_with_gap_line_and_item_lines_together():
    # 1 行目の見出しだけでは当たらない。件の行と合わせると 1001 に当たる（BASE SHOP 型）
    lines = ["BASESHOP", "matA", "3,000円 ×2"]
    items = [item(0, [2, 3], 3, price="3,000円", quantity="2")]

    result = gap_name_candidates(accepted_items(items), lines, masters(entry(1001, "BASESHOP matA")))

    assert result == [{"gemini_index": 0, "gap_lines": [1], "support_lines": [1], "candidates": [1001]}]


def test_t2_effect_range_runs_to_the_item_before_the_next_group():
    lines = ["BASESHOP", "matA", "3,000円 ×2", "matA", "4,000円 ×1", "別の見出し", "matZ", "5,000円 ×1"]
    items = [item(0, [2, 3], 3), item(1, [4, 5], 5), item(2, [7, 8], 8)]

    result = gap_name_candidates(accepted_items(items), lines, masters(entry(1001, "BASESHOP matA")))

    assert [(r["gemini_index"], r["gap_lines"], r["candidates"]) for r in result] == [(0, [1], [1001]), (1, [1], [1001]), (2, [6], [])]


def test_t2_a_line_that_matches_a_product_by_itself_is_not_used_as_support():
    # 見出しだけで当たる行（商品 2001）は支えに使わない。その結果、件 1002 には何も足されない
    lines = ["ALPHA", "matA", "3,000円 ×2"]
    items = [item(0, [2, 3], 3)]
    product_masters = masters(entry(2001, "ALPHA"), entry(1002, "ALPHA matA"))

    result = gap_name_candidates(accepted_items(items), lines, product_masters)

    assert result == [{"gemini_index": 0, "gap_lines": [1], "support_lines": [], "candidates": []}]


def test_t2_does_not_run_for_a_matched_item_so_an_unpriced_stock_list_stays_quiet():
    lines = ["在庫一覧", "matA", "matB", "matC", "品A", "3,000円 ×2"]
    items = [item(0, [5, 6], 6, status="matched")]  # 直後の件が matched

    assert gap_name_candidates(accepted_items(items), lines, masters(entry(1001, "在庫一覧 matA"))) == []


def test_t2_skips_items_without_price_or_quantity():
    lines = ["BASESHOP", "matA", "完売", "BASESHOP", "matA", "3,000円"]
    items = [
        item(0, [2, 3], 3, price=None, quantity="2"),
        item(1, [5, 6], 6, price="3,000円", quantity="none"),
    ]

    assert gap_name_candidates(accepted_items(items), lines, masters(entry(1001, "BASESHOP matA"))) == []


def test_t2_with_no_candidate_keeps_an_empty_candidate_list():
    lines = ["見出し", "品名", "3,000円 ×2"]
    items = [item(0, [2, 3], 3)]

    result = gap_name_candidates(accepted_items(items), lines, masters(entry(1001, "BASESHOP matA")))

    assert result == [{"gemini_index": 0, "gap_lines": [1], "support_lines": [], "candidates": []}]


def test_t2_ambiguous_union_is_returned_sorted():
    lines = ["BASESHOP", "matC", "3,000円 ×2"]
    items = [item(0, [2, 3], 3)]
    product_masters = masters(entry(2002, "BASESHOP matC"), entry(2001, "BASESHOP matC"))

    result = gap_name_candidates(accepted_items(items), lines, product_masters)

    assert result == [{"gemini_index": 0, "gap_lines": [1], "support_lines": [1], "candidates": [2001, 2002]}]


# --- 書く値 -----------------------------------------------------------------------------------------


def test_build_gap_detail_collects_post_review_t1_and_t2_without_any_text():
    lines = ["BASESHOP", "matA", "3,000円 ×2", "1,500円 ×2"]
    items = [item(0, [2, 3], 3), item(1, [9], 9, rejected="price_not_in_lines")]
    post_review = [
        {"kind": "possible_missing_item", "line": 4, "source": "system"},
        {"kind": "extract_exception", "error": "ValueError: 原文の一部", "source": "system"},
        {"kind": "gemini_unsure_invalid", "line": 7, "candidates": [1], "error": "x", "source": "system"},
    ]

    detail = build_gap_detail(items, lines, masters(entry(1001, "BASESHOP matA")), post_review)

    assert detail == {
        "post_review": [{"kind": "possible_missing_item", "line": 4}, {"kind": "gemini_unsure_invalid", "line": 7}],
        "gap_price_qty": [],
        "gap_name": [{"gemini_index": 0, "gap_lines": [1], "support_lines": [1], "candidates": [1001]}],
    }


def test_build_gap_detail_lists_t1_lines_as_objects():
    lines = ["品A", "100円 ×1", "1,500円 ×2", "品B", "200円 ×1"]
    items = [item(0, [1, 2], 2, status="matched"), item(1, [4, 5], 5, status="matched")]

    detail = build_gap_detail(items, lines, masters(), [])

    assert detail["gap_price_qty"] == [{"line": 3}]


def test_to_stored_detail_replaces_gemini_index_with_item_id_and_counts_unmapped():
    detail = {
        "post_review": [{"kind": "possible_missing_item", "line": 12}],
        "gap_price_qty": [{"line": 85}],
        "gap_name": [
            {"gemini_index": 0, "gap_lines": [31, 32], "support_lines": [31], "candidates": [440415]},
            {"gemini_index": 5, "gap_lines": [40], "support_lines": [], "candidates": []},
        ],
    }

    stored = to_stored_detail(detail, {0: "item-uuid-0"})

    assert stored == {
        "v": 1,
        "post_review": [{"kind": "possible_missing_item", "line": 12}],
        "gap_price_qty": [{"line": 85}],
        "gap_name": [
            {"extraction_item_id": "item-uuid-0", "gap_lines": [31, 32], "support_lines": [31], "candidates": [440415]},
        ],
        "unmapped": 1,
    }


def test_build_gap_detail_without_product_masters_still_gives_t1_and_leaves_gap_name_empty():
    lines = ["品A", "100円 ×1", "1,500円 ×2", "品B", "200円 ×1"]
    items = [item(0, [1, 2], 2), item(1, [4, 5], 5)]  # unmatched でも、商品のマスタが無ければ照合しない

    detail = build_gap_detail(items, lines, None, [])

    assert detail["gap_price_qty"] == [{"line": 3}] and detail["gap_name"] == []


def test_classify_uses_the_running_maximum_of_earlier_items_for_span_and_gap():
    # 件0 が 1〜10 を使い、その内側に件1（3-4）がある。5 行目は件0 の範囲内なので span、11 行目は gap
    lines = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m"]
    items = [item(0, [1, 10], 10), item(1, [3, 4], 4), item(2, [12, 13], 13)]

    classes = classify_lines(accepted_items(items), lines)

    assert classes[5] == (CLASS_SPAN, 2) and classes[11] == (CLASS_GAP, 2)


def test_build_gap_detail_classifies_the_post_only_once(monkeypatch):
    import app.services.v102_gap_lines as module

    calls = []
    original = module.classify_lines
    monkeypatch.setattr(module, "classify_lines", lambda *args: calls.append(1) or original(*args))
    lines = ["BASESHOP", "matA", "3,000円 ×2", "1,500円 ×2", "品B", "200円 ×1"]
    items = [item(0, [2, 3], 3), item(1, [5, 6], 6)]

    module.build_gap_detail(items, lines, masters(entry(1001, "BASESHOP matA")), [])

    assert len(calls) == 1


def test_classify_grows_with_the_number_of_lines_not_its_square():
    import time

    count = 4000
    lines = [f"行{n}" for n in range(1, count + 1)]
    items = [item(n, [n * 2 - 1], n * 2) for n in range(1, count // 2 + 1)]

    started = time.perf_counter()
    classify_lines(accepted_items(items), lines)

    assert time.perf_counter() - started < 1.0  # 二乗の実装では数秒かかる大きさ
