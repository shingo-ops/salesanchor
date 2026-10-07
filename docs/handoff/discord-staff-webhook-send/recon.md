# recon: Discord 返信を担当者名義の webhook で送る（ADR-159 便B）

実測基準: origin/main 79e9fae95（2026-10-01、便A #3908 マージ後）。事実のみ。file:line はリポジトリルート相対のフルパス。

## 既存 ADR 検索（着手前）

- git grep -i "webhook" docs/adr/ を確認。直接関係: docs/adr/ADR-159-staff-identity-on-discord.md（本便の根拠）、docs/adr/ADR-091-discord-bot-scope-definition.md（Manage Webhooks を「将来機能として許容」: 同ファイル 75 行目、Developer Portal の Webhooks タブは未使用: 97-104 行目）。
- 関連: ADR-072（commit 後 reset_tenant_context）、ADR-025（`*_token_encrypted` の手動投入禁止）、ADR-027（i18n）、ADR-144（UI 金型）、ADR-067（トークン）。
- 本便の結果として docs/adr/ADR-091-discord-bot-scope-definition.md の該当 2 箇所を更新する（ADR 追加なし。docs/adr/README.md は generate-adr-index.js で再生成、差分なし）。

## 事実

- テキスト返信（下書き送信も経由）: backend/app/routers/leads.py の `_send_discord_message`（変更前は Bot の `send_discord_dm`: backend/app/services/discord_sender.py）。staff 解決は送信後で、失敗は黙って None にしていた。
- 画像返信: backend/app/routers/leads.py の `send_lead_image_message` の Discord 分岐（変更前は Bot の `discord_api_request_with_file`: backend/app/services/discord_rest.py:139）。staff 解決は送信後。
- 変更前の送信エラー表現: Meta 経路は `detail={"message":..., "reason": ...}`（backend/app/routers/leads.py の rate_limited / send_error_reason）。フロントは `ApiError.responseDetail.reason` を読む: frontend/src/pages/inbox/useInboxState.ts（送信 catch 内 `detail?.reason`）。
- 送信エラーの表示: frontend/src/pages/inbox/InboxMessageThread.tsx の `inbox-send-error`（reason → i18n キーの三項連鎖）。文言は frontend/src/locales/{ja,en}.json の `inbox.sendError.*`。
- 入力文の保持: frontend/src/pages/inbox/useInboxState.ts の `submitSend` は成功後にのみ `setDraft("")` / `clearAttachment()`。失敗時は消えない（修正不要）。
- 再送: `submitSend()` は draft / attachedFile の現在値で再実行できる。
- 権限判定: `usePermissions().hasPermission(...)`（frontend/src/hooks/usePermissions.ts）。Discord 設定ページは `tenant.profile.edit` で編集可（frontend/src/pages/admin/DiscordConfigPage.tsx:230）、ルート `/admin/discord-config`（frontend/src/App.tsx:378）。アカウント設定ルートは `/account/settings`（frontend/src/App.tsx:287）。
- 受信側: bot / webhook 投稿は skip されるため二重記録なし（backend/app/discord_gateway/ticket_channel_writer.py:194）。
- 便A の公開 URL ヘルパ `build_avatar_url(token)`（API_BASE_URL 由来）: backend/app/services/staff_avatar.py。未登録なら None。
- 暗号化: backend/app/services/encryption.py の `encrypt` / `decrypt`（Fernet・str ↔ str）。`*_token_encrypted` の型は TEXT（migrations/076_add_google_calendar_config.sql）と BYTEA（migrations/040_create_tenant_meta_config.sql）が併存。str を返す API に合わせ TEXT を採用。
- migration 前例: migrations/20260927_100000_create_meta_message_reactions.sql（tenant_NNN 走査・RLS）。登録は scripts/run_all_migrations.sh 末尾の `run_sql`。
- Discord 公式（https://discord.com/developers/docs/resources/webhook）: webhook 作成 POST /channels/{id}/webhooks は MANAGE_WEBHOOKS 必須、名前に discord / clyde 不可、実行 POST /webhooks/{id}/{token}?wait=true で username / avatar_url をメッセージ単位で上書き可、画像は multipart + payload_json。
- httpx 自身の INFO ログ（"HTTP Request: POST <url>"）は webhook 実行 URL＝token を含む。テストで実測（test_token_never_logged が当初失敗）。ログフィルタで伏せる対応を入れた。
- テスト基盤: backend は SQLite + 手書き DDL（backend/tests/test_message_image_send.py）。respx は未導入のため httpx.MockTransport を使用。

## 未確認

- 本番 Discord 上での webhook 作成権限（各ギルドの Bot 役職に Manage Webhooks があるか）。招待権限 805432406 は MANAGE_WEBHOOKS を含む（backend/app/routers/discord_oauth.py:72）が、既存ギルドの実際の役職は未確認 → 実機確認項目。
- Discord が WebP の avatar_url を表示できること（実機確認項目）。
- 本番で METADATA_FERNET_KEY が設定済みであること（Meta 連携が使用中のため設定済みの想定。デプロイ後の初回送信で確認）。
