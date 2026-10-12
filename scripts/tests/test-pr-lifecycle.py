#!/usr/bin/env python3
"""PR lifecycle wrappers: temporary repositories and a fake gh only."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
CREATE = SOURCE_ROOT / "scripts/gh-pr-create-safe.sh"
HELPER = SOURCE_ROOT / "scripts/dev/check-pr-merge-ready.py"
CHECKER = SOURCE_ROOT / "scripts/check-process-artifacts.js"
DETECTOR = SOURCE_ROOT / "scripts/detect-external-api-change.js"
BRANCH = "release/lifecycle-test"
PR_NUMBER = 9999


def command(argv: list[str], cwd: Path, *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise AssertionError(f"command failed: {argv}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def go_body(number: int = PR_NUMBER, *, include_go: bool = True) -> str:
    body = """### 標準ワークフロー確認
- 対象ADR: ADR-113
- recon: docs/handoff/test/recon.md
- 設計: docs/handoff/test/design.md
触るファイル: scripts/target.sh
削除するファイル: scripts/target.sh
"""
    if include_go:
        body += f"""
### GO記録
- GO発行者: Shingo（shingo-ops）
- 日時: 2026-09-28 10:00 JST
- GO原文: GO #{number}
- バックアップ確認: 該当なし
"""
    return body


FAKE_GH = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

fixture_path = Path(os.environ["GH_FIXTURE"])
state_path = Path(os.environ["GH_STATE"])
log_path = Path(os.environ["GH_LOG"])
fixture = json.loads(fixture_path.read_text())
state = json.loads(state_path.read_text()) if state_path.exists() else {"views": 0, "checks": 0}
args = sys.argv[1:]
with log_path.open("a") as handle:
    handle.write(json.dumps({
        "args": args,
        "host": os.environ.get("GH_HOST"),
        "repo": os.environ.get("GH_REPO"),
    }, ensure_ascii=False) + "\n")

if args[:2] == ["api", "user"]:
    print(fixture.get("auth_login", "shingo-cc"))
elif args[:2] == ["pr", "create"]:
    raise SystemExit(fixture.get("create_rc", 0))
elif args[:2] == ["pr", "view"]:
    index = state["views"]
    state["views"] += 1
    state_path.write_text(json.dumps(state))
    if index in fixture.get("view_error_at", []):
        print("view failed", file=sys.stderr)
        raise SystemExit(1)
    views = fixture["views"]
    print(json.dumps(views[min(index, len(views) - 1)]))
elif args[:2] == ["pr", "checks"]:
    if fixture.get("touch_on_checks"):
        Path(fixture["touch_on_checks"]).write_text("changed during checks")
    if fixture.get("commit_on_checks"):
        import subprocess
        subprocess.run(["git", "commit", "--allow-empty", "-m", "changed during checks"], check=True)
    index = state["checks"]
    state["checks"] += 1
    state_path.write_text(json.dumps(state))
    sequence = fixture.get("checks_sequence", [fixture.get("checks", [])])
    print(json.dumps(sequence[min(index, len(sequence) - 1)]))
    rc_sequence = fixture.get("checks_rc_sequence", [fixture.get("checks_rc", 0)])
    raise SystemExit(rc_sequence[min(index, len(rc_sequence) - 1)])
elif args[:2] == ["pr", "merge"]:
    raise SystemExit(fixture.get("merge_rc", 0))
elif args and args[0] == "api" and any("/pulls/" in arg for arg in args):
    pr = fixture["views"][0]
    joined = " ".join(args)
    if "user.login" in joined:
        print(pr.get("author", {}).get("login", ""))
    else:
        print(pr.get("body", ""))
elif args[:2] == ["issue", "list"]:
    print("[]")
elif args[:2] == ["issue", "create"]:
    raise SystemExit(0)
else:
    print("unsupported fake gh call: " + " ".join(args), file=sys.stderr)
    raise SystemExit(1)
'''


class RepoFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pr-lifecycle-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.bare = self.root / "origin.git"
        self.bin = self.root / "bin"
        self.fixture = self.root / "fixture.json"
        self.state = self.root / "state.json"
        self.log = self.root / "gh.log"
        self.register_log = self.root / "register.log"
        self.bin.mkdir()
        self.create = self.repo / "scripts/gh-pr-create-safe.sh"
        fake = self.bin / "gh"
        fake.write_text(FAKE_GH)
        fake.chmod(0o755)
        command(["git", "init", "--bare", str(self.bare)], self.root)
        command(["git", "init", "-b", "main", str(self.repo)], self.root)
        command(["git", "config", "user.name", "test"], self.repo)
        command(["git", "config", "user.email", "test@example.com"], self.repo)
        self._seed_files()
        command(["git", "add", "."], self.repo)
        command(["git", "commit", "-m", "main"], self.repo)
        command(["git", "remote", "add", "origin", str(self.bare)], self.repo)
        command(["git", "push", "-u", "origin", "main"], self.repo)
        command(["git", "switch", "-c", BRANCH], self.repo)
        (self.repo / "scripts/target.sh").write_text("#!/bin/sh\necho changed\n")
        command(["git", "add", "scripts/target.sh"], self.repo)
        command(["git", "commit", "-m", "change"], self.repo)
        command(["git", "push", "-u", "origin", BRANCH], self.repo)
        command(["git", "remote", "set-url", "origin", "https://github.com/shingo-ops/salesanchor.git"], self.repo)
        command(["git", "config", f"url.file://{self.bare}.insteadOf", "https://github.com/shingo-ops/salesanchor.git"], self.repo)
        self.main_sha = command(["git", "rev-parse", "main"], self.repo).stdout.strip()
        self.head_sha = command(["git", "rev-parse", "HEAD"], self.repo).stdout.strip()

    def _seed_files(self) -> None:
        (self.repo / "scripts/dev").mkdir(parents=True)
        (self.repo / "scripts").mkdir(exist_ok=True)
        (self.repo / "docs/handoff/test").mkdir(parents=True)
        (self.repo / "scripts/check-process-artifacts.js").write_bytes(CHECKER.read_bytes())
        (self.repo / "scripts/detect-external-api-change.js").write_bytes(DETECTOR.read_bytes())
        self.create.write_bytes(CREATE.read_bytes())
        (self.repo / "scripts/dev/validate-pr-body.sh").write_bytes((SOURCE_ROOT / "scripts/dev/validate-pr-body.sh").read_bytes())
        (self.repo / "scripts/register-pr.sh").write_text(
            '#!/bin/sh\nprintf "%s|%s|%s\\n" "${GH_HOST:-}" "${GH_REPO:-}" "${GITHUB_ACTIONS:-}" >> "${REGISTER_LOG}"\n'
        )
        (self.repo / "scripts/target.sh").write_text("#!/bin/sh\necho base\n")
        (self.repo / "docs/handoff/test/recon.md").write_text("# recon\n")
        (self.repo / "docs/handoff/test/design.md").write_text(
            "# design\n\n## 外部・過去事例の参照と我々への応用\n該当なし（内部手順）\n\n"
            "## 維持の仕組み\n守り手: scripts/target.sh\n"
        )

    def env(self) -> dict[str, str]:
        return {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "GH_FIXTURE": str(self.fixture),
            "GH_STATE": str(self.state),
            "GH_LOG": str(self.log),
            "REGISTER_LOG": str(self.register_log),
        }

    def base_pr(self, **updates: object) -> dict[str, object]:
        value: dict[str, object] = {
            "number": PR_NUMBER,
            "state": "OPEN",
            "isDraft": False,
            "baseRefName": "main",
            "baseRefOid": self.main_sha,
            "headRefName": BRANCH,
            "headRefOid": self.head_sha,
            "author": {"login": "shingo-cc"},
            "body": go_body(),
            "reviewDecision": "APPROVED",
            "mergeStateStatus": "CLEAN",
            "mergeCommit": None,
            "mergedAt": None,
        }
        value.update(updates)
        return value

    def merged_pr(self) -> dict[str, object]:
        return self.base_pr(
            state="MERGED",
            mergeCommit={"oid": "a" * 40},
            mergedAt="2026-09-28T01:00:00Z",
        )

    def configure(self, **updates: object) -> None:
        base = self.base_pr()
        data: dict[str, object] = {
            "auth_login": "shingo-cc",
            "views": [base, base, self.merged_pr()],
            "checks": [{"name": "required", "bucket": "pass"}],
            "checks_rc": 0,
            "merge_rc": 0,
            "create_rc": 0,
        }
        data.update(updates)
        self.fixture.write_text(json.dumps(data))
        self.state.unlink(missing_ok=True)
        self.log.unlink(missing_ok=True)
        self.register_log.unlink(missing_ok=True)

    def calls(self, prefix: list[str]) -> list[list[str]]:
        if not self.log.exists():
            return []
        calls = [json.loads(line)["args"] for line in self.log.read_text().splitlines()]
        return [call for call in calls if call[: len(prefix)] == prefix]

    def records(self) -> list[dict[str, object]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def close(self) -> None:
        self.temp.cleanup()


class LifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = RepoFixture()
        self.fx.configure()

    def tearDown(self) -> None:
        self.fx.close()

    def run_helper(self, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = self.fx.env()
        if extra_env:
            env.update(extra_env)
        return command(["python3", str(HELPER), str(PR_NUMBER), BRANCH], self.fx.repo, env=env, check=False)

    def assert_no_merge(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.fx.calls(["pr", "merge"]), [])

    def test_merge_normal_one_send_with_checked_sha(self) -> None:
        self.fx.configure(checks=[
            {"name": "required", "bucket": "pass"},
            {"name": "not-applicable", "bucket": "skipping"},
        ])
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        merges = self.fx.calls(["pr", "merge"])
        self.assertEqual(len(merges), 1)
        self.assertIn("--merge", merges[0])
        self.assertEqual(merges[0][merges[0].index("--match-head-commit") + 1], self.fx.head_sha)
        self.assertIn("skipping=1", result.stdout)
        for record in self.fx.records():
            self.assertEqual(record["host"], "github.com")
            self.assertEqual(record["repo"], "github.com/shingo-ops/salesanchor")
            args = record["args"]
            if args[:2] in (["pr", "view"], ["pr", "checks"], ["pr", "merge"]):
                self.assertEqual(args[args.index("--repo") + 1], "github.com/shingo-ops/salesanchor")
            if args and args[0] == "api":
                self.assertEqual(args[args.index("--hostname") + 1], "github.com")

    def test_merge_rejects_go_missing_number_mismatch_and_env_override(self) -> None:
        for body, extra in [
            (go_body(include_go=False), None),
            (go_body(PR_NUMBER + 1), None),
            (go_body(include_go=False), {
                "MOCK_PR_BODY": go_body(),
                "CHANGED_FILES": "docs/x.md",
                "GH_HOST": "evil.example",
                "GH_REPO": "evil/repo",
            }),
        ]:
            with self.subTest(body=body[-40:], extra=bool(extra)):
                pr = self.fx.base_pr(body=body)
                self.fx.configure(views=[pr, pr, pr])
                self.assert_no_merge(self.run_helper(extra))

    def test_merge_rejects_pr_state_identity_and_review_conditions(self) -> None:
        cases = {
            "author": {"author": {"login": "outsider"}},
            "closed": {"state": "CLOSED"},
            "draft": {"isDraft": True},
            "base": {"baseRefName": "develop"},
            "head": {"headRefName": "release/other"},
            "review-required": {"reviewDecision": "REVIEW_REQUIRED"},
            "review-unknown": {"reviewDecision": "DISMISSED"},
            "behind": {"mergeStateStatus": "BEHIND"},
            "bad-base-sha": {"baseRefOid": "short"},
            "bad-head-sha": {"headRefOid": "short"},
        }
        for name, updates in cases.items():
            with self.subTest(name=name):
                pr = self.fx.base_pr(**updates)
                self.fx.configure(views=[pr, pr, pr])
                self.assert_no_merge(self.run_helper())

    def test_merge_rejects_api_checks_dirty_and_remote_mismatch(self) -> None:
        self.fx.configure(view_error_at=[0])
        self.assert_no_merge(self.run_helper())
        for checks, rc in [([], 0), ([{"name": "x", "bucket": "fail"}], 0), ([{"name": "x", "bucket": "pending"}], 8)]:
            with self.subTest(checks=checks, rc=rc):
                self.fx.configure(checks=checks, checks_rc=rc)
                self.assert_no_merge(self.run_helper())
        self.fx.configure()
        (self.fx.repo / "dirty.txt").write_text("dirty")
        self.assert_no_merge(self.run_helper())
        (self.fx.repo / "dirty.txt").unlink()
        command(["git", "commit", "--allow-empty", "-m", "local only"], self.fx.repo)
        self.fx.configure()
        self.assert_no_merge(self.run_helper())

    def test_merge_rejects_second_view_changes(self) -> None:
        for field, value in [("body", "changed"), ("baseRefOid", "b" * 40), ("headRefOid", "c" * 40)]:
            with self.subTest(field=field):
                first = self.fx.base_pr()
                second = self.fx.base_pr(**{field: value})
                self.fx.configure(views=[first, second, second])
                self.assert_no_merge(self.run_helper())

    def test_merge_post_send_failures_exit_two_without_retry(self) -> None:
        cases = [
            (1, self.fx.base_pr()),
            (1, self.fx.merged_pr()),
            (0, self.fx.base_pr()),
        ]
        for merge_rc, final in cases:
            with self.subTest(merge_rc=merge_rc, final=final["state"]):
                initial = self.fx.base_pr()
                self.fx.configure(views=[initial, initial, final], merge_rc=merge_rc)
                result = self.run_helper()
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(len(self.fx.calls(["pr", "merge"])), 1)
                self.assertEqual(len(self.fx.calls(["pr", "view"])), 3)
                if merge_rc and final["state"] == "MERGED":
                    self.assertIn("MERGED observed", result.stderr)
        initial = self.fx.base_pr()
        self.fx.configure(views=[initial, initial, initial], view_error_at=[2])
        result = self.run_helper()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(len(self.fx.calls(["pr", "merge"])), 1)

    def test_merge_rechecks_local_head_and_clean_before_send(self) -> None:
        dirty_path = self.fx.repo / "late-dirty.txt"
        self.fx.configure(touch_on_checks=str(dirty_path))
        self.assert_no_merge(self.run_helper())
        dirty_path.unlink()
        self.fx.configure(commit_on_checks=True)
        self.assert_no_merge(self.run_helper())

    def test_merge_rechecks_required_checks_after_full_checker(self) -> None:
        self.fx.configure(checks_sequence=[
            [{"name": "required", "bucket": "pass"}],
            [{"name": "required", "bucket": "pending"}],
        ])
        self.assert_no_merge(self.run_helper())

    def test_create_accepts_four_body_forms_without_go(self) -> None:
        body = go_body(include_go=False)
        body_file = self.fx.root / "body.md"
        body_file.write_text(body)
        forms = [
            ["--body", body],
            [f"--body={body}"],
            ["--body-file", str(body_file)],
            [f"--body-file={body_file}"],
        ]
        for args in forms:
            with self.subTest(form=args[0][:20]):
                self.fx.configure()
                result = command(["bash", str(self.fx.create), "--title", "test", *args], self.fx.repo, env=self.fx.env(), check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                creates = self.fx.calls(["pr", "create"])
                self.assertEqual(len(creates), 1)
                sent = creates[0]
                self.assertEqual(sent[sent.index("--repo") + 1], "github.com/shingo-ops/salesanchor")
                self.assertEqual(sent[sent.index("--body") + 1], body)
                self.assertNotIn("--body-file", sent)
                create_record = next(record for record in self.fx.records() if record["args"][:2] == ["pr", "create"])
                self.assertEqual(create_record["host"], "github.com")
                self.assertEqual(create_record["repo"], "github.com/shingo-ops/salesanchor")
                self.assertEqual(self.fx.register_log.read_text().strip(), "github.com|github.com/shingo-ops/salesanchor|")

    def test_create_rejects_body_input_and_identity_failures(self) -> None:
        bad_utf8 = self.fx.root / "bad.md"
        bad_utf8.write_bytes(b"\xff")
        nul = self.fx.root / "nul.md"
        nul.write_bytes(b"a\x00b")
        empty = self.fx.root / "empty.md"
        empty.write_bytes(b"")
        directory = self.fx.root / "body-dir"
        directory.mkdir()
        cases = [
            [],
            ["--body", ""],
            ["--body", go_body(False), "--body-file", str(empty)],
            ["--body-file", "-"],
            ["--body-file", str(bad_utf8)],
            ["--body-file", str(nul)],
            ["--body-file", str(empty)],
            ["--body-file", str(directory)],
            ["--draft", "--body", go_body(include_go=False)],
            ["--web", "--body", go_body(include_go=False)],
            ["--fill", "--body", go_body(include_go=False)],
            ["--title", "one", "--title", "two", "--body", go_body(include_go=False)],
            ["--title=", "--body", go_body(include_go=False)],
            ["--base=", "--body", go_body(include_go=False)],
            ["--head=", "--body", go_body(include_go=False)],
            ["--base", "main", "--base", "main", "--body", go_body(include_go=False)],
            ["--head", BRANCH, "--head", BRANCH, "--body", go_body(include_go=False)],
        ]
        for args in cases:
            with self.subTest(args=args):
                self.fx.configure()
                result = command(["bash", str(self.fx.create), "--title", "test", *args], self.fx.repo, env=self.fx.env(), check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.fx.calls(["pr", "create"]), [])
        self.fx.configure()
        result = command(
            ["bash", str(self.fx.create), "--title=", "--body", go_body(include_go=False)],
            self.fx.repo,
            env=self.fx.env(),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.fx.calls(["pr", "create"]), [])
        self.fx.configure()
        gha_env = self.fx.env()
        gha_env["GITHUB_ACTIONS"] = "true"
        result = command(["bash", str(self.fx.create), "--title", "test"], self.fx.repo, env=gha_env, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.fx.calls(["pr", "create"]), [])
        self.fx.configure()
        hostile_env = self.fx.env()
        hostile_env.update({"GH_HOST": "evil.example", "GH_REPO": "evil/repo", "GITHUB_ACTIONS": "true"})
        result = command(
            ["bash", str(self.fx.create), "--title", "test", "--body", go_body(include_go=False)],
            self.fx.repo,
            env=hostile_env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.fx.register_log.read_text().strip(), "github.com|github.com/shingo-ops/salesanchor|")
        self.fx.configure(auth_login="outsider")
        result = command(["bash", str(self.fx.create), "--title", "test", "--body", go_body(False)], self.fx.repo, env=self.fx.env(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.fx.calls(["pr", "create"]), [])

    def test_create_rejects_structure_origin_and_unpushed_head(self) -> None:
        self.fx.configure()
        result = command(["bash", str(self.fx.create), "--title", "test", "--body", "invalid"], self.fx.repo, env=self.fx.env(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.fx.calls(["pr", "create"]), [])

        command(["git", "remote", "set-url", "origin", "https://github.com/other/repo.git"], self.fx.repo)
        self.fx.configure()
        result = command(["bash", str(self.fx.create), "--title", "test", "--body", go_body(include_go=False)], self.fx.repo, env=self.fx.env(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.fx.calls(["pr", "create"]), [])

        command(["git", "remote", "set-url", "origin", "https://github.com/shingo-ops/salesanchor.git"], self.fx.repo)
        command(["git", "commit", "--allow-empty", "-m", "not pushed"], self.fx.repo)
        self.fx.configure()
        result = command(["bash", str(self.fx.create), "--title", "test", "--body", go_body(include_go=False)], self.fx.repo, env=self.fx.env(), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.fx.calls(["pr", "create"]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
