# recon — Gemini の道の自動切り替えと止まりの見張り

調べた人: Claude Opus（設計担当）、2026-11-05。基準: origin/main 32b39bd59（作業場所 release/gemini-auto-failover）。
本番の値は、本番サーバーで読むだけの問い合わせをして確かめた（書き換えはしていない）。

## 0. 既存 ADR の検索

- `git grep -i -l -E "gemini-egress|GEMINI_PROXY_URL|location is not supported" docs/adr/` → 該当なし。中継の決まりは ADR ではなく設計書 docs/handoff/gemini-direct-default/design.md（10/02、直接を既定・止まったら人が中継に切り替える）と docs/runbooks/gemini-egress-emergency.md にある。
- 送り直しと諦めの知らせ: docs/adr/ADR-1050-api-error-auto-retry.md（Proposed）。対象は HTTP 429/500/502/503/504 だけ（§What 1〜3）。
- 24時間保守: docs/adr/ADR-1012-ai-ops-247.md。
- 新しい番号: origin/main の最大は ADR-1060。ADR-1061 は PR #5155（共用マスタの値）が使用中 → 本件は ADR-1062。

## 1. 今日起きたこと（観測事実）

- 解析の試み（public.extraction_attempts、日本時間）: 07時台まで成功。08:49 から 19:25 まで失敗 73 回、全部 category=gemini_http_error・raw「リクエストエラー (HTTP 400)」。直前7日では成功 548・失敗 74。
- 直接の道の断り文（本番の backend から実測）: `400 FAILED_PRECONDITION "User location is not supported for the API use."`。10/02 にも同じ症状（docs/runbooks/gemini-egress-emergency.md §1）。
- Google 側で何が変わったか: 未確認（外から確かめる手段がない）。
- 中継へ切り替え: 19:49 JST（.env に GEMINI_PROXY_URL・GEMINI_GRPC_PROXY、backend・worker・beat・discord を入れ直し）。解析の成功を 20:01 JST に確認。
- 訳す機能は backend だけ残って失敗 → .env に grpc_proxy を足して backend を入れ直し、20:43 JST に成功を確認。

## 2. 半日気づかなかった理由（コード）

- 自動の送り直しの条件: `backend/app/tasks/tcg_extraction_recovery.py:306-314`（rate_limit・timeout、または http_error で raw が `(HTTP 429|500|502|503|504)` で終わる）。400 は入らない。
- 諦めの知らせの条件も同じ: `backend/app/tasks/tcg_extraction_recovery.py:402-410`。→ 400 は1回も知らせない。
- 10/02 の設計 docs/handoff/gemini-direct-default/design.md §8 は「気づく仕組み: 既存の API_ERROR 監視」と書いたが、その監視は 400 を数えない（入れ忘れ）。
- monitoring/prometheus/alert_rules.yml に解析失敗の見張りは無い（中継の箱の健康だけ）。
- 失敗の記録に残るのは「リクエストエラー (HTTP 400)」だけ: `backend/app/services/gemini_extraction_svc.py:198-210`（_safe_error_message は番号が取れると理由文を捨てる）。場所の断りか別の 400 かを DB から見分けられない。

## 3. Gemini を呼ぶ場所（新しい部品 google-genai）

- 部品の作り方: `backend/app/services/gemini_extraction_svc.py:248-276` `_get_genai_client()`。GEMINI_PROXY_URL があれば `HttpOptions(client_args={"proxy":url}, async_client_args={"proxy":url})`、無ければ直接。道は環境変数で1つに決まり、呼び出しの途中で変わらない。
- 呼び出し1（v6 の抽出・試行の記録あり）: `backend/app/services/gemini_extraction_svc.py:420`（client）・`:429`（generate_content）・`:439`（record_error_detail）。
- 呼び出し2（raw_copy・記録なし）: `backend/app/services/gemini_extraction_svc.py:508`・`:517`。
- 呼び出し3（v102 の本線）: `backend/app/services/gemini_raw_copy_v8.py:218`・`:221`、失敗は `:229` で RuntimeError に包む（`from exc`）。
- v102 の失敗の記録: `backend/app/services/line_analysis_v102_svc.py:518`（raw と category）→ `:519` RecordError("API_ERROR")。その場の送り直しは `:463`（429/500/502/503/504）・`:464`（2秒・8秒）。
- 呼び出し4（作品比べ・人が明示で呼ぶ道具）: `backend/app/services/tcg_work_comparison_svc.py:98-99`。自動では呼ばれない（:94 の説明）。

## 4. 訳す機能（古い部品 google.generativeai）

- `backend/app/services/message_translator.py:358-391` `_call_gemini`: `genai.configure`（:369）→ `GenerativeModel`（:372）→ `generate_content_async`（:377）。道は grpc_proxy 環境変数で決まり、プロセス全体に効く。呼び出しごとに道を変えられない。
- 既定の型: `backend/app/services/message_translator.py:49-50`（gemini-3.5-flash-lite）。本番は TRANSLATION_MODEL_* 未設定。:10-12 の説明文の 2.5 は古い記述。
- 使用量台帳の sdk 名: `backend/app/services/message_translator.py:495`・`:517`・`:649` が "google-generativeai"。許される名は `backend/app/services/llm_budget.py:172`（google-genai も可）。
- 呼ぶ所: backend の画面（routers の leads・translation・conv_logs）と worker（tasks/translation）。

## 5. 環境変数の渡り方

- worker: `docker-compose.yml:270-271` が GEMINI_PROXY_URL と grpc_proxy=${GEMINI_GRPC_PROXY-} を渡す。
- backend（無停止入れ替え）: `scripts/blue-green-cutover.sh:83-84` が .env のキー名だけを `--env NAME` で渡す（:97）。compose の写し（`docker-compose.yml:100-101`）は効かない。→ 今日の訳す機能の取り残しの原因。
- 中継の箱: `docker-compose.yml:427-467` gemini-egress。prod2（49.212.160.98）の tinyproxy へ SSH の通り道 `-L 0.0.0.0:18888:127.0.0.1:8888`。backnet だけに居る。backend からも worker からも http://gemini-egress:18888 で届く（今日の実測で両方成功）。

## 6. 部品の型（本番 worker の中で実物を確認）

- google-genai 2.8.0、httpx 0.28.1。
- `google.genai.errors.APIError` は `.code`・`.status`・`.message` を持ち、文字は `f'{code} {status}. {details}'`。
- `httpx.ProxyError` と `httpx.ConnectError`・`httpx.ConnectTimeout` は `httpx.TransportError` の子。
- 非同期の呼び出し（client.aio）は、aiohttp が入っていると aiohttp を使う（google/genai/_api_client.py:1138-1146 の _use_aiohttp。async_client_args に transport が無い場合）。aiohttp は discord.py（backend/requirements.txt:20）経由で入る。このとき道に届かない失敗は httpx ではなく aiohttp の例外になる（設計点検 R1 の指摘。card-1 T6b で実物を確かめる）。
- 動いたまま止まった試み: 15分動きが無い running のジョブは recover-stale-extraction-jobs（`backend/app/tasks/tcg_extraction_recovery.py:37`・`:54`、10分ごと）が pending に戻し、やり直しの結果が completed か failed で記録される。
- Context7 は月の上限で使えなかった（"Monthly quota exceeded"）。上の型は本番に入っている部品の中身を読んで確かめた。中継に届かないときに google-genai が httpx の例外をそのまま投げるか包むかは未確認 → 実装の試験で、実物の Client に届かない中継（127.0.0.1:9）を渡して確かめる（card-1 T6）。

## 7. 使える部品

- Discord 送信: `backend/app/services/discord_notifier.py:40` `_get_webhook_url`（ADMIN_NOTIFICATION_DISCORD_WEBHOOK）、`:45` `async _post_discord_webhook`。
- Redis で1回だけ送る型: `backend/app/tasks/tcg_extraction_recovery.py:457-467` `_get_redis` と `:470-504` `notify_given_up_api_error_jobs`。
- 定期作業の登録: `backend/app/celery_app.py:38`（include）・`:203-206`（recover-stale-extraction-jobs、600秒）。登録漏れの検査: `backend/tests/test_celery_beat_registered.py`。
- 試行の記録: `backend/app/services/tcg_extraction_record_svc.py:19`（TCG_SCHEMA="public"）・`:107` record_error_detail（最初の1回だけ残す）・`:231-238`（fail で validation_result に detail を全部入れる）。phase は started → received → completed、失敗は failed。

## 8. 見張りの条件を過去の記録で試した結果（読むだけ）

条件「直前30分に成功した試み0回 かつ 失敗した試み1回以上」を、直前7日の5分刻みで当てはめた。生出力: /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/aeec53ab-bd45-4a1d-84e1-ddeee58707d3/scratchpad/inc/watch-dryrun-7d.txt

| 日 | 鳴った刻み |
|---|---|
| 10/29〜11/04 | 0 |
| 11/05 | 124（08:50 から 19:55 まで） |

→ 今日の停止なら 08:50 に知らせが出ていた。7日間の空振りは 0。

見張りの問い合わせの重さ（本番・読むだけ）: extraction_attempts は 5074 行。索引は pkey・parent_attempt_id・(job, started_at)・(phase)。finished_at の索引は無く、30分の判定は全件をなめる形で 5.9 ms。5分ごとに走らせても負荷は無視できる → 索引は足さない（DB の変更なし）。

## 9. 既存の試験（Gemini の部品を差し替えている所）

- `backend/tests/test_tcg_gemini_extraction.py:505` ほか7か所、`backend/tests/test_gemini_raw_copy_v8.py:212`: `_get_genai_client` を引数なしの lambda に差し替える。
- `backend/tests/test_tcg_gemini_extraction.py:791-835`: GEMINI_PROXY_URL ありなしの部品の作り方を検査。
- `backend/tests/test_message_translator.py:84-91` `_install_fake_genai`（古い部品の偽物を _GENAI_CACHE に入れる）、`:565-566`（GenerativeModel が MODEL_SEND で呼ばれた）。
- `backend/tests/test_message_translator_usage_ledger.py:31-33`・`:70`（sdk == "google-generativeai"）・`:86`。
