# CARD-LINE-GUIDE-17 — 並行mainの統合とガイド再検証

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、既存PR○、報告先○、一目的○、起点○、書式○、検算○、L32○。
所有範囲: 調査済みmainの通常統合と既存試験実行。他者と共用中。他者変更を戻さない。
製品コードの独自編集・試験変更・GO発行・PR編集・main送信・本番操作は禁止。
起点HEAD88b495603df6d8398024ba300225386a9695c507。
統合対象main b3cf1fdf32bb57394239f973364273ed6f560fad。
Solの意味影響監査がAPPROVEの場合のみ進める。未確定/相違/実ガード拒否は停止してAstraへ報告。

手順1: 本カード文書だけの未追跡追加を除きcleanと固定HEAD/mainを照合し、通常統合をcommit前で止める。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-17.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git status --short
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git rev-parse HEAD origin/main
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git merge --no-ff --no-commit b3cf1fdf32bb57394239f973364273ed6f560fad
既知の台帳競合はAstraが双方保持で解消する。Solは競合を報告して待機し、独断解消しない。

手順2: Astraの台帳解消完了連絡後、check/build/unit/E2Eを実行し個別終了値を報告。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run check:all
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run build
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx vitest run src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx src/features/tcg-import-workflow/ImportWorkflowPanel.test.tsx
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && lsof -nP -iTCP:5173 -sTCP:LISTEN
lsofはexit1/空の場合のみE2Eへ進む。listenerや別エラーでは停止し他者processに触らない。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx playwright test tests-e2e/analysis-rules-line-guide.spec.ts --project=chromium
結果・前回比差分・失敗はAstraへ報告する。commit/pushは本カードに含めない。

END OF CARD
