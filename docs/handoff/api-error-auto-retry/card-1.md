# card-1: 一時的に断られた解析の自動送り直し（すぐ2回＋数分後2回）

状態: カード発行（Opus、2026-10-29）。根拠: design.md 第2版（PO 2026-10-29「1」）、recon.md。
担当: Sonnet（クラウド）。触ってよいのは下の「触るファイル」だけ。本番 DB・VPS・GitHub secret には触らない。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 新規ファイルは丸ごと書く／commit と push の後は git log で確かめる／PR はクラウドで作らない）。

## 受領確認
着手前に、この作業場所のブランチが release/api-error-auto-retry-design で、HEAD に docs/handoff/api-error-auto-retry/card-1.md があることを報告の1行目に書く。

## 0. 実装前点検（結果を報告に書く。外れたら実装せず BLOCKED で停止する）
- P1 `backend/app/services/line_analysis_v102_svc.py` の _call_gemini が、before_send → session.commit → call_gemini_raw_copy_v8 → except SoftTimeLimitExceeded（raise）→ except Exception（record_error_detail → RecordError("API_ERROR")）の順であること（main 基準で :455〜:485 付近）。
- P2 `backend/app/services/gemini_extraction_svc.py` に _HTTP_STATUS_RE があり、line_analysis_v102_svc.py から import できること（循環 import にならないこと）。なるなら同じ正規表現を写し、出典の行番号をコメントに書く。
- P3 `backend/app/tasks/tcg_extraction_recovery.py` の _run_recovery が、running 回収 → 停滞 pending → retry_analysis_failed_jobs の順で、停滞 pending があるときだけ _reenqueue_stale_pending_jobs を呼ぶこと。
- P4 public.extraction_attempts に extraction_job_id・started_at・finished_at・phase・validation_result の列があること（migrations を読む）。phase の失敗の値が 'failed' でなければ、実物の値を使い報告に書く。

## 1. 触るファイル
1. backend/app/services/line_analysis_v102_svc.py
2. backend/app/tasks/tcg_extraction_recovery.py
3. backend/tests/test_api_error_auto_retry.py（新規）
触らない: migrations、gemini_extraction_svc.py（import するだけ）、call_gemini_raw_copy_v8 の中身、tcg_diagnostics_svc.py、frontend、v6 経路、celery_app.py、docs（このカード・design.md・recon.md の中身も変えない）。

## 2. 変更の中身
design.md の「技術 How」A と B のとおり。要点:

### 2-1. line_analysis_v102_svc.py（すぐの送り直し）
- 定数: _TRANSIENT_HTTP_CODES = frozenset({429, 500, 502, 503, 504})、_IMMEDIATE_RETRY_DELAYS = (2, 8)、_IMMEDIATE_RETRY_BUDGET_SECONDS = 90。
- 関数 _is_transient_http(exc) -> bool: str(exc) に _HTTP_STATUS_RE を当て、取れた番号のどれかが _TRANSIENT_HTTP_CODES にあれば True。番号が無ければ False。時間切れは False。
- call_gemini_raw_copy_v8 の呼び出しだけを繰り返しで囲む。開始時刻は time.monotonic() で取る。例外のとき: SoftTimeLimitExceeded はそのまま raise。_is_transient_http が True、まだ使っていない待ちがある、経過が90秒未満、の3つが揃えば logger.warning("[line_analysis] 一時的な失敗のため送り直し: job=%s 回目=%d HTTP=%s", ...) → time.sleep(待ち) → もう一度呼ぶ。揃わなければ今のコードの except Exception の処理をそのまま行う。
- 送り直しの後に成功したら logger.info("[line_analysis] 送り直しで成功: job=%s 回目=%d", ...)。
- before_send と session.commit は繰り返しの外の今の位置のまま（1回だけ）。

### 2-2. tcg_extraction_recovery.py（数分後の送り直し）
- 定数（ANALYSIS_RETRY_MIN_AGE_MINUTES の並び）: API_ERROR_RETRY_MIN_AGE_MINUTES = 5、API_ERROR_RETRY_MAX_ATTEMPTS = 3、API_ERROR_RETRY_LOOKBACK_HOURS = 24、MAX_API_ERROR_RETRY_PER_RUN = 20。
- 関数 retry_transient_api_error_jobs(session) -> list[str]: design.md B-2 の条件の SELECT を1文で書く（定数は引数で渡す。文字列に埋め込まない）。最新の試行は LATERAL か DISTINCT ON で1件。一時的な番号の判定は validation_result->>'raw' の末尾が「(HTTP 429)」「(HTTP 500)」「(HTTP 502)」「(HTTP 503)」「(HTTP 504)」のどれか、または category が gemini_rate_limit・gemini_timeout。
- 1件ずつ: その job の extraction_items を消す文 → status を pending に戻す UPDATE（WHERE id=:id AND status='error' AND error_message='API_ERROR'）。UPDATE が1行なら commit して id を集める。0行なら rollback。1件の失敗で全体を止めない（logger.exception して次へ）。消す文と戻す文は retry_analysis_failed_jobs と tcg_diagnostics_svc.py:218 の書き方を手本にする。
- _run_recovery: retry_analysis_failed_jobs の後に呼ぶ。停滞 pending の id と合わせて重複を除き（順は保つ）、空でなければ _reenqueue_stale_pending_jobs を1回呼ぶ。戻り値に api_error_retry_count を足す。既存のキーと値は変えない。
- ログ: logger.info("[tcg_extraction_recovery] 一時的な失敗の送り直し: 対象%d件 投入%d件", ...)。

### 2-3. test_api_error_auto_retry.py
design.md の受け入れ基準 T1〜T9 を1つずつ試験にする。mock の作りは backend/tests/test_analysis_failed_record.py と同じ。time.sleep と time.monotonic は mock して、実際には待たない。

## 3. 確かめてから報告すること（生出力は /tmp/CC報告ファイル/api-error-auto-retry-impl/ に保存してパスを書く）
- 新しい試験と backend/tests/test_analysis_failed_record.py が全部通る。
- ruff（backend の設定どおり）が通る。
- `git diff origin/main...HEAD --name-only` が §1 の3ファイルと docs/handoff/api-error-auto-retry/ だけ。
- commit（shingo-cc 名義、最後の行は Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>）→ git log -1 で確かめる → git push origin release/api-error-auto-retry-design → git log origin/release/api-error-auto-retry-design -1 で確かめる。
- PR は作らない（手元の Opus が作る）。台帳ファイルは commit しない。

## 4. 想定される分岐
- P1〜P4 のどれかが外れた → 実装せず BLOCKED で停止し、実物の行を報告する。
- import が循環する → P2 のとおり写す。
- 既存試験が今の main で既に落ちている → 直さず、落ちた試験名と生出力のパスを報告する。
- 迷ったら停止して NEEDS_DECISION で Opus に戻す。

END OF CARD
