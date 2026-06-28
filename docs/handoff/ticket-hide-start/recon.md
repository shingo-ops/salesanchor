# recon: ticket-start 本人非表示（チケット発行後）

調査日: 2026-06-28 / 担当: CC / 関連: ADR-091

## F1 — 再発行抑止は既存実装あり（冪等）

`backend/app/discord_gateway/ticket_channel_creator.py:204-218`

```python
lead_state = await _get_lead_state(session, tenant_id, discord_user_id)
existing_ch_id = lead_state.discord_guild_channel_id if lead_state else None

if existing_ch_id:
    ch = guild.get_channel(int(existing_ch_id))
    if isinstance(ch, discord.TextChannel):
        return ch  # ← 既存チャンネルをそのまま返す（2枚目を作らない）
    # Discord上で削除済みの場合は再作成へ fall-through
```

判定キー: `leads.discord_guild_channel_id`（`discord_user_id` でDB検索）。

## F2 — ticket-start 本人非表示の処理は存在しない

grep 結果（`backend/app/discord_gateway/` + `backend/app/routers/`）で `PUT /channels/{ticket_start_id}/permissions/{user_id}` に相当する処理なし。  
`backend/app/discord_gateway/ticket_channel_creator.py:145-161` および `backend/app/discord_gateway/ticket_channel_creator.py:227-256` の overwrite 設定はいずれも **新規チャンネル作成時のみ**。

## F3 — 既存の権限削除ヘルパが前例

`backend/app/routers/discord_remove.py:90-116`: チケットチャンネルからユーザーを切る `DELETE /channels/{ch}/permissions/{user}` が httpx で実装済み。bot_token を使う経路の前例。

## F4 — bot の MANAGE_ROLES / MANAGE_CHANNELS 権限確認済み

`backend/app/routers/discord_oauth.py:52-53`: `_DISCORD_PERMISSIONS = "805432406"` に Manage Roles + Manage Channels 含む。  
`set_permissions()` に必要な `MANAGE_ROLES` は付与済み。

## F5 — ticket_start_id は config dict に既にある

`backend/app/discord_gateway/ticket_channel_creator.py:42-56`（`get_ticket_config`）:

```sql
SELECT ticket_category_id, ticket_button_channel_id, staff_role_id, welcome_template
FROM public.tenant_discord_ticket_config WHERE tenant_id = :tid
```

`ticket_button_channel_id` が `config` dict に入る。`get_or_create_ticket_channel` の引数 `config: dict`（`backend/app/discord_gateway/ticket_channel_creator.py:179`）でそのまま参照可能。追加 DB クエリ不要。

## F6 — Discord手動削除後の再作成パスは残る

`backend/app/discord_gateway/ticket_channel_creator.py:219-224`: guild.get_channel() が None → fall-through で再作成。  
ticket-start が本人非表示になると **ボタンに辿り着けず再問い合わせ導線が消える**。設計上は担当者の手動解除で対応（案ア合意済み）。

## F7 — 既存チャンネル返却経路と新規作成経路は合流しない

`backend/app/discord_gateway/ticket_channel_creator.py:256`（既存返却）と `backend/app/discord_gateway/ticket_channel_creator.py:343`（新規作成）は別経路。  
`_hide_ticket_start` ヘルパを1つ定義し、両 return 直前にそれぞれ呼ぶ形が最小実装。

## 参照 ADR

- ADR-091（Discord Bot スコープ定義）: `docs/adr/ADR-091-discord-bot-scope-definition.md`
