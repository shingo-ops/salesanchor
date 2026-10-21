"""Real PostgreSQL 16 acceptance; disposable CI databases, never live data.

No SQLite fallback and no skip. Database names are random and retained until the
existing CI service shuts down; no shared database cleanup is performed.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from fastapi import HTTPException
from psycopg2 import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from app.services import item_corrections_svc as corrections
from app.services.review_reason_codes_svc import split_reason_codes
from app.services import tcg_analyzer_svc as analyzer
from app.services import tcg_analysis_review_svc as review
from app.services import tcg_condition_review_svc as condition
from app.services import tcg_distribution_svc as distribution
from app.services.tcg_empty_box_rules import classification_sql, classify_empty_box
from tests.test_tcg_empty_box_rules import CASES
from tests.conftest import _PUBLIC_SUPPLIERS_DDL, _supplier_ssot_premigration
from tests.condition_value_columns import apply_condition_value_columns
from tests.seed_data import type_master_seed_sql
from tests.test_tcg_work_matching_integration import (
    _PUBLIC_PRODUCTS_DDL,
    _rewire_keyword_fks,
    apply_bundle_sale_columns,
    create_soldout_extra_targets,
    provision,
)

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
MIGRATION = MIGRATIONS / "20260913_150000_tcg_empty_box_condition.sql"
SCHEMA = "tenant_004"


@pytest.fixture
def pg(monkeypatch):
    assert os.getenv("GITHUB_ACTIONS") == "true", "Disposable CI PostgreSQL service required"
    configured = os.getenv("RLS_ADMIN_DATABASE_URL")
    assert configured, "Required PostgreSQL acceptance has no administrator URL"
    url = make_url(configured)
    assert url.host in ("localhost", "127.0.0.1") and url.database == "jarvis_test_db"
    kwargs = dict(host=url.host, port=url.port, user=url.username, password=url.password)
    name = "tcg_empty_test_" + uuid4().hex
    admin = psycopg2.connect(dbname=url.database, **kwargs)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute("SHOW server_version_num")
        assert 160000 <= int(cursor.fetchone()[0]) < 170000
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    admin.close()
    connection = psycopg2.connect(dbname=name, **kwargs)
    connection.autocommit = True
    engine = create_engine(url.set(database=name, drivername="postgresql+psycopg2"))
    try:
        with connection.cursor() as cursor:
            provision(cursor, SCHEMA)
            cursor.execute(_PUBLIC_PRODUCTS_DDL)
            cursor.execute((MIGRATIONS / "085_create_tcg_type_master.sql").read_text())
            cursor.execute((MIGRATIONS / "086_seed_additional_tcg_types.sql").read_text())
            cursor.execute((MIGRATIONS / "20260921_060000_create_product_kinds.sql").read_text())
            cursor.execute((MIGRATIONS / "20260921_070000_rename_tcg_type_master_to_type_master.sql").read_text())
            # type_master の行は migration ではなく試験側で入れる（ADR-1007 段2）
            cursor.execute(type_master_seed_sql())
            cursor.execute(_PUBLIC_SUPPLIERS_DDL)
            cursor.execute(_rewire_keyword_fks(SCHEMA))
            # Master SSOT Phase 3: public schema tables for 9 master tables
            cursor.execute((MIGRATIONS / "20260919_020000_master_ssot_public_tables.sql").read_text())
            apply_condition_value_columns(cursor)  # 本番の形（value_group / value_rank 列＋11状態の値）に揃える
            # Master SSOT Phase 3: unit_id/condition_id UUID→INTEGER rewire + product_category_id UUID→INTEGER
            cursor.execute((MIGRATIONS / "20260920_010000_phase3_fk_rewire_unit_condition.sql").read_text())
            cursor.execute((MIGRATIONS / "20260910_160000_tcg_work_evidence.sql").read_text())
            cursor.execute(MIGRATION.read_text())
            # Sprint 1: copy tenant_suppliers → public.suppliers, rewire supplier_channels.supplier_id UUID→INTEGER
            _supplier_ssot_premigration(cursor, SCHEMA)
            cursor.execute((MIGRATIONS / "20260917_020000_supplier_ssot_migration.sql").read_text())
            # Step 4/5: create pipeline tables in public schema
            cursor.execute((MIGRATIONS / "20260921_110000_pipeline_tables_public.sql").read_text())
            # 要確認一覧の LATERAL が public.extraction_attempts.thought_summaries を読む（本番適用済みの migration をそのまま当てる）
            cursor.execute((MIGRATIONS / "20261012_200000_add_extraction_attempts_thought_summaries.sql").read_text())
            # 段2a: 要確認一覧が読む extraction_jobs.system_review_detail（本番適用済みの migration をそのまま当てる）
            cursor.execute((MIGRATIONS / "20261012_100000_add_extraction_jobs_system_review_detail.sql").read_text())
            # 便A: 要確認の理由コード表（構造のみ。行は試験側で入れる）
            cursor.execute((MIGRATIONS / "20261009_200000_create_review_reason_codes.sql").read_text())
            # ADR-158 / PR #3747: is_current column added to analysis_results for supersession logic.
            cursor.execute(f"ALTER TABLE {SCHEMA}.analysis_results ADD COLUMN IF NOT EXISTS is_current BOOLEAN NOT NULL DEFAULT TRUE")
            create_soldout_extra_targets(cursor, SCHEMA)  # 便2-1: ADR-158 のマージが読む表
            # 発送日の専用列（v102）: 配信の SELECT が ship_ja を読む。
            cursor.execute((MIGRATIONS / "20261013_140000_add_analysis_results_ship_ja_ship_en.sql").read_text())
            cursor.execute(f"ALTER TABLE {SCHEMA}.analysis_results ADD COLUMN IF NOT EXISTS ship_ja TEXT")
            cursor.execute(f"ALTER TABLE {SCHEMA}.analysis_results ADD COLUMN IF NOT EXISTS ship_en TEXT")
            apply_bundle_sale_columns(cursor, SCHEMA)  # ADR-1027 便1: 配信の SELECT が bundle_size と line_units を読む
            # この試験は TCG_SCHEMA を差し替えず public の analysis_results を使うので、public にも作る（migration の本来の置き場）
            create_soldout_extra_targets(cursor, "public")
            # ADR-158 Phase 2: raw_product_code column on extraction_items (Gemini v6).
            cursor.execute((MIGRATIONS / "20260926_010000_add_raw_product_code.sql").read_text())
            cursor.execute(f"ALTER TABLE IF EXISTS {SCHEMA}.extraction_items ADD COLUMN IF NOT EXISTS raw_product_code text")
            # Seed a public.supplier_channels row for test data insertion
            cursor.execute("INSERT INTO public.supplier_channels(channel,is_active,supplier_id) "
                           "SELECT 'line',true,id FROM public.suppliers LIMIT 1")
            provision(cursor, "tenant_006")
            cursor.execute("INSERT INTO tenant_006.conditions (code,canonical,is_active) VALUES ('CN0099','untouched',true)")
            cursor.execute("INSERT INTO public.conditions (code,canonical,priority,app_kubun,search_kw,exclude_kw,is_active) VALUES ('CN0003','Sealed box',4,'箱系','未開封','',true) RETURNING id")
            normal = str(cursor.fetchone()[0])
            # CN0011 is inserted by MIGRATION into tenant_004.conditions; mirror to public for service access
            cursor.execute("INSERT INTO public.conditions (code,canonical,priority,app_kubun,search_kw,exclude_kw,is_active) SELECT code,canonical,priority,app_kubun,search_kw,exclude_kw,is_active FROM tenant_004.conditions WHERE code='CN0011' RETURNING id")
            empty = str(cursor.fetchone()[0])
            # Insert with explicit id=10 to match _UNIT_MASTER_ROWS unit_id for Box (UN0002).
            # public.units uses GENERATED BY DEFAULT AS IDENTITY, which allows explicit id insertion.
            cursor.execute("INSERT INTO public.units(id,code,canonical,kubun,is_active) VALUES (10,'UN0002','Box','箱系',true) RETURNING id")
            unit = str(cursor.fetchone()[0])
            cursor.execute("INSERT INTO public.unit_aliases(unit_id,alias_text,lang) VALUES (%s,'Box','en')", (unit,))
            cursor.execute("INSERT INTO public.tcg_product_categories (code, display_name, kubun_type, is_active) VALUES ('PC_BOX', 'Box', '箱系', true) ON CONFLICT (code) DO NOTHING")
            cursor.execute("""INSERT INTO public.products (product_code,name,category_class,is_active,work_id,product_category_id)
                SELECT 'PM0900','Test Booster','Box',true,w.id,c.id FROM public.type_master w,public.tcg_product_categories c
                WHERE w.code='pokemon_booster_box' AND c.code='PC_BOX' RETURNING id""")
            product = str(cursor.fetchone()[0])
            cursor.execute("INSERT INTO public.product_search_keywords(product_id,keyword,position) VALUES (%s,'Test Booster',0)", (product,))
        yield {"connection": connection, "engine": engine,
               "url": url.set(database=name, drivername="postgresql+asyncpg"), "empty": empty,
               "normal": normal, "unit": unit, "product": product}
    finally:
        engine.dispose()
        connection.close()


def seed(pg, *, name="Test Booster 空箱", state="", memo="", reasons="empty_box", prompt_version=None, channel_id=None, **overrides):
    smid, job, eid = str(uuid4()), str(uuid4()), str(uuid4())
    raw = name + state + memo
    with pg["connection"].cursor() as cursor:
        cursor.execute("""INSERT INTO public.source_messages(id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at,line_posted_at)
            SELECT %s,id,%s,%s,true,now(),now() FROM public.supplier_channels WHERE (%s::uuid IS NULL OR id=%s::uuid) ORDER BY id LIMIT 1""",
            (smid, raw, hashlib.sha256(raw.encode()).hexdigest(), channel_id, channel_id))
        cursor.execute("INSERT INTO public.extraction_jobs(id,source_message_id,status,prompt_version) VALUES (%s,%s,'done',%s)", (job,smid,prompt_version))
        cursor.execute("""INSERT INTO public.extraction_items(id,extraction_job_id,line_start,line_end,raw_product_name,
            raw_quantity,raw_price,raw_unit,raw_state,raw_memo) VALUES (%s,%s,1,1,%s,'1','10','Box',%s,%s)""", (eid,job,name,state,memo))
        values = {"product_id":pg["product"],"pid_resolved":True,"pid_basis":"EXACT","unit_id":pg["unit"],
            "unit_canonical":"Box","unit_resolved":True,"condition_id":pg["empty"],"condition_canonical":"Empty box",
            "condition_basis":"EMPTY_BOX:explicit","quantity_normalized":1,"price_normalized":10,"note_ja":None,
            "status":"active","exclusion":None,"needs_review":bool(reasons),"review_reasons":reasons or None,"engine_version":"test"}
        values.update(overrides)
        cursor.execute(sql.SQL("INSERT INTO public.analysis_results(extraction_item_id,{}) VALUES (%s,{})").format(
            sql.SQL(',').join(map(sql.Identifier, values)), sql.SQL(',').join(sql.Placeholder() for _ in values)), (eid,*values.values()))
    return {"eid":eid,"smid":smid,"job":job}


def context(pg, item):
    with Session(pg["engine"]) as db:
        return dict(db.execute(text(condition.context_sql()), {"eid":item["eid"]}).mappings().one())


def request(pg, item, *, decision="confirm", target=None, version=None, rid=None):
    return {"request_id":rid or str(uuid4()), "expected_review_version":version or context(pg,item)["review_version"],
            "decision":decision,"condition_id":target or pg["empty"]}


async def save_async(pg, item, payload):
    engine = create_async_engine(pg["url"])
    try:
        async with AsyncSession(engine) as db:
            return await condition.save_condition_review(db, extraction_item_id=item["eid"],source_message_id=item["smid"],
                request=payload, corrected_by="reviewer@example.invalid")
    finally:
        await engine.dispose()


def save(pg, item, payload=None):
    return asyncio.run(save_async(pg,item,payload or request(pg,item)))


def set_max_age_hours(pg, value):
    """tcg_distribution_settings の max_age_hours を入れる（None なら行を消す）。"""
    with pg["connection"].cursor() as cursor:
        if value is None:
            cursor.execute("DELETE FROM public.tcg_distribution_settings WHERE key='max_age_hours'")
        else:
            cursor.execute("INSERT INTO public.tcg_distribution_settings(key,value) VALUES ('max_age_hours',%s) "
                           "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (str(value),))


def age_message(pg, item, hours):
    """seed 済みの投稿日時を hours 時間前にずらす。"""
    with pg["connection"].cursor() as cursor:
        cursor.execute("UPDATE public.source_messages SET line_posted_at=now()-make_interval(hours=>%s) WHERE id=%s",
                       (hours, item["smid"]))


def output(pg):
    async def run():
        engine=create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return await distribution.fetch_output_rows(db)
        finally:
            await engine.dispose()
    return asyncio.run(run())


def test_pg_python_26_cases(pg):
    statement = text("SELECT " + classification_sql(":name", ":state", ":memo"))
    with Session(pg["engine"]) as db:
        for values, expected in CASES:
            result=db.execute(statement,dict(zip(("name","state","memo"),values))).scalar_one()
            assert result == classify_empty_box(*values) == expected


def test_migration_idempotent_and_other_tenant(pg):
    with pg["connection"].cursor() as cursor:
        cursor.execute("SELECT to_jsonb(c) FROM tenant_004.conditions c ORDER BY code")
        before=cursor.fetchall()
        cursor.execute(MIGRATION.read_text())
        cursor.execute(MIGRATION.read_text())
        cursor.execute("SELECT to_jsonb(c) FROM tenant_004.conditions c ORDER BY code")
        assert cursor.fetchall()==before
        cursor.execute("SELECT canonical FROM tenant_006.conditions WHERE code='CN0099'")
        assert cursor.fetchall()==[("untouched",)]
        cursor.execute("UPDATE tenant_004.conditions SET canonical='Wrong' WHERE code='CN0011'")
        with pytest.raises(psycopg2.Error, match="unexpected existing definition"):
            cursor.execute(MIGRATION.read_text())
        cursor.execute("ROLLBACK")
        cursor.execute("SELECT canonical FROM tenant_004.conditions WHERE code='CN0011'")
        assert cursor.fetchone()[0]=='Wrong'


def test_15_confirmation_states(pg):
    # One real DB; one independent item per design state, no fixture cleanup/deletion.
    labels=["unconfirmed","confirmed-empty","confirmed-other-reason","confirmed-product-unknown","confirmed-unit-unknown",
        "confirmed-price-unknown","confirmed-excluded","changed-raw","changed-source_hash","changed-product","changed-unit",
        "changed-quantity","changed-price","changed-condition_def","same-input-reanalysis"]
    for label in labels:
        extra={}
        if label=='confirmed-other-reason': extra['reasons']='empty_box,note_unmatched';extra['memo']='unclassified note'
        if label=='confirmed-product-unknown': extra['pid_resolved']=False
        if label=='confirmed-unit-unknown': extra['unit_resolved']=False
        if label=='confirmed-price-unknown': extra['price_normalized']=None
        if label=='confirmed-excluded': extra['exclusion']='excluded'
        item=seed(pg,**extra)
        if label!='unconfirmed': save(pg,item)
        changes={
            'changed-raw':("UPDATE public.extraction_items SET raw_quantity='2' WHERE id=%s",item['eid']),
            'changed-source_hash':("UPDATE public.source_messages SET raw_text=raw_text || 'changed' WHERE id=%s",item['smid']),
            'changed-product':("UPDATE public.analysis_results SET product_id=NULL WHERE extraction_item_id=%s",item['eid']),
            'changed-unit':("UPDATE public.analysis_results SET unit_canonical='Case' WHERE extraction_item_id=%s",item['eid']),
            'changed-quantity':("UPDATE public.analysis_results SET quantity_normalized=2 WHERE extraction_item_id=%s",item['eid']),
            'changed-price':("UPDATE public.analysis_results SET price_normalized=20 WHERE extraction_item_id=%s",item['eid']),
            'changed-condition_def':("UPDATE public.conditions SET search_kw='altered' WHERE id=%s",pg['empty']),
        }
        if label in changes:
            with pg['connection'].cursor() as cursor: cursor.execute(changes[label][0],(changes[label][1],))
        if label=='same-input-reanalysis':
            with Session(pg['engine']) as db: analyzer.analyze_extraction_job(db,item['job'])
        row=context(pg,item)
        with Session(pg['engine']) as db:
            ar=db.execute(text('SELECT * FROM public.analysis_results WHERE extraction_item_id=CAST(:eid AS uuid)'),item).mappings().one()
            eligible=not row['needs_review'] and ar['pid_resolved'] and ar['unit_resolved'] and ar['price_normalized'] is not None and ar['exclusion']!='excluded'
        assert eligible == (label in ('confirmed-empty','same-input-reanalysis')),label
        if label=='changed-condition_def':
            with pg['connection'].cursor() as cursor: cursor.execute("UPDATE public.conditions SET search_kw='空箱' WHERE id=%s",(pg['empty'],))


def test_rejections_replay_and_concurrent_requests(pg):
    item=seed(pg); payload=request(pg,item)
    invalids=[(dict(item,smid=str(uuid4())),payload,404), (item,dict(payload,expected_review_version='0'*64),409),
              (item,dict(payload,condition_id=str(uuid4())),422)]
    for target,bad,status in invalids:
        before=context(pg,item)
        with pytest.raises(HTTPException) as error: save(pg,target,bad)
        assert error.value.status_code==status
        assert context(pg,item)==before
    async def race():
        return await asyncio.gather(save_async(pg,item,payload),save_async(pg,item,payload))
    results=asyncio.run(race())
    assert sorted(result['saved'] for result in results)==[0,1]
    assert sum(result['condition_review']['replayed'] for result in results)==1
    with pytest.raises(HTTPException) as error: save(pg,item,dict(payload,decision='correct'))
    assert error.value.status_code==409
    second=seed(pg); one=request(pg,second); two=dict(one,request_id=str(uuid4()))
    async def different_race():
        return await asyncio.gather(save_async(pg,second,one),save_async(pg,second,two),return_exceptions=True)
    outcomes=asyncio.run(different_race())
    assert sum(isinstance(value,HTTPException) and value.status_code==409 for value in outcomes)==1
    with pg['connection'].cursor() as cursor:
        cursor.execute('SELECT count(*) FROM public.item_corrections WHERE extraction_item_id=%s',(item['eid'],))
        assert cursor.fetchone()[0]==1


def test_malformed_latest_never_falls_back(pg):
    for corrupt in (r'{"v":1,"bad":"\u0000"}', '{"v":1,"bad":1e1000000}', 'bad json','[]','{"v":0}', '{"v":1,"condition_id":"not-a-uuid"}', '{"v":1,"request_id":123}'):
        item=seed(pg);save(pg,item)
        with pg['connection'].cursor() as cursor:
            cursor.execute("""INSERT INTO public.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by)
                VALUES (%s,%s,'condition_review',%s,'test')""",(item['eid'],item['smid'],corrupt))
        assert context(pg,item)['needs_review'] is True
    assert output(pg)==[]


def test_historical_memo_and_other_reason(pg):
    item=seed(pg,name='Test Booster',memo=' 空箱 ',reasons='note_unmatched',condition_id=pg['normal'],condition_canonical='Sealed box',condition_basis='R4:単位既定')
    assert output(pg)==[]
    assert context(pg,item)['canonical']=='Empty box'
    result=save(pg,item)
    assert result['condition_review']['needs_review'] is False
    assert output(pg)[0][4]=='Empty box'
    other=seed(pg,memo='shipping note',reasons='empty_box,note_unmatched')
    assert save(pg,other)['condition_review']['needs_review'] is True
    assert len(output(pg))==1


def test_ambiguous_requires_correction_and_preserves_selected_on_reanalysis(pg):
    item=seed(pg,name='Test Booster 空箱も付属',condition_id=pg['normal'],condition_canonical='Sealed box',reasons='empty_box_ambiguous')
    with pytest.raises(HTTPException) as error: save(pg,item,request(pg,item,target=pg['normal']))
    assert error.value.status_code==422
    save(pg,item,request(pg,item,decision='correct',target=pg['normal']))
    with Session(pg['engine']) as db: analyzer.analyze_extraction_job(db,item['job'])
    assert context(pg,item)['valid_ack'] is True
    assert context(pg,item)['canonical']=='Sealed box'


def test_review_tabs_count_paging_and_preview(pg):
    a,b=seed(pg,prompt_version='v102:test'),seed(pg,prompt_version='v102:test')
    set_max_age_hours(pg,48)
    save(pg,a)
    async def run():
        engine=create_async_engine(pg['url'])
        try:
            async with AsyncSession(engine) as db:
                pending=await review.fetch_analysis_results(db,status_tab='NEEDS_REVIEW',limit=1)
                done=await review.fetch_analysis_results(db,status_tab='NORMAL_COMPLETED',limit=1)
                next_page=await review.fetch_analysis_results(db,status_tab='NEEDS_REVIEW',limit=1,offset=1)
                preview=await distribution.fetch_preview_data(db)
                rows=await distribution.fetch_output_rows(db)
                return pending,done,next_page,preview,rows
        finally: await engine.dispose()
    pending,done,next_page,preview,rows=asyncio.run(run())
    assert pending['total']==len(pending['items'])==1 and pending['items'][0]['extraction_item_id']==b['eid']
    assert done['total']==len(done['items'])==1 and done['items'][0]['extraction_item_id']==a['eid']
    assert next_page['total']==1 and next_page['items']==[]
    assert preview['output_count']==len(rows)==1


def test_product_confirmation_skip_and_unit_change_invalidate(pg):
    item=seed(pg);save(pg,item)
    async def confirm_product():
        engine=create_async_engine(pg['url'])
        try:
            async with AsyncSession(engine) as db:
                await corrections.save_corrections(db,extraction_item_id=item['eid'],source_message_id=item['smid'],
                    fields=[{'field_name':'product_id','system_value':pg['product'],'human_value':pg['product']}],corrected_by='test')
        finally: await engine.dispose()
    old=context(pg,item)['review_version']
    asyncio.run(confirm_product())
    assert context(pg,item)['review_version']!=old
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE public.extraction_items SET raw_price='20' WHERE id=%s",(item['eid'],))
    with Session(pg['engine']) as db:
        result=analyzer.analyze_extraction_job(db,item['job'])
        assert result['skipped_product_corrections']==1
    assert context(pg,item)['needs_review'] is True
    save(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE public.analysis_results SET unit_canonical='Case' WHERE extraction_item_id=%s",(item['eid'],))
    assert context(pg,item)['needs_review'] is True


def test_product_category_changes_binding(pg):
    item=seed(pg);save(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE public.products SET product_category_id=NULL WHERE id=%s",(pg['product'],))
    assert context(pg,item)['needs_review'] is True


@pytest.mark.parametrize("column,value,reason", [
    ("pid_resolved",False,"pid_unresolved"), ("unit_resolved",False,"unit_unresolved"),
    ("price_normalized",None,"price_unresolved"),
])
def test_remaining_issue_in_confirmation_response(pg,column,value,reason):
    item=seed(pg,reasons="",**{column:value})
    result=save(pg,item)
    assert result['condition_review']['needs_review'] is True
    assert reason in result['condition_review']['review_reasons'].split(',')
    assert output(pg)==[]


def test_master_missing_or_disabled_holds_historical_rows(pg):
    item=seed(pg,name='Test Booster',memo='空箱',reasons='',condition_id=pg['normal'],condition_canonical='Sealed box')
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE public.conditions SET is_active=false WHERE code='CN0011'")
    assert 'empty_box_master_unavailable' in context(pg,item)['review_reasons']
    assert output(pg)==[]
    with pytest.raises(HTTPException) as error: save(pg,item)
    assert error.value.status_code==422


def test_raw_update_waits_for_review_source_lock(pg, monkeypatch):
    item=seed(pg);payload=request(pg,item)
    async def run():
        engine=create_async_engine(pg['url'])
        locked,proceed=asyncio.Event(),asyncio.Event()
        try:
            async with AsyncSession(engine) as first, AsyncSession(engine) as second:
                original_execute=first.execute
                async def observed(statement,*args,**kwargs):
                    result=await original_execute(statement,*args,**kwargs)
                    if 'FOR SHARE OF ei, ej, sm' in str(statement):
                        locked.set()
                        await proceed.wait()
                    return result
                monkeypatch.setattr(first,'execute',observed)
                saving=asyncio.create_task(condition.save_condition_review(first,extraction_item_id=item['eid'],
                    source_message_id=item['smid'],request=payload,corrected_by='test'))
                await asyncio.wait_for(locked.wait(),10)
                await second.execute(text("SET LOCAL lock_timeout='100ms'"))
                try:
                    with pytest.raises(Exception,match='lock timeout'):
                        await second.execute(text("UPDATE public.source_messages SET raw_text='changed' WHERE id=CAST(:smid AS uuid)"),item)
                finally:
                    await second.rollback()
                    proceed.set()
                result=await asyncio.wait_for(saving,10)
                assert result['saved']==1
        finally: await engine.dispose()
    asyncio.run(run())


def test_migration_partial_structure_rejects_before_insert(pg):
    # New isolated schema, no destructive cleanup of any existing table.
    script=MIGRATION.read_text().replace('tenant_004','tenant_907')
    with pg['connection'].cursor() as cursor:
        provision(cursor, 'tenant_907')
        cursor.execute('CREATE SCHEMA tenant_908')
        cursor.execute('ALTER TABLE tenant_907.extraction_items SET SCHEMA tenant_908')
        # Migration now emits RAISE NOTICE + RETURN (graceful skip) instead of raising an exception
        cursor.execute(script)
        cursor.execute('SELECT count(*) FROM tenant_907.conditions')
        assert cursor.fetchone()[0]==0
        # An entirely absent TCG structure is the documented no-op, not partial success.
        cursor.execute(MIGRATION.read_text().replace('tenant_004','tenant_909'))
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='tenant_909'")
        assert cursor.fetchone()[0]==0


def test_product_correction_changes_binding_and_retains_manual_product(pg):
    item=seed(pg);save(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("INSERT INTO public.products(product_code,name,category_class,is_active) VALUES ('PM0901','Other product','Box',true) RETURNING id")
        other=str(cursor.fetchone()[0])
    async def run():
        engine=create_async_engine(pg['url'])
        try:
            async with AsyncSession(engine) as db:
                await corrections.save_corrections(db,extraction_item_id=item['eid'],source_message_id=item['smid'],
                    fields=[{'field_name':'product_id','system_value':pg['product'],'human_value':other}],corrected_by='test')
        finally: await engine.dispose()
    asyncio.run(run())
    assert context(pg,item)['needs_review'] is True
    with Session(pg['engine']) as db:
        analyzer.analyze_extraction_job(db,item['job'])
        assert str(db.execute(text("SELECT product_id FROM public.analysis_results WHERE extraction_item_id=CAST(:eid AS uuid)"),item).scalar_one())==other


def test_real_input_change_rejects_old_screen_without_writes(pg):
    item=seed(pg);payload=request(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE public.extraction_items SET raw_price='20' WHERE id=%s",(item['eid'],))
    before=context(pg,item)
    with pytest.raises(HTTPException) as error:save(pg,item,payload)
    assert error.value.status_code==409
    assert context(pg,item)==before


def test_missing_empty_definition_holds(pg):
    item=seed(pg,condition_id=pg['normal'],condition_canonical='Sealed box',reasons='')
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE public.conditions SET code='CN0098' WHERE code='CN0011'")
    assert 'empty_box_master_unavailable' in context(pg,item)['review_reasons']
    assert output(pg)==[]


def test_quantity_and_price_binding_matches_storage_precision(pg):
    item=seed(pg)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE public.extraction_items SET raw_quantity='2.345',raw_price='10.125' WHERE id=%s",(item['eid'],))
    with Session(pg['engine']) as db:
        analyzer.analyze_extraction_job(db,item['job'])
        numeric=db.execute(text("SELECT quantity_normalized::text,price_normalized::text FROM public.analysis_results WHERE extraction_item_id=CAST(:eid AS uuid)"),item).one()
        assert tuple(numeric)==('2.35','10.13')
    save(pg,item)
    binding=context(pg,item)['ack_binding_hash']
    with Session(pg['engine']) as db: analyzer.analyze_extraction_job(db,item['job'])
    after=context(pg,item)
    assert after['valid_ack'] is True and after['needs_review'] is False
    assert after['ack_binding_hash']==binding

def test_review_reason_details_use_code_table_and_keep_unknown_codes(pg):
    """理由ごとの配列は API 自身の review_reasons から作られ、表の出どころが付く（便A）。

    seed() は condition_canonical='Empty box' で入れるため、API の導出（tcg_condition_review_svc.py）が
    empty_box を足す。期待は固定の配列ではなく API 自身の文字列との一致で書く。
    """
    table = {"gemini_unsure": ("gemini", "extraction"),
             "empty_box": ("system", "analysis")}
    with pg["connection"].cursor() as cursor:
        cursor.execute("INSERT INTO public.review_reason_codes(code,source,fix_stage) VALUES "
                       "('gemini_unsure','gemini','extraction'),('empty_box','system','analysis')")
    known = seed(pg, name="Known", reasons="gemini_unsure, gemini_unsure ,,")
    unknown = seed(pg, name="Unknown", reasons="not_registered_code")
    empty = seed(pg, name="Empty", reasons="", needs_review=False, condition_canonical="Sealed box")

    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return await review.fetch_analysis_results(db, limit=500)
        finally:
            await engine.dispose()

    items = {item["extraction_item_id"]: item for item in asyncio.run(run())["items"]}
    for seeded in (known, unknown, empty):
        item = items[seeded["eid"]]
        codes = [d["code"] for d in item["review_reason_details"]]
        assert codes == split_reason_codes(item["condition_review"]["review_reasons"])
        for d in item["review_reason_details"]:
            expected = table.get(d["code"], (None, None))
            assert (d["source"], d["fix_stage"]) == expected
    by_code = {d["code"]: d for d in items[known["eid"]]["review_reason_details"]}
    assert by_code["gemini_unsure"] == {"code": "gemini_unsure", "source": "gemini", "fix_stage": "extraction", "ackable": True}
    assert [d["code"] for d in items[known["eid"]]["review_reason_details"]].count("gemini_unsure") == 1
    assert {"code": "not_registered_code", "source": None, "fix_stage": None, "ackable": True} in items[unknown["eid"]]["review_reason_details"]
    assert items[empty["eid"]]["review_reason_details"] == []


# --- effect='EXCLUDE' の状態（Error）は配信しない・選べない（便ER） ------------------------------------


def add_error_condition(pg):
    """旧い試験 DB には effect 列が無いので足す（本番にはある）。Error = effect EXCLUDE の1行。"""
    with pg["connection"].cursor() as cursor:
        cursor.execute("ALTER TABLE public.conditions ADD COLUMN IF NOT EXISTS effect TEXT NOT NULL DEFAULT 'OUTPUT'")
        cursor.execute("INSERT INTO public.conditions(code,canonical,priority,app_kubun,search_kw,exclude_kw,is_active,effect) "
                       "VALUES ('CN0012','Error',99,'','','',true,'EXCLUDE') RETURNING id")
        return str(cursor.fetchone()[0])


def seed_deliverable(pg, name, condition_id, canonical):
    return seed(pg, name=name, reasons="", needs_review=False, condition_id=condition_id, condition_canonical=canonical)


@pytest.mark.parametrize("include_flag_single", [False, True])
def test_excluded_effect_condition_is_not_delivered_even_when_review_is_clear(pg, include_flag_single):
    error_id = add_error_condition(pg)
    set_max_age_hours(pg, 48)
    seed_deliverable(pg, "Test Booster", pg["normal"], "Sealed box")
    seed_deliverable(pg, "Test Booster", error_id, "Error")

    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return (await distribution.fetch_output_rows(db, include_flag_single=include_flag_single),
                        await distribution.fetch_preview_data(db))
        finally:
            await engine.dispose()

    rows, preview = asyncio.run(run())
    assert [row[4] for row in rows] == ["Sealed box"]
    assert preview["output_count"] == 1 and preview["exclusion"]["flag_series"] == 1


def test_review_context_exposes_effect_of_the_effective_condition(pg):
    error_id = add_error_condition(pg)
    error = seed_deliverable(pg, "Test Booster", error_id, "Error")
    normal = seed_deliverable(pg, "Test Booster", pg["normal"], "Sealed box")
    assert context(pg, error)["effect"] == "EXCLUDE"
    assert context(pg, normal)["effect"] == "OUTPUT"


def test_condition_options_hide_excluded_effect_and_saving_it_is_422(pg):
    error_id = add_error_condition(pg)
    item = seed(pg, name="Test Booster", reasons="condition_unknown")

    async def options():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return await condition.condition_options(db)
        finally:
            await engine.dispose()

    codes = [o["code"] for o in asyncio.run(options())]
    assert "CN0012" not in codes and "CN0003" in codes
    with pytest.raises(HTTPException) as caught:
        save(pg, item, request(pg, item, decision="correct", target=error_id))
    assert caught.value.status_code == 422


@pytest.mark.parametrize(("reasons", "expected_reasons", "expected_needs_review"), [
    ("condition_unknown", "", False),
    ("condition_unknown,condition_multiple_candidates", "", False),
    ("condition_unknown,gemini_unsure", "gemini_unsure", True),
])
def test_saving_a_condition_removes_condition_reasons_at_save_time(pg, reasons, expected_reasons, expected_needs_review):
    """人が状態を選んで保存した直後に condition_unknown 等が外れる（再解析が積めなくても詰まらない）。他の理由は残る。"""
    item = seed(pg, name="Test Booster", reasons=reasons, condition_id=pg["normal"], condition_canonical="Sealed box")
    save(pg, item, request(pg, item, decision="correct", target=pg["normal"]))
    with pg["connection"].cursor() as cursor:
        cursor.execute("SELECT needs_review, COALESCE(review_reasons,'') FROM public.analysis_results WHERE extraction_item_id=%s", (item["eid"],))
        needs_review, stored = cursor.fetchone()
    assert needs_review is expected_needs_review
    assert stored == expected_reasons
    assert "condition_unknown" not in context(pg, item)["review_reasons"]


def _age_window_run(pg):
    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                settings = await distribution.load_distribution_settings(db)
                hours = distribution._max_age_hours(settings)
                return (await distribution.fetch_output_rows(db, max_age_hours=hours),
                        await distribution.fetch_preview_data(db))
        finally:
            await engine.dispose()
    return asyncio.run(run())


def test_age_window_same_condition_for_delivery_count_and_exclusion_breakdown(pg):
    """48時間(設定値)より前の行は 配信・件数・除外内訳 のどれにも入らない。"""
    set_max_age_hours(pg, 48)
    fresh_ok = seed_deliverable(pg, "Test Booster", pg["normal"], "Sealed box")
    old_ok = seed_deliverable(pg, "Test Booster", pg["normal"], "Sealed box")
    fresh_unresolved = seed(pg, name="Test Booster", reasons="", needs_review=False, pid_resolved=False)
    old_unresolved = seed(pg, name="Test Booster", reasons="", needs_review=False, pid_resolved=False)
    age_message(pg, fresh_ok, 47)
    age_message(pg, old_ok, 49)
    age_message(pg, fresh_unresolved, 1)
    age_message(pg, old_unresolved, 100)
    rows, preview = _age_window_run(pg)
    assert len(rows) == 1 and preview["output_count"] == 1
    assert preview["exclusion"]["pid_unresolved_only"] == 1  # 48時間より前の1件は数えない


def test_age_window_zero_is_unbounded_everywhere(pg):
    set_max_age_hours(pg, 0)
    old_ok = seed_deliverable(pg, "Test Booster", pg["normal"], "Sealed box")
    old_unresolved = seed(pg, name="Test Booster", reasons="", needs_review=False, pid_resolved=False)
    age_message(pg, old_ok, 1000)
    age_message(pg, old_unresolved, 1000)
    rows, preview = _age_window_run(pg)
    assert len(rows) == 1 and preview["output_count"] == 1
    assert preview["exclusion"]["pid_unresolved_only"] == 1


@pytest.mark.parametrize("value", [None, "", "abc", "-1"])
def test_preview_raises_when_max_age_hours_missing_or_invalid(pg, value):
    set_max_age_hours(pg, value)
    seed_deliverable(pg, "Test Booster", pg["normal"], "Sealed box")

    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return await distribution.fetch_preview_data(db)
        finally:
            await engine.dispose()

    with pytest.raises(distribution.MaxAgeHoursUnsetError):
        asyncio.run(run())


def test_review_joins_keeps_offset_zero_pullup_barrier():
    # OFFSET 0 stops PostgreSQL from pulling up the LATERAL subquery (docs/handoff/review-speed/design.md)
    barrier = "AS ar OFFSET 0) cr_data"
    plain = "AS ar) cr_data"

    joins = condition.review_joins()
    assert barrier in joins and plain not in joins

    context = condition.context_sql(analysis_expression="to_jsonb(ar) || CAST(:candidate AS jsonb)")
    assert barrier in context and plain not in context

    assert review._BASE_FROM.count(barrier) == 1 and plain not in review._BASE_FROM


def test_sold_out_row_is_excluded_from_preview_count_and_output_rows(pg):
    """便1: Sold out（前後の空白・大文字小文字を無視）は配信プレビューの件数と出力行の両方から除く。"""
    set_max_age_hours(pg, 48)
    seed_deliverable(pg, "Test Booster", pg["normal"], "Sealed box")
    seed(pg, name="Test Booster", reasons="", needs_review=False, condition_id=pg["normal"],
         condition_canonical="Sealed box", status=" Sold Out ")

    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return await distribution.fetch_preview_data(db), await distribution.fetch_output_rows(db)
        finally:
            await engine.dispose()

    preview, rows = asyncio.run(run())
    assert preview["output_count"] == len(rows) == 1


def test_needs_review_tab_hides_old_prompt_versions_only(pg):
    """旧解析版（v102 以外）の行は要確認タブに出ない。全件・他タブ+review_only では出る/出ない。"""
    with pg["connection"].cursor() as cursor:
        cursor.execute("INSERT INTO public.suppliers(name,supplier_type) VALUES ('OldVersionSupplier','corporate') RETURNING id")
        cursor.execute("INSERT INTO public.supplier_channels(channel,is_active,supplier_id) VALUES ('line',true,%s) RETURNING id", (cursor.fetchone()[0],))
        old_channel = str(cursor.fetchone()[0])
        cursor.execute("SELECT id FROM public.supplier_channels WHERE id<>%s::uuid LIMIT 1", (old_channel,))
        new_channel = str(cursor.fetchone()[0])
    new = seed(pg, name="Test Booster 新版", channel_id=new_channel, prompt_version="v102:test")
    old = seed(pg, name="Test Booster 旧版", prompt_version="raw-extraction-v5-product-p1", channel_id=old_channel)

    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                tabs = {}
                for key, kwargs in {
                    "needs": {"status_tab": "NEEDS_REVIEW"},
                    "all": {"status_tab": "ALL"},
                    "all_review_only": {"status_tab": "ALL", "review_only": True},
                    "unreg_review_only": {"status_tab": "PRODUCT_ID_UNRESOLVED", "review_only": True},
                }.items():
                    tabs[key] = await review.fetch_analysis_results(db, limit=50, **kwargs)
                by_id = await review.fetch_analysis_results(db, status_tab="ALL", extraction_item_ids=[old["eid"]], limit=50)
                return tabs, by_id
        finally:
            await engine.dispose()

    tabs, by_id = asyncio.run(run())
    ids = lambda r: {i["extraction_item_id"] for i in r["items"]}  # noqa: E731
    assert ids(tabs["needs"]) == {new["eid"]} and tabs["needs"]["total"] == 1  # (a)
    assert ids(tabs["all"]) == {new["eid"], old["eid"]} and tabs["all"]["total"] == 2  # (b)
    assert ids(tabs["all_review_only"]) == {new["eid"]} and tabs["all_review_only"]["total"] == 1  # (c)
    assert old["eid"] not in ids(tabs["unreg_review_only"])  # (c)
    assert "OldVersionSupplier" not in tabs["needs"]["providers"] and "OldVersionSupplier" in tabs["all"]["providers"]  # (d)
    assert ids(by_id) == {old["eid"]}  # ID 指定は不変（旧版も出る）


# ---- 〆の確認済み扱い（docs/handoff/shime-review-exclude/design.md §12-3・§7 T1） ----

def seed_shime(pg, **overrides):
    """価格のない〆（Sold out・excluded・価格と数量なし）の行。"""
    values = dict(name="Test Booster", reasons="", needs_review=False, condition_id=pg["normal"],
                  condition_canonical="Sealed box", status="Sold out", exclusion="excluded",
                  price_normalized=None, quantity_normalized=None)
    values.update(overrides)
    return seed(pg, **values)


def seed_partner(pg, hours, *, channel_id=None, **overrides):
    """同じ商品・同じ状態の相手の在庫（価格あり）。投稿を hours 時間前にする。"""
    values = dict(name="Test Booster", reasons="", needs_review=False, condition_id=pg["normal"],
                  condition_canonical="Sealed box")
    values.update(overrides)
    item = seed(pg, channel_id=channel_id, **values)
    age_message(pg, item, hours)
    return item


def shime_reasons(pg, item):
    return set(filter(None, context(pg, item)["review_reasons"].split(",")))


def test_shime_settled_when_partner_stock_is_gone(pg):  # (a)
    shime = seed_shime(pg)
    seed_partner(pg, 100)
    ctx = context(pg, shime)
    assert ctx["needs_review"] is False
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_settled_without_partner_stock(pg):  # (b)
    shime = seed_shime(pg)
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}
    assert context(pg, shime)["needs_review"] is False


def test_shime_stays_while_partner_stock_is_within_window(pg):  # (c)
    shime = seed_shime(pg)
    seed_partner(pg, 10)
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_settled_when_partner_stock_is_older_than_window(pg):  # (d)
    shime = seed_shime(pg)
    seed_partner(pg, 49)
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_stays_when_condition_is_flag(pg):  # (e)
    shime = seed_shime(pg, condition_basis="FLAG_UNKNOWN")
    seed_partner(pg, 100)
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_stays_when_human_correction_exists(pg):  # (f)
    shime = seed_shime(pg)
    seed_partner(pg, 100)
    with pg["connection"].cursor() as cursor:
        cursor.execute("""INSERT INTO public.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by)
            VALUES (%s,%s,'raw_memo','x','test')""", (shime["eid"], shime["smid"]))
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_settled_when_only_other_channel_has_the_partner(pg):  # (g)
    with pg["connection"].cursor() as cursor:
        cursor.execute("INSERT INTO public.suppliers(name,supplier_type) VALUES ('ShimeOtherSupplier','corporate') RETURNING id")
        cursor.execute("INSERT INTO public.supplier_channels(channel,is_active,supplier_id) VALUES ('line',true,%s) RETURNING id",
                       (cursor.fetchone()[0],))
        other_channel = str(cursor.fetchone()[0])
        cursor.execute("SELECT id FROM public.supplier_channels WHERE id<>%s::uuid ORDER BY id LIMIT 1", (other_channel,))
        own_channel = str(cursor.fetchone()[0])
    shime = seed_shime(pg, channel_id=own_channel)
    seed_partner(pg, 10, channel_id=other_channel)
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_other_saved_reason_stays_needs_review(pg):  # (h)
    shime = seed_shime(pg, reasons="condition_unknown", needs_review=True)
    seed_partner(pg, 100)
    ctx = context(pg, shime)
    assert ctx["needs_review"] is True
    reasons = shime_reasons(pg, shime)
    assert "condition_unknown" in reasons and not reasons & {"price_unresolved", "excluded"}


def test_shime_settled_when_partner_is_superseded_not_current(pg):  # (i)
    shime = seed_shime(pg)
    seed_partner(pg, 10, is_current=False)
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_settled_when_partner_was_posted_after_it_but_old(pg):  # (j)
    shime = seed_shime(pg)
    age_message(pg, shime, 200)
    seed_partner(pg, 100)
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_settled_when_partner_is_sold_out_too(pg):  # (k)
    shime = seed_shime(pg)
    seed_partner(pg, 100, status="Sold out")
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def put_in_same_post(pg, partner, shime):
    """相手の job を〆の投稿に付け替える（同じ投稿の別の行にする）。"""
    with pg["connection"].cursor() as cursor:
        cursor.execute("UPDATE public.extraction_jobs SET source_message_id=%s WHERE id=%s", (shime["smid"], partner["job"]))


def test_shime_settled_with_price_and_quantity_and_no_partner(pg):  # (p)
    shime = seed_shime(pg, price_normalized=7500, quantity_normalized=3)
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_settled_when_same_post_has_other_condition_stock(pg):  # (q)
    shime = seed_shime(pg)
    partner = seed_partner(pg, 0, condition_id=pg["empty"], condition_canonical="Empty box")
    put_in_same_post(pg, partner, shime)
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_stays_when_same_post_has_same_condition_stock(pg):  # (r)
    shime = seed_shime(pg)
    partner = seed_partner(pg, 0)
    put_in_same_post(pg, partner, shime)
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_stays_when_other_post_has_other_condition_stock(pg):  # (s)
    shime = seed_shime(pg)
    seed_partner(pg, 10, condition_id=pg["empty"], condition_canonical="Empty box")
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_stays_when_superseded_post_still_has_current_stock(pg):  # (t)
    shime = seed_shime(pg)
    partner = seed_partner(pg, 10)
    with pg["connection"].cursor() as cursor:
        cursor.execute("UPDATE public.source_messages SET is_active=false WHERE id=%s", (partner["smid"],))
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


# ---- 〆より前の別の状態の相手は最新の在庫の投稿のものだけ数える（design.md §13-10 A-2・T1 (kk)〜(nn)） ----

def test_shime_settled_when_other_state_partner_is_only_in_an_older_post_than_the_latest_stock_post(pg):  # (kk)
    shime = seed_shime(pg)
    seed_partner(pg, 20, condition_id=pg["empty"], condition_canonical="Empty box")  # P0：別の状態・現行
    seed_partner(pg, 10, is_current=False)  # P1：最新の在庫の投稿（行は現行でない＝相手の条件を満たさない）
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}


def test_shime_stays_when_older_post_partner_has_the_same_condition(pg):  # (ll)
    shime = seed_shime(pg)
    seed_partner(pg, 20)  # P0：〆と同じ状態・現行（どの投稿のものでも数える）
    seed_partner(pg, 10, is_current=False)
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_stays_when_the_latest_stock_post_has_other_state_partner(pg):  # (mm)
    shime = seed_shime(pg)
    seed_partner(pg, 20, condition_id=pg["empty"], condition_canonical="Empty box")
    seed_partner(pg, 10, condition_id=pg["empty"], condition_canonical="Empty box")  # P1：最新の在庫の投稿の別の状態
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_settled_when_the_latest_stock_post_is_outside_the_partner_window(pg):  # (oo)
    shime = seed_shime(pg)
    seed_partner(pg, 60, condition_id=pg["empty"], condition_canonical="Empty box")  # 〆より前の最新の在庫の投稿：60時間前（窓の外）・別の状態の現行行
    seed_partner(pg, 24, status="Sold out")  # 24時間前の投稿：在庫の行が無い（〆だけ）
    assert not shime_reasons(pg, shime) & {"price_unresolved", "excluded"}  # 現 HEAD（窓なしの cr_n1）でも同じ。窓の外は相手の条件で落ちる


def test_shime_stays_when_the_latest_stock_post_is_inside_the_partner_window(pg):  # (oo2)
    shime = seed_shime(pg)
    seed_partner(pg, 40, condition_id=pg["empty"], condition_canonical="Empty box")  # 窓の内なら相手になる（窓を狭めすぎていない）
    seed_partner(pg, 24, status="Sold out")
    assert {"price_unresolved", "excluded"} <= shime_reasons(pg, shime)


def test_shime_form_row_does_not_break_fenced_distribution_sql(pg):  # (l)
    set_max_age_hours(pg, 48)
    seed_shime(pg)
    seed_partner(pg, 100)
    seed_partner(pg, 1)
    rows = output(pg)  # review_joins(fenced=True, shime=False) を通る在庫表（cr_shime は作らない）。例外が出ず、〆の行は出ない（出るのは相手の2行だけ。output は年齢の窓を渡さない）
    assert len(rows) == 2


def test_shime_false_has_no_partner_subqueries():  # (m)
    for fenced in (False, True):
        joins = condition.review_joins(schema="tcg", fenced=fenced, shime=False)
        assert "cr_pa" not in joins and "cr_sa" not in joins
        assert joins.count("SELECT FALSE AS settled OFFSET 0) cr_shime") == 1
        assert joins.count("OFFSET 0") == (10 if fenced else 3)


@pytest.mark.parametrize("grouped", [False, True])
def test_distribution_rows_sql_has_no_shime_subquery(grouped):  # (n)
    sql = distribution.distribution_rows_sql(include_flag_single=False, age_condition="TRUE", merge_same_post=grouped)
    assert "cr_pa" not in sql and "cr_sa" not in sql


def test_callers_pass_shime_false():  # (o)
    root = Path(distribution.__file__).parent
    assert (root / "tcg_distribution_svc.py").read_text(encoding="utf-8").count("shime=False") == 3
    assert (root / "tcg_import_progress.py").read_text(encoding="utf-8").count("shime=False") == 1


def test_shime_review_joins_has_the_latest_stock_post_subquery_without_new_offset_0():  # (nn)
    joins = condition.review_joins(schema="tcg", shime=True)
    assert "cr_p.id" in joins and joins.count("OFFSET 0") == 3  # コメント1・cr_data 1・cr_shime 1（足していない）
    assert joins.count("cr_prev") == 2 and joins.count("cr_n1x.id") == 1  # cr_prev の参照も cr_n1x の参照も1か所だけ（コメントの1語を含む）
    assert "cr_n1" not in condition.review_joins(schema="tcg", shime=False) and "cr_prev" not in condition.review_joins(schema="tcg", shime=False)


def test_latest_stock_cte_is_in_source_cte_and_window_matches_the_partner_window():  # (pp)
    joins = condition.review_joins(schema="tcg", shime=True)
    window = f"line_posted_at >= NOW() - make_interval(hours => {condition.SHIME_STOCK_WINDOW_HOURS})"
    assert f"cr_sm.{window}" in joins and f"cr_n1.{window}" in condition.source_cte(schema="tcg")  # 相手の条件と同じ式
    assert condition.source_cte(schema="tcg").startswith("WITH cr_prev AS MATERIALIZED (")
    assert "cr_prev" not in condition.source_cte(schema="tcg", latest_stock=False)  # shime=False の呼び出し側は文字列が変わらない


# ---------------------------------------------------------------------------
# 便1（ADR-1023 改訂 2026-10-21）: 要確認タブの新しい道（1本の SQL）と今の道の中身が同じ
# ---------------------------------------------------------------------------


def _seed_posts_for_posted_desc(pg):
    """要確認の行: 24時間以内に3件（うち2件は同じ投稿・仕入元は2つ）、24時間より古い1件。"""
    set_max_age_hours(pg, 48)
    with pg["connection"].cursor() as cursor:
        cursor.execute("INSERT INTO public.suppliers(name) VALUES ('Other Supplier') RETURNING id")
        other_supplier = cursor.fetchone()[0]
        cursor.execute("INSERT INTO public.supplier_channels(channel,is_active,supplier_id) VALUES ('line',true,%s) RETURNING id",
                       (other_supplier,))
        other_channel = str(cursor.fetchone()[0])
    fresh_a = seed(pg, name="Fresh A", prompt_version="v102:test")
    fresh_b = seed(pg, name="Fresh B", prompt_version="v102:test", channel_id=other_channel)
    fresh_c = seed(pg, name="Fresh C", prompt_version="v102:test")
    old = seed(pg, name="Old D", prompt_version="v102:test")
    age_message(pg, fresh_a, 1)
    age_message(pg, fresh_b, 3)
    age_message(pg, old, 30)
    with pg["connection"].cursor() as cursor:
        # fresh_c の行を fresh_a と同じ投稿（同じ job）の2行目にする
        cursor.execute("UPDATE public.extraction_items SET extraction_job_id=%s, line_start=2, line_end=2 WHERE id=%s",
                       (fresh_a["job"], fresh_c["eid"]))
    return [fresh_a, fresh_b, fresh_c, old]


def _run_fetch(pg, **kwargs):
    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                return await review.fetch_analysis_results(db, status_tab="NEEDS_REVIEW", **kwargs)
        finally:
            await engine.dispose()
    return asyncio.run(run())


def _posted_desc_key(item):
    posted = item["posted_at"]
    return (posted is None, -(posted.timestamp() if posted is not None else 0), item["source_message_id"])


def _all_pages_posted_desc(pg, size, **kwargs):
    pages, offset = [], 0
    while True:
        page = _run_fetch(pg, order="posted_desc", limit=size, offset=offset, **kwargs)
        pages.append(page)
        offset += size
        if offset >= page["total"]:
            return pages


@pytest.mark.parametrize("size", [1, 2, 25])
def test_posted_desc_path_matches_current_path_without_window(pg, size):
    seeded = _seed_posts_for_posted_desc(pg)
    old = _run_fetch(pg, limit=500)
    assert old["total"] == len(seeded) == len(old["items"])
    expected = sorted(old["items"], key=_posted_desc_key)  # 安定ソート（今の道は ei.id まで全順序）
    pages = _all_pages_posted_desc(pg, size)
    merged = [item for page in pages for item in page["items"]]
    assert merged == expected
    for page in pages:
        assert page["total"] == old["total"] and page["providers"] == old["providers"]
    assert len(old["providers"]) >= 2


def test_posted_desc_path_with_window_matches_current_path_filtered(pg):
    from datetime import datetime, timedelta, timezone

    seeded = _seed_posts_for_posted_desc(pg)
    old = _run_fetch(pg, limit=500)
    border = datetime.now(timezone.utc) - timedelta(hours=24)
    expected = sorted([i for i in old["items"] if i["posted_at"] is not None and i["posted_at"] >= border],
                      key=_posted_desc_key)
    assert 0 < len(expected) < len(seeded)
    pages = _all_pages_posted_desc(pg, 2, posted_within_hours=24)
    merged = [item for page in pages for item in page["items"]]
    assert merged == expected
    assert all(page["total"] == len(expected) for page in pages)
    assert pages[0]["providers"] == sorted({i["provider"] for i in expected})


def test_posted_desc_path_empty_page_keeps_total_and_providers(pg):
    _seed_posts_for_posted_desc(pg)
    old = _run_fetch(pg, limit=500)
    page = _run_fetch(pg, order="posted_desc", limit=25, offset=100)
    assert page["items"] == [] and page["total"] == old["total"] and page["providers"] == old["providers"]


def test_posted_desc_path_restores_jit_setting(pg):
    _seed_posts_for_posted_desc(pg)

    async def run():
        engine = create_async_engine(pg["url"])
        try:
            async with AsyncSession(engine) as db:
                before = (await db.execute(text("SELECT current_setting('jit')"))).scalar_one()
                await review.fetch_analysis_results(db, status_tab="NEEDS_REVIEW", order="posted_desc", limit=25)
                after = (await db.execute(text("SELECT current_setting('jit')"))).scalar_one()
                return before, after
        finally:
            await engine.dispose()
    before, after = asyncio.run(run())
    assert before == after
