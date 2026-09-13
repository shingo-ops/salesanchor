# recon: Discord 送信判定をチケット専用チャンネル一本化へ切り替えた調査記録

この文書は何か: 受信箱の Discord 送信先をチケット専用チャンネルのみに絞るために変更したファイルと行番号を記録したもの。

## 対象ブランチ

`release/discord-guild-channel-only`（base: origin/main = `f1dc00d0bd208480c642b6a9bda1696f341568f7`）

## 関門0 実測結果

### frontend/src/pages/inbox/useInboxState.ts（変更前）

`frontend/src/pages/inbox/useInboxState.ts:608-611`

```
  // AC1.5: Discord DM channel が未設定の場合は送信不可
  const currentPlatform = messagesData?.lead?.platform ?? null;
  const discordDmChannelMissing = currentPlatform === "discord" && !leadDetail?.discord_dm_channel_id;
  const canSend = !!messagingWindow?.can_send_at_all && !discordDmChannelMissing;
```

### backend/app/routers/leads.py（変更前）

`backend/app/routers/leads.py:1887-1922`

```
    """Discord DM 経由でメッセージを送信し、meta_messages に outbound 行を INSERT して返す。
    ...
    ch_q = await db.execute(
        text(
            f"SELECT discord_user_id, discord_dm_channel_id,"
            f" discord_guild_channel_id FROM {leads_t}"
            f" WHERE id = :id AND tenant_id = :tenant_id"
        ),
        ...
    )
    ch_row = ch_q.first()
    if ch_row is None or (not ch_row[1] and not ch_row[2]):
        raise HTTPException(...)
    discord_user_id = ch_row[0]
    dm_channel_id = str(ch_row[2]) if ch_row[2] else str(ch_row[1])
```

## 影響範囲（実測）

| ファイル | 変更内容 |
|---|---|
| `backend/app/routers/leads.py:1887-1922` | 送信先を guild_channel_id のみに変更 |
| `backend/tests/test_discord_inbox.py:229,234,237,243` | ヘルパに guild_channel_id 引数追加 |
| `frontend/src/pages/inbox/useInboxState.ts:114,608-611,883` | 判定識別子を discordChannelMissing に変更 |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:37,62,533,585` | 識別子と翻訳キーを変更 |
| `frontend/src/pages/inbox/InboxPage.tsx:163` | prop 名を変更 |
| `frontend/src/locales/ja.json:969` | キーと文言を変更 |
| `frontend/src/locales/en.json:969` | キーと文言を変更 |

## ADR 参照

- `docs/adr/ADR-091-discord-bot-scope-definition.md` — Discord Bot 担当業務スコープ定義

## 関連 migration

- `migrations/091_add_leads_discord_messaging_columns.sql` — `discord_dm_channel_id` 列定義（削除しない）
- `discord_guild_channel_id` 列は既に存在（削除しない）
