# design: discord-gateway DB接続復旧

**GO**: Shingo 2026-06-17  
**優先度**: CRITICAL（Discord gateway の全 DB 操作が失敗中）  
**関連 ADR**: ADR-009  
**recon**: docs/handoff/runtime-config-audit/recon.md

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

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| gateway ログに `asyncpg.InvalidPasswordError` / `myapp_user` が出ない | `docker logs astro-webapp-discord-gateway-1 --tail=200 \| grep myapp_user` → 0 件 |
| Discord DM が DB に着地する | Shingo が `Sales Anchor#8667` に DM 送信 → `SELECT COUNT(*) FROM tenant_004.meta_messages WHERE platform='discord'` が 0 → 1 以上 |
| メモリ異常なし | デプロイ直後 `free -h` で available ≥ 200Mi |
| 他コンテナ影響なし | `docker compose ps` で backend/celery/postgres が healthy 維持 |

## デプロイ後監視

```bash
ssh prod1 "sudo sh -c 'free -h'"
# available が 200Mi 以上あることを確認（discord-gateway 256MB 上限）
```

## 外部・過去事例の参照と我々への応用

Docker Compose の environment セクションで env var を明示パススルーしないと `.env` の値がコンテナに届かないのは Docker Compose の既知の動作。  
- 公式 docs: `environment:` 記述なしでは `.env` の値はコンテナ内 `os.getenv` から参照不可（host shell の export と同様）。  
- 今回の教訓: `backend` コンテナが持つ env var を `discord-gateway` に複製する際、コードで `os.getenv` を使っているすべての変数を compose の `environment:` に明示することが必須。recon で「欠落+必要」1件だけと確認できたので 1 行追加で完結。
