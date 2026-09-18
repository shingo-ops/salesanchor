# Recon: 仕入元マスタ SSOT Sprint 1

## 既存ADR検索結果
- `docs/adr/` の `supplier` キーワード検索: 直接関連する確定ADRなし
- Migration 056 (`migrations/056_add_suppliers_type_and_promote_public.sql`): public.suppliers テーブルを作成（SERIAL PK, supplier_code UNIQUE）
- Migration 20260603_010000 (`migrations/20260603_010000_add_suppliers_line_and_address.sql`): public.suppliers に line_name カラム追加
- Migration 20260912_170000 (`migrations/20260912_170000_line_supplier_source_names.sql`): public.line_supplier_source_names テーブル作成（今回DROP対象）
- Migration 20260831_110000 (`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql`): tcg_suppliers(UUID PK), supplier_channels(supplier_id UUID FK → tcg_suppliers) を作成
- Migration 20260906_120000 (`migrations/20260906_120000_create_tcg_tables_t001.sql`): 同上（t001用）+ seed データ SP9001/SP9002/SP9003 with LINE channels

## 現在の構造
- `{schema}.tcg_suppliers`: id UUID PK, code VARCHAR(20) UNIQUE, name TEXT, is_active BOOLEAN
- `{schema}.supplier_channels`: id UUID PK, supplier_id UUID NOT NULL FK→tcg_suppliers(id), channel VARCHAR(50), is_active BOOLEAN
- `public.suppliers`: id SERIAL PK, supplier_code VARCHAR(20) UNIQUE, name, line_name (NULL許可), supplier_type, is_active
- `public.line_supplier_source_names`: tcg_schema, source_format, display_name, supplier_id UUID, evidence_sha256 (DROP対象)

## 変更対象ファイル
- `migrations/20260917_020000_supplier_ssot_migration.sql`: 新規作成（Sprint 1 migration）
- `scripts/run_all_migrations.sh:673`: 新規migration登録（末尾追加）
- `backend/tests/test_tcg_import_progress_pg.py:66-67,355-363`: UUID→INTEGER fixture変更 + Sprint 1 migration適用
- `backend/tests/test_tcg_line_import.py:538,606,744,863`: mock判定文字列 tcg_suppliers→public.suppliers
- `backend/tests/test_line_source_names.py:129`: assert文字列 tcg_suppliers→public.suppliers
- `backend/tests/test_tcg_result_order.py:76-81,221-223`: INSERT文 tcg_suppliers→public.suppliers + ANALYZE list変更
- `backend/tests/test_tcg_sold_out_results.py:131-134`: INSERT文変更 + Sprint 1 migration適用

## 触らない範囲
- サービスコード (tcg_line_import_svc.py, tcg_sold_out_results_svc.py 等) — Sprint 2 で対応
- フロントエンド — Sprint 2 以降
- tcg_suppliers テーブル削除 — Sprint 2 以降
