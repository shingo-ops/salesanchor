#!/usr/bin/env python3
"""monitoring/scripts/check_app_healthchecks.py の試験（ADR-1012 段階3 定着便 T1）。"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


chk = load("check_app_healthchecks", HERE.parent / "check_app_healthchecks.py")
cs = load("container_state", REPO / "scripts" / "ops" / "container_state.py")

try:
    import yaml
except ImportError:
    yaml = None

GOOD = {"test": ["CMD-SHELL", "exit 0"], "interval": "30s"}


def compose_with(**overrides):
    services = {name: {"image": "x", "healthcheck": dict(GOOD)} for name in chk.TARGETS}
    services.update(overrides)
    return {"services": services}


class ProblemsTest(unittest.TestCase):
    def test_all_good(self):
        self.assertEqual(chk.problems(compose_with()), [])

    def test_string_test_is_good(self):
        self.assertEqual(chk.problems(compose_with(**{"celery-beat": {"healthcheck": {"test": "exit 0"}}})), [])

    def test_missing_healthcheck(self):
        found = chk.problems(compose_with(**{"celery-beat": {"image": "x"}}))
        self.assertEqual(found, ["celery-beat: healthcheck がありません"])

    def test_disable_true(self):
        found = chk.problems(compose_with(**{"discord-gateway": {"healthcheck": {"disable": True}}}))
        self.assertEqual(found, ["discord-gateway: healthcheck が disable: true です"])

    def test_none(self):
        found = chk.problems(compose_with(**{"gemini-egress": {"healthcheck": {"test": ["NONE"]}}}))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("gemini-egress: healthcheck の test が空か NONE です"))

    def test_empty_string(self):
        found = chk.problems(compose_with(**{"celery-worker": {"healthcheck": {"test": "  "}}}))
        self.assertEqual(len(found), 1)

    def test_cmd_shell_without_command(self):
        found = chk.problems(compose_with(**{"celery-worker": {"healthcheck": {"test": ["CMD-SHELL"]}}}))
        self.assertEqual(len(found), 1)

    def test_missing_service(self):
        c = compose_with()
        del c["services"]["celery-beat"]
        self.assertEqual(chk.problems(c), ["celery-beat: サービスがありません"])

    def test_targets_match_container_state(self):
        self.assertEqual(set(chk.TARGETS), set(cs.SERVICES) - {"backend"})


@unittest.skipIf(yaml is None, "pyyaml が無い（CI では入る）")
class RealFileTest(unittest.TestCase):
    def test_real_compose_passes(self):
        self.assertEqual(chk.main(["x", str(REPO / "docker-compose.yml")]), 0)

    def test_broken_copy_fails(self):
        with open(REPO / "docker-compose.yml", encoding="utf-8") as f:
            compose = yaml.safe_load(f)
        for broken in ("remove", "none", "disable"):
            c = yaml.safe_load(yaml.safe_dump(compose))
            if broken == "remove":
                del c["services"]["celery-beat"]["healthcheck"]
            elif broken == "none":
                c["services"]["celery-beat"]["healthcheck"]["test"] = ["NONE"]
            else:
                c["services"]["celery-beat"]["healthcheck"]["disable"] = True
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "docker-compose.yml")
                with open(path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(c, f, allow_unicode=True)
                with self.subTest(broken=broken):
                    self.assertEqual(chk.main(["x", path]), 1)


if __name__ == "__main__":
    unittest.main()
