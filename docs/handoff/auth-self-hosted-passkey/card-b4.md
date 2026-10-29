# 実装カード 便4 — ログインを Firebase から自社の仕組みに切り替える

> この文書は何か：ADR-1013 便4 の作業指示書です。2 つの PR に分けます。**便4a** は、自社ログインを使う画面と API の残り（パスワード変更・新規登録の置き換え・再設定ページ・ログイン画面の金型化）を作ります。ただし初期値は今の Firebase のままなので、ログインの仕組みは変わりません。見た目の変化は、ログイン画面の 2 つのボタンが金型の補助ボタン（枠つき）になることだけです（design.md:206）。**便4b** は切り替えそのものです。設定の 3 か所を変え、初回パスワードを発行します。便4b は危険便なので、PO が決めた切り替え日に GO を出して反映します。

- 設計: docs/handoff/auth-self-hosted-passkey/design.md §3（:73-82・:103）・§5 画面（:127-130）・§6 便4（:157）・手順（:162-167）・受け入れ基準（:192・:195）・告知（:140・:221）
- 対象ADR: ADR-1013（本テーマ）、ADR-027（画面の文言は t()）、ADR-144（UI は金型）、ADR-075（秘密は GitHub Secrets）、ADR-135・ADR-136（危険PRの GO）
- 状態: 第5版。Opus 審査役の 5 回目の審査で APPROVE（2026-10-29。1〜4 回目は REVISE で、指摘はすべて反映。5 回目の LOW-10 も反映）。審査記録 /tmp/CC報告ファイル/auth-b4-recon2/review-card-b4-1.md〜review-card-b4-5.md。便を 4a・4b の 2 PR に分けるのは design.md:157（1 便）からの変更で、PO の合意を得て design.md に書き戻す。**PO の実装承認前（実装未着手）**
- 担当: 実装 Sonnet／コード審査 Opus（reviewer）／GO・マージ・反映確認 Opus／秘密の登録・初回パスワードの配布・切り替え日の決定 PO

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・1 手順 1 コマンド・出力に上限・sleep しない・報告に無い出力を成功と扱わない・プレースホルダを残さない | ○（§0-2・§5・§12） |
| guards/03-file.md | 編集は Write/Edit で行う | ○（§0-2） |
| guards/04-worktree.md | `bash scripts/new-worktree.sh release/auth-b4a-self-login-ui --claude`（便4b は `release/auth-b4b-switch`）で作る（CLAUDE.md が正本）。出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる。push は毎回 `git push -u origin HEAD` | ○（§0-2・§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは `### 標準ワークフロー確認` の中に同一行カンマ区切り。commit・push・PR 作成は段ごとに実在を確かめる | ○（§0-2・§10） |
| guards/08-vps.md | どの機体・どの鍵か。実装役は本番の機体に入らない。発行スクリプトの本番実行は PO が自分の Mac から行い、手順と機体・鍵は Opus が別紙で渡す | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1013 便4a（または便4b）の実行結果である」と書くこと。便4a と便4b は別々に渡す。PO の実装承認が出た便だけを実行する。

## 0-2. 作業の決まり

- 作業場所は、便4a が `/Users/tanizawashingo/worktrees/salesanchor/release-auth-b4a-self-login-ui`、便4b が `/Users/tanizawashingo/worktrees/salesanchor/release-auth-b4b-switch`（§10 のブランチを new-worktree.sh で作った場所）。全コマンドをこのフルパスへの `cd` と `&&` で始める。1 手順 1 コマンド。出力が長くなる命令には `| head -200` か `| tail -50` を付ける。生出力は `/tmp/CC報告ファイル/auth-b4a/`（便4b は `/tmp/CC報告ファイル/auth-b4b/`）に保存する
- ファイルの作成と編集は Write/Edit で行う。sleep しない（待ちは Opus が行う）
- §3 の触るファイル以外を変えない。足す必要が出たら §6 の分岐に従い、無ければ停止する
- 停止するときは、報告に 3 点を書いて終える: ①止まった手順（§ の番号）②最後のコマンド ③理由（エラーやフックの文の原文）。フックや自動判定に止められたら、言い換えて再試行しない
- 停止するのは、§6 に無い分岐・§5 の確かめが通らない・触るファイル以外を変える必要が出たときだけ。報告先は Opus

## 1. 範囲

便4a に入れる:
1. `POST /api/v1/auth/password/change`（design.md:78）
2. `register` の置き換え（design.md:82）。super admin 専用のまま。users を `password_argon2_hash` NULL で作り、purpose=invite の鍵で初回設定メールを送る
3. 画面の自社ログイン層。`VITE_AUTH_PROVIDER` が `self` のときだけ自社 API を使う。値が無い・`firebase` のときは今と同じ動き
4. 再設定ページ `/reset-password?token=`（design.md:127）
5. ログイン画面の金型化（生 `<button>` 2 つを金型へ）
6. アカウント設定のパスワード変更を、`self` のときは自社 API へ（design.md:128。パスキーの一覧・追加・削除は便5）
7. e2e の迂回を自社方式でも使える形に（design.md:130。開発サーバーのときだけ）
8. 担当者の追加（`POST /api/v1/staff`）で新しく利用者ができたとき（design.md に無い追加。§11 で PO の合意を取る）、`AUTH_PROVIDER=self` なら初回設定メールを送る（F21。Firebase が無くなったあとも新しい人が入れるように）
9. 誤りの文言を自社 API の応答から作る（`firebaseErrorMessage.ts` の置き換え先。design.md:131）
10. design.md の修正。直す場所は §3 の一覧のとおり（事実の誤りの修正と、PO の合意後に書き戻す分を分ける）

便4b に入れる:
1. GitHub の secret `AUTH_JWT_SECRET` を backend に渡す（deploy.yml の消す一覧と heredoc・docker-compose.yml の backend environment）
2. `AUTH_PROVIDER=self`・`VITE_AUTH_PROVIDER=self`（frontend/Dockerfile の ARG・compose の build args・deploy.yml）
3. `AUTH_PASSWORD_RESET_ALLOWLIST` を外す
4. 初回パスワード発行スクリプト `backend/scripts/issue_initial_passwords.py`（新設）

入れない（理由）:
- パスキー → 便5
- Firebase の SDK・設定・CSP の Firebase 許可の削除 → 便6（不可逆）。便4b のあとも Firebase は残し、戻せる状態を保つ
- 管理者の 2 段階の確認（ADR-1048）→ 便5 のあと

## 2. 前提の事実（2026-10-29・origin/main 84692a999 基準）

生出力: /tmp/CC報告ファイル/auth-b4-recon/・/tmp/CC報告ファイル/auth-b4-recon2/

| # | 事実 | 出典 |
|---|---|---|
| F1 | 自社トークンの発行は `AUTH_PROVIDER=="self"` かつ秘密ありのときだけ | `backend/app/auth/self_tokens.py:62-64` |
| F2 | 秘密は 32 文字以上。閲覧者の鍵と同じ値なら拒否 | `backend/app/auth/self_tokens.py:27,79-81`・`backend/app/auth/viewer_tokens.py:30` |
| F3 | deploy.yml・docker-compose.yml に `AUTH_PROVIDER`・`AUTH_JWT_SECRET` の行は 0 件。GitHub の secret にも `AUTH_JWT_SECRET` は無い | /tmp/CC報告ファイル/auth-b4-recon/ |
| F4 | `VITE_FIREBASE_API_KEY`・`VITE_FIREBASE_AUTH_DOMAIN` は frontend/Dockerfile の ARG と compose の build args で渡す。deploy.yml には 0 件 | `frontend/Dockerfile:7-8,11-12`・`docker-compose.yml:183-184` |
| F5 | login は成功時に `last_login` を更新する。更新用 Cookie は `sa_refresh`・httponly・SameSite=strict・Path=`/api/v1/auth`・Domain なし | `backend/app/routers/auth.py:294-297`・`:211-221`・`backend/app/auth/self_tokens.py:25-26` |
| F6 | design.md:192 の「今のコードは last_login を更新していない」は F5 と食い違う（古い記述） | F5 |
| F7 | design.md:82 の「auth.py:23」は今は `register` が auth.py:43。UserRegister は firebase_uid 必須。L143 で Firebase の claim を書く。画面から register を呼ぶ箇所は 0 件 | `backend/app/routers/auth.py:43-155`・`backend/app/schemas/auth.py:26` |
| F8 | `password/change` の口は無い | `backend/app/routers/auth.py` |
| F9 | 画面の API の呼び先は同じオリジンの `/api/v1`。CSP の connect-src を変えなくてよい | `frontend/src/lib/api.ts:30`・`nginx/nginx.conf:84` |
| F10 | `/api/v1/auth/` は IP ごと 10 回/分・burst 5 | `nginx/nginx.conf:6,144-146,406-408` |
| F11 | Firebase を参照する画面のファイルは 21 件。トークン取得は api.ts:51・useSSE.ts:38・RealtimeProvider.tsx:69・ShippingDetailPanel.tsx:316・ERPPage.tsx:37 の 5 か所 | /tmp/CC報告ファイル/auth-b4-recon2/ Q10 |
| F12 | e2e の偽ログインは `import.meta.env.DEV` のとき。`window.__salesanchorE2eAuthUser` か localStorage `salesanchor:e2e-firebase-auth-user` を読み、固定のトークン文字列を返す | `frontend/src/lib/firebase.ts:25,67`・`frontend/src/lib/firebase-auth.ts:27-28`・`frontend/tests-e2e/utils/auth.ts:20-47` |
| F13 | ログイン画面の生 `<button>` は「パスワードを忘れた」（:115-121）と「ログインへ戻る」（:154-156）。どちらも画面内の切り替え | `frontend/src/pages/login/LoginPage.tsx` |
| F14 | 金型: Button・ButtonLink・Callout・TextFieldControl・PageLayout がある。`/reset-password` のルートは無い | `frontend/src/components/*.tsx`・`frontend/src/App.tsx:156` |
| F15 | backend のイメージは `/app` に backend/ を丸ごと入れる。`backend/scripts/` に `__init__.py` は無い。`python -m scripts.X` で動かした例は 0 件 | `backend/Dockerfile:4,24` |
| F16 | 本番の使用中の利用者は 8 人（id 1・2・3・6・8・10・83・84。2026-10-29 02:09Z 読み取り）。2026-10-13 の 10 人との差は、2026-10-27 に止めた id 7・9（全 14 行のうち 10-13 以降に増えたのは試験用の id 86 だけなので、10-13 の使用中 10 人＝今の 8 人＋id 7・9） | /tmp/CC報告ファイル/auth-b4-recon2/opus-check2.txt・`docs/handoff/admin-2fa/deactivate-7-9/README.md:31`・`docs/handoff/auth-self-hosted-passkey/recon.md` P3 |
| F18 | id 2（tenant 3）は Firebase に居ない（2026-10-13 突き合わせ）。今は使用中なので、発行の対象に入る | `docs/handoff/auth-self-hosted-passkey/recon.md` P12 |
| F19 | Button の見た目は primary・secondary・ghost・danger・outline・tab の 6 種。文字だけの見た目は無い。ButtonLink は tab 以外の 5 種 | `frontend/src/components/Button.tsx:7,12`・`frontend/src/components/ButtonLink.tsx:9` |
| F20 | deploy.yml はサーバーの .env から古い行を消してから書き足す（消す一覧は `AUTH_PASSWORD_RESET_ALLOWLIST` などのキー名の並び）。backend は .env の全キーを名前で受け取る。よって便4b を revert すると「消す」行も無くなり、`AUTH_PROVIDER=self` が .env に残って backend は self のまま | `.github/workflows/deploy.yml:277-318`・`scripts/blue-green-cutover.sh:80-84`（照合 /tmp/CC報告ファイル/auth-b4-recon2/opus-verify-review.txt） |
| F21 | `POST /api/v1/staff` は、同じ email の利用者が居なければ `public.users` に新しい行を作る（パスワードなし） | `backend/app/routers/staff.py:70-100,585` |
| F22 | users は書き込みだけ RLS が FORCE。会社の文脈（`app.tenant_id`）か運営の文脈（`app.is_operator` が true）が無い UPDATE はエラーにならず 0 行 | `migrations/20261016_180000_add_users_write_rls.sql:6-28` |
| F23 | 更新用トークンは 1 回使うと失効。失効済みが届くと同じ組（family）を全部失効。refresh はパスワード変更時刻より前に作ったトークンを拒否 | `backend/app/auth/self_tokens.py:188-235` |
| F24 | アクセストークンの発行時刻（iat）は秒単位。照合ではパスワード変更時刻と比べる | `backend/app/auth/self_tokens.py:93`・`backend/app/auth/dependencies.py:89,101` |
| F25 | 担当者の追加の `_resolve_user_for_new_staff` は利用者の id だけを返し、作ったか既存かを返さない。`create_staff` は BackgroundTasks を受け取らず、commit は :638 | `backend/app/routers/staff.py:67-100,585-638` |
| F26 | users の RLS の試験は、`RLS_TEST_DATABASE_URL`（RLS を通り抜けない salesanchor_app の接続）で行う型がある。CI はこの値を渡している | `backend/tests/test_rls_invariants.py:1-56`・`.github/workflows/test.yml:223` |
| F27 | deploy の健康確認が失敗すると自動で前の版に戻す。戻すのはコードだけで .env は戻さない。戻した後は compose で起動し、compose の backend は `environment:` に書いたキーだけを受け取る（`env_file` なし） | `.github/workflows/deploy.yml:711-749`・`docker-compose.yml:63-` |
| F28 | `AUTH_PASSWORD_RESET_ALLOWLIST` は、消す一覧 :311・heredoc :361・compose :134 の 3 か所 | `.github/workflows/deploy.yml:311,361`・`docker-compose.yml:134` |
| F29 | 自社のアクセストークンの中身は iss・sub（利用者の id）・email・jti・iat・exp（・amr）。今の利用者を返す API の口（`/auth/me` など）は無い。画面が読む user の項目は uid・email・displayName・emailVerified | `backend/app/auth/self_tokens.py:86-100`・`frontend/src/lib/firebase-auth.ts:67-70` |
| F30 | 自社 API の応答の状態コードは 401（`invalid_credentials`。止められた口座も同じ）・403（`forbidden_origin`）・404（発行が無効）・429（`too_many_attempts`）・400（`invalid_or_expired_token`）・422（パスワードの決まり違反。detail は `password_too_short`・`password_too_long`・`password_too_common`）。423 を返す箇所は無い | `backend/app/routers/auth.py:201-208,234-235,250,392,433,436-437,452,462`・`backend/app/auth/password_policy.py:24-32` |
| F31 | 照合済みのトークンは Redis に 300 秒保持され、保持中は `password_changed_at` を見ずに通る。design.md:200 の「最大 5 分」はこの保持による | `backend/app/cache.py:15`・`backend/app/auth/dependencies.py:108,190-198` |
| F32 | 今の api.ts に 401 の処理は無い。POST などは二重送信を防ぐため送り直さない | `frontend/src/lib/api.ts:47-73` |
| F33 | deploy.yml は main への push で必ず走る。止める変数や条件は無い | `.github/workflows/deploy.yml:3-6` |
| F34 | 共通の検証の口は、SMOKE_SERVICE_TOKEN の照合を `AUTH_PROVIDER` に関係なく最初に行う | `backend/app/auth/dependencies.py:147-178` |
| F17 | パスワードを持つ人の数は、読み取りのビューに列が無く読めない | ai_ro.public__users |

## 3. 触るファイル（これ以外は触らない）

便4a:
- `backend/app/routers/auth.py`（register の置き換え・password/change の追加）
- `backend/app/schemas/auth.py`（UserRegister から firebase_uid を外す・PasswordChange を追加）
- `backend/app/services/auth_mail.py`（初回設定メールの文面。便3 の再設定メールと同じ作り）
- `backend/app/routers/staff.py`（新しい利用者を作ったときの初回設定メール。F21）
- `backend/tests/test_admin_api_super_admin_only.py`（register の入力が変わるため :19-24・:98-102）・`backend/tests/test_staff*.py` のうち担当者の追加の試験
- `backend/tests/test_self_auth.py`・`backend/tests/test_password_reset.py`・新設 `backend/tests/test_register_invite.py`
- 新設 `frontend/src/lib/auth/provider.ts`（`VITE_AUTH_PROVIDER` を読む 1 か所）
- 新設 `frontend/src/lib/auth/selfAuth.ts`（login・refresh・logout・メモリのアクセストークン）
- `frontend/src/contexts/AuthContext.tsx`・`frontend/src/lib/api.ts`・`frontend/src/hooks/useSSE.ts`・`frontend/src/lib/realtime/RealtimeProvider.tsx`・`frontend/src/components/ShippingDetailPanel.tsx`・`frontend/src/pages/erp/ERPPage.tsx`（トークン取得を 1 つの関数に寄せる）
- `frontend/src/pages/login/LoginPage.tsx`・新設 `frontend/src/pages/reset-password/ResetPasswordPage.tsx`・`frontend/src/App.tsx`
- `frontend/src/pages/account-settings/SecuritySection.tsx`
- 新設 `frontend/src/lib/auth/authErrorMessage.ts`（自社 API の応答→文言キー。firebaseErrorMessage.ts は便6 まで残す）
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
- `frontend/src/lib/firebase-auth.ts`・`frontend/tests-e2e/utils/auth.ts`（迂回）
- 画面のテスト（各ファイルの隣の `*.test.tsx`）
- `docs/handoff/auth-self-hosted-passkey/design.md`。直すのは次の場所だけ
  - 事実の誤りの修正（便4a でそのまま直す）: :82 の行番号（F7）・:192 の last_login の記述（F6）・:157 の戻し方（F20）・:140・:164・:192 と :157 の K1 欄の「10 人」「10」を「便4b の試し実行の件数」に・:131 の置き換え先を `authErrorMessage.ts` に（firebaseErrorMessage.ts は便6 まで残す）
  - PO の合意後に書き戻す分（§11 の合意が出るまで直さない）: :157 の便4 の行を 4a・4b の 2 行にする・担当者の追加の初回設定メールを足す
- 新設 `backend/app/services/invite.py`（初回設定の鍵を作る関数。register と担当者の追加の両方から呼ぶ）

便4b（危険パス）:
- `.github/workflows/deploy.yml`・`docker-compose.yml`・`frontend/Dockerfile`
- 新設 `backend/scripts/issue_initial_passwords.py`・新設 `backend/tests/test_issue_initial_passwords.py`
- `.env.example`・`docs/ENVIRONMENT_VARIABLES.md`

## 4. 作り方

### 4.1 便4a backend

1. `password/change`: 認証は共通の `get_current_user`（Firebase のトークンも自社トークンも通す。design.md:103 のとおり設定に関係なく動く。秘密が無いと自社トークンは断られる＝`backend/app/auth/self_tokens.py:67-69`・`backend/app/auth/dependencies.py:84-85`）。`password_argon2_hash` が NULL の人は照合が必ず失敗し 400 `invalid_credentials`。今のパスワードを照合し、新パスワードは便3 の決まり（15〜64 文字・一覧で拒否）。成功で hash を更新し、`password_changed_at` は**秒に切り捨てた**時刻で保存する（F24）。その人の更新用トークンを全部失効させ、今の端末には新しいアクセストークンと更新用 Cookie を出し直す（F23 のため、今の端末のトークンを残す形は成り立たない）。照合失敗は失敗回数に数える（login の :269-290 の処理を関数に切り出して両方から呼ぶ）。照合失敗の応答は **400・detail `invalid_credentials`**（401 にしない。401 は画面が「ログインが切れた」と読むため。§4.2-3）。新パスワードの決まり違反は confirm と同じ 422（F30）。Origin 照合（`_require_app_origin`）を付ける
1-2. 新しいアクセストークンと Cookie を出すのは `is_issuance_enabled()` のときだけ（firebase の間は出さず、失効だけ行う）。画面は応答のアクセストークンをメモリに入れ直す
2. `register`: Origin 照合を付ける。入力は今の UserRegister から firebase_uid だけを外した形（ほかの項目と既定値は変えない）。email を小文字に。users を hash NULL で作り、purpose=invite（72 時間）の鍵を作って、再設定ページへのリンクを初回設定メールで送る。Firebase の claim 書き込み（:143）を消す。super admin 専用は変えない。鍵と案内メールは `AUTH_PROVIDER=self` のときだけ作る。firebase の間は users の行だけ作り、鍵もメールも作らない（担当者の追加 4. と同じ決まり）
3. 口は 2 つとも `AUTH_PROVIDER` に関係なく動く（design.md:103）
4. `POST /api/v1/staff`（F25）: `_resolve_user_for_new_staff` の戻り値を `(user_id, created)` にする。`create_staff` に BackgroundTasks を足す。`created` かつ `AUTH_PROVIDER=self` のときだけ、`invite.py` の関数で鍵を同じトランザクションの中で INSERT し、commit（:638）の後に BackgroundTasks で初回設定メールを送る。既存の利用者を使ったときは何もしない。register も同じ関数を使う

### 4.2 便4a 画面

1. `provider.ts` だけが `import.meta.env.VITE_AUTH_PROVIDER` を読む。値がちょうど `self` のときだけ self、それ以外（未設定を含む）は firebase。ほかのファイルは読まない（設定の 1 か所化）
2. トークン取得は `getAccessToken()` 1 つにまとめ、F11 の 5 か所はこれを呼ぶ。firebase のときは今の `getIdToken()`、self のときはメモリのトークン（切れていたら refresh を 1 回）
3. 起動時（self）: メモリにトークンが無い → refresh を 1 回 → 401 なら「ログインしていない」状態にする。ログイン画面へ移すのは ProtectedRoute の中のページだけ（`frontend/src/App.tsx:162`）。`/login`・`/reset-password` を開いた人はそのページに留める（メールのリンクから来た人を飛ばさないため。K4・K9）
3-1. 動いている間の 401（self のときだけ。F32）: `/api/v1/auth/` で始まる口の 401 では refresh しない（login・refresh 自身の 401 で往復しないため。F10）。そのうち password/change・logout の 401 はログインが切れた印なので、ログイン画面へ移す（login の 401 は誤りの文言を出すだけ）。それ以外の口が 401 を返したときだけ refresh を 1 回送る。refresh が成功したら、元の要求を 1 回だけ送り直す（POST なども含む。401 は backend が処理の前に断った印なので二重にならない）。送り直しも 401 ならログイン画面へ。refresh が 401 でもログイン画面へ
3-2. refresh は同時に 1 本だけ（F23。2 本同時に送ると 2 本目が失効済みになり、組ごと失効してログアウトになる）。同じタブの中は 1 つの Promise を共有する。タブの間は `navigator.locks.request("sa-auth-refresh", …)` で順番にし、ロックを取ったあと最新のトークンがあれば refresh を送らない
3-3. AuthContext の `user` は、self のときも今使っている項目（使う所 8 か所が読む項目）を同じ名前で持つ形にする。使う所は書き換えない。self の `uid`・`email` は、メモリのアクセストークンの中身（`sub`・`email`。F29）から取る。表示に使うだけで、署名の確かめは backend が行う。`displayName` は null、`emailVerified` は true にする。新しい API の口は作らない。型は `AuthUser` として AuthContext.tsx に 1 つだけ定義する。refresh のたびに新しい物を作らない（`sub` と `email` が変わらない限り同じ物を返す。使う所の useEffect が 15 分ごとに走り直さないように）
3-4. B7（`navigator.locks` が無い）のときは、2 つのタブで同時に refresh するとログアウトすることがある。そのときはログイン画面に戻るだけで、データは失われない
4. アクセストークンは画面のメモリだけに置く。localStorage・sessionStorage に入れない
5. ログイン画面: 生 `<button>` 2 つを `Button variant="secondary"`（補助の操作。F19）に置き換える。新しい見た目は足さない。self のとき「パスワードを忘れた」は便3 の request 口を呼ぶ
6. 再設定ページ: ログイン不要のルートとして App.tsx の `/login` と同じ並び（ProtectedRoute の外）に置く。`token` を URL から読む → 新パスワード 2 回 → confirm。部品は `PageLayout`・`TextFieldControl`・`Button`・`Callout`。成功したらログイン画面への `ButtonLink`。自動ログインはしない
7. 文言はすべて `t()`。ja.json と en.json に同じキー。`authErrorMessage.ts` は、口と状態コード（F30）から文言キーを 1 つ選ぶ表を持つ。
   - 401 → ログインの誤り（1 文。理由を区別しない）
   - 403 → 画面を開き直してやり直す案内
   - 404 → 今は使えない
   - 429 → しばらく待つ
   - 400 → 口ごとに別キー。再設定ページは「リンクが無効か期限切れ」、パスワード変更は「今のパスワードが違う」
   - 422 → detail のコード（`password_too_short`・`password_too_long`・`password_too_common`）ごとに 1 キー。detail は決まった識別子なので読む。それ以外の本文の文章は読まない。FastAPI の入力検査の 422（detail が配列）は共通の 1 文
   - それ以外とネットワーク不通 → 共通の 1 文
8. e2e の迂回: 開発サーバー（`import.meta.env.DEV`）のときだけ。self のときも同じ `window.__salesanchorE2eAuthUser` を読み、固定トークンを返す

### 4.3 便4b

1. deploy.yml: 消す一覧に `AUTH_PROVIDER`・`AUTH_JWT_SECRET`・`VITE_AUTH_PROVIDER` の 3 キーを足す。heredoc に、既存の行と同じく値を単一引用符で囲んで `AUTH_PROVIDER='self'`・`AUTH_JWT_SECRET='${{ secrets.AUTH_JWT_SECRET }}'`・`VITE_AUTH_PROVIDER='self'` を足す（deploy.yml:350-365 の書き方）。`AUTH_PASSWORD_RESET_ALLOWLIST` は heredoc の :361 だけを消し、消す一覧の :311 は残す（.env に古い行を残さないため。F28）
2. docker-compose.yml: backend の environment に `AUTH_PROVIDER`・`AUTH_JWT_SECRET`（既定は `:-firebase`・`:-`）。:134 の ALLOWLIST の行を消す。frontend の build args に `VITE_AUTH_PROVIDER=${VITE_AUTH_PROVIDER:-firebase}`
3. frontend/Dockerfile: `ARG VITE_AUTH_PROVIDER`・`ENV`
4. 発行スクリプト: 対象は is_active かつ hash NULL の人。`--apply` なしは件数だけを**標準エラー**に出し、書かない。`--apply` は 1 つのトランザクションで、運営の文脈（`SET LOCAL app.is_operator` を true。F22）を設定し、1 人ずつ 20 文字のパスワードを作って Argon2id で保存する（UPDATE の条件に `AND password_argon2_hash IS NULL` を付ける）。UPDATE の件数が 1 でない人が 1 人でもいたら全部取り消して終わる（何も出力しない）。コミットが成功してから、design.md:164 の 3 列（タブ区切り）を標準出力へ出す。件数は標準エラーへ。コミットの前に切れたときは DB は取り消されているので、もう一度 `--apply` から。コミットの後に出力の途中で切れたときは、パスワードは DB に入ったが手元に無い。2 回目は 0 件になるので、その人たちには PO が再設定メールを送る（ログイン画面の「パスワードを忘れた」）。PO の Mac から呼ぶ `ssh` に `-t` を付けない（端末を割り当てると出力が崩れる）
4-2. 戻し方（F20）: 便4b は revert しない。heredoc の `AUTH_PROVIDER` と `VITE_AUTH_PROVIDER` を `firebase` に変える前進 PR（消す一覧は残す）をマージして deploy する
5. 起動の仕方は、backend のコンテナの中で `python -m scripts.issue_initial_passwords`。本番の命令（機体・鍵・コンテナ名）は、切り替え日に Opus が本番を読み取って決め、PO への別紙に書く。F15 のとおり実例が無いので、便4b のテストで `-m` 実行を確かめる（6. 分岐 B3）

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る）

便4a:
- `cd backend && pytest tests/test_self_auth.py tests/test_password_reset.py tests/test_register_invite.py -q`。試験に入れる項目:
  - password/change: 成功の応答の新アクセストークンで保護された口が 200／古い更新用トークンの refresh が 401／古いアクセストークンは Redis の保持なし（試験で保持を空にする）の状態で 401（保持中は最大 300 秒通る。F31。K8 の注記）／照合失敗で `failed_login_count` が 1 増え 400 `invalid_credentials`／新パスワード 14 文字で 422 `password_too_short`／Origin 違いで 403／firebase（秘密なし）では `get_current_user` を差し替えて呼び、新トークンも Cookie も返さず、更新用トークンの失効だけ行う／hash が NULL の人は 400
  - register と担当者の追加: self のとき invite の鍵が 1 行・送信関数の呼び出し 1 回（送信関数を差し替えて数える）／firebase のとき鍵 0 行・送信 0 回／既存の利用者を使った担当者の追加は鍵 0 行・送信 0 回
- `cd frontend && npx vitest run src/pages/login src/pages/reset-password src/pages/account-settings src/lib/auth`
- `cd frontend && npx tsc --noEmit`・`npm run lint`・`npm run build`
- `git grep -n "VITE_AUTH_PROVIDER" -- frontend/src` が `provider.ts` だけ
- 変更した画面ファイルに `grep -nE "<button|<input|#[0-9a-fA-F]{3,6}\b|rgb\("` で 0 件（`ui-allow:` の例外コメント付きを除く。design.md:205）
- `cd frontend && npm run check:i18n-missing-keys` が通る（ja/en のキー差分 0）
- `git grep -n "localStorage\|sessionStorage" -- frontend/src/lib/auth` が 0 件
- e2e（`Frontend E2E (Playwright)`。開発サーバーで動く）が VITE_AUTH_PROVIDER 無しで今と同じく通る
- `provider.ts` の単体試験: 未設定・`firebase`・`SELF`・空文字は firebase、`self` だけ self
- 画面の試験: firebase のときのログインは Firebase の関数を呼び、`/api/v1/auth/login` を呼ばない。本番での確かめは K0（login 404）
- 画面の試験（§4.2 3-1）: `/api/v1/auth/` の口の 401 では refresh しない／それ以外の口の 401 で refresh 1 回・元の要求の送り直し 1 回／送り直しの 401 でログイン画面へ
- `cd backend && pytest tests/test_staff*.py -q`（新しい利用者のときだけ鍵 1 行・既存のときは 0 行）

便4b:
- `cd backend && pytest tests/test_issue_initial_passwords.py -q`（`--apply` なしで書かない・`--apply` で件数分の行・2 回目は 0 件・件数は標準エラー）。RLS の試験は F26 の型で `RLS_TEST_DATABASE_URL` を使い、スーパーユーザーの接続では行わない。ログ（caplog）とファイルへの書き込みに、作ったパスワードの平文が 0 件であること（K11）
- `cd backend && python -m scripts.issue_initial_passwords --help` が動く
- deploy.yml の消す一覧と heredoc の両方に新しいキーがあることを grep で示す

## 6. 分岐ごとの対処

| # | こうなったら | どうする |
|---|---|---|
| B1 | `secondary` では画面の作りに合わない | 新しい見た目を足さずに止め、Opus へ（金型の追加は PO 判断） |
| B2 | 5 か所以外にトークン取得が見つかった | 同じ `getAccessToken()` に寄せる。触るファイルに足して報告 |
| B3 | `python -m scripts.X` が動かない | `__init__.py` を足して動けばそれで可。ほかの方法は止めて Opus へ |
| B4 | 便4a のマージ後に、ボタンの見た目以外が変わった（ログインの口が Firebase 以外を呼ぶなど） | 初期値が firebase になっていない。すぐ revert |
| B7 | `navigator.locks` が無いブラウザ | 同じタブの中の 1 本化だけで動かす。報告に書く |
| B5 | 発行の試し実行の件数が、PO が決めた対象者数（§11）と違う | 件数で止めて Opus へ。Opus は読み取りで差を確かめ、PO に聞く |
| B6 | テストで `public.` の付いた表が SQLite に無い | 便3 の conftest の置換に足す |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K0（便4a）: マージ後も本番のログインは今と同じ | deploy 後、本番で login 404（F1）・PO が今のパスワードでログインできる |
| K1: 発行ファイルの行数＝試し実行の件数。対象者全員が新パスワードでログインできる | `wc -l`（値は見ない）。切り替え時刻より後に `last_login` が入った使用中の利用者の数（F5） |
| K2: 画面の文言のハードコード 0 件・生ボタン 0 件 | §5 便4a の grep（生の部品と色の直書き）と `npm run check:i18n-missing-keys` |
| K3: アクセストークンをブラウザの保存領域に置かない | §5 の grep と、画面の開発者ツールで localStorage にトークンが無い |
| K4: 再設定の実演 | 試験の利用者（id 86 を再び有効にする。PO 同意）で、再設定ページから新パスワードを設定してログイン |
| K5: 戻せる | 戻しの前進 PR（§4.3 4-2）の差分を便4b の PR 本文に書いておく。deploy 後に backend の `AUTH_PROVIDER` が firebase になることを確かめる手順も書く（実行は戻すときだけ） |
| K6: 同時の refresh で落ちない・往復しない | 画面の試験で、同じタブで 3 本同時に API を呼び 401 が返ったとき refresh が 1 回だけ送られる。`/api/v1/auth/` の口の 401 では refresh しない。送り直しは 1 回（§4.2 3-1） |
| K7: 発行が DB に入る | 発行スクリプトの試験で、運営の文脈なしなら全部取り消され出力が 0 行、ありなら件数分入ることを、F26 の salesanchor_app の接続で確かめる（スーパーユーザーや SQLite では RLS を確かめられない） |
| K8: パスワード変更後、古い端末のアクセストークンは最大 5 分で拒否、更新用トークンは即時失効（design.md:200） | 結合テスト（§5 便4a の password/change の項目）。「最大 5 分」は Redis の保持 300 秒（F31）なので、試験は保持なしで 401 を示し、保持中に通ることは注記に書く |
| K9: 新しい利用者に初回設定メールが届き、リンクでパスワードを決めてログインできる（design.md:202） | 便4b の後、便3 の試験と同じ置き場（試験用の会社 tenant 6・便3 の試験用 Gmail の別名）に、PO の同意で試験の利用者を作って実演 |
| K10: ログイン画面の 2 つのボタンが枠付きの補助ボタンになる（design.md:206） | Evaluator の画面写真を PO が見る |
| K11: 発行スクリプトがサーバーに平文を残さない（design.md:208） | 試験は §5 便4b（caplog とファイル書き込みに平文 0 件）。本番は、PO の Mac から発行ファイルの値を標準入力で渡し、サーバーの /tmp とアプリのログで一致した件数だけを返す読み取りの命令（値は画面に出さない）を、Opus が別紙で渡す。件数 0 で合格 |
| K13: SMOKE_SERVICE_TOKEN の経路が今のまま動く（design.md の受け入れ基準） | 便4b の deploy 後、既存の FedEx smoke（`scripts/smoke/external-fedex.sh`）が緑。照合は `AUTH_PROVIDER` より前に行う（F34） |
| K12: 2 つのタブで同時に refresh しても落ちない | 画面の試験で、2 つのタブを模した同時の refresh が 1 回ずつ順番に送られる |

## 8. 反映の順番と PO の作業

（１）便4a をマージする（危険パスなし）。deploy 後に K0 を確かめる
（２）PO が切り替え日と告知の文を決める（design.md:140・:221）。使う人 8 人へ前もって知らせる
（３）PO が GitHub の secret に `AUTH_JWT_SECRET`（32 文字以上・閲覧者の鍵と別の値）を登録する。手順は Opus が別紙で渡す
（４）切り替え日に、便4b の PR を Opus が提示し、PO の「GO #PR番号」を受けてマージする
（５）deploy 後、PO が自分の Mac で発行スクリプトを実行する（design.md:162-167。umask 077・ファイルは 600・配り終えたら消す）。先に `--apply` なしで件数を見る（B5）
（６）PO が 8 人にパスワードを渡す。Opus が K1・K4 を確かめる

## 9. 戻し方

- 便4a: revert PR をマージ。初期値が firebase なので利用者への影響は無い
- 便4b: revert はしない（F20。backend が self のまま残る）。§4.3 4-2 の前進 PR をマージし deploy。前進 PR は deploy.yml を触る危険 PR なので、ADR-136 の PO の「GO #PR番号」が要る。入れない人が出ている本番障害のときは、CLAUDE.md の緊急の手順（PR タイトルに `EMERGENCY:` と理由・PO に即時報告・24 時間以内に事後の承認と記録。`docs/BRANCH_PROTECTION_SETUP.md` §4）に従う。Firebase の利用者と元のパスワードは便6 まで残るので、元どおりログインできる。便4b のあとに登録した人は戻すと入れない。戻す前に人数を読み取りで確かめる
- 便4b の deploy で自動の戻し（F27）が起きたとき: コードは前の版に戻り、compose で起動する。画面は VITE_AUTH_PROVIDER 無しで作り直されるので firebase。backend は compose の environment に AUTH_PROVIDER が無い版なので firebase。.env には self の行が残る。deploy を止める仕組みは無い（F33）ので、別の PR が main に入ると便4b がそのまま deploy され、初回パスワードの発行前なら使う人 8 人全員が入れなくなる。そこで Opus は自動の戻しを見たら、すぐに §4.3 4-2 の前進 PR（firebase に戻す）を作り、次に main に入る PR をそれにする。ほかの PR のマージは、その前進 PR の deploy が終わるまで待ってもらう（active-work に書く）。そのあと本番の backend の AUTH_PROVIDER が firebase であることを読み取りで確かめる。便4b の直しは、その後に新しい PR で出し直す

## 10. PR

- 便4a: `release/auth-b4a-self-login-ui`。区分は通常（危険パスなし）。reviewer の APPROVE と CI 全部で Opus がマージ
- 便4b: `release/auth-b4b-switch`。危険便。ADR-136 の GO 記録を PR 本文に残す

## 11. 未解決（審査で確かめる）

- id 2（Firebase に居ない使用中の利用者）を発行の対象にするか（PO 判断）。対象にすると、戻したときに入れなくなる人に数える
- 便を 4a・4b に分けること（PO の合意）
- 担当者の追加で新しくできた利用者にも初回設定メールを送ること（design.md に無い追加。PO の合意）
- 切り替え日と告知の文（PO 判断）
- F17 パスワードを持つ人の数（発行スクリプトの試し実行で分かる）

## 12. 報告欄（担当が追記）

END OF CARD
