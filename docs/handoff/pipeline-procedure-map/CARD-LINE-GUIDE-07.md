# CARD-LINE-GUIDE-07 — 最新main統合後のガイド検証

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、11-lint.md、frontend/AGENTS.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
目的: CARD-06統合結果のfrontend検証。Astraは同じ作業机で文書のみ更新する。他者変更を巻き戻さない。
所有範囲: 検証の実行、必要なローカル依存/自分が起動した開発server、tmp証跡のみ。
製品/試験コード・lockfile・設定・台帳・文書の編集、commit、push、PR、merge、本番変更は禁止。
前提: CARD-06完了、競合0、本店非台帳変更0、mainの追加localeキー保持。

手順1: 前提を再確認し、frontend/AGENTS.mdと実package scripts/playwright設定を読む。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-07.md
不足依存はnpm ciで既存lockfileどおり導入可。準備操作で正本が変わったら停止・報告。
前回画像/tmp/reports/card-line-guide-01は最新結果で上書き前に/tmp/reports/card-line-guide-before-resumeへ保存する。

手順2: 静的検査/build/関連unitを実施する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run check:all
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run build
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npm run test:unit -- --run src/pages/super-admin/components/LineWorkflowGuidePanel.test.tsx
unitの以前17件の関連セットが上記以外を含む場合は、その実pathを確認して同一範囲を追加実行する。

手順3: 実設定に従い現在作業机のfrontendだけを対象にE2E実施。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx playwright test tests-e2e/analysis-rules-line-guide.spec.ts --project=chromium
既存serverを無確認で再利用しない。他者processは停止しない。portが他者使用中なら事実を報告して停止。
E2E6件には390幅viewport検算を組込済み。成功した同一検査の重複再実行は不要。
画像は既存testの/tmp/reports/card-line-guide-01へ出力し、作成日時と対象branch/HEAD/MERGE_HEADを報告する。
モック環境の結果と本番確認は明確に区別する。

手順4: 終了値・成功件数/警告数・画像path・git statusをAstraへ報告し停止。
Astra同時更新文書は除外し、製品/lockfileに検証副作用差分がないことを確認する。
失敗/前提不明/実ガード拒否は停止して生出力をAstraへ報告。正規sandbox escalationは可。

END OF CARD
