判定: APPROVE

# マージ前審査 — api-error-auto-retry（reviewer, Opus）

- 審査した HEAD: 47efb69e1bb3781e0b32117d495db34e33da616e（ブランチ release/api-error-auto-retry-design）
- 審査対象: git diff origin/main...HEAD（実装 commit 47efb69e1。docs commit 8c6562aad・45ecece3f・cf67699e1）
- 基準: docs/handoff/api-error-auto-retry/design.md（第2版・PO 承認済み）、card-1.md、recon.md
- 日付: 2026-10-29

## 見た範囲

- 差分の全行: backend/app/services/line_analysis_v102_svc.py、backend/app/tasks/tcg_extraction_recovery.py、backend/tests/test_api_error_auto_retry.py
- 差分の外で読んだ実物: backend/app/tasks/tcg_extraction.py（_run_extraction :333〜:436、extract_source_message_task :816〜:840）、backend/app/services/tcg_extraction_record_svc.py（before_send :69〜:105、record_error_detail :107〜:113、fail :224〜:265）、backend/app/services/gemini_extraction_svc.py（_HTTP_STATUS_RE :185、_safe_error_message、_classify_error :213）、backend/app/services/gemini_raw_copy_v8.py（:182〜:230）、backend/app/services/tcg_distribution_svc.py（安全装置 #8/#8b :895〜:936）、recover_stale_running_jobs・find_stale_pending_job_ids・_reenqueue_stale_pending_jobs・Celery タスク定義（tcg_extraction_recovery.py 全体）

## 実行して確かめたこと（生出力は /tmp/CC報告ファイル/api-error-auto-retry-review/）

| 確認 | 結果 | 生出力 |
|------|------|--------|
| Python 3.12 venv で新規試験＋test_analysis_failed_record.py | 29 passed（rc=1 は部分実行で coverage 60% 未達のためだけ） | pytest.txt |
| 関連する既存試験 test_tcg_extraction_recovery.py・test_line_analysis_v102_svc.py・test_tcg_gemini_extraction.py（--no-cov） | 194 passed | pytest_related.txt |
| ruff 0.9.10（変更3ファイル） | All checks passed | ruff.txt |
| retry_transient_api_error_jobs を使い捨ての PostgreSQL 16（手元・最小の表）で psycopg2 経由で実行 | 12件の場面のうち、拾うべき A(503)・H(429/gemini_rate_limit)・J(試行2回・最新が gemini_timeout) の3件だけ pending に戻り items も消えた。402・置き換え済み・試行3回・失敗2分前・作成30時間前・v6・「(HTTP 503)」が末尾でない・別の error_message・最新の試行が400 の9件は error のまま。2回目の実行は 0件 | sqlcheck.txt（スクリプトは scratchpad の sqlcheck.py） |

SQL について: `(:lookback_hours || ' hours')::interval` は既存の recover_stale_running_jobs と同じ書き方で、PG16 で動いた。text() の中の `LIKE '%(HTTP 503)'` の `%` は psycopg2 方言で正しく逃がされ、意図どおり照合した。UPDATE の rowcount は psycopg2 で 1/0 が正しく返る（上の実行で確認）。

## 1. 設計・カードとの一致

| 項目 | 設計 / カード | 実装 | 判定 |
|------|---------------|------|------|
| すぐの送り直しの回数・待ち | (2, 8) 秒・最大2回 | `backend/app/services/line_analysis_v102_svc.py:464` `_IMMEDIATE_RETRY_DELAYS = (2, 8)`、:505 で `retries_used < len(...)` | 一致 |
| 90秒の打ち切り | 最初の呼び出しからの経過が90秒未満のときだけ | :491 `started = time.monotonic()`（呼び出しの直前）、:506 で例外の時点に判定 | 一致 |
| 対象の番号 | 429・500・502・503・504、時間切れは対象外 | :463 frozenset、:468 `_is_transient_http`（番号なしは False） | 一致 |
| SoftTimeLimitExceeded | そのまま投げる | :501 | 一致 |
| before_send・commit | 繰り返しの外で1回 | :478〜:490 は変更なし、ループは :493 から | 一致 |
| 利用料の記録 | 成功した1回だけ | _record_usage・on_response は run_v102_extraction 側で1回（変更なし）。失敗した呼び出しは結果が無いので記録されない | 一致 |
| 数分後の送り直しの定数 | 5分・3試行・24時間・1回20件 | `backend/app/tasks/tcg_extraction_recovery.py:271`〜:274 | 一致 |
| SELECT の条件 | error・API_ERROR・v102・24時間・is_active・superseded_by IS NULL・最新試行 failed・5分・一時的な番号・試行3未満・古い順 LIMIT 20 | :282〜:333。定数はすべて引数で渡している | 一致 |
| 戻しの手順 | items DELETE → UPDATE（status='error' AND error_message='API_ERROR' の条件付き）→ 1行なら commit、0行なら rollback | :338〜:356 | 一致 |
| _run_recovery | retry_analysis_failed_jobs の後、停滞 pending と重複を除いて1回で投入、api_error_retry_count を足す、既存キーは不変 | :370、:375〜:382、:392 | 一致 |
| 触らない範囲 | migration・gemini_extraction_svc.py・call_gemini_raw_copy_v8・tcg_diagnostics_svc.py・frontend・celery_app.py | 実装 commit の変更は3ファイルだけ（git log --name-only で確認） | 一致 |

## 2. 正しさ

- 重複しないもの: before_send（＝試行の行の追加と job の running 化）と session.commit は1回だけ。待っている間に DB の取引を持たない。record_error_detail は最初の書き手が勝つ作り（tcg_extraction_record_svc.py:112）なので、_run_extraction の except RecordError（tcg_extraction.py:425）が後から書く system 側の分類で、Gemini 側の category・raw が上書きされない。これで数分後の送り直しの SELECT が見る validation_result->>'category'／'raw' が正しく残る。
- prompt_version: run_v102_extraction が _call_gemini の前に recorder.prompt_version を v102 の値にし（line_analysis_v102_svc.py:539〜:540）、fail が jobs.prompt_version をその値で書く（tcg_extraction_record_svc.py:263）。失敗した job も `LIKE 'v102:%'` に当たる。
- pending に戻した後の再解析: _reenqueue_stale_pending_jobs は status='pending' で取り直して source_message_id で extract_source_message_task を積む（tcg_extraction_recovery.py:184〜:204）。_run_extraction はその投稿の pending の job を新しい順に1件取り（tcg_extraction.py:337〜:347）、before_send が `status='pending'` を条件に running にする（tcg_extraction_record_svc.py:79〜:85）。新しい試行は前の試行を親にして足されるので、試行の数え方（3未満）が正しく増える。再び失敗すれば error・API_ERROR に戻り、3試行目の後は拾わない。成功すれば error_message は NULL に戻る（line_analysis_v102_svc.py:581）。
- 二重に拾われないか: 同じ回の中では find_stale_pending_job_ids が retry_transient_api_error_jobs より先に走るので、いま戻した id は停滞 pending 側に入らない（重複除去は念のための形）。投入が遅れて次の回まで pending のまま残り、最新試行の開始から15分を過ぎた場合は停滞 pending として積み直されうるが、before_send の `status='pending'` 条件で片方は CLAIM_CONFLICT か no_pending_job になり、二重解析にはならない。これは既存の停滞 pending の扱いと同じ。recover_stale_running_jobs は running だけが対象で、交わらない。

## 3. 暴走しないか

- 400・402: 数分後の SELECT は「(HTTP 429/500/502/503/504)」で終わる raw か rate_limit・timeout の category だけを拾う。PG 実行で 402 と、最新試行が 400 の job が拾われないことを確認。すぐの送り直しも番号が対象外なら0回（T3 の試験で確認）。
- 置き換え済み: `sm.is_active = TRUE AND sm.superseded_by IS NULL`。PG 実行で拾われないことを確認。
- 上限: 1 job 合計3試行、1回の実行で20件、1試行の中で Google へ最大3回。
- _is_transient_http が無関係な3桁の数を拾う危険: 実物では call_gemini_raw_copy_v8 が SDK の例外を `RuntimeError(f"Gemini v8 API 呼び出し失敗: {_safe_error_message(exc)}")` に包み直して投げる（gemini_raw_copy_v8.py:229）。_safe_error_message は 4xx/5xx の番号が1つでもあれば「理由 (HTTP NNN)」だけを返し、無ければ番号の無い文を返す。そのため _is_transient_http に届く文字列に 4xx/5xx 形の数は多くても1つで、無関係な数を拾う道は実質ない（細部1）。

## 4. 試験（T1〜T9）

| 基準 | 試験 | 中身を検査しているか |
|------|------|----------------------|
| T1 | TestT1ImmediateRetrySucceeds | 戻り値・record_error_detail 未呼び出し・sleep(2) 1回・呼び出し2回を確認。○ |
| T2 | TestT2RetriesExhausted | sleep [2, 8]・呼び出し3回・RecordError・record_error_detail 1回・raw が「(HTTP 503)」で終わることまで確認（数分後の SELECT との受け渡しの形を押さえている）。○ |
| T3 | TestT3NotRetried | 400・402・時間切れ・番号なしで sleep 0回・呼び出し1回。_is_transient_http の単体も。○ |
| T4 | TestT4TimeBudget | monotonic を [0, 91] で与え、送り直さないこと。30秒なら送り直すことも。○ |
| T5 | TestT5SoftTimeLimitAndBeforeSend | 中断がそのまま上がり sleep・record_error_detail なし。送り直し2回でも before_send と commit が各1回。○ |
| T6 | TestT6SelectConditions | SQL 文字列の断片と引数の値を照合（設計どおり mock 型）。SQL が実際に動くかは本審査の PG 実行で補った。○ |
| T7 | TestT7ResetOrder | DELETE が UPDATE より先、UPDATE の WHERE 条件、1行なら id を集めて commit、0行なら rollback で集めない。○ |
| T8 | TestT8DedupAndFailureIsolation | 重複 id は1回・順を保って投入、空なら投入しない、1件の失敗で他が止まらない。△（細部2: 「投入で例外」の側は試験していない） |
| T9 | TestT9RunRecoveryResult＋既存試験 | 新キーと既存7キー。既存の関連試験 194件が通る。○ |

mock で素通りしている試験は見当たらない。_Env は call_gemini_raw_copy_v8・time.sleep・time.monotonic を差し替えるだけで、_call_gemini のループ本体は実物を通っている。

## 指摘（止める必要のあるもの）

なし。

## 細部（止めない。直すなら後の便でよい）

1. 軽・`backend/app/services/line_analysis_v102_svc.py:470`・`_is_transient_http` は findall（どれか1つでも一時的な番号なら True）で、`_safe_error_message`（記録する raw を作る側）は最初の1つだけを見る。今は上の §3 のとおり包み直しで番号が1つに絞られるので差は出ないが、将来 SDK の例外がそのまま届く経路ができると「すぐの送り直しは一時的と判断・記録される raw は永続的な番号」と食い違いうる（その場合も回数上限で止まる）。直し方: `_HTTP_STATUS_RE.search` で最初の番号だけを見て、記録側とそろえる。あわせて試験の `_http()`（`backend/tests/test_api_error_auto_retry.py:62`）に本番の実際の形「Gemini v8 API 呼び出し失敗: サービス利用不可 (HTTP 503)」を1件足すと、受け渡しの形が固定できる。
2. 軽・`backend/tests/test_api_error_auto_retry.py:215`・T8 の後半「投入で例外が出ても定期処理全体は止まらない」は、試験しているのが戻しの途中の例外（1件の失敗で他が止まらない）だけ。実装では `_reenqueue_stale_pending_jobs` の例外は `_run_recovery`（`backend/app/tasks/tcg_extraction_recovery.py:378`）を抜け、Celery タスクの self.retry（:430〜:433）に乗る。これは既存の停滞 pending の投入と同じ振る舞いで、戻した job は commit 済みの pending なので次の回以降に停滞 pending として拾い直される（設計 B-4 の「投入が失われても…拾い直す」に合う）。止めない理由はこれ。直し方: 設計の T8 の文言を「戻しの途中の1件の失敗で他が止まらない」に合わせるか、投入の例外の試験を足す。その回は「一時的な失敗の送り直し」のログ（:379）が出ない点だけ K1 の観測で知っておくこと。
3. 情報・`backend/app/services/tcg_distribution_svc.py:918`・安全装置 #8b は pending の job がある間、配信を止める。戻した job が投入を待つ数十秒は、他の投稿の解析完了で起きた配信が保留になる。戻した job が再び失敗すると、自分では配信を起こさない（成功時だけ起こす）。新しい投稿の job が失敗したときと同じ性質で新しい種類の危険ではないが、設計の「弊害」欄に無いので、K1 の確認のときに配信が保留のまま残っていないかを1回見るとよい。
4. 情報・`.claude-pipeline/active-work.d/release-api-error-auto-retry-design.md` が差分に入っている（実装 commit ではなく docs commit cf67699e1 で入った）。カードの「台帳ファイルは commit しない」は実装担当向けで、実装 commit は守っている。PR に載せてよいものか、PR を作る前に確かめること。
5. 情報・`backend/app/services/gemini_extraction_svc.py:213` の _classify_error は「timeout」「deadline」の語だけで時間切れを見分けるので、「timed out」のような文は gemini_unknown になり、数分後の送り直しに乗らない。既存の分類で、この PR の範囲外（触らない範囲に gemini_extraction_svc.py がある）。G1 を測るときに gemini_unknown の失敗が残っていたら別件で見る。
6. 情報・90秒の判定は例外が返った時点で行うので、1試行の最悪時間は「89秒＋8秒＋3回目の呼び出しの時間」。本番で観測された最長の66秒なら約163秒で処理の上限300秒に収まる。設計の受け入れた範囲。
