# design: discord-gateway DB接続復旧

**GO**: Shingo 2026-06-17  
**優先度**: CRITICAL（Discord gateway の全 DB 操作が失敗中）

---

## 問題

`discord-gateway` コンテナの `docker-compose.yml` に `DATABASE_URL` 環境変数が記載されておらず、`backend/app/database.py:8` のデフォルト fallback（`myapp_user:password@postgres:5432/myapp_db`）が使われていた。

本番 DB ユーザーは `jarvis` であり `myapp_user` は存在しない → 全 DB ops が `asyncpg.InvalidPasswordError` で失敗。

## 根拠（recon）

`docs/handoff/runtime-config-audit/recon.md §3` — 「欠落+必要」は `DATABASE_URL` のみ。

## 変更内容

`docker-compose.yml` の `discord-gateway.environment` セクションに 1 行追加:

```yaml
- DATABASE_URL=${DATABASE_URL}
```

加えて `depends_on: postgres: condition: service_healthy` を追加し、起動順序を保証。

## 変更範囲

- `docker-compose.yml` のみ（コード変更なし）
- 「1リリース1変更」の原則に準拠

## 検収条件

1. デプロイ後 `docker logs astro-webapp-discord-gateway-1` に `asyncpg.InvalidPasswordError` が出ない
2. Shingo が `Sales Anchor#8667` に Discord DM を送信
3. `SELECT COUNT(*), MAX(created_at) FROM tenant_004.meta_messages WHERE platform='discord'` が 1 以上に増える

## デプロイ後監視

```bash
ssh prod1 "sudo sh -c 'free -h'"
# available が 200Mi 以上あることを確認（discord-gateway 256MB 上限）
```
