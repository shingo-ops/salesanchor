---
mode: handoff
---
# recon — S1 段階③便B（public.tenants と public.users の書込経路）

> この文書は何か：会社表（public.tenants）と利用者表（public.users）に「書込・削除だけ RLS」を付ける前に、書込の全経路を行番号まで調べた記録です（読取専用調査。DB には接続していません）。

**日付**: 2026-10-16　**基準**: origin/main ee12d863147cc988f4021cfaff08b2517311c32d（fetch 後。調査の途中で e882207ca から進んだため、結論は ee12d86 の内容で取り直したもの）
**調査**: Sonnet（読取のみ）。Opus が要所（auth.py:255-300・:85-120・:440-460、staff.py:300-335、super_admin_tenants.py:50-70・:150-170、admin.py:40-70）を原文で再確認済み（/tmp/CC報告ファイル/s1-stage3b/opus-verify.txt）
**見た場所**: `git archive origin/main` で取り出した backend/app・scripts・migrations・backend/tests 等（作業ツリーは origin/main と大きく違うため見ていない）。取出し先 `/private/tmp/claude-501/-Users-tanizawashingo-salesanchor/3b391005-0a9a-425b-b1da-8f3ba95cd1bf/scratchpad/om`、`.../om2`
**生出力**: `/tmp/CC報告ファイル/s1-stage3b/`（w_sql.txt＝SQL 直書きの書込一覧、w_sql_other.txt＝backend 配下の補助スクリプト等・0 件、w_tests.txt＝試験、m_ddl.txt・m_fk.txt＝表定義と外部キー、orm_ctor.txt＝ORM 生成、app_words.txt＝語の全出現）。g_*.txt は途中の旧基準（e882207ca）の粗い grep で、結論には使っていない
**手法メモ**: 書込は 作業用の検索スクリプト find_writes.py（scratchpad。リポジトリ外）で複数行にまたがる SQL も拾った。動的な表名（`{table}` 展開）は §3-N に別掲

## 0. 既存 ADR・仕様

- ADR-1018（public 機微表の RLS 段階導入）段階③。手本: docs/handoff/s1-rls-stage3a/recon.md。
- ADR-072（commit 直後に reset_tenant_context）。ADR-131（プール返却前の文脈クリア。backend/app/database.py:46-62）。
- 【事実】段階③は案 C（書込だけ RLS）— 2026-10-16 PO「y」（docs/specs/tenant-rls/README.md 段階③欄）。トークン 3 表は RLS なし — 同日 PO「y」（質問2）。

## 1. 本番の現在地（2026-10-16 14:24 JST、PO の `!` 実行・読取のみ。生出力 /tmp/CC報告ファイル/s1-stage3b/prod-now.txt）

- 【事実】tenants・users とも RLS 無し（relrowsecurity=f・relforcerowsecurity=f）、所有者 jarvis（prod-now.txt:2-3）。ポリシー 0 本（:4 以降に pg_policies の行なし）。
- 【事実】tenants 5 行（有効 5）、users 15 行（tenant_id 空 0）（:4-5）。users.tenant_id は is_nullable=NO（:6）。
- 【事実】jarvis は rolsuper=t・rolbypassrls=t、salesanchor_app は f/f（:7-8）＝ migration（jarvis）は RLS を素通り、アプリは RLS を受ける。
- 【事実】本番のアプリ・Celery の接続名義は salesanchor_app（2026-10-15 段階①の pg_stat_activity 読取。scratchpad/s1-prod-conn-read.txt: salesanchor_backend 6 本・salesanchor_celery_distribute 1 本がすべて salesanchor_app）。scripts は同じ DATABASE_URL を使う（backend/app/database.py:8、ADMIN_DATABASE_URL は未設定なら DATABASE_URL へフォールバック :66）＝ backend コンテナで走らせると salesanchor_app。
- 【事実】tenants を参照する外部キーは 14 本（ON DELETE CASCADE 11・NO ACTION 3: line_units・tcg_status_master・payment_fee_settings）、users を参照する外部キーは各会社スキーマ含め 71 行（prod-now.txt:9-93）。
- 【事実】migrations/・backend/app に tenants/users 向けの CREATE POLICY / ENABLE ROW LEVEL SECURITY / トリガーは 0 件（m_ddl.txt）。

## 2. 表の定義

- 【事実】tenants・users の CREATE TABLE は migrations/ に存在しない（基本表は migrations より前に作られていた。m_ddl.txt に CREATE は 0 件、ALTER のみ）。
- 後続 ALTER（users のみ。tenants への ALTER は 0 件）:
  - migrations/053_add_users_locale.sql:4、054_add_users_theme.sql:4（054:10 は値の UPDATE を含む＝migration 実行時に users へ書く）
  - migrations/064_add_users_is_super_admin.sql:32（`is_super_admin BOOLEAN NOT NULL DEFAULT FALSE`）
  - migrations/20260612_150000_drop_password_hash.sql:9（password_hash 列を削除）
  - migrations/20261013_160000_add_self_hosted_auth_tables.sql:6-9（password_argon2_hash・password_changed_at・failed_login_count・locked_until）
- users.tenant_id が NULL を許すか:
  - 【事実】ORM は `nullable=False`（backend/app/models.py:26）。CI の最小定義も `NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE`（.github/workflows/migration-test.yml:198、同:1167、schema-check.yml:126）。試験用の定義も NOT NULL（backend/tests/rls_bootstrap.py:133）。
  - 【事実】アプリは `int(user.tenant_id)` を前提にする（backend/app/auth/dependencies.py:283）。運営（is_super_admin）も実在の会社に属する利用者（admin.py の経路も get_current_tenant を要求。main.py:259-263）。
  - 【事実】本番も NOT NULL（§1、prod-now.txt:6）。
  - 【事実】tenant_id が空の users 行を作る経路は、書込の全経路（§3）に 0 件。
- tenants に tenant_id 列は無い（主キーは id）。RLS の条件は users が `tenant_id = 接続の会社`、tenants が `id = 接続の会社` になる。【推測】
- 外部キー（REFERENCES tenants / users）: 生一覧は m_fk.txt。要点:

| 参照先 | 参照元 | ON DELETE |
|---|---|---|
| tenants(id) | users.tenant_id（CI 定義 migration-test.yml:198） | CASCADE |
| tenants(id) | tenant_paypal_config（20260610_071110_add_paypal_config.sql:17）、carrier_credentials（20260608_080000:16）、google_calendar_config（076:16）、calendar_sync（077:27）、google_drive_config（20260606_010000:18）、registration_tokens（20260604_080000:8）、discord_guild_config（099:7）、discord_ticket_config（20260602_120000:6）、spreadsheet（070:48） | CASCADE |
| tenants(id) | units.tenant_id（20260920_030000:11）、tcg_status_master（20260920_050000:2）、payment_fee_settings（20261002_160000:9） | 指定なし＝NO ACTION |
| users(id) | self_hosted_auth の 3 表（20261013_160000:18,49,70） | CASCADE |
| users(id) | user_inventory_filters（20260602_190000:15）、line_import_devices.owner_user_id（20260912_160000:11）、goals.user_id（075:55）、calendar_events.user_id（078:46） | CASCADE / SET NULL（078:46 は SET NULL） |
| users(id) | updated_by_user_id 系（paypal :21、carrier :21、calendar :21、drive :24）、goals.created_by（075:67）、tenant_deletion_audit.actor_id（20260614_040137:10）、viewer 系 actor_user_id（20261016_150000:89）、companies.sales_rep_id（20261013_100000:42） | SET NULL |
| users(id) | staff.user_id（019:38、services/tenant.py:600） | 指定なし＝NO ACTION |
| users(id) | 各会社スキーマの 6 列付け替え（20261013_110000:58。bots.owner_staff_id=NO ACTION、calendar_owner_settings=CASCADE、他=SET NULL） | 列ごと |
| users(id) | services/tenant.py:661（sales_rep_id SET NULL）、:678（owner_staff_id NO ACTION）、:1087・:1140（SET NULL）、:1128（CASCADE） | 列ごと |

- 【事実】tenants の物理削除は users と上表 CASCADE の表を連鎖削除する（backend/app/routers/super_admin_tenants.py:164 のコメント「CASCADE → public.users 連鎖削除」）。

## 3. 書込の全経路（origin/main ee12d86）

文脈の凡例: 会社文脈＝`SET app.tenant_id`（get_current_tenant＝backend/app/auth/dependencies.py:270-322、うち :312 が app.tenant_id、:316 が app.is_operator 空）。set_tenant_context＝:337-359。接続を返す前に get_db の finally が全部空に戻す（backend/app/database.py:56-62、clear_tenant_context＝dependencies.py:421-440）。commit 後の張り直し reset_tenant_context＝:399-418（docstring :404-408「commit 後は別の接続が払い出されうる」）。

### 3-A. tenants への書込（アプリ）

| # | 書込 file:line | 呼出元 | 書込時の会社文脈 |
|---|---|---|---|
| T1 | backend/app/routers/admin.py:59-65（ORM `Tenant(...)` → `db.add` → flush）。commit :84 | POST /api/v1/admin/tenants（admin.py:17。main.py:259-263） | **会社をまたぐ（新しい会社の作成）**。文脈は「呼んだ運営自身の会社」（ルーター依存 get_current_tenant＝main.py:262）。新会社の id は INSERT 時点で未確定＝`id = app.tenant_id` に合わない。create_tenant_schema（services/tenant.py）は文脈を張り替えない（services/tenant.py に set_tenant_context 0 件）。同じ処理で admin_db（別エンジン ADMIN_DATABASE_URL。database.py:75-98）も使う |
| T2 | backend/app/routers/super_admin_tenants.py:66 UPDATE is_active=FALSE（`async with db.begin()` :43 の中でコミット） | DELETE /api/v1/super-admin/tenants/{tenant_id}（:34。論理削除） | **文脈なし・会社をまたぐ**。依存は require_super_admin のみで get_current_tenant 無し（:34-40、:86 のコメントも「get_current_tenant を使わない設計」）。対象は引数の任意の会社 |
| T3 | backend/app/routers/super_admin_tenants.py:167 削除（`async with db.begin()` :165） | DELETE /api/v1/super-admin/tenants/{tenant_id}/physical（:96） | **文脈なし・会社をまたぐ**（同上）。直前の :153 に別の commit あり（監査 INSERT）。削除は users ほか CASCADE 表へ連鎖（§5 の未確認） |

### 3-B. users への書込（アプリ）

| # | 書込 file:line | 呼出元 | 書込時の会社文脈 |
|---|---|---|---|
| U1 | backend/app/routers/auth.py:96-97（ORM `User(...)`:89 → add → flush）。commit :144 | POST /api/v1/auth/register（:38。require_super_admin のみ。main.py:239 prefix /api/v1/auth） | **会社をまたぐ（他社に利用者を作る）**。書込時点で文脈なし（set_tenant_context は :116 ＝書込の後）。tenant_id は data.tenant_code で引いた別会社 |
| U2 | backend/app/routers/auth.py:266（失敗回数+1）／:275（ロック）。commit :279 | POST /api/v1/auth/login（:231） | **文脈なし**。ログイン前でトークン無し。依存は get_db のみ（:233-237）。行は誰の会社か不定（メールで引く） |
| U3 | backend/app/routers/auth.py:285（失敗回数0・locked_until 解除・last_login 更新）／:293（ハッシュ再計算）。commit :299 | 同 POST /api/v1/auth/login | **文脈なし**（上と同じ） |
| U4 | backend/app/routers/auth.py:456（パスワード確定）。commit :477 | POST /api/v1/auth/password-reset/confirm（:412） | **文脈なし**。メールの鍵（トークン）で本人特定。依存は get_db のみ |
| U5 | backend/app/routers/staff.py:98（新規 users INSERT。_resolve_user_for_new_staff :65-）。commit :632、reset_tenant_context :633 | POST /api/v1/staff（:579） | あり（:582 get_current_tenant）。tenant_id=自社。同メールが他社にあれば :82 で 409 にする |
| U6 | backend/app/routers/staff.py:308（locale）。commit :311 | PATCH /api/v1/staff/me/locale（:294） | **文脈なし**。依存は get_current_user のみ（:298。get_current_tenant 無し）。自分の行を id で更新 |
| U7 | backend/app/routers/staff.py:329（theme）。commit :332 | PATCH /api/v1/staff/me/theme（:315） | **文脈なし**（U6 と同じ） |
| U8 | （物理削除の連鎖）T3 の削除から | 同 T3 | T3 と同じ |

- 【事実】経路から users に書かないことを確認したもの: registration_tokens.py／services/registration_token.py（tenants・users を読むだけ。`User` は型のみ :38、:76）、staff の PATCH /staff/{id}（:657-732、書込先は staff）・DELETE /staff/{id}（:733-、書込先は staff）、refresh（auth.py:308-330）、viewer 系（別表 viewer_accounts）。
- 【事実】パスキー登録・パスキーでのログイン: コード上の言及は auth/self_tokens.py:63 の docstring のみ。tenants/users に書くコードは origin/main に 0 件。
- 【事実】Firebase 経由の users 自動作成（初回ログイン時の自動登録）のコードは 0 件（`User(`＝auth.py:89・`Tenant(`＝admin.py:59 の 2 件のみ。orm_ctor.txt）。
- 【事実】`.update(`・`.delete(` 形式の ORM 書込、`ON CONFLICT` つき tenants/users 書込は 0 件。

### 3-C. Celery・定期処理

- 【事実】backend/app/tasks の tenants/users への出現はすべて読取（`SELECT id FROM tenants WHERE is_active`: tasks/dashboard.py:132、maintenance.py:114、avatar.py:101、refresh_meta_tokens.py:105、verify_meta_subscriptions.py:90、priority_scoring_check.py:92、data_deletion.py:70、sa02_recon_monitor.py:61、translation.py:151）。書込 0 件。
- 【事実】課金・停止・集計で tenants/users に書くタスクは 0 件。

### 3-D. 動的な表名の書込（tenants/users に当たるか）

- 【事実】`{table}` 展開で書く箇所: archives.py:110・:146（表名は ARCHIVABLE_TABLES＝orders/leads/quotes/invoices に制限。archives.py:31,82）、tenant_profile.py:132（tenant_table_ref で会社スキーマの tenant_profile）、maintenance.py:69（保持期限削除、表名は呼出側。【未確認】引数が tenants/users になる呼出は見ていないが、同ファイル内の呼出箇所の表名定数は会社スキーマの業務表）、super_admin_dex.py（pokemon_dex 等）、contacts/orders 系（会社スキーマ内）。tenants/users に当たる経路は見つからなかった。

### 3-E. scripts（運用・初期設定）

| # | 書込 file:line | 呼出元 | 書込時の会社文脈 |
|---|---|---|---|
| S1 | scripts/setup_tenant.py:136 INSERT tenants（`engine.begin()` :122） | 運用スクリプト scripts/setup_tenant.py（DATABASE_URL の接続） | **文脈なし・新しい会社の作成**。SET app.tenant_id の呼出 0 件（scripts/setup_tenant.py 内） |
| S2 | scripts/setup_review_tenant.py:150 INSERT tenants | 運用スクリプト scripts/setup_review_tenant.py | **文脈なし・新しい会社の作成**（文脈を張るのは :207-208 ＝ロール取得時のみ） |
| S3 | scripts/setup_review_tenant.py:310（users.tenant_id の付け替え UPDATE）／:323（is_active）／:330（INSERT users） | 同上（_setup_user :287） | **文脈なし・会社をまたぐ**（:310 は他社の行を新しい会社へ移す）。文脈を張るのは :207-208（書込より後の _resolve_role_id）。同一トランザクション `engine.begin()` :292 |
| S4 | scripts/setup_test_users.py:130 INSERT tenants | 運用スクリプト scripts/setup_test_users.py | **文脈なし・新しい会社の作成** |
| S5 | scripts/setup_test_users.py:210（is_active）／:217（INSERT users） | 同上（register_user :187） | 文脈なし（書込の後の :236-237 で張る）。【事実】:200-206 のコメントどおり他社の行は UPDATE しない設計 |
| S6 | scripts/setup_single_test_user.py:201（INSERT users）／:483（is_active UPDATE） | 同名スクリプト（作成モード _run_create :379） | **不確実**。文脈を張る :171-172 は _resolve_role_id の接続。書込は別の `engine.begin()`（:474）で、同じ接続を使い回すかは接続プール次第。書込の後に :496-497 で張り直し |
| S7 | scripts/setup_single_test_user.py:368 削除（users） | 同スクリプト削除モード（_delete_user_record :352） | あり（:360-361 の SET が :368 の前）。対象は引数の会社の利用者 |
| S8 | scripts/qa/seed-tenant.sql:92 削除／:99 INSERT users（tenant 6 固定）／:299 UPDATE tenants（id=6 固定） | QA スモーク用 scripts/qa/reset-tenant.sh が psql で投入 | あり（:66-67 `set_config('app.tenant_id','6',false)`）。ただし【事実】:99 は列 `password_hash` を指定するが、この列は migrations/20260612_150000_drop_password_hash.sql:9 で削除済み＝このスクリプトは現状 INSERT で失敗しうる（RLS とは別件。【未確認】実行の有無） |
| S9 | scripts/qa/cleanup-smoke-data.sh:107 削除（users の qa- メール） | scripts/qa/cleanup-smoke-data.sh（psql） | あり（:79-80 の `set_config('app.tenant_id','6',false)`。BEGIN :78 の中） |

- 【事実】scripts の DB 接続は DATABASE_URL（アプリと同じ環境変数。例 setup_tenant.py:438）。【事実】本番では salesanchor_app（§1）。②b の migration は FORCE（migrations/20261016_020000_add_suppliers_rls.sql）。
- 【事実】migrations 内の users への値書込は migrations/054_add_users_theme.sql:10 の 1 件のみ（migration は jarvis＝rolbypassrls=t で流れる。§1）。
- 【事実】backend/scripts・backend/tcg_migration・backend/tools・monitoring・tools・tests に tenants/users への書込は 0 件（w_sql_other.txt が空）。

### 3-F. 試験が書く箇所（実 PostgreSQL の試験に影響しうる）

w_tests.txt 参照。RLS を付けると影響しうる実 PG 試験: backend/tests/rls_bootstrap.py:118,148,257（試験共通の土台）、test_paypal_regtoken_rls.py:74・:350（tenants を INSERT・削除。350 は app ロールで会社 B を消す＝RLS 後は 0 行になる）、test_discord_oauth_rls.py:55・:158・:212、test_permission_resolution_pg.py:64、test_line_import_devices_pg.py:38-39・:74・:76。【未確認】各試験が管理接続（所有者）か app 接続のどちらで書くか。

## 4. 読取の全経路（書込だけ RLS では影響なし。SELECT ポリシーは全行可）

- 認証前に users を読む経路が多数ある（auth.py:250 ログイン、:445 パスワード確定、auth/dependencies.py:102、auth/self_tokens.py:224、staff.py:74）。読取を全行可にする設計なら変わらない。
- tenants を会社文脈なしで読む箇所: 全 Celery 定期処理（§3-C）、services/discord_notifier.py:196、get_current_tenant（dependencies.py:283-300）。

## 5. 会社文脈の寿命（書込直前の commit・接続の入れ替え）

- 【事実】get_current_tenant は `SET`（セッション単位）で文脈を張る（dependencies.py:309-316）。commit のあと別接続が払い出されうるため、reset_tenant_context で張り直す（:399-418）。②b の _operator_writes は `set_operator_context`→処理→finally で `reset_operator_context`（backend/app/routers/super_admin_suppliers.py:57-72、dependencies.py:489-520）。
- 【事実】「接続の会社」に頼る経路（U5）は commit :632 の後に reset_tenant_context :633 がある。書込 → commit → 張り直しの順で、書込の時点では文脈が有効。
- 【事実】文脈なし経路（U2・U3・U4・U6・U7・T2・T3）は、そもそも書込の前に会社文脈を張らない。書込だけ RLS（`tenant_id = app.tenant_id`）を付けると、`UPDATE`／`DELETE` は無言で 0 行になる（②a recon §5 で確認済みの PostgreSQL 仕様。INSERT は WITH CHECK 不一致でエラー）。ログイン直後の last_login 更新・失敗回数、パスワード再設定、自分の言語・テーマ変更がすべて静かに効かなくなる。
- 【事実】既存の運営文脈 `app.is_operator='true'` は、②b の suppliers では「tenant_id が空の共通行」だけを通す式（migrations/20261016_020000_add_suppliers_rls.sql:21-37）。他社の行を書く許可ではない。tenants/users で運営が他社の行を触る経路（T1・T2・T3・U1）には、新しい式が要る。【推測】
- 【事実】便A の CI 実 PG 試験⑥（test_paypal_regtoken_rls.py:342-358、PR #4354 で合格）で、RLS 付きの子表が tenants 削除の連鎖で消えることを実測済み。以下は当時の記述：【当時未確認】T3 の連鎖削除（CASCADE）が RLS を通るか。②a recon §5 の未確認と同じ。PostgreSQL docs/16 ddl-rowsecurity は「Referential integrity checks ... always bypass row security」と書くが、CASCADE の実行そのものが RLS を通るかは明記が無く、試験で実測が要る（手本 test_paypal_regtoken_rls.py:342 の ⑥ と同形）。
- 【事実】operator 文脈を張る既存の呼出元: super_admin_suppliers.py（5 ルート :142,192,227,441,767）、ops.py（:227,284,303,366,438,456）、fx_rate_admin.py:135、tcg_line_import.py:459、services/tcg_line_import_svc.py:671、services/line_source_names.py:125。いずれも tenants/users への書込とは無関係。

## 6. 書込経路の集計（実装コード。試験・migration を除く）

- tenants: アプリ 3（T1・T2・T3）＋ scripts 4（S1・S2・S4・S8:299）＝ 7、ほかに連鎖削除 1
- users: アプリ 8（U1〜U7。うち auth.py:266/275/285/293/456 を別行で数えると SQL は 5 文）＋ scripts 11 文（S3 の 3、S5 の 2、S6 の 2、S7 の 1、S8 の 2、S9 の 1）、ほかに連鎖削除（T3）
- 文脈なし、不確実、会社をまたぐ経路: §7

## 7. 見落としやすい点・要判断

- 文脈なし: U2・U3（ログイン）、U4（パスワード確定）、U6・U7（言語・テーマ）、T2・T3（運営の会社停止・削除）、S1〜S5（スクリプト）
- 会社をまたぐ／新規作成: T1（POST /admin/tenants）、U1（POST /auth/register）、T2・T3、S1・S2・S4（新規作成）、S3（:310 の付け替え）
- 不確実: S6（接続の使い回し次第）、T3 の連鎖削除、本番の DB ロールと FORCE の要否

## 8. 試験・CI の前提

- 手本: backend/tests/test_paypal_regtoken_rls.py。実 PostgreSQL（RLS_ADMIN_DATABASE_URL／RLS_TEST_DATABASE_URL 未設定なら skip。:19-30）。使い捨て DB を作り、admin 接続（所有者）と app 接続（`pool_size=1` で接続を 1 本使い回し、SET の戻り忘れを検出。:63-66）の 2 本を使う。ロールは salesanchor_app（GRANT :40-43）。外部キー先の public.tenants・public.users は backend/tests/rls_bootstrap.py:106-158（`_ensure_public_users`）で用意する。
- 型: ① カタログ検査（FORCE RLS・4 ポリシー。:157）② 文脈なし全行読取（:191）③ 他社・文脈なしの書込拒否（:211）④ 自社の INSERT/UPDATE/DELETE（:273）⑤ 接続入れ替え後の保存（:300）⑥ 会社削除の連鎖（:342）⑦ 公開 API 相当（:361）。
- 【事実】rls_bootstrap.py の users 定義も tenant_id NOT NULL DEFAULT 999（:133）。
- 【事実】.github/workflows/migration-test.yml に tenants・users の最小定義がある: tenants :185（migration-test-run ジョブ）と :1154（migration-full-dryrun ジョブ）、users :196 と :1165。users は tenant_id NOT NULL・password_hash 付き（is_super_admin は意図的に無し＝:195 のコメント）。schema-check.yml:113（tenants）・:124（users）にも別の最小定義。
- 【事実】tenants の定義に `company_name` 列が無い（migration-test.yml:185-193）のに対し、rls_bootstrap.py:106 は `company_name` を持つ。両者の差異は試験の INSERT 列に影響する。
- 【事実】SQLite 用の定義（backend/tests/conftest.py:1176 users、:1343 tenants）は RLS 試験では使えない。

## 9. 追加調査（2026-10-16 Opus 依頼・Sonnet。生出力 /tmp/CC報告ファイル/s1-stage3b/b_*.txt）

- 【事実】文脈関数は生の `SET`（backend/app/auth/dependencies.py）: set_tenant_context :337-359（app.is_operator を '' にする）、reset_tenant_context :399、clear_tenant_context :421-440（app.tenant_id・app.is_operator を '' に）、set_operator_context :489-503（`SET app.is_operator = 'true'`）、reset_operator_context :506-520。
- 【事実】運営文脈の手本: backend/app/routers/super_admin_suppliers.py の `_operator_writes`（set → 処理 → finally で reset）。
- 【事実】User/Tenant の ORM 属性代入・merge・bulk 系・session.delete による書込は backend/app と scripts で 0 件（b_orm_attr.txt）。ORM 生成は auth.py:89 と admin.py:59 の 2 か所のみ。
- 【事実】admin.py は `db`（get_db）で Tenant を作り（:59-65・commit :84）、`admin_db`（get_admin_db）で会社スキーマを作る。super_admin_tenants.py も db・admin_db の 2 本（:101-102）、物理削除は db.commit :153 → admin_db の DROP SCHEMA → admin_db.commit :162 → db で public.tenants 削除 :165-167。
- 【事実】試験の型（backend/tests/test_paypal_regtoken_rls.py）: URL :19-20、会社番号 984/985 :34-35、実 migration 一覧 :36-41、GRANT :42-45、使い捨て DB と app 接続 pool_size=1 :53-92、文脈接続 `_ctx_conn` :123-131（set_config(...,true)）、⑥連鎖削除 :342-358。この試験が当てる migration 一覧に今回の新 migration は入らないため、既存試験は今回の RLS の影響を受けない。
- 【事実】migration-test.yml の tenants 最小定義 :185-195・:1154-、INSERT :238・:1206。CREATE ROLE/GRANT 0 件＝ migration は jarvis（rolbypassrls=t）で当たる。

## 10. 便B（tenants）の結論

- tenants への書込は 運営の 3 経路（T1 作成・T2 論理削除・T3 物理削除）と scripts（S1・S2・S4・S8:299）だけで、**会社の利用者が自社文脈で tenants に書く経路は 0 件**。
- よって tenants の書込は「運営文脈（app.is_operator='true'）だけ」に絞れる。アプリは T1〜T3 の書込の直前に運営文脈を張れば足りる。
- scripts は本番では salesanchor_app で走るため、運営文脈を張らないと会社作成の INSERT が 42501 で失敗する（無言ではなく明示エラー）。
- users（U1〜U7）は便C で扱う（ログイン・パスワード再設定・言語/テーマの文脈なし書込の修正が要る）。
