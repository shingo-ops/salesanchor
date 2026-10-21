"""ADR-1035：区分「ブックレット系」（v102）。例文は作り文だけ。DB は使わない。"""
from __future__ import annotations

import json

import pytest

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services import line_analysis_v102_svc as svc
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.tcg_analyzer_svc import SCOPED_VALUE_GROUPS, load_condition_entries
from app.services.tcg_result_order import VALUE_GROUP_ORDER

B = "ブックレット系"
_WITHOUT = r"(?i)((ブックレット|冊子)[\s　]*(無し|なし|抜き|欠品|欠け)|(?<![a-z])(no|without)[\s　]+booklet)"


def _row(code, canonical, rank, match_type="REGEX", search_kw="", priority=2):
    return {
        "cond_id": f"{900 + int(code[-2:])}", "code": code, "canonical": canonical, "priority": priority,
        "app_kubun": B, "search_kw": search_kw, "exclude_kw": "", "match_type": match_type,
        "effect": "OUTPUT", "value_group": "booklet", "value_rank": rank,
    }


_BOOKLET = (
    _row("CN0023", "With booklet", 1, match_type="KEYWORD", priority=10),
    _row("CN0024", "Without booklet", 2, search_kw=_WITHOUT),
)
_SCOPED = {"booklet": _BOOKLET}


def _cond(code, canonical, priority, app_kubun, search_kw):
    return {
        "cond_id": str(int(code[-4:])), "code": code, "canonical": canonical, "priority": priority, "app_kubun": app_kubun,
        "search_kw": search_kw, "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
        "value_group": None, "value_rank": None,
    }


_COND = [
    _cond("CN0008", "FLAG_SINGLE", 1, "枚系,単位不明", "PSA,SR"),
    _cond("CN0004", "Damaged sealed box", 2, "箱系", "難あり"),
    _cond("CN0003", "Sealed box", 4, "箱系", "シュリンク付き"),
]
_STATUS = [
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99,
     "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_PRODUCTS = (
    ProductEntry(id=7, product_code=None, mark=None, work_id=1, search_keywords=("作り冊子",), exclude_keywords=()),
)
_UNITS = {"Box": ("Box", "箱系"), "piece": ("Piece", "単品系")}


def _masters(scoped=_SCOPED):
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun={"7": B}, condition_unit={}, ignore_phrases=(),
        scoped_cond_entries=scoped,
    )


def _one(text: str, scoped=_SCOPED):
    raw = f"{text}\n3@500円"
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": [{"lines": [1, 2], "price": "500円", "quantity": "3"}]}, ensure_ascii=False),
        raw, status_entries=_STATUS,
    )
    assert errors == []
    (row,), _f = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=_masters(scoped),
        cond_entries=_COND, cond_canonical_to_uuid={}, unit_alias_to_info=_UNITS, status_entries=_STATUS,
    )
    return row


def _bk(word: str, scoped=_SCOPED):
    return _one(f"作り冊子 {word}".strip(), scoped)


# 1. 語が無ければ With booklet / R9 / 要確認なし
def test_default_is_with_booklet_r9():
    row = _bk("")
    assert (row["condition"], row["condition_basis"]) == ("With booklet", "R9:ブックレット既定")
    assert not row["condition_basis"].startswith("R4")
    assert row["review"] == []


# 2. 無しの語
@pytest.mark.parametrize("word", ["ブックレット無し", "冊子なし", "冊子 抜き", "No booklet", "without booklet"])
def test_without_words_give_without_booklet(word):
    assert _bk(word)["condition"] == "Without booklet"


# 3. 誤爆しない
@pytest.mark.parametrize("word", ["送料無料", "無地スリーブ", "casino booklet", "Mono booklet", "booklet付き"])
def test_lookalike_words_stay_with_booklet(word):
    assert _bk(word)["condition"] == "With booklet"


# 4. 群の行が masters に無いときは今と同じ道（ブックレット系の商品でも scoped を使わない）
def test_without_scoped_rows_uses_old_path():
    row = _bk("", scoped={})
    assert row["condition"] not in ("With booklet", "Without booklet")
    assert row["condition_basis"] != "R9:ブックレット既定"


# 5. v6 の経路は booklet の行を返さない
_DB_ROWS = [
    ("1", "CN0003", "Sealed box", 4, "箱系", "未開封", "", "KEYWORD", "OUTPUT", "box", 1),
    ("2", "CN0023", "With booklet", 10, B, "", "", "KEYWORD", "OUTPUT", "booklet", 1),
    ("3", "CN0024", "Without booklet", 2, B, _WITHOUT, "", "REGEX", "OUTPUT", "booklet", 2),
]


def _session(rows):
    from unittest.mock import MagicMock

    info = MagicMock()
    info.first.return_value = (1,)
    main = MagicMock()
    main.fetchall.return_value = rows
    session = MagicMock()
    session.execute.side_effect = [info, main]
    return session


def test_default_call_hides_booklet_group():
    assert "booklet" in SCOPED_VALUE_GROUPS
    assert [e["code"] for e in load_condition_entries(_session(_DB_ROWS))] == ["CN0003"]


def test_opt_in_returns_booklet_group():
    got = load_condition_entries(_session(_DB_ROWS), include_scoped_groups=True)
    assert [e["code"] for e in got] == ["CN0003", "CN0023", "CN0024"]


def test_other_kubun_hits_ignores_booklet_rows():
    assert pf._other_kubun_hits("ブックレット無し", "箱系", [*_COND, *_BOOKLET]) == []


# 条件 id は群の中で引く
def test_condition_id_is_taken_inside_the_group():
    masters = {"cond_entries": _COND, "cond_canonical_to_uuid": {}, "product_first": _masters()}
    assert svc._condition_columns("With booklet", masters, B) == ("With booklet", 923, True)
    assert svc._condition_columns("Without booklet", masters, B) == ("Without booklet", 924, True)


# 6. 並びの群は booklet の次が supply（ADR-1035 追補で supply を末尾に足した）
def test_value_group_order_ends_with_booklet():
    assert VALUE_GROUP_ORDER[-2:] == ("booklet", "supply")
    assert VALUE_GROUP_ORDER == ("case", "box", "pack", "promo_pack", "single", "booklet", "supply")


def test_booklet_scoped_group_mapping():
    assert svc._SCOPED_GROUP_OF_KUBUN[B] == "booklet"
