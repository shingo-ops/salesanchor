"""値を書く移行 8 本の無効化（ADR-1007 / 移行ランナー再設計 段5 5-1）の試験。

8 本から値を書く文（と #17 の件数の確かめ）を外した。DB 不要の静的な試験。
- 印がある・本文（コメント除く）に値を書く文が残っていない・残すべき構造がある。
- 8 本とも run_all_migrations.sh に登録されたまま（消していない）。
- 利用者のメールアドレス・仕入れ先や人の名前が残っていない。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"
RUNNER = REPO_ROOT / "scripts" / "run_all_migrations.sh"
MARK = "NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15)"

_WRITE = {
    "INSERT": re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    "UPDATE": re.compile(r"\bUPDATE\s+[\w.%\"${}]+\s+(?:AS\s+\w+\s+)?SET\b", re.IGNORECASE),
    "DELETE": re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    "ON CONFLICT": re.compile(r"\bON\s+CONFLICT\b", re.IGNORECASE),
    "RAISE EXCEPTION": re.compile(r"\bRAISE\s+EXCEPTION\b", re.IGNORECASE),
}

# ファイル → (値を書く文として禁止する種類, 残っているべき文字列)
SQL_SPECS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "027_backfill_customer_contact_channels.sql": (("INSERT", "ON CONFLICT"), ()),
    "054_add_users_theme.sql": (("UPDATE",), ("ADD COLUMN IF NOT EXISTS theme",)),
    "098_migrate_customer_discord_to_company_discord.sql": (
        ("INSERT", "ON CONFLICT", "RAISE EXCEPTION"),
        (),
    ),
    "20260622_020000_migrate_conv_only_into_meta_messages.sql": (("INSERT", "ON CONFLICT"), ()),
    "20260903_120000_tcg_unit_evidence_rules_t004.sql": (
        ("INSERT", "ON CONFLICT", "RAISE EXCEPTION"),
        ("CREATE TABLE IF NOT EXISTS %I.tcg_unit_evidence_rules",),
    ),
    "20260905_120000_register_15_suppliers_t004.sql": (("INSERT", "ON CONFLICT"), ()),
    "20260905_150000_record_manual_supplier_fixes_t004.sql": (("INSERT", "ON CONFLICT", "UPDATE"), ()),
    "20260929_120000_fix_source_messages_received_at.sql": (("UPDATE",), ()),
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


@pytest.mark.parametrize("filename", sorted(SQL_SPECS))
def test_neutralized_sql_is_still_registered_in_runner(filename):
    runner = RUNNER.read_text("utf-8")
    assert re.search(rf"^run_sql migrations/{re.escape(filename)}\s*$", runner, re.MULTILINE), (
        f"{filename}: run_all_migrations.sh の登録が外れている"
    )


def test_054_has_no_email_address():
    text = (MIGRATIONS_DIR / "054_add_users_theme.sql").read_text("utf-8")
    assert "@" not in text


@pytest.mark.parametrize(
    "filename",
    [
        "20260905_120000_register_15_suppliers_t004.sql",
        "20260905_150000_record_manual_supplier_fixes_t004.sql",
    ],
)
def test_supplier_and_person_names_are_gone(filename):
    text = (MIGRATIONS_DIR / filename).read_text("utf-8")
    assert re.search(r"name\s*(→|=)\s*'", text) is None
    assert re.search(r"SP0\d{3}\s+'", text) is None
    assert re.search(r"'SP0\d{3}',\s*'", text) is None
