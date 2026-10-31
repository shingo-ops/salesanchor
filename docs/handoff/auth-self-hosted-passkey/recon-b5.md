# 便5（パスキー）実装カードのための現在地

> 何の文書か：ログイン自社化 便5（パスキーの登録・ログイン・一覧・削除）の実装カードを書くために、origin/main の実物を file:line つきで集めた読み取り調査。提案は書かない。
> 調べた基準: origin/main = `5c13bfbef4d343b1f9f6cad8f182a05a59327fb9`（2026-10-31 取得）。行番号はこの時点のもの。
> 参照した決まり: ADR-1013、ADR-1048、`docs/handoff/auth-self-hosted-passkey/design.md`（便5 の行は :159）、`docs/handoff/admin-2fa/design.md`。
> 注記: この実行環境では `./scripts/dev/executor-preflight.sh` が [FAIL]（`api.github.com` へ届かない・`gh` を shingo-cc に切替できない）。読み取り調査と git push だけの作業なので、そのまま進めた。

---

## Q1 webauthn_credentials 表

【事実】作った migration は `migrations/20261013_160000_add_self_hosted_auth_tables.sql` の 1 本だけ。

- `migrations/20261013_160000_add_self_hosted_auth_tables.sql:16-32`
  ```
  CREATE TABLE IF NOT EXISTS public.webauthn_credentials (
      id BIGSERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
      credential_id BYTEA NOT NULL,
      public_key BYTEA NOT NULL,
      sign_count BIGINT NOT NULL DEFAULT 0,
      transports TEXT[] NOT NULL DEFAULT '{}',
      backup_eligible BOOLEAN NOT NULL DEFAULT FALSE,
      backup_state BOOLEAN NOT NULL DEFAULT FALSE,
      aaguid UUID NULL,
      label TEXT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      last_used_at TIMESTAMPTZ NULL,
      CONSTRAINT uq_webauthn_credentials_credential_id UNIQUE (credential_id),
      CONSTRAINT ck_webauthn_credentials_credential_id_len CHECK (octet_length(credential_id) BETWEEN 1 AND 1023),
      CONSTRAINT ck_webauthn_credentials_sign_count CHECK (sign_count >= 0)
  );
  ```
- 全列（型・NULL可否）: `id` BIGSERIAL PK / `user_id` INTEGER NOT NULL FK→`public.users(id)` ON DELETE CASCADE / `credential_id` BYTEA NOT NULL / `public_key` BYTEA NOT NULL / `sign_count` BIGINT NOT NULL 既定 0 / `transports` TEXT[] NOT NULL 既定 `'{}'` / `backup_eligible` BOOLEAN NOT NULL 既定 FALSE / `backup_state` BOOLEAN NOT NULL 既定 FALSE / `aaguid` UUID NULL / `label` TEXT NULL / `created_at` TIMESTAMPTZ NOT NULL 既定 now() / `last_used_at` TIMESTAMPTZ NULL。
- 索引: `:29` UNIQUE 制約 `uq_webauthn_credentials_credential_id (credential_id)`（暗黙の一意索引）／`:33` `CREATE INDEX IF NOT EXISTS ix_webauthn_credentials_user_id ON public.webauthn_credentials (user_id);`
- CHECK: `:30` credential_id の長さ 1〜1023 バイト／`:31` `sign_count >= 0`。
- 外部キー: `:18` のみ（users.id、CASCADE）。
- RLS は付けない: `:3` `-- RLS は付けない: public.users と同じく、テナントが決まる前（ログイン時）に引くため`
- 権限: `:95-101` `salesanchor_app` ロールがあれば `GRANT SELECT, INSERT, UPDATE, DELETE ON public.webauthn_credentials, ...` と `GRANT USAGE, SELECT ON SEQUENCE public.webauthn_credentials_id_seq, ...`（`:98-99`）。
- 同 migration の同居物（参考）: `password_reset_tokens`（:47-）、`auth_refresh_tokens`（:68-、`amr` 列は無い）。

【事実】この表を使う ORM モデル・SQL は py・sql・ts・tsx・sh・yml の各ファイル には 1 件も無い。`backend/app/auth/self_tokens.py:4-5` のコメントのとおり、同系の表は models.py に載せず生 SQL で読み書きする方針。
- 【無い】探した命令: `grep -rIn -i "webauthn_credentials" --include=*.py --include=*.sql --include=*.ts --include=*.tsx --include=*.sh --include=*.yml --include=*.yaml . --exclude-dir=node_modules`（上の migration 以外 0 件）。`grep -rIl -i webauthn --exclude-dir=node_modules --exclude-dir=.git .` の一致は migration 1 本と docs だけ（backend/app・frontend/src のコード 0 件）。
- 参考（根拠）: `backend/app/auth/self_tokens.py:4-5` 「更新用トークンの表 public.auth_refresh_tokens は models.py に載せず、生 SQL で読み書きする（migration-guard チェック1 を避けるため）。」

---

## Q2 backend/app/routers/auth.py

ファイル 601 行。ルーター登録は `backend/app/main.py:242` `app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])`。`auth.py:41` `router = APIRouter()`、`:42` `security = HTTPBearer()`。

### エンドポイント一覧（全 7 本）
| メソッド・パス（/api/v1/auth 配下） | 関数名 | 行（デコレータ／def） |
|---|---|---|
| POST `/register` | `register_user` | :45 / :46 |
| POST `/logout` | `logout` | :158 / :159 |
| POST `/login` | `self_login` | :264 / :265 |
| POST `/refresh` | `self_refresh` | :326 / :327 |
| POST `/password-reset/request` | `password_reset_request` | :388 / :389 |
| POST `/password-reset/confirm` | `password_reset_confirm` | :430 / :431 |
| POST `/password/change` | `password_change` | :510 / :511 |

passkey の口は 【無い】（探した命令: `grep -n "passkey" backend/app/routers/auth.py` → 0 件）。

### login が成功時に呼ぶもの（`self_login`、`backend/app/routers/auth.py:265-323`）
- `:203` `def _require_issuance_enabled() -> None:`（`self_tokens.is_issuance_enabled()` が偽なら 404）
- `:208` `def _require_app_origin(request: Request) -> None:` → `if request.headers.get("origin") != self_tokens.rp_origin(): raise HTTPException(status_code=403, detail="forbidden_origin")`
- `:314-316`
  ```
  raw, expires_at = await self_tokens.issue_refresh_token(
      db, user_row.id, request.headers.get("user-agent")
  )
  ```
  `backend/app/auth/self_tokens.py:156-162` `async def issue_refresh_token(db: AsyncSession, user_id: int, user_agent: str | None, family_id: str | None = None, family_created_at: datetime | None = None) -> tuple[str, datetime]:`
- `:318` `_set_refresh_cookie(response, raw, expires_at)` ／ 定義 `:213` `def _set_refresh_cookie(response: Response, raw: str, expires_at: datetime) -> None:`（`:215-224`）
  ```
  response.set_cookie(
      self_tokens.REFRESH_COOKIE_NAME, raw, httponly=True, secure=self_tokens.cookie_secure(),
      samesite="strict", path=self_tokens.REFRESH_COOKIE_PATH, max_age=max_age,
  )
  ```
- `:319-323` アクセストークン
  ```
  return SelfTokenResponse(
      access_token=self_tokens.create_access_token(user_row.id, user_row.email, "pwd"),
      token_type="bearer",
      expires_in=self_tokens.ACCESS_TOKEN_TTL_SECONDS,
  )
  ```
  `backend/app/auth/self_tokens.py:86` `def create_access_token(user_id: int, email: str, amr: str | None) -> str:`（claims `:88-95`: `iss`・`sub`・`email`・`jti`・`iat`・`exp`、`amr` は `:97` `claims["amr"] = [amr]`、ヘッダ `kid` は `:98`）。
- login 内の他の共通部品: `:226` `_clear_refresh_cookie`、`:236` `_invalid_credentials()`、`:240` `_count_login_failure(db, user_row, ip, now)`（口座ロックと `record_auth_failure(ip)`）。回数制限 `:275` `if await check_auth_rate_limit(ip):`。
- 「トークン発行と Cookie」を 1 関数にまとめた共通関数は 【無い】。login（`:314-323`）と refresh（`:345-356`、`create_access_token(user_id, email, None)` を `:351` で呼ぶ）、password/change（`:587-594`、`issue_refresh_token`＝`:587`・`_set_refresh_cookie`＝`:591`・`create_access_token(..., "pwd")`＝`:594`）にそれぞれ書かれている。探した命令: `grep -n "^def \|^async def " backend/app/routers/auth.py`（関数は上表の 7 本＋`_require_issuance_enabled`・`_require_app_origin`・`_set_refresh_cookie`・`_clear_refresh_cookie`・`_invalid_credentials`・`_count_login_failure`・`_password_reset_allowed` のみ）。
- 設計書の「login と同じ発行処理」の記述: `docs/handoff/auth-self-hosted-passkey/design.md:80`。

### 型・スキーマ（auth.py 内）
- `:186-` `INVALID_CREDENTIALS = "invalid_credentials"`、`class SelfLoginRequest(BaseModel)`（`:192`）、`class SelfTokenResponse(BaseModel)`（`:197`）。

---

## Q3 認証の設定値

定義場所は `backend/app/auth/self_tokens.py`（環境変数は呼び出し時に読む。`:3` 「環境変数は import 時に固定せず、呼び出し時に読む（テストの setenv を効かせるため）。」）。

| 設定 | 定義 | 既定値 |
|---|---|---|
| `AUTH_PROVIDER` | `backend/app/auth/self_tokens.py:37-38` `def auth_provider() -> str:` → `os.getenv("AUTH_PROVIDER", DEFAULT_AUTH_PROVIDER).strip().lower()`。既定 `:20` `DEFAULT_AUTH_PROVIDER = "firebase"  # firebase | self` | `firebase` |
| `AUTH_JWT_SECRET` | `:41-42` `return os.getenv("AUTH_JWT_SECRET", "")`。起動時検査 `:72-83` `validate_settings()`（`self` で空なら RuntimeError、32 文字未満も RuntimeError、`MIN_SECRET_LENGTH = 32`＝`:27`） | 空 |
| `AUTH_JWT_SECRET_PREVIOUS` | `:45-46` | 空 |
| `AUTH_RP_ORIGIN` | `:49-50` `def rp_origin() -> str:` → `os.getenv("AUTH_RP_ORIGIN", DEFAULT_RP_ORIGIN)`。既定 `:21` `DEFAULT_RP_ORIGIN = "https://app.salesanchor.jp"` | `https://app.salesanchor.jp` |
| `AUTH_COOKIE_SECURE` | `:53-54` `def cookie_secure() -> bool:` → `os.getenv("AUTH_COOKIE_SECURE", "true").strip().lower() != "false"` | true（"false" と書いたときだけ偽） |
| 発行の有効化 | `:62-64` `def is_issuance_enabled() -> bool:` → `auth_provider() == "self" and bool(_secret())`（login・refresh・passkey/login を有効にするか。docstring `:63`）／`:67-69` `is_verification_enabled()` = `bool(_secret())` | — |
| Cookie 名・パス | `:25` `REFRESH_COOKIE_NAME = "sa_refresh"`、`:26` `REFRESH_COOKIE_PATH = "/api/v1/auth"` | — |
| 時間 | `:23` `ACCESS_TOKEN_TTL_SECONDS = 900`、`:24` `REFRESH_ABSOLUTE_TTL = timedelta(days=30)`、`:28-29` `LOGIN_FAIL_LIMIT = 10`・`LOGIN_LOCK_DURATION = timedelta(minutes=15)` | — |

【無い】`AUTH_RP_ID`／RP ID の設定: 探した命令 `grep -rn -E "AUTH_RP_ID|RP_ID|rp_id" backend/app docker-compose.yml .github/workflows/deploy.yml .env.example frontend/src` → 0 件。RP の値でコードにあるのは `AUTH_RP_ORIGIN` の 1 つだけ（上表）。設計の指定は `docs/handoff/auth-self-hosted-passkey/design.md:85` 「RP ID = app.salesanchor.jp、確認するオリジン = https://app.salesanchor.jp」。

### docker-compose / deploy.yml で渡している行
- `docker-compose.yml:134-137`（backend サービスの environment）
  ```
  # ADR-1013 便4b: 自社ログインへの切り替え。.env に AUTH_PROVIDER=self が入る。
  # 戻すときは deploy.yml の heredoc を firebase に変える前進 PR（revert はしない）
  - AUTH_PROVIDER=${AUTH_PROVIDER:-firebase}
  - AUTH_JWT_SECRET=${AUTH_JWT_SECRET:-}
  ```
  `docker-compose.yml:139` `- AUTH_VIEWER_JWT_SECRET=${AUTH_VIEWER_JWT_SECRET:-}`（閲覧者用の別鍵）
- `docker-compose.yml:190`（frontend のビルド引数）`VITE_AUTH_PROVIDER: ${VITE_AUTH_PROVIDER:-firebase}`
- `frontend/Dockerfile:11` `ARG VITE_AUTH_PROVIDER`、`:16` `ENV VITE_AUTH_PROVIDER=$VITE_AUTH_PROVIDER`
- `.github/workflows/deploy.yml:318-320`（.env から古い行を消す）`-e '/^AUTH_PROVIDER=/d' \` `-e '/^AUTH_JWT_SECRET=/d' \` `-e '/^VITE_AUTH_PROVIDER=/d' \`
- `.github/workflows/deploy.yml:370-372`（.env へ書く）`AUTH_PROVIDER='self'` / `AUTH_JWT_SECRET='${{ secrets.AUTH_JWT_SECRET }}'` / `VITE_AUTH_PROVIDER='self'`（`:369` 直前は `AUTH_VIEWER_JWT_SECRET='${{ secrets.AUTH_VIEWER_JWT_SECRET }}'`）
- `.env.example:58-62`（`AUTH_PROVIDER=firebase`、`AUTH_JWT_SECRET=`、`VITE_AUTH_PROVIDER=firebase`）
- 【無い】`AUTH_RP_ORIGIN`・`AUTH_COOKIE_SECURE` を compose・deploy.yml・.env.example が渡す行は無い（コード既定値のまま）。探した命令: `grep -rn -E "AUTH_RP_ORIGIN|AUTH_COOKIE_SECURE" docker-compose*.yml .github/workflows .env.example` → 0 件（定義は self_tokens.py のみ、設定の読み替えはテストの monkeypatch だけ: `backend/tests/test_self_auth.py:41-42`）。

---

## Q4 依存

- 【無い】backend: `webauthn`/`py_webauthn` は `backend/requirements.txt`・`backend/requirements-dev.txt`・`backend/pyproject.toml` のどれにも無い。探した命令: `grep -n -i -E "webauthn|simplewebauthn|py_webauthn|passkey" backend/requirements.txt backend/requirements-dev.txt backend/pyproject.toml frontend/package.json frontend/package-lock.json` → 0 件。
- 【無い】frontend: `@simplewebauthn/browser` は `frontend/package.json`・`frontend/package-lock.json` に無い（上の同じ命令）。
- 関連する既存の依存:
  - `backend/requirements.txt:14` `python-jose[cryptography]==3.5.0`
  - `backend/requirements.txt:24` `cryptography==48.0.1`
  - `backend/requirements.txt:50` `argon2-cffi==25.1.0`
  - `backend/requirements.txt:16` `redis[hiredis]>=5.0.0`
  - `frontend/package.json:81` `"firebase": "^11.0.0"`、`:84` `"react": "^18.3.1"`
- 設計側が書いている版の指定: `docs/handoff/admin-2fa/design.md:142` 「py_webauthn 2.8.0・@simplewebauthn/browser 14.0.0 は ADR-1013 便5（パスキー）で足す。py_webauthn 3.x は cryptography>=49 が要り、今の 48.0.1（backend/requirements.txt:24）と両立しないため 2.8.0 にする。依存の引き上げは別件。」
- 便5 の行: `docs/handoff/auth-self-hosted-passkey/design.md:159` 「依存追加 `webauthn`（py_webauthn）・`@simplewebauthn/browser`。ボタンは端末がパスキーに対応しているときだけ表示（環境変数のスイッチは作らない＝compose・deploy を触らない）」

---

## Q5 自社ログインの画面側

- ログイン画面: `frontend/src/pages/login/LoginPage.tsx`（169 行）。
  - `:8` `import { isSelfAuth } from "../../lib/auth/provider";`
  - `:14` `type Mode = "signIn" | "reset";`
  - `:17-19` `function loginErrorMessage(...) { return isSelfAuth() ? authErrorMessage(err, t, context) : firebaseErrorMessage(err, t); }`
  - `:29` `const { signIn, sendPasswordReset, user, loading: authLoading } = useAuth();`
  - `:48` `await signIn(email, password);` ／ `:49-50` `navigate(from, { replace: true });`
  - 使っている部品 `:9-12` `Button`・`TextFieldControl`・`PasswordFieldControl`・`TextLink`
  - テスト `frontend/src/pages/login/LoginPage.test.tsx`
- `VITE_AUTH_PROVIDER` を読む箇所（唯一）: `frontend/src/lib/auth/provider.ts:15` `return resolveAuthProvider(import.meta.env.VITE_AUTH_PROVIDER);`。判定関数 `:19-21` `export function isSelfAuth(): boolean { return getAuthProvider() === "self" && !import.meta.env.DEV; }`（`:5` 「ビルド変数を読むのはこのファイルだけ。」）。`isSelfAuth` を使う箇所: `contexts/AuthContext.tsx:16,56`、`lib/auth/selfAuth.ts:10,162,174`、`lib/api.ts:28,80`、`pages/account-settings/SecuritySection.tsx:11,34`、`pages/login/LoginPage.tsx:8,18`。
- ログイン API を呼ぶ箇所:
  - `frontend/src/lib/auth/selfAuth.ts:88-101` `async function postAuth<T>(path: string, body?: unknown): Promise<T>`（`AUTH_BASE = "/api/v1/auth"`＝`:12`、`credentials: "same-origin"`＝`:92`、失敗は `SelfAuthError(res.status, detail)`＝`:98`）
  - `:103-106` `export async function selfLogin(email: string, password: string): Promise<void> { const res = await postAuth<TokenResponse>("/login", { email, password }); adoptAccessToken(res.access_token, res.expires_in); }`
  - 呼び出し元 `frontend/src/contexts/AuthContext.tsx:124-130` `const signIn = async (email, password) => { if (selfMode) { await selfLogin(email, password); return; } await signInWithEmailAndPassword(auth, email, password); };`（型 `:38` `signIn: (email: string, password: string) => Promise<void>;`）
- トークン・refresh を扱う箇所（すべて `frontend/src/lib/auth/selfAuth.ts`）:
  - `:30-33` `interface Session { accessToken: string; expiresAt: number; }`（`:40` `let session: Session | null = null;`、メモリのみ。`:4` 「アクセストークンは画面のメモリだけに置く」）
  - `:49` `subscribeSession(listener)`、`:57` `currentAccessToken()`、`:61-64` `adoptAccessToken(accessToken, expiresInSeconds)`、`:67` `expireSession()`、`:74` `readClaims(token)`
  - `:108-131` `refreshOnce()`（`navigator.locks` の `sa-auth-refresh`＝`:13`）、`:134` `selfRefresh()`、`:144` `ensureSelfToken()`、`:161` `getAccessToken()`、`:173` `hasSession()`
  - `:149-155` `selfRequestPasswordReset`・`selfConfirmPasswordReset`
  - `frontend/src/lib/api.ts:29` `import { expireSession, getAccessToken, selfRefresh } from "./auth/selfAuth";`、`:67-90` 401 の再試行（`fetchWithReauth`、`:80` `if (res.status !== 401 || !isSelfAuth()) return res;`、`:83-85` `/auth/` で始まる口は refresh しない）
  - `frontend/src/contexts/AuthContext.tsx:98-122`（起動時 `selfRefresh()` と `subscribeSession`）、`:132-140` サインアウト（`api.post("/auth/logout", {})` → `expireSession()`）
  - テスト `frontend/src/lib/auth/selfAuth.test.ts`・`frontend/src/lib/auth/apiReauth.test.ts`・`frontend/src/lib/auth/provider.test.ts`・`frontend/src/lib/auth/authErrorMessage.test.ts`
- パスキー関連の画面コードは 【無い】。探した命令: `grep -rln -i "passkey\|webauthn" frontend/src` → 0 件（`frontend/e2e` にも auth/login 名のファイル無し: `ls frontend/e2e | grep -i -E "auth|login"`）。

---

## Q6 利用者が自分の設定を見る画面

- ページ: `frontend/src/pages/account-settings/AccountSettingsPage.tsx`（`:3` `import SecuritySection from "./SecuritySection";`、`:11-13` `<ProfileSection />` `<PreferencesSection />` `<SecuritySection />`）。同ディレクトリ: `frontend/src/pages/account-settings/ProfileSection.tsx`・`frontend/src/pages/account-settings/PreferencesSection.tsx`・`frontend/src/pages/account-settings/SecuritySection.tsx`・`frontend/src/pages/account-settings/SecuritySection.test.tsx`・`frontend/src/pages/account-settings/ProfileSectionAvatar.test.tsx`・`frontend/src/pages/account-settings/AccountSettings.stories.tsx`・`account-settings.css`。
- パスワード変更の画面: `frontend/src/pages/account-settings/SecuritySection.tsx`（138 行）。
  - 自社ログインのとき `:41-56` `api.post<{ access_token?: string | null; expires_in?: number | null }>("/auth/password/change", { current_password: form.current, new_password: form.next })` → `:48` `adoptAccessToken(...)`、エラー `:53` `authErrorMessage(err, t, "passwordChange")`
  - 見出し `:85-89` `<section className="account-settings-section"> <div className="account-settings-section-title"> <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" /> {t("accountSettings.sectionSecurity")}`
  - 使っている部品（import）: `Button`（`components/Button`、`:16`）、`TextFieldControl`（`components/TextField`、`:17`）、`ACCOUNT_ICONS`（`constants/icons`）、`ICON`（`constants/iconSizes`）、`api`（`lib/api`）、`adoptAccessToken`（`lib/auth/selfAuth`）
  - フォーム部分は素の `<form>`・`<div className="form-group">`・`<label htmlFor=...>`（`:92,104,116`）。パスキーの一覧・追加・削除の UI は 【無い】（探した命令: `grep -n -i "passkey" frontend/src/pages/account-settings/SecuritySection.tsx` → 0 件）。
  - プロフィール: `frontend/src/pages/account-settings/ProfileSection.tsx`。
- 設計書が便5 に指定している金型: `docs/handoff/auth-self-hosted-passkey/design.md:128` 「アカウント設定 セキュリティ（`frontend/src/pages/account-settings/SecuritySection.tsx`）｜パスワード変更を自社 API に。パスキー一覧（名前・登録日・最後に使った日）・追加・削除｜`Button`・`TextFieldControl`・`DataTable`（`frontend/src/components/DataTable.tsx`）・`ConfirmModal`（削除確認）」
- 一覧に使える DataTable 金型: `frontend/src/components/DataTable.tsx`（`:147` `export function DataTable<T = Record<string, unknown>>({ columns, ...`）。関連ファイル: `DataTable.css`・`frontend/src/components/DataTable.stories.tsx`・`frontend/src/components/DataTable.test.tsx`・`frontend/src/components/DataTable.bin1.test.tsx`。
  - 列定義 `:39` `export interface DataTableColumn<T = Record<string, unknown>> {`（`key: string`・`header: string`・`width?`・`ellipsis?`・`sortable?`・`align?`・`stickyLeft?`・`renderCell` は `:5` のコメント「columns : 型付き列定義（key / header / width / sortable / renderCell）」）
  - Props `:74-77` `export interface DataTableProps<T> { columns: DataTableColumn<T>[]; data: T[]; rowKey: (row: T) => string;`
  - `:22` 「セル内に日本語ラベルを埋め込まない（columns.header / emptyState を通じて渡す）。」
- 削除確認の金型: `frontend/src/components/ConfirmModal.tsx`（`:21` `export default function ConfirmModal({`。Props `:6-18` `open`・`title`・`message`・`confirmLabel?`・`cancelLabel?`・`danger?`・`confirmDisabled?`・`confirmLoading?`・`onConfirm`・`onCancel`）。
- 同ディレクトリの他の金型（名前だけ）: `Button`・`TextField`（`TextFieldControl`）・`PasswordField`（`PasswordFieldControl`）・`TextLink`・`Card`・`Modal`・`Badge`・`EmptyState`・`ChoiceCardGroup`・`HoverCard`（`ls frontend/src/components | grep -i ...` の結果）。

---

## Q7 i18n（auth 系キー）

置き場: `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（2 ファイルの行番号は同じ。読み込みは `frontend/src/i18n.ts:15` `import ja from "./locales/ja.json";`）。viewer 用は別ファイル `frontend/src/locales/viewer/ja.json`（今回の対象外）。

| トップキー | 行 | 中のキー（接頭辞） |
|---|---|---|
| `login` | `frontend/src/locales/ja.json:674-683`（en も :674-683） | `login.email`・`login.password`・`login.signIn`・`login.forgotPassword`・`login.resetPassword`・`login.sendResetEmail`・`login.resetEmailSent`・`login.backToLogin` |
| `authError` | `:684-696` | `authError.invalidCredentials`・`forbiddenOrigin`・`unavailable`・`tooManyAttempts`・`resetLinkInvalid`・`currentPasswordWrong`・`passwordTooShort`・`passwordTooLong`・`passwordTooCommon`・`validation`・`default` |
| `resetPasswordPage` | `:697-` | `subtitle`・`title`・`newPassword` ほか（パスワード再設定画面） |
| `accountSettings` | `:3182-`（`sectionSecurity` は `:3185`、`currentPassword` は `:3196`、`passwordChanged` は `:3201`） | `accountSettings.subtitle`・`sectionProfile`・`sectionSecurity`・`changePassword`・`currentPassword`・`newPassword`・`confirmPassword`・`passwordMismatch`・`passwordTooShort`・`passwordChanged`・`sectionPreferences`・`avatar*` 等 |

- `frontend/src/locales/ja.json:422` にも `"sectionSecurity": "権限・セキュリティ"` がある（別の画面のキー。`accountSettings.sectionSecurity` とは別）。
- 識別子→文言の変換: `frontend/src/lib/auth/authErrorMessage.ts`（`login` と `SecuritySection` が呼ぶ。文脈引数は `AuthErrorContext`、`frontend/src/pages/login/LoginPage.tsx:7` で import）。
- 【無い】`passkey` 系のキー: 探した命令 `grep -n -i "passkey\|webauthn" frontend/src/locales/ja.json frontend/src/locales/en.json` → 0 件。

---

## Q8 auth のテスト

### backend/tests のファイル（`ls backend/tests | grep -i -E "auth|login|self_|token|password|refresh|passkey"` の結果）
`backend/tests/test_discord_oauth.py`・`backend/tests/test_discord_oauth_rls.py`・`backend/tests/test_google_drive_oauth.py`・`backend/tests/test_issue_initial_passwords.py`・`backend/tests/test_meta_inbox_auth.py`・`backend/tests/test_meta_oauth_endpoints.py`・`backend/tests/test_meta_oauth_scope.py`・`backend/tests/test_oauth_state.py`・`backend/tests/test_oauth_state_extra.py`・`backend/tests/test_password_gen.py`・`backend/tests/test_password_policy.py`・`backend/tests/test_password_reset.py`（342 行）・`backend/tests/test_paypal_regtoken_rls.py`・`backend/tests/test_refresh_meta_tokens.py`・`backend/tests/test_registration_token_schema.py`・`backend/tests/test_self_auth.py`（625 行）・`backend/tests/test_smoke_auth_least_privilege.py`・`backend/tests/test_viewer_password.py`・`backend/tests/test_viewer_tokens.py`。自社ログイン本体は `backend/tests/test_self_auth.py`（`self_login` を叩くのは他に `backend/tests/test_users_rls.py`・`backend/tests/test_viewer_isolation.py`）。passkey のテストは 【無い】（`ls backend/tests | grep -i passkey` → 0 件）。

### 代表: login の Cookie・トークンの確かめ方
`backend/tests/test_self_auth.py:125` `async def test_login_success_returns_token_and_cookie(http, db_session, password_hash):`
- `:128` `resp = await _login(http)` → `:130` `assert resp.status_code == 200`
- `:131-133` `body["token_type"] == "bearer"`、`body["expires_in"] == 900`
- `:134-135`
  ```
  claims = jwt.get_unverified_claims(body["access_token"])
  assert claims["iss"] == "salesanchor" and claims["sub"] == str(USER_ID) and claims["amr"] == ["pwd"]
  ```
- `:136-141` Cookie: `cookie = resp.headers["set-cookie"].lower()` → `assert "sa_refresh=" in cookie` / `"httponly" in cookie` / `"samesite=strict" in cookie` / `"path=/api/v1/auth" in cookie`
- `:142-144` DB: `last_login is not None`、`failed_login_count == 0`

### 同ファイルの土台（passkey 試験が真似る対象）
- `:36-43` `self_auth_env`（autouse。`AUTH_PROVIDER=self`、`AUTH_JWT_SECRET=SECRET`、`AUTH_RP_ORIGIN`・`AUTH_COOKIE_SECURE` は `delenv`）
- `:45-50` `no_redis`（autouse。`app.routers.auth.check_auth_rate_limit`・`record_auth_failure`・`blacklist_token` を差し替え）
- `:58` `_insert_user`、`:70-77` `cleanup_self_auth`（`auth_refresh_tokens` と `id >= 2000` の users を消す）、`:80-92` `http` フィクスチャ（`base_url="https://app.salesanchor.jp"`、`get_db` を `db_session` に差し替え）、`:95` `_login`（`origin` ヘッダ付き）
- 関連: `:184` `test_login_and_refresh_404_when_provider_firebase`、`:191` `test_login_and_refresh_403_when_origin_wrong_or_missing`、`:218` `test_refresh_rotates_and_old_cookie_is_rejected`、`:303` `test_logout_revokes_refresh_and_clears_cookie`、`:525` `test_password_change_success_issues_new_token_and_revokes_old_refresh`
- 画面側のテスト: `frontend/src/lib/auth/selfAuth.test.ts`・`frontend/src/lib/auth/apiReauth.test.ts`・`frontend/src/lib/auth/provider.test.ts`・`frontend/src/lib/auth/authErrorMessage.test.ts`、`frontend/src/pages/login/LoginPage.test.tsx`、`frontend/src/pages/account-settings/SecuritySection.test.tsx`。
- 設計書の守り手の記述: `docs/handoff/auth-self-hosted-passkey/design.md:242` 「ログインの安全に関わる検査は、便2・便5 で作るテストが守る。ファイルはまだ無いため、各便のカードで、テストのパスをこの欄に追記する」、受け入れ `:202` 「パスキー: 新値が保存値以下（保存値 > 0）の sign_count は拒否、challenge は 1 回で消える｜単体テスト（審査 MEDIUM-3）」。

---

## Q9 nginx

`nginx/nginx.conf`。app.salesanchor.jp の 443 サーバーは `:69-` （`:73` `server_name app.salesanchor.jp;`）、api.salesanchor.jp の 443 サーバーは `:333-` （`:337` `server_name api.salesanchor.jp;`）。

### /api/v1/auth/ の回数制限
- 帯の定義 `:5-6` `# ログインAPI: 1分間に10リクエストまで（ブルートフォース攻撃防止）` ／ `limit_req_zone $binary_remote_addr zone=login:10m rate=10r/m;`
- app.salesanchor.jp 側 `:144-146` `location /api/v1/auth/ {` ／ `limit_req zone=login burst=5 nodelay;` ／ `limit_req_status 429;`
- api.salesanchor.jp 側 `:406-408` 同じ 3 行（`location /api/v1/auth/ {` ／ `limit_req zone=login burst=5 nodelay;` ／ `limit_req_status 429;`）
- 閲覧者用の別の口（参考）: `:98-101`・`:115-116`・`:130-131`・`:362-363`・`:377-378`・`:392-393` も `zone=login burst=5 nodelay`（`:98` コメント「ADR-1019 段4a-1: 閲覧ページの login・パスワード再発行は auth と同じ厳しい回数制限（完全一致）」）。
- passkey 専用の `location` や別の帯は 【無い】（探した命令: `grep -n -i "passkey" nginx/nginx.conf` → 0 件。`/api/v1/auth/passkey/...` も上の `location /api/v1/auth/` に入る）。

### Content-Security-Policy・Permissions-Policy
- app.salesanchor.jp（`:69-` のサーバー内）
  - `:84` `add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://www.gstatic.com; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:" always;`
  - `:85` `add_header X-Frame-Options "DENY" always;`
  - `:88` `add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;`
- api.salesanchor.jp（`:333-` のサーバー内）: `:349` `add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;`、`:350` `X-Frame-Options "DENY"`。Permissions-Policy の行は 【無い】（探した命令: `grep -n "Permissions-Policy" nginx/nginx.conf` → `:88` と `:248` の 2 行だけ。`:248` は monitor.salesanchor.jp 側のサーバー）。
- monitor.salesanchor.jp（`:569-` のサーバー内）: `:245` に Grafana 用 CSP（`'unsafe-eval'` を含む）、`:248` `Permissions-Policy "camera=(), microphone=(), geolocation=()"`（今回の対象外）。
- 【無い】`publickey-credentials-get`／`publickey-credentials-create` の指定は nginx にも他のコードにも無い。探した命令: `grep -rn "publickey-credentials" --include=*.conf --include=*.py --include=*.ts --include=*.js --include=*.mjs --include=*.html --include=*.yml . --exclude-dir=node_modules --exclude-dir=docs --exclude-dir=.git` → 0 件。`frontend` 側に `<meta http-equiv="Content-Security-Policy">` 等も無く、CSP・Permissions-Policy を出すのは `nginx/nginx.conf` だけ（`grep -rn "Content-Security-Policy\|Permissions-Policy" ... -l` の一致は `nginx/nginx.conf` 1 ファイル）。

---

## Q10 admin-2fa/design.md が便5 に求める前提（便7a〜7d が使う、パスキーの表・関数・画面の名前）

`docs/handoff/admin-2fa/design.md`（218 行）の「便5」「パスキー」「webauthn」の出てくる箇所:

1. 表の名前: `:30` K1 の測り方 「管理者（§3-1 の判定）のうち、webauthn_credentials 0件かつ user_totp の確認済み行なしの人数」。→ 使う表は `public.webauthn_credentials`（Q1 の既存表）。列名の指定は 【無い】（`grep -n "webauthn_credentials" docs/handoff/admin-2fa/design.md` は :30 の 1 件だけ）。
2. 口の名前・経路:
   - `:69` 「4. パスキー: ADR-1013 便5 の login/verify（docs/handoff/auth-self-hosted-passkey/design.md:80「login と同じ発行処理」）」。トークンを出す 5 つの口（`:66-70`: login／6桁／承認待ち／パスキー／refresh）は「必ず全部が同じ関数を通る」（`:66`）。
   - `:109` 「パスキーの口（`/api/v1/auth/passkey/...`）には、いつもの機器の cookie（path `/api/v1/auth/2fa`）が届かない。そのため、パスキーの口では機器を登録しない。パスキーで入った後、画面が2段階の口の「この機器を登録」（`POST /api/v1/auth/2fa/devices/current`）を1回呼ぶ。…受け付けるのは amr=webauthn の全権トークンだけ」。
   - `:77` 「パスキーの登録の口（ADR-1013 便5、`/api/v1/auth/passkey/...`）は一覧に入れない。設定だけのトークンで設定できるのは6桁が先で、パスキーは6桁で全権を受け取った後に足す（便5 の設計がまだ確かめられていないため。…）」（scope=enroll のとき許す口の一覧に、パスキー登録の口は含めない）。
3. トークン・ログ：
   - `:57` 表 「パスキー（指紋・顔）｜全権。amr=["webauthn"]。機器を問わない」
   - `:81` ログ行 `admin_token_issued user_id=<id> scope=<full|enroll> amr=<webauthn|pwd+otp|pwd> device=<known|new|-> via=<login|otp|approval|passkey|refresh> request_id=...`。`:82` 「device は、6桁の口と承認待ちの口でだけ known か new を書く。パスキーと refresh とパスワードだけの口は `-`。」
   - `:61` 「パスキーだけを設定済み（user_totp の確認済み行が無い）なら券は作らず、「パスキーで入ってください」と返す」
   - `:127` 「パスキーが同期型（iCloud キーチェーンなど）なら、新しい機器でパスキーを使えば入れる（承認は要らない）」
4. 書き込み順の前提（便5 側で決まるとされているもの）: `:50` 「判定は、その口の書き込み（6桁の `last_used_timecode` の更新、券の削除、refresh の組の入れ替え `rotate_refresh_token`＝self_tokens.py:195-236、承認依頼の消費、パスキーの使用回数の更新＝便5 の設計で決まる）より前に行う。」
5. 画面の名前: 設計書 §3-7（`:131-138`）にパスキー専用の画面名・部品名は 【無い】（探した命令: `sed -n 131,138p` で確認。部品は `TextFieldControl`・`QrCode`（新設予定）・`Modal`・`Button`・`Card`・`LoadingBlock`・`Callout` のみ）。
6. 依存の版: `:142`（Q4 に既出）py_webauthn 2.8.0・@simplewebauthn/browser 14.0.0 を便5 で足す。
7. 便の順番: `:162` 「ADR-1013 の便3（メール・PO の画面作業）→ 便4（切替）→ 便5（パスキー）の後に置く。」便7 の表（`:164-169`）: 7a＝migration（`user_totp`・`user_trusted_devices`・`auth_refresh_tokens.amr`）／7b＝backend／7c＝frontend／7d＝切替。
8. `refresh` 側: `:71` 「パスキーの組を refresh しても全権が続く」前提は refresh の組に `amr TEXT[]` を足す 7a に依存（今の表に amr 列は無い: Q1）。`:215` 試験項目に 「パスキーで入った後の機器の登録を2回呼んでも行は1つ、pwd＋otp のトークンでは登録できない」「パスキーだけの管理者がパスワードで入ると券は作られずパスキーへ案内される」「パスキーの組を refresh しても全権が続く」。
9. 対象外: `:158` 「パスキーそのものの実装（ADR-1013 便5）」は admin-2fa の範囲外。

便7 側が名前で指定している「関数」は、上記のとおり login/verify の口（`/api/v1/auth/passkey/...`）と、発行の共通関数（名前は未定義。`:66` 「共通の関数1つ」）。パスキー専用の関数名・画面名の指定は 【無い】。

---

## 補足（便5 の設計書 design.md の記述、原文）

- `docs/handoff/auth-self-hosted-passkey/design.md:79` 「POST `passkey/register/options`・`passkey/register/verify`｜ログイン中｜py_webauthn で登録。`userVerification=required`、`residentKey=required`。user handle（`user.id`）は users.id を 8 バイトの固定長にしたもの（メール等の個人情報は入れない）」
- `:80` 「POST `passkey/login/options`・`passkey/login/verify`｜なし（端末が候補を出す）｜options は challenge と、それを引くための使い捨て ID を返す（challenge は Redis に 5 分・1 回限り、鍵はその ID）。verify は ID で challenge を取り出して消し、`userVerification=required` で照合。成功でアクセストークン＋更新用 Cookie（login と同じ発行処理）｜`sign_count`: 保存値と新値がどちらも 0 なら許可（同期型パスキーは 0 のまま）。保存値が 0 より大きく、新値が保存値以下なら拒否し、監査記録に残す（複製の疑い）」
- `:81` 「GET/DELETE `passkeys`｜ログイン中｜自分のパスキーの一覧・削除｜他人のものは触れない」
- `:103` 「無効にする「発行経路」は、`login`・`refresh`・`passkey/login/*` の 3 系統だけ」
- `:159` 便5 の行（Q4 に既出）。「無（migration は便1 で済。compose・deploy も触らない）」「revert」「K2: PO の端末で顔か指紋だけでログイン（画面録画）・`webauthn_credentials` に 1 行」
