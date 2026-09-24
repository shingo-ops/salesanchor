# recon: extraction-rules-ui-improvement

## 対象ファイル

- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:341-446` — 右ペインフォーム部分
- `frontend/src/locales/ja.json:4514-4544` — supplierExtractionRules セクション
- `frontend/src/locales/en.json:4514-4544` — supplierExtractionRules セクション

## 既存ADR調査

- `docs/adr/ADR-027-ui-internationalization.md` — i18n強制ルール（準拠済み）
- `docs/adr/ADR-144-*` — UIガバナンス（金型コンポーネント必須・生select/input禁止）
- 抽出ルールUI専用ADR: なし

## 現状の右ペイン順序

1. TextField: priceFormat
2. TextField: qtyFormat
3. Select: orderPattern
4. TextField: defaultUnit
5. TextField: stateFormat
6. Textarea: extraction_notes (rows=4)
7. Textarea: extraction_example_text (rows=8)
8. 保存ボタン

## 変更後の順序

1. Textarea: extraction_notes (rows=10) — ラベル「Geminiへの抽出指示」
2. Textarea: extraction_example_text (rows=8)
3. `<details>` 折りたたみ「詳細設定（技術者向け）」
   - TextField: priceFormat
   - TextField: qtyFormat
   - Select: orderPattern
   - TextField: defaultUnit
   - TextField: stateFormat
4. 保存ボタン

## 変更しないもの

- APIフィールド名（extraction_notes, extraction_example_text 等）
- 保存ロジック（handleSave）
- migration なし
