# recon — 本番の全画面の速さを毎日記録する

この文書は何か: 「画面の速さを機械で毎日測って残す」仕組みを作る前に、今どうなっているかを実物で確かめた記録です。

- 調べた日: 2026-10-31（JST）。基準: `origin/main` c63588620
- 生出力（リポジトリ外・Mac の中）: /tmp/CC報告ファイル/speed-check/ 以下（prom・alerts・safety・measure・existing・runs）

## 0. 既存 ADR の検索

- 検索語: 速さ・遅い・latency・p95・performance・SLO・prod-ui-check（`git grep -i` を `docs/adr/` に対して実行。生出力 /tmp/CC報告ファイル/speed-check/adr-grep.txt）
- 関わる ADR:
  - `docs/adr/ADR-1051-prod-ui-black-box-check.md` — 本番の画面点検。見るだけの人が毎日 JST 07:00 にログインして点検。DB に触らない。trace・スクリーンショットを作らない（公開リポジトリのため）
  - `docs/adr/ADR-079-claude-code-monitoring-access.md` — AI が監視の記録（Grafana/Prometheus）を読む道
  - `docs/adr/ADR-1024-ai-readonly-db-path.md` — AI の本番 DB 読み取り専用の道
- 画面の速さを「何秒以内」と決めた ADR は無い（検索 0 件）

## 1. 速さの自動確認は今どこにあるか

| 事実 | 根拠 |
|---|---|
| main の必須チェックに速さを測るものは無い | /tmp/CC報告ファイル/speed-check/perf.txt |
| 速さの試験は `backend/tests/test_inventory_search_perf.py` の 1 本だけ。`RUN_PERF=1` のときだけ動き、それを設定する所は `.github/` と `scripts/` に 0 件 | 同上 counts.txt |
| サーバー側の遅さの警報は `BackendHighLatency` 1 本。全部の操作をまとめて「2.5 秒を超えた割合が 5% を超えて 5 分続いた」で鳴る | `monitoring/prometheus/alert_rules.yml:83-92`、閾値の正本 `monitoring/tokens.yml`（backend_slow_request_sec・backend_slow_ratio） |
| その警報が鳴っていた長さ（30 日）: 札の付いた今の形で 324 回分、札の無い旧い形で 16319 回分（評価は 15 秒ごと） | /tmp/CC報告ファイル/speed-check/alerts/latency_firing_30d.json |
| 画面ごと（操作ごと）の警報は無い | `monitoring/prometheus/alert_rules.yml` に handler ごとの式が無い |

## 2. 本番の操作ごとの速さ（サーバーの処理時間・30 日）

- 正本: Prometheus `http_request_duration_seconds`（保存 30 日。`monitoring/tokens.yml` retention）
- 30 日で 198 種の操作。そのうち 162 種は 30 日で 20 回未満。サーバーの記録だけでは大半の画面を判定できない
- 遅い順: 解析結果の一覧 1 秒超 100/160・在庫表 1 秒超 196/1463（10 秒超 20）・解析ダッシュボードの推移 142/358
- 遅さの大半は本番反映の最中に集中（在庫表: 反映中 1 秒超 23.4%／反映外 1.3%）。30 日の記録では「データが増えたから遅くなった」関係は確認できなかった
- 生出力と計算: /tmp/CC報告ファイル/speed-check/recon-prod-30d.md、/tmp/CC報告ファイル/speed-check/regression/REPORT.md
- 限界: サーバーの処理時間だけ。画面の部品の読み込み・描画の時間は入らない

## 3. 画面の数（測る対象）

- `frontend/src/App.tsx` の画面の道すじを全部たどると 124 件。転送だけの道・ログイン系・OAuth の戻り口を除き、解析ルール画面の 25 区画を 1 画面ずつ数えると 135 件（/tmp/CC報告ファイル/speed-check/measure/targets.tsv）
- 番号つきの画面（例: 会社の詳細）は 10 種。番号は一覧画面の中のリンクから拾う
- 画面の入口の守りはログインの有無だけ（`frontend/src/components/ProtectedRoute.tsx:10-24`）。権限が足りない画面も開き、中の API が 403 を返す

## 4. 本番の画面点検（ADR-1051）の今

| 事実 | 根拠 |
|---|---|
| `.github/workflows/prod-ui-check.yml` が毎日 JST 07:00（cron `0 22 * * *`）と手動で動く。機械は `ubuntu-24.04` | `.github/workflows/prod-ui-check.yml:6-14,26` |
| 配備中は 10 分待って見送る | 同 `:29-52` |
| 点検の本体は `tests/prod-check/` の 3 ファイル。設定の `testDir` は `.`（同じ場所の、名前が .spec.ts で終わるファイルを全部動かす） | `tests/prod-check/playwright.config.ts:19` |
| 不合格のときだけ Discord に知らせる（`if: failure()`） | `.github/workflows/prod-ui-check.yml:108-141` |
| 仕事全体の時間上限は 20 分 | 同 `:27` |
| ログインする人は見るだけの役割（`dashboard.view`・`goals.view`・`customers.view`・`leads.view`）。tenant_001 のテスト用か tenant_002 の未使用の人 | `docs/handoff/qa-smoke-rebuild/design.md:188-192,369` |
| 秘密 `SMOKE_E2E_EMAIL`・`SMOKE_E2E_PASSWORD` は 2026-10-30 に登録済み（値は見ていない） | /tmp/CC報告ファイル/speed-check/existing/secrets_names.txt |
| 2026-10-31 03:00 JST に手動で 1 回動かした（run 41103098245） | /tmp/CC報告ファイル/speed-check/runs/ |
| 公開リポジトリ。実行の記録は 2026-07-19 の分が読めず（HTTP 410）、2026-08-16 の分は読める | `gh api repos/shingo-ops/salesanchor --jq .visibility`、`gh run view --log` の出力 |

### 4-2. 今の点検は、ログイン後の 4 項目が毎回失敗している（2026-10-31 判明）

| 事実 | 根拠 |
|---|---|
| run 41103007617・41103098245（どちらも 2026-10-30 18:00 UTC 前後の手動実行）: `4 failed`・`4 passed`。失敗は S3〜S6、各 1 回やり直しても失敗 | /tmp/CC報告ファイル/speed-check/runs/41103098245.log の 398-409 行・532-537 行 |
| 失敗 8 件はすべて `page.waitForLoadState("networkidle")` の行で `Timeout 30000ms exceeded`（`tests/prod-check/prod-ui.spec.ts:40,57,72,84`）。その手前の「見える」の確かめは通っている | 同 log の `> 40 |`・`> 57 |`・`> 72 |`・`> 84 |` |
| それ以前の合格 run 41006073342 は `6 skipped`・`2 passed`（秘密の登録前で中身を飛ばした）。run 41007260665 は通知の試験（`PROD_CHECK_FORCE_FAIL: 1`） | /tmp/CC報告ファイル/speed-check/runs/41006073342.log・41007260665.log |
| ログイン後に開いたままになる通信は `fetch` で開く（EventSource ではない） | `frontend/src/lib/realtime/RealtimeProvider.tsx:77-84` |
| 毎日の自動実行（schedule）はまだ 1 回も動いていない（実行一覧は手動の 4 件だけ）。次は 2026-10-31 07:00 JST | /tmp/CC報告ファイル/speed-check/runs/history.json |

### 4-3. 待ち方を直した後の残りの失敗は、ログインの回数制限が原因（2026-10-31 判明）

| 事実 | 根拠 |
|---|---|
| run 41113702544（HEAD fdf0e4798・2026-10-30 19:15 UTC 手動）: 3 failed・1 flaky・4 passed。S4 は合格。networkidle の 30 秒切れは 0 件 | /tmp/CC報告ファイル/speed-check/bin0-run-log.txt の 398-407 行 |
| S3 1 回目: console error 1 件 `Failed to load resource: the server responded with a status of 401 ()`。S3 再試行・S8 1 回目: `page.waitForURL` 30 秒切れ（`tests/prod-check/login.ts:23`）。S5・S6: `getByPlaceholder('顧客名・コードで検索...')` が 10 秒で見えない | 同 log 410-571 行 |
| 検索欄の文字は本線と同じ（`frontend/src/locales/ja.json:1136`・`frontend/src/pages/companies/CompaniesPage.tsx:392`）。同じ文字で S4 は通っている | `git grep -n "顧客名・コードで検索" origin/main -- frontend/src` |
| 本番の入口の記録で、点検の IP から `/api/v1/auth/` への通信が 3 分で 31 件。429 が 7 件（ログイン 2・refresh 5）。refresh の 429 の参照元は `/crm/companies`。403 は 0 件 | /tmp/CC報告ファイル/speed-check/bin0-auth-requests.txt・bin0-4xx.txt（Grafana の Loki `{job="containerlogs"}` を IP で絞った） |
| 入口の制限: `/api/v1/auth/` は IP ごと 1 分 10 件・まとめて 5 件まで、超えたら 429 | `nginx/nginx.conf:6`・`nginx/nginx.conf:144-146`（もう 1 つの入口 `nginx/nginx.conf:406-408` も同じ） |
| ログイン画面を開くたびに refresh が 401 になる（まだ入っていないため）。記録の 401 はすべて参照元 `/login` の refresh | 同 bin0-auth-requests.txt |
| Playwright の serial mode: 1 つ落ちると残りは飛ばし、再試行はまとめてやり直す。page を `beforeAll` で 1 つ作って使い回す例がある | https://playwright.dev/docs/test-retries （2026-10-31 直接確認。Context7 は月の上限で使えなかった） |

## 5. 開くだけで書き込む GET（測るときに止める）

画面を開いただけで本番のデータが変わる道。生出力 /tmp/CC報告ファイル/speed-check/safety/SUMMARY.md（呼び出しを 4 段までたどった検査 `get_reach.tsv` 9352 行）

| 道 | 何が起きるか | 根拠 |
|---|---|---|
| `GET /api/v1/leads/{id}/messages/{id}/attachment-url` | 添付の URL を取り直して `meta_messages` を UPDATE・commit | `backend/app/routers/leads.py:1534,1639-1649,1709-1717` |
| `GET /api/v1/tenant-commission-settings` | 行が無い会社では初期値を INSERT（`orders.view` が要る） | `backend/app/routers/tenant_commission_settings.py:88,120-131` |

- `/dashboard` は Redis の一時置き場を読むだけでデータは変えない（`backend/app/routers/dashboard.py:81-83`）

## 6. 測るときに気をつける動き

| 事実 | 根拠 |
|---|---|
| ログイン中はずっと開いたままの通信が最大 3 本ある（`/api/v1/events/stream`・`/api/v1/conversations/stream`・リード一覧だけ `/api/v1/leads/stream`）。「通信が全部終わったら表示完了」と数えると、どの画面も終わらない。3 本とも `Accept: text/event-stream` を付ける（2026-10-31 設計審査 M1 で 1 本から訂正） | `frontend/src/lib/realtime/RealtimeProvider.tsx:77-84`・`frontend/src/hooks/useSSE.ts:45-51`・`frontend/src/components/DesktopShell.tsx:138`・`frontend/src/pages/leads/LeadsPage.tsx:185` |
| 5 秒ごとに読み直す画面がある（取り込みの進み具合） | `frontend/src/features/tcg-import-workflow/useImportWorkflow.ts:61` |
| 読み込み中の印: `.sa-loading-block`・`.sa-skeleton`・`.loading-screen`・`.loading-indicator`・`[aria-busy="true"]` | `frontend/src/components/loading/`、`frontend/src/components/ProtectedRoute.tsx:16` |
| アプリは service worker を登録していない（`git grep` 0 件） | 同フォルダ measure の調査 |

## 7. 手元での全画面の測定（試した結果）

- PO のログインで全画面を測る手元の道具を用意した（/tmp/CC報告ファイル/speed-check/measure/measure.mjs。GET 以外とログイン以外の送信を全部止める）
- 2026-10-31 02:46〜03:01 JST にログインを待ったが、ログインが無く 0 画面で終わった（run3/run.log）。止める仕組みは働き、送信はログインの続き 1 件だけだった（run3/allowed_writes.jsonl）

## 8. 未確認

- U1: 点検用の人で 135 画面のうち、何画面が中身まで出るか（403 にならないか）→ 初回の記録で数える
- U2: 実行記録の保存日数の設定値（API が 403。上の 410/読める の境目から 90 日前後までしか言えない）
- U3: 点検用の人がどちらの会社か（tenant_001 か tenant_002）→ 今回の設計は会社を問わない（読むだけ）
- U4: 点検用の人が `messaging.view` を持つか（`docs/handoff/qa-smoke-rebuild/design.md:187` は「`*.view` だけ」とだけ書く）→ 便0 の手動実行（run 41113702544）の時間帯に 403 は 0 件（§4-3）。権限そのものは未確認のまま
