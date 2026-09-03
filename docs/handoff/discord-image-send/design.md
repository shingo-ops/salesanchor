# design: Discord 画像送信（attachment-storage 便6）

設計日: 2026-09-03  
参照 recon: `docs/handoff/discord-image-send/recon.md`  
参照 ADR: ADR-091 (attachment-storage), ADR-072 (reset_tenant_context)

## KGI

受信箱の Discord スレッドから画像を Discord チャンネルへ送信でき、  
送信画像が `lead_attachments` テーブルおよびディスクに保存される。

## KPI / 完了定義

| 基準 | 検証方法 |
|------|---------|
| `DISCORD_BOT_TOKEN` 未設定 → 409 | pytest `test_no_meta_config_returns_409` (messenger) / 409チェックは共通コード |
| `discord_guild_channel_id` 未設定 → 404 | pytest `test_discord_without_channel_returns_404` |
| Discord API 呼び出し成功 → 201 + `meta_messages` outbound 行 | CI pytest 全 PASS |
| 送信画像が `lead_attachments` に保存される | `test_discord_d2.py` or 結合テスト（便7以降） |
| 保存失敗時も送信成功として返す | try/except + WARNING ログ（ユニットテスト対象外・ログで確認） |

## 設計方針

### Discord API 呼び出し

既存 `discord_api_request_with_file()` (`discord_rest.py:139`) を利用。  
multipart POST で `files[0]` キーにファイルを添付。  
リトライは discord_rest.py の共通レジリエンスレイヤーに委譲。

### attachment 保存（便6）

- 受信側 (`ticket_channel_writer.py:42` `_save_attachment_to_disk`) と同一の保存形式を採用。
- 保存先: `ATTACHMENT_ROOT/tenant_{id:03d}/lead_{lead_id}/{discord_message_id}{ext}`
- `lead_attachments.message_id` は UNIQUE 制約 → `ON CONFLICT (message_id) DO NOTHING` で冪等。
- **保存失敗は警告ログのみ・送信成功扱い**（受信側と同じ設計決定）。

### meta_messages INSERT

- `direction='outbound'`, `platform='discord'`, `attachment_type='image'`
- RETURNING 未対応 SQLite 環境向けに `SELECT last_insert_rowid()` フォールバックあり。

### ADR-072 遵守

`db.commit()` 直後に `reset_tenant_context(db, tenant_id)` を実行（`leads.py:2347-2348`）。

## 外部事例

Discord Bot multipart upload: 公式ドキュメント  
`POST /channels/{channel_id}/messages` + `multipart/form-data` (`files[0]` key)  
添付ファイルは 8MB 上限（`leads.py:_MAX_IMAGE_BYTES = 8 * 1024 * 1024` で事前チェック済み）。

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| Discord API 一時障害 | discord_rest.py の 5xx 指数バックオフ (最大 5回) |
| ATTACHMENT_ROOT 未設定 | デフォルト `/data/attachments`・失敗は WARNING のみ |
| message_id 重複 (リトライ時) | `ON CONFLICT (message_id) DO NOTHING` |

## 触るファイル

- `backend/app/routers/leads.py` — 送信実装 + attachment 保存ブロック追加
- `backend/tests/test_message_image_send.py` — テスト修正 (400→404, DISCORD_BOT_TOKEN patch)

## 削除するファイル

- `backend/app/routers/leads.py` — 変更あり（deletions ≥ 1）
