---
branch: release/tcg-import-hotfix-imp39
date: 2026-09-05
card: IMP-39
---

# recon: TCG LINE import ホットフィックス（IMP-39）

## 発見経緯

本番デプロイ後に発覚。migration は正常（`review_status` カラムの ADD COLUMN IF NOT EXISTS 適用済み確認済み）。
ルーター順序と型変換の実装ミスが原因。

## 確認コマンド（IMP-38 SSH 読み取り）

```
# migration 適用確認
docker compose exec -T backend bash -c \
  "psql -U \$POSTGRES_USER -d \$POSTGRES_DB -c \
   \"SELECT column_name FROM information_schema.columns WHERE table_name='import_jobs' AND column_name='review_status';\""
# → review_status 1行確認

# 発生エラー確認（本番ログ）
# GET /api/v1/tcg/line-import/history → 500
# POST /api/v1/tcg/line-import         → 500
```

## バグ 1: ルーター順序

### 現象
`GET /api/v1/tcg/line-import/history` が 500 を返す。

### 根本原因
`backend/app/routers/tcg_line_import.py` で `/{import_job_id}` が `/history`・`/unresolved` より前に定義されていた。
FastAPI はルートを定義順に評価するため、リテラル `"history"` が `import_job_id` に捕捉された。

### 影響ファイル
- `backend/app/routers/tcg_line_import.py`

## バグ 2: datetime 型変換

### 現象
`POST /api/v1/tcg/line-import` が 500 を返す。

### 根本原因
`backend/app/services/tcg_line_import_svc.py` の `_compute_window` が `str | None` を返す。
`import_jobs` テーブルの `window_start` / `window_end` カラムは `TIMESTAMPTZ`。
asyncpg は文字列を TIMESTAMPTZ カラムへの直接渡しを拒否する。
INSERT 時に `datetime` オブジェクトへの変換が抜けていた。

### 影響ファイル
- `backend/app/services/tcg_line_import_svc.py`

## 既存テスト影響

修正前: 48 件 PASS
修正後: 51 件 PASS（3 件追加）

追加テスト:
- `test_history_route_before_job_id_route` — ルーター順序をリグレッション防止
- `test_pending_route_before_job_id_route` — 同上
- `test_import_window_start_passed_as_datetime` — INSERT 時に datetime が渡ることを検証

## 関連 ADR / PR

- ADR-154: GAS→FastAPI 照合ロジック（変更なし）
- PR #3306: TCG import review stage 本体（migration 適用済み）
- IMP-38: SSH 読み取りで migration 適用・エラー確認
