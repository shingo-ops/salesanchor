# ruff: noqa: F811
"""v102 のシステム段が、計算（run_v102_pipeline）の間 DB の取引を開いたままにしないことの PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。

K2: 計算を呼ぶ時点と返った後で、セッションに開いた取引が無い。
K3: 計算の間に同じ投稿の人の判断が保存されたら、その判断が結果に入る（入力が変わった記録が 1 行出て、計算は 2 回）。
K3b: 計算の間に何も変わらなければ、計算は 1 回だけで入力が変わった記録は出ない。
Gemini は呼ばない。原文はすべて架空。
"""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

import app.services.line_analysis_v102_svc as svc
import app.services.v102_human_decisions_svc as decisions_svc
from tests.test_line_analysis_v102_pg import make_job, one, run_extraction
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

CHANGED_LOG = "inputs changed"


def _prepare(pg, v102):
    """抽出まで済ませた投稿と、0 番目の件の (source_id, job_id, item_id) を返す。"""
    source_id, job_id = make_job(pg)
    run_extraction(pg, job_id)
    item_id = one(
        pg, f"SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s AND gemini_index=0", (job_id,)
    )[0][0]
    return source_id, job_id, str(item_id)


def _quantity_of(pg, job_id: str):
    rows = one(
        pg,
        f"""SELECT ar.quantity_normalized FROM {SCHEMA}.analysis_results ar
            JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id
            WHERE ei.extraction_job_id=%s AND ei.gemini_index=0""",
        (job_id,),
    )
    return rows[0][0] if rows else None


def _count_changed(caplog) -> int:
    return sum(1 for r in caplog.records if CHANGED_LOG in r.getMessage())


def test_k2_no_open_transaction_while_the_pipeline_runs(pg, v102, monkeypatch):
    _source_id, job_id, _item_id = _prepare(pg, v102)
    real = svc.run_v102_pipeline
    seen: dict = {}
    holder: dict = {}

    def wrapped(*args, **kwargs):
        seen["before"] = holder["session"].in_transaction()
        result = real(*args, **kwargs)
        seen["after"] = holder["session"].in_transaction()
        return result

    monkeypatch.setattr(svc, "run_v102_pipeline", wrapped)
    with Session(pg[1]) as session:
        holder["session"] = session
        svc.run_v102_analysis(session, job_id)
    assert seen == {"before": False, "after": False}


def test_k3_a_decision_saved_during_the_pipeline_reaches_the_result(pg, v102, monkeypatch, caplog):
    source_id, job_id, item_id = _prepare(pg, v102)
    monkeypatch.setattr(decisions_svc, "TCG_SCHEMA", SCHEMA)
    real = svc.run_v102_pipeline
    state = {"calls": 0}

    def save_in_other_session() -> None:
        async def run() -> None:
            engine = create_async_engine(pg[2])  # URL 型のまま渡す（str() はパスワードを *** に伏せる）
            try:
                async with AsyncSession(engine) as db:
                    # 直す前の main では解析が鍵を持ったままなので、待たずに失敗させる
                    await db.execute(text("SET LOCAL lock_timeout = '2s'"))
                    await decisions_svc.save_value_override(
                        db, extraction_item_id=item_id, source_message_id=source_id,
                        field="quantity", value="5", corrected_by="admin@example.com",
                    )
            finally:
                await engine.dispose()

        asyncio.run(run())

    def wrapped(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:  # 保存は 1 回目の計算の中だけ。2 回目は鍵を持ったまま走る
            save_in_other_session()
        return real(*args, **kwargs)

    monkeypatch.setattr(svc, "run_v102_pipeline", wrapped)
    with caplog.at_level(logging.INFO, logger=svc.logger.name), Session(pg[1]) as session:
        svc.run_v102_analysis(session, job_id)
    assert _quantity_of(pg, job_id) == Decimal("5")
    assert _count_changed(caplog) == 1
    assert state["calls"] == 2


def test_k3b_nothing_changed_means_one_pipeline_call_and_no_changed_log(pg, v102, monkeypatch, caplog):
    _source_id, job_id, _item_id = _prepare(pg, v102)
    real = svc.run_v102_pipeline
    state = {"calls": 0}

    def wrapped(*args, **kwargs):
        state["calls"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(svc, "run_v102_pipeline", wrapped)
    with caplog.at_level(logging.INFO, logger=svc.logger.name), Session(pg[1]) as session:
        svc.run_v102_analysis(session, job_id)
    assert state["calls"] == 1
    assert _count_changed(caplog) == 0
