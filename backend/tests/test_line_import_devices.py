from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.routers import line_import_devices as routes
from app.services import line_import_devices as svc

TOKEN = 'sali1_' + 'a' * 43


def row(**changes):
    value = dict(owner_user_id=1, revoked_at=None, expires_at=svc.now()+timedelta(days=1),
                 scope=svc.SCOPE, tcg_schema=svc.TCG_SCHEMA, user_active=True,
                 is_super_admin=True, tenant_active=True)
    value.update(changes)
    return value


@pytest.mark.parametrize('field,value', [('owner_user_id', None), ('revoked_at', svc.now()),
    ('expires_at', svc.now()-timedelta(seconds=1)), ('scope', 'other'), ('tcg_schema','tenant_999'),
    ('user_active',False), ('is_super_admin',False), ('tenant_active',False)])
def test_invalid_grants_denied(field, value):
    assert not svc.valid(row(**{field:value}))


def test_key_and_code_validation():
    assert svc.valid(row())
    assert svc.code_digest('ABCD-EFGH') == svc.code_digest('abcd efgh')
    assert svc.key_digest(TOKEN) == svc.digest(TOKEN)
    for bad in ['firebase-token', 'sali1_short', TOKEN+'\n']:
        with pytest.raises(HTTPException): svc.key_digest(bad)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(routes.router, prefix='/api/v1')
    app.dependency_overrides[get_db] = lambda: MagicMock()
    with TestClient(app) as client:
        yield client, app


def test_device_token_does_not_grant_approval(client):
    cli, _ = client
    # Fake Firebase token is rejected before the approval service can be called.
    with patch('app.auth.dependencies._init_firebase'), patch('app.auth.dependencies.is_token_blacklisted', new=AsyncMock(return_value=False)), patch('app.auth.dependencies.get_cached_jwt', new=AsyncMock(return_value=None)), patch('app.auth.dependencies.check_auth_rate_limit', new=AsyncMock(return_value=False)), patch('app.auth.dependencies.record_auth_failure', new=AsyncMock()), patch('app.auth.dependencies.firebase_auth.verify_id_token', side_effect=ValueError('invalid')), patch.object(svc,'approve',new_callable=AsyncMock) as approve:
        result = cli.post('/api/v1/tcg/line-devices/approve', headers={'Authorization':'Bearer '+TOKEN}, json={'user_code':'ABCD-EFGH'})
    assert result.status_code == 401
    approve.assert_not_called()


def test_approval_requires_existing_firebase_admin(client):
    cli, app = client
    app.dependency_overrides[require_super_admin] = lambda: SimpleNamespace(id=1)
    with patch.object(svc, 'approve', new=AsyncMock(return_value={'id':'example'})) as approve:
        result = cli.post('/api/v1/tcg/line-devices/approve', json={'user_code':'ABCD-EFGH'})
    assert result.status_code == 200
    assert result.headers['cache-control'] == 'no-store'
    assert approve.call_args.args[1].id == 1


def test_upload_requires_valid_device_and_preserves_raw_text(client):
    cli, app = client
    app.dependency_overrides[routes.device_user] = lambda: SimpleNamespace(id=1, email='test@example.invalid', device_id='device')
    answer = {'status':'imported','review_status':'ok','message_count':1,'provider_count':1,'unresolved_count':0,'unresolved_display_names':[],'skipped_message_count':0,'import_job_id':'job'}
    with patch.object(routes,'upload_android_line_export',new=AsyncMock(return_value=answer)) as upload, patch.object(svc,'used',new=AsyncMock()) as used:
        result = cli.post('/api/v1/tcg/line-devices/import', files={'file':('talk.txt','2026/9/12(土)\n12:00\tA\tbody')})
    assert result.status_code == 200
    assert upload.call_args.kwargs['window_hours'] == 0
    assert upload.call_args.kwargs['current_user'].id == 1
    used.assert_awaited_once()


async def test_pending_key_cannot_authenticate():
    with patch.object(svc, 'lookup', new=AsyncMock(return_value=row(owner_user_id=None))):
        with pytest.raises(HTTPException) as error:
            await svc.authenticate(MagicMock(), TOKEN)
    assert error.value.status_code == 401
