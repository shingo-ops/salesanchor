"""段5（ADR-1005 段階1）: 新テナントのひな形と、登録された「テナント全体」の migration を流した後の形が、同じであること。

新しいテナントは create_tenant_schema（backend/app/services/tenant.py のひな形）で作られる。
一方、既存テナントの構造は、scripts/run_all_migrations.sh に登録された migration を毎回流して保つ。
この 2 つが食い違うと、新しいテナントは、移行の再実行を待つまで古い形のままになる。
この試験は、食い違いを機械で見つける:
  1. 使い捨ての DB に、共有の public 表を用意し、create_tenant_schema で新しいテナントを作る。
  2. そのテナントの形（表・列の型・既定値・索引）を撮る。
  3. 登録された migration のうち、全テナントを走査するものを、登録順に、そのテナントへ流す。
  4. もう一度形を撮り、変わっていないことを確かめる。変わったものが、ひな形に足りないもの（または余るもの）。
失敗したときの出力が、直す一覧（正確な差）になる。

ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_rls_bootstrap_ordering.py と同じ形）。
別の DB を作るのは、migration のループが「全テナントのスキーマ」を走査するので、並列に動く他の試験の
スキーマに触れないため。流すのは、テナント全体の migration だけ（tenant_004 など固定のスキーマ向けは対象外）。
落ちた migration（public の前提が無い等）は、形を変えないので、一覧の末尾に報告する（差としては数えない）。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.tenant import create_tenant_schema
from tests.rls_bootstrap import _bootstrap_public_shared, _ensure_public_users

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts" / "run_all_migrations.sh"
DB_NAME = "jarvis_tenant_template_parity"
TENANT_ID = 995
SCHEMA = f"tenant_{TENANT_ID:03d}"
# 全テナントを走査する migration の目印（nspname ~ '^tenant_...' のループ、または nspname LIKE 'tenant_%'）
TENANT_LOOP = re.compile(r"nspname\s*(?:~\s*'\^?tenant_|LIKE\s*'tenant_)", re.IGNORECASE)

Snapshot = dict  # {"tables": set[str], "columns": {(table, column): tuple}, "indexes": {(table, name): str}}


def tenant_scoped_migrations() -> list[str]:
    """scripts/run_all_migrations.sh の run_sql のうち、全テナントを走査するもの（登録順）。"""
    files = [ln.split()[1] for ln in RUNNER.read_text(encoding="utf-8").splitlines() if ln.startswith("run_sql ")]
    result = []
    for path in dict.fromkeys(files):
        file = REPO / path
        if file.is_file() and TENANT_LOOP.search(file.read_text(encoding="utf-8")):
            result.append(path)
    return result


def _normalize(value: str | None, schema: str) -> str | None:
    return value.replace(schema, "{schema}") if value else value


async def snapshot(conn, schema: str) -> Snapshot:
    tables = {
        row[0]
        for row in await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :s AND table_type = 'BASE TABLE'"
            ),
            {"s": schema},
        )
    }
    columns = {}
    column_rows = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, udt_name, character_maximum_length, numeric_precision, "
            "numeric_scale, is_nullable, column_default FROM information_schema.columns WHERE table_schema = :s"
        ),
        {"s": schema},
    )
    for row in column_rows:
        if row[0] in tables:
            columns[(row[0], row[1])] = (row[2], row[3], row[4], row[5], row[6], row[7], _normalize(row[8], schema))
    indexes = {}
    for row in await conn.execute(
        text("SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = :s"), {"s": schema}
    ):
        indexes[(row[0], row[1])] = _normalize(row[2], schema)
    return {"tables": tables, "columns": columns, "indexes": indexes}


def _describe(attrs: tuple) -> str:
    data_type, udt, length, precision, scale, nullable, default = attrs
    size = f"({length})" if length else (f"({precision},{scale})" if precision and data_type == "numeric" else "")
    return f"{udt or data_type}{size} null={nullable} default={default}"


def diff_snapshots(before: Snapshot, after: Snapshot) -> list[str]:
    """before → after の差。ひな形にとっては、「+」が足りないもの、「-」が余るもの。"""
    lines: list[str] = []
    added_tables = sorted(after["tables"] - before["tables"])
    for table in added_tables:
        count = sum(1 for (t, _c) in after["columns"] if t == table)
        lines.append(f"+ table {table} ({count} columns)")
    for table in sorted(before["tables"] - after["tables"]):
        lines.append(f"- table {table}")
    for key in sorted(set(after["columns"]) - set(before["columns"])):
        if key[0] in before["tables"]:
            lines.append(f"+ column {key[0]}.{key[1]} {_describe(after['columns'][key])}")
    for key in sorted(set(before["columns"]) - set(after["columns"])):
        if key[0] in after["tables"]:
            lines.append(f"- column {key[0]}.{key[1]} {_describe(before['columns'][key])}")
    for key in sorted(set(before["columns"]) & set(after["columns"])):
        if before["columns"][key] != after["columns"][key]:
            lines.append(
                f"~ column {key[0]}.{key[1]} {_describe(before['columns'][key])} -> {_describe(after['columns'][key])}"
            )
    for key in sorted(set(after["indexes"]) - set(before["indexes"])):
        if key[0] in before["tables"]:
            lines.append(f"+ index {key[0]}.{key[1]}: {after['indexes'][key]}")
    for key in sorted(set(before["indexes"]) - set(after["indexes"])):
        if key[0] in after["tables"]:
            lines.append(f"- index {key[0]}.{key[1]}")
    for key in sorted(set(before["indexes"]) & set(after["indexes"])):
        if before["indexes"][key] != after["indexes"][key]:
            lines.append(f"~ index {key[0]}.{key[1]}: {before['indexes'][key]} -> {after['indexes'][key]}")
    return lines


def summarize(lines: list[str]) -> str:
    def count(prefix: str) -> int:
        return sum(1 for ln in lines if ln.startswith(prefix))

    return (
        f"表 +{count('+ table')} -{count('- table')} / 列 +{count('+ column')} -{count('- column')} ~{count('~ column')} "
        f"/ 索引 +{count('+ index')} -{count('- index')} ~{count('~ index')}"
    )


# ---------------------------------------------------------------- 差の整形（DB 不要。ローカルでも動く）
def test_diff_snapshots_reports_missing_tables_columns_and_indexes():
    before = {
        "tables": {"leads"},
        "columns": {("leads", "id"): ("integer", "int4", None, 32, 0, "NO", "nextval('{schema}.leads_id_seq'::regclass)")},
        "indexes": {("leads", "leads_pkey"): "CREATE UNIQUE INDEX leads_pkey ON {schema}.leads USING btree (id)"},
    }
    after = {
        "tables": {"leads", "calendar_events"},
        "columns": {
            **before["columns"],
            ("leads", "discord_user_id"): ("text", "text", None, None, None, "YES", None),
            ("calendar_events", "id"): ("integer", "int4", None, 32, 0, "NO", None),
        },
        "indexes": {**before["indexes"], ("leads", "idx_leads_discord"): "CREATE INDEX idx_leads_discord ON {schema}.leads (discord_user_id)"},
    }
    lines = diff_snapshots(before, after)
    assert "+ table calendar_events (1 columns)" in lines
    assert any(ln.startswith("+ column leads.discord_user_id text") for ln in lines)
    assert any(ln.startswith("+ index leads.idx_leads_discord") for ln in lines)
    assert diff_snapshots(before, before) == []
    assert summarize(lines) == "表 +1 -0 / 列 +1 -0 ~0 / 索引 +1 -0 ~0"


def test_tenant_scoped_migrations_are_found_in_registration_order():
    files = tenant_scoped_migrations()
    assert len(files) >= 10
    assert files == sorted(set(files), key=files.index)  # 重複なし・登録順
    registered = [ln.split()[1] for ln in RUNNER.read_text(encoding="utf-8").splitlines() if ln.startswith("run_sql ")]
    assert [registered.index(f) for f in files] == sorted(registered.index(f) for f in files)


# ---------------------------------------------------------------- 本体（PostgreSQL。CI で実行）
async def _fresh_database(admin_url: str):
    url = make_url(admin_url)
    maintenance = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with maintenance.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{DB_NAME}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
    await maintenance.dispose()
    return url.set(database=DB_NAME)


async def _drop_database(admin_url: str) -> None:
    maintenance = create_async_engine(make_url(admin_url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with maintenance.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{DB_NAME}" WITH (FORCE)'))
    await maintenance.dispose()


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_fresh_tenant_is_unchanged_by_registered_tenant_migrations():
    new_url = await _fresh_database(ADMIN_PG_URL)
    engine = create_async_engine(new_url, echo=False)
    errored: list[tuple[str, str]] = []
    applied = 0
    try:
        # 1) 共有の public 表と、新しいテナント（create_tenant_schema。tenant.py のひな形）
        async with engine.begin() as conn:
            await _bootstrap_public_shared(conn)
            await _ensure_public_users(conn)
            await conn.execute(
                text(
                    "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) "
                    "VALUES (:t, :c, :c, :c, TRUE) ON CONFLICT (id) DO NOTHING"
                ),
                {"t": TENANT_ID, "c": SCHEMA},
            )
            await create_tenant_schema(conn, TENANT_ID, admin_db=conn)
        # 2) 流す前の形
        async with engine.connect() as conn:
            before = await snapshot(conn, SCHEMA)
        # 3) 登録された、全テナントを走査する migration を、登録順に流す（1 本ごとに別のトランザクション）
        for path in tenant_scoped_migrations():
            sql = (REPO / path).read_text(encoding="utf-8")
            try:
                async with engine.begin() as conn:
                    raw = await conn.get_raw_connection()
                    await raw.driver_connection.execute(sql)
                applied += 1
            except Exception as exc:  # 落ちたものは形を変えない。末尾で報告する
                errored.append((path, str(exc).strip().splitlines()[0][:160]))
        # 4) 流した後の形
        async with engine.connect() as conn:
            after = await snapshot(conn, SCHEMA)
    finally:
        await engine.dispose()
        await _drop_database(ADMIN_PG_URL)

    lines = diff_snapshots(before, after)
    report = [
        f"新テナントの形が、登録された全テナント向け migration（流せた {applied} 本）で変わった: {summarize(lines)}",
        *lines,
        f"--- 流せなかった migration {len(errored)} 本（形を変えないので差には数えない。範囲の情報）---",
        *[f"  {p}: {m}" for p, m in errored],
    ]
    assert not lines, "\n".join(report)
