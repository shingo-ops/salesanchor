"""リード統合（POST /leads/{master_id}/merge と /merge/preview）の試験（ADR-1049）。

DB を使う試験は、実在の PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL）があるときだけ動く
（無ければ skip。CI の test.yml では設定済みなので動く）。
漏れの見張り（test_merge_table_list_matches_lead_id_tables）は静的な検査で、DB を使わず skip もされない。

テナントは rls_bootstrap の bootstrap_tenant_schema で本物の定義から作る。
テナント作成では作られない表（会話の記録・添付・分類・スコア・翻訳の下書き）は、
その表・列を作る本物の migration を _apply_migration_on_conn で（試験のテナントのスキーマだけに限って）流して用意する（試験の中に表の定義は書かない）。
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.models import User
from app.routers import leads as leads_router
from app.routers.leads import LEAD_MERGE_TABLES
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
requires_pg = pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。CI の test.yml で実行される。",
)

_TENANT_ID = 993
_USER_ID = 9931
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_REPO_ROOT = Path(__file__).resolve().parents[2]

# テナント作成では作られない表・列を作る本物の migration（この順で流す）。
# (ファイル名, 試験のテナントのスキーマだけに流すか)。False は public だけを触る migration。
_TABLE_MIGRATIONS = (
    ("014_create_current_tenant_id_function.sql", False),  # lead_attachments の RLS が public.current_tenant_id() を使う
    ("090_add_lead_contact_links.sql", True),  # leads: messenger_link, discord_id
    ("091_add_leads_discord_messaging_columns.sql", True),  # leads: discord_user_id, discord_dm_channel_id
    ("095_add_lead_social_links.sql", True),  # leads: instagram_link, whatsapp_link
    ("099_add_discord_guild_config.sql", True),  # leads: discord_role_sync_status, discord_role_sync_at
    ("20260602_120000_add_discord_ticket_config.sql", True),  # leads: discord_guild_channel_id
    ("20260604_090000_create_conversation_logs.sql", True),
    ("20260715_100000_add_conversation_logs_lead_fk.sql", True),
    ("20260902_100000_create_lead_attachments.sql", True),
    ("20260604_180000_analytics_agent_a_tables.sql", True),
    ("20260604_220000_create_translation_glossary.sql", True),
    ("20260604_080000_create_registration_tokens.sql", False),
)

_PUBLIC_TABLES = {s.name for s in LEAD_MERGE_TABLES if s.schema == "public"}
_bootstrapped = False


# ---------------------------------------------------------------------------
# 漏れの見張り（静的な検査・DB を使わない）
# ---------------------------------------------------------------------------

# 「後で消された表」の除外一覧: 表名 → それを DROP した migration のファイル名
DROPPED_LEAD_ID_TABLES = {
    "deals": "20260729_043520_drop_deals.sql",
    "customers": "20260601_140000_drop_customers_tables.sql",
}

_CREATE_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.{}%\"]+)\s*\(", re.IGNORECASE)
_ALTER_ADD_RE = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?([\w.{}%\"]+)\s+ADD\s+COLUMN\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?lead_id\b",
    re.IGNORECASE,
)
_LEAD_ID_COL_RE = re.compile(r"(?:^|,)[ \t]*lead_id[ \t]+\w+", re.IGNORECASE | re.MULTILINE)


def _table_name(raw: str) -> str:
    return raw.replace('"', "").split(".")[-1]


def _create_table_body(sql: str, open_idx: int) -> str:
    """open_idx の "(" から対応する ")" までの本文を返す。"""
    depth = 0
    for i in range(open_idx, len(sql)):
        if sql[i] == "(":
            depth += 1
        elif sql[i] == ")":
            depth -= 1
            if depth == 0:
                return sql[open_idx + 1 : i]
    return sql[open_idx + 1 :]


def _collect_lead_id_tables() -> dict[str, set[str]]:
    """lead_id 列を作る表名 → それを作る（足す）ファイル名の集合。"""
    sources = [_REPO_ROOT / "backend" / "app" / "services" / "tenant.py"]
    sources += sorted((_REPO_ROOT / "migrations").glob("*.sql"))
    found: dict[str, set[str]] = {}
    for path in sources:
        sql = path.read_text("utf-8")
        for m in _CREATE_RE.finditer(sql):
            body = _create_table_body(sql, m.end() - 1)
            if _LEAD_ID_COL_RE.search(body):
                found.setdefault(_table_name(m.group(1)), set()).add(path.name)
        for m in _ALTER_ADD_RE.finditer(sql):
            found.setdefault(_table_name(m.group(1)), set()).add(path.name)
    return found


def test_merge_table_list_matches_lead_id_tables():
    """lead_id 列を作る表（後で消された表を除く）が、統合の 13 表の定数と一致する。

    表が足されて lead_id を持つと、この試験が落ちて付け替えの漏れに気付ける。
    """
    collected = _collect_lead_id_tables()
    print("lead_id を作る表（全部）:", sorted(collected))
    print("除外の一覧（表名: DROP の migration）:", DROPPED_LEAD_ID_TABLES)

    # 除外の一覧が古くなっていない: 集めた表に入っていて、DROP の migration が実在し、その表を DROP している
    for table, filename in DROPPED_LEAD_ID_TABLES.items():
        assert table in collected, f"除外一覧の {table} は lead_id を作る表として見つからない"
        drop_sql = (_REPO_ROOT / "migrations" / filename).read_text("utf-8")
        assert re.search(r"DROP\s+TABLE[^;]*\b" + re.escape(table) + r"\b", drop_sql, re.IGNORECASE), (
            f"{filename} に {table} の DROP TABLE が見つからない"
        )

    live = set(collected) - set(DROPPED_LEAD_ID_TABLES)
    assert len(LEAD_MERGE_TABLES) == 13
    assert live == {s.name for s in LEAD_MERGE_TABLES}, (
        "lead_id を持つ表と LEAD_MERGE_TABLES が違う: "
        f"定数に無い={sorted(live - {s.name for s in LEAD_MERGE_TABLES})} "
        f"定数だけ={sorted({s.name for s in LEAD_MERGE_TABLES} - live)}"
    )


# ---------------------------------------------------------------------------
# DB を使う試験の土台
# ---------------------------------------------------------------------------

class _Env:
    def __init__(self, engine, client):
        self.engine = engine
        self.client = client

    async def run(self, sql: str, params: dict | None = None):
        """管理者接続で 1 文を流し、全行を返す（テナントを指定して RLS にも合う形）。"""
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(_TENANT_ID)})
            res = await conn.execute(text(sql), params or {})
            return res.mappings().all() if res.returns_rows else []

    async def lead(self, name: str, status: str = "lead", **cols) -> int:
        names = ["tenant_id", "customer_name", "status", *cols]
        values = [":tenant_id", ":customer_name", ":status", *[f":{c}" for c in cols]]
        rows = await self.run(
            f"INSERT INTO {_SCHEMA}.leads ({', '.join(names)}) VALUES ({', '.join(values)}) RETURNING id",
            {"tenant_id": _TENANT_ID, "customer_name": name, "status": status, **cols},
        )
        return int(rows[0]["id"])

    async def count(self, table: str, lead_id: int) -> int:
        if table in _PUBLIC_TABLES:
            sql = f"SELECT count(*) AS n FROM public.{table} WHERE lead_id = :l AND tenant_id = :t"
        else:
            sql = f"SELECT count(*) AS n FROM {_SCHEMA}.{table} WHERE lead_id = :l"
        return int((await self.run(sql, {"l": lead_id, "t": _TENANT_ID}))[0]["n"])

    async def total(self, table: str) -> int:
        if table in _PUBLIC_TABLES:
            sql = f"SELECT count(*) AS n FROM public.{table} WHERE tenant_id = :t"
        else:
            sql = f"SELECT count(*) AS n FROM {_SCHEMA}.{table}"
        return int((await self.run(sql, {"t": _TENANT_ID}))[0]["n"])

    async def catalogs(self) -> dict[str, list[int]]:
        """販売形態の選択肢 2 件と、成約・失注の理由 2 件を作って id を返す。"""
        tag = uuid.uuid4().hex[:8]
        options = [
            int((await self.run(
                f"INSERT INTO {_SCHEMA}.tenant_sales_form_options (tenant_id, label, value) "
                "VALUES (:t, :l, :v) RETURNING id",
                {"t": _TENANT_ID, "l": f"opt-{tag}-{i}", "v": f"opt-{tag}-{i}"},
            ))[0]["id"])
            for i in range(2)
        ]
        reasons = [
            int((await self.run(
                f"INSERT INTO {_SCHEMA}.close_reasons (type, label) VALUES ('won', :l) RETURNING id",
                {"l": f"reason-{tag}-{i}"},
            ))[0]["id"])
            for i in range(2)
        ]
        return {"options": options, "reasons": reasons}

    async def seed(self, table: str, lead_id: int, cat: dict[str, list[int]], slot: int = 0, extra: dict | None = None):
        """表ごとに最小の 1 行を lead_id に置く。slot は選択肢・理由のどちらを使うか。"""
        u = uuid.uuid4().hex
        p = {"l": lead_id, "t": _TENANT_ID, "u": u[:12], "u2": u, "slot": slot}
        if table == "companies":
            await self.run(
                f"INSERT INTO {_SCHEMA}.companies (company_code, lead_id, name) VALUES (:u, :l, :u)", p
            )
        elif table == "contacts":
            company_id = (await self.run(
                f"SELECT id FROM {_SCHEMA}.companies WHERE lead_id = :l ORDER BY id LIMIT 1", p
            ))[0]["id"]
            await self.run(
                f"INSERT INTO {_SCHEMA}.contacts (company_id, contact_code, lead_id, display_name) "
                "VALUES (:c, :u, :l, :u)",
                {**p, "c": company_id},
            )
        elif table == "meta_messages":
            await self.run(f"INSERT INTO {_SCHEMA}.meta_messages (lead_id, sender_id) VALUES (:l, :u)", p)
        elif table == "lead_channels":
            await self.run(
                f"INSERT INTO {_SCHEMA}.lead_channels (lead_id, platform, external_id) VALUES (:l, 'messenger', :u2)", p
            )
        elif table == "conversation_logs":
            await self.run(
                f"INSERT INTO {_SCHEMA}.conversation_logs (tenant_id, lead_id, channel_type, direction, occurred_at) "
                "VALUES (:t, :l, 'messenger', 'inbound', NOW())",
                p,
            )
        elif table == "quotes":
            await self.run(f"INSERT INTO {_SCHEMA}.quotes (lead_id) VALUES (:l)", p)
        elif table == "deal_close_reasons":
            await self.run(
                f"INSERT INTO {_SCHEMA}.deal_close_reasons (lead_id, reason_id) VALUES (:l, :r)",
                {**p, "r": cat["reasons"][slot]},
            )
        elif table == "lead_attachments":
            await self.run(
                f"INSERT INTO {_SCHEMA}.lead_attachments (tenant_id, lead_id, message_id, platform, file_path, file_size) "
                "VALUES (:t, :l, :u, 'messenger', '/x/y', 1)",
                p,
            )
        elif table == "lead_sales_form_selections":
            await self.run(
                f"INSERT INTO {_SCHEMA}.lead_sales_form_selections (lead_id, option_id) VALUES (:l, :o)",
                {**p, "o": cat["options"][slot]},
            )
        elif table == "message_labels":
            await self.run(
                f"INSERT INTO {_SCHEMA}.message_labels (tenant_id, message_id, lead_id, label, confidence, direction) "
                "VALUES (:t, 1, :l, 'other', 0.5, 'inbound')",
                p,
            )
        elif table == "customer_scores":
            await self.run(
                f"INSERT INTO {_SCHEMA}.customer_scores (tenant_id, lead_id, score, confidence, tier) "
                "VALUES (:t, :l, 0.5, 0.5, '有望')",
                p,
            )
        elif table == "outbound_translation_drafts":
            await self.run(
                f"INSERT INTO {_SCHEMA}.outbound_translation_drafts (tenant_id, lead_id, original_text, draft_text, model) "
                "VALUES (:t, :l, 'o', 'd', 'm')",
                p,
            )
        elif table == "registration_tokens":
            await self.run(
                "INSERT INTO public.registration_tokens (tenant_id, lead_id, token_hash, type, expires_at, created_by) "
                "VALUES (:t, :l, :h, 'register', NOW() + INTERVAL '1 day', 1)",
                {**p, "h": (u + uuid.uuid4().hex)[:64]},
            )
        else:  # pragma: no cover
            raise AssertionError(f"seed 未対応の表: {table}")

    async def seed_all(self, lead_id: int, cat: dict[str, list[int]]):
        for spec in LEAD_MERGE_TABLES:  # companies が contacts より前にある並び
            await self.seed(spec.name, lead_id, cat)

    def merge(self, master_id: int, loser_id: int):
        return self.client.post(f"/api/v1/leads/{master_id}/merge", json={"loser_id": loser_id, "reason": "試験"})

    def preview(self, master_id: int, loser_id: int):
        return self.client.post(f"/api/v1/leads/{master_id}/merge/preview", json={"loser_id": loser_id})


def _build_user() -> User:
    u = User()
    u.id = _USER_ID
    u.tenant_id = _TENANT_ID
    u.username = "lead-merge-tester"
    u.email = "lead-merge-tester@example.com"
    u.role = "admin"
    u.is_active = True
    return u


async def _apply_table_migrations(engine) -> None:
    """表と列を作る本物の migration を流す。全テナントを回すものは試験のテナントのスキーマだけに限る。"""
    async with public_bootstrap_lock(engine):  # public の関数・表を同時に作り直さないよう直列にする
        async with engine.begin() as conn:
            for filename, scoped in _TABLE_MIGRATIONS:
                await _apply_migration_on_conn(conn, filename, schema_name=_SCHEMA if scoped else None)


@pytest_asyncio.fixture
async def env():
    global _bootstrapped
    engine = create_async_engine(ADMIN_PG_URL, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            await session.execute(text(f"SET search_path = {_SCHEMA}, public"))
            await session.execute(text("SELECT set_config('app.tenant_id', :t, false)"), {"t": str(_TENANT_ID)})
            await session.execute(text("SELECT set_config('app.is_operator', '', false)"))
            yield session

    app = FastAPI()
    app.include_router(leads_router.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _build_user()
    app.dependency_overrides[get_current_tenant] = lambda: _TENANT_ID

    try:
        async with tenant_schema_lock(engine, _TENANT_ID):
            if not _bootstrapped:
                await bootstrap_tenant_schema(engine, _TENANT_ID)
                await _apply_table_migrations(engine)
                _bootstrapped = True
            # 前の試験の行を消す（この試験用テナントだけ）
            # 監査ログも空にする: leads の番号は RESTART IDENTITY で毎回 1 から振り直されるため、
            # 前の試験の merge_absorb が同じ record_id で残り、件数の確認がずれる
            tenant_tables = [f"{_SCHEMA}.{s.name}" for s in LEAD_MERGE_TABLES if s.schema == "tenant"]
            tenant_tables.append(f"{_SCHEMA}.audit_logs")
            async with engine.begin() as conn:
                await conn.execute(
                    text(f"TRUNCATE {_SCHEMA}.leads, {', '.join(tenant_tables)} RESTART IDENTITY CASCADE")
                )
                await conn.execute(text("DELETE FROM public.registration_tokens WHERE tenant_id = :t"), {"t": _TENANT_ID})
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                yield _Env(engine, client)
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ---------------------------------------------------------------------------
# 13 表・K1・K3
# ---------------------------------------------------------------------------

@requires_pg
@pytest.mark.asyncio
async def test_all_13_tables_are_moved_to_master(env):
    assert len(LEAD_MERGE_TABLES) == 13
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser")
    await env.seed_all(loser, cat)
    for spec in LEAD_MERGE_TABLES:
        assert await env.count(spec.name, loser) == 1, spec.name

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    assert res.json()["id"] == master
    for spec in LEAD_MERGE_TABLES:
        assert await env.count(spec.name, loser) == 0, f"{spec.name}: loser の行が残った"
        assert await env.count(spec.name, master) == 1, f"{spec.name}: master に移っていない"
    assert (await env.run(f"SELECT count(*) AS n FROM {_SCHEMA}.leads WHERE id = :l", {"l": loser}))[0]["n"] == 0


@requires_pg
@pytest.mark.asyncio
async def test_k1_loser_with_conversation_logs_merges_without_error(env):
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser")
    for _ in range(3):
        await env.seed("conversation_logs", loser, cat)

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    assert await env.count("conversation_logs", master) == 3
    assert await env.count("conversation_logs", loser) == 0


@requires_pg
@pytest.mark.asyncio
async def test_k3_attachments_and_sales_form_selections_keep_row_counts(env):
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser")
    for _ in range(2):
        await env.seed("lead_attachments", loser, cat)
    await env.seed("lead_sales_form_selections", loser, cat, slot=0)
    await env.seed("lead_sales_form_selections", loser, cat, slot=1)
    before = {t: await env.total(t) for t in ("lead_attachments", "lead_sales_form_selections")}

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    assert {t: await env.total(t) for t in before} == before
    assert await env.count("lead_attachments", master) == 2
    assert await env.count("lead_sales_form_selections", master) == 2


# ---------------------------------------------------------------------------
# 空欄埋め（K4）・残す方の番号（K5）
# ---------------------------------------------------------------------------

@requires_pg
@pytest.mark.asyncio
async def test_k4_blank_fields_of_master_are_filled_from_loser(env):
    master = await env.lead("master", company_name=None, email="", notes="   ")
    loser = await env.lead("loser", company_name="LoserCo", email="loser@example.com", notes="loser note")

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["company_name"] == "LoserCo"  # NULL は埋まる
    assert body["email"] == "loser@example.com"  # 空文字は埋まる
    assert body["notes"] == "loser note"  # 空白だけは埋まる
    assert body["customer_name"] == "master"


@requires_pg
@pytest.mark.asyncio
async def test_k4_existing_values_and_excluded_fields_are_not_changed(env):
    master = await env.lead("master", company_name="MasterCo", email=None, prospect_rank=None, phone="111")
    loser = await env.lead("loser", company_name="LoserCo", email="", prospect_rank="A", phone="222")

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["company_name"] == "MasterCo"  # 値があれば変えない
    assert body["phone"] == "111"
    assert body["email"] is None  # loser も空なら空のまま
    assert body["prospect_rank"] is None  # prospect_rank は対象外
    assert body["status"] == "lead"  # status は対象外


@requires_pg
@pytest.mark.asyncio
async def test_k5_master_id_is_kept_and_loser_is_gone(env):
    master = await env.lead("master")
    loser = await env.lead("loser")

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    assert res.json()["id"] == master
    again = await env.merge(master, loser)
    assert again.status_code == 404  # 消えた番号は 404


# ---------------------------------------------------------------------------
# 一意の決まりの 4 表
# ---------------------------------------------------------------------------

@requires_pg
@pytest.mark.asyncio
async def test_unique_lead_channels_duplicate_of_loser_is_dropped(env):
    master = await env.lead("master")
    loser = await env.lead("loser")
    # 実際の表は (platform, external_id) が一意なので、重複の分岐を通すために一時的に一意の決まりを外す
    cons = await env.run(
        "SELECT conname, pg_get_constraintdef(oid) AS def FROM pg_constraint "
        f"WHERE conrelid = '{_SCHEMA}.lead_channels'::regclass AND contype = 'u'"
    )
    try:
        for c in cons:
            await env.run(f"ALTER TABLE {_SCHEMA}.lead_channels DROP CONSTRAINT {c['conname']}")
        for lead_id in (master, loser):
            await env.run(
                f"INSERT INTO {_SCHEMA}.lead_channels (lead_id, platform, external_id) VALUES (:l, 'messenger', 'dup-1')",
                {"l": lead_id},
            )
        await env.run(
            f"INSERT INTO {_SCHEMA}.lead_channels (lead_id, platform, external_id) VALUES (:l, 'instagram', 'only-loser')",
            {"l": loser},
        )
        res = await env.merge(master, loser)
        assert res.status_code == 200, res.text
        assert await env.count("lead_channels", loser) == 0
        assert await env.count("lead_channels", master) == 2  # dup-1（master の分）と only-loser
        assert await env.total("lead_channels") == 2
    finally:
        for c in cons:
            await env.run(f"ALTER TABLE {_SCHEMA}.lead_channels ADD CONSTRAINT {c['conname']} {c['def']}")


@requires_pg
@pytest.mark.asyncio
async def test_unique_lead_sales_form_selections_duplicate_of_loser_is_dropped(env):
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser")
    await env.seed("lead_sales_form_selections", master, cat, slot=0)
    await env.seed("lead_sales_form_selections", loser, cat, slot=0)  # master と同じ選択肢
    await env.seed("lead_sales_form_selections", loser, cat, slot=1)

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    assert await env.count("lead_sales_form_selections", loser) == 0
    assert await env.count("lead_sales_form_selections", master) == 2
    assert await env.total("lead_sales_form_selections") == 2


@requires_pg
@pytest.mark.asyncio
async def test_unique_deal_close_reasons_duplicate_of_loser_is_dropped(env):
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser")
    await env.seed("deal_close_reasons", master, cat, slot=0)
    await env.seed("deal_close_reasons", loser, cat, slot=0)  # master と同じ理由
    await env.seed("deal_close_reasons", loser, cat, slot=1)

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    assert await env.count("deal_close_reasons", loser) == 0
    assert await env.count("deal_close_reasons", master) == 2
    assert await env.total("deal_close_reasons") == 2
    # 消えた loser 側の行は、全項目が監査ログ merge_absorb に残る（手で戻す材料）
    audit = await env.run(
        f"SELECT new_data FROM {_SCHEMA}.audit_logs WHERE action = 'merge_absorb' AND record_id = :m",
        {"m": master},
    )
    assert len(audit) == 1
    new_data = audit[0]["new_data"]
    if isinstance(new_data, str):
        new_data = json.loads(new_data)
    assert new_data["deleted_duplicates"]["deal_close_reasons"] == 1
    kept = new_data["deleted_rows"]["deal_close_reasons"]
    assert len(kept) == 1
    assert kept[0]["lead_id"] == loser and "reason_id" in kept[0] and "id" in kept[0]


@requires_pg
@pytest.mark.asyncio
async def test_unique_customer_scores_master_row_wins(env):
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser")
    await env.seed("customer_scores", master, cat)
    master_score_id = (await env.run(f"SELECT id FROM {_SCHEMA}.customer_scores WHERE lead_id = :l", {"l": master}))[0]["id"]
    await env.seed("customer_scores", loser, cat)

    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text
    rows = await env.run(f"SELECT id, lead_id FROM {_SCHEMA}.customer_scores")
    assert [(r["id"], r["lead_id"]) for r in rows] == [(master_score_id, master)]


# ---------------------------------------------------------------------------
# 下見
# ---------------------------------------------------------------------------

@requires_pg
@pytest.mark.asyncio
async def test_preview_does_not_write(env):
    cat = await env.catalogs()
    master = await env.lead("master", company_name=None)
    loser = await env.lead("loser", company_name="LoserCo")
    await env.seed_all(loser, cat)
    totals_before = {s.name: await env.total(s.name) for s in LEAD_MERGE_TABLES}
    leads_before = await env.run(f"SELECT id, company_name, updated_at FROM {_SCHEMA}.leads ORDER BY id")
    audits_before = await env.run(f"SELECT count(*) AS n FROM {_SCHEMA}.audit_logs")

    res = await env.preview(master, loser)
    assert res.status_code == 200, res.text
    body = res.json()
    assert [t["table"] for t in body["tables"]] == [s.name for s in LEAD_MERGE_TABLES]
    assert [f["field"] for f in body["fills"]] == ["company_name"]
    assert body["fills"][0]["new"] == "LoserCo"

    assert {s.name: await env.total(s.name) for s in LEAD_MERGE_TABLES} == totals_before
    assert await env.run(f"SELECT id, company_name, updated_at FROM {_SCHEMA}.leads ORDER BY id") == leads_before
    assert await env.run(f"SELECT count(*) AS n FROM {_SCHEMA}.audit_logs") == audits_before


@requires_pg
@pytest.mark.asyncio
async def test_preview_counts_match_what_merge_does(env):
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser")
    await env.seed_all(loser, cat)
    await env.seed("lead_sales_form_selections", master, cat, slot=0)  # 重複 1 件（loser 側が消える）
    await env.seed("customer_scores", master, cat)  # loser のスコアが消える
    before = {s.name: await env.count(s.name, master) for s in LEAD_MERGE_TABLES}
    totals_before = {s.name: await env.total(s.name) for s in LEAD_MERGE_TABLES}

    preview = (await env.preview(master, loser)).json()
    res = await env.merge(master, loser)
    assert res.status_code == 200, res.text

    for t in preview["tables"]:
        name = t["table"]
        assert await env.count(name, master) == before[name] + t["moved"], name
        assert await env.total(name) == totals_before[name] - t["deleted"], name
    deleted = {t["table"]: t["deleted"] for t in preview["tables"]}
    assert deleted["lead_sales_form_selections"] == 1
    assert deleted["customer_scores"] == 1


# ---------------------------------------------------------------------------
# 異常系
# ---------------------------------------------------------------------------

@requires_pg
@pytest.mark.asyncio
async def test_error_merging_into_itself_is_400(env):
    master = await env.lead("master")
    res = await env.merge(master, master)
    assert res.status_code == 400
    assert await env.count("companies", master) == 0
    assert (await env.run(f"SELECT count(*) AS n FROM {_SCHEMA}.leads WHERE id = :l", {"l": master}))[0]["n"] == 1


@requires_pg
@pytest.mark.asyncio
async def test_error_loser_that_is_not_a_lead_is_400(env):
    cat = await env.catalogs()
    master = await env.lead("master")
    loser = await env.lead("loser", status="existing_customer")
    await env.seed("companies", loser, cat)

    res = await env.merge(master, loser)
    assert res.status_code == 400
    assert await env.count("companies", loser) == 1
    assert (await env.preview(master, loser)).status_code == 400


@requires_pg
@pytest.mark.asyncio
async def test_error_unknown_lead_id_is_404(env):
    master = await env.lead("master")
    res = await env.merge(master, 999999)
    assert res.status_code == 404
    assert (await env.preview(master, 999999)).status_code == 404
