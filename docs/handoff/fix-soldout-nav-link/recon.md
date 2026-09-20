# 完売ルール メニュー非表示 — 現在地把握

設計書: [design.md](./design.md)

## 根本原因
- `frontend/src/components/DesktopShell.tsx:191` のリンク先が `/super-admin/tcg-line-import`
- `/super-admin/analysis-rules`（完売ルールを含む統合ハブページ）への導線がグローバルナビに存在しない

## 関連ファイル
- `frontend/src/components/DesktopShell.tsx:191` — saasAdminItemsのリンク定義
- `frontend/src/config/routeTitles.ts:14` — ルートタイトル定義
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:109-112` — importセクション選択時のリダイレクト
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:80` — sold-outサブナビ項目
- `frontend/src/pages/super-admin/components/SoldOutRulesPanel.tsx` — 完売ルールパネル

## 確認事項
- [x] Geminiはpublicスキーマ参照: YES（products, tcg_status_master等）
- [x] publicに完売ルール管理テーブル: NO（テナントスキーマのみ）
- [x] tenant_004の取り決め: YES（マイグレーション・API・UI全実装済み）
- [x] i18nキー nav.superAdminAnalysisRules: ja.json/en.json に既存
