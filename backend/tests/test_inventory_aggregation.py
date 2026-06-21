"""Inventory aggregation layer tests."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

TEST_PG_URL = os.getenv("TEST_PG_URL")
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "inventory_aggregation"
MIGRATION_FILE = "20260620_010000_create_inventory_aggregation_rules.sql"


def _split_sql_preserving_do_blocks(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    in_dollar = False
    dollar_tag = ""
    while i < len(sql):
        if sql[i] == "$":
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < len(sql) and sql[j] == "$":
                tag = sql[i : j + 1]
                if not in_dollar:
                    in_dollar = True
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
                if tag == dollar_tag:
                    in_dollar = False
                    dollar_tag = ""
                    buf.append(tag)
                    i = j + 1
                    continue
        if sql[i] == ";" and not in_dollar:
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(sql[i])
        i += 1
    if buf:
        statements.append("".join(buf))
    return statements


async def _apply_migration(eng, filename: str) -> None:
    from sqlalchemy import text

    sql = (Path(__file__).resolve().parents[2] / "migrations" / filename).read_text("utf-8")
    async with eng.begin() as conn:
        for stmt in _split_sql_preserving_do_blocks(sql):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt))


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _projection(row: dict[str, str]) -> dict[str, str]:
    return {
        "series": row.get("series") or row["Series"],
        "condition": row.get("condition") or row["Condition"],
        "quantity": row.get("quantity") or row["Quantity"],
        "unit_price": row.get("unit_price") or row["Unit Price"],
        "status": row.get("status") or row["Status"],
        "supplier_name": row.get("supplier_name") or row["提供者"],
        "reason": row.get("reason") or row.get("採用理由"),
    }


def _assert_golden_matches(input_path: Path, expected_path: Path) -> None:
    from app.services.inventory_aggregation import aggregate_inventory_offers

    if not input_path.exists() or not expected_path.exists():
        pytest.skip("ver4.1 実CSV が未配置のため、ゴールデンは一時スキップ")
    input_rows = _load_csv(input_path)
    expected_rows = _load_csv(expected_path)

    results = aggregate_inventory_offers(input_rows)
    actual = [
        {
            "series": row.series,
            "condition": row.condition,
            "quantity": str(row.quantity),
            "unit_price": str(row.unit_price),
            "status": row.status,
            "supplier_name": row.supplier_name or "",
            "reason": row.reason,
        }
        for row in results
    ]
    expected = [_projection(row) for row in expected_rows]

    assert actual == expected


def test_aggregate_inventory_offers_golden():
    _assert_golden_matches(
        FIXTURE_DIR / "ver41_output.csv",
        FIXTURE_DIR / "ver41_aggregation.csv",
    )


def test_aggregate_inventory_offers_note_track_golden():
    _assert_golden_matches(
        FIXTURE_DIR / "notetrack_output.csv",
        FIXTURE_DIR / "notetrack_aggregation.csv",
    )


def test_aggregate_inventory_offers_note_group_and_condition_normalization():
    from app.services.inventory_aggregation import aggregate_inventory_offers

    rows = [
        {
            "series": "メガシンフォニア",
            "condition": "Damaged box",
            "note_ja": "外箱破れ",
            "quantity": 1,
            "unit_price": 500,
            "status": "in_stock",
            "supplier_name": "Supplier X",
            "release_date": "2026/06/01",
        },
        {
            "series": "メガシンフォニア",
            "condition": "Damaged box",
            "note_ja": "外箱破れ",
            "quantity": 20,
            "unit_price": 600,
            "status": "in_stock",
            "supplier_name": "Supplier Y",
            "release_date": "2026/06/02",
        },
    ]

    results = aggregate_inventory_offers(rows)

    assert len(results) == 1
    assert results[0].condition == "Damaged sealed box"
    assert results[0].supplier_name == "Supplier X"
    assert results[0].reason_category == "lowest_price"
    assert results[0].reason == "最安値のため採用"


@pytest.mark.skipif(not TEST_PG_URL, reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。")
@pytest.mark.asyncio
async def test_inventory_aggregation_rules_migration_seeds_defaults():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(TEST_PG_URL, echo=False)
    try:
        await _apply_migration(engine, MIGRATION_FILE)
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT condition, price_tolerance, stock_tolerance "
                    "FROM public.inventory_aggregation_rules "
                    "ORDER BY id ASC"
                )
            )
            rows = [dict(row._mapping) for row in result]

        assert rows == [
            {"condition": "Case", "price_tolerance": 1000, "stock_tolerance": 5},
            {"condition": "Sealed box", "price_tolerance": 100, "stock_tolerance": 30},
            {
                "condition": "Damaged sealed box",
                "price_tolerance": 100,
                "stock_tolerance": 10,
            },
            {"condition": "No shrink box", "price_tolerance": 100, "stock_tolerance": 5},
        ]
    finally:
        await engine.dispose()
