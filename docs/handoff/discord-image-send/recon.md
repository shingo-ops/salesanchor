# recon: Discord 画像送信（attachment-storage 便6）

調査日: 2026-09-03  
ブランチ: release/discord-image-send

## 既存 ADR 確認

```
git grep -i discord docs/adr/
```

- ADR-091: attachment-storage テーマ全般（attachment 保存設計）
- ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須

## 変更ファイル一覧（git diff --name-only origin/main...HEAD）

```
backend/app/routers/leads.py
backend/app/services/discord_rest.py
backend/tests/test_message_image_send.py
docs/handoff/discord-image-send/recon.md
docs/handoff/discord-image-send/design.md
```

## 起点: 送信エンドポイント

`backend/app/routers/leads.py:2218` — `if platform == "discord":` ブロック  
`backend/app/services/discord_rest.py:139` — `discord_api_request_with_file()` 追加済み

### Discord 送信フロー（変更後）

1. `leads.py:2219` — `import os as _os`
2. `leads.py:2223` — `_os.environ.get("DISCORD_BOT_TOKEN")` → なければ 409
3. `leads.py:2230-2242` — `discord_guild_channel_id` SELECT → なければ 404
4. `leads.py:2247-2264` — `discord_api_request_with_file(channel_id, bot_token, file_bytes, dc_filename, content_type)` 呼び出し
5. `leads.py:2270-2334` — `meta_messages` INSERT（RETURNING → fallback SELECT last_insert_rowid）
6. `leads.py:2336-2378` — attachment 保存ブロック（便6追加分）
7. `leads.py:2380-2389` — `_record_send_audit_safely` + `db.commit()` + `reset_tenant_context`

### discord_rest.py 追加関数

`discord_rest.py:139` — `discord_api_request_with_file(channel_id, bot_token, file_bytes, filename, content_type)`  
POST `https://discord.com/api/v10/channels/{channel_id}/messages`  
multipart key: `files[0]`  
リトライ: 429 retry_after, 5xx 指数バックオフ 5s/最大 60s/最大 5回

### attachment 保存（便6）

`leads.py:2337` — `if dc_msg_id:` → try ブロック  
パス形式: `tenant_{id:03d}/lead_{lead_id}/{dc_msg_id}{ext}`  
ENV: `ATTACHMENT_ROOT`（デフォルト `/data/attachments`）  
テーブル: `lead_attachments` — `ON CONFLICT (message_id) DO NOTHING`  
失敗時: WARNING ログのみ・送信成功扱い（受信側と同一設計）

## テスト

`backend/tests/test_message_image_send.py:319` — 旧: `test_discord_platform_returns_400`（400を期待）  
変更後: `test_discord_without_channel_returns_404`（404を期待・DISCORD_BOT_TOKEN を patch.dict で注入）

## 触らないファイル

- `nginx/nginx.conf`（CSP blob: 追加は別PR #3240 で完了・main 済み）
- `frontend/` 以下（フロント結線は既存 `sendImageMessage` で完結・追加不要）
- `backend/app/services/discord_rest.py`（discord_api_request_with_file は実装済み・変更なし）
