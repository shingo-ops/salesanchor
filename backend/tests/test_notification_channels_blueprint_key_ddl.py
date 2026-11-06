"""discord-server-management 第2段 2c: notification_channels.blueprint_key の移行の試験（文字として読むだけ・DB を使わない）。

- 移行ファイルが在り、run_all_migrations.sh に 1 行だけ登録され、必要な文があり、値を入れない。
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261106_210000_add_notification_channels_blueprint_key.sql"


def _body() -> str:
    return (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")


def test_migration_file_exists():
    assert (_REPO_ROOT / "migrations" / _MIGRATION).is_file()


def test_migration_registered_exactly_once():
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1


def test_migration_has_column_and_partial_unique_index():
    body = _body()
    assert "ADD COLUMN IF NOT EXISTS blueprint_key TEXT" in body
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_channels_blueprint_key" in body
    assert "WHERE blueprint_key IS NOT NULL" in body


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT / UPDATE を含まない）。"""
    code = "\n".join(
        line for line in _body().splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT ", "UPDATE "):
        assert word not in code
