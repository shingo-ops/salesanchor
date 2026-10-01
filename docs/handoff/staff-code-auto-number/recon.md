# recon: スタッフ新規登録が「データベースエラーが発生しました」で失敗する

## PO 依頼（原文 2026-10-01）
「スタッフコード（空欄なら自動採番 EMP-00001 形式）→登録画面には表示させず、バックエンドで自動採番してくれれば良い。　保存を試したがデータベースエラーが発生しました。と表示が出て保存できなかった」

## 本番ログ（Opus が read-only で確認）
- backend log 2026-10-01T12:08:59Z
  `StringDataRightTruncationError: value too long for type character varying(20)` on `INSERT INTO staff (... staff_code ...)` -> 500「データベースエラーが発生しました。」

## 原因（file:line）
- `/Users/tanizawashingo/salesanchor/backend/app/services/tenant.py:590` `staff_code VARCHAR(20) NOT NULL`
- `/Users/tanizawashingo/salesanchor/backend/app/routers/staff.py:543-544`（修正前）仮コード `f"EMP-PENDING-{uuid.uuid4().hex}"` = 12 + 32 = 44 文字 > 20
- 同 `:574-577`（修正前）の `UPDATE ... 'EMP-%05d'` には到達しない（INSERT で失敗）
- commit 2a23aeeba (#101) 以来の既存不具合。SQLite テストは長さを強制しないため CI で検出されなかった。

## staff_code を create で渡す呼び出し元の全走査
- grep `staff_code` (backend/frontend/src/scripts/docs/adr):
  - `frontend/src/pages/staff/StaffPage.tsx`（登録フォーム。今回削除）
  - `frontend/src/components/StaffFormButtonMigration.test.tsx`（同フォームのテスト。今回更新）
  - `scripts/data_migration/*`, `scripts/setup_*`, `scripts/qa/seed-tenant.sql`: DB 直 INSERT で API 非経由
  - `backend/tests/*`: DB 直 INSERT
- `POST /staff` に staff_code を渡す他の呼び出し元（CSV インポート等）は無し。
- `StaffEditPage.tsx` は staff_code を表示のみ（型 `staff_code: string`）。変更不要。

## 関連 ADR
- 対象 ADR なし（staff_code 採番を規定する ADR は `grep -rli "staff_code" docs/adr` で ADR-023 のみヒット、採番規則の記述なし）。
- 参考: `docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md`（staff ライフサイクル）
