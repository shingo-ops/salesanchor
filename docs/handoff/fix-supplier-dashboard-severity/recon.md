# Recon: fix-supplier-dashboard-severity

## 調査対象

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx
- frontend/src/locales/ja.json
- frontend/src/locales/en.json

## 発見事項

### 問題1: i18n キー未登録による raw key 表示

AnalysisDashboardPanel.tsx にて t("supplierSeverity_danger") 等のキーを使用していたが、
ja.json / en.json に未登録。結果として raw key がそのまま画面に表示されていた。

確認箇所: frontend/src/locales/ja.json（当該キーなし）、frontend/src/locales/en.json（当該キーなし）

### 問題2: フロントエンド独自 severity 判定の二重管理

getImportSeverity() 関数がフロントで受信日数ベースの severity を計算していたが、
バックエンドAPIは既に row.severity として danger/warning/success を返却している。
（確認: frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1-250 のデータ型定義と API レスポンス構造）

## ADR 参照

- ADR-027: UI文字列は全て t("key") 経由（ハードコード日本語・raw key 表示は違反）
- ADR-067: デザイントークン・UIガバナンス（バッジ色はトークン経由）

## 触らないファイル

バックエンド API・DB・マイグレーションは変更なし。
