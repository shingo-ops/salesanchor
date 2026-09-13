from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app import line_import_admin as admin
from app.services import line_source_names as svc
from app.services.tcg_line_import_svc import resolve_suppliers


def message(name='Example Full', body=None):
    return {'display_name': name, 'body': body or 'inventory item 100 yen\n' * 10,
            'timestamp': '2026-09-12 15:30:00', 'is_system_event': False}


def supplier():
    return {'id': uuid4(), 'code': 'SP0001', 'name': 'Example'}


def source(code='SP0001', posted=None, body=None):
    return {'code': code, 'raw_text': body or 'Full ' + message()['body'],
            'line_posted_at': posted or datetime(2026, 9, 12, 6, 30, tzinfo=timezone.utc)}


def test_android_alias_preserves_original_and_pc_master():
    masters = [supplier()]
    original = message()
    before = deepcopy(original)
    aliases = [{'display_name': original['display_name'], **{k: masters[0][k] for k in ('code', 'name')}}]
    resolved, missing = svc.resolve_android([original], masters, aliases)
    assert not missing
    assert resolved[0]['sp_code'] == 'SP0001'
    assert resolved[0]['canonical_name'] == 'Example'
    assert resolved[0]['display_name'] == 'Example Full'
    assert original == before
    assert resolve_suppliers([original], masters)[1]  # PC remains exact-name-only.
    assert masters[0]['name'] == 'Example'


@pytest.mark.parametrize('aliases,masters', [
    ([{'display_name': 'Example Full', 'code': None, 'name': None}], []),
    ([{'display_name': 'Example Full', 'code': 'SP0002', 'name': 'Other'}],
     [{'name': 'Example Full', 'code': 'SP0001'}]),
    ([], [{'name': 'Example Full', 'code': 'SP0001'}, {'name': 'Example Full', 'code': 'SP0002'}]),
])
def test_dangling_conflicting_or_duplicate_names_are_unresolved(aliases, masters):
    resolved, missing = svc.resolve_android([message()], masters, aliases)
    assert not resolved
    assert missing[0]['display_name'] == 'Example Full'


def test_android_marker_is_explicit_and_mixed_input_is_rejected():
    assert not svc.is_android([message()])
    assert not svc.is_android([])
    marked = {**message(), '_line_source_format': svc.MARKER}
    assert svc.is_android([marked])
    with pytest.raises(ValueError):
        svc.is_android([marked, message()])


def test_proof_matches_name_remainder_timestamp_and_long_body():
    proof = svc.history_proof([message()], 'Example Full', 'SP0001', [supplier()], [source()])
    assert len(proof) == 64
    assert proof == svc.history_proof([message()], 'Example Full', 'SP0001', [supplier()], [source(), source()])


@pytest.mark.parametrize('sources', [[], [source(posted=datetime(2026, 9, 12, 7, 30, tzinfo=timezone.utc))],
    [{**source(), 'line_posted_at': None}], [source(body='different' * 20)],
    [source(), source(code='SP0002', body=message()['body'])]])
def test_missing_wrong_or_ambiguous_history_is_rejected(sources):
    with pytest.raises(ValueError):
        svc.history_proof([message()], 'Example Full', 'SP0001', [supplier()], sources)


def test_short_templates_do_not_establish_aliases():
    with pytest.raises(ValueError):
        svc.history_proof([message(body='hello')], 'Example Full', 'SP0001', [supplier()], [source(body='Full hello')])


def data():
    return {'action': 'link', 'device_id': str(uuid4()), 'import_job_id': str(uuid4()),
            'name_hash': svc.digest('Example Full'), 'supplier_code': 'SP0001', 'android_sha256': 'a'*64}


@pytest.mark.parametrize('change', [{'supplier_code': 'bad'}, {'android_sha256': ''}, {'name_hash': 'plain-name'}])
def test_link_request_validation(change):
    with pytest.raises(ValueError):
        admin.validate({**data(), **change})


async def test_link_requires_authorized_owner_before_mutation():
    with patch.object(admin, 'authorize', new=AsyncMock(side_effect=ValueError('owner'))), \
         patch.object(svc, 'link_pending', new_callable=AsyncMock) as link:
        with pytest.raises(ValueError):
            await admin.operate(MagicMock(), data())
    link.assert_not_called()


def result(value=None, rows=None):
    r = MagicMock()
    r.mappings.return_value.one.return_value = value
    r.mappings.return_value.all.return_value = rows or []
    r.scalar_one.return_value = value
    return r


@pytest.mark.parametrize('change', [{'raw_sha256': 'b'*64}, {'review_status': 'ok'}])
async def test_wrong_file_or_committed_job_cannot_be_tagged(change):
    job = {'raw_sha256': 'a'*64, 'review_status': 'pending_review', 'pending_messages': [message()], **change}
    db = MagicMock(execute=AsyncMock(return_value=result(job)), commit=AsyncMock())
    with pytest.raises(ValueError):
        await svc.link_pending(db, data())
    assert db.execute.await_count == 1
    db.commit.assert_not_called()


async def test_link_writes_alias_and_pending_metadata_but_not_master_or_source_messages():
    import json
    master = supplier()
    job = {'raw_sha256': 'a'*64, 'review_status': 'pending_review', 'pending_messages': [message(), message('Unknown')]}
    db = MagicMock(execute=AsyncMock(side_effect=[result(job), result(), result(rows=[master]),
        result(rows=[source()]), result(), result(master['id']),
        result(rows=[{'display_name': 'Example Full', 'code': master['code'], 'name': master['name']}]), result()]), commit=AsyncMock())
    response = await svc.link_pending(db, data())
    assert response == {'status': 'linked', 'supplier_code': 'SP0001', 'linked_message_count': 1, 'remaining_count': 1}
    queries = [str(c.args[0]) for c in db.execute.call_args_list]
    assert not any('UPDATE' in q and 'tcg_suppliers' in q for q in queries)
    assert not any('INSERT' in q and 'source_messages' in q for q in queries)
    last = db.execute.call_args.args[1]
    assert json.loads(last['names']) == ['Unknown']
    saved = json.loads(last['messages'])
    assert saved[0]['body'] == message()['body']
    assert saved[0]['display_name'] == 'Example Full'
    assert svc.is_android(saved)
    db.commit.assert_awaited_once()


async def test_existing_alias_is_not_reassigned():
    master = supplier()
    job = {'raw_sha256': 'a'*64, 'review_status': 'pending_review', 'pending_messages': [message()]}
    db = MagicMock(execute=AsyncMock(side_effect=[result(job), result(), result(rows=[master]),
        result(rows=[source()]), result(), result(uuid4())]), commit=AsyncMock())
    with pytest.raises(ValueError):
        await svc.link_pending(db, data())
    db.commit.assert_not_called()


async def test_android_upload_uses_alias_but_preserves_unknown_review_gate():
    from app.services.tcg_line_import_svc import import_line_export
    captured = []
    async def execute(sql, params=None):
        r = MagicMock()
        r.fetchone.return_value = None
        r.fetchall.return_value = [('SP0001', 'Example')]
        if 'INSERT INTO' in str(sql) and 'import_jobs' in str(sql):
            captured.append(params)
        return r
    db = MagicMock(execute=execute, commit=AsyncMock())
    export = '2026/9/12(土)\n15:30\tExample Full\tinventory\n15:31\tUnknown\tother\n'
    with patch.object(svc, 'load_aliases', new=AsyncMock(return_value=[{'display_name': 'Example Full', 'code': 'SP0001', 'name': 'Example'}])):
        response = await import_line_export(db, 'talk.txt', export, None, source_format='android', window_hours=0)
    assert response['unresolved_display_names'] == ['Unknown']
    import json
    saved = json.loads(captured[0]['pending_messages'])
    assert saved[0]['display_name'] == 'Example Full'
    assert svc.is_android(saved)


async def test_pending_android_commit_uses_alias_and_keeps_remaining_names_blocked():
    from fastapi import HTTPException

    from app.routers import tcg_line_import as routes
    pending = [{**message(), '_line_source_format': svc.MARKER}, {**message('Unknown'), '_line_source_format': svc.MARKER}]
    job, masters = MagicMock(), MagicMock()
    job.fetchone.return_value = ('pending_review', pending, None, None)
    masters.fetchall.return_value = [('SP0001', 'Example')]
    db = MagicMock(execute=AsyncMock(side_effect=[job, masters]), commit=AsyncMock())
    with patch.object(svc, 'load_aliases', new=AsyncMock(return_value=[{'display_name': 'Example Full', 'code': 'SP0001', 'name': 'Example'}])), \
         patch.object(routes, '_write_source_messages', new_callable=AsyncMock) as write:
        with pytest.raises(HTTPException) as exc:
            await routes.commit_pending_job(str(uuid4()), db)
    assert exc.value.status_code == 409
    assert exc.value.detail['unresolved_names'] == ['Unknown']
    write.assert_not_called()
