"""v102：状態の見出しを下の品目に使う（ADR-1041 What 5）。DB・Gemini は使わない。例文はすべて架空の文。

設計: docs/handoff/v102-heading-and-unit/design-heading.md / card-H.md
"""
from __future__ import annotations

import json
import logging
import re
from decimal import Decimal

import pytest

from app.services import gemini_raw_copy_v101 as v101
from app.services import line_analysis_v102_svc as svc
from app.services import v102_buyback_unit_svc as bb
from app.services.gemini_raw_copy_v102_context_work import MATCH_STATUS_MATCHED
from app.services.gemini_raw_copy_v102_product_first import (
    ConditionHeadingRule,
    ProductFirstMasters,
    validate_condition_heading,
)
from app.services.gemini_raw_copy_v102_soldout_ref import (
    SoldoutTarget,
    _is_inherit_candidate,
    _narrow_by_condition,
    condition_decided_by_word,
)
from app.services.v102_status_context import StatusContext
from app.tools import v102_replay_diff as rd

_SETTING = {
    "max_lines": 3,
    "sentence_end": ["。", "ます", "ません", "ございます", "おります", "です", "下さい", "ください"],
    "trailing_chars": "!！。",
}
_REFERENCE_RE = re.compile(r"(。|ます|ません|ございます|おります|です|下さい|ください)[!！。\s]*$")


def _rule(**over) -> ConditionHeadingRule:
    rule = validate_condition_heading(json.dumps({**_SETTING, **over}, ensure_ascii=False))
    assert rule is not None
    return rule


# ---------------------------------------------------------------------------
# 設定の検査
# ---------------------------------------------------------------------------


def test_missing_key_is_none_without_warning_or_info(caplog):
    with caplog.at_level(logging.DEBUG):
        assert validate_condition_heading(None) is None
    assert [r for r in caplog.records if r.levelno >= logging.INFO] == []


def test_empty_object_is_none_without_any_log(caplog):
    with caplog.at_level(logging.DEBUG):
        assert validate_condition_heading("{}") is None
    assert caplog.records == []


@pytest.mark.parametrize(
    "raw",
    [
        "{not json",
        json.dumps({**_SETTING, "max_lines": True}),
        json.dumps({**_SETTING, "max_lines": 0}),
        json.dumps({**_SETTING, "max_lines": 6}),
        json.dumps({**_SETTING, "max_lines": "3"}),
        json.dumps({**_SETTING, "sentence_end": []}),
        json.dumps({**_SETTING, "sentence_end": [""]}),
        json.dumps({**_SETTING, "sentence_end": "。"}),
        json.dumps({**_SETTING, "trailing_chars": 1}),
        json.dumps({**_SETTING, "extra": 1}),
        json.dumps({"max_lines": 3, "sentence_end": ["。"]}),
        json.dumps([1, 2]),
    ],
)
def test_bad_values_return_none_and_warn(raw, caplog):
    with caplog.at_level(logging.WARNING):
        assert validate_condition_heading(raw) is None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert warnings[0].getMessage().startswith("[condition_heading]")


def test_valid_value_returns_rule_and_allows_empty_trailing_chars(caplog):
    with caplog.at_level(logging.DEBUG):
        rule = validate_condition_heading(json.dumps(_SETTING, ensure_ascii=False))
        empty_trailing = validate_condition_heading(json.dumps({**_SETTING, "trailing_chars": ""}, ensure_ascii=False))
    assert rule is not None and rule.max_lines == 3
    assert empty_trailing is not None
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


@pytest.mark.parametrize(
    "line", ["在庫ございます！", "よろしくお願い致します。", "未開封です!", "。", "未サーチ品", "傷あり", "各10パック単位", "ご確認下さい 　"]
)
def test_setting_regex_matches_reference_regex(line):
    assert bool(_rule().sentence_end_re.search(line)) == bool(_REFERENCE_RE.search(line))


# ---------------------------------------------------------------------------
# _heading_block
# ---------------------------------------------------------------------------


def test_block_under_heading_with_blank_line():
    lines = ["未サーチ品", "", "商品A@100円"]
    assert v101._heading_block(lines, 3, {3}, _rule()) == ("未サーチ品", 1)


def test_block_stops_at_blank_line():
    lines = ["前の品@100円", "", "見出し", "商品@200円"]
    assert v101._heading_block(lines, 4, {1, 4}, _rule()) == ("見出し", 3)


def test_block_stops_at_item_line_returns_none():
    lines = ["前の品@100円", "言い分けの行", "商品@200円"]
    assert v101._heading_block(lines, 3, {1, 3}, _rule()) is None


def test_block_stops_at_start_of_post():
    assert v101._heading_block(["見出し", "商品@100円"], 2, {2}, _rule()) == ("見出し", 1)


def test_block_no_line_collected_returns_none():
    assert v101._heading_block(["商品@100円"], 1, {1}, _rule()) is None
    assert v101._heading_block(["", "商品@100円"], 2, {2}, _rule()) is None


def test_block_max_lines_then_next_is_item_line_returns_none():
    lines = ["前の品@100円", "一", "二", "三", "商品@200円"]
    assert v101._heading_block(lines, 5, {1, 5}, _rule()) is None


def test_block_max_lines_then_next_is_plain_line_goes_on():
    lines = ["別の行", "一", "二", "三", "商品@200円"]
    assert v101._heading_block(lines, 5, {5}, _rule()) == ("一\n二\n三", 2)


def test_block_skips_items_and_blank_lines_above_the_first_line():
    lines = ["見出し", "", "前の品@100円", "", "商品@200円"]
    # 前の品（3 行目）は件の行なので飛ばし、1 行目に届く。1 行目は件でない行で、その上は先頭
    assert v101._heading_block(lines, 5, {3, 5}, _rule()) == ("見出し", 1)


def test_block_price_shaped_line_returns_none():
    lines = ["傷あり", "落とした件@100円", "商品@200円"]
    assert v101._heading_block(lines, 3, {3}, _rule()) is None


def test_block_drops_sentence_ending_lines():
    lines = ["在庫ございます！", "未サーチ品", "商品@200円"]
    assert v101._heading_block(lines, 3, {3}, _rule()) == ("未サーチ品", 2)
    assert v101._heading_block(["よろしくお願いします。", "商品@200円"], 2, {2}, _rule()) is None
    assert v101._heading_block(["未開封です!", "商品@200円"], 2, {2}, _rule()) is None
    assert v101._heading_block(["。", "商品@200円"], 2, {2}, _rule()) is None


def test_block_emoji_ending_sentence_is_not_dropped_known_limit():
    lines = ["在庫ありますよ😀", "商品@200円"]
    assert v101._heading_block(lines, 2, {2}, _rule()) == ("在庫ありますよ😀", 1)


def test_block_fullwidth_space_only_line_counts_as_blank():
    lines = ["見出し", "　", "商品@200円"]
    assert v101._heading_block(lines, 3, {3}, _rule()) == ("見出し", 1)


def test_block_number_and_unit_only_line_is_taken():
    lines = ["未サーチ品", "各10パック単位", "商品@200円"]
    assert v101._heading_block(lines, 3, {3}, _rule()) == ("未サーチ品\n各10パック単位", 1)


# ---------------------------------------------------------------------------
# _heading_condition
# ---------------------------------------------------------------------------

_ENTRIES = [
    {"canonical": "Unsearched pack", "value_group": "pack"},
    {"canonical": "Searched pack", "value_group": "pack"},
    {"canonical": "Damaged box", "value_group": "box"},
    {"canonical": "Sealed box", "value_group": "box"},
    {"canonical": "Loose", "value_group": None},
]
_LINES = ["未サーチ品", "", "商品@100円"]


def _ctx(rule, entries=None):
    masters = ProductFirstMasters(
        product_entries=(), product_kubun={}, condition_unit={}, ignore_phrases=(), condition_heading=rule,
    )
    return v101.V101Context(
        cond_entries=list(_ENTRIES if entries is None else entries), cond_canonical_to_uuid={}, unit_alias_to_info={},
        status_entries=[], order=None, aliases=[], state_words=[], sold_out_words=[], product_first=masters,
    )


def _pf(basis="R5:パック既定", condition="Searched pack"):
    return {"condition_basis": basis, "condition": condition, "product_category": "分類", "unit_kubun": "区分"}


_STATUS_CTX = StatusContext(None, {}, frozenset({3}))


def _fake_resolver(monkeypatch, result):
    monkeypatch.setattr(v101, "_resolve_condition", lambda *_a, **_k: result)


def _call(pf=None, ctx=None, status_context=_STATUS_CTX, lines=None):
    return v101._heading_condition({"lines": [3]}, lines or _LINES, pf if pf is not None else _pf(), ctx or _ctx(_rule()), status_context)


def test_heading_condition_replaces_with_marker(monkeypatch):
    _fake_resolver(monkeypatch, ("Unsearched pack", "R3:未サーチ", []))
    assert _call() == ("Unsearched pack", "R3:未サーチ@見出し:L1")


def test_heading_condition_accepts_product_kubun_default_prefix(monkeypatch):
    _fake_resolver(monkeypatch, ("Unsearched pack", "R4c:商品分類既定>R2:未サーチ", []))
    assert _call() == ("Unsearched pack", "R4c:商品分類既定>R2:未サーチ@見出し:L1")


def test_heading_condition_rule_none_is_none(monkeypatch):
    _fake_resolver(monkeypatch, ("Unsearched pack", "R3:未サーチ", []))
    assert _call(ctx=_ctx(None)) is None


def test_heading_condition_missing_inputs_are_none(monkeypatch):
    _fake_resolver(monkeypatch, ("Unsearched pack", "R3:未サーチ", []))
    assert v101._heading_condition({"lines": [3]}, _LINES, None, _ctx(_rule()), _STATUS_CTX) is None
    assert _call(status_context=None) is None
    no_pf = v101.V101Context([], {}, {}, [], None, [], [], [], None)
    assert v101._heading_condition({"lines": [3]}, _LINES, _pf(), no_pf, _STATUS_CTX) is None


@pytest.mark.parametrize("basis", ["R3:未サーチ", "R4:単位既定:単位不明", "R4:語", "SOLDOUT_INHERIT", "R4:単位既定>末尾が違う"])
def test_heading_condition_skips_items_not_decided_by_default(monkeypatch, basis):
    _fake_resolver(monkeypatch, ("Unsearched pack", "R3:未サーチ", []))
    assert _call(pf=_pf(basis=basis)) is None


def test_heading_condition_default_unit_basis_is_taken(monkeypatch):
    _fake_resolver(monkeypatch, ("Damaged box", "R2:傷あり", []))
    got = _call(pf=_pf(basis="R4:単位既定", condition="Sealed box"))
    assert got == ("Damaged box", "R2:傷あり@見出し:L1")


def test_heading_condition_other_group_is_none(monkeypatch):
    _fake_resolver(monkeypatch, ("Damaged box", "R2:傷あり", []))
    assert _call() is None  # 今の状態はパックの群、新しい状態は箱の群


def test_heading_condition_flag_note_is_none(monkeypatch):
    _fake_resolver(monkeypatch, ("Unsearched pack", "単品語あり・要確認(x),R3:未サーチ", []))
    assert _call() is None


@pytest.mark.parametrize("hb", ["R1:語", "R4:語", "R4:単位既定", "R5:パック既定", "EMPTY_BOX:explicit"])
def test_heading_condition_only_r2_r3_are_taken(monkeypatch, hb):
    _fake_resolver(monkeypatch, ("Unsearched pack", hb, []))
    assert _call() is None


def test_heading_condition_group_column_none_is_none(monkeypatch):
    _fake_resolver(monkeypatch, ("Loose", "R3:語", []))
    assert _call(pf=_pf(condition="Loose")) is None
    _fake_resolver(monkeypatch, ("Unsearched pack", "R3:未サーチ", []))
    assert _call(ctx=_ctx(_rule(), entries=[{"canonical": "Unsearched pack"}, {"canonical": "Searched pack"}])) is None


def test_heading_condition_no_resolved_condition_is_none(monkeypatch):
    _fake_resolver(monkeypatch, (None, "R4:単位既定", []))
    assert _call() is None


def test_marker_survives_cut_to_100_chars():
    basis = ("R3:未サーチ@見出し:L12" + "x" * 100)[:100]
    assert condition_decided_by_word(basis)


# ---------------------------------------------------------------------------
# K0: 設定が無いとき（condition_heading=None）は全部の形で何もしない
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "basis", ["R5:パック既定", "R4:単位既定", "R4c:商品分類既定>R4:単位既定", "R3:語", "R4:単位既定:単位不明", "SOLDOUT_INHERIT"]
)
@pytest.mark.parametrize("status_context", [_STATUS_CTX, None])
def test_k0_without_setting_never_changes_anything(monkeypatch, basis, status_context):
    _fake_resolver(monkeypatch, ("Unsearched pack", "R3:未サーチ", []))
    ctx = _ctx(None)
    assert ctx.product_first.condition_heading is None
    assert v101._heading_condition({"lines": [3]}, _LINES, _pf(basis=basis), ctx, status_context) is None


# ---------------------------------------------------------------------------
# K5: 見出しで決めた件は、同じ語を件の行に書いた件と、値段からの推定・売り切れの適用の結果が同じ
# ---------------------------------------------------------------------------

_MARK_RE = re.compile(r"@見出し:L\d+")
_GROUPS = ("box", "case", "pack")
_UNIT_OF = {"box": "Box", "case": "Case", "pack": "Pack"}
_CONDITION_ID = {7: 101, 3: 102, 4: 103}


def _cmap() -> bb.ConditionMap:
    targets = {}
    for g in _GROUPS:
        kinds = {bb._KIND_DEFAULT: bb.Target(1, f"{g}-default", _UNIT_OF[g])}
        for label in (3, 4):
            kinds[label] = bb.Target(10 + label, f"{g}-{label}", _UNIT_OF[g])
        targets[g] = kinds
    return bb.ConditionMap(targets=targets, label_by_condition_id={v: k for k, v in _CONDITION_ID.items()}, label_by_code={})


def _k5_item(basis):
    return {
        "product_category": "箱系", "condition_basis": basis, "unit_basis": {"alias": None}, "review": [],
        "status_effect": "output", "status": "active",
    }


def _k5_values(basis, label, price):
    return {
        "pid_resolved": True, "product_id": 1, "price_normalized": price, "bundle_size": None, "condition_basis": basis,
        "condition_id": _CONDITION_ID[label], "condition_canonical": f"c{label}", "unit_canonical": "Unit", "unit_id": 9,
        "review_reasons": None, "needs_review": False, "unit_resolved": True,
    }


def _k5_price_step(basis, label, price):
    settings = bb.BuybackSettings(Decimal("1.5"), Decimal("3"), Decimal("5"), 30, pack_max=Decimal("0.5"))
    item, values = _k5_item(basis), _k5_values(basis, label, price)
    candidate = bb.is_candidate(item, values, {})
    decided = bb.decide_code(Decimal(str(price)), Decimal("1000"), settings)
    cmap = _cmap()
    kind = bb.decide_kind(item, values, cmap)
    out = None
    if decided is not None and kind is not None:
        unit, ratio = decided
        target = cmap.targets[bb._UNIT_GROUP[unit]].get(kind)
        if target is not None:
            out = bb.with_decision(values, target, ratio, {"Box": 1, "Case": 2, "Pack": 3}, condition_decided_by_word(basis))
    return candidate, kind, out


@pytest.mark.parametrize("label", [7, 3, 4])
@pytest.mark.parametrize("price", [400, 2000, 6000, 1000])  # パック／箱／ケース／どれでもない
def test_k5_heading_marker_gives_same_price_decision_as_word_in_item_line(label, price):
    marked = _k5_price_step("R3:未サーチ@見出し:L12", label, price)
    plain = _k5_price_step("R3:未サーチ", label, price)
    assert marked[0] == plain[0] and marked[1] == plain[1]
    if plain[2] is None:
        assert marked[2] is None
        return
    assert marked[2] is not None
    for key in ("condition_canonical", "unit_canonical", "unit_id", "condition_id"):
        assert marked[2][key] == plain[2][key]
    assert _MARK_RE.sub("", marked[2]["condition_basis"]) == plain[2]["condition_basis"]
    assert marked[2]["condition_basis"].startswith("R3:未サーチ")


@pytest.mark.parametrize("canonical", ["Unsearched pack", "Searched pack"])
def test_k5_heading_marker_gives_same_soldout_decision_as_word_in_item_line(canonical):
    targets = (
        SoldoutTarget(1, 11, "m1", 2, "Unsearched pack", 5, "Pack"),
        SoldoutTarget(1, 12, "m1", 3, "Searched pack", 5, "Pack"),
    )
    for plural in (False, True):
        marked = _narrow_by_condition(targets, {"condition_basis": "R3:未サーチ@見出し:L12", "condition": canonical}, plural)
        plain = _narrow_by_condition(targets, {"condition_basis": "R3:未サーチ", "condition": canonical}, plural)
        assert marked == plain
    sold = {
        "status_effect": "excluded", "status": "Sold out", "match_status": MATCH_STATUS_MATCHED, "product_id": 1,
        "unit_basis": {"alias": None},
    }
    marked_inherit = _is_inherit_candidate({**sold, "condition_basis": "R3:未サーチ@見出し:L12"}, 0, None)
    plain_inherit = _is_inherit_candidate({**sold, "condition_basis": "R3:未サーチ"}, 0, None)
    assert marked_inherit == plain_inherit


# ---------------------------------------------------------------------------
# 台本 v102_replay_diff
# ---------------------------------------------------------------------------


def test_replay_tool_makes_gemini_call_raise(monkeypatch):
    monkeypatch.setattr(svc, "_call_gemini", svc._call_gemini)  # 後で元に戻すための登録
    rd.disable_gemini()
    with pytest.raises(RuntimeError):
        svc._call_gemini(None, None, "prompt", "job", None)


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _row(post, index, **over):
    base = {
        "post_id": post, "index": index, "lines": [index + 1], "product": 1, "unit": "Pack", "unit_kubun": "x",
        "condition": "Searched pack", "condition_basis": "R5:パック既定", "price": 100, "quantity": 1, "status": "active",
        "soldout_targets": None, "soldout_target_basis": None,
    }
    return {**base, **over}


def test_diff_tool_counts_columns_and_lists_changed_conditions(tmp_path):
    before, after = tmp_path / "before.jsonl", tmp_path / "after.jsonl"
    _write_jsonl(before, [_row("p1", 0), _row("p1", 1), _row("p2", 0), _row("p3", 0)])
    _write_jsonl(after, [
        _row("p1", 0),
        _row("p1", 1, condition="Unsearched pack", condition_basis="R3:未サーチ@見出し:L1"),
        _row("p2", 0, unit="Box"),
        _row("p4", 0),
    ])
    out_dir = tmp_path / "out"
    result = rd.diff_files(before, after, out_dir)
    assert result["compared"] == 3 and result["changed"] == 1
    summary = {
        k: int(v) for k, v in (ln.split("\t") for ln in (out_dir / "summary.tsv").read_text(encoding="utf-8").splitlines()[1:])
    }
    assert summary["condition"] == 1 and summary["condition_basis"] == 1 and summary["unit"] == 1
    assert summary["price"] == 0 and summary["only_before"] == 1 and summary["only_after"] == 1
    changed = (out_dir / "changed.tsv").read_text(encoding="utf-8").splitlines()
    assert len(changed) == 2
    assert changed[1].split("\t")[:2] == ["p1", "1"]
    assert "Unsearched pack" in changed[1] and "R3:未サーチ@見出し:L1" in changed[1]
