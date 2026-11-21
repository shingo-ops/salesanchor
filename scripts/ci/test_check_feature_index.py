#!/usr/bin/env python3
"""check_feature_index.py・feature_index_lib.py の試験。python3 -I scripts/ci/test_check_feature_index.py"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import feature_index_lib as lib  # noqa: E402

CHECK = HERE / "check_feature_index.py"

HEADER = "# 索引\n\n## 表\n\n| 機能キーワード | 正準 ADR | 設計書 | コードの場所 | 補足 |\n|---|---|---|---|---|\n"
EXCL_HEAD = (
    "\n## 索引に載せない ADR・設計仕様書\n\n"
    "| 番号・ファイル名・フォルダ | 理由（どれに置き換わったか） |\n|---|---|\n"
)
BACKLOG = "\n## ADR 候補バックログ（未起案）\n\n| 課題 | 概要 | 起案優先度 |\n|---|---|---|\n"


def make_repo(index: str, adrs: dict[str, str], specs: list[str], files: dict[str, str] | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp())
    (tmp / "docs" / "adr").mkdir(parents=True)
    (tmp / "docs" / "adr" / "FEATURE-INDEX.md").write_text(index, encoding="utf-8")
    for name, body in adrs.items():
        (tmp / "docs" / "adr" / name).write_text(body, encoding="utf-8")
    for s in specs:
        (tmp / "docs" / "specs" / s).mkdir(parents=True)
        (tmp / "docs" / "specs" / s / "README.md").write_text("x\n", encoding="utf-8")
    for rel, body in (files or {}).items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
    return tmp


def run_check(root: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "-I", str(CHECK), "--root", str(root)], capture_output=True, text=True
    )
    return r.returncode, r.stdout


ADR_A = "# ADR-001: a\n\n| 項目 | 内容 |\n|---|---|\n| **状態** | Accepted |\n"


class CheckTests(unittest.TestCase):
    def good_index(self) -> str:
        return (
            HEADER
            + "| a | ADR-001 | [s](../specs/foo/README.md) | backend/a.py | 補足 |\n"
            + EXCL_HEAD
            + BACKLOG
        )

    def test_good_sample_passes(self):
        root = make_repo(self.good_index(), {"ADR-001-a.md": ADR_A}, ["foo"], {"backend/a.py": "x"})
        rc, out = run_check(root)
        self.assertEqual(rc, 0, out)
        self.assertIn("SUMMARY missing_adr=0 missing_spec=0 dead_glob=0 dup=0", out)

    def test_missing_adr(self):
        root = make_repo(
            self.good_index(),
            {"ADR-001-a.md": ADR_A, "ADR-002-b.md": ADR_A},
            ["foo"],
            {"backend/a.py": "x"},
        )
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("missing_adr=1", out)

    def test_note_column_number_not_counted(self):
        idx = (
            HEADER
            + "| a | ADR-001 | [s](../specs/foo/README.md) | - | ADR-002 を参照 |\n"
            + EXCL_HEAD
            + BACKLOG
        )
        root = make_repo(idx, {"ADR-001-a.md": ADR_A, "ADR-002-b.md": ADR_A}, ["foo"])
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("missing_adr=1", out)

    def test_missing_spec(self):
        root = make_repo(
            self.good_index(), {"ADR-001-a.md": ADR_A}, ["foo", "bar"], {"backend/a.py": "x"}
        )
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("missing_spec=1", out)

    def test_dead_glob(self):
        root = make_repo(self.good_index(), {"ADR-001-a.md": ADR_A}, ["foo"], {"backend/other.py": "x"})
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("dead_glob=1", out)

    def test_backlog_table_not_counted(self):
        idx = self.good_index() + "| ADR-002 の話 | ADR-002 | 中 |\n"
        root = make_repo(
            idx, {"ADR-001-a.md": ADR_A, "ADR-002-b.md": ADR_A}, ["foo"], {"backend/a.py": "x"}
        )
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("missing_adr=1", out)

    def test_same_number_two_files_one_superseded(self):
        sup = "# ADR-003: old\n\n**Status**: Superseded by ADR-1\n"
        live = "# ADR-003: new\n\n| ステータス | Accepted |\n"
        idx = (
            HEADER
            + "| a | ADR-001、ADR-003 | [s](../specs/foo/README.md) | backend/a.py | - |\n"
            + EXCL_HEAD
            + "| ADR-003-old.md | ADR-1 に置き換え |\n"
            + BACKLOG
        )
        root = make_repo(
            idx,
            {"ADR-001-a.md": ADR_A, "ADR-003-old.md": sup, "ADR-003-new.md": live},
            ["foo"],
            {"backend/a.py": "x"},
        )
        rc, out = run_check(root)
        self.assertEqual(rc, 0, out)

    def test_dup_single_file_in_both(self):
        idx = (
            HEADER
            + "| a | ADR-001 | [s](../specs/foo/README.md) | - | - |\n"
            + EXCL_HEAD
            + "| ADR-001 | 理由 |\n"
            + BACKLOG
        )
        root = make_repo(idx, {"ADR-001-a.md": ADR_A}, ["foo"])
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("dup=1", out)


class LibTests(unittest.TestCase):
    def test_glob_star_not_cross_slash(self):
        self.assertTrue(lib.match_glob("backend/*.py", "backend/a.py"))
        self.assertFalse(lib.match_glob("backend/*.py", "backend/a/b.py"))

    def test_glob_doublestar(self):
        self.assertTrue(lib.match_glob("backend/**/b.py", "backend/b.py"))
        self.assertTrue(lib.match_glob("backend/**/b.py", "backend/a/c/b.py"))
        self.assertFalse(lib.match_glob("backend/**/b.py", "backend/a/c/d.py"))

    def test_status_table(self):
        self.assertEqual(lib.status_word("# ADR-1: x\n\n| **状態** | Accepted |\n"), "Accepted")

    def test_status_colon(self):
        self.assertEqual(lib.status_word("# ADR-1: x\n\n**Status**: Superseded by ADR-1\n"), "Superseded")

    def test_status_heading(self):
        self.assertEqual(lib.status_word("# ADR-1: x\n\n## Status\n\nDeprecated\n"), "Deprecated")

    def test_status_japanese(self):
        self.assertEqual(lib.status_word("# ADR-1: x\n\nステータス：廃止（ADR-2 へ）\n"), "廃止")

    def test_status_skips_prose(self):
        self.assertIsNone(lib.status_word("# ADR-1: x\n\n状態を実現する\n"))

    def test_adr_ids(self):
        self.assertEqual(lib.adr_ids_in("**ADR-097** ／ ADR-SA-017"), ["97", "SA-17"])


if __name__ == "__main__":
    unittest.main()
