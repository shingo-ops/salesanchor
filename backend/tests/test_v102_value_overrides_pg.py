# ruff: noqa: F811
"""比較表から直した値（数量・単価・単位・メモ・販売状況）の PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。Gemini は呼ばない。原文はすべて架空。

再解析で人の値が残ること、書き写しの直しで無効になること、売り切れ（EXCLUDE）と在庫あり、〆の相手がある件、
同じ鍵の再解析との順番、追記のみ、一覧の system.quantity / price と manual_values。
"""
from __future__ import annotations

import asyncio
import json
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

import app.services.line_analysis_v102_svc as svc
import app.services.v102_human_decisions_svc as decisions_svc
from tests.test_line_analysis_v102_pg import make_job, one, run_analysis, run_extraction
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_v102_human_decisions_pg import (
    REASON_NOT_IN_MASTER,
    fix_product,
    in_tab,
    pf,  # noqa: F401  fixture
    prepare,
    reasons_of,
    view_of,
)
from tests.test_v102_soldout_extra_targets_pg import _extras, _inject, _target, ids  # noqa: F401  fixture

STATUS_ROWS = [("In Stock", "DEFAULT", 1), ("In Stock", "OUTPUT", 2), ("Pre-order", "OUTPUT", 3), ("Sold out", "EXCLUDE", 4)]
# 原文に当たらない検索語にする（空の語は何にでも当たり、件の販売状況が変わってしまう）。DEFAULT だけ空
STATUS_ENTRIES = [
    {"canonical": c, "effect": e, "search_pattern": "" if e == "DEFAULT" else f"ZZ{c}ZZ", "exclude_pattern": "", "priority": p, "match_type": "KEYWORD"}
    for c, e, p in STATUS_ROWS
]


@pytest.fixture
def vo(pg, v102, monkeypatch):  # noqa: F811
    """単位 Case と別名、販売状況マスタを入れる。v102 のマスタ・単位の表にも同じものを渡す。"""
    monkeypatch.setattr(decisions_svc, "TCG_SCHEMA", SCHEMA)
    with pg[0].cursor() as cur:
        cur.execute("INSERT INTO public.units(code,canonical,kubun,is_active) VALUES ('UN9002','Case','箱系',true)")
        cur.execute("INSERT INTO public.unit_aliases(unit_id,alias_text,lang) SELECT id, canonical, 'ja' FROM public.units WHERE code IN ('UN9001','UN9002')")
        for canonical, effect, priority in STATUS_ROWS:
            cur.execute(
                """INSERT INTO public.tcg_status_master(status_id, canonical, search_pattern, exclude_pattern, priority, match_type, effect, enabled)
                   VALUES (%s, %s, '', '', %s, 'KEYWORD', %s, TRUE)""",
                (f"ST{priority:04d}", canonical, priority, effect),
            )
    v102.masters["status_entries"] = STATUS_ENTRIES
    unit_ids = {canonical: uid for uid, canonical in one(pg, "SELECT id, canonical FROM public.units WHERE code IN ('UN9001','UN9002')")}
    monkeypatch.setattr(svc, "load_v102_masters", lambda _s: (v102.masters, unit_ids))
    return v102


def save(pg_fixture, source_id: str, item_id: str, field: str, value: str) -> int:
    async def run() -> int:
        engine = create_async_engine(pg_fixture[2])
        try:
            async with AsyncSession(engine) as db:
                return await decisions_svc.save_value_override(
                    db, extraction_item_id=item_id, source_message_id=source_id, field=field, value=value, corrected_by="admin@example.com",
                )
        finally:
            await engine.dispose()

    return asyncio.run(run())


def values_of(pg_fixture, job_id: str) -> dict:
    keys = ("quantity_normalized", "price_normalized", "unit_canonical", "unit_resolved", "note_ja", "status", "exclusion")
    row = one(pg_fixture, f"""SELECT {', '.join('ar.' + k for k in keys)} FROM {SCHEMA}.analysis_results ar
        JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s""", (job_id,))[0]
    return dict(zip(keys, row, strict=True))


def count_rows(pg_fixture, item_id: str, field: str | None = None) -> int:
    sql = f"SELECT count(*) FROM {SCHEMA}.item_corrections WHERE extraction_item_id=%s"
    if field:
        return one(pg_fixture, sql + " AND field_name=%s", (item_id, field))[0][0]
    return one(pg_fixture, sql, (item_id,))[0][0]


# --- 5項目が再解析で残る・書き写しの直しで無効 ----------------------------------------------------------


def test_the_five_overrides_survive_reanalysis(pg, vo, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    for field, value in (("quantity", "5"), ("price", "1200.5"), ("unit", "Case"), ("note", "人のメモ"), ("status", "Pre-order")):
        assert save(pg, source_id, item_id, field, value) == 1
    expected = {
        "quantity_normalized": Decimal("5"), "price_normalized": Decimal("1200.50"), "unit_canonical": "Case", "unit_resolved": True,
        "note_ja": "人のメモ", "status": "Pre-order", "exclusion": None,
    }
    assert values_of(pg, job_id) == expected  # 保存の直後にも、再解析を待たず反映される
    for _ in range(2):
        run_analysis(pg, job_id)
        assert values_of(pg, job_id) == expected


def test_a_transcription_fix_invalidates_the_overrides(pg, vo, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    before = values_of(pg, job_id)
    assert save(pg, source_id, item_id, "quantity", "9") == 1
    run_analysis(pg, job_id)
    assert values_of(pg, job_id)["quantity_normalized"] == Decimal("9")
    with pg[0].cursor() as cur:  # 書き写しの直しは、人の値より後の時刻にする
        cur.execute(
            f"""INSERT INTO {SCHEMA}.item_corrections(extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by, corrected_at)
                VALUES (%s, %s, 'v102_price', '', '1,000円', 'test', now() + interval '1 minute')""",
            (item_id, source_id),
        )
    run_analysis(pg, job_id)
    assert values_of(pg, job_id)["quantity_normalized"] == before["quantity_normalized"]


# --- 売り切れと在庫あり ---------------------------------------------------------------------------------


def test_sold_out_excludes_acks_the_reason_and_in_stock_brings_it_back(pg, vo, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    fix_product(pg, (source_id, job_id, item_id), pf.p_a, at=10)  # 他の理由を片付ける
    assert save(pg, source_id, item_id, "status", "Sold out") == 1
    now = values_of(pg, job_id)
    assert (now["status"], now["exclusion"]) == ("Sold out", "excluded")
    with Session(pg[1]) as session:
        assert "excluded" in decisions_svc.load_v102_decisions(session, [item_id])[item_id].ack_codes
    assert view_of(pg, item_id)["excluded_acked"] is True
    assert in_tab(pg, item_id, "NEEDS_REVIEW") is False and in_tab(pg, item_id, "ACKED") is True
    run_analysis(pg, job_id)
    assert values_of(pg, job_id)["exclusion"] == "excluded" and in_tab(pg, item_id, "NEEDS_REVIEW") is False
    assert save(pg, source_id, item_id, "status", "In Stock") == 1
    back = values_of(pg, job_id)
    assert (back["status"], back["exclusion"]) == ("In Stock", None)
    run_analysis(pg, job_id)
    assert values_of(pg, job_id)["exclusion"] is None


# --- 〆の相手がある件を在庫ありに直す -------------------------------------------------------------------


def test_in_stock_override_stops_the_extra_targets_but_keeps_the_status(pg, vo, ids, monkeypatch):
    _inject(monkeypatch, [_target(ids.p1, ids.box, 1), _target(ids.p1, ids.case, 2), _target(ids.p2, ids.box, 3)])
    source_id, job = make_job(pg)
    run_extraction(pg, job)
    run_analysis(pg, job)
    assert len(_extras(pg, job)) == 2
    item_id = one(pg, f"SELECT id::text FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s AND gemini_index=0", (job,))[0][0]
    assert save(pg, source_id, item_id, "status", "In Stock") == 1
    run_analysis(pg, job)
    assert _extras(pg, job) == []
    assert values_of(pg, job)["status"] == "In Stock"
    assert save(pg, source_id, item_id, "note", "メモだけ") == 1  # 販売状況が売り切れ側（EXCLUDE）なら、相手を止めない
    assert save(pg, source_id, item_id, "status", "Sold out") == 1
    run_analysis(pg, job)
    assert len(_extras(pg, job)) == 2


# --- 再解析との順番・追記のみ ---------------------------------------------------------------------------


def test_save_waits_while_the_same_job_lock_is_held(pg, vo, pf):
    source_id, job_id, item_id = prepare(pg, 0)

    async def scenario() -> None:
        engine = create_async_engine(pg[2])
        holder = Session(pg[1])
        try:
            holder.execute(text(decisions_svc._LOCK_SQL), {"key": f"v102_analysis:{job_id}"})
            async def run() -> int:
                async with AsyncSession(engine) as db:
                    return await decisions_svc.save_value_override(
                        db, extraction_item_id=item_id, source_message_id=source_id, field="quantity", value="7", corrected_by="admin@example.com",
                    )
            task = asyncio.create_task(run())
            await asyncio.sleep(1.5)
            assert not task.done()  # 再解析が鍵を持つ間は待つ
            holder.commit()
            assert await asyncio.wait_for(task, 30) == 1
        finally:
            holder.close()
            await engine.dispose()

    asyncio.run(scenario())
    assert values_of(pg, job_id)["quantity_normalized"] == Decimal("7")


def test_item_corrections_is_append_only(pg, vo, pf):
    source_id, _job_id, item_id = prepare(pg, 0)
    save(pg, source_id, item_id, "quantity", "4")
    first = one(pg, f"SELECT id, human_value FROM {SCHEMA}.item_corrections WHERE extraction_item_id=%s AND field_name='override_quantity'", (item_id,))
    assert len(first) == 1 and json.loads(first[0][1]) == {"v": 1, "value": "4"}
    before = count_rows(pg, item_id)
    save(pg, source_id, item_id, "quantity", "6")
    assert count_rows(pg, item_id) == before + 1  # 前の行は残る
    assert count_rows(pg, item_id, "override_quantity") == 2
    assert first[0] in one(pg, f"SELECT id, human_value FROM {SCHEMA}.item_corrections WHERE extraction_item_id=%s AND field_name='override_quantity'", (item_id,))


def test_a_rejected_value_writes_nothing(pg, vo, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    before, values = count_rows(pg, item_id), values_of(pg, job_id)
    for field, value in (("quantity", "-1"), ("price", "1.005"), ("unit", "Pallet"), ("status", "Heading"), ("note", "x" * 2001)):
        with pytest.raises(decisions_svc.DecisionRejected) as caught:
            save(pg, source_id, item_id, field, value)
        assert caught.value.status == 422
    assert count_rows(pg, item_id) == before and values_of(pg, job_id) == values


def test_reason_codes_are_not_changed_by_value_overrides(pg, vo, pf):
    source_id, job_id, item_id = prepare(pg, 0)
    before = reasons_of(pg, job_id)
    save(pg, source_id, item_id, "price", "1500")
    run_analysis(pg, job_id)
    assert REASON_NOT_IN_MASTER in before and reasons_of(pg, job_id) == before
