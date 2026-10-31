"""テスト用データの作り方・SQL の点検の試験（card-a-backend.md §5-2・§5-3・§5-4）。

scripts/lead_regression/ を import する。PostgreSQL に流す試験は、環境変数
LEAD_REGRESSION_PG_URL（そのクラウド・手元の使い捨ての PostgreSQL の localhost。asyncpg 形式
postgresql://...）がある環境だけで動く（無ければ skip）。本番やほかの外部の接続先は設定しない。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

from app.schemas.lead import LeadCustomerType, LeadScale, LeadStatus, LeadTemperature
from app.services import lead_conversion_factors as lcf

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts" / "lead_regression"))
import check_sql  # noqa: E402
import generate as gen  # noqa: E402

BASE = dt.date(2026, 11, 1)
DELETE_SQL = _ROOT / "docs" / "handoff" / "lead-regression" / "sql" / "delete_tenant_001.sql"


@pytest.fixture(scope="module")
def ds():
    return gen.generate(20261101, BASE)


# ── 作り方（§4）─────────────────────────────────────────────
def test_same_seed_same_sql_sha256():
    a = gen.render_sql(gen.generate(7, BASE), 1, "commit")
    b = gen.render_sql(gen.generate(7, BASE), 1, "commit")
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()
    c = gen.render_sql(gen.generate(8, BASE), 1, "commit")
    assert a != c


def test_dryrun_and_commit_differ_only_in_last_statement(ds):
    commit = gen.render_sql(ds, 1, "commit").splitlines()
    dry = gen.render_sql(ds, 1, "dryrun").splitlines()
    assert len(commit) == len(dry)
    diff = [i for i, (x, y) in enumerate(zip(commit, dry)) if x != y]
    assert diff == [len(commit) - 1]
    assert commit[-1] == "COMMIT;" and dry[-1] == "ROLLBACK;"


def test_counts_and_allocation(ds):
    assert len(ds.leads) == 470
    assert Counter(lead.status for lead in ds.leads) == {lcf.STATUS_WON: 150, lcf.STATUS_LOST: 320}
    assert Counter(lead.initiative for lead in ds.leads) == {lcf.INITIATIVE_INBOUND: 235, lcf.INITIATIVE_OUTBOUND: 235}
    forms = Counter(lead.sales_form_values[0] for lead in ds.leads)
    assert forms[lcf.SALES_FORM_WHOLESALE] == 141
    assert sorted(forms[v] for v in gen.SALES_FORM_OTHERS) == [82, 82, 82, 83]
    assert Counter(lead.customer_type for lead in ds.leads) == {
        LeadCustomerType.trust.value: 235,
        LeadCustomerType.price.value: 235,
    }
    assert Counter(lead.competitor_check for lead in ds.leads) == {True: 235, False: 235}
    for attr in ("channel_type", "country", "temperature", "estimated_scale"):
        assert sorted(Counter(getattr(lead, attr) for lead in ds.leads).values()) == [156, 157, 157]
    counts = Counter(sum(1 for m in ds.gen_messages if m.lead_index == i) for i in range(470))
    assert min(counts) >= 4 and max(counts) <= 20
    # 失注の理由: 8 個を順に繰り返し（40 件ずつ）
    orders = [o for o in ds.close_reason_order if o is not None]
    assert Counter(orders) == {k: 40 for k in range(1, 9)}
    assert ds.close_reason_order[[i for i, o in enumerate(ds.close_reason_order) if o][0]] == 1


def test_marks_are_unique_and_prefixed(ds):
    assert ds.lead_codes[0] == "TLR-00001" and ds.lead_codes[-1] == "TLR-00470"
    ids = [m.message_id for m in ds.gen_messages]
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"tlr-s20261101-m\d{6}", i) for i in ids)
    other = gen.generate(1, BASE)
    assert not set(ids) & {m.message_id for m in other.gen_messages}


def test_k2_all_470_computable_and_none_excluded(ds):
    res = lcf.analyze(ds.leads, ds.messages)
    assert res.included_count == 470
    assert all(v == 0 for v in res.excluded.values())
    for lead in ds.leads:
        msgs = [m for m in lcf._ordered_messages(ds.messages)[lead.id]]
        assert lcf.first_reply_seconds(msgs) is not None
        assert lcf.partner_reply_mean_seconds(msgs) is not None


def test_last_message_before_base_minus_2_days(ds):
    limit = dt.datetime.combine(BASE, dt.time(0, 0), tzinfo=dt.timezone.utc) - dt.timedelta(days=2)
    assert max(m.ts for m in ds.gen_messages) < limit
    assert all(m.ts.tzinfo is not None for m in ds.gen_messages)


def test_values_are_in_schema_enums(ds):
    statuses = {s.value for s in LeadStatus}
    temps = {t.value for t in LeadTemperature}
    scales = {s.value for s in LeadScale}
    types = {t.value for t in LeadCustomerType}
    for lead in ds.leads:
        assert lead.status in statuses and lead.temperature in temps
        assert lead.estimated_scale in scales and lead.customer_type in types


def test_planted_table_is_in_one_place():
    # 仕込む強さは generate.py だけ。入口・画面側（backend/app と frontend）には置かない
    assert gen.PLANTED_ODDS["sales_form_wholesale"] == 2.5
    for path in (_ROOT / "backend" / "app" / "services" / "lead_conversion_factors.py",
                 _ROOT / "backend" / "app" / "schemas" / "lead_conversion_factors.py"):
        assert "PLANTED" not in path.read_text(encoding="utf-8")


# ── 書き込みの SQL の点検（K5①(a)）────────────────────────────
def test_check_sql_passes_for_production_sql(ds):
    for mode in ("dryrun", "commit"):
        assert check_sql.check_sql(gen.render_sql(ds, 1, mode)) == []


@pytest.mark.parametrize(
    "bad",
    [
        "INSERT INTO tenant_004.leads (id) VALUES (1);",
        "INSERT INTO leads (id) VALUES (1);",
        "UPDATE tenant_002.leads SET status = 'lost';",
        "DELETE FROM leads WHERE id = 1;",
        "INSERT INTO tenant_001.leads (id) SELECT id FROM tenant_004.leads;",
        "INSERT INTO tenant_001.leads (id) SELECT id FROM leads;",
        "INSERT INTO tenant_001.leads (id) SELECT id FROM tenant_001.leads JOIN public.tenants t ON true;",
        "SET search_path TO tenant_001;",
        "SELECT 1 FROM tenant_005.audit_logs;",
    ],
)
def test_check_sql_rejects_violation(bad, ds):
    assert check_sql.check_sql(bad) != []
    assert check_sql.check_sql(gen.render_sql(ds, 1, "commit") + bad + "\n") != []


def test_delete_sql_writes_only_tenant_001():
    sql = DELETE_SQL.read_text(encoding="utf-8")
    assert check_sql.check_sql(sql, read_allow=("public.registration_tokens",)) == []
    # public の読み取りは名前で固定した 1 つだけ。許可なしなら不合格になる
    assert check_sql.check_sql(sql) != []
    assert "-- 手順0 の記録をここに貼る" in sql
    # 書き込み（DELETE）は tenant_001 の表だけ
    targets = re.findall(r"^DELETE FROM (\S+)", sql, re.MULTILINE)
    assert targets and all(t.startswith("tenant_001.") for t in targets)
    assert "audit_logs" not in " ".join(targets)  # audit_logs は消さない


def test_cli_refuses_output_inside_repo(tmp_path):
    inside = _ROOT / "scripts" / "lead_regression" / "should_not_exist.sql"
    rc = gen.main(["--seed", "1", "--base-date", "2026-11-01", "--tenant-id", "1", "--mode", "dryrun", "--out", str(inside)])
    assert rc == 2 and not inside.exists()
    out = tmp_path / "x.sql"
    assert gen.main(["--seed", "1", "--base-date", "2026-11-01", "--tenant-id", "1", "--mode", "dryrun", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").endswith("ROLLBACK;\n")


# ── PostgreSQL に流す試験（使い捨ての localhost だけ）────────────────
PG_URL = os.getenv("LEAD_REGRESSION_PG_URL")
pg_only = pytest.mark.skipif(not PG_URL, reason="LEAD_REGRESSION_PG_URL（使い捨ての PostgreSQL）が無い")

_DDL = """
CREATE SCHEMA tenant_001;
CREATE TABLE tenant_001.leads (
    id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL DEFAULT 1, lead_code VARCHAR(20),
    customer_name VARCHAR(255) NOT NULL, channel_type VARCHAR(30), initiative VARCHAR(10), type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'lead', temperature VARCHAR(20), estimated_scale VARCHAR(20),
    customer_type VARCHAR(50), country VARCHAR(100), competitor_check BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE tenant_001.tenant_sales_form_options (
    id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL, label VARCHAR(100) NOT NULL, value VARCHAR(100) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE (tenant_id, value));
CREATE TABLE tenant_001.lead_sales_form_selections (
    id SERIAL PRIMARY KEY, lead_id INTEGER NOT NULL REFERENCES tenant_001.leads(id) ON DELETE CASCADE,
    option_id INTEGER NOT NULL REFERENCES tenant_001.tenant_sales_form_options(id) ON DELETE RESTRICT,
    other_text TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE (lead_id, option_id));
CREATE TABLE tenant_001.close_reasons (
    id SERIAL PRIMARY KEY, type VARCHAR(10) NOT NULL, label TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE (type, label));
CREATE TABLE tenant_001.deal_close_reasons (
    id SERIAL PRIMARY KEY, lead_id INTEGER NOT NULL REFERENCES tenant_001.leads(id),
    reason_id INTEGER NOT NULL REFERENCES tenant_001.close_reasons(id), is_primary __PRIMARY_TYPE__ NOT NULL DEFAULT __PRIMARY_DEFAULT__,
    UNIQUE (lead_id, reason_id));
CREATE TABLE tenant_001.lead_channels (
    id SERIAL PRIMARY KEY, lead_id INTEGER NOT NULL REFERENCES tenant_001.leads(id) ON DELETE CASCADE,
    platform VARCHAR(30) NOT NULL, external_id VARCHAR(255) NOT NULL, display_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (platform, external_id));
CREATE TABLE tenant_001.meta_messages (
    id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL DEFAULT 1,
    lead_id INTEGER REFERENCES tenant_001.leads(id) ON DELETE SET NULL,
    platform VARCHAR(20) NOT NULL DEFAULT 'messenger', sender_id VARCHAR(100) NOT NULL, sender_name VARCHAR(200),
    message_id TEXT, message_text TEXT, direction VARCHAR(10) NOT NULL DEFAULT 'inbound', raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(), recipient_id VARCHAR(100), messaging_type VARCHAR(20),
    message_tag VARCHAR(50), page_id VARCHAR(50), original_language VARCHAR(10), occurred_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ DEFAULT NULL);
CREATE UNIQUE INDEX ON tenant_001.meta_messages (message_id) WHERE message_id IS NOT NULL;
CREATE TABLE tenant_001.conversation_logs (
    id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL, lead_id INTEGER REFERENCES tenant_001.leads(id) ON DELETE RESTRICT,
    contact_id INTEGER, company_id INTEGER, deal_id INTEGER, channel_type VARCHAR(30) NOT NULL,
    channel_identity VARCHAR(255), direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    sender VARCHAR(100), content_text TEXT, original_language VARCHAR(10), external_message_id VARCHAR(255) UNIQUE,
    raw_payload JSONB, status VARCHAR(20) DEFAULT 'sent', translated_text TEXT, analysis JSONB,
    occurred_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ DEFAULT NULL, recorded_by_user_id INTEGER);
CREATE TABLE tenant_001.meta_message_reactions (
    id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL DEFAULT 1,
    meta_message_id INTEGER NOT NULL REFERENCES tenant_001.meta_messages(id) ON DELETE CASCADE,
    emoji_name TEXT NOT NULL, reactor_discord_user_id TEXT NOT NULL);
CREATE TABLE tenant_001.message_translations (
    id SERIAL PRIMARY KEY, message_id TEXT NOT NULL, target_language VARCHAR(10) NOT NULL,
    translated_text TEXT NOT NULL, UNIQUE (message_id, target_language));
CREATE TABLE tenant_001.customer_scores (id SERIAL PRIMARY KEY, lead_id INTEGER NOT NULL);
CREATE TABLE tenant_001.message_labels (id SERIAL PRIMARY KEY, lead_id INTEGER);
CREATE TABLE tenant_001.quotes (id SERIAL PRIMARY KEY, lead_id INTEGER REFERENCES tenant_001.leads(id));
CREATE TABLE tenant_001.companies (id SERIAL PRIMARY KEY, lead_id INTEGER REFERENCES tenant_001.leads(id));
CREATE TABLE tenant_001.contacts (id SERIAL PRIMARY KEY, lead_id INTEGER REFERENCES tenant_001.leads(id));
CREATE TABLE tenant_001.outbound_translation_drafts (id SERIAL PRIMARY KEY, lead_id INTEGER);
CREATE TABLE tenant_001.lead_attachments (id SERIAL PRIMARY KEY, lead_id INTEGER REFERENCES tenant_001.leads(id) ON DELETE CASCADE);
CREATE TABLE tenant_001.audit_logs (
    id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL DEFAULT 1, user_id INTEGER NOT NULL DEFAULT 1,
    action VARCHAR(50) NOT NULL, table_name VARCHAR(100) NOT NULL, record_id INTEGER, old_data JSONB, new_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS public.registration_tokens (
    id SERIAL PRIMARY KEY, tenant_id INTEGER NOT NULL, lead_id INTEGER NOT NULL);
INSERT INTO tenant_001.close_reasons (type, label, sort_order) VALUES
  ('lost', 'r1', 1), ('lost', 'r2', 2), ('lost', 'r3', 3), ('lost', 'r4', 4), ('lost', 'r5', 5),
  ('lost', 'r6', 6), ('lost', 'r7', 7), ('lost', 'r8', 99),
  ('won', 'w1', 1), ('won', 'w2', 2), ('won', 'w3', 3), ('won', 'w4', 4), ('won', 'w5', 5), ('won', 'w6', 6), ('won', 'w7', 7);
-- 元の行（本番の leads の id 4・6 と、その元のメッセージ）
INSERT INTO tenant_001.leads (id, lead_code, customer_name, status) VALUES (4, 'LD-4', 'orig4', 'lead'), (6, 'LD-6', 'orig6', 'lead');
INSERT INTO tenant_001.meta_messages (lead_id, platform, sender_id, message_id, direction, message_text)
  VALUES (4, 'discord', 'd1', 'orig-m1', 'inbound', 'a'), (4, 'discord', 'd1', 'orig-m2', 'outbound', 'b');
SELECT setval('tenant_001.leads_id_seq', 100);
"""

_TEARDOWN = "DROP SCHEMA IF EXISTS tenant_001 CASCADE; DROP TABLE IF EXISTS public.registration_tokens;"

_RECORDS = """
INSERT INTO pg_temp.tlr_record_started VALUES (now() - interval '1 hour');
INSERT INTO pg_temp.tlr_record_orig_leads VALUES (4), (6);
INSERT INTO pg_temp.tlr_record_orig_meta SELECT id, lead_id FROM tenant_001.meta_messages WHERE message_id LIKE 'orig-%';
INSERT INTO pg_temp.tlr_record_orig_conv SELECT id, lead_id FROM tenant_001.conversation_logs WHERE lead_id IN (4, 6);
INSERT INTO pg_temp.tlr_record_orig_counts VALUES (0, 0, 0);
"""


def _split_psql_meta(sql: str) -> str:
    return "\n".join(line for line in sql.splitlines() if not line.startswith("\\"))


@pytest.fixture(params=[("BOOLEAN", "FALSE"), ("INTEGER", "0")], ids=["is_primary_boolean", "is_primary_integer"])
async def pg(request):
    import asyncpg

    conn = await asyncpg.connect(PG_URL)
    try:
        await conn.execute(_TEARDOWN)
        await conn.execute(_DDL.replace("__PRIMARY_TYPE__", request.param[0]).replace("__PRIMARY_DEFAULT__", request.param[1]))
        yield conn
    finally:
        await conn.execute(_TEARDOWN)
        await conn.close()


async def _count(conn, sql: str) -> int:
    return await conn.fetchval(sql)


async def _expect_stop(conn, sql: str, match: str) -> None:
    """止まること（psql は ON_ERROR_STOP で終了し、開いた取引は取り消される。ここでは ROLLBACK で同じにする）。"""
    with pytest.raises(Exception, match=match):
        await conn.execute(sql)
    await conn.execute("ROLLBACK")


@pg_only
async def test_pg_dryrun_leaves_nothing(pg, ds):
    await pg.execute(gen.render_sql(ds, 1, "dryrun"))
    assert await _count(pg, "SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TLR-%'") == 0
    assert await _count(pg, "SELECT count(*) FROM tenant_001.tenant_sales_form_options") == 0


@pg_only
async def test_pg_commit_counts_precheck_and_analysis(pg, ds):
    sql = gen.render_sql(ds, 1, "commit")
    await pg.execute(sql)
    exp = gen.expected_counts(ds)
    assert await _count(pg, "SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TLR-%'") == 470
    assert await _count(pg, "SELECT count(*) FROM tenant_001.leads WHERE status = 'existing_customer'") == 150
    assert await _count(pg, "SELECT count(*) FROM tenant_001.deal_close_reasons") == exp["deal_close_reasons"] == 320
    assert await _count(pg, "SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-s20261101-%'") == exp["meta_messages"]
    assert await _count(pg, "SELECT count(*) FROM tenant_001.conversation_logs WHERE external_message_id LIKE 'tlr-s20261101-%'") == exp["conv_logs_meta_copy"]
    # 時刻はすべて書き込む日の 2 日以上前
    assert await _count(pg, "SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-%' AND created_at > now() - interval '2 days'") == 0
    assert await _count(pg, "SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-%' AND occurred_at IS NOT NULL") == 0
    # 失注の理由: lost の 8 個だけが使われる
    assert await _count(pg, "SELECT count(DISTINCT d.reason_id) FROM tenant_001.deal_close_reasons d JOIN tenant_001.close_reasons r ON r.id = d.reason_id WHERE r.type = 'lost'") == 8
    # 2 回目は前提の点検で止まる
    await _expect_stop(pg, sql, "前提が違う")
    assert await _count(pg, "SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TLR-%'") == 470

    # 本番の入口と同じ読み方で、本番の外の計算と同じ答え
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.routers.analytics import _fetch_lead_conversion_inputs

    engine = create_async_engine(PG_URL.replace("postgresql://", "postgresql+asyncpg://", 1))
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SET search_path TO tenant_001"))
            leads, messages = await _fetch_lead_conversion_inputs(conn)
    finally:
        await engine.dispose()
    got = lcf.analyze(leads, messages)
    want = lcf.analyze(ds.leads, ds.messages)
    assert got.status == "ok" and got.included_count == 470 and got.excluded["by_status"] == 2
    for a, b in zip(got.items, want.items):
        assert a["key"] == b["key"]
        assert abs(a["odds_ratio"] - b["odds_ratio"]) < 1e-9
        assert abs(a["ci_low"] - b["ci_low"]) < 1e-9 and abs(a["ci_high"] - b["ci_high"]) < 1e-9


@pg_only
async def test_pg_delete_sql_removes_only_test_rows(pg, ds):
    await pg.execute(gen.render_sql(ds, 1, "commit"))
    await pg.execute("INSERT INTO tenant_001.message_translations (message_id, target_language, translated_text) "
                     "SELECT message_id, 'ja', 'x' FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-%' LIMIT 3")
    await pg.execute("INSERT INTO tenant_001.customer_scores (lead_id) SELECT id FROM tenant_001.leads WHERE lead_code = 'TLR-00001'")
    await pg.execute("INSERT INTO tenant_001.meta_message_reactions (meta_message_id, emoji_name, reactor_discord_user_id) "
                     "SELECT id, 'ok', 'u' FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-%' LIMIT 2")
    before_orig = await _count(pg, "SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'orig-%'")
    sql = _split_psql_meta(DELETE_SQL.read_text(encoding="utf-8"))
    marker = "-- 手順0 の記録をここに貼る"
    assert marker in sql
    # 記録の貼り付け: 元の行の id（書き込み前の値）。ここでは元の meta/conv の記録を貼る
    await pg.execute(sql.replace(marker, marker + "\n" + _RECORDS))
    for table in ("leads", "meta_messages", "conversation_logs", "lead_channels", "deal_close_reasons",
                  "lead_sales_form_selections", "tenant_sales_form_options", "message_translations",
                  "customer_scores", "meta_message_reactions"):
        n = await _count(pg, f"SELECT count(*) FROM tenant_001.{table}")
        expected = {"leads": 2, "meta_messages": before_orig}.get(table, 0)
        assert n == expected, (table, n)


@pg_only
async def test_pg_delete_sql_stops_when_quote_exists_or_records_missing(pg, ds):
    await pg.execute(gen.render_sql(ds, 1, "commit"))
    sql = _split_psql_meta(DELETE_SQL.read_text(encoding="utf-8"))
    marker = "-- 手順0 の記録をここに貼る"
    await _expect_stop(pg, sql, "記録が貼られていない")
    await pg.execute("INSERT INTO tenant_001.quotes (lead_id) SELECT id FROM tenant_001.leads WHERE lead_code = 'TLR-00005'")
    await _expect_stop(pg, sql.replace(marker, marker + "\n" + _RECORDS), "見積がある")
    assert await _count(pg, "SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TLR-%'") == 470
    # 統合の印: 元のリードにテスト用の目印の行が付いている
    await pg.execute("DELETE FROM tenant_001.quotes")
    await pg.execute("UPDATE tenant_001.meta_messages SET lead_id = 4 WHERE message_id LIKE 'tlr-%' AND id = (SELECT min(id) FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-%')")
    await _expect_stop(pg, sql.replace(marker, marker + "\n" + _RECORDS), "目印 tlr-")
    assert await _count(pg, "SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TLR-%'") == 470
