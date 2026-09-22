# Recon: TCG_SCHEMA 配線統一

## 調査日: 2026-09-23

### 問題
パイプラインテーブルは public に移行済みだが、10ファイルが `from app.tcg_config import TCG_SCHEMA` 経由で `tenant_004` を参照。
本番環境変数 `TCG_SCHEMA=tenant_004` のまま、テーブルは public にあるため、特定コードパスで「テーブルが見つからない」エラーが潜在。

### 本番DB実測
- `backend/app/tcg_config.py:20`: `_RAW = os.getenv("TCG_SCHEMA", "tenant_004")`
- `backend/app/tcg_config.py:21`: `_VALID = re.compile(r"^tenant_\d{3}$")` — "public"を拒否
- 本番環境変数: `TCG_SCHEMA=tenant_004`
- `public.line_import_devices`: 1行、`tcg_schema = 'tenant_004'`
- pipeline tables (analysis_results, extraction_items 等): public のみ（tenant_004 から削除済み）
- tcg_manufacturers: tenant_004 のみ（5行）
- tcg_series: tenant_004 のみ（11行）  
- tcg_unit_evidence_rules: tenant_004 のみ（4行）

### 既に修正済みのファイル (15本)
ローカル `TCG_SCHEMA = "public"` を使用: tcg_line_import.py, tcg_extraction.py, tcg_diagnostics_svc.py 等

### 未修正だったファイル (10本・本PR対象)
tcg_product_import.py, tcg_mirror.py, tcg_product_import_svc.py, tcg_product_master_svc.py,
tcg_product_detail_svc.py, line_import_devices.py, tcg_product_roundtrip_svc.py,
tcg_work_comparison_svc.py, line_import_admin.py, tcg_line_import_svc.py
