# recon — postgres healthcheck の DB 名指定

**仕事名**: postgres-healthcheck-dbname
**日付**: 2026-10-17
**対象ADR**: ADR-1012
**担当**: Sonnet（PO 承認済み 2026-10-17）

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docker-compose.yml:486` | postgres healthcheck が `pg_isready -U ${POSTGRES_USER:-postgres}` のみ。-d 省略時は pg_isready がユーザー名と同名 DB へ接続する。本番は POSTGRES_USER=jarvis・POSTGRES_DB=jarvis_db のため `database "jarvis" does not exist` が15秒ごとに出る |
| `docker-compose.yml:480` | postgres サービスの環境変数に `POSTGRES_DB=${POSTGRES_DB}` がある |
| `docker-compose.yml:145` | backend が postgres に `condition: service_healthy` |
| `docker-compose.yml:266` | celery-worker が postgres に `condition: service_healthy` |
| `docker-compose.yml:365` | discord-gateway が postgres に `condition: service_healthy` |
| `.github/workflows/deploy.yml:420` | `docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress`（postgres は対象外・--no-deps） |
| `.github/workflows/deploy.yml:423` | `docker compose up -d --no-deps node-exporter promtail`（postgres 対象外） |
| `.github/workflows/deploy.yml:457` | `docker compose up -d --no-deps --force-recreate nginx`（postgres 対象外） |
| `.github/workflows/deploy.yml:510` | `docker compose up -d --force-recreate celery-worker celery-beat discord-gateway`（--no-deps なし。postgres は --force-recreate の対象ではないが、設定差分があれば depends_on 経由で再作成されうる） |
| `.github/workflows/deploy.yml:686` | ロールバック経路の `docker compose up -d --remove-orphans`（サービス名指定なし＝postgres を含む全サービス。healthcheck 定義が変わっていれば postgres が再作成されうる） |
| `.github/workflows/deploy.yml:1008` | `docker compose up -d --no-deps --force-recreate nginx`（postgres 対象外） |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 通常デプロイで postgres が再作成されるか | deploy.yml の up 行を全走査（上表）。通常経路は --no-deps で postgres 非対象 | 解消済み（通常経路は再作成なし）。510行は --no-deps なしで依存の postgres が設定差分で再作成される可能性があり、未確認 |

**未解決ゼロ確認**: 510行・686行の実挙動（postgres 再作成の有無）は本番反映時に `docker inspect` の StartedAt で確認する。
