# CARD-PR-LIFECYCLE-04 — 審査済み変更のコミット

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 冒頭でカード名を示す。担当Sol、設計/最終審査Astra。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、ready指定○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates
ブランチ: release/pr-lifecycle-gates、起点origin/main 4bad43a4dca6368ffa7370792a3c912e90bba521。
目的: SolとAstraが審査した限定変更をコミットとして保存する。
設計: docs/handoff/go-record-transcription/pr-lifecycle-design.md末尾の実装審査結果。
コード編集禁止。下記19ファイルのstage/commitだけ許可する。push/PR/merge/deploy/GO作成は禁止。
他者と共用中。他者変更を巻き戻さず、scope外の変更があれば停止する。

許可する19ファイル:
.claude-pipeline/active-work.d/release-pr-lifecycle-gates.md
 docs/ai-agents/evidence-registry.md
 docs/handoff/go-record-transcription/README.md
 docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-01.md
 docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-02.md
 docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-03.md
 docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-04.md
 docs/handoff/go-record-transcription/pr-lifecycle-design.md
 docs/handoff/go-record-transcription/pr-lifecycle-recon.md
 scripts/aeon-release.sh
 scripts/check-process-artifacts.js
 scripts/dev/validate-pr-body.sh
 scripts/dev/check-pr-merge-ready.py
 scripts/gh-pr-create-safe.sh
 scripts/gh-pr-merge-safe.sh
 scripts/tests/test-merge-safe-guard.sh
 scripts/tests/test-process-artifacts.js
 scripts/tests/test-pr-lifecycle.py
 tasks/todo.md

手順1
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && ./scripts/dev/executor-preflight.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/card-lint.sh docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-04.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git status --short --untracked-files=all

手順2
上の19ファイルを明示列挙してgit addし、git diff --cached --check とstatを確認する。
commit messageは fix: separate PR preparation from merge approval checks とする。
コミット後にgit log -1 --format=fuller、git status --shortを取得してAstraへ報告し停止する。
各操作は単独コマンドで実行。対象worktreeへ明示cdする。main本店では変更しない。
hook/CI/署名等の検査をスキップしない。拒否/矛盾/検証失敗は停止報告。
sandbox固有制限は同じ操作をrequire_escalatedの正規審査に出してよい。

END OF CARD
