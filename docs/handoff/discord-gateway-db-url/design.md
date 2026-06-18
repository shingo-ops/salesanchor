# design — discord-gateway DATABASE_URL 未設定修正

**仕事名**: discord-gateway-db-url  
**日付**: 2026-06-17  
**対象ADR**: ADR-091  
**recon参照**: docs/handoff/discord-gateway-db-url/recon.md

---

## 外部・過去事例

- `backend` / `celery-worker` / `celery-beat` は同プロジェクト内の既存実装として `DATABASE_URL=${DATABASE_URL}` を docker-compose に記載済み（同一パターン）
- Discord.py ゲートウェイが asyncpg 経由で DB 接続するパターンは本プロジェクトの ticket_channel_creator.py が実装済み
- 該当なし（外部事例の参照は不要な単純設定漏れ修正）

---

## 技術 How

`docker-compose.yml` の `discord-gateway.environment` に1行追加:

```yaml
- DATABASE_URL=${DATABASE_URL}
```

あわせて `depends_on` に `postgres: condition: service_healthy` を追加（起動順保証）。

---

## KPI / 受け入れ基準

| 基準 | 検証方法 |
|-----|---------|
| デプロイ後 gateway コンテナに DATABASE_URL が存在する | `docker inspect astro-webapp-discord-gateway-1` の Env を確認 |
| `myapp_user` 接続失敗ログが出ない | `docker logs astro-webapp-discord-gateway-1` で確認 |
| ボタン押下でチケットチャンネルが作成される | Shingo が手作業で Discord ボタン押下確認 |

---

## 弊害 / トレードオフ

- `docker-compose.yml` 変更のため本番デプロイ時に `discord-gateway` コンテナが再起動する（一時的な接続断）
- `depends_on: postgres` 追加により起動順が強制されるが、postgres は既に先に起動しているため実質影響なし

---

## 計画票

1. `docker-compose.yml` 修正（1行追加）— 完了
2. PR 作成（base: develop）— 完了
3. develop マージ後、release PR で main へ反映
4. 本番デプロイ後、Shingo が環境変数確認 + Discord ボタン押下確認

---

## 継続

- 本番確認完了後、Discord Bot KGI を 100% 達成と報告
