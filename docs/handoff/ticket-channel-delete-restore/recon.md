# recon: チケットの部屋が消されたときの自動復旧

- 日付: 2026-10-02
- 実測基準: origin/main 9b1166421（git fetch 後）
- PO決定（原文）: Q「今後、チケットの部屋が消されたときに自動で復旧できるようにしますか？」
  A「自動で直す (推奨)」。選択肢の文: チケットの部屋が消されたら、そのお客様に ticket-start を自動でまた見えるようにし、リードに残った古い部屋の番号も消します。お客様はボタンを押せば新しい部屋ができます（アプリの会話履歴はそのまま）。Discordとやり取りする部分が止まっている間に消された分は、起動時に点検して直します。

## 1. ADR 検索

`git grep -il ticket docs/adr/` と `docs/adr/FEATURE-INDEX.md` を検索した。

- docs/adr/ADR-091-discord-bot-scope-definition.md（Bot の範囲・ticket-start へのボタン投稿）
- docs/adr/ADR-159-staff-identity-on-discord.md（担当者名義の返信）
- チャンネル削除時の復旧を定めた ADR は無い（`git grep -n "ticket.start" docs/adr` は ADR-091:63 のみ）。

## 2. 現状（file:line）

- ticket-start の本人非表示: backend/app/discord_gateway/ticket_channel_creator.py:177-212 `_hide_ticket_start`
  （`config["ticket_button_channel_id"]` :187、`set_permissions(member, view_channel=False)` :199）
- 保存済みチャンネルが guild に無い場合は再作成: backend/app/discord_gateway/ticket_channel_creator.py:280-296（警告ログ→再作成）、:299-344
- lead への部屋ID書き込み: backend/app/discord_gateway/ticket_channel_creator.py:129-145 `_update_lead_channel_id`
- Gateway に CHANNEL_DELETE ハンドラは無い: backend/app/discord_gateway/client.py のイベントは on_ready / on_resumed / on_disconnect / on_interaction / on_raw_reaction_add/remove / on_message のみ。intents.guilds=True（client.py:65 付近）
- leads.discord_guild_channel_id は VARCHAR(50): migrations/20260602_120000_add_discord_ticket_config.sql:35
- Discord 公式: ギルドチャンネルの削除は元に戻せない（"Deleting a guild channel cannot be undone"）

## 3. discord.py 2.4.0 の実測

- `GuildChannel.set_permissions(target, *, overwrite=None, reason=...)`: target は Member/Role のみ。それ以外は `ValueError('target parameter must be either Member or Role')`（site-packages/discord/abc.py の set_permissions）。つまり退会済みメンバーに `discord.Object` は使えない。
- `HTTPClient.delete_channel_permissions(channel_id, target, *, reason=None)` は user_id を直接渡せる（site-packages/discord/http.py:1935-1939）。退会済み分はこちらを使う。
