# recon.md — fix-auto-distribute

調査日: 2026-09-20

---

## Error 1: celery-worker が TCG_SHEETS_SA_KEY_FILE を持っていない

### 観測事実
- `docker-compose.yml:115` — backend サービスは `TCG_SHEETS_SA_KEY_FILE=${TCG_SHEETS_SA_KEY_FILE:-}` を environment に持つ
- `docker-compose.yml:120` — backend サービスは `${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro` を volumes に持つ
- `docker-compose.yml:191-239` — celery-worker サービスの environment / volumes に上記2行が存在しない（修正前）
- 結果: celery-worker で auto_distribute_after_analysis_task が Google Sheets SA キーを参照しようとすると `FileNotFoundError` または認証失敗

### コード参照
- `docker-compose.yml:115` — backend env 定義（対象パターン）
- `docker-compose.yml:120` — backend volume マウント（対象パターン）
- `docker-compose.yml:220-223` — celery-worker の TCG_SCHEMA 以下・volumes（修正対象箇所）

---

## Error 2: asyncio.run() が新規ループを生成し、モジュールレベルエンジンが旧ループに紐付く

### 観測事実
- `backend/app/database.py:33` — `engine = create_async_engine(DATABASE_URL, **_engine_kwargs)` がモジュールロード時に生成される
- `backend/app/database.py:36-40` — `AsyncSessionLocal = sessionmaker(engine, ...)` も同じくモジュールロード時に生成される
- `backend/app/tasks/tcg_extraction.py:398-406` — `auto_distribute_after_analysis_task` 内で `asyncio.run(_run())` を呼ぶと新規イベントループが作成されるが、`AsyncSessionLocal` が参照する `engine` は Celery ワーカー起動時のループ（または None ループ）に紐付いている
- 結果: `RuntimeError: Task <Task ...> got Future <Future ...> attached to a different loop`

### 既知パターン
- `asyncio.run()` は毎回新しいループを作る。SQLAlchemy async engine のコネクションプールはループに紐付く。Celery の同期タスクから `asyncio.run()` で非同期処理を呼ぶ場合は、ループ内でエンジンを生成しなければならない（ワンショットエンジンパターン）。

### コード参照
- `backend/app/database.py:33` — モジュールレベルエンジン生成
- `backend/app/database.py:36-40` — AsyncSessionLocal 定義
- `backend/app/tasks/tcg_extraction.py:396-406` — 問題の asyncio.run() 呼び出し（修正前）

---

## 既存 ADR 調査

- `ADR-100`: TCG 配信パイプライン関連（`docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md`）— 本修正の対象 ADR
