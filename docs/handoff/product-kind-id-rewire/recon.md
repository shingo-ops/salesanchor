# recon.md — ADR-156 Phase 3A: product_kind_id rewire

## 関連ADR

- ADR-156: 商品分類ツリー（大分類 product_kinds 新設・SSOT移行）
- ADR-155: INTEGER FK への移行方針（additive-first）
- ADR-025: 本番フェーズ移行後の手動INSERT禁止

## 変更ファイル一覧（file:line）

### マイグレーション

| ファイル | 変更内容 |
|---|---|
| `migrations/20260921_120000_add_products_product_kind_id.sql` | ADD COLUMN product_kind_id INTEGER FK to public.product_kinds |
| `scripts/run_all_migrations.sh` | 新migration登録 |

### バックエンド

| ファイル | 変更内容 |
|---|---|
| `backend/app/services/tcg_product_import_svc.py` | LOOKUP_ARGS: division_code→product_kind_id / Phase 3A SSOT override追加 |
| `backend/app/services/tcg_product_master_svc.py` | create_product/fetch_registration_form: division_id→product_kind_id |
| `backend/app/services/tcg_product_detail_svc.py` | LOOKUPS除去/PUBLIC_INTEGER_LOOKUPS追加/name_col mapping/UPDATE SQL |
| `backend/app/routers/tcg_product_import.py` | ProductDetailUpdate/CreateProductBody/lookups: division_id→product_kind_id |
| `backend/app/routers/tcg_product_master.py` | DuplicateCheckRequest/CreateProductRequest: division_id→product_kind_id |

### フロントエンド

| ファイル | 変更内容 |
|---|---|
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx` | classificationFields/draftFrom/emptyDraft/save payloads |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx` | RegistrationValues型/初期値/バリデーション/UI |
| `frontend/src/locales/ja.json` | "product_kind_id": "大分類" 追加 |
| `frontend/src/locales/en.json` | "product_kind_id": "Product kind" 追加 |

### テスト

| ファイル | 変更内容 |
|---|---|
| `backend/tests/test_tcg_schema_qualification.py` | text()カウント 8→9、product_kinds追加 |
| `backend/tests/test_tcg_product_master.py` | division_id → product_kind_id |
| `backend/tests/test_tcg_product_import.py` | division_id → product_kind_id |
| `backend/tests/test_tcg_product_detail_pg.py` | lookups set assertion更新 |
| `backend/tests/test_tcg_completion_safety.py` | tcg_major_categories → public.product_kinds |
| `backend/tests/conftest.py` | products テーブルに product_kind_id INTEGER 追加 |
