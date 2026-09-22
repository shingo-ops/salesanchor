# ADR-1002 Phase B: Recon

## 現在の DB 状態（本番・2026-09-15 デプロイ成功後）

- `tcg_products` テーブル: 全テナントから DROP 済み（Phase 2c）
- `public.products` に `tcg_uuid` (UUID, UNIQUE) カラムあり — 297件が non-NULL
- 4テーブルの `product_id` は UUID 型、FK は `public.products(tcg_uuid)` を参照

| テナントテーブル | product_id 型 | FK 先 | FK 名 |
|----------------|-------------|-------|-------|
| product_search_keywords | UUID | public.products(tcg_uuid) | fk_product_search_keywords_product_public |
| product_exclude_keywords | UUID | public.products(tcg_uuid) | fk_product_exclude_keywords_product_public |
| products_logistics | UUID | public.products(tcg_uuid) | fk_products_logistics_product_public |
| analysis_results | UUID | public.products(tcg_uuid) | fk_analysis_results_product_public |

## tcg_uuid 参照箇所（全量 grep）

### サービス層（14ファイル・43箇所）

| ファイル | 行 | パターン |
|---------|---|---------|
| tcg_condition_review_svc.py | 104 | JOIN `cr_product.tcg_uuid::text = cr_data.ar->>'product_id'` |
| tcg_condition_review_svc.py | 232-233 | `SELECT p.tcg_uuid` + `ar.product_id=p.tcg_uuid` |
| tcg_product_import_svc.py | 288 | JOIN `p.tcg_uuid = k.product_id` |
| tcg_sold_out_results_svc.py | 31 | SELECT `p.tcg_uuid AS product_id` |
| tcg_sold_out_results_svc.py | 49 | JOIN `p.tcg_uuid = ar.product_id` |
| tcg_product_master_svc.py | 128 | SELECT `p.tcg_uuid::text AS product_uuid` |
| tcg_product_master_svc.py | 136,139 | JOIN + GROUP BY `p.tcg_uuid` |
| tcg_product_master_svc.py | 233,244 | JOIN + GROUP BY `p.tcg_uuid` |
| tcg_product_master_svc.py | 371,376 | INSERT with `tcg_uuid` + RETURNING `tcg_uuid::text AS id` |
| tcg_product_master_svc.py | 435 | WHERE `tcg_uuid = CAST(:id AS uuid)` |
| tcg_product_master_svc.py | 470 | SELECT `tcg_uuid::text AS id` |
| tcg_product_detail_svc.py | 40,42 | subquery `k.product_id=p.tcg_uuid` |
| tcg_product_detail_svc.py | 59-60 | dict key `product["tcg_uuid"]` → `product["id"]` |
| tcg_product_detail_svc.py | 90 | SELECT `tcg_uuid AS id` |
| tcg_product_detail_svc.py | 98,121,129,134,141 | `product["tcg_uuid"]` as param |
| tcg_analyzer_svc.py | 80 | SELECT `tcg_uuid AS id` |
| tcg_analyzer_svc.py | 190,208 | JOIN `p.tcg_uuid = psk/pek.product_id` |
| tcg_parallel_report_svc.py | 39 | SELECT `tcg_uuid AS id` |
| tcg_parallel_report_svc.py | 93,111 | JOIN `p.tcg_uuid = psk/pek.product_id` |
| tcg_analysis_review_svc.py | 40 | JOIN `p.tcg_uuid = ar.product_id` |
| tcg_product_roundtrip_svc.py | 106 | subquery `k.product_id=p.tcg_uuid` |
| tcg_product_roundtrip_svc.py | 211 | dict `snapshot["product"]["tcg_uuid"]` |
| tcg_product_roundtrip_svc.py | 324 | WHERE `tcg_uuid=CAST(:product_id AS uuid)` |
| tcg_unit_recovery_svc.py | 281,796 | JOIN `tp.tcg_uuid = ar.product_id` |
| tcg_result_order.py | 28 | ORDER BY `p.tcg_uuid ASC` |
| tcg_work_reference.py | 48,50 | subquery `k.product_id=p.tcg_uuid` |
| tcg_distribution_svc.py | 237 | JOIN `p.tcg_uuid = ar.product_id` |
| tcg_import_progress.py | 125 | JOIN `p.tcg_uuid = ar.product_id` |

### ルーター層（1ファイル・2箇所）

| ファイル | 行 | パターン |
|---------|---|---------|
| tcg_product_import.py | 113,115 | subquery `k.product_id = p.tcg_uuid` |

### テスト（11ファイル・70箇所）

省略（design.md に変換ルールを記載）

### conftest.py（1箇所）

| ファイル | 行 | 内容 |
|---------|---|------|
| tests/conftest.py | 768 | `tcg_uuid UUID,` カラム定義 — Phase C で削除（Phase B では残す） |

### _next_pm_code()（1ファイル・3箇所）

| ファイル | 行 | 内容 |
|---------|---|------|
| tcg_product_master_svc.py | 274 | 関数定義 |
| tcg_product_master_svc.py | 349 | 呼び出し |
| test_tcg_product_import.py | 359 | mock パッチ |
