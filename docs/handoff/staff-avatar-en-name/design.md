# design: 担当者アイコン登録・英語名必須化（ADR-159 便A）

参照: docs/adr/ADR-159-staff-identity-on-discord.md、docs/handoff/staff-avatar-en-name/recon.md、docs/adr/ADR-072、docs/adr/ADR-027、docs/adr/ADR-144

## 目的（PO 承認 2026-10-01 verbatim）

- 表示名: 「名だけ (例: Shingo) (推奨)」
- 英語名: 「①…→必須項目とする、Discordは名前で表示」
- アイコン未登録: 「②…→discordのアイコンなしの状態と同じ表示」
- 失敗時: 「⑤…Bot感を出さずに顧客には演出してあげたい」→「送らずに止める (推奨)」
- エラー表示: 「フロントにも非エンジニアである担当者が理解できる内容でエラーメッセージを表示させて対応方法までCTA，簡潔に」
- 設計承認: 「この設計で進める (推奨)」（新金型 AvatarUpload の登録を含む）

## 便A の範囲（1便1目的）

便A = アイコン（avatar_token・Pillow・アップロード/削除/公開 API・AvatarUpload 金型・アカウント設定）と英語名必須化。便B（Discord webhook 送信）は含めない。

## 設計

- データ: staff.avatar_token TEXT NULL（additive）。画像実体は ATTACHMENT_ROOT/staff_avatars/<token>.webp。DB は token のみ
- API: POST/DELETE /api/v1/staff/me/avatar（本人のみ）、GET /api/public/staff-avatars/{token}.webp（認証不要・token 形式厳格検証・DB 参照なし）、StaffResponse.avatar_url
- 画像処理: 先頭バイト判定 jpg/png/webp・2MB 上限 → Pillow で EXIF 除去・中央正方形・256px WebP
- エラーコード: AVATAR_INVALID_TYPE(400) / AVATAR_TOO_LARGE(413) / AVATAR_SAVE_FAILED(500)
- 英語名: StaffCreate は名・姓とも必須、StaffUpdate・StaffProfileUpdate は指定時に空/null 不可（DB は NOT NULL にしない）
- 画面: 新金型 AvatarUpload（.tsx/.css/.stories・var() のみ・非表示 file input は type=file のためガバナンス禁止対象外）、アカウント設定のアイコン欄と英語名必須表示、スタッフ作成・編集の英語名必須。エラーは非エンジニア向け短文＋行動ボタン

## 受入条件

| 基準 | 検証方法 |
|---|---|
| jpg/png/webp のみ受理・2MB 超・偽装は拒否 | backend/tests/test_staff_avatar.py |
| 公開画像に EXIF が残らない・256x256 WebP | backend/tests/test_staff_avatar.py |
| 公開ルートは認証不要・不正 token とパストラバーサルは 404 | backend/tests/test_staff_avatar.py |
| 再アップロードで旧ファイル削除・削除は冪等 | backend/tests/test_staff_avatar.py |
| 英語名が作成/更新/プロフィールで必須（DB は NOT NULL にしない） | backend/tests/test_staff_avatar.py |
| 画像エラーが非エンジニア向け文言と行動ボタンで表示 | frontend ProfileSectionAvatar.test.tsx |
| AvatarUpload が .tsx/.css/.stories を持ち var() のみ | check:stories / check:css-colors / check:css-values / build-storybook |
| migration が冪等・既存行を壊さない | migration-test CI |

## 外部・過去事例の参照と我々への応用

- Discord webhook の username / avatar_url 上書き仕様: https://discord.com/developers/docs/resources/webhook
- OWASP File Upload Cheat Sheet: 内容で形式判定・再エンコードでメタデータ除去・推測不能なファイル名 → 先頭バイト判定・Pillow 再エンコード・token_urlsafe(32) として適用
- 過去事例: 認証不要ルーターの前例（backend/app/main.py の registration_tokens.public_router）に倣い公開配信ルーターを追加

## リスクと戻し方

- 公開画像 URL は token を知る者なら閲覧可（PO 承認④）。既存スタッフは編集時に英語名入力が必須になる
- 戻し方: PR を revert。migration は additive で列を残しても無害

## 維持の仕組み

- 守り手: backend/tests/test_staff_avatar.py と frontend の AvatarUpload / ProfileSectionAvatar テストが CI で常時実行。UI governance gate・check:stories が金型規約を検査。test_adr072_phase_2_reset_rollout.py が reset 呼び出し数を固定
