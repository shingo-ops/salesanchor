# recon: TCG_SCHEMA 環境変数化（TENANT-01）

## 調査日
2026-09-05

## 既存 ADR 検索結果
```
git grep -i "tcg_schema" docs/adr/
→ 該当なし（TCG_SCHEMA に関する ADR は未存在）

git grep -i "tcg" docs/adr/
→ ADR-072 (hybrid tenant strategy), ADR-131 (tenant context),
  ADR-025 (meta integration) に TCG 言及あり。スキーマ環境変数化は今回が初
```
`docs/adr/FEATURE-INDEX.md` に TCG_SCHEMA エントリなし（確認済み）。

## ハードコード箇所（修正前）

全 12 ファイルに `TCG_SCHEMA = "tenant_004"` がモジュールレベルで定義されていた。

| ファイル | 旧定義行 |
|---------|---------|
| `backend/app/services/tcg_analysis_review_svc.py:14` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/services/tcg_analyzer_svc.py:40` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/services/tcg_diagnostics_svc.py:13` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/services/tcg_distribution_svc.py:36` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/services/tcg_line_import_svc.py:24` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/services/tcg_parallel_report_svc.py:28` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/services/tcg_product_master_svc.py:25` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/services/tcg_supplier_quality_svc.py:13` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/tasks/tcg_extraction.py:38` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/tasks/tcg_mirror.py:33` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/tasks/tcg_import_discard.py:21` | `TCG_SCHEMA = "tenant_004"` |
| `backend/app/routers/tcg_line_import.py` | `TCG_SCHEMA = "tenant_004"` |

## コンテナへの環境変数伝達経路

**【事実】** IMP-29 にて確立済み。

- `docker-compose.yml`: `backend` / `celery-worker` / `celery-beat` サービスの `environment` セクション
- `scripts/blue-green-cutover.sh`: `docker run` の `--env` フラグ（docker-compose.yml とは独立した起動経路）

blue-green-cutover.sh を経由しないと本番 backend コンテナに環境変数が渡らないことを確認済み
（参照: `docs/handoff/zero-downtime-deploy/design.md`）。

## ルーター確認

`backend/app/routers/tcg_line_import.py` にも `TCG_SCHEMA = "tenant_004"` が存在。
モジュール検索は `git grep 'TCG_SCHEMA = "tenant_004"' backend/` で実施。

## テスト確認

修正前に影響するテストファイル:

| ファイル | 影響箇所 |
|---------|---------|
| `backend/tests/test_tcg_gemini_extraction.py:347` | `sql.replace("{TCG_SCHEMA}", "tenant_004")` |
| `backend/tests/test_tcg_gemini_extraction.py:366,386` | `assert "tenant_004." in sql` |
| `backend/tests/test_tcg_line_import.py` | SQL アサーション内の `tenant_004.` |
| `backend/tests/test_tcg_schema_qualification.py` | ソース静的検査（修正不要・`{TCG_SCHEMA}.` パターンを検証済み） |
