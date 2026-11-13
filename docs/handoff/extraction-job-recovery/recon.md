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

## 追記（2026-11-13）試験が時々落ちる件の調べ
- 基準: origin/main `c296af3bb`（worktree `release/test-clock-fix`）。生の記録は `/tmp/CC報告ファイル/flaky/`（手元のみ）

| 事実 | 根拠 |
|---|---|
| 試験ファイルは、読み込んだときに1回だけ「今」を決める: `_NOW = datetime.now(timezone.utc)` | `backend/tests/test_tcg_extraction_recovery_pg.py:20` |
| 「5分前に始まった」「5分前に作った」行を `_NOW` から作る | `backend/tests/test_tcg_extraction_recovery_pg.py:62`、`:110` |
| 「2分前に始まった」行を `_NOW` から作る | `backend/tests/test_tcg_extraction_recovery_pg.py:139` |
| 判定する側は DB の `NOW()` と15分を比べる | `backend/app/tasks/tcg_extraction_recovery.py:37-38`、`:78`、`:126`、`:129` |
| 試験ごとに `pg` の用意（DB 作成・表作り・migrate）が走り、終わってから試験本体が動く | `backend/tests/test_tcg_work_matching_integration.py:385`、`:398`、`:406`、`:408`、`:425` |
| 落ちた回（3回・ブランチはすべて別）: 2026-11-11 run 42988382082（pending の1件）、2026-11-12 run 43241609917（2件）、2026-11-13 run 43333593852（2件・流し直しで合格） | `gh run view <id> --log-failed`。直近200件の失敗 run のうち Backend Tests 28件を全部走査した |
| 落ちた形はどれも `assert jid not in result` が逆になる（5分前の行が「15分より古い」扱い） | run 43333593852 のログ（`AssertionError: assert '82d8…' not in ['82d8…']`） |
| run 43333593852 は Backend Tests 全体が13分06秒。2件は全体の93%地点で動いた | 同上 |
| 同じ書き方（ファイルの一番外で今の時刻を決める）は、ほかに1か所。日の単位の余裕で、実害は無い | `backend/tests/test_viewer_api.py:34`（使う所 `:311`、`:313`、`:347`、余裕は1日と2日） |
| 読み込みのときに時刻を読む所は、デコレータの引数にも2か所ある（審査1で指摘）。`revoked_at` は空でなければ必ず拒否、`expires_at` は過去なら必ず拒否で、時刻が古くなっても結果は変わらない（実害は無い） | `backend/tests/test_line_import_devices.py:25`、`:26`（判定 `backend/app/services/line_import_devices.py:98-102`、`now()` は `:37-38`） |
| backend/tests 配下の .py は 470 ファイル（git が追っているもの） | `git ls-tree -r --name-only c296af3bb backend/tests` の拡張子 .py の数。最初の版の「478」は数え方の誤りで、470 に直した |
| CI の Backend Tests は `pytest -q`（`-n auto`）で、試験ごとの合否の行は出ない。最後に合計の1行だけ出る（例: main の run 43339095971 は `8965 passed, 79 skipped, 1 xfailed`） | `.github/workflows/test.yml:257`、`backend/pyproject.toml` の `addopts`、run 43339095971 のログ |

### 計算（観測値からの算数）
- 読み込みから試験本体までの経過を E 分とすると、5分前の行は E≧10 で15分を超える（落ちる）。2分前の行は E≧13 で落ちる。run 43333593852 は5分の2件だけが落ちたので 10≦E<13。
- つまり、試験全体が長くなるほど落ちやすい。試験の数は増え続けるので、放っておくと落ちる回数は増える。

### 未確認
- 3回より前（直近200件の失敗 run より前）に落ちた回数は数えていない。
