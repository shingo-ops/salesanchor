# recon: マイグレーションの衛生（毎デプロイの再実行と値を書く migration の後始末）、役割の安定した識別子（2026-10-05、読み取りのみ）

基準: origin/main 41d65666f。本番の読み取りは単文の SELECT のみで、何も書いていない。生の出力・集計は「社外秘のローカル作業メモ（リポジトリ外）」にあり、ここには件数・file:line・引用だけを書く。パスは本文にそのまま書く（バッククォートで囲まない）。PR #3965 の元の資料は、同じフォルダの runner-design-from-3965.md と runner-recon-from-3965.md にそのまま置いた。

## 0. 要点（事実のみ）
- scripts/run_all_migrations.sh は登録された全手順（run_sql 291 行・run_py 26 行）を、デプロイのたびに最初から実行する。実行済みの記録は無い（runner-recon-from-3965.md:53）。.github/workflows/deploy.yml の「Run database migrations」ステップ（:500-514）は、新しい backend が切り替わった後に走る。
- 登録された SQL のうち 52 ファイルが、保護対象または同種のマスタ表へ値を書く。そのうち 28 ファイルは毎デプロイ実行される（保護された表への書き込みは ADR-155 が禁止している）。
- 28 ファイルのうち、既存の値を書き換える（OVERWRITE）のは 8 ファイル。本番の今の値はいずれも migration と一致した（差 0）。
- 4 つの migration（080、023、075、025）は、新テナントの作成が書かない値を次のデプロイで補っている（section 4）。
- migration-guard の Check 7・8 は「PR で追加された」migration ファイルだけを検査する（section 7）。既存ファイルの編集は検査されない。

## 1. 毎デプロイの再実行（現状）
- 登録: scripts/run_all_migrations.sh（run_sql 291 行・run_py 26 行、計 317 行。:530 と :536 に同じファイルの二重登録が 1 件）。set -e で、どこかで失敗すると以降は走らない（runner-recon-from-3965.md:23 の引用表）。最新の登録は 20261003_100000_create_app_fx_rate_history.sql。
- 順序: .github/workflows/deploy.yml の「Deploy to VPS」ステップ（:212）で blue-green の backend 切替（:375-376 scripts/blue-green-cutover.sh）と他コンテナの更新（:388-396）が先、その後「Run database migrations」（:500、条件 :501、実行 :514）。新しいコードは、同じデプロイの migration より先に動く。
- 障害の歴史（runner-recon-from-3965.md:59-62）: 2026-10-03 商品の表の列番号上限（修正に PR #3958〜#3963）、2026-09-15 古い表を削除した後の再実行失敗（ADR-1002）、追加→削除のデータ手順の組の衝突（migrations/20260924_040000_seed_knowledge_extraction_vocab.sql の注記）、二重登録。
- 2026-10-05 02:38:41Z に 110 商品の updated_at が同時に書き換わり、MEGAドリームex の mark が M2a から M3 に戻った。原因は migrations/20260604_010000_seed_product_marks.sql:23-25（名称の完全一致で mark を上書き。登録は scripts/run_all_migrations.sh:264）。audit_log に対応する行は無い。#3978（draft）が本文を無効化する（docs/handoff/neutralize-seed-product-marks/design.md §4）。

## 2. 値を書く migration の一覧（登録された SQL 290 ファイルの走査）
方法: コメントを除いて INSERT INTO / UPDATE ... SET / DELETE FROM を拾い、対象の表で集計。保護対象は migration-guard の 23 表（.github/workflows/migration-guard.yml:416）に、同種のマスタ表（tcg_suppliers、supplier_channels、tcg_series、tcg_manufacturers、tcg_major_categories、tcg_normalization_rules、tcg_unit_evidence_rules、tcg_distribution_settings、channel_masters、close_reasons、knowledge_rules、products_logistics、roles、role_permissions）を足した。
結果: 52 ファイルが書く。無効化済み（NEUTRALIZED の印のみ）14 ファイルは書き込みが残っていない（登録行 258、273、439、579、580、604、613、622、638、639、647、648、649、655）。Python の migration 26 本には、この表の集合への書き込みは正規表現では見つからなかった（文字列で組み立てる SQL は未確認）。

### 2.1 毎デプロイ必ず実行される 28 ファイル（登録行・文・種別）
種別: OVERWRITE = 既存の値を変える。FILL-ONLY = 無い行を足す、または NULL・空のときだけ埋める。
公開（共用）マスタ 24 ファイル:
- OVERWRITE: 264 migrations/20260604_010000_seed_product_marks.sql:23（products.mark）、182 migrations/20260620_010000_create_inventory_aggregation_rules.sql:25-32（ON CONFLICT (condition) DO UPDATE、許容差）、445 migrations/20260621_010000_create_countries_master.sql:31-222（ON CONFLICT (code) DO UPDATE、190 行）、080 migrations/080_phase_b_migration.sql:37（tenant_settings.spreadsheet_phase を A から B へ）、023 migrations/023_fix_system_admin_is_system_flag.sql:41（roles.is_system）、361 migrations/20260611_010000_fix_owner_role_color.sql:46（roles.color）、442 migrations/20260616_000000_fix_tcg_type_dedup.sql:53、:57、:65（products.tcg_type の更新と type_master の 2 コード削除）、844 migrations/20260928_100000_delete_skip_condition_rules.sql:13（knowledge_rules の skip_condition を削除）。
- FILL-ONLY: 018 migrations/018_extend_permissions_with_menu_grain.sql:41-68、024 migrations/024_add_staff_bots_permissions.sql:17-26、312 migrations/20260604_180000_analytics_agent_a_tables.sql:204-212（いずれも permissions）、170 migrations/075_create_goals.sql:36、:129、:138（permissions と role_permissions）、91 migrations/025_resync_owner_admin_all_permissions.sql:65（role_permissions）、192 migrations/085_create_tcg_type_master.sql:49 と 193 migrations/086_seed_additional_tcg_types.sql:28（type master）、218 migrations/20260602_020000_add_products_tcg_type.sql:10-22、249 migrations/20260603_000000_add_products_product_kind.sql:20、267 migrations/20260604_020000_backfill_products_shipping_defaults.sql:28、318 migrations/20260605_000000_add_products_display_order.sql:20、677 migrations/20260916_130000_work_id_not_null.sql:18、304 migrations/20260604_090000_create_link_templates.sql:23-29、786 migrations/20260923_030000_promote_remaining_tcg_tables.sql:45、:81、:120（tenant_004 から public へのコピー）、753 migrations/20260924_040000_seed_knowledge_extraction_vocab.sql:6、:43、835 migrations/20260927_120000_add_max_age_hours_setting.sql:2-4。
テナントの表 4 ファイル（FILL-ONLY）: 367 migrations/20260611_100000_create_channel_masters.sql:73、418 migrations/20260613_020000_funnel_close_reasons.sql:121、:134、545 migrations/20260902_110000_tcg_classification_masters.sql:85-122、552 migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql:47-107（いずれも tenant_004）。

### 2.2 ガードで本番では実行されない（UNREACHABLE）8 ファイル
migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql:86（public.products.work_id が NOT NULL なら RETURN、:69-79）、migrations/20260909_000000_public_products_phase2b_columns.sql:104（work_id が integer なら CONTINUE）、migrations/20260914_140000_unify_tcg_products_to_public.sql:180、:216、:251（tcg_uuid が UUID 型で無ければ RETURN、:104-123）、migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:64、:149、:229（tcg_uuid が無い場合は UPDATE の分岐に入らない）、migrations/20260604_170000_create_product_attribute_masters.sql:62（表が空のときだけ。本番は 30 行）、migrations/20260906_120000_create_tcg_tables_t001.sql:570-629（tenant_001 は audit_log があり tcg_products が無いので RETURN、:40-44）、migrations/20260913_200000_tcg_cardset_exclusion.sql:70 と migrations/20260913_210000_tcg_cardset_bundle_registration.sql:99（キーワード表が UUID のため tcg_uuid を要求して RETURN）。

### 2.3 同じ実行の中で作って消す tenant_004 の鎖（IN-RUN）
migrations/20260831_110000_create_tcg_analysis_tables_t004.sql（登録 530 と 536）は、tenant_004 に audit_log があり tcg_products が無い場合だけ飛ばす（:41-45）。本番はどちらも無いので、毎デプロイ conditions、units、tcg_products、キーワード表、解析の表、tcg_suppliers、supplier_channels を作り直す。続く 533、545、548、552、555、557、560、563、569、575、578、581、587、590、600、631、641、650 の migration がそれらに書き、668（migrations/20260915_010000_drop_tcg_products_phase2c.sql:86）、747（migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:17-18、:42、:49-50）、759（migrations/20260921_130000_drop_tenant004_master_copies.sql:27-28、:41-42）が消す。これはデプロイ中の登録順から導いた事実で、鎖を実行・再現して確かめてはいない。
- 既に受け入れ済みの記述: docs/handoff/products-column-churn-5/design.md:50-100（ウォーク1）は、この鎖を「不動点」として記述し、#3963 は鎖を成功させる修正であって除去ではない。その表は Phase 2c に関わる手順だけで、ノート・状態・正規化・配信設定の seed（555-641）は載っていない。

## 3. 本番との比較（OVERWRITE と FILL-ONLY、読み取り 2026-10-05）
- 264: 125 組、名称が一致した本番の行 110、mark が違う行 0（MEGAドリームex は M3 で seed と同じ）。
- 182: 4 行中、欠け・違いは 0。445: migration 190 行、本番 190 行、code/name/dial_code/is_active の md5 が一致（差 0）。080: spreadsheet_phase が A の行 0。023: オーナー・システム管理者で is_system が false の行 0（5 テナント）。361: 色が #ef4444 のままの system ロール 0（5 テナント）。442: tcg_type が pokemon または weiss の商品 0、type_master の該当コード 0。844: skip_condition 0 行。
- FILL-ONLY で足される行: permissions の 31 キー（018、024、075、20260604_180000）は欠け 0、025 は owner/admin の不足対 0（5 テナント）、075 の goals.view は不足 0、304 は 5 チャネル欠け 0、085/086 は 12 コード欠け 0、786 は tenant_004 から public へ未コピーの id が 3 表とも 0、835 の max_age_hours は 1 行存在、753 は block_delimiter が migration 17 に対し本番 18、status_keyword は 4 対 4（件数のみ比較）、218/249/267/318/677 は変わる行 0、367 は 6 プラットフォーム欠け 0、418 は 15 行欠け 0（5 テナント）。545 と 552 は比較していない。
- 結論（事実）: 今の本番は、OVERWRITE の 8 ファイルが書く値と一致している。無効化しても本番の今の値は変わらない。今後アプリや CSV で直した値は、次のデプロイで元に戻る。

## 4. 新テナントの作成と 4 つの migration（新テナントは何を書き、何を書かないか）
作成の流れ（backend/app/services/tenant.py:1620-1788 の create_tenant_schema）: :1652 スキーマ作成、:1663 _TENANT_TABLES_SQL（tenant.py:184-1166、41 表、deals は作らない: :340、:807-808）、:1667-1700 RLS・権限、:1707 meta_page_routing の同期トリガ、その後の DML: :1730 seed_system_roles（:1564-1617）、:1733 seed_default_channel_masters（:1544-1561）、:1735-1770 public.tenant_settings の初期行（:1748-1760 `VALUES (:tid, 'A', ...) ON CONFLICT (tenant_id) DO NOTHING`、失敗は警告のみ）。close_reasons と deal_close_reasons は空で作られる（tenant.py:810-827）。呼び出し元: backend/app/routers/admin.py:68、scripts/setup_tenant.py:184、scripts/setup_review_tenant.py:197、scripts/setup_test_users.py:140、:182。
作成が書かず、次のデプロイの再実行が補っているもの:
- 080（migrations/080_phase_b_migration.sql:33-40）: 作成は spreadsheet_phase を 'A' で入れる（backend/app/services/tenant.py:1753、コメント :1735-1738）。080 が A を B に変える。本番の 5 テナントはすべて B、列の既定値も 'B'::text。
- 023（migrations/023_fix_system_admin_is_system_flag.sql:40-44）: 作成は システム管理者 を is_system False で作る（tenant.py:62、オーナーは True: :54）。ON CONFLICT の更新（:1596-1603）は is_system を変えない。本番の 5 テナントは両ロールとも is_system が t。
- 075（migrations/075_create_goals.sql:36-38、:128-143）: DEFAULT_ROLES（tenant.py:49-178）に goals.* のキーは無い。goals.view を全ロール、goals.edit を 4 ロールに付与するのは 075 だけ。本番はマネージャーに goals.view と goals.edit、営業・CS・仕入れ・発送に goals.view。
- 025（migrations/025_resync_owner_admin_all_permissions.sql:52-69）: 作成時は "ALL"（tenant.py:55）と "ALL_EXCEPT_SYSTEM_MANAGE"（:63、_assign_permissions_to_role: :1504-1541）で同じ効果を出す。後から足されたキーだけが 025 の再実行で owner/admin に届く。
- close_reasons: 作成は行を入れず（tenant.py:810-817）、migrations/20260613_020000_funnel_close_reasons.sql の保護（:37-44、deals の無いスキーマは飛ばす）により新テナントには入らない。本番は 5 テナントに 15 行ずつある。
- channel_masters は作成が自分で入れる（tenant.py:1544-1561、:1733）ので、migrations/20260611_100000_create_channel_masters.sql に依存しない。
本番の 5 既存テナント（tenant_001、003、004、005、006）と「作成 + 4 migration」の比較: 各テナントに既定の 7 ロールだけ。オーナーは public.permissions の 123 キー全部、システム管理者は system.manage を除く 122 キー。色・priority は DEFAULT_ROLES と一致。営業と CS は 4 つの migration の範囲を超えて差がある（tenant_004・005 は menu.* を持ち、tenant_001・003 は Phase 2-4 のキーが欠け、tenant_006 は goals.view だけ）。menu.* の付与元は未確認（migrations/018_extend_permissions_with_menu_grain.sql は権限のキーを入れるだけで付与しない）。

## 5. 役割の識別、権限の判定経路、キーの定義
### 5.1 owner/admin を何で見分けているか
- roles 表（テナントごと、backend/app/services/tenant.py:485-496）: id、tenant_id、name VARCHAR(100)、color、priority、is_system BOOLEAN DEFAULT FALSE、description、UNIQUE(tenant_id, name)。コード・スラッグの列は無い。
- 判定は表示名だけ: DEFAULT_ROLES の name（tenant.py:51、:59）、upsert の鍵 (tenant_id, name)（:1596-1603）、既存ロールの検索 WHERE tenant_id = :tid AND name = :name（:1581）、migration 023:42、025:54、075:136、backend/app/routers/auth.py:105（既定ロールを名前で検索。DEFAULT_NEW_USER_ROLE = "CS": tenant.py:180）。
- priority は オーナー 1000、システム管理者 900（tenant.py:53、:61）で、backend/app/routers/roles.py:60-90 の _max_priority_for_user と編集ガード（:400-405）が使う。priority は一意ではない（営業と CS が 300）。backend と frontend は「オーナー」「システム管理者」で分岐しない（コメントと tenant.py のみ）。
### 5.2 権限の判定経路
- backend/app/auth/dependencies.py:485-529 load_user_permissions: キャッシュ（:496）→ SQL（:505-513、user_roles から role_permissions と public.permissions）→ 空かつ public.users.role が admin のとき public.permissions の全キー（:518-527）→ キャッシュ書き込み（:528）。require_permission（:532-558）が :550 で呼ぶ。同じ関数を使う呼び出し: backend/app/routers/roles.py:124、:424、backend/app/routers/calendar.py:167、:228、backend/app/routers/inventory_aggregated.py:63、backend/app/routers/inventory_search.py:89。frontend/src/hooks/usePermissions.ts:25 の /me/permissions（backend/app/routers/roles.py:112-148）も同じ関数。
- テナントのスキーマは get_current_tenant（dependencies.py:193-240、:233-236）の search_path で解決し、public.permissions は public 接頭辞で読む（:509、:523）。
- 判定を通らない role_permissions の読み書き: backend/app/routers/roles.py:353-376（行列表示）、:434-440（書き込み）、backend/app/routers/tenant_admin_inventory_visibility.py:71、:162、:172、:182、backend/app/services/tenant.py:1504-1541（作成）。
- キャッシュ: backend/app/cache.py:18 PERMISSIONS_CACHE_TTL = 300（秒）、:174 setex、無効化は :197 と :208（キーの追加は呼ばない）。
- users.role = 'admin' の予備経路: 本番の admin ユーザー 4 人はいずれもオーナーのロールを持ち、予備経路（キーが空のとき）に達する本番ユーザーは今いない。
### 5.3 owner/admin の権限の編集可否
backend/app/routers/roles.py:250-251（PATCH、is_system は 403）、:322-323（DELETE、同）、:393-398（PUT /roles/{role_id}/permissions、システムロールは 403）、:400-405（priority 以上は 403）、:423-433（持っていない権限は付与できない）、backend/app/routers/tenant_admin_inventory_visibility.py:119-137（is_system は編集不可）、frontend/src/pages/roles/RolesPage.tsx:182。保護は is_system に依存する。本番の両ロールは is_system が t だが、新規テナントのシステム管理者は False（tenant.py:62）。
### 5.4 権限のキーの追加経路と定義の場所
- public.permissions にアプリの書き手は無い（テストの backend/tests/conftest.py:712 のみ）。キーは migration の INSERT が足す（002、004、006、008、010、018、024、042、063、065、067、069、070、075、20260604_180000 の 15 ファイル）。本番 123 キー。migration-guard の PROTECTED_TABLES（.github/workflows/migration-guard.yml:416）に permissions が入ったのは commit e364dd233（2026-09-18）。それ以降に追加されたキーは無く、現行ルールでの追加経路の前例は無い。
- 直近 3 キー: analytics.customer_priority.override、analytics.customer_priority.view（migrations/20260604_180000_analytics_agent_a_tables.sql:204-211）、goals.edit、goals.view（migrations/075_create_goals.sql:36-38）。analytics のキーを owner/admin に付与する文は 025 以外に見つからない。
- 定義の場所（単一の定数は無い）: DB public.permissions（実行時の正）、migration の INSERT（15 ファイル）、backend/app/services/tenant.py:49-178 DEFAULT_ROLES（5 つのリストロールで 44 キー）、migrations/025_resync_owner_admin_all_permissions.sql:58-62 と migrations/075_create_goals.sql:128-143（役割とキーの対応のコピー）、backend/tests/conftest.py:1546-1590 ALL_TEST_PERMISSIONS（85 キー、本番にあって無いキーが 38）、frontend の使用箇所（frontend/src/components/DesktopShell.tsx:173-183、:223、frontend/src/pages/roles/RolesPage.tsx:60-68）。これらのコピーを突き合わせる検査は無い。

## 6. テストと CI が migration に依存している箇所（step2）
CI の前提: .github/workflows/test.yml:206-241 の pytest ジョブ（SQLite + PostgreSQL RLS）が PG のテストを含めて走る（RLS_ADMIN_DATABASE_URL と RLS_TEST_DATABASE_URL: :222-224）。
migration が出す値そのものを assert するテスト:
- backend/tests/test_countries_master.py:133-161（190 行、先頭 AF、末尾 ZW、frontend/src/constants/countries.ts との一致）、:174-241（migration をデータの供給元に使う）。:85-97 は SQLite の fixture を使い、migration に依存しない（backend/tests/conftest.py:118-126）。
- backend/tests/test_inventory_aggregation.py:13、:157-186（既定の 4 行をちょうど assert）。backend/tests/test_inventory_aggregated.py:230 は表を作るために適用（:427-430 の assert は緩い）。アプリの読み取りは backend/app/services/inventory_aggregation.py:389。
- backend/tests/test_rls_bootstrap_ordering.py:102-111 と backend/tests/rls_bootstrap.py:71-85 は、migrations/20260611_100000_create_channel_masters.sql に決まった文字列（WHERE nspname ~ '^tenant_\d+$'）がちょうど 1 回あることを要求する。本文を無効化するとこの単体テストと bootstrap_tenant_schema が壊れる。
構造と seed が 1 ファイルに同居し、PG テストの準備が適用するもの: backend/tests/rls_bootstrap.py:13-36 と backend/tests/test_products_tcg_type_fk.py:30-47 が 085、086、20260602_020000、20260603_000000、20260605_000000、20260616_000000 を適用。085/086 は backend/tests/test_tcg_distribution_pg.py:69-70、backend/tests/test_tcg_work_matching_integration.py:231-232、backend/tests/test_tcg_condition_review.py:60-61、backend/tests/test_tcg_product_list_pg.py:58-59 も適用し、type_master の行をコードで選ぶ（test_tcg_work_matching_integration.py:361-362）。backend/tests/test_tcg_product_list_pg.py:54 は 20260902_110000 を適用。これらのファイルは構造（表・列）も持つので、本文を丸ごと無効化すると表や列も消える。範囲外で同様に使われるもの: migrations/20260903_180000_tcg_products_mark_en_t004.sql（test_tcg_product_list_pg.py:53）、migrations/20260903_210000_tcg_distribution_settings_t004.sql（test_tcg_distribution_pg.py:73）。
CI のジョブ: .github/workflows/schema-check.yml:160-173 が 018 と 024 を適用（失敗は || true で無視、テナント作成の前）。.github/workflows/migration-test.yml:741-744 と :1540-1543 は 835 が INSERT するため tcg_distribution_settings の表を前提として作る。
migration の代わりに既に値を供給しているもの: backend/tests/conftest.py:118-143（国と 12 の type コード）、:706-740（permissions、countries、channel_masters、type_master の SQLite シード）、:1309 と :1463（close_reasons）、ALL_TEST_PERMISSIONS（:1546-1590）に goals、staff、bots、analytics.customer_priority のキーがある（menu.* は無い）。type_master の PG 側の同等物は無い。
依存が見つからなかったもの: 264、267、025、023、361、075、20260604_180000、304、677、786、753、844、418、20260903_120000（テスト・CI とも名前でも表でも参照なし）、835（CI の基準表の注記のみ。アプリは backend/app/services/tcg_distribution_svc.py:297 で既定 0 に倒す）。無効化済み 14 ファイルは参照なし。#3544 はテストの 7 本を削除し、キーワードのデータを fixture（backend/tests/test_tcg_work_matching_integration.py:349-363 の seed_products）へ移した。
テスト全般: 本番の load_user_permissions は全テストで差し替えられ、実関数を呼ぶテストは無い（backend/tests/conftest.py:1586-1604、:1673）。owner/admin が全キーを持つこと、判定の SQL、予備経路、キャッシュを assert するテストは無い。

## 7. 全件ドライラン、migration-guard の検査範囲、PR #3965
- 全件ドライラン（.github/workflows/migration-test.yml:1649-1720、同じ式が :1665 と :1699）: 名前の先頭が 0、2026060（4〜9）、2026061、2026062 のものだけを選ぶ式（grep -E の 4 つの選択肢）を run_sql の行に適用し、空の Postgres に 2 周（新規適用と冪等性）で psql -f。登録された 290 ファイルのうち 128 を含み（0xx が 46、20260604〜20260629 が 82）、162 を除く（20260601〜03 が 17、100_ 始まりが 1、202607 が 14、202608 が 1、202609 が 123、202610 が 6）。理由が書いてあるのは 20260601〜03 の除外だけ（:1649-1654「Python migration 依存」）。この式は commit 9e8c20c22 と a8e7e14a3（2026-06-12）で作られ、その後変わっていない。28 ファイルのうち 19 が含まれ、9 が除かれる。変更された migration を 2 回流す別のステップ（:1008-1030、一覧は :937-940）は、数字 3 桁で始まる名前（8 桁の日付形式も該当）で {schema} を含まないものを流す。
- Check 7・8（.github/workflows/migration-guard.yml）: トリガーは pull_request（:3-5）。対象の一覧は :75-90（git diff の --diff-filter=A で追加されたファイルから、名前が migrations/ の直下で数字で始まる .sql だけを拾う式）で、追加されたファイルだけ。Check 7（:407-493）は追加された行（コメントを除く）だけを INSERT/UPDATE/DELETE と保護された表で検査し、format('%I.table') のように変数で組んだ SQL は一致しない。Check 8（:495-）はそのファイルの全体を検査する。既存ファイルの編集、名前の変更、Python の migration、旧 migration の再実行は検査されない。保護リストはコード上 23 表（:416、:503）で、直前のコメントは「14 テーブル」のまま。
- PR #3965（draft、ADR-1005 草案）: 実行済みの記録表を作り、未実行の手順だけを登録順に 1 回実行する案（runner-design-from-3965.md:65-69）。記録表は案のまま（名前と列は未定）。既存 317 件は、全件成功の直後の状態を baseline として「実行済み」と記録し、実行はしない（:66）。毎回実行が必要な手順は名前付きの別リスト（:67）。全件やり直しの方式は戻し方として残す（:69）。段階0（CI の検査と二重登録の削除と全件ドライランの範囲の確認）、段階1（テナントの正本を 1 つに）、段階2（実行済み記録）。Architect の APPROVE は「段階0のみ実装可。段階1・2 は前調査と PO 判断の後」で、設計担当の自己審査（runner-design-from-3965.md:9）。PO の承認は未。値を書く migration、migration-guard の対象範囲（追加ファイルのみ）、既存 migration の編集（段階2のチェックサムのみ: :68）の扱いは、段階2以外にはない。active-work は release-migration-runner-design.md（状態 REVIEW、担当セッションは未確認）。
- ADR の番号: ADR-1005 は #3942（docs/adr/ADR-1005-api-contract-and-wiring-ledger.md、Accepted、2026-10-04）と #3965（docs/adr/ADR-1005-migration-run-once-ledger.md、Proposed）が取っている。#3971 は #3942 の ADR-1005 を根拠にする。ADR-1006 は #3976。main、open の PR、リモートのブランチに ADR-1007 以上は無い。

## 8. 未確認
- 保護表への書き込みを無効化する範囲の決定、新テナントの補完をコードに寄せる範囲、roles の識別子の設計は、この recon の範囲外（設計で決める）。
- 本番の 5 テナントの表の集合とテナントの行の件数（channel_masters、tenant_profile、close_reasons の最新の件数）は、読み取りがフックに止められて未実施。
- 鎖（IN-RUN）の実行順は登録順からの導出で、実行や再現はしていない。デプロイのログには手順の出力が残っていない。
- 545 と 552 の本番との比較、knowledge_rules のパターンの 1 件ずつの比較、tenant の deals 表が登録行 418 の時点で存在するか、20260902_110000 の seed を join するテストの有無は未確認。
- menu.* のロールへの付与元、permission キャッシュの無効化の全経路、RLS の設定（roles、role_permissions、user_roles）は未確認。
