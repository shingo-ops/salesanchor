# recon: tcg-diagnostics-extraction-keys

## タスク概要

TCG 診断 API（`GET /api/v1/tcg/diagnostics/{key}`）に抽出パイプライン監視用の
診断キーを4つ追加し、DiagnosticsDrawer のセクションとして表示する。

## 既存 ADR 検索結果

- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md` — 固定 SQL 診断 API の設計根拠
- `docs/adr/ADR-144-ui-component-governance.md` — UI ガバナンス（生 select/input 禁止）
- `docs/adr/ADR-027-ui-internationalization.md` — i18n 強制（t("key") 経由必須）

## 変更対象ファイル

### バックエンド
- `backend/app/services/tcg_diagnostics_svc.py:19` — `_ALLOWED_KEYS` に4キー追加
- `backend/app/services/tcg_diagnostics_svc.py:32` — `_QUERIES` に4 SQL 追加（TCG_SCHEMA・f-string・SELECT のみ）
- `backend/tests/test_tcg_diagnostics.py:7` — 8キーのカバーに拡張、4テスト追加

### フロントエンド
- `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:8` — 4 `DiagnosticsSection` 追加
- `frontend/src/locales/ja.json:2273` — sections 4キー + columns 9キー追加
- `frontend/src/locales/en.json:2273` — 同上（ja 対応）

## 既存パターン確認

### サービス層
- `backend/app/services/tcg_diagnostics_svc.py:13` — `TCG_SCHEMA = "tenant_004"` 定数を f-string で埋め込む
- `backend/app/services/tcg_diagnostics_svc.py:19` — `_ALLOWED_KEYS: frozenset[str]` で完全一致のみ許可
- `backend/app/services/tcg_diagnostics_svc.py:32` — `_QUERIES: dict[str, str]` にキーと SQL を 1:1 で固定埋め込み

### テスト層
- `backend/tests/test_tcg_diagnostics.py:110` — `patch("app.routers.tcg_diagnostics.run_diagnostic", AsyncMock(return_value=...))` パターン
- `backend/tests/test_tcg_diagnostics.py:54` — `super_admin_override` フィクスチャで依存性注入をバイパス

### フロントエンド
- `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:24` — `DiagnosticsSection` コンポーネント: `diagKey` / `titleKey` / `open` / `highlight?` props
- `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx:156` — `highlight={(row) => ...}` で行単位の赤表示制御

## テーブル構造確認（migration 参照）

- `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql` — `extraction_jobs` 定義:
  id UUID / source_message_id UUID FK / status VARCHAR(30) / extracted_at TIMESTAMPTZ / error_message TEXT / prompt_version VARCHAR(50) / created_at TIMESTAMPTZ
- 同 migration — `extraction_items.extraction_job_id` FK → `extraction_jobs.id`
- 同 migration — `analysis_results.extraction_item_id` UNIQUE FK → `extraction_items.id`

## status 遷移確認

`backend/app/tasks/tcg_extraction.py` より:
- pending → running（step2: UPDATE + commit）
- running → done/empty/error（step5: Gemini 結果を反映）
- 予期せぬ例外時: running のまま残留（DB UPDATE なし）→ `extraction-running-stale` で検出
