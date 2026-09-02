# 設計 — Discord添付の自社保存（便3）

> この文書は何か（専門用語なしの1行）:
> 顧客がDiscordに送った画像を、受け取った瞬間に自分たちのサーバーへ
> ダウンロードして保管するための作り方。

対象ADR: docs/adr/ADR-091-discord-bot-scope-definition.md
recon: docs/handoff/discord-attachment-save/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った画像やファイルが、いつ見返しても受信箱に残っている。

## 2. recon（実測）

docs/handoff/discord-attachment-save/recon.md を参照。要点は次の3つ。

- Discord CDN はブラウザから 503 を返すが、サーバーからは 200 で取得できる。
- Discord CDN URL は約24時間で失効し、元投稿の削除で実体も消える。
- 保存先ボリュームとDBテーブルは便1・便2で用意済み。

## 3. design（技術How）

`backend/app/discord_gateway/ticket_channel_writer.py` に次を追加する。

### 3-1. 保存ヘルパ

`_save_attachment_to_disk(tenant_id, lead_id, message_id, url, filename)`

- `httpx.AsyncClient` で添付をダウンロードする（タイムアウト30秒）
- 保存先は `{ATTACHMENT_ROOT}/{schema}/lead_{lead_id}/{message_id}{ext}`
- `ATTACHMENT_ROOT` は環境変数。既定値は `/data/attachments`
- 戻り値は `(相対パス, バイト数, content_type)`
- 失敗時は `(None, None, None)` を返し、例外を外へ出さない

### 3-2. 呼び出しと台帳記録

`meta_messages` への INSERT が成功した後、翻訳キューへ入れる前に実行する。

- `attachment_url` が存在する場合のみ処理する
- 保存に成功した場合のみ `lead_attachments` へ INSERT する
- `ON CONFLICT (message_id) DO NOTHING` で二重保存を防ぐ
- 台帳記録が失敗しても例外を握りつぶし、受信処理は続行する

### 3-3. 触らない範囲

`_extract_first_attachment` / `_lookup_ticket_channel_lead` /
`meta_messages` への INSERT 文 / backend の他ファイル / frontend / migrations /
docker-compose.yml。

## 4. 外部・過去事例の参照と我々への応用

Discord 公式は、添付CDN URLに `ex` / `is` / `hm` の3パラメータを付け、
署名は有効期限まで有効で、期限後はアプリ側が新しいCDN URLを取得し直す必要が
あると説明している。目的はCDNを恒久的なファイル置き場として使わせないことである。

LINE 公式ドキュメントも、ユーザーが送信したコンテンツは一定期間後に
自動的に削除されると明記している。

あるOSS実装では、Telegram / Feishu / DingTalk / iMessage は添付を
ローカルへ保存しているのに Discord だけがCDN URLを直接使っており、
チャンネル間で挙動が一貫しないとして不具合として起票されている。

我々への応用: プラットフォーム側は添付を恒久保持しない。
CRMとして履歴を残すには受信時の自社保存が必要であり、
これは特殊な選択ではなく他実装でも標準の対処である。本便はその定石に従う。

## 5. 弊害・トレードオフ

- 弊害: ダウンロード失敗時は静かにスキップするため、ログを見ないと気づけない。
  受信を止めないことを優先した設計判断による。
  画像が取れなくても本文は受信箱に残すべきであるため許容する。
- 弊害: 受信のたびにHTTPリクエストが1回増える。タイムアウトは30秒。
  現在の受信量（tenant_006 に3件）では問題にならない。
- 弊害: ディスク容量を消費する。上限8GBの管理は便5で実装する。
  本便では制限しない。
- トレードオフ: 保存に成功した場合のみ台帳へ記録するため、
  実体と台帳の不整合は起きないが、保存だけ成功して記録が失敗すると
  孤児ファイルが残る。件数は便5の掃除で検出できる。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| 構文が妥当である | python3 の ast.parse が例外を出さない |
| INSERT が2件ある | grep -c 'INSERT INTO' が 2 |
| lead_attachments への記録がある | grep -c 'lead_attachments' が 1 以上 |
| 既存の4関数が残っている | grep で 4 つの def がすべてヒットする |
| 既存処理を壊していない | tests/test_discord_ticket_channel.py が全 pass |
| 保存ヘルパが動作する | tests/test_discord_attachment_save.py が全 pass |
| 実環境で保存される | デプロイ後、Discord へ画像を送り docker exec で /data/attachments に実体を確認 |

## 7. 維持の仕組み

- 守り手: `backend/tests/test_discord_attachment_save.py`
- 理由: 保存ヘルパの戻り値仕様（成功・404・例外・拡張子の切り出し）は
  自動テストで検証できる。壊れると顧客の添付が保管されなくなる。
- 併せて `backend/tests/test_discord_ticket_channel.py` が
  既存の受信処理を壊していないことを守る。
- 人手で守る部分: 実環境での保存確認は Discord への実投稿を伴うため、
  PO または実装役の実測とする。
