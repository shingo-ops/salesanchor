# CARD-LINE-GUIDE-13 — 最新main統合の最終検証と保存

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md、frontend/AGENTS.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
他者と共用中、Astraが文書を更新する。製品/試験/設定/lockfile編集禁止、他者変更を巻き戻さない。
目的: 調査済みmain8862732の統合後に受入検証し、文書更新完了後にmerge commitで保存。
前提: HEAD3c198d435b73c3b05dca60c32affe2990b24eb04、MERGE_HEAD8862732e494ac5d92287d57aeea808cee05d3151。
12の実結果をAstraが確認し、競合があれば文書の両側追記を保持して解消済みと明示した後に実行。
push/PR/本番変更・ガード無効化は禁止。自己審査APPROVE。

手順1: 前提SHAと競合0、main側変更の保持、origin/main比較の製品差分がガイド8pathだけと確認する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-13.md

手順2: 最新main統合に対する必要検査を実施する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run check:all
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run build
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run test:unit -- --run src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx src/features/tcg-import-workflow/ImportWorkflowPanel.test.tsx
試験直前のlsofはexit1/出力空の場合だけ次へ進む。listenerあり/別エラーなら停止し他者processを触らない。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && lsof -nP -iTCP:5173 -sTCP:LISTEN
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx playwright test tests-e2e/analysis-rules-line-guide.spec.ts --project=chromium
全終了値/件数をAstraへ報告し、文書記録完了の明示連絡を待つ。失敗時は修正せず停止。

手順3: Astra文書記録完了の連絡後、指定文書だけstageする。
許可: docs/handoff/pipeline-procedure-map、docs/specs/inventory-management/feed-translation/README.md、tasks/todo.md、docs/ai-agents/evidence-registry.md、resume分割台帳。
main由来の既存staged差分は保持し、origin/main比で無関係な変更が増えないことを確認する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/check-task-state.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git diff --check origin/main
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git add docs/handoff/pipeline-procedure-map docs/specs/inventory-management/feed-translation/README.md tasks/todo.md docs/ai-agents/evidence-registry.md .claude-pipeline/active-work.d/release-line-workflow-guide-resume.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git commit -m "chore: integrate current main and record LINE guide validation"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git log -1 --format=fuller
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git status --short
commit SHA/parents/cleanをAstraへ報告し停止。pushは別カード。
正規sandbox escalation可。実ガード拒否・未知差分・前提相違は停止報告。

END OF CARD
