# ADR-009: Discord Gateway Worker

**日付**: 2026-06-17  
**ステータス**: 実装済み（M2 完了・M3 完了）  
**担当**: Hikky-dev / shingo-ops

---

## 背景

Sales Anchor は Discord を CRM のメッセージングチャネルとして統合する。  
Discord Bot の WebSocket 接続を維持する専用コンテナ（`discord-gateway`）を `docker-compose.yml` に追加し、  
`backend` イメージを流用して `python -m app.discord_gateway.main` で起動する。

## 決定

- `discord-gateway` サービスを `docker-compose.yml` に追加（`backend` イメージ再利用）
- per-tenant Bot Token を環境変数 `DISCORD_BOT_TOKEN_<TENANT_ID>` で渡す
- `DATABASE_URL` を必須で渡す（`backend/app/database.py:8` がモジュールロード時に engine を生成するため）
- `depends_on: postgres: condition: service_healthy` で起動順を保証

## マイルストーン

| フェーズ | 内容 | 状態 |
|---------|------|------|
| M2 | Skeleton: READY / heartbeat ログ | 完了 |
| M3 | MESSAGE_CREATE → DB 書き込み | 完了 |
| M4 | DM / ticket channel 作成 | 完了 |
| M5 | bots テーブル拡張・テナント越境拒否 | 未着手 |
| M6 | Prometheus metrics / Grafana パネル | 未着手 |

## 影響

- `docker-compose.yml` の `discord-gateway` サービス定義
- `backend/app/discord_gateway/` 以下のコード
