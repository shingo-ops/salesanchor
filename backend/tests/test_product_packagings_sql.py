"""ADR-1028 便3: 入数・重さの対応の式（DB を使わない）。"""
from app.services.inventory_search import build_search_sql
from app.services.product_packagings import LEGACY_FIELDS, legacy_field_sql


def test_count_fields_join_contained_unit():
    sql = legacy_field_sql("boxes_per_case", "p.id")
    assert sql == (
        "(SELECT pk.contained_count FROM public.product_packagings pk "
        "JOIN public.quantity_units u ON u.id = pk.unit_id "
        "JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id "
        "WHERE pk.product_id = p.id AND u.code = 'CASE' AND cu.code = 'BOX')"
    )
    sql = legacy_field_sql("packs_per_box", "x.id")
    assert "u.code = 'BOX' AND cu.code = 'PACK'" in sql and "pk.product_id = x.id" in sql


def test_weight_fields_have_no_contained_join():
    for field, unit in (("case_weight_kg", "CASE"), ("box_weight_kg", "BOX")):
        sql = legacy_field_sql(field, "p.id")
        assert sql.startswith("(SELECT pk.weight_kg FROM public.product_packagings pk ")
        assert f"u.code = '{unit}'" in sql
        assert "cu." not in sql


def test_four_fields_defined():
    assert set(LEGACY_FIELDS) == {"boxes_per_case", "case_weight_kg", "packs_per_box", "box_weight_kg"}


def test_inventory_search_uses_same_expressions():
    sql = build_search_sql(["a"], "and", 10, {})
    assert f'{legacy_field_sql("box_weight_kg", "p.id")} AS box_weight_kg' in sql
    assert f'{legacy_field_sql("case_weight_kg", "p.id")} AS case_weight_kg' in sql
    assert "p.box_weight_kg" not in sql
    assert "p.case_weight_kg" not in sql
