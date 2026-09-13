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
from app.services import tcg_analyzer_svc as analyzer
from app.services import tcg_analysis_review_svc as review
from app.services import tcg_condition_review_svc as condition
from app.services import tcg_distribution_svc as distribution
from app.services.tcg_empty_box_rules import classification_sql, classify_empty_box
from tests.test_tcg_empty_box_rules import CASES
from tests.test_tcg_work_matching_integration import provision

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
MIGRATION = MIGRATIONS / "20260913_150000_tcg_empty_box_condition.sql"
SCHEMA = "tenant_004"


@pytest.fixture
def pg():
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
            cursor.execute((MIGRATIONS / "20260910_160000_tcg_work_evidence.sql").read_text())
            cursor.execute(MIGRATION.read_text())
            provision(cursor, "tenant_006")
            cursor.execute("INSERT INTO tenant_006.conditions (code,canonical,is_active) VALUES ('CN0099','untouched',true)")
            cursor.execute("INSERT INTO tenant_004.conditions (code,canonical,priority,app_kubun,search_kw,exclude_kw,is_active) VALUES ('CN0003','Sealed box',4,'箱系','未開封','',true) RETURNING id")
            normal = str(cursor.fetchone()[0])
            cursor.execute("SELECT id FROM tenant_004.conditions WHERE code='CN0011'")
            empty = str(cursor.fetchone()[0])
            cursor.execute("INSERT INTO tenant_004.units(id,code,canonical,kubun,is_active) VALUES ('8e980434-eeff-4233-be5c-bcd0ba1db992','UN0002','Box','箱系',true) RETURNING id")
            unit = str(cursor.fetchone()[0])
            cursor.execute("INSERT INTO tenant_004.unit_aliases(unit_id,alias_text,lang) VALUES (%s,'Box','en')", (unit,))
            cursor.execute("""INSERT INTO tenant_004.tcg_products (code,japanese_title,category_class,is_active,work_id,product_category_id)
                SELECT 'PM0900','Test Booster','Box',true,w.id,c.id FROM tenant_004.tcg_series w,tenant_004.tcg_product_categories c
                WHERE w.code='IP001' AND c.code='PC_BOX' RETURNING id""")
            product = str(cursor.fetchone()[0])
            cursor.execute("INSERT INTO tenant_004.product_search_keywords(id,product_id,keyword,position) VALUES (%s,%s,'Test Booster',0)", (str(uuid4()),product))
        yield {"connection": connection, "engine": engine,
               "url": url.set(database=name, drivername="postgresql+asyncpg"), "empty": empty,
               "normal": normal, "unit": unit, "product": product}
    finally:
        engine.dispose()
        connection.close()


def seed(pg, *, name="Test Booster 空箱", state="", memo="", reasons="empty_box", **overrides):
    smid, job, eid = str(uuid4()), str(uuid4()), str(uuid4())
    raw = name + state + memo
    with pg["connection"].cursor() as cursor:
        cursor.execute("""INSERT INTO tenant_004.source_messages(id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at)
            SELECT %s,id,%s,%s,true,now() FROM tenant_004.supplier_channels LIMIT 1""",
            (smid, raw, hashlib.sha256(raw.encode()).hexdigest()))
        cursor.execute("INSERT INTO tenant_004.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')", (job,smid))
        cursor.execute("""INSERT INTO tenant_004.extraction_items(id,extraction_job_id,line_start,line_end,raw_product_name,
            raw_quantity,raw_price,raw_unit,raw_state,raw_memo) VALUES (%s,%s,1,1,%s,'1','10','Box',%s,%s)""", (eid,job,name,state,memo))
        values = {"product_id":pg["product"],"pid_resolved":True,"pid_basis":"EXACT","unit_id":pg["unit"],
            "unit_canonical":"Box","unit_resolved":True,"condition_id":pg["empty"],"condition_canonical":"Empty box",
            "condition_basis":"EMPTY_BOX:explicit","quantity_normalized":1,"price_normalized":10,"note_ja":None,
            "status":"active","exclusion":None,"needs_review":bool(reasons),"review_reasons":reasons or None,"engine_version":"test"}
        values.update(overrides)
        cursor.execute(sql.SQL("INSERT INTO tenant_004.analysis_results(extraction_item_id,{}) VALUES (%s,{})").format(
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
            'changed-raw':("UPDATE tenant_004.extraction_items SET raw_quantity='2' WHERE id=%s",item['eid']),
            'changed-source_hash':("UPDATE tenant_004.source_messages SET raw_text=raw_text || 'changed' WHERE id=%s",item['smid']),
            'changed-product':("UPDATE tenant_004.analysis_results SET product_id=NULL WHERE extraction_item_id=%s",item['eid']),
            'changed-unit':("UPDATE tenant_004.analysis_results SET unit_canonical='Case' WHERE extraction_item_id=%s",item['eid']),
            'changed-quantity':("UPDATE tenant_004.analysis_results SET quantity_normalized=2 WHERE extraction_item_id=%s",item['eid']),
            'changed-price':("UPDATE tenant_004.analysis_results SET price_normalized=20 WHERE extraction_item_id=%s",item['eid']),
            'changed-condition_def':("UPDATE tenant_004.conditions SET search_kw='altered' WHERE id=%s",pg['empty']),
        }
        if label in changes:
            with pg['connection'].cursor() as cursor: cursor.execute(changes[label][0],(changes[label][1],))
        if label=='same-input-reanalysis':
            with Session(pg['engine']) as db: analyzer.analyze_extraction_job(db,item['job'])
        row=context(pg,item)
        with Session(pg['engine']) as db:
            ar=db.execute(text('SELECT * FROM tenant_004.analysis_results WHERE extraction_item_id=CAST(:eid AS uuid)'),item).mappings().one()
            eligible=not row['needs_review'] and ar['pid_resolved'] and ar['unit_resolved'] and ar['price_normalized'] is not None and ar['exclusion']!='excluded'
        assert eligible == (label in ('confirmed-empty','same-input-reanalysis')),label
        if label=='changed-condition_def':
            with pg['connection'].cursor() as cursor: cursor.execute("UPDATE tenant_004.conditions SET search_kw='空箱' WHERE id=%s",(pg['empty'],))


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
        cursor.execute('SELECT count(*) FROM tenant_004.item_corrections WHERE extraction_item_id=%s',(item['eid'],))
        assert cursor.fetchone()[0]==1


def test_malformed_latest_never_falls_back(pg):
    for corrupt in (r'{"v":1,"bad":"\u0000"}', '{"v":1,"bad":1e1000000}', 'bad json','[]','{"v":0}', '{"v":1,"condition_id":"not-a-uuid"}', '{"v":1,"request_id":123}'):
        item=seed(pg);save(pg,item)
        with pg['connection'].cursor() as cursor:
            cursor.execute("""INSERT INTO tenant_004.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by)
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
    a,b=seed(pg),seed(pg)
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
        cursor.execute("UPDATE tenant_004.extraction_items SET raw_price='20' WHERE id=%s",(item['eid'],))
    with Session(pg['engine']) as db:
        result=analyzer.analyze_extraction_job(db,item['job'])
        assert result['skipped_product_corrections']==1
    assert context(pg,item)['needs_review'] is True
    save(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE tenant_004.analysis_results SET unit_canonical='Case' WHERE extraction_item_id=%s",(item['eid'],))
    assert context(pg,item)['needs_review'] is True


def test_product_category_changes_binding(pg):
    item=seed(pg);save(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE tenant_004.tcg_products SET product_category_id=NULL WHERE id=%s",(pg['product'],))
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
        cursor.execute("UPDATE tenant_004.conditions SET is_active=false WHERE code='CN0011'")
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
                        await second.execute(text("UPDATE tenant_004.source_messages SET raw_text='changed' WHERE id=CAST(:smid AS uuid)"),item)
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
        with pytest.raises(psycopg2.Error,match='incomplete TCG structure'): cursor.execute(script)
        cursor.execute('ROLLBACK')
        cursor.execute('SELECT count(*) FROM tenant_907.conditions')
        assert cursor.fetchone()[0]==0
        # An entirely absent TCG structure is the documented no-op, not partial success.
        cursor.execute(MIGRATION.read_text().replace('tenant_004','tenant_909'))
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='tenant_909'")
        assert cursor.fetchone()[0]==0


def test_product_correction_changes_binding_and_retains_manual_product(pg):
    item=seed(pg);save(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("INSERT INTO tenant_004.tcg_products(code,japanese_title,category_class,is_active) VALUES ('PM0901','Other product','Box',true) RETURNING id")
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
        assert str(db.execute(text("SELECT product_id FROM tenant_004.analysis_results WHERE extraction_item_id=CAST(:eid AS uuid)"),item).scalar_one())==other


def test_real_input_change_rejects_old_screen_without_writes(pg):
    item=seed(pg);payload=request(pg,item)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE tenant_004.extraction_items SET raw_price='20' WHERE id=%s",(item['eid'],))
    before=context(pg,item)
    with pytest.raises(HTTPException) as error:save(pg,item,payload)
    assert error.value.status_code==409
    assert context(pg,item)==before


def test_missing_empty_definition_holds(pg):
    item=seed(pg,condition_id=pg['normal'],condition_canonical='Sealed box',reasons='')
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE tenant_004.conditions SET code='CN0098' WHERE code='CN0011'")
    assert 'empty_box_master_unavailable' in context(pg,item)['review_reasons']
    assert output(pg)==[]


def test_quantity_and_price_binding_matches_storage_precision(pg):
    item=seed(pg)
    with pg['connection'].cursor() as cursor:
        cursor.execute("UPDATE tenant_004.extraction_items SET raw_quantity='2.345',raw_price='10.125' WHERE id=%s",(item['eid'],))
    with Session(pg['engine']) as db:
        analyzer.analyze_extraction_job(db,item['job'])
        numeric=db.execute(text("SELECT quantity_normalized::text,price_normalized::text FROM tenant_004.analysis_results WHERE extraction_item_id=CAST(:eid AS uuid)"),item).one()
        assert tuple(numeric)==('2.35','10.13')
    save(pg,item)
    binding=context(pg,item)['ack_binding_hash']
    with Session(pg['engine']) as db: analyzer.analyze_extraction_job(db,item['job'])
    after=context(pg,item)
    assert after['valid_ack'] is True and after['needs_review'] is False
    assert after['ack_binding_hash']==binding
