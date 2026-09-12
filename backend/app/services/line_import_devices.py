"""Revocable opaque device keys, accepted only by the Android import router."""
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import text

from app.tcg_config import TCG_SCHEMA

SCOPE = 'line:import:android'
ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
KEY_RE = re.compile(r'^sali1_[A-Za-z0-9_-]{43}$')


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def key_digest(value: str) -> str:
    if not KEY_RE.fullmatch(value):
        raise HTTPException(401, 'device_unauthorized')
    return digest(value)


def code_digest(value: str) -> str:
    normalized = value.replace('-', '').replace(' ', '').upper()
    if len(normalized) != 8 or any(c not in ALPHABET for c in normalized):
        raise HTTPException(400, 'invalid_device_code')
    return digest(normalized)


def now():
    return datetime.now(timezone.utc)


async def start(db, token_hash: str, name: str, peer: str):
    # Serialize registration limits in PostgreSQL; no fail-open Redis dependency.
    await db.execute(text("SELECT pg_advisory_xact_lock(9182445)"))
    counts = (await db.execute(text('''SELECT count(*) AS total,
        count(*) FILTER (WHERE created_ip_hash = :ip) AS peer
        FROM public.line_import_devices WHERE created_at > now() - interval '1 hour' '''),
        {'ip': digest(peer)})).mappings().one()
    if counts['total'] >= 30 or counts['peer'] >= 10:
        raise HTTPException(429, 'device_registration_limited', headers={'Retry-After': '3600'})
    # Keep approved/revoked records; expired unapproved requests contain no grants.
    await db.execute(text('''DELETE FROM public.line_import_devices
        WHERE owner_user_id IS NULL AND pending_expires_at < now() - interval '1 day' '''))
    code = ''.join(secrets.choice(ALPHABET) for _ in range(8))
    identifier = uuid.uuid4()
    result = await db.execute(text('''INSERT INTO public.line_import_devices
        (id,token_hash,user_code_hash,name,tcg_schema,created_ip_hash,pending_expires_at)
        VALUES (:id,:token,:code,:name,:schema,:ip,:until)
        ON CONFLICT DO NOTHING RETURNING id'''),
        {'id': identifier, 'token': token_hash, 'code': code_digest(code),
         'name': name, 'schema': TCG_SCHEMA, 'ip': digest(peer),
         'until': now() + timedelta(minutes=10)})
    if result.scalar_one_or_none() is None:
        raise HTTPException(409, 'device_request_conflict')
    await db.commit()
    return {'user_code': code[:4] + '-' + code[4:],
            'verification_uri': 'https://app.salesanchor.jp/account/line-import-devices',
            'expires_in': 600, 'interval': 5}


async def approve(db, user, code: str):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:owner,0))"),
                     {'owner': f'line-device-owner:{user.id}'})
    active = (await db.execute(text('''SELECT count(*) FROM public.line_import_devices
        WHERE owner_user_id=:owner AND revoked_at IS NULL AND expires_at>now()'''), {'owner': user.id})).scalar_one()
    if active >= 20:
        raise HTTPException(409, 'device_limit_reached')
    row = (await db.execute(text('''UPDATE public.line_import_devices
        SET owner_user_id=:owner, approved_at=now(), expires_at=now()+interval '90 days'
        WHERE user_code_hash=:code AND owner_user_id IS NULL AND revoked_at IS NULL
          AND pending_expires_at>now() AND tcg_schema=:schema AND scope=:scope
        RETURNING id, name'''), {'owner': user.id, 'code': code_digest(code),
                               'schema': TCG_SCHEMA, 'scope': SCOPE})).mappings().first()
    if not row:
        raise HTTPException(400, 'invalid_or_used_device_code')
    await db.commit()
    return {'id': str(row['id']), 'name': row['name']}


async def lookup(db, token: str):
    return (await db.execute(text('''SELECT d.*, u.email, u.is_active AS user_active,
        u.is_super_admin, t.is_active AS tenant_active
        FROM public.line_import_devices d
        LEFT JOIN public.users u ON u.id=d.owner_user_id
        LEFT JOIN public.tenants t ON t.id=u.tenant_id
        WHERE d.token_hash=:hash'''), {'hash': key_digest(token)})).mappings().first()


def valid(row) -> bool:
    return bool(row and row['owner_user_id'] is not None and row['revoked_at'] is None
                and row['expires_at'] and row['expires_at'] > now()
                and row['scope'] == SCOPE and row['tcg_schema'] == TCG_SCHEMA
                and row['user_active'] and row['is_super_admin'] and row['tenant_active'])


async def status(db, token: str):
    row = await lookup(db, token)
    if row and row['owner_user_id'] is None and row['revoked_at'] is None and row['pending_expires_at'] > now():
        return {'status': 'pending'}
    if not valid(row):
        raise HTTPException(401, 'device_unauthorized')
    return {'status': 'approved'}


async def authenticate(db, token: str):
    row = await lookup(db, token)
    if not valid(row):
        raise HTTPException(401, 'device_unauthorized')
    return SimpleNamespace(id=row['owner_user_id'], email=row['email'], device_id=row['id'])


async def used(db, identifier):
    await db.execute(text('''UPDATE public.line_import_devices SET last_used_at=now(),
        expires_at=now()+interval '90 days' WHERE id=:id AND revoked_at IS NULL'''), {'id': identifier})
    await db.commit()


async def list_devices(db, user):
    rows = (await db.execute(text('''SELECT id,name,approved_at,expires_at,last_used_at,revoked_at
        FROM public.line_import_devices WHERE owner_user_id=:owner
        ORDER BY (revoked_at IS NULL AND expires_at>now()) DESC, approved_at DESC LIMIT 100'''), {'owner': user.id})).mappings().all()
    return [dict(row) for row in rows]


async def revoke(db, user, identifier):
    result = await db.execute(text('''UPDATE public.line_import_devices SET revoked_at=now()
        WHERE id=:id AND owner_user_id=:owner RETURNING id'''), {'id': identifier, 'owner': user.id})
    if result.scalar_one_or_none() is None:
        raise HTTPException(404, 'device_not_found')
    await db.commit()
