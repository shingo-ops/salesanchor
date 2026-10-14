# 段階1 報知器 — 便割りの設計

> この文書は何か：AI保守運用24時間化（ADR-1012）の段階1「報知器」を、1便1目的の実装便に分けた設計です。親の設計は [design.md](design.md) §5 段階1（:89-101）。各便の作業指示書（カード）は、この文書を元に便ごとに作ります。

- 親設計: docs/handoff/ai-ops-247/design.md §5 段階1・受け入れ基準（:182-184）
- 現状調査: docs/handoff/ai-ops-247/recon.md（段階1 の追加調査は下の生出力）
- KGI: docs/specs/ai-ops-247/kgi.md（KGI 1 報知器が人より先に鳴る 100%、KGI 2 鳴った通知の 90% 以上が要対応）
- 対象ADR: ADR-1012（本テーマ・Proposed）、ADR-135（main マージ＝本番投入可）、ADR-136（危険 PR の GO）、ADR-1003（GO 委任）
- 状態: 設計審査済み。Fable 審査 1 回目 REVISE（2026-10-14・HIGH 3・MEDIUM 6・LOW 6）を反映し、2 回目 APPROVE（必須の文面修正 3 点を反映済み）実装は 2026-10-14 の PO の一任（段階1 をマージ・デプロイまで）に基づき、便ごとにカード → Sonnet 実装 → Fable 審査 → GO → 反映 → 測定 の順に 1 便ずつ進める
- 事実の生出力: /tmp/CC報告ファイル/ai-ops-stage1-recon2/facts.md・/tmp/CC報告ファイル/ai-ops-stage1-recon3/facts.md（2026-10-14 取得。本番は読み取りのみ）

## 1. 前提の事実（2026-10-14・origin/main 基準）

| # | 事実 | 出典 |
|---|---|---|
| S1 | Prometheus のルールは 15 本。本番で全て health=ok（評価エラー 0）。札（page/auto/ticket）のラベルと手順書リンクは 0 本 | `monitoring/prometheus/alert_rules.yml:8-157`・本番 `/api/v1/rules` |
| S2 | 計器の無いルールは 4 本。`pg_stat_activity_count`・`pg_up`・`nginx_http_requests_total` の系列数が本番で 0 | `monitoring/prometheus/alert_rules.yml:50`・`:60`・`:70`・`:80`、本番 `count({__name__=...})` |
| S3 | その計器を出す postgres-exporter・nginx-exporter・redis-exporter は prod1 のメモリ逼迫のため `profiles: heavy-exporters` で眠らせてある（2026-07-18 決定） | `docker-compose.exporters.yml:30-83`・`docs/handoff/infra-exporters-persist/design.md:14-19` |
| S4 | prod1 の空きメモリ（available）は約 1,050MB・swap 使用 約 520MB | 本番 `free -m`（recon2 B9・recon3 C8） |
| S5 | Loki のルールは repo に 6 本（1 ファイル）。本番は 4 本で評価中（評価失敗 0・最終評価 2026-10-14）。差は、repo のみ = Discord の 2 本と postgres 版の `BackendErrorSpike`、本番のみ = `DatabaseError`（中身は repo の postgres 版と同じ条件） | `monitoring/loki/rules/jarvis/alerts.yml:8-77`・本番 Loki の ruler 指標・本番ファイルとの diff |
| S6 | repo の Loki ルールは同じ名前のルール `BackendErrorSpike` が 2 本（:32・:69）、同じ名前のグループ `error_anomaly` が 2 つ（:29・:66） | `monitoring/loki/rules/jarvis/alerts.yml` |
| S7 | Loki のルール API が 0 本に見えた（実際は HTTP 400 のエラー応答）のは、`auth_enabled: false` のため問い合わせが `fake` という名前の置き場を探して失敗したため（HTTP 400 `/loki/rules/fake` 無し）。実際の評価は `jarvis` の置き場で動いている | `monitoring/loki/loki-config.yaml:2`・`:32-36`、本番 API 応答 |
| S8 | Grafana のアラートルールは本番で 0 件。repo の `monitoring/grafana/provisioning/alerting/alerting.yml` は本番では 2026-07-19 に退避済み（中身は repo と同一）。通知は Alertmanager → Discord の 1 本だけが働いている | 本番 Grafana API・本番 `retired/alerting.yml.disabled-202607191506`・`monitoring/alertmanager/alertmanager.yml` |
| S9 | Uptime Kuma の本番の見張りは 4 件（監視基盤と prod1 の node-exporter）。既存 4 件はすべて Kuma から Discord への直通通知（既定の通知先）が付いている。利用者が使う App・API・LP の見張りは 0 件。repo の定義 7 件は本番に無い | 本番 kuma.db（読み取り専用・recon2 B8）・`monitoring/uptime-kuma-monitors.yml:1-51` |
| S10 | repo 定義 7 件のうち PostgreSQL・Redis は `localhost` 宛てだが DB は prod1、Kuma は prod2 にあり届かない。Meta Graph API は応答するが 400（旧 script は 400 を正常扱いにしていた）、Firebase は名前解決できない | `monitoring/uptime-kuma-monitors.yml`・prod2 からの GET 結果（recon3 C9） |
| S11 | Kuma（1.23.16）は TLS を持つ見張りにだけ `monitor_cert_days_remaining`・`monitor_cert_is_valid` を出す。今は 0 系列 | Kuma 公式ソース `server/prometheus.js`（1.23.16 タグ。recon の生出力には無い＝【未確認・便2 の合格基準で検証】）・本番 Prometheus（今 0 系列） |
| S12 | Kuma への見張り登録は、本番で uptime-kuma-api（1.23 系固定の理由）を使った実績がある | `docker-compose.monitoring.yml:218`・prod2 の作業用 script |
| S13 | `/api/health` は DB に `SELECT 1` し、失敗時 503 を返す | `backend/app/routers/health.py:16-38` |
| S14 | 監視設定を prod2 に配る自動の仕組みは無い。prod2 の配置先は git 管理外で、過去は「控えを取る → ファイルを置く → main と diff 0 → 再読込」の手作業 | `docs/handoff/server-resource-optimization/design-20261001.md:130`・`:224-235`・`docs/runbooks/monitoring-vps-migration.md:251-270` |
| S15 | prod2 に GitHub Actions の self-hosted runner（名前 `salesanchor-vps`）が常駐し、`[self-hosted, salesanchor-vps]` の workflow が 3 本ある | prod2 `actions-runner/.runner`・`.github/workflows/qa-smoke.yml:58` ほか |
| S16 | CI に promtool / amtool によるルール検査は無い。monitoring-check.yml は tokens.yml の閾値との一致などを見る | `.github/workflows/monitoring-check.yml:25-57` |
| S17 | 本番の Prometheus コンテナに `promtool`（3.11.3）、Alertmanager コンテナに `amtool`（0.28.1）が入っている。Loki のルール（LogQL）は promtool で検査できない | 本番 `which`（recon3 C12） |
| S18 | 直近 30 日の発火: BackendHighLatency 447 回（計 16,250 分）、F2CleanupStale 4 回（計 27,420 分）、HighDiskUsage 3 回、HighMemoryUsage 33 回、ServiceDown 13 回 | 本番 Prometheus `ALERTS`（5 分刻み・recon2 B10） |
| S19 | バックアップは prod1 の cron（毎日 3:00 pg_dump・3:30 S3 転送）。成功の時刻を Prometheus に出す仕組みは無い。f2-cleanup は node-exporter の textfile に時刻を書く方式で出している | `scripts/backup.sh:3-58`・`scripts/backup_to_s3.sh`・`scripts/f2-cleanup.sh:9,61-67`。なお `scripts/backup_to_s3.sh:56-70` は失敗時に Discord へ直接通知する（Alertmanager を通らない 2 本目の経路） |
| S20 | celery の失敗・beat の停止・待ち行列の長さを示す指標は 0 個。backend の指標は HTTP の 4 種だけ。celery のシグナル（task_failure 等）の利用も 0 | `backend/app/metrics.py`・`backend/app/celery_app.py:60-178`・recon3 C6 |
| S21 | `llm_usage_events` に成否の列は無い（応答を受けたときだけ書く） | `migrations/20260930_150000_create_llm_usage_events.sql:26-53`・`backend/app/services/tcg_extraction_record_svc.py:213` |
| S22 | 証明書は 5 ドメイン。最短の期限は 2026-11-22（certbot が 12 時間ごとに更新を試みる） | prod1 certbot コンテナ内 `openssl x509 -enddate`・`docker-compose.yml:42-47` |
| S23 | prod2 の Loki はメモリ上限 256MB に対し 183〜254MB を使用。OOM による停止は記録なし | 本番 `docker stats`・`docker inspect`（recon2 B9・recon3 C10） |
| S24 | Loki は設定の置き場を定期に読み直している（`loki_ruler_sync_rules_total{reason="periodic"}` が増えている） | 本番 Loki 指標（recon2 B3b） |

## 2. 便割り（1便1目的・上から順に 1 便ずつ反映して測る）

| 便 | 目的 | 主に触るもの | 危険便 | 反映先 |
|---|---|---|---|---|
| 1 | repo と本番の「鳴らす条件」を一致させる（Loki・Grafana） | Loki ルール 1 ファイル・Grafana の alerting.yml 削除 | いいえ | prod2（手作業の配置） |
| 2 | 利用者が使う画面の見張りを本物にする（Kuma で App・API・LP を見る／計器の無い 4 本を置き換える／証明書の期限） | Kuma 定義・`monitoring/scripts/` の登録 script・Prometheus ルール・`monitoring/tokens.yml`・`monitoring/scripts/validate_tokens.py` | いいえ | prod2 |
| 3 | 全ルールに札と手順書リンクを付け、CI で検査する | Prometheus・Loki ルール・手順書 1 ファイル・検査 script・monitoring-check.yml | いいえ | prod2 |
| 4 | 雑音を減らす（BackendHighLatency の条件の決め直し） | Prometheus ルール 1 本 | いいえ | prod2 |
| 5 | celery の失敗・beat の停止・待ち行列の長さの見張り | backend（指標）・Prometheus ルール | いいえ | prod1（通常 deploy）＋ prod2 |
| 6 | バックアップの鮮度の見張り（あわせて動かない `scripts/setup_uptime_kuma.sh` を削除） | `scripts/backup.sh`・`scripts/backup_to_s3.sh`・`scripts/setup_uptime_kuma.sh`（削除）・Prometheus ルール | **はい**（本番 scripts） | prod1 ＋ prod2 |
| 7 | 本番の設定と repo の一致を毎日確かめ、ずれたら鳴らす | workflow（prod2 の self-hosted runner）・Prometheus ルール | いいえ | GitHub Actions ＋ prod2 |

危険便の判定は `scripts/check-process-artifacts.js` の DANGEROUS_PATTERNS（`migrations/`・`scripts/`・`.github/workflows/deploy.yml` 等）に従う。`scripts/` 配下を触る・消すのは便6 だけにする。

順番の理由: 便1 で正本を揃えないと、後の便の「本番と diff 0」の確認ができない。便2 は KGI 1（利用者に影響する不具合を先に知る）に一番効く（S9: 今は利用者向けの見張りが 0 件）。便3 は便2 で入れ替わったルールに札を付けるため後。便7 は全部の配置が終わってから入れないと、途中で鳴り続ける。

### 配置の実行者と鍵（全便共通）

- prod2（便1〜4・6・7）と prod1（便6）の配置は、制限付き鍵では書けない（recon2 facts.md: 制限付き鍵では配置先のファイルを読めないことを実測）。
- この段階1 は、PO の 2026-10-14 の明示許可（原文:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」）の範囲で、Sonnet が無制限鍵を使って配置する。各便のカードに PO の原文を写し、本番で行う操作を番号付きで限定する（カードに無い操作はしない）。
- これは docs/specs/ai-ops-247/kgi.md「変えない約束: VPS へは制限付き鍵だけ」の例外として kgi.md に記録した（段階1 の完了で失効）。CLAUDE.md「変更を伴う作業は作業ごとに PO の GO が必要（GO 原文を依頼文と PR に転記）」に従い、各便のカードと PR 本文に PO の原文と実行した操作の番号を書く。
- 担当が無制限鍵の操作で止まった場合は、Opus がカードと同じ手順を実行する。
- この許可は段階1 の便に限る。段階1 の後に配置が要る場合は、便ごとに 1 本の script にして PO が `!` で 1 回実行する型（段階0 と同じ）に戻す。
- 本番での出力は件数・sha256 の一致／不一致・指標の値だけを残し、鍵・IP・URL・webhook を報告や PR に書かない。
- 控えはルールの置き場の外（prod2 の `/opt/salesanchor-monitoring/backups/ai-ops-stage1/`）に置く。理由: 便1 で控えを Loki のルールの置き場に置いたところ、Loki が控えもルールとして読み、約 3 分間 古い 4 本が重ねて評価された（2026-10-14 実測・PR #4276 の配置記録）。
- 認証ファイルは中身を表示しない（cat・head・sed・grep の対象にしない）。確かめるのは `wc -c`・`wc -l` だけ。理由: 便2 の事実確認で、伏せ字の書式が合わず Kuma の管理者パスワードが端末出力に 1 回出た（2026-10-14・PO に報告済み）。
- 便6 の prod1 側は、cron が読む作業木が deploy で main の版に更新されるかをカードで実測してから配置方法を決める（`.github/workflows/deploy.yml` が `scripts/backup.sh` を呼ぶ箇所も同時に確認する）。

### 便1 鳴らす条件の一致

- Loki ルール（S5・S6）: repo の postgres 版を本番と同じ名前 `DatabaseError` にし、1 つ目の `error_anomaly` グループに入れる（グループ名の重複を消す）。Discord の 2 本は残す。結果、repo は「本番の 4 本 ＋ Discord の 2 本」の 6 本になる。
- 配置前に、Discord の 2 本の条件式を本番 Loki で直近 7 日分問い合わせ、閾値を超えた回数を記録する（入れた途端に鳴り続けないかの確認。閾値を超えた 5 分刻みの点が 1 日平均 12 点（1 時間分）を超えるなら、配置を止めて設計に戻す）。
- Grafana（S8）: repo の `monitoring/grafana/provisioning/alerting/alerting.yml` を削除し、本番（退避済み）に合わせる。通知の経路は Alertmanager の 1 本（design.md §3 の正本表どおり）。
- 本番への配置（S14 の手順）: 控え（`.bak-20261014-<PR番号>`）→ ファイルを置く → main と diff 0 → Loki は設定の置き場を定期に読み直すので再起動しない（S24）。5 分待っても Loki の ruler 指標が 6 本にならなければ `docker compose restart loki`。
- 合格: 本番 Loki の ruler 指標で `jarvis` のルールが 6 本・評価失敗 0。本番の Loki ルールファイルと main の sha256 が一致。

### 便2 利用者向けの見張り

- Kuma の正本（`monitoring/uptime-kuma-monitors.yml`）を本番の実物に合わせて書き直す: 今の 4 件（監視基盤）＋ App・API（`/api/health`）・LP の 3 件（https）。PostgreSQL・Redis・Meta Graph API・Firebase は消す（S10: 届かない・名前解決できない）。
- 正本 yml に監視基盤の 4 件を書き足すとき、IP を新たに直書きしない（公開リポジトリ。変数か伏せた書き方にする）。
- 登録は新規の monitoring/scripts/register_kuma_monitors.py（既存の `monitoring/scripts/validate_tokens.py` と同じ置き場。`scripts/` 配下には置かない）の 1 本で行う。uptime-kuma-api を使い、名前が同じ見張りは作らない（何度実行しても同じ結果）。正本の yml だけを読む。既存の `scripts/setup_uptime_kuma.sh` は Kuma 1.23 に無い REST の口を叩くもので動かない。削除は危険便の便6 で行う。
- 新規 3 件には Kuma の通知先を付けない（`notificationIDList` を空にし、既定の通知先の自動付与もしない）。通知は `KumaMonitorDown` → Alertmanager → Discord の 1 本だけ（ADR-1012・design.md §3）。既存 4 件の Kuma 直通通知は今は触らない（U5）。
- Prometheus ルールを足す: `KumaMonitorDown`（`monitor_status == 0` が 2 分）、`CertExpiringSoon`（`monitor_cert_days_remaining < 14`）、`CertInvalid`（`monitor_cert_is_valid == 0`）。
- 4 本を消すとき、`monitoring/tokens.yml` の閾値・for のトークンと `monitoring/scripts/validate_tokens.py` の検査パターンを同じ PR で消す。足すルールの閾値は `monitoring/tokens.yml` に足す。
- 計器の無い 4 本の扱い（design.md 段階1-1「exporter を入れるか、既にある指標で書き直すか」）: **既にある指標と Kuma で置き換え、4 本は消す**。理由: prod1 は空きが約 1,050MB で swap を使っている（S4）。exporter 3 つは 2026-07 にメモリを理由に止めたもの（S3）。置き換え先:
  - PostgresDown → Kuma の API 見張り（`/api/health` は DB が落ちると 503・S13）＋ `KumaMonitorDown`
  - High502Rate・HighErrorRate（nginx の 5xx）→ Kuma の App・API 見張り（nginx の先が落ちると失敗）＋既存の `BackendHighErrorRate`（backend の 5xx）
  - HighDbConnections → 置き換え先なし。今も計器が無く一度も働いていない（S2）。DB 接続数の見張りは、prod1 のメモリに余裕ができたときに postgres-exporter と合わせて戻す（未解決事項 U1 に記録）
- 合格: 本番 Kuma の見張り 7 件が正本と一致。Prometheus で `monitor_status` 7 系列・`monitor_cert_days_remaining` 3 系列。ルールが使う全指標の系列数が 1 以上（`absent()` 該当 0 本）。本番 kuma.db の通知の紐付け（`monitor_notification`）に新規 3 件の行が 0（読み取りの SELECT）。

### 便3 札と手順書と CI 検査

- 全ルールにラベル `tier`（`page`／`auto`／`ticket`）と注記 `runbook_url` を付ける。手順書は新規の docs/runbooks/alerts.md の 1 ファイル（ルールごとに見出し 1 つ。何が起きているか・最初に見るもの・直し方・止め方）。
- 札の割り当て（段階1 時点。段階3 で応急処置ができたものは `auto` に移す。今は `auto` に当たる処置が無い）:

| ルール | 札 | 理由 |
|---|---|---|
| ServiceDown・KumaMonitorDown・CriticalDiskUsage・BackendHighErrorRate・BackendErrorSpike・DatabaseError・BruteForceAttempt・DiscordGatewayReconnectFailure・CertInvalid | page | 利用者に今影響が出ている／出る直前 |
| HighCpuUsage・HighMemoryUsage・HighDiskUsage・BackendWorkerSaturated・BackendSseConnectionsHigh・BackendHighLatency・SustainedAuthFailure・DiscordDmWriterError・F2CleanupStale・F2CleanupAbsent・CertExpiringSoon | ticket | 急がないが放置すると悪化する。BackendHighLatency は便4 で条件を直すまで ticket |

- 検査 script（新規の monitoring/scripts/check_alert_rules.py。既存の `monitoring/scripts/validate_tokens.py` と同じ置き場）: 全ルールに `tier` があり値が 3 種のどれか／`runbook_url` が手順書の実在する見出しを指す／ルール名が Prometheus・Loki を通して重複しない／1 ファイル内でグループ名が重複しない。
- CI（`.github/workflows/monitoring-check.yml`）に足す: 上の script、Prometheus ルールに `promtool check rules` と `promtool test rules`（ルールごとの単体試験。擬似の時系列で鳴ることを確かめる）、`amtool check-config`。promtool・amtool は本番と同じ版のイメージから使う（S17）。`amtool check-config` が `webhook_url_file` の実在を見るかは【未確認】。CI で落ちる場合はダミーのファイルを置く手順をカードに書く。
- Loki のルール（LogQL）は promtool で検査できない（S17）。Loki は同じ版のイメージにある構文検査の道具を使う（同梱の有無は【未確認】。便3 のカードで確かめる）。無ければ、本番配置後の ruler 指標で評価失敗 0 を確かめる。
- 札（`tier`）は段階1 では Alertmanager の通知の経路を変えない（`monitoring/alertmanager/alertmanager.yml` は group_by だけ）。Discord に届く通知の数は札では変わらない。
- 合格: CI で検査が通る。わざと札を外した版で検査が落ちる（担当が手元で 1 回確かめて報告）。本番に配置後、`/api/v1/rules` の全ルールに `tier` が付いている。

### 便4 雑音を減らす

- BackendHighLatency（S18: 30 日で 447 回）の条件を、本番の直近 14 日分の P99 の実測から決め直す。候補の条件ごとに「14 日で何回鳴ったか」と「そのとき 5xx・Kuma の失敗が同時にあったか」を出し、利用者への影響と重なる回だけが残る条件を選ぶ。数値はこの便のカードで実測してから書く（今は書かない）。
- F2CleanupStale は条件を変えない。27,420 分鳴っていたのは掃除が実際に成功していなかったためで（最終成功 2026-10-11）、通知としては正しい。便3 で `ticket` にして手順書を付けることで扱いを決める。
- 便4 で直すのは 1 本だけ（変更は一度に 1 つ）。2 番目にうるさい HighMemoryUsage（30 日で 33 回）と ServiceDown（13 回）は、便4 の結果を見て次に判断する（U6）。
- 合格: 新しい条件で直近 14 日を数え直した鳴る回数が、同じ数え方の変更前の回数の 1/10 以下。かつ 5xx または Kuma の失敗と同時刻だった回を 1 件も落としていない（落とした回数 0）。

### 便5 celery と beat と待ち行列

- 指標の出し口は backend の `/metrics` の 1 か所（Prometheus が既に読んでいる口・S20）。親設計の pushgateway から変える（§3）。
  - beat の停止: 1 分ごとの軽いタスクが Redis に「最後に動いた時刻」を書き、backend が読んで `celery_beat_last_run_timestamp` として出す。worker の停止・詰まりも同じタスクで分かる（beat が動いても worker が拾わなければ時刻は進まない）。ルール名は `CeleryHeartbeatStale`。手順書に切り分け（beat コンテナの状態 → worker が処理中のタスク数）を書く。
  - このタスクは他のタスクと同じ既定キュー（worker は同時 2 本・`docker-compose.yml:209`）に並ぶため、長いタスクがあると遅れて誤報になる。閾値は本番の直近 14 日の最長タスク時間を実測してからカードで決める（今は書かない）。
  - celery の失敗: worker の `task_failure` で Redis の数を 1 増やし、backend が `celery_task_failures_total` として出す。
  - 待ち行列: backend が Redis の既定キューの長さを読み `celery_queue_length` として出す。
- Gemini の失敗率: `llm_usage_events` に成否が無い（S21）ため、この便のカードで、失敗がログにどの文言で出ているかを実測し、Loki ルールで数えられるかを確かめてから入れる。数えられない場合は段階1 から外し、未解決事項 U2 に残す。
- 合格: pytest で各指標が出る。反映後、本番 Prometheus で 3 つの指標の系列が 1 以上。反映後 24 時間の beat の時刻の更新間隔の最大値が閾値未満。

### 便6 バックアップの鮮度

- `scripts/backup.sh` と `scripts/backup_to_s3.sh` の成功時に、f2-cleanup と同じ方式で node-exporter の textfile に成功時刻を書く（S19）。ルール `BackupStale`（26 時間以上更新なし・ticket。利用者に今の影響は無いため。手順書に「翌営業日までに復旧」の期限を書く）。
- `scripts/backup.sh` は `set -euo pipefail`（:12）で、デプロイからも呼ばれる。textfile の書き込みが失敗しても exit 0 にする（`scripts/f2-cleanup.sh:61-67` と同じ `|| return` の書き方）。バックアップとデプロイを落とさない。
- `scripts/backup_to_s3.sh:56-70` の Discord 直通の失敗通知は残す（U5）。
- 動かない `scripts/setup_uptime_kuma.sh` を削除する（参照元を grep で確かめてから。便2 から移した）。
- 本番 scripts を触るため危険便（ADR-135・ADR-136）。GO は委任の範囲で Opus が発行する（DROP を含む migration・データの大量 DELETE・secrets の変更を含まない。script 1 本の git rm は ADR-1003 の例外に含まれない）。
- 合格: 翌日 3:00 の実行後に本番 Prometheus で 2 つの時刻の系列が出て、26 時間より新しい。

### 便7 本番の設定と repo の一致の見張り

- 安全の条件（リポジトリは公開）: トリガーは `schedule` と `workflow_dispatch` だけ（`pull_request`・`push` は付けない）。checkout は `ref: main` 固定。比較対象から secrets・`.env` 類を除く。ログには件数とファイル名だけを出す（中身と sha の全文は出さない）。pushgateway へは prod2 の中から送る。runner の利用者が配置先を読めるかは【未確認】、カードで確かめる。
- prod2 の self-hosted runner（S15）で毎日 1 回動く workflow が、本番の配置先の監視設定（Prometheus・Loki・Alertmanager のルールと設定、compose）と main の sha256 を比べ、ずれた件数を prod2 の pushgateway に送る。ルール `MonitoringConfigDrift`（ずれ 1 件以上・ticket）と、workflow 自体が止まったときの `absent()` ルール。
- ダッシュボード JSON（本番と repo で 8 本ずれている）は対象外（鳴らす条件ではないため。未解決事項 U3）。
- 合格: わざと 1 ファイルずらした状態で 1 回鳴ることを確かめ、戻す。

## 3. 親設計からの変更点と理由

| 親設計（design.md） | この設計 | 理由 |
|---|---|---|
| 擬似の故障は手元の docker compose で起こす（:184） | Prometheus のルールが鳴るかは `promtool test rules`（擬似の時系列を与える単体試験）を CI で毎回行う。Loki のルールは構文検査と、本番で擬似のログ 1 行を流して 1 回鳴らす。本番の経路は Alertmanager の擬似アラート 1 件で確かめる | 手元で監視一式と本体を同時に起動するより、同じことが毎回の CI で決まった結果で確かめられる。指標を出す側（便5・便6）は pytest と本番の系列で確かめる |
| 計器の無いルールは exporter か書き直しを段階0 の空きメモリで決める（:91） | 書き直し（Kuma と既存指標）。HighDbConnections は戻す時期を未解決に残す | S3・S4 |
| beat の最後に動いた時刻を pushgateway に送る（:92） | backend の `/metrics`（Redis 経由） | backend の口は Prometheus が既に読んでいる。pushgateway だと prod1 から prod2 への送り口と nginx の許可の変更が要る |
| Gemini の失敗率を足す（:92） | 便5 で数えられるかを実測してから。数えられなければ外す | S21 |

## 4. 弊害と対処

- 見張りを増やすと通知も増える → 便2 で足す見張りは 3 件だけ。便1 の Discord 2 本は配置前に 7 日分の鳴る回数を数える。便4 で一番うるさい 1 本を直す。
- 通知の経路が 2 本になる恐れ → 便2 の新規の Kuma 見張りには直通通知を付けない。既存の直通通知（Kuma 4 件・`scripts/backup_to_s3.sh`）は U5 に記録し、段階1 では増やさない。
- Loki のメモリが上限に近い（S23）→ 便1 で足すのはルール 2 本だけ。配置後 1 時間、Loki のメモリと再起動回数を記録する。
- 本番の配置が手作業 → どの便も「控え → 置く → main と diff 0 → 読み直し → 指標で確認」の同じ手順をカードに書く。便7 でずれを機械で見つける。

## 5. 戻し方

- 便1〜4・7: prod2 の控え（`.bak-20261014-<PR番号>`）を戻して読み直す。repo は revert の PR。
- 便7: workflow を消した後、pushgateway に残った該当の job を消す（残すと古い値が出続ける）。
- 便2 の Kuma: 足した 3 件を Kuma から消す（script の削除の動きは作らない。手順書に UI での消し方を書く）。
- 便5: revert の PR を main にマージして deploy。指標が消えるだけで本体の動きは変わらない。
- 便6: revert の PR。バックアップ本体の処理は変えない（成功後に 1 行書くだけ）。

## 6. 受け入れ基準（段階1 全体）

| 基準 | 検証方法 |
|------|---------|
| 本番の全ルールが計器を持つ（`absent()` で 0 本） | 便2 反映後、全ルールの指標について本番 Prometheus で系列数を出し、0 のものが 0 本であることを記録 |
| 全ルールに札と手順書リンクがある（欠け 0 本） | 便3 の検査 script が CI で通る |
| 足した見張りが擬似の条件で鳴る | Prometheus: `promtool test rules` が CI で通る。Loki: 本番で擬似のログ 1 行で 1 回鳴る。経路: Alertmanager の擬似アラート 1 件が Discord に届く |
| 利用者向けの App・API・LP が見張られている | 本番 Prometheus で `monitor_status` の 3 系列が 1（UP） |
| repo と本番の鳴らす条件が一致し、ずれたら鳴る | 便7 のわざとずらす試験 |
| BackendHighLatency の鳴る回数が 1/10 以下・影響と重なる回の取りこぼし 0 | 便4 の変更前後の 14 日の回数 |
| 新しく足した見張りが Discord へ直通で通知しない | 便2 の kuma.db の通知の紐付けで新規 3 件が 0 行 |

## 7. 未解決事項

- U1: DB 接続数の見張り（HighDbConnections）を戻す時期。prod1 のメモリに余裕ができたら postgres-exporter と合わせて戻す。
- U2: Gemini の失敗率（便5 のカードで実測して判断）。
- U3: ダッシュボード JSON 8 本と `generate-nav.js` の本番と repo のずれ（鳴らす条件ではないため段階1 の対象外）。
- U4: 監視設定を prod2 に自動で配る仕組み（今は手作業。便7 はずれを見つけるだけ）。
- U5: Alertmanager を通らない直通通知（Kuma の既存 4 件・`scripts/backup_to_s3.sh:56-70`）を Alertmanager へ寄せるか（段階2 で決める）。
- U6: HighMemoryUsage・ServiceDown の雑音（便4 の結果を見て判断）。
- U7: 証明書の見張りは App・API・LP の 3 ドメインだけ。残りの 2 ドメイン（監視画面・Legacy）の期限の見張り（Legacy は削除禁止・PO 確認が要る）。
- U8: Discord のコンテナのログが Loki に 1 件も無い（便1 の事前測定・2026-10-14）。Loki の Discord の 2 本（DiscordGatewayReconnectFailure・DiscordDmWriterError）は鳴らないが、壊れていても気づけない。ログの集め方（promtail の対象）を直すかを段階2 の前に決める。

## 8. 外部・過去事例の参照と我々への応用

- 親設計 docs/handoff/ai-ops-247/design.md §7 の事例を引き継ぐ。段階1 に直接効くのは事例3（Google SRE book 第 6 章「Every page should be actionable」）。応用: 札 page/ticket の割り当て（便3）、雑音の多い 1 本の条件の決め直し（便4）、新しい見張りの直通通知を付けず経路を 1 本に保つ（便2）。
- 過去事例（社内）: 2026-07 に prod1 のメモリ不足で exporter 3 つを止めた（S3）。応用: 計器の無い 4 本は exporter を戻さず、Kuma と既存の指標で置き換える（便2）。
- 段階1 のために新しく外部事例は調べていない。理由: 段階1 は既存の部品（Prometheus・Loki・Alertmanager・Kuma）の設定を直す作業で、成否は本番の指標と KGI の実測で判定するため。

## 維持の仕組み

- 守り手: .github/workflows/monitoring-check.yml（便3 で検査を足す。便3 の反映までは人手で守る＝便ごとの Fable 審査）
- 担当: 監視の正本は repo（monitoring/）。変更は便ごとのカード → PR → 審査 → 配置の順で、手作業で本番だけを変えない。
- 仕組み: 便3 の検査 script と CI（札・手順書リンク・名前の重複・promtool）で、ルールを足すたびに機械が欠けを止める。便7 の毎日の照合で、本番と repo のずれを鳴らす。
- 見直し: 便4 の後、雑音の次の候補（U6）を判断する。未解決 U1〜U8 は段階2 の設計の前に読み直す。
