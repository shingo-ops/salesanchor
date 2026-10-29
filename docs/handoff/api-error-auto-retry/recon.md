<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — api-error-auto-retry

親: docs/handoff/analysis-failed-record/design.md
素人向け1行: 読み取りを頼む先から「今は混んでいる」と断られた投稿が、送り直されずに残っている理由を調べた記録。

**仕事名**: api-error-auto-retry  
**日付**: 2026-10-29  
**対象ADR**: ADR-154（抽出の試行記録）／ADR-1003（GO委任）  
**担当**: Opus（読み取りは Sonnet に委任。行番号は origin/main d3e34dced 基準）

---

## 本番で観測した事実（読み取り専用の道 ADR-1024・2026-10-29 10:18〜10:30 JST）

- extraction_jobs で status='error'・error_message='API_ERROR' が8件。作成は 2026-10-27 06:44〜11:08 JST。
- 8件とも extraction_attempts は1回だけ。validation_result は raw「サービス利用不可 (HTTP 503)」・category gemini_http_error。モデル gemini-3.1-flash-lite。
- 同じ時間帯の試行は成功と失敗が数秒おきに混在（10:59:16 成功2件 → 10:59:57 失敗 → 11:00:01 成功 …）。
- 8件の投稿は、すべて後から同じ仕入元の新しい投稿に置き換わっている（source_messages.is_active=false・superseded_by あり）。置き換え先の投稿8件はすべて status='done'。
- 置き換えまでの空きは最短1分（達也）、最長約23時間（MASAKI MIYAZAKI 10/27 09:28 → 10/28 08:31）。
- 過去の API_ERROR 試行: 429（頼む回数が多すぎる）6件（10/10・10/11）、402 83件（9/27・10/6・10/27）、400 73件（9/29・9/30）、理由なし40件（9/25〜9/27）。
- 生出力: /tmp/CC報告ファイル/measure_20261029/（api_error_attempts.txt・window_attempts.txt・attempt_errors_by_day.txt・api_error_successors.txt）

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/line_analysis_v102_svc.py:473` | v102 の Gemini 呼び出し _call_gemini。SoftTimeLimitExceeded 以外の例外を捕まえる |
| `backend/app/services/line_analysis_v102_svc.py:485` | 例外時に raise RecordError("API_ERROR")。送り直しはしない |
| `backend/app/services/line_analysis_v102_svc.py:544` | 成功時の UPDATE で error_message = NULL に戻す |
| `backend/app/services/gemini_extraction_svc.py:185` | HTTP 番号を例外の文字列から正規表現で拾う |
| `backend/app/services/gemini_extraction_svc.py:194` | 503 →「サービス利用不可」の対応表 |
| `backend/app/services/gemini_extraction_svc.py:213` | _classify_error。429→gemini_rate_limit、他の4xx/5xx→gemini_http_error、timeout→gemini_timeout |
| `backend/app/services/gemini_extraction_svc.py:248` | _get_genai_client。HttpOptions に retry_options の指定なし（SDK の送り直しは使っていない） |
| `backend/app/services/tcg_extraction_record_svc.py:263` | 失敗時 status='error', error_message=:code, extracted_at=NULL |
| `backend/app/tasks/tcg_extraction.py:423` | RecordError を捕まえて recorder.fail(code) し、dict を返す（例外にしない） |
| `backend/app/tasks/tcg_extraction.py:816` | extract_source_message_task。max_retries=2 だが例外のときだけ。API_ERROR は dict 返しなので乗らない |
| `backend/app/tasks/tcg_extraction_recovery.py:37` | 定数 STALE_PENDING_MINUTES=15・MAX_RECOVER_PER_RUN=50・_COUNTDOWN_STEP=3 |
| `backend/app/tasks/tcg_extraction_recovery.py:105` | find_stale_pending_job_ids。pending のまま15分以上を拾う |
| `backend/app/tasks/tcg_extraction_recovery.py:140` | _reenqueue_stale_pending_jobs(job_ids)。apply_async で投入 |
| `backend/app/tasks/tcg_extraction_recovery.py:212` | ANALYSIS_RETRY_MIN_AGE_MINUTES=5・MAX_ANALYSIS_RETRY_PER_RUN=20 |
| `backend/app/tasks/tcg_extraction_recovery.py:216` | retry_analysis_failed_jobs。対象は status='done' AND error_message='ANALYSIS_FAILED' だけ。API_ERROR は対象外 |
| `backend/app/tasks/tcg_extraction_recovery.py:269` | _run_recovery。呼び順と戻り値 dict |
| `backend/app/celery_app.py:187` | recover-stale-extraction-jobs を 600 秒（10分）ごと |
| `backend/app/services/tcg_diagnostics_svc.py:146` | 手動の retry_extraction（super_admin 画面から）。error→items 削除→pending→投入 |
| `backend/app/services/tcg_diagnostics_svc.py:218` | items DELETE と status='pending' の UPDATE |
| `backend/app/services/tcg_line_import_svc.py:479` | 置き換え時に superseded_by=新id, is_active=FALSE |
| `backend/tests/test_analysis_failed_record.py:64` | 既存テストは session.execute を mock して SQL と引数を検査する作り |
| `migrations/20260921_110000_pipeline_tables_public.sql:157` | public.extraction_attempts に (extraction_job_id, started_at) の index あり |
| `backend/requirements.txt:29` | google-genai>=1.0.0（下限のみ） |

## 既存 ADR 検索

- `git grep -il -e retry -e 再試行 -e やり直し origin/main -- docs/adr/` の10件（ADR-014・040・056・093・1005・1013・1037・110・154・159）に、Gemini の一時的な失敗の送り直しを定めたものは無い。ADR-154 は試行履歴（extraction_attempts）の設計で、本件はその履歴で失敗回数を数える。
- `docs/adr/FEATURE-INDEX.md` の解析・パイプライン欄は ADR-100・ADR-014 のみ。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 503 を返したのが Google 本体か prod2 の中継か | 本番 .env の GEMINI_PROXY_URL と中継ログが必要。保存データには区別の材料なし | 未解消（設計には影響しない。どちらでも一時的な失敗として送り直す） |
| 2 | 本番の google-genai の実バージョン | コンテナで pip show | 未解消（本設計は SDK の送り直しを使わないので影響しない） |
| 3 | 失敗から次の投稿までの間、在庫表にその仕入元がどう出ていたか | 画面か表示用の表を確認 | 未解消（設計の要否には影響しない） |

**未解決ゼロ確認**: 設計の前提に効く未解決は無し（上の3件は設計に影響しない理由を併記）。
