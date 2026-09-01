# recon — 添付保存用ボリュームの追加

> この文書は何か（専門用語なしの1行）:
> 画像を置く場所をサーバーに用意する前に、今の設定がどうなっているかを実際に見て記録したもの。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-01）

サービス定義の位置:
- `docker-compose.yml:5` nginx
- `docker-compose.yml:42` certbot
- `docker-compose.yml:63` backend
- `docker-compose.yml:146` frontend
- `docker-compose.yml:182` celery-worker
- `docker-compose.yml:235` celery-beat
- `docker-compose.yml:270` discord-gateway
- `docker-compose.yml:306` redis
- `docker-compose.yml:336` postgres
- `docker-compose.yml:374` gha-exporter

ボリューム関連:
- `docker-compose.yml:111` に backend の volumes セクションが既に存在する。
- `docker-compose.yml:112` の既存マウントは
  `- ./firebase-credentials.json:/app/firebase-credentials.json:ro` の1件のみ。
- `docker-compose.yml:210` に celery-worker が同一のマウント行を持つ。
  そのため backend を一意に指すには `SMOKE_SERVICE_EMAIL` を含むアンカーが必要である。
- `docker-compose.yml:110` の `SMOKE_SERVICE_EMAIL` は同ファイル内で1箇所のみ。
- `docker-compose.yml:407` にトップレベル volumes が存在する。
  子要素は `postgres_data:`（408行）と `redis_data:`（409行）の2件のみ。
- インデントは、トップレベル volumes の子が半角2つ、
  backend の volumes の子が半角6つ + `- `。
- `docker inspect astro-webapp-backend-1` の Mounts は空配列であり、
  コンテナ内に書いたファイルはデプロイのたびに失われる状態である。

## 本便で変更する箇所

- `docker-compose.yml:112` の直後に1行追加
- `docker-compose.yml:409` の直後に1行追加

いずれも既存行を変更しない追加のみ。
