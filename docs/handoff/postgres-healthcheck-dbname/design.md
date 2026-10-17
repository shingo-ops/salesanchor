# Phase 3 設計 — postgres healthcheck の DB 名指定

**対象ADR**: ADR-1012
**recon**: docs/handoff/postgres-healthcheck-dbname/recon.md
**日付**: 2026-10-17
**担当**: Sonnet

## 外部・過去事例の参照と我々への応用

不要: PostgreSQL 既定動作の設定漏れ修正のため

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1 本番 postgres ログの `database "jarvis" does not exist` が反映後10分で0件 | `docker logs --since 10m <postgres コンテナ> 2>&1 | grep -c 'database "jarvis" does not exist'` で数える |
| K2 postgres コンテナの Health.Status が healthy | `docker inspect --format '{{.State.Health.Status}}' <postgres コンテナ>` で確認 |
| compose 展開後の healthcheck に DB 名が入る | `POSTGRES_USER=jarvis POSTGRES_DB=jarvis_db docker compose -f docker-compose.yml config | grep -n pg_isready` |

## 技術 How・KPI

- 変更: `docker-compose.yml:486` の1行のみ（`-d ${POSTGRES_DB:-postgres}` を追加）
- KPI: K1=0件、K2=healthy

## 弊害・トレードオフ

- healthcheck 定義が変わるため、postgres が再作成される経路（deploy.yml:510・686）では再起動が起きうる → 通常経路（--no-deps）では再作成されない。反映は PO 判断で行う。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | docker-compose.yml 1行変更 | Sonnet |

## 継続

- 完了後の監視: 反映後10分の postgres ログ（K1）と Health.Status（K2）

## 維持の仕組み

- 反映後10分の postgres ログ（K1）と Health.Status（K2）を PO/Opus が観測。healthcheck は compose に常設され、再発すれば同じログで検知できる。
