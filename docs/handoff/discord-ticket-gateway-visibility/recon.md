# recon: Discord ticket channel gateway visibility + lead upsert

**仕事名**: discord-ticket-gateway-visibility  
**調査日**: 2026-06-19  
**対象ADR**: ADR-091  
**目的**: private ticket channel を gateway bot が読めるようにし、lead 未作成時も紐付けを作る実装の根拠を残す  
**スコープ**: 実装変更の要点確認のみ

---

## 1. 事実

| 観点 | file:line | 事実 |
|---|---|---|
| gateway bot の可視性付与 | `backend/app/discord_gateway/ticket_channel_creator.py:145-160` | `guild.me` に `view_channel / read_message_history / send_messages` を付与する overwrite を追加 |
| ticket channel 作成時の権限 | `backend/app/discord_gateway/ticket_channel_creator.py:226-243` | @everyone は拒否しつつ、member / staff_role / gateway bot を許可 |
| 既存 lead の再利用 | `backend/app/discord_gateway/ticket_channel_creator.py:203-218` | `discord_user_id` で既存 lead の `discord_guild_channel_id` を引いて冪等に返す |
| lead 未作成時の作成 | `backend/app/discord_gateway/ticket_channel_creator.py:288-341` | `leads` に `channel_type='discord'`, `initiative='inbound'`, `discord_user_id`, `discord_guild_channel_id` を入れて upsert |
| 新規 lead 連携テスト | `backend/tests/test_discord_ticket_channel.py:166-210` | lead 未作成→作成、bot overwrite、`lead_channels` 補完を確認 |
| 既存 lead の再利用テスト | `backend/tests/test_discord_ticket_channel.py:214-254` | 既存 channel を再作成せず返す冪等性を確認 |

---

## 2. 結論

- private ticket channel は gateway bot が閲覧できる必要がある。
- opener が lead でない場合でも、ticket 作成時に lead を作成して `discord_guild_channel_id` を保存すれば、以後の受信経路が成立する。
- この修正は migration を伴わず、既存の `leads` 列で完結する。
