# Meta 審査用の会社のログイン確認なしスイッチ — 現在地（recon）

この文書は、Meta の審査員が審査用アカウントでログインできるかを、今のコードと本番の記録で確かめた結果です。

- 親（あるべき姿）: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)・決定 [ADR-1055](../../adr/ADR-1055-new-device-login-approval.md)
- 対の設計: [review-exempt-design.md](review-exempt-design.md)
- 区分（STANDARD-WORKFLOW §1.8）: 既存の延長・修正（ADR-1055 のテーマの子に足す）
- 基準: origin/main `feb07fbe0`（2026-11-21 22:38 JST）。調べた人: Claude Opus（設計担当）

## A. 既存 ADR の検索

- `git ls-tree origin/main docs/adr/ | grep -iE '1055|1048|1013'` → ADR-1013（自社ログイン）・ADR-1048（管理者の2段階）・ADR-1055（知らない機械の許可）。
- `git grep -n -iE 'review@salesanchor|tenant-review|審査用' origin/main -- backend/app docs/adr` → 審査用の受信箱の見張り（`backend/app/celery_app.py:151`、`backend/app/tasks/review_mail_monitor.py:24`）と撮影の ADR（ADR-013・016・018・019）。ログインの確認を外す決まりは **該当なし**。
- ADR-1055 What 9「点検専用の人には管理用の命令で印を発行」は、印（Cookie）を手で入れる方式。外の審査員の機械には入れられないので、今回は使えない。

## B. 本番の設定

- 本番は確認を必ず行う設定: `.github/workflows/deploy.yml:442` `AUTH_DEVICE_APPROVAL='enforce'`。
- 設定の読み方: `backend/app/auth/devices.py:56-62`（`approval_mode()` / `is_enforced()`）。設定は全員に効き、人ごとの例外は無い。

## C. ログインの判定（パスワードでのログイン）

`backend/app/routers/auth.py:425-475`:

1. `backend/app/routers/auth.py:431` いつもの機械の印があれば通す（`find_trusted_device`、`backend/app/auth/devices.py:185-201`）。
2. `backend/app/routers/auth.py:438` `last_login IS NULL` かつ機械の行が0件なら、最初の機械として登録して通す（D5）。
3. `backend/app/routers/auth.py:452-475` それ以外は許可依頼を作り 202 を返す。トークンは出さない。依頼は30分（`backend/app/auth/devices.py:36` `REQUEST_TTL`）。

## D. ログインの後で機械を確かめる場所（4か所）

| 場所 | 行 | 機械が無い組への扱い |
|---|---|---|
| パスワードのログイン | `backend/app/routers/auth.py:429` | 上の C |
| トークンの更新 | `backend/app/routers/auth.py:552-570` | 締切より後の組は 401（ログアウト） |
| パスワードの変更 | `backend/app/routers/auth.py:769-779` | 403 `device_not_trusted` |
| パスキーのログイン | `backend/app/routers/auth.py:1188-1200` | 機械を登録して通す（許可は求めない） |

- 締切は `AUTH_DEVICE_BOOTSTRAP_CUTOFF`（`backend/app/auth/devices.py:65-76`）。仕組みを入れた日に固定済み。
- 結論: ログインだけ通しても、更新の場所で機械が無いと 401 になる。例外はログインと更新の2か所に要る。

## E. 本番の記録（reader 鍵・読み取りだけ・2026-11-21 22:24 JST）

- tenant 6 =「Sales Anchor App Review」（tenant_code `tenant-review`）・有効。
- 有効な人は1人だけ: users.id=10（review@salesanchor.jp・role admin・is_super_admin False・last_login 2026-10-30 14:27:36Z）。
- ほかの4人（id 80・81・82・86）は is_active False。
- tenant 6 の人の `user_trusted_devices` は0件。`auth_login_requests` も0件。
- id=10 のパスキー（`webauthn_credentials`）は0件、予備の合言葉（`user_recovery_codes`）は0件（2026-11-21 23:11 JST）。今は期限の後に残る入口は無い。生の出力: `/tmp/CC報告ファイル/meta-review-login/prod_id10_entry.txt`。
- 事実の組み合わせ: id=10 は last_login が入っているので D5 に当たらない。機械も0件なので C の 1 にも当たらない。**どの機械からでも 202 で止まる。** 生の出力: `/tmp/CC報告ファイル/meta-review-login/prod_tenant6.txt`（社外に出さない）。

## F. 記録と知らせの既存の道

- ログインの記録は1か所: `public.auth_events`（`backend/app/middleware/audit.py:245-266`）。`reason` は50字（`migrations/20261101_130000_add_new_device_approval.sql:119`）。
- 新しい機械の知らせメール: `send_new_device_mail`（`backend/app/routers/auth.py:444-451` の使い方）。
- review@ の受信箱は5分ごとに見て Discord へ知らせる（`backend/app/celery_app.py:151`、`backend/app/services/review_mail_notifier.py:125`）。

## G. データの置き場（SSOT）

- 人の正本は `public.users`（ADR-1008）。人ごとの設定を列で足した前例: `migrations/20261117_100000_add_users_secretary_voice.sql:2`（`scripts/run_all_migrations.sh:1476` で流す）。
- 機械の登録の経路は DB の決まりで7種類に固定（`migrations/20261101_130000_add_new_device_approval.sql:21-22`）。ここに種類を足すと決まりの作り直しが要る。

## H. 画面の金型（ADR-144）

- 置き場の候補: super admin の「ログインの許可待ち」画面 `frontend/src/pages/super-admin/LoginRequestsPage.tsx:40-52`（`PageLayout` と `UserManagementSubMenu` を使用）。
- 使える金型（`frontend/src/components/`）: `frontend/src/components/SectionCard.tsx`・`frontend/src/components/TextField.tsx`・`frontend/src/components/Select.tsx`・`frontend/src/components/Button.tsx`・`frontend/src/components/DataTable.tsx`・`frontend/src/components/ConfirmModal.tsx`。
- 日付を選ぶ金型は見つからない。日数を `Select` で選ぶ形にすれば新しい金型は要らない。（注: 前の版の案。2026-11-22「1」の形では日数を選ばず、ON は最長14日で自動 OFF のため使わない）

## I. 試験と必須チェック

- 機械の許可の試験: `backend/tests/test_new_device_approval.py`。
- 試験を流す仕組み: `.github/workflows/test.yml:120`（`pytest-run-internal`）、移行の試験 `.github/workflows/migration-test.yml`。

## J. 外の事例（出典つき）

- Meta の申請の手引きは「審査員がアプリに入れる情報（テスト用のログイン情報など）」を求め、入れなければ対応依頼が来ると書いている（[Meta App Review submission guide](https://developers.facebook.com/documentation/resp-plat-initiatives/individual-processes/app-review/submission-guide)・2026-11-21 閲覧）。
- 開発者の報告では、2段階の確認がある口座は審査員が入れず、確認なしの口座を出し直して通した例がある（[Meta 開発者コミュニティ](https://developers.secure.facebook.com/community/threads/442251551600133)・個人の報告・数値なし。設計の成功の証明には使わない）。

## 未確認

- Meta の申請の「審査員への説明」に、review@ のパスワードが今の値で書かれているか（PO の申請画面で確かめる）。
- 本番でメール送信が今も成功しているか。ADR-1055 のステータス欄に「PO が知らせメールを本番で目で確かめた（2026-11-05）」とあるが、今日の時点では確かめていない（受入基準 K6 で確かめる）。

## K. 会社の表の書き込みの決まり（2026-11-22 追加・PO の条件「会社006だけ」の書き直し用）

- `public.tenants` は読み取りは全行可、書き込みは運営の文脈（`app.is_operator = 'true'`）のときだけ（`migrations/20261016_170000_add_tenants_write_rls.sql:9-23`）。会社の人が書くアプリの道は無い（`migrations/20261016_170000_add_tenants_write_rls.sql:4`）。
- 運営の文脈を付ける関数は `set_operator_context`／`reset_operator_context`（`backend/app/auth/dependencies.py:458-489`）。
- 会社の文脈を付けると `app.is_operator` は空に戻る（`backend/app/auth/dependencies.py:328`）。`_record_auth_audit`（`backend/app/routers/auth.py:282-293`）は会社の文脈を付けて外す。
- `public.users` も読み取りは全行可（`migrations/20261016_180000_add_users_write_rls.sql:9-10`）。
- 会社の行の型は `backend/app/models.py:8-17`（id・tenant_name・tenant_code・is_active・settings）。Meta 審査用の印の列は **無い**。
- 画面の金型: 切替スイッチ `frontend/src/components/Toggle.tsx`（checked・onCheckedChange・disabled・aria-label。className は受けない）、色の札 `frontend/src/components/Badge.tsx`（variant: neutral・info・success・warning・danger・purple）。
- 利用者管理の小さなメニュー: `frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx:38-46`（2つ目の組は「ログインの許可待ち」1つだけ）・`:49-50`（その鍵では何もしない）・`frontend/src/pages/super-admin/users/UserManagementSubMenu.tsx:63`（既定の選択）。道は `frontend/src/App.tsx:345`。

## L. ログインの記録の中身（2026-11-22 追加）

- 記録の書き手は1か所: `backend/app/middleware/audit.py:215-266`。`/api/v1/auth/` の口が対象（`backend/app/middleware/audit.py:37`）。
- 列: `event_type`・`path`・`method`・`status_code`・`client_ip`・`user_agent`・`created_at`（`migrations/001_create_auth_events.sql:6-16`）と `user_id`・`reason`・`is_new_device`（`migrations/20261101_130000_add_new_device_approval.sql:118-120`）。
- 打ったメールアドレスは記録に無い。会社に無いメールで試した回は `user_id` が NULL（`backend/app/routers/auth.py:413`）。
- 本番の id=10 の行は0件（reader 鍵・2026-11-21。生の出力 `/tmp/CC報告ファイル/meta-review-login/prod_id10_events.txt`）。
