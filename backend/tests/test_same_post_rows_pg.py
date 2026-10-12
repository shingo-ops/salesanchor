# ruff: noqa: F811
"""同じ投稿の同じ商品の行（便SP）の is_current の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。原文・値はすべて架空。

同じ投稿の同じ組の行はすべて TRUE／新しい投稿があれば古い投稿の行は FALSE／同順位は job id の大きい方／2回呼んでも同じ。
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.services import tcg_analyzer_svc as analyzer
from tests.test_line_analysis_v102_pg import one
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")

_COMPUTED_AT = "2026-10-10 00:00:00+00"
_FIXED_RECEIVED_AT = "2026-10-10 01:00:00+00"


@pytest.fixture
def ids(pg, v102):  # noqa: F811
    products = [r[0] for r in one(pg, "SELECT id FROM public.products ORDER BY id")]
    conditions = {r[1]: r[0] for r in one(pg, "SELECT id, canonical FROM public.conditions")}
    return SimpleNamespace(p1=products[0], p2=products[1], box=conditions["Sealed box"], case=conditions["Case"])


def _add_job(pg_fixture, hours_ago: float = 1, received_at: str | None = None) -> str:
    """投稿を1つ（source_message と job）入れて job id を返す。received_at を渡すと固定の時刻にする。"""
    source_id, job_id = str(uuid4()), str(uuid4())
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.source_messages (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
                SELECT %s,id,'架空',%s,true,COALESCE(%s::timestamptz, now() - make_interval(secs => %s)),
                       now() - make_interval(secs => %s)
                FROM {SCHEMA}.supplier_channels LIMIT 1""",
            (source_id, uuid4().hex, received_at, hours_ago * 3600, hours_ago * 3600),
        )
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')", (job_id, source_id))
    return job_id


def _add_row(pg_fixture, job_id: str, product_id: int, condition_id: int, *, unit: str = "Box", note: str | None = None,
             status: str | None = None, basis: str | None = None, price: int = 1000, qty: int | None = 1,
             canonical: str = "Sealed box") -> str:
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
                 condition_basis,note_ja,status,price_normalized,quantity_normalized,needs_review,engine_version,computed_at)
                VALUES (%s,%s,%s,true,%s,true,%s,%s,%s,%s,%s,%s,%s,false,'test',%s)""",
            (result_id, item_id, product_id, unit, condition_id, canonical, basis, note, status, price, qty, _COMPUTED_AT),
        )
    return result_id


def _merge(pg_fixture, job: str) -> None:
    with Session(pg_fixture[1]) as session:
        analyzer._merge_supplier_products(session, job, SCHEMA)


def _current(pg_fixture, result_id: str) -> bool:
    return one(pg_fixture, f"SELECT is_current FROM {SCHEMA}.analysis_results WHERE id=%s", (result_id,))[0][0]


# --- is_current ----------------------------------------------------------------------------------


def test_two_rows_of_the_same_post_and_pair_are_both_current(pg, ids):
    job = _add_job(pg)
    rows = [_add_row(pg, job, ids.p1, ids.box, note="a"), _add_row(pg, job, ids.p1, ids.box, note="b")]
    _merge(pg, job)
    assert [_current(pg, r) for r in rows] == [True, True]


def test_rows_of_an_older_post_are_all_not_current(pg, ids):
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    old = [_add_row(pg, old_job, ids.p1, ids.box), _add_row(pg, old_job, ids.p1, ids.box)]
    new = [_add_row(pg, new_job, ids.p1, ids.box)]
    _merge(pg, new_job)
    assert [_current(pg, r) for r in old] == [False, False]
    assert _current(pg, new[0]) is True


def test_same_received_at_and_computed_at_goes_to_the_larger_job_id(pg, ids):
    first, second = _add_job(pg, received_at=_FIXED_RECEIVED_AT), _add_job(pg, received_at=_FIXED_RECEIVED_AT)
    rows = {first: _add_row(pg, first, ids.p1, ids.box), second: _add_row(pg, second, ids.p1, ids.box)}
    _merge(pg, first)
    winner = one(pg, f"SELECT id::text FROM {SCHEMA}.extraction_jobs WHERE id IN (%s,%s) ORDER BY id DESC LIMIT 1", (first, second))[0][0]
    assert {job: _current(pg, row) for job, row in rows.items()} == {job: job == winner for job in rows}


def test_calling_merge_twice_gives_the_same_result(pg, ids):
    old_job, new_job = _add_job(pg, 5), _add_job(pg, 1)
    rows = [_add_row(pg, old_job, ids.p1, ids.box), _add_row(pg, new_job, ids.p1, ids.box), _add_row(pg, new_job, ids.p1, ids.box)]
    _merge(pg, new_job)
    first = [_current(pg, r) for r in rows]
    _merge(pg, new_job)
    assert [_current(pg, r) for r in rows] == first == [False, True, True]


def test_rows_of_the_same_post_stay_current_even_if_computed_at_or_engine_differ(pg, ids):
    # 1つの item には analysis_results が1行しかない（UNIQUE extraction_item_id）ので、解析し直しの前後の行は同じ投稿に並ばない。
    # 一部の行だけ計算時刻や engine_version が違っても、投稿が同じなら全部 TRUE のまま。
    job = _add_job(pg)
    rows = [_add_row(pg, job, ids.p1, ids.box, note="a"), _add_row(pg, job, ids.p1, ids.box, note="b")]
    with pg[0].cursor() as cur:
        cur.execute(
            f"UPDATE {SCHEMA}.analysis_results SET computed_at = computed_at - interval '3 days', engine_version = 'older' WHERE id = %s",
            (rows[0],),
        )
    _merge(pg, job)
    assert [_current(pg, r) for r in rows] == [True, True]
