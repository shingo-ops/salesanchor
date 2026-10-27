# 見張りのルール別 手順書

この文書は何か：見張り（アラート）のルールごとの手順書です。ルールの正本は `monitoring/prometheus/alert_rules.yml`（Prometheus 34 本）と `monitoring/loki/rules/jarvis/alerts.yml`（Loki 6 本）です。各ルールの `runbook_url` はこの文書の同名の見出しを指します。見出しはルール名と同じにしてあります。札とリンクの欠けは `monitoring/scripts/check_alert_rules.py` が CI で検査します。

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

## CeleryHeartbeatStale

- 札：page
- 何が起きているか：裏方の処理（celery）の 1 分ごとの heartbeat が 10 分以上更新されず、その状態が 2 分続いた。LINE 解析・翻訳・定期の集計が止まっている可能性がある。指標は backend の `/metrics` が Redis から読んで出す（Redis が読めないときは前の値のまま）。Redis はメモリが一杯になると記録を消すことがある（`allkeys-lru`）ので、heartbeat のキーが消えてもこの見張りは鳴る。
- 閾値の根拠：heartbeat と同じ短い定期タスクの、worker の受付から完了までの 14 日の最大は 60 秒。600 秒はその約 10 倍。worker に受け取られる前の待ちは測れていないので、反映後に本番で確かめた。
- 最初に見るもの：prod1 の celery-beat と celery-worker のコンテナの状態（`docker compose ps`）→ worker が今処理中のタスク数（`celery -A app.celery_app inspect active`）→ Loki の worker のログの直近の `received`／`succeeded`。
- 直し方：止まっている方のコンテナを `docker compose restart`。
- 止め方：`amtool silence add alertname=CeleryHeartbeatStale --duration=PERIOD --comment=REASON`（理由と期限を書く）

## CeleryTaskFailuresHigh

- 札：ticket
- 何が起きているか：同じ裏方のタスクが 1 時間に 3 回以上失敗した。指標は backend の `/metrics` が Redis から読んで出す（Redis が読めないときは前の値のまま）。Redis がメモリ一杯で記録を消すことがある（`allkeys-lru`）。
- 最初に見るもの：Loki で `|= "raised unexpected"` とタスク名で絞ったログ。
- 注記：2026-10-15 まで translate_pending_messages が毎日 2〜3 回失敗していた。原因は買取価格の取得（buyback.fetch_all_prices）が共用 engine を片付けず、同じ worker で次に動いた作業が "attached to a different loop" で落ちていたこと。2026-10 にまとめ翻訳を廃止し、買取価格の取得に後片付けを足した（docs/handoff/celery-unregistered-tasks/design.md）。
- 効く範囲：1 日に 1〜2 回しか動かないタスク（sa02・為替・tcg_mirror 等）の失敗ではこの見張りは鳴らない。またタスク名の系列ができた最初の 1 件は increase に数えられない。どちらも段階1 で決めた範囲で、日次タスクの失敗の見張りは別の便で扱う。
- 直し方：失敗の原因（ログの例外）を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=CeleryTaskFailuresHigh --duration=PERIOD --comment=REASON`

## CeleryQueueBacklog

- 札：ticket
- 何が起きているか：裏方の処理の待ち行列が 100 件を超えた状態が 10 分続いた。指標は backend の `/metrics` が Redis から読んで出す（Redis が読めないときは前の値のまま）。Redis がメモリ一杯で記録を消すことがある（`allkeys-lru`）。
- 閾値の根拠：14 日の 10 分あたりの受付の最大は 58 件なので、その 10 分に 1 件も片付かなくても 100 に届かない。
- 最初に見るもの：待ち行列の長さの推移（`celery_queue_length`）と、worker が処理中のタスク（長いタスク `tcg.extract_source_message` 等が並んでいないか）。
- 直し方：長いタスクが詰まっていれば Opus に報告する。worker の再起動は処理中のタスクを止めるので、Opus の判断を待つ。
- 止め方：`amtool silence add alertname=CeleryQueueBacklog --duration=PERIOD --comment=REASON`

## ViewerInventoryStale

- 札：ticket
- 何が起きているか：閲覧ページの在庫の作り置き（1 分ごとのタスク）が 10 分以上書けておらず、配信の保留でもない状態が 2 分続いた。作り置きのタスクの失敗が続いている可能性がある。worker の停止は CeleryHeartbeatStale が別に知らせる。指標は backend の `/metrics` が Redis（db0）から読んで出す（キーが無いときは 0 で、この見張りは鳴る）。
- 最初に見るもの：`docker logs --since 15m <worker> | grep viewer-cache`、Redis の `viewer:inventory:fail_count`（3 に達すると Discord にも知らせる）、配信の保留の理由は `[dist]` のログ。
- 閲覧者への影響：前回の在庫が出続ける。作り置きは 24 時間で消えるので、それまでに直らないと閲覧 API は 503 になる。
- 直し方：戻し方は無し。タスクが次に成功すれば自然に消える。失敗の原因（ログの例外）を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=ViewerInventoryStale --duration=PERIOD --comment=REASON`

## ViewerInventoryStaleOnHold

- 札：ticket
- 何が起きているか：閲覧ページの在庫の作り置きが 10 分以上書けておらず、直近 2 分以内に配信の保留を確かめている状態が 2 分続いた。解析の実行中などで配信が保留されている。閲覧ページは前回の在庫を出し続ける（設計 Q11）。
- 最初に見るもの：配信の保留の理由（`[dist]` のログ）、`docker logs --since 15m <worker> | grep viewer-cache`、Redis の `viewer:inventory:fail_count`。
- 閲覧者への影響：前回の在庫が出続ける。作り置きは 24 時間で消えるので、保留が長く続くと閲覧 API は 503 になる。
- 直し方：戻し方は無し。保留が解ければ次の 1 分で作り置きが書かれ、自然に消える。長く続くときは保留の原因を Opus に報告する。
- 止め方：`amtool silence add alertname=ViewerInventoryStaleOnHold --duration=PERIOD --comment=REASON`

## BackupLocalStale

- 札：ticket
- 何が起きているか：毎日 3:00 の `scripts/backup.sh`（DB バックアップ）が 26 時間以上成功していない状態が 10 分続いた。デプロイの Pre-deploy DB backup の成功でも時刻は進む。利用者に今の影響は無い。翌営業日までに復旧する。
- 閾値の根拠：cron は毎日 1 回、所要は最大 81 秒。1 日 1 回の成功なら差は最大で約 24 時間 2 分で、26 時間には届かない。1 回抜けると、約 2 時間後に鳴る。
- 最初に見るもの：prod1 の `/home/ubuntu/backups/postgres/backup.log` の末尾（成功の行と `TEXTFILE ... FAIL` の行）、`/home/ubuntu/backups/cron.log`（失敗の出力先）、ubuntu の crontab。
- 直し方：失敗の原因（postgres のコンテナ・ディスクの空き）を切り分けて Opus に報告する。手動で 1 回実行してよい（`bash /home/ubuntu/salesanchor/scripts/backup.sh`）。
- 止め方：`amtool silence add alertname=BackupLocalStale --duration=PERIOD --comment=REASON`

## BackupS3Stale

- 札：ticket
- 何が起きているか：毎日 3:30 の `scripts/backup_to_s3.sh`（S3 への写し）が 26 時間以上成功していない状態が 10 分続いた。毎月 1 日は Glacier への月次の保存の失敗でも成功時刻が書かれない。利用者に今の影響は無い。翌営業日までに復旧する。
- 最初に見るもの：`/home/ubuntu/backups/s3_backup.log` の末尾（`ERROR`・`WARN: TEXTFILE` の行）、Discord の ops チャンネルの「S3バックアップ失敗」の通知。
- 直し方：AWS の認証・S3 の応答・ローカルのバックアップの有無を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=BackupS3Stale --duration=PERIOD --comment=REASON`

## BackupTimestampAbsent

- 札：ticket
- 何が起きているか：バックアップの成功時刻（`backup_local.prom` か `backup_s3.prom`）のどちらかが 30 時間取れていない。textfile の断線かファイルの消失の疑い。利用者に今の影響は無い。翌営業日までに復旧する。
- 最初に見るもの：prod1 の `/home/ubuntu/node_exporter_textfile/` に `backup_local.prom` と `backup_s3.prom` があるか、`node_textfile_scrape_error{instance="app-vps"}`、`backup.log` の `TEXTFILE ... FAIL` の行。
- 直し方：断線の箇所を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=BackupTimestampAbsent --duration=PERIOD --comment=REASON`

## MonitoringConfigDrift

- 札：ticket
- 何が起きているか：毎日 09:23 JST ごろの確認で、prod2 に置いた監視設定 6 本のうち 1 本以上が main と一致しない状態が 5 分続いた。main にマージしてから prod2 に置くまでの間も鳴る（置き忘れの知らせ）。利用者に今の影響は無い。翌営業日までに直す。
- 最初に見るもの：GitHub の Actions の「Monitoring config drift check」の最新の実行ログ（`DRIFT:` の行にファイル名が出る）。
- 直し方：どちらが正しいかを切り分ける。main が正しければ main の版を prod2 に置き直して読み直す（手順は各便のカード §8 と同じ）。prod2 の手直しが正しければ repo に PR で取り込む。置き直した後は workflow を手動で 1 回実行して、ずれ 0 を確かめる（pushgateway は次に送るまで古い値を持ち続ける）。迷ったら Opus に報告する。比べるのは `monitoring/scripts/check_config_drift.sh` の `FILES` にある 6 本だけで、監視設定のファイルを増やしたら `FILES` にも足す。
- 止め方：`amtool silence add alertname=MonitoringConfigDrift --duration=PERIOD --comment=REASON`

## MonitoringConfigCheckStale

- 札：ticket
- 何が起きているか：監視設定のずれの確認が 50 時間以上 pushgateway に送っていない状態が 1 時間続いた（毎日 1 回の確認が 2 回続けて動かなかった）。利用者に今の影響は無い。翌営業日までに直す。
- 最初に見るもの：Actions の実行の一覧（失敗か、そもそも起動していないか）、prod2 の runner のサービス（`systemctl status actions.runner.shingo-ops-salesanchor.salesanchor-vps`）、pushgateway のコンテナ。
- 直し方：runner・workflow・pushgateway のどこで止まっているかを切り分けて Opus に報告する。
- pushgateway を再起動・作り直した後：pushgateway は値を保存しない設定（docker-compose.monitoring.yml:133-150 に persistence の指定なし）なので、溜まっていた値が消える。再起動の後は、Actions で `monitoring-config-drift.yml` と `sop-health-reporter.yml` を手動で 1 回ずつ実行し、両方 success を確かめる（U19・2026-10-15 PO 決定）。
- 止め方：`amtool silence add alertname=MonitoringConfigCheckStale --duration=PERIOD --comment=REASON`

## ContainerUnhealthy

- 札：page（処置の付く段階3 便G で auto に変える）
- 何が起きているか：prod1 の celery-worker・celery-beat・discord-gateway・gemini-egress のどれかの健康診断（docker-compose.yml の healthcheck）が unhealthy で、その状態が 1 分続いた。健康診断は、コンテナの中の「生きている印」が 2〜2 分半更新されないと失敗する（gemini-egress は中継の先の tinyproxy が答えないと失敗する）。値は prod1 の `scripts/ops/container_state.py` が毎分 textfile に書く。
- 影響：worker・beat は LINE 解析・翻訳・定期の集計が止まる。discord-gateway は Discord の受信が止まる。gemini-egress は緊急用の中継なので、Gemini が直接接続のままなら利用者への影響は無い。
- 最初に見るもの：prod1 で `docker inspect -f '{{json .State.Health}}'`（該当のコンテナ）の最後の記録 → Loki の該当コンテナのログの直近。
- 直し方：該当のコンテナを `docker compose restart`。gemini-egress は prod2 の tinyproxy の状態も見る。繰り返すときは原因を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=ContainerUnhealthy --duration=PERIOD --comment=REASON`

## ContainerStateStale

- 札：page
- 何が起きているか：prod1 の状態書き係（`scripts/ops/container_state.py`、ubuntu の cron で毎分）が 5 分以上 textfile を書いていない、または値が無い状態が 2 分続いた。この間はコンテナが不健康になっても ContainerUnhealthy が鳴らない。
- 最初に見るもの：prod1 の `crontab -l` に container_state の行があるか → `/tmp/container-state.log` の最後の行（失敗のときだけ書かれる）→ `/home/ubuntu/node_exporter_textfile/container_state.prom` の時刻。
- 直し方：ログの原因（docker が読めない・書けない）を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=ContainerStateStale --duration=PERIOD --comment=REASON`

## ContainerHealthcheckMissing

- 札：ticket
- 何が起きているか：prod1 の celery-worker・celery-beat・discord-gateway・gemini-egress のどれかが動いているのに、健康診断（docker-compose.yml の healthcheck）が無い状態が 10 分続いた。定義が消えた・無効にされた、または古い定義のまま作り直された。この間はそのコンテナが固まっても ContainerUnhealthy が鳴らない。値は prod1 の `scripts/ops/container_state.py` が毎分 textfile に書く。
- 影響：今の利用者への影響は無い。翌営業日までに直す。
- 最初に見るもの：main の docker-compose.yml の該当サービスの healthcheck（CI の `monitoring/scripts/check_app_healthchecks.py` が通っているか）→ prod1 で `docker inspect -f '{{json .Config.Healthcheck}}'`（該当のコンテナ）。
- 直し方：main に定義があれば、次の deploy で作り直されて戻る。main から消えていれば、消した変更を戻す PR を出して Opus に報告する。
- 止め方：`amtool silence add alertname=ContainerHealthcheckMissing --duration=PERIOD --comment=REASON`

## ClockSkew

- 札：page
- 何が起きているか：その機体の時計と監視サーバーの時計の差が 60 秒を超えた。さくらのメンテや機体の再起動の後に起きうる（2026-10-22 に prod1 が約 40 分遅れた）。
- 影響：時刻を比べる警報 7 本（F2CleanupStale・CeleryHeartbeatStale・ViewerInventoryStale・ViewerInventoryStaleOnHold・BackupLocalStale・BackupS3Stale・ContainerStateStale）は、この警報の間 Alertmanager で止めている。止めている間、それらの本物の停止にも気づけない。DB に書く時刻もずれる。
- 最初に見るもの：Grafana か Prometheus で `node_time_seconds - timestamp(node_time_seconds)` を機体ごとに見る。`node_timex_sync_status` が 1 か。
- 直し方：時刻合わせが動いていれば数分で自然に直る（2026-10-22 は約 11 分）。直らなければ Opus に報告する（時計を手で直す操作は本番の変更なので PO の判断）。
- prod2 自身の時計のずれはこの警報では見えない（差はいつもほぼ 0）。prod2 は ClockSyncStopped で見る。
- 止め方：`amtool silence add alertname=ClockSkew --duration=PERIOD --comment=REASON`

## ClockSyncStopped

- 札：ticket
- 何が起きているか：その機体で時刻合わせが 10 分以上同期していない。
- 影響：今は無いが、続くと時計がずれ、ClockSkew と誤警報が起きる。
- 最初に見るもの：`node_timex_sync_status` と `node_timex_offset_seconds` を機体ごとに見る。
- 直し方：Opus に報告する（時刻合わせの設定の変更は本番の変更なので PO の判断）。
- 止め方：`amtool silence add alertname=ClockSyncStopped --duration=PERIOD --comment=REASON`

## RecoveryCheckFailed

- 札：page
- 何が起きているか：本番の API が止まって戻った後の点検で、札 `item_ja` の項目が 6 分たっても正常に戻らない。項目は 10 個（アプリ画面・API・データベース・Redis・裏方の処理の受け手・紹介ページ・監視の読み取り・本番サーバーの時計・裏方の処理・コンテナの状態記録）。監視の読み取りが NG のときは時計・裏方の処理・コンテナの状態記録を、時計が NG のときは裏方の処理・コンテナの状態記録を判定しない（その間は一覧に出ない）。
- 影響：その項目が使えないまま。直るまで 5 分おきに点検を続ける。
- 最初に見るもの：Prometheus で `salesanchor_recovery_check_failed == 1` の `item`。`docker compose -f docker-compose.monitoring.yml logs --tail 50 recovery-check`（prod2）。同じ時間に鳴っている警報（ServiceDown・ClockSkew・CeleryHeartbeatStale 等）。
- 直し方：項目ごとの警報の節に従う。直れば自動で解決する。サービスの再起動などの本番の変更は Opus に報告する（PO の判断）。
- 止め方：`amtool silence add alertname=RecoveryCheckFailed --duration=PERIOD --comment=REASON`

## RecoveryCheckPassed

- 札：ticket（知らせだけ。対応は要らない）
- 何が起きているか：本番の API が止まって戻った後の点検で、10 項目すべてが正常だった。10 分だけ鳴り、Discord にだけ届く（障害記録には書かない。解決の通知も出ない）。
- 影響：無し。
- 最初に見るもの：無し。止まっていた間の原因は、同じ時間の ServiceDown・KumaMonitorDown の記録で見る。
- 直し方：無し。
- 止め方：`amtool silence add alertname=RecoveryCheckPassed --duration=PERIOD --comment=REASON`

## RecoveryCheckStale

- 札：ticket
- 何が起きているか：点検係（prod2 の `recovery-check`）が 5 分以上点検を回していない。
- 影響：サーバーが戻っても ✅/❌ が届かない。
- 最初に見るもの：prod2 の `docker compose -f docker-compose.monitoring.yml ps recovery-check` と `logs --tail 50 recovery-check`。ServiceDown（job recovery-check）が同時に鳴っているか。
- 直し方：Opus に報告する（コンテナの再起動は本番の変更なので PO の判断）。
- 止め方：`amtool silence add alertname=RecoveryCheckStale --duration=PERIOD --comment=REASON`

## OpsMailSilent

- 札：ticket
- 何が起きているか：運用の受け箱に、さくらの差出人のメールが 40 日届いていない。さくらは決済の案内を毎月送るので、業務用メールの自動転送（さくらの差出人だけを転送する設定）が切れている見込みがある。
- 影響：さくらの点検・障害の予告が Discord に届かない。
- 最初に見るもの：PO の業務用メールに、この 40 日の間にさくらからのメールがあるか（PO に聞く）。あれば転送の設定（Gmail の設定 → 転送とフィルタ）。無ければ、さくらが送っていないだけなので、次の決済の案内まで待つ。
- 直し方：転送の設定を PO が直す（card-bin3.md §8-6 の手順）。直った後、次にさくらからメールが届けば自動で解決する。
- 止め方：`amtool silence add alertname=OpsMailSilent --duration=PERIOD --comment=REASON`

## OpsMailPollStale

- 札：ticket
- 何が起きているか：裏方の処理（celery）が運用の受け箱を 3 時間読めていない。
- 影響：さくらの点検・障害のメールが Discord に届かない。
- 最初に見るもの：同じ時間に CeleryHeartbeatStale が鳴っているか（鳴っていればその節）。prod1 の celery-worker のログの `[ops_mail]` の行（接続の失敗・ログインの失敗）。
- 直し方：パスワードを変えた・受け箱を消したなら、PO が受け箱と GitHub の secret を直し、Opus が通常のデプロイで本番の設定に入れる。直れば自動で解決する。
- 止め方：`amtool silence add alertname=OpsMailPollStale --duration=PERIOD --comment=REASON`
