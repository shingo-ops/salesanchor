"""tests/seed_data.py（試験用 seed の供給元）の単体試験。DB は使わない（SQLite・PG 不要）。"""

from __future__ import annotations

from app.services.inventory_aggregation import DEFAULT_AGGREGATION_RULES
from tests.seed_data import (
    _load_country_seed_rows,
    _load_tcg_type_seed_rows,
    aggregation_rules_seed_sql,
    country_seed_sql,
    type_master_seed_sql,
)


def test_country_seed_rows_match_frontend_constant():
    rows = _load_country_seed_rows()
    codes = [code for code, _, _ in rows]

    assert len(rows) == 190
    assert len(set(codes)) == 190
    assert codes[0] == "AF"
    assert codes[-1] == "ZW"
    assert dict((code, dial) for code, _, dial in rows)["JP"] == "+81"


def test_country_seed_sql_has_one_value_row_per_country_and_is_idempotent():
    sql = country_seed_sql()

    assert sql.startswith("INSERT INTO public.countries (code, name, dial_code, is_active) VALUES")
    assert sql.count("\n('") == 190  # 全行が改行＋括弧で始まる
    assert sql.rstrip().endswith("ON CONFLICT (code) DO NOTHING")


def test_type_master_seed_sql_reuses_the_loader_rows():
    rows = _load_tcg_type_seed_rows()
    sql = type_master_seed_sql()

    assert len(rows) == 12
    for code, name_ja, name_en in rows:
        assert f"('{code}'," in sql
        assert name_ja in sql
    assert sql.rstrip().endswith("ON CONFLICT (code) DO NOTHING")


def test_type_master_seed_sql_escapes_single_quotes():
    # 名前に ' を含んでも SQL が壊れないこと（'' に置換）
    from tests.seed_data import _lit

    assert _lit("O'Brien") == "'O''Brien'"
    assert _lit(None) == "NULL"


def test_aggregation_rules_seed_sql_uses_app_defaults():
    sql = aggregation_rules_seed_sql()

    assert len(DEFAULT_AGGREGATION_RULES) == 4
    for rule in DEFAULT_AGGREGATION_RULES:
        assert f"('{rule.condition}', {rule.price_tolerance}, {rule.stock_tolerance})" in sql
    assert sql.rstrip().endswith("ON CONFLICT (condition) DO NOTHING")


def test_aggregation_default_values_match_spec_ver41():
    # 仕様（ver4.1）の 4 行。コードの定数と seed が同じ値を持つことを文字列で固定する
    assert [(r.condition, r.price_tolerance, r.stock_tolerance) for r in DEFAULT_AGGREGATION_RULES] == [
        ("Case", 1000, 5),
        ("Sealed box", 100, 30),
        ("Damaged sealed box", 100, 10),
        ("No shrink box", 100, 5),
    ]
