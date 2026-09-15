"""Real PostgreSQL read-only and production matcher parity, synthetic model only."""
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.services import tcg_work_comparison_svc as comparison
from tests.test_tcg_work_matching_integration import (
    SCHEMA,
    record,
    run_message,
    seed_products,
)
from tests.test_tcg_work_matching_integration import (
    pg as pg,
)


@pytest.fixture(autouse=True)
def deny_live(monkeypatch):
    monkeypatch.setattr(comparison.gemini, "_get_genai_client", lambda: pytest.fail("Live Gemini forbidden"))
    monkeypatch.setattr(comparison, "TCG_SCHEMA", SCHEMA)


def link_import(connection, source_ids):
    iid = str(uuid4())
    with connection.cursor() as cursor:
        migration = Path(__file__).resolve().parents[2] / "migrations/20260910_010000_tcg_import_message_links.sql"
        cursor.execute(migration.read_text())
        cursor.execute(f"INSERT INTO {SCHEMA}.import_jobs(id,filename,raw_sha256) VALUES (%s,'synthetic.txt',%s)", (iid, uuid4().hex))
        for sid in source_ids:
            cursor.execute(f"INSERT INTO {SCHEMA}.import_job_messages(import_job_id,source_message_id,relation_kind) VALUES (%s,%s,'created')", (iid, sid))
    return iid


def all_tables(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename", (SCHEMA,))
        names = [r[0] for r in cursor.fetchall()]
        result = {}
        for name in names:
            # Names originate from pg_tables of a fixed disposable schema.
            cursor.execute(f'SELECT to_jsonb(t)::text FROM {SCHEMA}."{name}" t ORDER BY to_jsonb(t)::text')
            result[name] = cursor.fetchall()
        return result


def public_products_rows(connection):
    """Capture all rows of public.products for before/after invariant checks (disposable DB only)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_jsonb(t)::text FROM public.products t ORDER BY to_jsonb(t)::text")
        return cursor.fetchall()


def fixture_data(pg, monkeypatch):
    connection, engine, _ = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        migration = Path(__file__).resolve().parents[2] / "migrations/20260903_160000_tcg_normalization_rules_t004.sql"
        cursor.execute(migration.read_text().replace("tenant_004", SCHEMA))
        cursor.execute(f"INSERT INTO {SCHEMA}.product_search_keywords(id,product_id,keyword,position) SELECT %s,tcg_uuid,'共通商品',99 FROM public.products WHERE product_code='PM0123'", (str(uuid4()),))
        cursor.execute(f"INSERT INTO {SCHEMA}.product_search_keywords(id,product_id,keyword,position) SELECT %s,tcg_uuid,'共通商品',99 FROM public.products WHERE product_code='PM0200'", (str(uuid4()),))
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {SCHEMA}.product_search_keywords(id,product_id,keyword,position) SELECT %s,tcg_uuid,'ALPHA BETA',100 FROM public.products WHERE product_code='PM0123'", (str(uuid4()),))
        cursor.execute(f"INSERT INTO {SCHEMA}.product_exclude_keywords(id,product_id,keyword,position) SELECT %s,tcg_uuid,'LIMITED EDITION',100 FROM public.products WHERE product_code='PM0123'", (str(uuid4()),))
    cases = [
        ("EB01 1BOX 1000円", record("EB01", 1)),
        ("メモリアルコレクション 1BOX 1000円", record("メモリアルコレクション", 1)),
        ("ワンピース\nEB01 1BOX 1000円", record("EB01", 2, "ワンピース", "L0001")),
        ("EB01 PSA10 1BOX 1000円", record("EB01", 1, state="PSA10")),
        ("メモリアルコレクション PSA10 1BOX 1000円", record("メモリアルコレクション", 1, state="PSA10")),
        ("共通商品 1BOX 1000円", record("共通商品", 1)),
        ("ALPHA  BETA 1BOX 1000円", record("ALPHA  BETA", 1)),
        ("ALPHA   BETA LIMITED  EDITION 1BOX 1000円", record("ALPHA   BETA", 1, state="LIMITED  EDITION")),
        ("メモリアルコレクション 1? 1000円", record("メモリアルコレクション", 1)),
    ]
    cases[-1][1][3] = "?"
    sources = []
    for raw, row in cases:
        sid, _, result = run_message(connection, engine, monkeypatch, raw, [row])
        assert result["status"] == "done"
        sources.append(sid)
    iid = link_import(connection, sources)
    return connection, engine, iid


def test_comparison_matches_production_and_leaves_all_tables_unchanged(pg, monkeypatch):
    production_matches = []
    original_match = comparison.analyzer.match_pid_with_work
    def capture(*args, **kwargs):
        result = original_match(*args, **kwargs)
        production_matches.append(result)
        return result
    monkeypatch.setattr(comparison.analyzer, "match_pid_with_work", capture)
    connection, engine, iid = fixture_data(pg, monkeypatch)
    monkeypatch.setattr(comparison.analyzer, "match_pid_with_work", original_match)
    sessions = []
    def factory():
        session = Session(engine)
        sessions.append(session)
        return session
    before = all_tables(connection)
    snap = comparison.read_snapshot(factory, iid)
    items = {i["id"]: i for i in snap["data"]["items"]}
    jobs = {j["id"]: j for j in snap["data"]["jobs"]}
    sources = {s["id"]: s for s in snap["data"]["sources"]}
    def model(prompt):
        import json
        assert all(not session.in_transaction() for session in sessions)
        payload = json.loads(prompt[len(comparison.PROMPT):])
        rows = []
        for fixed in reversed(payload["items"]):
            item = items[fixed["ITEM_ID"]]
            job = jobs[item["extraction_job_id"]]
            work = comparison.old_work(item, job, sources[job["source_message_id"]], snap["data"])
            rows.append(item["id"] + "｜" + (work or ""))
        return comparison.HEADER + "\n" + "\n".join(rows)
    report = comparison.compare_snapshot(snap, factory, model_call=model)
    assert report["status"] == "comparison_complete_unverified"
    assert report["model_calls"] == 9 and not report["mismatches"]
    spaced = {i["raw_product_name"]: i for i in items.values() if i["raw_product_name"].startswith("ALPHA")}
    assert set(spaced) == {"ALPHA  BETA", "ALPHA   BETA"}
    for name, expected in [("ALPHA  BETA", True), ("ALPHA   BETA", False)]:
        matched = comparison.match_item(spaced[name], None, snap["data"]["context"])
        assert matched["pid_resolved"] is expected
    for row in report["items"].values():
        assert row["saved"]["product_id"] == row["control"]["product_id"] == row["candidate"]["product_id"]
        assert row["control"]["candidates"] == row["candidate"]["candidates"]
    # Compare candidate sets actually returned inside the production analyzer,
    # independent of the comparator's own control/candidate calls.
    expected = sorted((code or "", resolved, tuple(sorted(candidates)))
                      for code, _, resolved, candidates in production_matches)
    ids_to_codes = {v: k for k, v in snap["data"]["context"]["product_ids"].items()}
    actual = sorted((ids_to_codes.get(row["control"]["product_id"], ""),
                     row["control"]["pid_resolved"], tuple(row["control"]["candidates"]))
                    for row in report["items"].values())
    assert actual == expected
    assert any(len(candidates) > 1 for _, _, _, candidates in production_matches)
    assert all_tables(connection) == before
    assert comparison.read_snapshot(factory, iid)["sha256"] == snap["sha256"]
    assert report["db_writes"] == 0 and not report["adoptable"]


def test_snapshot_transaction_rejects_dml(pg, monkeypatch):
    connection, engine, iid = fixture_data(pg, monkeypatch)
    before = all_tables(connection)
    class AttemptWrite(Session):
        def execute(self, statement, *args, **kwargs):
            result = super().execute(statement, *args, **kwargs)
            if str(statement).startswith("SET TRANSACTION"):
                assert super().execute(text("SHOW transaction_read_only")).scalar_one() == "on"
                super().execute(text(f"UPDATE {SCHEMA}.analysis_results SET needs_review=false"))
            return result
    with pytest.raises(DBAPIError) as exc:
        comparison.read_snapshot(lambda: AttemptWrite(engine), iid)
    assert exc.value.orig.pgcode == "25006"
    assert all_tables(connection) == before


@pytest.mark.parametrize("change", ["raw", "master", "correction", "analysis", "links"])
def test_changes_during_model_call_invalidate_entire_result(pg, monkeypatch, change):
    connection, engine, iid = fixture_data(pg, monkeypatch)
    def factory():
        return Session(engine)
    snap = comparison.read_snapshot(factory, iid)
    def model(_):
        with connection.cursor() as cursor:
            if change == "raw":
                cursor.execute(f"UPDATE {SCHEMA}.extraction_items SET raw_memo='changed'")
            elif change == "master":
                cursor.execute("UPDATE public.products SET name='changed' WHERE product_code='PM0123'")
            elif change == "correction":
                cursor.execute(f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by) SELECT i.id,j.source_message_id,'raw_memo','changed','fixture' FROM {SCHEMA}.extraction_items i JOIN {SCHEMA}.extraction_jobs j ON j.id=i.extraction_job_id LIMIT 1")
            elif change == "analysis":
                cursor.execute(f"UPDATE {SCHEMA}.analysis_results SET needs_review=NOT needs_review")
            else:
                cursor.execute(f"UPDATE {SCHEMA}.import_job_messages SET relation_kind='reused' WHERE import_job_id=%s", (iid,))
        return comparison.HEADER
    with pytest.raises(comparison.ComparisonError, match="INPUT_CHANGED"):
        comparison.compare_snapshot(snap, factory, model_call=model)


# ---------------------------------------------------------------------------
# §25-4 A便 PG tests: ⑦ DB unchanged, ⑧ no new IDs / no RAW writes
# ---------------------------------------------------------------------------

def _stale_fixture(pg, monkeypatch):
    """One extraction_job with 7 items; normalization rules applied."""
    connection, engine, _ = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        migration = Path(__file__).resolve().parents[2] / "migrations/20260903_160000_tcg_normalization_rules_t004.sql"
        cursor.execute(migration.read_text().replace("tenant_004", SCHEMA))
    raw = "\n".join("EB01 1BOX 1000円" for _ in range(7))
    rows = [record("EB01", i + 1) for i in range(7)]
    _, jobid, result = run_message(connection, engine, monkeypatch, raw, rows)
    assert result["status"] == "done"
    return connection, engine, jobid


def test_stale_read_and_compare_leaves_all_tables_unchanged(pg, monkeypatch):
    """⑦ All DB tables are bit-identical before and after read_job_snapshot + compare_stale_job_snapshot."""
    connection, engine, jobid = _stale_fixture(pg, monkeypatch)
    sessions = []

    def factory():
        s = Session(engine)
        sessions.append(s)
        return s

    before = all_tables(connection)
    snap = comparison.read_job_snapshot(factory, jobid)
    assert snap["sha256"] == comparison.fingerprint(snap["data"])
    assert len(snap["data"]["items"]) == 7  # ① 7 items read

    snap_item_ids = {i["id"] for i in snap["data"]["items"]}

    def model(prompt):
        assert all(not s.in_transaction() for s in sessions)
        rows = [item["id"] + "｜" for item in snap["data"]["items"]]
        return comparison.HEADER + "\n" + "\n".join(rows)

    report = comparison.compare_stale_job_snapshot(snap, factory, model_call=model)
    assert report["status"] == "comparison_complete_unverified"
    assert report["model_calls"] == 1 and report["db_writes"] == 0 and not report["adoptable"]
    assert set(report["results"]) == snap_item_ids  # ⑧ no new IDs
    assert all_tables(connection) == before  # ⑦ DB unchanged


def test_stale_read_job_snapshot_rejects_dml(pg, monkeypatch):
    """⑦ read_job_snapshot transaction blocks any write attempt (pgcode 25006)."""
    connection, engine, jobid = _stale_fixture(pg, monkeypatch)
    before = all_tables(connection)

    class AttemptWrite(Session):
        def execute(self, statement, *args, **kwargs):
            result = super().execute(statement, *args, **kwargs)
            if str(statement).startswith("SET TRANSACTION"):
                super().execute(text(f"UPDATE {SCHEMA}.analysis_results SET needs_review=false"))
            return result

    with pytest.raises(DBAPIError) as exc:
        comparison.read_job_snapshot(lambda: AttemptWrite(engine), jobid)
    assert exc.value.orig.pgcode == "25006"
    assert all_tables(connection) == before


# ---------------------------------------------------------------------------
# §25-4 work-reference stale PG tests: stale reference, INPUT_CHANGED guards
# ---------------------------------------------------------------------------

def _setup_workid_stale(pg, monkeypatch, n_items=1):
    """Done extraction job with valid work_reference_snapshot + resolved_work_id."""
    connection, engine, _ = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        migration = Path(__file__).resolve().parents[2] / "migrations/20260903_160000_tcg_normalization_rules_t004.sql"
        cursor.execute(migration.read_text().replace("tenant_004", SCHEMA))
    raw = "\n".join("EB01 1BOX 1000円" for _ in range(n_items))
    rows = [record("EB01", i + 1) for i in range(n_items)]
    _, jobid, result = run_message(connection, engine, monkeypatch, raw, rows)
    assert result["status"] == "done"
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s ORDER BY line_start", (jobid,))
        item_ids = [str(r[0]) for r in cursor.fetchall()]
    with Session(engine) as session:
        saved_ref = comparison.load_work_reference(session, SCHEMA)
    saved_sha = comparison.reference_digest(saved_ref)
    valid_work_id = saved_ref["works"][0]["id"]
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version=%s, work_reference_snapshot=%s::jsonb, work_reference_sha256=%s WHERE id=%s",
            ("raw-extraction-v4-work-id-p1", json.dumps(saved_ref), saved_sha, jobid),
        )
        for item_id in item_ids:
            cursor.execute(f"UPDATE {SCHEMA}.extraction_items SET resolved_work_id=%s WHERE id=%s", (valid_work_id, item_id))
    return connection, engine, jobid, item_ids, saved_ref


def test_stale_seven_item_changed_reference_and_db_unchanged(pg, monkeypatch):
    """7-item stale job with changed master produces comparison_complete_unverified, reference_diff.changed=True, and leaves DB unchanged."""
    connection, engine, jobid, item_ids, _ = _setup_workid_stale(pg, monkeypatch, n_items=7)

    sessions = []

    def factory():
        s = Session(engine)
        sessions.append(s)
        return s

    # Insert a new series BEFORE taking snapshot to create the stale-reference condition.
    # The job's saved work_reference_sha256 was captured above; the current reference now differs.
    with connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {SCHEMA}.tcg_series(id, code, display_name, is_active) VALUES (%s, 'IP999', 'New Series', true)",
            (str(uuid4()),),
        )
    before = all_tables(connection)
    before_public_products = public_products_rows(connection)
    snap = comparison.read_job_snapshot(factory, jobid)
    assert snap["data"]["reference_diff"]["changed"] is True  # stale reference confirmed

    def model(prompt):
        assert sessions, "factory must have been called at least once before model"
        assert all(not s.in_transaction() for s in sessions)
        rows = [item["id"] + "｜" for item in snap["data"]["items"]]
        return comparison.HEADER + "\n" + "\n".join(rows)

    report = comparison.compare_stale_job_snapshot(snap, factory, model_call=model)
    assert report["status"] == "comparison_complete_unverified"
    assert report["model_calls"] == 1 and report["db_writes"] == 0 and not report["adoptable"]
    assert set(report["results"]) == set(item_ids)
    assert all_tables(connection) == before
    assert public_products_rows(connection) == before_public_products


@pytest.mark.parametrize("change", ["correction", "non_done", "broken_reference"])
def test_stale_pre_model_conditions_give_input_changed(pg, monkeypatch, change):
    """DB changes after snapshot but before model call → INPUT_CHANGED at initial unchanged(), model not called."""
    connection, engine, jobid, item_ids, _ = _setup_workid_stale(pg, monkeypatch)

    def factory():
        return Session(engine)

    snap = comparison.read_job_snapshot(factory, jobid)
    model_calls = [0]

    def model(prompt):
        model_calls[0] += 1
        return comparison.HEADER + "\n" + "\n".join(iid + "｜" for iid in item_ids)

    with connection.cursor() as cursor:
        if change == "correction":
            cursor.execute(
                f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by) "
                f"SELECT i.id,j.source_message_id,'raw_memo','changed','test' "
                f"FROM {SCHEMA}.extraction_items i JOIN {SCHEMA}.extraction_jobs j ON j.id=i.extraction_job_id WHERE j.id=%s LIMIT 1",
                (jobid,),
            )
        elif change == "non_done":
            cursor.execute(f"UPDATE {SCHEMA}.extraction_jobs SET status='error' WHERE id=%s", (jobid,))
        else:
            cursor.execute(f"UPDATE {SCHEMA}.extraction_jobs SET work_reference_sha256=%s WHERE id=%s", ("0" * 64, jobid))

    with pytest.raises(comparison.ComparisonError, match="INPUT_CHANGED"):
        comparison.compare_stale_job_snapshot(snap, factory, model_call=model)
    assert model_calls[0] == 0


@pytest.mark.parametrize("change", ["source", "job", "item", "analysis", "correction", "master", "updated_at"])
def test_stale_input_changed_during_model_call(pg, monkeypatch, change):
    """DB changes during model call → INPUT_CHANGED at post-model unchanged() via real DB re-read."""
    connection, engine, jobid, item_ids, _ = _setup_workid_stale(pg, monkeypatch)

    def factory():
        return Session(engine)

    snap = comparison.read_job_snapshot(factory, jobid)

    def model(prompt):
        with connection.cursor() as cursor:
            if change == "source":
                cursor.execute(
                    f"UPDATE {SCHEMA}.source_messages SET raw_text='changed' WHERE id="
                    f"(SELECT source_message_id FROM {SCHEMA}.extraction_jobs WHERE id=%s)",
                    (jobid,),
                )
            elif change == "job":
                cursor.execute(f"UPDATE {SCHEMA}.extraction_jobs SET work_reference_sha256=%s WHERE id=%s", ("0" * 64, jobid))
            elif change == "item":
                cursor.execute(f"UPDATE {SCHEMA}.extraction_items SET raw_product_name='changed' WHERE extraction_job_id=%s", (jobid,))
            elif change == "analysis":
                cursor.execute(f"UPDATE {SCHEMA}.analysis_results SET needs_review=NOT needs_review WHERE extraction_item_id IN (SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s)", (jobid,))
            elif change == "correction":
                cursor.execute(
                    f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by) "
                    f"SELECT i.id,j.source_message_id,'raw_memo','changed','test' "
                    f"FROM {SCHEMA}.extraction_items i JOIN {SCHEMA}.extraction_jobs j ON j.id=i.extraction_job_id WHERE j.id=%s LIMIT 1",
                    (jobid,),
                )
            elif change == "updated_at":
                cursor.execute("UPDATE public.products SET updated_at = updated_at + interval '1 second' WHERE product_code='PM0123'")
            else:
                cursor.execute("UPDATE public.products SET product_code='PM0999' WHERE product_code='PM0123'")
        return comparison.HEADER + "\n" + "\n".join(iid + "｜" for iid in item_ids)

    with pytest.raises(comparison.ComparisonError, match="INPUT_CHANGED"):
        comparison.compare_stale_job_snapshot(snap, factory, model_call=model)
