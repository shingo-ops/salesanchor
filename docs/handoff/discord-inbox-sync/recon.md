# recon: 受信箱からチケットチャンネルへ送信＋添付の受信に対応

## 対象ADR
- ADR-091: Discord Bot スコープ定義（`docs/adr/ADR-091-discord-bot-scope.md`）
- ADR-146 B方式: 単一共有 DISCORD_BOT_TOKEN（`docs/adr/ADR-146-discord-bot-token-sharing.md`）

## 変更ファイルと根拠

### backend/app/routers/leads.py
- `_send_discord_message` 関数: `backend/app/routers/leads.py:1888`
  - 変更前: `discord_dm_channel_id` 1列のみ取得
  - 変更後: `discord_guild_channel_id` を3列目に追加し、チケットチャンネルを優先する
  - `SELECT discord_user_id, discord_dm_channel_id, discord_guild_channel_id`: `backend/app/routers/leads.py:1904`
  - チャンネル選択ロジック: `backend/app/routers/leads.py:1920`

### backend/app/discord_gateway/ticket_channel_writer.py
- `_extract_first_attachment` 関数を追加: `backend/app/discord_gateway/ticket_channel_writer.py:35`
  - Discord メッセージ添付から URL と種別（image/video/audio/file）を抽出する
  - Meta 経路 webhook.py と同じ `attachment_url` / `attachment_type` の意味を踏襲
- `process_ticket_channel_message` の INSERT に `attachment_url`, `attachment_type` を追加:
  - `backend/app/discord_gateway/ticket_channel_writer.py:156`
  - `backend/app/discord_gateway/ticket_channel_writer.py:160`

### backend/tests/test_discord_ticket_attachment.py（新規）
- `_extract_first_attachment` の5ケースユニットテスト
- 実際の Discord 接続不要（plain object シミュレート）

## 既存コードの参照

- `meta_messages` テーブルの `attachment_url`, `attachment_type` 列:
  マイグレーション `backend/migrations/versions/0100_*.py` にて既存定義済み
- `discord_guild_channel_id` 列: `backend/app/routers/leads.py` 内 `_create_ticket_channel` で書込済み
- `_extract_first_attachment` の設計参考: `backend/app/discord_gateway/dm_writer.py`（添付なし経路）
- `discord_sender.send_discord_dm` は `/channels/{channel_id}/messages` を送信先として受け取るため、
  チケットチャンネルID を渡しても DM チャンネルID と同じ API で動作する:
  `backend/app/services/discord_sender.py`
