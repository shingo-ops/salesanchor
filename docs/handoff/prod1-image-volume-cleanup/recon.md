# prod1 Playwright Image Cleanup Recon（2026-06-29 22:47 JST）

出典: `ssh prod1 'bash -s' <<'EOF' ... EOF`

## 基本情報

| 項目 | 値 |
|------|-----|
| ホスト | os3-322-50792 |
| 実行日時 | 2026-06-29 22:47:03 JST |
| Disk (`/`) | 50G 中 27G 使用 (58%)、残り 20G |
| Mem | 1.9Gi 中 1.5Gi 使用、available 440Mi |
| Swap | 2.0Gi 中 267Mi 使用 |
| Uptime | 80 days, 12:36 |

## ① 稼働コンテナ（11個・全て UP）

| NAMES | STATUS | IMAGE |
|------|--------|-------|
| astro-webapp-discord-gateway-1 | Up 5 hours | astro-webapp-discord-gateway |
| astro-webapp-frontend-1 | Up 5 hours (healthy) | astro-webapp-frontend |
| astro-webapp-celery-beat-1 | Up 5 hours | astro-webapp-celery-beat |
| astro-webapp-celery-worker-1 | Up 5 hours | astro-webapp-celery-worker |
| astro-webapp-backend-1 | Up 5 hours | astro-webapp-backend |
| astro-webapp-certbot-1 | Up 13 hours | certbot/certbot:v5.6.0 |
| astro-webapp-nginx-1 | Up 13 hours (healthy) | nginx:1.31.1 |
| astro-webapp-postgres-1 | Up 23 hours (healthy) | postgres:16 |
| astro-webapp-gha-exporter-1 | Up 23 hours | 640e564fa6ca |
| pushgateway | Up 23 hours | prom/pushgateway:v1.10.0 |
| astro-webapp-redis-1 | Up 23 hours (healthy) | redis:7-alpine |

## ② 停止コンテナ

**0個**

出典: `docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}'`

## ③ Image / Volume / Cache の正本

### Image

| 指標 | 値 |
|------|-----|
| `docker images -q | wc -l` | 38 |
| `docker images -q | sort -u | wc -l` | 36 |
| `docker images -f dangling=true -q | wc -l` | 0 |

### 主要な未使用 image

| Image | ID | SIZE | CONTAINERS |
|-------|----|------|------------|
| `mcr.microsoft.com/playwright:v1.61.0-noble` | `57b65fdc9cea` | 3.45GB | 0 |

### Volume

| 指標 | 値 |
|------|-----|
| `docker volume ls -q | wc -l` | 171 |

### Docker system df

| 項目 | 値 |
|------|-----|
| Images | 36 total / 10 active / 17.61GB / 12.13GB reclaimable |
| Containers | 11 total / 11 active / 5.472MB |
| Local Volumes | 171 total / 3 active / 2.132GB / 1.978GB reclaimable |
| Build Cache | 61 total / 2.34GB / 2.154GB reclaimable |

## ④ 影響確認

- 現役コンテナ 11 本は全て稼働
- `astro-webapp_postgres_data` と `astro-webapp_redis_data` は存在
- 監視系 volume は保持
- `mcr.microsoft.com/playwright:v1.61.0-noble` は CONTAINERS=0

## ⑤ 重要な読み取り結果

- `entity_count` は canonical 値として 36
- 対象 image は 1 件 בלבד
- volume は削除対象外
- named 個別削除以外の prune 系操作は使わない
