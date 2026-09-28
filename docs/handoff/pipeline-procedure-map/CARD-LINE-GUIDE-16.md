# CARD-LINE-GUIDE-16 — PR提出後のmain更新を統合し最終保存

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、ready○（既存PR維持）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
他者と共用中。製品/試験/設定/lockfileの追加編集禁止、Astra文書を保持する。
目的: PR3831のBEHINDを解消し、同じfrontendの最終HEADを通常保存する。
前提HEAD fb39d740bd6afd6faf104f88dd8f0acb85cf780a、調査済みmain157cd6799480e34481bdcc4a04804dc1e4732be7。
Sol監査: backend2/設計2だけのmain更新、frontend全体変更0、ガイド意味修正0、merge-tree競合0。
CI実ログ: process-artifactsはGO欠落のみ、guard-authoring errorはbase非包含。guard変更や検査skipをしない。
GO発行・PR本文編集・mainへのmerge送信・本番操作は禁止。自己審査APPROVE。

手順1: clean、branch、HEAD、実PRhead一致を確認し、fetch後mainを固定SHAと照合。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-16.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git fetch origin
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git rev-parse HEAD origin/main
相違は停止・再査定。新mainを無断採用しない。

手順2: 調査済みmainを通常mergeし、commit前停止。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git merge --no-ff --no-commit origin/main
競合が出たら独断解消せずAstraへ報告して停止。
成功ならfrontend treeが統合前と同じこと、origin/main比製品8path/既存仕様の範囲内を確認する。

手順3: 同一frontendに対して既定E2E6件を最終確認する。check/build/unitはfrontend変化0なら前回実測を保持し繰り返さない。
直前lsofはexit1/空のみ続行。listenerありや別エラーは停止、他者processに触らない。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && lsof -nP -iTCP:5173 -sTCP:LISTEN
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx playwright test tests-e2e/analysis-rules-line-guide.spec.ts --project=chromium
結果をAstraへ報告し、PR提出/検証文書の更新完了連絡を待つ。

手順4: Astra文書更新完了後、許可docs/台帳のみstageしてmerge commit保存。
許可はpipeline-procedure-map配下、feed-translation/README、todo/evidence、resume分割台帳。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/check-task-state.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git diff --check origin/main
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git add docs/handoff/pipeline-procedure-map docs/specs/inventory-management/feed-translation/README.md tasks/todo.md docs/ai-agents/evidence-registry.md .claude-pipeline/active-work.d/release-line-workflow-guide-resume.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git commit -m "chore: sync main and record LINE guide PR submission"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git log -1 --format=fuller
commit SHA/parents/cleanを報告して停止。pushはCARD14の通常手順をAstraの明示連絡後に適用する。
実ガード拒否/検査失敗は停止報告。正規sandbox escalation可、強制/skip/再送なし。

END OF CARD
