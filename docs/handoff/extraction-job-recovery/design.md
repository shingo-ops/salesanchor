# design：抽出ジョブの停滞回収

- 作成：2026-09-30（設計：Opus 設計担当 ／ 実装：Claude Sonnet 5 実装担当）
- 関連 ADR：ADR-1003（GO委任）
- recon: `docs/handoff/extraction-job-recovery/recon.md`

## §A 事実

recon.md 参照。要点のみ再掲する。

- `backend/app/celery_app.py:52-55`：`worker_prefetch_multiplier=1`、`task_acks_late=True`、`task_reject_on_worker_lost=True`。`broker_transport_options` はない。
- `backend/app/tasks/tcg_extraction.py` の `tcg.extract_source_message`：`max_retries=2`、`time_limit=330`、`soft_time_limit=300`。`_run_extraction` は `status='pending'` のジョブだけを拾う（224-249行目）。
- `docker-compose.yml:197-262` の celery-worker には、`stop_grace_period` と `stop_signal` がない。`--concurrency=2`。
- `.github/workflows/deploy.yml:332-335`：`docker ps -a --filter name=astro-webapp-${_svc} | xargs -r docker rm -f` で強制削除してから `docker compose up -d`。キューが空になるのを待つ処理はない。
- 停滞ジョブを自動で直す beat タスクはない。`backend/app/services/tcg_diagnostics_svc.py:91-100` の `extraction-running-stale` は、読み取りの診断だけ。
- 本番（2026-09-30）：直近7日の attempt 所要時間は p50 2.4 秒、p90 5.3 秒、最大 31.9 秒（1,142 件）。deploy.yml は 09-24 09:02 から 09-30 03:24 までに 51 回。9/30 03:29 のデプロイで、pending 5 件と running 1 件が取り残された。

## §B 変更

1. **停滞ジョブの回収タスク（新規）**：`backend/app/tasks/tcg_extraction_recovery.py`
   - Celery タスク `tcg.recover_stale_extraction_jobs` を作り、beat で10分ごとに動かす。
   - 回収の条件は定数でまとめる：`STALE_RUNNING_MINUTES=15`、`STALE_PENDING_MINUTES=15`、`MAX_RECOVER_PER_RUN=50`。
     - 根拠は §A（最大 32 秒、time_limit 330 秒）。実行中の attempt が15分を超えることは、time_limit 上ありえない。
   - (a) running のジョブで、最新の attempt の `started_at` から15分以上たったもの（attempt がなければ `created_at` から15分以上）を pending に戻す。
     - `UPDATE public.extraction_jobs SET status='pending' WHERE id = ANY(:ids) AND status='running'`
   - (b) pending のジョブで、`created_at` から15分以上たち、最新の attempt が無いか、あっても15分以上前に始まったものを、`retry_extraction(scope="pending")` と同じ方法（`extract_source_message_task.apply_async` を countdown 付きで呼ぶ）で再投入する。
     - 既存の `retry_extraction`（`backend/app/services/tcg_diagnostics_svc.py`）をそのまま import して呼ぶ。新しい再投入ロジックは増やさない。
     - `retry_extraction` は `AsyncSession` を要求する非同期関数なので、`backend/app/tasks/tcg_extraction.py:610-642`（`auto_distribute_after_analysis_task`）と同じパターン（ワンショット `create_async_engine`/`async_sessionmaker` ＋ `asyncio.run()`）で呼ぶ。
     - 最大 `MAX_RECOVER_PER_RUN` 件。古いものから（`retry_extraction` 内部が `ORDER BY created_at ASC LIMIT 50` のため、この上限は `retry_extraction` 自身の `_MAX_JOBS=50` と一致させる）。
   - 回収した件数と ID を `logger.warning` で出す。
   - DB の表や列は増やさない。
   - 見分けに使うのは、既存の `extraction_jobs` の `status` と `extraction_attempts` だけ。

2. **beat への登録**：`backend/app/celery_app.py` の `beat_schedule` に `recover-stale-extraction-jobs` を足す。10分ごと（`schedule=600.0`、既存の `refresh-dashboard-kpis` と同じ書式）。

3. **止め方をていねいにする**：
   - `docker-compose.yml` の celery-worker に、`stop_signal: SIGTERM` と `stop_grace_period: 60s` を足す。
   - `.github/workflows/deploy.yml:332-335` のループは、今 celery-worker も含めて一律 `docker rm -f` している。
   - これを「celery-worker だけは、先に `docker compose stop -t 60 celery-worker` で止めて（warm shutdown で実行中のタスクを終えさせる）、そのあと rm する」に変える。
   - ループの対象からは celery-worker を外し、`frontend celery-beat discord-gateway` の3つだけを従来どおり force-rm する。celery-worker は事前に `stop -t 60` してから、同じループの外で rm する。
   - ほかのサービス（frontend / celery-beat / discord-gateway）の扱いは変えない。変更は最小にする。

## §C 検証（基準と方法）

| # | 基準 | 方法 |
|---|---|---|
| T1 | 15分未満の running と pending は触らない | 単体テスト |
| T2 | 15分以上の running は pending に戻り、そのあと再投入される | 単体テストまたは pg テスト |
| T3 | 1回に回収するのは最大50件 | 単体テスト |
| T4 | beat に10分ごとで登録されている | テスト |
| V1 | 本番に反映したあと、beat が登録されている | celery inspect／beat のログ |
| V2 | 反映したあと30分以内に、pending・running が15分以上残っていない | 本番 DB の読み取り |

## §D リスク・戻し方

- 実行中のジョブを誤って二重に動かすリスクについて：time_limit が 330 秒なので、15分以上実行中のものは実在しない。回収は pending に戻すだけで、処理の冪等性は既存の retry と同じ（`extraction_items` を消して入れ直す、`retry_extraction` 内部の処理）。
- 戻し方：この PR を revert する。

## 維持の仕組み

- 守り手: Opus 設計担当（しきい値の見直し）／PO（運用の判断）
- しきい値（`STALE_RUNNING_MINUTES`・`STALE_PENDING_MINUTES`・`MAX_RECOVER_PER_RUN`）は定数としてモジュール冒頭にまとめ、根拠のコメントを§Aへのリンクとして残す。将来 `time_limit` を変更する場合は、このファイルのコメントが変更点を示す。
- beat 登録のテスト（T4）があるため、`beat_schedule` からの削除・書式崩れは CI で検知される。
- 回収件数と ID を `logger.warning` で出すため、本番ログ（Loki/Promtail 経由）で回収の発生を事後に確認できる（V1/V2 の裏付け）。

## 外部・過去事例

- 該当なし。社内の既存パターン（`backend/app/tasks/tcg_import_discard.py` の期限切れ回収タスク、`backend/app/tasks/tcg_extraction.py:610-642` の Celery→非同期サービス呼び出しパターン）を根拠にした。Celery の stale task 回収は Celery 公式ドキュメントの `task_acks_late`/`worker_prefetch_multiplier` の推奨設定（本リポジトリは既に採用済み、recon.md 参照）に沿う一般的な対処であり、外部の失敗事例調査は本件の変更規模（既存パターンの組み合わせ）に対して不要と判断した。
