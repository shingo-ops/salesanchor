# recon — exporter-port-align

## 背景
監視VPS(49.212.160.98)のPrometheusが、prod1(49.212.137.46)の
postgres/nginx/redis exporter を 19187/19113/19121 で取得する設定だが、
prod1側のcompose公開ポートが 9187/9113/9121 でズレている。

## 実コード根拠（file:line）
- prometheus.yml:32 postgres-exporter targets ["host-gateway:19187"]
- prometheus.yml:39 nginx-exporter targets ["host-gateway:19113"]
- prometheus.yml:86 redis-exporter targets ["host-gateway:19121"]
- docker-compose.exporters.yml:34 postgres-exporter "49.212.137.46:9187:9187"
- docker-compose.exporters.yml:51 nginx-exporter "49.212.137.46:9113:9113"
- docker-compose.exporters.yml:69 redis-exporter "49.212.137.46:9121:9121"

## 実測（FRESH-RUN 2026-06-29T05:18Z prod1）
- postgres/nginx/redis exporter: コンテナ未作成
- localhost:19187/19113/19121 → HTTP:000
- 既存稼働: nginx-1/postgres-1/redis-1/gha-exporter-1 はUp(healthy)

## 先行事例
PR #2672 で node-exporter を 9100:9100 → 19100:9100 に修正済み（同一パターンの横展開）。
