# recon: ADR-156 Phase 2 — tcg_type_master → type_master コード統一

## 概要

DB は Phase 1（PR #3620）で `type_master` にリネーム済み + 互換ビュー `tcg_type_master` を提供。
本 Phase 2 ではコード・テスト内の `tcg_type_master` 参照を `type_master` に統一する。

## 変更箇所（フルパス:行番号）

### Python 本体

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/routers/super_admin_tcg.py:38` | コメント `public.tcg_type_master` → `public.type_master` |
| `backend/app/routers/super_admin_tcg.py:150` | コメント `public.tcg_type_master` → `public.type_master` |
| `backend/app/routers/super_admin_tcg.py:164,183,186,222,242,267,270` | SQL 文字列 `public.tcg_type_master` → `public.type_master` |
| `backend/app/routers/products.py:100-101` | 関数名 `_tcg_type_master_ref` → `_type_master_ref`、SQL 文字列 `public.tcg_type_master` → `public.type_master` |
| `backend/app/routers/products.py:108,113,116,271,274,277,317,319` | コメント・SQL 文字列置換 |
| `backend/app/routers/tcg_product_import.py:135,317,319` | SQL 文字列 `public.tcg_type_master` → `public.type_master` |
| `backend/app/services/tcg_product_import_svc.py:168-170` | コメント・SQL 文字列置換 |
| `backend/app/services/tcg_product_master_svc.py:83-88,365-366` | コメント・SQL 文字列置換 |
| `backend/app/services/tcg_product_detail_svc.py:73-79,121,128` | コメント・SQL 文字列置換 |
| `backend/app/services/tcg_analyzer_svc.py:425` | SQL 文字列置換 |
| `backend/app/services/tcg_analysis_review_svc.py:41,303` | SQL 文字列置換 |
| `backend/app/services/tcg_product_roundtrip_svc.py:101-102,191-192` | コメント・SQL 文字列置換 |
| `backend/app/services/tcg_work_reference.py:63` | SQL 文字列置換 |
| `backend/app/services/tcg_distribution_svc.py:238` | SQL 文字列置換 |
| `backend/app/services/tcg_work_comparison_svc.py:129` | dict キー `"tcg_type_master"` → `"type_master"`、SQL 文字列置換 |

### スキーマ（コメントのみ）

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/schemas/central_masters.py:112-113` | コメント置換 |
| `backend/app/schemas/product_masters.py:6` | コメント置換 |

### テスト

| ファイル | 変更内容 |
|---------|---------|
| `backend/tests/conftest.py:122` | コメント置換 |
| `backend/tests/conftest.py:176-177` | `.replace("public.type_master", "type_master")` に変更 |
| `backend/tests/conftest.py:687` | `CREATE TABLE IF NOT EXISTS type_master` |
| `backend/tests/conftest.py:726` | `INSERT OR IGNORE INTO type_master` |
| `backend/tests/conftest.py:816` | `REFERENCES type_master(code)` |
| `backend/tests/test_tcg_work_matching_integration.py:36,230` | コメント置換 |
| `backend/tests/test_tcg_work_matching_integration.py:323,650,939,1014,1021,1070,1318,1503` | SQL 文字列置換 |
| `backend/tests/test_tcg_completion_safety.py:90,147` | SQL 文字列置換 |
| `backend/tests/test_tcg_distribution_pg.py:58` | コメント置換 |
| `backend/tests/test_tcg_product_list_pg.py:115,150,164` | SQL 文字列・コメント置換 |
| `backend/tests/test_tcg_condition_review.py:87` | SQL 文字列置換 |
| `backend/tests/test_tcg_product_roundtrip_pg.py:41,56,90` | SQL 文字列置換 |
| `backend/tests/test_products_tcg_type_fk.py:36` | migration ファイル名文字列のため変更なし |

### フロントエンド（コメントのみ）

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/pages/super-admin/ProductMastersTab.tsx:12,73` | コメント置換 |
| `frontend/src/pages/super-admin/TcgSeriesTab.tsx:9` | コメント置換 |

### CI/CD

| ファイル | 変更内容 |
|---------|---------|
| `.github/workflows/migration-guard.yml:224` | `PUBLIC_TABLES` から `tcg_type_master` を削除（`type_master` は既存） |
| `.github/workflows/migration-guard.yml:416,503` | `PROTECTED_TABLES` の `tcg_type_master` → `type_master` |
| `.github/workflows/migration-guard.yml:476,576` | echo 文の `tcg_type_master` → `type_master` |

### Migration（CI 並列テスト互換性修正のみ・本番影響なし）

| ファイル | 変更内容 |
|---------|---------|
| `migrations/085_create_tcg_type_master.sql` | relkind チェックで VIEW 時は `type_master` に対して操作する DO $$ ブロックに変更 |
| `migrations/086_seed_additional_tcg_types.sql` | 同様に relkind チェックを追加 |
| `migrations/20260616_000000_fix_tcg_type_dedup.sql` | relkind チェックで `_target` を分岐、DELETE を EXECUTE format に変更 |
| `migrations/20260623_060000_add_products_tcg_type_fk.sql` | relkind チェックで FK ターゲットを `type_master` に切り替え |

## 変更しないもの

- `migrations/` 内の上記4ファイル以外（他 migration の `tcg_type_master` 文字列はそのまま）
- `backend/tests/rls_bootstrap.py` の migration ファイル名文字列
- `backend/tests/test_products_tcg_type_fk.py:36` の `"085_create_tcg_type_master.sql"` ファイル名文字列

## ADR 参照

- ADR-156: type_master リネーム（Phase 1 = DB リネーム、Phase 2 = コード統一）
- ADR-083: TCG 種別マスタ
