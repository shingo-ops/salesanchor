"""scripts/check_template_needs_migration.py の試験（カード 5-2c 手順6）。

使い捨ての git 作業場所（tmp_path に git init）で base と head の commit を作り、台本を呼ぶ。
DB は使わない（git と Python の ast だけ）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_template_needs_migration.py"

TENANT_PATH = "backend/app/services/tenant.py"
RUN_ALL_PATH = "scripts/run_all_migrations.sh"
ALLOW_PATH = "scripts/migration-guard/template-only-allowlist.tsv"

TENANT_BASE = '''\
import logging

logger = logging.getLogger(__name__)

# Python の説明（古い）
_TENANT_TABLES_SQL = """
-- SQL の説明（古い）
ALTER TABLE {schema}.items
    ADD COLUMN IF NOT EXISTS id INTEGER;
"""

_RLS_ENABLE_SQL = """
ALTER TABLE {schema}.items ENABLE ROW LEVEL SECURITY;
"""


async def create_tenant_schema(db, tenant_id, admin_db=None):
    """説明（古い）"""
    if tenant_id < 0:
        raise ValueError("負の値（古い）")
    logger.info("作成（古い）")
    grant_sql = f"""
    ALTER DEFAULT PRIVILEGES IN SCHEMA {tenant_id}
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO salesanchor_app;
    """
    await db.execute(grant_sql)
    return "x"
'''

RUN_ALL_BASE = """\
#!/bin/bash
run_sql migrations/20260101_000000_existing.sql
"""


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def commit(repo: Path, msg: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.invalid")
    git(tmp_path, "config", "user.name", "t")
    write(tmp_path, TENANT_PATH, TENANT_BASE)
    write(tmp_path, RUN_ALL_PATH, RUN_ALL_BASE)
    write(tmp_path, "migrations/20260101_000000_existing.sql", "SELECT 1;\n")
    write(tmp_path, ALLOW_PATH, "# 空の許可一覧\n")
    commit(tmp_path, "base")
    return tmp_path


def run_check(repo: Path, base: str, head: str, pr: str = "9999") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", base, "--head", head, "--pr", pr, "--repo", str(repo)],
        capture_output=True,
        text=True,
    )


def add_column(repo: Path) -> None:
    src = (repo / TENANT_PATH).read_text(encoding="utf-8")
    write(repo, TENANT_PATH, src.replace("ADD COLUMN IF NOT EXISTS id INTEGER;", "ADD COLUMN IF NOT EXISTS id INTEGER,\n    ADD COLUMN IF NOT EXISTS note TEXT;"))


def test_a_python_comment_only_passes(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    src = (repo / TENANT_PATH).read_text(encoding="utf-8")
    write(repo, TENANT_PATH, src.replace("# Python の説明（古い）", "# Python の説明（新しい）\n# 追加の説明"))
    head = commit(repo, "head")
    res = run_check(repo, base, head)
    assert res.returncode == 0, res.stdout + res.stderr


def test_a2_sql_comment_docstring_logger_only_passes(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    src = (repo / TENANT_PATH).read_text(encoding="utf-8")
    src = src.replace("-- SQL の説明（古い）", "-- SQL の説明（新しい）\n-- もう1行")
    src = src.replace('"""説明（古い）"""', '"""説明（新しい）"""')
    src = src.replace('logger.info("作成（古い）")', 'logger.info("作成（新しい）")')
    write(repo, TENANT_PATH, src)
    head = commit(repo, "head")
    res = run_check(repo, base, head)
    assert res.returncode == 0, res.stdout + res.stderr


def test_b_template_column_without_migration_fails(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    add_column(repo)
    head = commit(repo, "head")
    res = run_check(repo, base, head)
    assert res.returncode == 1
    assert "_TENANT_TABLES_SQL" in res.stdout


def test_c_registered_new_migration_passes(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    add_column(repo)
    write(repo, "migrations/20260201_000000_add_note.sql", "SELECT 1;\n")
    write(repo, RUN_ALL_PATH, RUN_ALL_BASE + "run_sql migrations/20260201_000000_add_note.sql\n")
    head = commit(repo, "head")
    res = run_check(repo, base, head)
    assert res.returncode == 0, res.stdout + res.stderr


def test_d_unregistered_new_migration_fails(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    add_column(repo)
    write(repo, "migrations/20260201_000000_add_note.sql", "SELECT 1;\n")
    head = commit(repo, "head")
    res = run_check(repo, base, head)
    assert res.returncode == 1
    assert "_TENANT_TABLES_SQL" in res.stdout


def test_e_allowlisted_pr_passes(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    add_column(repo)
    write(repo, ALLOW_PATH, "# 空の許可一覧\n9999\tmigrations/20260101_000000_existing.sql が既に同じ物を作る\n")
    head = commit(repo, "head")
    res = run_check(repo, base, head, pr="9999")
    assert res.returncode == 0, res.stdout + res.stderr


def test_f_default_privileges_change_fails(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    src = (repo / TENANT_PATH).read_text(encoding="utf-8")
    write(repo, TENANT_PATH, src.replace("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES", "GRANT SELECT ON TABLES"))
    head = commit(repo, "head")
    res = run_check(repo, base, head)
    assert res.returncode == 1
    assert "create_tenant_schema" in res.stdout
