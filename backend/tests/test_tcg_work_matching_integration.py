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


def run_message(connection, engine, monkeypatch, raw, records):
    smid, jobid = str(uuid4()), str(uuid4())
    with connection.cursor() as cursor:
        cursor.execute(f"""INSERT INTO {SCHEMA}.source_messages
            (id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at)
            SELECT %s,id,%s,%s,true,now() FROM {SCHEMA}.supplier_channels LIMIT 1""",
                       (smid, raw, hashlib.sha256(raw.encode()).hexdigest()))
        cursor.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'pending')", (jobid, smid))
    response = HEADER + "\n" + "\n".join("｜".join(row) for row in records)
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
    assert result["analysis_stats"]["pid_resolved"] == 4
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT ei.id,ei.line_start,p.code,ar.pid_resolved,ar.pid_basis,ar.needs_review FROM {SCHEMA}.extraction_items ei JOIN {SCHEMA}.analysis_results ar ON ar.extraction_item_id=ei.id LEFT JOIN {SCHEMA}.tcg_products p ON p.id=ar.product_id WHERE ei.extraction_job_id=%s ORDER BY ei.line_start", (jobid,))
        rows = cursor.fetchall()
        assert [r[2] for r in rows] == ['PM0200', None, 'PM0285', 'PM0285', 'PM0285', None, None]
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
    assert len(candidates) == 5
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
        assert cursor.fetchone() == ("PM0123", True, "name-first-v3-work")


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
    assert guard_snapshot(connection, ("tenant_004",)) == before


def test_false_positive_guards_absent_tables_noop(pg):
    connection, _, _ = pg
    with connection.cursor() as cursor:
        cursor.execute((MIGRATIONS / GUARDS).read_text())
        cursor.execute("CREATE SCHEMA tenant_004")
        cursor.execute((MIGRATIONS / GUARDS).read_text())
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='tenant_004'")
        assert cursor.fetchone()[0] == 0


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
            cursor.execute(sql.SQL("ALTER TABLE tenant_004.temporarily_absent RENAME TO {}").format(sql.Identifier(table)))
    assert guard_snapshot(connection, ("tenant_004",)) == before


# Dictionary fixtures contain product labels only, with newly generated IDs.
GUARDS = "20260910_170000_tcg_keyword_false_positive_guards.sql"
GUARD_PRODUCTS = [('PM0104', 'ポケモンカード151', 'IP001', 'PC_BOX', [('ポケモンカード151', 2), ('151', 1)], [('vol.3', 1), ('hope', 3), ('jumbo', 6), ('surprised', 4), ('slim', 5), ('収集啦', 17), ('fat', 7), ('礼盒', 27), ('journey', 2)]), ('PM0184', 'スターターセットMEGA メガゲンガーex', 'IP001', 'PC_BOX', [('メガゲンガー', 1), ('メガゲンガーex', 4), ('MEGAゲンガーex', 2), ('MEGAゲンガー', 3)], [('MEGディアンシー', 1)]), ('PM0230', 'トライアルデッキ 【推しの子】', 'IP007', 'PC_SINGLE', [('OSK', 3), ('推しの子', 1), ('oshi no ko', 2), ('vol.1', 5), ('trial deck', 4)], [])]
GUARD_WRONG_INPUTS = [('リミテッドカードコレクション Vol.1', 'PM0230'), ('■スペシャルデッキセットMEGA メガオーダイル・メガカイリュー・メガゲンガー', 'PM0184'), ('マスターボールミラー151のみ', 'PM0104'), ('リミテッドカードコレクションvol.1', 'PM0230'), ('LIMIT OVER SPECIAL PACK Vol.1', 'PM0230'), ('BASE SHOP リミテッドカードコレクションvol.1', 'PM0230'), ('BASE SHOP vol.1', 'PM0230'), ('プレミアムカードコレクション  – 6 assort vol.1 -', 'PM0230'), ('プレミアムカードコレクション- ベストセレクションvol.1 -', 'PM0230'), ('プレミアムカードコレクション 6 assort vol.1', 'PM0230')]
GUARD_CONTROLS = [('推しの子 vol.1', '', '', 'PM0230'), ('推しの子', '', '', 'PM0230'), ('ポケモンカード151', '', '', 'PM0104'), ('151', '', '', 'PM0104'), ('スターターセットMEGA メガゲンガーex', '', '', 'PM0184'), ('BASE SHOP vol.1', '', '', None), ('リミテッドカードコレクション Vol.1', '', '', None), ('151', 'マスターボールミラー', '', None), ('151', '', 'マスターボールミラー', None), ('メガゲンガー', 'スペシャルデッキセット', '', None), ('メガゲンガー', '', 'スペシャルデッキセット', None), ('vol.1', '', '', None), ('BASE SHOP vol.10', '', '', None), ('BASE SHOP vol.11', '', '', None), ('リミテッドカードコレクション vol.10', '', '', None), ('BASE SHOP vol.2', '', '', None)]
