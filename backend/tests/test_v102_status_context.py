"""試作版 v102：ステータスを、発売日・先の日付・見出しの手がかりで予約に決める（便PO）。

設計: docs/handoff/v102-preorder-context/card-PO.md。例文はすべて作った文。Gemini・DB は使わない。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from app.services import gemini_raw_copy_v101 as v101
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.v102_status_context import posted_jst_date

_UNITS = {"BOX": ("BOX", "箱系"), "Box": ("Box", "箱系")}
_ARRIVAL = r"[^0-9]{0,4}(?:入荷|発送|発売)"
# tcg_status_master id25（便2 shipdate-range）。範囲「m/d1～d2」「m/d1～m/d2」は終わりの日を m・d に取る
_RANGE_SLASH = (
    r"(?:\d{1,2}/\d{1,2}[～〜~\-－](?=\d{1,2}/))?(?P<m>\d{1,2})/(?:\d{1,2}[～〜~\-－])?(?P<d>\d{1,2})"
)


def _row(canonical, effect, match_type, pattern, exclude, priority):
    return {"canonical": canonical, "search_pattern": pattern, "exclude_pattern": exclude, "priority": priority,
            "match_type": match_type, "effect": effect}


_BASE = [
    _row("Sold out", "EXCLUDE", "LITERAL", "完売", "", 1),
    _row("In Stock", "OUTPUT", "DEFAULT", "", "", 99),
]
_CONTEXT = [
    _row("Pre-order", "RELEASE_AHEAD", "RELEASE", "", "", 10),
    _row("Pre-order", "DATE_AHEAD", "REGEX", _RANGE_SLASH + _ARRIVAL, "", 10),
    _row("Pre-order", "DATE_AHEAD", "REGEX", r"(?P<m>\d{1,2})月(?P<d>\d{1,2})日" + _ARRIVAL, "", 20),
    _row("Pre-order", "DATE_AHEAD", "REGEX", r"(?P<m>\d{1,2})月(?P<part>上旬|中旬|下旬|末|頃)?" + _ARRIVAL, "", 30),
    _row("Pre-order", "HEADING", "REGEX", "予約", "ご予約可能|集荷予約", 10),
    _row("In Stock", "HEADING", "REGEX", "在庫|現物|即納", "在庫なし", 20),
]
_PRODUCTS = (
    ProductEntry(id=1, product_code=None, mark=None, work_id=1, search_keywords=("サンプル拡張",), exclude_keywords=()),
)
_POSTED = date(2026, 10, 11)


def _masters(status_entries, release=None, posted=_POSTED):
    return {
        "cond_entries": [], "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS, "status_entries": status_entries,
        "product_first": ProductFirstMasters(
            product_entries=_PRODUCTS, product_kubun={"1": "箱系"}, condition_unit={}, ignore_phrases=(),
            product_release=release or {}, posted_date=posted,
        ),
    }


def _it(lines, price="1,500円", quantity="3"):
    return {"lines": list(lines), "price": price, "quantity": quantity}


def _run(raw, item_lines, *, entries=None, release=None, posted=_POSTED):
    status_entries = _BASE + _CONTEXT if entries is None else entries
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": [_it(item_lines)]}, ensure_ascii=False), raw, status_entries=status_entries
    )
    assert errors == []
    masters = _masters(status_entries, release, posted)
    out, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=False, v102_fixes=True, review_reasons=True, gemini_trust=True, **masters
    )
    return out[0]


def _price_line(suffix=""):
    return f"3@1,500円{suffix}"


# --- 発売日 ----------------------------------------------------------------------------------


def test_future_release_date_makes_pre_order():
    row = _run(f"サンプル拡張\n{_price_line()}", [1, 2], release={"1": date(2026, 10, 16)})
    assert (row["status"], row["status_basis"]) == ("Pre-order", "RELEASE_AHEAD:2026-10-16")


@pytest.mark.parametrize("release", [date(2026, 10, 11), date(2026, 9, 1), None])
def test_release_today_past_or_missing_is_unchanged(release):
    row = _run(f"サンプル拡張\n{_price_line()}", [1, 2], release={"1": release} if release else {})
    assert row["status"] == "In Stock" and "status_basis" not in row


# --- 先の日付 --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("suffix", "posted", "expected"),
    [
        (" [10/14入荷]", _POSTED, "Pre-order"),
        (" 10/11入荷", _POSTED, "In Stock"),
        (" 10/5入荷", _POSTED, "In Stock"),
        (" 10月中旬発送予定", _POSTED, "Pre-order"),
        (" 10月中旬発送", date(2026, 10, 25), "In Stock"),
        (" 2月入荷分", _POSTED, "Pre-order"),
        (" 明日発送予定", _POSTED, "In Stock"),
        (" 移し替えて発送予定", _POSTED, "In Stock"),
        (" 2/30入荷", _POSTED, "In Stock"),
        (" 10月20日入荷", _POSTED, "Pre-order"),
    ],
)
def test_date_ahead(suffix, posted, expected):
    row = _run(f"サンプル拡張\n{_price_line(suffix)}", [1, 2], posted=posted)
    assert row["status"] == expected


@pytest.mark.parametrize(
    ("suffix", "posted", "expected"),
    [
        (" (10/11発送)", date(2026, 10, 10), "In Stock"),
        (" (10/12発送)", date(2026, 10, 10), "Pre-order"),
        (" 10月中旬発送", date(2026, 10, 19), "In Stock"),
        (" 10月中旬発送", date(2026, 10, 11), "Pre-order"),
        (" 9/30入荷", date(2026, 10, 11), "In Stock"),
        (" 9月入荷", date(2026, 10, 11), "In Stock"),
        (" 8月入荷", date(2026, 10, 11), "Pre-order"),
        (" 2月入荷分", date(2026, 10, 11), "Pre-order"),
        (" 6月入荷分", date(2026, 10, 11), "Pre-order"),
        (" 12/20入荷", date(2027, 1, 15), "In Stock"),
        (" 12月入荷", date(2027, 1, 15), "In Stock"),
        (" 11月入荷", date(2027, 1, 15), "Pre-order"),
        (" 10/5入荷", date(2026, 10, 11), "In Stock"),
    ],
)
def test_date_ahead_next_day_grace_and_past_month_rule(suffix, posted, expected):
    row = _run(f"サンプル拡張\n{_price_line(suffix)}", [1, 2], posted=posted)
    assert row["status"] == expected


def test_date_ahead_basis_is_matched_text():
    row = _run(f"サンプル拡張\n{_price_line(' [10/14入荷]')}", [1, 2])
    assert row["status_basis"] == "DATE_AHEAD:10/14入荷"


@pytest.mark.parametrize(
    ("suffix", "posted", "expected"),
    [
        (" 11/3～5入荷次第発送", date(2026, 10, 19), "Pre-order"),
        (" (10/16〜17入荷)", date(2026, 10, 15), "Pre-order"),
        (" (11/3〜6発送)", date(2026, 10, 18), "Pre-order"),
        (" 11/3～11/5入荷", date(2026, 10, 19), "Pre-order"),
        (" 10/14〜15入荷", date(2026, 10, 14), "In Stock"),  # 終わりの日が翌日猶予の内
        (" 10/5〜6入荷", date(2026, 10, 11), "In Stock"),  # 過ぎた日
        (" [10/14入荷]", date(2026, 10, 11), "Pre-order"),  # 範囲でない形は不変
        (" 10/30～11/2入荷", date(2026, 10, 19), "Pre-order"),  # 月またぎ
        (" 12/28-1/5発送", date(2026, 12, 20), "Pre-order"),  # 年またぎ
    ],
)
def test_date_ahead_range_reads_end_date(suffix, posted, expected):
    row = _run(f"サンプル拡張\n{_price_line(suffix)}", [1, 2], posted=posted)
    assert row["status"] == expected


def test_date_ahead_range_basis_is_matched_text():
    row = _run(f"サンプル拡張\n{_price_line(' 11/3～5入荷')}", [1, 2], posted=date(2026, 10, 19))
    assert row["status_basis"] == "DATE_AHEAD:11/3～5入荷"


def test_date_ahead_range_end_month_is_used_across_months():
    row = _run(f"サンプル拡張\n{_price_line(' 10/30～11/2入荷')}", [1, 2], posted=date(2026, 10, 19))
    assert row["status_basis"] == "DATE_AHEAD:10/30～11/2入荷"


def test_first_line_shipping_date_in_item_lines_is_pre_order():
    # 便1 の出力（1行目の「日付＋入荷次第発送」が最初の件の lines に入る形）を模す
    row = _run("11/3～5入荷次第発送\nサンプル拡張\n" + _price_line(), [1, 2, 3], posted=date(2026, 10, 19))
    assert (row["status"], row["status_basis"]) == ("Pre-order", "DATE_AHEAD:11/3～5入荷次第発送")


def test_year_rolls_over_only_when_month_is_before_posted_month():
    row = _run(f"サンプル拡張\n{_price_line(' 1月末入荷')}", [1, 2], posted=date(2026, 12, 20))
    assert row["status"] == "Pre-order"
    row = _run(f"サンプル拡張\n{_price_line(' 12月上旬入荷')}", [1, 2], posted=date(2026, 12, 20))
    assert row["status"] == "In Stock"


def test_no_posted_date_disables_date_rules_but_not_headings():
    assert _run(f"サンプル拡張\n{_price_line(' [10/14入荷]')}", [1, 2], posted=None)["status"] == "In Stock"
    assert _run(f"【予約商品】\nサンプル拡張\n{_price_line()}", [2, 3], posted=None)["status"] == "Pre-order"


# --- 見出し ----------------------------------------------------------------------------------


def test_item_below_pre_order_heading_is_pre_order():
    row = _run(f"【予約商品】\nサンプル拡張\n{_price_line()}", [2, 3])
    assert (row["status"], row["status_basis"]) == ("Pre-order", "HEADING:1")


def test_stock_heading_after_pre_order_heading_keeps_in_stock():
    row = _run(f"【予約商品】\n【ポケカ在庫商品】\nサンプル拡張\n{_price_line()}", [3, 4])
    assert row["status"] == "In Stock" and "status_basis" not in row


def test_excluded_heading_wording_does_not_count():
    row = _run(f"ご予約可能な商品\nサンプル拡張\n{_price_line()}", [2, 3])
    assert row["status"] == "In Stock"


def test_heading_inside_item_lines_is_not_used():
    row = _run(f"【予約商品】\nサンプル拡張\n{_price_line()}", [1, 2, 3])
    assert row["status"] == "In Stock"


def test_heading_owned_by_other_item_is_skipped():
    raw = f"【予約商品】\nサンプル拡張\n{_price_line()}\nサンプル拡張\n{_price_line()}"
    parsed, _ = v101.parse_v101_response(
        json.dumps({"items": [_it([1, 2, 3]), _it([4, 5])]}, ensure_ascii=False), raw, status_entries=_BASE + _CONTEXT
    )
    out, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=False, v102_fixes=True, gemini_trust=True, **_masters(_BASE + _CONTEXT)
    )
    assert [r["status"] for r in out] == ["In Stock", "In Stock"]


# --- 優先・不変 ------------------------------------------------------------------------------


def test_sold_out_is_never_changed():
    row = _run(f"【予約商品】\nサンプル拡張\n{_price_line(' 完売 10/14入荷')}", [2, 3], release={"1": date(2026, 10, 16)})
    assert row["status"] == "Sold out" and "status_basis" not in row


def test_existing_output_rule_is_never_changed():
    entries = [*_BASE, _row("Pre-order", "OUTPUT", "LITERAL", "予約受付", "", 5), *_CONTEXT]
    row = _run(f"【ポケカ在庫商品】\nサンプル拡張\n{_price_line(' 予約受付')}", [2, 3], entries=entries)
    assert row["status"] == "Pre-order" and "status_basis" not in row


def test_without_context_rows_nothing_changes():
    row = _run(f"【予約商品】\nサンプル拡張\n{_price_line(' [10/14入荷]')}", [2, 3], entries=_BASE, release={"1": date(2026, 10, 16)})
    assert row["status"] == "In Stock" and "status_basis" not in row


def test_non_v102_path_is_unchanged():
    raw = f"【予約商品】\nサンプル拡張\n{_price_line()}"
    parsed, _ = v101.parse_v101_response(json.dumps({"items": [_it([2, 3])]}, ensure_ascii=False), raw, status_entries=_BASE + _CONTEXT)
    out, _flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=False, cond_entries=[], cond_canonical_to_uuid={}, unit_alias_to_info=_UNITS,
        status_entries=_BASE + _CONTEXT,
    )
    assert out[0]["status"] == "In Stock" and "status_basis" not in out[0]


# --- 投稿日 ----------------------------------------------------------------------------------


def test_posted_date_is_jst_date():
    utc_late = datetime(2026, 10, 11, 16, 0, tzinfo=timezone.utc)  # JST では 10/12 01:00
    assert posted_jst_date(utc_late) == date(2026, 10, 12)
    assert posted_jst_date(datetime(2026, 10, 11, 9, 0)) == date(2026, 10, 11)  # タイムゾーン無しは JST
    assert posted_jst_date(None) is None
    assert posted_jst_date(datetime(2026, 10, 11, tzinfo=timezone(timedelta(hours=9)))) == date(2026, 10, 11)


# --- 既存の読み手は新しい行で挙動が変わらない（カード 0-1）--------------------------------------------


@pytest.mark.parametrize("text_val", ["予約商品 10/14入荷", "完売", "通常", "", "在庫 10月中旬発送"])
def test_existing_readers_ignore_context_rows(text_val):
    from app.services.tcg_analyzer_svc import resolve_status_v2

    assert resolve_status_v2(text_val, _BASE + _CONTEXT, raw_memo=text_val) == resolve_status_v2(text_val, _BASE, raw_memo=text_val)
    assert v101._is_sold_out(text_val, _BASE + _CONTEXT) == v101._is_sold_out(text_val, _BASE)


def test_sold_out_words_ignore_context_rows():
    assert v101._sold_out_words(_BASE + _CONTEXT) == v101._sold_out_words(_BASE) == ["完売"]
