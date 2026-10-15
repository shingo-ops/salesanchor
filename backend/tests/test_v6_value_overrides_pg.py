# ruff: noqa: F811
"""v6 の件に人が直した値（数量・販売状況）が、v6 の再解析（analyze_extraction_job）で残ることと、同じ鍵で順番になることの PostgreSQL 試験。

CI の使い捨て PostgreSQL 専用（Gemini は呼ばない）。原文・値はすべて架空。試験は2本まで（共有の pg fixture は試験ごとに DB を作る）。
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

import app.services.v102_human_decisions_svc as decisions_svc
from app.services import tcg_analyzer_svc as analyzer
from tests.test_tcg_work_matching_integration import NORMAL, SCHEMA, record, run_message, seed_products
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import prohibit_live_gemini as prohibit_live_gemini  # noqa: F401  autouse fixture（DBプロンプト読みのスタブ）

STATUS_ROWS = [("In Stock", "DEFAULT", 1), ("In Stock", "OUTPUT", 2), ("Sold out", "EXCLUDE", 4)]


def _seed_status_master(connection) -> None:
    with connection.cursor() as cur:
        for canonical, effect, priority in STATUS_ROWS:
            pattern = "" if effect == "DEFAULT" else f"ZZ{canonical}ZZ"  # 原文に当たらない語（空の語は何にでも当たる）
            cur.execute(
                """INSERT INTO public.tcg_status_master(status_id, canonical, search_pattern, exclude_pattern, priority, match_type, effect, enabled)
                   VALUES (%s, %s, %s, '', %s, %s, %s, TRUE)""",
                (
                    f"ST{priority:04d}",
                    canonical,
                    pattern,
                    priority,
                    "DEFAULT" if effect == "DEFAULT" else "KEYWORD",
                    effect,
                ),
            )


def _save(async_url: str, source_id: str, item_id: str, field: str, value: str) -> int:
    async def run() -> int:
        engine = create_async_engine(async_url)
        try:
            async with AsyncSession(engine) as db:
                return await decisions_svc.save_value_override(
                    db,
                    extraction_item_id=item_id,
                    source_message_id=source_id,
                    field=field,
                    value=value,
                    corrected_by="admin@example.com",
                )
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _ar(connection, item_id: str) -> tuple:
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT quantity_normalized, status, exclusion FROM {SCHEMA}.analysis_results WHERE extraction_item_id=%s",
            (item_id,),
        )
        return cur.fetchone()


def test_v6_reanalysis_keeps_human_values_including_product_corrected_item(pg, monkeypatch):
    connection, engine, async_url = pg
    seed_products(connection)
    _seed_status_master(connection)
    monkeypatch.setattr(decisions_svc, "TCG_SCHEMA", SCHEMA)
    names = [NORMAL, "MEGA スタートデッキ100"]
    smid, jobid, _result = run_message(
        connection, engine, monkeypatch, "\n".join(names), [record(n, i) for i, n in enumerate(names, 1)]
    )
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT id::text FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s ORDER BY line_start", (jobid,)
        )
        plain, corrected = [row[0] for row in cur.fetchall()]
        cur.execute(  # 2件目は商品の直しがある件（再解析で UPSERT に来ない分岐）
            f"UPDATE {SCHEMA}.analysis_results SET product_id=(SELECT id FROM public.products WHERE product_code='PM0285'),pid_resolved=true,pid_basis='HUMAN:confirmed' WHERE extraction_item_id=%s",
            (corrected,),
        )
        cur.execute(
            f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by) VALUES (%s,%s,'product_id','PM0285','test')",
            (corrected, smid),
        )
    assert _save(async_url, smid, plain, "quantity", "5") == 1
    assert _save(async_url, smid, plain, "status", "Sold out") == 1
    assert _save(async_url, smid, corrected, "quantity", "7") == 1

    with Session(engine) as session:
        analyzer.analyze_extraction_job(session, jobid)
    assert _ar(connection, plain) == (Decimal("5"), "Sold out", "excluded")  # 人の値が残り、除外は状態に合わせる
    assert _ar(connection, corrected)[0] == Decimal("7")  # 商品の直しがある件も人の値が残る

    assert _save(async_url, smid, plain, "status", "In Stock") == 1
    with Session(engine) as session:
        analyzer.analyze_extraction_job(session, jobid)
    assert _ar(connection, plain) == (Decimal("5"), "In Stock", None)

    holder = Session(engine)  # 別の接続が同じ鍵を持つ間は、解析が待たずに打ち切られる
    try:
        holder.execute(text(decisions_svc._LOCK_SQL), {"key": decisions_svc.v102_analysis_lock_key(jobid)})
        # 接続オプションで lock_timeout を持たせる（rollback されても消えない）
        timed_engine = create_engine(
            engine.url,
            connect_args={"options": "-c lock_timeout=200ms -c statement_timeout=10s"},
        )
        try:
            with Session(timed_engine) as session:
                with pytest.raises(OperationalError) as caught:
                    analyzer.analyze_extraction_job(session, jobid)
            assert getattr(caught.value.orig, "pgcode", None) == "55P03"
        finally:
            timed_engine.dispose()
    finally:
        holder.rollback()
        holder.close()
