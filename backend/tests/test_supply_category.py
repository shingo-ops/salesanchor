"""ADR-1035 追補：区分「サプライ系」（v102）。例文は作り文だけ。DB は使わない（migration 2回は PG 試験側）。

K1: サプライ系の商品で「100枚入 350円 在庫1,000」が 単位 Bag・状態 Supply・basis R10・数量 1000・価格 350 になる／
サプライ系でない商品の「100枚入」は Piece のまま／v6 の経路で supply の行が返らない。
数量・価格は resolve_product_first の戻り値には無いので、件を組み立てる層（extract_v101_items）で見る。
"""
from __future__ import annotations

import json
from pathlib import Path

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services import line_analysis_v102_svc as svc
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.tcg_analyzer_svc import SCOPED_VALUE_GROUPS, load_condition_entries
from app.services.tcg_result_order import VALUE_GROUP_ORDER

S = "サプライ系"
SINGLE = "シングル系"
ROOT = Path(__file__).resolve().parents[2]


def _row(code, canonical, rank, group, kubun, match_type="KEYWORD", search_kw="", priority=10):
    return {
        "cond_id": f"{900 + int(code[-2:])}", "code": code, "canonical": canonical, "priority": priority,
        "app_kubun": kubun, "search_kw": search_kw, "exclude_kw": "", "match_type": match_type,
        "effect": "OUTPUT", "value_group": group, "value_rank": rank,
    }


_SUPPLY = (_row("CN0025", "Supply", 1, "supply", S),)
_SINGLE = (_row("CN0026", "Single", 1, "single", SINGLE),)
_SCOPED = {"supply": _SUPPLY, "single": _SINGLE}


def _cond(code, canonical, priority, app_kubun, search_kw):
    return {
        "cond_id": str(int(code[-4:])), "code": code, "canonical": canonical, "priority": priority, "app_kubun": app_kubun,
        "search_kw": search_kw, "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
        "value_group": None, "value_rank": None,
    }


_COND = [_cond("CN0008", "FLAG_SINGLE", 1, "枚系,単位不明", "PSA,SR")]
_STATUS = [
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99,
     "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_PRODUCTS = (
    ProductEntry(id=7, product_code=None, mark=None, work_id=1, search_keywords=("作りスリーブ",), exclude_keywords=()),
    ProductEntry(id=8, product_code=None, mark=None, work_id=1, search_keywords=("作りカード",), exclude_keywords=()),
)
_UNITS = {"bag": ("Bag", "袋系"), "piece": ("Piece", "単品系"), "枚": ("Piece", "単品系"), "枚入": ("Piece", "単品系")}


def _masters():
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun={"7": S, "8": SINGLE}, condition_unit={"Supply": "Bag"},
        ignore_phrases=(), scoped_cond_entries=_SCOPED,
    )


def _one(name: str, *, price="350円", qty="1000"):
    raw = f"{name} 100枚入\n{qty}@{price}"
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": [{"lines": [1, 2], "price": price, "quantity": qty}]}, ensure_ascii=False),
        raw, status_entries=_STATUS,
    )
    assert errors == []
    (row,), _f = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=_masters(),
        cond_entries=_COND, cond_canonical_to_uuid={}, unit_alias_to_info=_UNITS, status_entries=_STATUS,
    )
    return row


def test_supply_kubun_gives_bag_supply_r10_with_qty_and_price():
    row = _one("作りスリーブ")
    assert row["unit"] == "Bag"
    assert (row["condition"], row["condition_basis"]) == ("Supply", "R10:サプライ既定")
    assert row["quantity_normalized"] == 1000 and row["price_normalized"] == 350
    assert row["unit_basis"].get("reason") == "supply_kubun" and row["unit_basis"].get("from_condition") == "Supply"


def test_non_supply_kubun_keeps_piece():
    row = _one("作りカード")
    assert row["unit"] == "Piece"
    assert row["condition"] != "Supply"


def test_basis_does_not_start_with_r4():
    assert not pf.BASIS_SUPPLY_DEFAULT.startswith("R4")
    assert pf.PRODUCT_KUBUN_SUPPLY not in pf.PRODUCT_KUBUNS_DEFAULTING_TO_BOX


# v6 の経路は supply の行を返さない
_DB_ROWS = [
    ("1", "CN0003", "Sealed box", 4, "箱系", "未開封", "", "KEYWORD", "OUTPUT", "box", 1),
    ("2", "CN0025", "Supply", 10, S, "", "", "KEYWORD", "OUTPUT", "supply", 1),
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


def test_default_call_hides_supply_group():
    assert "supply" in SCOPED_VALUE_GROUPS
    assert [e["code"] for e in load_condition_entries(_session(_DB_ROWS))] == ["CN0003"]
    got = load_condition_entries(_session(_DB_ROWS), include_scoped_groups=True)
    assert [e["code"] for e in got] == ["CN0003", "CN0025"]


def test_scoped_group_mapping_and_order():
    assert svc._SCOPED_GROUP_OF_KUBUN[S] == "supply"
    assert VALUE_GROUP_ORDER[-1] == "supply"


def test_migration_is_registered_after_booklet_and_guarded():
    sh = (ROOT / "scripts/run_all_migrations.sh").read_text()
    b = sh.index("20261020_100000_line_conditions_value_group_add_booklet.sql")
    s = sh.index("20261020_110000_line_conditions_value_group_add_supply.sql")
    assert b < s
    sql = (ROOT / "migrations/20261020_110000_line_conditions_value_group_add_supply.sql").read_text()
    assert "LIKE '%supply%'" in sql and "'booklet', 'supply'" in sql and "INSERT" not in sql.upper()
