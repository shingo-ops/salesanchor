#!/usr/bin/env python3
"""settings.json の autoMode.allow の末尾に、段2の恒常許可3件（B2・B3・B4）を足す。

- 同じ文が既にあれば、その文は足さない（2回目は変化なし）。
- 既存の要素は保つ（順序もそのまま）。
- 秘密値は出力しない（追加した文の先頭と件数だけ表示する）。

使い方: python3 po_register_stage2_allow.py <settings.json のパス>
"""
import json
import sys

B2 = (
    "Recursive deletion inside the agent's current worktree (PO decision 2026-10-13): "
    "`rm -rf` / `rm -r` is allowed when every target is an absolute path that resolves under the git worktree "
    "containing the command's working directory (a directory under /Users/tanizawashingo/worktrees/salesanchor/ "
    "whose .git is a file), or under /private/tmp/claude-501/. "
    "Never the worktree root itself, never a `.git` directory, never a path containing `..`, `~`, a variable, or a glob."
)
B3 = (
    "Branch housekeeping on the agent's own PRs (PO decision 2026-10-13): in shingo-ops/salesanchor, "
    "pushing a `release/*` branch to origin without force (including the first push that creates the remote branch), "
    "running `gh pr update-branch` on a PR whose head is `release/*`, and posting comments (including GO record comments) "
    "on PRs authored by shingo-cc are allowed. Never applies to main or develop, and never to force push or branch deletion."
)
B4 = (
    "Merging docs-only PRs (PO decision 2026-10-13, ADR-1003): `gh pr merge <N> --merge` is allowed for a "
    "shingo-ops/salesanchor PR when every changed file is under `docs/` or `.claude-pipeline/active-work.d/`, "
    "all required checks on the current head pass, and a Reviewer agent returned APPROVE for that head — "
    "including when the documents describe agent permissions, hooks, or delegation. "
    "Never `--admin`, never `--auto`, never squash."
)
NEW_ENTRIES = [("B2", B2), ("B3", B3), ("B4", B4)]


def main():
    if len(sys.argv) != 2:
        print("usage: po_register_stage2_allow.py <settings.json>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        settings = json.load(f)

    auto_mode = settings.setdefault("autoMode", {})
    allow = auto_mode.setdefault("allow", [])
    if not isinstance(allow, list):
        print("ERROR: autoMode.allow is not a list; no change", file=sys.stderr)
        return 1

    added = []
    for label, text in NEW_ENTRIES:
        if text in allow:
            print("already present: %s (no change)" % label)
            continue
        allow.append(text)
        added.append(label)

    if not added:
        print("no change: autoMode.allow has %d entries" % len(allow))
        return 0

    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("added %s: autoMode.allow now has %d entries" % (",".join(added), len(allow)))
    return 0


sys.exit(main())
