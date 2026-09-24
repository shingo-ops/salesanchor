"""CARD09 PostgreSQL acceptance in disposable CI databases. Never live Gemini."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import perf_counter
from types import SimpleNamespace
from uuid import uuid4

import psycopg2
import pytest
from celery.exceptions import SoftTimeLimitExceeded
from fastapi import HTTPException
from sqlalchemy import MetaData, Table
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from app.services import gemini_extraction_svc as gemini
from app.services import tcg_extraction_record_svc as records
from app.tasks import tcg_extraction as extraction
from tests.test_tcg_work_matching_integration import MIGRATIONS, SCHEMA, provision, seed_products
from tests.test_tcg_work_matching_integration import pg as pg

MIGRATION = MIGRATIONS / "20260914_010000_tcg_extraction_attempts.sql"
HEADER = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN｜RESOLVED_WORK_ID｜RESOLVED_PRODUCT_CODE"
VALID = HEADER + "\n◆原文商品｜2｜1,000円｜BOX｜未開封｜翌日発送｜L0001｜｜｜｜"
RAW = "◆原文商品 2BOX 1,000円 未開封 翌日発送"


@pytest.fixture(autouse=True)
def never_live(monkeypatch):
    monkeypatch.setattr(gemini, "_get_genai_client", lambda: pytest.fail("Live Gemini forbidden"))
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "0")


def source(pg):
    connection, _, _ = pg
    sid, jid = str(uuid4()), str(uuid4())
    with connection.cursor() as cur:
        cur.execute(f"""INSERT INTO {SCHEMA}.source_messages
            (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at)
            SELECT %s,id,%s,%s,true,now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
                    (sid, RAW, uuid4().hex))
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (jid, sid))
    return sid, jid


def fake_model(monkeypatch, response=VALID, action=None):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        if action:
            action()
        return SimpleNamespace(text=response)

    monkeypatch.setattr(gemini, "_get_genai_client", lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    return calls


def rows(pg, job):
    with pg[0].cursor() as cur:
        cur.execute(f"SELECT to_jsonb(a) FROM {SCHEMA}.extraction_attempts a WHERE extraction_job_id=%s ORDER BY started_at,id", (job,))
        return [r[0] for r in cur.fetchall()]


def item_count(pg, job):
    with pg[0].cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (job,))
        return cur.fetchone()[0]


def run(pg, sid):
    with Session(pg[1]) as session:
        return extraction._run_extraction(session, sid)


@pytest.mark.parametrize("response,status,count", [(VALID, "done", 1), (HEADER, "empty", 0), ("private invalid output", "error", 0), ("", "error", 0)])
def test_response_and_input_are_saved_before_parsing(pg, monkeypatch, response, status, count):
    seed_products(pg[0])
    sid, jid = source(pg)
    calls = fake_model(monkeypatch, response)
    result = run(pg, sid)
    assert result["status"] == status and item_count(pg, jid) == count
    attempt, = rows(pg, jid)
    assert len(calls) == 1
    assert attempt["input_payload"]["contents"] == calls[0]["contents"]
    assert attempt["input_payload"]["model"] == calls[0]["model"]
    assert attempt["input_payload"]["config"] == {"temperature": 0}
    assert attempt["response_text"] == response
    assert attempt["response_sha256"] == records.digest(response)
    assert attempt["phase"] == ("failed" if status == "error" else "completed")
    if count:
        item, = attempt["parsed_items"]
        assert item["raw_product_name"] == "◆原文商品" and item["raw_price"] == "1,000円"
        with pg[0].cursor() as cur:
            cur.execute(f"SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (jid,))
            assert str(cur.fetchone()[0]) == item["extraction_item_id"]


@pytest.mark.parametrize("failure", ["API_ERROR", "SOFT_TIME_LIMIT"])
def test_no_response_is_not_an_empty_response(pg, monkeypatch, failure):
    seed_products(pg[0])
    sid, jid = source(pg)

    def fail():
        if failure == "SOFT_TIME_LIMIT":
            raise SoftTimeLimitExceeded()
        raise RuntimeError("private provider payload")

    calls = fake_model(monkeypatch, action=fail)
    result = run(pg, sid)
    attempt, = rows(pg, jid)
    assert len(calls) == 1 and result["error_message"] == failure
    assert attempt["response_text"] is None and attempt["response_received_at"] is None
    assert attempt["error_code"] == failure and item_count(pg, jid) == 0


@pytest.mark.parametrize("soft", [False, True])
@pytest.mark.parametrize("stage", ["start", "receive", "items"])
def test_storage_failure_never_adopts_or_analyzes(pg, monkeypatch, stage, soft):
    seed_products(pg[0])
    sid, jid = source(pg)
    calls = fake_model(monkeypatch)
    analyzed = []
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
    monkeypatch.setattr(extraction, "analyze_extraction_job", lambda *a: analyzed.append(a))
    with Session(pg[1]) as session:
        original = session.commit
        commits = 0

        def commit():
            nonlocal commits
            commits += 1
            if commits == {"start": 1, "receive": 2, "items": 3}[stage]:
                if soft:
                    raise SoftTimeLimitExceeded()
                raise RuntimeError("private SQL parameter data")
            return original()

        monkeypatch.setattr(session, "commit", commit)
        result = extraction._run_extraction(session, sid)
    assert result["status"] == "error" and item_count(pg, jid) == 0 and analyzed == []
    assert result["error_message"] == ("SOFT_TIME_LIMIT" if soft else "RECORD_WRITE_FAILED")
    assert len(calls) == (0 if stage == "start" else 1)
    attempts = rows(pg, jid)
    assert len(attempts) == (0 if stage == "start" else 1)
    if attempts:
        assert attempts[0]["phase"] == "failed"
        assert attempts[0]["response_text"] == (VALID if stage == "items" else None)


def test_reference_change_preserves_response_but_rejects_items(pg, monkeypatch):
    seed_products(pg[0])
    sid, jid = source(pg)

    def change():
        with pg[0].cursor() as cur:
            cur.execute("UPDATE public.products SET mark='changed' WHERE product_code='PM0123'")

    fake_model(monkeypatch, action=change)
    result = run(pg, sid)
    attempt, = rows(pg, jid)
    assert result["error_message"] == "REFERENCE_CHANGED" and item_count(pg, jid) == 0
    assert attempt["response_text"] == VALID


def test_retry_keeps_previous_failure_and_completed_job_cannot_rerun(pg, monkeypatch):
    seed_products(pg[0])
    sid, jid = source(pg)
    fake_model(monkeypatch, "invalid")
    assert run(pg, sid)["status"] == "error"
    first = rows(pg, jid)[0]
    with pg[0].cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET status='pending' WHERE id=%s", (jid,))
    calls = fake_model(monkeypatch)
    assert run(pg, sid)["status"] == "done"
    assert run(pg, sid)["status"] == "no_pending_job"
    before, after = rows(pg, jid)
    assert before == first and after["parent_attempt_id"] == first["id"] and len(calls) == 1


def test_simultaneous_claims_allow_only_one_call(pg, monkeypatch):
    seed_products(pg[0])
    sid, jid = source(pg)
    barrier = Barrier(2)
    original = records.AttemptRecorder.before_send

    def synchronized(self, payload):
        barrier.wait(timeout=5)
        original(self, payload)

    monkeypatch.setattr(records.AttemptRecorder, "before_send", synchronized)
    calls = fake_model(monkeypatch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(pg, sid), range(2)))
    assert len(calls) == 1 and item_count(pg, jid) == 1 and len(rows(pg, jid)) == 1
    assert sorted(x["status"] for x in results) == ["done", "error"]


def test_interruption_leaves_started_attempt_without_claiming_api_not_sent(pg):
    sid, jid = source(pg)
    with Session(pg[1]) as session:
        recorder = records.AttemptRecorder(session, jid, sid, {"works": [], "products": []}, "synthetic")
        recorder.before_send({"model": "synthetic", "contents": "line", "config": {"temperature": 0}})
    attempt, = rows(pg, jid)
    assert attempt["phase"] == "started" and attempt["finished_at"] is None
    assert item_count(pg, jid) == 0


@pytest.mark.parametrize("stage", ["input", "response", "parsed"])
def test_size_exceeded_fails_closed(pg, monkeypatch, stage):
    seed_products(pg[0])
    sid, jid = source(pg)
    if stage == "input":
        monkeypatch.setattr(records, "MAX_BYTES", 1)
    elif stage == "response":
        # The reference is larger than this anonymous response, so shrink only after sending.
        pass
    calls = fake_model(monkeypatch, action=(lambda: monkeypatch.setattr(records, "MAX_BYTES", 1)) if stage == "response" else None)
    if stage == "parsed":
        original = records.AttemptRecorder.prepare_items

        def shrink(self, items):
            monkeypatch.setattr(records, "MAX_BYTES", 1)
            return original(self, items)

        monkeypatch.setattr(records.AttemptRecorder, "prepare_items", shrink)
    result = run(pg, sid)
    assert result["error_message"] == {"input": "INPUT_TOO_LARGE", "response": "RESPONSE_TOO_LARGE", "parsed": "PARSED_TOO_LARGE"}[stage]
    assert item_count(pg, jid) == 0 and len(calls) == (0 if stage == "input" else 1)
    assert rows(pg, jid)[0]["phase"] == "failed"


def test_byte_boundary_counts_utf8(monkeypatch):
    monkeypatch.setattr(records, "MAX_BYTES", 3)
    assert records.bounded("あ", "TOO_LARGE") == 3
    with pytest.raises(records.RecordError, match="TOO_LARGE"):
        records.bounded("あx", "TOO_LARGE")


@pytest.mark.parametrize("stage", ["input", "response", "parsed"])
@pytest.mark.parametrize("extra", [0, 1])
def test_actual_8mib_pg_boundaries(pg, monkeypatch, stage, extra):
    """Isolate storage boundaries from model parsing; exercise real task transactions."""
    assert records.MAX_BYTES == 8_388_608
    seed_products(pg[0])
    sid, jid = source(pg)
    sent = []
    captured = {}
    item = {"line_start": 1, "line_end": 1, "raw_product_name": "匿名商品",
            "raw_quantity": "2", "raw_price": "1000", "raw_unit": "BOX",
            "raw_state": "未開封", "raw_memo": "あ", "raw_work_name": None,
            "raw_work_source_line_span": None, "resolved_work_id": None}
    target = records.MAX_BYTES + extra
    if stage == "parsed":
        measured = [{**item, "extraction_item_id": str(uuid4()), "response_item_number": 1}]
        item["raw_memo"] += "x" * (target - len(records.encoded(measured).encode()))
        measured[0]["raw_memo"] = item["raw_memo"]
        assert len(records.encoded(measured).encode()) == target

    def synthetic_extract(raw_text, *, work_reference, recorder, supplier_context=None, knowledge_links=None):
        payload = {"model": "synthetic", "contents": "あ", "config": {"temperature": 0}}
        if stage == "input":
            size = len(records.encoded({**payload, "reference": work_reference}).encode())
            payload["contents"] += "x" * (target - size)
        captured["input"] = records.encoded({**payload, "reference": work_reference})
        response = "あ"
        if stage == "response":
            response += "x" * (target - len(response.encode()))
        captured["response"] = response
        recorder.before_send(payload)
        sent.append(True)
        recorder.on_response(response)
        return {"status": "done", "items": [item], "prompt_version": extraction.WORK_ID_PROMPT_VERSION,
                "error_message": None}

    monkeypatch.setattr(extraction, "extract_message", synthetic_extract)
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
    analyzed = []
    monkeypatch.setattr(extraction, "analyze_extraction_job", lambda *args, **kwargs: analyzed.append(True))
    result = run(pg, sid)
    attempt, = rows(pg, jid)
    assert len(sent) == (0 if stage == "input" and extra else 1)
    if extra:
        code = {"input": "INPUT_TOO_LARGE", "response": "RESPONSE_TOO_LARGE", "parsed": "PARSED_TOO_LARGE"}[stage]
        assert result["status"] == "error" and result["error_message"] == code
        assert attempt["phase"] == "failed" and attempt["error_code"] == code
        assert item_count(pg, jid) == 0 and analyzed == []
        if stage == "input":
            assert attempt["input_payload"] is None and attempt["response_text"] is None
        elif stage == "response":
            assert attempt["response_text"] is None and attempt["response_received_at"] is not None
        else:
            assert attempt["response_text"] == captured["response"] and attempt["parsed_items"] is None
    else:
        assert result["status"] == "done" and attempt["phase"] == "completed"
        assert item_count(pg, jid) == 1 and analyzed == [True]
        assert attempt["input_payload"] == json.loads(captured["input"])
        assert attempt["response_text"] == captured["response"]
        if stage == "parsed":
            assert attempt["parsed_bytes"] == target
            assert len(records.encoded(attempt["parsed_items"]).encode()) == target
            with pg[0].cursor() as cur:
                cur.execute(f"SELECT raw_memo FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (jid,))
                assert cur.fetchone()[0] == item["raw_memo"]
    if stage in ("input", "response"):
        assert attempt[f"{stage}_bytes"] == target
        assert attempt[f"{stage}_sha256"] == records.digest(captured[stage])


def test_migration_idempotent_and_parent_lifecycle(pg, monkeypatch):
    seed_products(pg[0])
    sid, jid = source(pg)
    fake_model(monkeypatch)
    run(pg, sid)
    before = rows(pg, jid)
    with pg[0].cursor() as cur:
        cur.execute(MIGRATION.read_text())
        cur.execute(MIGRATION.read_text())
        cur.execute("SELECT schemaname FROM pg_tables WHERE tablename='extraction_attempts' ORDER BY schemaname")
        assert cur.fetchall() == [('public',), (SCHEMA,)]
        cur.execute(f"SELECT tableowner FROM pg_tables WHERE schemaname='{SCHEMA}' AND tablename='extraction_attempts'")
        assert cur.fetchone()[0] == 'jarvis'
        cur.execute(f"SELECT has_table_privilege('salesanchor_app','{SCHEMA}.extraction_attempts','SELECT,INSERT,UPDATE')")
        assert cur.fetchone()[0]
    assert rows(pg, jid) == before
    with pg[1].begin() as connection:
        parent = Table('source_messages', MetaData(), schema=SCHEMA, autoload_with=connection)
        connection.execute(parent.delete().where(parent.c.id == sid))
    assert rows(pg, jid) == []


def test_partial_schema_stops_migration(pg):
    with pg[0].cursor() as cur:
        provision(cur, "tenant_904")
        cur.execute("ALTER TABLE tenant_904.extraction_items RENAME TO interrupted_items")
        with pytest.raises(psycopg2.errors.RaiseException, match="Partial extraction schema"):
            cur.execute(MIGRATION.read_text())
        cur.execute("ROLLBACK")
        cur.execute("SELECT to_regclass('tenant_904.extraction_attempts')")
        assert cur.fetchone()[0] is None


@pytest.mark.asyncio
async def test_private_detail_is_job_scoped_and_summary_omits_payload(pg, monkeypatch):
    seed_products(pg[0])
    sid, jid = source(pg)
    fake_model(monkeypatch)
    run(pg, sid)
    attempt = rows(pg, jid)[0]
    _, other = source(pg)
    engine = create_async_engine(pg[2])
    try:
        async with AsyncSession(engine) as session:
            summary = await records.read_attempts(session, jid)
            assert 'input_payload' not in summary['attempts'][0] and 'response_text' not in summary['attempts'][0]
            detail = await records.read_attempts(session, jid, attempt_id=attempt['id'])
            assert detail['attempts'][0]['response_text'] == VALID
            with pytest.raises(HTTPException) as exc:
                await records.read_attempts(session, other, attempt_id=attempt['id'])
            assert exc.value.status_code == 404
    finally:
        await engine.dispose()


def test_fixed_scale_44_attempts_storage_budget(pg, monkeypatch, capsys):
    """Synthetic upper input envelope, full reference copies and 729 actual inserts."""
    seed_products(pg[0])
    with Session(pg[1]) as session:
        reference = extraction.load_work_reference(session, SCHEMA)
    remaining = 83_610 - len(records.encoded(reference).encode())
    assert remaining >= 0
    reference["products"][0]["english_title"] = (reference["products"][0]["english_title"] or "")
    # Recalculate after normalizing a nullable title; use non-repeating anonymous data.
    remaining = 83_610 - len(records.encoded(reference).encode())
    reference["products"][0]["english_title"] += hashlib.shake_256(b"CARD09-reference").hexdigest(remaining)[:remaining]
    assert len(records.encoded(reference).encode()) == 83_610
    monkeypatch.setattr(extraction, "load_work_reference", lambda *_: reference)
    original_send = records.AttemptRecorder.before_send

    def sized_send(self, payload):
        missing = 99_099 - len(payload["contents"].encode())
        assert missing >= 0
        payload["contents"] += hashlib.shake_256(b"CARD09-input").hexdigest(missing)[:missing]
        original_send(self, payload)

    monkeypatch.setattr(records.AttemptRecorder, "before_send", sized_send)
    durations, stored_counts, input_sizes = [], [], []
    for index in range(44):
        count = 17 if index < 25 else 16
        sid, jid = source(pg)
        raw = "\n".join(f"◆匿名商品{i} 2BOX 1,000円 未開封 翌日発送" for i in range(count))
        response = HEADER + "\n" + "\n".join(
            f"◆匿名商品{i}｜2｜1,000円｜BOX｜未開封｜翌日発送｜L{i+1:04d}｜｜｜｜" for i in range(count)
        )
        with pg[0].cursor() as cur:
            cur.execute(f"UPDATE {SCHEMA}.source_messages SET raw_text=%s WHERE id=%s", (raw, sid))
        calls = fake_model(monkeypatch, response)
        started = perf_counter()
        result = run(pg, sid)
        durations.append(perf_counter() - started)
        assert result["status"] == "done", result
        assert len(calls) == 1 and len(calls[0]["contents"].encode()) == 99_099
        attempt, = rows(pg, jid)
        assert attempt["phase"] == "completed" and attempt["response_text"] == response
        assert attempt["input_payload"]["reference"] == reference
        assert len(attempt["parsed_items"]) == count and attempt["item_count"] == count
        with pg[0].cursor() as cur:
            cur.execute(f"SELECT work_reference_snapshot FROM {SCHEMA}.extraction_jobs WHERE id=%s", (jid,))
            assert cur.fetchone()[0] == reference
            cur.execute(f"SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s", (jid,))
            assert {str(row[0]) for row in cur.fetchall()} == {x["extraction_item_id"] for x in attempt["parsed_items"]}
        stored_counts.append(item_count(pg, jid))
        input_sizes.append(attempt["input_bytes"])
    assert sum(stored_counts) == 729
    assert max(durations) <= 5, json.dumps(durations)
    with capsys.disabled():
        print("CARD09_STORAGE_SCALE " + json.dumps({"attempts": 44, "items": sum(stored_counts),
              "reference_bytes": 83_610, "sdk_contents_bytes_each": 99_099,
              "input_json_bytes_max": max(input_sizes), "task_seconds_max": max(durations)}))


def test_analysis_failure_does_not_reclassify_committed_extraction(pg, monkeypatch):
    seed_products(pg[0])
    sid, jid = source(pg)
    fake_model(monkeypatch)
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")

    def failure(*args):
        raise RuntimeError("analysis failure")

    monkeypatch.setattr(extraction, "analyze_extraction_job", failure)
    result = run(pg, sid)
    assert result["status"] == "done" and result["items_count"] == 1
    assert result["analysis_stats"]["error_code"] == "ANALYSIS_FAILED"
    assert rows(pg, jid)[0]["phase"] == "completed"


def test_new_tcg_schema_receives_history_on_migration(pg):
    with pg[0].cursor() as cur:
        provision(cur, "tenant_903")
        cur.execute(MIGRATION.read_text())
        cur.execute("SELECT to_regclass('tenant_903.extraction_attempts') IS NOT NULL")
        assert cur.fetchone()[0]


def test_malformed_history_column_rejects_without_erasing_data(pg):
    with pg[0].cursor() as cur:
        cur.execute(f"ALTER TABLE {SCHEMA}.extraction_attempts RENAME COLUMN response_text TO different_name")
        with pytest.raises(psycopg2.errors.RaiseException, match="Incompatible extraction attempts column"):
            cur.execute(MIGRATION.read_text())
        cur.execute("ROLLBACK")


@pytest.mark.parametrize("received", [False, True])
def test_simulated_process_exit_keeps_last_committed_stage(pg, monkeypatch, received):
    seed_products(pg[0])
    sid, jid = source(pg)
    fake_model(monkeypatch)
    if received:
        original = records.AttemptRecorder.on_response

        def stop(self, response):
            original(self, response)
            raise SystemExit("simulated process exit")

        monkeypatch.setattr(records.AttemptRecorder, "on_response", stop)
    else:
        def stop():
            raise SystemExit("simulated process exit")

        fake_model(monkeypatch, action=stop)
    with pytest.raises(SystemExit):
        run(pg, sid)
    attempt, = rows(pg, jid)
    assert attempt["phase"] == ("received" if received else "started")
    assert attempt["finished_at"] is None and item_count(pg, jid) == 0
    assert attempt["response_text"] == (VALID if received else None)
