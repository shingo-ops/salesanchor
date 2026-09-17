from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app import line_import_admin as admin


def payload(action='inspect', **extra):
    return {'action': action, 'device_id': str(uuid4()), 'import_job_id': str(uuid4()), **extra}


def ready():
    return {'coverage': 'complete', 'review_status': 'ok',
            'messages': {'total': 1, 'inactive': 0, 'without_extraction_job': 0},
            'extraction': {'total': 1, 'pending': 0, 'running': 0, 'unknown': 0, 'failed': 0},
            'analysis': {'total': 1, 'results_missing': 0, 'needs_review': 0}}


@pytest.mark.parametrize('data', [None, [], {}, payload('shell'), payload(device_id='bad'),
    payload('create', name_hash='raw name'), payload('distribute', target_id=str(uuid4()))])
def test_reject_invalid_requests(data):
    with pytest.raises((ValueError, KeyError, TypeError)):
        admin.validate(data)


def test_delivery_requires_explicit_scope_and_target():
    value = payload('distribute', target_id=str(uuid4()), confirm='existing-global-inventory-to-selected-target')
    assert admin.validate(value) == value


@pytest.mark.parametrize('stage,field,value', [
    (None, 'coverage', 'legacy_unknown'), (None, 'review_status', 'pending_review'),
    ('messages', 'total', 0), ('messages', 'inactive', 1), ('messages', 'without_extraction_job', 1),
    ('extraction', 'total', 0), ('extraction', 'pending', 1), ('extraction', 'running', 1),
    ('extraction', 'unknown', 1), ('extraction', 'failed', 1),
    ('analysis', 'total', 0), ('analysis', 'results_missing', 1), ('analysis', 'needs_review', 1)])
def test_delivery_denied_on_unverified_import(stage, field, value):
    progress = deepcopy(ready())
    (progress[stage] if stage else progress)[field] = value
    assert not admin.ready_for_delivery(progress)


def test_complete_progress_is_ready():
    assert admin.ready_for_delivery(ready())
    assert not admin.ready_for_delivery({})


async def test_invalid_device_cannot_read_job():
    db = MagicMock()
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(ValueError):
        await admin.authorize(db, payload())
    assert db.execute.await_count == 1


async def test_other_owners_import_is_denied():
    db = MagicMock()
    owner_result, job_result = MagicMock(), MagicMock()
    owner_result.mappings.return_value.one_or_none.return_value = {'email': 'owner@example.invalid', 'owner_user_id': 7}
    job_result.mappings.return_value.one_or_none.return_value = {'uploaded_by': 'other@example.invalid'}
    db.execute = AsyncMock(side_effect=[owner_result, job_result])
    with patch.object(admin.devices, 'valid', return_value=True), pytest.raises(ValueError):
        await admin.authorize(db, payload())


async def test_unready_import_does_not_write_sheets():
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={'unresolved_names': []})), \
         patch.object(admin, 'read_progress', new=AsyncMock(return_value={})), \
         patch.object(admin.distribution, 'run_distribution', new_callable=AsyncMock) as send:
        with pytest.raises(ValueError):
            await admin.operate(MagicMock(), payload('distribute', target_id=str(uuid4())))
        send.assert_not_awaited()


async def test_selected_target_only_and_sanitized_delivery_response():
    data = payload('distribute', target_id=str(uuid4()))
    result = {'output_count': 2, 'results': [{'target_id': data['target_id'], 'target_name': 'private',
               'status': 'ok', 'rows_written': 2}], 'errors': []}
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={'unresolved_names': []})), \
         patch.object(admin, 'read_progress', new=AsyncMock(return_value=ready())), \
         patch.object(admin.distribution, 'run_distribution', new=AsyncMock(return_value=result)) as send:
        answer = await admin.operate(MagicMock(), data)
        assert send.call_args.kwargs == {'target_id': data['target_id']}
        assert 'private' not in str(answer)
        assert answer['status'] == 'distributed'


async def test_failed_delivery_is_not_confirmed_and_errors_are_not_reflected():
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={'unresolved_names': []})), \
         patch.object(admin, 'read_progress', new=AsyncMock(return_value=ready())), \
         patch.object(admin.distribution, 'run_distribution', new=AsyncMock(return_value={
             'output_count': 1, 'results': [], 'errors': [{'error': 'private URL'}]})):
        answer = await admin.operate(MagicMock(), payload('distribute', target_id=str(uuid4())))
        assert answer['status'] == 'not_confirmed'
        assert answer['error_count'] == 1
        assert 'private' not in str(answer)


async def test_create_requires_exact_pending_name_hash():
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={
         'unresolved_names': ['Private Supplier'], 'review_status': 'pending_review'})), \
         patch.object(admin, 'resolve_supplier', new_callable=AsyncMock) as resolve:
        with pytest.raises(ValueError):
            await admin.operate(MagicMock(), payload('create', name_hash=admin.name_hash('Other')))
        resolve.assert_not_awaited()


async def test_commit_delegates_existing_review_gate():
    response = SimpleNamespace(model_dump=lambda: {'status': 'committed'})
    data = payload('commit')
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={'unresolved_names': []})), \
         patch.object(admin, 'commit_pending_job', new=AsyncMock(return_value=response)) as commit:
        db = MagicMock()
        assert await admin.operate(db, data) == {'status': 'committed'}
        commit.assert_awaited_once_with(data['import_job_id'], db)


async def test_inspection_never_returns_names_or_sheet_addresses():
    job = {'unresolved_names': ['PRIVATE SENDER'], 'message_count': 2}
    target = {'id': uuid4(), 'is_active': True, 'last_distributed_at': None,
              'last_distributed_count': None, 'last_result': None,
              'name': 'PRIVATE TARGET', 'spreadsheet_id': 'PRIVATE SHEET ID'}
    with patch.object(admin, 'authorize', new=AsyncMock(return_value=job)), \
         patch.object(admin, 'read_progress', new=AsyncMock(return_value=ready())), \
         patch.object(admin.distribution, 'list_targets', new=AsyncMock(return_value=[target])), \
         patch.object(admin.distribution, 'load_distribution_settings', new=AsyncMock(return_value={})), \
         patch.object(admin.distribution, 'fetch_output_rows', new=AsyncMock(return_value=[['PRIVATE BODY']])):
        result = await admin.operate(MagicMock(), payload())
        assert 'PRIVATE' not in str(result)
        assert result['unresolved_name_hashes'] == [admin.name_hash('PRIVATE SENDER')]
        assert result['output_count'] == 1


async def test_inspect_starts_read_only_transaction():
    db = MagicMock()
    db.execute = AsyncMock()
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=db)
    manager.__aexit__ = AsyncMock(return_value=False)
    with patch.object(admin, 'AsyncSessionLocal', return_value=manager), \
         patch.object(admin, 'operate', new=AsyncMock(return_value={'status': 'inspected'})):
        await admin.run(payload())
    assert str(db.execute.call_args.args[0]) == 'SET TRANSACTION READ ONLY'


async def test_existing_supplier_not_created_again():
    name = 'PRIVATE SENDER'
    db = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = 1
    db.execute = AsyncMock(return_value=result)
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={
            'unresolved_names': [name], 'review_status': 'pending_review'})), \
         patch.object(admin, 'resolve_supplier', new_callable=AsyncMock) as resolve:
        with pytest.raises(ValueError):
            await admin.operate(db, payload('create', name_hash=admin.name_hash(name)))
        resolve.assert_not_awaited()


async def test_existing_commit_rejection_is_preserved():
    from fastapi import HTTPException
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={'unresolved_names': ['pending']})), \
         patch.object(admin, 'commit_pending_job', new=AsyncMock(side_effect=HTTPException(409, 'unresolved'))):
        with pytest.raises(HTTPException) as error:
            await admin.operate(MagicMock(), payload('commit'))
        assert error.value.status_code == 409


def test_private_report_only_decrypts_with_local_key_and_detects_tampering():
    import base64
    import json

    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    report = admin.seal_report({'name': 'PRIVATE SENDER'}, public)
    assert 'PRIVATE' not in str(report)
    secret = key.decrypt(base64.b64decode(report['key']), padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    body, nonce = base64.b64decode(report['body']), base64.b64decode(report['nonce'])
    assert json.loads(AESGCM(secret).decrypt(nonce, body, b'line-import-report-v1')) == {'name': 'PRIVATE SENDER'}
    with pytest.raises(InvalidTag):
        AESGCM(secret).decrypt(nonce, body[:-1] + bytes([body[-1] ^ 1]), b'line-import-report-v1')


def test_private_report_rejects_non_public_key_and_mutating_actions():
    with pytest.raises(ValueError):
        admin.report_key('not a public key')
    with pytest.raises(ValueError):
        admin.validate(payload('commit', report_public_key='not a public key'))


@pytest.mark.parametrize('source_count,truncated', [(1, False), (2, False), (3, True)])
async def test_source_comparison_exports_only_fingerprints_inside_encrypted_report(source_count, truncated):
    db = MagicMock()
    suppliers, sources = MagicMock(), MagicMock()
    suppliers.mappings.return_value.all.return_value = [{'code': 'SP1', 'name': 'PRIVATE', 'is_active': True}]
    sources.mappings.return_value.all.return_value = [{'code': 'SP1', 'raw_text': 'private\n body', 'line_posted_at': None, 'is_active': True}] * source_count
    alias_result = MagicMock()
    alias_result.mappings.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[suppliers, sources, alias_result])
    with patch.object(admin, 'authorize', new=AsyncMock(return_value={'unresolved_names': ['PRIVATE'], 'message_count': 1})), \
         patch.object(admin, 'read_progress', new=AsyncMock(return_value=ready())), \
         patch.object(admin.distribution, 'list_targets', new=AsyncMock(return_value=[])), \
         patch.object(admin.distribution, 'load_distribution_settings', new=AsyncMock(return_value={})), \
         patch.object(admin.distribution, 'fetch_output_rows', new=AsyncMock(return_value=[])), \
         patch.object(admin, 'seal_report', return_value={'body': 'encrypted'}) as seal, \
         patch.object(admin, 'SOURCE_REPORT_LIMIT', 2):
        result = await admin.operate(db, payload(report_public_key='test-public-key'))
    data = seal.call_args.args[0]
    assert data['source_fingerprints'][0]['compact_sha256'] == admin.name_hash('privatebody')
    assert 'raw_text' not in data['source_fingerprints'][0]
    assert data['source_fingerprints'][0]['posted_at'] == 'None'
    assert data['source_limit'] == 2
    assert data['sources_truncated'] is truncated
    assert len(data['source_fingerprints']) == min(source_count, 2)
    assert 'private' not in str(result).replace('private_report', '')
    assert 'LIMIT 3' in str(db.execute.call_args_list[-2].args[0])
    assert data['source_aliases'] == []


def test_large_report_roundtrips_through_bounded_log_lines(capsys):
    import base64
    import json
    data = {'status': 'inspected', 'private_report': {'body': 'x' * 90000}}
    admin.emit_result(data)
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == 'LINE_IMPORT_REPORT_END'
    assert max(len(line) for line in lines) <= 12019
    encoded = ''.join(line.split(':', 1)[1] for line in lines[:-1])
    assert json.loads(base64.b64decode(encoded)) == data


def test_small_report_preserves_existing_json_output(capsys):
    import json
    admin.emit_result({'status': 'committed'})
    assert json.loads(capsys.readouterr().out) == {'status': 'committed'}
