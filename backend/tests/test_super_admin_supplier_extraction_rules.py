"""仕入元ルール API：新しい仕組み専用の2列（extraction_layout_rules / extraction_hard_cases）。

DB を使わず、ルーターの関数を差し替えた AsyncSession で直接呼ぶ（手元でも動く）。
確かめること：読み出しで2列が返る、更新で2列が UPDATE に入り返る、スキーマの上限。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers import super_admin_suppliers as router
from app.schemas.central_masters import (
    SupplierExtractionRulesResponse,
    SupplierExtractionRulesUpdate,
)

_ALL_COLS = (
    "extraction_price_format", "extraction_qty_format", "extraction_order_pattern",
    "extraction_default_unit", "extraction_notes", "extraction_state_format",
    "extraction_example_text", "extraction_ship_format",
    "extraction_layout_rules", "extraction_hard_cases",
)


def _row(**over):
    return {"id": 5, **{c: None for c in _ALL_COLS}, **over}


def _result(first):
    res = MagicMock()
    res.mappings.return_value.first.return_value = first
    return res


def _db(*results):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_get_returns_new_system_columns():
    db = _db(_result(_row(extraction_layout_rules="L", extraction_hard_cases="H")), _result(None))
    resp = await router.get_supplier_extraction_rules(5, db)
    assert resp.extraction_layout_rules == "L"
    assert resp.extraction_hard_cases == "H"
    sql = str(db.execute.call_args_list[0].args[0])
    assert "extraction_layout_rules" in sql and "extraction_hard_cases" in sql


@pytest.mark.asyncio
async def test_get_returns_none_for_new_columns_when_unset():
    db = _db(_result(_row()), _result(None))
    resp = await router.get_supplier_extraction_rules(5, db)
    assert resp.extraction_layout_rules is None
    assert resp.extraction_hard_cases is None


@pytest.mark.asyncio
async def test_patch_saves_new_system_columns_and_returns_them():
    db = _db(_result(_row(extraction_layout_rules="L2", extraction_hard_cases="H2")))
    data = SupplierExtractionRulesUpdate(extraction_layout_rules="L2", extraction_hard_cases="H2")
    resp = await router.update_supplier_extraction_rules(5, data, db)
    sql = str(db.execute.call_args.args[0])
    params = db.execute.call_args.args[1]
    assert "extraction_layout_rules = :extraction_layout_rules" in sql
    assert "extraction_hard_cases = :extraction_hard_cases" in sql
    assert params["extraction_layout_rules"] == "L2" and params["extraction_hard_cases"] == "H2"
    assert resp.extraction_layout_rules == "L2" and resp.extraction_hard_cases == "H2"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_patch_only_one_new_column_leaves_others_out_of_update():
    db = _db(_result(_row(extraction_hard_cases="H")))
    data = SupplierExtractionRulesUpdate(extraction_hard_cases="H")
    await router.update_supplier_extraction_rules(5, data, db)
    sql = str(db.execute.call_args.args[0])
    assert "extraction_hard_cases = :extraction_hard_cases" in sql
    assert "extraction_layout_rules = :" not in sql


@pytest.mark.asyncio
async def test_patch_unknown_supplier_is_404():
    db = _db(_result(None))
    data = SupplierExtractionRulesUpdate(extraction_layout_rules="L")
    with pytest.raises(HTTPException) as exc:
        await router.update_supplier_extraction_rules(999, data, db)
    assert exc.value.status_code == 404


def test_new_columns_are_updatable_and_selected():
    for col in ("extraction_layout_rules", "extraction_hard_cases"):
        assert col in router._EXTRACTION_RULE_UPDATABLE
        assert col in router._EXTRACTION_RULE_COLS


def test_update_schema_accepts_50000_and_rejects_50001():
    for col in ("extraction_layout_rules", "extraction_hard_cases"):
        assert getattr(SupplierExtractionRulesUpdate(**{col: "x" * 50000}), col) == "x" * 50000
        with pytest.raises(ValidationError):
            SupplierExtractionRulesUpdate(**{col: "x" * 50001})


def test_schemas_default_to_none_for_new_columns():
    update = SupplierExtractionRulesUpdate()
    assert update.extraction_layout_rules is None and update.extraction_hard_cases is None
    resp = SupplierExtractionRulesResponse(supplier_id=1)
    assert resp.extraction_layout_rules is None and resp.extraction_hard_cases is None
