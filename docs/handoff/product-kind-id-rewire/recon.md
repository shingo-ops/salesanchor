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
| `scripts/run_all_migrations.sh:最終行` | 新migration登録 |

### バックエンド

| ファイル | 変更行 | 変更内容 |
|---|---|---|
| `backend/app/services/tcg_product_import_svc.py:71` | LOOKUP_ARGS: division_code → product_kind_id |
| `backend/app/services/tcg_product_import_svc.py:180-196` | load_lookup_maps: Phase 3A SSOT override追加（public.product_kinds） |
| `backend/app/services/tcg_product_master_svc.py:88-105` | fetch_registration_form: division_id → product_kind_id lookup |
| `backend/app/services/tcg_product_master_svc.py:319` | create_product: division_id → product_kind_id パラメータ |
| `backend/app/services/tcg_product_master_svc.py:363-400` | create_product: INSERT SQL division_id → product_kind_id |
| `backend/app/services/tcg_product_detail_svc.py:15-16` | LOOKUPS: division_id削除 |
| `backend/app/services/tcg_product_detail_svc.py:20-23` | PUBLIC_INTEGER_LOOKUPS: product_kind_id追加 |
| `backend/app/services/tcg_product_detail_svc.py:25-27` | PUBLIC_INTEGER_NAME_COL: product_kinds.name列マッピング追加 |
| `backend/app/services/tcg_product_detail_svc.py:90-96` | _response: name_col動的切替 |
| `backend/app/services/tcg_product_detail_svc.py:155-167` | update_product_detail: バリデーション name_col動的切替 |
| `backend/app/services/tcg_product_detail_svc.py:169-174` | UPDATE SQL: division_id → product_kind_id |
| `backend/app/routers/tcg_product_import.py:274` | ProductDetailUpdate: division_id: UUID → product_kind_id: int |
| `backend/app/routers/tcg_product_import.py:322-340` | get_product_lookups: product_kind_id lookup追加 |
| `backend/app/routers/tcg_product_import.py:350` | CreateProductBody: division_id → product_kind_id |
| `backend/app/routers/tcg_product_import.py:368` | create_product_standalone: division_id → product_kind_id |
| `backend/app/routers/tcg_product_master.py:75` | DuplicateCheckRequest: division_id → product_kind_id |
| `backend/app/routers/tcg_product_master.py:93` | CreateProductRequest: division_id → product_kind_id |
| `backend/app/routers/tcg_product_master.py:224` | create_product_master: division_id → product_kind_id |

### フロントエンド

| ファイル | 変更内容 |
|---|---|
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:11` | classificationFields: division_id → product_kind_id |
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:38,45` | draftFrom/emptyDraft |
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:132,159` | saveEdit/saveCreate: API送信オブジェクト |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:31` | RegistrationValues型: division_id → product_kind_id |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:89,131,195,226` | 初期値・バリデーション・UI |
| `frontend/src/locales/ja.json:3724` | "product_kind_id": "大分類" 追加 |
| `frontend/src/locales/en.json:3724` | "product_kind_id": "Product kind" 追加 |

### テスト

| ファイル | 変更内容 |
|---|---|
| `backend/tests/test_tcg_schema_qualification.py:197,97` | text()カウント 8→9、product_kinds追加 |
| `backend/tests/test_tcg_product_master.py:34,177-178,118,133,240,270,297,325,349,448,477` | division_id → product_kind_id |
| `backend/tests/test_tcg_product_import.py:360` | division_id → product_kind_id |
| `backend/tests/test_tcg_product_detail_pg.py:60` | lookups set assertion更新 |
| `backend/tests/test_tcg_completion_safety.py:147-151` | tcg_major_categories → public.product_kinds |
| `backend/tests/conftest.py:835` | products テーブルに product_kind_id INTEGER 追加 |
