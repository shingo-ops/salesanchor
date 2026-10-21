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
