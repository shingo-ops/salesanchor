# recon: チケットボタン成功時メッセージの廃止

## PO 依頼（原文・2026-10-03）
「過去にチケットを開いたときのメッセージが表示されている。むしろこのメッセージを送る意味はあるか？機能自体不要であるので削除してくれ」

## 既存 ADR 検索
`git grep -i "ticket" docs/adr/` の結果、関連は次の2件。
- docs/adr/ADR-091-discord-bot-scope-definition.md（Bot 担当業務・チケット発行）
- docs/adr/ADR-159-staff-identity-on-discord.md（Discord 上の表示）
いずれも「成功時 ephemeral 返信」を要件とする記述なし（成功返信の存在はコード側のみ）。

## 現在地（origin/main 796f708b5 時点）
- backend/app/discord_gateway/client.py:on_interaction（旧 :151-:222 付近）
  - 冒頭 `await interaction.response.defer(ephemeral=True)`（component 操作では thinking=False のため ephemeral は無視され DEFERRED_UPDATE_MESSAGE=type 6 になる）
  - 成功時 `interaction.followup.send(bot_texts.TICKET_READY_TEMPLATE.format(...), ephemeral=True)`（「Your private channel is ready → #channel」）
  - エラー4種（GUILD_ONLY / GUILD_NOT_REGISTERED / TICKET_NOT_CONFIGURED / TICKET_CREATE_FAILED）は followup で ephemeral 送信
- backend/app/discord_gateway/bot_texts.py:40 `TICKET_READY_TEMPLATE`（使用箇所は client.py と tests のみ）
- backend/tests/test_discord_bot_texts.py:43,144（定数と成功返信のテスト）

## 公式ドキュメント・ライブラリ確認（Step 0）
Discord API docs（Context7 `/discord/discord-api-docs`、developers/interactions/receiving-and-responding.mdx）:
> DEFERRED_UPDATE_MESSAGE | 6 | For components, ACK an interaction and edit the original message later; the user does not see a loading state

> Interaction tokens are valid for 15 minutes and can be used to send followup messages but you must send an initial response within 3 seconds of receiving the event.

discord.py 2.4.0（インストール済みパッケージの interactions モジュール行653-713 `InteractionResponse.defer`）:
```
if parent.type is InteractionType.component or parent.type is InteractionType.modal_submit:
    defer_type = (
        InteractionResponseType.deferred_channel_message.value
        if thinking
        else InteractionResponseType.deferred_message_update.value
    )
    if thinking and ephemeral:
        data = {'flags': 64}
```
docstring: 「thinking … instead of the default deferred_message_update if both are valid」。
よって `defer()`（thinking=False）＝ type 6（無言 ACK）。現行 `defer(ephemeral=True)` も実質同じだが意図を明確にするため `defer()` にする。

## 事実と未確認
- 【事実】現行コードは thinking 指定なしのため既に type 6。ACK 方式は変更不要。変更は成功 followup の削除のみ。
- 【事実】エラー followup は現行でも type 6 の後に ephemeral 送信で動作している（PO が成功時の同方式メッセージを実際に見ている）。
- 【未確認】type 6 後の followup ephemeral を明記した公式文は今回の検索範囲では未発見（現行本番動作で代替確認）。
