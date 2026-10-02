# design: チケットの部屋が消されたときの自動復旧

- 日付: 2026-10-02
- 関連 recon: docs/handoff/ticket-channel-delete-restore/recon.md
- 対象ADR: ADR-091 / ADR-159（docs/adr/ADR-091-discord-bot-scope-definition.md, docs/adr/ADR-159-staff-identity-on-discord.md）
- PO決定（原文）: 「自動で直す (推奨)」（2026-10-02）

## 1. 決定と動作

チケットの部屋（Discord チャンネル）が削除されたら、そのお客様に ticket-start を再び見えるようにし、
leads.discord_guild_channel_id を NULL に戻す。お客様はボタンを押せば新しい部屋ができる
（既存の get_or_create_ticket_channel が「保存IDなし」として新規作成する）。
lead_channels・meta_messages（アプリの会話履歴）には触らない。DB の行は他に何も消さない。

## 2. 変更

- backend/app/discord_gateway/ticket_channel_creator.py
  - `restore_after_ticket_deleted(guild, tenant_id, deleted_channel_id, db_factory, http=None) -> int`
    該当 lead が無ければ no-op。Discord 側の overwrite 解除に成功（または元から無い=404）した場合のみ
    部屋IDを NULL にする。失敗時は ID を残し、起動時点検で再試行させる。冪等。
  - 在籍中は `set_permissions(member, overwrite=None)`、退会済みは `http.delete_channel_permissions`
    （再参加後に ticket-start が見えないままになるのを防ぐ）。
  - `reconcile_deleted_ticket_channels(guild, tenant_id, db_factory, http=None) -> int`
    保存IDがキャッシュに無いものを REST `fetch_channel` で確認し、NotFound(404) のものだけ復旧。
    他のエラーは触らない。1 guild あたり確認は最大200件。
- backend/app/discord_gateway/client.py
  - `on_guild_channel_delete`: TextChannel かつ登録済み guild のみ。例外は警告ログのみ。
  - `on_ready`: 起動時点検を別タスクで1回だけ起動（READY 処理を塞がない）。close() で cancel。
- backend/tests/test_discord_ticket_channel_delete_restore.py（新規）

触らない範囲: migrations、deploy.yml、フロントエンド、lead_channels、meta_messages、
get_or_create_ticket_channel の既存ロジック。

## 3. 基準・検証方法

| 基準 | 検証方法 |
|---|---|
| 削除イベントで ticket-start の個別上書きが外れ、部屋IDが NULL になる | test_restore_removes_overwrite_and_nulls_channel_id |
| 無関係チャンネルの削除は何も変えない | test_restore_is_noop_for_unrelated_channel / test_client_delete_event_ignores_non_text_channel / test_client_delete_event_skips_unregistered_guild |
| 退会済みメンバーでも解除できる | test_restore_uses_rest_when_member_left_guild |
| 解除に失敗したら ID を残す（再試行可能） | test_restore_keeps_channel_id_when_discord_call_fails / test_restore_keeps_channel_id_when_member_left_and_no_http |
| 冪等 | test_restore_is_idempotent_on_second_call / test_restore_treats_overwrite_not_found_as_done |
| 停止中に消えた分を起動時に拾う（NotFound 確認分のみ） | test_reconcile_restores_only_channels_confirmed_missing |
| 例外がイベントループを止めない | test_client_delete_event_swallows_restore_failure |
| 実機: PO が tenant_001 のテスト用チケット部屋を削除 → 顧客（Akane）に数秒以内に ticket-start が再表示 → ボタンで 📩｜DM 配下に新規作成 → スタッフ返信が届く → アプリの会話履歴が残っている | 受入条件（PO実施） |

## 4. 外部事例

Discord 公式ドキュメント「Delete/Close Channel」: チャンネル削除は取り消せず、CHANNEL_DELETE が
Gateway イベント（GUILD intent）として配信される。discord.py の `on_guild_channel_delete` はこれに対応する。

## 5. 戻し方・測り方・継続

- 戻し方: 本PRを revert（DB スキーマ変更なし）。
- 測り方: ログ `[ticket] restored after channel delete` / `[ticket] reconcile done ... stale= restored=`。
- 継続: 上記テストが CI で回り続ける。reconcile は起動ごとに実行され、取りこぼしを自己修復する。

## 6. 弊害

- 起動時点検は REST を最大200件/guild 発行（Discord rate limit 内。失敗は警告のみ）。
- 解除に失敗した lead は次回起動まで ID が残る（顧客は ticket-start が見えないまま。再起動で解消）。
