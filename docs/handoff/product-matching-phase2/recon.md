# ADR-158 Phase 2 — Recon

## 既存ADR検索結果
- `docs/adr/ADR-158-*.md` — ADR-158 本体（Phase 1/2/3/4/5 計画）
- 関連: `docs/adr/ADR-025` (本番DB直接INSERT禁止), `docs/adr/ADR-072` (reset_tenant_context)

## 現在地（ファイル:行番号）

### バージョン定数
- `backend/app/services/tcg_work_reference.py:13` — `WORK_ID_PROMPT_VERSION = "raw-extraction-v5-product-p1"`（変更対象）
- `backend/app/services/tcg_work_reference.py:14` — `WORK_ID_PROMPT_VERSIONS` frozenset（変更対象）
- `backend/app/services/tcg_work_reference.py:16` — `PRODUCT_ID_PROMPT_VERSIONS` frozenset（変更対象）

### Gemini プロンプト
- `backend/app/services/gemini_extraction_svc.py:128` — 11列指定（変更対象）
- `backend/app/services/gemini_extraction_svc.py:130-131` — ヘッダー行（変更対象）
- `backend/app/services/gemini_extraction_svc.py:416` — version not in (2,3,4,5)（変更対象）
- `backend/app/services/gemini_extraction_svc.py:508-509` — resolved_product_code/raw_product_code 抽出（変更対象）
- `backend/app/services/gemini_extraction_svc.py:572` — version=5 指定（変更対象）

### 抽出タスク INSERT
- `backend/app/tasks/tcg_extraction.py:282-300` — extraction_items INSERT SQL（変更対象）
- `backend/app/tasks/tcg_extraction.py:316` — params dict（変更対象）

### アナライザー
- `backend/app/services/tcg_analyzer_svc.py:44-50` — tcg_work_reference imports（変更対象）
- `backend/app/services/tcg_analyzer_svc.py:1294-1304` — extraction_items SELECT（変更対象）
- `backend/app/services/tcg_analyzer_svc.py:1320-1335` — row アンパック（変更対象）
- `backend/app/services/tcg_analyzer_svc.py:1212-1215` — product_code_to_id 構築（変更対象）
- `backend/app/services/tcg_analyzer_svc.py:1420-1446` — GEMINI 直接ヒット + フォールバック（変更対象）

### テスト
- `backend/tests/test_tcg_work_id.py:17` — HEADER (v5, 11列)（変更対象）
- `backend/tests/test_tcg_extraction_record_pg.py:25-26` — HEADER/VALID (v5)（変更対象）
- `backend/tests/test_tcg_extraction_record_integrity_pg.py:156` — version=5（変更対象）
- `backend/tests/test_tcg_work_matching_integration.py:368` — ヘッダー構築（変更対象）
- `backend/tests/test_tcg_work_matching_integration.py:1613,1650,1693` — record() + [wid, pid]（変更対象）

### マイグレーション
- `migrations/20260926_010000_add_raw_product_code.sql` — 新規作成
- `scripts/run_all_migrations.sh` — 末尾に追記

## 触らないファイル
- `frontend/` — UI変更なし（Phase 2はバックエンドのみ）
- `backend/app/services/tcg_condition_review_svc.py` — 条件照合ロジック変更なし
- `backend/app/services/tcg_product_guards.py` — ガードロジック変更なし（Gate 1でも再利用）
- `deploy.yml` — マイグレーションはrun_all_migrations.sh経由
