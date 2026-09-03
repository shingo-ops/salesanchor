# recon — CSP が blob URL の画像をブロックしている

> この文書は何か（専門用語なしの1行）:
> 画像の取得には成功しているのに画面に出ない理由を、配信設定まで遡って調べた記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-03）

### 取得は成功している

backend のログに次が記録されている。

GET /api/v1/leads/1049/attachments/4 で 200 OK
GET /api/v1/leads/1049/attachments/5 で 200 OK

保管先に4件のファイルが存在し、backend コンテナからも見える。

### 画面には壊れた画像アイコンが出る

img タグは描画されているが、読み込みに失敗している。
プレースホルダの span ではなく img が出ている。

### CSP が blob を許可していない

nginx/nginx.conf:82 の img-src に blob の指定が無い。

同じファイルの nginx/nginx.conf:177 には blob の指定がある。
そちらは Grafana 用のブロックである。

frontend/src/pages/inbox/InboxMessageThread.tsx:174 が
URL.createObjectURL で blob URL を生成し img の src に渡している。

CSP が blob を許可しないため、ブラウザがその読み込みを止めている。

### 既存2件は別の理由で表示されない

meta_messages の attachment_url が古い形式のまま残っている行がある。

id=469 は /api/v1/leads/1049/attachments/2
id=471 は /api/v1/leads/1049/attachments/3

これらは新しい判定に合致せず、img の src に直接入る。
ブラウザは認証ヘッダーを付けないため 401 になる。

PR #3233 より前に保存された行であり、テストデータのため放置する（PO決定）。

## 本便で変更する箇所

nginx/nginx.conf:82 の img-src に blob を追加する。

nginx/nginx.conf:177 は変更しない。既に blob がある。
DBの既存行は変更しない。
