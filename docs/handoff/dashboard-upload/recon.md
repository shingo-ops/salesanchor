branch: release/dashboard-upload
date: 2026-09-25

## 調査対象

既存のアップロードUI (`TcgLineImportPage`) がダッシュボードの ImportTabContent とは独立したページとして存在していた。

## ファイル調査結果

| ファイル | 役割 | 行 |
|---------|------|----|
| frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx | ダッシュボード本体・ImportTabContent を含む | 1-2000+ |
| frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css | ダッシュボードスタイル | 1-200+ |
| frontend/src/pages/tcg/TcgLineImportPage.tsx | 既存アップロードページ（独立） | - |
| frontend/src/locales/ja.json | i18n日本語キー | - |
| frontend/src/locales/en.json | i18n英語キー | - |

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
