# ruff: noqa: F811
"""要確認・在庫表スライドの API が、その投稿の最新の completed 試行の thought_summaries を返す PostgreSQL 試験（CI の使い捨て PostgreSQL 専用）。値はすべて架空。

C1: failed と古い completed があっても、最新の completed の要約だけが返る。
C2: 試行が無い投稿は thought_summaries が None。
pg fixture は試験ごとに DB を作って終わりに DROP するので、後始末は書かない（test_tcg_work_matching_integration.py の pg）。
"""
from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tests.test_inventory_distribution_rows_pg import _add_job, _add_row, _item_id_of
from tests.test_inventory_distribution_rows_pg import ids as ids  # noqa: F401  fixture
from tests.test_line_analysis_v102_pg import v102 as v102  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")


def _add_attempt(pg_fixture, job_id: str, phase: str, started_at: str, summaries: str | None) -> None:
    """試行を1件入れる（completed / failed は finished_at 必須、completed は応答の列も必須）。"""
    done = phase in ("completed", "failed")
    completed = phase == "completed"
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.extraction_attempts
                (id, extraction_job_id, source_message_id, started_at, phase, finished_at, input_payload, input_sha256, input_bytes,
                 requested_model, prompt_version, response_text, response_received_at, parsed_items, item_count, thought_summaries)
                SELECT %s, ej.id, ej.source_message_id, %s::timestamptz, %s, CASE WHEN %s THEN %s::timestamptz END,
                       CASE WHEN %s THEN '{{}}'::jsonb END, %s, 0, 'test-model', 'test',
                       CASE WHEN %s THEN 'x' END, CASE WHEN %s THEN %s::timestamptz END,
                       CASE WHEN %s THEN '[]'::jsonb END, CASE WHEN %s THEN 0 END, %s::jsonb
                FROM {SCHEMA}.extraction_jobs ej WHERE ej.id = %s""",
            (str(uuid4()), started_at, phase, done, started_at, completed, uuid4().hex,
             completed, completed, started_at, completed, completed, summaries, job_id),
        )


def _fetch_item(pg_fixture, monkeypatch, job: str, item_id: str) -> dict:
    from app.services import tcg_analysis_review_svc as review

    monkeypatch.setattr(review, "TCG_SCHEMA", SCHEMA)
    monkeypatch.setattr(review, "_BASE_FROM", review._base_from())

    async def _no_reason_codes(_db):  # 理由コード表は検証対象外（この pg には表が無い）
        return {}

    monkeypatch.setattr(review, "load_review_reason_codes", _no_reason_codes)

    async def _fetch() -> dict:
        engine = create_async_engine(pg_fixture[2])
        try:
            async with AsyncSession(engine) as db:
                return await review.fetch_analysis_results(db, extraction_item_ids=[item_id], limit=1)
        finally:
            await engine.dispose()

    # fetch_analysis_results は public.supplier_channels を固定で JOIN する。同じ id の行を public にも用意する（DB ごと破棄される）。
    with pg_fixture[0].cursor() as cur:
        cur.execute(
            f"""INSERT INTO public.supplier_channels (id, channel, is_active, supplier_id)
                SELECT sc.id, sc.channel, sc.is_active, sc.supplier_id FROM {SCHEMA}.supplier_channels sc
                WHERE sc.id = (SELECT sm.supplier_channel_id FROM {SCHEMA}.source_messages sm
                               JOIN {SCHEMA}.extraction_jobs ej ON ej.source_message_id = sm.id WHERE ej.id = %s)
                ON CONFLICT (id) DO NOTHING""", (job,),
        )
    data = asyncio.run(_fetch())
    assert [i["extraction_item_id"] for i in data["items"]] == [item_id]
    return data["items"][0]


def test_c1_latest_completed_attempt_summary_only(pg, ids, v102, monkeypatch):
    job = _add_job(pg)
    item_id = _item_id_of(pg, _add_row(pg, job, ids.p1, ids.box))
    _add_attempt(pg, job, "completed", "2026-10-10 00:00:00+00", '["old completed"]')
    _add_attempt(pg, job, "completed", "2026-10-11 00:00:00+00", '["latest completed"]')
    _add_attempt(pg, job, "failed", "2026-10-12 00:00:00+00", '["failed newer"]')
    assert _fetch_item(pg, monkeypatch, job, item_id)["thought_summaries"] == ["latest completed"]


def test_c2_no_attempt_returns_none(pg, ids, v102, monkeypatch):
    job = _add_job(pg)
    item_id = _item_id_of(pg, _add_row(pg, job, ids.p1, ids.box))
    assert _fetch_item(pg, monkeypatch, job, item_id)["thought_summaries"] is None
