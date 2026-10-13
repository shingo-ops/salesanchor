<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — auth-self-hosted-passkey

> この文書は何か：ログインを Firebase から自社サーバーへ移し、顔・指紋（パスキー）でのログインを足す設計の前に、「今どうなっているか」を実物で確かめた記録です。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)

**仕事名**: auth-self-hosted-passkey  
**日付**: 2026-10-13  
**対象ADR**: ADR-138（パスワード保管の廃止＝本テーマで覆す）、ADR-127（認証失敗ロックの順序）、ADR-023（3層同期・提案のまま）、ADR-032（Firebase 認証ドメイン）、ADR-1008（人の正本＝public.users.id）。本テーマ専用 ADR は ADR-1012 として起案予定  
**担当**: 設計パートナー（Opus。リポジトリ調査は Sonnet、設計相談は Fable、本番の読み取りは PO の端末で実行）  
**基準**: origin/main `3c451d5e0`

---

## 既存 ADR 検索の結果

- `git grep -il -E "firebase|MFA|認証|password|auth" origin/main -- docs/adr` → 多数。本テーマに直接関係するのは次の5件
  - ADR-138: `docs/adr/ADR-138-remove-password-hash.md:12`「ログイン認証は Firebase Authentication が全担当」、:20 `public.users.password_hash` 列を物理削除
  - ADR-127: `docs/adr/ADR-127-auth-lockout-bystander-fix.md`（JWT キャッシュ確認を IP ロックより先に）
  - ADR-023: `docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md:5` ステータス「提案」。Firebase・users・staff の3層同期
  - ADR-032: Firebase 認証ドメインを auth.salesanchor.jp に（採用 2026-05-27）
  - ADR-1008: `docs/adr/ADR-1008-person-ssot-users-id.md` 人の正本は public.users.id
- `docs/adr/FEATURE-INDEX.md:28-29` に認証・password_hash の行あり（ADR-023/032/138）。パスキー・WebAuthn の行は無い
- `git grep -n -i -E "passkey|webauthn|biometric|FIDO|SimpleWebAuthn" origin/main` → 0 件
- 設計仕様書索引 `docs/specs/README.md` の「認証・権限・ロール」（`docs/specs/auth-roles/README.md`）は「対象外: ログイン方式」と明記 → 新規テーマ `docs/specs/auth-login/`（STANDARD-WORKFLOW の新規テーマ区分）

## file:line 引用表（リポジトリ内・origin/main）

### ログインとトークン検証

| 引用先 `path:line` | 確認内容 |
|---|---|
| `frontend/src/lib/firebase-auth.ts:129` | ログインは Firebase SDK の `signInWithEmailAndPassword`（自前のログイン API は無い） |
| `frontend/src/contexts/AuthContext.tsx:63` | `signIn` が上記を呼ぶ。:71-73 パスワード再設定は `sendPasswordResetEmail`（Firebase がメール送信） |
| `frontend/src/lib/api.ts:50` | API 呼び出しごとに `user.getIdToken()` を取り `Authorization: Bearer` で送る |
| `frontend/src/hooks/useSSE.ts:38` | SSE も同じ Bearer 方式 |
| `frontend/src/components/ShippingDetailPanel.tsx:315` | 添付取得も Firebase のトークンで Bearer |
| `backend/app/auth/dependencies.py:72` | `get_current_user` が全 API の認証の出口（1 本） |
| `backend/app/auth/dependencies.py:99` | SMOKE_SERVICE_TOKEN の照合が全検証より前（:99-113） |
| `backend/app/auth/dependencies.py:116` | ①ブラックリスト ②JWT キャッシュ（:125）③IP ロック（:136）④`verify_id_token`（:144） |
| `backend/app/auth/dependencies.py:32` | `MFA_REQUIRED` 既定 true。:153-160 で `sign_in_second_factor` が無いと 403 |
| `backend/app/auth/dependencies.py:169` | 紐付けは email（`User.email == email, User.is_active == True`）。uid は使わない |
| `backend/app/auth/dependencies.py:181` | トークンの tenant_id は「あれば整合確認」のみ。テナントの正は DB（:194） |
| `backend/app/auth/utils.py:15` | `set_custom_user_claims`（tenant_id）。アプリから Firebase を呼ぶのは `backend/app/routers/auth.py:123` の1か所だけ |
| `backend/app/cache.py:14` | JWT キャッシュ 300 秒。キーは `sha256(token)`（:50）。ブラックリストも同様（:155） |
| `backend/app/cache.py:288` | IP 単位で失敗 10 回／15 分ロック（:288-318）。Redis 不通時は通す（:295） |
| `backend/app/middleware/audit.py:50` | 署名検証なしで JWT の payload から email を読む（ログ用） |
| `backend/app/middleware/rate_limit.py:39` | 同上（email が取れないと IP 単位 60 回/分に落ちる。:95-107） |
| `backend/app/middleware/session_guard.py:45` | 同上（実際に使うのは token のハッシュのみ :159-160） |
| `backend/app/main.py:208` | CORS `allow_credentials=True`、`allow_headers=["Authorization","Content-Type"]`。Cookie 認証は無い |

### データと運用

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/models.py:22` | public.users の列（id, tenant_id, username, email, full_name, role, is_super_admin, is_active, last_login 等）。パスワード列・firebase_uid 列は無い |
| `migrations/019_create_staff_tables.sql:51` | テナントの staff に `firebase_uid`（ログインでは未使用。ADR-1008 で削除予定） |
| `backend/app/services/email_sender.py:40` | SMTP_HOST/USER/PASSWORD/MAIL_FROM が揃わないと送らずログだけ（:40-56） |
| `docker-compose.yml:69` | 環境変数 GOOGLE_APPLICATION_CREDENTIALS に Firebase の資格情報ファイル（コンテナ内 /app/firebase-credentials.json）を指定。:166 VITE_FIREBASE_API_KEY。:75 MFA_REQUIRED（既定 true）。SMTP_* を backend に渡す行は無い |
| `nginx/nginx.conf:82` | CSP に Firebase 用の許可（www.gstatic.com・*.googleapis.com・*.firebaseio.com） |
| `backend/requirements.txt:13` | `firebase-admin==6.6.0`。:14 `python-jose[cryptography]==3.5.0`（自社トークンの署名に使える）。:10 `bcrypt==4.2.1`（ADR-138 の整理残り） |
| `frontend/package.json:81` | `"firebase": "^11.0.0"`（lock は 11.10.0） |
| `backend/app/routers/line_import_devices.py:46` | LINE 取込端末の承認・一覧・失効は `require_super_admin`。端末の鍵は自前で Firebase 非依存 |
| `scripts/setup_review_tenant.py:87` | 審査用アカウントのパスワード再生成は `ALLOW_REVIEW_TENANT_PASSWORD_RESET=1` 時のみ（Firebase Admin） |
| `scripts/blue-green-cutover.sh:80` | 本番 backend は `docker run` で入れ替え（コンテナ名 `astro-webapp-backend-1`、:161） |
| `.github/workflows/qa-smoke.yml:18` | 本番 Firebase に実ログインする週次試験 |

### 画面（金型・i18n）

| 引用先 `path:line` | 確認内容 |
|---|---|
| `frontend/src/pages/login/LoginPage.tsx:6` | 金型 `Button`・`TextFieldControl`（:7）を使用。ただし「パスワードを忘れた」「ログインへ戻る」は生 `<button>`（:115, :154） |
| `frontend/src/pages/account-settings/SecuritySection.tsx` | パスワード変更（Firebase）。金型 `Button`/`TextFieldControl` |
| `frontend/src/lib/firebaseErrorMessage.ts:26` | Firebase の誤り（invalid-credential 等）を1つの文言に丸める |

## 本番の実物（読み取りのみ・2026-10-13・PO の端末で実行）

スクリプト: 設計者の作業用（リポジトリ外）。結果ファイルは PO の Mac の /tmp/CC報告ファイル/auth-po-check-20261013-120315.txt。秘密値・メールアドレスは表示していない。

| # | 何を | 結果 |
|---|---|---|
| P1 | 本番 backend（コンテナ astro-webapp-backend-1）の MFA_REQUIRED | `false`（二段階認証は本番で止まっている） |
| P2 | 同コンテナの SMTP_ / MAIL_FROM 環境変数 | 該当なし（自社からメールを送る設定は無い） |
| P3 | public.users の件数 | 総数 13・is_active=true 10・is_super_admin=true 2 |
| P4 | public.line_import_devices | 総数 1・承認済みで有効 1 |
| P5 | Firebase 登録ユーザー（firebase auth:export の集計） | 総数 12・passwordHash あり 12・mfaInfo あり 0・disabled 0・version 欄なし 12・providerUserInfo 欄なし |
| P6 | review@salesanchor.jp | Firebase に存在・disabled=false（ログインできない原因はパスワード不一致） |
| P7 | gh secret 名（値は見ない） | SMTP を含む名前 0 件。FEDEX_SMOKE_API_TOKEN/EMAIL あり。QA_* 15 件 |
| P8 | DNS | `salesanchor.jp` TXT に `v=spf1 a:salesanchor.sakura.ne.jp mx ~all`。`_dmarc.salesanchor.jp` TXT は空。DKIM はセレクタ不明で未確認 |
| P9 | jarvis-claude.uk | `301 → https://app.salesanchor.jp/`（別の Firebase は使っていない） |
| P10 | app.salesanchor.jp の JS | projectId `sales-ops-with-claude`・authDomain `auth.salesanchor.jp`・API は相対パス `/api/v1` |
| P11 | qa-smoke.yml・external-state-snapshot.yml | 直近 5 回・3 回すべて failure（原因は未調査） |
| P12 | public.users と Firebase のメール突き合わせ（小文字化。結果ファイル /tmp/CC報告ファイル/auth-user-diff-20261013-121557.txt） | 両方にある 9 人（全員 is_active=true）。DB にだけある 4 人: id=2（is_active=true・tenant 3・jarvis-test.local）、id=80〜82（is_active=false・tenant 6・salesanchor.demo）。Firebase にだけある 3 人（いずれも salesanchor.jp・DB に行が無いためアプリは使えない）。DB 側の大文字小文字重複 0 |
| P13 | review@salesanchor.jp の public.users（結果ファイル /tmp/CC報告ファイル/auth-review-in-db-20261013-122432.txt） | 1 件: id=10・tenant_id=6（tenant_code `tenant-review`）・is_active=true・role=admin。P6 と合わせ、ログインできない原因はパスワード不一致のみ |

→ 今ログインして使える人は 9 人（P12 の両方にある人）。

## 公式仕様（Context7 は月間上限で利用不可のため公式資料を直接確認・2026-10-13）

出典 URL と原文引用の全文は /tmp/CC報告ファイル/auth-external-research.md（リポジトリ外）。要点:

- Firebase のパスキー: 公式の本番ドキュメントに記載なし。firebase-tools PR #10636（2026-06-12）本文「Passkey support is currently in "private preview"」。Web SDK 13.0.0（2026-10-07）のリリースノートにも記載なし
- Firebase の TOTP MFA は Identity Platform へのアップグレードが前提（https://firebase.google.com/docs/auth/web/totp-mfa）
- py_webauthn 3.0.1（2026-09-25）・Python 3.10 以上・BSD-3。@simplewebauthn/browser 14.0.0（MIT）
- WebAuthn の RP ID は「登録可能ドメインの接尾辞」なら可（W3C WebAuthn L3 §5.1.3）。保存する値は credential ID（≤1023 バイト）・公開鍵・signCount・backup 状態・transports
- W3C §6.1.3「Relying Parties SHOULD ensure that each user account has additional authenticators registered」
- OWASP Password Storage: 第一選択 Argon2id（19 MiB・反復 2・並列 1 以上）
- OWASP Forgot Password: 有無で同じ応答・使い捨て・期限・再設定後に自動ログインしない
- NIST SP 800-63B-4（2025-07-31 Final）: 単独要素なら 15 文字以上・定期変更を強制しない・漏洩パスワード照合必須・失敗 100 回以下で止める・同期型パスキーは AAL2 まで可

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | public.users 13 人と Firebase 12 人の差は誰か | 突き合わせスクリプト（PO の端末）→ P12 | ✅ 解消（差は 1 人ではなく DB だけ 4 人・Firebase だけ 3 人） |
| 2 | 新パスワードを発行する範囲（今使える 9 人／id=2 を含む 10 人／停止中を含む 13 人）と、Firebase にだけある 3 人の扱い | PO 判断 | 未解消 |
| 3 | 認証アプリ（TOTP）を今回の範囲に入れるか（PO の当初の言葉「authenticationや生体認証」） | PO 判断 | 未解消 |
| 4 | 自社メールの送信元（さくらの SMTP アカウント・送信用アドレス）と DKIM/DMARC | さくらのコントロールパネル（PO の GUI） | 未解消 |
| 5 | qa-smoke の失敗原因 | 本テーマでは Firebase 実ログイン試験を置き換えるため、置き換え便で扱う | 設計で扱う |
