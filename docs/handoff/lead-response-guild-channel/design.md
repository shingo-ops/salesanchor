# design: lead-response-guild-channel

## 目的

`LeadResponse` スキーマに `discord_guild_channel_id` を追加し、
フロントエンドの `LeadDetail.discord_guild_channel_id` が常に API 値を受け取れるようにする。

ADR-091 が定義する Discord Bot スコープにおいて、チケット専用チャンネルIDをAPIレスポンスへ含めることは必須要件。

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

## 外部・過去事例の参照と我々への応用

ADR-091 で定義された Discord Bot スコープでは、`discord_guild_channel_id`（チケット専用チャンネルID）を
メッセージ送信先として使用する設計が確定している。
フロントエンド（`useInboxState.ts:608-611`）も同フィールドで送信可否を判定している。
スキーマ側の欠落のみが原因で API レスポンスに含まれていなかった典型的な「定義漏れ」パターン。

## 触るファイル

`backend/app/schemas/lead.py`

## 削除するファイル

なし

## 弊害・リスク

- `str | None = None` のオプショナルフィールドなので後方互換性あり
- フロントは既に型定義済みなので追加の変更不要

## 維持の仕組み

- 守り手: 人手で守る（スキーマ追加のみ・自動テスト範囲外）
