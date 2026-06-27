# recon: ticket-start チャンネル bot 書込許可追加（403修正）

関連ADR: ADR-146（B方式）  
調査日: 2026-06-28

## 確認事項

### F1. ボタン設置失敗ログ（本番バックエンド）

```
[discord_rest] api error method=POST path=/channels/1520509440908988557/messages status=403
[discord_auto_setup] button post failed ch=1520509440908988557: Discord API エラー: HTTP 403: {"message": "Missing Permissions", "code": 50013}
[discord_rest] api error method=POST path=/channels/1520516388010070108/messages status=403
[discord_auto_setup] button post failed ch=1520516388010070108: Discord API エラー: HTTP 403: {"message": "Missing Permissions", "code": 50013}
```

### F2. 原因箇所

`backend/app/routers/discord_auto_setup.py:637-657` — `_ticket_ch_overwrites` 関数。

bot のロールは `Sales Anchor`（id: 1520508875298574569 / 1520516218665308201）だが、
ticket-start の overwrite は `Sales Anchor Staff` ロールにしか SEND_MESSAGES を付与していない。

`backend/app/routers/discord_auto_setup.py:642-656` の生コード:

```python
overwrites: list[dict[str, Any]] = [
    {"id": guild_id, "type": 0, "allow": str(_VIEW_CHANNEL | _READ_MESSAGE_HISTORY), "deny": str(_SEND_MESSAGES)},
]
if staff_role_id:
    overwrites.append({"id": staff_role_id, "type": 0, "allow": str(_SEND_MESSAGES), "deny": "0"})
# ← bot user (type=1 member overwrite) が存在しない
```

### F3. bot_user_id の取得元

`backend/app/routers/discord_auto_setup.py:146-155` — `GET /users/@me` で取得済み、呼び出し箇所 :255 で参照可能。

### F4. カテゴリには bot overwrite が付いている

`backend/app/routers/discord_auto_setup.py:207-219` — カテゴリは `{"id": bot_user_id, "type": 1, "allow": VIEW+SEND+READ+MANAGE}` 付与済み。チャンネルレベルで欠落。

### F5. 呼び出し箇所は1箇所のみ

```
backend/app/routers/discord_auto_setup.py:255
```

波及なし。

### F6. 既存チャンネルの overwrite は再実行で更新されない

`backend/app/routers/discord_auto_setup.py:487-502` — チャンネルが存在すれば `status="skipped"` を返し overwrite は送信しない。テストサーバーは手動削除→再実行で対応。
