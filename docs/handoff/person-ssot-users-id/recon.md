# recon: 「人」の正本を public.users.id 一本にする（段階3）

docs/handoff/person-ssot-users-id/design.md と docs/adr/ADR-1008-person-ssot-users-id.md の根拠

- 基準: origin/main 8a421f22c6666c64445b5d4f9a618d5d0e4b58c5（worktree release-person-ssot-users-id、2026-10-13 に実物を開いて行番号を確認）
- 材料: /tmp/CC報告ファイル/user-ssot/ の findings-20261012.md、recon-phase3-code.md、recon-phase3-code2.md、recon-phase3-prod.md、recon-phase3-prod2.md（短縮パスはすべてフルパスに直した）
- 本番の値は材料の値のまま。メールアドレス・トークン・firebase_uid の値は書かない。本番は今回 DB 未接続（材料の転記のみ）。

## 0. 既存 ADR 検索結果

実行: `git -C <worktree> grep -il -e staff -e assigned_to -e sales_rep docs/adr/`（結果 17 件）

```
docs/adr/ADR-021-order-management.md
docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md
docs/adr/ADR-025_meta_integration_operational_hardening.md
docs/adr/ADR-033-app-theme-switching.md
docs/adr/ADR-038-qa-smoke-suite.md
docs/adr/ADR-072-tenant-schema-prefix-enforcement.md
docs/adr/ADR-091-discord-bot-scope-definition.md
docs/adr/ADR-093-sales-management-page.md
docs/adr/ADR-094-sales-management-page.md
docs/adr/ADR-107-sa-analytics-agent-a-customer-priority.md
docs/adr/ADR-108-inbox-karte-panel-redesign.md
docs/adr/ADR-110-karte-reference-alignment.md
docs/adr/ADR-120-status-presentation-ssot.md
docs/adr/ADR-138-funnel-dashboard-stage1.md
docs/adr/ADR-159-staff-identity-on-discord.md
docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md
docs/adr/README.md
```

docs/adr/FEATURE-INDEX.md の該当行（`grep -n -i -e staff -e assigned_to -e sales_rep -e 担当`）:
- docs/adr/FEATURE-INDEX.md:25 `会社 / 顧客情報 / Client Profile / contact / 担当者 | ADR-060 ／ ADR-058 | リネーム・担当者統合`
- docs/adr/FEATURE-INDEX.md:43 `担当者アイコン / 英語名必須 / Discord webhook 送信 / avatar | ADR-159 ／ ADR-091 | ...`
- 「担当者（assigned_to / sales_rep_id）が users.id か staff.id か」を定める ADR は、上の検索では見つからなかった（ADR-1008 が新設でそれを定める）。

関連 ADR の該当箇所:
- ADR-023（docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md）
  - :3-5 ステータス「提案 — Meta App Review 通過後に着手」
  - :9-13 認証は Firebase / public.users / tenant_XXX.staff の 3 層
  - :15 ログインは public.users を email で検索
  - :19-24 POST /auth/register は users のみ、POST /staff は staff のみ作る対応表
  - :26 管理画面で追加したスタッフはログイン時 401
  - :34-36 決定: 追加は 3 層に作成、status 変更は users.is_active を同期
  - :47-49 backend/app/auth/dependencies.py はスコープ外
  - :56 招待メールはスコープ外
  - origin/main 実物では POST /staff は users を作らない（backend/app/routers/staff.py:556-623）ので、ADR-023 は未実装に見える。ステータス更新履歴は未確認。
- ADR-091（docs/adr/ADR-091-discord-bot-scope-definition.md）
  - :242-243 `connected_by_staff_id INTEGER REFERENCES public.staff(id) ON DELETE SET NULL`
  - :246-247 GET API で staff を JOIN して接続者名を返す
  - 実装は外部キーなしの INTEGER で、users.id が入る（§1-5）。ADR と実装が不一致。
- ADR-159（docs/adr/ADR-159-staff-identity-on-discord.md）
  - :14 staff に avatar 列が無く、given_name_en は任意だった
  - :26 英語名（名・姓）を必須化（DB は NOT NULL にしない）
  - :29 staff.avatar_token のみ保持
- ADR-1007（docs/adr/ADR-1007-migration-structure-only-run-once.md）
  - :31-36 migration は構造変更だけ。値の変更は画面・CSV・テナント作成コード・1 回だけのデータ変更（PO 合意、記録を docs/handoff/<topic>/ に残す）
  - :41-47 テナント作成は作った時点で完全にする
  - 影響: P1 の migration は外部キーの付け直しだけにし、値の付け替え（D2）は 1 回だけのデータ変更として別に行う。

## 1. 現状（コード）

### 1-1. public.users
- backend/app/models.py:22 `class User`、:25 id、:26 tenant_id（NOT NULL、FK tenants）、:27 username NOT NULL、:28 email NOT NULL unique、:30 role（default "user"）、:34 is_super_admin、:37 is_active（nullable、default True）、:38 last_login。firebase_uid 列は models.py に無い。
- テスト用の定義: backend/tests/rls_bootstrap.py:130-141（firebase_uid UNIQUE あり）、backend/tests/conftest.py:1172（sqlite 簡易表）。
- 本番の CREATE TABLE public.users は migrations/ に無い（材料の git grep 結果）。実 DDL は本番で確認済み（§2-1）。
- backend/app/routers/staff.py:218-224 のコメントに「users に firebase_uid が無い」旨の記載。

### 1-2. ログイン判定・権限（段階 1・2 反映後の実物）
- backend/app/auth/dependencies.py:72 get_current_user。email で引く: :170 `select(User).where(User.email == email, User.is_active == True)`。キャッシュ経路 :129、smoke 経路 :105 も同条件。firebase_uid は使わない。
- :174-178 行が取れなければ 401。:181-186 JWT claim に tenant_id があるときだけ突合。
- :194-232 get_current_tenant は tenants.is_active を見る（:211、:222）。staff.status は dependencies.py で参照されない（材料）。
- 食い違い（実物を正とする）: 材料 findings の「users.role の判定用の読み 10 件」は origin/main d4659832 時点。#4163 反映後の 8a421f22c では判定用の読みは 0 件。
  - コメント: backend/app/auth/dependencies.py:540、backend/app/auth/system_roles.py:18、backend/app/routers/roles.py:95、:161 が「users.role は見ない、正本は user_roles」と明記。
  - 残る参照: 書き込み backend/app/routers/auth.py:79 `role="user"`、出力 backend/app/routers/auth.py:96、backend/app/schemas/auth.py:57、:67。
  - frontend/src で `user?.role`、`role === "admin"` は 0 件。
  - 材料の dependencies.py:413 は docstring、:537/541 の全権限救済は実物の行と一致しない。

### 1-3. tenant.staff の定義
- backend/app/services/tenant.py:597-618: id SERIAL、tenant_id、:600 `user_id INTEGER UNIQUE REFERENCES public.users(id)`（NULL 許容）、staff_code、氏名各種、primary_email NOT NULL（一意制約なし）、role_id NOT NULL（FK roles）、status CHECK、firebase_uid UNIQUE。
- 同等: migrations/019_create_staff_tables.sql（staff 本体）。後付け列: is_employee（migrations/050_add_commissions.sql:48）、phone（migrations/083_add_staff_phone.sql:42）、avatar_token（migrations/20261001_120000_add_staff_avatar_token.sql:36）。
- backend/app/services/tenant.py:597-618 の CREATE には is_employee、phone、avatar_token が無い。backend/app/routers/staff.py:69 の `_STAFF_COLS` はこの 3 列を SELECT する。新規テナントへの付与経路は migration の流し直しのみ（backend/app/routers/admin.py:68 → create_tenant_schema は migrations を流さない）。実発生は未確認。
- 付属表: staff_emails backend/app/services/tenant.py:627、staff_ui_preferences :639（いずれも staff(id) を ON DELETE CASCADE で参照）。
- backend/app/schemas/staff.py:71、:105 `user_id: int | None`（登録・更新とも任意）。

### 1-4. staff.id を参照する列
| 列 | 外部キー定義 | 書き込み | 読み出し |
|---|---|---|---|
| bots.owner_staff_id | backend/app/services/tenant.py:678、migrations/020_create_bots_and_senders_view.sql:42 | backend/app/routers/bots.py:126-157（存在確認 :126-134、INSERT :146、:157） | backend/app/routers/bots.py:89、:110、:183、:202、:232、:263、:278（LEFT JOIN staff） |
| calendar_owner_settings.staff_id | migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql:55（CASCADE）。tenant.py に定義なし | backend/app/routers/calendar.py:251-280（PATCH /calendar/owners/{staff_id}） | backend/app/routers/calendar.py:179、:301（LEFT JOIN cos.staff_id = s.id）。現ユーザーの staff 解決 :60-63 は `user_id = :uid OR primary_email = :email` |
| companies.sales_rep_id | §3 | backend/app/routers/companies.py:388-412、:495-557 | backend/app/routers/analytics.py（§1-5） |
| order_commissions.staff_id | migrations/050_add_commissions.sql:131（SET NULL） | backend/app/routers/order_commissions.py:273-309（`_validate_staff` :240-250） | backend/app/routers/order_commissions.py:162、:183、:212、:230、:518、集計 :522 |
| staff_emails.staff_id | backend/app/services/tenant.py:629、migrations/019_create_staff_tables.sql:77 | backend/app/routers/staff.py:183-194 | backend/app/routers/staff.py:96 |
| staff_ui_preferences.staff_id | backend/app/services/tenant.py:640、migrations/019_create_staff_tables.sql:92 | backend/app/routers/staff.py:150-161 | backend/app/routers/staff.py:104 |
| tenant_meta_config.connected_by_staff_id | backend/app/services/tenant.py:1086、migrations/040_create_tenant_meta_config.sql:33 | backend/app/routers/meta_inbox.py:106-126（`_resolve_staff_id`: users.email → staff.primary_email）、:195-249、:537 | backend/app/routers/meta_inbox.py:744-748、:761-765（LEFT JOIN）、:818-819。表示のみ |
| meta_messages.sent_by_staff_id / seen_by_staff_id | migrations/041_extend_meta_messages.sql:42、:47 | backend/app/routers/leads.py:1172-1186（既読）、:1931-1944、:2093-2125（`_resolve_staff_identity`）、:2218-2223、:2390-2396、:2705-2717 | backend/app/routers/leads.py:990-1038（列を返すのみ） |
| public.tenant_discord_config.connected_by_staff_id | 外部キーなし。ADR-091:242-243 は public.staff を参照と記載（不一致） | backend/app/routers/discord_oauth.py:115 `staff_id=current_user.id`（= users.id）、:175-200 でそのまま保存 | backend/app/routers/discord_guild_config.py:77 `connected_by_staff_name = None`（JOIN なし） |

### 1-5. 「担当者」列が users.id か staff.id か
- leads.assigned_to: 外部キーなし INTEGER（backend/app/services/tenant.py:376）。POST は検証せず保存（backend/app/routers/leads.py:430-455）、更新可能列に含まれる（:84）。読み出しは users.id として扱う: backend/app/routers/analytics.py:111 `LEFT JOIN public.users u ON u.id = l.assigned_to`、:499-500、:1127、:1160、:1732、:1854、:1979 は `:uid`（current_user.id）と比較。backend/app/routers/goals.py:371 は team_members.user_id（users.id）。
- companies.sales_rep_id は staff.id を参照する外部キーだが、backend/app/routers/analytics.py:1330 `COALESCE(c.sales_rep_id, l.assigned_to) = :uid`、:1344、:1378、:1412 `LEFT JOIN users u ON u.id = COALESCE(...)`、:1527、:2199 で users.id として比較・結合している。→ staff.id と users.id が一致しない行で別の人に結び付く。
- 作成者系は users.id: quotes.created_by、calendar_events.created_by_user_id、goals.user_id（材料の行番号は未再確認）。
- 送信 UI: sales_rep_id / assigned_to を送る画面は frontend/src に 0 件（型のみ: frontend/src/pages/companies/CompaniesPage.tsx:63、frontend/src/pages/company-detail/company-detail.types.ts:39）。

### 1-6. frontend（staff.id を値に使う画面）
- frontend/src/pages/bots/BotsPage.tsx:108 GET /staff、:252 `<option key={s.id} value={s.id}>`、:135、:161 `owner_staff_id: parseInt(...)` を POST・PATCH /bots。
- frontend/src/pages/bots/BotEditPage.tsx:45 GET /staff。frontend/src/pages/bots/BotFormFields.tsx:77-78 owner_staff_id の選択。
- frontend/src/components/CommissionPanel.tsx:91 GET `/staff?per_page=100`、:113 `value: s.id`、:124 body `{ role, staff_id: staffId }`。
- frontend/src/pages/schedule/schedule-owner.ts:23-24、:38-39 は staffId と userId の両方を保持。frontend/src/pages/schedule/SchedulePageImpl.tsx:512、:543 は `owner.userId ?? owner.staffId` をキーに使う。frontend/src/pages/schedule/ScheduleSettingsPage.tsx:92 は PATCH `/calendar/owners/${owner.staffId}`。
- users.id を使う画面: frontend/src/pages/teams/TeamsPage.tsx:153（手入力 ID）、frontend/src/pages/roles/RolesPage.tsx:314（PUT /users/{id}/roles）。

### 1-7. スタッフ追加・利用者登録の流れ
- POST /staff（backend/app/routers/staff.py:556-623）: staff INSERT（user_id は入力が任意で入る :583）、staff_code 更新、ui_prefs、副メール、監査。users・user_roles・Firebase は触らない。
- users を作るのは POST /auth/register（backend/app/routers/auth.py:23-134）のみ（super admin 限定 :43）。User INSERT :74-83、user_roles INSERT :100-117（DEFAULT_NEW_USER_ROLE）、Firebase クレーム :123。staff 行は作らない。
- 手動の users INSERT: scripts/setup_review_tenant.py:330、scripts/setup_single_test_user.py:201、scripts/setup_test_users.py:217、scripts/qa/seed-tenant.sql:99（材料。行番号は未再確認）。
- 招待メールの実装は backend/app に無い（材料）。

### 1-8. staff 行の引き方の分布
- email 一致（primary_email）: backend/app/routers/staff.py:244、:337、:403、backend/app/routers/meta_inbox.py:117、backend/app/routers/leads.py:1172、:1936、:2106、:2710。いずれも ORDER BY id LIMIT 1 で、primary_email に一意制約は無い。
- user_id または email: backend/app/routers/calendar.py:60-63。
- staff 行が無い users の挙動: GET /staff/me 404（backend/app/routers/staff.py:253-257）、GET /calendar/owners 404（backend/app/routers/calendar.py:164-169）、Discord 送信は 422（backend/app/routers/leads.py:2218、:2390）、Meta 送信・既読は staff_id=None で続行。

### 1-9. users 一覧・is_active
- GET /users 一覧 API なし（材料）。is_active の参照: backend/app/auth/dependencies.py:105、:129、:170、backend/app/routers/teams.py:266。

### 1-10. migration の適用と検査
- 適用: scripts/run_all_migrations.sh が全件を毎回流し直す（冪等前提）。末尾に run_sql を追記する。.github/workflows/deploy.yml:504-521。
- 全テナントに流す型は DO ブロック＋ `pg_namespace WHERE nspname ~ '^tenant_[0-9]+$'`（migrations/20261001_120000_add_staff_avatar_token.sql:19-43 ほか）。`{schema}` プレースホルダは deploy で使えない（backend/CLAUDE.md）。
- 危険 PR: migrations/ を含む PR は GO 記録が必須（scripts/check-process-artifacts.js:116、.github/workflows/process-artifacts-gate.yml）。migration-guard は REFERENCES public.X の実在を検査（.github/workflows/migration-guard.yml:219）、`{schema}` 使用を禁止（:171）。これらの行番号は材料のまま。

## 2. 現状（本番、2026-10-12 読み取り専用。材料の値のまま）

### 2-1. public.users
- 列: id、tenant_id、username（NOT NULL・一意なし）、email（NOT NULL・UNIQUE `users_email_key`）、full_name、role、created_at、updated_at、is_active（NULL 可・default true）、last_login、locale、theme、is_super_admin。firebase_uid 列なし。
- 10 行（id: tenant, role, super_admin, active）: 1: t1 admin 〇 〇 / 2: t3 user / 3: t4 admin 〇 / 4: t4 user / 5: t4 user / 6: t4 user / 7: t5 admin / 8: t5 user / 9: t1 user / 10: t6 admin。全員 active。

### 2-2. tenant.staff（7 行）
- t1: staff 1（user_id NULL、メールが users 1 と一致）
- t4: staff 1（NULL、メールが users 3 と一致）、staff 7（NULL、メールが users 10 = t6 の人と一致。レビュー用アカウント）
- t6: staff 1（user_id=10、役割 1）、staff 8・9・10（NULL、メール一致なし、is_employee=t、role_id 4・4・3）
- t3、t5: 0 行。
- tenant_006.staff 制約: staff_user_id_fkey（users 参照）、staff_user_id_key（UNIQUE）など（recon-phase3-prod2.md Q2）。

### 2-3. 外部キー本数
- staff(id) を参照: 43 本（9 列 × 5 テナント。meta_messages は t6 に無い）。companies.sales_rep_id の FK 名は tenant_006 だけ fk_companies_sales_rep、他は companies_sales_rep_id_fkey。
- users(id) を参照: 32 本。

### 2-4. 値の入っている参照列
- t1: meta_messages.seen_by_staff_id=1（1 件）、sent_by_staff_id=1（1 件）
- t4: companies.sales_rep_id=1（42 件）、meta_messages.seen_by_staff_id=1（25 件）、tenant_meta_config.connected_by_staff_id=1（11 件）・=7（2 件）
- t6: tenant_meta_config.connected_by_staff_id=1（1 件）
- t3、t5: 0 件
- staff_ui_preferences は t1、t4、t6 に各 1 件（staff 1）。
- leads.assigned_to: t1 NULL 2 件、t4 NULL 56 件、t6 は 10 が 8 件・NULL 66 件。companies.sales_rep_id: t4 だけ 1 が 42 件。

### 2-5. 突き合わせ
- t4 companies.sales_rep_id=1（42 件）: 同テナントの staff 1 は谷澤 伸吾（users 3 とメール一致）。users.id=1 は tenant_1 の人 → analytics.py の users 結合は別テナントの人に結び付く。
- t6 leads.assigned_to=10（8 件）: users.id=10（t6）と staff.id=10（t6、未リンク）の両方に当たり、意図は判別不能。
- user_roles（user_id, role_id）: t1: (1,1)(9,1) / t3: (2,7) / t4: (3,1)(4,4)(5,5)(6,4) / t5: (7,1)(8,5) / t6: (10,1)。全件が同テナントの users に一致し、ロール無しの active users は 0。
- staff に到達できた 3 人のロールは一致。users 9（t1）は user_roles がオーナーだが users.role='user'。

## 3. P1 実物点検

### a. companies.sales_rep_id の定義と外部キー
- backend/app/services/tenant.py:224 `sales_rep_id INTEGER,  -- FK は staff 作成後に付与`、:233 索引 idx_companies_sales_rep_id。
- backend/app/services/tenant.py:650-661: コメント :650、`pg_constraint` に conname='fk_companies_sales_rep'（当該スキーマ）が無い場合だけ `FOREIGN KEY (sales_rep_id) REFERENCES {schema}.staff(id)` を付ける（:656、:660-661）。→ 新規テナントの FK 名は fk_companies_sales_rep。
- migrations/028_create_companies.sql:80 `sales_rep_id INTEGER REFERENCES %I.staff(id)`（列定義に埋め込み → 自動名 companies_sales_rep_id_fkey）。:102 索引。
- 旧 customers 側（現在は廃止済み）: migrations/015_replace_customers_schema.sql:89、migrations/019_create_staff_tables.sql:126-138（fk_customers_sales_rep）。backend/app/services/tenant.py:653 に ADR-089 で廃止のコメント。
- 本番の FK 名: tenant_006 は fk_companies_sales_rep、他 4 テナントは companies_sales_rep_id_fkey（§2-3）。名前に依存せず、参照先と列で探す必要がある。
- 外部キー名 fk_companies_sales_rep / companies_sales_rep_id_fkey を含むのは `git grep` の結果、backend/app/services/tenant.py:656、:660 のみ（docs 除く）。

### b. sales_rep_id を読む・書く全箇所（`git grep -n sales_rep_id`、docs と .claude-pipeline を除く）
- backend/app/routers/companies.py
  - :85 `_COMPANY_COLUMNS`、:98 `_UPDATABLE_COLUMNS` に sales_rep_id
  - POST: :388、:397、:412 `"sales_rep_id": data.sales_rep_id`（存在確認なし。:363 create_company）
  - PATCH: :500 update_company。:521 `data.model_dump(exclude_unset=True)`、:531 `_UPDATABLE_COLUMNS` で絞り、:551 `UPDATE companies SET {set_sql}` に渡す。sales_rep_id 個別の検証なし。
  - merge_companies（:683、:678 から）: sales_rep_id の参照 0 件（master 側の値がそのまま残る）。
- backend/app/schemas/company.py: :7（コメント）、:118 `sales_rep_id: int | None = Field(default=None, description="担当スタッフ id")`、:143（更新用）、:173（応答）。
- backend/app/routers/analytics.py: :1330、:1344、:1378、:1412、:1524（コメント）、:1527、:2199。
- backend/app/services/tenant.py: :224、:233、:650-661。
- backend/tests: backend/tests/conftest.py:203（sqlite の companies、FK なし）、backend/tests/test_analytics.py:991-995（999 と 321 を直接 UPDATE）。それ以外 0 件。
- frontend/src: 型のみ（frontend/src/pages/companies/CompaniesPage.tsx:63、frontend/src/pages/company-detail/company-detail.types.ts:39、frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:18 のテストデータ）。送信コードは 0 件。frontend/tests-e2e/scene1-dashboard.spec.ts:498、frontend/tests-e2e/ui-companies-edit-modal-i18n.spec.ts:30、frontend/tests-e2e/ui-company-detail-tabs.spec.ts:24 は null のテストデータ。frontend/api-contract/openapi.json:4588、:5034、:5097、:5341（生成物）。
- scripts/: scripts/_archive/data_migration/migrate_companies_contacts_from_customers.py（:194-529 ほか）、scripts/_archive/data_migration/migrate_customers_from_sheet.py（:142-249）、scripts/_archive/data_migration/verify_customers_migration.py:155-162（いずれも archive）。scripts/migrate_phase1_redesign.py:16 はコメントのみ。
- backend/app/routers/integrations.py:651 の companies INSERT は sales_rep_id を含まない（材料）。

### c. 「同じテナントの users に存在するか」確かめる処理の流用候補
- backend/app/routers/roles.py:500 と :534 `SELECT id FROM public.users WHERE id = :uid AND tenant_id = :tid`（不在は 404。:499-505 は GET の対象確認、:533-539 は PUT の対象確認）
- backend/app/routers/teams.py:266 `SELECT id FROM public.users WHERE id = :uid AND tenant_id = :tid AND is_active = TRUE`（不在は 400、:265-271）
- 上記以外に同形の処理は `git grep "FROM public.users WHERE id"` で 0 件。
- 対比: 現行の companies POST は存在確認なし。bots は staff の存在確認あり（backend/app/routers/bots.py:126-134）、order_commissions も `_validate_staff`（backend/app/routers/order_commissions.py:240-250）。

### d. 外部キーの付け直しの既存 migration 実例（pg_namespace 走査）
- migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql:18-60 が最も近い。
  - :19 `pg_namespace WHERE nspname ~ '^tenant_[0-9]+$'` で全テナントを走査
  - :24-32 表・列が無いテナントは CONTINUE
  - :35-42 `pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (product_id)%'` で既存 FK を名前非依存で探して外す
  - :46-57 新しい FK が無ければ付与（public.products 参照）。FK 名は `tbl || '_product_id_public_fkey'`
  - 本番の FK 名がテナントごとに違う場合（§2-3）にそのまま使える形。
- ほかに migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:101、:116-117、migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:93、:113-114（public 側表への付け直し）。
- 「IF EXISTS 付きで外してから付け直す」書き方の実例: migrations/20260918_030000_supplier_ssot_phase2.sql:193（動的 SQL、IF EXISTS 付き）。
- users(id) への付け直しで、companies に対し同じ処理をしている migration は 無し。

### e. 試験と試験用スキーマ
- 試験が companies を作る箇所: backend/tests/test_companies.py（POST /api/v1/companies を sales_rep_id なしで呼ぶ。:12、:24 ほか）、backend/tests/test_audit_subtable_diff.py:266（直接 INSERT、sales_rep_id なし）。sales_rep_id を扱う試験は backend/tests/test_analytics.py:991-995 のみ（999、321 を UPDATE）。
- backend/tests/conftest.py（sqlite）: :198 companies、:203 `sales_rep_id INTEGER`（FK なし）。:340 staff（user_id INTEGER、FK なし）、:1172 users（簡易表）、:1185-1186 users 999（tenant 999）を投入。sqlite なので FK 変更の影響は受けない。
- backend/tests/rls_bootstrap.py: :130-141 public.users、:281 `create_tenant_schema(conn, tenant_id, admin_db=conn)` を呼ぶ → 実 Postgres では backend/app/services/tenant.py:650-661 の FK（fk_companies_sales_rep → staff）が作られる。tenant.py を直すと試験側にも反映される。companies の直接定義は無い。
- .github/workflows/migration-test.yml
  - migration-test-run ジョブ（:88-）: :305 tenant_001.companies、:447 tenant_002.companies を sales_rep_id なしで事前作成（FK なし）。:196 public.users、:259 tenant_001.staff。
  - migration-full-dryrun ジョブ（:1050-）: :1251、:1355 のコメントどおり companies は事前作成せず migration 028 が作る → companies_sales_rep_id_fkey（staff 参照）。:1118 public.users（email UNIQUE）、:1197 tenant_001.staff、:1383 tenant_002.staff。:1027-1039 は二回流しの冪等性確認（材料）。
- 影響: 付け直し migration は、全件ドライラン（028 が作る FK）と実 Postgres 試験（tenant.py が作る FK）の両方で通る必要がある。FK 名が 2 種類あるので、名前を決め打ちしない書き方（§3-d）が要る。

### f. scripts/run_all_migrations.sh の末尾と最新 migration
- scripts/run_all_migrations.sh 全 912 行。末尾 5 行（:908-912）:
```
# extraction_attempts に Gemini の思考要約の列を足す（構造のみ）
run_sql migrations/20261012_200000_add_extraction_attempts_thought_summaries.sql

# tcg_distribution_targets に要確認タブ名の列を足す（構造のみ・冪等。値は docs/handoff/review-sheet-export/data/ の1回だけのデータ変更）
run_sql migrations/20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql
```
- migration 028 の登録: scripts/run_all_migrations.sh:98。
- `ls migrations | tail -5`:
```
20261010_120000_create_analysis_soldout_extra_targets.sql
20261011_150000_add_analysis_results_price_basis.sql
20261012_100000_add_extraction_jobs_system_review_detail.sql
20261012_200000_add_extraction_attempts_thought_summaries.sql
20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql
```

## 4. 未確認
1. 新規テナントで staff の追加列（is_employee、phone、avatar_token）が欠ける問題の実発生。
2. leads.assigned_to と companies.sales_rep_id を本番で実際に書いた経路（フロントに送信 UI が無い）。
3. 本番 public.users の外部キー参照元のうち、材料で確認していない列の実値（材料に記載の範囲外）。
4. ADR-023 の正式な実装ステータス（ステータス更新履歴）。
5. meta_messages.sent_by_staff_id / seen_by_staff_id の名前結合の有無（backend/app/routers/leads.py:990-1038 は列を返すのみ確認）。
6. 材料から転記した行番号のうち §1-5（quotes.created_by など）、§1-7 の手動 INSERT スクリプト、§1-10 の CI 行は、今回実物では再確認していない。
7. 招待メールの実装有無（backend/app には未発見）。
8. GAS / CSV 経由の sales_rep_id 書き込み、本番の users.id と staff.id の将来の一致状況（D1 実施後に再測定）。
