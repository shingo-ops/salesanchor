# design: Firebase を画面とサーバーから全部外す（ADR-1013 便6）

- 書いた日: 2026-11-04（Opus）
- 状態: 設計案作成済み → 自己審査（§10）済み → クラウドの設計審査 1 回目 REVISE・2 回目 REVISE（重い指摘 0・中 2・軽い 5。2026-11-04）→ 3 回目 APPROVE（重い・中 0、軽い 2 は直した。2026-11-04）→ PO 承認済み（2026-11-04「1」。PO の原文は「1、推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ。また配線とDBのSSOTは遵守してデータを分散させることは禁止。フロントエンドのパーツもデザイントークンとデザインシステム を遵守して、金型登録のないハードコードを禁止する。推測で自身で判断したり不透明無まま進めることは禁止、分からないことは聞いてくれ。確立したなら進める。」）→ 便1 のカード発行済み（`docs/handoff/firebase-removal/card-1.md`、card-lint 合格）→ 便1 本番反映済み → 便2 は PO 承認（2026-11-05「1」）を受けてカード発行済み（`docs/handoff/firebase-removal/card-2.md`、card-lint 合格）。便2 は #5145 でマージ・本番反映済み（2026-11-05 14:31 JST に deploy 完了）。本番の確かめ: K2 は本番の backend で `import firebase_admin` が ModuleNotFoundError（○）。K4 は Google の部品の読み込みが通り、celery の worker で `sync_google_calendar_all` が 14:50・15:05 JST に `succeeded`（2 回）、同じ時間に ImportError・ModuleNotFoundError 0 件（○。別の deploy で worker が 14:35 JST に入れ替わったため、2 回目は便2 の deploy 完了から 34 分後）。K3 は deploy 内の smoke 14 件が全部 PASS、本番で札の更新 `POST /api/v1/auth/refresh` が 200（2 件）。次は便3（PO の開始の判断を待つ）。便5 は戻せないので、実行の直前に改めて PO の GO をもらう。
- PO の進める判断: 2026-11-04「1」。Opus が出した選択肢は「Firebase を画面とサーバーから全部外す設計に進む【おすすめ】　裏口のもとになる部品がなくなります。Firebase に残っている利用者の削除は元に戻せないので、その前に改めて確認をお願いします。」。
- 「」で囲み区切りを全角の ／ にした道筋は、画面から Firebase を外す変更（release/firebase-removal-bin1）で消したファイル（消したので今の版には無く、引用の自動点検の対象から外している）。
- 根拠: [recon.md](./recon.md)（`docs/handoff/firebase-removal/recon.md`。以下 R 番号はこの recon を指す）。
- 親 ADR: ADR-1013（Decision 6・Consequences）。前の便: `docs/handoff/block-firebase-token/design.md`。元の便6 の行: `docs/handoff/auth-self-hosted-passkey/design.md:160`。

## 1. 目的（PO の言葉で）

Firebase は使わない設定に切り替えた（PO 2026-11-04「firebaseは使わない設定に切り替えている」）。11/4 にサーバーは Firebase の札を断るようにした（#5118）。それでも Firebase の部品は画面にもサーバーにも残っていて、裏口のもとになりうる（R1・R11）。ログインの情報が Firebase と自社の 2 か所に分かれている状態も、PO の「データを分散させない」に反する（ADR-1013 Why）。

これを、部品・配線・データ・外部の利用者の順に外し、ログインを自社 1 か所にする。

利用者から見た変化は無い。画面はもう自社のログインしか使っていないからだ（R12・R24）。

## 2. 成功条件（○×で判定できる形）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 本番の画面のファイルに Firebase の部品が入っていない | CI: `npm run build` で作った `frontend/dist` のすべての `.js`（本体と閲覧ページ）で、`firebase`・`identitytoolkit`・`securetoken`・`googleapis`・`gstatic` の 5 語（大小無視）を数え、合計 0 件（コマンドは「維持の仕組み」）。本番: 便1 の deploy 後、本番の `index.html` と `viewer/index.html` が読む JS を全部取って同じ数え方で 0 件（今は main だけで `firebase` 88 件・`googleapis` 5 件。R27）。Storybook の出力は `frontend/dist` に入らないので対象外 |
| K2 | サーバーに Firebase の部品が入っていない | 便2 の後、`backend/requirements.txt` に `firebase-admin` が無い。本番の backend で `python -c "import firebase_admin"` が失敗する（ModuleNotFoundError） |
| K3 | 自社ログイン・パスキー・パスワード再設定・新しい機械の許可が今までどおり動く | 各便の deploy 後に deploy 内の smoke が緑。PO がいつもどおりログインして画面を開ける。backend の試験 `backend/tests/test_self_auth.py`・`backend/tests/test_passkeys.py`・`backend/tests/test_password_reset.py`・`backend/tests/test_new_device_approval.py` が全件緑 |
| K4 | Google カレンダー・Drive・表の書き出し・Gemini が今までどおり動く | 便2 の CI で、firebase-admin を抜いて入れ直した環境で `python -c "import google.oauth2.credentials, google.oauth2.service_account, google.auth.transport.requests, googleapiclient.discovery, googleapiclient.http, googleapiclient.errors, google_auth_oauthlib.flow, gspread, google.genai, google.generativeai"` が通る（R30 の全部。recon U1 を機械で確かめる）。deploy 後 30 分以内に、celery の worker のログで 15 分おきの `app.tasks.google_calendar_sync.sync_google_calendar_all`（`backend/app/celery_app.py:210`）が `succeeded` を 2 回以上出し、同じ時間に `ImportError`・`ModuleNotFoundError` が 0 件 |
| K5 | 開発サーバーと e2e が、Firebase なしで今までどおりログインした状態で動く | e2e・karte-gate の workflow が緑。どちらも偽の `VITE_FIREBASE_*`・`VITE_GCP_PROJECT_ID` を渡さない。開発での動き方は §5-1 の表のとおり |
| K6 | 本番のビルドに開発用の偽ログインが入っていない | CI: `frontend/dist` のすべての `.js` で、`__salesanchorE2eAuthUser`・`e2e-auth-user`・`e2e-firebase-auth-user`・`e2e-fake` の 4 語を数え、合計 0 件（今の本番は 4 件入っている。R27） |
| K7 | `staff.firebase_uid` の列がどの会社の表にも無い | 便4 の後、reader 鍵で `information_schema.columns` を数え 0 件。ai_cloud の `build_log` の最新行が ok |
| K8 | Firebase の利用者が 0 人で、ログインの入口が全部止まっている | 便5 の後、PO が Firebase の画面で利用者の数 0 と、ログインの方法（メールとパスワード・Google ほか）が全部「無効」を確かめる（画像）。画面用の API キーは消えているか、Firebase のログインに使えないよう制限されている（画像）。削除の前に暗号化した書き出しが PO の Mac にある |
| K9 | リポジトリに Firebase の文字が、認めた例外の他に無い | 全便の後、`git grep -il firebase -- . ':!docs'` の結果が §8-2 の例外の一覧と一致する。§8-1 の割り当て表で、今ある 120 個のファイルはすべて、どれかの便か例外に入っている |

## 3. 対象と対象外

対象: R1〜R19 の部品・配線・試験・運用スクリプト・監視の板、`staff.firebase_uid` の列、Firebase の利用者、Firebase だけに使う秘密。

対象外（触らない）:
- GCP プロジェクト `sales-ops-with-claude` そのもの。Google カレンダーの OAuth が使っている（R25）。
- `bcrypt`。ボットの API キーの保管が使っている（R6）。元の設計 `docs/handoff/auth-self-hosted-passkey/design.md:160` の「`bcrypt` の除去」は誤りなので、この設計で取り消す（§9）。
- 古い qa-smoke の資産（`.github/workflows/qa-smoke.yml`・`scripts/qa/reset-tenant.sh`・`tests/qa-smoke/`・QA_* の secrets）。持ち主は ADR-1051 D5 で、新しい点検が 14 日続けて合格した後に消す。ただし `scripts/qa/seed-tenant.sql` は、便4 で列が無くなると手で動かしたときに失敗するので、便4 で INSERT から列だけを外す（R31・§5-4）。
- `.github/workflows/external-state-snapshot.yml` の GCP の段と、secret `GOOGLE_APPLICATION_CREDENTIALS_JSON`（GCP の段が使う。R19）。
- 過去の migration（`migrations/019_create_staff_tables.sql`・`migrations/20260612_150000_drop_password_hash.sql`）。過去の記録なので書き換えない。

## 4. 便の分け方と順序

1 便ずつ、変更 → 本番反映 → 確かめ → 次の便、の順で進める。便1〜便4 は revert で戻せる。便5 だけ戻せない。

| 便 | 中身 | 危険の区分 | 戻し方 |
|---|---|---|---|
| 便1 画面 | §5-1 | 通常（frontend と e2e の workflow だけ） | PR を revert |
| 便2 サーバーのコードと運用スクリプト | §5-2 | 危険（リポジトリ直下の `scripts/`） | PR を revert |
| 便3 配線 | §5-3 | 危険（`docker-compose.yml`・`.github/workflows/deploy.yml`・`scripts/blue-green-cutover.sh`・nginx） | PR を revert |
| 便4 DB の列 | §5-4 | 危険（`migrations/`） | 列を足し直す前進の migration（値は戻らない。R26 のとおり使い道の無い 1 件だけ） |
| 便5 外部の片付け | §5-5 | **不可逆**（外部の画面・secrets） | 戻せない。書き出しから作り直す道だけ残す |

順序の理由:
- 便1 が先。画面が Firebase を読まなくなってから、配線（便3）の値を外す。逆だと、画面の Firebase の初期化が値なしで失敗し、画面全体が開かなくなる。
- 便2 は便4 より先。運用スクリプトが `firebase_uid` を書かなくなってから列を消す（R9・R19 の `scripts/setup_review_tenant.py:256`・`:273`）。
- 便3 は便1・便2 の後。部品を読む所が無くなってから値と鍵のマウントを外す。
- 便5 は最後。便1〜便4 の本番反映から 7 日、ログインの不具合が 0 件であることを確かめてから、PO に改めて削除の確認をもらう。
- 戻すときは逆の順（便4→便3→便2→便1）。便3 を残したまま便1 だけを revert すると、画面が値なしで Firebase を初期化して開かなくなるため。
- サーバーの `.env` の `VITE_FIREBASE_*` と、サーバー上の鍵のファイルは、便5 まで消さない。便1〜便4 を戻す道を残すため。

## 5. 変更の前と後（便ごと）

各便の前に実装カード（「docs/handoff/firebase-removal/card-N.md」）を作る。カードには、ファイル:行、変更の前後、触らない範囲、試験を書く。この章は便の範囲と決めごとまでを書く。

### 5-1. 便1 画面

- 消すファイル: 「frontend／src／lib／firebase.ts」、「frontend／src／lib／firebase-auth.ts」、「frontend／src／lib／firebaseErrorMessage.ts」 とその試験、「frontend／src／lib／__storybook-mocks__／firebase-app.ts」・「frontend／src／lib／__storybook-mocks__／firebase-auth.ts」。
- `frontend/package.json:84` の `firebase` と、lock の中身を消す。
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の `firebaseError` の塊（便1 の基準 0f297666c で :3289）を消す。両方から同じキーを消す（ADR-027）。
- `frontend/.storybook/main.ts:34-35` の差し替えを消す。
- `frontend/src/test-setup.ts` の firebase の差し替えを消す。`frontend/vite.config.ts` の注記を直す。
- スイッチ: 「frontend／src／lib／auth／provider.ts」 とその試験を消す。`isSelfAuth()` を使う 10 か所（R12）は、下の「開発での動き方」の表に合わせて書き換える。
  - `frontend/src/contexts/AuthContext.tsx`: Firebase の分岐（`onAuthStateChanged`・`sendPasswordResetEmail` ほか）を消す。
  - `frontend/src/lib/auth/selfAuth.ts:224`・`:236`: Firebase に戻る道を消す。
  - `frontend/src/pages/login/LoginPage.tsx:44`: `authErrorMessage` だけを使う。
  - `frontend/src/pages/account-settings/SecuritySection.tsx:262` 付近: Firebase の再認証とパスワード変更の分岐を消し、常に自社の `/auth/password/change` を使う。
- 開発サーバーと e2e の偽ログイン（`devSession`）:
  - 置き場: 「frontend/src/lib/auth/devSession.ts」（新設）。今の偽物（R11）と同じく `window.__salesanchorE2eAuthUser` と保存の鍵を読む。保存の鍵の名前は `salesanchor:e2e-auth-user` に変える。
  - 受け口の置き場（カード作成時に改めた。2026-11-04）: 受け口は `frontend/src/lib/auth/selfAuth.ts` ではなく、新設の 「frontend/src/lib/auth/devSessionSlot.ts」 に置く。中身は型（`DevSessionUser`・`DevSessionAdapter`）と `registerDevSession()`・`isDevSession()`・`getDevSession()` だけで、偽ログインの文字は持たない。理由: 試験の土台（`frontend/src/test-setup.ts`）が受け口に登録する一方、9 つの試験が `selfAuth` を `vi.mock` で差し替えている。Vitest の資料（Context7 `/vitest-dev/vitest`）に「setup file の中で import したモジュールはキャッシュされるので差し替えられない」とあり、受け口を `frontend/src/lib/auth/selfAuth.ts` に置くと、土台の登録と試験の差し替えがぶつかる。受け口を別のファイルにすれば、`selfAuth` を差し替える試験も、受け口の登録をそのまま使える。
  - 読み込み方: `frontend/src/main.tsx` で `if (import.meta.env.DEV)` の中だけ `import("./lib/auth/devSession")` で読み込み、受け口に登録してから画面を描く（`frontend/tsconfig.json` の target が ES2020 なので、ファイルの一番外の `await` は使わず、`async function bootstrap()` の中で行う）。本番では受け口は空のまま。静的な import は使わない。R27 のとおり、静的に読み込むと `import.meta.env.DEV` で分けても文字がビルドに残るため。
  - 開発かどうかの判定は 1 つにする: 受け口の `isDevSession()`（登録されているか）を、他の所はこれだけを見る。`import.meta.env.DEV` を直接見る所は `frontend/src/main.tsx` の 1 か所だけにする。
  - 試験の土台: `frontend/src/test-setup.ts` は firebase の差し替えを消し、`devSession` の偽ログインを「札は出さない（`getAccessToken` は未ログインの誤り、`hasSession` は false）」形で登録する。今の試験の状態（画面は開発用の利用者で開くが、札は無い）と同じにするため。自社ログインの動きを試す試験は `beforeEach` で `registerDevSession(null)` を呼ぶ。札が要る試験（`SharedButtonMigration`・`RealtimeProvider`・`api.httpError`）は、札を返す偽ログインを `beforeEach` で登録し直す。
  - Storybook: `frontend/.storybook/preview.tsx` で `devSession` を登録する。Storybook の出力は `frontend/dist` に入らない（K1・K6 の対象外）。
  - 入っていないことは K6 の grep で確かめ、推測に頼らない。K6 が 0 件にならないときは、実装役は止まって Opus に戻す（代わりの方法は Opus が決める）。
- 開発での動き方（今と外した後。本番は自社ログインで、今と同じ）:

| 機能 | 今の開発（`isSelfAuth()` が false） | 外した後の開発（`isDevSession()` が true） |
|---|---|---|
| ログインの状態・ログイン・ログアウト | Firebase の偽物（「frontend／src／lib／firebase-auth.ts」） | `devSession` が同じ動きをする（seed と保存の鍵を読む。ログインは `e2e-<メールの@より前>` の利用者を作る） |
| API に付ける札（`getAccessToken`）・ログイン中か（`hasSession`） | 偽物が `e2e-fake-id-token` を返す | `devSession` が `e2e-fake-id-token` を返す |
| 401 の送り直し（`frontend/src/lib/api.ts:83`） | しない | しない（`isDevSession()` なら今と同じくそのまま返す） |
| パスキーのボタン（`frontend/src/lib/auth/passkey.ts:23`） | 出さない | 出さない |
| 新しい機械の許可の見張り（「frontend／src／features／auth／LoginApprovalWatcher.tsx」の 34 行目（便1で削除））・回復コードの案内（`frontend/src/features/auth/RecoveryCodePrompt.tsx:61`） | 動かない | 動かない |
| セキュリティの 4 つの欄（`frontend/src/pages/account-settings/SecuritySection.tsx:366-369`） | 出さない | 出さない |
| パスワード変更（`frontend/src/pages/account-settings/SecuritySection.tsx:262`） | 偽物の再認証を通る | 自社の API を呼ぶ。e2e にこの試験は無い（R28） |
| パスワード再設定の申し込み | 偽物が何もせず成功 | 自社の API（`/password-reset/request`）を呼ぶ。`frontend/tests-e2e/login.spec.ts:51` の差し替え先をこの宛先に変える（R29） |
| ログイン画面の誤りの文 | `firebaseErrorMessage` | `authErrorMessage` |

- e2e の付け替え: `frontend/tests-e2e/utils/auth.ts:23`・`:31` を新しい保存の鍵に合わせる。注記だけの `frontend/tests-e2e/scene1-dashboard.spec.ts:370`・`frontend/tests-e2e/visual-language/viewer-focus-trap.spec.ts:83`・`frontend/tests-e2e/visual-language/viewer-helpers.ts:8` の文を直す（R32）。
- 試験: `vi.mock` で firebase を差し替える 14 ファイル（R15）と、`provider` を差し替える試験を、`selfAuth` か `devSession` の差し替えに直す。
- 注記だけの所（R32）: `frontend/src/contexts/UiPrefsContext.tsx:46`・`frontend/src/lib/query/QueryAuthSync.tsx:3`・`frontend/src/lib/api.ts:3`・`:41`・`:73`・`frontend/src/lib/auth/authErrorMessage.ts:4` の文を事実に合わせて直す。
- 設定: `frontend/playwright.config.ts:149-152`、`.github/workflows/e2e.yml:202-204`・`:308-311`、`.github/workflows/karte-gate.yml:73-75`・`:83-85`・`:108-110` から偽の `VITE_FIREBASE_*` と `VITE_GCP_PROJECT_ID` を消す。`VITE_GCP_PROJECT_ID` を画面で読むのは 「frontend／src／lib／firebase.ts」の 21 行目 だけ。
- CI に K1・K6 の数え方の段を足す（「維持の仕組み」）。
- CSP はこの便では触らない（便3）。
- 金型・i18n: 新しい画面の部品は作らない。文言は既存の `authError` 系のキーを使い、新しいキーは足さない。足す場合は ja・en 両方に足す。

### 5-2. 便2 サーバーのコードと運用スクリプト

- `backend/requirements.txt:13` の `firebase-admin` を消す。`bcrypt` は残す（R6）。
- `backend/app/auth/dependencies.py`:
  - :8・:11・:12 の import、:50-70 の `_init_firebase` と :155 の呼び出しを消す。
  - Firebase の確かめの分岐を消し、自社の札でなければ常に `_reject_self_token` で 401 にする（#5118 の断り方と同じ。新しい文言は作らない）。
  - 回数制限・失効の一覧・smoke の順序（ADR-127・ADR-1017・ADR-1055）は変えない。
- `backend/app/auth/self_tokens.py`:
  - スイッチ（:21・:39-40・:81-85）を外す。
  - `is_issuance_enabled()` は「秘密があるか」だけで決める。
  - `validate_settings()` は、本番（`ENVIRONMENT=production`）で `AUTH_JWT_SECRET` が無ければ起動を止める。
- スイッチを読む所（R3）は、自社ログインの側だけを残す。`backend/app/services/invite.py:20-21` は常に初回設定のメールを作る。
- `backend/app/auth/utils.py:13-15` の `set_tenant_claim` を消す。`generate_password` は残す（R4）。
- `backend/app/schemas/auth.py:19` の説明文（「上流のFirebase Auth側で担保される」）を直す。この型に `firebase_uid` は無く、API の形は変わらない。
- 注記だけの所（R10・R32）の文を、事実に合わせて直す。`backend/app/main.py:183` の注記を直し、`:184` の `self_tokens.validate_settings()` の呼び出しは残す。ほかに `backend/app/cache.py`・`backend/app/line_device_admin.py`・`backend/app/middleware/session_guard.py`・`backend/app/routers/leads.py`・`backend/app/routers/line_import_devices.py`・`backend/app/routers/staff.py`・`backend/app/routers/auth.py`・`backend/app/services/review_mail_notifier.py` の Firebase の文字を、カードで 1 行ずつ「コード」か「注記」かを分けて直す。
- API の説明文が変わる（`backend/app/schemas/auth.py:19`・`backend/app/routers/auth.py:80`・`:186`・`backend/app/routers/staff.py:265-271` の文が `frontend/api-contract/openapi.json:37858`・`:41323`・`:41950`・`:58540` の description になっている）ので、`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で `frontend/api-contract/openapi.json` を作り直して同じ PR に入れる（`.github/workflows/api-contract-check.yml:35`・`:53`）。
- 運用スクリプト（R4・R8・R19）:
  - `scripts/setup_review_tenant.py`: Firebase の利用者を作る所を、`backend/app/auth/passwords.py:20` の `hash_password` で `users.password_argon2_hash` を書く形に変える。Firebase を使う関数（`_init_firebase`・`_firebase_get_uid`・`_firebase_create_user`・`_firebase_update_password`）は関数ごと消し、`firebase_uid` を受け渡す所（:231・:256・:273・:289・:351・:369・:483・:487・:491）と注記（:18・:24・:37・:296・:455・:459・:469・:490）も消す。終わりの条件は「このファイルの `firebase`（大小無視）が 0 件」（import :55-56・見出し :93・:350・:352・呼ぶ所 :472-480 も含む）。すでにいる利用者かどうかは `users` で判定し、`password_argon2_hash` は新しく作るときか、`ALLOW_REVIEW_TENANT_PASSWORD_RESET` を指定したときだけ書く（今の動き `:452-487` を引き継ぐ）。`backend/tests/test_setup_review_tenant.py` を合わせる。
  - 「scripts／setup_single_test_user.py」・「scripts／setup_test_users.py」: 消す。呼ぶ所はリポジトリに無く、中身は Firebase の利用者を作ることだけ（R19 の検索）。
  - `scripts/setup_tenant.py:29`・`:471`: 「Firebase ユーザーを作る」の案内を、初回設定メールの案内に直す。
  - `backend/scripts/CLAUDE.md`・`backend/AGENTS.md:8` の手順を合わせる。
- 試験: Firebase の既定に頼る試験（R21 の 15 ファイル）と、Firebase の文字がある次の試験を直す: `backend/tests/test_client_ip.py`・`backend/tests/test_event_loop_nonblocking.py`・`backend/tests/test_export_inventory_for_sheet.py`・`backend/tests/test_line_import_devices.py`・`backend/tests/test_review_mail_notifier.py`・`backend/tests/test_security_hardening.py`・`backend/tests/test_smoke_auth_least_privilege.py`・`backend/tests/test_viewer_isolation.py`・`backend/tests/test_register_invite.py`・`backend/tests/conftest.py`（列の足場 :512 は便4）。#5118 で足した T1・T2・T6 は、Firebase の分岐が無くなるので「自社以外の札は 401」の試験に置き換える。
- K4 の import の確かめ（R30 の 10 個）を、firebase-admin を抜いて入れ直した環境で流す段として CI に足す。通らないものは、その部品を `backend/requirements.txt` に直接書いて直す。

### 5-3. 便3 配線

- `docker-compose.yml`:
  - :69・:241 の `GOOGLE_APPLICATION_CREDENTIALS` を消す。
  - :161・:298 の鍵のマウントを消す。
  - :201-203 の VITE_FIREBASE と GCP の build args を消す。
  - :136・:205 の `AUTH_PROVIDER` と `VITE_AUTH_PROVIDER` を消す。
- `scripts/blue-green-cutover.sh:94`・`:99` を消す。
- `frontend/Dockerfile:7-9`・`:12-14`（VITE_FIREBASE と VITE_GCP_PROJECT_ID）と `:11`・`:16`（VITE_AUTH_PROVIDER）の ARG と ENV を消す。`:10`・`:15` の `VITE_FUNNEL_DASHBOARD` は残す。
- `.github/workflows/deploy.yml`:
  - :378・:380 の `AUTH_PROVIDER='self'` と `VITE_AUTH_PROVIDER='self'` を書く行を消す。
  - :318・:320 の消す行は残す。古い値を `.env` から消し続けるため。
- `nginx/nginx.conf:96`（app.salesanchor.jp の塊）の CSP から `https://www.gstatic.com`、`https://*.googleapis.com`、`https://*.firebaseio.com` を外す。便1 の本番反映後、本番の画面の JS にこれらへの通信が 0 件であることを K1 で確かめてから外す。
- 運用と監視:
  - `.github/workflows/external-state-snapshot.yml:82-88`（Firebase の段）を消す。GCP の段は残す。
  - `.github/workflows/rotate-qa-firebase.yml`、`scripts/snapshot/firebase.sh`、`scripts/smoke/external-firebase.sh` を消す。
  - `docs/external-state-contract.yml:29-37` を消す。
  - `scripts/detect-external-api-change.js:84-89` とその試験から Firebase の見張りを消す。
  - `monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json:124-132` の板を消す。
  - `.env.example`・`frontend/.env.example` から Firebase の項目を消す。GCP カレンダーの項目（R25）は残す。
  - `.gitleaks.toml:38-40` の偽の値の例外を消す。
  - `backend/.dockerignore:14`・`.gitignore:29-30` は残す。鍵のファイルを誤って上げないための守りなので、§8-2 の例外にする。
- 危険 PR の GO（ADR-136）は、PO の委任に基づき Opus が発行する。

### 5-4. 便4 DB の列

- 新しい migration で、すべての `tenant_*` の `staff` から `firebase_uid` を外す（`ALTER TABLE ... DROP COLUMN IF EXISTS`・冪等・構造のみ。ADR-1007）。
  - `scripts/run_all_migrations.sh` の末尾に登録する。
  - ビューは先頭で外れ、最後に作り直される（R20）。
- `backend/app/services/tenant.py:614`（新しい会社の型紙）から列を消す。
- `backend/tests/conftest.py:512` と `backend/tests/rls_bootstrap.py:238`・`:253` の足場から列を消す。
- `backend/tests/test_staff_create_users.py:163`・`:232` は列を SELECT している。列が無い前提の試験（「保存しない」ことを、列が無いことと応答に無いことで確かめる）に直す。
- `migrations/20261024_100300_create_ai_cloud_views.sql:535` の分類の行から `firebase_uid` を外し、:3 の行数と `backend/tests/ops/test_ai_cloud_views.py:484` の数（今 1068）を合わせる。`:556` の足場だけの列の一覧から `("public","users","firebase_uid")` を外す（rls_bootstrap の列を消すため）。`scripts/migration-guard/reference-allowlist.tsv:7` のハッシュも更新する。正しい数は、カードで実物を流して数える。
- `scripts/qa/seed-tenant.sql:110-120` の 3 つの INSERT から `firebase_uid` の列と値を外す（R31）。同じファイルの注記 :21-23（psql 変数 `qa_*_firebase_uid` の説明）も消す。手で動かしたときに失敗しないため。`scripts/qa/reset-tenant.sh:120-122` が渡す値は使われなくなるだけで、psql は失敗しない。ファイルごと消すのは ADR-1051 D5 に任せる。
- `scripts/data_migration/*` は過去の移行の記録なので触らない（§8-2 の例外）。ほかに列が無いと失敗する SQL が見つかれば、カードの段階で止まる。
- 本番で消える値は tenant_006 の 1 件だけ。人の正本とはつながっていて（R26）、アプリはこの列を読まない。

### 5-5. 便5 外部の片付け（PO の手作業と GO）

始める条件: 便1〜便4 の本番反映から 7 日、ログインの不具合が 0 件。

1. PO が Firebase の利用者を書き出し、暗号化して PO の Mac に置く。人数を数える（recon U2）。手順は便5 のカードに書き、書き出しの道具の使い方は Context7 か公式の資料で確かめてから書く。
2. **PO に削除の確認をもらう（戻せない）**。同意票（ADR-1033）で聞く。
3. PO が Firebase の画面で利用者を全員消す。画像で 0 人を確かめる（K8）。
4. 秘密と配線の片付け（PO の permit-danger が要るものは PO が実行する）:
   - GitHub の secret `FIREBASE_API_KEY` を消す。
   - サーバーの `.env` の `VITE_FIREBASE_*` と `GCP_PROJECT_ID` を消す。deploy の消す行に足す前進 PR で行い、他に読む所が無いことは便5 のカードで実物を確かめる（recon U4）。
   - サーバーの 「firebase-credentials.json」 を消し、GCP でその鍵を無効にする。鍵の番号がほかの用途に使われていないことを、便5 のカードで確かめる。
   - 画面用の API キー（今の `VITE_FIREBASE_API_KEY` の値）を GCP で消す。ほかの用途（カレンダーなど）に使われていれば、Firebase のログイン（Identity Toolkit・Token Service）に使えないよう制限する。どちらにするかは、便5 のカードで GCP の画面の実物を確かめて決める（recon U6）。
   - Firebase のログインの方法を全部無効にする（メールとパスワードのほか、Google などが有効になっていればそれも）。どれが有効かは便5 のカードで確かめる（recon U6）。
   - Uptime Kuma の「Firebase Auth」の監視を消す（recon U5）。
   - ADR-032 の認証ドメインの DNS が残っていれば消す。
5. 書類: ADR-032 と ADR-023 を Superseded にする。ADR-1013 に便6 の完了を書く。`node scripts/generate-adr-index.js` を流す。

## 6. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| A. 全部を 1 つの PR で外す | 120 ファイルに及び、危険な配線と DB を混ぜることになる。不具合が出たとき原因を切り分けられない。「変更は一度に1つ」に反する |
| B. 部品は残し、Firebase の利用者だけを消す | 部品と配線が残り、裏口のもとが消えない。K9 の検査も通らない |
| C. 利用者の削除を先に行う | 戻す道が先に無くなる。ADR-1013 Decision 6（削除は最後）に反する |
| D. `staff.firebase_uid` の列を残す | 使い道の無い値が残り、Firebase の利用者を消した後は存在しない番号を指す。人の正本（ADR-1008）の外にログインの情報を残すことになる |
| E（採用）. 画面 → サーバー → 配線 → DB → 外部 の 5 便に分け、1 便ずつ反映と確かめをする | 便ごとに戻せる。戻せない操作は最後に 1 つだけ残る |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| firebase-admin を外すと、Google の部品が一緒に抜けてカレンダーなどが止まる | K4 の import の確かめを CI で行う。通らなければ、要る部品を `backend/requirements.txt` に直接書く |
| 開発用の偽ログインが本番に入る | K6 の grep を CI に入れる |
| e2e が自社ログインの API を呼んで落ちる | 便1 で devSession を入れる。e2e・karte-gate の緑を合格の条件にする（K5） |
| CSP を早く閉じすぎて画面が通信できない | 便1 の本番反映後に、本番の JS に Google への通信が 0 件であることを確かめてから便3 で閉じる |
| 審査用の会社のログインが作れなくなる | 便2 で `scripts/setup_review_tenant.py` を自社のパスワードに切り替える。試験で確かめる |
| 戻す順を間違えて画面が開かなくなる | §4 に逆順で戻すことを書く。各カードの戻し方にも書く |
| 便5 の削除後に、Firebase にしかいない人がログインできなくなる | 自社ログインは 10/30 から本番で動き、使用中の 9 人は users にいる（R22）。Firebase にしかいない人（10/13 時点で 3 人）は users に行が無く、今もログインできない。便5 の前に書き出しで数え、PO に人数と名前を見せてから確認をもらう |

## 8. K9 で認める例外と、ファイルの割り当て

### 8-1. 割り当て表（2026-11-04 の `git grep -il firebase -- . ':!docs'` の 120 ファイル。R32）。数えたのはこの設計の枝で、うち 1 個はこの枝だけにある台帳 `.claude-pipeline/active-work.d/release-firebase-removal-design.md`（§8-2 の例外）。origin/main 7d56ab771 では 119 個

| 行き先 | ファイル |
|---|---|
| 便1 画面 | `frontend/` の下すべて（`frontend/.storybook/main.ts`・`frontend/package.json`・`frontend/package-lock.json`・`frontend/playwright.config.ts`・`frontend/vite.config.ts`・`src/` の下・`tests-e2e/` の下の 5 ファイル。ただし `frontend/Dockerfile`・`frontend/.env.example`・`frontend/api-contract/openapi.json` を除く）、`.github/workflows/e2e.yml`、`.github/workflows/karte-gate.yml` |
| 便2 サーバー | `backend/app/` の下すべて（`backend/app/services/tenant.py` を除く）、`backend/requirements.txt`、`backend/scripts/CLAUDE.md`、`backend/tests/` の下（`backend/tests/conftest.py` の Firebase の既定の部分を含む。下の便4 の行に挙げた列の部分を除く）、`frontend/api-contract/openapi.json`（作り直し）、`scripts/setup_review_tenant.py`、「scripts／setup_single_test_user.py」、「scripts／setup_test_users.py」、`scripts/setup_tenant.py` |
| 便3 配線 | `docker-compose.yml`、`frontend/Dockerfile`、`.env.example`、`frontend/.env.example`、`nginx/nginx.conf`、`scripts/blue-green-cutover.sh`、`.github/workflows/external-state-snapshot.yml`、`.github/workflows/rotate-qa-firebase.yml`、`.gitleaks.toml`、`monitoring/grafana/provisioning/dashboards/json/uptime-kuma.json`、`scripts/detect-external-api-change.js`、`scripts/tests/test-detect-external-api-change.js`、`scripts/smoke/external-firebase.sh`、`scripts/snapshot/firebase.sh` |
| 便4 DB の列 | `backend/app/services/tenant.py`、`backend/tests/conftest.py`（:512）、`backend/tests/rls_bootstrap.py`、`backend/tests/test_staff_create_users.py`、`backend/tests/ops/test_ai_cloud_views.py`、`migrations/20261024_100300_create_ai_cloud_views.sql`、`scripts/qa/seed-tenant.sql` |
| 例外（§8-2） | 残りすべて |

カードを作るときに同じ grep をもう一度流す。増えたファイルがあれば、この表に足してから渡す。

### 8-2. 例外の一覧（K9 の正本）

- `docs/` の下（過去の設計・ADR・記録。書き換えない）。ただし `docs/external-state-contract.yml:29-37` は §5-3 で消す（設定の正本なので、記録ではない）
- `.claude-pipeline/` の下（作業の台帳）
- `AGENTS.md`（:17 は「外部の画面の操作は PO に確かめる」の例に Firebase を挙げているだけ。便5 の後に例から外すかは、その時に決める）
- `migrations/019_create_staff_tables.sql`・`migrations/20260612_150000_drop_password_hash.sql`（過去の migration）と、便4 で足す列を消す migration
- `scripts/run_all_migrations.sh`（:612 は過去の注記。便4 で足す行も migration の名前に firebase を含む）
- `.gitignore`・`backend/.dockerignore`（鍵のファイルを上げないための守り）
- `tools/termux-line-import/README.md`・`tools/termux-line-import/device_session.py`（「Firebase を使わない」と書いてあるだけ）
- ADR-1051 D5 が消すまでの古い qa-smoke の資産: `.github/workflows/qa-smoke.yml`、`scripts/qa/reset-tenant.sh`、`tests/qa-smoke/` の下（6 ファイル）
- `scripts/data_migration/migrate_staff_from_sheet.py`・`scripts/data_migration/verify_staff_migration.py`（過去の移行の記録）

## 維持の仕組み

- 守り手: .github/workflows/test.yml（backend の試験）と .github/workflows/e2e.yml（画面の試験）。便1 で K1・K6 の数え方を、便2 で K2・K4 の確かめを CI の段に足す。K1・K6 は `.github/workflows/frontend-check.yml` の job `check` の段「Viewer bundle check」（`npx vite build --manifest` で `frontend/dist` を作る段）の直後に足す（カード作成時に実物を見て決めた。2026-11-04）。便2 の K2・K4 は `.github/workflows/test.yml` の job `pytest-run` の段「Install dependencies」の直後に段「Firebase removal check (K2 K4)」として足す（カード2 の作成時に実物を見て決めた。2026-11-05）。
- K1 の数え方（`frontend/` で `npm run build` の後）: `cat $(find dist -name '*.js') | grep -oiE 'firebase|identitytoolkit|securetoken|googleapis|gstatic' | wc -l` が 0。
- K6 の数え方（同じ dist）: `cat $(find dist -name '*.js') | grep -oE '__salesanchorE2eAuthUser|e2e-auth-user|e2e-firebase-auth-user|e2e-fake' | wc -l` が 0。
- 便1 の後に `frontend/package.json` へ firebase をもう一度足すと、K1 の grep が赤になる。
- 便2 の後に `firebase-admin` を足すと、K2 の確かめが赤になる。
- 例外の一覧（§8-2）は便5 の書類の便で ADR-1013 に書き写し、K9 の検査の正本にする。

## 9. 元の設計との違い

`docs/handoff/auth-self-hosted-passkey/design.md:160` の便6 の行と比べて、次を改める。同じ行に、この設計への参照を書き足す。
- `bcrypt` は外さない。ボットの API キーが使っている（R6）。
- `.github/workflows/qa-smoke.yml` は ADR-1051 D5 に任せる（ADR-1051 は便6 の行より後に決まった）。
- `staff.firebase_uid` の列を外す便（便4）を足す。元の行は `backend/app/schemas/auth.py` の `firebase_uid` だけを挙げていた。
- 1 便を 5 便に分ける（§4）。

## 10. 設計審査（同じ Opus が自分で審査した。独立した審査ではない）

判定: APPROVE（クラウドの設計審査の 3 回目 APPROVE。2026-11-04）。

- 1 回目のクラウドの設計審査（2026-11-04）は REVISE。指摘と直した所:
  - 重い 1: 開発での動き方が決まっていなかった → §5-1 の表で、今止まっている機能（R28）を外した後も止めたままにすると決めた。判定は `isDevSession()` の 1 つにした。
  - 重い 2: K9 の割り当てが足りなかった → §8-1 の表で、今ある 120 ファイル全部を便か例外に入れた。スクリプトで割り当て漏れ 0 を確かめた。
  - 中: 便4 に `backend/tests/test_staff_create_users.py`・`backend/tests/rls_bootstrap.py`・`backend/tests/ops/test_ai_cloud_views.py:556` を足した。便2 に `frontend/api-contract/openapi.json` の作り直しを足した。K4 の import を R30 の 10 個にした。K6 の数える語を偽ログインの印 4 語にした。`scripts/qa/seed-tenant.sql` は便4 で列だけ外すと決めた。便5 に API キーとログインの方法の止め方を足した。
  - 軽い: 行番号を実物に合わせた（recon R11・R13・R32）。
  - 審査で新しく見つかった事実: 本番の画面のファイルに開発用の偽ログインの文字が今も入っている（R27）。静的な import では落ちないので、§5-1 で読み込み方を決めた。
- 2 回目のクラウドの設計審査（2026-11-04）は REVISE（重い指摘 0）。1 回目の指摘は全部直っていて、§5-1 の読み込み方は dev・e2e・karte-gate を壊さず本番に入らない筋、§8-1 は漏れ・重なり 0 と確かめられた。指摘と直した所:
  - 中 1: `backend/app/schemas/auth.py` に `firebase_uid` は無かった → :19 の説明文を直すと書き、openapi.json を作り直す理由を description の 4 か所に直した（§5-2）。
  - 中 2: `scripts/qa/seed-tenant.sql:21-23` の注記が K9 に残る → 消すと書き足した（§5-4）。
  - 軽い: §8-2 に `docs/external-state-contract.yml` の例外を書いた。`scripts/setup_review_tenant.py` は関数ごと消すと書き、行を全部載せた。「recon8」を R4・R8・R19 に直した。K4 の deploy 後の見方を celery のログの語で書いた。120 個と 119 個の差を §8-1 に書いた。
- 3 回目のクラウドの設計審査（2026-11-04）は APPROVE。2 回目の指摘 7 件が直り、1・2 回目に確かめた所も崩れていないと確かめられた。軽い 2 件（`scripts/setup_review_tenant.py` の行の漏れ、パスワードを書き直す条件）は §5-2 に書き足した。
- 既存の仕様との整合:
  - ADR-1013 Decision 6（削除は最後・PO の GO）は便5 の順序と同意票で守る。
  - ADR-1051 D5 の資産には、`scripts/qa/seed-tenant.sql` の列の 1 か所の他は触らない。
  - ADR-1007 の migration は構造だけで、値は書かない。
  - ADR-027 の i18n は ja・en を同じキーで消す。
  - ADR-144 の金型は、新しい画面の部品を作らないので当たらない。
  - ADR-1024・ADR-1052 のビューは R20 の順で作り直される。
- 根拠: 事実は全部 recon にファイル:行か本番の読み取りで付けた。
- 受け入れ基準: K1〜K9 はすべて、grep・CI・reader 鍵・PO の画面のどれかで○×が出る。
- 実装の範囲: 便ごとにカードを作るまで、実装は渡さない。
- 残る事項:
  - recon U1 は便2 の K4 で、U2・U4・U5・U6 は便5 のカードで確かめる。
  - 便5 の書き出しの道具の使い方は、まだ確かめていない。カードを作るときに Context7 か公式の資料で確かめる。
  - `devSession` を動的に読み込む形で K6 が 0 件になることは、便1 の CI で初めて確かめる。0 件にならなければ便1 は止まる（§5-1）。

## 外部・過去事例の参照と我々への応用

この設計の根拠に外部事例は使わない。理由: 判断の根拠は、この置き場のコードと本番の実物（recon）で足りる。

過去の事例は次の 2 つを使う。
- この置き場の #5118（2026-11-04）。サーバーの断り方を 1 か所で変え、smoke と試験で確かめて本番に入れた。便2 の断り方はこれを引き継ぐ。
- ADR-1030・ADR-1038 便3b の「使われていない列を前進の migration で外す」（`scripts/run_all_migrations.sh:1183`・`:1194`）。便4 はこの形に合わせる。
