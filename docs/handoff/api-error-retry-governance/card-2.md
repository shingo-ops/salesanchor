# 実装カード 2 — api-error-retry-governance（月曜の数の知らせの直し）

親: docs/handoff/api-error-retry-governance/design.md
この文書は何か: PR #4869 のマージ前審査（REQUEST_CHANGES on d875021f475c66ab8c59ce393d56d5c8bf9005a8）で見つかった不具合を直すカード。

状態: カード発行（Opus、2026-10-30）。根拠: design.md 第1版 B・受入条件 T5、審査の生出力 /tmp/CC報告ファイル/api-error-retry-governance-review/sqlcheck.txt（手元）。
担当: Sonnet（クラウド）。触ってよいのは下の「触るファイル」だけ。本番 DB・VPS・GitHub secret には触らない。DB の変更なし。.github/workflows・migrations・scripts は触らない。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、作業場所のブランチが release/api-error-retry-governance で、HEAD に docs/handoff/api-error-retry-governance/card-2.md があることを報告の1行目に書く。

## 何が起きているか（審査の事実）

- `backend/app/tasks/api_error_retry_weekly.py` の週次の SQL は、`(:lookback_hours || ' hours')::interval` と `(:days || ' days')::interval` に int を渡している。
- 週次は AsyncSessionLocal（asyncpg）で動く。asyncpg はこの形で int を受け付けず、`DataError: invalid input for query argument $2: 24 (expected str, got int)` で毎回落ちる。psycopg2 では通る。
- 週次の「諦めた」の数が、設計 B の「A の条件に当たる」より広い。置き換え済みの投稿や、最後の試行が一時的でない断られ方（HTTP 400 など）の job も数えている。

## 実装前点検（結果を報告に書く。外れたら実装せず BLOCKED で停止する）
- P1 `backend/app/tasks/api_error_retry_weekly.py` の _COUNT_SQL に `|| ' hours')::interval` と `|| ' days')::interval` があること。
- P2 `backend/app/tasks/tcg_extraction_recovery.py` の find_given_up_api_error_jobs の WHERE に、sm.is_active = TRUE・sm.superseded_by IS NULL・latest_attempt.phase = 'failed' と一時的な断られ方の条件があること。

## 触るファイル

1. `backend/app/tasks/api_error_retry_weekly.py`
2. `backend/tests/test_api_error_retry_governance.py`（足すだけ。既存の試験の中身は変えない）

## 触らない範囲

- `backend/app/tasks/tcg_extraction_recovery.py` のすべて（同期の psycopg2 で動き、審査で正しく動くと確かめ済み）。
- `backend/app/celery_app.py`、`backend/app/services/` のすべて、ほかの試験ファイル。

## 1. 直す中身（api_error_retry_weekly.py）

- 時間の幅は文字のつなぎをやめ、`make_interval(days => :days)` と `make_interval(hours => :lookback_hours)` にする。params の値は int のまま。
- 週次の「諦めた」（given_up_jobs）の FILTER を、find_given_up_api_error_jobs と同じ意味にする。次をすべて満たす job だけを数える:
  - ej.status = 'error' かつ ej.error_message = 'API_ERROR'
  - 投稿が有効で置き換えられていない（source_messages の is_active = TRUE かつ superseded_by IS NULL）
  - 最新の試行（started_at DESC, id DESC の1件）が phase = 'failed' で、一時的な断られ方（category が gemini_rate_limit・gemini_timeout、または gemini_http_error で raw の末尾が HTTP 429・500・502・503・504）
  - 試行の数が :max_attempts 以上、または作られてから :lookback_hours 時間を過ぎた
- 書き方は、最新の試行を LEFT JOIN LATERAL で1件取り、source_messages を LEFT JOIN する形にする。transient_jobs と recovered_jobs の数え方（直前7日・v102・試行のどれかが一時的な断られ方）は変えない。
- 一時的な断られ方の条件は、文字の重複を減らすため、ファイルの中で1つの関数か文字列にまとめて、試行どれか（EXISTS）と最新の試行の両方で使ってよい。

## 2. 試験を足す（test_api_error_retry_governance.py）

- T8: `_COUNT_SQL` の文字に `|| '` が無く、`make_interval(days => :days)` と `make_interval(hours => :lookback_hours)` がある。
- T9: `_params()` が prefix・days=7・max_attempts=3・lookback_hours=24 を返す。
- T10: `_COUNT_SQL` を sqlalchemy の postgresql の asyncpg 方言（`sqlalchemy.dialects.postgresql.asyncpg.dialect()`）で compile でき、given_up の FILTER に superseded_by IS NULL と latest の phase = 'failed' の条件がある。
- T11: `_run_report` を、AsyncSessionLocal の偽物（execute が counts を返す）・_get_webhook_url・_post_discord_webhook の偽物で流し、送信が1回呼ばれ、本文が build_message の結果と一致する。

## 3. 確かめ方

- 手元で使い捨ての PostgreSQL 16 と asyncpg が用意できるなら、_COUNT_SQL と _params() を asyncpg で実際に流し、例外なく1行返ることを確かめる。用意できなければ「未確認」と報告に書く（それで止まらない）。
- pytest は backend/tests/test_api_error_retry_governance.py backend/tests/test_api_error_auto_retry.py backend/tests/test_celery_beat_registered.py を --no-cov で流す。
- ruff は変更したファイルだけ。
- 生出力は /tmp/CC報告ファイル/api-error-retry-governance-impl2/ に保存し、パスと exit code と passed/failed の数を報告に書く。
- `git diff origin/main...HEAD --name-only` が card-1 の4ファイルと docs/・.claude-pipeline/ の文書だけであること。

## 想定される分岐と止まる条件

- make_interval の名前付き引数が使えない → `(:days * interval '1 day')` の形にして進め、報告に書く。
- 既存の試験が落ちる → 直さずに止まり、BLOCKED: で生出力のパスを返す。
- カードに無いファイルを触る必要が出た → 止まり、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION で Opus に戻す。
- 終わったら commit（shingo-cc 名義、最後の行は Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>）→ git log -1 で確かめる → git push origin release/api-error-retry-governance → git log origin/release/api-error-retry-governance -1 で確かめる。PR は作らない。

END OF CARD
