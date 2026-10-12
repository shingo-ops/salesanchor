# CARD-LINE-GUIDE-11 — 検証済みガイドの統合commit保存

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
目的: 保存済みガイドをmain fdf3b45aへ統合した成果と限定検証修正/設計文書をcommitする。
他者と共用中。既存Astra文書を保持。未知の変更を取り込まない。
前提: CARD10のeslint/既定E2E6件成功、Astraの差分レビュー合格、Astra文書更新完了を明示受領後のみ実行。
製品追加編集・main/develop操作・push・PR・merge送信・本番変更は禁止。

手順1: branch/HEAD/MERGE_HEAD/statusを照合し、次の範囲以外があれば停止。
frontendは既存ガイド8pathだけ（ja/en、AnalysisRulesPage/Sidebar、GuidePanel css/test/tsx、E2E）。
文書はpipeline-procedure-map配下、feed-translation/README、guards/04-worktreeと05-pr、go-record-transcription READMEとpr-lifecycle-design。
台帳はtodo/evidenceとrelease-line-workflow-guide及びresumeの分割台帳だけ。
HEAD fdf3b45a4c0423413e704694fb99700d94e1d5a7、MERGE_HEAD87c4ad83a96e25dfab792a3b57dda75ba51a65eb。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-11.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/check-task-state.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git diff --check HEAD

手順2: 許可pathだけ明示してstageし、stat/path一覧を確認する。git add -Aは禁止。
設計文書内のcard-lintを追加05〜11に実施し、全exit0であること。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git add .claude-pipeline/active-work.d/release-line-workflow-guide.md .claude-pipeline/active-work.d/release-line-workflow-guide-resume.md docs/ai-agents/evidence-registry.md docs/handoff/design-partner-card-ops/guards/04-worktree.md docs/handoff/design-partner-card-ops/guards/05-pr.md docs/handoff/go-record-transcription/README.md docs/handoff/go-record-transcription/pr-lifecycle-design.md docs/handoff/pipeline-procedure-map docs/specs/inventory-management/feed-translation/README.md frontend/src/locales/en.json frontend/src/locales/ja.json frontend/src/pages/super-admin/AnalysisRulesPage.tsx frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.css frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.tsx frontend/tests-e2e/analysis-rules-line-guide.spec.ts tasks/todo.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git diff --cached --stat

手順3: 検証済み統合をmerge commitで保存する。hooksは維持する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git commit -m "feat: add readable LINE workflow guide with verified navigation"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git log -1 --format=fuller
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git status --short
commit SHA/parents/終了値をAstraへ報告して停止。次の最新main統合は別カード。
正規sandbox escalation可。実ガード拒否・check失敗・未知差分は停止。強制/skip/trust変更は禁止。

END OF CARD
