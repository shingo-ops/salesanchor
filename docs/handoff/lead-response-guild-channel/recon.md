# recon: lead-response-guild-channel

## 調査基準

- 基準 SHA (origin/main): `92ccc22df4fa7939244b39731ed55e48d832ea60`
- 調査日: 2026-09-01

## 問題の概要

`discord_guild_channel_id` はDBに存在し、ルーターのSELECTに含まれているが、
`LeadResponse` スキーマに定義されていないため API レスポンスに含まれない。

## 調査結果

### DB カラム（事実・select 確認済み）

- `backend/app/routers/leads.py:76` — SELECT リストに `discord_guild_channel_id` あり
- `backend/app/routers/leads.py:1890,1902,1907` — `_send_discord_message` がこのフィールドを参照

### フロントエンド型（事実）

- `frontend/src/pages/inbox/inbox.types.ts:99` — `discord_guild_channel_id: string | null;` が `LeadDetail` interface に存在
- `frontend/src/pages/inbox/useInboxState.ts:608-611` — `discordChannelMissing` の判定で参照

### バックエンドスキーマ（問題点）

- `backend/app/schemas/lead.py:266` — `discord_dm_channel_id: str | None = None` あり
- `discord_guild_channel_id` の定義が **欠落**

### 関連 ADR

- なし（スキーマ漏れの補完・新規 ADR 不要）

## 影響範囲

| ファイル | 行 | 変更種別 |
|---|---|---|
| `backend/app/schemas/lead.py` | 267 | 追加（1行） |

## 削除ファイル

なし
