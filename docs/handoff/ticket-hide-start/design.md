# design: ticket-start 本人非表示（チケット発行後）

設計日: 2026-06-28 / 担当: CC / recon 参照: docs/handoff/ticket-hide-start/recon.md / 関連: ADR-091

## 目的

顧客がチケットボタンを押して専用チャンネルが用意された後、**その顧客にだけ ticket-start を非表示**にする。  
構造的に同一人物の再押下を防ぎ、1人1チケットを徹底する。

## KGI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| ボタンを押した本人の画面から ticket-start が消える | 006_test の顧客役アカウントでチケット開封後、そのアカウントのチャンネル一覧から ticket-start が非表示になっていることを目視確認 |
| 他の未開封顧客には ticket-start が見えたまま | 別アカウント（未開封）から ticket-start が見えることを目視確認 |
| 既存受信箱への振り分けはデグレなし | チケットチャンネルへのメッセージが受信箱に届くことを確認 |

## 変更内容

### 追加: `_hide_ticket_start` ヘルパ関数（`ticket_channel_creator.py:171 直後`）

```python
async def _hide_ticket_start(
    guild: discord.Guild,
    config: dict,
    member: discord.Member,
    tenant_id: int,
) -> None:
    ticket_start_id = config.get("ticket_button_channel_id")
    if not ticket_start_id:
        return
    ticket_start_ch = guild.get_channel(int(ticket_start_id))
    if not isinstance(ticket_start_ch, discord.TextChannel):
        logger.warning(...)
        return
    try:
        await ticket_start_ch.set_permissions(member, view_channel=False)
    except Exception as exc:
        logger.warning(...)  # 失敗してもチケット発行は妨げない
```

### 追加: 既存チャンネル返却直前（`ticket_channel_creator.py:256 直前`）

```python
await _hide_ticket_start(guild, config, member, tenant_id)
return ch
```

### 追加: 新規チャンネル返却直前（`ticket_channel_creator.py:343 直前`）

```python
await _hide_ticket_start(guild, config, member, tenant_id)
return new_channel
```

### 変更しないもの

- 1人1チケット冪等ロジック（F1）: 変更なし
- 専用チャンネル内の権限・welcomeメッセージ: 変更なし
- 他テナント・他チャンネル: 影響なし

## 実装方針の判断

設計書では `discord_api_request(method="PUT", ...)` を示したが、`ticket_channel_creator.py` コンテキストに `bot_token` が存在しないため、  
**discord.py ネイティブの `channel.set_permissions(member, view_channel=False)`** を採用。  
Discord API 上は同じ `PUT /channels/{id}/permissions/{user_id}` に解釈される。

## 外部事例

- discord.py `TextChannel.set_permissions()`: 既存 `_bot_permission_overwrites`（同ファイル:145-161）が discord.py PermissionOverwrite を使っており、同じパターン。
- `discord_remove.py:90-116`: httpx 経由 DELETE の前例。今回は PUT 相当を discord.py 経由で実施（引数に bot_token 不要）。

## リスク・副作用

- **非表示失敗はチケット発行をブロックしない**: `except Exception` で吸収し `return new_channel` / `return ch` は実行される（設計合意）。
- **再問い合わせ導線の喪失**: ticket-start が本人非表示になると、担当者がチケットチャンネルを削除した場合に本人が再度ボタンを押せない。**担当者が Discord で本人の ticket-start 非表示を手動解除**して対応（案ア・設計合意）。
- **ロールバック**: revert PR で即時戻し可能（DB 変更なし）。
