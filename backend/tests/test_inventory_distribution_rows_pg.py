# ruff: noqa: F811
"""在庫表を LINE 解析の配信行に切り替える便SP2の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。原文・値はすべて架空。

T1: GAS の出力（fetch_output_rows の14列と並び）が、変更前の SQL と1文字も変わらない。配信件数も同じ。
T2: まとめ ON で R2:甲 と R2:乙 の組が1行（数量は合計・単価は最大・merged_count=2）。
T3: 備考・発送・status が違う組、数量が空の組、根拠が同じ組、根拠が NULL の組はまとまらない。
T4: まとめ OFF の行数が配信件数と同じ。ON と OFF の行数の差は Σ(merged_count-1)。
"""
from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from app.services import tcg_distribution_svc as distribution
from app.services.tcg_condition_review_svc import review_joins, source_cte
from app.services.tcg_result_order import result_order_sql
from tests.test_line_analysis_v102_pg import one
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")

_COMPUTED_AT = "2026-10-10 00:00:00+00"
_ARGS = {"include_flag_single": False, "age_condition": ""}
_PRICE, _QTY, _NOTE, _STATUS, _SHIP = 5, 6, 7, 8, 13  # 14列の位置


@pytest.fixture
def ids(pg, v102):  # noqa: F811
    products = [r[0] for r in one(pg, "SELECT id FROM public.products ORDER BY id")]
    conditions = {r[1]: r[0] for r in one(pg, "SELECT id, canonical FROM public.conditions")}
    return SimpleNamespace(p1=products[0], p2=products[1], box=conditions["Sealed box"], case=conditions["Case"])


def _add_job(pg_fixture, hours_ago: float = 1) -> str:
    source_id, job_id = str(uuid4()), str(uuid4())
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                SELECT %s,id,'架空',%s,true,now() - make_interval(secs => %s), now() - make_interval(secs => %s)
                FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (source_id, uuid4().hex, hours_ago * 3600, hours_ago * 3600),
        )
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')", (job_id, source_id))
    return job_id


def _add_row(pg_fixture, job_id: str, product_id: int, condition_id: int, *, unit: str = "Box", note: str | None = None,
             ship: str | None = None, status: str | None = "In Stock", basis: str | None = None, price: int = 1000,
             qty: int | None = 1, canonical: str = "Sealed box") -> str:
    item_id, result_id = str(uuid4()), str(uuid4())
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.extraction_items (id,extraction_job_id,line_start,line_end,source_lines,gemini_index,created_at)
                SELECT %s,%s,n,n,ARRAY[n],n,now() FROM (SELECT count(*)::int + 1 AS n FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s) c""",
            (item_id, job_id, job_id),
        )
        cur.execute(
            f"""INSERT INTO {SCHEMA}.analysis_results
                (id,extraction_item_id,product_id,pid_resolved,unit_canonical,unit_resolved,condition_id,condition_canonical,
                 condition_basis,note_ja,ship_ja,status,price_normalized,quantity_normalized,needs_review,engine_version,computed_at)
                VALUES (%s,%s,%s,true,%s,true,%s,%s,%s,%s,%s,%s,%s,%s,false,'test',%s)""",
            (result_id, item_id, product_id, unit, condition_id, canonical, basis, note, ship, status, price, qty, _COMPUTED_AT),
        )
    return result_id


def _rows(pg_fixture, merge: bool) -> list[dict]:
    sql = f"SELECT * FROM ({distribution.distribution_rows_sql(**_ARGS, merge_same_post=merge)}) d ORDER BY sort_ord"
    with Session(pg_fixture[1]) as session:
        return [dict(r) for r in session.execute(text(sql)).mappings().all()]


def _legacy_output_sql() -> str:
    """変更前の fetch_output_rows の SQL（比較の基準。配信の WHERE と ORDER BY を当時のまま持つ）。"""
    return f"""{source_cte(schema=SCHEMA, include_inactive=True)}
        SELECT
            COALESCE(TO_CHAR(sm.line_posted_at AT TIME ZONE 'Asia/Tokyo', 'YYYY-MM-DD HH24:MI:SS'), '') AS posted_at,
            COALESCE(p.mark, '') AS mark, COALESCE(p.name, '') AS japanese_title, COALESCE(p.name_en, '') AS english_title,
            cr.canonical AS condition,
            COALESCE(ROUND(ar.price_normalized)::bigint::text, '') AS unit_price,
            COALESCE(ROUND(ar.quantity_normalized)::bigint::text, '') AS quantity,
            COALESCE(ar.note_ja, '') AS note_ja, COALESCE(ar.status, '') AS status,
            COALESCE(p.release_date::text, '') AS release_date, COALESCE(ser.name_ja, '') AS series,
            COALESCE(ps.name, '') AS provider,
            COALESCE((SELECT string_agg(psk.keyword, ' | ' ORDER BY psk.position, psk.id)
                      FROM public.product_search_keywords psk WHERE psk.product_id = p.id), '') AS search_keywords,
            COALESCE(ar.ship_ja, '') AS ship_ja
        FROM {SCHEMA}.analysis_results ar
        JOIN {SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
        JOIN {SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN {SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
        JOIN {SCHEMA}.supplier_channels sc ON sc.id = sm.supplier_channel_id
        LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
        LEFT JOIN public.products p ON p.id = ar.product_id
        LEFT JOIN public.type_master ser ON ser.id = p.work_id
        {review_joins(schema=SCHEMA)}
        WHERE ar.pid_resolved = TRUE AND ar.is_current = TRUE AND cr.needs_review IS FALSE
          AND ar.exclusion IS DISTINCT FROM 'excluded' AND ar.unit_resolved = TRUE
          AND ar.price_normalized IS NOT NULL AND sm.line_posted_at IS NOT NULL
          AND cr.canonical NOT LIKE 'FLAG_%' AND cr.effect IS DISTINCT FROM 'EXCLUDE'
        ORDER BY {result_order_sql()}"""


def _seed_mixed(pg_fixture, ids) -> None:
    job = _add_job(pg_fixture)
    _add_row(pg_fixture, job, ids.p1, ids.box, note="X", basis="R2:甲", price=1000, qty=3)
    _add_row(pg_fixture, job, ids.p1, ids.box, note="X", basis="R2:乙", price=1200, qty=4)
    _add_row(pg_fixture, job, ids.p1, ids.box, note="Y", basis="R2:甲", price=3000, qty=5)
    _add_row(pg_fixture, job, ids.p2, ids.case, basis="R2:甲", price=2000, qty=None, canonical="Case", unit="Case")
    _add_row(pg_fixture, _add_job(pg_fixture, 2), ids.p2, ids.case, basis="R2:丙", price=500, qty=1, canonical="Case", unit="Case")


# --- T1 ------------------------------------------------------------------------------------------


def test_t1_gas_output_matches_the_previous_query_exactly(pg, ids):
    _seed_mixed(pg, ids)
    with Session(pg[1]) as session:
        legacy = [list(r) for r in session.execute(text(_legacy_output_sql())).all()]

    async def _new() -> list[list[str]]:
        engine = create_async_engine(pg[2])
        try:
            async with AsyncSession(engine) as db:
                return await distribution.fetch_output_rows(db)
        finally:
            await engine.dispose()

    assert legacy and asyncio.run(_new()) == legacy


def test_t1_distribution_count_matches_the_previous_query(pg, ids):
    _seed_mixed(pg, ids)
    with Session(pg[1]) as session:
        legacy_count = len(session.execute(text(_legacy_output_sql())).all())
    assert len(_rows(pg, merge=False)) == legacy_count > 0


# --- T2 ------------------------------------------------------------------------------------------


def test_t2_ranks_of_the_same_post_become_one_row(pg, ids):
    job = _add_job(pg)
    first = _add_row(pg, job, ids.p1, ids.box, note="X", basis="R2:甲", price=1000, qty=3)
    _add_row(pg, job, ids.p1, ids.box, note="X", basis="R2:乙", price=1200, qty=4)
    rows = _rows(pg, merge=True)
    assert len(rows) == 1
    assert (rows[0]["unit_price"], rows[0]["quantity"], rows[0]["merged_count"]) == ("1200", "7", 2)
    assert rows[0]["row_key"] == first  # 組の中で並びが最初の行（単価の安い方）の id
    assert len(_rows(pg, merge=False)) == 2


# --- T3 ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ({"note": "a"}, {"note": "b"}),
        ({"ship": "今週"}, {"ship": "来週"}),
        ({"status": "In Stock"}, {"status": "Pre-order"}),
        ({"qty": 3}, {"qty": None}),
        ({"basis": "R2:甲"}, {"basis": "R2:甲"}),
        ({"basis": "R2:甲"}, {"basis": None}),
    ],
    ids=["note", "ship", "status", "qty-null", "same-basis", "basis-null"],
)
def test_t3_these_pairs_are_not_merged(pg, ids, first, second):
    job = _add_job(pg)
    _add_row(pg, job, ids.p1, ids.box, **{"basis": "R2:甲", **first})
    _add_row(pg, job, ids.p1, ids.box, **{"basis": "R2:乙", **second})
    assert len(_rows(pg, merge=True)) == 2


def test_t3_rows_of_different_posts_are_not_merged(pg, ids):
    _add_row(pg, _add_job(pg), ids.p1, ids.box, basis="R2:甲")
    _add_row(pg, _add_job(pg), ids.p1, ids.box, basis="R2:乙")
    assert len(_rows(pg, merge=True)) == 2


# --- T4 ------------------------------------------------------------------------------------------


def test_t4_off_count_equals_distribution_count_and_on_differs_by_merged_rows(pg, ids):
    _seed_mixed(pg, ids)
    off, on = _rows(pg, merge=False), _rows(pg, merge=True)
    assert all(r["merged_count"] == 1 for r in off)
    assert len(off) - len(on) == sum(r["merged_count"] - 1 for r in on) == 1
    assert [r["sort_ord"] for r in on] == sorted(r["sort_ord"] for r in on)
