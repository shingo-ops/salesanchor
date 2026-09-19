# recon — 送信画像が表示されずプレビューも残る

> この文書は何か（専門用語なしの1行）:
> 送った画像が受信箱に映らず、入力欄の画像も消えない理由を実際に見て調べた記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-04）

### 課題1 — 送信画像が表示されない

meta_messages の outbound の行は3件あり、
いずれも attachment_url が null である。

一方 lead_attachments には送信分の行が存在する。
id 6 と id 7 が該当し、ファイルも保存されている。

backend/app/routers/leads.py:2278 の dc_insert_params に
attachment_url が含まれていない。

INSERT の列にも attachment_url が無い。

受信時は配信URLを設定しているが、送信時は設定していない。

### 課題2 — 入力欄のプレビューが残る

frontend/src/pages/inbox/useInboxState.ts:216 の clearAttachment は
attachedFile のみを null にする。

frontend/src/pages/inbox/InboxMessageThread.tsx:75 で
previewUrl は別の state として保持されている。

画面は previewUrl を見て表示するため、
attachedFile が消えても previewUrl は残る。

frontend/src/pages/inbox/useInboxState.ts:625 で送信後に
clearAttachment を呼んでいるが、previewUrl には届かない。

### 課題3 — Enter でファイル選択が開く（本便の対象外）

frontend/src/pages/inbox/useInboxState.ts:660 の handleKeyDown は
Enter で submitSend を呼んでいる。

原因は特定できていない。本便では扱わない。

## 本便で変更する箇所

backend/app/routers/leads.py に配信URLの設定を追加する。
frontend/src/pages/inbox/InboxMessageThread.tsx に
attachedFile に追従してプレビューを消す処理を追加する。

frontend/src/pages/inbox/useInboxState.ts は変更しない。
