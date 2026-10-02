# design: チケットボタン成功時メッセージの廃止（サイレント ACK）

recon: docs/handoff/ticket-silent-ack/recon.md

対象ADR: ADR-159, ADR-091（docs/adr/ADR-159-staff-identity-on-discord.md, docs/adr/ADR-091-discord-bot-scope-definition.md）

## KGI
チケットボタンを押したとき、過去チケットを指す「Your private channel is ready」メッセージが出ず、新チケットチャンネルだけが現れる。

## 変更方針（Opus 決定）
- 成功時の followup 送信を削除。エラー ephemeral は維持。
- `defer(ephemeral=True)` → `defer()`（type 6 の無言 ACK。意図を明示）。
- 未使用になる `bot_texts.TICKET_READY_TEMPLATE` を削除。テストを更新。
- 触らない: エラー文言、get_or_create_ticket_channel、DB、フロント。

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| 成功時にメッセージが出ない | PO が tenant_001 で「Open a ticket」を押し、「Your private channel is ready」が表示されない |
| 「interaction failed」が出ない | 同操作で Discord クライアントにエラー表示が出ない |
| 新チケットチャンネルが作られる | 同操作でチケットチャンネルが現れる（既存があれば再利用） |
| エラー時は従来どおり通知 | 単体テスト（GUILD_ONLY/未登録/未設定/作成失敗が followup ephemeral で送られる）が緑 |
| 成功時に followup が送られない | test_success_acks_silently_and_sends_no_message が緑 |

## 影響範囲
呼び出し元: `TICKET_READY_TEMPLATE` の参照は client.py と test_discord_bot_texts.py のみ（`git grep` で全走査済み）。

## 戻し方
このPRを revert すれば元の成功メッセージに戻る（DB 変更なし）。

## 外部・過去事例の参照と我々への応用
Discord 公式: コンポーネント操作は DEFERRED_UPDATE_MESSAGE(6) で「ローディング表示なし」の ACK ができる（recon.md 引用）。ボタンの結果が別の場所（新チャンネル）に現れる UI は無言 ACK が標準的。

## 維持の仕組み
守り手: backend/tests/test_discord_bot_texts.py（成功時 followup 不在・定数不在・エラー返信の維持）。
