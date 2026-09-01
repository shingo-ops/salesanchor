# design: lead-response-guild-channel

## 目的

`LeadResponse` スキーマに `discord_guild_channel_id` を追加し、
フロントエンドの `LeadDetail.discord_guild_channel_id` が常に API 値を受け取れるようにする。

## recon 相互参照

- recon: `docs/handoff/lead-response-guild-channel/recon.md`
- ルーター SELECT: `backend/app/routers/leads.py:76`
- フロント参照: `frontend/src/pages/inbox/inbox.types.ts:99`
- フロント使用: `frontend/src/pages/inbox/useInboxState.ts:608-611`

## 変更内容

### `backend/app/schemas/lead.py`（267行目に1行追加）

```python
# 変更前
    discord_dm_channel_id: str | None = None
    # Discord role sync fields ...

# 変更後
    discord_dm_channel_id: str | None = None
    discord_guild_channel_id: str | None = None
    # Discord role sync fields ...
```

## KGI / 検証基準

| 基準 | 検証方法 |
|---|---|
| API レスポンスに `discord_guild_channel_id` キーが含まれる | `GET /api/leads/{id}` のレスポンス JSON で確認 |
| 既存テストが壊れていない | CI backend test PASS |

## 触るファイル

`backend/app/schemas/lead.py`

## 削除するファイル

なし

## 弊害・リスク

- `str | None = None` のオプショナルフィールドなので後方互換性あり
- フロントは既に型定義済みなので追加の変更不要
