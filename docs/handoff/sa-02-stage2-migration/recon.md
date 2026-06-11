# SA-02 段階2 recon: meta_messages → conversation_logs 移行

> 調査日: 2026-06-11（Terminal CC）

## 現状コード調査（file:line 付き）

| 調査観点 | 現状（file:line） | 備考 |
|----------|-----------------|------|
| meta_messages スキーマ | `migrations/012_add_meta_tenant_tables.sql:8-11` — id/tenant_id/lead_id/platform/sender_id/sender_name/message_text/direction/raw_payload/created_at | 拡張列: `migrations/041_extend_meta_messages.sql:38` — message_id/seen_at 等 |
| meta_messages への書き込み経路 | `backend/app/routers/webhook.py:665-758` — Messenger/Instagram受信をmeta_messagesに保存 | Discord: `backend/app/discord_gateway/dm_writer.py:225` |
| conversation_logs スキーマ | `migrations/20260604_090000_create_conversation_logs.sql:34-54` | is_manual/recorded_by_user_id/deleted_at: `migrations/20260611_120000_add_conv_log_manual_columns.sql` |
| conversation_logs の external_message_id UNIQUE 制約 | `migrations/20260604_090000_create_conversation_logs.sql:48` — `VARCHAR(255) UNIQUE` | 冪等性の根拠。ON CONFLICT DO NOTHING で再実行可 |
| message_translations スキーマ | `migrations/094_create_message_translations.sql:25-32` — message_id(TEXT)/target_language/translated_text | meta_messages.message_id（Meta mid）を外部キーとしてJOINできる |
| companies と leads の紐づけ | `backend/app/routers/registration_tokens.py:165` — コメント「companies.lead_id が SSOT（leads に company_id 列はない）」 | company_id は `companies WHERE lead_id = mm.lead_id` で導出 |
| 既存移行スクリプトのパターン | `scripts/migrate_adr021_remove_confirmed_status.py:90-145` — asyncpg/SQLAlchemy async パターン | バッチ処理・テナントループ・エラーハンドリングを流用 |

## 移行カラムマッピング

| meta_messages 列 | conversation_logs 列 | 変換ルール |
|-----------------|---------------------|-----------|
| tenant_id | tenant_id | そのまま |
| lead_id | lead_id | そのまま |
| -(なし) | contact_id | NULL（meta_messagesにcontact_id列なし） |
| -(JOIN) | company_id | `companies.id WHERE companies.lead_id = mm.lead_id` |
| platform | channel_type | 'messenger'→'meta_messenger', 'instagram'→'instagram', 'discord'→'discord' |
| sender_id | channel_identity | そのまま |
| sender_name | sender | そのまま |
| message_text | content_text | そのまま |
| direction | direction | そのまま（'inbound'/'outbound'） |
| raw_payload | raw_payload | そのまま |
| message_id | external_message_id | NULLの場合は合成キー `meta_legacy:{id}` |
| -(JOIN) | translated_text | message_translations.translated_text WHERE target_language='ja' |
| created_at | occurred_at | そのまま |
| created_at | created_at | そのまま |
| -(固定) | is_manual | false |
| -(固定) | recorded_by_user_id | NULL |
| -(固定) | deleted_at | NULL |

## 成果物

| ファイル | 役割 |
|---------|------|
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py` | 移行スクリプト本体（冪等・ドライラン対応） |
| `scripts/verify_sa02_stage2_count_check.py` | 件数突合検証スクリプト |
| `docs/handoff/sa-02-stage2-migration/rollback.md` | ロールバック手順 |
