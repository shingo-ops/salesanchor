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
    # テスト用 DB の public.products には category が無い。本番の型（VARCHAR(50)）に合わせて足す。
    # 根拠: migrations/082_extend_products_box_attributes.sql
    # 作品は products.work_id → type_master.code で決まる（ADR-1030）。tcg_type 列は使わない（NULL のまま）。
    with pg[0].cursor() as cur:
        cur.execute("ALTER TABLE public.products ADD COLUMN IF NOT EXISTS category VARCHAR(50)")
        cur.execute(
            "INSERT INTO public.type_master (code, name_ja, sort_order, is_active) "
            "VALUES ('T_A', '作品A', 100, TRUE), ('T_B', '作品B', 100, TRUE) ON CONFLICT (code) DO NOTHING"
        )
        cur.execute(
            "UPDATE public.products SET category = 'C_A', "
            "work_id = (SELECT id FROM public.type_master WHERE code = 'T_A') WHERE id = %s", (products[0],))
        cur.execute(
            "UPDATE public.products SET category = 'C_B', "
            "work_id = (SELECT id FROM public.type_master WHERE code = 'T_B') WHERE id = %s", (products[1],))
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


def _item_id_of(pg_fixture, result_id: str) -> str:
    with Session(pg_fixture[1]) as session:
        return str(session.execute(
            text(f"SELECT extraction_item_id::text FROM {SCHEMA}.analysis_results WHERE id = :i"), {"i": result_id},
        ).scalar_one())


def test_b1_unmerged_row_has_its_own_extraction_item_id(pg, ids):
    job = _add_job(pg)
    only = _add_row(pg, job, ids.p1, ids.box, note="X", basis="R2:甲")
    for merge in (True, False):
        rows = _rows(pg, merge=merge)
        assert len(rows) == 1
        assert rows[0]["extraction_item_ids"] == [_item_id_of(pg, only)]


def test_b2_merged_row_lists_every_extraction_item_id_in_sort_order(pg, ids):
    job = _add_job(pg)
    first = _add_row(pg, job, ids.p1, ids.box, note="X", basis="R2:甲", price=1000, qty=3)
    second = _add_row(pg, job, ids.p1, ids.box, note="X", basis="R2:乙", price=1200, qty=4)
    merged = _rows(pg, merge=True)
    assert len(merged) == 1 and merged[0]["merged_count"] == 2
    plain = _rows(pg, merge=False)  # sort_ord 順の1行ずつ
    expected = [_item_id_of(pg, r["row_key"]) for r in plain]
    assert sorted(expected) == sorted([_item_id_of(pg, first), _item_id_of(pg, second)])
    assert merged[0]["extraction_item_ids"] == expected
    assert len(merged[0]["extraction_item_ids"]) == merged[0]["merged_count"]


def test_b5_item_id_lookup_includes_inactive_posts_with_current_rows_but_the_plain_list_does_not(pg, ids, monkeypatch):
    from app.services import tcg_analysis_review_svc as review

    monkeypatch.setattr(review, "TCG_SCHEMA", SCHEMA)
    monkeypatch.setattr(review, "_BASE_FROM", review._base_from())

    async def _no_reason_codes(_db):  # 理由コード表は検証対象外（この pg には表が無い）
        return {}

    monkeypatch.setattr(review, "load_review_reason_codes", _no_reason_codes)

    job = _add_job(pg)
    result_id = _add_row(pg, job, ids.p1, ids.box, basis="R2:甲")
    item_id = _item_id_of(pg, result_id)
    with pg[0].cursor() as cur:
        cur.execute(
            f"UPDATE {SCHEMA}.source_messages SET is_active = false "
            f"WHERE id = (SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id = %s)", (job,),
        )

    async def _fetch(**kwargs) -> dict:
        engine = create_async_engine(pg[2])
        try:
            async with AsyncSession(engine) as db:
                return await review.fetch_analysis_results(db, **kwargs)
        finally:
            await engine.dispose()

    # fetch_analysis_results は public.supplier_channels を固定で JOIN する（tcg_analysis_review_svc.py:58）。
    # _add_job は tenant_901 側の仕入元を使うので、同じ id の行を public にも用意し、終わりに消す。
    # 列は両表とも id/channel/external_id/is_active/supplier_id で同一（NOT NULL は channel・is_active・supplier_id）。
    with pg[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO public.supplier_channels (id, channel, is_active, supplier_id)
                SELECT sc.id, sc.channel, sc.is_active, sc.supplier_id FROM {SCHEMA}.supplier_channels sc
                WHERE sc.id = (SELECT sm.supplier_channel_id FROM {SCHEMA}.source_messages sm
                               JOIN {SCHEMA}.extraction_jobs ej ON ej.source_message_id = sm.id WHERE ej.id = %s)
                ON CONFLICT (id) DO NOTHING RETURNING id""", (job,),
        )
        seeded = [r[0] for r in cur.fetchall()]
    try:
        by_id = asyncio.run(_fetch(extraction_item_ids=[item_id], limit=1))
        assert [i["extraction_item_id"] for i in by_id["items"]] == [item_id]
        plain = asyncio.run(_fetch(limit=500))
        assert item_id not in [i["extraction_item_id"] for i in plain["items"]]
    finally:
        with pg[0].cursor() as cur:
            for channel_id in seeded:
                cur.execute("DELETE FROM public.supplier_channels WHERE id = %s", (channel_id,))


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


# --- 在庫表 GET /inventory を1文にする便 --------------------------------------------------------------------------

_VIEW_CASES = [
    {},
    {"sort": "unit_price", "order": "asc"},
    {"work_code_filter": True},
    {"page": 99},
    {"limit": 3},
    {"limit": 3, "page": 2, "sort": "unit_price", "order": "asc"},
    {"sort": "name", "order": "desc"},
    {"sort": "name", "order": "asc"},
]


def _old_three_statements(session, *, merge: bool, where: str, params: dict, sort_col: str, order_dir: str,
                          limit: int, offset: int, args: dict = _ARGS):
    """変更前の3文（COUNT / ページ / facets）。比較の基準。"""
    # 基準の ORDER BY（ADR-1014 改訂 2026-10-18・2026-10-19: まとまりは発売日→題名→product_id。タイトル列は変更前のまま）
    from app.routers.inventory_offers import _build_view_order_by

    order_by = _build_view_order_by(sort_col=sort_col, order_dir=order_dir)

    def rows_sql(m: bool) -> str:
        inner_rows = distribution.distribution_rows_sql(**args, merge_same_post=m)
        return ("SELECT x.*, tm.code AS work_code, pp.category AS category, "
                "MIN(x.sort_ord) OVER (PARTITION BY x.product_id, x.condition) AS cond_block "
                f"FROM ({inner_rows}) x LEFT JOIN public.products pp ON pp.id = x.product_id "
                "LEFT JOIN public.type_master tm ON tm.id = pp.work_id")

    inner = rows_sql(merge)
    total = session.execute(text(f"SELECT COUNT(*) FROM ({inner}) d {where}"), params).scalar_one()
    page_rows = [dict(r) for r in session.execute(
        text(f"SELECT d.* FROM ({inner}) d {where} {order_by} "
             "LIMIT :limit OFFSET :offset"), {**params, "limit": limit, "offset": offset}).mappings().all()]
    facets = {tuple(r[k] for k in ("supplier_id", "provider", "category", "condition", "unit_canonical"))
              for r in session.execute(text(
                  "SELECT DISTINCT d.supplier_id, d.provider, d.category, d.condition, d.unit_canonical "
                  f"FROM ({rows_sql(False)}) d"),
              # 年齢窓の bind だけ渡す（絞り込みの bind は facet に使わない。age_condition が空なら {}）
              {k: v for k, v in params.items() if k == "max_age_hours"}).mappings().all()}
    return int(total), page_rows, facets


def _new_single_statement(session, *, merge: bool, where: str, params: dict, sort_col: str, order_dir: str,
                          limit: int, offset: int, args: dict = _ARGS):
    from app.routers.inventory_offers import _build_inventory_view_sql

    head, final = distribution.distribution_rows_parts(**args, merge_same_post=merge)
    sql = _build_inventory_view_sql(head=head, final_main=final, merge=merge, where=where, sort_col=sort_col,
                                    order_dir=order_dir)
    total, pages, facets = None, [], set()
    for r in session.execute(text(sql), {**params, "limit": limit, "offset": offset}).mappings().all():
        r = dict(r)
        assert [k for k in r if k.startswith("__")] == ["__kind", "__total", "__ord", "__badge_cheapest", "__badge_most_stock",
                                                        "__expiry_s", "__f_supplier_id", "__f_provider", "__f_category",
                                                        "__f_condition", "__f_unit"]
        if r["__kind"] == "total":
            total = int(r["__total"])
        elif r["__kind"] == "page":
            pages.append((r["__ord"], {k: v for k, v in r.items() if not k.startswith("__")}))
        else:
            facets.add((r["__f_supplier_id"], r["__f_provider"], r["__f_category"], r["__f_condition"], r["__f_unit"]))
    pages.sort(key=lambda t: t[0])
    return total, [p for _, p in pages], facets


@pytest.mark.parametrize("merge", [True, False])
@pytest.mark.parametrize("case", _VIEW_CASES)
def test_single_statement_equals_the_previous_three_statements(pg, ids, merge, case):
    from app.routers.inventory_offers import _SORT_COLUMNS, _build_view_filters

    _seed_mixed(pg, ids)
    none = dict.fromkeys(("q", "work_code", "category", "offer_type", "hide_supplier_ids", "hide_categories", "condition",
                          "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max", "price_min", "price_max"))
    with Session(pg[1]) as session:
        if case.get("work_code_filter"):
            none["work_code"] = "T_A"
        conditions, params = _build_view_filters(**none)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        page = case.get("page", 1)
        kw = {"merge": merge, "where": where, "params": params,
              "sort_col": _SORT_COLUMNS.get(case.get("sort", "release_date"), "d.japanese_title"),
              "order_dir": "ASC" if case.get("order", "desc") == "asc" else "DESC", "limit": case.get("limit", 1),
              "offset": (page - 1) * case.get("limit", 1)}
        old = _old_three_statements(session, **kw)
        new = _new_single_statement(session, **kw)
    assert new == old
    if case.get("page") == 99:  # 最終頁+1: items は空だが total は正しい
        assert new[1] == [] and new[0] > 0


def test_facets_are_not_affected_by_filters(pg, ids):
    from app.routers.inventory_offers import _build_view_filters

    _seed_mixed(pg, ids)
    base = dict.fromkeys(("q", "work_code", "category", "offer_type", "hide_supplier_ids", "hide_categories", "condition",
                          "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max", "price_min", "price_max"))
    results = []
    with Session(pg[1]) as session:
        for override in ({}, {"condition": "Case"}, {"qty_min": 4}):
            conditions, params = _build_view_filters(**{**base, **override})
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            results.append(_new_single_statement(
                session, merge=True, where=where, params=params, sort_col="d.japanese_title", order_dir="ASC",
                limit=50, offset=0))
    assert results[0][2] and all(r[2] == results[0][2] for r in results)
    assert results[1][0] < results[0][0]  # 絞り込みで total だけが減る


def _fresh_args() -> tuple[dict, dict]:
    """「24時間以内」ON のときの配信行の引数と bind（API は年齢窓そのものを24hにする）。"""
    age_condition, age_params = distribution._age_window(distribution.FRESH_WINDOW_HOURS)
    return {"include_flag_single": False, "age_condition": age_condition}, age_params


_OLD_FRESH_WHERE = "WHERE d.posted_ts >= NOW() - make_interval(hours => :fresh_hours)"


@pytest.mark.parametrize("merge", [True, False])
def test_fresh_window_inside_equals_the_previous_outer_filter_for_total_and_page(pg, ids, merge):
    """変更前: 48h 窓の外側で 24h を絞る。変更後: 窓そのものを24hにする。total とページ（順番含む）は同じ。"""
    from app.routers.inventory_offers import _SORT_COLUMNS

    _seed_mixed(pg, ids)
    _add_row(pg, _add_job(pg, 30), ids.p1, ids.box, basis="R2:丁", price=700, qty=2)  # 24h より古い行
    old_age, old_age_params = distribution._age_window(48)
    new_args, new_age_params = _fresh_args()
    with Session(pg[1]) as session:
        for sort in ("release_date", "unit_price", "name"):
            for order_dir in ("ASC", "DESC"):
                common = {"merge": merge, "sort_col": _SORT_COLUMNS[sort], "order_dir": order_dir, "limit": 50, "offset": 0}
                old_total, old_page, old_facets = _old_three_statements(
                    session, where=_OLD_FRESH_WHERE, params={**old_age_params, "fresh_hours": 24},
                    args={"include_flag_single": False, "age_condition": old_age}, **common)
                new_total, new_page, new_facets = _new_single_statement(
                    session, where="", params=new_age_params, args=new_args, **common)
                # sort_ord は窓の行数で採番が変わる並びの内部番号（API 応答に出ない）。行の順番と他の全列は比べる
                # cond_block は sort_ord から作る（MIN(sort_ord)）ので同じく外す
                def _no_sort_ord(rows):
                    return [{k: v for k, v in r.items() if k not in ("sort_ord", "cond_block")} for r in rows]

                assert new_total == old_total
                assert _no_sort_ord(new_page) == _no_sort_ord(old_page)
                assert new_total > 0
                assert new_facets <= old_facets


def test_fresh_only_facets_are_limited_to_the_last_24_hours(pg, ids):
    """fresh_only=true: 絞り込み候補は24h内の行の値だけ。false（年齢窓のみ）では古い行の値も残る。"""
    _add_row(pg, _add_job(pg, 1), ids.p1, ids.box, basis="R2:甲")
    _add_row(pg, _add_job(pg, 30), ids.p2, ids.case, basis="R2:乙", canonical="Case", unit="Case")
    old_age, old_age_params = distribution._age_window(48)
    new_args, new_age_params = _fresh_args()
    kw = {"merge": True, "where": "", "sort_col": "d.japanese_title", "order_dir": "ASC", "limit": 50, "offset": 0}
    with Session(pg[1]) as session:
        _, _, facets_wide = _new_single_statement(
            session, params=old_age_params, args={"include_flag_single": False, "age_condition": old_age}, **kw)
        _, _, facets_fresh = _new_single_statement(session, params=new_age_params, args=new_args, **kw)
    # facet の列順: supplier_id, provider, category, condition, unit_canonical
    assert {f[3] for f in facets_wide} == {"Sealed box", "Case"}
    assert {f[3] for f in facets_fresh} == {"Sealed box"}
    assert {f[2] for f in facets_fresh} == {"C_A"}
    assert facets_fresh <= facets_wide


# --- 便1（在庫表と GAS 在庫一覧の揃え）------------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["Sold out", " sold out ", "SoldOut"])
def test_bin1_sold_out_rows_are_not_distribution_rows(pg, ids, status):
    job = _add_job(pg)
    _add_row(pg, job, ids.p1, ids.box, status=status, basis="R2:甲")
    _add_row(pg, job, ids.p2, ids.case, status="In Stock", basis="R2:乙", canonical="Case", unit="Case")
    for merge in (False, True):
        rows = _rows(pg, merge=merge)
        assert [r["status"] for r in rows] == ["In Stock"]


def _view_items(pg_fixture, *, sort: str, order: str, fresh_only: bool = False) -> tuple[int, list[dict]]:
    from app.routers.inventory_offers import _SORT_COLUMNS, _build_inventory_view_sql, _build_view_filters

    none = dict.fromkeys(("q", "work_code", "category", "offer_type", "hide_supplier_ids", "hide_categories", "condition",
                          "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max", "price_min", "price_max"))
    conditions, params = _build_view_filters(**none)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    # API と同じ: 年齢窓は 48h。fresh_only のときは窓そのものを24hにする（便2）
    age_condition, age_params = distribution._age_window(distribution.FRESH_WINDOW_HOURS if fresh_only else 48)
    params = {**params, **age_params}
    head, final = distribution.distribution_rows_parts(
        include_flag_single=False, age_condition=age_condition, merge_same_post=False)
    sql = _build_inventory_view_sql(head=head, final_main=final, merge=False, where=where,
                                    sort_col=_SORT_COLUMNS[sort], order_dir=order.upper())
    total, pages = 0, []
    with Session(pg_fixture[1]) as session:
        for r in session.execute(text(sql), {**params, "limit": 50, "offset": 0}).mappings().all():
            if r["__kind"] == "total":
                total = int(r["__total"])
            elif r["__kind"] == "page":
                pages.append((r["__ord"], dict(r)))
    pages.sort(key=lambda t: t[0])
    return total, [p for _, p in pages]


def test_work_code_comes_from_work_id_not_tcg_type(pg, ids):
    """tcg_type が NULL でも work_id の商品は work_code で出る。別の work_id の商品は出ない（ADR-1030）。"""
    from app.routers.inventory_offers import _SORT_COLUMNS, _build_inventory_view_sql, _build_view_filters

    with pg[0].cursor() as cur:
        # この試験は写しの列に頼らない。tcg_type には値を入れない（NULL のまま）。
        cur.execute("UPDATE public.products SET work_id = (SELECT id FROM public.type_master WHERE code = 'T_A') "
                    "WHERE id = %s", (ids.p1,))
    job = _add_job(pg)
    _add_row(pg, job, ids.p1, ids.box, basis="R2:甲", price=1000)
    _add_row(pg, job, ids.p2, ids.case, basis="R2:乙", canonical="Case", unit="Case", price=2000)
    none = dict.fromkeys(("q", "work_code", "category", "offer_type", "hide_supplier_ids", "hide_categories",
                          "condition", "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max",
                          "price_min", "price_max"))
    none["work_code"] = "T_A"
    conditions, params = _build_view_filters(**none)
    where = "WHERE " + " AND ".join(conditions)
    head, final = distribution.distribution_rows_parts(**_ARGS, merge_same_post=False)
    sql = _build_inventory_view_sql(head=head, final_main=final, merge=False, where=where,
                                    sort_col=_SORT_COLUMNS["release_date"], order_dir="DESC")
    with Session(pg[1]) as session:
        rows = [dict(r) for r in session.execute(text(sql), {**params, "limit": 50, "offset": 0}).mappings().all()
                if r["__kind"] == "page"]
    assert len(rows) == 1
    assert rows[0]["work_code"] == "T_A"
    assert rows[0]["product_id"] == ids.p1


def test_bin1_fresh_only_excludes_rows_older_than_24_hours_and_total_follows(pg, ids):
    _add_row(pg, _add_job(pg, 1), ids.p1, ids.box, basis="R2:甲")
    _add_row(pg, _add_job(pg, 30), ids.p2, ids.case, basis="R2:乙", canonical="Case", unit="Case")
    total_all, items_all = _view_items(pg, sort="release_date", order="desc")
    total_fresh, items_fresh = _view_items(pg, sort="release_date", order="desc", fresh_only=True)
    assert total_all == len(items_all) == 2
    assert total_fresh == len(items_fresh) == 1


def _expiry_s(pg_fixture, *, max_age_hours: int, fresh_only: bool):
    """API（list_inventory_view）と同じ窓の決め方で、total 枝の __expiry_s を返す（便4）。"""
    from app.routers.inventory_offers import _SORT_COLUMNS, _build_inventory_view_sql, _build_view_filters

    none = dict.fromkeys(("q", "work_code", "category", "offer_type", "hide_supplier_ids", "hide_categories", "condition",
                          "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max", "price_min", "price_max"))
    conditions, params = _build_view_filters(**none)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    window_hours = max_age_hours
    if fresh_only:
        window_hours = (min(max_age_hours, distribution.FRESH_WINDOW_HOURS) if max_age_hours
                        else distribution.FRESH_WINDOW_HOURS)
    age_condition, age_params = distribution._age_window(window_hours)
    params = {**params, **age_params}
    expiry = bool(window_hours)
    if expiry:
        params["expiry_hours"] = window_hours
    head, final = distribution.distribution_rows_parts(
        include_flag_single=False, age_condition=age_condition, merge_same_post=False)
    sql = _build_inventory_view_sql(head=head, final_main=final, merge=False, where=where,
                                    sort_col=_SORT_COLUMNS["release_date"], order_dir="DESC", expiry=expiry)
    with Session(pg_fixture[1]) as session:
        for r in session.execute(text(sql), {**params, "limit": 50, "offset": 0}).mappings().all():
            if r["__kind"] == "total":
                return r["__expiry_s"]
    raise AssertionError("total 枝が無い")


def test_bin4_expiry_seconds_for_row_posted_23h_ago(pg, ids):
    _add_row(pg, _add_job(pg, 23), ids.p1, ids.box, basis="R2:甲")
    assert abs(_expiry_s(pg, max_age_hours=24, fresh_only=False) - 3600) <= 120


def test_bin4_expiry_is_none_when_window_is_unbounded(pg, ids):
    _add_row(pg, _add_job(pg, 23), ids.p1, ids.box, basis="R2:甲")
    assert _expiry_s(pg, max_age_hours=0, fresh_only=False) is None


def test_bin4_expiry_uses_24h_basis_when_fresh_only_and_max_age_is_zero(pg, ids):
    _add_row(pg, _add_job(pg, 23), ids.p1, ids.box, basis="R2:甲")
    assert abs(_expiry_s(pg, max_age_hours=0, fresh_only=True) - 3600) <= 120


def test_bin4_expiry_uses_24h_basis_when_fresh_only_and_max_age_is_48(pg, ids):
    _add_row(pg, _add_job(pg, 23), ids.p1, ids.box, basis="R2:甲")
    assert abs(_expiry_s(pg, max_age_hours=48, fresh_only=True) - 3600) <= 120


def test_bin4_expiry_is_none_when_no_rows(pg, ids):
    assert _expiry_s(pg, max_age_hours=24, fresh_only=False) is None


def test_bin1_sort_groups_by_release_date_then_title(pg, ids):
    with pg[0].cursor() as cur:
        cur.execute("UPDATE public.products SET name_en = 'Alpha', release_date = '2026-02-01' WHERE id = %s", (ids.p1,))
        cur.execute("UPDATE public.products SET name_en = 'Beta', release_date = '2026-01-01' WHERE id = %s", (ids.p2,))
    job = _add_job(pg)
    _add_row(pg, job, ids.p1, ids.box, basis="R2:甲", price=1)
    _add_row(pg, job, ids.p2, ids.case, basis="R2:乙", price=2, canonical="Case", unit="Case")
    _add_row(pg, job, ids.p1, ids.box, basis="R2:丙", price=3, note="N")
    _, items = _view_items(pg, sort="release_date", order="asc")
    assert [r["english_title"] for r in items] == ["Beta", "Alpha", "Alpha"]  # 発売日の早い商品が先
    _, items_desc = _view_items(pg, sort="release_date", order="desc")
    assert [r["english_title"] for r in items_desc] == ["Alpha", "Alpha", "Beta"]
    _, by_price = _view_items(pg, sort="unit_price", order="desc")
    assert [r["english_title"] for r in by_price] == ["Alpha", "Alpha", "Beta"]  # まとまりの順は既定と同じ発売日の新しい順（ADR-1014 改訂 2026-10-19）
    _, by_name_desc = _view_items(pg, sort="name", order="desc")
    assert [r["english_title"] for r in by_name_desc] == ["Beta", "Alpha", "Alpha"]
    _, by_name_asc = _view_items(pg, sort="name", order="asc")
    assert [r["english_title"] for r in by_name_asc] == ["Alpha", "Alpha", "Beta"]


def test_bin1_empty_release_date_comes_last_in_both_directions(pg, ids):
    with pg[0].cursor() as cur:
        cur.execute("UPDATE public.products SET name_en = 'Alpha', release_date = NULL WHERE id = %s", (ids.p1,))
        cur.execute("UPDATE public.products SET name_en = 'Beta', release_date = '2026-01-01' WHERE id = %s", (ids.p2,))
    job = _add_job(pg)
    _add_row(pg, job, ids.p2, ids.case, basis="R2:乙", canonical="Case", unit="Case")
    _add_row(pg, job, ids.p1, ids.box, basis="R2:甲")
    for order in ("asc", "desc"):
        _, items = _view_items(pg, sort="release_date", order=order)
        assert [r["english_title"] for r in items] == ["Beta", "Alpha"]


# --- 便3（検索と提供者）-------------------------------------------------------------------------------------------
# 検索の正規化ベクタは frontend/src/features/inventory/searchNormalize.vectors.json（frontend の vitest も同じ物を読む）。
# ベクタを変えるときは、このファイルと frontend/src/features/inventory/searchNormalize.test.ts の両方を触ること。


def _set_supplier(pg_fixture, job_id: str, name: str) -> int:
    """job の投稿を、新しく作る仕入元（name）の窓口に付け替える。仕入元 id を返す。"""
    with pg_fixture[0].cursor() as cur:
        cur.execute("INSERT INTO public.suppliers(name) VALUES (%s) RETURNING id", (name,))
        supplier_id = cur.fetchone()[0]
        cur.execute(
            f"INSERT INTO {SCHEMA}.supplier_channels(channel, external_id, is_active, supplier_id) "
            "VALUES ('line', %s, true, %s) RETURNING id",
            (f"bin3-{supplier_id}", supplier_id),
        )
        channel_id = cur.fetchone()[0]
        cur.execute(
            f"UPDATE {SCHEMA}.source_messages SET supplier_channel_id = %s "
            f"WHERE id = (SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id = %s)",
            (channel_id, job_id),
        )
    return supplier_id


def _search_items(pg_fixture, **overrides) -> tuple[int, list[str]]:
    """GET /inventory と同じ絞り込みで (total, 並べた日本語名) を返す。"""
    from app.routers.inventory_offers import _SORT_COLUMNS, _build_inventory_view_sql, _build_view_filters

    none = dict.fromkeys(("q", "work_code", "category", "offer_type", "hide_supplier_ids", "hide_categories", "condition",
                          "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max", "price_min", "price_max"))
    conditions, params = _build_view_filters(**{**none, **overrides})
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    head, final = distribution.distribution_rows_parts(**_ARGS, merge_same_post=False)
    sql = _build_inventory_view_sql(head=head, final_main=final, merge=False, where=where,
                                    sort_col=_SORT_COLUMNS["name"], order_dir="ASC")
    total, pages = 0, []
    with Session(pg_fixture[1]) as session:
        for r in session.execute(text(sql), {**params, "limit": 50, "offset": 0}).mappings().all():
            if r["__kind"] == "total":
                total = int(r["__total"])
            elif r["__kind"] == "page":
                pages.append((r["__ord"], r["japanese_title"]))
    pages.sort(key=lambda t: t[0])
    return total, [name for _, name in pages]


@pytest.fixture
def searchable(pg, ids):
    """p1 = ポケモンカード(英名 Pokemon Card・mark SV1)、p2 = ワンピース(英名 ABC Booster・検索ワード ルフィ)。仕入元は別々。"""
    with pg[0].cursor() as cur:
        cur.execute("UPDATE public.products SET name = 'ポケモンカード', name_en = 'Pokemon Card', mark = 'SV1' WHERE id = %s", (ids.p1,))
        cur.execute("UPDATE public.products SET name = 'ワンピース', name_en = 'ABC Booster', mark = 'OP01' WHERE id = %s", (ids.p2,))
        cur.execute("INSERT INTO public.product_search_keywords(product_id,keyword,position) VALUES (%s,'ルフィ',0)", (ids.p2,))
    job1, job2 = _add_job(pg), _add_job(pg)
    s1 = _set_supplier(pg, job1, "甲提供者")
    s2 = _set_supplier(pg, job2, "乙提供者")
    _add_row(pg, job1, ids.p1, ids.box, basis="R2:甲")
    _add_row(pg, job2, ids.p2, ids.case, basis="R2:乙", canonical="Case", unit="Case")
    return SimpleNamespace(s1=s1, s2=s2)


_BIN3_SEARCH_CASES = [
    ("ぽけもん", ["ポケモンカード"]),   # ひらがな → カタカナ
    ("ポケモン", ["ポケモンカード"]),
    ("ＡＢＣ", ["ワンピース"]),          # 全角英数 → 半角小文字（英名 ABC Booster に当たる）
    ("abc", ["ワンピース"]),
    ("ぽけもん ｐｏｋｅｍｏｎ", ["ポケモンカード"]),  # 2語 AND（両方含む）
    ("ぽけもん abc", []),                 # 2語 AND（片方しか含まない行は出ない）
    ("ルフィ", ["ワンピース"]),           # 検索ワードだけに含む語で当たる
    ("sv1", ["ポケモンカード"]),          # mark（型番）
    ("甲提供者", []),                     # 提供者名では当たらない
    ("   ", ["ポケモンカード", "ワンピース"]),  # 空白だけは全件
]


def test_bin3_search_and_supplier_filters(pg, ids, searchable):
    """pg フィクスチャは DB を作り捨てずに残すため、CI の /dev/shm を使い切らないよう 1 関数にまとめている。"""
    import json
    import pathlib

    from app.routers.inventory_offers import _KANA_FROM, _KANA_TO, normalize_search_text

    # 検索の正規化と AND
    for q, expected in _BIN3_SEARCH_CASES:
        total, names = _search_items(pg, q=q)
        assert sorted(names) == sorted(expected), q
        assert total == len(expected), q

    # Python と SQL の正規化が共有ベクタで一致する
    vectors = json.loads((pathlib.Path(__file__).resolve().parents[2] / "frontend/src/features/inventory/searchNormalize.vectors.json").read_text())
    with Session(pg[1]) as session:
        for v in vectors:
            assert normalize_search_text(v["input"]) == v["expected"]
            sql_value = session.execute(
                text("SELECT translate(lower(normalize(CAST(:s AS text), NFKC)), CAST(:f AS text), CAST(:t AS text))"),
                {"s": v["input"], "f": _KANA_FROM, "t": _KANA_TO},
            ).scalar_one()
            assert sql_value == v["expected"], v

    # 選んだ提供者だけを表示
    both = f"{searchable.s1},{searchable.s2}"
    assert _search_items(pg, supplier_ids=both)[0] == 2
    assert _search_items(pg, supplier_ids=str(searchable.s1)) == (1, ["ポケモンカード"])
    assert _search_items(pg, supplier_ids=str(searchable.s2)) == (1, ["ワンピース"])
    assert _search_items(pg, supplier_ids="x,y")[0] == 2     # 整数が1つも無ければ絞らない
    assert _search_items(pg, supplier_ids="")[0] == 2
    assert _search_items(pg, supplier_ids=f"x,{searchable.s2}") == (1, ["ワンピース"])  # 整数だけ採る

    # supplier_ids と hide_supplier_ids の併用
    assert _search_items(pg, hide_supplier_ids=str(searchable.s1)) == (1, ["ワンピース"])
    assert _search_items(pg, supplier_ids=f"{searchable.s1},{searchable.s2}", hide_supplier_ids=str(searchable.s1)) == (1, ["ワンピース"])


# --- ADR-1014 改訂 2026-10-19（2）: 同じ商品のまとまりの最安・在庫最多バッジ ------------------------------


def _badge_rows(session, *, merge, where, params, limit, offset):
    """page の行の (__ord, __badge_cheapest, __badge_most_stock, row_key) を __ord 順に返す。

    前例 _view_items と同じ形（同期の Session で _build_inventory_view_sql を直接流す）。
    並びは release_date DESC に固定し、年齢の窓は _ARGS（窓なし）を使う。where / params は _build_view_filters の値。
    """
    from app.routers.inventory_offers import _SORT_COLUMNS, _build_inventory_view_sql

    head, final = distribution.distribution_rows_parts(**_ARGS, merge_same_post=merge)
    sql = _build_inventory_view_sql(head=head, final_main=final, merge=merge, where=where,
                                    sort_col=_SORT_COLUMNS["release_date"], order_dir="DESC")
    out = []
    for r in session.execute(text(sql), {**params, "limit": limit, "offset": offset}).mappings().all():
        if r["__kind"] == "page":
            out.append((r["__ord"], r["__badge_cheapest"], r["__badge_most_stock"], r["row_key"]))
    return sorted(out, key=lambda t: t[0])


def _badge_filters(**overrides):
    from app.routers.inventory_offers import _build_view_filters

    none = dict.fromkeys(("q", "work_code", "category", "offer_type", "hide_supplier_ids", "hide_categories", "condition",
                          "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max", "price_min", "price_max"))
    conditions, params = _build_view_filters(**{**none, **overrides})
    return (("WHERE " + " AND ".join(conditions)) if conditions else ""), params


def _badges_by_key(pg_fixture, *, merge=False, limit=50, offset=0, **filters) -> dict:
    where, params = _badge_filters(**filters)
    with Session(pg_fixture[1]) as session:
        rows = _badge_rows(session, merge=merge, where=where, params=params, limit=limit, offset=offset)
    return {key: (cheap, most) for _, cheap, most, key in rows}


def test_b1_cheapest_and_most_stock_mark_every_row_equal_to_the_extreme(pg, ids):
    job = _add_job(pg)
    a = _add_row(pg, job, ids.p1, ids.box, note="a", price=100, qty=10)
    b = _add_row(pg, job, ids.p1, ids.box, note="b", price=200, qty=20)
    c = _add_row(pg, job, ids.p1, ids.box, note="c", price=100, qty=20)
    got = _badges_by_key(pg)
    assert got[a] == (True, False)
    assert got[b] == (False, True)
    assert got[c] == (True, True)


def test_b2_no_badge_for_single_row_or_all_same_values(pg, ids):
    job = _add_job(pg)
    s1 = _add_row(pg, job, ids.p1, ids.box, note="s1", price=100, qty=5)  # p1: 全部同じ価格・同じ数量
    s2 = _add_row(pg, job, ids.p1, ids.box, note="s2", price=100, qty=5)
    only = _add_row(pg, job, ids.p2, ids.box, note="only", price=100, qty=5)  # p2: 1行だけ
    got = _badges_by_key(pg)
    assert got[s1] == got[s2] == got[only] == (False, False)


def test_b2_empty_quantity_is_left_out_of_most_stock(pg, ids):
    job = _add_job(pg)
    a = _add_row(pg, job, ids.p1, ids.box, note="a", price=100, qty=None)
    b = _add_row(pg, job, ids.p1, ids.box, note="b", price=200, qty=5)
    c = _add_row(pg, job, ids.p1, ids.box, note="c", price=300, qty=9)
    got = _badges_by_key(pg)
    assert got[a] == (True, False)  # 数量が空の行は在庫最多の比べから外れる
    assert got[b] == (False, False)
    assert got[c] == (False, True)


def test_b2_empty_quantity_only_one_valued_row_gets_no_most_stock(pg, ids):
    job = _add_job(pg)
    a = _add_row(pg, job, ids.p1, ids.box, note="a", price=100, qty=None)
    b = _add_row(pg, job, ids.p1, ids.box, note="b", price=200, qty=5)
    got = _badges_by_key(pg)
    assert got[a] == (True, False)
    assert got[b] == (False, False)  # 数量のある行が1行だけなので付けない


def test_b3_badges_are_decided_within_the_filtered_rows(pg, ids):
    job = _add_job(pg)
    a = _add_row(pg, job, ids.p1, ids.box, note="a", price=100, qty=1)
    b = _add_row(pg, job, ids.p1, ids.box, note="b", price=200, qty=1)
    c = _add_row(pg, job, ids.p1, ids.box, note="c", price=300, qty=1)
    assert _badges_by_key(pg)[a][0] is True
    got = _badges_by_key(pg, price_min=200)  # a が絞り込みで消え、残りの b が最安になる
    assert a not in got and got[b] == (True, False) and got[c] == (False, False)
    assert _badges_by_key(pg, price_min=300) == {c: (False, False)}  # 1行だけ残ると付かない


def test_b3_badges_are_decided_across_pages(pg, ids):
    job = _add_job(pg)
    keys = [_add_row(pg, job, ids.p1, ids.box, note=f"n{i}", price=100 + i * 100, qty=1) for i in range(3)]
    seen: dict = {}
    for offset in range(3):  # per_page=1 で1行ずつ取る
        page = _badges_by_key(pg, limit=1, offset=offset)
        assert len(page) == 1
        seen.update(page)
    assert set(seen) == set(keys)
    assert [seen[k][0] for k in keys] == [True, False, False]  # どのページでも、まとまり全体で最安が決まる


def test_b3b_merge_mode_compares_the_values_shown_on_screen(pg, ids):
    job = _add_job(pg)
    merged_first = _add_row(pg, job, ids.p1, ids.box, note="X", basis="R2:甲", price=1000, qty=3)
    _add_row(pg, job, ids.p1, ids.box, note="X", basis="R2:乙", price=1200, qty=4)  # まとめると 数量7・単価1200
    other = _add_row(pg, job, ids.p1, ids.box, note="Y", price=1100, qty=5)
    got = _badges_by_key(pg, merge=True)
    assert set(got) == {merged_first, other}
    assert got[merged_first] == (False, True)  # 合計数量 7 > 5
    assert got[other] == (True, False)  # まとめた行の単価は最大の 1200、other は 1100


# --- ADR-1014 改訂 2026-10-19（3）: 比べる単位は 同じ商品・ステータス・状態 ---------------------------------


@pytest.mark.parametrize("merge", [False, True])
def test_f1_different_status_is_compared_separately(pg, ids, merge):
    job = _add_job(pg)
    a1 = _add_row(pg, job, ids.p1, ids.box, note="a1", status="In Stock", price=100, qty=5)
    a2 = _add_row(pg, job, ids.p1, ids.box, note="a2", status="In Stock", price=200, qty=9)
    b1 = _add_row(pg, job, ids.p1, ids.box, note="b1", status="Pre-order", price=300, qty=1)
    b2 = _add_row(pg, job, ids.p1, ids.box, note="b2", status="Pre-order", price=400, qty=3)
    got = _badges_by_key(pg, merge=merge)
    assert got[a1] == (True, False)
    assert got[a2] == (False, True)
    assert got[b1] == (True, False)
    assert got[b2] == (False, True)


@pytest.mark.parametrize("merge", [False, True])
def test_f2_different_condition_is_compared_separately(pg, ids, merge):
    job = _add_job(pg)
    a1 = _add_row(pg, job, ids.p1, ids.box, note="a1", price=100, qty=5)
    a2 = _add_row(pg, job, ids.p1, ids.box, note="a2", price=200, qty=9)
    c1 = _add_row(pg, job, ids.p1, ids.case, note="c1", price=500, qty=1, canonical="Case", unit="Case")
    c2 = _add_row(pg, job, ids.p1, ids.case, note="c2", price=600, qty=3, canonical="Case", unit="Case")
    got = _badges_by_key(pg, merge=merge)
    assert got[a1] == (True, False)
    assert got[a2] == (False, True)
    assert got[c1] == (True, False)
    assert got[c2] == (False, True)


@pytest.mark.parametrize("merge", [False, True])
def test_f2b_a_group_with_a_single_row_gets_no_badge(pg, ids, merge):
    job = _add_job(pg)
    a1 = _add_row(pg, job, ids.p1, ids.box, note="a1", price=100, qty=5)
    a2 = _add_row(pg, job, ids.p1, ids.box, note="a2", price=200, qty=9)
    c = _add_row(pg, job, ids.p1, ids.case, note="c", price=500, qty=50, canonical="Case", unit="Case")
    got = _badges_by_key(pg, merge=merge)
    assert got[c] == (False, False)  # 旧規則（商品だけで比べる）なら数量50 に在庫最多が付く
    assert got[a1] == (True, False)
    assert got[a2] == (False, True)


# --- 並び替えは「商品 → 状態」のまとまりの中だけ（ADR-1014 改訂 2026-10-19（5））----------------------------------------


def _seed_interleaved(pg_fixture, ids) -> None:
    """同じ商品に状態2つ。価格・数量が状態をまたいで交互になる（ブロックが無ければ状態が混ざる並び）。"""
    job = _add_job(pg_fixture)
    for price, qty, cond, canon, unit in (
        (1000, 1, ids.box, "Sealed box", "Box"), (2000, 8, ids.case, "Case", "Case"),
        (3000, 2, ids.box, "Sealed box", "Box"), (4000, 7, ids.case, "Case", "Case"),
    ):
        _add_row(pg_fixture, job, ids.p1, cond, basis=f"R2:{price}", price=price, qty=qty, canonical=canon, unit=unit)


def _view_page(pg_fixture, sort: str, order_dir: str) -> list[dict]:
    from app.routers.inventory_offers import _SORT_COLUMNS

    with Session(pg_fixture[1]) as session:
        _, page, _ = _new_single_statement(
            session, merge=False, where="", params={}, sort_col=_SORT_COLUMNS[sort], order_dir=order_dir,
            limit=50, offset=0)
    return page


def _default_condition_order(pg_fixture) -> list[str]:
    seen: list[str] = []
    for r in _view_page(pg_fixture, "release_date", "DESC"):
        if r["condition"] not in seen:
            seen.append(r["condition"])
    return seen


def test_s1_price_sort_keeps_condition_blocks_in_default_order(pg, ids):
    _seed_interleaved(pg, ids)
    default_order = _default_condition_order(pg)
    assert len(default_order) == 2
    page = _view_page(pg, "unit_price", "ASC")
    assert [r["condition"] for r in page] == [c for c in default_order for _ in range(2)]
    for cond in default_order:
        prices = [r["price_num"] for r in page if r["condition"] == cond]
        assert prices == sorted(prices)
    page_desc = _view_page(pg, "unit_price", "DESC")
    assert [r["condition"] for r in page_desc] == [c for c in default_order for _ in range(2)]
    for cond in default_order:
        prices = [r["price_num"] for r in page_desc if r["condition"] == cond]
        assert prices == sorted(prices, reverse=True)


def test_s2_quantity_sort_keeps_condition_blocks_in_default_order(pg, ids):
    _seed_interleaved(pg, ids)
    default_order = _default_condition_order(pg)
    page = _view_page(pg, "quantity", "DESC")
    assert [r["condition"] for r in page] == [c for c in default_order for _ in range(2)]
    for cond in default_order:
        qtys = [r["qty_num"] for r in page if r["condition"] == cond]
        assert qtys == sorted(qtys, reverse=True)
