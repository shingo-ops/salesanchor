---
mode: handoff
---
# recon — S1 段階③便C（public.users の書込全経路）

基準: origin/main 01f7d46386d2266fffd4f2abda004ef01925eac4（git fetch 後。作業ツリーは読んでいない）
前回版: ee12d863147cc988f4021cfaff08b2517311c32d（docs/handoff/s1-rls-stage3b/recon.md）
生出力: /tmp/CC報告ファイル/s1-stage3c/（g-sql.txt, g-multiline.txt, g-orm.txt, g-attr.txt, g-fk-users.txt, g-fk-tenants.txt, tests-users.txt, diff-key.txt, auth-excerpt.txt, ctx-excerpt.txt）

## 0. 前回(ee12d86)からの差分（結論）

【事実】`git diff ee12d86 origin/main` で backend/app・scripts・migrations に出た変更は12ファイル（diff-since-ee12d86.txt）。users に書く経路の追加・削除・行番号のずれは 0 件。
- 変わったのは tenants 側（便B）だけ: backend/app/routers/admin.py（set/reset_operator_context 追加）、super_admin_tenants.py（同）、scripts/setup_tenant.py・setup_review_tenant.py・setup_test_users.py（`SET app.is_operator='true'` を tenants INSERT 直前に追加）、scripts/qa/seed-tenant.sql（:68-69 に is_operator 追加）、migrations/20261016_170000_add_tenants_write_rls.sql（新規）、scripts/run_all_migrations.sh。
- 新規 backend/app/tools/reextract_v6_with_v102.py と scripts/ops/reextract-v6-loop.sh: users への書込 0 件（g-multiline.txt に出ない）。
- U1〜U7・S3〜S9 の行番号は前回版と同一（auth.py:96/266/275/285/293/456、staff.py:98/308/329、scripts 各行を origin/main で再確認）。

【事実】ログイン自社化(ADR-1013)で増えた users 書込: auth.py の 266/275/285/293/456 のみ（前回 U2〜U4 に既出）。パスキー: backend/app と routers に passkey/webauthn のコードは 0 件（言及は auth/self_tokens.py:63 の docstring のみ）。表 public.webauthn_credentials は migrations/20261013_160000_add_self_hosted_auth_tables.sql:16 に定義だけあり、users への書込を伴うコードは無い。メール認証(email_verified)は users に書く app コード 0 件（scripts の `email_verified=False` は Firebase 引数。setup_review_tenant.py:119、setup_single_test_user.py:125、setup_test_users.py:109）。
【事実】ORM: `User(` 生成は auth.py:89 の1か所のみ。User への属性代入・session.delete・merge・bulk 系・update(User)/delete(User) は backend/app と scripts で 0 件（g-attr.txt、g-orm.txt。`from app.models import User` は型注釈のみ）。
【事実】書込動詞を含む検索(複数行 SQL 含む、g-multiline.txt)で backend/app・scripts・.github・backend/tests 以外に users 書込はなし。Celery(backend/app/tasks) に users 書込 0 件。

## 1. 文脈関数（backend/app/auth/dependencies.py）

- set_tenant_context :337-359 — 中身: `SET search_path = tenant_NNN, public`(:357)／`SET app.tenant_id = '{safe_id}'`(:358)／`SET app.is_operator = ''`(:359)。SQLite では no-op(:353)。
- reset_tenant_context :399-418 — `await set_tenant_context(db, tenant_id)`(:418) を呼ぶだけ。
- clear_tenant_context :421-440 — `SET search_path = public`(:438)／`SET app.tenant_id = ''`(:439)／`SET app.is_operator = ''`(:440)。
- set_operator_context :489-503 — `SET app.is_operator = 'true'`(:503)。app.tenant_id は触らない。
- reset_operator_context :506-520 — `SET app.is_operator = ''`(:520)。
- get_current_tenant :270-321 — :309 search_path、:312 `SET app.tenant_id = '{safe_id}'`、:316 `SET app.is_operator = ''`。値は DB 上の user.tenant_id（:283）。
- いずれもセッション単位の SET（SET LOCAL ではない）。get_db の finally で clear_tenant_context(:61) が走り接続を返す（database.py:56-61）。

## 2. 接続（backend/app/database.py）

- get_db :46-61 — `AsyncSessionLocal`(:36) ＝ `engine`(:33) ＝ `create_async_engine(DATABASE_URL)`。DATABASE_URL は環境変数（:8、既定値は myapp_user のダミー）。application_name=salesanchor_backend(:15)。pool_size=20, max_overflow=10(:26-27)。
- get_admin_db :88-95 — `AdminSessionLocal`(:85) ＝ `admin_engine`(:84) ＝ `create_async_engine(ADMIN_DATABASE_URL)`。`ADMIN_DATABASE_URL = os.getenv("ADMIN_DATABASE_URL", DATABASE_URL)`(:66)＝未設定なら DATABASE_URL にフォールバック。application_name=salesanchor_admin_ops(:70)。pool_size=5(:78)。get_admin_db は clear_tenant_context を呼ばない（:88-95 に finally なし）。
- docker-compose.yml:66-67 / :216-217 / :298-299 は両変数を環境変数から渡す（`ADMIN_DATABASE_URL=${ADMIN_DATABASE_URL:-}`）。.env.example:12 DATABASE_URL は myapp_user、:15 ADMIN_DATABASE_URL は jarvis（例）。
- 【事実】本番のロール（前回 recon §1 の引用・今回は未再測定）: アプリ・Celery は salesanchor_app（rolbypassrls=f）、migration 実行は jarvis（rolbypassrls=t）。【未確認】本番で ADMIN_DATABASE_URL が設定されているか（前回 recon も「未設定なら DATABASE_URL」としか確認していない。admin.py/super_admin_tenants.py が admin_db で何の接続を使うかは本番の環境変数次第）。
- 【事実】users への書込経路(U1〜U7)はすべて get_db（DATABASE_URL 側）。get_admin_db 経由の users 書込は 0 件（admin_db は会社スキーマの DDL 用。admin.py・super_admin_tenants.py）。

## 3. users 書込経路 — アプリ（8 経路 / SQL・ORM 9 文）

凡例: 「文脈」＝書込の瞬間に app.tenant_id が張られているか。依存は FastAPI の Depends。

| # | 書込行 / commit行 | 呼び出し口 | 書込時の会社文脈 | 対象行 | 依存 |
|---|---|---|---|---|---|
| U1 | backend/app/routers/auth.py:89-97（ORM `User(...)` → `db.add` :96 → flush :97）／commit :144 | POST /api/v1/auth/register（:38） | **文脈なし**。set_tenant_context は :116 ＝書込(:97)の後。get_current_tenant を使わない | **他社**（data.tenant_code で引いた会社 :65-76 の tenant.id を tenant_id に入れる :90） | get_db、require_super_admin |
| U2a | auth.py:266（failed_login_count+1 RETURNING）／commit :279 | POST /api/v1/auth/login（:231） | **文脈なし**（ログイン前。依存は get_db のみ :236） | メールで引いた1行（会社不定。自社/他社の区別なし）:247-255 | get_db のみ |
| U2b | auth.py:275（locked_until 設定・失敗回数0）／commit :279（同一パス） | 同上 | 文脈なし | 同上 | 同上 |
| U3a | auth.py:285（失敗回数0・locked_until NULL・last_login）／commit :299 | 同 POST /auth/login 成功側 | 文脈なし | 同上 | 同上 |
| U3b | auth.py:293（ハッシュ再計算 needs_rehash 時のみ :290）／commit :299 | 同上 | 文脈なし | 同上 | 同上 |
| U4 | auth.py:456（password_argon2_hash・password_changed_at・failed_login_count・locked_until）／commit :477 | POST /api/v1/auth/password-reset/confirm（:412） | 文脈なし。メールのトークン(:432-436 password_reset_tokens.used_at UPDATE)で本人特定、id は token_row.user_id(:446) | トークン保持者の1行（会社不定） | get_db のみ |
| U5 | backend/app/routers/staff.py:98（INSERT。_resolve_user_for_new_staff :65-104。呼出 :592）／commit :632（reset_tenant_context :633） | POST /api/v1/staff（:579） | **あり**。get_current_tenant 依存(:582)＝auth/dependencies.py:312 で app.tenant_id 設定済。tenant_id 値は :99 `:tid`＝自社。同メールが他社に在れば :79-83 で 409 | **自社** | get_db、get_current_tenant、get_current_user、require_permission("staff.create") |
| U6 | staff.py:308（locale）／commit :311 | PATCH /api/v1/staff/me/locale（:294） | **文脈なし**（get_current_tenant 無し :297-298） | **自分の行**（id=current_user.id）＝自社 | get_db、get_current_user |
| U7 | staff.py:329（theme）／commit :332 | PATCH /api/v1/staff/me/theme（:315） | 文脈なし | 自分の行 | get_db、get_current_user |
| U8 | （書込なし・連鎖）super_admin_tenants.py:178 の `DELETE FROM public.tenants WHERE id = :id`（:173 の `db.begin()` 内。便B で set_operator_context 追加） → users が連鎖削除 | DELETE /api/v1/super-admin/tenants/{tenant_id}/physical（:104） | app.tenant_id なし。app.is_operator='true'（便B）。users 側 RLS が連鎖削除を止めるか **未確認** | 他社の全 users 行 | get_db、get_admin_db、require_super_admin |

補足（再確認した事実）:
- 【事実】get_current_user(dependencies.py:131-267)は users を読むだけ。last_login 等の書込なし（auth.py:285 のログイン経路のみ）。refresh(auth.py)・logout・password-reset 要求(:380-409)は users に書かない（password_reset_tokens／auth_refresh_tokens 側。g-multiline.txt に出ない）。
- 【事実】U1 の読みは SELECT Tenant(:65)・SELECT User(:79)を get_db で実行。書込後 :116 に set_tenant_context、:131 invalidate_user_permissions。Firebase 失敗時は :138 rollback。
- 【事実】U5 は書込(:98)→ staff INSERT(:595) → assign_single_role(:624) → commit(:632) → reset_tenant_context(:633)。書込の時点で文脈は有効。
- 【事実】U6/U7 は `SET search_path`/app.tenant_id を張らない。get_current_tenant を通る他ルートと異なり、接続は文脈が空（clear 済み）の状態で UPDATE する。users RLS を tenant_id 一致にすると、UPDATE は無言で 0 行（エラーにならない）。
- 【事実】U2〜U4 はログイン前(トークンなし)で会社が不定。RLS の条件に使える app.tenant_id が無い。
- 【推測】便C の方針は「文脈なし経路(U1,U2,U3,U4,U6,U7)に対し、①対象行の tenant_id を先に SELECT してから set_tenant_context、または ②運営文脈相当の別式を許す」のどちらか。選択はこの調査の範囲外。

## 4. users 書込経路 — scripts（5 スクリプト・11 文）

接続はすべて DATABASE_URL（setup_review_tenant.py:438-445、setup_test_users.py:44/296、setup_single_test_user.py:407-414）。本番コンテナで走らせると salesanchor_app（前回 recon §1）。【未確認】これらの script を本番で今後走らせる予定の有無。

| # | 書込行 | 呼び出し口 | 書込時の会社文脈 | 対象行 |
|---|---|---|---|---|
| S3a | scripts/setup_review_tenant.py:312（tenant_id 付け替え＋is_active UPDATE） | python scripts/setup_review_tenant.py（_setup_user :289。`engine.begin()` :300） | **文脈なし**。SET app.tenant_id は :210（_resolve_role_id）で、別の `engine.begin()`／書込より後 | **他社の行を新会社へ移す**（:308-318） |
| S3b | setup_review_tenant.py:325（is_active） | 同上 | 文脈なし | 自社（:306-308 で同一 tenant 確認済み） |
| S3c | setup_review_tenant.py:332（INSERT） | 同上 | 文脈なし | 自社 |
| S5a | scripts/setup_test_users.py:211（is_active UPDATE） | python scripts/setup_test_users.py（register_user :188。`engine.begin()` :197） | 文脈なし（SET app.tenant_id は :237＝書込の後） | 既存行。**他社の行も UPDATE しうる**（:205-212。他社なら tenant_id は変えないが is_active=TRUE は書く。:203-207 の warning） |
| S5b | setup_test_users.py:218（INSERT） | 同上 | 文脈なし | 自社 |
| S6a | scripts/setup_single_test_user.py:201（INSERT。_create_user_record :192。呼出 :489 は `engine.begin()` :474 内） | python scripts/setup_single_test_user.py（作成モード _run_create :379） | **不確実**。:423-425 の `engine.connect()` ブロックで `_resolve_role_id`(:170-174) が `SET app.tenant_id`（セッション単位）を張るが、書込は別の `engine.begin()`(:474)。同じプール接続が再利用されたときだけ効く。:497 の再 SET は INSERT(:489)の後 | 自社 |
| S6b | setup_single_test_user.py:483（is_active UPDATE、ALLOW_OVERWRITE_PASSWORD=1 のとき） | 同上 | 不確実（同上） | 既存行。他社なら :456-462 で中断するので自社 |
| S7 | setup_single_test_user.py:368（DELETE。_delete_user_record :352。:361 に `SET app.tenant_id` が :368 より前） | 同スクリプト削除モード（_run_delete :539、`engine.begin()` :571） | **あり**（:361） | 自社（引数の会社の user） |
| S8a | scripts/qa/seed-tenant.sql:94（DELETE qa-%）／S8b :101（INSERT。tenant_id=6 固定） | scripts/qa/reset-tenant.sh が psql で投入（BEGIN :43） | **あり**: :67 `set_config('app.tenant_id','6',false)`、:69 `set_config('app.is_operator','true',false)`（便Bで追加） | 自社（tenant 6） |
| S9 | scripts/qa/cleanup-smoke-data.sh:107（DELETE qa-%）。BEGIN :79、COMMIT :111 | scripts/qa/cleanup-smoke-data.sh（psql heredoc :78） | **あり**: :81 `set_config('app.tenant_id','6',false)` | 自社（tenant 6） |

- 【事実】seed-tenant.sql:101 の INSERT は列 `password_hash` を指定。この列は migrations/20260612_150000_drop_password_hash.sql:9 で削除済み（前回 recon 既出）＝このスクリプトは現状 INSERT で失敗しうる。RLS とは別件。【未確認】実行の有無。
- 【事実】docs/（B-04, B-12, handoff 各種）の手書き SQL 例はコードではないので表に含めない（g-sql.txt に出るが docs/）。

## 5. 集計

- アプリ（HTTP）: 8 経路 = U1,U2,U3,U4,U5,U6,U7 + U8(連鎖削除)。書込 SQL/ORM 文は 9 文（U1 1、U2 2、U3 2、U4 1、U5 1、U6 1、U7 1）。
  - 会社文脈なし: U1,U2,U3,U4,U6,U7 = 6 経路（8 文）。ありは U5 の 1 経路(1 文)のみ。U8 は app.tenant_id なし(is_operator のみ)。
  - 他社の行を書く: U1（他社に作成）、U8（連鎖削除）。U2,U3,U4 は会社不定（メール/トークンで引く）。
- scripts: 5 スクリプト（setup_review_tenant.py, setup_test_users.py, setup_single_test_user.py[作成/削除の2モード], scripts/qa/seed-tenant.sql, scripts/qa/cleanup-smoke-data.sh）で書込 11 文（S3 3、S5 2、S6 2、S7 1、S8 2、S9 1）。
  - 文脈なし: S3(3文)、S5(2文)＝5 文。不確実: S6(2文)。あり: S7、S8(2文)、S9＝4 文。
- Celery・tasks: 0 件。migrations 内の users 値書込: migrations/054_add_users_theme.sql:10 の 1 件（migration は jarvis＝rolbypassrls=t）。

## 6. 外部キー

users が親（users を参照する側）— 先頭は migrations/ と backend/app/services/tenant.py（生一覧 g-fk-users.txt、他に `.github/workflows/migration-test.yml` の CI 用最小定義 7 行）:

| 参照元 | file:line | ON DELETE |
|---|---|---|
| public.staff.user_id（UNIQUE） | migrations/019_create_staff_tables.sql:38 / backend/app/services/tenant.py:600（NOT NULL UNIQUE） | 指定なし＝NO ACTION |
| goals.user_id | migrations/075_create_goals.sql:55 | CASCADE |
| goals.created_by | 075:67 | SET NULL |
| google_calendar_config.connected_by_user_id | migrations/076_add_google_calendar_config.sql:21 | SET NULL |
| calendar_events.user_id／created_by_user_id | migrations/078_create_calendar_events_tenant.sql:46 / :63 | SET NULL |
| user_inventory_filters.user_id（PK） | migrations/20260602_190000_create_user_inventory_filters.sql:15 | CASCADE |
| google_drive_config.connected_by_user_id | migrations/20260606_010000_add_google_drive_config.sql:24 | SET NULL |
| carrier_credentials.updated_by_user_id | migrations/20260608_080000_add_carrier_credentials.sql:21 | SET NULL |
| tenant_paypal_config.updated_by_user_id | migrations/20260610_071110_add_paypal_config.sql:21 | SET NULL |
| tenant_deletion_audit.actor_id | migrations/20260614_040137_add_tenant_deletion_audit.sql:10 | SET NULL |
| line_import_devices.owner_user_id | migrations/20260912_160000_line_import_devices.sql:11 | CASCADE |
| companies.sales_rep_id（各会社スキーマ） | migrations/20261013_100000_repoint_companies_sales_rep_to_users.sql:42 / services/tenant.py:661 | SET NULL |
| 各会社スキーマ6列: bots.owner_staff_id=NO ACTION, order_commissions.staff_id=SET NULL, calendar_owner_settings.staff_id=CASCADE, tenant_meta_config.connected_by_staff_id=SET NULL, meta_messages.sent_by_staff_id/seen_by_staff_id=SET NULL | migrations/20261013_110000_repoint_person_columns_to_users.sql:19-24（FK作成 :58） | 列ごと（左記） |
| 新規会社スキーマ側の同等定義 | backend/app/services/tenant.py:678 owner_staff_id NO ACTION、:1087 connected_by_staff_id SET NULL、:1128 user_id CASCADE、:1140 created_by SET NULL | 左記 |
| public.webauthn_credentials.user_id／password_reset_tokens.user_id／auth_refresh_tokens.user_id | migrations/20261013_160000_add_self_hosted_auth_tables.sql:18 / :49 / :70 | CASCADE（3表。:16 webauthn_credentials 他の表名は同ファイル CREATE 行） |
| viewer 系 actor_user_id | migrations/20261016_150000_add_viewer_accounts.sql:89 | SET NULL |

- 【事実】前回 recon §1 の本番実測では users を参照する FK は各会社スキーマ込みで 71 行（prod-now.txt:9-93）。今回の列挙は migrations/ とコードの定義からの再構成で、本番の件数とは一致を確認していない（【未確認】）。

users が子（users → tenants）:
- 【事実】migrations に public.users の CREATE TABLE は無い。ORM は `ForeignKey("tenants.id", ondelete="CASCADE")`（backend/app/models.py:26、NOT NULL）。CI の最小定義も `tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE`（.github/workflows/migration-test.yml:198, :1167、schema-check.yml:126）。本番も tenant_id NOT NULL（前回 recon §1）。
- 【未確認】本番の users→tenants FK が ON DELETE CASCADE か（migration に無く CI 定義と ORM の記述のみ。super_admin_tenants.py のコメント「CASCADE → public.users 連鎖削除」が根拠）。
- tenants を参照する他の FK 12 行（g-fk-tenants.txt）: 070:48, 076:16, 077:27, 099:7, 20260602_120000:6, 20260604_080000:8, 20260606_010000:18, 20260608_080000:16, 20260610_071110:17 = CASCADE。20260920_030000:11 units、20260920_050000:2 tcg_status_master、20261002_160000:9 payment_fee_settings = 指定なし(NO ACTION)。

## 7. テスト（backend/tests）

users へ書込を含む（SQL 直書き、g-sql.txt の行）:
- backend/tests/rls_bootstrap.py:148（`_ensure_public_users`。実PG試験の土台）
- backend/tests/test_export_inventory_for_sheet.py:75
- backend/tests/test_line_import_devices_pg.py:39, :74, :76
- backend/tests/test_meta_channels.py:362, :383, :416
- backend/tests/test_order_commissions.py:423, :538
- backend/tests/test_password_reset.py:116
- backend/tests/test_role_assignment.py:75
- backend/tests/test_self_auth.py:66, :177, :288
- backend/tests/test_staff_create_users.py:67, :104
- backend/tests/test_tenants_rls.py:94（便B。users を INSERT）

users を参照するが書込の確認を取っていないもの（tests-users.txt に出た語一致。【未確認】書込の有無）:
- backend/tests/conftest.py（SQLite 用 users 定義 :1176 付近）、test_adr072_phase_2_reset_rollout.py、test_bots_owner_users.py、test_companies_sales_rep_users.py、test_paypal_regtoken_rls.py、test_rls_tenant_meta_config.py、test_roles_hidden_system_admin.py、test_tenant_admin_ssot.py、test_viewer_tokens.py

- 【事実】実PG(RLS)試験の型は test_paypal_regtoken_rls.py と test_tenants_rls.py（RLS_ADMIN_DATABASE_URL 未設定なら skip）。SQLite 試験では SET が no-op（dependencies.py:353）なので users RLS の効果は SQLite では検証できない。
- 【事実】CI 定義(.github/workflows/migration-test.yml:241, :1209)も `INSERT INTO public.users` を持つ（jarvis で実行）。

## 8. 見落としやすい点（便C 設計で効くもの）

1. ログイン前の経路(U2,U3,U4)は会社文脈の元になる値が無い。さらに get_current_user(:131-267) 側の users 読取が文脈なしでも通る前提（読取は全行可の想定）。
2. U6/U7 は get_current_tenant を経由しないため、PATCH /staff/me/locale|theme は文脈なし書込。RLS 追加で無言 0 行になる。
3. U1 は書込(:97)が set_tenant_context(:116)より前。順序の入れ替えまたは運営文脈の扱いが要る。
4. U8（会社の物理削除）の users 連鎖削除が users 側 RLS を通るかは未実測（便A の test_paypal_regtoken_rls.py:342-358 は子表の連鎖を実測済み。users そのものへ FORCE RLS を付けた場合の連鎖は users 表では未確認）。
5. get_admin_db は文脈クリアなし(database.py:88-95)。

## 9. 設計前の追加確認（Q1〜Q9、2026-10-16）


基準: origin/main（git fetch 後）。作業ツリーは読んでいない。生出力: /tmp/CC報告ファイル/s1-stage3c/q5-p*.txt, q5b-p*.txt

### Q1 record_audit_log の表
【事実】書込先は `{schema_name}.audit_logs`、schema_name=`tenant_{tenant_id:03d}`（backend/app/services/audit.py:303, :313）。スキーマ修飾つきなので search_path に依存しない。
【事実】会社スキーマに同名表がある: backend/app/services/tenant.py:481 `CREATE TABLE IF NOT EXISTS {schema}.audit_logs`。public.audit_logs を指す記述は audit.py に無い。
【事実】会社スキーマ audit_logs は RLS 有効（tenant.py:1185）、ポリシー tenant_isolation_audit_logs は `USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)`（tenant.py:1246-1248）。FORCE ROW LEVEL SECURITY の記述は tenant.py に 0 件（grep 結果）。
【未確認】本番で salesanchor_app が audit_logs の所有者か（所有者なら FORCE なしで RLS を素通りする）。

### Q2 self_tokens.py の SQL
【事実】全て `public.` 修飾: INSERT :171、UPDATE :197 / :214 / :243、SELECT :207（auth_refresh_tokens）、SELECT :224（public.users）。修飾なしの SQL は 0 件（grep 結果）。search_path 変更の影響を受けない。

### Q3 register の audit(:100) の実行時状態
【事実】register の依存は get_db と require_super_admin のみ（auth.py:41-42）。require_super_admin は is_super_admin を見るだけ（dependencies.py:523-551）。get_current_user（:131-267）は search_path も app.tenant_id も張らない（SET は :309-316 の get_current_tenant と :357-359 等の set_*_context のみ。register は get_current_tenant を使わない）。よって :100 の時点は search_path=public、app.tenant_id は空文字（get_db が返却時に clear: database.py:61。初期は下記 Q4）。
【事実】audit の INSERT は `tenant_NNN.audit_logs` と修飾済み（Q1）なので search_path が public でも tenant_NNN でも宛先は同じ。
【推測】audit_logs のポリシーが app.tenant_id を見るため、今の :100 は app.tenant_id 空のまま走る。空文字を ::INTEGER にすると型エラーになりうる／所有者なら素通り。今動いているなら素通りのはず。【未確認】本番実測なし。設計の「users 書込前に set_tenant_context」を入れると :100 は tenant 文脈下で走り、ポリシー上はむしろ通りやすくなる。
【事実】set_tenant_context の後（:116-130）の SQL は `roles`・`user_roles` の非修飾（search_path 依存）で、今も :116 の後に走っている。:97 の users 書込と :116 の間にあるのは audit(:100) のみ。

### Q4 ログイン前の get_db の接続状態
【事実】get_db（database.py:46-61）は開始時に何も SET しない。終了時に clear_tenant_context（:61 → dependencies.py:438-440: search_path=public / app.tenant_id='' / app.is_operator=''）。初期値は「前のリクエストの clear 済み」か新規接続（サーバ既定）。【未確認】新規接続の既定 search_path（ロール設定 ALTER ROLE の有無）。
【事実】middleware 4 つ（main.py:223-229: Audit, RateLimit, SessionGuard, Realtime）。rate_limit・realtime・session_guard に SET/get_db/AsyncSessionLocal の記述 0 件。audit.py だけ自前の `AsyncSessionLocal()` を開く（middleware/audit.py:160, :209）が、別セッションで SET は無い。リクエスト開始時に app.tenant_id を張る箇所は main.py に無い（search_path/app.tenant_id は main.py では :257, :521, :523, :613 のコメントのみ）。
【事実】get_current_tenant（dependencies.py:270-321）を Depends に持つルートだけが文脈を張る。login・password-reset は get_db のみ（auth.py:236 ほか）。
【事実・注意】login の SELECT（auth.py:249-251）は列に tenant_id を含まない。設計で「その利用者の tenant_id」を使うなら SELECT 列の追加が要る。password-reset/confirm は tenant_id を既に SELECT（auth.py:445）。

### Q5 users 書込の二重確認（別方式）
【事実】使ったパターンと件数（backend/app と scripts、origin/main）:
- P1 書込動詞（文字クラス）＋ users（public. 任意、複数単語対応）: 19 件 → q5b-p1.txt。内訳は全て既知: auth.py:266/275/285/293/456、staff.py:98/308/329、scripts は setup_review_tenant.py:312/325/332、setup_single_test_user.py:201/368/483、setup_test_users.py:211/218、qa/seed-tenant.sql:94/101、qa/cleanup-smoke-data.sh:107。= U2a/U2b/U3a/U3b/U4/U5/U6/U7 ＋ S3〜S9。新規 0 件。
- P2 sqlalchemy の update/insert/delete に User/users を渡す: 0 件。
- P3 User 属性への代入（user./current_user./db_user./target_user./.user. の既知列）: 3 件 → q5b-p3.txt。中身は git の `-c user.name=` を含むシェル（scripts/dev/test-agent-hooks.sh:43、scripts/tests/test-disk-janitor.sh:72, :101）で users 表と無関係。
- P5 `User(`・session.delete・db.delete・merge・bulk_*: 2 件 → models.py:22（クラス定義）と auth.py:89（U1）。既知。
- P4/P6（f-string・連結・`{x}.users`）: public.users を含む 94 行を目視。書込は P1 と同じ行のみ。`{schema}.users` 形式は 0 件。
- 複数行 SQL（書込動詞が行末にある形）: 0 件（common-passwords.txt の単語のみ）。backend/app/tasks と tools の users 書込: 0 件。
- relationship 経由（staff.user.xxx = ）: P3 の `.user.` パターンで 0 件。
結論【事実】前回 U1〜U8・S3〜S9 以外の users 書込は見つからず。

### Q6 Firebase 認証経路
【事実】backend/app/auth/ 配下の users 書込は 0 件。dependencies.py の users 参照は SELECT のみ（:101-112 select、:159, :200, :245, :295 select）。firebase_uid・last_login・UPDATE の grep はこの配下で self_tokens.py の auth_refresh_tokens UPDATE（:197, :214, :243）と utils.py:13-15 の set_tenant_claim（Firebase 側のクレーム設定。DB 書込でない）のみ。
【事実】last_login の更新は auth.py:285（自社ログイン成功）だけ。firebase_uid の DB 紐付け処理は backend/app/auth 内に無い。register は firebase_uid を DB に入れない（auth.py:89-95。set_tenant_claim に渡すのみ :136）。

### Q7 FK の ON DELETE CASCADE と子表 FORCE RLS
Context7: 月間上限超過で使えなかった（"Monthly quota exceeded"）。WebFetch で https://www.postgresql.org/docs/16/ddl-rowsecurity.html を確認。
【事実・原文】"Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security to ensure that data integrity is maintained. Care must be taken when developing schemas and row level policies to avoid “covert channel” leaks of information through such referential integrity checks."
【事実】同ページに "cascade" の語は無い（WebFetch の回答）。CASCADE の子表削除が RLS を受けるかを明記した文は同ページに無い。近接文: "Operations that apply to the whole table, such as TRUNCATE and REFERENCES, are not subject to row security."
【事実（repo 内実測）】backend/tests/test_tenants_rls.py:325-345 は、tenants の物理削除で users（FORCE RLS なしの現状）が連鎖削除されることを確認。FORCE RLS を users に付けた場合の連鎖は未実測。
【未確認】上の原文は「整合性チェック」の記述で、CASCADE の削除アクション自体が子表のポリシーを素通りするとは書かれていない。試験で確かめるのが確実（users に FORCE RLS＋書込ポリシーを付けた状態で test_tenants_rls.py:325 相当を app 接続で回す）。

### Q8 実 PG 試験
【事実】rls_bootstrap.py:131-156 `_ensure_public_users` は admin 接続（conn は admin_engine.begin()、test_tenants_rls.py:80-81）で CREATE TABLE と INSERT（ON CONFLICT DO NOTHING）。app 役ではない。users に RLS を付ける migration は _PG_BOOTSTRAP_MIGRATIONS（rls_bootstrap.py:14-34）に載っていないので、載せない限りこの INSERT は影響なし。
【事実】test_tenants_rls.py: users への INSERT は admin 接続（:92-98）。app 役で users に書く箇所は 0 件。app 役は DELETE FROM public.tenants（:275-279）で users が連鎖削除される（:283, :345）。→ users に FORCE RLS を付けると :283/:345 が影響を受けうる（Q7 未確認と同じ）。:122-132 `_ctx_conn` は set_config(…, true)（トランザクション内のみ）で文脈を張る。
【事実】test_paypal_regtoken_rls.py: users は _ensure_public_users 経由（admin）のみ（:17, :70）。app 役で users に書く箇所は 0 件。:301-371 は set_tenant_context を実関数で使用。
【事実】test_line_import_devices_pg.py:39, :74, :76 は owner（admin）接続で users に書く。app 役には SELECT のみ付与（:40）。
【事実】test_self_auth.py / test_password_reset.py / test_staff_create_users.py / test_role_assignment.py / test_order_commissions.py の `INSERT INTO users`（public. なし）は SQLite 土台（conftest.py:160-161 で public.users→users に置換、:1173）。SQLite では SET が no-op（dependencies.py:353）なので RLS の影響なし。test_meta_channels.py:362/383/416 は `public.users` 付きだが db_session（conftest の SQLite 土台）。【未確認】db_session が実 PG になる設定の有無。
【結論】users に RLS を付けて落ちる候補: test_tenants_rls.py の物理削除系（:275-283, :325-345。連鎖削除の挙動次第）。app 役で users に直接書く試験は無く、便C 用の新試験が要る。落ちる可能性が高い既存試験は他に確認できず。

### Q9 CI の grep 規則
【事実】.github/workflows/test.yml:92-107。パターンは `grep -rn "execute.*SET search_path" app/ --include="*.py" | grep -v "^app/auth/dependencies.py:"`、working-directory: backend。対象は backend/app/ 配下の .py のみ、dependencies.py だけ除外。scripts/ は対象外。
【事実】`SET app.tenant_id` を禁じる規則は test.yml の grep では 0 件（"search_path|app\.tenant_id" で :92-107 の search_path のみヒット）。
【未確認】他の workflow（test.yml 以外）に app.tenant_id の直書き禁止があるか（今回は test.yml のみ確認）。

## 10. 本番の前提と既存 ADR

- 【事実】本番 2026-10-16 14:24 JST（PO の `!` 実行、/tmp/CC報告ファイル/s1-stage3b/prod-now.txt）: public.users は RLS f/f・ポリシー 0、15 行、tenant_id は NULL 0 件で NOT NULL。所有者 jarvis（rolsuper=t・rolbypassrls=t）。アプリと Celery は salesanchor_app（rolsuper=f・rolbypassrls=f）で接続。
- 【事実】既存 ADR: ADR-1018（本テーマ・段階③は案 C＝書込だけ RLS、PO 2026-10-16「y」）、ADR-072（commit 直後の reset_tenant_context）、ADR-131（get_db の finally で文脈を空に戻す）、ADR-1013（自社ログイン。users の password_argon2_hash・failed_login_count・locked_until・last_login を書く）、ADR-135/136（危険パスの GO）。検索は docs/adr/FEATURE-INDEX.md と `git grep -il "users" docs/adr/` の該当から選定。
- 【事実】便B（PR #4379）で public.tenants に同型の書込だけ RLS を入れ、本番反映後 42501・5xx 0 件（docs/specs/tenant-rls/README.md 段階③欄）。
