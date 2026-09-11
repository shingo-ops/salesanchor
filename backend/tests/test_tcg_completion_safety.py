"""Synthetic regression inputs only; no customer originals or real Gemini calls."""
import asyncio
import hashlib
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from app.services import tcg_analyzer_svc as analyzer
from app.services import tcg_distribution_svc as distribution
from app.services import tcg_unit_recovery_svc as recovery
from tests import test_tcg_work_matching_integration as work_fixture

SCHEMA = work_fixture.SCHEMA
pg = work_fixture.pg


@pytest.mark.parametrize('keyword,name,expected', [
    ('ST-31', 'ST-310', False), ('ST-31', 'ST-31 箱', True),
    ('vol.2', 'vol.20', False), ('日本語 vol.2', '日本語 vol.20', False),
    ('日本語 vol.2', '日本語 vol.2 限定', True),
    ('THE BEST', 'THE BEST1', True), ('ST-31', 'ST-31A', False),
])
def test_product_number_boundaries(keyword, name, expected):
    assert analyzer.match_product_keyword(keyword, analyzer.normalize_en(name)) is expected


def test_shared_keyword_semantics_unchanged():
    assert analyzer.match_one_kw('ST-31', 'st-310')
    assert analyzer.match_one_kw('THE BEST', 'the best1')


@pytest.mark.parametrize('name,expected', [
    ('ONE PIECE 架空商品 カートン', 'Case'),
    ('架空商品 カートン(10BOX入り)', 'Case'),
    ('架空商品 BOX', 'Box'), ('架空商品 BOX2', None),
    ('SANDBOX', None), ('架空商品 カートン(明日発送)', None),
    ('架空商品 カートン(10BOX入り、開封済)', None),
    ('架空商品 ケース', 'Case'), ('架空商品ケース', None),
    ('架空商品', None),
])
def test_terminal_unit(name, expected):
    term = recovery.find_terminal_unit(name, recovery.build_unit_recovery_terms())
    assert (term['canonical'] if term else None) == expected


def status_master():
    return [
        dict(canonical='Sold out', search_pattern='完売', priority=1, match_type='LITERAL', effect='EXCLUDE'),
        dict(canonical='In Stock', search_pattern='', priority=9, match_type='DEFAULT', effect='OUTPUT'),
    ]


@pytest.mark.parametrize('memo,expected', [
    ('完売', 'Sold out'), (' 完売 ', 'Sold out'), ('完売ではありません', 'In Stock'),
    ('一部完売、別日発送分あり', 'In Stock'), ('完売予定', 'In Stock'), ('', 'In Stock'),
])
def test_exact_sold_memo(memo, expected):
    value, exclusion = analyzer.resolve_status_v2('', status_master(), raw_memo=memo)
    assert value == expected
    assert exclusion == ('excluded' if expected == 'Sold out' else None)


def test_postgres_analysis_replay_and_distribution(pg, monkeypatch):
    connection, engine, async_url = pg
    # No extractor is invoked. The input is inserted directly as synthetic extracted data.
    with connection.cursor() as cur:
        for i, unit in enumerate(recovery._UNIT_MASTER_ROWS, 1):
            cur.execute(f'INSERT INTO {SCHEMA}.units(id,code,canonical,kubun,is_active) VALUES (%s,%s,%s,%s,true)',
                        (unit['unit_id'], f'UN{i:04d}', unit['canonical'], unit['kubun']))
            for alias in set([unit['canonical']] + unit['aliases'].split(',')) - {''}:
                cur.execute(f'INSERT INTO {SCHEMA}.unit_aliases(unit_id,alias_text,lang) VALUES (%s,%s,\'ja\')', (unit['unit_id'], alias))
        for code, canonical, kubun in [('C1','Case','箱系大'),('C2','Sealed box','箱系'),('C3','FLAG_SINGLE','単位不明')]:
            cur.execute(f'INSERT INTO {SCHEMA}.conditions(code,canonical,app_kubun,is_active,priority) VALUES (%s,%s,%s,true,1) RETURNING id', (code,canonical,kubun))
            cid = cur.fetchone()[0]
            cur.execute(f'INSERT INTO {SCHEMA}.condition_aliases(condition_id,alias_text,lang) VALUES (%s,%s,\'ja\')',(cid,canonical))
        status_migration = work_fixture.MIGRATIONS / "20260903_150000_tcg_status_master_t004.sql"
        cur.execute(status_migration.read_text().replace("tenant_004", SCHEMA))
        cur.execute(f'''INSERT INTO {SCHEMA}.tcg_products(code,japanese_title,category_class,is_active,work_id,product_category_id)
            SELECT 'SYN001','ONE PIECE 架空検証商品','Box',true,w.id,c.id FROM {SCHEMA}.tcg_series w,
            {SCHEMA}.tcg_product_categories c WHERE w.code='IP002' AND c.code='PC_BOX' RETURNING id''')
        pid = cur.fetchone()[0]
        cur.execute(f'INSERT INTO {SCHEMA}.product_search_keywords(id,product_id,keyword,position) VALUES (%s,%s,%s,0)',(str(uuid4()),pid,'架空検証商品'))
        smid, jobid = str(uuid4()), str(uuid4())
        original='ワンピース\n架空検証商品 カートン\n架空検証商品 BOX\n架空検証商品 カートン(10BOX入り)\n架空検証商品'
        cur.execute(f'''INSERT INTO {SCHEMA}.source_messages(id,supplier_channel_id,raw_text,raw_sha256,is_active,received_at)
            SELECT %s,id,%s,%s,true,now() FROM {SCHEMA}.supplier_channels LIMIT 1''',(smid,original,hashlib.sha256(original.encode()).hexdigest()))
        cur.execute(f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES (%s,%s,'done')",(jobid,smid))
        items=[]
        for line,name,memo in [(2,'ONE PIECE 架空検証商品 カートン',''),(3,'架空検証商品 BOX','完売'),(4,'架空検証商品 カートン(10BOX入り)',''),(5,'架空検証商品','')]:
            iid=str(uuid4());items.append(iid)
            cur.execute(f'''INSERT INTO {SCHEMA}.extraction_items(id,extraction_job_id,line_start,line_end,raw_product_name,raw_quantity,raw_price,raw_unit,raw_state,raw_memo)
                VALUES (%s,%s,%s,%s,%s,'2','1000','','',%s)''',(iid,jobid,line,line,name,memo))
    query=f'''SELECT ei.id,ar.pid_resolved,ar.unit_resolved,ar.unit_canonical,ar.condition_canonical,ar.status,ar.exclusion,ar.quantity_normalized,ar.price_normalized
        FROM {SCHEMA}.analysis_results ar JOIN {SCHEMA}.extraction_items ei ON ei.id=ar.extraction_item_id ORDER BY ei.line_start'''
    with Session(engine) as session:
        stats=analyzer.analyze_extraction_job(session,jobid)
    assert stats['e3a_recovered']==3
    with connection.cursor() as cur:
        cur.execute(query);first=cur.fetchall()
    assert [r[2] for r in first]==[True,True,True,False]
    assert [r[3] for r in first][:3]==['Case','Box','Case']
    assert first[1][5:7]==('Sold out','excluded')
    with Session(engine) as session:
        analyzer.analyze_extraction_job(session,jobid)
    with connection.cursor() as cur:
        cur.execute(query);assert cur.fetchall()==first
        cur.execute(f'SELECT raw_text FROM {SCHEMA}.source_messages WHERE id=%s',(smid,));assert cur.fetchone()[0]==original
        cur.execute(f'UPDATE {SCHEMA}.analysis_results SET pid_basis=\'HUMAN:confirmed\' WHERE extraction_item_id=%s',(items[0],))
        cur.execute(f'INSERT INTO {SCHEMA}.item_corrections(extraction_item_id,source_message_id,field_name,human_value,corrected_by) VALUES (%s,%s,\'product_id\',%s,\'test\')',(items[0],smid,str(pid)))
    with Session(engine) as session:
        assert analyzer.analyze_extraction_job(session,jobid)['skipped_product_corrections']==1
    with connection.cursor() as cur:
        cur.execute(f'SELECT pid_basis FROM {SCHEMA}.analysis_results WHERE extraction_item_id=%s',(items[0],));assert cur.fetchone()[0]=='HUMAN:confirmed'
    async def fetch():
        ae=create_async_engine(async_url)
        try:
            async with AsyncSession(ae) as session:
                return await distribution.fetch_output_rows(session,include_flag_single=True)
        finally:
            await ae.dispose()
    output=asyncio.run(fetch())
    assert len(output)==2
    assert all(row[8]!='Sold out' for row in output)


def test_new_product_registration_keeps_box_single_filter(pg, monkeypatch):
    from app.services import tcg_product_master_svc as master
    connection, engine, async_url = pg
    monkeypatch.setattr(master, 'TCG_SCHEMA', SCHEMA)
    async def register():
        ae = create_async_engine(async_url)
        try:
            async with AsyncSession(ae) as session:
                from sqlalchemy import text
                refs = {}
                for key, table, code in [('division_id','tcg_major_categories','DIV01'),('work_id','tcg_series','IP002'),('manufacturer_id','tcg_manufacturers','MK002'),('product_category_id','tcg_product_categories','PC_BOX')]:
                    refs[key] = str((await session.execute(text(f'SELECT id FROM {SCHEMA}.{table} WHERE code=:code'),{'code':code})).scalar_one())
                args = dict(extraction_item_id='',source_message_id='',japanese_title='架空の登録検証デッキ',release_date=None,search_keywords='架空の登録検証デッキ',exclude_keywords='',**refs)
                first = await master.create_product(session, **args)
                second = await master.create_product(session, **args)
                assert first['ok'] and not second['ok'] and second['code']=='DUPLICATE_CANDIDATE'
                return first['product_id']
        finally:
            await ae.dispose()
    code = asyncio.run(register())
    with connection.cursor() as cur:
        cur.execute(f'SELECT category_class FROM {SCHEMA}.tcg_products WHERE code=%s',(code,))
        assert cur.fetchone()[0]=='One Piece'  # Existing registration contract; not the Box/Single column.
    _, jobid, result = work_fixture.run_message(connection, engine, monkeypatch,
        'ワンピース\n架空の登録検証デッキ PSA10',
        [work_fixture.record('架空の登録検証デッキ',2,state='PSA10')])
    assert result['analysis_stats']['pid_resolved']==0
