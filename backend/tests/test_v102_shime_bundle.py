"""まとめて〆る投稿（価格 none の件どうしが同じ売り切れの行を持つ）の受け取り側の試験。

設計: docs/handoff/shime-bundle-close/design.md §3-2。商品・原文はすべて架空。
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from app.services import gemini_raw_copy_v101 as v101
from app.services import line_analysis_v102_svc as svc
from app.services.line_analysis_v102_svc import Decisions

_UNITS = {
    "BOX": ("BOX", "箱系"), "box": ("BOX", "箱系"), "ボックス": ("BOX", "箱系"),
    "セット": ("セット", "セット系"), "枚": ("枚", "単品系"),
}
# 売り切れの言葉の表（架空。「完売」「〆」を売り切れとして扱う）
_STATUS = [
    {"canonical": "sold_out", "search_pattern": "完売", "exclude_pattern": "", "priority": 1,
     "match_type": "LITERAL", "effect": "EXCLUDE"},
    {"canonical": "sold_out", "search_pattern": "〆", "exclude_pattern": "", "priority": 2,
     "match_type": "LITERAL", "effect": "EXCLUDE"},
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99,
     "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_MASTERS = {
    "cond_entries": [], "cond_canonical_to_uuid": {}, "unit_alias_to_info": _UNITS, "status_entries": _STATUS,
}
_DUP = v101.REJECTED_DUPLICATE


def _it(lines, price="none", quantity="none"):
    return {"lines": list(lines), "price": price, "quantity": quantity}


def _resp(*items):
    return json.dumps({"items": list(items)}, ensure_ascii=False)


def _parse(raw, *items, keep=True):
    return v101.parse_v101_response(_resp(*items), raw, status_entries=_STATUS, keep_rejected=keep)


def _accepted(out):
    return [it for it in out if "rejected" not in it]


def _rejected(out):
    return [it for it in out if "rejected" in it]


def _extract_keep(raw, *items):
    parsed, errors = _parse(raw, *items)
    out, flags = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=None,
        review_reasons=True, gemini_trust=False, **_MASTERS,
    )
    return out, flags, errors


_RAW3 = "型番AA-01\n型番BB-02\n〆"


def test_t1_two_none_items_share_the_shime_line():
    out, errors = _parse(_RAW3, _it([1, 3]), _it([2, 3]))
    assert len(_accepted(out)) == 2 and _rejected(out) == [] and errors == []
    assert [it["price_line"] for it in _accepted(out)] == [3, 3]


def test_t2_both_items_become_sold_out_through_extraction():
    out, _flags, errors = _extract_keep(_RAW3, _it([1, 3]), _it([2, 3]))
    assert errors == []
    assert [r["status"] for r in out] == ["sold_out", "sold_out"]
    assert [r["name"] for r in out] == ["型番AA-01", "型番BB-02"]


def test_t3_priced_items_sharing_a_line_are_still_rejected():
    raw = "型番AA-01\n型番BB-02\n1,000円"
    out, errors = _parse(raw, _it([1, 3], "1,000円", "1"), _it([2, 3], "1,000円", "1"))
    assert len(_accepted(out)) == 1 and len(errors) == 1
    assert [r["rejected"] for r in _rejected(out)] == [_DUP]
    # 価格 none の件と混ぜても変わらない
    out2, errors2 = _parse(raw, _it([1, 3], "1,000円", "1"), _it([2, 3]))
    assert [r["rejected"] for r in _rejected(out2)] == [_DUP] and len(errors2) == 1


def test_t4_shared_line_that_is_not_sold_out_is_rejected():
    raw = "型番AA-01\n型番BB-02\n残り2"
    out, errors = _parse(raw, _it([1, 3]), _it([2, 3]))
    assert len(_accepted(out)) == 1 and len(errors) == 1
    assert [r["rejected"] for r in _rejected(out)] == [_DUP]


def test_t5_second_item_without_its_own_name_line_is_rejected():
    out, errors = _parse(_RAW3, _it([1, 3]), _it([1, 3]))
    assert len(_accepted(out)) == 1 and len(errors) == 1
    assert [r["rejected"] for r in _rejected(out)] == [_DUP]


def test_t6_v101_path_still_rejects():
    out, errors = _parse(_RAW3, _it([1, 3]), _it([2, 3]), keep=False)
    assert len(out) == 1 and len(errors) == 1


def test_t7_dictionaries_keep_the_first_item_for_a_shared_line():
    out, flags, _errors = _extract_keep(_RAW3, _it([1, 3]), _it([2, 3]))
    assert len(out) == 2 and flags is not None
    # 〆の行から作る名前（owners）は先の件を返す
    items = _accepted(_parse(_RAW3, _it([1, 3]), _it([2, 3]))[0])
    owners: dict = {}
    for it in items:
        owners.setdefault(it["price_line"], it)
    assert owners[3] is items[0]
    # by_price_line も先の件の位置を残す（迷う行の付け直しの経路が落ちないこと）
    assert out[0]["name"] == "型番AA-01"


def test_t8_three_items_the_third_overlapping_is_rejected():
    raw = "型番AA-01\n型番BB-02\n型番CC-03\n〆"
    out, _ = _parse(raw, _it([1, 4]), _it([2, 4]), _it([2, 4]))
    assert len(_accepted(out)) == 2
    assert [r["rejected"] for r in _rejected(out)] == [_DUP]
    out2, errors2 = _parse(raw, _it([1, 4]), _it([2, 4]), _it([3, 4]))
    assert len(_accepted(out2)) == 3 and _rejected(out2) == [] and errors2 == []


def test_t9_blank_or_symbol_only_own_line_is_rejected():
    for middle in ("", "＝＝＝", "【〇〇】"):
        raw = f"型番AA-01\n{middle}\n〆"
        out, _ = _parse(raw, _it([1, 3]), _it([2, 3]))
        assert len(_accepted(out)) == 1, middle
        assert [r["rejected"] for r in _rejected(out)] == [_DUP], middle


def test_t10_rebuild_path_keeps_both_items():
    rows = [SimpleNamespace(id=uuid4(), gemini_index=0), SimpleNamespace(id=uuid4(), gemini_index=1)]
    ctx = SimpleNamespace(raw_text=_RAW3, supplier_context=None)
    decisions = {str(rows[0].id): Decisions(product_id=11), str(rows[1].id): Decisions(product_id=12)}
    result = svc._fixed_products(_resp(_it([1, 3]), _it([2, 3])), ctx, {"status_entries": _STATUS}, rows, decisions)
    # 2件とも rejected にならず残る（位置 0・1 の両方に商品が付く）。T10 は残ることだけ確かめる
    assert result == {0: 11, 1: 12}


def test_t11_single_item_with_supplement_line_stays_one():
    raw = "サンプルBOX\n未開封\n完売"
    out, errors = _parse(raw, _it([1, 2, 3]))
    assert len(_accepted(out)) == 1 and _rejected(out) == [] and errors == []


def test_t12_second_item_overlapping_beyond_the_price_line_is_rejected():
    out, errors = _parse(_RAW3, _it([2, 3]), _it([1, 2, 3]))
    assert len(_accepted(out)) == 1 and len(errors) == 1
    assert [r["rejected"] for r in _rejected(out)] == [_DUP]
