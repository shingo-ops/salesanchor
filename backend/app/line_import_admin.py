"""Fixed maintenance operations; no device key or arbitrary SQL is accepted."""
import asyncio
import base64
import os
import hashlib
import json
import logging
import sys
from uuid import UUID

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.routers.tcg_line_import import ResolveRequest, commit_pending_job, resolve_supplier
from app.services import line_import_devices as devices
from app.services import tcg_distribution_svc as distribution
from app.services.tcg_import_progress import read_progress
from app.tcg_config import TCG_SCHEMA


def name_hash(name):
    return hashlib.sha256(name.encode('utf-8')).hexdigest()


def validate(data):
    if not isinstance(data, dict) or data.get('action') not in ('inspect', 'create', 'commit', 'distribute'):
        raise ValueError('invalid action')
    if set(data) - {'action', 'device_id', 'import_job_id', 'name_hash', 'target_id', 'confirm', 'report_public_key'}:
        raise ValueError('unexpected fields')
    for key in ('device_id', 'import_job_id'):
        data[key] = str(UUID(data[key]))
    if data['action'] == 'create':
        value = data.get('name_hash', '')
        if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('invalid name hash')
    if data['action'] == 'distribute':
        data['target_id'] = str(UUID(data['target_id']))
        if data.get('confirm') != 'existing-global-inventory-to-selected-target':
            raise ValueError('explicit distribution scope required')
    if 'report_public_key' in data:
        if data['action'] != 'inspect':
            raise ValueError('private report is inspect-only')
        report_key(data['report_public_key'])
    return data


def report_key(pem):
    if not isinstance(pem, str) or len(pem) > 1200:
        raise ValueError('invalid public key')
    key = serialization.load_pem_public_key(pem.encode('ascii'))
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size != 4096:
        raise ValueError('RSA 4096 public key required')
    return key


def seal_report(data, pem):
    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    body = AESGCM(key).encrypt(nonce, json.dumps(data, ensure_ascii=False, default=str).encode(), b'line-import-report-v1')
    wrapped = report_key(pem).encrypt(key, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return {k: base64.b64encode(v).decode('ascii') for k, v in {'key': wrapped, 'nonce': nonce, 'body': body}.items()}


def ready_for_delivery(progress):
    if progress.get('coverage') != 'complete' or progress.get('review_status') != 'ok':
        return False
    messages, extraction, analysis = (progress.get(k, {}) for k in ('messages', 'extraction', 'analysis'))
    if not messages.get('total') or messages.get('inactive', 1) != 0 or messages.get('without_extraction_job', 1) != 0:
        return False
    if not extraction.get('total') or not analysis.get('total'):
        return False
    if any(extraction.get(k, 1) != 0 for k in ('pending', 'running', 'unknown', 'failed')):
        return False
    return analysis.get('results_missing') == 0 and analysis.get('needs_review') == 0


async def authorize(db, data):
    # This CLI is reachable only via the authorized SSH maintenance workflow.
    row = (await db.execute(text('''SELECT d.owner_user_id,d.revoked_at,d.expires_at,
        d.scope,d.tcg_schema,u.is_active AS user_active,u.is_super_admin,
        t.is_active AS tenant_active,u.email
        FROM public.line_import_devices d JOIN public.users u ON u.id=d.owner_user_id
        JOIN public.tenants t ON t.id=u.tenant_id WHERE d.id=:id'''),
        {'id': data['device_id']})).mappings().one_or_none()
    if row is None or not devices.valid(row):
        raise ValueError('active import device owner required')
    job = (await db.execute(text(f'''SELECT id,uploaded_by,review_status,unresolved_names,
        message_count,created_at FROM {TCG_SCHEMA}.import_jobs WHERE id=:id'''),
        {'id': data['import_job_id']})).mappings().one_or_none()
    if job is None or job['uploaded_by'] not in (row['email'], str(row['owner_user_id'])):
        raise ValueError('import owner mismatch')
    return job


async def operate(db, data):
    job = await authorize(db, data)
    names = job['unresolved_names'] or []
    if isinstance(names, str):
        names = json.loads(names)
    action, job_id = data['action'], data['import_job_id']
    if action == 'inspect':
        progress = await read_progress(db, job_id)
        targets = await distribution.list_targets(db)
        settings = await distribution.load_distribution_settings(db)
        rows = await distribution.fetch_output_rows(db, include_flag_single=settings.get('include_flag_single', 'false').lower() == 'true')
        private = None
        if data.get('report_public_key'):
            suppliers = (await db.execute(text(f'SELECT code,name,is_active FROM {TCG_SCHEMA}.tcg_suppliers ORDER BY code'))).mappings().all()
            private = seal_report({'unresolved_names': names, 'suppliers': [dict(r) for r in suppliers],
                                   'targets': [{k: t[k] for k in ('id', 'name', 'spreadsheet_id', 'sheet_name', 'is_active')} for t in targets]}, data['report_public_key'])
        return {'status': 'inspected', 'private_report': private, 'job_id': job_id, 'progress': progress,
                'unresolved_name_hashes': [name_hash(n) for n in names],
                'message_count': job['message_count'], 'distribution_scope': 'global_inventory',
                'output_count': len(rows), 'ready_for_delivery': ready_for_delivery(progress),
                'targets': [{'id': str(t['id']), 'active': t['is_active'],
                             'last_distributed_at': str(t['last_distributed_at']),
                             'last_distributed_count': t['last_distributed_count'],
                             'last_result_ok': t['last_result'] == 'ok'} for t in targets]}
    if action == 'create':
        matching = [n for n in names if name_hash(n) == data['name_hash']]
        if len(matching) != 1 or job['review_status'] != 'pending_review':
            raise ValueError('pending name not uniquely identified')
        # Serialize code allocation against other maintenance operations and API INSERT/UPDATE.
        await db.execute(text(f'LOCK TABLE {TCG_SCHEMA}.tcg_suppliers IN SHARE ROW EXCLUSIVE MODE'))
        existing = (await db.execute(text(f'SELECT count(*) FROM {TCG_SCHEMA}.tcg_suppliers WHERE name=:name'),
                                    {'name': matching[0]})).scalar_one()
        if existing:
            raise ValueError('supplier already exists; inspect and commit instead')
        result = await resolve_supplier(job_id, ResolveRequest(display_name=matching[0], action='create'), db)
        return {'status': 'created', 'remaining_count': len(result.remaining_unresolved)}
    if action == 'commit':
        result = await commit_pending_job(job_id, db)
        return result.model_dump()
    progress = await read_progress(db, job_id)
    if not ready_for_delivery(progress):
        raise ValueError('import review/extraction/analysis is not ready')
    result = await distribution.run_distribution(db, target_id=data['target_id'])
    # Never reflect target names, raw exception strings or URLs into public logs.
    return {'status': 'distributed' if result.get('results') and not result.get('errors') else 'not_confirmed',
            'output_count': result['output_count'], 'error_count': len(result.get('errors', [])),
            'results': [{k: r[k] for k in ('target_id', 'status', 'rows_written')} for r in result.get('results', [])]}


async def run(data):
    data = validate(data)
    async with AsyncSessionLocal() as db:
        if data['action'] == 'inspect':
            await db.execute(text('SET TRANSACTION READ ONLY'))
        return await operate(db, data)


if __name__ == '__main__':
    # Existing services log supplier names/errors; keep this public CI transport sanitized.
    logging.disable(logging.CRITICAL)
    try:
        result = asyncio.run(run(json.loads(sys.stdin.read(4097))))
        print(json.dumps(result, default=str))
        if result.get('status') == 'not_confirmed':
            raise SystemExit(1)
    except Exception:
        print('Import operation stopped; inspect state before any retry.', file=sys.stderr)
        raise SystemExit(1) from None
