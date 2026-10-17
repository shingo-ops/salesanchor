#!/usr/bin/env python3
"""scripts/ops/container_state.py の試験（ADR-1012 段階3 便E）。docker は差し替え、本物は呼ばない。"""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parent.parent / "ops" / "container_state.py"
spec = importlib.util.spec_from_file_location("container_state", MODULE_PATH)
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


class SummarizeTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(cs.summarize([]), (0, 0))

    def test_running_healthy(self):
        self.assertEqual(cs.summarize([{"Running": True, "Health": {"Status": "healthy"}}]), (1, 0))

    def test_running_unhealthy(self):
        self.assertEqual(cs.summarize([{"Running": True, "Health": {"Status": "unhealthy"}}]), (1, 1))

    def test_stopped_old_unhealthy_not_counted(self):
        states = [
            {"Running": False, "Health": {"Status": "unhealthy"}},
            {"Running": True, "Health": {"Status": "healthy"}},
        ]
        self.assertEqual(cs.summarize(states), (1, 0))

    def test_running_without_health(self):
        self.assertEqual(cs.summarize([{"Running": True}]), (1, 0))


class MainTest(unittest.TestCase):
    def _fake_docker(self, args):
        if args[0] == "ps":
            return "abc\n"
        return json.dumps([{"State": {"Running": True, "Health": {"Status": "unhealthy"}}}])

    def test_main_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(cs, "TEXTFILE_DIR", d), mock.patch.object(cs, "run_docker", side_effect=self._fake_docker):
                rc = cs.main()
            self.assertEqual(rc, 0)
            path = os.path.join(d, "container_state.prom")
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                lines = f.read().splitlines()
            self.assertIn('salesanchor_container_unhealthy{service="celery-beat"} 1', lines)
            self.assertTrue(any(l.startswith("salesanchor_container_state_last_run_timestamp_seconds ") for l in lines))
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o644)
            self.assertEqual([n for n in os.listdir(d) if n.startswith(".container_state.")], [])

    def test_main_docker_error_keeps_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "container_state.prom")
            with open(path, "w") as f:
                f.write("old\n")
            err = subprocess.CalledProcessError(1, ["docker"])
            with mock.patch.object(cs, "TEXTFILE_DIR", d), mock.patch.object(cs, "run_docker", side_effect=err):
                rc = cs.main()
            self.assertEqual(rc, 1)
            with open(path) as f:
                self.assertEqual(f.read(), "old\n")

    def test_main_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            err = subprocess.TimeoutExpired(["docker"], 20)
            with mock.patch.object(cs, "TEXTFILE_DIR", d), mock.patch.object(cs, "run_docker", side_effect=err):
                rc = cs.main()
            self.assertEqual(rc, 1)


class HealthcheckMissingTest(unittest.TestCase):
    def test_none_running(self):
        self.assertEqual(cs.healthcheck_missing([]), 0)

    def test_running_with_health(self):
        self.assertEqual(cs.healthcheck_missing([{"Running": True, "Health": {"Status": "starting"}}]), 0)

    def test_running_without_health(self):
        self.assertEqual(cs.healthcheck_missing([{"Running": True}]), 1)

    def test_stopped_without_health_not_counted(self):
        self.assertEqual(cs.healthcheck_missing([{"Running": False}, {"Running": True, "Health": {"Status": "healthy"}}]), 0)

    def test_main_writes_missing_line(self):
        def fake(args):
            if args[0] == "ps":
                return "abc\n"
            return json.dumps([{"State": {"Running": True}}])

        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(cs, "TEXTFILE_DIR", d), mock.patch.object(cs, "run_docker", side_effect=fake):
                self.assertEqual(cs.main(), 0)
            with open(os.path.join(d, "container_state.prom")) as f:
                lines = f.read().splitlines()
            self.assertIn('salesanchor_container_healthcheck_missing{service="celery-beat"} 1', lines)
            self.assertIn('salesanchor_container_unhealthy{service="celery-beat"} 0', lines)


if __name__ == "__main__":
    unittest.main()
