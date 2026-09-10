"""Real PostgreSQL contract tests; only an explicitly named disposable test database."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg2
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.routers import tcg_line_import as routes
from app.services import tcg_import_progress as progress
from app.services import tcg_line_import_svc as svc

URL = os.getenv("PMG_TEST_PG_URL") or os.getenv("RLS_ADMIN_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="PMG_TEST_PG_URL must identify a disposable test database")
SCHEMA = "tenant_871"


def provision_tcg(cursor,schema):
    # Execute canonical migrations, changing only the isolated test schema target.
    migrations=Path(__file__).resolve().parents[2]/"migrations"
    for name in ("20260831_110000_create_tcg_analysis_tables_t004.sql",
                 "20260905_140000_import_jobs_review_stage_t004.sql"):
        cursor.execute((migrations/name).read_text().replace("tenant_004",schema))


@pytest_asyncio.fixture
async def pg(monkeypatch):
    url = make_url(URL)
    assert url.database in ("pmg_import_ssot_test", "jarvis_test_db"), "Refuse non-disposable database"
    assert url.host in ("127.0.0.1", "localhost"), "Local test database only"
    conn = psycopg2.connect(host=url.host, port=url.port, dbname=url.database, user=url.username, password=url.password)
    conn.autocommit = True
    with conn.cursor() as c:
        # These schemas belong only to this per-task disposable database.
        c.execute("DROP SCHEMA IF EXISTS tenant_871 CASCADE; DROP SCHEMA IF EXISTS tenant_872 CASCADE")
        c.execute("CREATE SCHEMA tenant_871; CREATE SCHEMA tenant_872")
        for schema in (SCHEMA, "tenant_872"):
            provision_tcg(c,schema)
            c.execute(f"INSERT INTO {schema}.tcg_suppliers(id,code,name,is_active) VALUES ('00000000-0000-0000-0000-000000000001','SP1','Alice',true)")
            c.execute(f"INSERT INTO {schema}.supplier_channels(id,supplier_id,channel,is_active) VALUES ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','line',true)")
        migration=Path(__file__).resolve().parents[2]/"migrations/20260910_010000_tcg_import_message_links.sql"
        c.execute(migration.read_text())
        c.execute(migration.read_text())
    for module in (svc, routes, progress):
        monkeypatch.setattr(module, "TCG_SCHEMA", SCHEMA)
    enqueue=MagicMock()
    monkeypatch.setattr(svc,"_enqueue_extraction",enqueue)
    monkeypatch.setattr(routes,"_enqueue_extraction",enqueue)
    engine=create_async_engine(URL)
    yield engine, conn, enqueue
    await engine.dispose()
    with conn.cursor() as c:
        c.execute("DROP SCHEMA tenant_871 CASCADE; DROP SCHEMA tenant_872 CASCADE")
    conn.close()


async def upload(engine, content):
    async with AsyncSession(engine) as db:
        return await svc.import_line_export(db,"test.txt",content,None,window_hours=0)


def export(body="stock", day="10", header="", sender="Alice", hour="10:00"):
    return f"{header}\n2026.09.{day} Thursday\n{hour} {sender} {body}\n"


def count(conn, table):
    with conn.cursor() as c:
        c.execute(f"SELECT count(*) FROM {SCHEMA}.{table}")
        return c.fetchone()[0]


async def test_reuse_distinct_file_and_new_date_body(pg):
    engine,conn,enqueue=pg
    a=await upload(engine,export())
    b=await upload(engine,export(header="new export"))
    assert a["import_job_id"] != b["import_job_id"]
    assert count(conn,"source_messages")==1
    assert count(conn,"import_job_messages")==2
    assert enqueue.call_count==1
    assert (await upload(engine,export()))["import_job_id"]==a["import_job_id"]
    await upload(engine,export(day="11"))
    await upload(engine,export(body="different"))
    assert count(conn,"source_messages")==3
    async with AsyncSession(engine) as db:
        r=await progress.read_progress(db,b["import_job_id"])
        assert r["messages"]["reused"]==1
        assert r["messages"]["inactive"]==1  # No revival when reusing historical data.


async def test_actual_timestamp_is_latest_and_legacy_not_inferred(pg):
    engine,conn,_=pg
    await upload(engine,export(body="early")+"15:00 Alice latest\n")
    with conn.cursor() as c:
        c.execute(f"SELECT received_at, line_posted_at FROM {SCHEMA}.source_messages")
        received,posted=c.fetchone()
        assert (posted-received).total_seconds()==5*3600
        c.execute(f"UPDATE {SCHEMA}.source_messages SET line_posted_at=NULL")
    await upload(engine,export(body="latest",hour="15:00"))
    assert count(conn,"source_messages")==2


async def test_concurrent_file_and_post_retries(pg):
    engine,conn,enqueue=pg
    a,b=await asyncio.gather(upload(engine,export(header="a")),upload(engine,export(header="b")))
    assert a["import_job_id"]!=b["import_job_id"]
    c,d=await asyncio.gather(upload(engine,export()),upload(engine,export()))
    assert c["import_job_id"]==d["import_job_id"]
    assert count(conn,"import_jobs")==3
    assert count(conn,"source_messages")==1
    assert count(conn,"extraction_jobs")==1
    assert count(conn,"import_job_messages")==3
    assert enqueue.call_count==1


async def test_pending_commit_and_concurrent_commit(pg):
    engine,conn,enqueue=pg
    job=await upload(engine,export(sender="Bob"))
    duplicate=await upload(engine,export(sender="Bob"))
    assert duplicate["review_status"]=="pending_review"
    assert count(conn,"source_messages")==0
    with conn.cursor() as c:
        c.execute(f"UPDATE {SCHEMA}.tcg_suppliers SET name='Bob'")
    async def commit():
        async with AsyncSession(engine) as db:
            try:
                return await routes.commit_pending_job(job["import_job_id"],db)
            except HTTPException as e:
                return e.status_code
    result=await asyncio.gather(commit(),commit())
    assert sum(x==409 for x in result)==1
    assert count(conn,"source_messages")==1
    assert count(conn,"import_job_messages")==1
    assert enqueue.call_count==1


async def test_rollback_no_partial_import_or_enqueue(pg,monkeypatch):
    engine,conn,enqueue=pg
    original=svc._link_message
    async def fail(*args):
        await original(*args)
        raise RuntimeError("injected after link")
    monkeypatch.setattr(svc,"_link_message",fail)
    with pytest.raises(RuntimeError,match="injected"):
        await upload(engine,export())
    for table in ("import_jobs","source_messages","extraction_jobs","import_job_messages"):
        assert count(conn,table)==0
    enqueue.assert_not_called()


async def test_constraints_and_cross_schema_fk(pg):
    engine,conn,_=pg
    a=await upload(engine,export())
    with conn.cursor() as c:
        c.execute(f"SELECT id FROM {SCHEMA}.source_messages")
        message=str(c.fetchone()[0])
        other=str(uuid4())
        c.execute("INSERT INTO tenant_872.import_jobs(id,filename,raw_sha256) VALUES (%s,'test','foreign')",(other,))
        c.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema IN ('tenant_871','tenant_872') AND column_name IN ('messages_linked_at','line_posted_at')")
        assert c.fetchone()[0]==4
    for jid,mid,kind in ((other,message,"created"),(a["import_job_id"],message,"invalid"),(a["import_job_id"],message,"created")):
        async with AsyncSession(engine) as db:
            with pytest.raises(IntegrityError):
                await db.execute(text(f"INSERT INTO {SCHEMA}.import_job_messages VALUES (:j,:m,:k,now())"),{"j":jid,"m":mid,"k":kind})


async def test_unknown_zero_pending_and_foreign_id(pg):
    engine,conn,_=pg
    zero=await upload(engine,"empty file")
    pending=await upload(engine,export(sender="Unknown"))
    legacy=str(uuid4())
    foreign=str(uuid4())
    with conn.cursor() as c:
        c.execute(f"INSERT INTO {SCHEMA}.import_jobs(id,review_status,filename,raw_sha256) VALUES (%s,'ok','test','legacy')",(legacy,))
        c.execute("INSERT INTO tenant_872.import_jobs(id,review_status,filename,raw_sha256) VALUES (%s,'ok','test','legacy')",(foreign,))
    async with AsyncSession(engine) as db:
        z=await progress.read_progress(db,zero["import_job_id"])
        assert z["coverage"]=="complete" and z["messages"]["total"]==0
        for jid,coverage in ((legacy,"legacy_unknown"),(pending["import_job_id"],"pending_review")):
            r=await progress.read_progress(db,jid)
            assert r["coverage"]==coverage and r["extraction"]["total"] is None
            page=await progress.read_items(db,jid,50,0,"all")
            assert page["total"] is None and page["items"] is None
        with pytest.raises(HTTPException) as e:
            await progress.read_progress(db,foreign)
        assert e.value.status_code==404


async def test_errors_results_reasons_and_pagination(pg):
    engine,conn,_=pg
    job=await upload(engine,export())
    with conn.cursor() as c:
        c.execute(f"UPDATE {SCHEMA}.extraction_jobs SET status='error' RETURNING id,source_message_id")
        first,message=c.fetchone()
        jobs=[first]
        for _ in range(56):
            jid=str(uuid4()); jobs.append(jid)
            c.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'error')",(jid,str(message)))
        for i in range(166):
            item=str(uuid4())
            c.execute(f"INSERT INTO {SCHEMA}.extraction_items(id,extraction_job_id,raw_product_name) VALUES (%s,%s,'card')",(item,str(jobs[i%57])))
            c.execute(f"INSERT INTO {SCHEMA}.analysis_results(id,extraction_item_id,note_ja,needs_review,review_reasons,pid_resolved,unit_resolved,engine_version) VALUES (%s,%s,'予約 9/20',%s,%s,false,false,'test')",(str(uuid4()),item,i==0,'reason_a,reason_b' if i==0 else None))
    async with AsyncSession(engine) as db:
        r=await progress.read_progress(db,job["import_job_id"])
        assert r["extraction"]["failed"]==57
        assert r["extraction"]["succeeded"]==0
        assert r["extraction"]["residual_results_on_error"]==166
        assert r["analysis"]["needs_review"]==1
        assert r["analysis"]["review_reasons"]=={"reason_a":1,"reason_b":1}
        assert r["analysis"]["succeeded"] is None
        a=await progress.read_items(db,job["import_job_id"],100,0,"all")
        b=await progress.read_items(db,job["import_job_id"],100,100,"all")
        assert (a["total"],len(a["items"]),len(b["items"]))==(166,100,66)
        assert len({x["id"] for x in a["items"]+b["items"]})==166
        assert a["items"][0]["note_ja"]=="予約 9/20"
        review=await progress.read_items(db,job["import_job_id"],50,0,"needs_review")
        assert review["total"]==1
        empty=await progress.read_items(db,job["import_job_id"],50,200,"all")
        assert empty["total"]==166 and empty["items"]==[]


async def test_api_auth_validation_and_db_errors(pg):
    engine,_,_=pg
    app=FastAPI(); app.include_router(routes.router)
    async def db():
        async with AsyncSession(engine) as session:
            yield session
    app.dependency_overrides[get_db]=db
    app.dependency_overrides[get_current_user]=lambda: SimpleNamespace(is_super_admin=False)
    path=f"/tcg/line-import/{uuid4()}"
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as client:
        assert (await client.get(path+"/progress")).status_code==403
        app.dependency_overrides[get_current_user]=lambda: SimpleNamespace(is_super_admin=True)
        assert (await client.get(path+"/items?limit=101")).status_code==422
        assert (await client.get(path+"/items?offset=-1")).status_code==422
        assert (await client.get(path+"/items?filter=bad")).status_code==422
        assert (await client.get(path+"/progress")).status_code==404
    # A database failure propagates; no manufactured zero-count response.
    class Broken:
        async def execute(self,*args,**kwargs):
            raise RuntimeError("unavailable")
    with pytest.raises(RuntimeError,match="unavailable"):
        await progress.read_progress(Broken(),str(uuid4()))


async def test_pending_rollback_retains_pending_payload(pg,monkeypatch):
    engine,conn,enqueue=pg
    job=await upload(engine,export(sender="Bob"))
    with conn.cursor() as c:
        c.execute(f"UPDATE {SCHEMA}.tcg_suppliers SET name='Bob'")
    original=svc._link_message
    async def fail(*args):
        await original(*args)
        raise RuntimeError("injected pending link")
    monkeypatch.setattr(svc,"_link_message",fail)
    async with AsyncSession(engine) as db:
        with pytest.raises(RuntimeError):
            await routes.commit_pending_job(job["import_job_id"],db)
        await db.rollback()
    assert count(conn,"source_messages")==0 and count(conn,"import_job_messages")==0
    with conn.cursor() as c:
        c.execute(f"SELECT review_status,pending_messages,messages_linked_at FROM {SCHEMA}.import_jobs")
        state,payload,linked=c.fetchone()
        assert state=="pending_review" and payload and linked is None
    enqueue.assert_not_called()


async def test_link_retry_preserves_created_and_enqueue_sees_commit(pg,monkeypatch):
    engine,conn,_=pg
    def queue(message_id):
        with conn.cursor() as c:
            c.execute(f"SELECT count(*) FROM {SCHEMA}.import_job_messages WHERE source_message_id=%s",(message_id,))
            assert c.fetchone()[0]==1
    monkeypatch.setattr(svc,"_enqueue_extraction",queue)
    job=await upload(engine,export())
    with conn.cursor() as c:
        c.execute(f"SELECT id FROM {SCHEMA}.source_messages")
        message=str(c.fetchone()[0])
    async with AsyncSession(engine) as db:
        await svc._link_message(db,job["import_job_id"],message,"reused")
        await db.commit()
        r=await progress.read_progress(db,job["import_job_id"])
        assert r["messages"]["created"]==1 and r["messages"]["reused"]==0


async def test_different_supplier_does_not_reuse_and_missing_channel_rolls_back(pg):
    engine,conn,_=pg
    await upload(engine,export())
    with conn.cursor() as c:
        c.execute(f"INSERT INTO {SCHEMA}.tcg_suppliers(id,code,name,is_active) VALUES (%s,'SP2','Bob',true)",('00000000-0000-0000-0000-000000000003',))
    with pytest.raises(ValueError,match="no active LINE channel"):
        await upload(engine,export(sender="Bob"))
    assert count(conn,"import_jobs")==1
    with conn.cursor() as c:
        c.execute(f"INSERT INTO {SCHEMA}.supplier_channels(id,supplier_id,channel,is_active) VALUES (%s,%s,'line',true)",('00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000003'))
    await upload(engine,export(sender="Bob"))
    assert count(conn,"source_messages")==2


async def test_later_tcg_schema_provisioning(pg):
    _,conn,_=pg
    migration=Path(__file__).resolve().parents[2]/"migrations/20260910_010000_tcg_import_message_links.sql"
    with conn.cursor() as c:
        c.execute("CREATE SCHEMA tenant_873")
        provision_tcg(c,"tenant_873")
        try:
            c.execute(migration.read_text())
            c.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema='tenant_873' AND column_name IN ('messages_linked_at','line_posted_at')")
            assert c.fetchone()[0]==2
            c.execute("SELECT count(*) FROM pg_constraint WHERE conrelid='tenant_873.import_job_messages'::regclass AND contype='f'")
            assert c.fetchone()[0]==2
        finally:
            c.execute("DROP SCHEMA tenant_873 CASCADE")


async def test_pending_confirmation_reuses_existing_post(pg):
    engine,conn,enqueue=pg
    await upload(engine,export())
    pending=await upload(engine,export(sender="Bob"))
    with conn.cursor() as c:
        c.execute(f"UPDATE {SCHEMA}.tcg_suppliers SET name='Bob'")
    async with AsyncSession(engine) as db:
        result=await routes.commit_pending_job(pending["import_job_id"],db)
        assert result.enqueued_count==0
        r=await progress.read_progress(db,pending["import_job_id"])
        assert r["coverage"]=="complete" and r["messages"]["reused"]==1
    assert count(conn,"source_messages")==1 and count(conn,"import_job_messages")==2
    assert enqueue.call_count==1
