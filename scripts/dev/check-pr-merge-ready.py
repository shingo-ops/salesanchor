#!/usr/bin/env python3
"""Fail-closed PR validation and one-shot merge sender."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = "shingo-ops/salesanchor"
GH_HOST = "github.com"
GH_REPO = "github.com/shingo-ops/salesanchor"
ALLOWED_AUTHORS = {"shingo-cc", "Hikky-dev"}
PR_FIELDS = (
    "number,state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,"
    "author,body,reviewDecision,mergeStateStatus,mergeCommit,mergedAt"
)


class Stop(RuntimeError):
    pass


class PostSend(RuntimeError):
    pass


def run(argv: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, text=True, capture_output=True, env=env)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise Stop(f"command failed ({result.returncode}): {' '.join(argv)}: {detail}")
    return result


def git(*args: str) -> str:
    return run(["git", *args]).stdout.strip()


def github_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update({"GH_HOST": GH_HOST, "GH_REPO": GH_REPO})
    return env


def pr_view(number: str) -> dict[str, Any]:
    raw = run(
        ["gh", "pr", "view", number, "--repo", GH_REPO, "--json", PR_FIELDS],
        env=github_env(),
    ).stdout
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Stop(f"invalid PR JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise Stop("PR response is not an object")
    return value


def author_login(pr: dict[str, Any]) -> str:
    author = pr.get("author")
    return author.get("login", "") if isinstance(author, dict) else ""


def validate_pr(pr: dict[str, Any], number: int, branch: str, local_sha: str, origin_sha: str) -> None:
    sha_pattern = re.compile(r"[0-9a-fA-F]{40}")
    for label, value in {
        "local HEAD": local_sha,
        "origin head": origin_sha,
        "PR base": pr.get("baseRefOid"),
        "PR head": pr.get("headRefOid"),
    }.items():
        if not isinstance(value, str) or not sha_pattern.fullmatch(value):
            raise Stop(f"{label} is not a 40-character SHA: {value!r}")
    expected = {
        "number": number,
        "state": "OPEN",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": branch,
        "headRefOid": local_sha,
    }
    for field, wanted in expected.items():
        if pr.get(field) != wanted:
            raise Stop(f"PR {field} mismatch: expected {wanted!r}, got {pr.get(field)!r}")
    if origin_sha != local_sha:
        raise Stop("local HEAD and origin head differ")
    if author_login(pr) not in ALLOWED_AUTHORS:
        raise Stop(f"PR author is not allowed: {author_login(pr)!r}")
    if not isinstance(pr.get("baseRefOid"), str) or not pr["baseRefOid"]:
        raise Stop("baseRefOid is missing")
    if not isinstance(pr.get("body"), str):
        raise Stop("PR body is missing")
    if pr.get("reviewDecision") not in {"APPROVED", ""}:
        raise Stop(f"reviewDecision is not allowed: {pr.get('reviewDecision')!r}")
    if pr.get("mergeStateStatus") != "CLEAN":
        raise Stop(f"mergeStateStatus is not CLEAN: {pr.get('mergeStateStatus')!r}")


def check_required_checks(number: str) -> None:
    raw = run([
        "gh", "pr", "checks", number, "--repo", GH_REPO, "--required",
        "--json", "name,bucket",
    ], env=github_env()).stdout
    try:
        checks = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Stop(f"invalid checks JSON: {exc}") from exc
    if not isinstance(checks, list) or not checks:
        raise Stop("required checks were not returned")
    failed = [
        c for c in checks
        if not isinstance(c, dict) or c.get("bucket") not in {"pass", "skipping"}
    ]
    if failed:
        raise Stop(f"required checks are not all successful: {json.dumps(failed, ensure_ascii=False)}")
    skipped = sum(1 for check in checks if check.get("bucket") == "skipping")
    print(f"required checks: total={len(checks)} pass={len(checks) - skipped} skipping={skipped}")


def checker_env(pr: dict[str, Any], number: str, branch: str) -> dict[str, str]:
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("MOCK_")
        and key not in {"CHANGED_FILES", "MAINTENANCE_ENFORCE", "GITHUB_OUTPUT"}
    }
    env.update({
        "BASE_SHA": pr["baseRefOid"],
        "HEAD_SHA": pr["headRefOid"],
        "PR_NUMBER": number,
        "REPO": REPO,
        "HEAD_REF": branch,
        "BASE_REF": "main",
        "GH_HOST": GH_HOST,
        "GH_REPO": GH_REPO,
    })
    return env


def stable_fields(pr: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "number", "state", "isDraft", "baseRefName", "baseRefOid", "headRefName",
        "headRefOid", "author", "body", "reviewDecision", "mergeStateStatus",
    )
    return {field: pr.get(field) for field in fields}


def main() -> int:
    if len(sys.argv) != 3 or not re.fullmatch(r"[1-9][0-9]*", sys.argv[1]):
        raise Stop("usage: check-pr-merge-ready.py <PR number> <current branch>")
    number_s, branch = sys.argv[1], sys.argv[2]
    number = int(number_s)
    if not re.fullmatch(r"(?:release|hotfix)/[A-Za-z0-9._/-]+", branch):
        raise Stop(f"invalid branch: {branch!r}")

    root = Path(git("rev-parse", "--show-toplevel"))
    os.chdir(root)
    if git("branch", "--show-current") != branch:
        raise Stop("current branch differs from wrapper input")
    origin = git("config", "--get", "remote.origin.url")
    allowed_origins = {
        "https://github.com/shingo-ops/salesanchor",
        "https://github.com/shingo-ops/salesanchor.git",
        "git@github.com:shingo-ops/salesanchor.git",
        "ssh://git@github.com/shingo-ops/salesanchor.git",
    }
    if origin not in allowed_origins:
        raise Stop(f"unexpected origin: {origin!r}")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise Stop("worktree is not clean")

    run(["git", "fetch", "origin", "main", branch, "--quiet"])
    local_sha = git("rev-parse", "HEAD")
    origin_sha = git("rev-parse", f"refs/remotes/origin/{branch}")
    pr = pr_view(number_s)
    validate_pr(pr, number, branch, local_sha, origin_sha)
    check_required_checks(number_s)

    checker = root / "scripts" / "check-process-artifacts.js"
    run(["node", str(checker), "--validation-only"], env=checker_env(pr, number_s, branch))
    check_required_checks(number_s)

    if git("rev-parse", "HEAD") != local_sha:
        raise Stop("local HEAD changed during validation; merge was not sent")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise Stop("worktree changed during validation; merge was not sent")
    current = pr_view(number_s)
    if stable_fields(current) != stable_fields(pr):
        raise Stop("PR changed after validation; merge was not sent")

    merge_result = run([
        "gh", "pr", "merge", number_s, "--repo", GH_REPO, "--merge",
        "--match-head-commit", local_sha,
    ], check=False, env=github_env())

    try:
        final = pr_view(number_s)
    except Stop as exc:
        raise PostSend(f"merge result GET failed; no retry and no cleanup: {exc}") from exc
    merge_commit = final.get("mergeCommit")
    merge_oid = merge_commit.get("oid") if isinstance(merge_commit, dict) else ""
    merged_confirmed = (
        final.get("state") == "MERGED"
        and final.get("headRefOid") == local_sha
        and bool(merge_oid)
        and bool(final.get("mergedAt"))
    )
    if merge_result.returncode != 0:
        observation = "MERGED observed" if merged_confirmed else f"state={final.get('state')!r}"
        detail = (merge_result.stderr or merge_result.stdout).strip()
        raise PostSend(
            f"merge command failed (rc={merge_result.returncode}); {observation}; "
            f"no retry and no cleanup: {detail}"
        )
    if not merged_confirmed:
        raise PostSend("merge command returned success but MERGED result was not confirmed; no retry and no cleanup")

    print(json.dumps({
        "status": "MERGED",
        "number": number,
        "headRefOid": local_sha,
        "mergeCommit": merge_oid,
        "mergedAt": final["mergedAt"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PostSend as exc:
        print(f"POST-SEND STOP: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Stop as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1)
