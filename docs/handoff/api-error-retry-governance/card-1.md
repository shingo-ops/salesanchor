# 実装カード 1 — api-error-retry-governance（諦めた分の知らせ・月曜の数の知らせ）

親: docs/handoff/api-error-retry-governance/design.md
この文書は何か: Sonnet が迷わず作れるよう、触る場所・中身・試験・触らない範囲を決めたカード。

状態: カード発行（Opus、2026-10-30）。根拠: design.md 第1版（PO 2026-10-30「1」）、recon.md。
担当: Sonnet（クラウド）。触ってよいのは下の「触るファイル」だけ。本番 DB・VPS・GitHub secret には触らない。DB の変更なし。.github/workflows・migrations・scripts は触らない。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 新規ファイルは丸ごと書く／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが release/api-error-retry-governance で、HEAD に docs/handoff/api-error-retry-governance/card-1.md があることを報告の1行目に書く。

## 実装前点検（結果を報告に書く。外れたら実装せず BLOCKED で停止する）
- P1 `backend/app/tasks/tcg_extraction_recovery.py` の _run_recovery が、with Session() の中で retry_transient_api_error_jobs を呼んでいること（main 基準で :362〜:370 付近）。
- P2 `backend/app/services/discord_notifier.py` に _get_webhook_url と async の _post_discord_webhook があること（:40・:45 付近）。
- P3 `backend/app/celery_app.py` の include に app.tasks.bundle_bulk_monitor があり、beat_schedule に report-bundle-bulk-weekly があり、timezone が Asia/Tokyo であること。
- P4 `backend/tests/test_celery_beat_registered.py` が beat の全タスク名の登録を検査していること。

## 触るファイル

1. `backend/app/tasks/tcg_extraction_recovery.py`（足すだけ。既存の関数の中身は変えない）
2. backend/app/tasks/api_error_retry_weekly.py（新規）
3. `backend/app/celery_app.py`（include に1行、beat_schedule に1件）
4. backend/tests/test_api_error_retry_governance.py（新規）

## 触らない範囲

- `backend/app/tasks/tcg_extraction_recovery.py` の retry_transient_api_error_jobs と、その定数（:271-274）と SQL。`backend/tests/test_api_error_auto_retry.py` がそれを完全一致で見ている。
- `backend/app/services/line_analysis_v102_svc.py` のすべて。
- 既存の試験ファイルのすべて。

## 1. 諦めた分の知らせ（tcg_extraction_recovery.py に足す）

定数（retry_transient_api_error_jobs の定数の下に置く）:
- API_ERROR_GIVEN_UP_WINDOW_HOURS = 48
- API_ERROR_GIVEN_UP_REDIS_PREFIX = "api_error_given_up:notified:"
- API_ERROR_GIVEN_UP_REDIS_TTL_SECONDS = 7 * 24 * 60 * 60
- API_ERROR_GIVEN_UP_LIST_LIMIT = 10

関数 find_given_up_api_error_jobs(session) -> list[dict]:
- SQL の条件は retry_transient_api_error_jobs（:297-321）と同じにする。違いは次の点だけ:
  - 「作られてから24時間以内」の代わりに、作られてから48時間以内（:window_hours）
  - 「最新の試行が5分より前」の条件を外す
  - 試行の数の条件を次に置き換える: 試行の数が :max_attempts 以上、または created_at が :lookback_hours 時間より前
- 値は既存の定数をバインドで渡す（max_attempts=API_ERROR_RETRY_MAX_ATTEMPTS、lookback_hours=API_ERROR_RETRY_LOOKBACK_HOURS）。数字の直書きは禁止。
- 返す列: job の id、作られた時刻、最新の試行の validation_result->>'raw' の末尾の HTTP の番号（取れなければ category）、仕入元の名前。
- 仕入元の名前: source_messages から仕入元の名前に辿る既存の結合を、リポジトリの既存コードから探して同じ形で使う。辿れる結合が見つからなければ source_messages の id を代わりに出す。どちらにしたかを報告に書く。
- 並び: created_at の古い順。上限なし（件数を数えるため）。

関数 notify_given_up_api_error_jobs(session) -> int:
- 送った件数を返す。
- 送り先の URL は `backend/app/services/discord_notifier.py:40` の _get_webhook_url で取る。空なら warning を1行出して 0 を返す。
- Redis は `backend/app/tasks/viewer_share_flag_monitor.py:46` の _get_redis と同じ形で取る（このファイルに同じ関数を作る。import で使い回さない）。None なら 0 を返す。
- find_given_up_api_error_jobs の結果から、Redis キー（接頭辞＋job id）があるものを除く。残りが0なら 0 を返す。
- 1通だけ送る。送信は `backend/app/services/discord_notifier.py:45` の _post_discord_webhook を asyncio.run で呼ぶ。
- 本文（build_given_up_message(rows) を作る）:
  - 1行目: 「⚠️ 解析を3回送り直しても終わらなかった投稿が N 件あります（ADR-1050）」
  - 続けて先頭 API_ERROR_GIVEN_UP_LIST_LIMIT 件を1行ずつ:「・」＋仕入元の名前＋半角空白＋投稿が作られた時刻（日本時間・YYYY-MM-DD HH:MM）＋「 断られ方 」＋HTTP の番号
  - 残りがあれば「ほか M 件」
  - 最後の行: 「要確認の画面で手でやり直してください。」
- 送れた（True）ときだけ、送った全 job id のキーを TTL 付きで置く。キーを置く処理の失敗は warning にとどめる。
- 関数の全体を try/except Exception で包み、例外は logger.exception にして 0 を返す。

_run_recovery への組み込み:
- with Session() as session: の中、retry_transient_api_error_jobs の呼び出しの後で given_up_notified = notify_given_up_api_error_jobs(session) を呼ぶ。
- result に "given_up_notified": given_up_notified を足す。
- 既存の logger.info の行は変えない。given_up_notified が1以上のときだけ、別に logger.warning を1行出す。

## 2. 月曜の数の知らせ（api_error_retry_weekly.py を新規）

- 型は `backend/app/tasks/bundle_bulk_monitor.py` と同じ。async の _run_report、@shared_task、asyncio.run、最後に engine.dispose。
- タスク名: app.tasks.api_error_retry_weekly.report_api_error_retry_weekly
- 送信は _post_discord_webhook と _get_webhook_url を使う（URL が空なら warning で終わる）。
- 数える SQL（読むだけ。schema は tcg_extraction_recovery の TCG_SCHEMA を import して使う）。直前7日に作られた v102 の job（prompt_version LIKE 接頭辞）のうち:
  - transient_jobs: 試行のどれかが一時的な断られ方で failed（条件は 1. と同じ category と HTTP の番号）
  - recovered_jobs: そのうち ej.status = 'done'
  - given_up_jobs: そのうち 1. の諦めの条件（status='error' かつ error_message='API_ERROR'、かつ試行の数が3以上、または作られてから24時間を過ぎた）
- 定数: WEEKLY_DAYS = 7、ATTENTION_TRANSIENT_JOBS = 20。
- 本文（build_message(counts) を作る）:
  - 1行目: 要調査なら「⚠️ 要調査」、そうでなければ「✅」。続けて「 解析の送り直し 週次（ADR-1050）」
  - 「直前7日に一時的に断られた投稿: N 件」
  - 「・送り直しで解析が終わった: N 件」
  - 「・3回送り直しても終わらなかった: N 件」
  - 要調査の条件: given_up_jobs >= 1、または transient_jobs >= ATTENTION_TRANSIENT_JOBS
- 0件でも必ず送る。

celery_app.py:
- include の `"app.tasks.bundle_bulk_monitor",` の行の後に `"app.tasks.api_error_retry_weekly",  # ADR-1050: 解析の送り直しの週次件数` を足す。
- beat_schedule の report-bundle-bulk-weekly の後に、report-api-error-retry-weekly を足す。予定は crontab(hour=9, minute=10, day_of_week=1)。コメントは「# ADR-1050: 解析の一時的な失敗の送り直しの件数を毎週月曜 09:10 に管理者用 Discord へ」。

## 3. 試験（backend/tests/test_api_error_retry_governance.py を新規）

既存の `backend/tests/test_api_error_auto_retry.py` と同じ作法にする（session は偽物、SQL の文字列と params を検査する）。

- T1: find_given_up_api_error_jobs の SQL に「>= :max_attempts」と「:lookback_hours」の両方があり、params が max_attempts=3・lookback_hours=24・window_hours=48 である。
- T2: SQL が status='error'・error_message='API_ERROR'・HTTP 429/500/502/503/504 の条件を持つ。HTTP 400 は条件に含まれない。最新の試行の5分の条件（:min_age）を持たない。
- T3: Redis の偽物にキーがある job は送らない（送信を呼ばない）。送信が False のときはキーを置かない。True のときは全 id のキーを TTL 7日で置く。
- T4: 送り先の URL が空、Redis が None、find が例外、のどれでも 0 を返し、_run_recovery の result に api_error_retry_count と given_up_notified がある。
- T5: build_message が、given_up 1件で「⚠️ 要調査」になる。transient 20件で「⚠️ 要調査」になる。transient 19件・given_up 0件で「✅」になる。0件の本文も作られる。
- T6: celery_app.conf.beat_schedule["report-api-error-retry-weekly"] の task 名が正しく、schedule が月曜 09:10 である。
- T7: build_given_up_message が、11件のとき先頭10行と「ほか 1 件」を出す。

## 4. 確かめ方

- 手元では新しい試験と、関係する既存の試験だけを流してよい（pytest backend/tests/test_api_error_retry_governance.py backend/tests/test_api_error_auto_retry.py backend/tests/test_celery_beat_registered.py）。全件は CI に任せる。
- ruff は変更したファイルだけ。
- 生出力は作業場所の外の一時フォルダに保存し、パスを報告に書く。
- `git diff origin/main...HEAD --name-only` が「触るファイル」の4つと docs/・.claude-pipeline/ の文書だけであること。

## 想定される分岐と止まる条件

- 仕入元の名前に辿れない → source_messages の id を出して進める。報告に書く。
- 既存の試験が落ちる → 直さずに止まり、BLOCKED: で生出力のパスを返す。
- カードに無いファイルを触る必要が出た → 止まり、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION で Opus に戻す。
- 終わったら commit（shingo-cc 名義、最後の行は Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>）→ git log -1 で確かめる → git push origin release/api-error-retry-governance → git log origin/release/api-error-retry-governance -1 で確かめる。PR は作らない（手元の Opus が作る）。

END OF CARD
