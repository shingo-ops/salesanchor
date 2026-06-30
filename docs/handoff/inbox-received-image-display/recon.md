# recon.md — 受信画像表示（Meta Messenger/Instagram）

- 作成: 2026-06-26
- 基準: origin/main (432831c6740b0db8647c5c8ec97a592f5a26c82e)

## R-F1 attachment_url / attachment_type 列の実在

`migrations/100_add_meta_messages_image_columns.sql:33-34`
```sql
ADD COLUMN IF NOT EXISTS attachment_url  TEXT,
ADD COLUMN IF NOT EXISTS attachment_type VARCHAR(20)
```
コメント（:7）に「受信時は Meta CDN URL」と明記済み。**新規 migration 不要・GO 不要**。

## R-F2 受信 INSERT に列が無い（原因）

`backend/app/routers/webhook.py:631-655`（変更前）
- `INSERT INTO meta_messages` の列リストに `attachment_url`, `attachment_type` が存在しない。
- `_iter_inbound_messages` の `:356/:369/:400` で `bool(msg.get("attachments"))` に変換し URL を捨てていた。

## R-F3 message_id と platform は保存済み（取り直し前提）

`backend/app/routers/webhook.py:651` — `"message_id": message_id`
`backend/app/routers/webhook.py:648` — `"platform": platform`（"messenger" or "instagram"）

## R-F4 page_access_token 取得・復号の土台

`backend/app/routers/leads.py:44` — `from app.services import encryption, meta_graph`
`backend/app/routers/leads.py:1432-1439` — `_decode_token_blob()` 定義済み
`backend/app/routers/leads.py:1488` — `encryption.decrypt(_decode_token_blob(encrypted_token_blob))`

## R-F5 取り直し API 関数 — 変更前は未実装

`backend/app/services/meta_graph.py:1197-1219`（変更前 `__all__`）— `fetch_attachment_url` なし。新規追加。

## R-F6 フロント表示側

`frontend/src/pages/inbox/InboxMessageThread.tsx:332-342`（変更前）
- `<img src={msg.attachment_url}>` に `onError` ハンドラなし。
- 取り直し・ライトボックス・期限切れ表示すべて未実装。

## R-F7 既存 endpoint の認証パターン（流用）

`backend/app/routers/leads.py:901-904` — `@router.get("/leads/{lead_id}/messages", dependencies=[Depends(require_permission("messaging.view"))])`
`backend/app/routers/leads.py:1166-1168` — 翻訳 endpoint も同じ `messaging.view` 権限。

## R-F8 対象 ADR

- ADR-110: 送信下訳プレビュー（本 PR は受信画像のため参照のみ）
- migration 100 コメント: ADR-089 関連（画像送信 Sprint 2）
