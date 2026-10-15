# 見張りのルール別 手順書

この文書は何か：見張り（アラート）のルールごとの手順書です。ルールの正本は `monitoring/prometheus/alert_rules.yml`（Prometheus 14 本）と `monitoring/loki/rules/jarvis/alerts.yml`（Loki 6 本）です。各ルールの `runbook_url` はこの文書の同名の見出しを指します。見出しはルール名と同じにしてあります。札とリンクの欠けは `monitoring/scripts/check_alert_rules.py` が CI で検査します。

### 札（tier）の意味

- `page`：利用者に今影響が出ている、または出る直前。すぐ見る。
- `ticket`：急がないが、放置すると悪化する。翌営業日までに見る。
- `auto`：段階3 で自動の応急処置が付いたもの。今は該当なし。

### 共通の見方と止め方

- 見る場所：Grafana（監視用サーバー prod2）、Uptime Kuma、ログは Grafana の Loki（`{job="containerlogs"}`）。
- 鳴り止まないときの止め方：prod2 の Alertmanager のコンテナの中で `amtool silence add alertname=RULE --duration=PERIOD --comment=REASON` を実行する（RULE はルール名、PERIOD は期間、REASON は理由に置き換える）。期間と理由は記録に残す。
- 直し方が書けないものは「原因を切り分けて Opus に報告する」とだけ書いてある。推測で手順を作らない。

## HighCpuUsage

- 札：ticket
- 何が起きているか：CPU 使用率（5 分間平均）が 80% を超えた状態が 5 分続いた。
- 最初に見るもの：Grafana のサーバー資源のダッシュボード、サーバー上で `docker stats --no-stream`。手順は [monitoring-vps-migration.md](monitoring-vps-migration.md) も参照。
- 直し方：どのコンテナが CPU を使っているかを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=HighCpuUsage --duration=PERIOD --comment=REASON`

## HighMemoryUsage

- 札：ticket
- 何が起きているか：メモリ使用率が 85% を超えた状態が 5 分続いた。
- 最初に見るもの：Grafana のサーバー資源のダッシュボード、`docker stats --no-stream`。
- 直し方：どのコンテナがメモリを使っているかを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=HighMemoryUsage --duration=PERIOD --comment=REASON`

## HighDiskUsage

- 札：ticket
- 何が起きているか：ルート（`/`）のディスク使用率が 80% を超えた状態が 5 分続いた。
- 最初に見るもの：Grafana のディスクのダッシュボード、サーバー上で `df -h /` と `docker system df`。
- 直し方：何が容量を使っているかを切り分けて Opus に報告する。削除は不可逆操作なので PO の確認なしに行わない。
- 止め方：`amtool silence add alertname=HighDiskUsage --duration=PERIOD --comment=REASON`

## CriticalDiskUsage

- 札：page
- 何が起きているか：ルート（`/`）のディスク使用率が 90% を超えた状態が 2 分続いた。満杯になるとサービスが止まる。
- 最初に見るもの：`df -h /` と `docker system df`（どのサーバーかはアラートの `instance` で分かる）。
- 直し方：何が容量を使っているかを切り分けてすぐ Opus に報告する。削除は不可逆操作なので PO の確認なしに行わない。
- 止め方：`amtool silence add alertname=CriticalDiskUsage --duration=PERIOD --comment=REASON`

## ServiceDown

- 札：page
- 何が起きているか：Prometheus が Exporter から 2 分以上応答を得られない（`up == 0`）。アラートの `job` が止まっている対象。
- 最初に見るもの：サーバー上で `docker compose ps` と該当コンテナのログ、Grafana の Targets。
- 直し方：該当コンテナが落ちているか、ネットワークの問題かを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=ServiceDown --duration=PERIOD --comment=REASON`

## BackendHighErrorRate

- 札：page
- 何が起きているか：バックエンドの 5xx エラーが毎秒 5 件を超える状態が 2 分続いた（閾値の正本は `monitoring/tokens.yml`）。
- 最初に見るもの：Grafana のバックエンドのダッシュボード、Loki で `{job="containerlogs", container_name=~".*backend.*"} |~ "ERROR|Exception|Traceback"`。
- 直し方：エラーの種類と直近のデプロイとの関係を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=BackendHighErrorRate --duration=PERIOD --comment=REASON`

## BackendHighLatency

- 札：ticket
- 何が起きているか：/api/health を除いた利用者のリクエストのうち、2.5 秒を超えたものの割合が 5% を超える状態が 5 分続いた。2026-10-15 に条件を P99 > 2.0 秒から変えた。/api/health が毎回 1〜2.5 秒かかり、P99 を常に 2.0 秒より上に押し上げていたため（14 日で 393 回鳴っていた）。/api/health が遅い原因は未調査（設計 docs/handoff/ai-ops-247/stage1-design.md の U9）。
- 最初に見るもの：Grafana のバックエンドのダッシュボード。どの handler が遅いかは `topk(5, sum by (handler) (rate(http_request_duration_seconds_count{job="backend",handler!="/api/health"}[5m])) - sum by (handler) (rate(http_request_duration_seconds_bucket{job="backend",handler!="/api/health",le="2.5"}[5m])))` で出す。Grafana の backend の画面の P99 のパネルは /api/health を含んだまま変えていない（設計 U3 の扱い）。画面の P99 が高くても、この見張りは鳴らないことがある。
- 直し方：遅いリクエストと DB の状態を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=BackendHighLatency --duration=PERIOD --comment=REASON`

## BackendWorkerSaturated

- 札：ticket
- 何が起きているか：同時処理中のリクエストが 1 を超える状態が 2 分続いた（workers=1 運用では待ち行列ができる）。
- 最初に見るもの：Grafana の `http_requests_in_flight`、遅いリクエストのパス。
- 直し方：長く掛かっているリクエストを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=BackendWorkerSaturated --duration=PERIOD --comment=REASON`

## BackendSseConnectionsHigh

- 札：ticket
- 何が起きているか：SSE の接続数が 8 を超える状態が 5 分続いた。接続とメモリを消費する。
- 最初に見るもの：Grafana の `sse_connections_active`、バックエンドのメモリ。
- 直し方：接続が増えた原因（利用者数かクライアントの再接続か）を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=BackendSseConnectionsHigh --duration=PERIOD --comment=REASON`

## F2CleanupStale

- 札：ticket
- 何が起きているか：f2 掃除（`scripts/f2-cleanup.sh`）の最終の完全成功の時刻から 8 日（691200 秒）以上たった状態が 1 時間続いた（app-vps）。
- 経緯：2026-10 に 27,420 分鳴っていた原因は、掃除が実際に成功していなかったことだった。通知としては正しかった。鳴ったら「掃除が成功していない」ことを疑う。
- 最初に見るもの：app-vps の cron の実行記録、`scripts/f2-cleanup.sh` の出力、textfile の黒板ファイル（node_exporter の textfile 配線）。
- 直し方：cron・スクリプト・textfile の配線のどこで止まっているかを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=F2CleanupStale --duration=PERIOD --comment=REASON`

## F2CleanupAbsent

- 札：ticket
- 何が起きているか：f2 掃除の黒板メトリクスそのものが 24 時間消えている（app-vps）。黒板ファイルか textfile 配線の断線の疑い。
- 最初に見るもの：app-vps の node_exporter の textfile の設定と黒板ファイルの有無。
- 直し方：断線の箇所を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=F2CleanupAbsent --duration=PERIOD --comment=REASON`

## KumaMonitorDown

- 札：page
- 何が起きているか：Uptime Kuma の見張り（App・API・LP・監視基盤）のどれかが 2 分以上失敗している。どれかはアラートの `monitor_name` で分かる。
- 最初に見るもの：Uptime Kuma の該当の見張り、外から実際にそのページを開く、バックエンドのログ。
- 直し方：見張りの対象が本当に落ちているか、見張り側の問題かを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=KumaMonitorDown --duration=PERIOD --comment=REASON`

## CertExpiringSoon

- 札：ticket
- 何が起きているか：証明書の残り日数が 14 日未満の状態が 1 時間続いた。対象はアラートの `monitor_name`。
- 最初に見るもの：Uptime Kuma の該当の見張りの証明書の期限、証明書の自動更新の状態。
- 直し方：更新が止まっている原因を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=CertExpiringSoon --duration=PERIOD --comment=REASON`

## CertInvalid

- 札：page
- 何が起きているか：Uptime Kuma が証明書を無効と判定した状態が 10 分続いた。利用者のブラウザに警告が出る可能性がある。
- 最初に見るもの：Uptime Kuma の該当の見張り、ブラウザでの表示。
- 直し方：期限切れか、名前の不一致かを切り分けてすぐ Opus に報告する。
- 止め方：`amtool silence add alertname=CertInvalid --duration=PERIOD --comment=REASON`

## BruteForceAttempt

- 札：page
- 何が起きているか：認証失敗らしきログ（401・403 など）が 5 分間に 20 件を超えた状態が 1 分続いた。攻撃の可能性。
- 最初に見るもの：Loki で `{job="containerlogs"} |~ "401|403|auth.*fail|login.*fail|Unauthorized"`、どの経路・どのテナントか。
- 直し方：正常な利用の失敗か攻撃かを切り分け、攻撃の疑いなら security-reviewer と Opus に報告する。
- 止め方：`amtool silence add alertname=BruteForceAttempt --duration=PERIOD --comment=REASON`

## SustainedAuthFailure

- 札：ticket
- 何が起きているか：認証失敗らしきログが 1 時間に 50 件を超えた状態が 5 分続いた。低頻度の継続的な失敗。
- 最初に見るもの：Loki で `{job="containerlogs"} |~ "401|403|auth.*fail|Unauthorized"` を時間帯別に見る。
- 直し方：特定の利用者の設定ミスか攻撃かを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=SustainedAuthFailure --duration=PERIOD --comment=REASON`

## BackendErrorSpike

- 札：page
- 何が起きているか：バックエンドのログの `ERROR|Exception|Traceback` が 5 分間に 30 件を超えた状態が 2 分続いた。
- 最初に見るもの：Loki で `{job="containerlogs", container_name=~".*backend.*"} |~ "ERROR|Exception|Traceback"`。
- 直し方：同じ種類のエラーが繰り返しているかを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=BackendErrorSpike --duration=PERIOD --comment=REASON`

## DatabaseError

- 札：page
- 何が起きているか：PostgreSQL のログに `ERROR|FATAL|PANIC` が 5 分間に 5 件を超えた状態が 1 分続いた。
- 最初に見るもの：Loki で `{job="containerlogs", container_name=~".*postgres.*"} |~ "ERROR|FATAL|PANIC"`、DB コンテナの状態。
- 直し方：エラーの内容（接続・ディスク・クエリ）を切り分けてすぐ Opus に報告する。DB への書き込み操作は PO の確認なしに行わない。
- 止め方：`amtool silence add alertname=DatabaseError --duration=PERIOD --comment=REASON`

## DiscordGatewayReconnectFailure

- 札：page
- 何が起きているか：Discord Gateway のログの `reconnect|LoginFailure|RuntimeError|接続失敗` が 10 分間に 3 件を超えた状態が 2 分続いた。DM の受信が止まっている可能性。
- 最初に見るもの：Loki で `{job="containerlogs", container_name=~".*discord.*"}`。運用の手順は [discord-gateway-operations.md](discord-gateway-operations.md)。
- 直し方：Bot トークンの失効か、Discord 側の障害かを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=DiscordGatewayReconnectFailure --duration=PERIOD --comment=REASON`

## DiscordDmWriterError

- 札：ticket
- 何が起きているか：`[dm_writer]` のログのエラーが 5 分間に 5 件を超えた状態が 1 分続いた。DM の受信箱への書き込みが失敗している。
- 最初に見るもの：Loki で `{job="containerlogs", container_name=~".*discord.*"} |= "[dm_writer]"`。運用の手順は [discord-gateway-operations.md](discord-gateway-operations.md)。
- 直し方：DB 接続かスキーマかを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=DiscordDmWriterError --duration=PERIOD --comment=REASON`
