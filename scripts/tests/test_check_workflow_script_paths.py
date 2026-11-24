#!/usr/bin/env python3
"""check_workflow_script_paths.py の試験（標準ライブラリの unittest）。

実行: python3 -I scripts/tests/test_check_workflow_script_paths.py -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ci", "check_workflow_script_paths.py"
)

KNOWN = ["scripts/notify/ping.sh", "frontend/scripts/audit.js"]

JOB_DEFAULT_ROOT_PATH = """\
name: Audit
on: workflow_dispatch
jobs:
  audit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Audit
        run: node scripts/audit.js
      - name: Discord
        run: bash scripts/notify/ping.sh "$MSG"
"""

WORKFLOW_DEFAULT_ROOT_PATH = """\
name: Audit
on: workflow_dispatch
defaults:
  run:
    working-directory: frontend
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Discord
        run: bash scripts/notify/ping.sh
"""

CD_BACKEND = """\
name: Cd
on: workflow_dispatch
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Cd then parent
        run: |
          cd backend
          python3 ../scripts/notify/ping.sh
"""

STEP_OVERRIDE = """\
name: Override
on: workflow_dispatch
jobs:
  audit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Root step
        working-directory: .
        run: bash scripts/notify/ping.sh
"""

DOLLAR_PATH = """\
name: Dollar
on: workflow_dispatch
jobs:
  audit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Variable path
        run: bash scripts/${NAME}.sh
      - name: Variable cd
        run: |
          cd "$GITHUB_WORKSPACE"
          bash scripts/notify/ping.sh
"""


def run(workflows, known=KNOWN):
    with tempfile.TemporaryDirectory() as d:
        wdir = os.path.join(d, "workflows")
        os.mkdir(wdir)
        for name, body in workflows.items():
            with open(os.path.join(wdir, name), "w", encoding="utf-8") as f:
                f.write(body)
        listing = os.path.join(d, "known.txt")
        with open(listing, "w", encoding="utf-8") as f:
            f.write("".join(f"{p}\n" for p in known))
        p = subprocess.run(
            [sys.executable, "-I", CHECK, "--workflows-dir", wdir, "--known-files", listing],
            capture_output=True, text=True,
        )
        return p.returncode, p.stdout


class CheckWorkflowScriptPathsTest(unittest.TestCase):
    def test_job_default_frontend_with_root_path_fails(self):
        code, out = run({"audit.yml": JOB_DEFAULT_ROOT_PATH})
        self.assertEqual(code, 1, out)
        self.assertIn("frontend/scripts/notify/ping.sh", out)
        self.assertIn("道の不一致 1 件", out)

    def test_job_default_frontend_with_parent_path_passes(self):
        body = JOB_DEFAULT_ROOT_PATH.replace("bash scripts/notify", "bash ../scripts/notify")
        code, out = run({"audit.yml": body})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 2 件 / 道の不一致 0 件", out)

    def test_workflow_default_frontend_fails(self):
        code, out = run({"audit.yml": WORKFLOW_DEFAULT_ROOT_PATH})
        self.assertEqual(code, 1, out)
        self.assertIn("frontend/scripts/notify/ping.sh", out)

    def test_cd_backend_then_parent_path_passes(self):
        code, out = run({"cd.yml": CD_BACKEND})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 1 件 / 道の不一致 0 件", out)

    def test_step_working_directory_overrides_job_default(self):
        code, out = run({"override.yml": STEP_OVERRIDE})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 1 件 / 道の不一致 0 件", out)

    def test_dollar_path_and_dollar_cd_are_skipped(self):
        code, out = run({"dollar.yml": DOLLAR_PATH})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 0 件 / 道の不一致 0 件", out)

    def test_broken_yaml_fails(self):
        code, out = run({"broken.yml": "jobs: [unclosed\n"})
        self.assertEqual(code, 1, out)
        self.assertIn("読めませんでした", out)

    def test_missing_workflows_dir_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run(
                [sys.executable, "-I", CHECK, "--workflows-dir", os.path.join(d, "none"),
                 "--known-files", os.path.join(d, "none.txt")],
                capture_output=True, text=True,
            )
        self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main()
