# recon — 自社配信APIの画像表示

> この文書は何か（専門用語なしの1行）:
> 保管した画像が受信箱に出ない理由を、実際のコードとログを見て突き止めた記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-02）

### 便4までは動作している

- /data/attachments に画像が2件保存されている
- tenant_006 の台帳に2行が記録されている
- gateway ログに保存完了と配信URL設定の両方が出ている
- meta_messages の attachment_url が自社APIのパスになっている

### 画面で表示されない理由

backend ログに 401 Unauthorized が3件記録されている。

backend/app/auth/dependencies.py:70 の get_current_user は
HTTPAuthorizationCredentials のみを引数に取る。

backend/app/auth/dependencies.py に Cookie の処理は0件である。
backend/app/main.py にも0件である。

img タグは Authorization ヘッダーを送れない。
frontend/src/pages/inbox/InboxMessageThread.tsx:379 が
attachment_url を img の src へ直接入れているため、認証が通らない。

### 使える既存部品

frontend/src/lib/api.ts:131 に requestBlob が定義されている。
Authorization ヘッダー付きで Blob を返し、リトライとタイムアウトを持つ。

frontend/src/lib/api.ts:206 で getBlob として公開されている。

frontend/src/components/ShippingDetailPanel.tsx:320 に
URL.createObjectURL による Blob 表示の実例がある。

### Meta 経路との違い

Meta の画像は外部CDNの公開URLであり、認証なしで表示できる。
実測した1件は fbcdn.net のURLである。
この経路は変更しない。

## 本便で変更する箇所

frontend/src/pages/inbox/InboxMessageThread.tsx のみ。
frontend/src/lib/api.ts と backend は変更しない。
