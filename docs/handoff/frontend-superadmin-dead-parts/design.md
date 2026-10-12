
#### AY-2e 本番反映（2026-10-09 記録）

AY-2e: PR #4092 merge 0caa64700137385bd45341e460b63cf772cd2a3b（2026-10-09T13:41:55Z、必須15/15成功）、Deploy 37938703727 success（headSha 0caa64700、13:41:58Z〜13:44:32Z）。本番の JS で `input w-full`・`qty-input`・`manual-record-datetime` 0 件。app 200、/api/health 200。GO: POの委任に基づくClaude Opus発行（ADR-1003）。Reviewer APPROVE。

#### AY-2f スーパー管理の使われていない部品の削除（2026-10-10）

mode: handoff。PO 原文（2026-10-10、本セッション）: 「5. どこからも使われていない部品→消す」。対象は直前の棚卸し（/tmp/CC報告ファイル/super-admin-menu/report.md）で「どこからも使われていない」と示した6部品。GO は ADR-1003 の委任に基づく Claude Opus 発行。POのGO原文は創作しない。

現在地（origin/main c59e0fe02。調査 /tmp/CC報告ファイル/super-admin-menu/）:
- 試験からしか参照されない4部品（App.tsx に `/super-admin/masters` の Route は無い。:341-361 は `/super-admin/masters/*/import` のみ）:
  - frontend/src/pages/super-admin/DexTab.tsx（354行）
  - TcgSeriesTab.tsx（376行）
  - LLMBudgetTab.tsx（248行）
  - ProductMastersTab.tsx（135行）
- 参照0件の2部品:
  - components/RuleCreateDrawer.tsx（305行）。呼び出し箇所は 7a3f62c1b（2026-09-25、ルール編集 Drawer）で無くなった。
  - components/StatusMasterPanel.tsx（374行）。中身は 155a01e45（2026-09-26）で RuleManagementPanel に統合済み。RuleManagementPanel.tsx:5 のコメントに名前が出るだけ。
- 連鎖して不要になるもの: frontend/src/components/master-list-editor/（MasterListEditor.tsx 226行・index.ts 2行）。本番コードからの参照元は ProductMastersTab.tsx:18 だけ。ほかに試験 MasterSearchButtonMigration.test.tsx:7 が直接 import している。
- 6部品専用の CSS・hook・api 関数・型は無い。className の CSS 定義も0件。共用部品はすべて他から使われている。
- 試験（部分編集。ファイルは残す）:
  - AdminMasterSaveButtonMigration.test.tsx: it :39〜:66 の7本（Dex・TCG）
  - PurchaseAdminEditorButtonMigration.test.tsx: it :76〜:94 の4本（Dex・LLM予算・TCG種別）
  - AllLegacyButtonDynamicMigration.test.tsx: it :58 の1本（ProductMasters）。describe 名 "six" は "five" に直す。
  - MasterSearchButtonMigration.test.tsx: MasterList 系（:62 以降の3グループ）と :7 の import
- e2e: tests-e2e/super-admin-masters.spec.ts（3 test）と super-admin-llm-budget.spec.ts（3 test）。どちらも存在しない `/super-admin/masters` を開き、src に無い testid `super-admin-tab-*` を前提にしている。今の画面では成り立たない。CI では実行していない（e2e.yml:103-105 の playwright job は `if: false`）。
- i18n: 6部品と MasterListEditor を消すと、次の名前空間は使われなくなる。名前空間ごと消してよいかは、実装時に動的キー（テンプレート文字列の接頭辞）も含めて参照0件を確認してから決める。
  - `superAdmin.dex.*` 16
  - `superAdmin.tcg.*` 16
  - `superAdmin.llmBudget.*` 13
  - `superAdmin.attrMasters.*` 22
  - 未使用キーを検出する CI は無い。消し漏れがあっても落ちない。逆に、使っているキーを消すと check-i18n-missing-keys で落ちる。
- backend: 変更しない。画面から呼ばれなくなる API は dex・tcg/series・llm-budget・product-masters の4系統で、扱いは別途判断する。tcg/types と status-master は他の画面が使っている。

AY-2f 変更契約:
1. 次のファイルを削除する:
   - pages/super-admin の DexTab.tsx・TcgSeriesTab.tsx・LLMBudgetTab.tsx・ProductMastersTab.tsx
   - components/RuleCreateDrawer.tsx・components/StatusMasterPanel.tsx
   - frontend/src/components/master-list-editor/ の2ファイル
   - frontend/tests-e2e/super-admin-masters.spec.ts・super-admin-llm-budget.spec.ts
2. 試験4ファイルから、削除する部品の it・import・固定値・モック分岐だけを取り除く。残る it の中身は1文字も変えない（AllLegacy の describe 名だけは "five" に直す）。
3. RuleManagementPanel.tsx:5 の、消える StatusMasterPanel に触れたコメント行を削除する。コードは変えない。
4. ja.json・en.json: 上の4名前空間のうち、src 全体（試験を含む）で参照0件と確認できたキーだけを削除する。ja と en は同じキー集合を保つ。
5. 変更しないもの:
   - 5ページ（tcg-sold-out・tcg-product-master・tcg-parallel-report・tcg-supplier-quality・supplier-master）。PO の判断待ち。
   - ItemComparison、backend、CSS、トークン、金型、CI、依存
   - docs/ の過去の記述（migration.md TB-27/31/33/39 など）。本節で削除を記録する。
6. design.md: 本節と実装結果を追記する。

前後表:

| 対象 | 変わる項目 |
|---|---|
| 画面 | 変化0（削除するのはどの画面からも開けない部品だけ） |
| コード | 8ファイル（約2,020行）と e2e 2 spec を削除。試験は it が12本と MasterList 系が減る |
| 生 input 件数 | ページ側の生 text 系 84 から、実測した分だけ減る（実装後に ay0-input-inventory で確定する。§AY-2e で「到達不可13」とした数は再計測で確定し、違えばここに訂正を書く） |

受入:

| 基準 | 検証方法 |
|---|---|
| 消した部品が参照されていない | 削除後に `git grep` で8部品名と `master-list-editor` の参照0件 |
| 画面の変化0 | `vite build` の成果物で、ルートの一覧（App.tsx の Route）とメニュー定義ファイル（DesktopShell/MobileShell/AnalysisRulesSidebar）の差分0 |
| 残る試験の中身が不変 | 試験4ファイルで、残した it の本文が変更前と1文字も違わないことを差分で示す |
| i18n | check-i18n-missing-keys 成功、ja/en のキー集合が一致、削除したキーの src 参照0件（テンプレート接頭辞を含む） |
| 品質 | generate 後の tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook、CI 必須全成功 |
| 本番 | Deploy 成功、app 200・/api/health 200、本番 JS で `super-admin-dex-tab`・`super-admin-llm-budget-tab` 0 件（本番でも元から0の可能性がある。そのときは0のままであることだけを記録する） |

Architect 自己審査（AY-2f）: APPROVE。根拠は次のとおり。同一AI（Opus）の自己審査で、独立した第二者のレビューではない。外部事例は不要（使われていないコードの削除のため）。
- 削除対象と連鎖を file:line で確定した。
- 本番コードからの参照は0件。
- CI のベースライン（ui-governance・token ratchet）は差分比較で、削除では落ちない。
- 画面・配線・データ・backend は不変。
- PO の明示指示の範囲内。

維持の仕組み: 守り手は tsc（参照が残れば落ちる）、check-i18n-missing-keys、frontend-check。守っていないものは次の2つ。切戻しは本PRの merge commit を revert する（DB 影響なし）。
- 未使用 i18n キーの検出
- 画面から呼ばれない backend API 4系統

#### AY-2f 実装結果

実装: 変更契約1〜4のとおり。削除は src 8ファイル（DexTab・TcgSeriesTab・LLMBudgetTab・ProductMastersTab・RuleCreateDrawer・StatusMasterPanel・MasterListEditor・master-list-editor/index.ts）と e2e 2 spec。試験4ファイルは削除した部品の it・import・固定値・モック分岐だけを取り除いた。RuleManagementPanel.tsx の StatusMasterPanel に触れたコメント行（:5）を削除。ja.json・en.json から superAdmin.dex 16・tcg 16・llmBudget 13・attrMasters 22 の計67キーを、ja・en とも同じ集合で削除した。

変更契約の補足（設計者指示）: SuppliersPage.tsx :58 と :154 のコメントにあった「（MasterListEditor パターンと統一）」の語句だけを削除した（消える部品名に触れていたため）。コードは変更なし。

事実（設計の想定との差）: MasterSearchButtonMigration.test.tsx の MasterList 系は、設計では「:62 以降の3グループ」としていたが、実際は 4 ブロック（:62 it.each・:79 it・:99 it.each・:111 it.each）だった。4 ブロックすべてが MasterListEditor 専用のため全て削除した。残った it は :44 の it.each(remoteCases) の 1 本。削除した it は AdminMasterSave 7・PurchaseAdminEditor 4・AllLegacy 1・MasterSearch 4 ブロック。

計測（evidence-20260910/ay2f-*）:
- 生 input（ay0-input-inventory）: ページ側の生 text 系 84 → 70（差14: MasterListEditor 3・DexTab 5・TcgSeriesTab 5・LLMBudgetTab 1）。ページ側の生 input 全体 172 → 155。AY-2e で「到達不可13」とした数は再計測で14だったため、ここに訂正する（ay2f-inv-before.json / ay2f-inv-after.json）。
- 参照0件: 8部品名・master-list-editor・MasterListEditor・super-admin-dex-tab・super-admin-llm-budget-tab の git grep（frontend・.github・docs/ai-agents）は0件（ay2f-grep-diff.txt）。
- 画面不変: App.tsx・DesktopShell.tsx・MobileShell.tsx・AnalysisRulesSidebar.tsx の git diff origin/main は差分0（ay2f-grep-diff.txt）。
- 残した it の本文: 試験4ファイルで、残した 11 本（2+4+4+1）すべてが変更前と同一（ay2f-it-compare.txt、変更前の原本は ay2f-orig-tests/）。
- i18n: 削除キーの src 参照0件（テンプレート接頭辞を含む）を確認。残したキーは0。削除キー一覧は ay2f-removed-keys/。
- 品質（ay2f-quality.txt・ay2f-test-counts.txt）: generate:icon-sizes・generate:api-types 後に tsc 0、lint 0、check:all 0、test:coverage --maxWorkers=1 0（74 files・944 tests 成功。AY-2e 時点は963）、build 0、build-storybook 0。frontend/coverage は worktree 外へ移動。

限界: 本番反映後の確認（Deploy・app 200・本番 JS の testid 0件）は merge 後。backend の4系統 API（dex・tcg/series・llm-budget・product-masters）は変更しておらず、扱いは別途判断。切戻し: 本PRの merge commit を revert（DB 影響なし）。

## 維持の仕組み
守り手: frontend/scripts/check-i18n-missing-keys.js（tsc とフロント検査も併用）。守っていないもの: 未使用 i18n キーの検出と、画面から呼ばれない backend API 4系統。切戻しは本PRの merge commit を revert する（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 使われていないコードの削除のため不要（PO 原文「どこからも使われていない部品→消す」）。過去事例: AY-2e（PR #4092）で到達不可13件として除外していた部品を、本PRで参照0件を git grep で確認したうえで削除する。recon は recon.md（参照元の file:line）、受入基準は上記「受入」表。

参照: recon は docs/handoff/frontend-superadmin-dead-parts/recon.md。対象ADR は ADR-027（docs/adr/ADR-027-ui-internationalization.md）と ADR-144。
