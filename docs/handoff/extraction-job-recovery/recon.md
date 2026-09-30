# recon：抽出ジョブの停滞回収

- 作成：2026-09-30（実装担当、設計担当の指示に基づき origin/main を再確認）
- 基準：origin/main（2026-09-30 実装担当セッションで fetch 済み。worktree HEAD = `34abf56e8`）

## 1. 事実（origin/main 上のファイルを実際に開いて確認）

| 事実 | 根拠 |
|---|---|
| `worker_prefetch_multiplier=1`・`task_acks_late=True`・`task_reject_on_worker_lost=True` が設定されている。`broker_transport_options` は無い | `backend/app/celery_app.py:52`、`:54`、`:55` |
| `tcg.extract_source_message`（`extract_source_message_task`）は `max_retries=2`・`time_limit=330`・`soft_time_limit=300` | `backend/app/tasks/tcg_extraction.py:576`、`:578`、`:579` |
| `_run_extraction` は `ej.status = 'pending'` の行だけを取得する（`ORDER BY created_at DESC LIMIT 1`） | `backend/app/tasks/tcg_extraction.py:224-249` |
| `docker-compose.yml` の celery-worker サービス（197〜262行目）には `stop_grace_period` と `stop_signal` が無い。`command` は `--concurrency=2` | `docker-compose.yml:197-262` |
| `.github/workflows/deploy.yml:332-335` は `frontend celery-worker celery-beat discord-gateway` をまとめて `docker ps -a --filter name=astro-webapp-${_svc} \| xargs -r docker rm -f` で強制削除してから `docker compose up -d --no-deps --remove-orphans ...` している。キューが空になるのを待つ処理は無い | `.github/workflows/deploy.yml:332-335` |
| 停滞ジョブを自動で直す beat タスクは無い。`extraction-running-stale` 診断（`backend/app/services/tcg_diagnostics_svc.py:91-100`）は `ej.status='running' AND ej.created_at < NOW() - INTERVAL '10 minutes'` を返すだけの読み取り専用 SQL で、更新は行わない | `backend/app/services/tcg_diagnostics_svc.py:91-100` |
| `extraction_jobs.status` は `VARCHAR(30) NOT NULL` で CHECK 制約は無い（自由文字列。コード側で pending/running/error/done/empty/filtered を使用） | `migrations/20260921_110000_pipeline_tables_public.sql:80-89` |
| `extraction_attempts` は `extraction_job_id`・`started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()` を持ち、`extraction_jobs` への FK は `ON DELETE CASCADE` | `migrations/20260914_010000_tcg_extraction_attempts.sql`（`CREATE TABLE` 節、`started_at` 列・`extraction_attempts_job_fk` 制約） |
| 既存の `retry_extraction(db, job_ids=None, scope="pending")`（`backend/app/services/tcg_diagnostics_svc.py:146-234`）は `status='pending'` の全件（`ORDER BY created_at ASC LIMIT 50`）を対象に、`extract_source_message_task.apply_async(countdown=i*3)` で再エンキューする。`AsyncSession` を要求する非同期関数 | `backend/app/services/tcg_diagnostics_svc.py:146-234`（`_MAX_JOBS=50`、`_COUNTDOWN_STEP=3`） |
| Celery タスクから非同期関数を呼ぶ既存パターンは `asyncio.run()` ＋ ワンショット `create_async_engine`/`async_sessionmaker`（モジュールレベルの `AsyncSessionLocal` は別イベントループに紐付くため使えない） | `backend/app/tasks/tcg_extraction.py:610-642`（`auto_distribute_after_analysis_task`） |
| 同様のパターンで、単純な beat タスクは同期 SQLAlchemy（`create_engine` + `sessionmaker`）＋ `@shared_task` で書かれている例もある | `backend/app/tasks/tcg_import_discard.py`（全体） |
| ADR-1003（GO委任）が存在する | `docs/adr/ADR-1003-go-delegation-to-opus.md` |

## 2. 本番の数字（設計担当が提示した既知の値。今回の実装担当は再計測していない）

- 直近7日の attempt 所要時間：p50 2.4 秒、p90 5.3 秒、最大 31.9 秒（1,142 件）
- deploy.yml 実行回数：09-24 09:02 〜 09-30 03:24 に 51 回
- 9/30 03:29 のデプロイで pending 5 件・running 1 件が取り残された

これらの数値は設計担当（Opus）が本番 DB を読み取って提示したもので、実装担当セッションでは再確認していない。

## 3. 未確認

- 本番の `salesanchor_app` ロールが `extraction_attempts`／`extraction_jobs` に対して持つ権限の詳細（`GRANT SELECT,INSERT,UPDATE`固定分以外の付与状況）は、今回の実装（UPDATE のみ）には影響しないため未確認のまま進める。
