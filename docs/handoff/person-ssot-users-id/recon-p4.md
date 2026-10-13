# recon-p4: 重複4列（staff.role_id / staff.primary_email / staff.firebase_uid / users.role）の全参照

基準: origin/main（fetch 済み）。引用はリポジトリ相対 path:行。メール・firebase_uid の値は出していない。

## 0. 先に結論（事実）

- 名簿の PATCH /staff で role_id を変えても user_roles は変わらない。UPDATE staff だけ（backend/app/routers/staff.py:696-702）。user_roles へ書くのは POST /staff の作成時だけ（:624-631）。権限キャッシュの破棄（invalidate_user_permissions）も PATCH では呼ばない（呼ぶのは :641 の作成時のみ）。
- PATCH /staff の primary_email 変更は staff 行だけ更新し、public.users.email は変えない（:696-702）。ログインに使うメールは users.email なので、名簿のメールを直しても login には効かない。
- staff.role_id の読み出しは、名簿 API の `LEFT JOIN roles r ON r.id = s.role_id` で role_name を出す用途に集約（:277,359,397,437,545,565,656,671,722,734）。backend/app 内で staff.role_id を権限判定に使っている箇所は 0 件（grep で s.role_id は staff.py のみ）。
- 本番（5テナントの staff 計5行）: staff.role_id は全行 user_roles に含まれる（in_ur = t）。primary_email は全行 users.email と lower 一致。firebase_uid は NULL でない行が 1 件（tenant_006 の id=1）。staff_emails は全テナント 0 件。users.role は admin 4 / user 9。

## 1. 列A: tenant.staff.role_id

### 1-1 定義
- backend/app/services/tenant.py:610 `role_id INTEGER NOT NULL REFERENCES {schema}.roles(id)`（外部キー、ON DELETE 指定なし）
- backend/app/services/tenant.py:621 `idx_staff_role_id`
- migrations/019_create_staff_tables.sql:48（定義）、:59（索引）
- ビュー: staff.role_id を使うビューは repo 内に 0 件。v_senders（tenant.py:709-719、migrations/020_create_bots_and_senders_view.sql:70-77）は role_id を含まない。
- トリガ: trg_staff_updated_at（tenant.py:694-697）は updated_at のみ。列名なし。
- RLS: tenant.py:1363-1370 tenant_isolation_staff（列名なし）。
- 試験用スキーマ: backend/tests/conftest.py:353 `role_id INTEGER NOT NULL`（SQLite、FK なし）。rls_bootstrap.py に staff 定義なし。.github/workflows/migration-test.yml:259-267, 1197-1205, 1383-1391 の簡易 staff 表は role_id 列を持たない（id, tenant_id, user_id, full_name, is_active, created_at, updated_at）。

### 1-2 backend/app の読み書き
| 場所 | 用途 |
|---|---|
| backend/app/schemas/staff.py:68 StaffCreate.role_id: int（必須） | 書き込み入力 |
| backend/app/schemas/staff.py:102 StaffUpdate.role_id: int \| None | 書き込み入力 |
| backend/app/schemas/staff.py:160-161 StaffResponse.role_id: int / role_name: str \| None | 表示（レスポンス項目名 role_id, role_name） |
| backend/app/routers/staff.py:111 _STAFF_COLS に s.role_id、:114 r.name AS role_name | 読み出し（全 SELECT の共通列） |
| backend/app/routers/staff.py:120 _UPDATABLE に "role_id" | PATCH で書ける列の許可リスト |
| backend/app/routers/staff.py:124-136 _ensure_assignable_role | 照合（同テナントに存在・隠すロールでないこと。priority 上限の検査はない） |
| backend/app/routers/staff.py:277,359,397,437,545,565,656,671,722,734 `LEFT JOIN roles r ON r.id = s.role_id` | 表示（role_name を出す）。10 箇所。GET /staff/me、PATCH /staff/me/profile、一覧、1件、作成後、更新前後、削除前 |
| backend/app/routers/staff.py:587,599,604,614 | POST /staff で INSERT（書き込み） |
| backend/app/routers/staff.py:624-631 | POST /staff で同じ role_id を user_roles にも INSERT（ON CONFLICT DO NOTHING）。ここだけが staff→user_roles の橋 |
| backend/app/routers/staff.py:693-702 | PATCH /staff で role_id 検証→UPDATE staff（user_roles は触らない） |
| backend/app/services/tenant.py:610,621 | 定義 |
| 検索条件 | role_id を検索・並べ替えに使う箇所はなし（list_staff の search は :535 で staff_code/氏名/primary_email のみ） |

backend/app 内のそれ以外の role_id は roles.py・auth.py・dependencies.py・discord_*・tenant_admin_inventory_visibility.py・central_masters.py・schemas/role.py の role_permissions / user_roles / Discord の staff_role_id で、staff.role_id とは別物。

### 1-3 frontend
- frontend/src/pages/staff/StaffPage.tsx:54 型 role_id:number、:55 role_name、:82,91,97 フォーム初期値、:104 編集フォームへ String(s.role_id)、:166 作成送信 parseInt、:193 更新送信 parseInt、:265-266 作成フォームの選択欄、:348-350 一覧の「ロール」列は s.role_name を表示（`s.role_name || "-"`）
- frontend/src/pages/staff/StaffEditPage.tsx:46 型、:70,81 フォーム、:111 読込、:141 送信、:188-189 選択欄
- frontend/src/pages/staff/StaffFormFields.tsx:16 型、:70-71 選択欄
- vitest: frontend/src/components/StaffFormButtonMigration.test.tsx:23（role_id:2, role_name）、:62（送信期待 role_id:3）
- tests-e2e: staff の role_id を含むモックは 0 件（tenant-inventory-visibility.spec.ts の role_id は在庫表示ロールAPIで別物）
- openapi.json（frontend/api-contract/openapi.json）: role_id を含む行 29 本のうち、Staff 系は StaffCreate :29336/:29397、StaffResponse :29858/:29956、StaffUpdate :30112 の 5 行（行番号は properties 内の行と required 内の行）。残りは RoleVisibility*（:27803,27816,27858,27868）、UserRoleResponse（:34665,34675）、パラメータ role_id（:35702,50608,50647,50705,50755）。

### 1-4 scripts ほか
- scripts/data_migration/migrate_staff_from_sheet.py:151-166（INSERT/UPSERT）
- scripts/data_migration/verify_staff_migration.py:9,119（全 staff の role_id が roles に存在するか）
- scripts/qa/seed-tenant.sql:107-118（staff INSERT）、:126（SELECT u.id, s.role_id で user_roles を作る。primary_email = u.email で結合 :128）
- scripts/setup_review_tenant.py:254、scripts/setup_single_test_user.py:279,316-317
- tests/qa-smoke/scene-06.spec.ts:24（読み出し）、:75,:79（`UPDATE tenant_006.staff SET role_id = ...` を直接実行）
- monitoring/・gas/: 0 件（gas ディレクトリは origin/main に存在しない）
- backend/tests で role_id が staff に関わる試験: conftest.py:353、test_bots_owner_users.py:37、test_order_commissions.py:383-415、test_roles_hidden_system_admin.py:156-192,237（PATCH /staff の role_id 400 / 200）、test_staff_avatar.py:63,306、test_staff_code_auto_number.py:40、test_staff_create_users.py:21,53,75（作成時に user_roles へ入ることを検証）、test_staff_me.py:27,65,91,114,140,175

### 1-5 外した場合の代替
- 名簿のロール表示（role_name）: user_roles を JOIN する。既存の JOIN の型は次の 3 つ。
  - backend/app/routers/roles.py:506-513 `SELECT ur.role_id, r.name AS role_name, r.color, r.priority ... FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE ur.user_id = :uid AND {_visible_role_sql("r.system_key")} ORDER BY r.priority DESC`（GET /users/{user_id}/roles。隠すロールの除外つき）
  - backend/app/routers/roles.py:98-105 `_max_priority_for_user`（user_roles JOIN roles で最大 priority）
  - backend/app/auth/dependencies.py:480-488 `get_user_system_keys`
- 入力（作成・編集フォームのロール選択）: 外す場合は PUT /users/{user_id}/roles（roles.py:520-594、role_ids の配列、priority 検査つき、権限 roles.assign）に寄せるか、PATCH /staff が内部で同じ処理を呼ぶ形にする必要がある。現状の PATCH /staff の role_id 経路には priority 検査と user_roles 更新がない。
- フロントの StaffPage は role_name を一覧に出すだけ。名簿用の「1人1ロール」前提は staff 型（role_id: number）にある。

## 2. 列B: tenant.staff.primary_email

### 2-1 定義
- tenant.py:608 `primary_email VARCHAR(255) NOT NULL`、:622 `idx_staff_primary_email`。UNIQUE なし（migrations/019:46 に「UNIQUE 制約なし（共有アドレス運用許容）」、:68-69 COMMENT）
- ビュー: tenant.py:709-719 / migrations/020:70-77 の v_senders が `primary_email AS contact_email`（staff 側の枝）。使う側の backend/app・frontend・scripts のコードは grep で 0 件（定義のみ）。
- 試験用: conftest.py:351（staff）。別表の primary_email（contacts: conftest.py:240、tenant.py:248,263）は別物。test_discord_inbox.py:128、test_message_image_send.py:150、test_message_send.py:168、test_messages.py:144、test_meta_channels.py:100、test_meta_oauth_endpoints.py:102、test_outbound_draft_send.py:147、test_rls_tenant_meta_config.py:96、test_502_paths.py:90 が各ファイル内で staff の CREATE を持ち primary_email 列を含む。migration-test.yml の staff 簡易表は primary_email 列なし。

### 2-2 backend/app の読み書き
| 場所 | 用途 |
|---|---|
| schemas/staff.py:66 StaffCreate.primary_email（必須）、:79-85 検証 | 書き込み入力 |
| schemas/staff.py:100,114 StaffUpdate.primary_email | 書き込み入力 |
| schemas/staff.py:158 StaffResponse.primary_email: str | 表示 |
| routers/staff.py:111 _STAFF_COLS、:120 _UPDATABLE | 読み出し・更新許可 |
| routers/staff.py:101 | public.users 新規作成時の email に data.primary_email を使う（users.email への書き込み） |
| routers/staff.py:73,:597-615 | :73 は `lower(email) = lower(:email)` で既存 users を引く（照合）。:598,613 は staff.primary_email へ INSERT |
| routers/staff.py:535 | list_staff の search（ILIKE）で検索 |
| routers/calendar.py:59,172,249,294 SELECT s.primary_email、:53 表示名のフォールバック、:197,317 OwnerRosterItem.primary_email（レスポンス項目名 primary_email、:81） | 表示（カレンダーのオーナー名簿） |
| routers/meta_inbox.py:720,737 `COALESCE(s.surname_jp \|\| ' ' \|\| s.given_name_jp, s.primary_email) AS staff_name`（staff は s.user_id = tmc.connected_by_staff_id で結合 :723,740） | 表示（氏名が空のときのフォールバック） |
| services/calendar_service.py:116-122 | staff を結合するが氏名のみ。primary_email は使わない |
- contacts.py / invoices.py / registration_tokens.py / integrations.py / schemas/contact.py の primary_email は contacts 表の列で別物。

### 2-3 frontend
- StaffPage.tsx:52,80,91,97,103,164,192,257,342（型・フォーム・送信・一覧の「メール」列 `{s.primary_email}` と副メール件数 `+{s.emails.length}` :340-346）
- StaffEditPage.tsx:44,68,80,109,139,180、StaffFormFields.tsx:15,63-64
- 本人画面: ProfileSection.tsx:27,57（`setEmail(me.primary_email)`。GET /staff/me の結果を本人のメール欄に表示）、UiPrefsContext.tsx:75（型）
- カレンダー: frontend/src/pages/schedule/schedule-owner.ts:8,42（GET のオーナー名簿 primary_email）
- vitest: StaffFormButtonMigration.test.tsx:21,62、AccountCompanySaveButtonMigration.test.tsx:17、ProfileSectionAvatar.test.tsx:19
- tests-e2e（/staff/me などのモックに primary_email）: analysis-rules-line-guide.spec.ts:32、f11-ac11-5-super-admin-inventory-offers.spec.ts:26、inbox-header-ui-screenshots.spec.ts:36、lead-channel-control.spec.ts:49、lead-country-control.spec.ts:49、order-commission.spec.ts:82,90、product-edit-tcg-type.spec.ts:69、scene1-dashboard.spec.ts:437、send-guard-screenshots.spec.ts:41、super-admin-phase-switch.spec.ts:24、tcg-import-workflow.spec.ts:57,208,329,361、tenant-inventory-visibility.spec.ts:22、ui-company-detail-tabs.spec.ts:59（これは contacts の可能性あり。未確認）、utils/common-mocks.ts:49、visual-language/inbox-helpers.ts:44（計 15 ファイル。contacts 用の混在は未仕分け）
- openapi.json: Staff 系 primary_email は StaffCreate :29331/:29396、StaffResponse :29854/:29954、StaffUpdate :30100 の 5 行。OwnerRosterItem :20768/:20808。Contact 系 :6507,6897,6956,7108 は contacts で別物。

### 2-4 scripts ほか
- scripts/data_migration/migrate_staff_from_sheet.py:11,119,139-194（シートのメール→primary_email、他の行は staff_emails へ）
- scripts/qa/seed-tenant.sql:88,91,107-128,319、scripts/qa/cleanup-smoke-data.sh:68,103,106（qa- 接頭の primary_email で行を特定して削除）
- scripts/setup_review_tenant.py:233,254、scripts/setup_single_test_user.py:251,279,329（primary_email で既存 staff を探す＝照合）
- tests/qa-smoke/scene-06.spec.ts:25,75,79（primary_email で行を特定）
- backend/tests で staff の primary_email を使う試験: test_bots_owner_users.py:37、test_calendar_owner_api.py（モック 7 箇所）、test_discord_inbox.py:407、test_discord_staff_send.py:112、test_meta_channels.py:350、test_order_commissions.py:401、test_roles_hidden_system_admin.py:160、test_staff_avatar.py:63,306、test_staff_code_auto_number.py:40、test_staff_create_users.py:21、test_staff_me.py（12 箇所。:16 は「名簿の primary_email は users.email と別でも user_id で引ける」ことを確認する試験）
- monitoring/・gas/: 0 件

### 2-5 代替
- 表示: `LEFT JOIN public.users u ON u.id = s.user_id` で `u.email`。staff.user_id は NOT NULL 化済み（migrations/20261013_120000_staff_user_id_not_null.sql:27、tenant.py:600 `user_id INTEGER NOT NULL UNIQUE REFERENCES public.users(id)`）なので JOIN は内部結合でも成立する。既に staff→users の結合は routers/staff.py:161-177（locale/theme を users から取得）、services/calendar_service.py:119-122 にある。
- 検索（routers/staff.py:535）: `u.email ILIKE :search` に差し替え。
- 照合: scripts の `WHERE primary_email = :email` は `JOIN public.users u ON u.id = s.user_id WHERE lower(u.email) = lower(:email)`。
- 書き込み（POST）: users.email へはすでに入れている（:101）。staff 側の INSERT 列を外すだけでよい。PATCH で primary_email を変える場合は users.email を更新する処理が新しく必要（users.email は UNIQUE: models.py:28 `unique=True`。重複時の 409 設計が要る）。
- 副メール: staff_emails はそのまま（本番 0 件、routers/staff.py:139-144,226-242）。
- v_senders の contact_email: users.email の JOIN に定義を作り直す必要がある（ビューの定義変更はテナント数分の migration）。

## 3. 列C: tenant.staff.firebase_uid

### 3-1 定義
- tenant.py:613 `firebase_uid VARCHAR(128) UNIQUE`（UNIQUE 制約が暗黙の索引）。migrations/019:51,70-71（COMMENT: 認証時の突合に使用）。専用の索引・ビュー・トリガなし。
- public.users: backend/app/models.py:22-38 に firebase_uid 列なし（User モデル）。試験の backend/tests/rls_bootstrap.py:133,148 は試験用 public.users に firebase_uid 列を持つ（本番とは違う形）。test_export_inventory_for_sheet.py:75 も public.users に firebase_uid を INSERT（試験内）。
- 試験用 staff: conftest.py:355。

### 3-2 backend/app の読み書き（staff.firebase_uid）
| 場所 | 用途 |
|---|---|
| schemas/staff.py:70 StaffCreate、:104 StaffUpdate、:163 StaffResponse（firebase_uid: str \| None） | 書き込み入力・表示 |
| routers/staff.py:111 SELECT、:120 _UPDATABLE、:599,604,615 POST で INSERT | 書き込み・読み出し |
| routers/staff.py:259-266（docstring のみ） | 「User に firebase_uid が無く firebase_uid 経路は dead code だったので削除」と明記。/staff/me は user_id で引く（:273-281） |
- ログイン照合に staff.firebase_uid を使う箇所は backend/app に 0 件（grep の firebase_uid ヒットは auth/utils.py:13-15, routers/auth.py:123, schemas/auth.py:26 の UserRegister.firebase_uid＝Firebase カスタムクレーム設定用の引数、leads.py:1185 コメント、tenant.py:613 のみ）。UserRegister.firebase_uid は staff 列とは別物（POST /register の入力。DB へは保存しない: routers/auth.py:74-82）。

### 3-3 frontend
- StaffPage.tsx:57 型、:84,92 フォーム、:168 作成送信 `firebase_uid: toNull(...)`。作成フォームの入力欄（TextFieldControl）の有無: 未確認（:168 は送信、入力欄の描画行は grep に出ていない）
- StaffEditPage.tsx:48,72,82,113,143,204（編集フォームに入力欄あり :204）
- vitest: StaffFormButtonMigration.test.tsx:24,65
- tests-e2e: 0 件
- openapi.json: StaffCreate :29288、StaffResponse :29791/:29958、StaffUpdate :30039 の 4 行。UserRegister :34533/:34567（別物）。

### 3-4 scripts ほか
- scripts/data_migration/migrate_staff_from_sheet.py:10,152（NULL で投入）、verify_staff_migration.py:8,104-108（重複 0 件検査）
- scripts/qa/seed-tenant.sql:21-23,107-118、scripts/qa/reset-tenant.sh:120-122、scripts/setup_review_tenant.py:229,254,271,287,347,365,479-487、scripts/setup_single_test_user.py:239,279,297,507、scripts/setup_test_users.py:187,232,284-285（Firebase UID を作って staff に入れる／カスタムクレーム設定）
- backend/tests: conftest.py:355、rls_bootstrap.py:133,148、test_admin_api_super_admin_only.py:23、test_export_inventory_for_sheet.py:75（後二者は staff ではなく users または payload 側）
- monitoring/・gas/・.github: 0 件

### 3-5 代替
- 代替は不要と読める（根拠: 読み出しはレスポンスに返すだけで、判定・照合に使う箇所が backend/app に 0 件。ログインは users を email で引く）。ただし「ログインが users.email で引く」実装本体の file:line は今回の grep 範囲（staff 周辺）では未確認。認証経路（backend/app/auth/ 内のメール引き）は別途確認が要る。
- 外すときの作業: スキーマ 3 項目（Create/Update/Response）、フォーム 2 画面、スクリプト 4 本、openapi、vitest 1 件。UNIQUE 制約は列と一緒に消える。

## 4. 列D: public.users.role

### 4-1 定義
- backend/app/models.py:30 `role = Column(String(50), default="user")`。users 表の CREATE は migrations/ に存在しない（grep で CREATE TABLE users は migration-test.yml のみ）。.github/workflows/migration-test.yml:202 と :1124 に `role VARCHAR(50) DEFAULT 'user'`。:252 の `role VARCHAR(50) NOT NULL` は別表（users ではない。どの表かは未確認）。
- 試験: backend/tests/rls_bootstrap.py:136,148-150（role='admin' を INSERT）、conftest.py:1186（SQLite の users INSERT に role）
- ビュー・トリガ・索引: users.role に付いたものは repo 内 0 件。

### 4-2 backend/app の読み書き
| 場所 | 用途 |
|---|---|
| backend/app/models.py:30、:32 コメント（「テナント admin (role='admin')」） | 定義 |
| backend/app/routers/auth.py:79 `User(... role="user" ...)` | 書き込み（POST /register で固定値 'user'） |
| backend/app/routers/auth.py:96 | 書き込み（監査ログ new_data に role を記録） |
| backend/app/routers/staff.py:97-98 `INSERT INTO public.users (..., role, is_active) VALUES (..., 'user', true)` | 書き込み（名簿作成時の固定値 'user'） |
| backend/app/schemas/auth.py:57 TokenData.role: str、:67 UserResponse.role: str | 出力項目（POST /register のレスポンス。from_attributes で User.role を返す） |
- 判定への使用: なし。権限判定は user_roles（auth/dependencies.py:474-489,540、auth/system_roles.py:18、routers/roles.py:95,161 のコメントが「users.role は見ない」と明記）。
- TokenData.role（schemas/auth.py:57）を生成・参照するコードの有無: 未確認（今回は定義行のみ確認）。

### 4-3 frontend
- UserResponse.role を読むフロントのコード: 0 件（frontend/src の `.role` 参照は design-system のサンプル・DbViewerPanel.tsx:129 の列名リストのみ）。DbViewerPanel.tsx:129 は "role" という文字列を含む。何の一覧かは未確認（今回その行しか見ていない）。
- openapi.json: UserResponse の role（OrderCommission*/MonthlyByRoleItem の role は別物）。行番号は未確認。

### 4-4 scripts・試験
- scripts/qa/seed-tenant.sql:99、scripts/setup_test_users.py:217、scripts/setup_single_test_user.py:201、scripts/setup_review_tenant.py:330（public.users INSERT に role を含む）
- scripts/migrate_phase1.py:191（コメント: `role='admin' → オーナー、それ以外 → メンバー`）。移行用の過去スクリプト。
- migrations/064_add_users_is_super_admin.sql:42（COMMENT に users.role='admin' への言及）
- backend/tests: `u.role = "admin"` を使う試験 — test_discord_d2.py:87、test_inventory_offers_rbac.py:28,44、test_priority_prospects_pg_rls.py:53、test_real_redis_lockout.py:83、test_super_admin_phase_switch.py:91、test_super_admin_unit_ignore_phrases.py:46。INSERT に role 列を含む試験 — test_bots_owner_users.py:23、test_companies_sales_rep_users.py:17,24、test_order_commissions.py:423,538、test_roles_hidden_system_admin.py:43、test_staff_create_users.py:61,98。「users.role は見ない」を検証する試験 — test_tenant_admin_ssot.py:1-5、test_google_calendar.py:271-300、test_roles.py:18,90,225、test_roles_hidden_system_admin.py:31。
- monitoring/・gas/: 0 件

### 4-5 代替
- 権限判定の代替は不要（すでに user_roles が正本）。
- 出力: POST /register の UserResponse.role と TokenData.role。外す場合は schemas/auth.py:57,67 の項目削除（互換が要るなら固定値か user_roles の最高 priority ロール名）。auth.py:79,96 と staff.py:97-98 の書き込み 3 箇所を削る。
- 試験用スキーマ・INSERT の role 列が 8 ファイル超に散っている（上記）。

## 5. 6. staff.role_id と user_roles の関係
- user_roles の定義: backend/app/services/tenant.py:518-525。`id SERIAL PRIMARY KEY`、`user_id INTEGER NOT NULL`（FK なし）、`role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE`、`UNIQUE(user_id, role_id)`。1人に複数ロール可（主キーは id、一意制約は (user_id, role_id) の組）。テスト側 conftest.py:748-751 も同じ UNIQUE。
- 複数ロールの前提が既にコードにある: 権限は和集合（dependencies.py:501 docstring「Discord方式: 複数ロールの権限を和集合で判定」、:510-518）。PUT /users/{id}/roles は role_ids 配列を受ける（schemas/role.py:91 `role_ids: list[int] = Field(min_length=1)`、routers/roles.py:524-594）。
- 名簿でロールを変える操作: PATCH /staff/{id} の role_id（routers/staff.py:693-702）。user_roles は変わらない（上記 0 章）。ロールを実際に変える操作は PUT /users/{user_id}/roles（RolesPage.tsx:312-323、画面は対象ユーザーID を数値入力し、ロールをチェックボックスで複数選択 :556-570。既存の付与状況を表示する欄はない）。
- 名簿の作成: POST /staff が staff.role_id と user_roles を同時に作る（:599-631）。
- 既存の複数ロール表示の材料: GET /users/{user_id}/roles が `ORDER BY r.priority DESC` で返す（roles.py:506-512）。UserRoleResponse に color と priority がある（schemas/role.py:96 周辺）。名簿に出す場合の候補 — (a) 最高 priority の 1 件を表示、(b) 全ロールを priority 降順で並べて表示。どちらも既存 API と同じ並び順になる。隠すロール（_visible_role_sql）を super admin 以外に出さない処理が roles.py:511 にあるので、名簿側でも同じ除外が要る。
- 本番では全員 1 ロール（下の 7 章）で、staff.role_id と user_roles の食い違いは 0 件。

## 6. 本番の読み取り（生出力）

注意（実施の事実）: 次のうち tenant_001 と tenant_003 の 2 回は、指定の「単一引用符で囲んだ 1 行」ではなく、for ループと二重引用符の外側（bash -c 風）で実行した。内容は SELECT のみの読み取り（SET default_transaction_read_only = on; BEGIN READ ONLY; ... ROLLBACK;）で同じ。tenant_004/005/006 と users.role と staff_emails は指定形式で実行。

### 6-1 staff 行ごと（id, user_id, staff.role_id, user_roles の role_id 一覧, staff.role_id が user_roles に含まれるか, primary_email と users.email の lower 一致, firebase_uid が NULL でないか）

tenant_001
```
 id | user_id | role_id | ur_roles | in_ur | email_match | fb_not_null 
----+---------+---------+----------+-------+-------------+-------------
  1 |       1 |       1 | {1}      | t     | t           | f
(1 row)
```
tenant_003
```
 id | user_id | role_id | ur_roles | in_ur | email_match | fb_not_null 
----+---------+---------+----------+-------+-------------+-------------
(0 rows)
```
tenant_004
```
 id | user_id | role_id | ur_roles | in_ur | email_match | fb_not_null 
----+---------+---------+----------+-------+-------------+-------------
  1 |       3 |       1 | {1}      | t     | t           | f
(1 row)
```
tenant_005
```
 id | user_id | role_id | ur_roles | in_ur | email_match | fb_not_null 
----+---------+---------+----------+-------+-------------+-------------
(0 rows)
```
tenant_006
```
 id | user_id | role_id | ur_roles | in_ur | email_match | fb_not_null 
----+---------+---------+----------+-------+-------------+-------------
  1 |      10 |       1 | {1}      | t     | t           | t
  8 |      80 |       4 | {4}      | t     | t           | f
  9 |      81 |       4 | {4}      | t     | t           | f
 10 |      82 |       3 | {3}      | t     | t           | f
(4 rows)
```

### 6-2 public.users.role の値別件数
```
 role  | n 
-------+---
 admin | 4
 user  | 9
(2 rows)
```

### 6-3 staff_emails の件数（テナントごと）
```
 t001 | t003 | t004 | t005 | t006 
------+------+------+------+------
    0 |    0 |    0 |    0 |    0
(1 row)
```

### 6-4 集計（生出力の後）
- staff 行は計 5 行（001:1, 004:1, 006:4。003 と 005 は 0 行）。全行で in_ur = t、email_match = t。user_roles が複数ロールの staff は 0 件（全員 1 件）。
- firebase_uid が NULL でない行: 1 件（tenant_006 の staff id=1）。
- staff が存在しない users（users 13 件に対し staff 5 行）の user_roles は今回見ていない（要求外）。

## 7. DB のビュー・関数・トリガ（item 8）

BLOCKED（本番では未実施）。pg_views / pg_proc の定義文を列名で絞る SQL を、文字列リテラルを chr() の連結で組み立てて送ろうとしたところ、実行前に自動モード分類器に拒否された（指定形式の外側が単一引用符で、SQL 内に単一引用符・二重引用符を置けないための組み立てだった）。言い換えての再試行はしていない。

repo 側の事実（定義の出所）:
- ビュー: v_senders（tenant.py:709-719、migrations/020:70-77）が staff.primary_email を含む。staff.role_id / firebase_uid を含むビューは repo 内にない。
- トリガ: trg_staff_updated_at（tenant.py:694-697、migrations/019 の CREATE TRIGGER :118）は updated_at のみ。
- 関数: trg_set_updated_at 以外に staff 列を参照する関数は repo 内で未確認（migrations の SQL 関数の本文までは読んでいない）。
- 本番の実体（手で作られたビュー・関数・トリガ）は 未確認。

## 8. 未確認一覧
1. 本番 DB のビュー・関数・トリガに 3 列（role_id, primary_email, firebase_uid）が出てくるか（上の BLOCKED）。
2. 本番 public.users に firebase_uid 列があるか（information_schema の読み取りは指示範囲外と判断して実行していない。repo の models.py:22-38 には無い。試験用 rls_bootstrap.py:133 には有る）。
3. ログイン時に users.email で引く認証コードの file:line（今回は staff 周辺のみ確認）。firebase_uid が判定に使われないという結論は、backend/app の grep（staff.firebase_uid のヒットが staff.py/schemas/staff.py/tenant.py のみ）に基づく。
4. TokenData.role の生成・参照箇所、openapi.json の UserResponse.role の行番号、DbViewerPanel.tsx:129 の文脈。
5. StaffPage 作成フォームに firebase_uid の入力欄があるか（StaffPage.tsx:168 は送信のみ確認）。
6. tests-e2e の primary_email モック 15 ファイルのうち contacts 用が混ざるか（ui-company-detail-tabs.spec.ts:59 など）。
7. migration-test.yml:252 の `role VARCHAR(50) NOT NULL` がどの表か。
8. 作業ツリーは使っていない。基準は origin/main の fetch 時点（`git fetch origin main` 実行済み）。

## 9. 補足: 設計時に効く観察（事実のみ）
- PATCH /staff の role_id は priority 上限の検査がない（_ensure_assignable_role は存在と隠すロールの検査のみ :124-136）。PUT /users/{id}/roles は検査あり（roles.py:558-563）。
- PATCH /staff/{id}（:696-702）は staff 行を更新するが invalidate_user_permissions を呼ばない。作成時のみ呼ぶ（:641）。
- test_staff_me.py:16,61,87 は staff.primary_email が users.email と一致しない場合・同じメールの名簿行が複数ある場合の挙動を試験している（本番の現状は全行一致）。

DONE（item 8 のみ BLOCKED: 本番のビュー・関数・トリガ検査は分類器に拒否され未実施）
