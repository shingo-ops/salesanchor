# recon: extraction_example_text 追加

## 対象 ADR
- 直接対応するADRなし（既存 extraction_rules 機能の拡張）

## 既存実装の調査結果

### DB
- `public.suppliers` に既に extraction_* 列が存在（`migrations/20260924_010000_add_supplier_extraction_rules.sql`）
- 追加カラム: `extraction_example_text TEXT`

### バックエンド
- `backend/app/schemas/central_masters.py:409` — `SupplierExtractionRulesResponse`
- `backend/app/schemas/central_masters.py:422` — `SupplierExtractionRulesUpdate`
- `backend/app/routers/super_admin_suppliers.py:747` — `_EXTRACTION_RULE_COLS`
- `backend/app/routers/super_admin_suppliers.py:752` — `_EXTRACTION_RULE_UPDATABLE`
- `backend/app/routers/super_admin_suppliers.py:858` — GET レスポンス構築
- `backend/app/routers/super_admin_suppliers.py:908` — PATCH レスポンス構築
- `backend/app/services/gemini_extraction_svc.py:218` — `_build_supplier_context_note()`
- `backend/app/tasks/tcg_extraction.py:122` — LEFT JOIN SELECT + supplier_context dict (row[2]-row[7])

### フロントエンド
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:37` — `SupplierExtractionDetail` interface
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:54` — `RulesFormState` type
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:63` — `emptyForm`
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:72` — `detailToForm()`
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:204` — PATCH payload
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:392` — Textarea for extraction_notes (直後に追加)

### テスト
- `backend/tests/test_tcg_work_id.py:107` — mock タプル (8要素→9要素に変更が必要)
- `backend/tests/test_tcg_work_id.py:140` — mock タプル (8要素→9要素に変更が必要)
