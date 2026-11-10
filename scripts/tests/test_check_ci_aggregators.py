#!/usr/bin/env python3
"""check_ci_aggregators.py の試験（標準ライブラリの unittest）。

実行: python3 -I scripts/tests/test_check_ci_aggregators.py -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ci", "check_ci_aggregators.py"
)

GREEN_RUN = """\
          det="${{ needs.detect-changes.result }}"
          out="${{ needs.detect-changes.outputs.frontend }}"
          r="${{ needs.x-run.result }}"
          echo "detect-changes: $det (frontend=$out) / x-run: $r"
          if [[ "$det" != "success" ]]; then
            echo "FAIL: detect-changes is not success (detect-changes=$det)"
            exit 1
          fi
          case "$out" in
            true)
              if [[ "$r" == "success" ]]; then
                echo "OK: frontend changed and checks passed"
                exit 0
              fi
              echo "FAIL: frontend changed but checks did not succeed: x-run=$r"
              exit 1
              ;;
            false)
              if [[ "$r" == "skipped" ]]; then
                echo "OK: frontend not changed and checks were skipped"
                exit 0
              fi
              echo "FAIL: frontend not changed but checks were not skipped: x-run=$r"
              exit 1
              ;;
            *)
              echo "FAIL: detect-changes output is not true/false: frontend='$out'"
              exit 1
              ;;
          esac
"""

CURRENT_FORM_RUN = """\
          r="${{ needs.x-run.result }}"
          echo "x-run: $r"
          if [[ "$r" == "success" || "$r" == "skipped" ]]; then
            echo "OK"
            exit 0
          else
            echo "FAIL: x-run=$r"
            exit 1
          fi
"""


def make_yml(run, extra_job="", extra_need=""):
    return (
        "name: sample\n"
        "on: [pull_request]\n"
        "jobs:\n"
        "  detect-changes:\n"
        "    runs-on: ubuntu-latest\n"
        "    outputs:\n"
        "      frontend: ${{ steps.f.outputs.frontend }}\n"
        "    steps:\n"
        "      - id: f\n"
        "        run: echo frontend=true >> \"$GITHUB_OUTPUT\"\n"
        "  x-run:\n"
        "    needs: detect-changes\n"
        "    if: needs.detect-changes.outputs.frontend == 'true'\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: echo hi\n"
        + extra_job
        + "  x:\n"
        f"    needs: [detect-changes, x-run{extra_need}]\n"
        "    if: always()\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: Report results\n"
        "        run: |\n"
        + run
    )


Y_RUN_JOB = (
    "  y-run:\n"
    "    needs: detect-changes\n"
    "    if: needs.detect-changes.outputs.frontend == 'true'\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - run: echo hi\n"
)


def run_check(yml_text=None):
    cmd = [sys.executable, "-I", CHECK, "--json"]
    if yml_text is None:
        p = subprocess.run(cmd, capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout)
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "sample.yml"), "w", encoding="utf-8") as f:
            f.write(yml_text)
        p = subprocess.run(
            cmd[:3] + ["--workflows-dir", d, "--json"], capture_output=True, text=True
        )
    return p.returncode, json.loads(p.stdout)


class CheckCiAggregatorsTest(unittest.TestCase):
    def test_green(self):
        code, res = run_check(make_yml(GREEN_RUN))
        self.assertEqual(code, 0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["aggregators"][0]["combos"], 48)
        self.assertEqual(res["aggregators"][0]["mismatches"], 0)

    def test_red_current_form(self):
        code, res = run_check(make_yml(CURRENT_FORM_RUN))
        self.assertEqual(code, 1)
        problems = res["aggregators"][0]["problems"]
        self.assertTrue(any("needs.detect-changes.result" in p for p in problems))

    def test_red_missing_need(self):
        code, res = run_check(
            make_yml(GREEN_RUN, extra_job=Y_RUN_JOB, extra_need=", y-run")
        )
        self.assertEqual(code, 1)
        problems = res["aggregators"][0]["problems"]
        self.assertTrue(any("y-run" in p for p in problems))

    def test_red_false_allows_success(self):
        bad = GREEN_RUN.replace(
            'if [[ "$r" == "skipped" ]]; then',
            'if [[ "$r" == "skipped" || "$r" == "success" ]]; then',
        )
        self.assertNotEqual(bad, GREEN_RUN)
        code, res = run_check(make_yml(bad))
        self.assertEqual(code, 1)
        self.assertGreaterEqual(res["aggregators"][0]["mismatches"], 1)

    def test_real_repo(self):
        code, res = run_check()
        self.assertEqual(code, 0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["total_mismatches"], 0)
        found = {(a["file"], a["job"]) for a in res["aggregators"]}
        required = {
            ("test.yml", "pytest"),
            ("e2e.yml", "lint"),
            ("e2e.yml", "visual-language"),
            ("migration-test.yml", "migration-test"),
            ("schema-check.yml", "schema-check"),
            ("karte-gate.yml", "karte-gate"),
        }
        self.assertTrue(required <= found, required - found)


if __name__ == "__main__":
    unittest.main()
