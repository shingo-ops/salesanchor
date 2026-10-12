# recon: フォーマットビルダー UI

## 既存 ADR 検索結果

- ADR-027: UI 文字列 i18n 強制（`t("key")` 経由）
- ADR-144: UIガバナンス（金型コンポーネントのみ使用）

## 変更対象ファイル（全文確認済み）

| ファイル:行 | 内容 |
|------------|------|
| `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:1-486` | 仕入元抽出ルール設定ページ本体 |
| `frontend/src/components/Select.tsx:1-133` | Select/SelectControl コンポーネント（props 確認） |
| `frontend/src/components/Button.tsx:1-89` | Button コンポーネント（props 確認） |
| `frontend/src/locales/ja.json:4514-4548` | supplierExtractionRules セクション |
| `frontend/src/locales/en.json:4514-4548` | supplierExtractionRules セクション |
| `backend/app/services/gemini_extraction_svc.py:218-242` | `_build_supplier_context_note()` 関数 |

## 触らない範囲

- DB スキーマ（`extraction_order_pattern` は既存 TEXT 列、migration 不要）
- バックエンド API エンドポイント（変更なし）
- 他ページ・コンポーネント
