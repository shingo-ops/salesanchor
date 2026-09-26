# design: Discord 送信判定を discord_guild_channel_id のみに切り替え

対象ADR: ADR-091
recon: docs/handoff/discord-guild-channel-only/recon.md

## 変更の方針

Discord 送信先の決定ロジックを「チケット専用チャンネル（discord_guild_channel_id）のみ」に一本化する。
従来の DM チャンネル（discord_dm_channel_id）フォールバックは廃止する。

- 変更前: `discord_guild_channel_id` が優先、未設定時は `discord_dm_channel_id` にフォールバック
- 変更後: `discord_guild_channel_id` のみ参照。未設定 → 409

## 外部・過去事例の参照と我々への応用

Discord の Bot 接続では「DM チャンネル」と「サーバーチャンネル（guild channel）」の 2 種類の送信先が存在する。
DM チャンネルは顧客が最初にメッセージを送って初めて開通する非同期モデルであり、
チケット専用チャンネルは管理者がセットアップ時に確定するため常に既知である。

過去の DM フォールバック設計（PR #3179）は移行期の互換措置であった。
チケットフローが確立した現在は、サーバー内チャンネルへの統一が運用上の一貫性を高める。
Discord 社のガイドラインでも「Bot はできる限りサーバーチャンネルで通知し、DM は最小限に」とされている。

我々への応用: DM チャンネル ID は引き続き `leads` テーブルに保持するが（列削除禁止）、
送信経路からは除外する。これにより将来の再利用余地を残しつつ、現在の判定を単純化する。

## 受入基準

| 基準 | 検証方法 |
|---|---|
| `discord_guild_channel_id` が設定済みのリードへ送信 → 201 | `test_send_discord_success_inserts_outbound_meta_message` PASS |
| `discord_guild_channel_id` が未設定のリードへ送信 → 409 | `test_send_discord_returns_409_when_no_dm_channel` PASS |
| Discord API エラー → 502 | `test_send_discord_returns_502_on_discord_send_error` PASS |
| 受信箱画面で discord かつ `discord_guild_channel_id` 未設定 → 送信ボタン無効 + 案内文言表示 | `discordChannelMissing` フラグが true の場合 placeholder / title に `t("inbox.discordChannelMissing")` が表示されること（人手確認） |
| `discordDmChannelMissing` の参照が frontend/src/ に残っていない | `grep -rn 'discordDmChannelMissing' frontend/src/` → 0件 |

## 維持の仕組み

- 守り手: `backend/tests/test_discord_inbox.py`（`_insert_discord_lead` に `discord_guild_channel_id` 引数追加済み）
- 対象: `_send_discord_message` が `discord_guild_channel_id` のみを参照すること
- 409 テスト（`test_send_discord_returns_409_when_no_dm_channel`）が guild_channel_id=None を前提とするように修正済み
- `discord_dm_channel_id` 列は `migrations/091_add_leads_discord_messaging_columns.sql` で定義されており、削除しない

## GO記録

GO発行者:
日時:
GO原文:
バックアップ確認:
