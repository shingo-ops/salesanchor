#!/usr/bin/env python3
"""check_queue_triggers.py の試験（標準ライブラリの unittest）。

実行: python3 -I scripts/tests/test_check_queue_triggers.py -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ci", "check_queue_triggers.py"
)

GOOD_JOB = """\
name: Good
on:
  pull_request:
  merge_group:
    types: [checks_requested]
jobs:
  check:
    name: good check
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

NO_QUEUE_JOB = """\
name: No queue
on:
  pull_request:
jobs:
  check:
    name: good check
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

ACTION_JOB = """\
name: Old scan
on:
  pull_request:
  merge_group:
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: gitleaks/gitleaks-action@v2
"""

ID_ONLY_JOB = """\
name: Id only
on: [pull_request, merge_group]
jobs:
  id-only-check:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

PREFIX_JOB = """\
name: Prefix
on:
  pull_request:
jobs:
  check:
    name: good check (extra)
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

STATUS_COPY = """\
name: Merge queue guard status
on:
  merge_group:
    types: [checks_requested]
jobs:
  copy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "CONTEXT='guard-authoring/evaluation'"
"""


def run(files, required):
    with tempfile.TemporaryDirectory() as d:
        wdir = os.path.join(d, "workflows")
        os.mkdir(wdir)
        for name, body in files.items():
            with open(os.path.join(wdir, name), "w", encoding="utf-8") as f:
                f.write(body)
        req = os.path.join(d, "required-checks.txt")
        with open(req, "w", encoding="utf-8") as f:
            f.write("".join(f"{n}\t-\n" for n in required))
        p = subprocess.run(
            [sys.executable, "-I", CHECK, "--workflows-dir", wdir, "--required", req],
            capture_output=True, text=True,
        )
        return p.returncode, p.stdout


class CheckQueueTriggersTest(unittest.TestCase):
    def test_all_good_passes(self):
        code, out = run(
            {"good.yml": GOOD_JOB, "id.yml": ID_ONLY_JOB, "queue-guard-status.yml": STATUS_COPY},
            ["good check", "id-only-check", "guard-authoring/evaluation"],
        )
        self.assertEqual(code, 0, out)
        self.assertIn("問題 0 件", out)

    def test_required_without_merge_group_fails(self):
        code, out = run({"x.yml": NO_QUEUE_JOB}, ["good check"])
        self.assertEqual(code, 1, out)
        self.assertIn("merge_group がありません", out)

    def test_gitleaks_action_fails(self):
        code, out = run({"good.yml": GOOD_JOB, "scan.yml": ACTION_JOB}, ["good check"])
        self.assertEqual(code, 1, out)
        self.assertIn("gitleaks/gitleaks-action@v2", out)

    def test_unlisted_status_name_fails(self):
        code, out = run({"good.yml": GOOD_JOB}, ["good check", "someone/status"])
        self.assertEqual(code, 1, out)
        self.assertIn("someone/status", out)

    def test_status_copy_without_merge_group_fails(self):
        code, out = run(
            {"queue-guard-status.yml": STATUS_COPY.replace("merge_group:", "pull_request:")},
            ["guard-authoring/evaluation"],
        )
        self.assertEqual(code, 1, out)

    def test_name_match_is_exact(self):
        code, out = run({"p.yml": PREFIX_JOB}, ["good check"])
        self.assertEqual(code, 1, out)
        self.assertIn("当たりません", out)

    def test_missing_required_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run(
                [sys.executable, "-I", CHECK, "--workflows-dir", d,
                 "--required", os.path.join(d, "none.txt")],
                capture_output=True, text=True,
            )
        self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main()
