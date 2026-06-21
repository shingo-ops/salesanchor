# ADR-141: 受信翻訳の標準入口を `enqueue_inbound_translation()` に統一する

## Status

Accepted

## Context

Discord ticket と Meta inbound は受信保存後の即時翻訳 enqueue を個別に持っていた。Meta はこれまで翻訳 enqueue の標準入口がなく、将来の新チャンネル追加時に実装差分が増えやすかった。

## Decision

受信翻訳の標準入口を `app.services.inbound_translation.enqueue_inbound_translation()` とする。

- 役割は `translate_inbound_message.delay(...)` を呼ぶ薄いラッパ
- enqueue 失敗時は例外を呼び出し元へ伝播させず、ログだけを残す
- 各受信チャネルは保存後にこの入口へ1行接続する

## Consequences

- Discord ticket と Meta inbound の enqueue 経路を統一できる
- 受信処理は翻訳 queue の障害で止まらない
- 新チャンネル追加時の実装点が明確になる

## Related files

- `backend/app/services/inbound_translation.py`
- `backend/app/discord_gateway/ticket_channel_writer.py`
- `backend/app/routers/webhook.py`
- `backend/CLAUDE.md`
