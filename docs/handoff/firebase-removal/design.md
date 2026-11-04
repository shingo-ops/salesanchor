# design: Firebase を画面とサーバーから全部外す（ADR-1013 便6）

- 書いた日: 2026-11-04（Opus）
- 状態: 設計案作成済み → 自己審査（§10）済み → クラウドの設計審査待ち → PO の設計承認待ち。実装は未着手。
- PO の進める判断: 2026-11-04「1」。Opus が出した選択肢は「Firebase を画面とサーバーから全部外す設計に進む【おすすめ】　裏口のもとになる部品がなくなります。Firebase に残っている利用者の削除は元に戻せないので、その前に改めて確認をお願いします。」。
- 根拠: [recon.md](./recon.md)（`docs/handoff/firebase-removal/recon.md`。以下 R 番号はこの recon を指す）。
- 親 ADR: ADR-1013（Decision 6・Consequences）。前の便: `docs/handoff/block-firebase-token/design.md`。元の便6 の行: `docs/handoff/auth-self-hosted-passkey/design.md:160`。

## 1. 目的（PO の言葉で）

Firebase は使わない設定に切り替えた（PO 2026-11-04「firebaseは使わない設定に切り替えている」）。11/4 にサーバーは Firebase の札を断るようにした（#5118）。それでも Firebase の部品は画面にもサーバーにも残っていて、裏口のもとになりうる（R1・R11）。ログインの情報が Firebase と自社の 2 か所に分かれている状態も、PO の「データを分散させない」に反する（ADR-1013 Why）。

これを、部品・配線・データ・外部の利用者の順に外し、ログインを自社 1 か所にする。

利用者から見た変化は無い。画面はもう自社のログインしか使っていないからだ（R12・R24）。

## 2. 成功条件（○×で判定できる形）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 本番の画面のファイルに Firebase の部品が入っていない | 便1 の deploy 後、本番の画面の JS を取得して `firebase`・`gstatic`・`googleapis` の文字を数え、0 件。CI ではビルドした dist に同じ grep をかけて 0 件 |
| K2 | サーバーに Firebase の部品が入っていない | 便2 の後、`backend/requirements.txt` に `firebase-admin` が無い。本番の backend で `python -c "import firebase_admin"` が失敗する（ModuleNotFoundError） |
| K3 | 自社ログイン・パスキー・パスワード再設定・新しい機械の許可が今までどおり動く | 各便の deploy 後に deploy 内の smoke が緑。PO がいつもどおりログインして画面を開ける。backend の試験 `test_self_auth.py`・`test_passkeys.py`・`test_password_reset.py`・`test_new_device_approval.py` が全件緑 |
| K4 | Google カレンダー・Drive・表の書き出しが今までどおり動く | 便2 の CI で `python -c "import google.oauth2.credentials, google.auth.transport.requests, googleapiclient.discovery, google_auth_oauthlib.flow"` が通る（recon U1 を機械で確かめる）。deploy 後、カレンダーの取り込みの定期作業の記録が成功 |
| K5 | 開発サーバーと e2e が、Firebase なしで今までどおりログインした状態で動く | e2e・karte-gate の workflow が緑。どちらも偽の VITE_FIREBASE_* の値を渡さない |
| K6 | 本番のビルドに開発用の偽ログインが入っていない | dist に `e2e-fake` の文字が 0 件（CI で grep） |
| K7 | `staff.firebase_uid` の列がどの会社の表にも無い | 便4 の後、reader 鍵で `information_schema.columns` を数え 0 件。ai_cloud の `build_log` の最新行が ok |
| K8 | Firebase の利用者が 0 人 | 便5 の後、PO が Firebase の画面で利用者の数が 0 を確かめる（画像）。削除の前に暗号化した書き出しが PO の Mac にある |
| K9 | リポジトリに Firebase の文字が、認めた例外の他に無い | 全便の後、`git grep -il firebase` の結果が §8 の例外の一覧と一致する |

## 3. 対象と対象外

対象: R1〜R19 の部品・配線・試験・運用スクリプト・監視の板、`staff.firebase_uid` の列、Firebase の利用者、Firebase だけに使う秘密。

対象外（触らない）:
- GCP プロジェクト `sales-ops-with-claude` そのもの。Google カレンダーの OAuth が使っている（R25）。
- `bcrypt`。ボットの API キーの保管が使っている（R6）。元の設計 `docs/handoff/auth-self-hosted-passkey/design.md:160` の「`bcrypt` の除去」は誤りなので、この設計で取り消す（§9）。
- 古い qa-smoke の資産（`.github/workflows/qa-smoke.yml`・`scripts/qa/`・`tests/qa-smoke/`・QA_* の secrets）。持ち主は ADR-1051 D5 で、新しい点検が 14 日続けて合格した後に消す。
- `external-state-snapshot.yml` の GCP の段と、secret `GOOGLE_APPLICATION_CREDENTIALS_JSON`（GCP の段が使う。R19）。
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
- 便2 は便4 より先。運用スクリプトが `firebase_uid` を書かなくなってから列を消す（R9・recon8 の `scripts/setup_review_tenant.py:256`・`:273`）。
- 便3 は便1・便2 の後。部品を読む所が無くなってから値と鍵のマウントを外す。
- 便5 は最後。便1〜便4 の本番反映から 7 日、ログインの不具合が 0 件であることを確かめてから、PO に改めて削除の確認をもらう。
- 戻すときは逆の順（便4→便3→便2→便1）。便3 を残したまま便1 だけを revert すると、画面が値なしで Firebase を初期化して開かなくなるため。
- サーバーの `.env` の `VITE_FIREBASE_*` と、サーバー上の鍵のファイルは、便5 まで消さない。便1〜便4 を戻す道を残すため。

## 5. 変更の前と後（便ごと）

各便の前に実装カード（`docs/handoff/firebase-removal/card-N.md`）を作る。カードには、ファイル:行、変更の前後、触らない範囲、試験を書く。この章は便の範囲と決めごとまでを書く。

### 5-1. 便1 画面

- 消すファイル: `frontend/src/lib/firebase.ts`、`frontend/src/lib/firebase-auth.ts`、`frontend/src/lib/firebaseErrorMessage.ts` とその試験、`frontend/src/lib/__storybook-mocks__/firebase-app.ts`・`firebase-auth.ts`。
- `frontend/package.json:84` の `firebase` と、lock の中身を消す。
- `frontend/src/locales/ja.json`・`en.json` の `firebaseError` の塊（:3274）を消す。両方から同じキーを消す（ADR-027）。
- `frontend/.storybook/main.ts:34-35` の差し替えを消す。
- `frontend/src/test-setup.ts` の firebase の差し替えを消す。`frontend/vite.config.ts` の注記を直す。
- スイッチ: `frontend/src/lib/auth/provider.ts` を消し、`isSelfAuth()` の分かれ道（R12 の 10 か所）を自社ログインだけにする。
  - `AuthContext.tsx`: Firebase の分岐（`onAuthStateChanged` ほか）を消す。
  - `selfAuth.ts:49-63`: Firebase に戻る道を消す。
  - `LoginPage.tsx:44`: `authErrorMessage` だけを使う。
  - `SecuritySection.tsx`: Firebase の再認証とパスワード変更の分岐を消し、`:366-369` の条件を外す。
- 開発サーバーと e2e の偽ログイン:
  - `frontend/src/lib/auth/devSession.ts`（新設）に置く。`import.meta.env.DEV` のときだけ `selfAuth.ts` から使う。
  - 今の偽物（R11）と同じく、`window.__salesanchorE2eAuthUser` と保存の鍵を読む。保存の鍵の名前は `salesanchor:e2e-auth-user` に変え、`frontend/tests-e2e/utils/auth.ts:23`・`:31` を合わせる。
  - Vite は本番のビルドで `import.meta.env.DEV` を false に置き換え、使わない枝を落とす。入っていないことは K6 の grep で確かめ、推測に頼らない。
- 試験: `vi.mock` で firebase を差し替える 14 ファイルを、`selfAuth` か `devSession` の差し替えに直す（R15）。
- e2e の設定: `frontend/playwright.config.ts:150-151` と `.github/workflows/e2e.yml:204`・`:311`、`karte-gate.yml:75`・`:85`・`:110` から偽の VITE_FIREBASE_* を消す。
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
- `backend/app/schemas/auth.py` の `firebase_uid` を消す。
- 注記だけの所（R10）の文を、事実に合わせて直す。
- 運用スクリプト（recon8）:
  - `scripts/setup_review_tenant.py`: Firebase の利用者を作る所を、`backend/app/auth/passwords.py:20` の `hash_password` で `users.password_argon2_hash` を書く形に変える。`firebase_uid` を書く所（:231・:256・:273・:351・:369）を消す。`backend/tests/test_setup_review_tenant.py` を合わせる。
  - `scripts/setup_single_test_user.py`・`scripts/setup_test_users.py`: 消す。呼ぶ所はリポジトリに無く、中身は Firebase の利用者を作ることだけ（recon8 の検索）。
  - `scripts/setup_tenant.py:29`・`:471`: 「Firebase ユーザーを作る」の案内を、初回設定メールの案内に直す。
  - `backend/scripts/CLAUDE.md`・`backend/AGENTS.md:8` の手順を合わせる。
- 試験: Firebase の既定に頼る試験（R21 の 15 ファイル）を直す。#5118 で足した T1・T2・T6 は、Firebase の分岐が無くなるので「自社以外の札は 401」の試験に置き換える。
- K4 の import の確かめを、カードの試験の段に入れる。

### 5-3. 便3 配線

- `docker-compose.yml`:
  - :69・:241 の `GOOGLE_APPLICATION_CREDENTIALS` を消す。
  - :161・:298 の鍵のマウントを消す。
  - :201-203 の VITE_FIREBASE と GCP の build args を消す。
  - :136・:205 の `AUTH_PROVIDER` と `VITE_AUTH_PROVIDER` を消す。
- `scripts/blue-green-cutover.sh:94`・`:99` を消す。
- `frontend/Dockerfile:7-13` の VITE_FIREBASE・GCP・AUTH_PROVIDER の ARG と ENV を消す。
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
  - `backend/.dockerignore:14`・`.gitignore:29-30` は残す。鍵のファイルを誤って上げないための守りなので、§8 の例外にする。
- 危険 PR の GO（ADR-136）は、PO の委任に基づき Opus が発行する。

### 5-4. 便4 DB の列

- 新しい migration で、すべての `tenant_*` の `staff` から `firebase_uid` を外す（`ALTER TABLE ... DROP COLUMN IF EXISTS`・冪等・構造のみ。ADR-1007）。
  - `scripts/run_all_migrations.sh` の末尾に登録する。
  - ビューは先頭で外れ、最後に作り直される（R20）。
- `backend/app/services/tenant.py:614`（新しい会社の型紙）から列を消す。
- `backend/tests/conftest.py:512` と `backend/tests/rls_bootstrap.py` の足場から列を消す。
- `migrations/20261024_100300_create_ai_cloud_views.sql:535` の分類の行から `firebase_uid` を外し、:3 の行数と `backend/tests/ops/test_ai_cloud_views.py:484` の数を合わせる（`scripts/migration-guard/reference-allowlist.tsv:7` のハッシュも更新）。
- `scripts/qa/seed-tenant.sql` と `scripts/data_migration/*` は ADR-1051 D5 と過去の移行の資産なので触らない。§8 の例外にする。ただし、列が無いと失敗する SQL があれば、カードの段階で実物を見て止まる。
- 本番で消える値は tenant_006 の 1 件だけ。人の正本とはつながっていて（R26）、アプリはこの列を読まない。

### 5-5. 便5 外部の片付け（PO の手作業と GO）

始める条件: 便1〜便4 の本番反映から 7 日、ログインの不具合が 0 件。

1. PO が Firebase の利用者を書き出し、暗号化して PO の Mac に置く。人数を数える（recon U2）。手順は便5 のカードに書き、書き出しの道具の使い方は Context7 か公式の資料で確かめてから書く。
2. **PO に削除の確認をもらう（戻せない）**。同意票（ADR-1033）で聞く。
3. PO が Firebase の画面で利用者を全員消し、メールとパスワードのログインを無効にする。画像で 0 人を確かめる（K8）。
4. 秘密と配線の片付け（PO の permit-danger が要るものは PO が実行する）:
   - GitHub の secret `FIREBASE_API_KEY` を消す。
   - サーバーの `.env` の `VITE_FIREBASE_*` と `GCP_PROJECT_ID` を消す。deploy の消す行に足す前進 PR で行い、他に読む所が無いことは便5 のカードで実物を確かめる（recon U4）。
   - サーバーの `firebase-credentials.json` を消し、GCP でその鍵を無効にする。鍵の番号がほかの用途に使われていないことを、便5 のカードで確かめる。
   - Uptime Kuma の「Firebase Auth」の監視を消す（recon U5）。
   - ADR-032 の認証ドメインの DNS が残っていれば消す。
5. 書類: ADR-032 と ADR-023 を Superseded にする。ADR-1013 に便6 の完了を書く。`node scripts/generate-adr-index.js` を流す。

## 6. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| A. 全部を 1 つの PR で外す | 115 ファイルに及び、危険な配線と DB を混ぜることになる。不具合が出たとき原因を切り分けられない。「変更は一度に1つ」に反する |
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
| 審査用の会社のログインが作れなくなる | 便2 で `setup_review_tenant.py` を自社のパスワードに切り替える。試験で確かめる |
| 戻す順を間違えて画面が開かなくなる | §4 に逆順で戻すことを書く。各カードの戻し方にも書く |
| 便5 の削除後に、Firebase にしかいない人がログインできなくなる | 自社ログインは 10/30 から本番で動き、使用中の 9 人は users にいる（R22）。Firebase にしかいない人（10/13 時点で 3 人）は users に行が無く、今もログインできない。便5 の前に書き出しで数え、PO に人数と名前を見せてから確認をもらう |

## 8. K9 で認める例外

- `docs/` の過去の設計・ADR・記録（書き換えない）
- `migrations/019_create_staff_tables.sql`・`migrations/20260612_150000_drop_password_hash.sql`（過去の migration）と、便4 で足す列を消す migration
- `.gitignore:29-30`・`backend/.dockerignore:14`（鍵のファイルを上げないための守り）
- ADR-1051 D5 が消すまでの古い qa-smoke の資産（`.github/workflows/qa-smoke.yml`・`scripts/qa/`・`tests/qa-smoke/`）
- `scripts/data_migration/*`（過去の移行の記録）

## 維持の仕組み

- 守り手: .github/workflows/test.yml（backend の試験）と .github/workflows/e2e.yml（画面の試験）。便1 で K1・K6 の grep を、便2 で K2・K4 の確かめを CI の段に足す。
- 便1 の後に `frontend/package.json` へ firebase をもう一度足すと、K1 の grep が赤になる。
- 便2 の後に `firebase-admin` を足すと、K2 の確かめが赤になる。
- 例外の一覧（§8）は便5 の書類の便で ADR-1013 に書き写し、K9 の検査の正本にする。

## 9. 元の設計との違い

`docs/handoff/auth-self-hosted-passkey/design.md:160` の便6 の行と比べて、次を改める。同じ行に、この設計への参照を書き足す。
- `bcrypt` は外さない。ボットの API キーが使っている（R6）。
- `.github/workflows/qa-smoke.yml` は ADR-1051 D5 に任せる（ADR-1051 は便6 の行より後に決まった）。
- `staff.firebase_uid` の列を外す便（便4）を足す。元の行は `schemas/auth.py` の `firebase_uid` だけを挙げていた。
- 1 便を 5 便に分ける（§4）。

## 10. 設計審査（同じ Opus が自分で審査した。独立した審査ではない）

判定: APPROVE（クラウドの設計審査の結果で改める）。

- 既存の仕様との整合:
  - ADR-1013 Decision 6（削除は最後・PO の GO）は便5 の順序と同意票で守る。
  - ADR-1051 D5 の資産には触らない。
  - ADR-1007 の migration は構造だけで、値は書かない。
  - ADR-027 の i18n は ja・en を同じキーで消す。
  - ADR-144 の金型は、新しい画面の部品を作らないので当たらない。
  - ADR-1024・ADR-1052 のビューは R20 の順で作り直される。
- 根拠: 事実は全部 recon にファイル:行か本番の読み取り（AUDIT）で付けた。元の設計の誤り（bcrypt）は実物の検索で見つけた。
- 受け入れ基準: K1〜K9 はすべて、grep・CI・reader 鍵・PO の画面のどれかで○×が出る。
- 実装の範囲: 便ごとにカードを作るまで、実装は渡さない。
- 残る事項:
  - recon U1 は便2 の K4 で、U2・U4・U5 は便5 のカードで確かめる。
  - 便5 の書き出しの道具の使い方は、まだ確かめていない。カードを作るときに Context7 か公式の資料で確かめる。

## 外部・過去事例の参照と我々への応用

この設計の根拠に外部事例は使わない。理由: 判断の根拠は、この置き場のコードと本番の実物（recon）で足りる。

過去の事例は次の 2 つを使う。
- この置き場の #5118（2026-11-04）。サーバーの断り方を 1 か所で変え、smoke と試験で確かめて本番に入れた。便2 の断り方はこれを引き継ぐ。
- ADR-1030・ADR-1038 便3b の「使われていない列を前進の migration で外す」（`scripts/run_all_migrations.sh:1183`・`:1194`）。便4 はこの形に合わせる。
