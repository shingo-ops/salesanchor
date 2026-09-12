"""Migration and device lifecycle checks in a disposable CI PostgreSQL database."""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit
import uuid

import asyncpg
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from app.models import Tenant, User

from app.services import line_import_devices as svc

ADMIN = os.getenv('RLS_ADMIN_DATABASE_URL', '')
APP = os.getenv('RLS_TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not ADMIN or not APP, reason='Requires CI PostgreSQL')


@pytest_asyncio.fixture
async def pg():
    admin = urlsplit(ADMIN.replace('postgresql+asyncpg://','postgresql://'))
    assert admin.hostname in ('localhost', '127.0.0.1'), 'local test PostgreSQL only'
    name = 'line_device_test_' + uuid.uuid4().hex
    control = await asyncpg.connect(urlunsplit(admin))
    await control.execute(f'CREATE DATABASE {name}')
    app_url = urlsplit(APP)
    engine = owner = None
    try:
        owner = await asyncpg.connect(urlunsplit(admin._replace(path='/'+name)))
        for model in (Tenant, User):
            await owner.execute(str(CreateTable(model.__table__).compile(dialect=postgresql.dialect())))
        await owner.execute("INSERT INTO public.tenants (id,tenant_name,tenant_code,is_active) VALUES (1,'Device test','device-test',true)")
        await owner.execute("INSERT INTO public.users (id,username,email,tenant_id,is_active,is_super_admin) VALUES (1,'device-test','test@example.invalid',1,true,true)")
        await owner.execute('GRANT SELECT ON public.tenants,public.users TO salesanchor_app')
        migration = (Path(__file__).resolve().parents[2]/'migrations/20260912_160000_line_import_devices.sql').read_text()
        await owner.execute(migration)
        await owner.execute(migration)
        columns = await owner.fetch("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='line_import_devices'")
        assert {'token_hash','owner_user_id','revoked_at','expires_at'} <= {r[0] for r in columns}
        assert 'token' not in {r[0] for r in columns}
        engine = create_async_engine(urlunsplit(app_url._replace(path='/'+name)), echo=False)
        yield async_sessionmaker(engine, expire_on_commit=False), owner
    finally:
        if engine: await engine.dispose()
        if owner: await owner.close()
        await control.execute(f'DROP DATABASE {name}')
        await control.close()


async def test_complete_device_lifecycle_and_revocation(pg):
    sessions, owner = pg
    token = 'sali1_' + 'a' * 43
    user = SimpleNamespace(id=1, email='test@example.invalid')
    async with sessions() as db:
        started = await svc.start(db, svc.digest(token), 'phone', 'local-test')
        assert started['scope'] == svc.SCOPE
        assert 'verification_uri' not in started
        assert (await svc.status(db, token))['status'] == 'pending'
        with pytest.raises(HTTPException): await svc.authenticate(db, token)
        approved = await svc.approve(db, user, started['user_code'])
        assert (await svc.status(db, token))['status'] == 'approved'
        verified = await svc.authenticate(db, token)
        assert verified.id == 1
        await svc.used(db, verified.device_id)
        items = await svc.list_devices(db, user)
        assert items[0]['last_used_at'] is not None
        assert 'token_hash' not in items[0]
        await owner.execute('UPDATE public.users SET is_super_admin=false WHERE id=1')
        with pytest.raises(HTTPException): await svc.authenticate(db, token)
        await owner.execute('UPDATE public.users SET is_super_admin=true WHERE id=1')
        await svc.revoke(db, user, uuid.UUID(approved['id']))
        with pytest.raises(HTTPException): await svc.authenticate(db, token)
        with pytest.raises(HTTPException): await svc.status(db, token)


async def test_approval_is_single_use_even_concurrently(pg):
    sessions, _ = pg
    async with sessions() as db:
        started = await svc.start(db, svc.digest('sali1_'+'b'*43), 'phone', 'local-test')
    async def approve():
        async with sessions() as db:
            try:
                await svc.approve(db, SimpleNamespace(id=1), started['user_code'])
                return 'approved'
            except HTTPException:
                await db.rollback()
                return 'rejected'
    assert sorted(await asyncio.gather(approve(), approve())) == ['approved','rejected']


async def test_expiry_and_wrong_owner_cannot_be_bypassed(pg):
    sessions, owner = pg
    token = 'sali1_'+'c'*43
    async with sessions() as db:
        started = await svc.start(db, svc.digest(token), 'phone', 'local-test')
        await owner.execute("UPDATE public.line_import_devices SET pending_expires_at=now()-interval '1 second'")
        with pytest.raises(HTTPException): await svc.approve(db, SimpleNamespace(id=1), started['user_code'])
        await db.rollback()
        await owner.execute("UPDATE public.line_import_devices SET pending_expires_at=now()+interval '10 minutes'")
        approved = await svc.approve(db, SimpleNamespace(id=1), started['user_code'])
        with pytest.raises(HTTPException): await svc.revoke(db, SimpleNamespace(id=2), uuid.UUID(approved['id']))
        await db.rollback()
        await owner.execute("UPDATE public.line_import_devices SET expires_at=now()-interval '1 second'")
        with pytest.raises(HTTPException): await svc.authenticate(db, token)


async def test_registration_rate_limit_is_database_enforced(pg):
    sessions, _ = pg
    async with sessions() as db:
        for n in range(10):
            await svc.start(db, svc.digest(f'unique-hash-{n}'), 'phone', 'same-peer')
        with pytest.raises(HTTPException) as error:
            await svc.start(db, svc.digest('over-limit'), 'phone', 'same-peer')
        assert error.value.status_code == 429
