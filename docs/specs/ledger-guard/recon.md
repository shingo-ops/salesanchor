# recon — 現在地の事実（2026-07-04実測・file:line）

## ガードの実体（ホーム側・リポ外）
- ~/.claude/scripts/worktree-only-guard.sh（4891B・2026-06-02版・r-xr-xr-x）
  - worktree内（~/worktrees/配下）は無条件許可（冒頭のPWD判定）
  - ルール1: feature/fix/releaseブランチ×worktree外で、Bashは
    grep 'git push|gh pr merge' のみ遮断、Edit/Writeは遮断。
    **git commit は遮断対象外**（穴）。**mainブランチは全て対象外**（穴）
  - ルール2: worktree外からfeature/fix/release宛push遮断
  - ケース3案内文に「git checkout develop」の化石（誤誘導）
  - エスケープ: WORKTREE_BYPASS=1／記録: ~/.claude/logs/agent-events.jsonl
- 実測（2026-07-04）: 本店release/inbox-recordsでpush阻止=作動確認。
  直コミット4604c685=素通り（commitの穴の実証）
- hooks配線: ~/.claude/settings.json PreToolUse 12エントリ、全て
  ~/.claude/scripts/ 配下を指し全ファイル実在（ls実測）

## 台帳（active-work.md）の書き手・読み手 = 17ファイル
scripts/: new-worktree.sh（121-129行で自動登録・置き書類の発生源）、
release-worktree.sh、reaper-worktree.sh、check-stale-worktrees.sh、
cleanup-worktree.sh、backfill-active-work-done.sh、register-pr.sh、
gh-pr-merge-safe.sh、validate-pr-ownership.sh、codex-generator.sh、
check-active-work-format.sh（列数検査・82行でERRORS計上）、
check-process-artifacts.js、test_pre_commit_hook.py、
tests/test-reaper-safety.sh、tests/test-manifest-generation.sh
frontend/.husky/: pre-push（28-30行でフォーマット検査）、
pre-commit（17-21行でactive-work単独変更を例外許可）

## その他
- release/worktree-canon-main はブランチ不在（台帳に幽霊行のみ）→衝突リスク消滅
- 第2弾（書き先分割）は上記17読者のフォーマット依存の精査が前提
