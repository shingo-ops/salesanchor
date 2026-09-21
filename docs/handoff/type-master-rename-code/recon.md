# recon: ADR-156 Phase 2 — tcg_type_master → type_master コード統一

## 関連ADR
- ADR-083: TCG 種別マスタ設計（固定リスト廃止・DB管理化）
- ADR-156: type_master リネーム（Phase 1=DB リネーム、Phase 2=コード統一）

## 変更箇所（フルパス:行番号）

### Python 本体

**backend/app/routers/products.py**
- `products.py:124` — エラーメッセージ `tcg_type_master.code` → `type_master.code`

**backend/app/schemas/central_masters.py**
- `central_masters.py:112-113` — ADR-083 コメント `public.tcg_type_master` → `public.type_master`、`tcg_type_master` → `type_master`

**backend/app/schemas/product_masters.py**
- `product_masters.py:6` — モジュール docstring `public.tcg_type_master` → `public.type_master`

**backend/app/services/tcg_analysis_review_svc.py**
- `tcg_analysis_review_svc.py:41` — LEFT JOIN `public.tcg_type_master ws` → `public.type_master ws`
- `tcg_analysis_review_svc.py:303` — SELECT `FROM public.tcg_type_master s` → `FROM public.type_master s`

**backend/app/services/tcg_analyzer_svc.py**
- `tcg_analyzer_svc.py:425` — SELECT `FROM public.tcg_type_master` → `FROM public.type_master`

**backend/app/services/tcg_distribution_svc.py**
- `tcg_distribution_svc.py:238` — LEFT JOIN `public.tcg_type_master ser` → `public.type_master ser`

**backend/app/services/tcg_product_detail_svc.py**
- `tcg_product_detail_svc.py:73` — コメント `public.tcg_type_master` → `public.type_master`
- `tcg_product_detail_svc.py:76` — SELECT `FROM public.tcg_type_master` → `FROM public.type_master`
- `tcg_product_detail_svc.py:120` — コメント `public.tcg_type_master` → `public.type_master`
- `tcg_product_detail_svc.py:128` — SELECT `"SELECT name_ja FROM public.tcg_type_master` → `public.type_master`

**backend/app/services/tcg_product_master_svc.py**
- `tcg_product_master_svc.py:83` — コメント `public.tcg_type_master` → `public.type_master`
- `tcg_product_master_svc.py:86` — SELECT `FROM public.tcg_type_master` → `FROM public.type_master`
- `tcg_product_master_svc.py:364` — コメント `tcg_type_master.name_ja` → `type_master.name_ja`
- `tcg_product_master_svc.py:366` — SELECT `FROM public.tcg_type_master` → `FROM public.type_master`

**backend/app/services/tcg_product_roundtrip_svc.py**
- `tcg_product_roundtrip_svc.py:101` — コメント `public.tcg_type_master` → `public.type_master`
- `tcg_product_roundtrip_svc.py:102` — LEFT JOIN `public.tcg_type_master work` → `public.type_master work`
- `tcg_product_roundtrip_svc.py:191` — コメント `public.tcg_type_master` → `public.type_master`
- `tcg_product_roundtrip_svc.py:192` — SELECT `FROM public.tcg_type_master r` → `FROM public.type_master r`

**backend/app/services/tcg_work_comparison_svc.py**
- `tcg_work_comparison_svc.py:129` — dict キー `"tcg_type_master"` → `"type_master"`、SQL `FROM public.tcg_type_master t` → `FROM public.type_master t`

**backend/app/services/tcg_work_reference.py**
- `tcg_work_reference.py:63` — SELECT `FROM public.tcg_type_master s` → `FROM public.type_master s`

### スキーマ（上記に含む）

### テスト

**backend/tests/conftest.py**
- `conftest.py:122` — docstring `tcg_type_master` → `type_master`
- `conftest.py:176-177` — SQLite 互換 `.replace("public.tcg_type_master", "tcg_type_master")` → `.replace("public.type_master", "type_master")`
- `conftest.py:687` — `CREATE TABLE IF NOT EXISTS tcg_type_master` → `type_master`
- `conftest.py:726` — `INSERT OR IGNORE INTO tcg_type_master` → `type_master`
- `conftest.py:816` — FK `REFERENCES tcg_type_master(code)` → `REFERENCES type_master(code)`

**backend/tests/test_tcg_work_matching_integration.py**
- `test_tcg_work_matching_integration.py:36` — コメント（→ `public.type_master.code mapping`）
- `test_tcg_work_matching_integration.py:230` — コメント `tcg_type_master must exist` → `type_master must exist`
- 複数行の `FROM public.tcg_type_master` → `FROM public.type_master`（全箇所）

**backend/tests/test_tcg_completion_safety.py**
- `test_tcg_completion_safety.py:90` — INSERT SELECT `FROM public.tcg_type_master w` → `public.type_master w`
- `test_tcg_completion_safety.py:147` — `'public.tcg_type_master'` → `'public.type_master'`

**backend/tests/test_tcg_distribution_pg.py**
- `test_tcg_distribution_pg.py:58` — コメント `public.tcg_type_master required` → `public.type_master required`

**backend/tests/test_tcg_product_list_pg.py**
- `test_tcg_product_list_pg.py:115` — SELECT `FROM public.tcg_type_master` → `FROM public.type_master`
- `test_tcg_product_list_pg.py:150` — コメント `tcg_type_master entries` → `type_master entries`
- `test_tcg_product_list_pg.py:164` — SELECT `FROM public.tcg_type_master` → `FROM public.type_master`

**backend/tests/test_tcg_condition_review.py**
- `test_tcg_condition_review.py:87` — INSERT SELECT `FROM public.tcg_type_master w` → `public.type_master w`

**backend/tests/test_tcg_product_roundtrip_pg.py**
- 複数行の `FROM public.tcg_type_master` → `FROM public.type_master`（全箇所）

**backend/tests/test_product_masters.py**
- `test_product_masters.py:33` — コメント `tcg_type_master 側` → `type_master 側`

### フロントエンド（コメントのみ）

**frontend/src/pages/super-admin/ProductMastersTab.tsx**
- `ProductMastersTab.tsx:12` — コメント `public.tcg_type_master` → `public.type_master`
- `ProductMastersTab.tsx:73` — JSDoc `public.tcg_type_master` → `public.type_master`

**frontend/src/pages/super-admin/TcgSeriesTab.tsx**
- `TcgSeriesTab.tsx:9` — コメント `public.tcg_type_master ベースへ移行` → `public.type_master ベースへ移行`

### CI/CD

**.github/workflows/migration-guard.yml**
- `migration-guard.yml:224` — `PUBLIC_TABLES` から `tcg_type_master` を削除（`type_master` は既存）
- `migration-guard.yml:403` — コメント `tcg_type_master` → `type_master`
- `migration-guard.yml:416` — `PROTECTED_TABLES` パイプ区切り `tcg_type_master` → `type_master`（2箇所）
- `migration-guard.yml:476` — echo 文 `tcg_type_master` → `type_master`（2箇所）

## 変更しなかった箇所（意図的）

- `migrations/` 配下のすべてのファイル（歴史的記録）
- `backend/app/routers/rls_bootstrap.py` の migration ファイル名文字列
- テストファイル内の `"085_create_tcg_type_master.sql"` 文字列（migration ファイル名参照）
