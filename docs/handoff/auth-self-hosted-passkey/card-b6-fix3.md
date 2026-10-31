# 実装カード 便6 の直し 3 — ログイン直後の案内が誰にも出ない不具合

対象: branch `release/passkey-prompt-get-origin-fix`（origin/main `26dec7f26e2f1dd67e0d976f79649d7244f05a2a` 起点）。
元のカード: `docs/handoff/auth-self-hosted-passkey/card-b6-login-enroll.md`、設計: `docs/handoff/auth-self-hosted-passkey/design-login-enroll.md`（§の決まりはここに書いた所以外そのまま有効）。
PO 承認: 2026-10-31「1」（2 つとも直し、本物のブラウザと同じ送り方の試験を足して同じミスを機械で止める）。

## 0. 何が起きたか（事実）

本番の認証の呼び出し記録（`public.auth_events`、2026-10-31 UTC）:

```
11:31:53.311 POST /api/v1/auth/login           200
11:31:53.377 GET  /api/v1/auth/passkey/prompt  403
11:31:53.564 GET  /api/v1/auth/passkeys        200
11:32:37.027 POST /api/v1/auth/login           200
11:32:37.078 GET  /api/v1/auth/passkey/prompt  403
11:32:37.259 GET  /api/v1/auth/passkeys        200
```

- `backend/app/routers/auth.py:215-217` の `_require_app_origin` は Origin 付け札が `rp_origin()` と違えば 403 `forbidden_origin`。
- `backend/app/routers/auth.py:745-752` の `GET /passkey/prompt` がこれを呼ぶ。`_require_app_origin` を呼ぶ口は auth.py に 13 か所・viewer.py に 4 か所あり、GET はここだけ（ほかは POST・DELETE）。
- ブラウザは同じサイトあての GET・HEAD に Origin を付けない（MDN「Origin」: same-origin requests except for GET or HEAD）。よって本物のブラウザからは必ず 403。
- 試験 `backend/tests/test_passkey_login_enroll.py:151-155` の `_headers` は GET にも Origin を必ず付けるので、試験では通った。
- 画面 `frontend/src/pages/login/LoginPage.tsx:59-75` は 403 を例外として受け、案内を出さずに元の画面へ進む。結果、登録済みかどうかに関係なく、自動作成も案内も一度も動いていない。

もう 1 つの抜け（コードの事実）: `LoginPage.tsx:64-65` は自動作成の結果が `"not_allowed"` 以外なら元の画面へ進む。`"failed"`（NotAllowedError・InvalidStateError 以外の失敗と 10 秒の打ち切り、`frontend/src/lib/auth/passkey.ts:94-111`）でも案内を出さない。設計「できなければ案内」（PO 案A）と食い違う。

## 1. 触るファイル（これ以外は触らない）

- `backend/app/routers/auth.py`
- `backend/tests/test_passkey_login_enroll.py`
- `backend/tests/test_origin_check_not_on_get.py`（新規）
- `frontend/src/pages/login/LoginPage.tsx`
- `frontend/src/pages/login/LoginPage.test.tsx`

`frontend/api-contract/openapi.json` は口の形が変わらないので触らない（CI の書き出し比較が落ちたときだけ、書き出し直して差分をそのまま載せ、報告に書く）。

## 2. 直すこと

### 2-1 `backend/app/routers/auth.py` — GET の口から出どころの確認を外す

変更前（:745-753 付近）:

```python
@router.get("/passkey/prompt", response_model=PasskeyPromptStatus)
async def passkey_prompt_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ログイン直後のパスキー登録（自動作成・案内）を出してよいか。"""
    _require_app_origin(request)
    if not _is_fresh_password_login(request, current_user):
```

変更後:

```python
@router.get("/passkey/prompt", response_model=PasskeyPromptStatus)
async def passkey_prompt_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ログイン直後のパスキー登録（自動作成・案内）を出してよいか。

    読むだけの口なので出どころの確認はしない（ブラウザは同じサイトあての GET に Origin を付けない）。
    本人の Bearer トークンが要るので、他のサイトからは読めない。
    """
    if not _is_fresh_password_login(request, current_user):
```

`request: Request` は `_is_fresh_password_login` が使うので残す。POST・DELETE の口の `_require_app_origin` は 1 つも触らない。

なぜ安全か: この口はトークンの持ち主本人の真偽 2 つを返すだけで、何も書かない。Bearer トークンはメモリにしかなく（`frontend/src/lib/auth/selfAuth.ts:4`）、他のサイトはこれを付けて送れない。既存の `GET /passkeys`（`auth.py:995-`）も同じ理由で出どころの確認をしていない。

### 2-2 `frontend/src/pages/login/LoginPage.tsx` — 自動作成が失敗・打ち切りでも案内へ進む

変更前（:63-66）:

```ts
      if (status.can_auto && (await conditionalCreateSupported())) {
        const result = await autoRegisterPasskey();
        if (result !== "not_allowed") return navigate(from, { replace: true });
      }
```

変更後:

```ts
      if (status.can_auto && (await conditionalCreateSupported())) {
        const result = await autoRegisterPasskey();
        // 作れた・登録済みなら案内は要らない。断られた・失敗・打ち切りは案内へ進む
        if (result === "created" || result === "exists") return navigate(from, { replace: true });
      }
```

ほかの行は変えない。

### 2-3 試験 `backend/tests/test_passkey_login_enroll.py` — 本物のブラウザと同じ送り方を足す

既存の試験は変えない。末尾に次の試験を足す（`_insert_user`・`_token`・`AUTH_PATH`・fixture は同じファイルの物を使う）:

- `test_t8_prompt_get_without_origin_like_a_browser`: Origin を付けず `authorization` だけで `GET {AUTH_PATH}/passkey/prompt` → 200 で `{"can_auto": True, "show_prompt": True}`。
- 同じく Origin 無しで、`amr=None` の合図 → 200 で `{"can_auto": False, "show_prompt": False}`。
- 同じく Origin 無しで、他のサイトの Origin（`https://evil.example`）を付けても 200（読むだけの口なので出どころで断らない。本人のトークンが要ることは既存の 401 の試験で見る）。

T 番号が既に 8 まであれば、次の空き番号にする（報告に書く）。

### 2-4 試験 `backend/tests/test_origin_check_not_on_get.py`（新規）— 同じミスを機械で止める

`app.main` の `app.routes` を全部回し、`APIRoute` のうち `methods` に `GET` か `HEAD` を含むものについて、`inspect.getsource(route.endpoint)` に `_require_app_origin(` も `headers.get("origin")` も含まれないことを確かめる。違反があれば `(method, path)` の一覧を失敗の文に出す。

- `app` の取り込み方は既存の試験（例: `backend/tests/test_realtime_topics.py`）と同じにする。
- 違反 0 件のときに合格し、2-1 を戻すと落ちることを手元で 1 回確かめて報告に書く（戻した差分はコミットしない）。

### 2-5 試験 `frontend/src/pages/login/LoginPage.test.tsx` — 失敗・打ち切りで案内が出る

既存の L1〜L7 は変えない。L7 の後に足す:

- `L8 auto create failed + show_prompt: prompt shown`: `getPasskeyPrompt` → `{ can_auto: true, show_prompt: true }`、`autoRegisterPasskey` → `"failed"`。案内の題が出て、`after-login` はまだ出ない。
- `L9 auto create exists: no prompt`: `autoRegisterPasskey` → `"exists"`。案内は出ず `after-login` が出る。
- `L10 auto create failed + no show_prompt: no prompt`: `{ can_auto: true, show_prompt: false }`・`"failed"`。案内は出ず `after-login` が出る。

## 3. 確かめ方（生の最終行を報告に貼る）

- `cd backend && python -m pytest tests/test_passkey_login_enroll.py tests/test_origin_check_not_on_get.py tests/test_realtime_topics.py --no-cov -q`（python は 3.12 の venv）
- 2-4 の「戻すと落ちる」確認の失敗の文（1 回分）
- `cd backend && ruff check app/routers/auth.py tests/test_passkey_login_enroll.py tests/test_origin_check_not_on_get.py`
- `cd frontend && npx vitest run src/pages/login/LoginPage.test.tsx src/lib/auth/passkey.test.ts`
- `cd frontend && npx eslint src/pages/login/LoginPage.tsx src/pages/login/LoginPage.test.tsx`
- `git diff --stat origin/main` で触ったファイルが §1 の中だけ

## 4. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| Origin 無しの GET で案内の判定が 200・正しい真偽 | 2-3 の試験の合格（報告の生の最終行・CI） |
| GET・HEAD の口が出どころの確認を呼ばない（全口） | 2-4 の試験の合格と、戻すと落ちる 1 回分の失敗の文 |
| 自動作成が `"failed"` なら案内が出る・`"created"`/`"exists"` なら出ない | L8〜L10 の合格（vitest の生の最終行・CI） |
| POST・DELETE の出どころの確認は 1 つも減っていない | Opus が差分を読む（`_require_app_origin(request)` の行数が auth.py で 13→12、viewer.py で 4 のまま） |
| 本番で、未登録の人がパスワードで入ると案内の判定が 200 | デプロイ後、`public.auth_events` の `GET /api/v1/auth/passkey/prompt` に 200 が記録される（PO のログイン 1 回） |
| 本番で、未登録の人に案内か自動作成が出る | PO の目視（テナント 004 でログイン） |

## 5. 同じ種類の漏れを止める仕組み

- 漏れた理由: 出どころの確認を「書き込みの守り」として作ったのに、読むだけの GET にも付けた。試験は付け札を必ず付けて送ったので、本物のブラウザとの違いを見なかった。
- 止める仕組み: 2-4 の試験が、どの口でも GET・HEAD に出どころの確認を付けた時点で CI で落とす。2-3 の試験が、本物のブラウザと同じ送り方で案内の口を確かめる。
- 確かめの決まり: ログイン直後の動きを変えたときは、本番反映後に `public.auth_events` で各口の応答の番号を読んでから合格とする（今回はこれをせずに「合格」と報告した）。
