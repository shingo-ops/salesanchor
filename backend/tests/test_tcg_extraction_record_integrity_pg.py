"""Canonical DDL and real-task regressions; disposable Docker PostgreSQL only."""
import json
import re
from unittest.mock import Mock
from uuid import UUID

import psycopg2
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import gemini_extraction_svc as gemini
from app.services import tcg_extraction_record_svc as records
from app.tasks import tcg_extraction as extraction
from tests.test_tcg_extraction_record_pg import (
    MIGRATION,
    RAW,
    SCHEMA,
    VALID,
    fake_model,
    item_count,
    rows,
    run,
    seed_products,
    source,
)
from tests.test_tcg_extraction_record_pg import never_live as never_live
from tests.test_tcg_extraction_record_pg import pg as pg_fixture
from tests.test_tcg_work_matching_integration import provision

pg = pg_fixture

CATALOG = """
SELECT jsonb_agg(jsonb_build_array(c.conname,c.contype,c.convalidated,c.condeferrable,
 c.condeferred,c.connoinherit,
 ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(num,pos)
  JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.num ORDER BY k.pos),
 CASE WHEN c.contype='c' THEN pg_get_constraintdef(c.oid,false) END,
 CASE WHEN c.contype='f' THEN CASE WHEN n.nspname=%s THEN '$self' ELSE n.nspname END END,
 CASE WHEN c.contype='f' THEN r.relname END,
 ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(num,pos)
  JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.num ORDER BY k.pos),
 c.confupdtype,c.confdeltype,c.confmatchtype) ORDER BY c.conname)
FROM pg_constraint c LEFT JOIN pg_class r ON r.oid=c.confrelid
LEFT JOIN pg_namespace n ON n.oid=r.relnamespace
WHERE c.conrelid=to_regclass(%s)
"""


def fingerprint(connection, schema=SCHEMA):
    with connection.cursor() as cur:
        cur.execute("SHOW search_path")
        old = cur.fetchone()[0]
        cur.execute("SELECT set_config('search_path','pg_catalog',false)")
        try:
            cur.execute(CATALOG, (schema, f"{schema}.extraction_attempts"))
            return cur.fetchone()[0]
        finally:
            cur.execute("SELECT set_config('search_path',%s,false)", (old,))


def new_record(pg):
    sid, jid = source(pg)
    session = Session(pg[1])
    recorder = records.AttemptRecorder(session, jid, sid, {}, "synthetic")
    recorder.before_send({"model": "synthetic", "contents": "fixture", "config": {}})
    recorder.on_response("fixture response")
    return session, recorder, jid


def test_expected_catalog_matches_independent_canonical_ddl(pg):
    """Create a separate baseline from DDL, never infer expectations from subject rows."""
    sql = MIGRATION.read_text()
    ddl = sql.split("EXECUTE format($ddl$", 1)[1].split("$ddl$,", 1)[0]
    expected = json.loads(re.search(r"\$expected\$(.*?)\$expected\$", sql, re.S).group(1))
    with pg[0].cursor() as cur:
        provision(cur, "tenant_baseline")
        cur.execute(ddl.replace("%I", "tenant_baseline"))
    assert fingerprint(pg[0], "tenant_baseline") == expected
    assert len(expected) == 9


NORMAL = ["normal_other_schema", "migration_repeat", "public", "tenant_901, public", "tenant_902, public", "pg_catalog", "whitespace_parentheses"]


@pytest.mark.parametrize("case", NORMAL)
def test_canonical_normal_variants_and_records_unchanged(pg, case):
    session, recorder, jid = new_record(pg)
    session.close()
    before = rows(pg, jid)
    with pg[0].cursor() as cur:
        if case == "whitespace_parentheses":
            cur.execute(f"ALTER TABLE {SCHEMA}.extraction_attempts DROP CONSTRAINT extraction_attempts_input_size")
            cur.execute(f"ALTER TABLE {SCHEMA}.extraction_attempts ADD CONSTRAINT extraction_attempts_input_size CHECK ( ( input_bytes >= 0 ) )")
        if case == "normal_other_schema":
            provision(cur, "tenant_903")
        path = case if case not in ("normal_other_schema", "migration_repeat", "whitespace_parentheses") else "public"
        cur.execute("SELECT set_config('search_path',%s,false)", (path,))
        cur.execute(MIGRATION.read_text())
        cur.execute("SHOW search_path")
        assert cur.fetchone()[0] == path
        cur.execute(MIGRATION.read_text())
    assert rows(pg, jid) == before


BAD = [
 ("wrong_check", "DROP CONSTRAINT extraction_attempts_phase_check, ADD CONSTRAINT extraction_attempts_phase_check CHECK(true)"),
 ("missing_check", "DROP CONSTRAINT extraction_attempts_finish_check"),
 ("wrong_fk_column", "DROP CONSTRAINT extraction_attempts_job_fk, ADD CONSTRAINT extraction_attempts_job_fk FOREIGN KEY(source_message_id) REFERENCES tenant_901.extraction_jobs(id) ON DELETE CASCADE"),
 ("wrong_fk_delete", "DROP CONSTRAINT extraction_attempts_job_fk, ADD CONSTRAINT extraction_attempts_job_fk FOREIGN KEY(extraction_job_id) REFERENCES tenant_901.extraction_jobs(id) ON DELETE RESTRICT"),
 ("unvalidated_fk", "DROP CONSTRAINT extraction_attempts_job_fk, ADD CONSTRAINT extraction_attempts_job_fk FOREIGN KEY(extraction_job_id) REFERENCES tenant_901.extraction_jobs(id) ON DELETE CASCADE NOT VALID"),
 ("deferred_fk", "DROP CONSTRAINT extraction_attempts_job_fk, ADD CONSTRAINT extraction_attempts_job_fk FOREIGN KEY(extraction_job_id) REFERENCES tenant_901.extraction_jobs(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED"),
 ("wrong_unique_column", "DROP CONSTRAINT extraction_attempts_parent_attempt_id_key, ADD CONSTRAINT extraction_attempts_parent_attempt_id_key UNIQUE(source_message_id)"),
 ("wrong_fk_schema", "DROP CONSTRAINT extraction_attempts_job_fk, ADD CONSTRAINT extraction_attempts_job_fk FOREIGN KEY(extraction_job_id) REFERENCES tenant_foreign.extraction_jobs(id) ON DELETE CASCADE"),
 ("unknown_equivalent_expression", "DROP CONSTRAINT extraction_attempts_input_size, ADD CONSTRAINT extraction_attempts_input_size CHECK(0 <= input_bytes)"),
 ("extra_constraint", "ADD CONSTRAINT unauthorized_check CHECK(true)"),
 ("wrong_pk", "DROP CONSTRAINT extraction_attempts_pkey, ADD CONSTRAINT extraction_attempts_pkey PRIMARY KEY(source_message_id)"),
 ("check_noinherit", "DROP CONSTRAINT extraction_attempts_input_size, ADD CONSTRAINT extraction_attempts_input_size CHECK(input_bytes>=0) NO INHERIT"),
]


@pytest.mark.parametrize("case,alter", BAD, ids=[row[0] for row in BAD])
def test_rejects_noncanonical_constraints_atomically(pg, case, alter):
    session, recorder, jid = new_record(pg)
    session.close()
    with pg[0].cursor() as cur:
        if case == "wrong_fk_column":
            cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (recorder.source_id, recorder.source_id))
        if case == "wrong_fk_schema":
            provision(cur, "tenant_foreign")
            cur.execute(f"""INSERT INTO tenant_foreign.source_messages(id,raw_text,raw_sha256,is_active)
                SELECT id,raw_text,raw_sha256,is_active FROM {SCHEMA}.source_messages WHERE id=%s""",
                        (recorder.source_id,))
            cur.execute("INSERT INTO tenant_foreign.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')",
                        (jid, recorder.source_id))
        cur.execute(f"ALTER TABLE {SCHEMA}.extraction_attempts {alter}")
        # This earlier valid schema would be provisioned before the incompatible later table.
        provision(cur, "tenant_000")
    before = rows(pg, jid)
    structure = fingerprint(pg[0])
    with pg[0].cursor() as cur:
        with pytest.raises(psycopg2.errors.RaiseException, match="Incompatible extraction attempts"):
            cur.execute(MIGRATION.read_text())
        cur.execute("ROLLBACK")
        cur.execute("SELECT to_regclass('tenant_000.extraction_attempts')")
        assert cur.fetchone()[0] is None
    assert rows(pg, jid) == before
    assert fingerprint(pg[0]) == structure


@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_real_task_parsed_limit_preserves_measured_size(pg, monkeypatch, delta):
    seed_products(pg[0])
    sid, jid = source(pg)
    fake_model(monkeypatch)
    item = gemini.parse_extraction_response(VALID, RAW, version=4)[0]
    fixed_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    monkeypatch.setattr(records, "uuid4", lambda: fixed_id)
    item["raw_memo"] = ""
    prepared = {**item, "extraction_item_id": str(fixed_id), "response_item_number": 1}
    size = records.MAX_BYTES + delta
    item["raw_memo"] = "x" * (size - len(records.encoded([prepared]).encode()))
    monkeypatch.setattr(gemini, "parse_extraction_response", lambda *a, **kw: [item])
    analyzer = Mock(return_value={"status": "done"})
    monkeypatch.setattr(extraction, "analyze_extraction_job", analyzer)
    monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
    result = run(pg, sid)
    attempt, = rows(pg, jid)
    assert attempt["parsed_bytes"] == size
    if delta > 0:
        assert result["status"] == "error" and attempt["error_code"] == "PARSED_TOO_LARGE"
        assert attempt["parsed_items"] is None and item_count(pg, jid) == 0
        analyzer.assert_not_called()
    else:
        assert result["status"] == "done" and item_count(pg, jid) == 1
        assert len(records.encoded(attempt["parsed_items"]).encode()) == size
        analyzer.assert_called_once()


@pytest.mark.parametrize("method", ["prepare_items", "complete"])
def test_both_parsed_oversize_entry_points(pg, method):
    session, recorder, jid = new_record(pg)
    try:
        items = [{"blob": "x" * records.MAX_BYTES}]
        with pytest.raises(records.RecordError, match="PARSED_TOO_LARGE"):
            getattr(recorder, method)(items)
        measured = recorder._oversized_parsed_bytes
        assert measured > records.MAX_BYTES
        recorder.fail("PARSED_TOO_LARGE")
        attempt, = rows(pg, jid)
        assert attempt["parsed_bytes"] == measured and attempt["parsed_items"] is None
        assert item_count(pg, jid) == 0
    finally:
        session.close()


@pytest.mark.parametrize("protection", ["terminal", "successor", "foreign", "commit_failure"])
def test_oversize_failure_respects_ownership_and_storage_failure(pg, monkeypatch, protection):
    session, recorder, jid = new_record(pg)
    try:
        if protection == "terminal":
            recorder.complete([])
            session.execute(text(f"UPDATE {SCHEMA}.extraction_jobs SET status='empty' WHERE id=:id"), {"id": jid})
            session.commit()
        if protection == "successor":
            with pg[0].cursor() as cur:
                cur.execute(f"UPDATE {SCHEMA}.extraction_jobs SET status='pending' WHERE id=%s", (jid,))
            with Session(pg[1]) as newer_session:
                newer = records.AttemptRecorder(newer_session, jid, recorder.source_id, {}, "synthetic")
                newer.before_send({"model": "synthetic", "contents": "new", "config": {}})
        if protection == "foreign":
            _, other_job = source(pg)
            recorder.job_id = other_job
        before = rows(pg, jid)
        if protection == "commit_failure":
            monkeypatch.setattr(session, "commit", Mock(side_effect=RuntimeError("synthetic storage failure")))
        with pytest.raises(records.RecordError, match="PARSED_TOO_LARGE"):
            recorder.complete([{"blob": "x" * records.MAX_BYTES}])
        recorder.fail("PARSED_TOO_LARGE")
        assert rows(pg, jid) == before
    finally:
        session.close()
