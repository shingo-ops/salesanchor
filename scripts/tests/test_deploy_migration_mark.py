#!/usr/bin/env python3
"""scripts/ops/deploy_migration_mark.py と deploy.yml の手順の試験（ADR-1012 段階3 便H）。"""

import contextlib
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE.parent / "ops" / "deploy_migration_mark.py"
DEPLOY_YML = HERE / ".." / ".." / ".github" / "workflows" / "deploy.yml"
spec = importlib.util.spec_from_file_location("deploy_migration_mark", MODULE_PATH)
dmm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmm)

SUCCESS_METRIC = "salesanchor_deploy_migration_last_success_timestamp_seconds"
FAILURE_METRIC = "salesanchor_deploy_migration_last_failure_timestamp_seconds"
STEP_NAME = "- name: Record migration result (ADR-1012 段階3 便H)"


def run_main(argv, textfile_dir):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(dmm, "TEXTFILE_DIR", textfile_dir), mock.patch.object(
        dmm.time, "time", return_value=1700000000.7
    ), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = dmm.main(argv)
    return rc, out.getvalue(), err.getvalue()


class MarkTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_01_success_writes_success_file(self):
        rc, out, _ = run_main(["x", "success"], self.dir)
        self.assertEqual(rc, 0)
        with open(self.path("deploy_migration_success.prom"), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith(f"# HELP {SUCCESS_METRIC} "))
        self.assertEqual(lines[1], f"# TYPE {SUCCESS_METRIC} gauge")
        self.assertEqual(lines[2], f"{SUCCESS_METRIC} 1700000000")
        self.assertFalse(os.path.exists(self.path("deploy_migration_failure.prom")))
        self.assertEqual(len(out.splitlines()), 1)

    def test_02_failure_writes_failure_file(self):
        rc, _, _ = run_main(["x", "failure"], self.dir)
        self.assertEqual(rc, 0)
        with open(self.path("deploy_migration_failure.prom"), encoding="utf-8") as f:
            self.assertIn(f"{FAILURE_METRIC} 1700000000", f.read().splitlines())
        self.assertFalse(os.path.exists(self.path("deploy_migration_success.prom")))

    def test_03_cancelled_writes_failure_file(self):
        rc, _, _ = run_main(["x", "cancelled"], self.dir)
        self.assertEqual(rc, 0)
        with open(self.path("deploy_migration_failure.prom"), encoding="utf-8") as f:
            self.assertIn(f"{FAILURE_METRIC} 1700000000", f.read().splitlines())
        self.assertFalse(os.path.exists(self.path("deploy_migration_success.prom")))

    def test_04_failure_leaves_success_file_untouched(self):
        run_main(["x", "success"], self.dir)
        with open(self.path("deploy_migration_success.prom"), "rb") as f:
            before = f.read()
        run_main(["x", "failure"], self.dir)
        with open(self.path("deploy_migration_success.prom"), "rb") as f:
            after = f.read()
        self.assertEqual(before, after)

    def test_05_bad_args_return_2(self):
        cases = [
            ["x", "skipped"],
            ["x", ""],
            ["x", "SUCCESS"],
            ["x"],
            ["x", "success", "failure"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                rc, _, err = run_main(argv, self.dir)
                self.assertEqual(rc, 2)
                self.assertEqual(os.listdir(self.dir), [])
                self.assertEqual(len(err.splitlines()), 1)

    def test_06_missing_dir_returns_1(self):
        missing = os.path.join(self.dir, "no_such_dir")
        rc, _, err = run_main(["x", "success"], missing)
        self.assertEqual(rc, 1)
        self.assertEqual(len(err.splitlines()), 1)
        self.assertTrue(err.startswith("deploy_migration_mark: write failed:"))

    def test_07_mode_644_and_no_tmp_left(self):
        run_main(["x", "success"], self.dir)
        mode = os.stat(self.path("deploy_migration_success.prom")).st_mode & 0o777
        self.assertEqual(mode, 0o644)
        self.assertEqual([n for n in os.listdir(self.dir) if n.startswith(".deploy_migration.")], [])

    def test_08_replace_error_cleans_tmp(self):
        with mock.patch.object(dmm.os, "replace", side_effect=OSError("boom")):
            rc, _, _ = run_main(["x", "failure"], self.dir)
        self.assertEqual(rc, 1)
        self.assertEqual([n for n in os.listdir(self.dir) if n.startswith(".deploy_migration.")], [])


class DeployYmlTest(unittest.TestCase):
    def setUp(self):
        with open(DEPLOY_YML, encoding="utf-8") as f:
            self.lines = f.read().splitlines()

    def step_index(self):
        idx = [i for i, ln in enumerate(self.lines) if ln.strip() == STEP_NAME]
        self.assertEqual(len(idx), 1)
        return idx[0]

    def test_09_step_position(self):
        i = self.step_index()
        migrate = [n for n, ln in enumerate(self.lines) if ln.strip() == "id: migrate"]
        cleanup = [n for n, ln in enumerate(self.lines) if ln.strip() == "- name: Clean up DB orphans after failure"]
        smoke = [n for n, ln in enumerate(self.lines) if ln.strip() == "- name: Post-deploy smoke tests (SA-19)"]
        self.assertEqual(len(migrate), 1)
        self.assertEqual(len(cleanup), 1)
        self.assertEqual(len(smoke), 1)
        self.assertGreater(i, migrate[0])
        self.assertGreater(i, cleanup[0])
        self.assertLess(i, smoke[0])

    def test_10_step_body(self):
        i = self.step_index()
        j = i + 1
        while j < len(self.lines) and not self.lines[j].lstrip().startswith("- name:"):
            j += 1
        body_lines = self.lines[i:j]
        body = "\n".join(body_lines)
        for needle in (
            "always()",
            "steps.migrate.outcome == 'success'",
            "steps.migrate.outcome == 'failure'",
            "steps.migrate.outcome == 'cancelled'",
            "continue-on-error: true",
            "command_timeout: 2m",
            "scripts/ops/deploy_migration_mark.py ${{ steps.migrate.outcome }}",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, body)
        if_lines = [ln for ln in body_lines if ln.strip().startswith("if:")]
        self.assertTrue(if_lines)
        for ln in if_lines:
            self.assertNotIn("skipped", ln)


if __name__ == "__main__":
    unittest.main()
