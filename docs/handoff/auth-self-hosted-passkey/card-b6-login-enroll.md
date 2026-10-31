# 実装カード 便6 — ログイン直後のパスキー登録（自動作成＋案内＋スキップの記録）

> この文書は何か：パスワードでログインした直後に、パスキーを裏で自動で用意する。できない端末では SA の画面で登録を案内し、「今はスキップ」を 6 か月で 3 回押した人には出さない。その実装の指示書です。

- 設計: docs/handoff/auth-self-hosted-passkey/design-login-enroll.md（調べ書きは docs/handoff/auth-self-hosted-passkey/recon-login-enroll.md）
- 対象ADR: ADR-1013
- 状態: 設計は Opus 自己審査 APPROVE（design-login-enroll.md §11）。PO の決定 2026-10-31「1」（案A）・「1」（6 か月で 3 回）と、PO 指示「PRマージ、デプロイまで完走させてくれ」に基づく実装便
- 危険便: はい（`migrations/` と `scripts/run_all_migrations.sh` を含む）。マージ前にバックアップ確認と GO 記録を Opus が行う。担当はマージしない
- 担当: 実装 Sonnet（クラウド）／コード審査 Opus 審査役／PR 作成・マージ・反映確認 Opus

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 出力に上限・報告に無い出力を成功と扱わない | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/05-pr.md | PR は Opus が作る。担当は commit と push まで。各段で git log で実在を確かめる | ○（§5・§8） |
| guards/07-migration.md | 採番は直近を実測。`scripts/run_all_migrations.sh` の末尾に `run_sql` を登録 | ○（§4-2） |
| guards/10-executor.md | 散文で組み立てを頼まない。形と期待値を書く | ○（§4） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 便6 ログイン直後のパスキー登録 の実行結果である」と書くこと。

## 1. 範囲

入れる: 下の §3 のファイルへの §4 の変更だけ。
入れない: パスキーでのログインの決まり（`passkey_login_*`）・設定画面 `PasskeySection.tsx` の動き・閲覧ページ（viewer）・Firebase・ADR-1048・文言以外の画面の見た目の変更・リファクタ。

## 2. 前提の事実（2026-10-31・origin/main 8c6f52813 基準）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 合図の `amr` は配列。パスワードのログインとパスワード変更で `["pwd"]`、パスキーで `["webauthn"]`、更新で無し。有効期間 900 秒 | `backend/app/auth/self_tokens.py:24`・`:92-104`、`backend/app/routers/auth.py:360`・`:391`・`:633`・`:882` |
| F2 | 登録 options の口は本文を受けない。challenge は kind `reg` で保存 | `backend/app/routers/auth.py:688-710` |
| F3 | challenge の鍵は kind・本人・id の組。取り出すと消える | `backend/app/auth/passkeys.py:42-60` |
| F4 | 登録 verify は `take_challenge("reg", ...)` と `require_user_verification=True` | `backend/app/routers/auth.py:713-734` |
| F5 | py_webauthn 2.8.0 の `verify_registration_response` は `require_user_presence`（既定 True）と `require_user_verification`（既定 False）を受ける | 公式 https://raw.githubusercontent.com/duo-labs/py_webauthn/v2.8.0/webauthn/registration/verify_registration_response.py |
| F6 | @simplewebauthn/browser 14.0.0 の `startRegistration` は `useAutoRegister: true` で `mediation: "conditional"` を付ける | 公式配布物 https://unpkg.com/@simplewebauthn/browser@14.0.0/esm/methods/startRegistration.js |
| F7 | ログイン画面のパスワードの成功は `handleSignIn` の `await signIn(email, password)` の直後だけ | `frontend/src/pages/login/LoginPage.tsx:45-59` |
| F8 | パスキーの表の migration の形（RLS なし・DO ブロックで GRANT） | `migrations/20261013_160000_add_self_hosted_auth_tables.sql:16-33`・`:96-101` |
| F9 | 試験用 SQLite 版の表と `public.` の置換 | `backend/tests/conftest.py:324-325`・`:1366-` |
| F10 | `scripts/run_all_migrations.sh` の最後の `run_sql` は `migrations/20261024_100100_create_ai_reader_cloud_role.sql` | 同ファイルの末尾 |

## 3. 触るファイル（これ以外は触らない）

- `backend/app/auth/passkeys.py`
- `backend/app/routers/auth.py`
- `migrations/20261031_200000_add_passkey_enroll_prompt_skips.sql`（新設。採番前に `ls migrations` の末尾 3 件を貼り、これより新しいものが無いことを確かめる。あれば止まって `NEEDS_DECISION:`）
- `scripts/run_all_migrations.sh`
- `backend/tests/conftest.py`
- `backend/tests/test_passkey_login_enroll.py`（新設）
- `backend/tests/test_rls_passkey_enroll_skips.py`（新設・PostgreSQL 専用）
- `frontend/src/lib/auth/passkey.ts`
- `frontend/src/lib/auth/passkey.test.ts`
- `frontend/src/pages/login/LoginPage.tsx`
- `frontend/src/pages/login/LoginPage.test.tsx`
- `frontend/src/locales/ja.json`
- `frontend/src/locales/en.json`
- `frontend/api-contract/openapi.json`（審査で書き漏れが分かり追加。作り直しは `docs/handoff/auth-self-hosted-passkey/card-b6-fix.md`）

## 4. 作り方

### 4-1. passkeys.py

- 定数を足す: `FRESH_LOGIN_SECONDS = 300`・`PROMPT_SKIP_WINDOW_DAYS = 180`・`PROMPT_SKIP_LIMIT = 3`
- `store_challenge` の説明文の「kind は reg か login」を「kind は reg・reg_auto・login」に直す

### 4-2. migration と登録

`migrations/20261031_200000_add_passkey_enroll_prompt_skips.sql`:

```sql
-- ADR-1013 便6: ログイン直後のパスキー登録の案内で「今はスキップ」を押した記録（冪等）
-- RLS なし: public.webauthn_credentials と同じく、テナントが決まる前に引くため
CREATE TABLE IF NOT EXISTS public.passkey_enroll_prompt_skips (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    skipped_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_passkey_enroll_prompt_skips_user_at
    ON public.passkey_enroll_prompt_skips (user_id, skipped_at);
COMMENT ON TABLE public.passkey_enroll_prompt_skips IS 'ログイン直後のパスキー登録の案内で「今はスキップ」を押した記録。直近 180 日で 3 回あれば案内を出さない';
COMMENT ON COLUMN public.passkey_enroll_prompt_skips.user_id IS 'スキップした人';
COMMENT ON COLUMN public.passkey_enroll_prompt_skips.skipped_at IS 'スキップした時刻';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT ON public.passkey_enroll_prompt_skips TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.passkey_enroll_prompt_skips_id_seq TO salesanchor_app;
    END IF;
END $$;
```

`scripts/run_all_migrations.sh` の最後の `run_sql` 行の次に 2 行足す:

```bash
# ADR-1013 便6: ログイン直後のパスキー登録の案内のスキップ記録（空の表を作るだけ・冪等）
run_sql migrations/20261031_200000_add_passkey_enroll_prompt_skips.sql
```

### 4-3. auth.py

(1) 判定の関数（`passkey_register_options` の直前）:

```python
def _is_fresh_password_login(request: Request, user: User) -> bool:
    """パスワードを打って FRESH_LOGIN_SECONDS 以内の合図か（便6 の自動作成と案内だけに使う）。"""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return False
    token = header[7:].strip()
    if self_tokens.peek_issuer(token) != self_tokens.ISSUER:
        return False
    try:
        claims = self_tokens.decode_access_token(token)
        issued_at = int(claims["iat"])
    except (JWTError, ValueError, KeyError, TypeError):
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    return (
        claims.get("sub") == str(user.id)
        and claims.get("amr") == ["pwd"]
        and 0 <= now - issued_at <= passkeys.FRESH_LOGIN_SECONDS
    )
```

`JWTError`・`self_tokens.ISSUER` の import が auth.py に無ければ足す（既存の import 元に合わせる）。

(2) 本人のパスキー数と直近のスキップ数を返す小関数 `_passkey_count(db, user_id)`・`_recent_prompt_skips(db, user_id)` を足す。スキップ数は `SELECT count(*) FROM public.passkey_enroll_prompt_skips WHERE user_id = :uid AND skipped_at > :since`（`since = now - timedelta(days=passkeys.PROMPT_SKIP_WINDOW_DAYS)`）。

(3) `GET /passkey/prompt`（`response_model=PasskeyPromptStatus`、`BaseModel` で `can_auto: bool`・`show_prompt: bool`）。依存は `passkey_register_options` と同じ（`get_current_user`・`get_db`・先頭で `_require_app_origin(request)`）。
- `fresh` が偽なら両方 false を返す（DB を引かない）
- `can_auto = count < passkeys.MAX_PASSKEYS_PER_USER`
- `show_prompt = count == 0 and skips < passkeys.PROMPT_SKIP_LIMIT`

(4) `POST /passkey/prompt/skip`（`status_code=204`）。`fresh` が偽なら `HTTPException(403, "auto_not_allowed")`。真なら `INSERT INTO public.passkey_enroll_prompt_skips (user_id) VALUES (:uid)` → commit。監査記録は付けない。

(5) `passkey_register_options` に本文を足す: `class PasskeyRegisterOptionsRequest(BaseModel): auto: bool = False`、引数 `data: PasskeyRegisterOptionsRequest | None = None`。`auto = bool(data and data.auto)`。`auto` かつ `fresh` が偽なら 403 `auto_not_allowed`（上限の確認より前）。`store_challenge("reg_auto" if auto else "reg", ...)`。ほかは変えない。

(6) `passkey_register_verify`: `take_challenge("reg", ...)` が None なら `take_challenge("reg_auto", ...)` を試し、`auto = True`。両方 None なら今の 400 `challenge_expired`。`verify_registration_response` は、`auto` のとき `require_user_presence=False, require_user_verification=False`、でなければ今のまま `require_user_verification=True`。監査記録の `new_data` を `{"event": "passkey_registered", "auto": auto}` にする（`_record_auth_audit` 経由のまま）。ほかは変えない。

### 4-4. 試験（backend）

`backend/tests/conftest.py`: SQLite 版 `passkey_enroll_prompt_skips`（id INTEGER PRIMARY KEY AUTOINCREMENT・user_id INTEGER NOT NULL・skipped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP）を `webauthn_credentials` の隣に足し、`:324-325` の置換に `public.passkey_enroll_prompt_skips` を足す。

`backend/tests/test_passkey_login_enroll.py`（既存 `backend/tests/test_passkeys.py` の作りに合わせる）。合図は `self_tokens.create_access_token(user_id, email, amr)` で作り、`iat` の古さは時刻の差し替えで作る:
- T1 `amr="pwd"` の直後: `GET /passkey/prompt` が `can_auto=true`・`show_prompt=true`
- T2 `amr=None`（更新）・`amr="webauthn"`・301 秒前の `pwd`: どれも両方 false。`POST /passkey/register/options {"auto": true}` と `POST /passkey/prompt/skip` が 403 `auto_not_allowed`
- T3 `{"auto": false}` と本文なしの options は今のまま 200（kind `reg`）
- T4 スキップ 2 回で `show_prompt=true`、3 回目で false。181 日前の 3 行は数えない（`show_prompt=true`）
- T5 パスキーを 1 個持つ人は `show_prompt=false`・`can_auto=true`。10 個なら `can_auto=false`
- T6 verify: `reg_auto` の challenge のとき `verify_registration_response` が `require_user_presence=False, require_user_verification=False` で呼ばれ、`reg` のときは `require_user_verification=True` で呼ばれる（`unittest.mock.patch` で呼び出し引数を確かめる）。監査記録の `new_data["auto"]` がそれぞれ true / false
- T7 `reg` の challenge id を `reg_auto` として取り違えない（他人の challenge では 400）

`backend/tests/test_rls_passkey_enroll_skips.py`（手本 `backend/tests/test_rls_auth_audit.py`。`RLS_TEST_DATABASE_URL` が無ければ skip）:
- 管理者接続で migration ファイルを流し、2 回目も失敗しない（冪等）
- アプリ接続（`salesanchor_app`）で INSERT と count の SELECT が通る
- 後始末で表を DROP する（管理者接続）

### 4-5. passkey.ts

足す（既存の `registerPasskey`・`passkeyBrowserError` は変えない）:

```ts
export type AutoRegisterResult = "created" | "exists" | "not_allowed" | "failed";
const AUTO_REGISTER_TIMEOUT_MS = 10_000;

export async function conditionalCreateSupported(): Promise<boolean> {
  try {
    const getCaps = (PublicKeyCredential as unknown as {
      getClientCapabilities?: () => Promise<Record<string, boolean>>;
    }).getClientCapabilities;
    if (typeof getCaps !== "function") return false;
    const caps = await getCaps.call(PublicKeyCredential);
    return caps.conditionalCreate === true;
  } catch {
    return false;
  }
}

export async function getPasskeyPrompt(): Promise<{ can_auto: boolean; show_prompt: boolean }> {
  return api.get("/auth/passkey/prompt");
}

export async function autoRegisterPasskey(): Promise<AutoRegisterResult> {
  // 10 秒で打ち切る。InvalidStateError→exists、NotAllowedError→not_allowed、ほか→failed
}

export async function skipPasskeyPrompt(): Promise<void> {
  await api.post("/auth/passkey/prompt/skip", {});
}
```

`autoRegisterPasskey` の中身: `api.post("/auth/passkey/register/options", { auto: true })` → `startRegistration({ optionsJSON: res.options, useAutoRegister: true })` → `api.post("/auth/passkey/register/verify", { challenge_id, credential, label: "" })` → `"created"`。全体を `Promise.race` で 10 秒の打ち切りと競わせ、打ち切りは `"failed"`。`api` の get の型付けは既存の `api.post<T>` の書き方に合わせる。

### 4-6. LoginPage.tsx

`handleSignIn` の `navigate(from, { replace: true })` を、新しい関数 `afterPasswordSignIn()` の呼び出しに置き換える。`afterPasswordSignIn` はどこで例外が起きても最後に必ず `navigate(from, { replace: true })` するか案内を開く:

1. `passkeySupported()` が偽 → navigate
2. `getPasskeyPrompt()`（例外 → navigate）
3. `can_auto` かつ `await conditionalCreateSupported()` → `autoRegisterPasskey()`。結果が `"not_allowed"` 以外 → navigate
4. `show_prompt` → `setPromptOpen(true)`（navigate しない）。でなければ navigate

案内は金型 `Modal`（`frontend/src/components/Modal.tsx`）:
- `open={promptOpen}`・`size="sm"`・`title={t("login.passkeyPromptTitle")}`・`onClose` はスキップと同じ
- 本文 `t("login.passkeyPromptBody")`
- `footer` に `Button` 2 つ: `t("login.passkeyPromptSkip")`（`variant="secondary"`。`frontend/src/components/Button.tsx:7` の規格）と `t("login.passkeyPromptRegister")`（`variant="primary"`）
- 登録: `registerPasskey("")` を try/catch（どの結果でも）→ 閉じて navigate
- スキップ・閉じる: `skipPasskeyPrompt()` を try/catch → 閉じて navigate
- 二度押し防止に処理中はボタンを `disabled`
- 色・大きさ・余白の直書きをしない（ADR-144）。文字はすべて `t()`（ADR-027）

`handlePasskeySignIn` と `useEffect`（:39-43）は変えない。ただし案内を開いている間に `useEffect` が navigate しないよう、`useEffect` の条件に `!promptOpen` を足す。

### 4-7. 文言（ja.json・en.json の `login` に 4 キー。両方に同じキー）

| キー | ja | en |
|---|---|---|
| `login.passkeyPromptTitle` | 顔や指紋でログインできるようにしますか | Sign in with your face or fingerprint? |
| `login.passkeyPromptBody` | 次からはパスワードを入れずに、顔や指紋だけですぐにログインできます。 | Next time, sign in instantly with your face or fingerprint instead of your password. |
| `login.passkeyPromptRegister` | 登録する | Set up |
| `login.passkeyPromptSkip` | 今はスキップ | Skip for now |

### 4-8. 試験（frontend）

`frontend/src/lib/auth/passkey.test.ts` に: `conditionalCreateSupported` が 関数なし→false・`{conditionalCreate:true}`→true・例外→false。`autoRegisterPasskey` が 成功→created・InvalidStateError→exists・NotAllowedError→not_allowed・ほかの例外→failed・10 秒で failed（偽の時計）。

`frontend/src/pages/login/LoginPage.test.tsx` に（既存の `vi.mock("../../lib/auth/passkey", ...)` を広げる）:
- L1 パスキー非対応 → 案内なしで元の画面へ
- L2 `can_auto` かつ対応 → `autoRegisterPasskey` が呼ばれ `created` → 案内なしで元の画面へ
- L3 `not_allowed` かつ `show_prompt` → 案内が出る。「今はスキップ」で `skipPasskeyPrompt` が 1 回呼ばれ元の画面へ
- L4 `not_allowed` かつ `show_prompt=false` → 案内なしで元の画面へ
- L5 `getPasskeyPrompt` が失敗 → 案内なしで元の画面へ
- L6 案内の「登録する」→ `registerPasskey("")` が 1 回呼ばれ、失敗しても元の画面へ

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る。出力はそれぞれ最後の 30 行まで）

1. 実装の前に `backend/tests/test_passkey_login_enroll.py` を書いて走らせ、失敗することを確かめ最終行を貼る（TDD の順）
2. `cd backend && python -m pytest -q tests/test_passkey_login_enroll.py tests/test_passkeys.py tests/test_self_auth.py tests/test_auth_audit_helper.py 2>&1 | tail -30`
3. PostgreSQL 16 を立てられるなら `RLS_TEST_DATABASE_URL`・`RLS_ADMIN_DATABASE_URL` を付けて `python -m pytest -q tests/test_rls_passkey_enroll_skips.py tests/test_rls_auth_audit.py -v 2>&1 | tail -30`。立てられないならその事実を書く（通ったと書かない）
4. `cd backend && ruff check app/routers/auth.py app/auth/passkeys.py tests/test_passkey_login_enroll.py tests/test_rls_passkey_enroll_skips.py tests/conftest.py`
5. `cd frontend && npx vitest run src/lib/auth/passkey.test.ts src/pages/login/LoginPage.test.tsx 2>&1 | tail -30`
6. `cd frontend && npx tsc --noEmit -p . 2>&1 | tail -20` と `npx eslint src/lib/auth/passkey.ts src/pages/login/LoginPage.tsx 2>&1 | tail -20`
7. ja.json と en.json の `login` のキー数が同じこと（`node -e` で数えて両方の数を貼る）
8. commit のあと `git log -1 --stat | tail -20`、push のあと `git log origin/release/passkey-login-enroll-design -1 --format=%H` を貼る
9. `git diff origin/main...HEAD --name-only` が §3 のファイルと、設計文書 3 つ（recon-login-enroll.md・design-login-enroll.md・このカード）と active-work の 1 ファイルだけ

## 6. 分岐ごとの対処（止まるときは停止して、報告の冒頭に BLOCKED: か NEEDS_DECISION: を書く）

| 状況 | 対処 |
|---|---|
| 手順 1 の試験が実装前でも通る | 試験が的外れ。停止して `NEEDS_DECISION:` |
| `migrations/` に 20261031_200000 より新しいファイルがある | 停止して `NEEDS_DECISION:`（末尾 3 件を貼る） |
| 既存の試験（test_passkeys.py ほか）が落ちる | 落ちた試験名と生の出力を貼って停止し `NEEDS_DECISION:` |
| `Modal`・`Button` の props が §4-6 と違う | 実物の props を貼って停止し `NEEDS_DECISION:` |
| §3 以外のファイルを触る必要が出た | 停止して `NEEDS_DECISION:` |
| フックに止められた | 言い換えて再試行しない。停止して `BLOCKED:` |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| パスワード直後の合図だけが自動作成と案内に使える | T1・T2（CI の pytest） |
| 自動作成の道だけ UP・UV の印を求めず、設定画面の道は今のまま | T3・T6 |
| 6 か月で 3 回のスキップで案内が止まる | T4 |
| 表の migration が本物の PostgreSQL で冪等に流れ、アプリの権限で書ける | test_rls_passkey_enroll_skips.py（CI の RLS 試験） |
| 画面の分岐がどれもログインを止めない | L1〜L6（CI の vitest） |
| 文言の直書き・色の直書きが無い | 既存 CI（i18n・UI ガバナンス） |

## 8. 報告と PR

- ブランチ: release/passkey-login-enroll-design（設計文書が入った既存の枝。origin から取ってその上に commit）。担当は commit と push まで。PR は作らない・マージしない
- commit の題: `feat: passkey auto-create and enroll prompt after password login (ADR-1013 b6)`
- 報告は DONE: / BLOCKED: / NEEDS_DECISION: で始め、§5 の生の最終行を貼る。推測で埋めない

END OF CARD
