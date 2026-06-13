# recon: Discord DM受信箱連携 実機検収

**日付**: 2026-06-14  
**ブランチ**: `feature/morimoto/discord-inbox-acceptance-check`  
**KGI**: 顧客Discord DM → Sales Anchor受信箱表示 + Sales Anchor返信 → 顧客Discord DM着信 が実機で成功すること

---

## 既存ADR検索結果

| ADR | 関連度 | 概要 |
|-----|--------|------|
| ADR-009 (参照先: `docs/adr/FEATURE-INDEX.md`) | HIGH | Discord Gateway基盤。discord.py WebSocket常駐プロセス |
| `docs/adr/ADR-091-discord-bot-scope-definition.md` | HIGH | Bot担当業務スコープ定義。KPI 7項目（DM受信箱は基盤として前提）|
| `docs/adr/ADR-119-lead-channels-and-lead-merge.md` | HIGH | lead_channels 二段lookup (ADR-119)。dm_writer.py の primary authority |
| `docs/adr/ADR-088-*` (inbox AI翻訳) | MEDIUM | meta_messages.platform='discord' は翻訳対象 |

---

## コード実証（file:line 引用）

### 1. DM受信経路

| ステップ | ファイル:行 | 内容 |
|---------|------------|------|
| Gatewayで受信 | `backend/app/discord_gateway/client.py:179` | `on_message` → guild判定で分岐 |
| DM経路振分け | `backend/app/discord_gateway/client.py:195-197` | `message.guild is None` → `_process_dm_message` |
| DBへ書き込み呼び出し | `backend/app/discord_gateway/client.py:218-228` | `dm_writer.upsert_lead_and_message(...)` |
| Lead二段lookup | `backend/app/discord_gateway/dm_writer.py:112-152` | ADR-119 Stage1(lead_channels) → Stage2(source) |
| Lead新規作成 | `backend/app/discord_gateway/dm_writer.py:156-175` | INSERT leads + lead_channels |
| discord_dm_channel_id保存 | `backend/app/discord_gateway/dm_writer.py:208-223` | UPDATE leads SET discord_dm_channel_id |
| meta_messages INSERT | `backend/app/discord_gateway/dm_writer.py:226-257` | platform='discord', direction='inbound', ON CONFLICT DO NOTHING |
| SSE通知 | `backend/app/discord_gateway/client.py:240-243` | `publish_inbox_update(tenant_id)` |
| conv_log書き込み | `backend/app/discord_gateway/dm_writer.py:260-280` | SA-02 Stage1: channel_type='discord' |

### 2. 受信箱UI経路

| ステップ | ファイル:行 | 内容 |
|---------|------------|------|
| platform='discord'判定 | `backend/app/routers/leads.py:793` | `if latest_platform == "discord":` |
| messaging_window | `backend/app/routers/leads.py:794-800` | can_send_at_all=True（24h制限なし） |

### 3. 返信経路

| ステップ | ファイル:行 | 内容 |
|---------|------------|------|
| platform判定分岐 | `backend/app/routers/leads.py:1166-1174` | platform=='discord' → `_send_discord_message` |
| dm_channel_id取得 | `backend/app/routers/leads.py:1496-1512` | SELECT discord_user_id, discord_dm_channel_id FROM leads |
| 未設定時409 | `backend/app/routers/leads.py:1503-1510` | discord_dm_channel_id IS NULL → 409 Conflict |
| Discord REST API送信 | `backend/app/services/discord_sender.py:56-89` | DISCORD_BOT_TOKEN_{tenant_id} → POST /channels/{ch}/messages |
| outbound INSERT | `backend/app/routers/leads.py:1543-1565` | meta_messages platform='discord' direction='outbound' |

### 4. 環境設定

| 確認項目 | ファイル:行 | 状態 |
|---------|------------|------|
| discord-gatewayサービス定義 | `docker-compose.yml:250` | `discord-gateway:` service with `DISCORD_BOT_TOKEN_4` |
| backendコンテナにもToken | `docker-compose.yml:96-97` | `DISCORD_BOT_TOKEN_4=${DISCORD_BOT_TOKEN_4:-}` |
| Tenant設定 | `docker-compose.yml:259-260` | `DISCORD_BOT_TOKEN_4`, `DISCORD_TENANT_CODE_4=highlife-jpn` |

---

## テスト結果

```
cd backend && python3 -m pytest tests/test_discord_inbox.py -q
10 passed, 93 warnings in 9.79s
```

### カバーされているテスト（`backend/tests/test_discord_inbox.py`）

| テスト名 | 内容 |
|---------|------|
| `test_send_discord_dm_success` | HTTP送信成功 → discord_msg_id返却 |
| `test_send_discord_dm_raises_on_non_200` | 403 → DiscordSendError("送信権限") |
| `test_send_discord_dm_raises_user_friendly_on_401` | 401 → DiscordSendError("Token が無効") |
| `test_send_discord_dm_raises_when_token_missing` | Token未設定 → DiscordSendError |
| `test_send_discord_returns_409_when_no_dm_channel` | dm_channel_id NULL → 409 |
| `test_send_discord_returns_502_on_discord_send_error` | API失敗 → 502 (meta_messages書かない) |
| `test_send_discord_success_inserts_outbound_meta_message` | 送信成功 → outbound行確認 (platform/message_id/recipient_id) |
| `test_get_messages_discord_messaging_window_can_send` | GET /messages → can_send_at_all=True, platform='discord' |
| `test_dm_writer_creates_new_lead` | 初回DM → lead新規作成 + conv_log書き込み (8 execute) |
| `test_dm_writer_idempotent_on_duplicate_message_id` | 重複メッセージ → ON CONFLICT DO NOTHING |

---

## 実機検収手順（VPS上での手動確認チェックリスト）

以下は本番VPS（`docker compose ps discord-gateway`）での確認手順。

### 環境確認

```bash
# 1. discord-gatewayが起動しているか
docker compose ps discord-gateway

# 2. Bot Tokenが渡っているか
docker compose exec discord-gateway env | grep DISCORD_BOT_TOKEN_4

# 3. Gatewayログで READY が出ているか
docker compose logs discord-gateway --tail=50
```

### 受信確認（顧客役DM送信後）

```bash
# 4. DBで lead が作成されているか
docker compose exec -T db psql -U postgres salesanchor -c \
  "SELECT id, customer_name, source, discord_user_id, discord_dm_channel_id FROM tenant_004.leads WHERE source LIKE 'discord:%' ORDER BY created_at DESC LIMIT 5;"

# 5. meta_messages に inbound が入っているか
docker compose exec -T db psql -U postgres salesanchor -c \
  "SELECT id, lead_id, platform, direction, sender_id, message_text, created_at FROM tenant_004.meta_messages WHERE platform='discord' ORDER BY created_at DESC LIMIT 10;"
```

### 返信確認（Sales Anchor UI から返信後）

```bash
# 6. outbound が保存されているか
docker compose exec -T db psql -U postgres salesanchor -c \
  "SELECT id, lead_id, platform, direction, message_id, message_text FROM tenant_004.meta_messages WHERE platform='discord' AND direction='outbound' ORDER BY created_at DESC LIMIT 5;"
```

---

## 検出された不足・ギャップ

なし。コード・テスト・docker-compose設定はすべて揃っている。

---

## 外部・過去事例参照

**該当なし（小規模検収タスク）。** Discord DM受信箱はADR-091で設計済みであり、新規技術選定なし。参照事例を調査する規模・新規性に該当しない。
