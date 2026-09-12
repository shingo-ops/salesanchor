"""Scoped manual provisioning over the existing authorized VPS maintenance channel.

Receives only {action, user_email, user_code|device_id} on stdin. Never receives
an API key, password or Firebase token. No arbitrary SQL/command execution.
"""
import asyncio
import json
import sys
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.services import line_import_devices as service


async def run(data):
    if data.get('action') not in ('approve', 'revoke'):
        raise ValueError('unsupported action')
    email = data.get('user_email', '')
    if not isinstance(email, str) or not 3 <= len(email) <= 254:
        raise ValueError('invalid account')
    async with AsyncSessionLocal() as db:
        user = (await db.execute(text('''SELECT u.id,u.email FROM public.users u
            JOIN public.tenants t ON t.id=u.tenant_id
            WHERE lower(u.email)=lower(:email) AND u.is_active IS TRUE
              AND u.is_super_admin IS TRUE AND t.is_active IS TRUE'''),
            {'email': email})).mappings().one_or_none()
        if user is None:
            raise ValueError('active super-admin account required')
        owner = SimpleNamespace(**dict(user))
        if data['action'] == 'approve':
            result = await service.approve(db, owner, data.get('user_code', ''))
            return {'status': 'approved', 'device_id': result['id'], 'scope': service.SCOPE}
        identifier = UUID(data.get('device_id', ''))
        await service.revoke(db, owner, identifier)
        return {'status': 'revoked', 'device_id': str(identifier)}


if __name__ == '__main__':
    try:
        payload = json.loads(sys.stdin.read(2048))
        print(json.dumps(asyncio.run(run(payload))))
    except Exception:
        # No traceback or reflected request fields in public CI logs.
        print('Device operation failed. Check account, code expiry and deployment.', file=sys.stderr)
        raise SystemExit(1) from None
