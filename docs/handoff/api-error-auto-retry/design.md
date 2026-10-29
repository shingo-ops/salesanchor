<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — api-error-auto-retry（一時的に断られた解析を自動で送り直す）

親: docs/handoff/analysis-failed-record/design.md
素人向け1行: 読み取りを頼む先から「今は混んでいる」と断られた投稿を、数分あけて自動で送り直す。

**対象ADR**: ADR-154（試行記録で失敗回数を数える）／ADR-1003（GO委任）  
**recon**: docs/handoff/api-error-auto-retry/recon.md  
**日付**: 2026-10-29  
**担当**: Opus（Planner・Architect 兼務の自己審査。独立の第二者審査ではない）  
**状態**: 設計案（PO の成功条件の承認待ち・実装未着手）

---

## 目的（PO の言葉）

PO「1」（2026-10-29。選択肢「断られたら数分あけて自動で送り直す仕組みを考える」）。
10/27 に仕入元8社の投稿が「サービス利用不可 (HTTP 503)」で1回断られ、そのまま読み取られなかった。最長で約23時間、次の投稿まで空いた（recon「本番で観測した事実」）。

## 成功条件（KGI・○×で判定）

| # | 条件 | 判定のしかた |
|---|------|-------------|
| G1 | 一時的な断られ方（429・500・502・503・504・時間切れ）で失敗した投稿のうち、置き換わっていないものは、失敗から30分以内に読み取り直されて「完了」になっている | 本番を読むだけで数える: 「一時的な断られ方で失敗」かつ「置き換わっていない」かつ「失敗から40分以上たった」投稿が 0件なら○ |
| G2 | 待っても直らない断られ方（400・402 など）と、後から置き換わった古い投稿は、送り直さない | 同じ読み取りで、それらの投稿に2回目の試行が 0件なら○ |
| G3 | 1つの投稿の試行は合計3回まで（最初の1回＋自動の送り直し2回） | 同じ読み取りで、試行が4回以上の投稿が 0件なら○ |

## 外部・過去事例の参照と我々への応用

- 事例1: Google 公式 SDK google-genai の HttpRetryOptions（googleapis/python-genai の google/genai/types.py、2026-10-29 取得。Context7 は月間上限で使えず公式リポジトリを直接確認）。既定の送り直し対象は 408・429・5xx、既定5回、待ち1秒から倍々で最大60秒。→ 我々への応用: 送り直す対象を同じ考え方（429・5xx・時間切れ）にそろえる。400・402 は送り直さない。
- 事例2: 社内の前例 docs/handoff/analysis-failed-record/design.md（2026-10-17。結果が読めなかった失敗を、5分待って1回だけ送り直す）。本番反映後に失敗0件のまま、送り直しの暴走も起きていない（REPORT 10/20〜10/29 測定）。→ 我々への応用: 同じ定期処理・同じ「5分待つ」「1回20件まで」「書き換えてから投入して二重を防ぐ」を使う。
- 数値の効果を示す外部事例は見つけていない。効果は G1〜G3 を本番で測って確かめる。

## 変更前 → 変更後

- 変更前: 一時的な断られ方でも status='error'・error_message='API_ERROR' のまま残る。自動の送り直しは結果が読めなかった失敗だけ（`backend/app/tasks/tcg_extraction_recovery.py:216`）。手で送り直す画面はあるが、誰も気づかない。
- 変更後: 10分ごとの定期処理（`backend/app/celery_app.py:187`）の中で、条件に合う失敗を pending に戻して投入する。失敗から5〜15分後に1回目、さらに10分後に2回目。

## 技術 How

変更するのは `backend/app/tasks/tcg_extraction_recovery.py` 1ファイルと、新しいテスト1ファイルだけ。

1. 定数を足す（`backend/app/tasks/tcg_extraction_recovery.py:212` の並び）:
   - API_ERROR_RETRY_MIN_AGE_MINUTES = 5（失敗してから待つ時間）
   - API_ERROR_RETRY_MAX_ATTEMPTS = 3（試行の合計の上限）
   - API_ERROR_RETRY_LOOKBACK_HOURS = 24（これより古い失敗は拾わない。9月の 402 などを掘り起こさない）
   - MAX_API_ERROR_RETRY_PER_RUN = 20
   - 一時的とみなす HTTP 番号: 429・500・502・503・504。category が gemini_rate_limit・gemini_timeout のものも一時的とみなす。
2. 関数 retry_transient_api_error_jobs(session) -> list[str] を足す。選ぶ条件（1つの SELECT）:
   - extraction_jobs.status='error' AND error_message='API_ERROR' AND prompt_version LIKE 'v102:%'
   - extraction_jobs.created_at が24時間以内
   - 対応する public.source_messages が is_active=TRUE AND superseded_by IS NULL
   - その job の最新の試行（extraction_attempts を extraction_job_id・started_at DESC で1件）が phase='failed' で、finished_at が5分より前、validation_result->>'category' が gemini_rate_limit・gemini_timeout、または gemini_http_error かつ validation_result->>'raw' が「(HTTP 429)」「(HTTP 500)」「(HTTP 502)」「(HTTP 503)」「(HTTP 504)」のどれかで終わる
   - その job の試行の数が3未満
   - ORDER BY created_at ASC LIMIT 20
3. 1件ずつ、手動の送り直しと同じ手順（`backend/app/services/tcg_diagnostics_svc.py:218`）を同期 Session で行う: その job の extraction_items を DELETE → UPDATE extraction_jobs SET status='pending' WHERE id=:id AND status='error' AND error_message='API_ERROR'。更新が1行のときだけ commit して id を集める。0行なら rollback して飛ばす（二重投入の防止）。error_message は API_ERROR のまま残る。成功すれば NULL に戻る（`backend/app/services/line_analysis_v102_svc.py:544`）。
4. 集めた id は、既存の `_reenqueue_stale_pending_jobs`（`backend/app/tasks/tcg_extraction_recovery.py:140`）にそのまま渡して投入する。投入が失われても、15分後に pending の停滞として既存の処理（`backend/app/tasks/tcg_extraction_recovery.py:105`）が拾い直す。
5. `_run_recovery`（`backend/app/tasks/tcg_extraction_recovery.py:269`）で retry_analysis_failed_jobs の後に呼ぶ。戻り値の dict に api_error_retry_count を足す。ログは logger.info で「[tcg_extraction_recovery] 一時的な失敗の送り直し: 対象%d件 投入%d件」。
6. 触らない: migration・列の追加・Gemini の呼び出し部分（`backend/app/services/gemini_extraction_svc.py:248`）・手動の送り直し・画面・v6 経路。

### 選ばなかった案

- SDK の HttpRetryOptions を使う（`backend/app/services/gemini_extraction_svc.py:248` に1行）: 翻訳など全部の Gemini 呼び出しに効いてしまい、影響が広い。本番の SDK のバージョンがまだ分からない（recon 不明点2）。1件の処理の中で最大数分待つので、処理の時間上限（300秒）を食う。→ 採らない。
- 失敗のたびにすぐ送り直す: 混んでいる最中に重ねて送ることになる。→ 5分待つ。

## KPI

- KPI1（G1）: 一時的な失敗で、置き換わっておらず、40分以上たって pending/done になっていない投稿 = 0件
- KPI2（G2）: 送り直してはいけない投稿の2回目の試行 = 0件
- KPI3（G3）: 試行4回以上の投稿 = 0件
- 基準値（2026-10-29）: 一時的な失敗で送り直されなかった投稿 8件（すべて10/27）。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| T1 SELECT に status='error'・API_ERROR・v102・24時間・is_active・superseded_by IS NULL・5分・試行3未満・一時的な番号の条件と LIMIT 20 が入っている | pytest（新規テスト test_api_error_auto_retry.py の SELECT 条件の検査。mock の作りは `backend/tests/test_analysis_failed_record.py:64` と同じ） |
| T2 更新が1行のときだけ投入対象に入り、items の DELETE が UPDATE より先 | pytest（同ファイル。session.execute の呼び順と引数を検査） |
| T3 更新が0行なら投入しない | pytest（同ファイル） |
| T4 投入で例外が出ても定期処理全体は止まらない | pytest（同ファイル） |
| T5 _run_recovery の戻り値に api_error_retry_count があり、既存のキーは変わらない | pytest（同ファイル）＋既存 `backend/tests/test_analysis_failed_record.py` がそのまま通る |
| K1 本番反映後、定期処理のログに「一時的な失敗の送り直し」が10分ごとに出る | 本番ログ（反映後30分） |
| K2〜K4 KPI1〜3 が 0件 | 読み取り専用の道（ADR-1024）で集計。事象が起きるまでは「未観測」 |

## 弊害・トレードオフ

- 料金が増える → 断られた試行は応答が無いので利用料の記録に載らない（recon・`backend/app/services/tcg_extraction_record_svc.py:263` の失敗側）。成功した送り直しの1回分だけ増える。上限は1件あたり2回・1回20件。
- 混んでいる最中に送り直しが重なる → 5分待ち・10分ごと・1回20件・3秒ずつずらす（既存 _COUNTDOWN_STEP）で薄める。
- 時間切れ（gemini_timeout）は重い投稿で毎回起きうる → 合計3回で止まる。G3 で見張る。
- 「(HTTP NNN)」は文字列から拾っている（`backend/app/services/gemini_extraction_svc.py:185`）ので、番号を取り違える可能性がある → 末尾一致に限る。取り違えても上限3回で止まる。
- 戻し方: この PR を revert。DB の形は変えないので、戻しても残るものは無い。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | PO が成功条件 G1〜G3 を承認 | PO |
| 2 | 実装カードを作り、カードの点検 | Opus |
| 3 | PO の実装承認の後、上の技術 How どおり実装＋テスト | Sonnet |
| 4 | マージ前の審査（reviewer, model opus） | Opus |
| 5 | マージ・本番反映・K1 を確認 | Opus（GO 委任の範囲） |
| 6 | 次に一時的な失敗が起きたとき K2〜K4 を測る | Opus |

## 継続

- 完了後の監視: 週1回、読み取り専用の道で KPI1〜3 を数える（error_message 別の件数と試行回数）。
- 次フェーズへの引き継ぎ: 503 の出どころ（Google か中継か）は未確認のまま残る。送り直しが3回とも失敗する事象が週に1件でも出たら、出どころの調査を別件で起こす。

## 維持の仕組み

- 守り手: 人手で守る（実装 PR で新規テスト test_api_error_auto_retry.py を守り手に差し替える）
- 対象: `backend/app/tasks/tcg_extraction_recovery.py` の送り直しの条件と上限
- 関所なしの場合: 条件や上限を変える PR は、この design.md の G1〜G3 を見直してから出す。

## 設計審査（Architect・自己審査）

- 判定: APPROVE（設計合格。PO 承認・実装開始の承認は兼ねない）
- 根拠: 変更は1ファイル＋テスト。既存の前例（同じファイルの retry_analysis_failed_jobs）と同じ型。DB の形を変えない。置き換え済み・永続的な失敗・回数上限の3つの暴走止めがある。成功時に error_message が NULL に戻ることを実物で確認（`backend/app/services/line_analysis_v102_svc.py:544`）。
- 未解決: なし（recon の不明点3件は設計に影響しない理由を記載）。
- 実物確認済み（Opus・2026-10-29）: `_reenqueue_stale_pending_jobs` は job id のリストを受け、status='pending' で再取得してから source_message_id で投入する（`backend/app/tasks/tcg_extraction_recovery.py:181`〜`:205`）。pending に戻した後に状態が変わった行は自動で外れる。
- 実装上の注意: `_run_recovery` は停滞 pending があるときだけ投入を呼ぶ。送り直しの id は停滞 pending の id と重複を除いて1つのリストにまとめ、1回の投入で渡す（同じ投稿を2回投入しない）。
