"""値を書く migration の無効化（ADR-1007 決定2・PR-3c）の試験。

run_py が毎デプロイ流す SQL（12 本）と Python（5 本）から、値を書く文を外した。
- SQL: 印がある・値を書く文が残っていない・構造（DDL）は残っている（DB 不要の静的な試験）。
- Python: run_py の入口 main() が、DB に触れずに終わる。adr119 と country は、試験が import する
  backfill_schema を、関数として残している。
"""

from __future__ import annotations

import asyncio
import importlib.util
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"
SCRIPTS_DIR = REPO_ROOT / "scripts"
MARK = "NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07)"

_WRITE = {
    "INSERT": re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    "UPDATE": re.compile(r"\bUPDATE\s+[\w.%\"${}]+\s+(?:AS\s+\w+\s+)?SET\b", re.IGNORECASE),
    "DELETE": re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    "ON CONFLICT": re.compile(r"\bON\s+CONFLICT\b", re.IGNORECASE),
}

# ファイル → (値を書く文として禁止する種類, 残っているべき構造の文字列)
SQL_SPECS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "042_seed_meta_inbox_permissions.sql": (("INSERT", "ON CONFLICT"), ()),
    "051_remove_confirmed_status.sql": (("UPDATE",), ()),
    "055_add_granted_scopes.sql": (("UPDATE",), ("ADD COLUMN IF NOT EXISTS granted_scopes",)),
    "056_add_suppliers_type_and_promote_public.sql": (
        ("INSERT", "ON CONFLICT"),
        ("CREATE TABLE IF NOT EXISTS public.suppliers", "set_updated_at_suppliers"),
    ),
    "063_tenant_rbac_extensions.sql": (("INSERT", "ON CONFLICT"), ("ADD COLUMN",)),
    "064_add_users_is_super_admin.sql": (
        ("UPDATE",),
        ("ADD COLUMN IF NOT EXISTS is_super_admin", "idx_users_super_admin_partial"),
    ),
    "065_seed_central_admin_permissions.sql": (("INSERT", "ON CONFLICT"), ()),
    "066_add_tenant_llm_budgets_notification_dedupe.sql": (("INSERT", "ON CONFLICT"), ("ADD COLUMN",)),
    "067_add_inbound_review_version_and_permissions.sql": (("INSERT", "ON CONFLICT"), ("ADD COLUMN",)),
    "069_create_tenant_profile.sql": (("INSERT", "ON CONFLICT"), ("CREATE TABLE IF NOT EXISTS",)),
    "070_add_spreadsheet_phase.sql": (("INSERT", "ON CONFLICT"), ("CREATE TRIGGER", "ADD COLUMN spreadsheet_phase")),
}


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", sql)


@pytest.mark.parametrize("filename", sorted(SQL_SPECS))
def test_neutralized_sql_has_mark_no_value_writes_and_keeps_structure(filename):
    forbidden, kept = SQL_SPECS[filename]
    sql = (MIGRATIONS_DIR / filename).read_text("utf-8")
    body = _strip_sql_comments(sql)

    assert MARK in sql
    for kind in forbidden:
        assert _WRITE[kind].search(body) is None, f"{filename}: 値を書く文 ({kind}) が残っている"
    for text in kept:
        assert text in body, f"{filename}: 構造 ({text}) が消えている"


def test_044_keeps_trigger_and_function_but_not_the_backfill():
    sql = (MIGRATIONS_DIR / "044_create_meta_page_routing_trigger.sql").read_text("utf-8")
    body = _strip_sql_comments(sql)

    assert MARK in sql
    # 構造: 同期の関数とトリガー（関数の本文の INSERT … ON CONFLICT は 1 つだけ残る）
    assert "CREATE TRIGGER trg_sync_meta_page_routing" in body
    assert "CREATE OR REPLACE FUNCTION" in body
    assert len(re.findall(r"ON CONFLICT \(tenant_id, config_id\) DO UPDATE", body)) == 1
    # 値: 既存行の backfill（トップレベルの INSERT … SELECT … FROM {schema}.tenant_meta_config）は無い
    assert re.search(r"FROM\s+\{schema\}\.tenant_meta_config\s+ON\s+CONFLICT", body, re.IGNORECASE) is None


def test_064_keeps_the_column_but_never_regrants_super_admin():
    sql = (MIGRATIONS_DIR / "064_add_users_is_super_admin.sql").read_text("utf-8")
    body = _strip_sql_comments(sql)

    assert "ADD COLUMN IF NOT EXISTS is_super_admin" in body
    assert _WRITE["UPDATE"].search(body) is None
    assert "@" not in body  # メールアドレスを本文に書かない


# --- Python（run_py の入口だけを止める）---------------------------------------------------------
PY_ENTRYPOINTS = [
    "migrate_073_lead_status.py",
    "migrate_20260620_080000_calendar_category_backfill.py",
    "migrate_adr109_status_codes.py",
    "migrate_adr119_lead_channels_backfill.py",
    "migrate_20260621_020000_backfill_lead_country.py",
]


def _load_script(filename: str):
    spec = importlib.util.spec_from_file_location(f"neutralized_{filename[:-3]}", SCRIPTS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("filename", PY_ENTRYPOINTS)
def test_python_main_does_not_touch_the_database(filename, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://nobody:none@127.0.0.1:1/none")
    module = _load_script(filename)

    def _forbidden(*args, **kwargs):
        raise AssertionError(f"{filename}: main() が DB に接続しようとした")

    monkeypatch.setattr(module, "create_async_engine", _forbidden, raising=False)
    asyncio.run(module.main())  # 例外・sys.exit なしで終わる

    source = (SCRIPTS_DIR / filename).read_text("utf-8")
    assert MARK in source
    assert 'if __name__ == "__main__":' in source


@pytest.mark.parametrize("filename", PY_ENTRYPOINTS)
def test_python_main_without_database_url_is_a_noop_not_an_error(filename, monkeypatch):
    # 以前は DATABASE_URL が無いと sys.exit(1) でデプロイの migration を止めた
    monkeypatch.delenv("DATABASE_URL", raising=False)
    module = _load_script(filename)

    asyncio.run(module.main())


@pytest.mark.parametrize(
    "filename",
    ["migrate_adr119_lead_channels_backfill.py", "migrate_20260621_020000_backfill_lead_country.py"],
)
def test_backfill_schema_is_kept_as_a_library_function(filename):
    # 試験（test_adr119_backfill_source_guard.py、test_lead_country_control.py）が import する
    assert callable(_load_script(filename).backfill_schema)


# --- 試験が自分で入れる seed（063・069 を入力にしていた TEST_PG_URL の試験用）-------------------------
def test_inventory_visibility_seed_sql_has_the_four_keys():
    from tests.seed_inventory_data import inventory_visibility_permissions_seed_sql

    sql = inventory_visibility_permissions_seed_sql()
    for key in (
        "inventory.visibility.full",
        "inventory.visibility.staff",
        "inventory.visibility.viewer",
        "tenant.inventory_visibility.edit",
    ):
        assert f"('{key}'," in sql
    assert sql.rstrip().endswith("ON CONFLICT (key) DO NOTHING")


def test_tenant_profile_seed_sql_has_two_keys_and_a_checked_default_row():
    from tests.seed_inventory_data import tenant_profile_default_row_sql, tenant_profile_permissions_seed_sql

    sql = tenant_profile_permissions_seed_sql()
    assert "('tenant.profile.view'," in sql and "('tenant.profile.edit'," in sql
    assert tenant_profile_default_row_sql("tenant_901").startswith("INSERT INTO tenant_901.tenant_profile")
    with pytest.raises(ValueError):
        tenant_profile_default_row_sql("public; DROP")
