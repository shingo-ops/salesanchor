# recon: ボタン案内・ウェルカムをサーバー名義で投稿

> 作成: 2026-10-02 | 基準: origin/main 946e6dbcd | 対象ADR: ADR-159, ADR-091

## PO 決定（原文）
Q「ボタンの案内とチケットの案内文を、各サーバーの名前とアイコンで投稿するように作りますか？」
A「作る (推奨)」（名前＝サーバー名、アイコン＝サーバーのアイコン（毎回Discordから取得、DBに複製しない）。「アプリ」の印は残る。ephemeral は Sales Anchor 名義のまま）

## 既存 ADR 検索
- `git grep -il webhook docs/adr/` / FEATURE-INDEX 確認: ADR-159（担当者名義 webhook、docs/adr/ADR-159-staff-identity-on-discord.md）、ADR-091（Bot スコープ、docs/adr/ADR-091-discord-bot-scope-definition.md）。

## 現在地（file:line、origin/main）
- ボタン投稿（auto-setup）: `backend/app/routers/discord_auto_setup.py:593` で `bot_texts.ticket_button_payload()` を Bot 名義 POST。
- ボタン投稿（deploy-button）: `backend/app/routers/discord_ticket_config.py:257` 同上。
- ウェルカム: `backend/app/discord_gateway/ticket_channel_creator.py:324` `new_channel.send(welcome_template)`（Bot 名義）。
- ペイロード: `backend/app/discord_gateway/bot_texts.py:58` `ticket_button_payload()`（custom_id=ticket_open）。
- webhook 送信基盤: `backend/app/services/discord_webhook_sender.py:303` `send_as_staff`（Bot 作成 = application-owned webhook）。
- ボタン押下の受信: `backend/app/discord_gateway/client.py:152` `on_interaction`。

## 事実と出典
- Application-owned webhook は components を常に送れる。非 owned は interactive component 不可。出典: https://github.com/discord/discord-api-docs/blob/main/developers/resources/webhook.mdx （Execute Webhook、`with_components` の説明）。当アプリの webhook は Bot が作成するため application-owned。
- ギルドアイコン URL: `https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png`。ハッシュが `a_` で始まるとアニメーション（gif）。出典: https://discord.com/developers/docs/reference#image-formatting
- GET /guilds/{guild_id}（Bot token）で name / icon を取得できる。出典: https://discord.com/developers/docs/resources/guild#get-guild

## 未確認
- [?] webhook 投稿のボタン押下が INTERACTION_CREATE として当アプリの Bot に届くか。docs に明記なし。PO が tenant_001 テストサーバーで実機確認する（design.md 受入条件）。
