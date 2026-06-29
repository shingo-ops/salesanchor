# recon — node-exporter-port-fix

- 仕事名: node-exporter-port-fix
- 日付: 2026-06-29
- 対象ADR: ADR-081（監視VPS最終運用設計）
- 担当: Planner=Claude / Generator=CC

## file:line 引用表

| 事実 | 参照 |
|---|---|
| 監視は別VPS 49.212.160.98。prod1 は入口のみで /grafana/ を proxy | nginx/nginx.conf:166-167 |
| Prometheus は app-vps を host-gateway:19100 で scrape | /opt/salesanchor-monitoring/monitoring/prometheus/prometheus.yml:25 |
| host-gateway の解決定義（extra_hosts） | /opt/salesanchor-monitoring/docker-compose.monitoring.yml:34 |
| prod1 の node-exporter 公開ポート定義は 9100:9100 | docker-compose.exporters.yml:16 |
| node-exporter に restart: unless-stopped は既に在り | docker-compose.exporters.yml:17 |
| 監視VPS ターゲットは mgmt-vps=9100 / app-vps=19100 と意図的に分離 | prometheus.yml（node-exporter job 2ターゲット） |
| 既存アラート HighDiskUsage>80%/HighMemoryUsage>85%/HighCpuUsage>80% | /opt/salesanchor-monitoring/monitoring/prometheus/alert_rules.yml |
| Discord通知 discord-ops 定義あり・GF_DISCORD_WEBHOOK_URL 設定済み | /opt/salesanchor-monitoring/monitoring/grafana/provisioning/alerting/alerting.yml |
| docker-compose.exporters.yml は deploy.yml の自動導線に不在 | .github/workflows/deploy.yml（exporters 記述なし） |

## 実測（Prometheus 生クエリ）

| 観測 | 結果 |
|---|---|
| node_filesystem_avail_bytes{instance="app-vps"} | 空（データ未到達） |
| node_memory_MemAvailable_bytes{instance="app-vps"} | 空 |
| up{job="node-exporter",instance="app-vps"} | 0 |
| HighDiskUsage / HighMemoryUsage ルール状態 | inactive |
| prod1 ss/curl localhost:9100・19100 | 待ち受け・応答なし |
| prod1 docker ps -a node-exporter | 痕跡なし（未起動・過去起動なし） |

## 不明点リスト（確認して解消済み）

- 「監視は別VPSか同居か」→ 確認: nginx.conf:166-167 と ADR-081 で別VPS(49.212.160.98)と確定。
- 「19100 は誤りか共通規約か」→ 確認: 監視VPSが mgmt-vps=9100 / app-vps=19100 と意図的に分離。app-vps を 19100 で見るのは設計意図。よって prod1 側を 19100 に合わせるのが正。
- 「沈黙原因は閾値か通知先か」→ 確認: 閾値妥当・webhook設定済み。真因は app-vps ホストメトリクスが Prometheus に未到達（node-exporter 未起動＋ポート不一致）。

## 未解決ゼロ確認

未解決事項なし。真因は「prod1 node-exporter 未起動 ＋ 公開ポート9100が監視VPS期待19100と不一致」で確定。
