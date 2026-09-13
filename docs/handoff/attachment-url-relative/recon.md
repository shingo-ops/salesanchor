# recon — 配信URLの二重付与

> この文書は何か（専門用語なしの1行）:
> 画像が出ない理由を調べたら、住所が二重に書かれていたことが分かった記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-02）

### 保存と記録は正しく動いている

- /data/attachments に画像が3件保存されている
- tenant_006 の台帳に3行が記録されている
- gateway ログに保存完了と配信URL設定の両方が出ている

### 画面で表示されない理由

backend ログに次の2件が記録されている。

GET /api/v1/api/v1/leads/1049/attachments/3 で 404 Not Found
GET /api/v1/api/v1/leads/1049/attachments/2 で 404 Not Found

api/v1 が2回入っている。

frontend/src/lib/api.ts:144 で API_BASE と引数のパスを連結している。
DBに保存された attachment_url が既に api/v1 を含むため、二重になる。

backend/app/discord_gateway/ticket_channel_writer.py:293 が
保存するURLに api/v1 を含めている。

### 配信されているコードは新版である

frontend コンテナの index-C3GujT45.js に getBlob が含まれている。
2026-09-02 14:40 のビルドである。

## 本便で変更する箇所

backend/app/discord_gateway/ticket_channel_writer.py:293 の
URL組み立てから api/v1 を除く。

frontend/src/pages/inbox/InboxMessageThread.tsx:168 と
frontend/src/pages/inbox/InboxMessageThread.tsx:405 の
判定文字列を合わせる。

frontend/src/lib/api.ts と backend/app/routers/leads.py は変更しない。
