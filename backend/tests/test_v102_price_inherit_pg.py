# ruff: noqa: F811
"""価格なし・数ありの件への価格の引き継ぎ（line_analysis_v102_svc._inherit_price）の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。

原文・値はすべて架空。型は test_inventory_distribution_rows_pg.py。
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.services.line_analysis_v102_svc as svc
from app.services.v102_unit_price_check_svc import _MARKET_SQL
from tests.test_inventory_distribution_rows_pg import (  # noqa: F401  fixture
    _add_job,
    _add_row,
    _rows,
    _set_supplier,
    ids,
)
from tests.test_line_analysis_v102_pg import one
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")


def _source(pg, job: str) -> tuple[str, str]:
    """(job の投稿 id, job id) を返す。"""
    return one(pg, f"SELECT source_message_id::text FROM {SCHEMA}.extraction_jobs WHERE id = %s", (job,))[0][0], job


def _item_id(pg, result_id: str) -> str:
    return one(pg, f"SELECT extraction_item_id::text FROM {SCHEMA}.analysis_results WHERE id = %s", (result_id,))[0][0]


def _values(product_id: int, condition_id: int, **overrides) -> dict:
    return {
        "price_normalized": None, "quantity_normalized": 2, "product_id": product_id, "pid_resolved": True,
        "condition_id": condition_id, "status": "In Stock", "price_basis": None, **overrides,
    }


def _inherit(pg, job: str, result_id: str, product_id: int, condition_id: int, *, raw_price=None, **overrides) -> dict:
    row = SimpleNamespace(id=_item_id(pg, result_id), raw_price=raw_price)
    with Session(pg[1]) as session:
        return svc._inherit_price(session, job, row, _values(product_id, condition_id, **overrides))


def _qty_only(pg, job: str, ids, **kw) -> str:
    """価格なし・数ありの行（analysis_results.id を返す）。"""
    return _add_row(pg, job, ids.p1, ids.box, price=None, qty=2, **kw)


def _persist(pg, result_id: str, values: dict) -> None:
    with pg[0].cursor() as cur:
        cur.execute(
            f"UPDATE {SCHEMA}.analysis_results SET price_normalized = %s, price_basis = %s WHERE id = %s",
            (values["price_normalized"], values["price_basis"], result_id),
        )


def test_inherits_price_and_basis_from_the_previous_post_within_48_hours(pg, v102, ids):
    source = _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)

    result = _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box)

    assert result["price_normalized"] == 1234 and result["price_basis"] == f"INHERIT:{source}"


def test_does_not_inherit_when_the_source_is_older_than_48_hours(pg, v102, ids):
    _add_row(pg, _add_job(pg, 49), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)

    assert _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box)["price_normalized"] is None


def test_does_not_inherit_when_there_is_no_source(pg, v102, ids):
    job = _add_job(pg, 1)

    assert _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box)["price_normalized"] is None


def test_does_not_inherit_from_another_condition(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.case, price=1234, qty=1, canonical="Case", unit="Case")
    job = _add_job(pg, 1)

    assert _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box)["price_normalized"] is None


def test_does_not_inherit_from_another_channel(pg, v102, ids):
    other = _add_job(pg, 30)
    _add_row(pg, other, ids.p1, ids.box, price=1234, qty=1)
    _set_supplier(pg, other, "架空仕入元X")
    job = _add_job(pg, 1)

    assert _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box)["price_normalized"] is None


def test_does_not_inherit_into_a_sold_out_row(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)

    result = _inherit(pg, job, _qty_only(pg, job, ids, status="Sold out"), ids.p1, ids.box, status="Sold out")

    assert result["price_normalized"] is None and result["price_basis"] is None


def test_does_not_inherit_from_a_sold_out_source(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1, status="Sold out")
    job = _add_job(pg, 1)

    assert _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box)["price_normalized"] is None


def _correction(pg, job: str, result_id: str, human_value: str) -> None:
    source_id, _ = _source(pg, job)
    with pg[0].cursor() as cur:
        cur.execute(
            f"INSERT INTO {SCHEMA}.item_corrections (extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by) "
            "VALUES (%s, %s, 'v102_price', '', %s, 'tester')",
            (_item_id(pg, result_id), source_id, human_value),
        )


def test_does_not_inherit_when_a_human_cleared_the_price_but_does_when_no_correction_exists(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)
    cleared, added = _qty_only(pg, job, ids), _qty_only(pg, job, ids)
    _correction(pg, job, cleared, "")

    assert _inherit(pg, job, cleared, ids.p1, ids.box)["price_normalized"] is None
    assert _inherit(pg, job, added, ids.p1, ids.box)["price_normalized"] == 1234


def test_a_later_human_price_correction_makes_the_row_a_target_again(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)
    result_id = _qty_only(pg, job, ids)
    _correction(pg, job, result_id, "")
    _correction(pg, job, result_id, "999")  # 最新が空文字でなければ消した扱いにしない

    assert _inherit(pg, job, result_id, ids.p1, ids.box)["price_normalized"] == 1234


def test_distribution_rows_show_the_new_quantity_with_the_inherited_price(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=9)
    job = _add_job(pg, 1)
    result_id = _qty_only(pg, job, ids)
    assert [r for r in _rows(pg, False) if r["quantity"] == "2"] == []  # 価格なしは配信に出ない

    _persist(pg, result_id, _inherit(pg, job, result_id, ids.p1, ids.box))

    shown = [r for r in _rows(pg, False) if r["quantity"] == "2"]
    assert len(shown) == 1 and shown[0]["unit_price"] == "1234"


def test_chain_inherits_from_the_original_not_from_an_inherited_row(pg, v102, ids):
    source = _add_row(pg, _add_job(pg, 40), ids.p1, ids.box, price=1234, qty=1)
    job_b, job_c = _add_job(pg, 20), _add_job(pg, 1)
    row_b, row_c = _qty_only(pg, job_b, ids), _qty_only(pg, job_c, ids)
    b = _inherit(pg, job_b, row_b, ids.p1, ids.box)
    _persist(pg, row_b, b)

    c = _inherit(pg, job_c, row_c, ids.p1, ids.box)

    assert b["price_basis"] == f"INHERIT:{source}"
    assert c["price_normalized"] == 1234 and c["price_basis"] == f"INHERIT:{source}"


def test_chain_stops_when_the_original_is_older_than_48_hours(pg, v102, ids):
    _add_row(pg, _add_job(pg, 60), ids.p1, ids.box, price=1234, qty=1)
    job_b, job_c = _add_job(pg, 30), _add_job(pg, 1)
    row_b, row_c = _qty_only(pg, job_b, ids), _qty_only(pg, job_c, ids)
    b = _inherit(pg, job_b, row_b, ids.p1, ids.box)
    _persist(pg, row_b, b)

    assert b["price_normalized"] == 1234  # B から A まで30時間
    assert _inherit(pg, job_c, row_c, ids.p1, ids.box)["price_normalized"] is None  # C から A まで59時間。B は元にしない


def test_rows_with_a_price_or_sold_out_keep_the_values_unchanged(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)
    priced = _add_row(pg, job, ids.p1, ids.box, price=500, qty=2)
    sold = _qty_only(pg, job, ids, status="Sold out")

    with_price = _values(ids.p1, ids.box, price_normalized=500, price_basis="V102:yen_free")
    sold_out = _values(ids.p1, ids.box, status="Sold out")
    with Session(pg[1]) as session:
        assert svc._inherit_price(session, job, SimpleNamespace(id=_item_id(pg, priced), raw_price="500円"), with_price) == with_price
        assert svc._inherit_price(session, job, SimpleNamespace(id=_item_id(pg, sold), raw_price=None), sold_out) == sold_out


@pytest.mark.parametrize("raw_price", ["37万", "＠65,000円", "  "])
def test_written_raw_price_is_never_overwritten_but_blank_raw_price_is_a_target(pg, v102, ids, raw_price):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)

    result = _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box, raw_price=raw_price)

    assert (result["price_normalized"] == 1234) is (raw_price.strip() == "")


def test_raw_price_none_text_is_a_target(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)

    assert _inherit(pg, job, _qty_only(pg, job, ids), ids.p1, ids.box, raw_price="None")["price_normalized"] == 1234


def test_does_not_inherit_when_condition_id_is_null(pg, v102, ids):
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)
    result_id = _qty_only(pg, job, ids)

    row = SimpleNamespace(id=_item_id(pg, result_id), raw_price=None)
    values = {**_values(ids.p1, ids.box), "condition_id": None}
    with Session(pg[1]) as session:
        assert svc._inherit_price(session, job, row, values) == values


def test_market_sql_ignores_inherited_rows(pg, v102, ids):
    own_job, inherit_job = _add_job(pg, 30), _add_job(pg, 20)
    own = _add_row(pg, own_job, ids.p1, ids.box, price=1000, qty=1)
    inherited = _add_row(pg, inherit_job, ids.p1, ids.box, price=9000, qty=1)
    with pg[0].cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET engine_version = 'v102-test' WHERE id IN (%s, %s)", (own, inherited))
        cur.execute(f"UPDATE {SCHEMA}.source_messages SET raw_text = '架空の原文1' WHERE id = %s", (_source(pg, own_job)[0],))
        cur.execute(f"UPDATE {SCHEMA}.source_messages SET raw_text = '架空の原文2' WHERE id = %s", (_source(pg, inherit_job)[0],))

    def market() -> list[tuple]:
        with Session(pg[1]) as session:
            rows = session.execute(
                text(_MARKET_SQL.format(schema=SCHEMA)), {"pids": [ids.p1], "engine": "v102%", "smid": str(uuid4())}
            ).all()
        return [(r.product_id, r.unit, float(r.median_price), r.posts) for r in rows]

    before = market()
    assert before == [(ids.p1, "Box", 5000.0, 2)]  # INHERIT: の印を付ける前は2投稿の中央値
    _persist(pg, inherited, {"price_normalized": 9000, "price_basis": f"INHERIT:{own}"})

    assert market() == [(ids.p1, "Box", 1000.0, 1)]


def test_bundle_rows_are_not_inherited_and_not_sources(pg, v102, ids):
    """まとめ売り行（bundle_size あり）は価格を引き継がず、引き継ぎ元にもならない（ADR-1027）。"""
    assert "ar.bundle_size IS NULL" in svc._INHERIT_PRICE_SQL
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)
    result_id = _qty_only(pg, job, ids)
    assert _inherit(pg, job, result_id, ids.p1, ids.box, bundle_size=40)["price_normalized"] is None


def test_a_stored_bundle_row_is_not_an_inherit_source(pg, v102, ids):
    """bundle_size の有る実際の行は、価格の引き継ぎ元にならない（ADR-1027）。"""
    source = _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, price=1234, qty=1)
    job = _add_job(pg, 1)
    target = _qty_only(pg, job, ids)
    assert _inherit(pg, job, target, ids.p1, ids.box)["price_normalized"] == 1234  # まとめ売りでなければ引き継ぐ
    with pg[0].cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.analysis_results SET bundle_size = 40 WHERE id = %s", (source,))
    assert _inherit(pg, job, target, ids.p1, ids.box)["price_normalized"] is None
