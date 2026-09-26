# design: tcg-extraction-retry

**対象 ADR**: ADR-154, ADR-027, ADR-144
**recon**: docs/handoff/tcg-extraction-retry/recon.md

## 設計方針

既存の TCG 診断 API（固定 SQL 方式・`require_super_admin`）にエンドポイントを 1 本追加し、
Celery タスク（`extract_source_message_task`）を再エンキューする。
DB の UPDATE は `status='error'` → `'pending'` への戻しのみ。migration なし。

## Request Body 形式

| フィールド | 型 | 意味 |
|-----------|------|------|
| `job_ids` | `list[str]` ｜ null | 再実行対象の extraction_job ID（最大 50 件） |
| `scope` | `"pending"` ｜ null | `status='pending'` の全件（最大 50 件）を対象 |

`job_ids` か `scope` のどちらか一方のみ必須（Pydantic `model_validator` で強制）。

**選択理由**: pending セクションは全件再実行が自然なので `scope: "pending"` の shorthand を提供。
error セクションは UI に表示済みの行 ID を用いて `job_ids` で POST する（表示件数 ≤ 100 件・POST は ≤ 50 件でスライス）。

## Countdown 分散

```
job at index i → countdown = i × 3 seconds
```

50 件を同時投入すると最後のジョブが 147 秒後にエンキュー。
Gemini API の 429 対策として、Celery worker 間でリクエストが分散される。

## done/running の扱い

`job_ids` 指定時: DB から全件取得 → `status IN ('pending', 'error')` でフィルタ → 残りを `skipped` に計上。
`scope: "pending"` 時: SQL で `WHERE status = 'pending'` のみ取得するため `skipped = 0`。

## Celery 503 処理

| 状況 | 処理 |
|------|------|
| `extract_source_message_task is None`（Celery 初期化失敗） | `RuntimeError` → `503` |
| `apply_async` が例外（Redis 接続失敗等） | `RuntimeError` → `503` |

既存の `_enqueue_extraction()` は握りつぶしていたが、本エンドポイントは明示的に 503 を返す。

## DB 変更

- `UPDATE tenant_004.extraction_jobs SET status = 'pending' WHERE id = ANY(:ids) AND status = 'error'`
- `db.commit()` 後に `reset_tenant_context()` は不要（`set_tenant_context()` を使用しないため）

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `POST /retry-extraction` scope=pending で 200・enqueued/skipped 返却 | `test_retry_extraction_scope_pending_returns_200` PASS |
| done/running ジョブが skipped にカウントされる | `test_retry_extraction_job_ids_done_running_are_skipped` PASS |
| super_admin 以外は 401/403 | `test_retry_extraction_requires_super_admin` PASS |
| extraction-pending セクションに「再実行」ボタンが表示される | `DiagnosticsDrawer.tsx` の extractionPending に `onRetry` prop あり |
| extraction-errors セクションに「再実行」ボタンが表示される | 同上 extractionErrors |
| ボタン押下で confirm → POST → toast | `handleRetryPending` / `handleRetryErrors` に実装 |
| `ja.json` / `en.json` の retryButton 等 5 キー追加 | 両ファイルに `retryButton` 他 4 キー存在 |
| 既存テスト 11 件が全件 PASS | `pytest backend/tests/test_tcg_diagnostics.py` 全件 PASS |

## 外部・過去事例

- Celery `apply_async(countdown=N)` — ETA ベースよりも `countdown` の方が相対指定で簡潔（Celery 公式ドキュメント）
- Gemini API 429 backoff: 件数×3秒は Google の推奨 exponential backoff の第一段階（1件目=0, 2件目=3秒, ...）に相当
- OWASP Top 10 A04 Insecure Design: rate limiting を UI 層（50件上限）とサービス層（countdown分散）の2段階で制御

## 維持の仕組み

守り手: `backend/tests/test_tcg_diagnostics.py`
- 既存 11 テスト（GET 診断・400・401） + 新規 3 テスト（POST retry）= 計 14 件
- Celery タスクのモック差し替えにより Redis なし環境でも全件 PASS
- 再実行エンドポイントの削除・signature 変更・認証外しを検出する
