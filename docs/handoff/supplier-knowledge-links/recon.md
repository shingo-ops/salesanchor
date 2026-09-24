# recon: supplier-knowledge-links

## 既存ADR検索

- `git grep -i "knowledge_rules\|block_delimiter\|skip_condition\|status_keyword" docs/adr/` → 専用ADRなし
- 関連ADR: ADR-027 (i18n), ADR-144 (UI Governance), ADR-072 (reset_tenant_context)

## 既存コード調査

### knowledge_rules テーブル（shared public）
- `backend/app/schemas/central_masters.py:32` — KnowledgeRuleBase, KnowledgeRuleCreate, KnowledgeRuleResponse
- `backend/app/routers/super_admin_suppliers.py:43` — imports (SupplierExtractionRulesResponse 等)

### gemini 注入経路
- `backend/app/services/gemini_extraction_svc.py:218` — `_build_supplier_context_note(supplier_context: dict)`
- `backend/app/services/gemini_extraction_svc.py:300` — `call_gemini_extraction(...)` ← supplier_context を注入
- `backend/app/services/gemini_extraction_svc.py:526` — `extract_message(...)` ← call_gemini_extraction を呼ぶ
- `backend/app/tasks/tcg_extraction.py:118` — `_run_extraction(session, source_message_id)` ← supplier_context 取得
- `backend/app/tasks/tcg_extraction.py:237` — `_run_recorded_extraction(...)` ← extract_message を呼ぶ

### フロントエンド対象ページ
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:1` — 仕入元別抽出ルール設定ページ
- `frontend/src/locales/ja.json` — i18n (supplierExtractionRules セクション)
- `frontend/src/locales/en.json` — i18n (supplierExtractionRules セクション)

### migration スクリプト
- `scripts/run_all_migrations.sh` — 末尾に追記

## 影響範囲

- extract_message の呼び出し元: tcg_extraction.py の _run_recorded_extraction のみ
- call_gemini_extraction の呼び出し元: extract_message のみ（外部からの直接呼び出しなし）
- knowledge_rules テーブル: 既存カテゴリ以外に block_delimiter/skip_condition/status_keyword を追加（既存データ影響なし）
