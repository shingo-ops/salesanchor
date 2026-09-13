# recon — Discord への画像送信

> この文書は何か（専門用語なしの1行）:
> 画像を Discord へ送る機能を作る前に、いまある部品を実際に見て記録したもの。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-03）

### 画面側は既にある

frontend/src/lib/messages.ts:206 に sendImageMessage が定義されている。
画像を FormData に載せて送る。

frontend/src/pages/inbox/useInboxState.ts:624 が唯一の呼び出し箇所である。
現在は戻り値を捨てている。

画面にはファイル選択ボタンとプレビューの仕組みがある。
ドラッグ&ドロップは未実装である。

### backend の入口もある

backend/app/routers/leads.py:2144 に send_lead_image_message がある。

同ファイル:2136 で上限が 8MB に定義され、:2170 で超過を弾いている。

ただし Discord は 400 で拒否していた。
Meta の Send API 専用の実装だったためである。

### Discord への送信部品

backend/app/services/discord_rest.py はリトライとレート制限を持つ共通層である。
ファイル送信の関数は無かった。本テーマで追加した。

### テキスト送信の分岐に前例がある

backend/app/routers/leads.py:1386 でテキストが Discord へ分岐している。
Bot Token を環境変数から取り、leads の列からチャンネルIDを引く。

同じ形を画像送信にも使える。

### 保存の仕組み

backend/app/discord_gateway/ticket_channel_writer.py:42 の関数は
URL からダウンロードして保存する実装である。

送信画像は手元にバイト列があるため、この関数は使えない。
同等の処理を新たに書く必要がある。

### 壊れたテスト

backend/tests/test_message_image_send.py:319 が 400 を期待していた。
Discord のブロックを外したため、このテストは失敗する。

## 本便で変更する箇所

backend/app/routers/leads.py に送信と保存の処理を追加する。
backend/app/services/discord_rest.py にファイル送信の関数を追加する。
backend/tests/test_message_image_send.py:319 の期待値を是正する。
frontend/src/pages/inbox/useInboxState.ts で保存の成否を受け取る。
