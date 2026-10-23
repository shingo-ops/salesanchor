# CLAUDE.md

@AGENTS.md

## Claude Code だけの決まり

- 作業場所は `bash scripts/new-worktree.sh release/<topic> --claude` で作る（`--claude` は作った場所で Claude Code を起動する）
- `.claude/agents/` 変更前は必ず `git pull` で最新取得（複数セッション同時書き込みによる上書き防止）
- 個人設定は `~/.claude/CLAUDE.md`、初期セットアップは `docs/onboarding/claude-code.md`
