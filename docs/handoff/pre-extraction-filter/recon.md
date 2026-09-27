# recon: Gemini呼び出し前事前フィルタ

## 対象ファイル調査

### backend/app/tasks/tcg_extraction.py
- 空チェック: L222-240 (`if len(raw_text.strip()) == 0:`)
- Gemini呼び出し: L242 (`recorder = AttemptRecorder(...)`) の後の `_run_recorded_extraction()`
- knowledge_links取得: L201-220（supplier_id紐付けあり）
- `re` モジュール: 未インポート → 追加必要

### backend/app/services/tcg_analysis_dashboard_svc.py
- `get_pipeline_summary()` L31-33: `total_extraction` / `error_rate` 計算
- `get_supplier_pipeline()` L412-416: `extraction_empty` / `extraction_other` のCOUNT FILTER条件

### backend/app/routers/tcg_analysis_dashboard.py
- `ExtractionByStatus` L37-42: Pydantic モデル（done/error/pending/running/empty）

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx
- `RULE_CATEGORIES` L43: 現在 `["normalize", "split", "alias_normalize", "exclude"]`
- カテゴリ表示: L380 `t(\`superAdmin.knowledge.categories.\${r.category}\`)`

### frontend/src/locales/ja.json / en.json
- `superAdmin.knowledge.categories` L2456-2461: 現在4カテゴリ
- `extractionStatus` L3801-3808: done/empty/error/pending/running/unknown

## 既存ADR調査

`git grep -i docs/adr/` でキーワード検索（knowledge_rules, pre_filter, extraction_filter）→ 該当ADRなし。
新機能のため新規ADR不要（設計はタスク指示書で承認済み）。

## DBスキーマ確認

- `knowledge_rules.category`: VARCHAR(50) → 新カテゴリ値追加OK（DB変更不要）
- `extraction_jobs.status`: VARCHAR系 → 'filtered'追加OK（DB変更不要）
