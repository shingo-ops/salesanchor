"""v3 acceptance in unique databases of the disposable CI PostgreSQL service.

No database deletion: CI destroys its service after the job. Random databases
isolate generic migrations from xdist workers. Missing credentials fail, not skip.
Gemini outputs here are anonymous fixtures, never live model measurements.
"""
import asyncio
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from app.services import gemini_extraction_svc as gemini
from app.services import tcg_analyzer_svc as analyzer
from app.services import tcg_diagnostics_svc as diagnostics
from app.services import tcg_distribution_svc as distribution
from app.services import tcg_extraction_record_svc as extraction_records
from app.services import tcg_product_master_svc as product_master
from app.tasks import tcg_extraction as extraction
from tests.conftest import _PUBLIC_SUPPLIERS_DDL, _supplier_ssot_premigration

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SCHEMA = "tenant_901"
STRUCTURE = "20260910_160000_tcg_work_evidence.sql"
HEADER = "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN"
NORMAL = "MEGA スタートデッキ100 バトルコレクション"
# Phase 2 SSOT: tcg_series.code → public.type_master.code mapping
_SERIES_CODE_TO_TYPE = {
    "IP001": "pokemon_booster_box",
    "IP002": "one_piece",
    "IP003": "dragon_ball",
    "IP004": "yugioh",
    "IP005": "union_arena",
    "IP006": "gundam",
}


def provision(cursor, schema):
    cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    cursor.execute((MIGRATIONS / "20260906_120000_create_tcg_tables_t001.sql").read_text().replace("tenant_001", schema))
    # Migration 20260906_120000 creates tcg_suppliers; production DB was renamed to
    # tenant_suppliers (ADR-155). Align test schema to match renamed table.
    cursor.execute(sql.SQL("ALTER TABLE IF EXISTS {}.tcg_suppliers RENAME TO tenant_suppliers").format(sql.Identifier(schema)))


_PUBLIC_PRODUCTS_DDL = (Path(__file__).parent / "fixtures" / "public_products_test.sql").read_text()

def _rewire_keyword_fks(schema: str) -> str:
    """Return SQL that drops tcg_products FKs, converts product_id UUID→INTEGER, and adds public.products(id) FKs.

    ADR-1002 Phase B: keyword/analysis tables now reference public.products(id) (INTEGER).
    """
    return f"""
DO $rw$
DECLARE
    _rec RECORD;
BEGIN
    -- Skip if product_id is already INTEGER (Phase B migration already ran)
    IF EXISTS (
        SELECT 1 FROM pg_attribute a
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = '{schema}'
          AND c.relname = 'product_search_keywords'
          AND a.attname = 'product_id'
          AND a.atttypid = 23  -- int4
    ) THEN
        RETURN;
    END IF;

    -- Phase C path: tcg_uuid dropped from public.products
    -- Tables are empty after provision(), so direct column type swap is safe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
    ) THEN
        -- Drop any existing FKs
        FOR _rec IN
            SELECT c.conname, rel.relname AS tbl
            FROM pg_constraint c
            JOIN pg_class rel ON c.conrelid = rel.oid
            JOIN pg_namespace ns ON rel.relnamespace = ns.oid
            JOIN pg_class ref ON c.confrelid = ref.oid
            WHERE ns.nspname = '{schema}'
              AND rel.relname IN ('product_search_keywords', 'product_exclude_keywords',
                                  'analysis_results')
              AND c.contype = 'f'
        LOOP
            EXECUTE format('ALTER TABLE {schema}.%I DROP CONSTRAINT %I',
                           _rec.tbl, _rec.conname);
        END LOOP;

        -- product_search_keywords: swap to INTEGER
        ALTER TABLE {schema}.product_search_keywords DROP COLUMN product_id;
        ALTER TABLE {schema}.product_search_keywords ADD COLUMN product_id INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE {schema}.product_search_keywords ALTER COLUMN product_id DROP DEFAULT;
        ALTER TABLE {schema}.product_search_keywords
            ADD CONSTRAINT fk_psk_public_products
            FOREIGN KEY (product_id) REFERENCES public.products (id) ON DELETE CASCADE;

        -- product_exclude_keywords: swap to INTEGER
        ALTER TABLE {schema}.product_exclude_keywords DROP COLUMN product_id;
        ALTER TABLE {schema}.product_exclude_keywords ADD COLUMN product_id INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE {schema}.product_exclude_keywords ALTER COLUMN product_id DROP DEFAULT;
        ALTER TABLE {schema}.product_exclude_keywords
            ADD CONSTRAINT fk_pek_public_products
            FOREIGN KEY (product_id) REFERENCES public.products (id) ON DELETE CASCADE;

        -- analysis_results: swap to INTEGER (nullable)
        ALTER TABLE {schema}.analysis_results DROP COLUMN product_id;
        ALTER TABLE {schema}.analysis_results ADD COLUMN product_id INTEGER;
        ALTER TABLE {schema}.analysis_results
            ADD CONSTRAINT fk_ar_public_products
            FOREIGN KEY (product_id) REFERENCES public.products (id);

        -- analysis_run_snapshots: swap if table exists
        IF to_regclass('{schema}.analysis_run_snapshots') IS NOT NULL THEN
            IF EXISTS (
                SELECT 1 FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = '{schema}'
                  AND c.relname = 'analysis_run_snapshots'
                  AND a.attname = 'product_id'
                  AND a.atttypid != 23
            ) THEN
                ALTER TABLE {schema}.analysis_run_snapshots DROP COLUMN product_id;
                ALTER TABLE {schema}.analysis_run_snapshots ADD COLUMN product_id INTEGER;
            END IF;
        END IF;

        RETURN;
    END IF;

    -- Drop any existing FKs referencing tcg_products or public.products on these tables
    FOR _rec IN
        SELECT c.conname, rel.relname AS tbl
        FROM pg_constraint c
        JOIN pg_class rel ON c.conrelid = rel.oid
        JOIN pg_namespace ns ON rel.relnamespace = ns.oid
        JOIN pg_class ref ON c.confrelid = ref.oid
        WHERE ns.nspname = '{schema}'
          AND rel.relname IN ('product_search_keywords', 'product_exclude_keywords',
                              'analysis_results')
          AND c.contype = 'f'
    LOOP
        EXECUTE format('ALTER TABLE {schema}.%I DROP CONSTRAINT %I',
                       _rec.tbl, _rec.conname);
    END LOOP;

    -- Convert product_search_keywords.product_id UUID → INTEGER
    ALTER TABLE {schema}.product_search_keywords
        ADD COLUMN IF NOT EXISTS product_int_id INTEGER;
    UPDATE {schema}.product_search_keywords sk
        SET product_int_id = p.id
        FROM public.products p
        WHERE p.tcg_uuid = sk.product_id;
    ALTER TABLE {schema}.product_search_keywords DROP COLUMN product_id;
    ALTER TABLE {schema}.product_search_keywords RENAME COLUMN product_int_id TO product_id;
    ALTER TABLE {schema}.product_search_keywords ALTER COLUMN product_id SET NOT NULL;
    ALTER TABLE {schema}.product_search_keywords
        ADD CONSTRAINT fk_psk_public_products
        FOREIGN KEY (product_id) REFERENCES public.products (id) ON DELETE CASCADE;

    -- Convert product_exclude_keywords.product_id UUID → INTEGER
    ALTER TABLE {schema}.product_exclude_keywords
        ADD COLUMN IF NOT EXISTS product_int_id INTEGER;
    UPDATE {schema}.product_exclude_keywords ek
        SET product_int_id = p.id
        FROM public.products p
        WHERE p.tcg_uuid = ek.product_id;
    ALTER TABLE {schema}.product_exclude_keywords DROP COLUMN product_id;
    ALTER TABLE {schema}.product_exclude_keywords RENAME COLUMN product_int_id TO product_id;
    ALTER TABLE {schema}.product_exclude_keywords ALTER COLUMN product_id SET NOT NULL;
    ALTER TABLE {schema}.product_exclude_keywords
        ADD CONSTRAINT fk_pek_public_products
        FOREIGN KEY (product_id) REFERENCES public.products (id) ON DELETE CASCADE;

    -- Convert analysis_results.product_id UUID → INTEGER (NULLABLE)
    ALTER TABLE {schema}.analysis_results
        ADD COLUMN IF NOT EXISTS product_int_id INTEGER;
    UPDATE {schema}.analysis_results ar
        SET product_int_id = p.id
        FROM public.products p
        WHERE p.tcg_uuid = ar.product_id;
    ALTER TABLE {schema}.analysis_results DROP COLUMN product_id;
    ALTER TABLE {schema}.analysis_results RENAME COLUMN product_int_id TO product_id;
    ALTER TABLE {schema}.analysis_results
        ADD CONSTRAINT fk_ar_public_products
        FOREIGN KEY (product_id) REFERENCES public.products (id);

    -- Convert analysis_run_snapshots.product_id UUID → INTEGER (if table exists)
    IF to_regclass('{schema}.analysis_run_snapshots') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = '{schema}'
              AND c.relname = 'analysis_run_snapshots'
              AND a.attname = 'product_id'
              AND a.atttypid != 23
        ) THEN
            ALTER TABLE {schema}.analysis_run_snapshots
                ADD COLUMN IF NOT EXISTS product_int_id INTEGER;
            UPDATE {schema}.analysis_run_snapshots ars
                SET product_int_id = p.id
                FROM public.products p
                WHERE p.tcg_uuid = ars.product_id;
            ALTER TABLE {schema}.analysis_run_snapshots DROP COLUMN product_id;
            ALTER TABLE {schema}.analysis_run_snapshots RENAME COLUMN product_int_id TO product_id;
        END IF;
    END IF;
END;
$rw$;
"""


def migrate(cursor):
    cursor.execute(_PUBLIC_PRODUCTS_DDL)
    cursor.execute(_PUBLIC_SUPPLIERS_DDL)
    # Master SSOT Phase 2: type_master must exist before code queries it
    cursor.execute((MIGRATIONS / "085_create_tcg_type_master.sql").read_text())
    cursor.execute((MIGRATIONS / "086_seed_additional_tcg_types.sql").read_text())
    cursor.execute((MIGRATIONS / "20260921_060000_create_product_kinds.sql").read_text())
    # Seed public.product_kinds so load_lookup_maps() can resolve division codes (DIV01→TCG etc.)
    cursor.execute("""
        INSERT INTO public.product_kinds (code, name, display_order, is_active) VALUES
            ('TCG',    'トレーディングカードゲーム', 10, true),
            ('FIGURE', 'フィギュア',               20, true),
            ('GOODS',  'グッズ',                   30, true)
        ON CONFLICT (code) DO NOTHING
    """)
    # ADR-156 Phase 3A: add product_kind_id FK column to public.products
    cursor.execute((MIGRATIONS / "20260921_120000_add_products_product_kind_id.sql").read_text())
    cursor.execute((MIGRATIONS / "20260921_070000_rename_tcg_type_master_to_type_master.sql").read_text())
    cursor.execute(_rewire_keyword_fks(SCHEMA))
    # Master SSOT Phase 3: public schema tables for 9 master tables
    cursor.execute((MIGRATIONS / "20260919_020000_master_ssot_public_tables.sql").read_text())
    # Seed public.tcg_product_categories from tenant schema so seed_products() can resolve PC_BOX
    cursor.execute(f"""
        INSERT INTO public.tcg_product_categories (code, display_name, kubun_type, is_active)
        SELECT code, display_name, kubun_type, is_active
        FROM {SCHEMA}.tcg_product_categories
        ON CONFLICT (code) DO NOTHING
    """)
    # Phase 3 SSOT: seed public.conditions with the standard condition master so the analyzer
    # can resolve condition_id (INTEGER FK NOT NULL in analysis_results after Phase 3 migration).
    # Unit seeding is intentionally deferred to test-specific setup (tests like
    # test_tcg_completion_safety.py seed their own UN-coded units after migrate()).
    # Condition codes use CN-prefix to avoid conflicts with test fixtures that use C1/C2/C3.
    cursor.execute("""
        INSERT INTO public.conditions (code, canonical, priority, app_kubun, search_kw, exclude_kw, is_active) VALUES
            ('CN0001', 'Case',               4, '箱系大',       '',       '',  true),
            ('CN0002', 'Damaged case',       2, '箱系大',       'ダメ,傷', '', true),
            ('CN0003', 'Sealed box',         4, '箱系',         '未開封',  '', true),
            ('CN0004', 'Damaged sealed box', 2, '箱系',         'ダメ,傷', '', true),
            ('CN0005', 'No shrink box',      3, '',             'シュリなし', '', true),
            ('CN0006', 'Opened box',         3, '',             '開封',    '', true),
            ('CN0007', 'Unsearched pack',    3, '',             '未サーチ', '', true),
            ('CN0008', 'FLAG_SINGLE',        1, '枚系,単位不明', '単品',   '', true),
            ('CN0009', 'Opened case',        2, '箱系大',       '開封',    '', true),
            ('CN0010', 'Searched pack',      2, 'パック系',     'サーチ済み', '', true)
        ON CONFLICT (code) DO NOTHING
    """)
    # Master SSOT Phase 3: unit_id/condition_id UUID→INTEGER rewire + product_category_id UUID→INTEGER
    cursor.execute((MIGRATIONS / "20260920_010000_phase3_fk_rewire_unit_condition.sql").read_text())
    cursor.execute((MIGRATIONS / STRUCTURE).read_text())
    cursor.execute((MIGRATIONS / "20260912_020000_tcg_resolved_work_id.sql").read_text())
    cursor.execute((MIGRATIONS / "20260914_010000_tcg_extraction_attempts.sql").read_text())
    cursor.execute((MIGRATIONS / "20260917_010000_add_product_code_to_extraction.sql").read_text())
    # Sprint 1: copy tenant_suppliers → public.suppliers, rewire supplier_channels.supplier_id UUID→INTEGER
    _supplier_ssot_premigration(cursor, SCHEMA)
    cursor.execute((MIGRATIONS / "20260917_020000_supplier_ssot_migration.sql").read_text())
    # product_code_seq: created by phase_b migration in prod, add idempotently for test DB
    cursor.execute(
        "CREATE SEQUENCE IF NOT EXISTS public.product_code_seq START WITH 1"
    )


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
        for module in (analyzer, extraction, distribution, extraction_records):
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
        migrate(cursor)
        for code, title, work, search, exclude in products:
            cursor.execute(f"""INSERT INTO public.products
                (product_code,name,category_class,is_active,work_id,product_category_id)
                SELECT %s,%s,'Box',true,m.id,c.id FROM public.type_master m,
                public.tcg_product_categories c WHERE m.code=%s AND c.code='PC_BOX' RETURNING id""", (code, title, _SERIES_CODE_TO_TYPE[work]))
            pid = cursor.fetchone()[0]
            for table, keywords in (("product_search_keywords", search), ("product_exclude_keywords", exclude)):
                for position, keyword in enumerate(keywords):
                    cursor.execute(f"INSERT INTO public.{table}(product_id,keyword,position) VALUES (%s,%s,%s)", (pid, keyword, position))
        cursor.execute("INSERT INTO public.units(code,canonical,kubun,is_active) VALUES ('UN0001','BOX','箱系',true) RETURNING id")
        uid = cursor.fetchone()[0]
        cursor.execute("INSERT INTO public.unit_aliases(unit_id,alias_text,lang) VALUES (%s,'BOX','ja')", (uid,))
        # ADR-155: 'コロ' exclusion keyword for PM0200 (was in DICTIONARY migration)
        cursor.execute("""INSERT INTO public.product_exclude_keywords(product_id,keyword,position)
            SELECT p.id, 'コロ', COALESCE(MAX(e.position), -1)+1
            FROM public.products p LEFT JOIN public.product_exclude_keywords e ON e.product_id=p.id
            WHERE p.product_code='PM0200'
            GROUP BY p.id""")


def run_message(connection, engine, monkeypatch, raw, records, *, work_id_mode=False):
    smid, jobid = str(uuid4()), str(uuid4())
    with connection.cursor() as cursor:
        cursor.execute(f"""INSERT INTO {SCHEMA}.source_messages
            (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at)
            SELECT %s,id,%s,%s,true,now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
                       (smid, raw, hashlib.sha256(raw.encode()).hexdigest()))
        cursor.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (jobid, smid))
    header = HEADER + ("｜RESOLVED_WORK_ID｜RESOLVED_PRODUCT_CODE" if work_id_mode else "")
    response = header + "\n" + "\n".join("｜".join(row) for row in records)
    if not work_id_mode:
        # Keep legacy 9-column end-to-end regressions while new jobs use v4.
        monkeypatch.setattr(extraction, "extract_message", lambda raw, **kw: gemini.extract_message(raw, recorder=kw["recorder"]))
    else:
        monkeypatch.setattr(extraction, "extract_message", gemini.extract_message)
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text=response)))
    monkeypatch.setattr(gemini, "_get_genai_client", lambda: client)
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
        cursor.execute("SELECT count(*) FROM public.products")
        assert cursor.fetchone()[0] == 0




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
        cursor.execute(f"SELECT ei.id,ei.line_start,p.product_code,ar.pid_resolved,ar.pid_basis,ar.needs_review FROM {SCHEMA}.extraction_items ei JOIN {SCHEMA}.analysis_results ar ON ar.extraction_item_id=ei.id LEFT JOIN public.products p ON p.id=ar.product_id WHERE ei.extraction_job_id=%s ORDER BY ei.line_start", (jobid,))
        rows = cursor.fetchall()
        assert [r[2] for r in rows] == ['PM0200', None, None, 'PM0285', 'PM0285', None, None]
        assert rows[1][3:] == (False, 'NONE', True)
        corrected = rows[1][0]
        cursor.execute(f"UPDATE {SCHEMA}.analysis_results SET product_id=(SELECT id FROM public.products WHERE product_code='PM0285'),pid_resolved=true,pid_basis='HUMAN:confirmed' WHERE extraction_item_id=%s", (corrected,))
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
        cursor.execute(f"SELECT p.product_code,ar.pid_resolved,ar.engine_version FROM {SCHEMA}.analysis_results ar JOIN public.products p ON p.id=ar.product_id JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=%s", (jobid,))
        assert cursor.fetchone() == ("PM0123", True, "name-first-v9-product-all-terms")


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
            # ADR-155: migration no longer UPDATEs conditions — CN0007.exclude_kw must remain unchanged
            assert rows == after[key]
        else:
            # ADR-155: migration only INSERTs NJ079; NJ041.exclude_keywords must remain unchanged
            assert len(new_rows) == len(old_rows) + 1
            for old in old_rows:
                new = next(r for r in new_rows if r["id"] == old["id"])
                assert new == old
    with connection.cursor() as cursor:
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
    # ADR-155: pre-UPDATE guards removed together with UPDATE statements.
    # Only the NJ079 identity-collision guard remains (collision case still raises).
    # For condition/* and note/* targets the migration now runs without error
    # (it only INSERTs NJ079 ON CONFLICT DO NOTHING).
    connection, _, _ = pg
    seed_condition_note(connection)
    with connection.cursor() as cursor:
        if target == "collision":
            cursor.execute("INSERT INTO tenant_004.tcg_note_master(id,label_ja,label_en,priority) VALUES ('NJ079','wrong','wrong',1)")
            before = condition_note_snapshot(connection)
            with pytest.raises(psycopg2.errors.RaiseException, match="identity collision"):
                cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
            cursor.execute("ROLLBACK")
            assert condition_note_snapshot(connection) == before
        else:
            table, key, identity = ("conditions", "code", "CN0007") if target == "condition" else ("tcg_note_master", "id", "NJ041")
            cursor.execute(sql.SQL("UPDATE tenant_004.{} SET {}=%s WHERE {}=%s").format(sql.Identifier(table), sql.Identifier(field), sql.Identifier(key)), (value, identity))
            before = condition_note_snapshot(connection)
            # No exception expected — validation guards were removed per ADR-155
            cursor.execute((MIGRATIONS / CONDITION_NOTE).read_text())
            # Master rows that were altered must be unchanged (migration doesn't touch them)
            assert condition_note_snapshot(connection)[("tenant_004", "conditions")] == before[("tenant_004", "conditions")]


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
    for module in (analyzer, extraction, distribution, product_master, extraction_records):
        monkeypatch.setattr(module, "TCG_SCHEMA", "tenant_004")
    monkeypatch.setattr(product_master, "_SYNC_DB_URL", str(engine.url.render_as_string(hide_password=False)))
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / STRUCTURE).read_text())
        cursor.execute((MIGRATIONS / "20260912_020000_tcg_resolved_work_id.sql").read_text())
        cursor.execute((MIGRATIONS / "20260914_010000_tcg_extraction_attempts.sql").read_text())
        cursor.execute((MIGRATIONS / "20260917_010000_add_product_code_to_extraction.sql").read_text())
        cursor.execute(_PUBLIC_PRODUCTS_DDL)
        cursor.execute(_PUBLIC_SUPPLIERS_DDL)
        # Sprint 1: rewire supplier_channels.supplier_id UUID→INTEGER for distribution JOIN
        _supplier_ssot_premigration(cursor, "tenant_004")
        cursor.execute((MIGRATIONS / "20260917_020000_supplier_ssot_migration.sql").read_text())
        cursor.execute(_rewire_keyword_fks("tenant_004"))
        # Phase 3 FK rewire: convert tenant_004.analysis_results.unit_id/condition_id UUID→INTEGER.
        # tenant_004 was provisioned by seed_condition_note() after migrate() ran, so the rewire
        # migration must be applied explicitly here to match what pg fixture does for tenant_901.
        cursor.execute((MIGRATIONS / "20260920_010000_phase3_fk_rewire_unit_condition.sql").read_text())
        # Phase 3 rewire also covers analysis_run_snapshots which stores a copy of analysis_results columns.
        # The base migration creates unit_id/condition_id as UUID; convert to INTEGER so that
        # reanalyze_extraction_job() can copy INTEGER values from analysis_results without type mismatch.
        cursor.execute("""
            ALTER TABLE tenant_004.analysis_run_snapshots
                DROP COLUMN IF EXISTS unit_id,
                ADD COLUMN unit_id INTEGER;
            ALTER TABLE tenant_004.analysis_run_snapshots
                DROP COLUMN IF EXISTS condition_id,
                ADD COLUMN condition_id INTEGER;
        """)
        for code, name in [("PM0268", "匿名パック"), ("PM0141", "匿名箱")]:
            cursor.execute("INSERT INTO public.products(product_code,name,category_class,is_active,work_id) SELECT %s,%s,'Box',true,id FROM public.type_master WHERE code='pokemon_booster_box' RETURNING id", (code, name))
            pid = cursor.fetchone()[0]
            cursor.execute("INSERT INTO public.product_search_keywords(product_id,keyword,position) VALUES (%s,%s,1)", (pid, name))
        # Insert units with explicit IDs matching _UNIT_MASTER_ROWS (9-16) so that
        # apply_unit_recovery_for_job() FK references resolve correctly.
        # UN0001=Case(9), UN0002=BOX(10), UN0003=Pack(11)
        for unit_id, code, canonical, kubun in [(9, "UN0001", "CASE", "箱系大"), (10, "UN0002", "BOX", "箱系"), (11, "UN0003", "Pack", "パック系")]:
            cursor.execute("INSERT INTO public.units(id,code,canonical,kubun,is_active) VALUES (%s,%s,%s,%s,true) RETURNING id", (unit_id, code, canonical, kubun))
            cursor.execute("INSERT INTO public.unit_aliases(unit_id,alias_text,lang) VALUES (%s,%s,'ja')", (cursor.fetchone()[0], canonical))
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
        # Phase 3 SSOT: load_tcg_note_master() reads from public.tcg_note_master.
        # Mirror tenant_004 note master to public so the analyzer can find NJ079 ('伝票剥がし跡あり').
        cursor.execute("""
            INSERT INTO public.tcg_note_master
                (label_ja, label_en, enabled, search_keywords, exclude_keywords,
                 category, priority, match_type, search_pattern, label_template)
            SELECT label_ja, label_en, enabled, search_keywords, exclude_keywords,
                   category, priority, match_type, search_pattern, label_template
            FROM tenant_004.tcg_note_master tnm
            WHERE NOT EXISTS (
                SELECT 1 FROM public.tcg_note_master pnm WHERE pnm.label_ja = tnm.label_ja
            )
        """)
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
def test_interrupted_recovery_partial_tables_skip(pg, table):
    """When one pipeline table is absent, the recovery migration should skip gracefully
    (not raise) because 20260921_050000 may have dropped tables partially or fully."""
    connection, _, _ = pg
    seed_recovery(connection)
    before = recovery_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("ALTER TABLE tenant_004.{} RENAME TO temporarily_absent").format(sql.Identifier(table)))
        try:
            # Should not raise — migration silently returns when table_count < 3
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


def guard_snapshot(connection, schemas=("tenant_004", "tenant_903")):
    result = {}
    with connection.cursor() as cursor:
        for schema in schemas:
            for table in ("product_search_keywords", "product_exclude_keywords"):
                cursor.execute(sql.SQL("SELECT k.id,k.product_id,k.keyword,k.position,p.product_code FROM {}.{} k JOIN public.products p ON p.id=k.product_id ORDER BY k.id").format(
                    sql.Identifier(schema), sql.Identifier(table)))
                result[schema, table] = cursor.fetchall()
    return result



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


@pytest.mark.parametrize("saved_version", ["raw-extraction-v4-work-id-p1", "raw-extraction-v4-work-id-p2"])
def test_work_id_v4_database_roundtrip_and_review_filter(pg, monkeypatch, saved_version):
    connection, engine, async_url = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM public.type_master WHERE code='one_piece'")
        wid = str(cursor.fetchone()[0])
    raw = "◆EB01 1BOX 1000円"
    _, jid, result = run_message(connection, engine, monkeypatch, raw,
        [record("◆EB01", 1) + [wid, ""]], work_id_mode=True)
    assert result["status"] == "done" and result["items_count"] == 1
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE {SCHEMA}.extraction_jobs SET prompt_version=%s WHERE id=%s", (saved_version, jid))
    with Session(engine) as session:
        analyzer.analyze_extraction_job(session, jid)
        basis = session.execute(text(f"SELECT ar.pid_basis FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id WHERE ei.extraction_job_id=:jid"), {"jid": jid}).scalar_one()
        assert basis.startswith("GEMINI|WORK:")
        session.rollback()
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
        cursor.execute("UPDATE public.products SET name='changed' WHERE product_code='PM0123'")
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
        assert {r[1:] for r in rows} == {('resolved_work_id','integer'),('work_reference_snapshot','jsonb'),('work_reference_sha256','text')}



@pytest.mark.parametrize("name,state,memo,work_code,duplicate,expected", [
    ("スターターセットV 草", "", "", "IP001", False, "resolved"),
    ("スターターセットV　草", "", "", "IP001", False, "resolved"),
    ("スターターセットV 草", "", "", "IP006", False, "none"),
    ("スターターセットV 草", "PSA10", "", "IP001", False, "none"),
    ("スターターセットV 草", "", "限定", "IP001", False, "none"),
    ("スターターセットV 草 10箱", "", "", "IP001", False, "none"),
    ("別商品", "", "スターターセットV 草", "IP001", False, "none"),
    ("スターターセットV 草", "", "", "IP001", True, "multi"),
])
def test_space_product_match_saved_in_isolated_database(
    pg, monkeypatch, name, state, memo, work_code, duplicate, expected,
):
    connection, engine, _ = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        for code in (["SPACE_A", "SPACE_B"] if duplicate else ["SPACE_A"]):
            cursor.execute(f"""INSERT INTO public.products
                (product_code,name,category_class,is_active,work_id,product_category_id)
                SELECT %s,'スターターセットV 草','Box',true,m.id,c.id
                FROM public.type_master m,public.tcg_product_categories c
                WHERE m.code='pokemon_booster_box' AND c.code='PC_BOX' RETURNING id""", (code,))
            product_id = cursor.fetchone()[0]
            for table, keyword in [("product_search_keywords", "スターターセットV草"),
                                   ("product_exclude_keywords", "限定")]:
                cursor.execute(f"INSERT INTO public.{table}(product_id,keyword,position) VALUES (%s,%s,0)",
                               (product_id, keyword))
        cursor.execute("SELECT id FROM public.type_master WHERE code=%s", (_SERIES_CODE_TO_TYPE.get(work_code, work_code),))
        row = cursor.fetchone()
        work_id = str(row[0]) if row else "0"
    _, jobid, result = run_message(connection, engine, monkeypatch,
        name + " 1BOX 1000円 " + state + " " + memo,
        [record(name, 1, state=state, memo=memo) + [work_id, ""]], work_id_mode=True)
    assert result["status"] == "done" and result["items_count"] == 1
    assert result["analysis_stats"]["pid_resolved"] == int(expected == "resolved")
    with connection.cursor() as cursor:
        cursor.execute(f"""SELECT p.product_code,ar.pid_resolved,ar.pid_basis,ar.needs_review
            FROM {SCHEMA}.analysis_results ar
            JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id
            LEFT JOIN public.products p ON p.id=ar.product_id
            WHERE ei.extraction_job_id=%s""", (jobid,))
        code, resolved, basis, needs_review = cursor.fetchone()
        assert resolved is (expected == "resolved")
        if expected == "resolved":
            assert code == "SPACE_A" and basis == f"GEMINI|WORK:{work_id}|SK:スターターセットV草"
        elif expected == "none":
            assert code is None and basis == "NONE" and needs_review
        else:
            assert needs_review and "MULTI(" in basis and "SPACE_A" in basis and "SPACE_B" in basis


CARDSET_MIGRATION = "20260913_200000_tcg_cardset_exclusion.sql"
CARDSET_KINDS = ["フシギダネ", "チコリータ", "キモリ", "ナエトル", "ツタージャ",
                 "ハリマロン", "モクロー", "サルノリ", "ニャオハ"]


def seed_cardset_dictionary(connection, schema):
    with connection.cursor() as cursor:
        provision(cursor, schema)
        cursor.execute(_PUBLIC_PRODUCTS_DDL)
        cursor.execute(_rewire_keyword_fks(schema))
        products = [
            ("PM0263", "30th CELEBRATION", ["30th CELEBRATION"],
             ["FUTURISTIC", "プレミアムデッキセット", "エーフィ"]),
            ("PM0264", "FUTURISTIC BOX", ["30th CELEBRATION FUTURISTIC"], []),
            ("PM0265", "プレミアムデッキセット", ["プレミアムデッキセット"], []),
        ] + [(f"PM{276+i:04d}", "カードセット " + kind, ["カードセット " + kind], [])
             for i, kind in enumerate(CARDSET_KINDS)]
        for code, title, search, exclude in products:
            cursor.execute("SELECT id FROM public.products WHERE product_code=%s", (code,))
            existing = cursor.fetchone()
            if existing:
                pid = existing[0]
            else:
                cursor.execute("""INSERT INTO public.products
                    (product_code,name,category_class,is_active,work_id,product_category_id)
                    SELECT %s,%s,'Box',true,m.id,c.id FROM public.type_master m,
                    public.tcg_product_categories c WHERE m.code='pokemon_booster_box' AND c.code='PC_BOX' RETURNING id""", (code, title))
                pid = cursor.fetchone()[0]
            for table, keywords in (("product_search_keywords", search), ("product_exclude_keywords", exclude)):
                for position, word in enumerate(keywords, 5):
                    # ADR-155 Phase 3: insert into public (SSOT for load_product_keywords)
                    cursor.execute(sql.SQL("INSERT INTO public.{}(product_id,keyword,position) VALUES (%s,%s,%s)").format(
                        sql.Identifier(table)), (pid, word, position))
                    # Also insert into tenant schema for migration guard checks (guard_snapshot reads tenant tables)
                    cursor.execute(sql.SQL("INSERT INTO {}.{}(id,product_id,keyword,position) VALUES (%s,%s,%s,%s)").format(
                        sql.Identifier(schema), sql.Identifier(table)), (str(uuid4()), pid, word, position))


def test_cardset_exclusion_additive_idempotent_and_matching(pg, monkeypatch):
    connection, engine, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_cardset_dictionary(connection, schema)
    monkeypatch.setattr(analyzer, "TCG_SCHEMA", "tenant_004")
    def match(name, state="", memo=""):
        with Session(engine) as session:
            search, exclude = analyzer.load_product_keywords(session)
        return analyzer.match_pid_with_work(name, list(search), search, exclude,
            work_id=None, product_work_ids={}, raw_state=state, raw_memo=memo)
    bundle = "MEGA 30th CELEBRATION カードセット (9種セット)"
    assert match(bundle)[0:3:2] == ("PM0263", True)
    names = ["30th  CELEBRATION", "30th CELEBRATION FUTURISTIC", "30th CELEBRATION プレミアムデッキセット"]
    controls = [match(name) for name in names]
    individual = ["30th CELEBRATION カードセット " + kind for kind in CARDSET_KINDS]
    assert all(not match(name)[2] for name in individual)
    before = guard_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / CARDSET_MIGRATION).read_text())
        cursor.execute("""
            INSERT INTO public.product_exclude_keywords (product_id, keyword, position)
            SELECT product_id, keyword, position FROM tenant_004.product_exclude_keywords
            WHERE keyword = 'カードセット'
            ON CONFLICT DO NOTHING
        """)
    after = guard_snapshot(connection)
    key = ("tenant_004", "product_exclude_keywords")
    added = set(after[key]) - set(before[key])
    assert len(added) == 1 and {(r[4], r[2], r[3]) for r in added} == {("PM0263", "カードセット", 8)}
    assert set(before[key]).issubset(set(after[key]))
    for other_key in before:
        if other_key != key:
            assert before[other_key] == after[other_key]
    assert match(bundle) == (None, "NONE", False, [])
    assert [match(name) for name in names] == controls
    for i, name in enumerate(individual):
        result = match(name)
        assert result[0] == f"PM{276+i:04d}" and result[2] and result[3] == [f"PM{276+i:04d}"]
    assert match("30th CELEBRATION", state="カードセット") == (None, "NONE", False, [])
    assert match("30th CELEBRATION", memo="カードセット") == (None, "NONE", False, [])
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / CARDSET_MIGRATION).read_text())
    assert guard_snapshot(connection) == after


@pytest.mark.parametrize("field,value,should_add_keyword", [
    # ADR-155: identity check removed; migration succeeds or skips gracefully
    ("name", "別商品", True),             # product found by product_code, keyword added
    ("work_id", None, True),              # product found, keyword added
    ("product_category_id", None, True),  # product found, keyword added
    ("product_code", "PM_CHANGED", False), # PM0263 no longer found by product_code, skip
    ("is_active", False, True),           # product found, keyword added
])
def test_cardset_graceful_skip_on_product_change(pg, field, value, should_add_keyword):
    connection, _, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_cardset_dictionary(connection, schema)
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("UPDATE public.products SET {}=%s WHERE product_code='PM0263'").format(sql.Identifier(field)), (value,))
    before = guard_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / CARDSET_MIGRATION).read_text())
    after = guard_snapshot(connection)
    key = ("tenant_004", "product_exclude_keywords")
    added = set(after[key]) - set(before[key])
    if should_add_keyword:
        assert len(added) == 1, f"Expected 1 keyword added, got {len(added)}"
    else:
        assert len(added) == 0, f"Expected skip (0 keywords added), got {len(added)}"


def test_cardset_duplicate_target_preserves_keywords(pg):
    connection, _, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_cardset_dictionary(connection, schema)
    with connection.cursor() as cursor:
        cursor.execute(_PUBLIC_PRODUCTS_DDL)
        cursor.execute(_rewire_keyword_fks("tenant_004"))
        for position in (8, 9):
            cursor.execute("INSERT INTO tenant_004.product_exclude_keywords(id,product_id,keyword,position) SELECT %s,id,'カードセット',%s FROM public.products WHERE product_code='PM0263'", (str(uuid4()), position))
    before = guard_snapshot(connection)
    with connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.RaiseException, match="duplicate cardset"):
            cursor.execute((MIGRATIONS / CARDSET_MIGRATION).read_text())
        cursor.execute("ROLLBACK")
    assert guard_snapshot(connection) == before


def test_cardset_absent_schema_and_partial_structure(pg):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / CARDSET_MIGRATION).read_text())
        cursor.execute("SELECT to_regnamespace('tenant_004')")
        assert cursor.fetchone()[0] is None
        provision(cursor, "tenant_004")
        cursor.execute("ALTER TABLE tenant_004.product_search_keywords RENAME TO temporarily_missing_search")
        with pytest.raises(psycopg2.errors.RaiseException, match="incomplete TCG structure"):
            cursor.execute((MIGRATIONS / CARDSET_MIGRATION).read_text())
        cursor.execute("ROLLBACK")
        cursor.execute("SELECT count(*) FROM public.products")
        assert cursor.fetchone()[0] == 0


def test_cardset_migration_registered_once():
    runner = (MIGRATIONS.parent / "scripts/run_all_migrations.sh").read_text()
    assert runner.splitlines().count("run_sql migrations/" + CARDSET_MIGRATION) == 1


BUNDLE_MIGRATION = "20260913_210000_tcg_cardset_bundle_registration.sql"
BUNDLE_SEEDS = [('PM0263',
  '30th CELEBRATION',
  ['30th CELEBRATION', '30thCELEBRATION', '30周年セレブレーション'],
  ['FUTURISTIC', 'プレミアムデッキセット', 'エーフィ']),
 ('PM0264',
  'FUTURISTIC BOX',
  ['30th CELEBRATION FUTURISTIC', 'FUTURISTIC BOX', 'フューチャリスティック'],
  ['プレミアムデッキセット', 'エーフィ']),
 ('PM0265',
  '30th CELEBRATION プレミアムデッキセット',
  ['30th CELEBRATION プレミアムデッキセット', 'エーフィ・ブラッキー', 'エーフィブラッキー'],
  ['FUTURISTIC']),
 ('PM0276', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ', ['カードセット フシギダネ'], []),
 ('PM0277', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ', ['カードセット チコリータ'], []),
 ('PM0278', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ', ['カードセット キモリ'], []),
 ('PM0279', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ', ['カードセット ナエトル'], []),
 ('PM0280', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル', ['カードセット ツタージャ'], []),
 ('PM0281', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ', ['カードセット ハリマロン'], []),
 ('PM0282', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット モクロー・ニャビー・アシマリ', ['カードセット モクロー'], []),
 ('PM0283', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン', ['カードセット サルノリ'], []),
 ('PM0284', 'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス', ['カードセット ニャオハ'], []),
 ('PM0219', 'ストームエメラルダ', ['ストームエメラルダ'], [])]

BUNDLE_SOURCE_NAMES = [('ストームエメラルダ', 'PM0219'),
 ('30th CELEBRATION', 'PM0263'),
 ('30th  CELEBRATION FUTURISTIC BOX', 'PM0264'),
 ('MEGA 30th CELEBRATION カードセット (9種セット)', 'PM0297'),
 ('MEGA 30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー', 'PM0265'),
 ('30th CELEBRATION BOX', 'PM0263'),
 ('・30th  CELEBRATION  未サーチパック\u300018日発送', 'PM0263'),
 ('30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー\u300018日発送', 'PM0265'),
 ('・30th  CELEBRATION  発送日要相談', 'PM0263'),
 ('・30th  CELEBRATION FUTURISTIC\u300018日発送', 'PM0264'),
 ('・30th  CELEBRATION FUTURISTIC\u300017日発送', 'PM0264'),
 ('・30th  CELEBRATION  17日発送', 'PM0263'),
 ('・30th  CELEBRATION  18日発送', 'PM0263'),
 ('・30th  CELEBRATION  シュリンク無し\u300018日発送', 'PM0263'),
 ('・30th  CELEBRATION  未サーチパック\u300017日発送', 'PM0263'),
 ('30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー\u300017日発送', 'PM0265'),
 ('・30th  CELEBRATION  16日発送', 'PM0263'),
 ('30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー\u3000発送日要相談', 'PM0265'),
 ('・30th  CELEBRATION  シュリンク無し\u300017日発送', 'PM0263'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ', 'PM0277'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット モクロー・ニャビー・アシマリ', 'PM0282'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル', 'PM0280'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ', 'PM0281'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ', 'PM0279'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ', 'PM0278'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス', 'PM0284'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン', 'PM0283'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ', 'PM0276')]

BUNDLE_BOUNDARIES = [('MEGA 30th CELEBRATION カードセット (1種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (2種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (3種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (4種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (5種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (6種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (7種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (8種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (9種セット)', 'PM0297'),
 ('MEGA 30th CELEBRATION カードセット (10種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (11種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (12種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (13種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (14種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (15種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (16種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (17種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (18種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (19種セット)', None),
 ('MEGA 30th CELEBRATION カードセット (20種セット)', None),
 ('30th  CELEBRATION カードセット (1種セット)', None),
 ('30th  CELEBRATION カードセット (2種セット)', None),
 ('30th  CELEBRATION カードセット (3種セット)', None),
 ('30th  CELEBRATION カードセット (4種セット)', None),
 ('30th  CELEBRATION カードセット (5種セット)', None),
 ('30th  CELEBRATION カードセット (6種セット)', None),
 ('30th  CELEBRATION カードセット (7種セット)', None),
 ('30th  CELEBRATION カードセット (8種セット)', None),
 ('30th  CELEBRATION カードセット (9種セット)', 'PM0297'),
 ('30th  CELEBRATION カードセット (10種セット)', None),
 ('30th  CELEBRATION カードセット (11種セット)', None),
 ('30th  CELEBRATION カードセット (12種セット)', None),
 ('30th  CELEBRATION カードセット (13種セット)', None),
 ('30th  CELEBRATION カードセット (14種セット)', None),
 ('30th  CELEBRATION カードセット (15種セット)', None),
 ('30th  CELEBRATION カードセット (16種セット)', None),
 ('30th  CELEBRATION カードセット (17種セット)', None),
 ('30th  CELEBRATION カードセット (18種セット)', None),
 ('30th  CELEBRATION カードセット (19種セット)', None),
 ('30th  CELEBRATION カードセット (20種セット)', None),
 ('MEGA 30th CELEBRATION カードセット（９種セット）', 'PM0297'),
 ('◆MEGA 30th CELEBRATION カードセット (9種セット)', 'PM0297'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ', 'PM0276'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ', 'PM0277'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ', 'PM0278'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ', 'PM0279'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル', 'PM0280'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ', 'PM0281'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット モクロー・ニャビー・アシマリ', 'PM0282'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン', 'PM0283'),
 ('ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス', 'PM0284'),
 ('30th CELEBRATION', 'PM0263'),
 ('30th CELEBRATION FUTURISTIC', 'PM0264'),
 ('30th CELEBRATION プレミアムデッキセット', 'PM0265'),
 ('別作品 カードセット (9種セット)', None),
 ('MEGA 30th CELEBRATION カードセット', None),
 ('MEGA 30th CELEBRATION カードセット (9種セット) FUTURISTIC', None),
 ('MEGA 30th CELEBRATION カードセット (9種セット) プレミアムデッキセット', None)]


def seed_bundle_dictionary(connection, schema):
    with connection.cursor() as cursor:
        provision(cursor, schema)
        cursor.execute(_PUBLIC_PRODUCTS_DDL)
        cursor.execute(_rewire_keyword_fks(schema))
        for code, title, search, exclude in BUNDLE_SEEDS:
            cursor.execute("SELECT id FROM public.products WHERE product_code=%s", (code,))
            existing = cursor.fetchone()
            if existing:
                pid = existing[0]
            else:
                cursor.execute(sql.SQL("""INSERT INTO public.products
                    (product_code,name,category_class,is_active,division_id,work_id,manufacturer_id,product_category_id)
                    SELECT %s,%s,'Box',true,d.id,tm.id,m.id,c.id
                    FROM {}.tcg_major_categories d, public.type_master tm, {}.tcg_manufacturers m,
                         public.tcg_product_categories c
                    WHERE d.code='DIV01' AND tm.code='pokemon_booster_box' AND m.code='MK001' AND c.code='PC_BOX'
                    RETURNING id""").format(*[sql.Identifier(schema)] * 2), (code, title))
                pid = cursor.fetchone()[0]
            for table, words in (("product_search_keywords", search), ("product_exclude_keywords", exclude)):
                for position, word in enumerate(words, 4):
                    # ADR-155 Phase 3: insert into public (SSOT for load_product_keywords)
                    cursor.execute(sql.SQL("INSERT INTO public.{} (product_id,keyword,position) VALUES (%s,%s,%s)").format(
                        sql.Identifier(table)), (pid, word, position))
                    # Also insert into tenant schema for migration guard checks (bundle_snapshot reads tenant tables)
                    cursor.execute(sql.SQL("INSERT INTO {}.{} (id,product_id,keyword,position) VALUES (%s,%s,%s,%s)").format(
                        sql.Identifier(schema), sql.Identifier(table)), (str(uuid4()), pid, word, position))


def bundle_snapshot(connection):
    result = {}
    with connection.cursor() as cursor:
        for schema in ("tenant_004", "tenant_903"):
            for table in ("tcg_major_categories", "tcg_series", "tcg_manufacturers",
                          "tcg_product_categories", "product_search_keywords", "product_exclude_keywords"):
                cursor.execute(sql.SQL("SELECT to_jsonb(t) FROM {}.{} t ORDER BY id").format(
                    sql.Identifier(schema), sql.Identifier(table)))
                result[schema, table] = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT to_jsonb(t) FROM public.products t ORDER BY id")
        result["public", "products"] = [r[0] for r in cursor.fetchall()]
    return result


def test_bundle_registration_preserves_products_and_matches_28_plus_58(pg, monkeypatch):
    connection, engine, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_bundle_dictionary(connection, schema)
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / CARDSET_MIGRATION).read_text())
        cursor.execute("""
            INSERT INTO public.product_exclude_keywords (product_id, keyword, position)
            SELECT product_id, keyword, position FROM tenant_004.product_exclude_keywords pek
            WHERE NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords ppek WHERE ppek.product_id = pek.product_id AND ppek.keyword = pek.keyword)
        """)
    before = bundle_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / BUNDLE_MIGRATION).read_text())
        cursor.execute("""
            INSERT INTO public.product_search_keywords (product_id, keyword, position)
            SELECT product_id, keyword, position FROM tenant_004.product_search_keywords psk
            WHERE NOT EXISTS (SELECT 1 FROM public.product_search_keywords ppsk WHERE ppsk.product_id = psk.product_id AND ppsk.keyword = psk.keyword)
        """)
        cursor.execute("""
            INSERT INTO public.product_exclude_keywords (product_id, keyword, position)
            SELECT product_id, keyword, position FROM tenant_004.product_exclude_keywords pek
            WHERE NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords ppek WHERE ppek.product_id = pek.product_id AND ppek.keyword = pek.keyword)
        """)
    after = bundle_snapshot(connection)
    for key, rows in before.items():
        for row in rows:
            assert row in after[key], (key, row)
        if key[0] == "tenant_903" or key[1] not in ("product_search_keywords", "product_exclude_keywords"):
            if key != ("public", "products"):
                assert rows == after[key]
    # ADR-155: PM0297 is no longer created by migration (INSERT removed).
    # PM0297 is absent from BUNDLE_SEEDS so seed_bundle_dictionary also does not create it.
    # All 3 PM0297 keywords (1 search + 2 exclude) are skipped gracefully via RAISE NOTICE.
    new = [r for r in after["public", "products"] if r not in before["public", "products"]]
    assert len(new) == 0, f"Migration must not create new products (ADR-155), got: {[r['product_code'] for r in new]}"
    # search_keywords: PM0297 search skipped (+0). exclude_keywords: 11 for PM0263-PM0284.
    # PM0263 カードセット already added by cardset_exclusion (skip). PM0264-PM0265 (2) + PM0276-PM0284 (9) = 11 new.
    # PM0297 keywords skipped (product absent, ADR-155).
    assert len(after["tenant_004", "product_search_keywords"]) - len(before["tenant_004", "product_search_keywords"]) == 0
    assert len(after["tenant_004", "product_exclude_keywords"]) - len(before["tenant_004", "product_exclude_keywords"]) == 11
    monkeypatch.setattr(analyzer, "TCG_SCHEMA", "tenant_004")
    with Session(engine) as session:
        search, exclude = analyzer.load_product_keywords(session)
    assert "PM0297" not in search, "PM0297 has no search keyword (product absent)"
    assert "PM0297" not in exclude, "PM0297 has no exclude keyword (product absent)"
    for code in ("PM0263", "PM0264", "PM0265"):
        assert exclude[code].count("カードセット") == 1
    for number in range(276, 285):
        assert exclude[f"PM{number:04d}"].count("種セット") == 1
    assert len(BUNDLE_SOURCE_NAMES) == 28 and len(BUNDLE_BOUNDARIES) == 58
    for name, expected in BUNDLE_SOURCE_NAMES + BUNDLE_BOUNDARIES:
        actual, _, resolved, _ = analyzer.match_pid_with_work(name, list(search), search, exclude,
            work_id=None, product_work_ids={}, raw_state="", raw_memo="")
        # PM0297-mapped names cannot resolve because PM0297 has no keywords loaded
        if expected == "PM0297":
            assert (actual if resolved else None) is None, name
        else:
            assert (actual if resolved else None) == expected, name
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / BUNDLE_MIGRATION).read_text())
    assert bundle_snapshot(connection) == after


@pytest.mark.parametrize("table", ["tcg_major_categories", "tcg_series", "tcg_manufacturers", "tcg_product_categories"])
@pytest.mark.parametrize("fault", ["inactive", "missing_code"])
def test_bundle_invalid_reference_rolls_back(pg, table, fault):
    connection, _, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_bundle_dictionary(connection, schema)
    with connection.cursor() as cursor:
        field, value = ("is_active", False) if fault == "inactive" else ("code", "MISSING")
        expected = {"tcg_major_categories": "DIV01", "tcg_series": "IP001",
                    "tcg_manufacturers": "MK001", "tcg_product_categories": "PC_BOX"}[table]
        cursor.execute(sql.SQL("UPDATE tenant_004.{} SET {}=%s WHERE code=%s").format(
            sql.Identifier(table), sql.Identifier(field)), (value, expected))
    before = bundle_snapshot(connection)
    with connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.RaiseException, match="reference missing or inactive"):
            cursor.execute((MIGRATIONS / BUNDLE_MIGRATION).read_text())
        cursor.execute("ROLLBACK")
    assert bundle_snapshot(connection) == before


@pytest.mark.parametrize("field,value", [
    # ADR-155: identity check removed; migration succeeds and adds keywords regardless of field changes
    ("is_active", False),
    ("division_id", None), ("work_id", None), ("manufacturer_id", None), ("product_category_id", None),
    ("category_class", "Single")])
def test_bundle_graceful_with_modified_product(pg, field, value):
    connection, _, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_bundle_dictionary(connection, schema)
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("UPDATE public.products SET {}=%s WHERE product_code='PM0276'").format(sql.Identifier(field)), (value,))
    before = bundle_snapshot(connection)
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / BUNDLE_MIGRATION).read_text())
    after = bundle_snapshot(connection)
    # PM0276 exists (only field modified, product_code unchanged), so keywords are added
    before_count = len(before["tenant_004", "product_exclude_keywords"])
    after_count = len(after["tenant_004", "product_exclude_keywords"])
    assert after_count > before_count, "PM0276 種セット keyword should be added (product found by product_code)"


def test_bundle_late_duplicate_keyword_is_atomic(pg):
    # ADR-155: code_collision and same_product_other_code checks removed from migration.
    # Only the duplicate-keyword guard remains; verify it raises and rolls back.
    connection, _, _ = pg
    for schema in ("tenant_004", "tenant_903"):
        seed_bundle_dictionary(connection, schema)
    with connection.cursor() as cursor:
        cursor.execute(_PUBLIC_PRODUCTS_DDL)
        cursor.execute(_rewire_keyword_fks("tenant_004"))
        for position in (10, 11):
            cursor.execute(
                "INSERT INTO tenant_004.product_exclude_keywords(id,product_id,keyword,position) "
                "SELECT %s,id,'種セット',%s FROM public.products WHERE product_code='PM0284'",
                (str(uuid4()), position))
    before = bundle_snapshot(connection)
    with connection.cursor() as cursor:
        with pytest.raises(psycopg2.errors.RaiseException, match="duplicate keyword"):
            cursor.execute((MIGRATIONS / BUNDLE_MIGRATION).read_text())
        cursor.execute("ROLLBACK")
    assert bundle_snapshot(connection) == before


def test_bundle_absent_and_partial_schema(pg):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / BUNDLE_MIGRATION).read_text())
        cursor.execute("SELECT to_regnamespace('tenant_004')")
        assert cursor.fetchone()[0] is None
        provision(cursor, "tenant_004")
        cursor.execute("ALTER TABLE tenant_004.tcg_manufacturers RENAME TO temporarily_missing_manufacturers")
        with pytest.raises(psycopg2.errors.RaiseException, match="incomplete TCG structure"):
            cursor.execute((MIGRATIONS / BUNDLE_MIGRATION).read_text())
        cursor.execute("ROLLBACK")
        cursor.execute("SELECT count(*) FROM public.products")
        assert cursor.fetchone()[0] == 0


def test_bundle_runner_registration_after_cardset_exclusion():
    lines = (MIGRATIONS.parent / "scripts/run_all_migrations.sh").read_text().splitlines()
    target = "run_sql migrations/" + BUNDLE_MIGRATION
    assert lines.count(target) == 1
    assert lines.index("run_sql migrations/" + CARDSET_MIGRATION) < lines.index(target)


def test_all_terms_product_results_persist_with_guards(pg, monkeypatch):
    connection, engine, _ = pg
    seed_products(connection)
    with connection.cursor() as cursor:
        cursor.execute(f"""INSERT INTO public.products
            (product_code,name,category_class,is_active,work_id,product_category_id)
            SELECT 'TERMS_A','30th CELEBRATION FUTURISTIC BOX','Box',true,m.id,c.id
            FROM public.type_master m,public.tcg_product_categories c
            WHERE m.code='pokemon_booster_box' AND c.code='PC_BOX' RETURNING id,work_id""")
        pid, work = cursor.fetchone()
        for table, keyword in [("product_search_keywords", "30th FUTURISTIC"),
                               ("product_exclude_keywords", "LIMITED EDITION")]:
            cursor.execute(f"INSERT INTO public.{table}(product_id,keyword,position) VALUES (%s,%s,0)",
                           (pid, keyword))
    cases = [
        ("30th CELEBRATION FUTURISTIC BOX", "", "", True),
        ("FUTURISTIC BOX 30th CELEBRATION", "", "", True),
        ("30th　FUTURISTIC", "", "", True),
        ("FUTURISTIC BOX", "", "", False),
        ("130th FUTURISTIC", "", "", False),
        ("30th FUTURISTIC", "PSA10", "", False),
        ("unrelated_product", "", "30th FUTURISTIC", False),
        ("30th FUTURISTIC", "", "LIMITED EDITION", False),
        ("30th FUTURISTIC", "", "LIMITED special EDITION", True),
    ]
    raw = "\n".join(name + " 1BOX 1000円 " + state + " " + memo for name, state, memo, _ in cases)
    records = [record(name, line, state=state, memo=memo) + [str(work), ""]
               for line, (name, state, memo, _) in enumerate(cases, 1)]
    _, jobid, result = run_message(connection, engine, monkeypatch, raw, records, work_id_mode=True)
    assert result["status"] == "done" and result["items_count"] == len(cases)
    with connection.cursor() as cursor:
        cursor.execute(f"""SELECT ei.raw_product_name, ar.pid_resolved, p.product_code, ar.engine_version
            FROM {SCHEMA}.extraction_items ei JOIN {SCHEMA}.analysis_results ar ON ar.extraction_item_id=ei.id
            LEFT JOIN public.products p ON p.id=ar.product_id
            WHERE ei.extraction_job_id=%s ORDER BY ei.line_start""", (jobid,))
        rows = cursor.fetchall()
    assert len(rows) == len(cases)
    for row, (name, _, _, expected) in zip(rows, cases):
        assert row == (name, expected, "TERMS_A" if expected else None, analyzer.ENGINE_VERSION)
    assert analyzer.ENGINE_VERSION == "name-first-v9-product-all-terms"
