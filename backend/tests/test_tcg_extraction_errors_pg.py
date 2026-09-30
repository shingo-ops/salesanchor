"""
DB-A3: 抽出エラー一覧 API (list_extraction_errors) の PostgreSQL 受け入れテスト。

design: docs/handoff/extraction-error-handling-status/design.md §4, §5, §7 (T2, T3, T4, T5)

pg フィクスチャは disposable CI PostgreSQL サービス限定
（GITHUB_ACTIONS=="true" 前提。ローカル実行は不可 — 既存の *_pg.py と同じ制約）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.routers import tcg_analysis_dashboard as router_module
from app.services import tcg_diagnostics_svc as diagnostics
from tests.test_tcg_extraction_record_pg import source
from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401

pytestmark = pytest.mark.asyncio

_BASE_TIME = datetime(2026, 9, 29, 0, 0, tzinfo=timezone.utc)


def add_failed_attempt(connection, job_id, source_message_id, *, minutes_offset, error_code=None, category=None):
    """extraction_attempts に phase='failed' の行を1件追加する。"""
    started_at = _BASE_TIME + timedelta(minutes=minutes_offset)
    validation_result = {"category": category, "raw": f"detail-{minutes_offset}"} if category else {}
    with connection.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.extraction_attempts
                (id, extraction_job_id, source_message_id, started_at, finished_at, phase,
                 input_sha256, input_bytes, requested_model, prompt_version,
                 error_code, validation_result)
            VALUES (%s, %s, %s, %s, %s, 'failed', %s, 1, 'synthetic-model', 'v1', %s, %s)""",
            (
                str(uuid4()), job_id, source_message_id, started_at, started_at,
                uuid4().hex, error_code, json.dumps(validation_result),
            ),
        )


def add_completed_attempt(connection, job_id, source_message_id, *, minutes_offset):
    """extraction_attempts に phase='completed' の行を1件追加する（NOT NULL 制約を満たす最小構成）。"""
    started_at = _BASE_TIME + timedelta(minutes=minutes_offset)
    with connection.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {SCHEMA}.extraction_attempts
                (id, extraction_job_id, source_message_id, started_at, response_received_at, finished_at, phase,
                 input_sha256, input_bytes, requested_model, prompt_version,
                 input_payload, response_text, response_sha256, response_bytes,
                 parsed_items, parsed_bytes, item_count, validation_result)
            VALUES (%s, %s, %s, %s, %s, %s, 'completed', %s, 1, 'synthetic-model', 'v1',
                    '{{}}', 'ok', %s, 1, '[]', 1, 0, '{{}}')""",
            (
                str(uuid4()), job_id, source_message_id, started_at, started_at, started_at,
                uuid4().hex, uuid4().hex,
            ),
        )


def set_job_status(connection, job_id, status):
    with connection.cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET status = %s WHERE id = %s", (status, job_id))


async def call_list_extraction_errors(async_url, *, status, offset=0, limit=50):
    engine = create_async_engine(async_url)
    try:
        async with AsyncSession(engine) as session:
            return await router_module.list_extraction_errors(
                status=status, offset=offset, limit=limit, db=session
            )
    finally:
        await engine.dispose()


async def test_job_without_failed_attempt_is_excluded(pg, monkeypatch):
    """T2: failed の attempt が無いジョブは一覧に出ない。"""
    connection, _, async_url = pg
    monkeypatch.setattr(router_module, "_TCG_SCHEMA", SCHEMA)
    sid, jid = source(pg)
    add_completed_attempt(connection, jid, sid, minutes_offset=0)
    set_job_status(connection, jid, "done")

    response = await call_list_extraction_errors(async_url, status="resolved")
    assert jid not in {item.id for item in response.items}


async def test_category_comes_from_latest_failed_attempt_not_latest_attempt(pg, monkeypatch):
    """T3: failed のあとに completed がある場合でも、failed 側の category が出る。"""
    connection, _, async_url = pg
    monkeypatch.setattr(router_module, "_TCG_SCHEMA", SCHEMA)
    sid, jid = source(pg)
    add_failed_attempt(connection, jid, sid, minutes_offset=0, error_code="GEMINI_TIMEOUT", category="gemini_timeout")
    add_completed_attempt(connection, jid, sid, minutes_offset=5)
    set_job_status(connection, jid, "done")

    response = await call_list_extraction_errors(async_url, status="resolved")
    item = next(i for i in response.items if i.id == jid)
    assert item.error_category == "gemini_timeout"
    assert item.error_message == "GEMINI_TIMEOUT"
    assert item.handling_status == "resolved"
    assert item.job_status == "done"


async def test_handling_status_assignment_for_all_six_job_statuses(pg, monkeypatch):
    """T1 (統合確認): 6状態それぞれで handling_status が design §3 のとおりに割り当たること。"""
    connection, _, async_url = pg
    monkeypatch.setattr(router_module, "_TCG_SCHEMA", SCHEMA)
    expected = {
        "error": "unhandled",
        "pending": "in_progress",
        "running": "in_progress",
        "done": "resolved",
        "empty": "resolved",
        "filtered": "resolved",
    }
    job_ids: dict[str, str] = {}
    for offset, (job_status, _handling) in enumerate(expected.items()):
        sid, jid = source(pg)
        add_failed_attempt(connection, jid, sid, minutes_offset=offset)
        set_job_status(connection, jid, job_status)
        job_ids[job_status] = jid

    for job_status, handling in expected.items():
        response = await call_list_extraction_errors(async_url, status=handling)
        item = next(i for i in response.items if i.id == job_ids[job_status])
        assert item.handling_status == handling
        assert item.job_status == job_status


async def test_counts_and_total_match_bucketed_job_counts(pg, monkeypatch):
    """T4: counts と total が、failed の attempt を持つジョブの状態別件数と一致すること。"""
    connection, _, async_url = pg
    monkeypatch.setattr(router_module, "_TCG_SCHEMA", SCHEMA)
    # unhandled x2 (error), in_progress x1 (pending), resolved x3 (done x2, filtered x1)
    plan = ["error", "error", "pending", "done", "done", "filtered"]
    for offset, job_status in enumerate(plan):
        sid, jid = source(pg)
        add_failed_attempt(connection, jid, sid, minutes_offset=offset)
        set_job_status(connection, jid, job_status)
    # ノイズ: failed attempt を持たない pending ジョブは、いずれの bucket にも数えない
    noise_sid, noise_jid = source(pg)
    set_job_status(connection, noise_jid, "pending")

    response = await call_list_extraction_errors(async_url, status="unhandled")
    assert response.counts.unhandled == 2
    assert response.counts.in_progress == 1
    assert response.counts.resolved == 3
    assert response.total == 2  # status="unhandled" 選択時の total


async def test_retry_extraction_job_ids_rejects_pending_and_running(pg, monkeypatch):
    """T5: pending/running のジョブ ID で retry-extraction を呼ぶと enqueued=0, skipped=件数。"""
    connection, _, async_url = pg
    queued = []
    monkeypatch.setattr(diagnostics, "TCG_SCHEMA", SCHEMA)
    from app.tasks import tcg_extraction as extraction  # noqa: PLC0415

    monkeypatch.setattr(extraction.extract_source_message_task, "apply_async", lambda **kw: queued.append(kw))

    pending_sid, pending_jid = source(pg)  # source() 既定で status='pending'
    running_sid, running_jid = source(pg)
    set_job_status(connection, running_jid, "running")

    engine = create_async_engine(async_url)
    try:
        async with AsyncSession(engine) as session:
            result = await diagnostics.retry_extraction(
                session, job_ids=[pending_jid, running_jid], scope=None
            )
    finally:
        await engine.dispose()

    assert result == {"enqueued": 0, "skipped": 2}
    assert queued == []
