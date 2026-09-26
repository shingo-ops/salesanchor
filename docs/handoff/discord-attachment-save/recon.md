# recon — Discord添付の自社保存（便3）

> この文書は何か（専門用語なしの1行）:
> 顧客がDiscordに送った画像を自分たちのサーバーに保管する処理を作る前に、
> 今のコードがどうなっているかを実際に見て記録したもの。

対象ADR: docs/adr/ADR-091-discord-bot-scope-definition.md
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-02）

### 受信処理の現状

`backend/app/discord_gateway/ticket_channel_writer.py`（206行）

- 12行目: `from sqlalchemy import text`
- 17行目: `from app.auth.dependencies import set_tenant_context`
- 33行目: `def _extract_first_attachment(message)` の定義。
  Discord メッセージから最初の添付の URL と種別を取り出す。
  戻り値は `(url, kind)`。kind は image / video / audio / file。
- 58行目: `async def _lookup_ticket_channel_lead(...)` の定義。
  `discord_guild_channel_id` から lead を引く。
- 87行目: `async def process_ticket_channel_message(...)` の定義。
- 122行目: `await set_tenant_context(db, tenant_id)` を実行済み。
  同一トランザクション内では追加のテナント設定は不要。
- 156行目: `attachment_url, attachment_type = _extract_first_attachment(message)`
- 159行目以降: `meta_messages` への INSERT。
  `ON CONFLICT (message_id) WHERE message_id IS NOT NULL DO NOTHING`。

### HTTPクライアントの既存の使い方

`backend/app/services/discord_sender.py`

- 20行目: `import httpx`
- 25行目: `_TIMEOUT_SEC = 10.0`
- 69行目: `async with httpx.AsyncClient(timeout=_TIMEOUT_SEC) as client:`

### テナント文脈の設定

`backend/app/auth/dependencies.py:255` `async def set_tenant_context(db, tenant_id)`

`SET search_path` / `SET app.tenant_id` / `SET app.is_operator` を一括設定する。
生の `SET search_path` を書くことは CI grep チェックが禁止している。

### 保存先の前提

- 便1（PR #3195）で `attachments_data` ボリュームを backend にマウント済み。
  `docker inspect astro-webapp-backend-1` の Mounts に
  `/data/attachments` (rw) を実測確認済み。
- 便2（PR #3199）で `tenant_XXX.lead_attachments` を5テナントに作成済み。
  migration 実行ログで tenant_001 / 003 / 004 / 005 / 006 の作成完了を確認済み。

### Discord CDN の挙動（2026-09-01 実測）

- ブラウザから `cdn.discordapp.com` へのリクエストが 503（6回すべて再現）。
- 同じURLをサーバー（prod1）から取得すると 200（3回とも成功・295679バイト）。
- 署名パラメータ `ex` は翌日の日時であり、期限切れではない。

## 本便で変更する箇所

`backend/app/discord_gateway/ticket_channel_writer.py` のみ。

- import に `os` / `pathlib.Path` / `httpx` を追加
- `_save_attachment_to_disk` を新設
- `meta_messages` INSERT の後、翻訳キューの前に保存処理を挿入

既存の `_extract_first_attachment` / `_lookup_ticket_channel_lead` /
`meta_messages` への INSERT は変更しない。
