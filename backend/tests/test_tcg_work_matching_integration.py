"""v3 acceptance in unique databases of the disposable CI PostgreSQL service.

No database deletion: CI destroys its service after the job. Random databases
isolate generic migrations from xdist workers. Missing credentials fail, not skip.
Gemini outputs here are anonymous fixtures, never live model measurements.
"""
import asyncio
import hashlib
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2 import sql
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from app.services import gemini_extraction_svc as gemini
from app.services import tcg_analyzer_svc as analyzer
from app.services import tcg_distribution_svc as distribution
from app.services import tcg_diagnostics_svc as diagnostics
from app.services import tcg_product_master_svc as product_master
from app.tasks import tcg_extraction as extraction

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SCHEMA = "tenant_901"
STRUCTURE = "20260910_160000_tcg_work_evidence.sql"
DICTIONARY = "20260910_160100_tcg_normal_deck_coro_exclusion.sql"
HEADER = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN"
NORMAL = "MEGA スタートデッキ100 バトルコレクション"


def provision(cursor, schema):
    cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    cursor.execute((MIGRATIONS / "20260906_120000_create_tcg_tables_t001.sql").read_text().replace("tenant_001", schema))


def migrate(cursor):
    cursor.execute((MIGRATIONS / STRUCTURE).read_text())
    cursor.execute((MIGRATIONS / "20260912_020000_tcg_resolved_work_id.sql").read_text())
    cursor.execute((MIGRATIONS / DICTIONARY).read_text())


@pytest.fixture
def pg(monkeypatch):
    assert os.getenv("GITHUB_ACTIONS") == "true", "Disposable CI service required; databases retained until service shutdown"
    configured = os.getenv("RLS_ADMIN_DATABASE_URL")
    assert configured, "PostgreSQL acceptance MUST run: RLS_ADMIN_DATABASE_URL required"
    url = make_url(configured)
    assert url.host in ("localhost", "127.0.0.1"), "Refuse nonlocal server"
    assert url.database == "jarvis_test_db", "Refuse non-test administration database"
    kwargs = dict(host=url.host, port=url.port, user=url.username, password=url.password)
    name = "tcg_work_test_" + uuid4().hex
    admin = psycopg2.connect(dbname=url.database, **kwargs)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    finally:
        admin.close()
    connection = psycopg2.connect(dbname=name, **kwargs)
    connection.autocommit = True
    engine = create_engine(url.set(database=name, drivername="postgresql+psycopg2"))
    try:
        with connection.cursor() as cursor:
            provision(cursor, SCHEMA)
            cursor.execute("CREATE SCHEMA tenant_006; CREATE SCHEMA tenant_902")
            migrate(cursor)
        for module in (analyzer, extraction, distribution):
            monkeypatch.setattr(module, "TCG_SCHEMA", SCHEMA)
        monkeypatch.setenv("TCG_AUTO_ANALYZE", "1")
        yield connection, engine, url.set(database=name, drivername="postgresql+asyncpg")
    finally:
        engine.dispose()
        connection.close()


def seed_products(connection):
    products = [
        ("PM0123", "メモリアルコレクション", "IP002", ["EB-01", "EB01", "メモリアルコレクション"], []),
        ("PM0200", NORMAL, "IP001", ["MEGA スタートデッキ100", "スタートデッキ100"],
         ["Generations", "ex", "コロコロ", "コロちゃお", "コロチャオ"]),
        ("PM0285", "スタートデッキ100 コロちゃおVer.", "IP001", ["コロちゃお", "コロチャオ"], []),
    ]
    with connection.cursor() as cursor:
        for code, title, work, search, exclude in products:
            cursor.execute(f"""INSERT INTO {SCHEMA}.tcg_products
                (code,japanese_title,category_class,is_active,work_id,product_category_id)
                SELECT %s,%s,'Box',true,w.id,c.id FROM {SCHEMA}.tcg_series w,
                {SCHEMA}.tcg_product_categories c WHERE w.code=%s AND c.code='PC_BOX' RETURNING id""", (code, title, work))
            pid = cursor.fetchone()[0]
            for table, keywords in (("product_search_keywords", search), ("product_exclude_keywords", exclude)):
                for position, keyword in enumerate(keywords):
                    cursor.execute(f"INSERT INTO {SCHEMA}.{table}(id,product_id,keyword,position) VALUES (%s,%s,%s,%s)", (str(uuid4()), pid, keyword, position))
        cursor.execute(f"INSERT INTO {SCHEMA}.units(code,canonical,kubun,is_active) VALUES ('UN0001','BOX','箱系',true) RETURNING id")
        uid = cursor.fetchone()[0]
        cursor.execute(f"INSERT INTO {SCHEMA}.unit_aliases(unit_id,alias_text,lang) VALUES (%s,'BOX','ja')", (uid,))
        migrate(cursor)


def run_message(connection, engine, monkeypatch, raw, records, *, work_id_mode=False):
    smid, jobid = str(uuid4()), str(uuid4())
    with connection.cursor() as cursor:
        cursor.execute(f"""INSERT INTO {SCHEMA}.source_messages
            (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at)
            SELECT %s,id,%s,%s,true,now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
                       (smid, raw, hashlib.sha256(raw.encode()).hexdigest()))
        cursor.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (jobid, smid))
    header = HEADER + ("｜RESOLVED_WORK_ID" if work_id_mode else "")
    response = header + "\n" + "\n".join("｜".join(row) for row in records)
    if not work_id_mode:
        # Keep legacy 9-column end-to-end regressions while new jobs use v4.
        monkeypatch.setattr(extraction, "extract_message", lambda raw, **kw: gemini.extract_message(raw))
    monkeypatch.setattr(gemini, "call_gemini_extraction", lambda *args, **kwargs: response)
    with Session(engine) as session:
        result = extraction._run_extraction(session, smid)
    return smid, jobid, result


def record(name, line, work="", work_line="", state="", memo=""):
    return [name, "1", "1000", "BOX", state, memo, f"L{line:04d}", work, work_line]


def test_schema_migrations_existing_absent_future_and_repeat(pg):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        migrate(cursor)
        cursor.execute("SELECT table_schema,column_name,is_nullable,data_type FROM information_schema.columns WHERE column_name IN ('raw_work_name','raw_work_source_line_span')")
        columns = cursor.fetchall()
        assert len(columns) == 2 and all(row[0] == SCHEMA and row[2:] == ('YES', 'text') for row in columns)
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('tenant_006','tenant_902')")
        assert cursor.fetchone()[0] == 0
        cursor.execute((MIGRATIONS / "20260906_120000_create_tcg_tables_t001.sql").read_text().replace("tenant_001", "tenant_902"))
        migrate(cursor)
        migrate(cursor)
        cursor.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema='tenant_902' AND column_name IN ('raw_work_name','raw_work_source_line_span')")
        assert cursor.fetchone()[0] == 2
        cursor.execute(f"SELECT count(*) FROM {SCHEMA}.tcg_products")
        assert cursor.fetchone()[0] == 0


def test_dictionary_idempotent_and_identity_guard(pg):
    connection, _, _ = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        migrate(cursor)
        cursor.execute(f"SELECT keyword,position FROM {SCHEMA}.product_exclude_keywords e JOIN {SCHEMA}.tcg_products p ON p.id=e.product_id WHERE p.code='PM0200' ORDER BY position")
        assert cursor.fetchall() == [(word, i) for i, word in enumerate(["Generations", "ex", "コロコロ", "コロちゃお", "コロチャオ", "コロ"])]
        cursor.execute(f"SELECT count(*) FROM {SCHEMA}.tcg_products")
        assert cursor.fetchone()[0] == 3
        cursor.execute(f"UPDATE {SCHEMA}.tcg_products SET japanese_title='different' WHERE code='PM0200'")
        with pytest.raises(psycopg2.errors.RaiseException, match="identity mismatch"):
            cursor.execute((MIGRATIONS / DICTIONARY).read_text())
        cursor.execute(f"UPDATE {SCHEMA}.tcg_products SET japanese_title=%s,work_id=NULL WHERE code='PM0200'", (NORMAL,))
        with pytest.raises(psycopg2.errors.RaiseException, match="identity mismatch"):
            cursor.execute((MIGRATIONS / DICTIONARY).read_text())


def test_extract_analyze_29_historical_inputs_with_work_and_unknown_codes(pg, monkeypatch):
    connection, engine, _ = pg
    seed_products(connection)
    # Saved input counts, NOT 29 live-Gemini correct extractions.
    cases = [("ガンダム EB01", 16), ("◆Eternal Nexus [EB01]カートン", 6),
             ("◆Eternal Nexus [EB01]", 3), ("Eternal Nexus [EB01]カートン", 1),
             ("・ガンダム EB01", 2), ("Eternal Nexus [EB01]", 1)]
    names = [name for name, count in cases for _ in range(count)]
    assert len(names) == 29
    raw = "ガンダム\n" + "\n".join(names)
    records = [record(name, i, "ガンダム", f"L{i:04d}" if "ガンダム" in name else "L0001")
               for i, name in enumerate(names, 2)]
    _, jobid, result = run_message(connection, engine, monkeypatch, raw, records)
    assert result["status"] == "done" and result["items_count"] == 29
    assert result["analysis_stats"]["pid_resolved"] == 0
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT count(*), count(*) FILTER (WHERE ar.pid_resolved), count(*) FILTER (WHERE ar.needs_review AND ar.pid_basis='NONE') FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s", (jobid,))
        assert cursor.fetchone() == (29, 0, 29)
        cursor.execute(f"SELECT count(*) FROM {SCHEMA}.extraction_items WHERE raw_work_name='ガンダム' AND raw_work_source_line_span IS NOT NULL")
        assert cursor.fetchone()[0] == 29
    _, _, unknown = run_message(connection, engine, monkeypatch, "\n".join(["EB01"] * 29),
                                [record("EB01", i) for i in range(1, 30)])
    assert unknown["analysis_stats"]["pid_resolved"] == 0


def test_normal_limited_memo_scope_and_correction_preservation(pg, monkeypatch):
    connection, engine, async_url = pg
    seed_products(connection)
    names = [NORMAL, "MEGA スタートデッキ100", "MEGA スタートデッキ100 コロちゃおバージョン",
             "MEGA スタートデッキ100 バトルコレクション コロちゃおバージョン",
             "MEGA スタートデッキ100 コロちゃおバージョン",
             "スタートデッキ100 コロコロコミックver.", "スタートデッキ100 コロ"]
    records = [record(name, i, memo="コロちゃおバージョン" if i == 2 else "",
                      state="PSA10" if i == 3 else "") for i, name in enumerate(names, 1)]
    smid, jobid, result = run_message(connection, engine, monkeypatch, "\n".join(names), records)
    assert result["analysis_stats"]["pid_resolved"] == 3
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT ei.id,ei.line_start,p.code,ar.pid_resolved,ar.pid_basis,ar.needs_review FROM {SCHEMA}.extraction_items ei JOIN {SCHEMA}.analysis_results ar ON ar.extraction_item_id=ei.id LEFT JOIN {SCHEMA}.tcg_products p ON p.id=ar.product_id WHERE ei.extraction_job_id=%s ORDER BY ei.line_start", (jobid,))
        rows = cursor.fetchall()
        assert [r[2] for r in rows] == ['PM0200', None, None, 'PM0285', 'PM0285', None, None]
        assert rows[1][3:] == (False, 'NONE', True)
        corrected = rows[1][0]
        cursor.execute(f"UPDATE {SCHEMA}.analysis_results SET product_id=(SELECT id FROM {SCHEMA}.tcg_products WHERE code='PM0285'),pid_resolved=true,pid_basis='HUMAN:confirmed' WHERE extraction_item_id=%s", (corrected,))
        cursor.execute(f"INSERT INTO {SCHEMA}.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by) VALUES (%s,%s,'product_id','PM0285','test')", (corrected, smid))
        cursor.execute(f"SELECT product_id,pid_resolved,pid_basis FROM {SCHEMA}.analysis_results WHERE extraction_item_id=%s", (corrected,))
        before = cursor.fetchone()
    with Session(engine) as session:
        stats = analyzer.analyze_extraction_job(session, jobid)
    assert stats['skipped_product_corrections'] == 1
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT product_id,pid_resolved,pid_basis FROM {SCHEMA}.analysis_results WHERE extraction_item_id=%s", (corrected,))
        assert cursor.fetchone() == before

    async def output():
        async_engine = create_async_engine(async_url)
        try:
            async with AsyncSession(async_engine) as session:
                return await distribution.fetch_output_rows(session, include_flag_single=True)
        finally:
            await async_engine.dispose()
    candidates = asyncio.run(output())  # read-only, never delivery
    assert len(candidates) == 3  # PSA10 Box and the still-needs-review corrected row are excluded
    assert sum(r[2] == NORMAL for r in candidates) == 1


def test_v3_format_error_partial_save_zero_and_legacy_null_evidence(pg, monkeypatch):
    connection, engine, _ = pg
    seed_products(connection)
    _, jobid, result = run_message(connection, engine, monkeypatch, 'ガンダム EB01\nbad',
                                   [record('ガンダム EB01', 1, 'ガンダム', 'L0001'), ['bad', 'columns']])
    assert result['status'] == 'error' and result['items_count'] == 0
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT count(*) FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s', (jobid,))
        assert cursor.fetchone()[0] == 0
        cursor.execute(f"INSERT INTO {SCHEMA}.extraction_items(extraction_job_id,line_start,line_end,raw_product_name,raw_unit) VALUES (%s,1,1,'ガンダム EB01','BOX')", (jobid,))
    with Session(engine) as session:
        stats = analyzer.analyze_extraction_job(session, jobid)
    assert stats['total'] == 1 and stats['pid_resolved'] == 0
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT raw_work_name,raw_work_source_line_span FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s', (jobid,))
        assert cursor.fetchone() == (None, None)


def test_onepiece_code_positive_with_verified_work(pg, monkeypatch):
    connection, engine, _ = pg
    seed_products(connection)
    _, jobid, result = run_message(connection, engine, monkeypatch,
        "ワンピース EB01", [record("ワンピース EB01", 1, "ワンピース", "L0001")])
    assert result["analysis_stats"]["pid_resolved"] == 1
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT p.code,ar.pid_resolved,ar.engine_version FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.tcg_products p ON p.id=ar.product_id JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s", (jobid,))
        assert cursor.fetchone() == ("PM0123", True, "name-first-v7-gemini-work-id")


RECOVERY = "20260910_180000_tcg_interrupted_jobs_recovery_t004.sql"
CONDITION_NOTE = "20260910_200000_tcg_condition_note_delivery_t004.sql"


def seed_condition_note(connection, schema="tenant_004"):
    with connection.cursor() as cursor:
        provision(cursor, schema)
        for migration in ["20260903_130000_tcg_note_master_t004.sql",
                          "20260907_100000_tcg_note_master_expand_t004.sql",
                          "20260903_160000_tcg_normalization_rules_t004.sql",
                          "20260903_190000_tcg_normalization_rules_nr0136.sql",
                          "20260909_130000_tcg_note_b2_t004.sql",
                          "20260903_220000_create_tcg_analysis_history_t004.sql"]:
            cursor.execute((MIGRATIONS / migration).read_text().replace("tenant_004", schema))
        cursor.execute(sql.SQL("INSERT INTO {}.conditions(code,canonical,is_active,priority,app_kubun,search_kw,exclude_kw) VALUES ('CN0007','Unsearched pack',true,3,'','未サーチ,サーチなし,サーチ痕なし,サーチ痕無し,サーチ無し','[サーチ済み]'),('CN0001','Case',true,NULL,'','',''),('CN0003','Sealed box',true,NULL,'','',''),('CN0010','Searched pack',true,NULL,'','','')").format(sql.Identifier(schema)))


def condition_note_snapshot(connection, schemas=("tenant_004",)):
    result = {}
    with connection.cursor() as cursor:
        for schema in schemas:
            for table in ("conditions", "tcg_note_master"):
                cursor.execute(sql.SQL("SELECT row_to_json(t)::text FROM {}.{} t ORDER BY id").format(sql.Identifier(schema), sql.Identifier(table)))
                result[schema, table] = cursor.fetchall()
    return result


@pytest.mark.parametrize("partial", ["none", "condition", "old_note", "new_note"])
def test_condition_note_master_changes_repeat_partial_and_other_tenant(pg, partial):
    import json

    connection, _, _ = pg
    for schema in ("tenant_004", "tenant_905"):
        seed_condition_note(connection, schema)
    before = condition_note_snapshot(connection, ("tenant_004", "tenant_905"))
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
    after = condition_note_snapshot(connection, ("tenant_004", "tenant_905"))
    for key, rows in before.items():
        new_rows = [json.loads(r[0]) for r in after[key]]
        old_rows = [json.loads(r[0]) for r in rows]
        if key[0] != "tenant_004":
            assert rows == after[key]
        elif key[1] == "conditions":
            for old, new in zip(old_rows, new_rows):
                if old["code"] == "CN0007":
                    assert len(new["exclude_kw"].split(",")) == 7
                    new["exclude_kw"] = old["exclude_kw"]
                assert new == old
        else:
            assert len(new_rows) == len(old_rows) + 1
            for old in old_rows:
                new = next(r for r in new_rows if r["id"] == old["id"])
                if old["id"] == "NJ041":
                    assert new["exclude_keywords"] == "伝票剥がし跡あり"
                    new["exclude_keywords"] = old["exclude_keywords"]
                assert new == old
    with connection.cursor() as cursor:
        if partial in ("condition", "new_note"):
            cursor.execute("UPDATE tenant_004.conditions SET exclude_kw='[サーチ済み]' WHERE code='CN0007'")
        if partial in ("old_note", "new_note"):
            cursor.execute("UPDATE tenant_004.tcg_note_master SET exclude_keywords='' WHERE id='NJ041'")
        cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
        cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
    assert condition_note_snapshot(connection, ("tenant_004", "tenant_905")) == after


@pytest.mark.parametrize("target,field,value", [
    ("condition", "canonical", "wrong"), ("condition", "search_kw", "wrong"),
    ("condition", "exclude_kw", "wrong"), ("condition", "code", "missing"),
    ("note", "label_ja", "wrong"), ("note", "search_keywords", "wrong"),
    ("note", "exclude_keywords", "wrong"), ("note", "id", "missing"),
    ("collision", "label_ja", "wrong"),
])
def test_condition_note_invalid_master_rolls_back(pg, target, field, value):
    connection, _, _ = pg
    seed_condition_note(connection)
    with connection.cursor() as cursor:
        if target == "collision":
            cursor.execute("INSERT INTO tenant_004.tcg_note_master(id,label_ja,label_en,priority) VALUES ('NJ079','wrong','wrong',1)")
        else:
            table, key, identity = ("conditions", "code", "CN0007") if target == "condition" else ("tcg_note_master", "id", "NJ041")
            cursor.execute(sql.SQL("UPDATE tenant_004.{} SET {}=%s WHERE {}=%s").format(sql.Identifier(table), sql.Identifier(field), sql.Identifier(key)), (value, identity))
        before = condition_note_snapshot(connection)
        with pytest.raises(psycopg2.errors.RaiseException, match="unexpected master|identity collision"):
            cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
        cursor.execute("ROLLBACK")
    assert condition_note_snapshot(connection) == before


@pytest.mark.parametrize("missing", [None, "conditions", "tcg_note_master"])
def test_condition_note_absent_and_partial_tables(pg, missing):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        if missing is None:
            cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
        else:
            seed_condition_note(connection)
            before = condition_note_snapshot(connection)
            cursor.execute(sql.SQL("ALTER TABLE tenant_004.{} RENAME TO temporarily_absent").format(sql.Identifier(missing)))
            try:
                with pytest.raises(psycopg2.errors.RaiseException, match="incomplete master structure"):
                    cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
            finally:
                cursor.execute("ROLLBACK")
                cursor.execute(sql.SQL("ALTER TABLE tenant_004.temporarily_absent RENAME TO {}").format(sql.Identifier(missing)))
            assert condition_note_snapshot(connection) == before


def test_condition_note_lock_timeout(pg):
    connection, engine, _ = pg
    seed_condition_note(connection)
    before = condition_note_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        settings = cursor.fetchone()
        blocker = engine.raw_connection()
        try:
            with blocker.cursor() as other:
                other.execute("LOCK TABLE tenant_004.tcg_note_master IN SHARE ROW EXCLUSIVE MODE")
            with pytest.raises(psycopg2.errors.LockNotAvailable, match="lock timeout"):
                cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
            cursor.execute("ROLLBACK")
        finally:
            blocker.rollback()
            blocker.close()
        assert condition_note_snapshot(connection) == before
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        assert cursor.fetchone() == settings
        cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        assert cursor.fetchone() == settings


def test_condition_note_18_items_history_twice_and_distribution(pg, monkeypatch):
    import sys

    connection, engine, async_url = pg
    seed_condition_note(connection)
    monkeypatch.setattr(sys.modules[__name__], "SCHEMA", "tenant_004")
    for module in (analyzer, extraction, distribution, product_master):
        monkeypatch.setattr(module, "TCG_SCHEMA", "tenant_004")
    monkeypatch.setattr(product_master, "_SYNC_DB_URL", str(engine.url.render_as_string(hide_password=False)))
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / STRUCTURE).read_text())
        for code, name in [("PM0268", "匿名パック"), ("PM0141", "匿名箱")]:
            cursor.execute("INSERT INTO tenant_004.tcg_products(code,japanese_title,category_class,is_active) VALUES (%s,%s,'Box',true) RETURNING id", (code, name))
            pid = cursor.fetchone()[0]
            cursor.execute("INSERT INTO tenant_004.product_search_keywords(product_id,keyword,position) VALUES (%s,%s,1)", (pid, name))
        for code, canonical, kubun in [("UN0001", "CASE", "箱系大"), ("UN0002", "BOX", "箱系"), ("UN0003", "Pack", "パック系")]:
            cursor.execute("INSERT INTO tenant_004.units(code,canonical,kubun,is_active) VALUES (%s,%s,%s,true) RETURNING id", (code, canonical, kubun))
            cursor.execute("INSERT INTO tenant_004.unit_aliases(unit_id,alias_text,lang) VALUES (%s,%s,'ja')", (cursor.fetchone()[0], canonical))
    records = [record("匿名パック", 1, memo="※未サーチ品"), record("匿名箱", 2, state="伝票剥がし跡あり")]
    records[0][3], records[1][3] = "Pack", "CASE"
    records += [record("匿名箱", i) for i in range(3, 19)]
    # Master absent for memo handling until migration: baseline is old behavior.
    original = analyzer.resolve_condition_v2
    monkeypatch.setattr(analyzer, "resolve_condition_v2", lambda *args, **kw: original(*args))
    _, jobid, result = run_message(connection, engine, monkeypatch, "\n".join(r[0] for r in records), records)
    assert result["analysis_stats"]["total"] == 18
    monkeypatch.setattr(analyzer, "resolve_condition_v2", original)

    def values():
        with connection.cursor() as cursor:
            cursor.execute("SELECT ar.product_id,ar.quantity_normalized,ar.price_normalized,ar.status,ar.unit_id,ar.unit_canonical,ar.condition_canonical,ar.note_ja FROM tenant_004.analysis_results ar JOIN tenant_004.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s ORDER BY ei.line_start", (jobid,))
            return cursor.fetchall()
    before = values()
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
    first = asyncio.run(product_master.reanalyze_extraction_job(jobid))
    after = values()
    assert before[0][6] == "Searched pack" and after[0][6] == "Unsearched pack"
    assert before[1][6:] == ("Case", None) and after[1][6:] == ("Case", "伝票剥がし跡あり")
    assert all(a[:6] == b[:6] for a, b in zip(before, after))
    assert before[2:] == after[2:]
    second = asyncio.run(product_master.reanalyze_extraction_job(jobid))
    assert values() == after and first["run_id"] != second["run_id"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM tenant_004.analysis_runs WHERE extraction_job_id=%s AND completed_at IS NOT NULL", (jobid,))
        assert cursor.fetchone()[0] == 2
        cursor.execute("SELECT count(*) FROM tenant_004.analysis_run_snapshots WHERE run_id=ANY(%s::uuid[])", ([first["run_id"], second["run_id"]],))
        assert cursor.fetchone()[0] == 36

    async def outputs():
        async_engine = create_async_engine(async_url)
        try:
            async with AsyncSession(async_engine) as session:
                return await distribution.fetch_output_rows(session)
        finally:
            await async_engine.dispose()
    rows = asyncio.run(outputs())
    assert len(rows) == 18
    assert sum(r[4] == "Unsearched pack" for r in rows) == 1
    assert sum(r[4] == "Case" and r[7] == "伝票剥がし跡あり" for r in rows) == 1
RECOVERY_JOBS = ["6da3ca68-651e-4ff6-8316-1c9135508ad2", "bfa07018-9b34-42b6-990a-017e3c1cf140"]
RECOVERY_SOURCES = ["b1b58ee9-0d6a-4ed1-8034-f1d62a72b4b2", "afbc08d1-cf3b-43be-87e5-4b7200144b6c"]
RECOVERY_SUCCESSOR = "3a4633b1-82a6-4ce5-8694-053cd637c5f6"
RECOVERY_ERROR = "LINE-RECOVERY-20260910: interrupted job; PO-approved recovery"


def seed_recovery(connection, schema="tenant_004", count=2):
    with connection.cursor() as cursor:
        provision(cursor, schema)
        for i, source in enumerate([RECOVERY_SUCCESSOR, *RECOVERY_SOURCES]):
            raw = f"Anonymous product list {i}"
            cursor.execute(sql.SQL("INSERT INTO {}.source_messages(id,raw_text,raw_sha256,is_active,superseded_by) VALUES (%s,%s,%s,%s,%s)").format(sql.Identifier(schema)),
                (source, raw, hashlib.sha256(raw.encode()).hexdigest(), i != 1, RECOVERY_SUCCESSOR if i == 1 else None))
        for job, source in zip(RECOVERY_JOBS[:count], RECOVERY_SOURCES[:count]):
            cursor.execute(sql.SQL("INSERT INTO {}.extraction_jobs(id,source_message_id,status,created_at) VALUES (%s,%s,'running','2026-09-10T02:49:21.105805Z')").format(sql.Identifier(schema)), (job, source))
        cursor.execute(sql.SQL("INSERT INTO {}.extraction_jobs(source_message_id,status) VALUES (%s,'running')").format(sql.Identifier(schema)), (RECOVERY_SUCCESSOR,))


def recovery_snapshot(connection, schemas=("tenant_004",)):
    result = {}
    with connection.cursor() as cursor:
        for schema in schemas:
            for table in ("source_messages", "extraction_jobs", "extraction_items"):
                cursor.execute(sql.SQL("SELECT row_to_json(t)::text FROM {}.{} t ORDER BY id").format(sql.Identifier(schema), sql.Identifier(table)))
                result[schema, table] = cursor.fetchall()
    return result


def test_interrupted_recovery_exact_changes_repeat_and_single_retry(pg, monkeypatch):
    import json

    connection, _, async_url = pg
    for schema in ("tenant_004", "tenant_904"):
        seed_recovery(connection, schema)
    before = recovery_snapshot(connection, ("tenant_004", "tenant_904"))
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / RECOVERY).read_text())
    after = recovery_snapshot(connection, ("tenant_004", "tenant_904"))
    for key, rows in before.items():
        if key != ("tenant_004", "extraction_jobs"):
            assert rows == after[key]
            continue
        expected = []
        for (serialized,) in rows:
            row = json.loads(serialized)
            if row["id"] in RECOVERY_JOBS:
                row.update(status="error", error_message=RECOVERY_ERROR)
            expected.append(row)
        assert expected == [json.loads(row[0]) for row in after[key]]
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / RECOVERY).read_text())
    assert recovery_snapshot(connection, ("tenant_004", "tenant_904")) == after

    queued = []
    monkeypatch.setattr(diagnostics, "TCG_SCHEMA", "tenant_004")
    monkeypatch.setattr(extraction.extract_source_message_task, "apply_async", lambda **kw: queued.append(kw))

    async def retry():
        engine = create_async_engine(async_url)
        try:
            async with AsyncSession(engine) as session:
                return await diagnostics.retry_extraction(session, job_ids=[RECOVERY_JOBS[1]], scope=None)
        finally:
            await engine.dispose()
    assert asyncio.run(retry()) == {"enqueued": 1, "skipped": 0}
    assert queued == [{"args": (RECOVERY_SOURCES[1],), "countdown": 0}]
    with connection.cursor() as cursor:
        cursor.execute("SELECT id::text,status,error_message FROM tenant_004.extraction_jobs WHERE id=ANY(%s::uuid[]) ORDER BY id", (RECOVERY_JOBS,))
        assert cursor.fetchall() == [(RECOVERY_JOBS[0], "error", RECOVERY_ERROR), (RECOVERY_JOBS[1], "pending", RECOVERY_ERROR)]
    retried = recovery_snapshot(connection, ("tenant_004", "tenant_904"))
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / RECOVERY).read_text())
    assert recovery_snapshot(connection, ("tenant_004", "tenant_904")) == retried


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("field", ["source_message_id", "created_at", "is_active", "superseded_by", "extracted_at", "prompt_version", "error_message", "items"])
def test_interrupted_recovery_precondition_failure_preserves_all(pg, index, field):
    connection, _, _ = pg
    seed_recovery(connection)
    with connection.cursor() as cursor:
        if field == "items":
            cursor.execute("INSERT INTO tenant_004.extraction_items(extraction_job_id,raw_product_name) VALUES (%s,'Anonymous item')", (RECOVERY_JOBS[index],))
        elif field == "is_active":
            cursor.execute("UPDATE tenant_004.source_messages SET is_active=NOT is_active WHERE id=%s", (RECOVERY_SOURCES[index],))
        elif field == "superseded_by":
            cursor.execute("UPDATE tenant_004.source_messages SET superseded_by=%s WHERE id=%s", (None if index == 0 else RECOVERY_SUCCESSOR, RECOVERY_SOURCES[index]))
        else:
            value = {"source_message_id": RECOVERY_SUCCESSOR, "created_at": "2026-09-10T02:49:22Z",
                     "extracted_at": "2026-09-10T03:00:00Z", "prompt_version": "v3", "error_message": "already attempted"}[field]
            cursor.execute(sql.SQL("UPDATE tenant_004.extraction_jobs SET {}=%s WHERE id=%s").format(sql.Identifier(field)), (value, RECOVERY_JOBS[index]))
        before = recovery_snapshot(connection)
        with pytest.raises(psycopg2.errors.RaiseException, match="identity mismatch|precondition mismatch"):
            cursor.execute((MIGRATIONS / RECOVERY).read_text())
        cursor.execute("ROLLBACK")
    assert recovery_snapshot(connection) == before


@pytest.mark.parametrize("status", ["done", "empty", "error", "pending"])
@pytest.mark.parametrize("index", [0, 1])
def test_interrupted_recovery_nonrunning_retained(pg, status, index):
    connection, _, _ = pg
    seed_recovery(connection)
    with connection.cursor() as cursor:
        cursor.execute("UPDATE tenant_004.extraction_jobs SET status=%s,error_message='retained',prompt_version='v3',extracted_at=now() WHERE id=%s", (status, RECOVERY_JOBS[index]))
        cursor.execute("SELECT row_to_json(j)::text FROM tenant_004.extraction_jobs j WHERE id=%s", (RECOVERY_JOBS[index],))
        before = cursor.fetchone()
        cursor.execute((MIGRATIONS / RECOVERY).read_text())
        cursor.execute("SELECT row_to_json(j)::text FROM tenant_004.extraction_jobs j WHERE id=%s", (RECOVERY_JOBS[index],))
        assert cursor.fetchone() == before
        cursor.execute("SELECT status,error_message FROM tenant_004.extraction_jobs WHERE id=%s", (RECOVERY_JOBS[1-index],))
        assert cursor.fetchone() == ("error", RECOVERY_ERROR)


@pytest.mark.parametrize("count", [0, 1])
def test_interrupted_recovery_absent_job_contract(pg, count):
    connection, _, _ = pg
    seed_recovery(connection, count=count)
    before = recovery_snapshot(connection)
    with connection.cursor() as cursor:
        if count == 1:
            with pytest.raises(psycopg2.errors.RaiseException, match="one target job missing"):
                cursor.execute((MIGRATIONS / RECOVERY).read_text())
            cursor.execute("ROLLBACK")
        else:
            cursor.execute((MIGRATIONS / RECOVERY).read_text())
    assert recovery_snapshot(connection) == before


def test_interrupted_recovery_absent_tables_noop(pg):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / RECOVERY).read_text())
        cursor.execute("CREATE SCHEMA tenant_004")
        cursor.execute((MIGRATIONS / RECOVERY).read_text())
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='tenant_004'")
        assert cursor.fetchone()[0] == 0


@pytest.mark.parametrize("table", ["source_messages", "extraction_jobs", "extraction_items"])
def test_interrupted_recovery_partial_tables_fail(pg, table):
    connection, _, _ = pg
    seed_recovery(connection)
    before = recovery_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("ALTER TABLE tenant_004.{} RENAME TO temporarily_absent").format(sql.Identifier(table)))
        try:
            with pytest.raises(psycopg2.errors.RaiseException, match="incomplete TCG structure"):
                cursor.execute((MIGRATIONS / RECOVERY).read_text())
        finally:
            cursor.execute("ROLLBACK")
            cursor.execute(sql.SQL("ALTER TABLE tenant_004.temporarily_absent RENAME TO {}").format(sql.Identifier(table)))
    assert recovery_snapshot(connection) == before


def test_interrupted_recovery_lock_timeout_and_settings(pg):
    connection, engine, _ = pg
    seed_recovery(connection)
    before = recovery_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        settings = cursor.fetchone()
        blocker = engine.raw_connection()
        try:
            with blocker.cursor() as other:
                other.execute("LOCK TABLE tenant_004.extraction_items IN SHARE ROW EXCLUSIVE MODE")
            with pytest.raises(psycopg2.errors.LockNotAvailable, match="lock timeout"):
                cursor.execute((MIGRATIONS / RECOVERY).read_text())
            cursor.execute("ROLLBACK")
        finally:
            blocker.rollback()
            blocker.close()
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        assert cursor.fetchone() == settings
        assert recovery_snapshot(connection) == before
        cursor.execute((MIGRATIONS / RECOVERY).read_text())
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        assert cursor.fetchone() == settings


def seed_guard_dictionary(connection, schema):
    with connection.cursor() as cursor:
        provision(cursor, schema)
        products = [*GUARD_PRODUCTS, ("PM_OTHER", "別商品", "IP001", "PC_BOX",
                    [("vol.1", 3)], [("マスターボールミラー", 8)])]
        for code, title, work, category, search, exclude in products:
            cursor.execute(sql.SQL("""INSERT INTO {}.tcg_products
                (code,japanese_title,category_class,is_active,work_id,product_category_id)
                SELECT %s,%s,'Box',true,w.id,c.id FROM {}.tcg_series w,
                {}.tcg_product_categories c WHERE w.code=%s AND c.code=%s RETURNING id""").format(
                    *[sql.Identifier(schema)] * 3), (code, title, work, category))
            pid = cursor.fetchone()[0]
            for table, entries in (("product_search_keywords", search), ("product_exclude_keywords", exclude)):
                for word, position in entries:
                    cursor.execute(sql.SQL("INSERT INTO {}.{}(id,product_id,keyword,position) VALUES (%s,%s,%s,%s)").format(
                        sql.Identifier(schema), sql.Identifier(table)), (str(uuid4()), pid, word, position))


def guard_snapshot(connection, schemas=("tenant_004", "tenant_903")):
    result = {}
    with connection.cursor() as cursor:
        for schema in schemas:
            for table in ("product_search_keywords", "product_exclude_keywords"):
                cursor.execute(sql.SQL("SELECT k.id,k.product_id,k.keyword,k.position,p.code FROM {}.{} k JOIN {}.tcg_products p ON p.id=k.product_id ORDER BY k.id").format(
                    sql.Identifier(schema), sql.Identifier(table), sql.Identifier(schema)))
                result[schema, table] = cursor.fetchall()
    return result


def test_false_positive_guards_exact_changes_idempotency_and_26_inputs(pg, monkeypatch):
    connection, engine, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_guard_dictionary(connection, schema)
    monkeypatch.setattr(analyzer, "TCG_SCHEMA", "tenant_004")
    codes = [product[0] for product in GUARD_PRODUCTS]

    def evaluate(cases):
        with Session(engine) as session:
            search, exclude = analyzer.load_product_keywords(session)
        return [analyzer.match_pid_with_work(name, codes, search, exclude,
                    work_id=None, product_work_ids={}, raw_state=state, raw_memo=memo)
                for name, state, memo in cases]

    wrong = [(name, "", "") for name, _ in GUARD_WRONG_INPUTS]
    assert len(wrong) == 10 and len(GUARD_CONTROLS) == 16
    previous = evaluate(wrong)
    assert [row[0] for row in previous] == [code for _, code in GUARD_WRONG_INPUTS]
    assert all(row[2] for row in previous)
    old_controls = evaluate([row[:3] for row in GUARD_CONTROLS])
    before = guard_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / GUARDS).read_text())
    after = guard_snapshot(connection)
    search_key = ("tenant_004", "product_search_keywords")
    exclude_key = ("tenant_004", "product_exclude_keywords")
    assert after[search_key] == [r for r in before[search_key] if not (r[4] == "PM0230" and r[2] == "vol.1")]
    assert len(before[search_key]) - len(after[search_key]) == 1
    assert set(before[exclude_key]).issubset(set(after[exclude_key]))
    added = set(after[exclude_key]) - set(before[exclude_key])
    assert {(r[4], r[2], r[3]) for r in added} == {
        ("PM0104", "マスターボールミラー", 28), ("PM0184", "スペシャルデッキセット", 2)}
    for table in ("product_search_keywords", "product_exclude_keywords"):
        assert before["tenant_903", table] == after["tenant_903", table]
        assert [r for r in before["tenant_004", table] if r[4] == "PM_OTHER"] == [
            r for r in after["tenant_004", table] if r[4] == "PM_OTHER"]
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / GUARDS).read_text())
    assert guard_snapshot(connection) == after
    assert evaluate(wrong) == [(None, "NONE", False, [])] * 10
    current = evaluate([row[:3] for row in GUARD_CONTROLS])
    for old, actual, (_, _, _, expected) in zip(old_controls, current, GUARD_CONTROLS):
        if expected:
            assert actual == old and actual[0] == expected and actual[2]
        else:
            assert actual == (None, "NONE", False, [])


@pytest.mark.parametrize("code", ["PM0230", "PM0104", "PM0184"])
@pytest.mark.parametrize("field", ["japanese_title", "work_id", "product_category_id", "code"])
def test_false_positive_guards_identity_mismatch_preserves_all(pg, code, field):
    connection, _, _ = pg
    seed_guard_dictionary(connection, "tenant_004")
    with connection.cursor() as cursor:
        if field in ("work_id", "product_category_id"):
            cursor.execute(sql.SQL("UPDATE tenant_004.tcg_products SET {}=NULL WHERE code=%s").format(sql.Identifier(field)), (code,))
        else:
            cursor.execute(sql.SQL("UPDATE tenant_004.tcg_products SET {}='different' WHERE code=%s").format(sql.Identifier(field)), (code,))
        before = guard_snapshot(connection, ("tenant_004",))
        with pytest.raises(psycopg2.errors.RaiseException, match="identity mismatch"):
            cursor.execute((MIGRATIONS / GUARDS).read_text())
        cursor.execute("ROLLBACK")
    assert guard_snapshot(connection, ("tenant_004",)) == before


@pytest.mark.parametrize("code,table,word", [
    ("PM0230", "product_search_keywords", "vol.1"),
    ("PM0104", "product_exclude_keywords", "マスターボールミラー"),
    ("PM0184", "product_exclude_keywords", "スペシャルデッキセット"),
])
def test_false_positive_guards_duplicate_preserves_all(pg, code, table, word):
    connection, _, _ = pg
    seed_guard_dictionary(connection, "tenant_004")
    with connection.cursor() as cursor:
        for _ in range(1 if code == "PM0230" else 2):
            cursor.execute(sql.SQL("INSERT INTO tenant_004.{}(id,product_id,keyword,position) SELECT %s,id,%s,99 FROM tenant_004.tcg_products WHERE code=%s").format(sql.Identifier(table)),
                           (str(uuid4()), word, code))
        before = guard_snapshot(connection, ("tenant_004",))
        with pytest.raises(psycopg2.errors.RaiseException, match="duplicate target keyword"):
            cursor.execute((MIGRATIONS / GUARDS).read_text())
        cursor.execute("ROLLBACK")
    assert guard_snapshot(connection, ("tenant_004",)) == before


def test_false_positive_guards_absent_tables_noop(pg):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / GUARDS).read_text())
        cursor.execute("CREATE SCHEMA tenant_004")
        cursor.execute((MIGRATIONS / GUARDS).read_text())
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='tenant_004'")
        assert cursor.fetchone()[0] == 0


def test_false_positive_guards_lock_timeout_preserves_dictionary_and_settings(pg):
    connection, engine, _ = pg
    seed_guard_dictionary(connection, "tenant_004")
    before = guard_snapshot(connection, ("tenant_004",))
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        settings = cursor.fetchone()
        blocker = engine.raw_connection()
        try:
            with blocker.cursor() as blocking_cursor:
                blocking_cursor.execute("LOCK TABLE tenant_004.product_exclude_keywords IN SHARE ROW EXCLUSIVE MODE")
            with pytest.raises(psycopg2.errors.LockNotAvailable, match="lock timeout"):
                cursor.execute((MIGRATIONS / GUARDS).read_text())
            cursor.execute("ROLLBACK")
        finally:
            blocker.rollback()
            blocker.close()
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        assert cursor.fetchone() == settings
        assert guard_snapshot(connection, ("tenant_004",)) == before
        cursor.execute((MIGRATIONS / GUARDS).read_text())
        cursor.execute("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
        assert cursor.fetchone() == settings


@pytest.mark.parametrize("table", ["tcg_products", "tcg_series", "tcg_product_categories",
                                 "product_search_keywords", "product_exclude_keywords"])
def test_false_positive_guards_partial_structure_stops(pg, table):
    connection, _, _ = pg
    seed_guard_dictionary(connection, "tenant_004")
    before = guard_snapshot(connection, ("tenant_004",))
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("ALTER TABLE tenant_004.{} RENAME TO temporarily_absent").format(sql.Identifier(table)))
        try:
            with pytest.raises(psycopg2.errors.RaiseException, match="incomplete TCG structure"):
                cursor.execute((MIGRATIONS / GUARDS).read_text())
        finally:
            cursor.execute("ROLLBACK")
            cursor.execute(sql.SQL("ALTER TABLE tenant_004.temporarily_absent RENAME TO {}").format(sql.Identifier(table)))
    assert guard_snapshot(connection, ("tenant_004",)) == before


# Dictionary fixtures contain product labels only, with newly generated IDs.
GUARDS = "20260910_170000_tcg_keyword_false_positive_guards.sql"
GUARD_PRODUCTS = [('PM0104', 'ポケモンカード151', 'IP001', 'PC_BOX', [('ポケモンカード151', 2), ('151', 1)], [('vol.3', 1), ('hope', 3), ('jumbo', 6), ('surprised', 4), ('slim', 5), ('収集啦', 17), ('fat', 7), ('礼盒', 27), ('journey', 2)]), ('PM0184', 'スターターセットMEGA メガゲンガーex', 'IP001', 'PC_BOX', [('メガゲンガー', 1), ('メガゲンガーex', 4), ('MEGAゲンガーex', 2), ('MEGAゲンガー', 3)], [('MEGディアンシー', 1)]), ('PM0230', 'トライアルデッキ 【推しの子】', 'IP007', 'PC_SINGLE', [('OSK', 3), ('推しの子', 1), ('oshi no ko', 2), ('vol.1', 5), ('trial deck', 4)], [])]
GUARD_WRONG_INPUTS = [('リミテッドカードコレクション Vol.1', 'PM0230'), ('■スペシャルデッキセットMEGA メガオーダイル・メガカイリュー・メガゲンガー', 'PM0184'), ('マスターボールミラー151のみ', 'PM0104'), ('リミテッドカードコレクションvol.1', 'PM0230'), ('LIMIT OVER SPECIAL PACK Vol.1', 'PM0230'), ('BASE SHOP リミテッドカードコレクションvol.1', 'PM0230'), ('BASE SHOP vol.1', 'PM0230'), ('プレミアムカードコレクション  – 6 assort vol.1 -', 'PM0230'), ('プレミアムカードコレクション- ベストセレクションvol.1 -', 'PM0230'), ('プレミアムカードコレクション 6 assort vol.1', 'PM0230')]
GUARD_CONTROLS = [('推しの子 vol.1', '', '', 'PM0230'), ('推しの子', '', '', 'PM0230'), ('ポケモンカード151', '', '', 'PM0104'), ('151', '', '', 'PM0104'), ('スターターセットMEGA メガゲンガーex', '', '', 'PM0184'), ('BASE SHOP vol.1', '', '', None), ('リミテッドカードコレクション Vol.1', '', '', None), ('151', 'マスターボールミラー', '', None), ('151', '', 'マスターボールミラー', None), ('メガゲンガー', 'スペシャルデッキセット', '', None), ('メガゲンガー', '', 'スペシャルデッキセット', None), ('vol.1', '', '', None), ('BASE SHOP vol.10', '', '', None), ('BASE SHOP vol.11', '', '', None), ('リミテッドカードコレクション vol.10', '', '', None), ('BASE SHOP vol.2', '', '', None)]


@pytest.mark.parametrize("heading,state,memo,resolved", [
    ("【ワンピース】", "", "", True),
    ("🟡ONE PIECE在庫🟡", "", "", True),
    ("【ワンピース】", "PSA10", "", False),
    ("【ワンピース】", "", "SAR", False),
    ("【ガンダム】", "", "", False),
])
def test_raw_heading_and_box_guard_through_analysis(pg, monkeypatch, heading, state, memo, resolved):
    connection, engine, _ = pg
    seed_products(connection)
    _, jobid, result = run_message(connection, engine, monkeypatch,
        heading + "\nEB01 1000円 1BOX", [record("EB01", 2, state=state, memo=memo)])
    assert result["analysis_stats"]["pid_resolved"] == int(resolved)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT ar.pid_resolved,ar.pid_basis FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s", (jobid,))
        actual, basis = cursor.fetchone()
        assert actual is resolved
        if resolved:
            assert basis.startswith("WORK_HEADER:L1|")


@pytest.fixture(autouse=True)
def prohibit_live_gemini(monkeypatch):
    def forbidden():
        pytest.fail("Gemini live calls are forbidden in tests")
    monkeypatch.setattr(gemini, "_get_genai_client", forbidden)


def test_work_id_v4_database_roundtrip_and_review_filter(pg, monkeypatch):
    connection, engine, async_url = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {SCHEMA}.tcg_series WHERE code='IP002'")
        wid = str(cursor.fetchone()[0])
    raw = "◆EB01 1BOX 1000円"
    _, jid, result = run_message(connection, engine, monkeypatch, raw,
        [record("◆EB01", 1) + [wid]], work_id_mode=True)
    assert result["status"] == "done" and result["items_count"] == 1
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT ei.raw_product_name,ei.raw_work_name,ei.resolved_work_id,ar.pid_resolved,ar.pid_basis FROM {SCHEMA}.extraction_items ei JOIN {SCHEMA}.analysis_results ar ON ar.extraction_item_id=ei.id WHERE ei.extraction_job_id=%s", (jid,))
        row = cursor.fetchone()
        assert row[0:2] == ("◆EB01", "") and str(row[2]) == wid
        assert row[3] and row[4].startswith("GEMINI|WORK:")
        cursor.execute(f"SELECT work_reference_snapshot,work_reference_sha256 FROM {SCHEMA}.extraction_jobs WHERE id=%s", (jid,))
        ref, digest = cursor.fetchone()
        from app.services.tcg_work_reference import reference_digest
        assert reference_digest(ref) == digest
        cursor.execute(f"UPDATE {SCHEMA}.analysis_results SET needs_review=false,condition_canonical='Sealed box',unit_resolved=true,price_normalized=1000 WHERE extraction_item_id IN (SELECT id FROM {SCHEMA}.extraction_items WHERE extraction_job_id=%s)", (jid,))

    async def fetch():
        ae = create_async_engine(async_url)
        try:
            async with AsyncSession(ae) as session:
                return await distribution.fetch_output_rows(session)
        finally:
            await ae.dispose()
    assert len(asyncio.run(fetch())) == 1
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE {SCHEMA}.analysis_results SET needs_review=true")
    assert asyncio.run(fetch()) == []
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE {SCHEMA}.tcg_products SET japanese_title='changed' WHERE code='PM0123'")
    with Session(engine) as session, pytest.raises(ValueError, match="reference changed"):
        analyzer.analyze_extraction_job(session, jid)


def test_work_id_schema_existing_future_and_repeat(pg):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        migrate(cursor)
        provision(cursor, "tenant_907")
        migrate(cursor)
        migrate(cursor)
        cursor.execute("SELECT table_schema,column_name,data_type FROM information_schema.columns WHERE table_schema IN ('tenant_901','tenant_907') AND column_name IN ('resolved_work_id','work_reference_snapshot','work_reference_sha256') ORDER BY 1,2")
        rows = cursor.fetchall()
        assert len(rows) == 6
        assert {r[1:] for r in rows} == {('resolved_work_id','uuid'),('work_reference_snapshot','jsonb'),('work_reference_sha256','text')}
