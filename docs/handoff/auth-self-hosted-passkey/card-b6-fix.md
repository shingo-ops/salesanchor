# 実装カード 便6 の直し — 審査（REQUEST_CHANGES）の 3 点

対象: PR #4944（branch `release/passkey-login-enroll-design`、審査した HEAD `db7b6c03956558fcc540454554c0b7c2509601b9`）。
元のカード: `docs/handoff/auth-self-hosted-passkey/card-b6-login-enroll.md`（§4〜§6 の決まりはそのまま有効）。
審査役の生の記録: Opus 審査役が 2026-10-31 に REQUEST_CHANGES。直す点は下の 3 つだけ。製品コード（`backend/app/`・`frontend/src/` の試験以外）は触らない。

## 1. 触るファイル（これ以外は触らない）

- `frontend/api-contract/openapi.json`（作り直すだけ。手で書かない）
- `frontend/src/pages/login/LoginPage.test.tsx`
- `backend/tests/test_rls_passkey_enroll_skips.py`

## 2. 直すこと

### 2-1. API の形の書き出し（必須 CI「API contract is up to date」が赤）

CI と同じ命令で作り直してコミットする（`.github/workflows/api-contract-check.yml:35`）:

```
cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json
```

python は 3.12 の venv で動かす。作り直した差分は、新しい口 `GET /api/v1/auth/passkey/prompt`・`POST /api/v1/auth/passkey/prompt/skip` と、`PasskeyRegisterOptionsRequest`・`PasskeyPromptStatus` の追加、options の口の本文の追加だけのはず。それ以外の差が出たら止まって `NEEDS_DECISION:`（差分の名前の一覧を貼る）。

`.github/workflows/api-contract-check.yml` に TypeScript の型の生成（`frontend/src/api/generated/` 等）の手順があり、それもずれる場合は、その生成物も CI と同じ命令で作り直してよい。そのときは触ったファイル名を報告に書く。

### 2-2. 画面の試験に「ログイン後の画面へ進んだ」の確認を足す（設計の受入基準 A5）

今の `renderLogin()`（`frontend/src/pages/login/LoginPage.test.tsx:51-61`）は行き先の画面が無く、移らなくても合格してしまう。

- 新しい関数 `renderLoginWithHome()` を足す。`MemoryRouter initialEntries={["/login"]}` の中に `Routes` を置き、`/login` に `<LoginPage />`、`/` に `<div data-testid="after-login" />` を置く（`LoginPage.tsx:48-49` の既定の行き先が `/`）。文字は置かない（i18n の検査に掛けないため）
- 既存の `renderLogin()` と既存の試験は変えない
- `describe("LoginPage (enroll after password sign-in)")` の L1〜L6 を `renderLoginWithHome()` に替え、次を足す:
  - L1・L2・L4・L5: `await screen.findByTestId("after-login")` が出る
  - L3・L6: 案内が出ている間は `screen.queryByTestId("after-login")` が null。スキップ／登録のあとに `findByTestId("after-login")` が出る
- 新しい試験 L7 を足す（`!enrolling` の守り）: `getPasskeyPrompt` を解決しない Promise にしてログインする → `waitFor` で `getPasskeyPrompt` が 1 回呼ばれたあと、`queryByTestId("after-login")` が null（先に移っていない）。そのあと Promise を `{ can_auto: false, show_prompt: true }` で解決すると、案内の題が出て、`after-login` はまだ null
- 試しに `LoginPage.tsx` の useEffect の条件から `!enrolling` を外すと L7 が赤になることを、手元で 1 回だけ確かめ、元に戻す（コミットしない）。赤になった生の最終行を報告に貼る

### 2-3. PostgreSQL の試験で GRANT を本当に試す（審査の第 4 節）

CI は試験の前に既定の権限を流すため（`.github/workflows/test.yml:180-203`）、migration の GRANT が無くても今の試験は通ってしまう。

`backend/tests/test_rls_passkey_enroll_skips.py` に試験を 1 つ足す:

1. 管理の接続で `REVOKE ALL ON TABLE public.passkey_enroll_prompt_skips FROM salesanchor_app` と `REVOKE ALL ON SEQUENCE public.passkey_enroll_prompt_skips_id_seq FROM salesanchor_app` を流す
2. 管理の接続で `has_table_privilege('salesanchor_app', 'public.passkey_enroll_prompt_skips', 'INSERT')` が false になったことを確かめる（取り消しが効いた証拠）
3. migration をもう一度流す（`_run_migration`）
4. 同じ関数が INSERT・SELECT とも true、`has_sequence_privilege('salesanchor_app', 'public.passkey_enroll_prompt_skips_id_seq', 'USAGE')` が true
5. アプリの接続で INSERT と count の SELECT が通る

この試験は既存の 2 つより後に流れるよう、ファイルの末尾に置く。手元では PostgreSQL を作れないので CI で確かめる（見張りを回り道しない）。

## 3. 確かめ方（生の最終行を報告に貼る）

- `cd frontend && npx vitest run src/pages/login/LoginPage.test.tsx src/lib/auth/passkey.test.ts`
- 2-2 の「`!enrolling` を外すと L7 が赤」の 1 回
- `cd frontend && npx eslint src/pages/login/LoginPage.test.tsx`
- `cd backend && python -m pytest tests/test_passkey_login_enroll.py tests/test_rls_passkey_enroll_skips.py --no-cov -q`（PostgreSQL の試験は skip で正しい）
- `git diff --stat origin/release/passkey-login-enroll-design` で触ったファイルが §1 の 3 つ（と 2-1 で許した生成物）だけ

## 4. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 必須 CI「API contract is up to date」が緑 | `gh pr checks 4944` |
| L1〜L7 がすべて「ログイン後の画面に進んだ／進んでいない」を確かめている | 差分を Opus が読む・vitest 合格 |
| `!enrolling` を外すと L7 が赤 | 担当の報告の生の最終行 |
| GRANT を取り消してから migration で戻ることを PostgreSQL で確かめる | CI の pytest（SQLite + PostgreSQL RLS）が緑 |
| 製品コードの変更 0 | `git diff --stat` |

## 5. 残すと決めたこと（今回は直さない）

- 審査の第 7 節（`getPasskeyPrompt` に 10 秒の打ち切りが無い）: 失敗しても必ず先へ進む作りで、設計の決まりとも食い違わない。14 日後の確かめで、ログインの遅れの声や 500 が出たら別に直す
- 審査の第 8 節（自動作成で UV を求める指定のまま）: ブラウザが断っても案内に回り、ログインは止まらない。本番で自動作成が 0 件なら、14 日後の確かめで調べる
