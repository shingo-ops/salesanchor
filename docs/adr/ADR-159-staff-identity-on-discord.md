# ADR-159: Discord 返信を担当者の名前・アイコンで送る

- **Status**: Accepted (2026-10-01 PO 承認: 「この設計で進める (推奨)」)
- **Date**: 2026-10-01
- **Deciders**: しんごさん（PO）, Claude Opus（設計）

## Context

Discord への返信は Bot 名義で送られるため、顧客に Bot 感が出る。返信した担当者が顧客に分かる形で送りたい（PO 要望 2026-10-01）。

- Discord 公式: webhook 実行は username / avatar_url をメッセージ毎に上書きできるが、Bot の通常送信は不可。webhook 作成には MANAGE_WEBHOOKS が必要（https://discord.com/developers/docs/resources/webhook）
- 招待権限 805432406 は MANAGE_WEBHOOKS(536870912) を含む（backend/app/routers/discord_oauth.py:72）。ADR-091 で「将来機能として許容」済み
- 受信側 backend/app/discord_gateway/ticket_channel_writer.py:194 が bot/webhook 投稿を skip するため二重記録は起きない
- staff 表に avatar 列が無く、given_name_en は全スキーマで任意だった（backend/app/schemas/staff.py）

## Decision

PO 回答（verbatim）:
- 表示名: 「名だけ (例: Shingo) (推奨)」
- 英語名: 「①…→必須項目とする、Discordは名前で表示」
- アイコン未登録: 「②…→discordのアイコンなしの状態と同じ表示」
- 失敗時: 「⑤…Bot感を出さずに顧客には演出してあげたい」→「送らずに止める (推奨)」
- エラー表示: 「フロントにも非エンジニアである担当者が理解できる内容でエラーメッセージを表示させて対応方法までCTA，簡潔に」

採用する設計:
1. 表示名 = 英語名の「名」(given_name_en) のみ。英語名（名・姓）はアカウント設定・スタッフ作成/編集で必須。DB は NOT NULL にしない（既存データ保護、API 入力検証で必須化）
2. アイコン未登録 = Discord 標準アイコン（avatar_url を指定しない）
3. 画像は jpg/png/webp・2MB 以下。本人がアカウント設定で登録・変更・削除。Pillow で EXIF 除去・中央正方形切り抜き・256px WebP 再エンコード
4. 画像は推測不能 token（secrets.token_urlsafe(32)）の URL でログイン不要公開（Discord が取得するため）。DB は staff.avatar_token のみ保持し、実体は ATTACHMENT_ROOT/staff_avatars/<token>.webp
5. 失敗時・英語名未登録時は送らない（自動再試行1回→失敗表示・入力文保持）。Bot 名義では一切送らない
6. 対象 = Discord のテキスト・画像返信。リアクションは Bot 名義のまま
7. エラーは非エンジニア向け短文＋行動ボタン（CTA）。既存金型・i18n・トークンのみ。新金型 AvatarUpload を追加登録（PO 承認済み）

### 便の分割（1便1目的）
- 便A（本 ADR の最初の実装）: staff.avatar_token migration・Pillow・アップロード/削除/公開 API・AvatarUpload 金型・アカウント設定・英語名必須化
- 便B: tenant_NNN.discord_channel_webhooks（webhook token は services/encryption.py で暗号化保存）・services/discord_webhook_sender.py・送信前 staff 解決・エラーコード（STAFF_EN_NAME_REQUIRED / STAFF_EN_NAME_INVALID / DISCORD_WEBHOOK_PERMISSION / DISCORD_SEND_FAILED）・送信エラー表示 CTA・ADR-091 範囲表更新

## Scope

- Included: staff アイコン画像の保存と公開、英語名の必須化、Discord webhook による担当者名義送信（便B）
- Excluded: リアクション送信、Discord 以外のチャネル、過去メッセージの表示名遡及変更（Discord 仕様上不可）

## Evidence

- evidence: 設計 docs/handoff/staff-avatar-en-name/design.md、recon docs/handoff/staff-avatar-en-name/recon.md
- confidence: high（Discord 公式仕様・既存コードの file:line を確認済み）
- tradeoff: 公開画像 URL は token を知る者なら誰でも閲覧可（PO 承認）。Bot 役職に Manage Webhooks が無い既存ギルドは便B で権限エラー案内

## Consequences

### Positive

- 顧客に Bot 感を出さず、返信した担当者が分かる
- EXIF（位置情報等）が公開 URL に載らない

### Negative / Tradeoff

- 名前・アイコン変更は過去メッセージに反映されない（Discord 仕様）
- 既存スタッフは英語名の登録をするまで Discord 返信できない（便B 適用後）
- Pillow 依存の追加

## Exceptions

なし。

## Follow-up

- 便B: Webhook 送信（別 PR）
- 各便マージ後に tenant_001 テストサーバーで実機確認
