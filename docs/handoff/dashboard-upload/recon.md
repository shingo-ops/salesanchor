branch: release/dashboard-upload
date: 2026-09-25

## 調査対象

既存のアップロードUI (`TcgLineImportPage`) がダッシュボードの ImportTabContent とは独立したページとして存在していた。

## ファイル調査結果

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1` — ダッシュボード本体・ImportTabContent を含む
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:1` — ダッシュボードスタイル
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:1` — 既存アップロードページ（独立）・移植元
- `frontend/src/locales/ja.json:1` — i18n日本語キー
- `frontend/src/locales/en.json:1` — i18n英語キー

## API SSOT

アップロードAPI: `/tcg/line-import` (POST multipart/form-data)
- パラメータ: `file`, `window_hours`
- 既存 TcgLineImportPage と同一エンドポイント

## 関連 ADR

- `docs/adr/ADR-027-ui-internationalization.md` — i18n強制
- `docs/adr/ADR-144-ui-component-governance.md` — デザインシステム遵守

## 既存機能との重複確認

TcgLineImportPage はナビゲーションから独立アクセス可能なページとして残置。
ダッシュボードのImportタブにも同機能を統合（DRY違反ではなくUX導線の追加）。
