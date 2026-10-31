# Phase 2 現在地 — ログイン直後のパスキー登録（ADR-1013 便5 の続き）

調べた日: 2026-10-31。基準: `origin/main` = `8c6f52813e23f131dbe2466cad01d2b4d2f4c361`。
コードの読み取りはクラウド Sonnet（読むだけ）と Opus の `git show origin/main:<path>` の両方で行い、下の行番号は Opus が `git show` で確かめた。

## 既存 ADR の検索

- `docs/adr/ADR-1013-*`（自社ログイン・パスキー。便5 でパスキー登録を設定画面に置いた）→ 本件はその続き
- `docs/adr/ADR-1048-admin-two-step-login.md:4` は Proposed（2026-10-27）。管理者の 2 段階の確認は、まだ画面に実装されていない（frontend の ts/tsx に mfa・totp・2fa の該当なし。viewer と firebase.ts だけ）
- ADR-027（i18n）・ADR-144（UI 金型）・ADR-025（手動 INSERT 禁止）を守る

## 1. ログイン成功後の流れ（frontend）

- パスワードでのログインは `frontend/src/pages/login/LoginPage.tsx:45-59` の `handleSignIn`。`await signIn(email, password)`（:50）の直後に `navigate(from, { replace: true })`（:52）
- パスキーでのログインは別の関数 `handlePasskeySignIn`（`LoginPage.tsx:61-76`）→ **パスワード経路だけに処理を足せる**
- ログイン済みで /login を開くと自動で移る `useEffect`（`LoginPage.tsx:39-43`）がある。更新用トークンでの復帰もここを通るので、`user` の出現をきっかけにすると、パスワードを打っていない時にも出てしまう → `handleSignIn` の中だけに足す
- 初回パスワード変更の強制は社内の利用者には無い（`password_must_change` は viewer 側だけ: `backend/app/auth/viewer_dependencies.py:51`）

## 2. 今のパスキー登録

- 部品: `frontend/src/lib/auth/passkey.ts:38-49` `registerPasskey(label)` が options 取得 → `startRegistration({ optionsJSON })`（:43）→ verify
- 誤りの見分け: `passkey.ts:52-57`（NotAllowedError→cancelled、InvalidStateError→exists）
- 設定画面: `frontend/src/pages/account-settings/PasskeySection.tsx`（名前を入れて登録・一覧・削除。`ConfirmModal` を使用）
- 道具: `frontend/package.json:78` `"@simplewebauthn/browser": "14.0.0"`
- 14.0.0 の `startRegistration` は `useAutoRegister`（既定 false）を受け、true のときだけ `mediation = 'conditional'` を付ける。失敗は `identifyRegistrationError` で投げ直す（公式配布物 https://unpkg.com/@simplewebauthn/browser@14.0.0/esm/methods/startRegistration.js を 2026-10-31 に直接確認。Context7 は月の上限で使えなかった）
- 【未確認→設計で回避】14.0.0 に「自動作成ができる端末か」を調べる関数があるかは確かめていない。設計では標準の `PublicKeyCredential.getClientCapabilities()` の `conditionalCreate` を直接見る

## 3. サーバー側（backend）

- 登録 options: `backend/app/routers/auth.py:690-710`。本人の既存パスキーを `exclude_credentials` に入れる（`backend/app/auth/passkeys.py:76`）。上限 10 個で 409（`auth.py:704-705`・`passkeys.py` `MAX_PASSKEYS_PER_USER = 10`）
- options の決まり: `passkeys.py:72-74` resident_key REQUIRED・user_verification REQUIRED
- 登録 verify: `auth.py:713-777`。`verify_registration_response(..., require_user_verification=True)`（:727-733）。challenge は `take_challenge("reg", user_id, challenge_id)`（:722）
- 道具: `backend/requirements.txt` `webauthn==2.8.0`。`verify_registration_response` は `require_user_presence: bool = True`・`require_user_verification: bool = False` を受ける（公式 https://raw.githubusercontent.com/duo-labs/py_webauthn/v2.8.0/webauthn/registration/verify_registration_response.py を 2026-10-31 に確認）
- **自動作成では、端末が「本人がその場にいた」「顔・指紋で確かめた」の印を立てないことがある**（Chrome 公式: サーバーは自動作成のとき UP・UV の印を無視する）→ 今の verify（UV 必須・UP 既定で必須）では自動作成の登録が 400 になる
- ログインの合図（アクセストークン）: `backend/app/auth/self_tokens.py:92-104` に `iat`（発行時刻）と `amr`（ログイン方法）。`amr` は パスワードのログイン `auth.py:360` とパスワード変更 `auth.py:633` で `"pwd"`、パスキーのログイン `auth.py:882` で `"webauthn"`、更新 `auth.py:391` で付けない
- 合図の読み取りは `backend/app/auth/dependencies.py:82-109`（`_authenticate_self_token`）。`claims` は口（endpoint）に渡っていない
- 監査記録は `_record_auth_audit`（`auth.py:250`）。#4942 の直しで会社を指定してから書く

## 4. 「スキップ」の回数と日時の置き場

- 人ごとの設定の表は無い。`public.users.theme`（`migrations/054_add_users_theme.sql`）は 1 値の列。`staff_ui_preferences`（`migrations/019_create_staff_tables.sql:91`）は会社ごとの schema にあり、ログインの人（public.users）ではない
- パスキーの表 `public.webauthn_credentials`（`migrations/20261013_160000_add_self_hosted_auth_tables.sql:16-33`）は RLS なし（同ファイル:3「テナントが決まる前に引くため」）・`salesanchor_app` に GRANT（:96-101）
- 試験の SQLite 版の表は `backend/tests/conftest.py:1366-` に手で書いてある（`public.` を外す置換は :324-325）

## 5. 画面の金型

- `frontend/src/components/Modal.tsx:25-` `Modal({ open, onClose, title, size, dismissOnOverlay, children, footer })`
- `Button`・`Stack` は LoginPage が既に使用（`LoginPage.tsx:10-11`）
- パスキーの文言は `frontend/src/locales/ja.json`・`en.json` の `accountSettings.passkey*`・`authError.passkey*`

## 6. 試験

- `backend/tests/test_passkeys.py`・`backend/tests/test_rls_auth_audit.py`・`backend/tests/test_auth_audit_helper.py`
- `frontend/src/lib/auth/passkey.test.ts`・`frontend/src/pages/account-settings/PasskeySection.test.tsx`・`frontend/src/pages/login/` の LoginPage 試験
- e2e: `frontend/tests-e2e/login.spec.ts`（パスキーの試験なし）

## 7. 本番の基準値（読み取りのみ・2026-10-31 18:27 JST）

| 項目 | 値 |
|---|---|
| パスキーを持つ人 | 1 人（2 個） |
| パスワードでログインできる有効な人 | 9 人 |
| 直近 14 日にログインした有効な人 | 4 人 |
