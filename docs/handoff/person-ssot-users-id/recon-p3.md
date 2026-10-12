# recon-p3: 人の正本 users.id 化 P3 の現状調査（読み取りのみ）

基準: origin/main（git fetch origin main 後、git grep / git show origin/main:<path>）。本番は読み取り専用トランザクションのみ。
メール・トークン・firebase_uid の値は出していない。調査日 2026-10-13。

## 1. (b) 名簿を primary_email で引く箇所の全量

| # | file:line | 内容 | 呼び出し元 | 引けなかったとき |
|---|---|---|---|---|
| b1 | backend/app/routers/staff.py:239-250 | GET /staff/me。`WHERE s.primary_email = :email ORDER BY s.id ASC LIMIT 1` | 画面: frontend/src/contexts/UiPrefsContext.tsx:103、LocaleContext.tsx:46、ThemeContext.tsx:76、pages/account-settings/ProfileSection.tsx:56 | staff.py:252-256 で 404「現在のユーザに紐づく staff レコードが見つかりません」。画面側 UiPrefsContext.tsx:112 は console.warn してデフォルト値で動作 |
| b2 | backend/app/routers/staff.py:332-343 | PATCH /staff/me/profile。同じ email 引き | frontend/src/lib/staffProfile.ts:14 | staff.py:344-348 で 404 |
| b3 | backend/app/routers/staff.py:398-412 | `_my_staff_id_and_token`（`SELECT id, avatar_token FROM staff WHERE primary_email = :email ORDER BY id ASC LIMIT 1`） | staff.py:436（POST /staff/me/avatar）、staff.py:483（DELETE /staff/me/avatar）。画面 frontend/src/lib/staffProfile.ts:25,48 | email が空: 401（staff.py:400-401）。行なし: 404（staff.py:407-411） |
| b4 | backend/app/routers/leads.py:2067-2099 `_resolve_staff_identity` の SQL は 2077-2083（`FROM {staff_t} WHERE primary_email = :email ORDER BY id ASC LIMIT 1`、staff_t は tenant_table_ref） | leads.py:2192（Discord テキスト送信）、leads.py:2363（Discord 画像送信）。どちらも `current_user.email` を渡す | 行なし、または given_name_en が空: leads.py:2085-2089 で 422（DISCORD_ERR_EN_NAME_REQUIRED）。送信しない |
| b5 | backend/app/routers/calendar.py:56-69 `_current_staff_row`（`WHERE user_id = :uid OR primary_email = :email ORDER BY CASE WHEN user_id = :uid THEN 0 ELSE 1 END, id ASC LIMIT 1`） | calendar.py:164（GET 一覧）、calendar.py:264（PATCH owner 設定） | 164: 行なしで 404（165-169）。264: None のまま続行し current_staff_id=None（265） |
| b6 | backend/app/routers/staff.py:120, 130（`_fetch_locale` / `_fetch_theme`: `FROM public.users WHERE email = :email`）、staff.py:277, 301（PATCH /staff/me/locale・theme: `UPDATE public.users ... WHERE email = :email`） | `_compose`（staff.py:145-146）が **staff.primary_email** を渡す。これは staff 行 → users 行を email で引く向き。PATCH は current_user.email | locale/theme: 行なしでデフォルト "ja"/"light"（staff.py:124, 134）。PATCH は 0 行更新のまま 200 を返す |

補足（事実）
- ほかに staff を primary_email で引く SQL は backend/app に無い（`git grep primary_email` と `FROM/JOIN ... staff` の全件を確認。contacts.py / invoices.py / registration_tokens.py / integrations.py の primary_email は contacts 表の列で別物）。
- すでに user_id で引いている箇所: calendar.py:174 系の一覧、calendar.py:249-262（user_id 完全一致）、meta_inbox.py:723・740、bots.py の `s.user_id = b.owner_staff_id`（84-284）、order_commissions.py の `s.user_id = oc.staff_id`（156-517）、services/calendar_service.py:120・122。
- backend/app/auth/dependencies.py は users を email で引く（後述 §3）。ここは staff を引かない。
- 試験が email 引きに依存: backend/tests/test_staff_me.py:13 `test_get_my_staff_via_email_fallback`、:55 `..._404_when_no_link`、:65 `..._deterministic_when_shared_email`（同一メールの staff 2件で id の小さい方を返す前提）。user_id 引きにすると書き換え対象。
- scripts/qa/seed-tenant.sql:128-129 は `JOIN tenant_006.staff s ON s.primary_email = u.email`（QA 用の紐付け SQL）。
- 本番の 6 行は users.email と staff.primary_email が完全一致（§6-4）。つまり現状は email 引きと user_id 引きの結果が同じ。

## 2. (c) POST /staff の現状

backend/app/routers/staff.py
- :556-558 `POST /staff`、`require_permission("staff.create")`、status 201。
- :562 `_ensure_assignable_role(db, data.role_id, tenant_id, current_user)`（staff.py:81-93）。roles を tenant_id 一致かつ隠しロールでないことで検証。無ければ 400「指定の role_id はこのテナントに存在しません」。
- :565 staff_code は `_new_placeholder_code()`（TMP-+uuid）で入れ、:594-597 で `EMP-{id:05d}` に UPDATE。
- :567-592 `INSERT INTO staff (tenant_id, user_id, staff_code, 氏名..., primary_email, discord_user_id, role_id, status, firebase_uid, is_employee)`。user_id は `data.user_id`（クライアント指定、任意）をそのまま入れる。**users の INSERT も user_roles の INSERT も無い**（staff.py に `user_roles` / `INSERT INTO ... users` の記述なし）。
- :598-599 `_upsert_ui_prefs`、`_replace_additional_emails`。:600-604 監査ログ。:605 commit。
- エラー応答: IntegrityError は :607-613 で rollback し 409「スタッフの登録に失敗しました（staff_code / discord_user_id / firebase_uid 重複の可能性）」。

backend/app/schemas/staff.py StaffCreate（:59-90）
- 必須: surname_jp(1-50), given_name_jp(1-50), surname_en(1-100・空不可 :64, :87-90), given_name_en(同), primary_email(255・validate_email_loose :79-85), role_id(int)
- 任意: surname_kana, given_name_kana, discord_user_id(50), status(既定 active, enum StaffStatus :69), firebase_uid(128), **user_id: int | None = None（:71）**, is_employee(既定 False), ui_preferences, additional_emails(既定 [])
- StaffUpdate（:93-123）も user_id / firebase_uid / role_id / status を受ける。staff.py:74-78 `_UPDATABLE` に user_id, role_id, status, primary_email, firebase_uid が入っている。

フロント（POST /staff を呼ぶのは 1 か所）
- frontend/src/pages/staff/StaffPage.tsx:172 `api.post("/staff", payload)`。payload は :157-170: surname_jp, given_name_jp, surname_kana, given_name_kana, surname_en, given_name_en, primary_email, discord_user_id, role_id, status, firebase_uid(常に空→null), ui_preferences。**user_id は送っていない**。
- 画面は同ファイル :231-306 の `Modal`（components/Modal）内のフォーム。部品: TextFieldControl（components/TextField）、Select（components/Select）、Button（components/Button）、ui_preferences は素の `<input type="checkbox">`（:293、6 項目）。フォーム状態は :73-93（CreateFormState）。firebase_uid の入力欄は無い（state と payload のみ、:84, :92, :168）。
- 失敗時は :176-177 で `setError(err.message)`（バックエンドの detail 文字列）。
- 編集は Drawer（StaffFormFields.tsx 6 項目）と StaffEditPage.tsx:132 の PATCH。
- 試験: frontend/src/components/StaffFormButtonMigration.test.tsx:187, 221 が POST /staff の payload を検証している。

結論（事実）: 現行の POST /staff で作られた staff 行は user_id=NULL（フロントが送らないため）。ADR-023:22 の「POST /staff は staff だけ INSERT」と一致。

## 3. ログイン成立条件

backend/app/auth/dependencies.py
- :162-172 Firebase の ID トークンを `firebase_auth.verify_id_token`（:144）で検証後、**トークンの email クレームで `select(User).where(User.email == email, User.is_active == True)`**。users に無い／is_active=false なら 401「ユーザーが見つかりません」（:174-178）。firebase_uid では引かない（models.py:22-38 の User に firebase_uid 列なし）。
- キャッシュ経路 :125-133 も email + is_active=True。
- :153-160 MFA_REQUIRED（既定 true、:32）。トークンに `sign_in_second_factor` が無いと 403「MFA認証が必要です」。
- テナント: :181-186 トークンのカスタムクレーム tenant_id は「ある場合だけ」users.tenant_id と照合（不一致で 403）。クレームが無い（None）なら照合しない。実際のテナントは :206 `get_current_tenant` が **users.tenant_id** から決める（"JWTからではなくDB上のuser.tenant_id"、:199-200）。search_path=tenant_XXX（:231-232）。
- つまりテナントは DB の users.tenant_id が正で、tenant claim は必須ではない（無くても通る）。

POST /auth/register（backend/app/routers/auth.py:23-134）
- super admin のみ（:27, :43-47）。入力 UserRegister（backend/app/schemas/auth.py:14-26）は email, username, full_name, tenant_code, **firebase_uid（必須）**。
- やること: tenant_code でテナント検索(:50-61) → email 重複 409(:63-71) → users INSERT(:74-83) → 監査ログ(:86-98) → CS ロールを user_roles に INSERT(:100-118) → **Firebase に `set_tenant_claim(firebase_uid, tenant.id)`**（:123、実体 backend/app/auth/utils.py:13-15 `firebase_auth.set_custom_user_claims(uid, {"tenant_id": tenant_id})`）→ 失敗なら rollback + 500（:124-129）→ commit(:131)。
- **Firebase のユーザーを作る処理は無い**。firebase_uid は「既に Firebase にいるユーザーの uid」を渡す前提。staff は作らない。
- 同様に backend/app 全体で `firebase_auth.create_user` / `get_user_by_email` は無い（grep）。Firebase ユーザー作成は scripts/setup_review_tenant.py:115、scripts/setup_single_test_user.py:121、scripts/setup_test_users.py:105 のみ。パスワード生成は backend/app/auth/utils.py:18 `generate_password`（呼び出しは試験 backend/tests/test_password_gen.py のみ。本体からの呼び出しは無い）。

フロントのログイン手段
- frontend/src/contexts/AuthContext.tsx:64 と frontend/src/lib/firebase-auth.ts:129 は `signInWithEmailAndPassword` のみ。Google ログイン（GoogleAuthProvider / signInWithPopup）は frontend/src に無い（grep 0 件）。

「users 行を DB に作るだけで、その人は Google 等でログインできるか」の判定材料（事実から）
- 不足 1: Firebase 側に当該メールのアカウントが必要。バックエンドに作成コードは無い（上記）。
- 不足 2: 画面のログインは email+パスワードのみ。Google ログインの実装は frontend/src に無い。パスワードの用意（または招待・リセットメール）が要る。ADR-023:54-56 はパスワードリセット・招待メールを範囲外としている。
- 不足 3: MFA_REQUIRED=true 既定。初回ログインで MFA 登録が必要（ADR-023:65）。
- 満たす条件: users 行があり is_active=true なら DB 側は通る。tenant claim は無くてもログインは通る（dependencies.py:181 は None ならスキップ）が、register は付与している。
- 判定: 「users 行だけ」ではログインできない（Firebase アカウントが前提）。ただし「ログインしない人」を users に is_active=false で持つだけなら Firebase は不要。ログインする人の作成は (c) で Firebase 作成を含めるか否かが未決（要設計）。

## 4. (d) status 変更・削除の現状

- PATCH /staff/{id}（staff.py:626-684）: `UPDATE staff SET ...`（:655-661）で status を含む `_UPDATABLE` を更新。**users / user_roles に触らない**。role_id を変えても user_roles は変わらない（権限の正本は user_roles、dependencies.py:475-483, 507-513）。
- DELETE /staff/{id}（staff.py:687-714）: `DELETE FROM staff WHERE id = :id`（:701）。副表は ON DELETE CASCADE（:700 コメント）。**users / user_roles は残る**。IntegrityError は 409「この担当者は他のデータから参照されているため削除できません」（:709-714）。
- backend/app/routers/staff.py に `is_active` の記述なし。backend/app 全体で users.is_active を更新する SQL は無い（`UPDATE users` は locale/theme のみ staff.py:277, 301）。tenant の is_active は super_admin_tenants.py:41 で別。
- staff.status は CHECK (active, inactive, pending)（backend/app/services/tenant.py:611-612）。users.is_active は boolean。対応表は未定義（pending をどちらに倒すかは未決）。
- 現状のずれ（本番、§6-3）: tenant_006 の staff 3 行は status=active なのに users.is_active=false。

## 5. (a) NOT NULL 化の影響

ひな形
- backend/app/services/tenant.py:600 `user_id INTEGER UNIQUE REFERENCES public.users(id)`（NULL 許容）。:623 `idx_staff_user_id`。migrations/019_create_staff_tables.sql:38 も同様（「旧データ移行期は NULL 許容」）。既存テナント用の ALTER migration はまだ無い（migrations/ に staff.user_id の変更 SQL なし。20261013_110000_repoint_person_columns_to_users.sql は staff を参照するが別目的）。

staff を INSERT する経路（user_id を入れていないものに ★）
| file:line | user_id | 備考 |
|---|---|---|
| backend/app/routers/staff.py:569-591 | data.user_id（任意・既定 None）| ★実質 NULL（フロントが送らない）。P3(c) の対象 |
| scripts/data_migration/migrate_staff_from_sheet.py:148-158 | 明示的に `NULL`（:157）| ★ |
| scripts/setup_review_tenant.py:251-260 | :uid あり | OK |
| scripts/setup_single_test_user.py:276-285 | :uid あり | OK |
| scripts/qa/seed-tenant.sql:107, 112, 117 | u.id あり | OK |
| backend/tests/test_discord_inbox.py:406 | 無し | ★ |
| backend/tests/test_discord_staff_send.py:111 | 無し | ★ |
| backend/tests/test_order_commissions.py:399-405 | 無し | ★ |
| backend/tests/test_staff_avatar.py:61-67 | 無し | ★ |
| backend/tests/test_staff_me.py:25, 78, 102, 128, 163 | 無し（5 か所） | ★ |
| backend/tests/test_meta_channels.py:350 | user_id=5 あり | OK |
- scripts/setup_test_users.py には staff の INSERT なし（grep 0 件）。複数行に分かれた `INSERT INTO\n staff` は grep で拾えない可能性あり＝未確認。

試験用スキーマの staff 定義（user_id の列と NOT NULL の有無）
- backend/tests/conftest.py:340-362: `user_id INTEGER`（NULL 許容、SQLite）。
- 個別に CREATE TABLE staff を持つ試験（user_id 列なし）: backend/tests/test_502_paths.py:87、test_discord_inbox.py:124、test_message_image_send.py:147、test_message_send.py:165、test_messages.py:141、test_meta_oauth_endpoints.py:99、test_outbound_draft_send.py:144。user_id 列あり: test_meta_channels.py:96。test_rls_tenant_meta_config.py:93 は id, tenant_id, primary_email のみ。
- 重複防止の検査 scripts/tests/test_check_test_schema_dup.py:41, 73 がある（CREATE TABLE staff の重複検査）。
- backend/tests/rls_bootstrap.py に staff の記述なし（grep 0 件）。
- .github/workflows/migration-test.yml:259（tenant_001）、:1197（tenant_001）、:1383（tenant_002）の staff は簡易ダミー（`user_id INTEGER, full_name, is_active`。NOT NULL なし、role_id・primary_email 等の列なし）。実際の 019 とは別定義。ここは NOT NULL 化 migration を流す対象になる場合、列定義が違う点に注意（未確認: migration-test が新 migration をこのダミーに対して流すか）。

本番の事前条件（§6-1）: 全テナントで user_id NULL は 0 件。NOT NULL 化は現時点で通る。

## 6. 本番の読み取り結果（生出力）

経路: 指定の 1 行形式、読み取り専用トランザクション。SQL 内の文字列リテラル・二重引用符は使わず、テナントは数値で表現。

### 6-1 staff の user_id NULL 件数
```
 t | total | null_uid 
---+-------+----------
 1 |     1 |        0
 3 |     0 |        0
 4 |     1 |        0
 5 |     0 |        0
 6 |     4 |        0
(5 rows)
```
6 行すべて user_id あり。

### 6-2 users と staff の突き合わせ（users の全 13 行）
```
 id | tenant_id | is_active | staff_rows_any_tenant | staff_rows_same_tenant 
----+-----------+-----------+-----------------------+------------------------
  1 |         1 | t         |                     1 |                      1
  9 |         1 | t         |                     0 |                      0
  2 |         3 | t         |                     0 |                      0
  3 |         4 | t         |                     1 |                      1
  4 |         4 | t         |                     0 |                      0
  5 |         4 | t         |                     0 |                      0
  6 |         4 | t         |                     0 |                      0
  7 |         5 | t         |                     0 |                      0
  8 |         5 | t         |                     0 |                      0
 10 |         6 | t         |                     1 |                      1
 80 |         6 | f         |                     1 |                      1
 81 |         6 | f         |                     1 |                      1
 82 |         6 | f         |                     1 |                      1
(13 rows)
```
staff 行が無い users は 7 人（id 9, 2, 4, 5, 6, 7, 8）。名簿のある users は 6 人（id 1, 3, 10, 80, 81, 82）。別テナントの staff に紐付く users は無い（any_tenant と same_tenant が一致）。

### 6-3 staff.status × users.is_active
```
 tenant | status | is_active | n 
--------+--------+-----------+---
      1 | active | t         | 1
      4 | active | t         | 1
      6 | active | f         | 3
      6 | active | t         | 1
(4 rows)
```
status=active なのに is_active=false が tenant_006 に 3 行（user_id 80, 81, 82）。inactive / pending の行は 0 件。

### 6-4 staff.primary_email と users.email の一致（値は出していない）
```
 tenant | staff_id | user_id | email_exact_match | email_ci_match 
--------+----------+---------+-------------------+----------------
      1 |        1 |       1 | t                 | t
      4 |        1 |       3 | t                 | t
      6 |        1 |      10 | t                 | t
      6 |        8 |      80 | t                 | t
      6 |        9 |      81 | t                 | t
      6 |       10 |      82 | t                 | t
(6 rows)
```
6 行すべて一致。email 引きから user_id 引きへ変えても、本番の現データでは同じ行に当たる。

## 7. ADR-023（docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md）

- :5 ステータス「提案 — Meta App Review 通過後に着手」（Accepted ではない）。
- :9-15 認証は Firebase / public.users / tenant.staff の 3 層。ログインは users を email で検索（:15）。
- :17-24 既存エンドポイント表。POST /auth/register は users のみ、POST /staff・DELETE・PATCH は staff のみ。
- :30-36 **決定**: 追加＝3 層すべてに作成（:34）、削除＝3 層から削除または論理削除で同期（:35）、status 変更（active ↔ inactive）は `public.users.is_active` も同期（:36）。
- :45-57 **スコープ外**: dependencies.py の変更（:47-49、「変更禁止: 認証・認可の中核」、users を検索する設計は維持し書き込み側で担保）、POST /auth/register の再設計・廃止判断（:50-51、別 ADR）、既存スタッフ（Shingo, review@）への遡及（:52-53）、パスワードリセット・MFA 再設定フロー（:54-55）、招待メール送信（:56-57）。
- :59-65 制約: Meta App Review 非妨害、tenant_004 の既存スタッフ動作継続、新規顧客受け入れ前に完了、**仮パスワードの安全な配布手段が必要（:64）**、MFA_REQUIRED=true と矛盾しないこと（:65）。
- ADR-1008（docs/adr/ADR-1008-person-ssot-users-id.md）:8 は ADR-023 を「提案」と記載、:26 決定 5 は users・staff・user_roles を 1 トランザクションで作る。docs/handoff/person-ssot-users-id/design.md:98 は「ADR-023 は P3 で users・staff・user_roles の同時作成として取り込む」。ADR-023 の「Firebase Auth にも作る」「削除」「仮パスワード配布」を P3 に含めるかは、ADR-1008 決定5 の文言（users・staff・user_roles の 3 つ）上は含まれない。

## 未確認

- 複数行 `INSERT INTO\n  staff` の取りこぼし有無（grep は 1 行一致のみ）。
- migration-test.yml のダミー staff（259, 1197, 1383）に対し NOT NULL 化 migration が流れるか。
- tenant 別 information_schema での staff.user_id の現在の is_nullable・UNIQUE 制約の実在（ひな形上は UNIQUE。本番の実表は未確認。SQL にリテラルを書けず取得できなかった）。
- staff.status=pending を users.is_active にどう対応させるか（定義が無い）。
- (c) で Firebase アカウントを作るか、仮パスワードをどう配るか（ADR-1008 決定5 に記述なし、ADR-023:64 は要件のみ）。
- 本番で users の 7 人（id 2,4,5,6,7,8,9）に staff 行が無い理由と、P3 後の扱い（ADR-1008 は「ログインする人だけ登録」）。

DONE
