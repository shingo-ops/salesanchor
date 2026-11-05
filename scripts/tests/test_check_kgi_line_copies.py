#!/usr/bin/env python3
"""scripts/ci/check_kgi_line_copies.py の試験（標準ライブラリのみ・一時フォルダで完結）。

実行: python3 -I scripts/tests/test_check_kgi_line_copies.py -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "..", "ci", "check_kgi_line_copies.py")
REAL_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

KGI = (
    "| ID | 名 | 現在 | 合格ライン | 測り方 |\n"
    "|---|---|---|---|---|\n"
    "| K1 | 行数 | 200行 → 197行 | **210行以下**（200行から変更） | wc |\n"
    "| K9 | 量 | 6.5k → 7.4k | **7.5k 以下**（6.5k から変更） | /context |\n"
    "| K12 | 割合 | 1/20 → 18/20 | **18/20 以上**（10/20 から引き上げ） | 数える |\n"
)
WEEKLY = "K1_LIMIT=210\nK9_LIMIT_TOKENS=7500\nK12_DAYS=90\n  add_ng \"K9>7.5k\"\n"
REQ = "| L1 | K9 ≤ ~~6.5k~~ **7.5k**、K1 ≤ ~~200~~ **210** | x |\n"
WTEST = "check \"T2 RESULT=NG K1>210\" has_re '^RESULT=NG.*K1>210'\n"
MARK = "ひみつの目印文字列ZZZ"


def routines(n=18, name="入口の文書 週次点検"):
    text = "前置き %s …%d/20 以上（docs/specs/doc-agenda-nav/kgi.md の K12）…" % (MARK, n)
    return json.dumps({"version": 1, "items": [{"name": name, "promptText": text}]}, ensure_ascii=False)


class LineCopies(unittest.TestCase):
    def _make(self, d, kgi=KGI, weekly=WEEKLY, req=REQ, wtest=WTEST):
        for rel, text in (
            ("docs/specs/doc-agenda-nav/kgi.md", kgi),
            ("scripts/dev/doc-entry-weekly-check.sh", weekly),
            ("docs/handoff/doc-agenda-nav/library-requirements.md", req),
            ("scripts/dev/test_doc_entry_weekly_check.sh", wtest),
        ):
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)

    def _run(self, root, *extra):
        p = subprocess.run([sys.executable, "-I", CHECK, "--root", root, *extra],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def _case(self, *extra_args, routines_text=None, **files):
        with tempfile.TemporaryDirectory() as d:
            self._make(d, **files)
            args = list(extra_args)
            if routines_text is not None:
                rp = os.path.join(d, "routines.json")
                with open(rp, "w", encoding="utf-8") as f:
                    f.write(routines_text)
                args += ["--routines", rp]
            return self._run(d, *args)

    def test_all_same(self):
        rc, out = self._case()
        self.assertEqual(rc, 0, out)
        self.assertIn("SUMMARY same=6 diff=0 missing=0", out)
        self.assertIn("BASE K1=210 K9=7.5 K12=18", out)

    def test_each_copy_diff(self):
        cases = [
            ("C1", dict(weekly=WEEKLY.replace("K1_LIMIT=210", "K1_LIMIT=200"))),
            ("C2", dict(weekly=WEEKLY.replace("7500", "6500"))),
            ("C3", dict(weekly=WEEKLY.replace("K9>7.5k", "K9>6.5k"))),
            ("C4a", dict(req=REQ.replace("**7.5k**", "**6.5k**"))),
            ("C4b", dict(req=REQ.replace("**210**", "**200**"))),
            ("C5", dict(wtest=WTEST.replace("K1>210", "K1>200"))),
        ]
        for name, files in cases:
            with self.subTest(name):
                rc, out = self._case(**files)
                self.assertEqual(rc, 1, out)
                self.assertRegex(out, r"COPY %s expected=\S+ found=\S+ DIFF" % name)
                self.assertIn("diff=1", out)

    def test_missing_k1_line(self):
        rc, out = self._case(weekly=WEEKLY.replace("K1_LIMIT=210\n", ""))
        self.assertEqual(rc, 1, out)
        self.assertIn("COPY C1 expected=210 found=- MISSING", out)

    def test_struck_through_old_value_ignored(self):
        # ~~200~~ は読まない（読むと C4b が 200 と 210 で DIFF になる）
        rc, out = self._case()
        self.assertEqual(rc, 0, out)
        self.assertIn("COPY C4b expected=210 found=210 SAME", out)

    def test_routines_same(self):
        rc, out = self._case(routines_text=routines(18))
        self.assertEqual(rc, 0, out)
        self.assertIn("COPY C6 expected=18 found=18 SAME", out)
        self.assertIn("SUMMARY same=7 diff=0 missing=0", out)
        self.assertNotIn(MARK, out)

    def test_routines_diff(self):
        rc, out = self._case(routines_text=routines(10))
        self.assertEqual(rc, 1, out)
        self.assertIn("COPY C6 expected=18 found=10 DIFF", out)
        self.assertNotIn(MARK, out)

    def test_routines_file_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self._make(d)
            rc, out = self._run(d, "--routines", os.path.join(d, "nothing.json"))
        self.assertEqual(rc, 1, out)
        self.assertIn("COPY C6 expected=18 found=- MISSING", out)

    def test_routines_name_differs(self):
        rc, out = self._case(routines_text=routines(18, name="別の名前"))
        self.assertEqual(rc, 1, out)
        self.assertIn("COPY C6 expected=18 found=- MISSING", out)
        self.assertNotIn(MARK, out)

    def test_routines_broken_json(self):
        rc, out = self._case(routines_text="{not json")
        self.assertEqual(rc, 1, out)
        self.assertIn("C6 expected=18 found=- MISSING", out)

    def test_base_unreadable(self):
        kgi = "\n".join(l for l in KGI.split("\n") if not l.startswith("| K9 |"))
        rc, out = self._case(kgi=kgi)
        self.assertEqual(rc, 2, out)
        self.assertIn("BASE K9 unreadable", out)

    def test_bad_args(self):
        p = subprocess.run([sys.executable, "-I", CHECK], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)

    def test_real_repo(self):
        rc, out = self._run(REAL_ROOT)
        self.assertEqual(rc, 0, out)
        self.assertIn("SUMMARY same=6 diff=0 missing=0", out)


if __name__ == "__main__":
    unittest.main()
