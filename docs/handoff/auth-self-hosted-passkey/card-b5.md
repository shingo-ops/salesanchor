# 実装カード 便5 — 顔・指紋（パスキー）でログインできるようにする

> この文書は何か：ADR-1013 便5 の作業指示書です。パスキーの登録・ログイン・一覧・削除を、backend と画面に足します。DB の表は便1 で作り済みです（migration なし）。compose・deploy・nginx・secrets は触りません。パスワードのログインは今のまま残ります。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md §3（:79-81・:85-86・:103）・§5 画面（:126-128）・§6 便5（:159）・受け入れ基準（:202）・維持の仕組み（:242）
- 前提を決めている別の設計: docs/handoff/admin-2fa/design.md（ADR-1048。:57・:66-70・:77・:109・:142）
- 現在地: docs/handoff/auth-self-hosted-passkey/recon-b5.md（origin/main 5c13bfbef 基準。以下「recon Qn」）
- 対象ADR: ADR-1013（本テーマ）、ADR-1048（発行の共通関数・amr）、ADR-027（文言は t()）、ADR-144（UI は金型）、ADR-025（手動 INSERT 禁止。このカードは手動 INSERT をしない）
- 状態: 第4版（2026-10-31 Opus）。第1版（5157d338c）の審査は REVISE（MAJOR 4・MINOR 14）。第2版（f6b3e3b09）の審査は REVISE（MAJOR 1・MINOR 7）。第3版（21cbffa6b）の審査は REVISE（MAJOR 2・MINOR 3）。第4版で全件を反映した（末尾「改訂の記録」）。PO の実装承認は 2026-10-31（「1」＝審査に通れば便5 と ADR-1048 便7a〜7d を止めずに本番まで進める）。**実装未着手**
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
2. 発行の共通関数 `_issue_session_tokens` を auth.py に作る。login・refresh・password/change・passkey/login/verify の 4 か所がこれを通る（ADR-1048 admin-2fa/design.md:66「必ず全部が同じ関数を通る」の土台）。ログ行 `admin_token_issued` は便7b で足す。今回は足さない
3. 設定 `AUTH_RP_ID`（design.md:86。既定 `app.salesanchor.jp`）を self_tokens.py に足す
4. 画面: ログイン画面に「顔・指紋でログイン」ボタン（自社ログインかつ端末が対応しているときだけ）。アカウント設定のセキュリティ（SecuritySection の中。design.md:128）にパスキーの一覧・追加・削除
5. 依存: backend `webauthn==2.8.0`・`pyOpenSSL==26.2.0`、frontend `@simplewebauthn/browser` `14.0.0`（版は固定）
6. design.md に、維持の仕組み（:242）のテストのパスと、§11 の判断（U1〜U4）を書き戻す

入れない（理由）:
- 管理者の 2 段階の確認・`admin_token_issued` のログ・`auth_refresh_tokens.amr` → ADR-1048 便7a〜7d
- refresh 後の amr の引き継ぎ（今の refresh は amr を付けない＝`auth.py:351`）→ 便7a で表に amr 列を足してから
- nginx・CSP・Permissions-Policy の変更 → 要らない（§2 F9）
- 自動入力の候補にパスキーを出す（conditional UI）・パスワードからの自動登録 → 今回はボタンだけ
- 登録前のもう一度の本人確認 → U4（今回は入れない理由を design.md に残す）
- Firebase の削除 → 便6

## 2. 前提の事実（origin/main 5c13bfbef・2026-10-31）

公式資料の生の写し: /tmp/CC報告ファイル/passkey-2fa/official/。Context7 は月の上限で使えなかった。そのため PyPI・npm・GitHub のタグ（py_webauthn v2.8.0・SimpleWebAuthn v14.0.0）・W3C を直接取得した。

- F1 表 `public.webauthn_credentials` は `migrations/20261013_160000_add_self_hosted_auth_tables.sql:16-32`、索引は :33。12 列。型は `id BIGSERIAL`・`user_id INTEGER`・`credential_id BYTEA UNIQUE`（長さ 1〜1023）・`public_key BYTEA`・`sign_count BIGINT >= 0`・`transports TEXT[]`・`backup_eligible`/`backup_state BOOLEAN`・`aaguid UUID NULL`・`label TEXT NULL`・`created_at`/`last_used_at TIMESTAMPTZ`。RLS なし（:3）。使うコードは 0 件（recon Q1）。生 SQL で読み書きする方針（`backend/app/auth/self_tokens.py:4-5`）
- F2 login は `backend/app/routers/auth.py:265-323`。発行の順は `issue_refresh_token`（:314-316）→ `db.commit()`（:317）→ `_set_refresh_cookie`（:318）→ `create_access_token(..., "pwd")`（:319-323）。refresh は :327-356（Cookie は :349、アクセストークンは :350-354 で amr は None）。password/change は :587-597。共通関数は無い（recon Q2）
- F3 設定: `rp_origin()` は `self_tokens.py:49-50`（既定 `https://app.salesanchor.jp`）。`AUTH_RP_ID` は無い（recon Q3）。本番は deploy.yml:370-372 で `AUTH_PROVIDER=self`（自社ログインに切替済み）。アクセストークンの寿命は 900 秒（self_tokens.py:23）
- F4 Redis: `backend/app/cache.py:62` `get_redis()`（`decode_responses=True`＝:46。未接続なら None）。本番の Redis は `redis:7-alpine`（docker-compose.yml:459）。redis-py は `redis[hiredis]>=5.0.0`（requirements.txt:16）。`GETDEL` は Redis 6.2 以降で使え、redis-py では `getdel()`
- F5 IP 単位の失敗回数: `check_auth_rate_limit`（cache.py:311）・`record_auth_failure`（:328）。login は :275 で確かめる。Redis が無いときは素通し（既存の login と同じ）
- F6 監査記録: `record_audit_log(db, tenant_id, user_id, action, table_name, record_id, old_data, new_data)`（`backend/app/services/audit.py:277`）。書き先は `tenant_{tenant_id:03d}.audit_logs`。password/change は tenant の文脈を外した後に呼ぶ（auth.py:567 で外し、:575 で呼ぶ）
- F7 py_webauthn 2.8.0（PyPI 2026-06-13 公開）の依存は `cryptography>=46.0.0`・`pyOpenSSL>=26.0.0`・`cbor2<6,>=5.6.5`・`pyasn1>=0.6.2`・`pyasn1-modules>=0.4.2`（official/webauthn-deps.txt）。今の `cryptography==48.0.1`（requirements.txt:24）と両立する pyOpenSSL は **26.2.0（`cryptography<49,>=46.0.0`）だけ**。26.3.0 以降と webauthn 3.x は `cryptography>=49` を求める（official/pyopenssl-26-crypto.txt）。だから両方を固定する。手元での `pip check` は審査の道具が止められたため未確認。§5-2 で担当が確かめる
- F8 py_webauthn 2.8.0 の部品（official/pywebauthn-init.py・structs.py・exceptions.py・verify_authentication_response.py・parse_*_credential_json.py）:
  - 公開関数: `generate_registration_options`・`verify_registration_response`・`generate_authentication_options`・`verify_authentication_response`・`options_to_json`・`base64url_to_bytes`。補助（webauthn.helpers）: `parse_registration_credential_json`・`parse_authentication_credential_json`・`bytes_to_base64url`
  - 例外は全部 `WebAuthnException` の子（exceptions.py:1。`InvalidRegistrationResponse`:9・`InvalidAuthenticationResponse`:17・`InvalidJSONStructure`:29・`InvalidCBORData`:69 など）
  - `parse_authentication_credential_json` の返り値: `raw_id` は bytes（:87）、`response.authenticator_data` は bytes（:90）、`response.user_handle` は bytes か None（:63-71・:92）。形が違えば `InvalidJSONStructure`。ただし `userHandle` の base64url の解読（:68）は包まれていない。壊れた文字列では `binascii.Error`（`ValueError` の子。`WebAuthnException` ではない）が出る
  - `verify_authentication_response` の中で 401 相当に包まれるのは `InvalidSignature` だけ（:178-185）。公開鍵の解読・署名の照合が別の例外を出すかは未確認。そのため except は `(WebAuthnException, ValueError)` で受ける（§4.4）
  - `parse_registration_credential_json` は transports のうち知っている値だけを `AuthenticatorTransport` にして残す（:60-67）
  - `VerifiedRegistration.aaguid` は str。`credential_id`・`credential_public_key` は bytes
  - `verify_authentication_response` の照合の順: id/raw_id（:86）→ 種類 → clientData・challenge（:113）→ origin → rpIdHash（:148）→ 本人の存在・確認（:151-154）→ 使用回数（:158-166）→ 署名（:178-185）。返り値は `new_sign_count`（:191）。使用回数の決まりは「新値か保存値が 0 より大きく、新値 ≦ 保存値なら拒否」で design.md:80 と同じ。ただし**署名より先に**照らす。`user_handle` は照らさない
- F9 nginx: Permissions-Policy は `camera=(), microphone=(), geolocation=()` だけ（nginx.conf:88）。W3C WebAuthn L3 §5.9 には「publickey-credentials-create と publickey-credentials-get の既定の許可は 'self'」とある。書かれていない機能は既定のままなので、同じ場所の画面からは使える。CSP（:84）の `connect-src 'self'` は同じ場所の `/api/v1/auth/` を許す。パスキーの口は `location /api/v1/auth/`（:144-146・10 回/分・burst 5）に入る（recon Q9）
- F10 @simplewebauthn/browser 14.0.0（official/npm-sw-browser-14.json・2193 バイト。tarball `browser-14.0.0.tgz`）:
  - `startRegistration({ optionsJSON })`・`startAuthentication({ optionsJSON })`・`browserSupportsWebAuthn()`（official/sw-index.ts・startRegistration.ts・startAuthentication.ts）
  - ブラウザの誤りは `WebAuthnError` に包んで投げる（startAuthentication.ts:112-113・startRegistration.ts:84-85）。`name` は元の誤りの名前を引き継ぐ（webAuthnError.ts `this.name = name ?? cause.name`）。取り消しは `NotAllowedError`、登録済みの端末は `InvalidStateError`（code `ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED`。identifyRegistrationError.ts:61-66）
- F11 画面:
  - ログインは `frontend/src/pages/login/LoginPage.tsx`。サインインの `<form>` は :101-133。送信ボタンは :130-132 の `Button loading={loading} variant="primary" size="auth" shape="pill" fullWidth type="submit" disabled={loading}`
  - 誤りの文言は、同じファイルの `loginErrorMessage`（:17-19。自社ログインなら `authErrorMessage`、そうでなければ Firebase 用）で作る。成功後は :50 の `navigate(from, { replace: true })`
  - 自社ログインの判定は `isSelfAuth()`（`frontend/src/lib/auth/provider.ts:19-21`）。ログインの呼び出しは `selfAuth.ts:88-106`（`postAuth`・`selfLogin`）→ `AuthContext.tsx:124-130`
  - `selfAuth.ts` で `postAuth`（:88）と `TokenResponse`（:35）は export されていない。`adoptAccessToken`（:61）は export 済み
  - `AuthContext.tsx` の型は :38-40、Provider の値は :154、開発用の代わりの値は :170-179（`signIn`・`signOut`・`sendPasswordReset`）。AuthContext を vi.mock で偽物にする試験はほかにもあるが、`signIn` を持ち LoginPage を描く偽物は `AllLegacyButtonOperationMigration.test.tsx:12-15` だけ。`LoginPage.test.tsx` は本物の `AuthProvider`（:26・:38）を描き、偽物にしているのは `lib/firebase`・`lib/firebase-auth`・`lib/auth/provider`（:14-24。`isSelfAuth: () => mock.self`）
  - アカウント設定は `frontend/src/pages/account-settings/SecuritySection.tsx`。外枠は `return (`（:83）の `<section className="account-settings-section">`（:84）〜`</section>`（:136）。見出しは :85-89。`AccountSettingsPage.tsx:13` から呼ばれ、各節は `.account-settings-layout`（account-settings.css:3-8。縦並び・間は `--space-8`）の子として並ぶ。`.account-settings-section` は枠線・角丸・内側の余白つき（account-settings.css:10-18）。試験は `SecuritySection.test.tsx`
  - 画面の API 呼び出しの 401（lib/api.ts:78-99 `fetchWithReauth`。説明の注釈は :69-77）: `/auth/` で始まる口の 401 では更新をしない（:82-85）。更新しないうえでログイン切れとして扱う口は `SESSION_END_PATHS`（:68。password/change・logout）。アクセスの期限は、切れる 30 秒前に先回りで更新される（selfAuth.ts:15 `EXPIRY_MARGIN_MS`・:144-146 `ensureSelfToken`）。試験は `frontend/src/lib/auth/apiReauth.test.ts`
  - API の形の正本は `frontend/api-contract/openapi.json`。CI「API contract is up to date」（.github/workflows/api-contract-check.yml:9）は `ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（:31-35）で書き出し、差分が出たら落とす（:50-53）。口を足すと必ず変わる（前例: 便4a の 51915ba57 は openapi.json を一緒にコミットした）
  - 金型: `DataTable`（components/DataTable.tsx。空の表示は `emptyState?: ReactNode`＝:94、スマホのカード表示は `mobileCards?`＝:127）・`ConfirmModal`（components/ConfirmModal.tsx:21）・`Button`・`TextFieldControl`・`Stack`（components/Stack.tsx。縦に積む・`gap` は `--space-N`）
  - Button の種類は `primary | secondary | ghost | danger | outline | tab`（components/buttonAppearance.ts:1）
  - API は `api.get`・`api.post`・`api.delete`（lib/api.ts:237-246）
- F12 文言と誤りの変換:
  - 文言の置き場は `login.*`（ja.json/en.json :674-683）・`authError.*`（:684-696）・`accountSettings.*`（:3182-）。パスキーのキーは無い（recon Q7）
  - 誤りの変換は `frontend/src/lib/auth/authErrorMessage.ts`。文脈は `"login" | "resetRequest" | "resetConfirm" | "passwordChange"` の 4 つ（:7）
  - 状態コードの対応（:31-52）: 401 → `authError.invalidCredentials`（「メールアドレスまたはパスワードが正しくありません。」）、400 で passwordChange → `currentPasswordWrong`、404 → `unavailable`、409・503 は扱いなし（`default`）
  - **このままパスキーに使うと、パスワードの話が画面に出る**。だから文脈 `"passkey"` を足す（§4.5）
- F13 試験:
  - `backend/tests/test_self_auth.py`（`self_auth_env`:36-43・`no_redis`:45-50・`http`:80-92・`_login`:95・Cookie の確かめ :136-141）。DB は SQLite（conftest.py:17・:266）
  - SQLite の作りは conftest.py に有る。`public.` を外す書き換えは :317-320、SQLite 版の表は :1334-1361。どちらも `auth_refresh_tokens`・`password_reset_tokens` だけで、**`webauthn_credentials` は無い**
  - UUID の列には str を渡している（self_tokens.py:164・:172。本番の PostgreSQL でも動いている）。sqlite の型の変換は conftest.py:270-280（`register_adapter`）
  - CI の pytest は `test.yml:207-242`（SQLite の全部＋PostgreSQL の RLS 試験）
  - 全部の口を数える既存の試験が 2 つある。CI は全件を流す（.github/workflows/test.yml「Run pytest (full suite + PostgreSQL RLS)」の `pytest -q --tb=short`）
    - `backend/tests/test_realtime_topics.py:68-73`: 書き込みの口（POST/PUT/PATCH/DELETE）は全部、`backend/app/realtime/topics.py` の `WRITE_ROUTE_TOPICS`（:20）か `NO_SIGNAL_ROUTES`（:86）のどちらか一方に載っていないと落ちる。auth の口は :100-126 に `_PENDING`（:83）で並ぶ。前例: 便4a の 51915ba57 は password/change を足した
    - `backend/tests/test_viewer_isolation.py:27-55・:91-114`: 閲覧者のトークンで全部の口を叩き、401 以外を返した口が `_PUBLIC_NO_AUTH_ROUTES`（:27。auth は :41-45）に無ければ落ちる
  - 画面の単体試験は `npm run test:unit`＝`vitest run --config vitest.unit.config.ts --project unit`（package.json:44）。型の生成は `npm run generate:api-types`（package.json:10。`src/api/generated/schema.d.ts` を作る）

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
- backend/tests/conftest.py（SQLite 版の表と書き換え。§4.6）
- frontend/package.json
- frontend/package-lock.json
- frontend/src/lib/auth/selfAuth.ts（`postAuth` と `TokenResponse` に `export` を足すだけ）
- frontend/src/contexts/AuthContext.tsx
- frontend/src/components/AllLegacyButtonOperationMigration.test.tsx（useAuth の偽物に `signInWithPasskey: vi.fn()` を足すだけ）
- frontend/src/pages/login/LoginPage.tsx
- frontend/src/pages/login/LoginPage.test.tsx
- frontend/src/pages/account-settings/SecuritySection.tsx（返す中身を `<>`〜`</>` で包み、`</section>` の後に `<PasskeySection />` を置くだけ。§4.5 (5)）
- frontend/src/lib/api.ts（パスキーの口の 401 で更新を許すだけ。§4.5 (7)）
- frontend/src/pages/account-settings/SecuritySection.test.tsx（api の偽物に get・delete を足し、試験を足す。§5）
- backend/app/realtime/topics.py（`NO_SIGNAL_ROUTES` に 5 行足すだけ。§4.4）
- backend/tests/test_viewer_isolation.py（`_PUBLIC_NO_AUTH_ROUTES` に 2 行足すだけ。§4.4）
- frontend/src/lib/auth/apiReauth.test.ts
- frontend/api-contract/openapi.json（§5-6 で書き出したものをそのままコミット。手で書かない）
- frontend/src/lib/auth/authErrorMessage.ts
- frontend/src/lib/auth/authErrorMessage.test.ts
- frontend/src/locales/ja.json
- frontend/src/locales/en.json
- docs/handoff/auth-self-hosted-passkey/design.md（:159 の便5 の行と :242 の維持の仕組み。§4.7）
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

`_clear_refresh_cookie`（:226）の上に足す。commit は呼び出し側に残す。今の順序 `issue/rotate → commit → cookie → access` は変えない。

```python
def _issue_session_tokens(
    response: Response, raw: str, expires_at: datetime, user_id: int, email: str, amr: str | None
) -> str:
    """更新用 Cookie を付け、アクセストークンを返す。トークンを出す口は全部ここを通る（ADR-1048 admin-2fa/design.md:66）。"""
    _set_refresh_cookie(response, raw, expires_at)
    return self_tokens.create_access_token(user_id, email, amr)
```

置き換え（中身は同じ。値の出どころを変えない）:
- login :318-323 → `access = _issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd")`。返すのは `SelfTokenResponse(access_token=access, token_type="bearer", expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS)`
- refresh :349-354 → `access = _issue_session_tokens(response, new_raw, expires_at, user_id, email, None)`。返す形は同じ
- password/change :591-594 → `_issue_session_tokens(response, raw, expires_at, user_row.id, user_row.email, "pwd")`

### 4.3 パスキーの部品（backend/app/auth/passkeys.py・新設）

置くもの（関数は全部この中に置き、auth.py からは呼ぶだけ）:

- 定数: `CHALLENGE_TTL_SECONDS = 300`・`MAX_PASSKEYS_PER_USER = 10`・`RP_NAME = "Sales Anchor"`・`LABEL_MAX = 64`
- `user_handle(user_id: int) -> bytes`: `user_id.to_bytes(8, "big")`（design.md:79。メールは入れない）
- `async def store_challenge(kind: str, owner: str, challenge: bytes) -> str`
  - `get_redis()` が None なら `HTTPException(503, "unavailable")`
  - `challenge_id = secrets.token_urlsafe(24)`。キーは `passkey_chal:{kind}:{owner}:{challenge_id}`、値は `bytes_to_base64url(challenge)`、`ex=CHALLENGE_TTL_SECONDS`
  - `challenge_id` を返す。kind は `reg` か `login`。owner は reg なら `str(user_id)`、login なら `-`
- `async def take_challenge(kind: str, owner: str, challenge_id: str) -> bytes | None`
  - 同じキーを `getdel` で取り出す（1 回で消える＝design.md:80）。無ければ None
  - 値は `base64url_to_bytes` で戻す。Redis が None なら 503
- `def registration_options(user_id: int, email: str, existing: list[bytes])`
  - `generate_registration_options(rp_id=self_tokens.rp_id(), rp_name=RP_NAME, user_name=email, user_id=user_handle(user_id), user_display_name=email, authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED, user_verification=UserVerificationRequirement.REQUIRED), exclude_credentials=[PublicKeyCredentialDescriptor(id=c) for c in existing])`
  - 呼び出し側は `options.challenge` を保存し、`json.loads(options_to_json(options))` を返す
  - user_name に email を使う理由（U2）: 端末の候補一覧で、本人がどのアカウントかを見分けるため。端末の中だけに置かれ、user handle には入れない
- `def authentication_options()`: `generate_authentication_options(rp_id=self_tokens.rp_id(), user_verification=UserVerificationRequirement.REQUIRED)`。allow_credentials は空（端末が候補を出す。design.md:80）
- `def sign_count_rejected(stored: int, received: int) -> bool`: `(received > 0 or stored > 0) and received <= stored`（design.md:80。F8 のライブラリと同じ式）

### 4.4 口（auth.py。`password/change` の後ろに足す）

共通の決まり:
- POST と DELETE は全部、最初に `_require_app_origin(request)` を通す（design.md:75）
- py_webauthn の parse と verify は**同じ try の中**に置く。`except (WebAuthnException, ValueError)` でまとめて受ける（F8。`userHandle` の解読は `binascii.Error`＝`ValueError` を出す）
- 返す detail は識別子だけ
- 全部の口を数える既存の試験（F13）に合わせる:
  - `topics.py` の `NO_SIGNAL_ROUTES` の auth の行（:100-126）に、アルファベット順で次の 5 行を `_PENDING` で足す: `("DELETE", "/api/v1/auth/passkeys/{passkey_id}")`・`("POST", "/api/v1/auth/passkey/login/options")`・`("POST", "/api/v1/auth/passkey/login/verify")`・`("POST", "/api/v1/auth/passkey/register/options")`・`("POST", "/api/v1/auth/passkey/register/verify")`。`WRITE_ROUTE_TOPICS` には足さない
  - `test_viewer_isolation.py` の `_PUBLIC_NO_AUTH_ROUTES` の auth の行（:41-45）に、ログイン前の 2 本 `("POST", "/api/v1/auth/passkey/login/options")`・`("POST", "/api/v1/auth/passkey/login/verify")` を足す。この 2 本はトークンを見ない（§4.4 の作り）。ログイン後の 4 本は `get_current_user` を通るので足さない（閲覧者のトークンで 401 になる）
- `record_audit_log` は、`tenant_id=利用者の tenant_id`・`user_id=利用者の id` で呼ぶ。tenant の文脈の外で呼ぶ（password/change と同じ順＝F6）

**POST `/passkey/register/options`**（`get_current_user`・入力なし）
1. `SELECT credential_id FROM public.webauthn_credentials WHERE user_id = :uid` で本人の分を引く
2. 10 件以上なら 409 `passkey_limit`
3. `registration_options(uid, email, existing)` を作る
4. `store_challenge("reg", str(uid), options.challenge)`
5. `{"challenge_id": str, "options": dict}` を返す

**POST `/passkey/register/verify`**（`get_current_user`）
- 入力: `challenge_id: str`（1〜64 字）・`credential: dict`・`label: str | None`（`LABEL_MAX` 字まで。前後の空白を除き、空なら NULL）
1. `take_challenge("reg", str(uid), challenge_id)` が None なら 400 `challenge_expired`
2. try の中で `parsed = parse_registration_credential_json(credential)` → `verified = verify_registration_response(credential=parsed, expected_challenge=..., expected_rp_id=rp_id(), expected_origin=rp_origin(), require_user_verification=True)`。`WebAuthnException`・`ValueError` は 400 `passkey_invalid`
3. INSERT の値:
   - `user_id`＝uid
   - `credential_id`＝`verified.credential_id`（bytes）、`public_key`＝`verified.credential_public_key`（bytes）、`sign_count`＝`verified.sign_count`
   - `transports`＝`[t.value for t in (parsed.response.transports or [])]`（list[str]）
   - `backup_eligible`＝`verified.credential_device_type == CredentialDeviceType.MULTI_DEVICE`、`backup_state`＝`verified.credential_backed_up`
   - `aaguid`＝`verified.aaguid`（str のまま渡す。F13 の UUID の列と同じ扱い）
   - `label`、`created_at`＝今
   - `RETURNING id, created_at`
4. 一意制約に当たったら（`IntegrityError`）rollback して 409 `passkey_exists`
5. `record_audit_log(action="create", table_name="webauthn_credentials", record_id=新しい id, new_data={"event": "passkey_registered"})` → commit
6. 201 で `{"id": int, "label": str | None, "created_at": str}`

**POST `/passkey/login/options`**（認証なし・入力なし）
1. `_require_issuance_enabled()`（design.md:103）→ origin → `check_auth_rate_limit(ip)` が真なら 429 `too_many_attempts`
2. `authentication_options()` を作り、`store_challenge("login", "-", options.challenge)`
3. `{"challenge_id": str, "options": dict}` を返す

**POST `/passkey/login/verify`**（認証なし）
- 入力: `challenge_id`・`credential: dict`
- 失敗はどれも同じ 401 `invalid_credentials` を返し、`record_auth_failure(ip)` を呼ぶ（以下「401」）
1. `_require_issuance_enabled()` → origin → 回数制限（429）
2. `take_challenge("login", "-", challenge_id)` が None なら 401
3. try の中で `parsed = parse_authentication_credential_json(credential)`。`WebAuthnException`・`ValueError` は 401
4. `SELECT c.id, c.user_id, c.public_key, c.sign_count, u.email, u.tenant_id, u.is_active FROM public.webauthn_credentials c JOIN public.users u ON u.id = c.user_id WHERE c.credential_id = :cid`（`:cid`＝`parsed.raw_id`）。行が無い・`is_active` が偽なら 401
5. 持ち主の確かめ（F8 でライブラリは照らさない）: `parsed.response.user_handle` が None か、`user_handle(c.user_id)` と違えば 401
6. try の中で `verified = verify_authentication_response(credential=parsed, expected_challenge=..., expected_rp_id=rp_id(), expected_origin=rp_origin(), credential_public_key=c.public_key, credential_current_sign_count=0, require_user_verification=True)`。`WebAuthnException`・`ValueError` は 401
   - **`credential_current_sign_count=0` を渡す理由**: ライブラリは使用回数を署名より先に照らす（F8）。保存値を渡すと、署名の無い偽の応答でも使用回数の拒否になる。そこで使用回数はここでは止めず、署名が通った後の 7 で照らす。0 を渡すと、ライブラリの式は `received > 0 and received <= 0` となり、必ず通る
7. 使用回数の照合（署名が通った後だけ）: `sign_count_rejected(c.sign_count, verified.new_sign_count)` が真なら、`record_audit_log(tenant_id, user_id, action="update", table_name="webauthn_credentials", record_id=c.id, new_data={"event": "passkey_sign_count_rejected", "stored": 保存値, "received": 新値})` → commit → 401（design.md:80「拒否し、監査記録に残す」）
8. 成功のとき:
   - `UPDATE public.webauthn_credentials SET sign_count = :n, backup_state = :b, last_used_at = :now WHERE id = :id`（`:n`＝`verified.new_sign_count`、`:b`＝`verified.credential_backed_up`）
   - `set_tenant_context(db, tenant_id)` → `UPDATE public.users SET last_login = :now WHERE id = :uid` → `clear_tenant_context(db)`（login :303-310 と同じ順）
   - `issue_refresh_token` → commit → `_issue_session_tokens(..., "webauthn")`
   - `SelfTokenResponse`（login と同じ形）を返す

**GET `/passkeys`**（`get_current_user`）
- `SELECT id, label, created_at, last_used_at FROM public.webauthn_credentials WHERE user_id = :uid ORDER BY created_at`
- `{"items": [...]}` を返す（日時は ISO 8601）

**DELETE `/passkeys/{passkey_id}`**（`get_current_user`・パスの int）
1. origin を確かめる
2. `DELETE FROM public.webauthn_credentials WHERE id = :id AND user_id = :uid RETURNING id`。0 行なら 404 `passkey_not_found`（他人のものも同じ 404）
3. `record_audit_log(action="delete", ..., new_data={"event": "passkey_deleted"})` → commit → 204

判断（§11 で設計書へ戻す）:
- 口座の停止（`locked_until`）は、パスキーのログインでは見ない（U1）
  - 理由: 停止は、パスワードの総当たりへの対策（design.md:52「口座単位の失敗回数」）。パスキーは端末と顔・指紋の両方が要り、総当たりできない
  - 停止中でも本人がパスキーで入れる。これにより、他人がパスワードを試して本人を締め出すのを防げる
  - `is_active=false` の人は必ず拒否する（4）
- 失敗の応答は、どの理由でも同じ 401 `invalid_credentials` にする。理由は、表に無い・停止された人・持ち主違い・照合失敗・使用回数の拒否。外から理由を見分けさせない

### 4.5 画面

決まり:
- 文言は全部 `t("key")`。ja.json と en.json に同じキーを同じ位置に足す（ADR-027）
- 生の `<button>`・`<input>`・`<table>`・色の直書きは使わない（ADR-144）。新しい CSS は足さない。並びは金型 `Stack` で作る（足す必要が出たら §6 B4）

足すキー（ja / en）:
- `login.signInWithPasskey`: 「顔・指紋でログイン」/ "Sign in with face or fingerprint"
- `authError.passkeyFailed`: 「顔・指紋でのログインに失敗しました。パスワードでログインするか、もう一度お試しください。」/ "Sign-in with face or fingerprint failed. Sign in with your password or try again."
- `authError.passkeyExpired`: 「時間切れです。もう一度お試しください。」/ "Timed out. Please try again."
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

(1) `frontend/src/lib/auth/selfAuth.ts`: `async function postAuth`（:88）と `interface TokenResponse`（:35）の前に `export` を足すだけ。中身は変えない

(2) `frontend/src/lib/auth/passkey.ts`（新設）
- `export function passkeySupported(): boolean { return isSelfAuth() && browserSupportsWebAuthn(); }`
- `export async function selfPasskeyLogin(): Promise<void>`
  - `postAuth<{ challenge_id: string; options: PublicKeyCredentialRequestOptionsJSON }>("/passkey/login/options")`
  - → `startAuthentication({ optionsJSON: res.options })`
  - → `postAuth<TokenResponse>("/passkey/login/verify", { challenge_id, credential })`
  - → `adoptAccessToken(token.access_token, token.expires_in)`（selfLogin :103-106 と同じ受け取り方）
- `export async function registerPasskey(label: string): Promise<void>`: `api.post("/auth/passkey/register/options", {})` → `startRegistration({ optionsJSON })` → `api.post("/auth/passkey/register/verify", { challenge_id, credential, label })`
- `export function passkeyBrowserError(err: unknown): "cancelled" | "exists" | null`
  - `err instanceof Error` で `err.name === "NotAllowedError"` なら `"cancelled"`、`"InvalidStateError"` なら `"exists"`、ほかは null
  - 根拠は F10（WebAuthnError は元の名前を引き継ぐ）

(3) `AuthContext.tsx`
- 型（:38-40）に `signInWithPasskey: () => Promise<void>` を足す
- `signIn`（:124-130）の隣に `signInWithPasskey` を作り、自社ログインのときだけ `selfPasskeyLogin` を呼ぶ。自社ログインでないときは何もしない
- Provider の値（:154）と、開発用の代わりの値（:170-179）にも足す（代わりの値は `async () => {}`）
- `AllLegacyButtonOperationMigration.test.tsx:12` の偽物に `signInWithPasskey: vi.fn()` を足す（useAuth の偽物はここだけ。`LoginPage.test.tsx` は本物の AuthProvider を使うので足さない＝F11）

(4) `LoginPage.tsx`
- サインインの `<form>`（:101-133）を `<Stack gap="3">` で包み、`</form>` の後に置く
- `passkeySupported()` が真のときだけ、`Button variant="outline" size="auth" shape="pill" fullWidth type="button"` で `t("login.signInWithPasskey")` を出す
- 処理中は既存の `loading` を真にする。両方のボタンを `loading`・`disabled` にして二度押しを防ぐ（:130 と同じ持ち方）
- 押すと `signInWithPasskey()` を呼ぶ。成功したら :50 と同じ `navigate(from, { replace: true })`
- 誤りの文言:
  - `passkeyBrowserError(err) === "cancelled"` なら `authError.passkeyCancelled`
  - それ以外は `authErrorMessage(err, t, "passkey")`（ボタンは自社ログインのときだけ出るので、:17 の `loginErrorMessage` を通さない）

(5) `PasskeySection.tsx`（新設）と `SecuritySection.tsx`
- SecuritySection の `return (`（:83）の中身を `<>`〜`</>` で包む。既存の `<section>`（:84-136）は 1 文字も変えない。その `</section>` の後に `{isSelfAuth() && <PasskeySection />}` を置く
  - 枠の中に枠を入れない。PasskeySection は自分の `<section className="account-settings-section">` を持ち、セキュリティの節のすぐ下に、同じ形の別の枠として並ぶ（間は `.account-settings-layout` の `--space-8`。新しい CSS は要らない）
  - design.md:128 の「セキュリティの欄に置く」は、セキュリティの節の直後に並べることで満たす
- PasskeySection の見出しは、SecuritySection の形（:84-89 の `account-settings-section`・`account-settings-section-title`・`ACCOUNT_ICONS.security`）をそのまま使い、題は `t("accountSettings.passkeyTitle")`
- 一覧: `DataTable`
  - 列: `label`（空なら `passkeyUnnamed`）・`created_at`・`last_used_at`（空なら `passkeyNeverUsed`）・削除の列（`Button variant="danger" size="sm"`）
  - 日時は `new Date(v).toLocaleDateString(i18n.language)`
  - 0 件は `emptyState={t("accountSettings.passkeyEmpty")}`（DataTable.tsx:94）。`mobileCards` を付ける（スマホで横にはみ出さないため。DataTable.tsx:127）
- 追加: `TextFieldControl`（名前・任意・`maxLength={64}`）＋ `Button variant="secondary"`（`passkeyAdd`）を縦に `Stack`
  - 処理中は `loading`・`disabled`
  - `browserSupportsWebAuthn()` が偽なら、ボタンの代わりに `passkeyUnsupported` の文を出す
- 削除: `ConfirmModal`（`danger`・`passkeyDeleteTitle`・`passkeyDeleteMessage`）→ `api.delete("/auth/passkeys/" + id)` → 一覧を読み直す
- 誤りの文言: `passkeyBrowserError(err)` が `"cancelled"` なら `passkeyCancelled`、`"exists"` なら `passkeyExists`。それ以外は `authErrorMessage(err, t, "passkey")`

(6) `authErrorMessage.ts`
- `AuthErrorContext`（:7）に `"passkey"` を足す
- `context === "passkey"` のときだけ、既存の switch（:31）の前で次を返す:
  - 401 → `authError.passkeyFailed`
  - 400 で detail が `challenge_expired` → `authError.passkeyExpired`
  - 400 のそれ以外 → `authError.passkeyFailed`
  - 409 で detail が `passkey_exists` → `authError.passkeyExists`
  - 409 で detail が `passkey_limit` → `authError.passkeyLimit`
  - 503 → `authError.unavailable`
  - それ以外は既存の switch に任せる（403・404・429・422）
- 既存の 4 つの文脈の振る舞いは変えない

(7) `lib/api.ts`（ログインしてから使うパスキーの口の 401）
- 理由: 今は `/auth/` で始まる口の 401 では更新をしない（:82-85）。期限は切れる前に先回りで更新される（F11）。それでも先回りの後に失効した場合などは 401 になり、パスキーの口だけ更新されずに失敗の文言が出る。ほかの口と同じく 1 回だけ更新する（design.md:129「401 のときの自動 refresh は 1 回まで」）
- `SESSION_END_PATHS`（:68）の隣に `const REAUTH_AUTH_PREFIXES = ["/auth/passkey/register/", "/auth/passkeys"];` を置く
- :82 の条件を `if (path.startsWith("/auth/") && !REAUTH_AUTH_PREFIXES.some((p) => path.startsWith(p)))` にする。それ以外は変えない
- :69-77 の説明の注釈に「パスキーの登録・一覧・削除はログイン後の口なので、ほかの口と同じく更新する」を 1 行足す
- ログイン前の login/options・login/verify は `postAuth`（selfAuth.ts:88）で送り、api.ts を通らないので、この変更の影響を受けない

### 4.6 試験の DB（backend/tests/conftest.py）

- :319-320 の後に、`public.webauthn_credentials` → `webauthn_credentials` の書き換えを足す（同じ形）
- :1361 の後に、SQLite 版の表を足す（コメントは :1334 と同じ形「ADR-1013 便5: public.webauthn_credentials の SQLite 版（BYTEA→BLOB, UUID→TEXT, TEXT[]→TEXT, BIGSERIAL→INTEGER）」）:

```sql
CREATE TABLE IF NOT EXISTS webauthn_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    credential_id BLOB NOT NULL UNIQUE,
    public_key BLOB NOT NULL,
    sign_count INTEGER NOT NULL DEFAULT 0,
    transports TEXT NOT NULL DEFAULT '[]',
    backup_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    backup_state BOOLEAN NOT NULL DEFAULT FALSE,
    aaguid TEXT,
    label TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
)
```

- transports の渡し方は、本番のコードでは 1 通りにする（list[str] を渡す。PostgreSQL では TEXT[] になる）。SQLite だけ、conftest.py:270-280 の `set_sqlite_compat` に `sqlite3.register_adapter(list, json.dumps)` を足す。DB ごとの分岐を本番のコードに入れない
- PostgreSQL の RLS 試験（test.yml:207-242）は、migration で作った本物の表を使う。表に RLS は無い（F1）ので、ここの追加は要らない

### 4.7 設計書へ書き戻す（design.md）

- :159 の便5 の行に足す: 「pyOpenSSL 26.2.0 固定（cryptography 48 と両立する唯一の版）」「使用回数の照合は署名の確認の後」「user handle の持ち主を照らす」「口座の停止は見ない（U1）」「端末の候補名に email（U2）」
- :242 の維持の仕組みに足す: 試験のパス `backend/tests/test_passkeys.py`・`frontend/src/lib/auth/passkey.test.ts`・`frontend/src/pages/account-settings/PasskeySection.test.tsx`。毎朝の画面点検はパスキーの口を通らないこと（U3）。そのため pytest（CI の必須の確かめ）で守ること
- U4 の理由を、「弊害・トレードオフ」（design.md:219）の欄に 1 行足す

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る）

1. `cd "${WT}" && cd backend && pip install -r requirements.txt 2>&1 | tail -5`
2. `cd "${WT}" && cd backend && pip check 2>&1 | tail -5`（「No broken requirements found.」が出ること）
3. `cd "${WT}" && cd backend && python -c "import webauthn, OpenSSL, cryptography; print(webauthn.__version__, OpenSSL.__version__, cryptography.__version__)"`（`2.8.0 26.2.0 48.0.1`）
4. `cd "${WT}" && cd backend && python -m pytest tests/test_passkeys.py tests/test_self_auth.py tests/test_realtime_topics.py tests/test_viewer_isolation.py -q 2>&1 | tail -15`
5. `cd "${WT}" && cd frontend && npm ci 2>&1 | tail -5`
6. `cd "${WT}" && cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -5` の後に `cd "${WT}" && cd frontend && npm run generate:api-types 2>&1 | tail -5`。書き出した `frontend/api-contract/openapi.json` はコミットする（CI「API contract is up to date」＝api-contract-check.yml:31-53 が差分で落とすため。ADR-1010。前例 51915ba57）。続けて `cd "${WT}" && git status --short frontend/api-contract/` を貼る（コミット後は空）
7. `cd "${WT}" && cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/auth src/pages/login src/pages/account-settings src/components/AllLegacyButtonOperationMigration.test.tsx 2>&1 | tail -20`
8. `cd "${WT}" && cd frontend && npx tsc --noEmit -p . 2>&1 | tail -10`
9. `cd "${WT}" && cd frontend && npm run lint 2>&1 | tail -15`
10. `cd "${WT}" && node -e "const a=require('./frontend/src/locales/ja.json'),b=require('./frontend/src/locales/en.json');const k=o=>Object.entries(o).flatMap(([x,v])=>typeof v==='object'?k(v).map(y=>x+'.'+y):[x]);const A=k(a),B=new Set(k(b));console.log(A.filter(x=>!B.has(x)).length, k(b).filter(x=>!new Set(A).has(x)).length)"`（`0 0`）
11. `cd "${WT}" && grep -c "_issue_session_tokens" backend/app/routers/auth.py`（定義 1＋呼び出し 4＝`5`）
12. `cd "${WT}" && git diff --name-only origin/main...HEAD | tail -40`（§3 の一覧と一致すること）

backend/tests/test_passkeys.py に入れる試験:
- py_webauthn の照合関数は `monkeypatch` で差し替え、実物の暗号は使わない
- 差し替えるのは `app.auth.passkeys` と `app.routers.auth` が import した名前（`verify_registration_response`・`verify_authentication_response`・`parse_authentication_credential_json`・`parse_registration_credential_json`）
- Redis は、`async def` の `get`・`set`（`ex` を受ける）・`getdel` を持つ辞書の偽物を渡す（cache.py:8 は `redis.asyncio` なので、呼ぶ側は `await` する）。差し替える先は `app.auth.passkeys.get_redis`（passkeys.py は `from app.cache import get_redis` で読むため、`app.cache.get_redis` を差し替えても効かない）
- 監査記録は表を読まずに確かめる: `app.routers.auth.record_audit_log` を `AsyncMock` で差し替え（test_self_auth.py:512-515 の `noop_audit` と同じ形）、`await_args_list` の `new_data["event"]` を数える。以下「監査に〜」はこの数え方
- 後片付けは test_self_auth.py の `cleanup_self_auth`（:70-77）と同じ形で、webauthn_credentials も消す

試験の中身:
- T1 login/options: 200。`challenge_id` が返り、偽の Redis に 300 秒で入る
- T2 login/verify: 正しい challenge で 200。`amr == ["webauthn"]`。Cookie の 4 属性（test_self_auth.py:136-141 と同じ確かめ）。`sign_count`・`last_used_at`・users.last_login が更新される
- T3 同じ challenge_id を 2 回使うと、2 回目は 401（challenge は 1 回で消える＝design.md:202）
- T4 使用回数（署名の照合は成功させたうえで、`new_sign_count` を変える）:
  - 保存値 5・新値 5 → 401。監査に `passkey_sign_count_rejected` が 1 回
  - 保存値 5・新値 3 → 401
  - 保存値 0・新値 0 → 200（design.md:80・:202）
- T4b 署名の照合が失敗する応答（verify が `InvalidAuthenticationResponse` を投げる）→ 401。監査に `passkey_sign_count_rejected` は 0 回。`verify_authentication_response` に渡った `credential_current_sign_count` が 0 である
- T5 表に無い credential → 401。`is_active=false` の人 → 401。user_handle が別の人 → 401。user_handle が無い → 401。応答の本文は T4・T5 で全部同じ
- T5b 壊れた `userHandle`: この試験だけ `parse_authentication_credential_json` を差し替えず本物を使う。id・rawId・type・response は正しい形にし、`userHandle` だけを `"A"`（長さが 4 の倍数より 1 多く、解読で `binascii.Error` が出る）にする → 401（500 にならない）。`"!!!"` は解読で b'' になり誤りが出ないので使わない。register の credential が壊れた base64url → 400 `passkey_invalid`
- T6 `AUTH_PROVIDER=firebase` で、login/options と login/verify が 404（design.md:103）
- T7 Origin が違う・無いとき、5 本の POST/DELETE の口が全部 403
- T8 register:
  - verify の成功で 1 行入る。transports・backup_eligible・aaguid・label も入る。監査に `passkey_registered` が 1 回
  - 同じ credential_id で 409 `passkey_exists`
  - 10 件ある人の register/options が 409 `passkey_limit`
  - 他人の reg challenge（owner が違う）は 400 `challenge_expired`
  - parse が `InvalidJSONStructure` を投げると 400 `passkey_invalid`
- T9 GET /passkeys は本人の分だけ返す。DELETE で他人の id は 404 になり、行は残る。本人の id は 204 で消え、監査に `passkey_deleted` が 1 回
- T10 Redis が None のとき、options が 503 `unavailable`
- T11 login・refresh・password/change の既存試験（test_self_auth.py）が全部そのまま通る（共通関数への置き換えで振る舞いが変わらない）

画面の試験:
- passkey.test.ts
  - `passkeySupported` は、自社ログインかつ対応端末のときだけ真
  - `selfPasskeyLogin` は options → startAuthentication → verify の順に呼び、トークンを受け取る（@simplewebauthn/browser は vi.mock）
  - `passkeyBrowserError` は NotAllowedError で `"cancelled"`、InvalidStateError で `"exists"` を返す
- LoginPage.test.tsx（本物の AuthProvider のまま。`mock.self = true` で自社ログインにする）
  - `vi.mock("../../lib/auth/passkey", async (orig) => ({ ...(await orig()), passkeySupported: () => mock.passkey, selfPasskeyLogin: mock.selfPasskeyLogin }))` を足す。`passkeyBrowserError` は本物のまま。`mock`（:8 の vi.hoisted）に `passkey: true`・`selfPasskeyLogin: vi.fn()` を足す
  - 対応端末でボタンが出る。非対応では出ない
  - 押すと AuthProvider を通って `selfPasskeyLogin` が 1 回呼ばれ、処理中は両方のボタンが押せない
  - 取り消しで `authError.passkeyCancelled`、401 で `authError.passkeyFailed`（パスワードの文言が出ない）
- PasskeySection.test.tsx: 一覧・0 件の表示・追加・削除の確認窓から api.delete・409 の 2 つの文言・InvalidStateError で passkeyExists
- authErrorMessage.test.ts: `"passkey"` の 401・400×2・409×2・503。既存の 4 つの文脈の結果が変わらないこと
- SecuritySection.test.tsx: まず偽物を直す。:7 の `mock` に `get: vi.fn()`・`delete: vi.fn()` を足し、beforeEach で `mock.get.mockReset().mockResolvedValue({ items: [] })` とする。:23 の差し替えを `api: { get: mock.get, post: mock.post, delete: mock.delete }` にする（便5 の後は既存の試験でも PasskeySection が描かれ、一覧を読むため）。その上で: 自社ログインでパスキーの節が、セキュリティの `<section>` の中ではなく後ろの兄弟として出る（`container.querySelectorAll(".account-settings-section")` が 2 つで、入れ子でない）。Firebase では出ない。既存の試験は全部そのまま通る
- apiReauth.test.ts: `/auth/passkeys` と `/auth/passkey/register/options` の 401 は更新を 1 回送って元の要求を送り直す。`/auth/login` などほかの `/auth/` の 401 は今までどおり更新しない（:97 の試験がそのまま通る）

## 6. 分岐ごとの対処

- B1 `pip install` で pyOpenSSL 26.2.0 と他の依存がぶつかる → 停止（版の引き上げは別件＝admin-2fa/design.md:142）
- B2 `npm ci` で、@simplewebauthn/browser 14.0.0 の peer の警告以外の誤りが出る → 停止
- B3 `Stack` で包むとログイン画面の並びが崩れる（form の幅・余白が変わる）、またはアカウント設定でパスキーの枠がセキュリティの枠と揃わない → 新しい CSS を足さずに停止し、画面の写しを報告に付ける
- B4 ほかに新しい CSS が要る → 足さずに停止し、画面の写しを報告に付ける
- B5 `get_current_user` が `/api/v1/auth` 配下で別の振る舞いをする（試験で 401 になる等）→ 停止
- B6 SQLite で `register_adapter(list, ...)` が効かない、または aiosqlite が list を拒む → 停止（本番のコードに DB ごとの分岐を入れない）
- B7 §5-8 の tsc が、パスキーと関係ないファイルで落ちる → 落ちたファイルと行を報告して停止。`@simplewebauthn/browser` の型が見つからない（TS2307 など）ときも、型の宣言を自作せずに停止
- B8 フック・CI に止められた → 言い換えずに停止し、原文を報告
- B9 §5-6 の書き出しで、パスキーの口以外の差分が openapi.json に出る → コミットせずに停止し、差分の行数と最初の 40 行を報告
- B10 §5-4 の test_realtime_topics.py・test_viewer_isolation.py が、§4.4 で足した行のあとも落ちる → 落ちた口の一覧を報告して停止（表から口を外す・試験を緩める直しはしない）

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K2: PO の端末で、顔か指紋だけでログインできる（パスワードを打たない） | PO が本番で実演（§8）。画面の写しか録画 |
| K2-DB: PO の登録後、`webauthn_credentials` に PO の行が 1 行 | 本番 DB の読み取りの道で件数だけ見る（Opus） |
| 使用回数の拒否と監査記録は、署名が正しい応答でだけ起きる。challenge は 1 回限り | T3・T4・T4b（design.md:202） |
| 他人の端末の応答を自分のパスキーとして通さない | T5（user_handle） |
| 発行の 4 経路が `_issue_session_tokens` を通る | §5-11 が `5` |
| 他人のパスキーを見られない・消せない | T9 |
| パスキーの失敗で、パスワードの文言が画面に出ない | LoginPage.test.tsx・authErrorMessage.test.ts |
| 既存のログインが変わらない | T11・本番の画面点検（毎朝）が合格のまま |
| 文言は ja/en 同じキー・金型だけ | §5-10 が `0 0`・lint 緑・差分に生の button/input/table が 0・新しい CSS ファイルが 0 |
| compose・deploy・nginx・migrations を触らない | §5-12 |

## 8. 反映の順番と PO の作業

1. PR → 審査（reviewer opus）APPROVE → CI 緑 → Opus がマージ。危ないパスを含まないため、ADR-136 の GO の対象外（区分はコードのみ）→ deploy の成功と /health 200 を確かめる
2. Opus が本番で `POST /api/v1/auth/passkey/login/options`（Origin 付き）が 200 になることを確かめる（DB には書かない）
3. PO の作業（K2）: スマホかパソコンで app.salesanchor.jp にパスワードでログイン → アカウント設定 →「この端末を登録」→ 顔か指紋 → いったんログアウト →「顔・指紋でログイン」→ 顔か指紋だけで入れる
4. Opus が読み取りの道で `webauthn_credentials` の件数を見る

## 9. 戻し方

PR を revert して deploy する。登録済みのパスキーの行は残るが、口が無くなるので使われない（design.md:159）。パスワードのログインは便5 の前後で変わらない。

## 10. PR

1. `bash scripts/new-worktree.sh release/passkey-b5` → `git worktree list | tail -20` で実在を確かめ、`export WT=...` に入れる
2. 実装 → §5 の 1〜12
3. `cd "${WT}" && git add -A && git commit -m "feat: passkey sign-in, register, list and delete (ADR-1013 b5)"`（.claude-pipeline/active-work.d は入れない。`src/api/generated/schema.d.ts` は git の対象外のまま入れない）
4. `cd "${WT}" && git push -u origin HEAD`
5. `cd "${WT}" && bash scripts/gh-pr-create-safe.sh` で PR を作る（ベースは main・下書きにしない）。本文の `### 標準ワークフロー確認` に書くもの:
   - recon: docs/handoff/auth-self-hosted-passkey/recon-b5.md
   - 設計: docs/handoff/auth-self-hosted-passkey/design.md
   - カード: docs/handoff/auth-self-hosted-passkey/card-b5.md
   - 対象ADR: ADR-1013, ADR-1048
   - 触るファイル: §3 の全部をカンマ区切り 1 行
   - 削除するファイル: なし
6. マージはしない（Opus が行う）

## 11. 判断（第2版で決めた。§4.7 で design.md へ書き戻す）

- U1 口座の停止は、パスキーのログインでは見ない（§4.4）。`is_active` は必ず見る。審査（第1版）で妥当と判定
- U2 `user_name`・`user_display_name` に email を使う（§4.3）。design.md:79 が禁じるのは user handle にメールを入れることだけ。審査で妥当と判定
- U3 本番の画面点検の利用者（点検専用の人）はパスキーを持たない。そのため毎朝の点検は、パスキーの口を通らない。パスキーの口の守りは T1〜T11（CI の必須の pytest）。審査で妥当と判定
- U4 登録の前に、もう一度の本人確認は求めない
  - 起こりうること: 盗まれたアクセストークンで、他人がパスキーを足すおそれがある
  - 今回は入れない理由:
    - アクセストークンはメモリだけに置く。寿命は 900 秒（F3）
    - 更新用の Cookie は HttpOnly。画面のスクリプトからは読めない
    - 登録・削除は監査記録に残る
    - 一覧で本人が見つけて消せる
  - 管理者には ADR-1048 便7 で 2 段階の確認が入る。強める時期はそこで見直す

## 12. 報告欄（担当が追記）

## 改訂の記録

- 第2版（2026-10-31）: 第1版 5157d338c の審査（reviewer opus・REVISE）を反映
  - MAJOR-1 使用回数の照合を署名の後へ移した（§4.4 の 6・7、T4b）
  - MAJOR-2 文脈 `"passkey"` と文言キーを足した（§4.5 (6)）
  - MAJOR-3 試験の DB に表を足した（§3・§4.6・B6）
  - MAJOR-4 vitest に `--config vitest.unit.config.ts --project unit` を付け、型の生成を先に流す（§5-6・§5-7）
  - MINOR-1 refresh の行を :349-354 に直した
  - MINOR-2 selfAuth.ts を触るファイルに入れた
  - MINOR-3 開発用の代わりの値・偽物 2 か所を入れた
  - MINOR-4 user_handle の照合を足した
  - MINOR-5 監査記録の tenant_id・user_id・呼ぶ順を書いた
  - MINOR-6 INSERT の値の出どころを書いた
  - MINOR-7 parse を try の中に入れた
  - MINOR-8 InvalidStateError を passkeyExists にした
  - MINOR-9 二度押しを防ぐ
  - MINOR-10 「または」の文字をやめ、金型 Stack で並べる
  - MINOR-11 emptyState・mobileCards に決めた
  - MINOR-12 一覧の置き場を SecuritySection の中にして design.md:128 に合わせた
  - MINOR-13 U4 として理由を残した
  - MINOR-14 次の 4 点は公式の写しを取り足して確かめた（F8・F10）
    - npm の写しは 2193 バイトで、空ではない
    - 例外の親
    - transports の扱い
    - WebAuthnError の name

- 第3版（2026-10-31）: 第2版 f6b3e3b09 の審査（reviewer opus・REVISE）を反映
  - MAJOR-A API の形の正本 openapi.json を書き出してコミットする（§3・§5-6・B9）
  - MINOR-B LoginPage.test.tsx は本物の AuthProvider を使うので、useAuth の偽物ではなく lib/auth/passkey を偽物にする（F11・§4.5 (3)・§5）
  - MINOR-C 監査記録は record_audit_log の差し替えで数える（§5）
  - MINOR-D Redis の差し替え先を app.auth.passkeys.get_redis にした（§5）
  - MINOR-E design.md の参照を「弊害・トレードオフ」(:219) に直した（§4.7）
  - MINOR-F 枠の中に枠を入れず、セキュリティの節の後ろに兄弟の枠として並べる（§4.5 (5)・§5・B3）
  - MINOR-G パスキーの口の 401 で更新する（§3・§4.5 (7)・§5）
  - MINOR-H 壊れた userHandle で 500 にしない（F8・§4.4・T5b）
  - F11 の SecuritySection の行番号を実物（:83-136）に直した

- 第4版（2026-10-31）: 第3版 21cbffa6b の審査（reviewer opus・REVISE）を反映
  - MAJOR-1 全部の口を数える既存の試験 2 つに新しい口を載せる（F13・§3・§4.4・§5-4・B10）
  - MAJOR-2 SecuritySection.test.tsx を触るファイルに入れ、api の偽物に get・delete を足す（§3・§5）
  - MINOR-1 api.ts の行番号を実物（:68・:69-77・:78-99・:82）に直し、理由の文を先回りの更新に合わせた（F11・§4.5 (7)）
  - MINOR-2 T5b を本物の parse と `"A"` にした
  - MINOR-3 test_self_auth.py の行番号・F11 の言い過ぎ・Redis の偽物は async・§6 の並びを直した

END OF CARD
