# prod1 Docker Recon（2026-06-29 14:32 JST）

出典: `ssh prod1 'bash -s' <<'EOF' ... EOF` / `~/.ssh/manual-only/id_ed25519`

## 基本情報

| 項目 | 値 |
|------|-----|
| ホスト | os3-322-50792 |
| 実行ユーザー | ubuntu |
| 実行日時 | 2026-06-29 14:32:10 JST |
| ディスク (`/dev/vda2`) | 50G 中 27G 使用 (58%)、残り 20G |
| メモリ | 1.9Gi 中 1.4Gi 使用、空き 280Mi |
| スワップ | 2.0Gi 中 130Mi 使用 |

## ① 稼働コンテナ（11個・全て UP）

```
NAMES                            STATUS                    IMAGE
astro-webapp-frontend-1          Up 19 minutes (healthy)   astro-webapp-frontend
astro-webapp-celery-worker-1     Up 19 minutes             astro-webapp-celery-worker
astro-webapp-discord-gateway-1   Up 19 minutes             astro-webapp-discord-gateway
astro-webapp-celery-beat-1       Up 19 minutes             astro-webapp-celery-beat
astro-webapp-backend-1           Up 20 minutes             astro-webapp-backend
astro-webapp-certbot-1           Up 5 hours                certbot/certbot:v5.6.0
astro-webapp-nginx-1             Up 5 hours (healthy)      nginx:1.31.1
astro-webapp-postgres-1          Up 15 hours (healthy)     postgres:16
astro-webapp-gha-exporter-1      Up 15 hours               640e564fa6ca
pushgateway                      Up 15 hours               prom/pushgateway:v1.10.0
astro-webapp-redis-1             Up 15 hours (healthy)     redis:7-alpine
```

## ② 停止コンテナ

**0個（クリーン）**

出典: `docker ps -a --filter status=exited --filter status=created`

## ③ Volume（171個）

出典: `docker volume ls` / `docker system df -v`

**保持必須（LINKS=1・アクティブ）**

| Volume 名 | SIZE | 用途 |
|-----------|------|------|
| `astro-webapp_postgres_data` | 128.4MB | **本番DB — 絶対保持** |
| `astro-webapp_redis_data` | 24.39MB | **本番Redis — 絶対保持** |
| `16d82472d2fed201d21ece55d554162b72a30d39a9c33a2eec4fcdff4fedf618` | 0B | anonymous（certbot 関連推定） |

**データあり・LINKS=0（現在未使用）**

| Volume 名 | SIZE | 推定用途 |
|-----------|------|---------|
| `astro-webapp_prometheus_data` | 1.361GB | 監視メトリクス（コンテナ停止中） |
| `astro-webapp_loki_data` | 220.8MB | ログ集約（コンテナ停止中） |
| `astro-webapp_grafana_data` | 55.01MB | Grafana 設定（コンテナ停止中） |
| `astro-webapp_uptime_kuma_data` | 848.3kB | UptimeKuma（コンテナ停止中） |
| `salesanchor_grafana_data` | 0B | 旧 Grafana（用途不明） |
| anonymous × 7個 | 40〜98MB 各 | 不明（ハッシュ名） |

残り約160個: 0B × LINKS=0 の匿名孤児 volume

**合計**: 171 volumes / 2.13GB / 回収可能 1.978GB (92%)

## ④ イメージ（36個・計 17.57GB）

出典: `docker images` / `docker system df -v`

**使用中（CONTAINERS≥1）**

| Image | SIZE |
|-------|------|
| astro-webapp-backend/celery-beat/celery-worker/discord-gateway | 1.14GB × 4（共有含む） |
| astro-webapp-frontend | 105MB |
| nginx:1.31.1 | 241MB |
| postgres:16 | 641MB |
| redis:7-alpine | 61.2MB |
| certbot/certbot:v5.6.0 | 308MB |
| prom/pushgateway:v1.10.0 | 38.6MB |
| 640e564fa6ca (gha-exporter) | 154MB |

**未使用（CONTAINERS=0）主要なもの**

| Image | SIZE |
|-------|------|
| mcr.microsoft.com/playwright:v1.61.0-noble | 3.45GB |
| louislam/uptime-kuma:2 | 2.48GB |
| louislam/uptime-kuma:2.3.0 | 2.48GB |
| grafana/grafana:13.0.1 | 1.45GB |
| grafana/grafana:latest | 1.01GB |
| prom/prometheus:v3.11.3 / latest | 578MB × 2 |
| grafana/promtail:3.6.11 / latest | 331MB / 283MB |
| certbot/certbot:latest | 311MB |
| postgres:16-alpine | 396MB |
| louislam/uptime-kuma:latest | 724MB |

回収可能合計: **12.13GB (69%)**

## ⑤ Build キャッシュ

出典: `docker system df` / `docker system df -v` / `docker buildx du`

| 項目 | 値 |
|------|-----|
| 合計 | 2.287GB |
| Shared | 186.2MB |
| Private（全て reclaimable） | 2.101GB |
| 最古エントリ | 2ヶ月前（tbps6ou8cugo: 12.97MB） |
| 最新エントリ | 20分前（今日のビルド由来） |

## ⑥ Cron

出典: `crontab -l` / `ls /etc/cron.d /etc/cron.daily`

**ubuntu ユーザー crontab（2本のみ）**

```cron
# Jarvis CRM 日次バックアップ（毎日3:00）
0 3 * * * /home/ubuntu/salesanchor/scripts/backup.sh >> /home/ubuntu/backups/cron.log 2>&1

# S3遠隔バックアップ（毎日3:30 JST）
30 3 * * * TZ=Asia/Tokyo /home/ubuntu/salesanchor/scripts/backup_to_s3.sh >> /home/ubuntu/backups/s3_backup.log 2>&1
```

**掃除系 cron: 不在**（backup 2本のみ）

**システム cron**（OS 標準・触らない）: e2scrub_all, sysstat, apport, apt-compat, dpkg, logrotate, man-db
