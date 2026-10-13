# 許可の自律保守（ADR-1011）の台帳。変更はすべてここに追記する。既存の行は書き換えない

設計書: [self-maintenance-design.md](self-maintenance-design.md)

## 基準

- 2026-10-13 基準
- autoMode sha256: 6a616c3d708be7138cca6a14d69969a0e4ad0d2e33e6f55155846785c72f6492
- 計算方法: 設計書 §5-6 / 写しの置き場所: ~/.claude/logs/permission-baseline-2026-10-13.json（repo の外。repo は PUBLIC のため）

## 履歴（基準に含む・再生では当てない）

| 日時 | 種別 | source | 変更 | 理由 | 根拠の件数 | 報告書 | バックアップ | 試験 | PR |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-13 | 結果 | PO | add: Recursive deletion inside the agent's current worktree (PO decision 2026-10-13): `rm -rf` / `rm -r` is allowed when every target is an absolute path that resolves under the git worktree containing the command's working directory (a directory under /Users/tanizawashingo/worktrees/salesanchor/ whose .git is a file), or under /private/tmp/claude-501/. Never the worktree root itself, never a `.git` directory, never a path containing `..`, `~`, a variable, or a glob. | B2。PO が `!` で追加 | - | - | - | - | - |
| 2026-10-13 | 結果 | PO | add: Branch housekeeping on the agent's own PRs (PO decision 2026-10-13): in shingo-ops/salesanchor, pushing a `release/*` branch to origin without force (including the first push that creates the remote branch), running `gh pr update-branch` on a PR whose head is `release/*`, and posting comments (including GO record comments) on PRs authored by shingo-cc are allowed. Never applies to main or develop, and never to force push or branch deletion. | B3。PO が `!` で追加 | - | - | - | - | - |
| 2026-10-13 | 結果 | PO | add: Merging docs-only PRs (PO decision 2026-10-13, ADR-1003): `gh pr merge <N> --merge` is allowed for a shingo-ops/salesanchor PR when every changed file is under `docs/` or `.claude-pipeline/active-work.d/`, all required checks on the current head pass, and a Reviewer agent returned APPROVE for that head — including when the documents describe agent permissions, hooks, or delegation. Never `--admin`, never `--auto`, never squash. | B4。PO が `!` で追加 | - | - | - | - | - |

## 記録

| 日時 | 種別 | source | 変更 | 理由 | 根拠の件数 | 報告書 | バックアップ | 試験 | PR |
|---|---|---|---|---|---|---|---|---|---|
