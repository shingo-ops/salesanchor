# recon: Firebase を画面とサーバーから全部外す（ADR-1013 便6）

- 調べた日: 2026-11-04 18:00〜18:50 JST（Opus）
- 基準: `origin/main` 7d56ab771（worktree `release/firebase-removal-design`）。本店の写しは古いので使っていない。
- 本番の DB は reader 鍵（ai_ro のビュー）で読んだ。1 文ずつ流し、AUDIT 行を残している。
- 前の便: `docs/handoff/block-firebase-token/`（自社ログイン中は Firebase の札を 401 にする。#5118・11/4 17:49 JST 本番反映）。

## 0. 既存 ADR の検索結果

- `docs/adr/ADR-1013-self-hosted-auth-and-passkey.md`
  - Decision 6: 「切替はスイッチ（AUTH_PROVIDER）で行い、Firebase のユーザー削除は最後の便で PO の GO を取ってから行う」。
  - Consequences: 「qa-smoke・rotate-qa-firebase・snapshot・smoke は便6 で置き換える」「Firebase のユーザー削除（便6）だけは戻せない」。
  - 関連欄: 「ADR-032（Firebase 認証ドメイン）と ADR-023（3 層同期・提案）は便6 完了時に Superseded とする」。
- `docs/handoff/auth-self-hosted-passkey/design.md:160`（便6 の行）、`:195`（K3）、`:226`（戻し方）。
- ADR-1051 D5（`docs/handoff/qa-smoke-rebuild/design.md`）: 古い qa-smoke 資産の削除は、新しい点検が 14 日続けて合格した後に行う。対象は qa-smoke.yml・scripts/qa・tests/qa-smoke・QA_* の secrets 13 個。**この設計では触らない**（持ち主は ADR-1051）。
- ADR-1024（ai_ro）・ADR-1052（ai_cloud）: 列を消すときのビューの扱い（R20）。
- 名前のかぶり: `docs/handoff/auth-self-hosted-passkey/card-b6-login-enroll.md` は、パスキー登録の案内にも「便6」という名前を使っている。この設計の「便6」は design.md:160 の Firebase 撤去を指す。

## 1. 事実（ファイル:行）

### サーバー（backend）

- R1: Firebase の確かめは `backend/app/auth/dependencies.py` の 1 か所だけ。
  - import は :8・:11・:12（`firebase_admin`）。
  - 初期化 `_init_firebase` は :50-70 にあり、:155 から呼ばれる。
  - :210-212 の `firebase_closed = self_tokens.auth_provider() == "self"` から 401 で断る（#5118）。その後ろが Firebase の確かめの分岐（`verify_id_token`・MFA の確認・email で引く・tenant_id の確認・一時記憶）。
- R2: スイッチは `backend/app/auth/self_tokens.py` にある。
  - :21 `DEFAULT_AUTH_PROVIDER = "firebase"`。
  - :39-40 `auth_provider()`。
  - :69-71 `is_issuance_enabled()` は self で、かつ秘密があるときだけ真。
  - :81-85 `validate_settings()` は firebase と self 以外の値を拒む。`backend/app/main.py:183` から呼ばれる。
- R3: スイッチを読む所は次のとおり（R2 の他）。
  - `backend/app/routers/auth.py:222`・`:599`・`:767`・`:808`
  - `backend/app/routers/staff.py:642`
  - `backend/app/services/invite.py:20-21`（firebase の間は初回設定のメールを作らない）
  - `backend/app/auth/dependencies.py:86`・`:129`・`:212`
- R4: `backend/app/auth/utils.py:13-15` `set_tenant_claim` は Firebase のカスタムクレームを書く。同じファイルの `generate_password` は `scripts/setup_review_tenant.py:438`・`scripts/setup_test_users.py:278`・`backend/tests/test_password_gen.py:13` が使う。
- R5: `backend/requirements.txt:13` `firebase-admin==6.6.0`。
- R6: `bcrypt` は**消せない**。`backend/requirements.txt:10` `bcrypt==4.2.1` は `backend/app/routers/bots.py:18`・`:59` が使っている（ボットの API キーの保管）。`docs/handoff/auth-self-hosted-passkey/design.md:160` の「`bcrypt` の除去」はこの事実と食い違う。
- R7: Google の部品で Firebase 以外が使うものは次のとおり。
  - `google-api-python-client`・`google-auth-oauthlib`・`google-auth-httplib2`（`backend/requirements.txt:40-42`）
  - 使っている所: `backend/app/services/google_calendar.py:125-305`、`google_drive_oauth.py:161-384`、`google_webhook.py:241`、`tcg_distribution_svc.py:81`、`backend/app/tasks/tcg_mirror.py:70`
  - `google.cloud` と `google.api_core` を直接 import している所は backend・scripts・tools に 0 件（`git grep` の結果は 0 行）。
  - firebase-admin を外したときに `google.oauth2` などが入るかどうかは、まだ確かめていない（未確認 U1）。
- R8: `GOOGLE_APPLICATION_CREDENTIALS` を backend/app で読むのは `backend/app/auth/dependencies.py:64` だけ。
  - 他に読む所: 運用スクリプト `scripts/setup_review_tenant.py:99`・`scripts/setup_single_test_user.py:103`・`scripts/setup_test_users.py:60`
  - 設定する所: `docker-compose.yml:69`・`:241`・`scripts/blue-green-cutover.sh:99`
  - 鍵ファイルのマウント: `docker-compose.yml:161`・`:298`・`scripts/blue-green-cutover.sh:94`
  - 表サービス用の鍵は別のファイル（`TCG_SHEETS_SA_KEY_FILE`）を使う。
- R9: `staff.firebase_uid` の列は次の所にある。
  - 列を作る所: `migrations/019_create_staff_tables.sql:51`、新しい会社の型紙 `backend/app/services/tenant.py:614`
  - 試験の足場: `backend/tests/conftest.py:512`・`backend/tests/rls_bootstrap.py`
  - 伏せる列の一覧: `migrations/20261024_100300_create_ai_cloud_views.sql:535`
  - アプリのモデルにこの列は無い（`backend/app/routers/staff.py:265-271` の注記）。
  - アプリのコードで値を読み書きする所は見つかっていない（検索の結果は注記とスクリプトだけ）。
- R10: 注記だけで Firebase に触れている所: `line_import_devices.py:1`・`staff.py:265-271`・`leads.py:1241`・`cache.py:306`・`session_guard.py:37`・`routers/auth.py:186`・`schemas/auth.py:19`・`review_mail_notifier.py:14`・`line_device_admin.py:4`・`tools/termux-line-import/device_session.py:1`。

### 画面（frontend）

- R11: Firebase の部品を読み込む所（試験を除く）は次のとおり。
  - `frontend/src/lib/firebase.ts:15-16`（本物の初期化と、開発中の偽物 :351・:366-393）
  - `frontend/src/lib/firebase-auth.ts`（開発中の偽物。:27 `useFakeFirebaseAuth = import.meta.env.DEV`、:28 保存の鍵 `salesanchor:e2e-firebase-auth-user`。:151-159 `sendPasswordResetEmail` は偽物のとき何もせず成功する。:169-189 再認証とパスワード変更の偽物）
  - `frontend/src/contexts/AuthContext.tsx:8`・`:14`
  - `frontend/src/lib/auth/selfAuth.ts:9`
  - `frontend/src/pages/account-settings/SecuritySection.tsx:7-9`
  - `frontend/src/pages/login/LoginPage.tsx:5`・`:44`
- R12: 画面のスイッチは `frontend/src/lib/auth/provider.ts`。
  - :14-15 `getAuthProvider()`
  - :19-20 `isSelfAuth()` は `getAuthProvider() === "self" && !import.meta.env.DEV`。開発サーバーと e2e では、自社 API を呼ばずに Firebase の偽物を使う。
  - `isSelfAuth` を使う所: `AuthContext.tsx:60`、`LoginApprovalWatcher.tsx:34`、`RecoveryCodePrompt.tsx:61`、`api.ts:83`、`passkey.ts:23`、`selfAuth.ts:224`・`:236`、`SecuritySection.tsx:262`・`:366-369`、`LoginPage.tsx:44`。
- R13: `selfAuth.ts:223-232` `getAccessToken()` は、self でなければ Firebase の `auth.currentUser.getIdToken()` を返す（:224 が分かれ目）。`:235-237` `hasSession()` も同じ分かれ方をする（:236）。
- R14: 誤りの文言は次のとおり。
  - `frontend/src/lib/firebaseErrorMessage.ts` を使う所は `LoginPage.tsx:44`（self でないとき）と `SecuritySection.tsx:9`・`:302`。
  - 文言のキー `firebaseError` は `frontend/src/locales/ja.json:3274`・`en.json:3274`。
  - 自社用の `frontend/src/lib/auth/authErrorMessage.ts:4` に「firebaseErrorMessage.ts は便6 まで残す」とある。
- R15: 部品と試験の足場は次のとおり。
  - `frontend/package.json:84` `"firebase": "^11.0.0"`
  - Storybook の差し替え: `frontend/.storybook/main.ts:34-35`、`frontend/src/lib/__storybook-mocks__/firebase-app.ts`・`firebase-auth.ts`
  - 単体試験の共通足場: `frontend/src/test-setup.ts`（`./lib/firebase` を差し替える）。`frontend/vite.config.ts` の unit の `setupFiles` から読む。
  - `vi.mock` で firebase を差し替える試験は 14 ファイル。
- R16: e2e は開発サーバー（`npm run dev`）で動く。
  - 設定: `frontend/playwright.config.ts:150-151`・`:140-160`。偽の VITE_FIREBASE_* の値を渡している。
  - ログインは `frontend/tests-e2e/utils/auth.ts:23`・`:31` が `window.__salesanchorE2eAuthUser` と保存の鍵 `salesanchor:e2e-firebase-auth-user` を入れて、R11 の偽物に通している。
  - 偽の値を渡す workflow: `.github/workflows/e2e.yml:204`・`:311`、`karte-gate.yml:75`・`:85`・`:110`。
- R17: ビルドで Firebase の値を受け取る所は次のとおり。
  - `frontend/Dockerfile:7-13`（ARG・ENV 3 組）
  - `docker-compose.yml:201-203`（build args）。`:205` `VITE_AUTH_PROVIDER: ${VITE_AUTH_PROVIDER:-firebase}`
  - `.github/workflows/deploy.yml` に VITE_FIREBASE の行は無い。本番の値はサーバーの `.env` にある。
  - deploy.yml の `:318`・`:320` は `AUTH_PROVIDER` と `VITE_AUTH_PROVIDER` の行を消し、`:378`・`:380` は両方を `'self'` で書き直す。
- R18: CSP は次のとおり。
  - `nginx/nginx.conf:96` は `server_name app.salesanchor.jp`（:79-393 の塊）にある。中身は `script-src 'self' https://www.gstatic.com; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com`。
  - frontend/src にある googleapis・gstatic の参照は firebase の部品だけ（前の調べ hits.txt）。

### 運用・CI・監視

- R19: Firebase に依存する運用の部品は次のとおり。
  - `.github/workflows/external-state-snapshot.yml:82-88`（週 1 回 `'0 18 * * 6'`。`scripts/snapshot/firebase.sh` を `secrets.FIREBASE_API_KEY` で流す）。同じ workflow の GCP の段（:120 付近）は Firebase と別なので残す。
  - `.github/workflows/rotate-qa-firebase.yml`（手動だけ。ADR-1051 D5 の削除一覧に入っていない）
  - `scripts/smoke/external-firebase.sh`（呼ぶ所はコメントの相互参照だけ）
  - `docs/external-state-contract.yml:29-37`
  - `scripts/detect-external-api-change.js:84-89` とその試験 `scripts/tests/test-detect-external-api-change.js:128`・`:199`
  - `monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json:124-132` の「Firebase Auth」の板。Uptime Kuma の監視そのものはリポジトリの外にある。
  - 運用スクリプト `scripts/setup_review_tenant.py`・`scripts/setup_single_test_user.py`・`scripts/setup_test_users.py`（firebase_admin を使う）、`backend/tests/test_setup_review_tenant.py`
  - `scripts/setup_tenant.py:29`・`:471`（「Firebase ユーザーを作る」という案内の文）
  - `.env.example:17-30`・`:87-88`、`frontend/.env.example`、`.gitignore:29-30`、`.gitleaks.toml:38-40`、`backend/.dockerignore:14`
- R20: 列を消すときのビューの扱いは次のとおり。
  - `scripts/run_all_migrations.sh:220` が ai_cloud のビューを、`:224` が ai_ro のビューを、どの migration よりも先に外す。作り直しは最後の EXIT trap で行う（`:231`・`:234` 以降）。
  - ai_cloud のビューは、今ある列だけから作られる。`migrations/20261024_100000_create_ai_cloud_meta.sql:95-108` が `pg_attribute` を元に回し、分類表を LEFT JOIN している。
  - 分類の漏れの検査 `backend/tests/ops/test_ai_cloud_views.py:490-521` も、今ある列から数える。
  - このため、列を消した後に分類表の行が残っても、ビューの作り直しと検査は止まらない。分類表の行数の試験（`backend/tests/ops/test_ai_cloud_views.py:484` の `== 1068`）は、行を消すと直す必要がある。
- R21: 試験の総数は次のとおり。
  - `firebase` を含むファイルは、docs を除いて、大小を無視すると 120 個、大小を区別すると 90 個（2026-11-04 に数え直した。前に書いた 115 個は数え方を記録していなかったので使わない。一覧は R32）。
  - 一番多いのは `frontend/package-lock.json` の 260 行（部品の中身）。
  - backend の試験で Firebase に触れるのは 15 ファイル。

### 本番の実物（reader 鍵・2026-11-04 18:41〜18:42 JST）

- R22: `public.users` は 15 人。使用中は 9 人。そのうち 10/20 以降にログインした人は 4 人で、直近 7 日も 4 人。
- R23: `staff.firebase_uid` が空でない行は次のとおり。
  - tenant_001: 2 行中 0
  - tenant_003: 0 行
  - tenant_004: 2 行中 0
  - tenant_005: 0 行
  - tenant_006: 4 行中 1（値は伏せて読んだ。中身は見ていない）
- R24: 自社ログインに切り替えたのは commit f86defebc（2026-10-30）。本番の deploy は `AUTH_PROVIDER='self'` と `VITE_AUTH_PROVIDER='self'` を毎回書く（R17）。
- R26: tenant_006 の `firebase_uid` が入った 1 行は、`user_id` が埋まっていて（人の正本とつながっている）、状態は active（2026-11-04 18:48 JST・AUDIT sha=f745ae66efa6）。アプリはこの列を読まない（R9）。列を消して失われるのは Firebase の利用者の番号だけで、Firebase の利用者を消した後は使い道が無い。
- R25: GCP プロジェクト `sales-ops-with-claude` は Google カレンダー連携の OAuth でも使う（`.env.example:17-30`・`:87-88`）。**プロジェクトは消さない。消すのは Auth の利用者だけ**。
- R27: 本番の画面のファイルには、開発用の偽ログインの文字がもう入っている。2026-11-04 に本番の `assets/main-CQpfABgR.js`（2,579,127 バイト）を取って数えた: `__salesanchorE2eAuthUser` 1 件、`e2e-firebase-auth-user` 1 件、`e2e-fake-id-token` 2 件、`firebase`（大小無視）88 件、`googleapis` 5 件、`gstatic` 0 件。`googleapis` の 5 件の内訳は `identitytoolkit.googleapis.com` 2・`securetoken.googleapis.com` 1・`staging-identitytoolkit.sandbox.googleapis.com` 1・`test-identitytoolkit.sandbox.googleapis.com` 1 で、全部 Firebase のログインの宛先。`import.meta.env.DEV` で分けても、静的に読み込んだ偽物の文字はビルドから落ちていない。
- R28: 開発サーバーで今止まっている機能（`isSelfAuth()` が false のため）: `api.ts:83` の 401 の送り直し、`passkey.ts:23` のパスキーのボタン、`LoginApprovalWatcher.tsx:34`、`RecoveryCodePrompt.tsx:61`、`SecuritySection.tsx:366-369` の 4 つの欄（通知・機械・回復コード・パスキー）。`SecuritySection.tsx:262` のパスワード変更は Firebase の偽物の再認証（`firebase-auth.ts:169-189`）を通る。e2e にパスワード変更・パスキー・回復コード・新しい機械の許可・セキュリティの欄の試験は無い（`frontend/tests-e2e` の検索が 0 件）。
- R29: e2e のパスワード再設定の試験 `frontend/tests-e2e/login.spec.ts:51` は `**/identitytoolkit.googleapis.com/**sendOobCode**` を偽の応答に差し替えている。自社の再設定は `selfAuth.ts:212` が `/password-reset/request` に送る。
- R30: backend の Google の部品の import（Firebase 以外）: `google.oauth2.credentials`（`google_calendar.py:228`・`google_drive_oauth.py:257`）、`google.oauth2.service_account`（`tcg_distribution_svc.py:81`・`:1007`、`tasks/tcg_mirror.py:70`）、`google.auth.transport.requests`（`google_calendar.py:266`・`google_drive_oauth.py:295`）、`googleapiclient.discovery`・`googleapiclient.http`（`google_drive_oauth.py:384`）・`googleapiclient.errors`（`google_webhook.py:241`）、`google_auth_oauthlib.flow`（`google_calendar.py:125`）、`gspread`（`tcg_distribution_svc.py:80`）、`google.genai`（`gemini_extraction_svc.py:256`）、`google.generativeai`（`message_translator.py:107`）。`backend/requirements.txt:30`・`:32`・`:40-42`・`:44` に直接書いてある。`google-auth` だけは直接書いておらず、`google-api-python-client` などを通して入る。
- R31: `scripts/qa/seed-tenant.sql:110-120` は `tenant_006.staff` に `firebase_uid` を入れる INSERT が 3 つある。`scripts/qa/reset-tenant.sh:120-122` が値を渡す。`.github/workflows/qa-smoke.yml:12` のとおり定期と PR での実行は 2026-10-30 に止まっていて、手で動かしたときだけ走る。
- R32: 他に Firebase の文字がある所: `backend/tests/test_staff_create_users.py:163`・`:232`（`staff.firebase_uid` を SELECT）、`backend/tests/rls_bootstrap.py:238`・`:253`（試験の足場の `public.users` の列）、`backend/tests/ops/test_ai_cloud_views.py:556`（足場だけの列の一覧）・`:484`（列の分類の数 1068）、`.github/workflows/api-contract-check.yml:35`・`:53`（`frontend/api-contract/openapi.json` を作り直してコミットする決まり）。注記だけの所: `AGENTS.md:17`、`scripts/run_all_migrations.sh:612`、`tools/termux-line-import/README.md:17`・`:19`・`:92`、`tools/termux-line-import/device_session.py:1`、`frontend/src/contexts/UiPrefsContext.tsx:46`、`frontend/src/lib/query/QueryAuthSync.tsx:3`、`frontend/src/lib/api.ts:3`・`:41`・`:73`、`frontend/src/lib/auth/authErrorMessage.ts:4`、`frontend/tests-e2e/scene1-dashboard.spec.ts:370`、`frontend/tests-e2e/visual-language/viewer-focus-trap.spec.ts:83`、`frontend/tests-e2e/visual-language/viewer-helpers.ts:8`。設定の行: `frontend/playwright.config.ts:149-152`、`.github/workflows/e2e.yml:202-204`・`:309-311`、`.github/workflows/karte-gate.yml:73-75`・`:83-85`・`:108-110`、`frontend/Dockerfile:7-9`・`:12-14`（Firebase と GCP）と `:11`・`:16`（`VITE_AUTH_PROVIDER`）。`:10`・`:15` の `VITE_FUNNEL_DASHBOARD` は Firebase と関係ない。`backend/app/main.py:183` は注記（「既定 firebase」）で、`:184` の `self_tokens.validate_settings()` の呼び出しは残す。Firebase の文字があるファイルは、`docs/` を除いて 120 個（2026-11-04 の `git grep -il firebase`）。

## 2. 推測

- 無し。下の未確認は、確かめるまで設計の前提にしない。

## 3. 未確認

- U1: firebase-admin を外した後も、`google.oauth2`・`google.auth.transport.requests`・`googleapiclient`・`google_auth_oauthlib` が入るか。設計では、便2 の受け入れ基準 K4 で「入れ直した環境で import が通る」ことを機械で確かめる（対象の一覧は R30）。
- U2: Firebase の利用者は今何人か。最後に数えたのは 10/13 の 12 人（ADR-1013 Context）。削除の便（便5）の直前に、PO の画面か書き出しで数える。
- （U3 は確かめ済み → R26）
- U4: サーバーの `.env` にある `VITE_FIREBASE_*`・`GCP_PROJECT_ID` を他に読む所があるか。リポジトリの中では R8・R17 以外に見つかっていない。サーバーの上の他の仕組みはまだ確かめていない。
- U5: Uptime Kuma の「Firebase Auth」の監視の設定（リポジトリの外）。
- U6: Firebase で有効になっているログインの方法（メールとパスワードのほか、Google などがあるか）と、画面用の API キーがほかの用途に使われているか（GCP の画面。リポジトリの外）。便5 のカードで確かめる。
