<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — api-error-auto-retry（一時的に断られた解析を自動で送り直す）

親: docs/handoff/analysis-failed-record/design.md
素人向け1行: 読み取りを頼む先から「今は混んでいる」と断られた投稿を、数秒あけてすぐ送り直し、それでも駄目なら数分後にもう一度送り直す。

**対象ADR**: ADR-154（試行記録で失敗回数を数える）／ADR-1003（GO委任）  
**recon**: docs/handoff/api-error-auto-retry/recon.md  
**日付**: 2026-10-29（第2版）  
**担当**: Opus（Planner・Architect 兼務の自己審査。独立の第二者審査ではない）  
**状態**: 設計審査済み（第2版）・PO 承認済み（2026-10-29「1」＝この作り方で作り始める）・実装カード発行済み（card-1.md）

---

## 目的（PO の言葉）

- PO「1」（2026-10-29。選択肢「断られたら数分あけて自動で送り直す仕組みを考える」）。
- PO「1,何分待てば安定して取得できる？なるべく早く取得したいが安定して取得できるようにしてほしい」（2026-10-29。第1版の「この条件と作り方で作ってよい」に対して）。→ 第2版で、数秒後のすぐの送り直しを足した。
- 発端: 10/27 に仕入元8社の投稿が「サービス利用不可 (HTTP 503)」で1回断られ、そのまま読み取られなかった。最長で約23時間、次の投稿まで空いた（recon「本番で観測した事実」）。

## 待ち時間の根拠（PO の「何分待てば安定するか」への答え）

- Google 公式の案内（ai.google.dev/gemini-api/docs/troubleshooting、2026-10-29 取得）: 429・503 は「送り直すべき失敗」。1秒待って送り直し、だめなら 2秒・4秒・8秒と間を倍にする。公式 SDK は最大4回・最初約1秒・最大60秒。
- 本番の記録（10/27、recon）: 断られた2〜4秒後に別の投稿が成功している（10:59:57 失敗 → 11:00:01 成功、11:00:25 失敗 → 11:00:27 成功）。止まり続けたのではなく、ときどき断られていた。
- ただし 06:44 の失敗は、断られる返事が来るまでに66秒かかった（試行の開始 06:44:19・終了 06:45:25）。すぐの送り直しを何回も重ねると、1件の処理の時間上限（300秒）を超えうる。
- 結論: すぐの送り直しは「2秒後」「8秒後」の2回まで。最初の呼び出しから90秒を過ぎていたら、すぐの送り直しはせず、数分後の送り直しに回す。数分後の送り直しは、失敗から5〜15分後と、そのさらに10分後。

## 成功条件（KGI・○×で判定）

| # | 条件 | 判定のしかた |
|---|------|-------------|
| G1 | 一時的な断られ方（429・500・502・503・504・時間切れ）で失敗した投稿のうち、置き換わっていないものは、失敗から30分以内に読み取り直されて「完了」になっている | 本番を読むだけで数える: 「一時的な断られ方で失敗」かつ「置き換わっていない」かつ「失敗から40分以上たった」投稿が 0件なら○ |
| G2 | 待っても直らない断られ方（400・402 など）と、後から置き換わった古い投稿は、数分後の送り直しをしない | 同じ読み取りで、それらの投稿に2回目の試行が 0件なら○ |
| G3 | 1つの投稿の試行は合計3回まで（最初の1回＋数分後の送り直し2回）。1回の試行の中で Google に送るのは最大3回（最初＋すぐの送り直し2回） | 同じ読み取りで試行が4回以上の投稿が 0件、かつログで1回の試行の中のすぐの送り直しが3回以上の例が 0件なら○ |
| G4 | すぐの送り直しで助かった投稿が、数分後の送り直しに回らずに済んでいる | ログの「すぐ送り直して成功」の件数 ÷ 一時的な断られ方の件数。目標 80%以上（基準の記録は10/27の8件だけなので、最初の1か月で見直す） |

## 外部・過去事例の参照と我々への応用

- 事例1: Google 公式の案内（ai.google.dev/gemini-api/docs/troubleshooting、2026-10-29 取得）と公式 SDK google-genai の HttpRetryOptions（googleapis/python-genai の google/genai/types.py、2026-10-29 取得。Context7 は月間上限で使えず公式を直接確認）。送り直す対象は 408・429・5xx、1秒から倍々、最大60秒。→ 我々への応用: 送り直す対象を同じ考え方（429・5xx・時間切れ）にそろえる。400・402 は送り直さない。すぐの送り直しは 2秒・8秒。
- 事例2: 社内の前例 docs/handoff/analysis-failed-record/design.md（2026-10-17。結果が読めなかった失敗を、5分待って1回だけ送り直す）。本番反映後に暴走は起きていない（REPORT 10/20〜10/29 測定）。→ 我々への応用: 数分後の送り直しは、同じ定期処理・同じ「5分待つ」「1回20件まで」「書き換えてから投入して二重を防ぐ」を使う。
- 数値の効果を示す外部事例は見つけていない。効果は G1〜G4 を本番で測って確かめる。

## 変更前 → 変更後

- 変更前: 一時的な断られ方でも、1回で status='error'・error_message='API_ERROR' になって残る（`backend/app/services/line_analysis_v102_svc.py:485`）。自動の送り直しは結果が読めなかった失敗だけ（`backend/app/tasks/tcg_extraction_recovery.py:216`）。
- 変更後:
  1. 断られたらその場で 2秒待って送り直し、だめなら 8秒待ってもう1回（v102 の呼び出し部分）。
  2. それでも駄目で error になったものは、10分ごとの定期処理（`backend/app/celery_app.py:187`）が、失敗から5分以上たったものを pending に戻して投入する。合計3試行まで。

## 技術 How

変更するのは2ファイルと、新しいテスト1ファイル。

### A. すぐの送り直し（`backend/app/services/line_analysis_v102_svc.py:455` の _call_gemini）

1. 定数を足す: _TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}、_IMMEDIATE_RETRY_DELAYS = (2, 8)（秒）、_IMMEDIATE_RETRY_BUDGET_SECONDS = 90。
2. 小さな関数 _is_transient_http(exc) -> bool を足す: `backend/app/services/gemini_extraction_svc.py:185` の _HTTP_STATUS_RE（import して使う。新しい正規表現は作らない）で例外の文字列から番号を取り、_TRANSIENT_HTTP_CODES に入っていれば True。時間切れは True にしない（時間を食うので、数分後の送り直しに任せる）。
3. `call_gemini_raw_copy_v8(...)` の呼び出しを、最初の1回＋最大2回の繰り返しで囲む。例外が出たとき、SoftTimeLimitExceeded はそのまま投げる（今と同じ）。_is_transient_http(exc) が True で、残りの待ちがあり、最初の呼び出しからの経過が90秒未満なら、logger.warning("[line_analysis] 一時的な失敗のため送り直し: job=%s 回目=%d HTTP=%s", ...) を出して time.sleep(待ち) し、もう一度呼ぶ。それ以外は今と同じ処理（record_error_detail → RecordError("API_ERROR")）に進む。
4. すぐの送り直しで成功したら logger.info("[line_analysis] 送り直しで成功: job=%s 回目=%d", ...) を出す（G4 の数え方）。
5. recorder.before_send は最初の1回だけ（試行の記録は1つのまま）。利用料の記録は成功した応答の1回だけ（`backend/app/services/line_analysis_v102_svc.py:443` の _record_usage は呼び出し元で1回。変えない）。
6. session.commit()（`:470`）は繰り返しの外の今の位置のまま。待っている間に DB の取引を持たない。

### B. 数分後の送り直し（`backend/app/tasks/tcg_extraction_recovery.py`）

1. 定数を足す（`:212` の並び）: API_ERROR_RETRY_MIN_AGE_MINUTES = 5、API_ERROR_RETRY_MAX_ATTEMPTS = 3、API_ERROR_RETRY_LOOKBACK_HOURS = 24（9月の 402 などを掘り起こさない）、MAX_API_ERROR_RETRY_PER_RUN = 20。
2. 関数 retry_transient_api_error_jobs(session) -> list[str] を足す。選ぶ条件（1つの SELECT）:
   - extraction_jobs.status='error' AND error_message='API_ERROR' AND prompt_version LIKE 'v102:%'
   - extraction_jobs.created_at が24時間以内
   - 対応する public.source_messages が is_active=TRUE AND superseded_by IS NULL
   - その job の最新の試行（extraction_attempts を extraction_job_id・started_at DESC で1件）が phase='failed' で、finished_at が5分より前で、validation_result->>'category' が gemini_rate_limit か gemini_timeout、または gemini_http_error かつ validation_result->>'raw' が「(HTTP 429)」「(HTTP 500)」「(HTTP 502)」「(HTTP 503)」「(HTTP 504)」のどれかで終わる
   - その job の試行の数が3未満
   - ORDER BY created_at ASC LIMIT 20
3. 1件ずつ、手動の送り直しと同じ手順（`backend/app/services/tcg_diagnostics_svc.py:218`）を同期 Session で行う: その job の extraction_items を DELETE → UPDATE extraction_jobs SET status='pending' WHERE id=:id AND status='error' AND error_message='API_ERROR'。更新が1行のときだけ commit して id を集める。0行なら rollback して飛ばす（二重投入の防止）。error_message は API_ERROR のまま残り、成功すれば NULL に戻る（`backend/app/services/line_analysis_v102_svc.py:544`）。
4. `_run_recovery`（`backend/app/tasks/tcg_extraction_recovery.py:269`）で retry_analysis_failed_jobs の後に呼ぶ。集めた id は停滞 pending の id と重複を除いて1つのリストにまとめ、既存の `_reenqueue_stale_pending_jobs`（`backend/app/tasks/tcg_extraction_recovery.py:140`）に1回で渡す。投入が失われても、15分後に pending の停滞として既存の処理（`backend/app/tasks/tcg_extraction_recovery.py:105`）が拾い直す。
5. 戻り値の dict に api_error_retry_count を足す。ログは logger.info で「[tcg_extraction_recovery] 一時的な失敗の送り直し: 対象%d件 投入%d件」。

### 触らない

migration・列の追加・Gemini の呼び出しの作り（`backend/app/services/gemini_extraction_svc.py:248`）・`call_gemini_raw_copy_v8` の中身・手動の送り直し・画面・v6 経路・翻訳など v102 以外の Gemini 呼び出し。

### 選ばなかった案

- SDK の HttpRetryOptions を使う（`backend/app/services/gemini_extraction_svc.py:248` に1行）: 翻訳など全部の Gemini 呼び出しに効いてしまい、影響が広い。本番の SDK のバージョンがまだ分からない（recon 不明点2）。既定5回・最大60秒待ちで、処理の時間上限（300秒）を食う。→ 採らない。v102 の呼び出し1か所だけに、回数と時間を絞って入れる。
- 数分後の送り直しだけにする（第1版）: 最短でも5分待つ。本番では2〜4秒後に成功しているので、遅すぎる。→ 第2版ですぐの送り直しを足した。
- すぐの送り直しを4回以上: 06:44 のように断られるまで66秒かかる場合、時間上限に近づく。→ 2回・90秒までにした。

## KPI

- KPI1（G1）: 一時的な失敗で、置き換わっておらず、40分以上たって pending/done になっていない投稿 = 0件
- KPI2（G2）: 送り直してはいけない投稿の2回目の試行 = 0件
- KPI3（G3）: 試行4回以上の投稿 = 0件、1回の試行の中のすぐの送り直し3回以上 = 0件
- KPI4（G4）: すぐの送り直しで成功した割合 80%以上
- 基準値（2026-10-29）: 一時的な失敗で送り直されなかった投稿 8件（すべて10/27）。すぐの送り直しは0回（仕組みが無い）。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| T1 503 で1回失敗→2回目で成功すると、結果が返り、record_error_detail は呼ばれず、time.sleep(2) が1回呼ばれる | pytest（新規テスト test_api_error_auto_retry.py。call_gemini_raw_copy_v8 と time.sleep を mock） |
| T2 503 が3回続くと、sleep(2)・sleep(8) の後 RecordError("API_ERROR") になり、record_error_detail が1回呼ばれる | pytest（同ファイル） |
| T3 400・402・時間切れ・番号なしの例外は、すぐの送り直しをせず1回で RecordError("API_ERROR") になる | pytest（同ファイル） |
| T4 最初の呼び出しから90秒を過ぎていたら、503 でもすぐの送り直しをしない | pytest（同ファイル。時刻の関数を mock） |
| T5 SoftTimeLimitExceeded はそのまま投げる。recorder.before_send は1回だけ呼ばれる | pytest（同ファイル） |
| T6 数分後の送り直しの SELECT に status='error'・API_ERROR・v102・24時間・is_active・superseded_by IS NULL・5分・試行3未満・一時的な番号の条件と LIMIT 20 が入っている | pytest（同ファイル。mock の作りは `backend/tests/test_analysis_failed_record.py:64` と同じ） |
| T7 更新が1行のときだけ投入対象に入り、items の DELETE が UPDATE より先。0行なら投入しない | pytest（同ファイル） |
| T8 停滞 pending と重なった id は1回だけ投入される。投入で例外が出ても定期処理全体は止まらない | pytest（同ファイル） |
| T9 _run_recovery の戻り値に api_error_retry_count があり、既存のキーは変わらない。既存テストがそのまま通る | pytest（同ファイル）＋既存 `backend/tests/test_analysis_failed_record.py` |
| K1 本番反映後、定期処理のログに「一時的な失敗の送り直し」が10分ごとに出る | 本番ログ（反映後30分） |
| K2〜K5 KPI1〜4 | 読み取り専用の道（ADR-1024）とログで集計。事象が起きるまでは「未観測」 |

## 弊害・トレードオフ

- 料金が増える → 断られた回は応答が無いので利用料の記録に載らない（`backend/app/services/tcg_extraction_record_svc.py:263` の失敗側）。成功した1回分だけ増える。
- すぐの送り直しの間、解析の作業員が最大10秒止まる → 2秒＋8秒で上限10秒。90秒を過ぎたらしない。
- 混んでいる最中に送り直しが重なる → すぐの送り直しは1件につき2回まで。数分後の送り直しは5分待ち・10分ごと・1回20件・3秒ずつずらす（既存 _COUNTDOWN_STEP）。
- 時間切れは重い投稿で毎回起きうる → すぐの送り直しはしない。数分後の送り直しも合計3回で止まる。
- 「(HTTP NNN)」は文字列から拾っている（`backend/app/services/gemini_extraction_svc.py:185`）ので、番号を取り違える可能性がある → 取り違えても回数の上限で止まる。
- 戻した job が pending の間は、配信の安全装置 #8b が配信を止める（`backend/app/services/tcg_distribution_svc.py:918`）。戻した job がまた失敗しても自分では配信を起こさない → 新しい投稿が失敗したときと同じ性質で、次の投稿・定期配信で解消する（マージ前審査 review-opus.md 細部3 で追記）。
- 戻し方: この PR を revert。DB の形は変えないので、戻しても残るものは無い。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | PO の承認（方向は 2026-10-29「1」、第2版も 2026-10-29「1」で済） | PO（済） |
| 2 | 実装カードを作り、カードの点検 | Opus |
| 3 | 上の技術 How どおり実装＋テスト | Sonnet |
| 4 | マージ前の審査（reviewer, model opus） | Opus |
| 5 | マージ・本番反映・K1 を確認 | Opus（GO 委任の範囲） |
| 6 | 次に一時的な失敗が起きたとき K2〜K5 を測る | Opus |

## 継続

- 完了後の監視: 週1回、読み取り専用の道で KPI1〜3 を数え、ログで KPI4 を数える。
- 次フェーズへの引き継ぎ: 503 の出どころ（Google か中継か）は未確認のまま残る。数分後の送り直しが3回とも失敗する事象が週に1件でも出たら、出どころの調査を別件で起こす。

## 維持の仕組み

- 守り手: 人手で守る（実装 PR で新規テスト test_api_error_auto_retry.py を守り手に差し替える）
- 対象: `backend/app/services/line_analysis_v102_svc.py` のすぐの送り直しの回数・待ち時間と、`backend/app/tasks/tcg_extraction_recovery.py` の数分後の送り直しの条件・上限
- 関所なしの場合: 回数・待ち時間・条件を変える PR は、この design.md の G1〜G4 と「待ち時間の根拠」を見直してから出す。

## 設計審査（Architect・自己審査）

- 判定: APPROVE（設計合格。第2版で再審査）
- 根拠: 変更は2ファイル＋テスト。数分後の送り直しは、同じファイルの前例（retry_analysis_failed_jobs）と同じ型。DB の形を変えない。すぐの送り直しは v102 の呼び出し1か所に限り、回数2回・待ち合計10秒・90秒で打ち切りの3つで時間上限を守る。置き換え済み・永続的な失敗・回数上限の3つの暴走止めがある。成功時に error_message が NULL に戻ることを実物で確認（`backend/app/services/line_analysis_v102_svc.py:544`）。
- 実物確認済み（Opus・2026-10-29）: `_reenqueue_stale_pending_jobs` は job id のリストを受け、status='pending' で再取得してから source_message_id で投入する（`backend/app/tasks/tcg_extraction_recovery.py:181`〜`:205`）。`_call_gemini` は before_send → commit → 呼び出し → except の順（`backend/app/services/line_analysis_v102_svc.py:455`〜`:485`）。
- 未解決: なし（recon の不明点3件は設計に影響しない理由を記載）。
