# recon: tcg-extraction-retry

## タスク概要

TCG 診断 API に再実行エンドポイント（`POST /api/v1/tcg/diagnostics/retry-extraction`）を追加し、
DiagnosticsDrawer の extraction-pending・extraction-errors セクションに「再実行」ボタンを追加する。

## 実測の経緯

2026-09-05 11:20 の取り込みで、Gemini の無料枠上限により 15件が pending のまま滞留した。
Celery は起動中であったが Gemini API が 429 を返し続けたため、タスクが retry 上限に到達して
`status='error'` に遷移した行と、エンキュー自体が行われずに `status='pending'` のまま残った行が混在した。
手動で再実行するために UI ボタンが必要と判断した。

## 既存 ADR 検索結果

- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md` — 固定 SQL 診断 API の設計根拠（SELECT のみ・`_ALLOWED_KEYS` frozenset）
- `docs/adr/ADR-072-write-endpoint-tenant-context-reset.md` — write endpoint の `db.commit()` 直後 `reset_tenant_context()` 必須
  - **本タスクでは**: retry エンドポイントは `set_tenant_context()` を経由しない（TCG_SCHEMA 直指定）ため `reset_tenant_context()` 不要と判断
- `docs/adr/ADR-027-ui-internationalization.md` — i18n 強制（`t("key")` 経由必須）
- `docs/adr/ADR-144-ui-component-governance.md` — UI ガバナンス（生 Button 禁止・コンポーネント使用必須）

## 変更対象ファイル

### バックエンド
- `backend/app/routers/tcg_diagnostics.py` — `POST /tcg/diagnostics/retry-extraction` エンドポイント追加
- `backend/app/services/tcg_diagnostics_svc.py` — `retry_extraction()` 関数追加（UPDATE + Celery enqueue）
- `backend/tests/test_tcg_diagnostics.py` — 再実行エンドポイントのテスト 3 件追加

### フロントエンド
- `frontend/src/features/tcg-analysis-review/DiagnosticsDrawer.tsx` — `DiagnosticsSection` に `onRetry` prop 追加、再実行ボタン、toast 連携
- `frontend/src/locales/ja.json` — `superAdmin.diagnostics.retryButton` 他 4 キー追加
- `frontend/src/locales/en.json` — 同上

## 既存パターン確認

### Celery タスク定義
- `backend/app/tasks/tcg_extraction.py:255` — `extract_source_message_task(self, source_message_id: str) -> dict`
- `backend/app/tasks/tcg_extraction.py:274` — Redis 未起動時は `extract_source_message_task = None`
- `backend/app/services/tcg_line_import_svc.py:538` — `_enqueue_extraction()` は例外を握りつぶす（今回は別扱い）

### DB テーブル構造
- `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql` — `extraction_jobs(id UUID, source_message_id UUID FK, status VARCHAR(30), ...)`
- status 遷移: pending → running → done/empty/error（`backend/app/tasks/tcg_extraction.py`）

### 既存 super_admin ルーター作法
- `backend/app/routers/tcg_diagnostics.py:48` — `_user: dict = Depends(require_super_admin)`
- `backend/app/auth/dependencies.py:317` — `reset_tenant_context(db, tenant_id: int)`（本タスクでは不使用・ADR-072 検討済み）

## 守り手

`backend/tests/test_tcg_diagnostics.py` — 既存 11 テスト + 新規 3 テスト（全 14 件 PASS 維持）
