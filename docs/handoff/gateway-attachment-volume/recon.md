# recon — discord-gateway への添付ボリューム追加

> この文書は何か（専門用語なしの1行）:
> 画像を保存する処理が実際にどのコンテナで動いているかを調べ、
> 保管場所が足りていないことを確かめた記録。

対象ADR: docs/adr/ADR-091-discord-bot-scope-definition.md
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-02）

### 保存処理を実行するコンテナ

- `backend/app/discord_gateway/client.py:230` が
  `ticket_channel_writer.process_ticket_channel_message` を呼び出す。
- `backend/app/discord_gateway/ticket_channel_writer.py:145` が同関数の定義。
- `docker-compose.yml:271` の discord-gateway サービスは
  `command: python -m app.discord_gateway.main` で起動する。
- したがって添付の保存処理は **discord-gateway コンテナで実行される**。

### ボリュームの現状

- `docker inspect astro-webapp-discord-gateway-1` の Mounts は空配列。
- `docker inspect astro-webapp-backend-1` の Mounts は
  firebase-credentials.json の bind のみ。
- `docker volume ls` に `astro-webapp_attachments_data` は存在する。
- prod1 の `docker-compose.yml:113` に backend 向けの記述は存在する。
- prod1 の `docker-compose.yml:411` にトップレベル定義は存在する。
- discord-gateway サービス定義には volumes セクションが存在しない。

### 便1（PR #3195）の設計漏れ

便1では backend にのみボリュームを追加した。
保存処理がどのコンテナで実行されるかを確認しないまま設計したため、
実際に保存を行う discord-gateway が対象から漏れた。

## 本便で変更する箇所

`docker-compose.yml` の discord-gateway サービスに volumes セクションを新設し、
`- attachments_data:/data/attachments` を1行追加する。

トップレベル volumes と backend の設定は既存のまま変更しない。
