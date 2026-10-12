#!/usr/bin/env python3
"""scripts/deploy/app-services-plan.sh の単体テスト（偽物の docker を PATH の先頭に置く）。"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "deploy" / "app-services-plan.sh"

FAKE_DOCKER = r"""#!/usr/bin/env bash
# 呼ばれた引数を1行ずつ記録し、応答は FAKE_DIR 内のファイルから返す
printf '%s\n' "$*" >> "${FAKE_DIR}/calls.log"
case "$1" in
  ps)
    if [[ "$*" == *"--filter"* ]]; then
      for a in "$@"; do
        case "$a" in name=astro-webapp-*) svc="${a#name=astro-webapp-}" ;; esac
      done
      [ -f "${FAKE_DIR}/ps_${svc}" ] && cat "${FAKE_DIR}/ps_${svc}"
    else
      [ -f "${FAKE_DIR}/ps_all" ] && cat "${FAKE_DIR}/ps_all"
    fi
    exit 0
    ;;
  compose)
    if [ "$2" = "config" ] && [ "$3" = "--hash" ]; then
      [ -f "${FAKE_DIR}/hash_fail" ] && exit 1
      echo "$4 $(cat "${FAKE_DIR}/hash_$4")"
      exit 0
    fi
    exit 0
    ;;
  image)
    svc="${@: -1}"
    svc="${svc#astro-webapp-}"
    cat "${FAKE_DIR}/image_${svc}"
    exit 0
    ;;
  inspect)
    cat "${FAKE_DIR}/current_image"
    exit 0
    ;;
esac
exit 0
"""

SVC = "celery-worker"
KEEPER = f"id1|astro-webapp-{SVC}-1|astro-webapp|{SVC}|hashA"


class PlanTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text(FAKE_DOCKER)
        docker.chmod(0o755)
        self.fake = self.tmp / "fake"
        self.fake.mkdir()
        self.env = dict(os.environ)
        self.env["PATH"] = f"{bin_dir}:{self.env['PATH']}"
        self.env["FAKE_DIR"] = str(self.fake)

    def put(self, name: str, content: str) -> None:
        (self.fake / name).write_text(content + "\n")

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=self.env,
            capture_output=True,
            text=True,
            cwd=str(REPO),
        )

    def calls(self) -> list:
        log = self.fake / "calls.log"
        return log.read_text().splitlines() if log.exists() else []

    def assert_read_only(self) -> None:
        for line in self.calls():
            words = line.split()
            for banned in ("rm", "stop", "run", "exec", "kill", "down", "restart"):
                self.assertNotIn(banned, words, line)
            if "up" in words:
                self.assertIn("--dry-run", words, line)


class ObserveTest(PlanTestBase):
    def prepare(self, ps="", expected_hash="hashA", expected_image="img1", current_image="img1") -> None:
        self.put(f"ps_{SVC}", ps)
        self.put(f"hash_{SVC}", expected_hash)
        self.put(f"image_{SVC}", expected_image)
        self.put("current_image", current_image)

    def test_same_hash_and_image_keeps(self) -> None:
        self.prepare(ps=KEEPER)
        result = self.run_script("--observe", SVC)
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"PLAN svc={SVC} decision=keep reason=same", result.stdout)
        self.assert_read_only()

    def test_hash_diff_recreates(self) -> None:
        self.prepare(ps=KEEPER, expected_hash="hashB")
        result = self.run_script("--observe", SVC)
        self.assertIn(f"PLAN svc={SVC} decision=recreate reason=hash_diff", result.stdout)
        self.assert_read_only()

    def test_image_diff_recreates(self) -> None:
        self.prepare(ps=KEEPER, current_image="img0")
        result = self.run_script("--observe", SVC)
        self.assertIn(f"PLAN svc={SVC} decision=recreate reason=image_diff", result.stdout)
        self.assert_read_only()

    def test_no_container_recreates(self) -> None:
        self.prepare(ps="")
        result = self.run_script("--observe", SVC)
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"PLAN svc={SVC} decision=recreate reason=no_container", result.stdout)
        self.assert_read_only()

    def test_hash_command_failure_is_unknown(self) -> None:
        self.prepare(ps=KEEPER)
        self.put("hash_fail", "")
        result = self.run_script("--observe", SVC)
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"PLAN svc={SVC} decision=recreate reason=unknown", result.stdout)
        self.assert_read_only()

    def test_stale_and_duplicate_are_listed(self) -> None:
        ps = "\n".join(
            [
                KEEPER,
                f"id2|abc123_astro-webapp-{SVC}-1|oldproj|{SVC}|hashA",
                f"id3|astro-webapp-{SVC}-2|astro-webapp|{SVC}|hashA",
            ]
        )
        self.prepare(ps=ps)
        result = self.run_script("--observe", SVC)
        self.assertIn(f"PLAN svc={SVC} stale=abc123_astro-webapp-{SVC}-1 reason=project", result.stdout)
        self.assertIn(f"PLAN svc={SVC} stale=astro-webapp-{SVC}-2 reason=duplicate", result.stdout)
        self.assertIn(f"PLAN svc={SVC} decision=keep reason=same", result.stdout)
        self.assert_read_only()


class VerifyTest(PlanTestBase):
    def test_verify_ok(self) -> None:
        self.put(
            "ps_all",
            "\n".join(
                [
                    "astro-webapp-frontend-1|astro-webapp|frontend",
                    "astro-webapp-celery-worker-1|astro-webapp|celery-worker",
                    "pushgateway||",
                ]
            ),
        )
        result = self.run_script("--verify")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("VERIFY ok", result.stdout)
        self.assert_read_only()

    def test_verify_ng_on_duplicate_and_stale(self) -> None:
        self.put(
            "ps_all",
            "\n".join(
                [
                    "astro-webapp-frontend-1|astro-webapp|frontend",
                    "astro-webapp-frontend-2|astro-webapp|frontend",
                    "astro-webapp-celery-beat-1|oldproj|celery-beat",
                    "pushgateway||",
                ]
            ),
        )
        result = self.run_script("--verify")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("VERIFY ng svc=frontend count=2", result.stdout)
        self.assertIn("VERIFY ng stale=astro-webapp-celery-beat-1", result.stdout)
        self.assertNotIn("VERIFY ok", result.stdout)
        self.assert_read_only()


if __name__ == "__main__":
    unittest.main()
