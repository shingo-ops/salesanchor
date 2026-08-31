# design: 受信箱からチケットチャンネルへ送信＋添付の受信に対応

## 対象ADR
- ADR-091: `docs/adr/ADR-091-discord-bot-scope-definition.md`
- ADR-146 はコード内コメントでのみ参照され、docs/adr/ 配下に文書は存在しない（2026-08-31 実測）。

## recon 参照
`docs/handoff/discord-inbox-sync/recon.md`

## 変更概要

### 送信経路（_send_discord_message）
チケット専用チャンネル（`discord_guild_channel_id`）を優先し、未設定時は DM チャンネル（`discord_dm_channel_id`）にフォールバックする。
Discord REST API はどちらも `/channels/{id}/messages` で送信できるため、`send_discord_dm` の I/F 変更なし。

### 添付受信（ticket_channel_writer.py）
顧客がチケットチャンネルに画像や PDF を送信した場合、`_extract_first_attachment` が URL と種別を抽出し `meta_messages.attachment_url` / `.attachment_type` に保存する。
Meta 経路（webhook.py）と同じカラム設計を踏襲。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `discord_guild_channel_id` 設定済みリードへのスタッフ送信がチケットチャンネルに届く | pytest `test_message_send.py` PASS + 本番スモーク |
| `discord_guild_channel_id` 未設定・`discord_dm_channel_id` あり → DM に届く | pytest `test_message_send.py` PASS |
| 両チャンネルとも未設定 → HTTP 409 が返る | pytest `test_message_send.py` PASS |
| 顧客がチケットチャンネルに添付付きメッセージを送ると `meta_messages.attachment_url` が保存される | pytest `test_discord_ticket_attachment.py` 5/5 PASS |
| 添付なしメッセージは `attachment_url` = NULL のまま保存される | pytest `test_discord_ticket_attachment.py` PASS |
| 変更3ファイル（leads.py, ticket_channel_writer.py, test_discord_ticket_attachment.py）のみ | `git diff --numstat` で確認済み |

## 触るファイル
- `backend/app/routers/leads.py`
- `backend/app/discord_gateway/ticket_channel_writer.py`
- `backend/tests/test_discord_ticket_attachment.py`（新規）

## 削除するファイル
なし

## 外部・過去事例
- Discord REST API `/channels/{channel_id}/messages`: DM チャンネルとギルドチャンネルで同一エンドポイント（公式 API v10 仕様）
- Meta Messenger webhook.py の `attachment_url` / `attachment_type` 設計を踏襲（プロジェクト内事例）

## 維持の仕組み

- 守り手: `backend/tests/test_discord_ticket_attachment.py`
- 対象: `_extract_first_attachment` の戻り値仕様（添付なし・image・file・URL欠落の分岐）が
  壊れると、顧客の添付が受信箱に出なくなる。
- 送信先の切替（チケットチャンネル優先・DMフォールバック）は
  `backend/tests/test_message_send.py` が守る。
- 実動作の確認は人手で守る。理由: Discord 実環境との往復は自動テストで再現できないため、
  tenant_006 での往復確認を別途行う。

## GO記録

GO発行者:
日時:
GO原文:
バックアップ確認:
