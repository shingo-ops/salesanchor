# 実装カード 便2 — サーバー復旧後の点検と Discord への ✅/❌

> この文書は何か：outage-recovery-watch 便2 の作業指示書です。
> - 監視サーバー（prod2）に小さな点検係 `recovery-check` を常駐させます。
> - 本番の API が止まってから戻ったとき、アプリ・API・LP・裏方の処理・時計を点検します。
> - 結果は Discord に ✅（全部正常）か ❌＋異常の項目名で 1 件届きます。
> - 2026-10-22 のさくらメンテで prod1 が 12:02〜12:54 JST に止まりましたが、戻った後に「全部戻ったか」を知らせる仕組みがありませんでした。そのための便です。
> - 本番への配置は §8 で行います。マージの後に、Opus が PO の同意票を受けて行います。

- 設計: docs/handoff/outage-recovery-watch/design.md §1 G2・§3-2・§3-2-1・受け入れ基準
- recon: docs/handoff/outage-recovery-watch/recon.md
- 事実確認の生出力（2026-10-22 Sonnet。repo は origin/main だけを読み、本番は読んでいない）:
  - /tmp/CC報告ファイル/outage-bin2/recon-raw.md
  - /tmp/CC報告ファイル/outage-bin2/recon-raw2.md
  - /tmp/CC報告ファイル/outage-bin2/mc.txt
- 対象ADR:
  - ADR-1012（AI保守運用24時間化。決定1「経路の正本は Alertmanager 1 本」:25）
  - ADR-080（監視は管理室VPSへ分離）
- 状態: 設計は PO 承認済み（2026-10-22 PO 返信「1」。KGI G1〜G3 と案M）。PO の「1」（2026-10-22、便2・便3の設計に進む）と GO 委任に基づく実装便
- 前提: このカードの PR（文書だけ）が main にマージされていること（§10 で確かめる）
- 危険便（ADR-136 の危険パス）: いいえ
  - 触るのは `monitoring/`・`docker-compose.monitoring.yml`・`.github/workflows/monitoring-check.yml`・`docs/` だけ。
  - `migrations/`・`deploy.yml`・本番の `scripts/` は触らない。
  - ADR-1015 の区分は A（新機能）で、PO 承認は設計の承認で済んでいる（状態の行）。
- §10 の手順で作業場所を作った直後に `cd /Users/tanizawashingo/worktrees/salesanchor/release-outage-recovery-check && ./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:。AGENTS.md:99）
- 担当:
  - Sonnet: 実装と配置台本の下書き
  - Opus（reviewer）: コード審査
  - Opus: GO・マージ・本番配置・反映確認

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（復旧後の点検と、その結果の通知だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§5-6。件数とルール名を対で出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。今はルール 29 本・手順書 35 節・送り先の子ルート 2 本） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§8 は prod2 だけ。担当は本番に接続しない。配置は Opus が同意票を受けて行う） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード outage-recovery-watch 便2 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 新しいディレクトリ `monitoring/recovery-check/`（点検係の本体・Dockerfile・依存・単体試験）
2. `docker-compose.monitoring.yml` に service `recovery-check` と volume `recovery_check_data`
3. `monitoring/prometheus/prometheus.yml` に scrape の job `recovery-check`
4. `monitoring/prometheus/alert_rules.yml` に新しいグループ `recovery_check_alerts`（3 本）
5. `monitoring/prometheus/tests/alert_rules_test.yml` に 3 本の試験
6. `monitoring/alertmanager/alertmanager.yml` に、✅ だけを Discord に送る子ルート 1 本と受け手 1 つ
7. `.github/workflows/monitoring-check.yml` に、点検係の単体試験 1 行と、送り先の試験 2 行
8. `docs/runbooks/alerts.md` に 3 節
9. `monitoring/tokens.yml` に閾値 1 行と for 1 行
10. 本番配置の台本 3 本（リポジトリの外 `/tmp/CC報告ファイル/outage-bin2/deploy/`。commit しない。§4-10）

入れない:
- メールの見張り（便3）
- 時計を自動で直す仕組み、止まったサービスを自動で再起動する仕組み（点検は読み取りだけ）
- 既存の 29 本のルールの式・for・札
- alertmanager.yml の既存の route・receivers・inhibit_rules の行（足すだけ）
- `monitoring/scripts/check_alert_rules.py`（変えない。新ルール 3 本は既存の検査に乗る）
- `monitoring/scripts/check_config_drift.sh` の比べる 6 本（compose・prometheus.yml・alert_rules.yml・alertmanager.yml は既に入っている。点検係の本体はずれ検査に入れない。§2 決めたこと）
- Discord の文面の型（Alertmanager の既定の文面のまま）
- 本番への接続（担当は prod1・prod2 に接続しない）

## 2. 前提の事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | Prometheus のルールは今 29 本。最後のグループは `clock_alerts`（alert_rules.yml:349）。試験の頭書き :4 は「全 29 本」。手順書 :3 は「Prometheus 29 本」「Loki 6 本」で、見出しは 35 節 | mc.txt・便1 配置記録 |
| F2 | alertmanager.yml の route（:1-10）: 既定 receiver discord-server-alerts、group_by alertname・job・instance、group_wait 30s、group_interval 5m、repeat_interval 4h。子ルートは 2 本で matcher 無し（1 本目 discord-server-alerts に continue: true、2 本目 ops-api）。つまり全警報が Discord と保守 API の両方に届く。Discord は `webhook_url_file: /etc/alertmanager/secrets/discord-webhook`・send_resolved: true（:11-15）。inhibit_rules は :27 以降 | recon-raw2 §1・recon-raw §2 |
| F3 | Alertmanager の公式設定: route の `continue` の既定は false で、continue が false なら一致した最初の子ルートで止まる。discord_config の `send_resolved` の既定は true で、意味は「解決の通知を送るか」 | https://prometheus.io/docs/alerting/latest/configuration/（2026-10-22 Opus が WebFetch で確認。Context7 は月の上限で使えなかった） |
| F4 | CI の送り先の試験（monitoring-check.yml の step「Alertmanager 送り先の試験」）は `alertname=CiRoutesTest` が discord-server-alerts と ops-api の両方に届くことを 2 行で確かめる | mc.txt |
| F5 | CI の単体試験の step「アプリの健康診断の欠け検査と状態書き係の試験」は `python3 monitoring/.../tests/test_*.py -v` の形で 3 行を動かす（pytest ではなく、標準の unittest を直接実行する形）。CI の変更検出の正規表現（monitoring-check.yml:30）は `monitoring/` と `docker-compose.monitoring.yml` を含む | mc.txt・recon-raw §6 |
| F6 | `/api/health`（backend/app/routers/health.py:16-75）: DB 失敗は HTTP 503 で `{"status":"error","database":"disconnected"}` だけを返す（redis・celery のキーは無い）。それ以外は HTTP 200 で `status`（ok か degraded）・`database`・`redis`・`celery`。redis や celery が止まっていても HTTP 200 になる。だから HTTP 200 だけでは足りず、本文の 3 つの値を見る | recon-raw §5(a) |
| F7 | 見る URL（monitoring/uptime-kuma-monitors.yml:37・:44・:51）: アプリ `https://app.salesanchor.jp/`、API `https://api.salesanchor.jp/api/health`、LP `https://salesanchor.jp/`。prod2 の Uptime Kuma が 60 秒おきに同じ URL を見ている（prod2 から公開 URL に届く） | recon-raw §8 |
| F8 | 指標: `celery_heartbeat_last_success_timestamp_seconds{job="backend"}`（ルールは古さ > 600 秒。alert_rules.yml:184）・`salesanchor_container_state_last_run_timestamp_seconds{instance="app-vps"}`（> 300 秒。:327）・`node_time_seconds{job="node-exporter"}`（ClockSkew の式 :355） | recon-raw §5(c) |
| F9 | 型にする既存の常駐: monitoring/github-collector（python:3.12-slim、prometheus_client==0.21.1・requests==2.32.3、`while True` と `time.sleep`、`start_http_server`、compose :152-174 に healthcheck・メモリ 64M・cpus 0.25・no-new-privileges）。状態ファイルも試験も無い | recon-raw §1 |
| F10 | compose に `networks:` は無い（既定のネットワークに全員がいる）。Prometheus にはサービス名 `prometheus:9090` で届く。名前付き volume は :243-247 の 4 つ | recon-raw §1・mc.txt |
| F11 | ServiceDown は `up == 0` が 2 分続くと鳴る（alert_rules.yml:58）。新しい scrape の job も自動で見張られる | recon-raw2 §6 |
| F12 | 毎日の設定ずれの見回り（monitoring-config-drift.yml、日本時間 09:23）は compose・prometheus.yml・alert_rules.yml・alertmanager.yml を含む 6 本を本番と比べる | recon-raw §6 |
| F13 | 保守 API（backend/app/routers/ops.py:213-267）は届いた警報をすべて障害記録の表に書く。札は alertname と severity だけを使い、tier では分けない | recon-raw2 §2・§10 |

決めたこと:
- 通知の道は design.md §3-2-1 のとおり、指標 → ルール → Alertmanager。点検係は Discord に直接送らない。
- ✅ は警報 `RecoveryCheckPassed` で表す。新しい子ルート（matcher `alertname="RecoveryCheckPassed"`）を一番前に置く。
  - continue は付けないので、F3 のとおりそこで止まり、Discord にだけ届く。
  - 保守 API には届かない（正常の知らせを障害記録に書かない）。
  - 受け手は `send_resolved: false` にする。✅ の警報は 10 分で消えるが、そのときに「解決」は届かない。
- ❌ は警報 `RecoveryCheckFailed`（項目ごとに 1 本。札 `item` と `item_ja`）。既存の道で Discord と保守 API の両方に届く。
  - group_by が alertname・job・instance なので、同時に NG の項目は 1 件の通知にまとまる。
  - 全項目が直ると、Discord に「解決」が届く。
- 点検係の繰り返しが止まったら `RecoveryCheckStale` が鳴る。点検係そのものが落ちたら ServiceDown が鳴る（F11）。
- 時計は Prometheus の値で見る（design.md §3-2-1）。
  - Prometheus に聞けないときは、時計・裏方・コンテナの記録の 3 項目を判定しない。
  - 時計が NG のときは、裏方・コンテナの記録の 2 項目を判定しない。
  - 判定しない項目は NG にも OK にも数えない。全体は ✅ にならない（判定した中に NG があるため）。
- DB が NG（HTTP 503）のときは、redis と celery を判定しない（F6。本文にキーが無いため）。
- 「止まっていた」と見なすのは、本番の本体が 2 回続けて応答しないとき（約 2 分。KumaMonitorDown の for 2m と揃える）。1 回だけでは騒がない。
  - 「応答した」とは、API が本文つきで応答した（JSON として読め `status` キーがある。HTTP 200 でも 503 でもよい）か、アプリ画面が HTTP 200 を返したこと（§4-1 の `server_responding`）。
  - 本文の database・redis・celery の値では判定しない。値で判定すると、裏方の処理だけが戻らないときに「戻った」とならず ❌ が届かない。止まっていないのに裏方の応答確認が外れただけで ✅ が出ることもある（2026-10-22 設計審査の指摘1）。
  - Cloudflare の 52x のように本文が JSON でない応答は「応答なし」とする。
- 点検係自身が 300 秒より長く止まっていた（prod2 の再起動など）ときは、起動した後に 1 回点検する。prod2 とprod1 が同時に止まった場合も ✅/❌ が届くようにするため。
- 状態は名前付き volume のファイル 1 つ（`/data/state.json`）に置く。書くときは一時ファイルに書いてから `os.replace` で置き換える（mac-jobs-watch の型）。
- 点検係の本体はずれ検査（F12）に入れない。点検係の本体は `docker compose build` で入れたイメージで動き、ずれ検査は設定ファイルの比較のためのもの。compose の service 定義はずれ検査に入っている。
- 単体試験は標準の unittest にする（F5。CI に pytest も prometheus_client も入れずに済む）。判定の部品 `recovery_check.py` は標準ライブラリだけで書く。`prometheus_client` は `main.py` だけで使う。

## 3. 触るファイル（これ以外は触らない）

- 新規: `monitoring/recovery-check/Dockerfile`
- 新規: `monitoring/recovery-check/requirements.txt`
- 新規: `monitoring/recovery-check/recovery_check.py`
- 新規: `monitoring/recovery-check/main.py`
- 新規: `monitoring/recovery-check/tests/test_recovery_check.py`
- 変更: `docker-compose.monitoring.yml`
- 変更: `monitoring/prometheus/prometheus.yml`
- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`
- 変更: `monitoring/alertmanager/alertmanager.yml`
- 変更: `.github/workflows/monitoring-check.yml`
- 変更: `monitoring/tokens.yml`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/outage-recovery-watch/card-bin2.md`（このカード。担当は §13 報告欄の追記のみ）
- リポジトリの外（commit しない）:
  - `/tmp/CC報告ファイル/outage-bin2/deploy/deploy-bin2.sh`
  - `/tmp/CC報告ファイル/outage-bin2/deploy/verify-bin2.sh`
  - `/tmp/CC報告ファイル/outage-bin2/deploy/rollback-bin2.sh`

## 4. 作り方

4-1. `monitoring/recovery-check/recovery_check.py`（判定の部品。標準ライブラリだけ。ネットワークに触る関数は引数で受け取り、試験で偽物に差し替えられるようにする）

点検の項目（この順・この名前。`item` は英字、`item_ja` は Discord に出る日本語）:

| item | item_ja | 判定（OK の条件） |
|---|---|---|
| `app` | アプリ画面 | `APP_URL` の GET が HTTP 200 |
| `api` | API | `API_HEALTH_URL` の GET が HTTP 200 |
| `database` | データベース | health 本文の `database` が `"connected"` |
| `redis` | Redis | health 本文の `redis` が `"connected"`（`database` が connected でなければ判定しない） |
| `celery` | 裏方の処理の受け手 | health 本文の `celery` が `"connected"`（同上） |
| `lp` | 紹介ページ | `LP_URL` の GET が HTTP 200 |
| `prometheus` | 監視の読み取り | 下の 3 つの問い合わせがすべて応答を返す（HTTP 200 で `status` が `success`） |
| `clock` | 本番サーバーの時計 | `abs(node_time_seconds{job="node-exporter",instance="app-vps"} - timestamp(node_time_seconds{job="node-exporter",instance="app-vps"}))` の結果が 1 件以上あり、値が 60 未満（`prometheus` が NG なら判定しない） |
| `celery_heartbeat` | 裏方の処理 | `time() - max(celery_heartbeat_last_success_timestamp_seconds{job="backend"})` の結果が 1 件あり、値が 600 未満（`prometheus` か `clock` が NG なら判定しない） |
| `container_state` | コンテナの状態記録 | `time() - max(salesanchor_container_state_last_run_timestamp_seconds{instance="app-vps"})` の結果が 1 件あり、値が 300 未満（同上） |

- health の本文が JSON として読めない（または `database` キーが無い）ときは、`database` を NG にし、`redis`・`celery` は判定しない（並びに入れない）。
- 関数 `http_get(url) -> (status, body)`（本物の実装。試験では偽物に差し替える）:
  - `urllib.request.urlopen` で GET。timeout 10 秒、`User-Agent: salesanchor-recovery-check/1`。転送（redirect）は標準の動きのまま追う。
  - 成功: `(resp.status, resp.read())`。
  - `urllib.error.HTTPError`（4xx・5xx）: `(e.code, e.read())`。503 の本文もこれで読める。
  - それ以外の例外（つながらない・timeout・`URLError`）: `(None, b"")`。
- 関数 `prom_query(expr) -> list[float] | None`（本物の実装。試験では偽物）:
  - `PROMETHEUS_URL` + `/api/v1/query?query=...`（URL エンコードする）。timeout 10 秒。
  - HTTP 200 で `status` が `"success"`: `data.result` の各要素の `value[1]` を float にした並び（結果が 0 件なら空の並び）。
  - それ以外（例外・200 以外・`status` が success でない）: None。
  - 表の `prometheus` 項目は、時計・裏方・コンテナの 3 つの問い合わせのどれか 1 つでも None なら NG。
- 関数 `run_check(http_get, prom_query) -> list[str]`: NG の item の並び（上の表の順）を返す。全部 OK なら空の並び。判定しない項目は入れない。
- 関数 `server_responding(http_get) -> bool`（本番の本体が応答したか。§2 決めたこと）: 先に API を見て、True ならアプリ画面は見ない。次のどちらかなら True。
  - `API_HEALTH_URL` の status が None でなく、本文が JSON の object として読め、`status` キーがある（HTTP 200 でも 503 でもよい）。
  - （API が False のときだけ見る）`APP_URL` の status が 200。
- timeout 10 秒は 1 回の読み書きごとの上限で、名前の解決や転送を追う分を含めると 1 回の GET が 10 秒を超えることがある。時間の見込みは §7 の終わりの模型による（main の周期を固定するので、1 回分の所要が 60 秒未満なら周期はずれない）。

状態（`state.json` の中身。キーはこの 7 つ）:

```json
{"phase": "ok", "ng_streak": 0, "attempt": 0, "next_check_at": 0, "failed_items": [], "passed_until": 0, "last_poll_at": 0}
```

- `phase` は `ok`（ふだん）・`down`（止まっていた）・`checking`（戻った後の点検中）・`failed`（❌ を出した）の 4 つ。
- 関数 `tick(state, now, responding, check, simulate_down) -> state`（1 回分の進め方。`responding` は `server_responding` の結果。`check` は引数なしで `run_check` の結果を返す関数。`state` が None なら初回）。上から順に行う:
  1. `state` が None（初回）: 上の初期値に `last_poll_at=now` を入れて返す。点検も通知もしない。
  2. `simulate_down` が True: `phase="down"`・`ng_streak=0`・`last_poll_at=now` にして返す（§8 の本番での確かめ用）。この回は手順 3・4 を行わない。
  3. `phase == "ok"` で、`now - last_poll_at > 300`（点検係自身が止まっていた）: `phase="checking"`・`attempt=0`・`next_check_at=now`・`last_poll_at=now` にして返す。この回は手順 4 を行わない（点検は次の回）。
  4. `phase` ごとに進める。段が変わっても同じ回の中で次の段へ続けて進めない。ただし `down` → `checking` の 1 つだけは例外で、同じ回の中で `checking` の段を 1 回行う（復帰から ✅/❌ までを約 1 分縮めるため。2026-10-22 設計審査の指摘9）:
     - `ok`: `responding` なら `ng_streak=0`。違えば `ng_streak += 1`、2 以上になったら `phase="down"`。
     - `down`: `responding` なら `phase="checking"`・`attempt=0`・`next_check_at=now` にして、続けて下の `checking` の段を行う。違えば何もしない。
     - `checking`: `now >= next_check_at` なら `check()` を 1 回呼び、`attempt += 1`。
       - 結果が空: `passed_until = now + 600`・`phase="ok"`・`ng_streak=0`・`failed_items=[]`（✅）。
       - 空でなく `attempt >= 4`: `failed_items = 結果`・`phase="failed"`・`next_check_at = now + 300`（❌）。
       - 空でなく `attempt < 4`: `next_check_at = now + 110`（次の点検は 2 回後の回＝約 2 分後。0・2・4・6 分の 4 回。120 ちょうどにすると、時刻の揺れで 1 回分飛ばすことがあるため 110 にする。2026-10-22 再審査の指摘N1）。
     - `failed`: `now >= next_check_at` なら `check()` を 1 回呼ぶ。
       - 結果が空: `failed_items=[]`・`phase="ok"`・`ng_streak=0`。`passed_until` は変えない（Discord には ❌ の「解決」が届くので、✅ を重ねて出さない）。
       - 空でない: `failed_items = 結果`・`next_check_at = now + 300`。
       - `responding` は `failed` の中では見ない（❌ を出したまま点検を続ける。止まっていることは ServiceDown・KumaMonitorDown が別に知らせる）。
  5. `last_poll_at = now` にして返す。
- 関数 `load_state(path)`: ファイルが無ければ None。JSON として読めないとき、または 7 つのキーが揃わないときも None（初回と同じ扱いにして、例外で止まらない）。その旨を 1 行ログに出す。
- 関数 `save_state(path, state)`: 同じディレクトリの一時ファイルに書き、`os.replace` で置き換える。

4-2. `monitoring/recovery-check/main.py`（常駐の本体）
- 環境変数: `PORT`（既定 8000）・`POLL_INTERVAL`（既定 60）・`STATE_FILE`（既定 `/data/state.json`）・`PROMETHEUS_URL`（既定 `http://prometheus:9090`）・`APP_URL`・`API_HEALTH_URL`・`LP_URL`（既定は F7 の 3 つ）。
- `prometheus_client` の Gauge を 3 つ出す:
  - `salesanchor_recovery_check_failed`（札 `item`・`item_ja`。表の 10 項目すべてを毎回出す。`phase == "failed"` で `failed_items` に入っている項目は 1、それ以外は 0）
  - `salesanchor_recovery_check_passed_until_timestamp_seconds`（`passed_until`）
  - `salesanchor_recovery_check_last_poll_timestamp_seconds`（`last_poll_at`）
- 起動時に `start_http_server(PORT)` を呼び、次の繰り返しに入る。毎回、状態はファイルから読み直す（ファイルが正本）。
  1. `simulate_down` を求める印のファイル（`STATE_FILE` と同じディレクトリの `simulate-down`）があれば、消してから True を渡す。
  2. `tick(load_state(...), time.time(), server_responding(...), lambda: run_check(...), simulate_down)` を呼ぶ。
  3. `save_state` して Gauge を更新する。
  4. `time.sleep(max(0, POLL_INTERVAL - その回の所要秒))`（周期を 60 秒に固定する。その回の始めに `time.monotonic()` を取り、終わりとの差を所要秒とする。2026-10-22 再審査の指摘N1）。
  - 1 回分の中の例外は `log.exception` で記録して続ける（github-collector の型）。
- 引数 `--simulate-down` を付けて起動したときは、常駐せず、印のファイルを作るだけで終わる（§8 の確かめで `docker compose exec` から使う）。
- 引数 `--check-once` を付けて起動したときは、常駐せず、状態ファイルにも触らず、`server_responding` と `run_check` を 1 回ずつ実行して、1 行の JSON `{"responding": true, "ng": []}` を標準出力に出して終わる。終了コードは、`responding` が True かつ `ng` が空なら 0、それ以外は 1（§8 で、本番での確かめの前に偽の ❌ が出ないことを確かめるため。2026-10-22 設計審査の指摘4）。
- `--simulate-down` と `--check-once` は HTTP の口（`start_http_server`）を開かない（常駐中の本体と口がぶつからないように）。
- ログは状態が変わったとき（`phase` が変わったとき・点検を行ったとき）だけ 1 行出す。点検の結果は NG の item の並びを書く。URL の秘密や本文の全文は出さない。

4-3. `monitoring/recovery-check/Dockerfile`・`requirements.txt`: github-collector の Dockerfile・requirements.txt と同じ形（`FROM python:3.12-slim`・`WORKDIR /app`・pip install・EXPOSE 8000）。
- requirements は `prometheus_client==0.21.1` の 1 行だけ。requests は使わない（HTTP は標準の `urllib.request`）。
- COPY は `recovery_check.py` と `main.py`。CMD は `["python", "main.py"]`。

4-4. `monitoring/recovery-check/tests/test_recovery_check.py`（unittest。`sys.path` に 1 つ上のディレクトリを足して `recovery_check` を読む。ネットワークは使わない）。最低限この 14 件:
1. 初回（state None）: phase ok、`check` は呼ばれない。
2. ok で responding False 1 回: ng_streak 1・phase ok。2 回目で phase down。
3. down で responding True: 同じ回で `check` が 1 回呼ばれ、空を返すと passed_until = now+600・phase ok。
4. down で responding True、`check` が NG を返し続ける: 1 回目（同じ回）・120 秒後・240 秒後は phase checking のまま・failed_items は空。360 秒後の 4 回目で phase failed・failed_items に NG の項目・next_check_at = now+300。
5. checking で NG 2 回の後に空: ✅（passed_until が入る）で、failed にはならない。
6. failed で 300 秒後の点検が空: failed_items 空・phase ok・passed_until は変わらない。
7. `run_check`: Prometheus が答えない（`prom_query` が None）と、`prometheus` だけが NG で、`clock`・`celery_heartbeat`・`container_state` は並びに入らない。
8. `run_check`: 時計の差が 61 なら `clock` が NG で、`celery_heartbeat`・`container_state` は並びに入らない。59 なら OK。
9. `run_check`: health が `(503, b'{"status":"error","database":"disconnected"}')` のとき、`api` と `database` が NG、`redis` と `celery` は並びに入らない。health が `(None, b"")` のときも `api` と `database` が NG、`redis` と `celery` は並びに入らない。
10. `server_responding`: health が `(503, b'{"status":"error",...}')` なら True。health が `(502, b"<html>...")` でアプリ画面が `(502, ...)` なら False。health が `(None, b"")` でもアプリ画面が `(200, ...)` なら True。
11. ok で `last_poll_at` が 301 秒前: phase checking・next_check_at = now・この回は `check` が呼ばれない。次の回で `check` が呼ばれる。
12. `simulate_down` True: phase down・この回は `check` が呼ばれない。`save_state` → `load_state` で同じ中身に戻る。壊れた JSON・キーの欠けた JSON は None になる。
13. 部分的にしか戻らない（指摘1）: down で responding True、`check` が `["celery", "celery_heartbeat"]` を 4 回返す: 4 回目で phase failed・failed_items が `["celery", "celery_heartbeat"]`。
14. 止まっていないのに裏方だけ外れる（指摘1）: ok で responding True のまま 60 秒おきに 5 回 tick しても、phase は ok のまま・`check` は呼ばれない・passed_until は 0 のまま。
- 実行: `python3 monitoring/recovery-check/tests/test_recovery_check.py -v`（作業場所の直下から）。

4-5. `docker-compose.monitoring.yml`:
- github-collector の service（:152-174）の後に足す（完成形）:

```yaml
  # 復旧後の点検係（outage-recovery-watch 便2）
  # 本番 API が止まって戻ったら、アプリ・API・LP・裏方・時計を点検し、結果を指標で出す（通知は Alertmanager）
  recovery-check:
    build:
      context: ./monitoring/recovery-check
    environment:
      - PORT=8000
      - POLL_INTERVAL=60
      - STATE_FILE=/data/state.json
      - PROMETHEUS_URL=http://prometheus:9090
      - APP_URL=https://app.salesanchor.jp/
      - API_HEALTH_URL=https://api.salesanchor.jp/api/health
      - LP_URL=https://salesanchor.jp/
    volumes:
      - recovery_check_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/metrics', timeout=4).status == 200 else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: "0.25"
    security_opt:
      - no-new-privileges:true
```

- 行の字下げと書き方は、github-collector の実際の行（:152-174）に合わせる（上と違えば実物に合わせ、報告に書く）。
- 最後の `volumes:` の段（:243-247）に `  recovery_check_data:` を足す。

4-6. `monitoring/prometheus/prometheus.yml`: github-collector の job（:56-59）の後に足す（scrape_interval は書かない。既定の 15s を使う）:

```yaml

  # 復旧後の点検係（outage-recovery-watch 便2。alert_rules.yml: recovery_check_alerts）
  - job_name: "recovery-check"
    static_configs:
      - targets: ["recovery-check:8000"]
```

4-7. `monitoring/prometheus/alert_rules.yml` の最後（`clock_alerts` の後）に足す（完成形。他の行は変えない）:

```yaml
  - name: recovery_check_alerts
    rules:
      # 復旧後の点検で、6 分たっても直らない項目がある（outage-recovery-watch 便2・monitoring/recovery-check）
      # 同時に NG の項目は group_by（alertname, job, instance）で 1 件の通知にまとまる。全部直ると Discord に「解決」が届く
      - alert: RecoveryCheckFailed
        expr: salesanchor_recovery_check_failed{job="recovery-check"} == 1
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "❌ サーバー復旧後の点検で異常: {{ $labels.item_ja }}"
          description: "本番の API が止まって戻った後の点検で、{{ $labels.item_ja }}（{{ $labels.item }}）が 6 分たっても正常に戻りません。5 分おきに点検を続け、直ればこの警報は解決します。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#recoverycheckfailed"

      # 復旧後の点検がすべて正常（✅）。10 分だけ鳴り、Discord にだけ届く（alertmanager.yml の子ルート。解決の通知は出さない）
      - alert: RecoveryCheckPassed
        expr: salesanchor_recovery_check_passed_until_timestamp_seconds{job="recovery-check"} > time()
        labels:
          severity: info
          tier: ticket
        annotations:
          summary: "✅ サーバー復旧後の点検: すべて正常です"
          description: "本番の API が止まって戻った後の点検で、アプリ画面・API・データベース・Redis・裏方の処理の受け手・紹介ページ・監視の読み取り・本番サーバーの時計・裏方の処理・コンテナの状態記録がすべて正常でした。対応は不要です。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#recoverycheckpassed"

      # 点検係の繰り返しが 5 分以上止まっている（tokens.yml: recovery_check_stale_sec=300）
      - alert: RecoveryCheckStale
        expr: (time() - salesanchor_recovery_check_last_poll_timestamp_seconds{job="recovery-check"}) > 300
        for: 5m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "復旧後の点検係が止まっています"
          description: "点検係（recovery-check）が {{ $value | humanizeDuration }} の間、点検を回していません。この間、サーバーが戻っても ✅/❌ は届きません。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#recoverycheckstale"
```

- `tier` の値が `check_alert_rules.py` の TIERS にあるかを、作業の前に確かめる（`grep -n "TIERS" monitoring/scripts/check_alert_rules.py`）。`ticket` が無ければ BLOCKED:。
- `runbook_url` の前半は、既存のルールの行と同じ文字列であることを確かめる（`check_alert_rules.py` が URL_BASE と比べる）。

4-8. `monitoring/prometheus/tests/alert_rules_test.yml`（:4 の「全 29 本」を「全 32 本」に直す。他の試験は変えない）。最後に足す。入力ごとに test group を分ける。系列の札は `job="recovery-check", instance="recovery-check:8000"` に揃える。
1. RecoveryCheckFailed 鳴る: `salesanchor_recovery_check_failed{..., item="clock", item_ja="本番サーバーの時計"}` を `'1x10'` にする。`eval_time` 1m で 1 件。`exp_labels` は job・instance・item・item_ja・severity・tier。`exp_annotations` は 3 つとも書く。
2. RecoveryCheckFailed 鳴らない: `'0x10'` で `eval_time` 1m に 0 件。
3. RecoveryCheckPassed 鳴る: `salesanchor_recovery_check_passed_until_timestamp_seconds` を `'600x20'`。`eval_time` 5m（time() = 300 < 600）で 1 件。
4. RecoveryCheckPassed 鳴らない（期限切れ）: 同じ入力で `eval_time` 15m（time() = 900 > 600）は 0 件。
5. RecoveryCheckStale 鳴る: `salesanchor_recovery_check_last_poll_timestamp_seconds` を `'0x30'`（ずっと時刻 0 のまま）にする。`eval_time` 15m で 1 件（time()-0 = 900 > 300 が 5 分以上）。`exp_annotations` の description の humanizeDuration は 900 秒で `15m 0s` の見込み（便1 の試験 2 で `61` が `1m 1s` になったのと同じ規則）。CI で違えば、Opus が got 側を渡すので合わせる。
6. RecoveryCheckStale 鳴らない: `'0+60x30'`（毎分更新）で `eval_time` 15m に 0 件。

4-9. `monitoring/alertmanager/alertmanager.yml`（足すだけ。既存の行は消さない・変えない）:
- `routes:`（:7）の直後、既存の 1 本目（`- receiver: discord-server-alerts`）の前に足す:

```yaml
    # 復旧後の点検の ✅ は Discord にだけ送る。障害記録（ops-api）に載せず、解決の通知も出さない（outage-recovery-watch 便2）
    # continue を付けないので、一致したらここで止まる
    - receiver: discord-recovery-info
      matchers:
        - alertname="RecoveryCheckPassed"
```

- `receivers:` の段の、既存の受け手の後（ops-api の後、`inhibit_rules:` の前）に足す:

```yaml
  - name: discord-recovery-info
    discord_configs:
      - webhook_url_file: /etc/alertmanager/secrets/discord-webhook
        send_resolved: false
```

- 字下げは実物の discord-server-alerts の行に合わせる。

4-10. `.github/workflows/monitoring-check.yml`（足すだけ）:
- step「アプリの健康診断の欠け検査と状態書き係の試験」の `run:` の最後に 1 行: `python3 monitoring/recovery-check/tests/test_recovery_check.py -v`
- step「Alertmanager 送り先の試験（amtool routes test）」の最後に 2 行。既存の 2 行と同じ `docker run ... config routes test --config.file=/a/alertmanager.yml` の形で:
  - `--verify.receivers=discord-recovery-info alertname=RecoveryCheckPassed`（✅ は Discord の受け手 1 つだけ）
  - `--verify.receivers=discord-server-alerts,ops-api alertname=RecoveryCheckFailed severity=critical`（❌ は既存どおり両方）
- 同じ step のコメント（「どの通知も Discord と保守 API の両方に届くこと」）の次の行に、`# ただし RecoveryCheckPassed（復旧後の点検の ✅）だけは Discord にだけ届くこと（outage-recovery-watch 便2）` を足す。
- これ以外の step・`on:`・変更検出の正規表現は変えない。
- このファイルの編集が見張り（フック）に止められたら、言い換えずに BLOCKED:（止まった原文を報告）。

4-11. `docs/runbooks/alerts.md`（:3 の「Prometheus 29 本」を「32 本」に直す）。最後に `## RecoveryCheckFailed`・`## RecoveryCheckPassed`・`## RecoveryCheckStale` の 3 節を足す。形は既存の節（`- 札：`・`- 何が起きているか：`・（`- 影響：`）・`- 最初に見るもの：`・`- 直し方：`・`- 止め方：`）。書くこと:
- RecoveryCheckFailed:
  - 札：page
  - 何が起きているか：本番の API が止まって戻った後の点検で、札 `item_ja` の項目が 6 分たっても正常に戻らない。項目は 10 個（アプリ画面・API・データベース・Redis・裏方の処理の受け手・紹介ページ・監視の読み取り・本番サーバーの時計・裏方の処理・コンテナの状態記録）。監視の読み取りが NG のときは時計・裏方の処理・コンテナの状態記録を、時計が NG のときは裏方の処理・コンテナの状態記録を判定しない（その間は一覧に出ない）。
  - 影響：その項目が使えないまま。直るまで 5 分おきに点検を続ける。
  - 最初に見るもの：Prometheus で `salesanchor_recovery_check_failed == 1` の `item`。`docker compose -f docker-compose.monitoring.yml logs --tail 50 recovery-check`（prod2）。同じ時間に鳴っている警報（ServiceDown・ClockSkew・CeleryHeartbeatStale 等）。
  - 直し方：項目ごとの警報の節に従う。直れば自動で解決する。サービスの再起動などの本番の変更は Opus に報告する（PO の判断）。
  - 止め方：`amtool silence add alertname=RecoveryCheckFailed --duration=PERIOD --comment=REASON`
- RecoveryCheckPassed:
  - 札：ticket（知らせだけ。対応は要らない）
  - 何が起きているか：本番の API が止まって戻った後の点検で、10 項目すべてが正常だった。10 分だけ鳴り、Discord にだけ届く（障害記録には書かない。解決の通知も出ない）。
  - 影響：無し。
  - 最初に見るもの：無し。止まっていた間の原因は、同じ時間の ServiceDown・KumaMonitorDown の記録で見る。
  - 直し方：無し。
  - 止め方：`amtool silence add alertname=RecoveryCheckPassed --duration=PERIOD --comment=REASON`
- RecoveryCheckStale:
  - 札：ticket
  - 何が起きているか：点検係（prod2 の `recovery-check`）が 5 分以上点検を回していない。
  - 影響：サーバーが戻っても ✅/❌ が届かない。
  - 最初に見るもの：prod2 の `docker compose -f docker-compose.monitoring.yml ps recovery-check` と `logs --tail 50 recovery-check`。ServiceDown（job recovery-check）が同時に鳴っているか。
  - 直し方：Opus に報告する（コンテナの再起動は本番の変更なので PO の判断）。
  - 止め方：`amtool silence add alertname=RecoveryCheckStale --duration=PERIOD --comment=REASON`
- IP・URL の秘密・鍵のパス・webhook を書かない（公開リポジトリ）。

4-12. `monitoring/tokens.yml`:
- `thresholds:` の中、時計ずれの段（:97-98）の後に、空行と次の段を足す:

```yaml
  # 復旧後の点検係（alert_rules.yml: recovery_check_alerts）
  recovery_check_stale_sec: 300  # RecoveryCheckStale: time() - salesanchor_recovery_check_last_poll_timestamp_seconds > 300
```

- `for_durations:` の最後（:130 `clock_sync_stopped` の後）に足す:

```yaml
  recovery_check_stale: "5m"   # RecoveryCheckStale
```

- 作業の前に `sed -n '95,101p;125,132p' monitoring/tokens.yml` で場所を確かめ、行番号がずれていれば段の並びで合わせる。

4-13. 本番配置の台本 3 本（リポジトリの外。commit しない）を Write で作る。担当は実行しない（実行は Opus が PO の同意票を受けて行う）。置き場は `/tmp/CC報告ファイル/outage-bin2/deploy/`。
- 共通:
  - 形は便1 の台本 `/tmp/CC報告ファイル/outage-bin1/deploy/deploy-bin1.sh` に揃える（担当は最初に全文を読む）。
    - 接続先（prod2・利用者 `ubuntu`・鍵 `~/.ssh/manual-only/id_ed25519`・IP の決め方）
    - 本店での `git fetch` と `git show "${MC}:パス"` の使い方
    - `set -euo pipefail`、`tee` で生出力を残す
  - 推測で利用者名を書かない（fail2ban に当たる）。sudo は使わない。秘密（webhook・token の値）は出さない。
  - 引数: `deploy-bin2.sh` は 1 つ（実装 PR のマージ commit の sha）。`verify-bin2.sh` は無し。`rollback-bin2.sh` は 1 つ（deploy の手順 3 で控えに付けた日付の文字列。便1 の rollback-bin1.sh と同じ形）。
  - prod2 の上のコマンドは、3 本とも `cd /opt/salesanchor-monitoring` の後に実行する。
- `deploy-bin2.sh` の手順（この順。外れたらその場で止まる）:
  1. 書き込みの確かめ: `/opt/salesanchor-monitoring`・`/opt/salesanchor-monitoring/backups`・`/opt/salesanchor-monitoring/monitoring`・`.../monitoring/prometheus`・`.../monitoring/alertmanager` に `test -w`。1 つでも書けなければ止まる。本番の `docker-compose.monitoring.yml` に `recovery-check:` の service が既にあれば止まる（`n=$(grep -c '^  recovery-check:' docker-compose.monitoring.yml || true)` が 0 でなければ。`grep -c` は 0 件のとき exit 1 になり `set -e` で止まるので、`|| true` を必ず付ける。便1 の台本と同じ）。`monitoring/recovery-check/` のディレクトリだけが残っているのは、`rollback-bin2.sh` で戻した後の置き直しなので止まらない（手順 7 で上書きする）。
  2. 本番の 4 本（`docker-compose.monitoring.yml`・`monitoring/prometheus/prometheus.yml`・`monitoring/prometheus/alert_rules.yml`・`monitoring/alertmanager/alertmanager.yml`）の sha256 が、マージ commit の 1 つ前（`"${MC}^1:パス"`）と一致することを出す。違えば止まる。
  3. 控え: `mkdir -p /opt/salesanchor-monitoring/backups/outage-bin2` の後、4 本を `cp -p` で `.bak-` に日付を付けた名前で写し、sha256 を出す。
  4. Alertmanager の silence の数と、鳴っている警報の件数・alertname の一覧を出す（便1 の手順 3 と同じ。silence が 1 以上なら止まる）。
  5. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-outage-bin2/` に、マージ commit の版の 4 本と `monitoring/recovery-check/` の 5 本を scp で送る。
  6. 同じ版のイメージで検査する。どれか落ちたら止まる。
     - `promtool check rules`（期待 "SUCCESS: 32 rules found"）
     - `amtool check-config`
     - `amtool config routes test` の 2 行（§4-10 と同じ。RecoveryCheckPassed は discord-recovery-info だけ・RecoveryCheckFailed は両方）
  7. 4 本を `install -m 644` で本番の場所に置く。`monitoring/recovery-check/`（と `tests/`）を `install -d` で作り、5 本を `install -m 644` で置く。置いた全部の sha256 がマージ commit の版と一致することを出す。
  8. `cd /opt/salesanchor-monitoring && docker compose -f docker-compose.monitoring.yml config -q`（compose の書式の検査）。落ちたら `rollback-bin2.sh` を実行するよう出力して止まる。
  9. `docker compose -f docker-compose.monitoring.yml build recovery-check` の後、`docker compose -f docker-compose.monitoring.yml run --rm --no-deps recovery-check python -c "import os; p='/data/state.json'; print('removed' if os.path.exists(p) else 'none'); os.path.exists(p) and os.remove(p)"` で前に残った状態ファイルを消し、その出力を出す（戻した後の置き直しで、止まっていないのに ✅ が出るのを防ぐ。2026-10-22 3回目の審査の R1）。その後 `up -d --no-deps recovery-check`（他のサービスは作り直さない）。
  10. Prometheus を読み直す（便1 の手順 7 と同じ `/-/reload`）。Alertmanager を作り直す（便1 の手順 8 と同じ。`/-/ready` が 200 になるまで最大 12 回・5 秒おき）。
  11. 読み取りで確かめて出す。期待との違いがあっても止まらず、全部出してから exit 1 にする。
      - Prometheus `/api/v1/targets` で job `recovery-check` の `health`（期待 up。scrape の初回まで最大 12 回・5 秒おきに読み直す）。
      - `/api/v1/rules` でルール数（期待 32）、`recovery_check_alerts` の 3 本の名前と `health`（期待 ok）、`health` が ok でないルールの数（期待 0）。
      - `/api/v1/query` で `salesanchor_recovery_check_failed` の件数（期待 10）と値の合計（期待 0）、`salesanchor_recovery_check_passed_until_timestamp_seconds`（期待 0）、`time() - salesanchor_recovery_check_last_poll_timestamp_seconds`（期待 120 未満）。
      - Alertmanager `/api/v2/status` の `config.original` に `discord-recovery-info` と `RecoveryCheckPassed` の語があるか（語の有無だけ）。silence の数（手順 4 と同じ）。
      - `docker compose -f docker-compose.monitoring.yml ps recovery-check` と `logs --tail 20 recovery-check`。
      - `docker compose -f docker-compose.monitoring.yml exec -T recovery-check python main.py --check-once` の出力と終了コード（期待: 0 と `{"responding": true, "ng": []}`）。
- `verify-bin2.sh`（G2 の本番での確かめ。設計の受け入れ基準「点検係を状態『NG』で 1 回動かす」）:
  1. 実行した時刻（日本時間）を出す。Alertmanager の `/api/v2/alerts?filter=alertname="RecoveryCheckPassed"` が 0 件であることを確かめ、1 件以上なら exit 1 で止まる（前の ✅ が鳴っている間は Alertmanager が新しく送らないため。10 分たてば消える。2026-10-22 再審査の指摘N5）。あわせて Prometheus の `salesanchor_recovery_check_passed_until_timestamp_seconds` が 0 か、今より 300 秒以上前であることを確かめ、そうでなければ exit 1 で止まる（✅ が消えた直後は、Alertmanager が送った記録を片付けるまで次の ✅ を送らない見込みがあるため。未確認。3回目の審査の R2）。
  2. 先に `docker compose -f docker-compose.monitoring.yml exec -T recovery-check python main.py --check-once` を実行し、出力と終了コードを出す。0 でなければ、印を置かずに exit 1 で止まる（本番で偽の ❌ と障害記録を出さないため。2026-10-22 設計審査の指摘4）。
  3. Alertmanager の指標 `alertmanager_notifications_total{integration="discord"}` と `alertmanager_notifications_failed_total{integration="discord"}` を出す（前の値）。札の名前は推測で書かず、`/metrics` の該当行をそのまま出して合計する（受け手ごとの札があれば受け手ごとにも出す）。
  4. `docker compose -f docker-compose.monitoring.yml exec -T recovery-check python main.py --simulate-down` で印を置く。
  5. Alertmanager の `/api/v2/alerts?filter=alertname="RecoveryCheckPassed"` を、1 件になるまで最大 60 回・10 秒おき（最大 10 分）に読む。1 件になった時刻と、印を置いてからの経過秒を出す。
  6. 1 件になった後、group_wait（30 秒）を待つため、手順 3 の指標を最大 12 回・10 秒おきに読み直す。discord の送った数の合計が前の値より増えたら止めて、前後の値と差を出す（期待: 差 1 以上・失敗の差 0。同じ時間に別の警報が送られると差が 2 以上になるので、そのときは手順 5 の時点の `/api/v2/alerts` の alertname の一覧も出す）。12 回読み直しても増えなければ、前後の値を出して exit 1。
  7. `logs --tail 20 recovery-check` を出す。
  - 10 分で 1 件にならなければ、`/api/v2/alerts` の alertname の一覧と `salesanchor_recovery_check_failed == 1` の結果を出して exit 1。
- `rollback-bin2.sh`:
  - 点検係が動いていれば、先に `docker compose -f docker-compose.monitoring.yml exec -T recovery-check python -c "import os; p='/data/state.json'; os.path.exists(p) and os.remove(p)"` で状態ファイルを消す（置き直したときに古い時刻から「点検係が止まっていた」と扱われ、止まっていないのに ✅ が出るのを防ぐ。2026-10-22 再審査の指摘N2）。動いていなければ飛ばし、その旨を出す。
  - `docker compose -f docker-compose.monitoring.yml rm -sf recovery-check` で点検係を止めて取り除く（volume は残す）。
  - 手順 3 の控えの 4 本を `install -m 644` で戻し、Prometheus を読み直し、Alertmanager を作り直す。
  - 戻した 4 本の sha256 が控えと一致すること、ルール数（期待 29）を出す。
  - `monitoring/recovery-check/` のディレクトリは消さない（削除はフックに止められる。置いたままでも compose が参照しなければ動かない）。
- 3 本とも `bash -n` が通ることを §5-9 で出す。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `python3 -c "import yaml; [print(g['name'], r['alert'], r.get('for'), r['labels']) for g in yaml.safe_load(open('monitoring/prometheus/alert_rules.yml'))['groups'] for r in g['rules']]"` を作業場所と merge-base の版（`git show "$(git merge-base origin/main HEAD):monitoring/prometheus/alert_rules.yml" > /tmp/CC報告ファイル/outage-bin2/rules-main.yml`）の両方で実行し、`diff` に通す（期待: 足された 3 行だけ）。
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 32 rules, Loki 6 rules, runbook 38 sections`。
5-3. `git diff --numstat "$(git merge-base origin/main HEAD)" -- monitoring/prometheus/alert_rules.yml monitoring/alertmanager/alertmanager.yml monitoring/prometheus/prometheus.yml docker-compose.monitoring.yml .github/workflows/monitoring-check.yml` の出力。期待: 5 本とも 2 列目（削除行数）が 0。ただし `.github/workflows/monitoring-check.yml` の「どの通知も…」のコメント行を書き換えずに次の行へ足した場合に限る。
5-4. `python3 monitoring/recovery-check/tests/test_recovery_check.py -v` の出力の最後の 3 行（期待: `Ran 14 tests` 以上・`OK`）。
5-5. わざと壊して落ちることを確かめる（Mac で。python だけで済む）:
- `recovery_check.py` の `attempt >= 4` を一時的に `attempt >= 1` に書き換えると、試験 4・5・13 が落ちる（exit 1）。確かめたら Edit で戻す（`git checkout` は使わない）。
- 戻した後に `grep -n "attempt >= " monitoring/recovery-check/recovery_check.py` の行と、試験がもう一度 `OK` になる最後の 3 行を出す。
5-6. 手順書の見出し: `grep -c '^## ' docs/runbooks/alerts.md`（期待 38）と `grep -n '^## RecoveryCheck' docs/runbooks/alerts.md`（期待 3 行）。
5-7. promtool・amtool・`docker compose config` は Mac では実行しない（Mac に promtool・amtool は無く、Docker も起動しない）。PR の CI `monitoring-check` で動く（§4-10 の追加分を含む）。担当は PR を作った後に `gh pr checks` の行のうち monitoring-check の 1 行を貼る（待たない。合否は Opus が確かめる）。
5-8. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「閾値ズレ」の行（期待: exit 0・閾値ズレ 0 行）。
5-9. `bash -n` を台本 3 本に実行した終了コード（期待 0）。3 本の全文を報告に貼る（鍵のパスと利用者名は伏せずに貼ってよい。秘密の値は台本に書かない）。
5-10. `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" docs/runbooks/alerts.md monitoring/alertmanager/alertmanager.yml monitoring/recovery-check/*.py docker-compose.monitoring.yml` の該当。期待: 新しく足した行には 0 行。既存の行が当たったら、その行を貼って新規でないことを書く。
5-11. `git diff "$(git merge-base origin/main HEAD)" --stat` が §3 のリポジトリ内の 14 ファイルであること。
5-12. `python3 -c "import ast,sys; ast.parse(open('monitoring/recovery-check/main.py').read()); ast.parse(open('monitoring/recovery-check/recovery_check.py').read()); print('ok')"` と、`grep -n "^import\|^from" monitoring/recovery-check/recovery_check.py`（期待: 標準ライブラリだけ。`prometheus_client` と `requests` が無い）。

## 6. 分岐ごとの対処

- 5-1〜5-6・5-8〜5-12 の出力が違う → 直してやり直す（記録のみで続行）。
- CI の結果は担当は待たない。落ちていたら Opus が担当に出力を渡して直させる。
  - promtool の test の落ちは試験の期待値（展開後の文字列・札）を直す。§4-7 の式・閾値・札を変えて合わせることはしない。
  - amtool の routes test の落ちは、§4-9 を自分で変えずに BLOCKED:。
- `ticket` が TIERS に無い・`runbook_url` の前半が既存と違う → BLOCKED:（§4-7）。
- `.github/workflows/monitoring-check.yml` の編集がフックに止められた → BLOCKED:（言い換えない）。
- この Mac で `colima`・`docker`・`limactl` を打たない（docs/ops/runner-commands.md:351）。
- PR の CI で Docker Hub の取得回数の制限に当たって落ちる → `quay.io` の同じ版に替えてよい（便1 カード §6 と同じ）。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 本番の本体が 2 回続けて応答しなかった後に応答すると点検が始まり、0・2・4・6 分の 4 回のうち全部 OK になった時点で ✅、4 回目も NG なら ❌（項目つき）になる。1 回だけでは始まらない。裏方だけが戻らない場合も ❌ になり、止まっていないときは ✅ も ❌ も出ない | 単体試験 1〜6・11〜14（§5-4）・壊すと落ちる（§5-5） |
| 監視の読み取りや時計が NG のとき、時刻を比べる項目を判定せず、誤った ❌ を出さない。DB が NG・API が答えないとき redis・celery を判定しない。503 の本文つきの応答は「応答あり」、本文の無い 52x は「応答なし」 | 単体試験 7〜10 |
| ✅ は Discord にだけ届き、障害記録には書かれない。❌ は Discord と障害記録の両方に届く。既存の警報の届け先は変わらない | CI の routes test 4 行（§4-10・§5-7） |
| 警報 3 本が §4-7 の完成形で入り、既存の 29 本は変わらない。札・手順書リンク・見出しの検査が通る（32 本・38 節） | §5-1・§5-2・§5-3・§5-6・CI の promtool |
| 本番で点検係が動き、指標が出て、ルールに評価の失敗が無い。1 回だけの点検で NG が 0 件 | §8（deploy-bin2.sh の手順 11。`--check-once` の終了コード 0） |
| G2: 本番で「止まっていた」状態を 1 回作ると、10 分以内に ✅ が Discord に 1 件届く | §8（verify-bin2.sh。経過秒・Discord の送信数）＋ PO が Discord で ✅ を目で確かめる |

- 時間の見込み（2026-10-22 再審査の模型 /tmp/CC報告ファイル/outage-bin2/review2/tick_sim2_fix.txt。周期を 60 秒に固定し、次の点検を now+110 にした場合。scrape 15 秒・評価 15 秒・group_wait 30 秒・HTTP の打ち切り 10 秒を含む）:
  - 復帰から Discord まで、✅ は最悪 3.17 分、❌ は最悪 9.67 分。
  - 【未確認】✅ の後、約 15 分以内にもう一度止まって戻ると、2 度目の ✅ が Discord に届かない見込みがある（Alertmanager が送った記録を片付ける時間。3回目の審査の R2）。❌ は札が違うので届く。起きたら記録して Opus が見直す。
  - 1 回分の所要が 60 秒を超える（多くの項目が同時に打ち切られる）と周期がずれ、❌ が 10 分を超えうる。次に本番が止まって戻ったときに実測し、10 分を超えたら Opus が間隔を見直す（設計「継続」）。

## 8. 本番への配置（マージの後。Opus が行う。担当はしない）

- 機体は prod2 だけ。制限付き鍵では書けないため無制限鍵を使う。無制限鍵は、PO の同意票（ADR-1033）を受けた Opus だけが使う。担当は使わない。
- 8-1. Opus が台本 3 本を読み、§4-13 と合うか確かめる。
- 8-2. Opus が PO に同意票を出す。
  - 操作1: `bash /tmp/CC報告ファイル/outage-bin2/deploy/deploy-bin2.sh マージcommitのsha`
  - 操作2: `bash /tmp/CC報告ファイル/outage-bin2/deploy/verify-bin2.sh`（Discord に ✅ が 1 件届く）
- 8-3. PO の「1」を受けて Opus が実行し、生出力を `/tmp/CC報告ファイル/outage-bin2/deploy/` に残す。自動の許可判定に止められたら、言い換えずに PO に `!` での実行を頼む（便1 と同じ）。
- 8-4. 手順 11 と verify の結果を PR にコメントで追記する。PO に Discord の ✅ を目で確かめてもらう。
- マージから配置までの間に毎日の設定ずれの見回り（日本時間 09:23）を過ぎると、MonitoringConfigDrift（warning）が 1 件鳴る（F12。4 本が対象）。Opus はこの時刻の前に配置まで終えられる時間にマージする。鳴った場合は、配置の後の次の見回りで消えることを確かめる。
- ❌ の道は本番では試さない（障害記録に偽の障害が残るため）。単体試験と CI の routes test で代える。本物で確かめられるのは次に prod1 が止まったとき。そのときは Opus が、復帰から Discord に届くまでの分を記録する（設計「継続」）。

§8 の分岐:
- 手順 1〜6 で止まる → 置かずに止まる（Opus が PO に報告）。
- 手順 7（install）が途中で落ちる → 本番の 4 本が混ざっているので、`rollback-bin2.sh` を同意票で出し直して戻す。
- 手順 9（build・up）か手順 10（読み直し・作り直し）で落ちる → `rollback-bin2.sh` を同意票で出し直して戻す（4 本は置いた後なので、そのままにしない）。
- 手順 11 の `--check-once` だけが 0 でない（他は期待どおり） → 戻さずに verify を行わない。NG の項目を見て、公開 URL や Prometheus の問い合わせの作りを直す便を Opus が切る（点検係が ❌ を出すのは、次に本番が止まって戻ったときだけ。それまでに直す）。
- 手順 8 で compose の検査が落ちる、または手順 11 でルールの `health` が ok でない・`/-/ready` が 200 にならない・job が up にならない → `rollback-bin2.sh` を同意票で出し直して戻す。
- 手順 11 のそれ以外の期待外れ（指標の件数 10・合計 0・passed_until 0・最終点検の古さ・config.original の語・silence の数） → 戻さずに verify を行わず、Opus が PO に報告する（既存の監視は動いているため）。
- verify の手順 1 か 2 で止まる → 印を置いていないので何も変わっていない。理由を見て Opus が判断する。
- verify で 10 分以内に ✅ にならない → 出力の `salesanchor_recovery_check_failed == 1` の項目を見る。公開 URL が 200 にならない（例: Cloudflare に止められる）なら、戻さずに点検係の作りを直す便を Opus が切る（点検係が ❌ を出すだけで、既存の監視には影響しないため）。理由が分からなければ PO に報告する。

## 9. 戻し方

- prod2: `rollback-bin2.sh`（§4-13。点検係を止め、控えの 4 本を戻し、Prometheus を読み直し、Alertmanager を作り直す）。無制限鍵を使うので、同意票を受けて Opus が実行する。
- repo: この PR の revert を main にマージする。
- 戻すと、復旧後の ✅/❌ が届かない状態に戻る（10/22 以前と同じ）。便1 の時計の警報と抑止は残る。

## 10. PR

- 作業場所:
  - このカードの PR が main にマージされたことを確かめる: `gh pr list --state merged --head release/outage-bin2-card --limit 1 --json number,state`。合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:。
  - その後 `cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/outage-recovery-check --claude`（origin/main 起点）を実行する。
  - 出力はパイプに通さない。最後に「Input must be provided」と出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-22 実測）。`cannot lock ref` で失敗したら、同じコマンドを 1 回だけやり直す（2026-10-22 実測。他の作業の fetch と重なったため）。
  - 作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-outage-recovery-check` と `git worktree list` の両方で実在を確かめる。`ls docs/handoff/outage-recovery-watch/card-bin2.md` でこのカードの実在を確かめる。
  - 以後の作業はすべてその作業場所に `cd` してから行う。
- push は `git push -u origin release/outage-recovery-check`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/outage-recovery-check -1 --oneline` で実在を確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。
  - 先に Write ツールで本文ファイル `/tmp/CC報告ファイル/outage-bin2/pr-body.md` を作り、`--body-file` で渡す（executor-checklist.md §0）。
  - 作成後に `gh pr list --head release/outage-recovery-check --limit 1 --json number,isDraft` で 1 件・isDraft が false を確かめる。
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
- PR は ready で作る（`--draft` を付けない）。base は main。マージは Opus の審査と GO 記録の後に限る（担当はマージしない）。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` には次を書く:
  - recon・設計・このカード（docs/handoff/outage-recovery-watch/ の 3 本）
  - `対象ADR:` は ADR-1012, ADR-080
  - `設計仕様書（あるべき姿）:` は docs/specs/ai-ops-247/README.md
  - `区分:` は A（新機能。PO 承認は設計の PO 承認 2026-10-22「1」）
  - `Opus 審査記録:` は「コード審査はこれから」
  - `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし。`削除するファイル:` には、行を書き換えた既存ファイルを全部書く（`validate-pr-body.sh` の規則）
- 本文に、§8 の本番配置はマージ後に Opus が同意票を受けて行うこと、台本はリポジトリの外にあり commit しないことを書く。
- 本文に IP・URL の秘密・鍵のパス・利用者名・認証ファイルの中身・メールアドレスを書かない。実在しないパスをバッククォートで書かない。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（2 分以上かかる。Bash の timeout は 240000 以下にする）。

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-12 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う。例外は §4-13 の台本の中の待ちだけ。台本は担当が実行しない。Mac の上では sleep しない）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
