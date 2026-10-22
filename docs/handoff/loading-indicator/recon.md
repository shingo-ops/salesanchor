# recon: 読み込み中の表示（2026-10-22 Opus・Sonnet 調査）

基準: origin/main（git fetch 後）。生出力: /tmp/CC報告ファイル/loading-indicator-recon/

## 1 金型
- frontend/src/components/loading/Spinner.tsx:6-32 — props: size('sm'|'md'|'lg') / color / onAccent / tone / decorative / className / label（既定 'Loading'）。role="status" と aria-label を自分で付ける（:31）。
- frontend/src/components/loading/Skeleton.tsx:5-12 — variant('text'|'table'|'list'|'card') / rows / width。table 形は aria-label="Loading" が英語直書き（:27）。
- frontend/src/loading-animations.css:7-9 `@keyframes sa-spin`、:66-103 `.sa-spinner*`、:543-551 prefers-reduced-motion で停止。
- frontend/src/tokens.css:135 `--duration-spinner: 800ms`、:136 `--duration-shimmer: 1500ms`。
- Storybook の stories は components/loading 配下に無い（Button.stories.tsx:64-69 に Button の loading 状態のみ）。

## 2 使用箇所
- Spinner: frontend/src/components/Button.tsx:17（import）・:68 の1か所だけ。
- Skeleton / ProgressBar / SplashScreen / SaveIndicator: アプリ側の使用 0 件。

## 3 文字だけの読み込み中表示
- `role="status"` と `common.loading` が同じ行: 10 件（q3_status_oneline.txt）。うち frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:284 `{loading && <p role="status">{t("common.loading")}</p>}`。
- `<p>{t("common.loading")}</p>`（role なし）: 46 件（q3_p.txt）。

## 4 DataTable
- frontend/src/components/DataTable.tsx:73-128 の DataTableProps に loading / skeleton は無い。

## 5 決まり
- docs/CC_UI_GOVERNANCE.md・docs/adr/ に、画面の読み込み中の表示についての決まりは無い（該当は ADR-009:27 の Discord の話だけ）。

## 6 アイコン金型
- frontend/src/constants/icons.tsx・icons-base.tsx に回転ローダー（Loader2 等）の登録は無い。

## 既存ADR検索
ADR-027（i18n）・ADR-067（デザイントークン）・ADR-144（UIガバナンス）が対象。読み込み表示の専用ADRは無い（上記 5）。

## 未確認
- なし（段階1の範囲）

---

# 段階2 の現在地（2026-10-22 Opus。調査は Sonnet、origin/main 544e124ee 基準）

生出力: /tmp/CC報告ファイル/loading-stage2-recon/（00_INDEX.txt・G_INDEX.txt）と /tmp/CC報告ファイル/loading-stage2-recon2/

## S1 読み込み中の表示の数（B_table.tsv・G7_counts_by_dir.txt）
- 試験以外で読み込み系キーを使う行は 191。内訳: 文字だけのブロック表示 T1 67・T2 75（計 142、122 ファイル）／ボタン内の三項 T3 42／その他 T4〜T6 7。
- 保存・送信系（「保存中」等、33 キー）は 68 行。性質が違う（押した操作の進行表示）ため段階2の対象外。
- 142 件の場所: pages/ 118・features/ 13・components/ 11。

## S2 金型の実物
- frontend/src/components/loading/Spinner.tsx:26 既定ラベル `'Loading'` 英語直書き。:31 role=status と aria-label を自分で付ける。
- frontend/src/components/loading/index.ts:1-29 が loading 系の一括 export（Spinner・Skeleton・EmptyState 等）。
- frontend/src/components/Button.tsx:58-71 は loading 時に `<Spinner size="sm" tone="inherit" decorative />`（role を持たない）。loading props を持つのは Button だけ（HeaderButton.tsx:16-36 等には無い）。
- frontend/src/components/DataTable.tsx に loading/isLoading の props は無い（H3.txt）。:292・:404 の `'No data'` は直書き。
- 名前: `LoadingBlock` は frontend/ に 0 件。`LoadingState` は frontend/src/pages/schedule/SchedulePageImpl.tsx:816 の同ファイル内関数と重なる（H2.txt）。
- 金型の中で既定文字を t() で出す前例: frontend/src/components/ConfirmModal.tsx:31-32、frontend/src/components/Modal.tsx:134。

## S3 見た目の正本
- frontend/src/components.css:423-427 `.loading`（text-align center・color var(--text-muted)・padding var(--space-8)）。他の CSS に上書き無し（G3_dot_loading_all_css.txt）。
- 専用 class 21 種は中央寄せ・余白・色・文字サイズだけ。高さ確保や grid 位置を担うものは無い。`.fn-loading` だけカード風（背景・角丸・影）。`.fu-loading`・`.frr-loading` 等 5 組は空・エラー表示と class を共用（G3_dedicated_class_css.txt）。
- トークン: frontend/src/tokens.css:69-78 `--space-1`〜`--space-12`、--text-muted は frontend/src/index.css:25・:231。

## S4 金型の登録手順
- docs/adr/ADR-144-ui-component-governance.md:59-64「金型がない場合は PO 許可を得て Xxx.tsx + Xxx.css（var() のみ）+ Xxx.stories.tsx で新設」。
- Storybook は frontend/.storybook/main.ts:11 が `src/**/*.stories.*` を自動で拾う。一覧への登録作業は無い。
- 直近の前例（Radio、2db5c98ab）は docs/CC_UI_GOVERNANCE.md の禁止事項の表に1行足している。

## S5 検査
- scripts/check-ui-governance.js:341-349 `countAll`、:38 対象は `frontend/src/pages/` だけ、:381-400 は BASE と HEAD の件数比較（増えたら赤）。試験は scripts/tests/test-ui-governance.js:30-53 の形。CI は .github/workflows/ui-governance-gate.yml（必須）。

## S6 試験への影響（G5_trace_result.txt）
- frontend/src/pages/super-admin/components/ProductMasterPanel.test.tsx:126 は `queryByRole("status")` が null を期待。ProductMasterPanel.tsx:116 を Spinner にすると落ちる可能性が高い（未実行）。
- e2e tcg-product-import.spec.ts:63,86 は画面全体の `getByRole("status")`。影響は未確認。
- 試験は i18n を各自で import して初期化する（frontend/src/test-setup.ts に i18n 初期化は無い。H6.txt）。en.json の common.loading は "Loading..."。

## 段階2 便2 の調査（origin/main 16000c2d5、生出力 /tmp/CC報告ファイル/loading-bin2-recon/）
- B1 対象: pages/super-admin の文字だけ表示 31 件（targets.tsv）。検査の数え方で super-admin は 48 件、残り 17 件はボタン内の三項 13・"uploading" 1・"errorLoading" 2・TcgDistributionPage.tsx:25 1（gov-counts.txt）。
- B2 置き方: 親が td・li・p の中にあるもの 0、同じ要素に他の文字が混ざるもの 0（context.txt）。要素ごと LoadingBlock に替えられる。
- B3 文言: analysisRules.dashboard.loading・tcgLineImport.loading は日英とも common.loading と同じ文言。label は要らない。
- B4 CSS: 使っている class は analysis-dashboard-empty（空表示と共用）と page（共用）だけで、置換後に使われなくなる規則は 0（css.txt）。
- B5 試験: frontend/src/pages/super-admin/components/ProductMasterPanel.test.tsx:126 は置換後に落ちる（tests.txt §3）。試験 :112-128 の意図は「古い失敗で alert と件数表示を出さない」。件数表示は :100 と同じ文面 "Products: N"。
- B6 e2e: frontend/tests-e2e/tcg-product-import.spec.ts:63・:86 は排他の三項の別の枝を見るため重ならない（コード読み、実機は CI で確認）。

## 段階2 便3 の調査（origin/main 44c34a488、生出力 /tmp/CC報告ファイル/loading-bin3-recon/）
- C1 対象: frontend/src/pages/ のうち super-admin 以外で countLoadingText が当たるのは 106 件。替えられるもの 84 件（targets.tsv）、替えないもの 22 件（excluded.tsv: ボタン内の三項 18・prop 1・aria-live などを持つ要素 3）。
- C2 組分け（groups.txt）: 第1組 32 件・25 ファイル（buyback-prices・dashboard・admin・inbox・integrations・inventory）、第2組 28 件、第3組 24 件。ファイルは組をまたがない。
- C3 文言: common.loading と文言が違うのは inventoryVisibility.loadingMatrix と dashboard.weeklyLoading（keys.txt）。他は同じ文言。
- C4 CSS: 置換で使われなくなる規則は .db-loading など 8 つ（css.txt 末尾の精密再計測）。共用の .loading・.page は残る。
- C5 試験: 対象の画面の試験に、読み込み中の文字・role=status への依存は見つからない（tests.txt、コード読み）。
- C6 lint: 対象のうち 3 ファイルにもともと eslint 警告 4 件（exhaustive-deps 1・日本語の直書き 3）があり、触ると commit 前の lint-staged（--max-warnings=0）で止まる（/tmp/CC報告ファイル/loading-stage2-bin3/）。
- C7 第2組（groups.txt「第2組」・targets.tsv）: 18 ディレクトリ 28 ファイル 28 件。文言は全件 common.loading で label は要らない。要素は `<div className="loading">` 21・`<p>` 7。roles/RolesPage.tsx:303 だけ外側に `<div className="page">` があり残す（css.txt）。対象 18 ディレクトリに試験ファイルは 0 本で、対象ページを読み込む試験は src/components/*ButtonMigration.test.tsx の 10 本（/tmp/CC報告ファイル/loading-stage2-bin3-g2/related-tests.txt）。
- C8 第3組（groups.txt「第3組」・targets.tsv・context.txt）: 17 ディレクトリ 23 ファイル 24 件。文言は全件 common.loading。外側の枠（`page`・`page-container`）の中にあるものが 6 件（CompanyDetailPage:64・InvoiceDetailPage:191・QuoteDetailPage:119・Register 系 3 件）、枠の div 自身が文字を持つものが 1 件（ScheduleSettingsPage:109）。CommissionsPage:167 は style（marginTop）付き。置換後に対象 23 ファイルで残る 1 件は QuoteDetailPage:147 のボタン内三項（excluded.tsv）。対象ページを読み込む試験は 14 本（/tmp/CC報告ファイル/loading-stage2-bin3-g3/importing-tests.txt）。
