"""Android-specific sender aliases; canonical PC master names stay unchanged."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

MARKER = 'android-v1'
JST = timezone(timedelta(hours=9))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def is_android(messages):
    marked = [m.get('_line_source_format') == MARKER for m in messages]
    if any(marked) and not all(marked):
        raise ValueError('mixed import formats')
    return bool(marked) and all(marked)


async def load_aliases(db):
    # line_supplier_source_names は Sprint 1 で DROP 済み。空リストを返す
    return []


def resolve_android(messages, suppliers, aliases):
    by_name = defaultdict(dict)
    for supplier in suppliers:
        by_name[supplier['name']][supplier['code']] = supplier['name']
    blocked = set()
    for alias in aliases:
        if not alias['code']:
            blocked.add(alias['display_name'])
        else:
            by_name[alias['display_name']][alias['code']] = alias['name']
    resolved, missing = [], defaultdict(list)
    for message in messages:
        name = message['display_name']
        candidates = by_name[name]
        if name not in blocked and len(candidates) == 1:
            code, canonical = next(iter(candidates.items()))
            resolved.append({**message, 'sp_code': code, 'canonical_name': canonical})
        else:
            missing[name].append(message['timestamp'])
    return resolved, [{'display_name': n, 'timestamps': t} for n, t in missing.items()]


def history_proof(messages, display_name, supplier_code, suppliers, sources):
    """Require long normalized body + timestamp, uniquely identifying one code."""
    index = defaultdict(set)
    for message in messages:
        if message['display_name'] != display_name:
            continue
        body = ''.join(message['body'].split())
        if len(body) < 80:
            continue
        posted = datetime.fromisoformat(message['timestamp']).replace(tzinfo=JST).astimezone(timezone.utc)
        index[(posted, digest(body))].add(None)
        for supplier in suppliers:
            if display_name.startswith(supplier['name'] + ' '):
                remainder = display_name[len(supplier['name']) + 1:]
                index[(posted, digest(''.join(remainder.split()) + body))].add(supplier['code'])
    evidence = set()
    for source in sources:
        posted = source['line_posted_at']
        if posted is None:
            continue
        body_hash = digest(''.join(source['raw_text'].split()))
        expected = index.get((posted.astimezone(timezone.utc), body_hash), set())
        if None in expected or source['code'] in expected:
            evidence.add((source['code'], posted.isoformat(), body_hash))
    if {item[0] for item in evidence} != {supplier_code}:
        raise ValueError('unique timestamp and body evidence required')
    return digest(json.dumps(sorted(evidence)))


async def link_pending(db, data):
    # Caller verifies active device owner and import ownership before entering here.
    job = (await db.execute(text('''SELECT raw_sha256,review_status,pending_messages
        FROM public.import_jobs WHERE id=:id FOR UPDATE'''),
        {'id': data['import_job_id']})).mappings().one()
    if job['review_status'] != 'pending_review' or job['raw_sha256'] != data['android_sha256']:
        raise ValueError('pending Android file digest required')
    messages = job['pending_messages']
    if isinstance(messages, str):
        messages = json.loads(messages)
    if not messages:
        raise ValueError('pending messages required')
    names = {m['display_name'] for m in messages if digest(m['display_name']) == data['name_hash']}
    if len(names) != 1:
        raise ValueError('unique sender required')
    name = names.pop()
    # Protect name/code selection against concurrent master renames/deactivation.
    await db.execute(text('LOCK TABLE public.suppliers IN SHARE MODE'))
    suppliers = (await db.execute(text('SELECT id, supplier_code AS code, line_name AS name FROM public.suppliers WHERE is_active=TRUE AND line_name IS NOT NULL'))).mappings().all()
    target = [s for s in suppliers if s['code'] == data['supplier_code']]
    if len(target) != 1 or any(s['name'] == name and s['code'] != data['supplier_code'] for s in suppliers):
        raise ValueError('active nonconflicting supplier required')
    times = sorted({datetime.fromisoformat(m['timestamp']).replace(tzinfo=JST)
                    for m in messages if m['display_name'] == name})
    sources = (await db.execute(text('''SELECT ps.supplier_code AS code,sm.raw_text,sm.line_posted_at
        FROM public.source_messages sm
        JOIN public.supplier_channels sc ON sc.id=sm.supplier_channel_id
        JOIN public.suppliers ps ON ps.id=sc.supplier_id
        WHERE sc.channel='line' AND sm.line_posted_at=ANY(CAST(:times AS timestamptz[]))
        LIMIT 10001'''), {'times': times})).mappings().all()
    if len(sources) > 10000:
        raise ValueError('evidence query truncated')
    history_proof(messages, name, data['supplier_code'], suppliers, sources)
    await db.execute(text('UPDATE public.suppliers SET line_name=:name WHERE id=:supplier_id'),
        {'name': name, 'supplier_id': target[0]['id']})
    # Re-fetch suppliers so the updated line_name is reflected in resolve_android
    suppliers_updated = (await db.execute(text('SELECT id, supplier_code AS code, line_name AS name FROM public.suppliers WHERE is_active=TRUE AND line_name IS NOT NULL'))).mappings().all()
    tagged = [{**m, '_line_source_format': MARKER} for m in messages]
    resolved, missing = resolve_android(tagged, suppliers_updated, await load_aliases(db))
    mapped = [m for m in resolved if m['display_name'] == name]
    if not mapped or any(m['sp_code'] != data['supplier_code'] for m in mapped):
        raise ValueError('alias resolution verification failed')
    await db.execute(text('''UPDATE public.import_jobs SET pending_messages=CAST(:messages AS jsonb),
        unresolved_names=CAST(:names AS jsonb),unresolved_count=:count WHERE id=:id'''),
        {'id': data['import_job_id'], 'messages': json.dumps(tagged, ensure_ascii=False),
         'names': json.dumps([m['display_name'] for m in missing], ensure_ascii=False), 'count': len(missing)})
    await db.commit()
    return {'status': 'linked', 'supplier_code': data['supplier_code'],
            'linked_message_count': len(mapped), 'remaining_count': len(missing)}
