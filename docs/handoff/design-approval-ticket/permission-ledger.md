# 許可の自律保守（ADR-1011）の台帳。変更はすべてここに追記する。既存の行は書き換えない

設計書: [self-maintenance-design.md](self-maintenance-design.md)

## 基準

- 2026-10-13 基準
- autoMode sha256: 6a616c3d708be7138cca6a14d69969a0e4ad0d2e33e6f55155846785c72f6492
- 計算方法: 設計書 §5-6 / 写しの置き場所: ~/.claude/logs/permission-baseline-2026-10-13.json（repo の外。repo は PUBLIC のため）

## 履歴（基準に含む・再生では当てない）

| 日時 | 種別 | source | 結果 | 変更 | 理由 | 根拠の件数 | 報告書 | バックアップ | 試験 | PR |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-13 | 結果 | PO | 適用（PO） | add: Recursive deletion inside the agent's current worktree (PO decision 2026-10-13): `rm -rf` / `rm -r` is allowed when every target is an absolute path that resolves under the git worktree containing the command's working directory (a directory under /Users/tanizawashingo/worktrees/salesanchor/ whose .git is a file), or under /private/tmp/claude-501/. Never the worktree root itself, never a `.git` directory, never a path containing `..`, `~`, a variable, or a glob. | B2。PO が `!` で追加 | - | - | - | - | - |
| 2026-10-13 | 結果 | PO | 適用（PO） | add: Branch housekeeping on the agent's own PRs (PO decision 2026-10-13): in shingo-ops/salesanchor, pushing a `release/*` branch to origin without force (including the first push that creates the remote branch), running `gh pr update-branch` on a PR whose head is `release/*`, and posting comments (including GO record comments) on PRs authored by shingo-cc are allowed. Never applies to main or develop, and never to force push or branch deletion. | B3。PO が `!` で追加 | - | - | - | - | - |
| 2026-10-13 | 結果 | PO | 適用（PO） | add: Merging docs-only PRs (PO decision 2026-10-13, ADR-1003): `gh pr merge <N> --merge` is allowed for a shingo-ops/salesanchor PR when every changed file is under `docs/` or `.claude-pipeline/active-work.d/`, all required checks on the current head pass, and a Reviewer agent returned APPROVE for that head — including when the documents describe agent permissions, hooks, or delegation. Never `--admin`, never `--auto`, never squash. | B4。PO が `!` で追加 | - | - | - | - | - |

## 記録

| 日時 | 種別 | source | 結果 | 変更 | 理由 | 根拠の件数 | 報告書 | バックアップ | 試験 | PR |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-13 12:11 | 結果 | PO | 適用（PO） | add: Permission self-maintenance (explicitly wanted by the PO, ADR-1011, decision 2026-10-13). This rule is the PO's consent for this class of change; the weekly report and ledger are records of process, not consent. During the weekly permission-maintenance routine, Claude may (A) append to `autoMode.allow` in /Users/tanizawashingo/.claude/settings.json a new entry whose text starts with `SM-YYYY-MM-DD-N:`, or (B) remove an entry that starts with `SM-`, only when ALL hold: (0) a Reviewer agent returned APPROVE on the report PR head that lists this exact entry text with its stop counts; (1) the report is under docs/handoff/design-approval-ticket/permission-reports/ and the ledger row is in docs/handoff/design-approval-ticket/permission-ledger.md, both merged to main before the change; (2) a backup is taken and ~/.claude/logs/permission-maintenance-pending.json is written before the change; (3) an added entry is at most 120 words; contains none of these strings: `Bash(`, `:*`, `ssh`, `psql`, `docker`, `sudo`, `gh api`, `permit-danger`, the address of any host named in `autoMode.environment`, `secret`, `token`, `password`, `credential`, `.env`, `.pem`, `id_ed25519`, `.clasprc`, `~/.claude`, `/.claude/`, `settings`, `hook`; uses no universal wording (`any`, `all`, `every`, `regardless`); and only covers commands that begin with the exact first two words quoted from the stop shape in the report, run inside /Users/tanizawashingo/worktrees/salesanchor/ or /private/tmp/claude-501/. It never covers: editing or removing any entry not starting with `SM-`, this rule itself, `hard_deny`, `soft_deny`, `environment`, `permissions`, `hooks`, any file under ~/.claude/scripts/, scripts/dev/test-agent-hooks.sh, the ledger's existing rows, or anything that would allow DROP / TRUNCATE / ALTER / DELETE, force push, branch-protection or ruleset changes, external GUI operations, production writes, or merging non-docs PRs without the ADR-1003 conditions. | PO が `!` で例外の文を登録 | - | - | ~/.claude/settings.json.bak-20261013121121 | - | #4211 |
| 2026-10-13 | 予定 | routine | 未適用 | add: SM-2026-10-13-0: test entry for acceptance test S2 (ADR-1011); it matches no command and grants nothing. | 受入試験 S2 | 該当なし（試験） | docs/handoff/design-approval-ticket/permission-reports/2026-10-13-s2-trial.md | - | - | - |
| 2026-10-13 12:30 | 結果 | routine | 適用 | add: SM-2026-10-13-0: test entry for acceptance test S2 (ADR-1011); it matches no command and grants nothing. | 受入試験 S2（追加） | 該当なし（試験） | docs/handoff/design-approval-ticket/permission-reports/2026-10-13-s2-trial.md | ~/.claude/settings.json.bak-20261013123019 | PASS=57 FAIL=0（取り除いた後に実行・手順の順序の逸脱あり） | #4213 |
| 2026-10-13 12:31 | 結果 | routine | 適用 | remove: SM-2026-10-13-0: test entry for acceptance test S2 (ADR-1011); it matches no command and grants nothing. | 受入試験 S2（取り除き） | 該当なし（試験） | 同上 | ~/.claude/settings.json.bak-20261013123158 | 同上 | #4213 |
