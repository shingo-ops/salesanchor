"""Real PostgreSQL read-only and production matcher parity, synthetic model only."""
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


def fixture_data(pg, monkeypatch):
    connection, engine, _ = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {SCHEMA}.product_search_keywords(id,product_id,keyword,position) SELECT %s,id,'共通商品',99 FROM {SCHEMA}.tcg_products WHERE code='PM0123'", (str(uuid4()),))
        cursor.execute(f"INSERT INTO {SCHEMA}.product_search_keywords(id,product_id,keyword,position) SELECT %s,id,'共通商品',99 FROM {SCHEMA}.tcg_products WHERE code='PM0200'", (str(uuid4()),))
    cases = [
        ("EB01 1BOX 1000円", record("EB01", 1)),
        ("メモリアルコレクション 1BOX 1000円", record("メモリアルコレクション", 1)),
        ("ワンピース\nEB01 1BOX 1000円", record("EB01", 2, "ワンピース", "L0001")),
        ("EB01 PSA10 1BOX 1000円", record("EB01", 1, state="PSA10")),
        ("メモリアルコレクション PSA10 1BOX 1000円", record("メモリアルコレクション", 1, state="PSA10")),
        ("共通商品 1BOX 1000円", record("共通商品", 1)),
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
    assert report["model_calls"] == 7 and not report["mismatches"]
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
                cursor.execute(f"UPDATE {SCHEMA}.tcg_products SET japanese_title='changed' WHERE code='PM0123'")
            elif change == "correction":
                cursor.execute(f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by) SELECT i.id,j.source_message_id,'raw_memo','changed','fixture' FROM {SCHEMA}.extraction_items i JOIN {SCHEMA}.extraction_jobs j ON j.id=i.extraction_job_id LIMIT 1")
            elif change == "analysis":
                cursor.execute(f"UPDATE {SCHEMA}.analysis_results SET needs_review=NOT needs_review")
            else:
                cursor.execute(f"UPDATE {SCHEMA}.import_job_messages SET relation_kind='reused' WHERE import_job_id=%s", (iid,))
        return comparison.HEADER
    with pytest.raises(comparison.ComparisonError, match="INPUT_CHANGED"):
        comparison.compare_snapshot(snap, factory, model_call=model)
