# design: Discord 返信を担当者名義の webhook で送る（ADR-159 便B）

参照: docs/adr/ADR-159-staff-identity-on-discord.md、docs/handoff/discord-staff-webhook-send/recon.md、docs/adr/ADR-091-discord-bot-scope-definition.md、docs/adr/ADR-072、docs/adr/ADR-027、docs/adr/ADR-144

## 目的（PO 決定 2026-10-01 verbatim）

- 表示名: 「名だけ (例: Shingo) (推奨)」。英語名は必須
- アイコン未登録: 「discordのアイコンなしの状態と同じ表示」（avatar_url を省略・webhook は avatar なしで作成）
- 失敗時: 「送らずに止める (推奨)」（Bot 名義では送らない・自動再送は確実に未送信の場合のみ 1 回・失敗表示・入力文保持）
- エラー表示: 「非エンジニアである担当者が理解できる内容でエラーメッセージを表示させて対応方法までCTA，簡潔に」
- リアクションは Bot 名義のまま

## 便B の範囲（1便1目的）

Discord のテキスト・画像返信を、担当者の名前・アイコンで送る。アイコン登録・英語名必須化は便A（マージ済み）。

## 設計

- データ: tenant_NNN.discord_channel_webhooks(id, tenant_id, channel_id UNIQUE, webhook_id, webhook_token_encrypted TEXT, created_at) + RLS。token は encryption.encrypt で暗号化しアプリコードのみが書く（migrations/20261001_150000_create_discord_channel_webhooks.sql）
- 送信: backend/app/services/discord_webhook_sender.py
  - `validate_username`: 前後空白除去・1〜80 文字・discord / clyde（大文字小文字不問）を含まない → `StaffNameInvalidError`
  - `send_as_staff`: 保管 webhook を取得、無ければ POST /channels/{id}/webhooks（name="Sales Anchor"・avatar なし・Bot 認証）で作成して暗号化保管。実行は POST /webhooks/{id}/{token}?wait=true（json、画像は multipart + payload_json）。avatar_url は未登録なら省略
  - 実行が 401/404 → 保管行を削除し 1 回だけ作り直して 1 回だけ再送（作成直後の 404 は作り直さない）
  - 自動再送は確実に未送信の場合のみ（顧客への二重送信を防ぐ）: 429（retry_after が 5 秒以下のときだけ待つ）と、接続前の失敗（ConnectError / ConnectTimeout）を 1 回だけ再試行。読み取りタイムアウト・5xx・その他は「送られたかもしれない」ため再試行せず `DISCORD_SEND_FAILED`（担当者が「もう一度送る」で再送）
  - 想定外の応答（JSON でない・id / token が無い）は `WebhookSendError` → `DISCORD_SEND_FAILED`（500 にしない）
  - 「もう一度送る」は下書き（draft_id）経由の送信なら同じ draft_id で再送する（useInboxState の retrySend）
  - 作成 403 → `WebhookPermissionError`。その他の失敗 → `WebhookSendError`。Bot 名義の送信（/channels/{id}/messages）は一切呼ばない
  - token / 実行 URL をログに出さない（例外文は種別名のみ。httpx / httpcore（子 logger 含む）のログは LogRecordFactory で token を `***` に置換）
- ルーター: backend/app/routers/leads.py
  - `_resolve_staff_identity` を送信前に実行（チャンネル未設定の 409 / 404 の後・送信の前）。英語名なし or staff 不在 → 422 `STAFF_EN_NAME_REQUIRED`、不正 → 422 `STAFF_EN_NAME_INVALID`
  - `_send_discord_as_staff` が例外を HTTP に変換: 権限 → 409 `DISCORD_WEBHOOK_PERMISSION`、送信失敗 → 502 `DISCORD_SEND_FAILED`
  - エラー詳細は `{"message", "reason", "code"}`。フロントの既存規約（`detail.reason`）に合わせ reason を主とし、ADR-159 の code も同値で併記
  - meta_messages INSERT は従来どおり（message_id・sent_by_staff_id）。失敗時は行を作らない。権限エラーは 409（403 は「ユーザーの権限」と紛れるため避けた）
- 画面: frontend/src/pages/inbox/discordSendError.ts（コード → 文言キー・CTA の対応表）、InboxMessageThread.tsx の `inbox-send-error` に文言＋既存 Button 金型（secondary / sm）。新コンポーネントなし
  - STAFF_EN_NAME_REQUIRED「Discordで返信するには、英語の名前の登録が必要です。」[アカウント設定を開く → /account/settings]
  - STAFF_EN_NAME_INVALID「英語の名前に使えない言葉（discord など）が含まれています。」[アカウント設定を開く]
  - DISCORD_SEND_FAILED「送信できませんでした。入力した文は残っています。」[もう一度送る → submitSend]
  - DISCORD_WEBHOOK_PERMISSION: `tenant.profile.edit` を持つ人「Discordの設定が足りないため送れません。」[Discord設定を開く → /admin/discord-config]／それ以外「…管理者に連絡してください。」（ボタンなし）
- ADR-091: Manage Webhooks 行を実装済みに更新、Webhooks タブ注記を更新

## 受入条件

| 基準 | 検証方法 |
|---|---|
| webhook の作成・実行・404 作り直し 1 回・429 と接続前失敗のみ再試行 1 回・5xx/読み取りタイムアウトは再試行しない・想定外応答は失敗扱い・権限エラー | backend/tests/test_discord_webhook_sender.py（httpx.MockTransport） |
| avatar 未登録なら avatar_url を送らない・webhook 作成も avatar なし | 同上 |
| token は暗号化保存（DB に平文なし）・ログに出ない | 同上（test_creates_webhook_stores_encrypted_and_sends / test_token_never_logged） |
| 英語名なし 422・不正名 422・権限 409・失敗 502、いずれも送らず meta_messages 行を作らない | backend/tests/test_discord_staff_send.py、backend/tests/test_discord_inbox.py |
| Bot 名義へフォールバックしない | 同上（send_discord_dm / discord_api_request_with_file が一度も呼ばれない） |
| 成功時 meta_messages に message_id・sent_by_staff_id が記録される | 同上 |
| 4 コードが非エンジニア向け文言と行動ボタンで表示・管理者以外は権限案内のみ・入力文が残る | frontend discordSendError.test.ts、InboxMessageThread.discordSendError.test.tsx |
| ja / en 同一キー | frontend check-i18n-missing-keys |
| migration が冪等 | CI migration-test |
| 実機: 返信が Discord 上で担当者の名（例: Shingo）と登録アイコンで表示。アイコン未登録者は Discord 標準アイコン。画像返信も担当者名義。受信側で二重記録されない（meta_messages 件数が増えない） | PO が tenant_001 テストサーバーで確認（マージ・デプロイ後） |
| 実機: Bot に Manage Webhooks が無いサーバーで権限エラー案内（管理者向け CTA）が出る | PO が確認（任意） |

## 外部・過去事例の参照と我々への応用

- Discord Webhook 公式仕様（https://discord.com/developers/docs/resources/webhook）: username / avatar_url のメッセージ単位上書き、`?wait=true` で message id 取得 → 本設計の中核
- Discord 公式 Rate Limits（https://discord.com/developers/docs/topics/rate-limits）: 429 は retry_after に従う → 小さい場合のみ待って 1 回再試行（メッセージ未作成が確実なため）、大きい場合は画面を止めないため失敗扱い
- 過去事例: 便A（#3908）の公開 URL ヘルパ再利用、migrations/20260927_100000_create_meta_message_reactions.sql の migration 型、discord_rest.py の再試行方針（本便は二重送信回避のため、確実に未送信の場合の 1 回に限定）
- 実測で見つけた事象: httpx の INFO ログが webhook 実行 URL（token 入り）を出す → フィルタで伏せた

## リスクと戻し方

- 既存ギルドの Bot 役職に Manage Webhooks が無いと webhook を作れず送れない → 管理者向け CTA で案内（Bot 名義での代替送信はしない: PO 決定）
- 英語名未登録のスタッフは登録するまで Discord 返信できない（ADR-159 記載の Tradeoff）
- webhook を Discord 側で手動削除された場合は次回送信で自動作り直し
- 戻し方: PR を revert。migration は additive（新テーブルのみ）で残しても無害。revert すると送信は Bot 名義に戻る
- 本番影響: migration を含むため危険パス扱い（ADR-135/136）。GO 受領まで main にマージしない

## 維持の仕組み

- 守り手: backend/tests/test_discord_webhook_sender.py・test_discord_staff_send.py が CI pytest で常時実行（Bot フォールバック禁止・token 非ログ・暗号化保存を固定）。frontend の discordSendError テストが文言キーと CTA の対応を固定。ja/en キー同一は check-i18n-missing-keys が検査
