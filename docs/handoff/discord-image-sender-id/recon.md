# recon — 画像送信が 500 を返す

> この文書は何か（専門用語なしの1行）:
> 送った画像が Discord には届くのに画面がエラーを出す理由を、
> サーバーのログから突き止めた記録。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-04）

### 症状

受信箱から画像を送ると、画面に送信できませんでしたと表示される。
POが実機で確認したところ、Discord のチャンネルには画像が届いていた。

### サーバーのログ

POST /api/v1/leads/1049/messages/image で 500 Internal Server Error。

エラーの内容は次のとおりである。

NotNullViolationError: null value in column sender_id
of relation meta_messages violates not-null constraint

つまり Discord への送信は成功し、
その後のデータベースへの記録で失敗している。

### 原因

backend/app/routers/leads.py:2282 の Discord 分岐が
sender_id に None を入れている。

meta_messages の sender_id は NOT NULL である。

### 既存のテキスト送信は正しい

backend/app/routers/leads.py:2098 の既存のテキスト送信は
bot と tenant_id を組み合わせた文字列を入れている。

同じ値を使えばよい。

### 他の要因は問題ない

- Bot Token は backend の環境変数に存在する
- discord_guild_channel_id は設定済みである
- Traceback は出ていない。データベースの制約違反のみである

## 本便で変更する箇所

backend/app/routers/leads.py の Discord 分岐の sender_id を
既存のテキスト送信と同じ値にする。
