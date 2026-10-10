"""scripts/check-migration-value-writes.py と scripts/migration-dryrun-report.py の試験。

一時的な git リポジトリを作り、BASE / HEAD の差分に対して検査を流し、終了コードと出力を確かめる（ネットワーク・DB 不要）。
実行: python3 -m unittest scripts/tests/test_migration_value_writes.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "scripts" / "check-migration-value-writes.py"
REPORT = REPO / "scripts" / "migration-dryrun-report.py"
TABLES = REPO / "scripts" / "migration-guard" / "protected-tables.txt"

STRUCTURE_ONLY = "ALTER TABLE public.products ADD COLUMN IF NOT EXISTS x INTEGER;\n"
VALUE_WRITING = """DO $$
BEGIN
    INSERT INTO public.permissions (key) VALUES ('a.b');
END $$;
"""
NEUTRALIZED = """-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07): 権限キーの INSERT を外した。
DO $$ BEGIN RAISE NOTICE 'neutralized'; END $$;
"""


class TempRepo:
    """scripts/ に検査の本体と保護対象の一覧を置いた、一時的な git リポジトリ。"""

    def __init__(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="mg-test-"))
        (self.dir / "scripts" / "migration-guard").mkdir(parents=True)
        (self.dir / "migrations").mkdir()
        shutil.copy(CHECK, self.dir / "scripts" / "check-migration-value-writes.py")
        shutil.copy(REPORT, self.dir / "scripts" / "migration-dryrun-report.py")
        shutil.copy(TABLES, self.dir / "scripts" / "migration-guard" / "protected-tables.txt")
        (self.dir / "scripts" / "run_all_migrations.sh").write_text("#!/bin/bash\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.dir, capture_output=True, text=True, check=True).stdout.strip()

    def write(self, path: str, text: str) -> None:
        target = self.dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def register(self, *names: str) -> None:
        runner = self.dir / "scripts" / "run_all_migrations.sh"
        runner.write_text(
            "#!/bin/bash\n" + "".join(f"run_sql migrations/{n}\n" for n in names), encoding="utf-8"
        )

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/check-migration-value-writes.py", *args], cwd=self.dir, capture_output=True, text=True
        )

    def cleanup(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class DiffMode(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.repo.write("migrations/20260101_000000_a.sql", VALUE_WRITING)
        self.base = self.repo.commit("base")

    def diff(self, check: str = "all") -> subprocess.CompletedProcess[str]:
        head = self.repo.commit("change")
        return self.repo.run("diff", self.base, head, "--check", check)

    def test_neutralization_edit_passes(self) -> None:
        """値の書き込みを外し、コメントと NOTICE を足す編集は通る（#3544 の形）。"""
        self.repo.write("migrations/20260101_000000_a.sql", NEUTRALIZED)
        result = self.diff()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("チェック7 通過", result.stdout)

    def test_added_insert_on_protected_table_fails(self) -> None:
        self.repo.write("migrations/20260101_000000_a.sql", VALUE_WRITING + "INSERT INTO public.permissions (key) VALUES ('x');\n")
        result = self.diff("7")
        self.assertEqual(result.returncode, 1)
        self.assertIn("MIGRATION GUARD FAILED (チェック7)", result.stdout)
        self.assertIn("20260101_000000_a.sql", result.stdout)

    def test_added_update_on_products_fails(self) -> None:
        self.repo.write("migrations/20260101_000000_a.sql", VALUE_WRITING + "UPDATE public.products SET mark = 'M3';\n")
        self.assertEqual(self.diff("7").returncode, 1)

    def test_added_dynamic_schema_insert_fails(self) -> None:
        """tenant ループの動的なスキーマ名（%I.）でも見逃さない（今のチェック 7 の穴）。"""
        self.repo.write(
            "migrations/20260101_000000_a.sql",
            VALUE_WRITING + "EXECUTE format('INSERT INTO %I.tcg_products (code) VALUES (1)', s);\n",
        )
        self.assertEqual(self.diff("7").returncode, 1)

    def test_reindented_existing_write_is_not_flagged(self) -> None:
        """字下げだけの変更（同じ文面が削除側にもある）は、新しい値の書き込みとは数えない。"""
        self.repo.write("migrations/20260101_000000_a.sql", VALUE_WRITING.replace("    INSERT", "        INSERT"))
        self.assertEqual(self.diff("7").returncode, 0)

    def test_added_select_from_protected_table_fails_check8_but_structure_passes(self) -> None:
        self.repo.write("migrations/20260101_000000_a.sql", VALUE_WRITING + "SELECT id FROM public.products WHERE id = 1;\n")
        self.assertEqual(self.diff("8").returncode, 1)

    def test_added_structure_change_passes_check8(self) -> None:
        self.repo.write("migrations/20260101_000000_a.sql", VALUE_WRITING + STRUCTURE_ONLY)
        self.assertEqual(self.diff("8").returncode, 0)

    def test_new_file_with_insert_fails_and_structure_only_passes(self) -> None:
        self.repo.write("migrations/20260102_000000_b.sql", VALUE_WRITING)
        self.assertEqual(self.diff("7").returncode, 1)
        self.repo.write("migrations/20260102_000000_b.sql", STRUCTURE_ONLY)
        self.assertEqual(self.diff("all").returncode, 0)

    def test_word_boundary_does_not_flag_similar_names(self) -> None:
        self.repo.write(
            "migrations/20260101_000000_a.sql",
            VALUE_WRITING
            + "INSERT INTO public.products_category_classification_backup (id) VALUES (1);\n"
            + "SELECT 1 FROM tenant_001.role_permissions;\n",
        )
        self.assertEqual(self.diff("all").returncode, 0)

    def test_no_migration_change_is_a_pass(self) -> None:
        self.repo.write("README.md", "x\n")
        result = self.diff()
        self.assertEqual(result.returncode, 0)
        self.assertIn("スキップ", result.stdout)


class RepoMode(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.repo.write("migrations/20260101_000000_a.sql", VALUE_WRITING)
        self.repo.write("migrations/20260101_000100_b.sql", STRUCTURE_ONLY)
        self.repo.register("20260101_000000_a.sql", "20260101_000100_b.sql")

    def allowlist(self, *rows: tuple[str, str]) -> None:
        text = "# test\n" + "".join(f"migrations/{f}\t{t}\ttest reason\ttest ref\n" for f, t in rows)
        self.repo.write("scripts/migration-guard/value-write-allowlist.tsv", text)

    def test_flagged_file_not_in_allowlist_fails(self) -> None:
        self.allowlist()
        result = self.repo.run("repo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("許可一覧にない値の書き込み", result.stdout)

    def test_flagged_file_in_allowlist_passes(self) -> None:
        self.allowlist(("20260101_000000_a.sql", "permissions"))
        result = self.repo.run("repo")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("全件走査 通過", result.stdout)

    def test_stale_allowlist_row_fails(self) -> None:
        self.allowlist(("20260101_000000_a.sql", "permissions"), ("20260101_000100_b.sql", "products"))
        result = self.repo.run("repo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("古い行", result.stdout)

    def test_row_for_unregistered_file_fails(self) -> None:
        self.repo.write("migrations/20260101_000200_c.sql", VALUE_WRITING)
        self.allowlist(("20260101_000000_a.sql", "permissions"), ("20260101_000200_c.sql", "permissions"))
        result = self.repo.run("repo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("登録されていない", result.stdout)

    def test_tables_mismatch_fails(self) -> None:
        self.allowlist(("20260101_000000_a.sql", "products"))
        result = self.repo.run("repo")
        self.assertEqual(result.returncode, 1)
        self.assertIn("tables が実際と違う", result.stdout)

    def test_neutralized_file_with_its_row_removed_passes(self) -> None:
        self.repo.write("migrations/20260101_000000_a.sql", NEUTRALIZED)
        self.allowlist()
        self.assertEqual(self.repo.run("repo").returncode, 0)


class DryrunReport(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo()
        self.addCleanup(self.repo.cleanup)
        self.names = ["20260101_000000_a.sql", "20260101_000100_b.sql", "20260101_000200_c.sql"]
        for name in self.names:
            self.repo.write(f"migrations/{name}", "SELECT 1;\n")
        self.repo.register(*self.names)

    def exclusions(self, *files: str) -> None:
        text = "# test\n" + "".join(f"migrations/{f}\ttest reason\ttest ref\n" for f in files)
        self.repo.write("scripts/migration-guard/dryrun-exclusions.tsv", text)

    def report(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/migration-dryrun-report.py", *args], cwd=self.repo.dir, capture_output=True, text=True
        )

    def test_set_is_registered_minus_exclusions(self) -> None:
        self.exclusions(self.names[0])
        result = self.report("set")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), [f"migrations/{n}" for n in self.names[1:]])

    def test_exclusion_for_unregistered_file_is_rejected(self) -> None:
        self.exclusions("nope.sql")
        result = self.report("set")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("登録されていない除外", result.stderr + result.stdout)

    def test_run_reports_failures_but_exits_zero(self) -> None:
        """報告のみ: 落ちたファイルがあっても終了コードは 0。"""
        self.exclusions(self.names[0])
        fake = self.repo.dir / "fake-psql.sh"
        fake.write_text('#!/bin/bash\ncase "$*" in *"%s"*) echo "ERROR: relation x does not exist" >&2; exit 3;; esac\nexit 0\n' % self.names[1])
        fake.chmod(0o755)
        result = self.report("run", "--db", "x", "--rounds", "1", "--psql", str(fake))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("対象 2 ファイル", result.stdout)
        self.assertIn("❌ [1周目 1/2]", result.stdout)
        self.assertIn("1周目: 成功 1 / 失敗 1", result.stdout)


class RealRepo(unittest.TestCase):
    """この PR が入ったリポジトリそのものを検査する。"""

    def test_repo_scan_passes_with_the_committed_allowlist(self) -> None:
        result = subprocess.run([sys.executable, str(CHECK), "repo"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_dryrun_exclusions_are_valid(self) -> None:
        result = subprocess.run([sys.executable, str(REPORT), "set"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip())

    def test_protected_tables_include_the_four_added_masters(self) -> None:
        names = {ln.strip() for ln in TABLES.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}
        for table in ("product_lines", "product_formats", "product_kinds", "supplier_aliases"):
            self.assertIn(table, names)
        self.assertEqual(len(names), 27)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    unittest.main()
