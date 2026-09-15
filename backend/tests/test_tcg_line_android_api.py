"""Android-only entry point: transport validation, authorization and shared review."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user, require_super_admin
from app.database import get_db
from app.routers import tcg_line_import as routes
from app.services.tcg_line_android_parser import AndroidExportError
from app.services.tcg_line_import_svc import import_line_export, sha256_text

EXPORT = '2026/9/12(土)\n12:00\t姓 名\t商品A\n\n末尾\n'
RESULT = dict(status='imported', review_status='pending_review', message_count=1,
              provider_count=0, unresolved_count=1, unresolved_display_names=['姓 名'],
              skipped_message_count=0, import_job_id='test-job')


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(routes.router, prefix='/api/v1')
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[require_super_admin] = lambda: SimpleNamespace(email='test@example.invalid')
    with TestClient(app) as client:
        yield client


def test_android_route_passes_explicit_format_and_full_window(client):
    with patch.object(routes, 'import_line_export', new_callable=AsyncMock, return_value=RESULT) as run:
        response = client.post('/api/v1/tcg/line-import/android', files={'file':('talk.txt',EXPORT,'text/plain')})
    assert response.status_code == 200
    assert response.json()['review_status'] == 'pending_review'
    assert run.call_args.kwargs['source_format'] == 'android'
    assert run.call_args.kwargs['window_hours'] == 0
    assert run.call_args.kwargs['export_text'] == EXPORT


@pytest.mark.parametrize('filename,content,expected', [
    ('talk.pdf', b'text', 400), ('talk.txt', b'\xff', 400),
    ('talk.txt', b'x' * (10 * 1024 * 1024 + 1), 413),
])
def test_invalid_upload_never_calls_service(client, filename, content, expected):
    with patch.object(routes, 'import_line_export', new_callable=AsyncMock) as run:
        response = client.post('/api/v1/tcg/line-import/android', files={'file':(filename,content)})
    assert response.status_code == expected
    run.assert_not_called()


def test_pc_format_on_android_route_is_a_client_error(client):
    with patch.object(routes, 'import_line_export', new_callable=AsyncMock, side_effect=AndroidExportError('bad')):
        response = client.post('/api/v1/tcg/line-import/android', files={'file':('talk.txt','PC text')})
    assert response.status_code == 400


def test_negative_window_rejected(client):
    with patch.object(routes, 'import_line_export', new_callable=AsyncMock) as run:
        response = client.post('/api/v1/tcg/line-import/android', data={'window_hours':-1}, files={'file':('talk.txt',EXPORT)})
    assert response.status_code == 422
    run.assert_not_called()


def test_non_super_admin_is_forbidden():
    app = FastAPI()
    app.include_router(routes.router, prefix='/api/v1')
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_super_admin=False)
    with TestClient(app) as client:
        response = client.post('/api/v1/tcg/line-import/android', files={'file':('talk.txt',EXPORT)})
    assert response.status_code == 403


async def test_invalid_android_export_does_not_touch_database():
    db = MagicMock(execute=AsyncMock())
    with pytest.raises(AndroidExportError):
        await import_line_export(db,'talk.txt','not a history',None,source_format='android')
    db.execute.assert_not_called()


async def test_android_duplicate_has_separate_identity_and_keeps_review_status():
    db = MagicMock()
    result = MagicMock()
    result.fetchone.return_value = ('prior-job','pending_review','pending_review')
    db.execute = AsyncMock(return_value=result)
    response = await import_line_export(db,'talk.txt',EXPORT,None,source_format='android')
    assert response['status'] == 'already_imported'
    assert response['review_status'] == 'pending_review'
    expected = sha256_text('line-android-v1\0' + EXPORT)
    assert db.execute.call_args_list[1].args[1]['sha256'] == expected


async def test_android_unresolved_sender_and_multiline_body_are_preserved():
    sqls = []
    captured = []
    async def execute(stmt, params=None):
        sqls.append(str(stmt))
        result = MagicMock()
        result.fetchone.return_value = None
        result.fetchall.return_value = []
        result.mappings.return_value.all.return_value = []
        if 'INSERT INTO' in str(stmt) and 'import_jobs' in str(stmt):
            captured.append(params)
        return result
    db = MagicMock(execute=execute, commit=AsyncMock())
    with patch('app.services.tcg_line_import_svc._enqueue_extraction') as enqueue:
        response = await import_line_export(db,'talk.txt',EXPORT,None,window_hours=0,source_format='android')
    assert response['review_status'] == 'pending_review'
    assert response['unresolved_display_names'] == ['姓 名']
    assert not any('source_messages' in sql and 'INSERT' in sql for sql in sqls)
    enqueue.assert_not_called()
    pending = json.loads(captured[0]['pending_messages'])
    assert pending[0]['display_name'] == '姓 名'
    assert pending[0]['body'] == '商品A\n\n末尾'
