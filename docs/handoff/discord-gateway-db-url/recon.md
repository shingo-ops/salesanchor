# recon — discord-gateway DATABASE_URL 未設定修正

**仕事名**: discord-gateway-db-url  
**日付**: 2026-06-17  
**対象ADR**: ADR-091  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docker-compose.yml:259` | discord-gateway サービス定義 |
| `docker-compose.yml:262` | environment セクション（DATABASE_URL 未記載を確認） |
| `backend/app/database.py:3` | `DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://myapp_user:password@...")` デフォルト確認 |
| `backend/app/discord_gateway/ticket_channel_creator.py:32` | `get_ticket_config` が DB アクセス（エラー発生箇所） |
| `backend/app/discord_gateway/client.py:73` | `from app.database import AsyncSessionLocal` — gateway が database.py を使用 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | gateway コンテナの DB 接続ユーザーが何か | `docker inspect astro-webapp-discord-gateway-1` + ログ確認 | ✅ 解消済み（myapp_user にフォールバック） |
| 2 | depends_on も必要か | `docker-compose.yml` の backend/celery-worker と同パターンを確認 | ✅ 解消済み（postgres 追加が必要） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

本番ログ（2026-06-17 07:44:18）から取得したエラー:

```
asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "myapp_user"
```

`backend` / `celery-worker` / `celery-beat` はいずれも `DATABASE_URL=${DATABASE_URL}` を持つが、
`discord-gateway` だけ環境変数が渡っていなかった。
