# design.md — 受信画像表示（Meta Messenger/Instagram）

- 作成: 2026-06-26
- 対象 ADR: migration 100（ADR-089 連動）
- recon 参照: `docs/handoff/inbox-received-image-display/recon.md`

## 何を直すか

相手から届いた画像が受信箱に出ない。原因は `_iter_inbound_messages` が
`attachments[].payload.url` を `bool` に変換して捨てていること（recon R-F2）。
列は既存（recon R-F1）。migration ゼロ・GO 不要。

## 変更内容

### backend/app/routers/webhook.py
- `_extract_first_image_url(msg)` / `_extract_first_image_type(msg)` ヘルパー追加
- `_iter_inbound_messages` Format A/B yield に `attachment_url`, `attachment_type` を追加
- `_persist_meta_message` シグネチャに `attachment_url`, `attachment_type` を追加
- INSERT 列リスト・params に 2 列追加
- `process_messenger_event` 呼び出しに `m.get("attachment_url")`, `m.get("attachment_type")` を渡す

### backend/app/services/meta_graph.py
- `fetch_attachment_url(*, page_access_token, message_id) -> str | None` 新規追加
- `GET /{message_id}/attachments?fields=image_data,file_url` を呼び、`image_data.url` → `file_url` の順でURLを返す
- 失敗・404・IG 20件制限超過は None を返す（呼び出し側でフォールバック）

### backend/app/routers/leads.py
- `GET /leads/{lead_id}/messages/{message_id}/attachment-url` 新規追加
- `messaging.view` 権限で保護（既存パターン流用）
- page_access_token を `_decode_token_blob` + `encryption.decrypt` で復号（既存パターン流用）
- 成功: `{"url": "..."}` + DB の `attachment_url` を UPDATE
- 失敗: 404 + `detail="expired_or_unavailable"`

### frontend/src/pages/inbox/InboxMessageThread.tsx
- `resolvedUrl` (Record<number, string>) 状態追加
- `retriedRef` (useRef<Set<number>>) 追加（無限リトライ防止）
- `lightboxUrl` 状態 + `openLightbox` / `closeLightbox` 追加
- `handleAttachmentError(msgDbId, msgMetaId)` 追加（1回のみ再取得）
- `<img>` に `onError` / `onClick` (ライトボックス) 追加
- 取り直し失敗後は `inbox.imageExpired` テキスト表示
- 会話切り替え時に `resolvedUrl` / `retriedRef` リセット
- ライトボックスオーバーレイ（`role="dialog" aria-modal="true"`）追加

### frontend/src/locales/ja.json / en.json
- `inbox.imageExpired` = 「画像を表示できません（期限切れ）」/ "Image unavailable (expired)"

## 検証基準

| 基準 | 検証方法 |
|---|---|
| G1: 受信箱にサムネ表示 | tenant_006 で相手から画像を送る → 吹き出しに画像表示。DB: `SELECT direction, attachment_type, (attachment_url IS NOT NULL) AS has_url FROM tenant_006.meta_messages WHERE direction='inbound' AND attachment_type='image' ORDER BY id DESC LIMIT 3;` → has_url=t |
| G2: サムネクリックで原寸表示 | 画像クリック → ライトボックスが開く。再クリックで閉じる |
| G3: URL 期限切れ時の取り直し | DB の attachment_url を無効値に変更 → 開いて表示 → 取り直し成功で表示。IG 古い画像は期限切れ表示 |
| G4: テキスト表示への影響なし | テキストのみメッセージが従来どおり表示される |
| G5: 送信機能への影響なし | 英訳送信(K1〜K4)・画像送信・通常送信が従来どおり動作 |

## 外部・過去事例の参照と我々への応用

### Meta Platform Policy Section 3.e
Messenger 通信コンテンツは Platform Data の一般制限から除外される。受信画像 URL の保存・CDN URL の一時キャッシュは規約上 OK。CDN URL は期限切れがある（期間非公表・数時間〜数日）ため、期限切れ検知後に `GET /{message-id}/attachments` で取り直す設計を採用。

### Instagram 20件/スレッド制限
IG の添付取り直し API は直近 20 件/スレッドまでの制限がある。古い IG 画像は取り直せないため、`fetch_attachment_url` が None を返す場合は `inbox.imageExpired` へのフォールバックを実装。

### 先行 PR 教訓（便1 #2614）
- process-artifacts ゲートは「GO記録」と「外部・過去事例欄」の両方を要求する
- 本設計では migration なし・危険パス非該当のため GO 記録は不要
- ただし `frontend/src/` 変更 = ユーザー影響変更のため recon.md + design.md は必須
