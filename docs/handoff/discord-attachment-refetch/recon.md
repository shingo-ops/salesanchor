# recon: discord-attachment-refetch

この文書は何か: Discordで受信した画像のURLが期限切れになったとき、画面が再取得APIを呼ぶ流れの現状調査メモです。

## 調査基準

- 基準 SHA (origin/main): `ebbc024115c8f097bce3aa657e210d59ff638331`
- 調査日: 2026-09-01

## 1. Discord REST 共通関数の引数

`backend/app/services/discord_rest.py:34`

```python
async def discord_api_request(
    *,
    method: str,
    path: str,
    bot_token: str,
    json: dict[str, Any] | None = None,
    expected_statuses: tuple[int, ...] = (200, 201, 204),
) -> dict[str, Any] | None:
```

引数: method / path / bot_token / json（省略可）/ expected_statuses（省略可）

## 2. platform 取得箇所

`backend/app/routers/leads.py:1322`

```python
    platform = msg_row[0]
```

直前の SELECT:
```python
    msg_q = await db.execute(
        text(
            f"SELECT platform FROM {meta_messages_t} "
            "WHERE message_id = :message_id AND lead_id = :lead_id AND tenant_id = :tenant_id"
        ),
        ...
    )
```

## 3. 画面側の再取得呼び出し（プラットフォーム非依存）

`frontend/src/pages/inbox/InboxMessageThread.tsx:164`

```typescript
          `/api/v1/leads/${selectedLeadId}/messages/${encodeURIComponent(msgMetaId)}/attachment-url`,
```

フロントエンドは platform 値に関わらず同一エンドポイントを呼ぶ。
platform による分岐はバックエンド側（`backend/app/routers/leads.py:1326`）で行う。
