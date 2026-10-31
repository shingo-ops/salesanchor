# 実装カード 便5 — 顔・指紋（パスキー）でログインできるようにする

> この文書は何か：ADR-1013 便5 の作業指示書です。パスキーの登録・ログイン・一覧・削除を、backend と画面に足します。DB の表は便1 で作り済み（migration なし）。compose・deploy・nginx・secrets は触りません。パスワードのログインは今のまま残ります。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md §3（:79-81・:85-86・:103）・§5 画面（:126-128）・§6 便5（:159）・受け入れ基準（:202）・維持の仕組み（:242）
- 前提を決めている別の設計: docs/handoff/admin-2fa/design.md（ADR-1048。:57・:66-70・:77・:109・:142）
- 現在地: docs/handoff/auth-self-hosted-passkey/recon-b5.md（origin/main 5c13bfbef 基準。以下「recon Qn」）
- 対象ADR: ADR-1013（本テーマ）、ADR-1048（発行の共通関数・amr）、ADR-027（文言は t()）、ADR-144（UI は金型）、ADR-025（手動 INSERT 禁止。このカードは手動 INSERT をしない）
- 状態: 第1版（2026-10-31 Opus 作成）。審査前。PO の実装承認は 2026-10-31（「1」＝審査に通れば便5 と ADR-1048 便7a〜7d を止めずに本番まで進める）。**実装未着手**
- 担当: 実装 クラウドの Sonnet／コード審査 Opus（reviewer）／マージ・反映確認 Opus（PO の委任）／K2 の実演 PO

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・1 手順 1 コマンド・出力に上限・sleep しない・プレースホルダを残さない | ○（§0-2・§5） |
| guards/03-file.md | 編集は Write/Edit で行う | ○（§0-2） |
| guards/04-worktree.md | `bash scripts/new-worktree.sh release/passkey-b5` で作り、実在は `git worktree list` で確かめる。push は `git push -u origin HEAD` | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触るファイル・削除するファイルを `### 標準ワークフロー確認` に同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 実装役は本番の機体に入らない | ○（本カードに本番操作なし） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1013 便5 の実行結果である」と書くこと。

## 0-2. 作業の決まり

- 作業場所は §10 ①で作った worktree。以下 `WT` と書く（`git worktree list` に出たフルパスを `export WT=...` で入れる）。全コマンドを `cd "${WT}" &&` で始める。1 手順 1 コマンド。出力が長い命令は `| tail -60` を付ける
- ファイルの作成と編集は Write/Edit で行う。sleep しない
- §3 の触るファイル以外を変えない。必要が出たら §6 の分岐に従い、無ければ停止する
- 停止するときは報告に 3 点を書く: ①止まった手順（§ の番号）②最後のコマンド ③理由（エラーやフックの文の原文）。フックに止められたら言い換えて再試行しない。報告先は Opus
- 秘密の値・メール・IP を、コード・テスト・報告に書かない（テストの email は既存の `test_self_auth.py` と同じ example ドメインの形）

## 1. 範囲

入れる:
1. backend の口 6 本（design.md:79-81）: `POST /passkey/register/options`・`POST /passkey/register/verify`・`POST /passkey/login/options`・`POST /passkey/login/verify`・`GET /passkeys`・`DELETE /passkeys/{passkey_id}`（すべて `/api/v1/auth` 配下）
2. 発行の共通関数 `_issue_session_tokens` を auth.py に作り、login・refresh・password/change・passkey/login/verify の 4 か所がこれを通る（ADR-1048 admin-2fa/design.md:66「必ず全部が同じ関数を通る」の土台。ログ行 `admin_token_issued` は便7b で足す。今回は足さない）
3. 設定 `AUTH_RP_ID`（design.md:86。既定 `app.salesanchor.jp`）を self_tokens.py に足す
4. 画面: ログイン画面に「顔・指紋でログイン」ボタン（自社ログインかつ端末が対応しているときだけ）。アカウント設定のセキュリティにパスキーの一覧・追加・削除
5. 依存: backend `webauthn==2.8.0`・`pyOpenSSL==26.2.0`、frontend `@simplewebauthn/browser` `14.0.0`（版は固定）
6. design.md の維持の仕組み（:242）にテストのパスを書き足す

入れない（理由）:
- 管理者の 2 段階の確認・`admin_token_issued` のログ・`auth_refresh_tokens.amr` → ADR-1048 便7a〜7d
- refresh 後の amr の引き継ぎ（今の refresh は amr を付けない＝`auth.py:351`）→ 便7a で表に amr 列を足してから
- nginx・CSP・Permissions-Policy の変更 → 要らない（§2 F9）
- 自動入力の候補にパスキーを出す（conditional UI）・パスワードからの自動登録 → 今回はボタンだけ
- Firebase の削除 → 便6

## 2. 前提の事実（origin/main 5c13bfbef・2026-10-31）

公式資料の生の写し: /tmp/CC報告ファイル/passkey-2fa/official/（Context7 は月の上限で使えなかったため、PyPI・npm・GitHub のタグ・W3C を直接取得した）

- F1 表 `public.webauthn_credentials` は `migrations/20261013_160000_add_self_hosted_auth_tables.sql:16-33` に有る。12 列・`credential_id` UNIQUE・長さ 1〜1023・`sign_count >= 0`・`user_id` に索引・RLS なし（:3）。使うコードは 0 件（recon Q1）。生 SQL で読み書きする方針（`backend/app/auth/self_tokens.py:4-5`）
- F2 login は `backend/app/routers/auth.py:265-323`。発行は `issue_refresh_token`（:314-316）→ `db.commit()`（:317）→ `_set_refresh_cookie`（:318）→ `create_access_token(..., "pwd")`（:319-323）。refresh は :345-356（amr は None）、password/change は :587-597。共通関数は無い（recon Q2）
- F3 設定: `rp_origin()` は `self_tokens.py:49-50`（既定 `https://app.salesanchor.jp`）。`AUTH_RP_ID` は無い（recon Q3）。本番は deploy.yml:370-372 で `AUTH_PROVIDER=self`（自社ログインに切替済み）
- F4 Redis: `backend/app/cache.py:62` `get_redis()`（`decode_responses=True`＝:46。未接続なら None）。本番の Redis は `redis:7-alpine`（docker-compose.yml:459）、redis-py は `redis[hiredis]>=5.0.0`（requirements.txt:16）。`GETDEL` は Redis 6.2 以降・redis-py の `getdel()` で使える
- F5 IP 単位の失敗回数: `check_auth_rate_limit`（cache.py:311）・`record_auth_failure`（:328）。login は :275 で確かめる
- F6 監査記録: `record_audit_log(db, tenant_id, user_id, action, table_name, record_id, old_data, new_data)`（`backend/app/services/audit.py:277`）。password/change は tenant の文脈を外した後に呼んでいる（auth.py:575 付近）
- F7 py_webauthn 2.8.0（PyPI 2026-06-13 公開）の依存は `cryptography>=46.0.0`・`pyOpenSSL>=26.0.0`・`cbor2<6,>=5.6.5`・`pyasn1>=0.6.2`・`pyasn1-modules>=0.4.2`。今の `cryptography==48.0.1`（requirements.txt:24）と両立する pyOpenSSL は **26.2.0（`cryptography<49,>=46.0.0`）だけ**。26.3.0 以降は `cryptography>=49` を求める（official/pyopenssl-26-crypto.txt）。だから pyOpenSSL を 26.2.0 に固定する
- F8 py_webauthn 2.8.0 の公開関数（official/pywebauthn-init.py）: `generate_registration_options`・`verify_registration_response`・`generate_authentication_options`・`verify_authentication_response`・`options_to_json`・`base64url_to_bytes`。補助に `parse_authentication_credential_json`・`parse_registration_credential_json`・`parse_authenticator_data`・`bytes_to_base64url`（webauthn.helpers）。例外の親は `WebAuthnException`（webauthn.helpers.exceptions）。`verify_authentication_response` は「新値か保存値が 0 より大きく、新値 ≦ 保存値」で `InvalidAuthenticationResponse` を出す（verify_authentication_response.py:158-166）＝design.md:80 の決まりと同じ
- F9 nginx: Permissions-Policy は `camera=(), microphone=(), geolocation=()` だけ（nginx.conf:88）。W3C WebAuthn L3 §5.9「publickey-credentials-create と publickey-credentials-get の既定の許可は 'self'」。書かれていない機能は既定のままなので、同じ場所の画面からは使える。CSP（:84）の `connect-src 'self'` は同じ場所の `/api/v1/auth/` を許す。パスキーの口は `location /api/v1/auth/`（:144-146・10 回/分・burst 5）に入る（recon Q9）
- F10 @simplewebauthn/browser 14.0.0（npm 2026-09-02 公開・MIT・依存なし）: `startRegistration({ optionsJSON })`・`startAuthentication({ optionsJSON })`・`browserSupportsWebAuthn()`（official/sw-index.ts・startRegistration.ts・startAuthentication.ts）
- F11 画面: ログインは `frontend/src/pages/login/LoginPage.tsx`（ボタンは :130-132 の `Button variant="primary" size="auth" shape="pill" fullWidth`）。自社ログインの判定は `isSelfAuth()`（`frontend/src/lib/auth/provider.ts:19-21`）。ログインの呼び出しは `selfAuth.ts:88-106`（`postAuth`・`selfLogin`）→ `AuthContext.tsx:124-130`。アカウント設定は `frontend/src/pages/account-settings/SecuritySection.tsx`（138 行）。金型 `DataTable`（components/DataTable.tsx:147）・`ConfirmModal`（components/ConfirmModal.tsx:21）・`Button`・`TextFieldControl`。Button の種類は `primary | secondary | ghost | danger | outline | tab`（components/buttonAppearance.ts:1）。API は `api.get`・`api.post`・`api.delete`（lib/api.ts:237-246）
- F12 文言: `login.*`（ja.json/en.json :674-683）・`authError.*`（:684-696）・`accountSettings.*`（:3182-）。パスキーのキーは無い（recon Q7）。誤り文言は `frontend/src/lib/auth/authErrorMessage.ts`（文脈 `AuthErrorContext` は `login | resetRequest | resetConfirm | passwordChange`）
- F13 試験: `backend/tests/test_self_auth.py`（`self_auth_env`:36-43・`no_redis`:45-50・`http`:80-92・`_login`:95・Cookie の確かめ :136-141）（recon Q8）

## 3. 触るファイル（これ以外は触らない）

新設:
- backend/app/auth/passkeys.py
- backend/tests/test_passkeys.py
- frontend/src/lib/auth/passkey.ts
- frontend/src/lib/auth/passkey.test.ts
- frontend/src/pages/account-settings/PasskeySection.tsx
- frontend/src/pages/account-settings/PasskeySection.test.tsx

変更:
- backend/app/routers/auth.py
- backend/app/auth/self_tokens.py
- backend/requirements.txt
- frontend/package.json
- frontend/package-lock.json
- frontend/src/contexts/AuthContext.tsx
- frontend/src/pages/login/LoginPage.tsx
- frontend/src/pages/login/LoginPage.test.tsx
- frontend/src/pages/account-settings/AccountSettingsPage.tsx
- frontend/src/lib/auth/authErrorMessage.ts
- frontend/src/lib/auth/authErrorMessage.test.ts
- frontend/src/locales/ja.json
- frontend/src/locales/en.json
- docs/handoff/auth-self-hosted-passkey/design.md（:242 の維持の仕組みにテストのパスを足す・:159 の便5 の行に「pyOpenSSL 26.2.0 固定（F7）」を足す）
- docs/handoff/auth-self-hosted-passkey/handoff.md（状態の表に便5 の行を足す）

削除: なし

## 4. 作り方

### 4.1 設定（self_tokens.py）

`rp_origin()`（:49-50）のすぐ下に足す。

```python
DEFAULT_RP_ID = "app.salesanchor.jp"  # :21 の DEFAULT_RP_ORIGIN の隣に置く


def rp_id() -> str:
    """パスキーが結びつくドメイン（design.md:85。後から変えると登録済みのパスキーが全部使えなくなる）。"""
    return os.getenv("AUTH_RP_ID", DEFAULT_RP_ID)
```

### 4.2 発行の共通関数（auth.py）

`_clear_refresh_cookie`（:226）の上に足す。commit は呼び出し側に残す（今の順序 `issue/rotate → commit → cookie → access` を変えない）。

```python
def _issue_session_tokens(
    response: Response, raw: str, expires_at: datetime, user_id: int, email: str, amr: str | None
) -> str:
    """更新用 Cookie を付け、アクセストークンを返す。トークンを出す口は全部ここを通る（ADR-1048 admin-2fa/design.md:66）。"""
    _set_refresh_cookie(response, raw, expires_at)
    return self_tokens.create_access_token(user_id, email, amr)
```

置き換え（中身は同じ。値の出どころを変えない）:
- login :318-323 → `access = _issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd")` を作り、`SelfTokenResponse(access_token=access, token_type="bearer", expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS)` を返す
- refresh :352-356 → `_issue_session_tokens(response, new_raw, expires_at, user_id, email, None)`
- password/change :591-594 → `_issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd")`

### 4.3 パスキーの部品（backend/app/auth/passkeys.py・新設）

置くもの（関数は全部この中。auth.py からは呼ぶだけ）:

- 定数: `CHALLENGE_TTL_SECONDS = 300`・`MAX_PASSKEYS_PER_USER = 10`・`RP_NAME = "Sales Anchor"`・`LABEL_MAX = 64`
- `user_handle(user_id: int) -> bytes`: `user_id.to_bytes(8, "big")`（design.md:79。メールは入れない）
- `async def store_challenge(kind: str, owner: str, challenge: bytes) -> str`: `get_redis()` が None なら `HTTPException(503, "unavailable")`。`challenge_id = secrets.token_urlsafe(24)`、キー `passkey_chal:{kind}:{owner}:{challenge_id}`、値 `bytes_to_base64url(challenge)`、`ex=CHALLENGE_TTL_SECONDS`。`challenge_id` を返す。kind は `reg` か `login`、owner は reg なら `str(user_id)`、login なら `-`
- `async def take_challenge(kind: str, owner: str, challenge_id: str) -> bytes | None`: 同じキーを `getdel` で取り出す（1 回で消える＝design.md:80）。無ければ None。値は `base64url_to_bytes` で戻す。Redis が None なら 503
- 登録の options: `generate_registration_options(rp_id=self_tokens.rp_id(), rp_name=RP_NAME, user_name=email, user_id=user_handle(user_id), user_display_name=email, authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED, user_verification=UserVerificationRequirement.REQUIRED), exclude_credentials=[PublicKeyCredentialDescriptor(id=c) for c in 既存の credential_id])`。返すときは `json.loads(options_to_json(options))`。user_name に email を使うのは、端末の候補一覧で本人がどのアカウントか分かるようにするため（端末の中だけに置かれ、user handle には入れない）
- ログインの options: `generate_authentication_options(rp_id=self_tokens.rp_id(), user_verification=UserVerificationRequirement.REQUIRED)`（allow_credentials は空＝端末が候補を出す。design.md:80）

### 4.4 口（auth.py。`password/change` の後ろに足す）

共通の決まり: POST と DELETE は全部 `_require_app_origin(request)` を最初に通す（design.md:75）。py_webauthn の例外は `WebAuthnException` でまとめて受ける。返す detail は識別子だけ。

| 口 | 認証 | 入力 | 動き | 返り |
|---|---|---|---|---|
| POST `/passkey/register/options` | `get_current_user` | なし | 本人の credential_id を `SELECT credential_id FROM public.webauthn_credentials WHERE user_id = :uid` で引く。10 件以上なら 409 `passkey_limit`。options を作り、challenge を `store_challenge("reg", str(uid), ...)` | `{"challenge_id": str, "options": dict}` |
| POST `/passkey/register/verify` | `get_current_user` | `challenge_id: str`（1〜64 字）・`credential: dict`・`label: str | None`（`LABEL_MAX` 字まで。前後の空白を除き、空なら NULL） | `take_challenge("reg", str(uid), id)` が None なら 400 `challenge_expired`。`verify_registration_response(credential=..., expected_challenge=..., expected_rp_id=rp_id(), expected_origin=rp_origin(), require_user_verification=True)`。失敗は 400 `passkey_invalid`。`parse_registration_credential_json(credential).response.transports` を `[t.value for t in (... or [])]` にする。INSERT（列: user_id・credential_id・public_key・sign_count・transports・backup_eligible＝`credential_device_type == CredentialDeviceType.MULTI_DEVICE`・backup_state＝`credential_backed_up`・aaguid＝`uuid.UUID(verified.aaguid)`・label）。一意制約に当たったら 409 `passkey_exists`。`record_audit_log(action="create", table_name="webauthn_credentials", record_id=新しい id, new_data={"event": "passkey_registered"})`。commit | `{"id": int, "label": str | None, "created_at": str}`（201） |
| POST `/passkey/login/options` | なし | なし | `_require_issuance_enabled()`（design.md:103）→ origin → `check_auth_rate_limit(ip)` が真なら 429 `too_many_attempts`。options を作り `store_challenge("login", "-", ...)` | `{"challenge_id": str, "options": dict}` |
| POST `/passkey/login/verify` | なし | `challenge_id`・`credential: dict` | `_require_issuance_enabled()` → origin → 回数制限（429）。`take_challenge` が None なら 401 `invalid_credentials`＋`record_auth_failure(ip)`。`parse_authentication_credential_json(credential).raw_id` で `SELECT c.id, c.user_id, c.public_key, c.sign_count, u.email, u.tenant_id, u.is_active FROM public.webauthn_credentials c JOIN public.users u ON u.id = c.user_id WHERE c.credential_id = :cid`。無い・`is_active` 偽なら 401＋`record_auth_failure`。**複製の疑いの先回り**: `parse_authenticator_data(...response.authenticator_data).sign_count` を新値とし、「新値か保存値が 0 より大きく、新値 ≦ 保存値」なら `record_audit_log(tenant_id, user_id, action="update", table_name="webauthn_credentials", record_id=c.id, new_data={"event": "passkey_sign_count_rejected", "stored": 保存値, "received": 新値})` を書いて commit し、401＋`record_auth_failure`（design.md:80「拒否し、監査記録に残す」）。次に `verify_authentication_response(credential=..., expected_challenge=..., expected_rp_id=rp_id(), expected_origin=rp_origin(), credential_public_key=c.public_key, credential_current_sign_count=c.sign_count, require_user_verification=True)`。失敗は 401＋`record_auth_failure`。成功で `UPDATE public.webauthn_credentials SET sign_count = :n, backup_state = :b, last_used_at = :now WHERE id = :id`、`set_tenant_context(db, tenant_id)` → `UPDATE public.users SET last_login = :now WHERE id = :uid` → `clear_tenant_context(db)`（login :303-310 と同じ順）。`issue_refresh_token` → commit → `_issue_session_tokens(..., "webauthn")` | `SelfTokenResponse`（login と同じ形） |
| GET `/passkeys` | `get_current_user` | なし | `SELECT id, label, created_at, last_used_at FROM public.webauthn_credentials WHERE user_id = :uid ORDER BY created_at` | `{"items": [...]}`（日時は ISO 8601） |
| DELETE `/passkeys/{passkey_id}` | `get_current_user` | パスの int | origin。`DELETE FROM public.webauthn_credentials WHERE id = :id AND user_id = :uid RETURNING id`。0 行なら 404 `passkey_not_found`（他人のものも同じ 404）。`record_audit_log(action="delete", ..., new_data={"event": "passkey_deleted"})`。commit | 204 |

- 口座の停止（`locked_until`）はパスキーのログインでは見ない。理由: 停止はパスワードの総当たり対策（design.md:52「口座単位の失敗回数」）。パスキーは端末と顔・指紋の両方が要り、総当たりできない。停止中に本人がパスキーで入れることは、他人のパスワード試行で本人が締め出されるのを防ぐ。`is_active=false` は必ず拒否する
- 失敗の応答は、表に無い・停止された人・照合失敗・使用回数の拒否で同じ 401 `invalid_credentials`（どれかを外から区別させない）

### 4.5 画面

文言は全部 `t("key")`。ja.json と en.json に同じキーを同じ位置に足す（ADR-027）。生の `<button>`・`<input>`・`<table>`・色の直書きは使わない（ADR-144）。新しい CSS は足さない（足す必要が出たら §6 の分岐）。

足すキー（ja / en）:
- `login.signInWithPasskey`: 「顔・指紋でログイン」/ "Sign in with face or fingerprint"
- `login.orDivider`: 「または」/ "or"
- `authError.passkeyCancelled`: 「顔・指紋の確認が取り消されました。もう一度お試しください。」/ "Face or fingerprint check was cancelled. Please try again."
- `authError.passkeyExists`: 「この端末のパスキーはすでに登録されています。」/ "A passkey for this device is already registered."
- `authError.passkeyLimit`: 「パスキーは10個まで登録できます。」/ "You can register up to 10 passkeys."
- `accountSettings.passkeyTitle`: 「顔・指紋でのログイン（パスキー）」/ "Sign in with face or fingerprint (passkeys)"
- `accountSettings.passkeyDescription`: 「この端末の顔認証・指紋認証でログインできるようにします。顔や指紋のデータは端末から出ません。」/ "Lets you sign in with this device's face or fingerprint check. Your face or fingerprint data never leaves the device."
- `accountSettings.passkeyLabel`: 「名前（例: 仕事用iPhone）」/ "Name (e.g. work iPhone)"
- `accountSettings.passkeyAdd`: 「この端末を登録」/ "Register this device"
- `accountSettings.passkeyAdded`: 「登録しました。」/ "Registered."
- `accountSettings.passkeyColName`・`passkeyColCreated`・`passkeyColLastUsed`: 「名前」「登録日」「最後に使った日」/ "Name" "Registered" "Last used"
- `accountSettings.passkeyUnnamed`: 「名前なし」/ "Unnamed"
- `accountSettings.passkeyNeverUsed`: 「まだ使っていません」/ "Not used yet"
- `accountSettings.passkeyEmpty`: 「登録されたパスキーはありません。」/ "No passkeys registered."
- `accountSettings.passkeyDelete`: 「削除」/ "Delete"
- `accountSettings.passkeyDeleteTitle`: 「パスキーを削除しますか」/ "Delete this passkey?"
- `accountSettings.passkeyDeleteMessage`: 「削除すると、この端末の顔・指紋ではログインできなくなります。パスワードでのログインはそのまま使えます。」/ "You will no longer be able to sign in with this device's face or fingerprint. Password sign-in still works."
- `accountSettings.passkeyUnsupported`: 「この端末・ブラウザはパスキーに対応していません。」/ "This device or browser does not support passkeys."

(1) `frontend/src/lib/auth/passkey.ts`（新設）
- `export function passkeySupported(): boolean { return isSelfAuth() && browserSupportsWebAuthn(); }`
- `export async function selfPasskeyLogin(): Promise<void>`: `postAuth<{challenge_id: string; options: PublicKeyCredentialRequestOptionsJSON}>("/passkey/login/options")` → `startAuthentication({ optionsJSON: res.options })` → `postAuth<TokenResponse>("/passkey/login/verify", { challenge_id, credential })` → `adoptAccessToken(...)`。`postAuth`・`adoptAccessToken`・`TokenResponse` は selfAuth.ts から import する（selfAuth.ts で export されていなければ export を足す。selfAuth.ts は §3 に無いので、export を足す必要があれば §6 B5 に従う）
- `export async function registerPasskey(label: string): Promise<void>`: `api.post("/auth/passkey/register/options", {})` → `startRegistration({ optionsJSON })` → `api.post("/auth/passkey/register/verify", { challenge_id, credential, label })`
- `export function isPasskeyCancel(err: unknown): boolean`: `err instanceof Error && err.name === "NotAllowedError"`（利用者が取り消したとき、ブラウザは NotAllowedError を出す。@simplewebauthn は名前を引き継ぐ WebAuthnError を投げる）

(2) `AuthContext.tsx`: 型（:38 の隣）に `signInWithPasskey: () => Promise<void>` を足し、:124-130 の `signIn` の隣で `selfPasskeyLogin` を呼ぶ（自社ログインでないときは呼ばない）

(3) `LoginPage.tsx`: :130-132 の送信ボタンと `</form>` の後に、`passkeySupported()` が真のときだけ、`login.orDivider` の文字（既存の `login-subtitle` クラスの `<p>`）と `Button variant="outline" size="auth" shape="pill" fullWidth type="button"` で `t("login.signInWithPasskey")` を出す。押すと `signInWithPasskey()` → 成功で :49-50 と同じ `navigate(from, { replace: true })`。取り消しは `authError.passkeyCancelled`、ほかは `loginErrorMessage(err)`（:17-19）

(4) `PasskeySection.tsx`（新設）と `AccountSettingsPage.tsx`: `<SecuritySection />` の下に `{isSelfAuth() && <PasskeySection />}`。中身は SecuritySection の見出しの形（:85-89 の `account-settings-section` と `account-settings-section-title`・`ACCOUNT_ICONS.security`）をそのまま使う
- 一覧: `DataTable`。列 `label`（空なら `passkeyUnnamed`）・`created_at`・`last_used_at`（空なら `passkeyNeverUsed`）・削除の列（`Button variant="danger" size="sm"`）。日時は `new Date(v).toLocaleDateString(i18n.language)`。0 件は DataTable の空の表示に `passkeyEmpty`
- 追加: `TextFieldControl`（名前・任意・`maxLength=64`）＋ `Button variant="secondary"`（`passkeyAdd`）。`browserSupportsWebAuthn()` が偽ならボタンの代わりに `passkeyUnsupported` の文
- 削除: `ConfirmModal`（`danger`・`passkeyDeleteTitle`・`passkeyDeleteMessage`）→ `api.delete("/auth/passkeys/" + id)` → 一覧を読み直す
- 誤り: 409 `passkey_exists`・`passkey_limit` は対応の文言、取り消しは `passkeyCancelled`、ほかは `authErrorMessage(err, t, "passwordChange")`

(5) `authErrorMessage.ts`: 409 の detail `passkey_exists`・`passkey_limit` を対応のキーへ。既存の分岐は変えない

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る）

1. `cd "${WT}" && cd backend && pip install -r requirements.txt 2>&1 | tail -5`
2. `cd "${WT}" && cd backend && pip check 2>&1 | tail -5`（「No broken requirements found.」が出ること）
3. `cd "${WT}" && cd backend && python -c "import webauthn, OpenSSL, cryptography; print(webauthn.__version__, OpenSSL.__version__, cryptography.__version__)"`（`2.8.0 26.2.0 48.0.1`）
4. `cd "${WT}" && cd backend && python -m pytest tests/test_passkeys.py tests/test_self_auth.py -q 2>&1 | tail -15`
5. `cd "${WT}" && cd frontend && npm ci 2>&1 | tail -5`
6. `cd "${WT}" && cd frontend && npx vitest run src/lib/auth src/pages/login src/pages/account-settings 2>&1 | tail -20`
7. `cd "${WT}" && cd frontend && npx tsc --noEmit -p . 2>&1 | tail -10`
8. `cd "${WT}" && cd frontend && npm run lint 2>&1 | tail -15`
9. `cd "${WT}" && node -e "const a=require('./frontend/src/locales/ja.json'),b=require('./frontend/src/locales/en.json');const k=o=>Object.entries(o).flatMap(([x,v])=>typeof v==='object'?k(v).map(y=>x+'.'+y):[x]);const A=k(a),B=new Set(k(b));console.log(A.filter(x=>!B.has(x)).length, k(b).filter(x=>!new Set(A).has(x)).length)"`（`0 0`）
10. `cd "${WT}" && git diff --name-only origin/main...HEAD | tail -40`（§3 の一覧と一致すること）

backend/tests/test_passkeys.py に入れる試験（py_webauthn の照合関数は `monkeypatch` で差し替え、実物の暗号は使わない。差し替えるのは `app.auth.passkeys` から import した名前）:
- T1 login/options: 200・`challenge_id` が返り、Redis（試験用の偽物）に 300 秒で入る
- T2 login/verify: 正しい challenge で 200、`amr == ["webauthn"]`、Cookie の 4 属性（test_self_auth.py:136-141 と同じ確かめ）、`sign_count`・`last_used_at`・users.last_login が更新
- T3 同じ challenge_id を 2 回使うと 2 回目は 401（challenge は 1 回で消える＝design.md:202）
- T4 保存値 5・新値 5 → 401、audit_logs に `passkey_sign_count_rejected` が 1 行。保存値 5・新値 3 → 401。保存値 0・新値 0 → 200（design.md:80・:202）
- T5 表に無い credential → 401。`is_active=false` の人 → 401。応答の本文は T5 の 2 つと T4 で同じ
- T6 `AUTH_PROVIDER=firebase` で login/options と login/verify が 404（design.md:103）
- T7 Origin が違う・無いと 6 本の口が全部 403
- T8 register/verify: 成功で 1 行・transports・backup_eligible・aaguid・label が入る。同じ credential_id で 409 `passkey_exists`。10 件ある人の register/options が 409 `passkey_limit`。他人の reg challenge（owner が違う）は 400 `challenge_expired`
- T9 GET /passkeys は本人の分だけ。DELETE で他人の id は 404 で行は残る。本人の id は 204 で消え、audit_logs に `passkey_deleted`
- T10 Redis が None のとき options が 503 `unavailable`
- T11 login・refresh・password/change の既存試験（test_self_auth.py）が全部そのまま通る（共通関数への置き換えで振る舞いが変わらない）

画面の試験:
- passkey.test.ts: `passkeySupported` が自社ログインかつ対応端末のときだけ真。`selfPasskeyLogin` が options → startAuthentication → verify の順に呼び、トークンを受け取る（@simplewebauthn/browser は vi.mock）。`isPasskeyCancel` が NotAllowedError で真
- LoginPage.test.tsx: 対応端末でボタンが出る・非対応で出ない・押すと signInWithPasskey が呼ばれる・取り消しで `authError.passkeyCancelled`
- PasskeySection.test.tsx: 一覧・0 件の表示・追加・削除の確認窓から api.delete・409 の文言
- authErrorMessage.test.ts: 409 の 2 つの detail

## 6. 分岐ごとの対処

- B1 `pip install` で pyOpenSSL 26.2.0 と他の依存がぶつかる → 停止（版の引き上げは別件＝admin-2fa/design.md:142）
- B2 `npm ci` で @simplewebauthn/browser 14.0.0 の peer の警告以外の誤り → 停止
- B3 DataTable の空の表示の渡し方が分からない（props 名が見つからない）→ DataTable.tsx の Props（:74- ）と DataTable.stories.tsx の例に従う。例が無ければ停止
- B4 新しい CSS が要る（並びが崩れる等）→ 足さずに停止し、画面の写しを報告に付ける
- B5 selfAuth.ts の `postAuth`・`adoptAccessToken`・`TokenResponse` が export されていない → selfAuth.ts に `export` の語を足すだけは許す（§3 に selfAuth.ts を足し、報告に書く）。中身は変えない
- B6 `get_current_user` が `/api/v1/auth` 配下で別の振る舞いをする（試験で 401 になる等）→ 停止
- B7 フック・CI に止められた → 言い換えずに停止し、原文を報告

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K2: PO の端末で、顔か指紋だけでログインできる（パスワードを打たない） | PO が本番で実演（§8）。画面の写しか録画 |
| K2-DB: PO の登録後、`webauthn_credentials` に PO の行が 1 行 | 本番 DB の読み取りの道で件数だけ見る（Opus） |
| 使用回数の拒否と監査記録・challenge 1 回限り | T3・T4（design.md:202） |
| 発行の 4 経路が `_issue_session_tokens` を通る | `grep -n "_issue_session_tokens" backend/app/routers/auth.py` が定義 1＋呼び出し 4 |
| 他人のパスキーを見られない・消せない | T9 |
| 既存のログインが変わらない | T11・本番の画面点検（毎朝）が合格のまま |
| 文言は ja/en 同じキー・金型だけ | §5-9 が `0 0`・lint 緑・差分に生の button/input/table が 0 |
| compose・deploy・nginx・migrations を触らない | §5-10 |

## 8. 反映の順番と PO の作業

1. PR → 審査（reviewer opus）APPROVE → CI 緑 → Opus がマージ（危ないパスを含まないため、ADR-136 の GO 対象外。区分はコードのみ）→ deploy の成功と /health 200 を確かめる
2. Opus が本番で `POST /api/v1/auth/passkey/login/options`（Origin 付き）が 200 になることを確かめる（DB には書かない）
3. PO の作業（K2）: スマホかパソコンで app.salesanchor.jp にパスワードでログイン → アカウント設定 →「この端末を登録」→ 顔か指紋 → いったんログアウト →「顔・指紋でログイン」→ 顔か指紋だけで入れる
4. Opus が読み取りの道で `webauthn_credentials` の件数を見る

## 9. 戻し方

PR を revert して deploy する。登録済みのパスキーの行は残るが、口が無くなるので使われない（design.md:159）。パスワードのログインは便5 の前後で変わらない。

## 10. PR

1. `bash scripts/new-worktree.sh release/passkey-b5` → `git worktree list | tail -20` で実在を確かめ、`export WT=...` に入れる
2. 実装 → §5 の 1〜10
3. `cd "${WT}" && git add -A && git commit -m "feat: passkey sign-in, register, list and delete (ADR-1013 b5)"`（.claude-pipeline/active-work.d は入れない）
4. `cd "${WT}" && git push -u origin HEAD`
5. `cd "${WT}" && bash scripts/gh-pr-create-safe.sh` で PR（ベースは main・下書きにしない）。本文に `### 標準ワークフロー確認`（recon: docs/handoff/auth-self-hosted-passkey/recon-b5.md・設計: docs/handoff/auth-self-hosted-passkey/design.md・カード: docs/handoff/auth-self-hosted-passkey/card-b5.md・対象ADR: ADR-1013, ADR-1048・触るファイル: §3 の全部をカンマ区切り 1 行・削除するファイル: なし）
6. マージはしない（Opus が行う）

## 11. 未解決（審査で確かめる）

- U1 口座の停止をパスキーのログインで見ない判断（§4.4）は、design.md に書かれていない。審査で妥当かを見る。妥当なら design.md の便5 の行に書き戻す（§3 の design.md の変更に含める）
- U2 `user_name`・`user_display_name` に email を使う（§4.3）。design.md:79 は user handle にメールを入れないことだけを決めている
- U3 本番の画面点検の利用者（点検専用の人）がパスキーを持たないため、毎朝の点検はパスキーの口を通らない。パスキーの口の守りは T1〜T10 だけになる

## 12. 報告欄（担当が追記）

END OF CARD
