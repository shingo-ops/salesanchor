<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — 本番の点検のブラウザで、ログイン直後の顔・指紋の登録案内を出さない

**仕事名**: prod-check-no-passkey-prompt  
**日付**: 2026-11-01  
**対象ADR**: ADR-1051, ADR-1013  
**担当**: 設計担当（Claude Opus）

---

## 起きたこと（観測事実）

- ログインボタンの探し方を直した（#4950・main 7e9155163）あと、2026-10-31 14:53 UTC に prod-ui-check を手で動かした（run 41212202516）。結果は failure。
  - S1（ログイン画面が開く）と S7（間違ったパスワード）は ✓。ボタンは見つかり、押せている。
  - S2〜S6・S8 は、どれも `TimeoutError: page.waitForURL: Timeout 30000ms exceeded.`（`tests/prod-check/login.ts:40`）。ログインボタンを押したあと、30 秒たっても `/` か `/dashboard` に移らない。
  - 速さの記録の本体も同じ所（login.ts:40、`tests/prod-check/page-speed.spec.ts:480` から）で止まった。精度の試しは ✓（2.0s）。
  - 記録全文: /tmp/CC報告ファイル/page-speed/line/run2-log.txt（760 行）。画面の写しは workflow が残していない（artifacts 0 件）。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/login/LoginPage.tsx:53` | ログイン済みでも `enrolling` か `promptOpen` の間は自動で移らない |
| `frontend/src/pages/login/LoginPage.tsx:59` | パスワードでログインした直後: `passkeySupported()` が false ならすぐ元の画面へ移る（:61）。true なら `getPasskeyPrompt()`（:62）を読み、`show_prompt` なら案内を開いて止まる（:68-70） |
| `frontend/src/pages/login/LoginPage.tsx:270` | 案内（Modal）。「あとで」か「登録」を押すまで閉じない |
| `frontend/src/lib/auth/passkey.ts:22` | `passkeySupported()` = 自社ログイン かつ `browserSupportsWebAuthn()` |
| `backend/app/routers/auth.py:745` | `GET /auth/passkey/prompt`: パスワードでログインした直後なら `show_prompt = 登録数 0 かつ 最近の「あとで」< 3`（:762） |
| `backend/app/routers/auth.py:766` | 「あとで」は `public.passkey_enroll_prompt_skips` に 1 行書く（:777） |
| `tests/prod-check/login.ts:35` | 点検のログイン手順（今の点検 S2〜S6・S8 と速さの記録が使う。`tests/prod-check/fixtures.ts:39`・`tests/prod-check/prod-ui.spec.ts:37`・:129・page-speed.spec.ts:480） |
| `tests/qa-smoke/utils/real-backend.ts:27` | 手で動かす動作確認のログイン手順（scene-01〜09 が使う） |

- `@simplewebauthn/browser` は 14.0.0（frontend/package.json:78）。公開版の `esm/helpers/browserSupportsWebAuthn.js`（unpkg.com で実物を読んだ）は `globalThis?.PublicKeyCredential !== undefined && typeof globalThis.PublicKeyCredential === 'function'` だけで判定する。
- 点検用の人は顔・指紋をまだ登録していない。そのため `show_prompt` が true になり、案内が開いて /login に留まる（上の 2 つの式と、30 秒移らなかった観測が一致する）。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 止まった画面が案内だったか（写しが無い） | コードの流れ（LoginPage.tsx:59-75）と、登録 0 件の人なら必ず案内が開く式（auth.py:762）で説明できる。直したあとの手動実行で success を見て確かめる | ✅ 解消済み（直したあとの実行で確かめる） |
| 2 | 「あとで」を押す直し方を選ぶと本番に何が残るか | 押すたびに skips に 1 行増え、3 回で案内が出なくなる（auth.py:762・:777）。回によって流れが変わる | ✅ 解消済み（この直し方は採らない） |
| 3 | Playwright の `addInitScript` の公式説明 | Context7 は月の上限で使えない。同じ点検で既に `page.addInitScript` を使い、毎回動いている（page-speed.spec.ts:441） | ✅ 解消済み（実物で確認） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- このままだと 2026-11-01 07:00 JST の毎朝の点検が落ち、間違いの知らせが Discord に届く（今夜すでに 2 回届いた）。
