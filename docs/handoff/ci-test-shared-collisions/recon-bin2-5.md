# recon 追補: 種類 A・B・C・E の調べ（読むだけ）

状態: 調べ済み（調べ役・Sonnet・2026-11-26）。基準: `origin/main` 33f2112f9。
前提: 親の `recon.md` §1・§3・§4 を読んだ上での追補。製品・試験のコードは変えていない。試験も流していない（読むだけ）。
直し方の案は書かない（設計は Opus）。「事実」は file:line つき。推測・未確認は明記して分ける。

注意（行番号のずれ）: 依頼文は `backend/tests/test_tcg_product_list_pg.py` の `product_db` を :55-125 としていたが、実際は `create_product_schema` が :47-92、`product_db` が :95-120。以下は実際の行を使う。

---

## A 「調べたが無い」の相手: `product_db` が流す migration と、2回流しても壊れないか

### A-1 共有 DB に流す一覧（`backend/tests/test_tcg_product_list_pg.py:47-92`・事実）

`product_db`（:95-120）は共有 DB `jarvis_test_db` で、1つの transaction（:106）を最後に巻き戻す（:118）。transaction の中で `public_bootstrap_lock` と同じ鍵を **共有**（`pg_advisory_xact_lock_shared`・:110-113）で取る。`create_product_schema` はその transaction の中で次を順に流す。
なお「荷姿の表」だけは transaction の外で先に確定させる（`ensure_product_packagings`・:104。`backend/tests/rls_bootstrap.py:111-149`。自分で `public_bootstrap_lock` を取る）。

| 順 | 流すもの（出どころ） | public への作用 | 各文の冪等さ（file:line） |
|---|---|---|---|
| 0 | `CREATE SCHEMA product_csv_test_<uuid>`（:49） | なし（一意の名前） | 一意なので対象外 |
| 1 | `_PUBLIC_PRODUCTS_DDL` = `backend/tests/fixtures/public_products_test.sql`（:51-54。`;` で割って1文ずつ。前後を `pg_advisory_lock(2147483647)`／unlock で挟む :50・:55） | `public.products` の作成・列追加・index | 全文が `IF NOT EXISTS`: CREATE TABLE（fixtures/public_products_test.sql:2）、UNIQUE INDEX（:24・:41）、ADD COLUMN ×13（:28-40）。冪等 |
| 2 | `20260831_110000_create_tcg_analysis_tables_t004.sql`（:58→:62-63。`tenant_004` を試験の schema 名に置換） | 一意の schema だけ。`public.` の参照は grep で当たりなし | DO ブロック（:23）の中の CREATE TABLE／INDEX が全て `IF NOT EXISTS`（:55-373 を grep で確認）。冪等 |
| 3 | `20260903_180000_tcg_products_mark_en_t004.sql`（:59） | 一意の schema だけ | DO ブロック（:15）。schema 無し・表無しなら RETURN（:20-31）。列追加は `information_schema` で無いときだけ（:34-57）。UPDATE は `COALESCE`（:59-63）。冪等 |
| 4 | `20260902_110000_tcg_classification_masters.sql`（:60） | 一意の schema だけ | DO ブロック（:12）。INSERT 4か所すべて `ON CONFLICT (code) DO NOTHING`（:85-125）。表の作成は冒頭コメント :10 が「CREATE TABLE IF NOT EXISTS」と明記（本文の全文は未確認） |
| 5 | `085_create_tcg_type_master.sql`（:64） | `public.tcg_type_master` | DO ブロック（:16）で relkind を見る（:21）。`CREATE TABLE IF NOT EXISTS`（:33）・`CREATE INDEX IF NOT EXISTS`（:45）・`CREATE OR REPLACE FUNCTION`（:52）・`DROP TRIGGER IF EXISTS`→`CREATE TRIGGER`（:61-65）・`COMMENT ON`（:71）・`DROP CONSTRAINT IF EXISTS`（:82-83、to_regclass ガード）。INSERT は本文に無い（grep で当たりなし）。冪等 |
| 6 | `086_seed_additional_tcg_types.sql`（:65） | なし | 本文は `RAISE NOTICE` だけ（:14）。冪等 |
| 7 | `20260921_060000_create_product_kinds.sql`（:66） | `public.product_kinds` | `CREATE TABLE IF NOT EXISTS`（:14）・`CREATE INDEX IF NOT EXISTS`（:25）・`CREATE OR REPLACE FUNCTION`（:28）・`DROP TRIGGER IF EXISTS`（:36）→`CREATE TRIGGER`（:37）・`COMMENT ON TABLE`（:41）。冪等 |
| 8 | 直書き INSERT `public.product_kinds` 3行（:68-74） | 行 | `ON CONFLICT (code) DO NOTHING`（:73）。冪等 |
| 9 | `20260921_120000_add_products_product_kind_id.sql`（:76） | **`public.products`** に `ALTER TABLE … ADD COLUMN IF NOT EXISTS`（migration :5-6）＋ `CREATE INDEX IF NOT EXISTS`（:9） | 文は冪等。ただし ALTER TABLE なので、列が既にあっても表ロックを取る（PostgreSQL の一般仕様。この環境では実測していない＝推測）。recon.md §3 の「ALTER TABLE は ACCESS EXCLUSIVE」と同じ根拠 |
| 10 | `20260921_070000_rename_tcg_type_master_to_type_master.sql`（:77） | `public.type_master`・互換 view・trigger・`kind_id` 列 | DO ブロック2つは存在確認つき（migration :16-17・:38-39・:52-53）。`CREATE TABLE IF NOT EXISTS`（:25）・`CREATE OR REPLACE VIEW`（:41、DO ブロック内）・`CREATE OR REPLACE FUNCTION`（:48）・`DROP TRIGGER IF EXISTS`→`CREATE TRIGGER`（:58-59）・`ADD COLUMN IF NOT EXISTS`（:62）・`CREATE INDEX IF NOT EXISTS`（:65）。`COMMENT ON VIEW public.tcg_type_master`（:45）は DO ブロックの外で無条件（view で無いと失敗しうるか未確認） |
| 11 | `type_master_seed_sql()`（:79。`backend/tests/seed_data.py:73-83`） | 行 | `ON CONFLICT (code) DO NOTHING`。冪等 |
| 12 | `_rewire_keyword_fks(schema)`（:80。`backend/tests/test_tcg_work_matching_integration.py:61-143`） | 一意の schema の列の型を入れ替え、`public.products(id)` への外部キーを足す | DO ブロックの先頭で、`product_id` が既に int4 なら RETURN（:72-82）。型が違うときだけ DROP COLUMN／ADD COLUMN／ADD CONSTRAINT（:107-127）。schema 単位では冪等。ただし ADD CONSTRAINT は `public.products` への外部キーなので表ロックを伴う（推測） |
| 13 | `20260919_020000_master_ssot_public_tables.sql`（:81） | `public.units`・`unit_aliases`・`conditions`・`condition_aliases`・`tcg_note_master`・`tcg_status_master`・`tcg_product_categories`・`product_search_keywords`・`product_exclude_keywords` | `CREATE TABLE IF NOT EXISTS` と `CREATE INDEX IF NOT EXISTS`（:62・:145・:234-326）。index の追加は `pg_indexes` を見る DO ブロック（:73-83・:123-133・:159-172・:212-222）。全文が冪等 |
| 14 | `20260920_010000_phase3_fk_rewire_unit_condition.sql`（:84-86。`BEGIN;`・`COMMIT;` を取り除いて流す） | **共有 DB の `tenant_%` で `analysis_results` を持つ全 schema を回す**（migration :24-31）。さらに `public.products.product_category_id` の型変換（:238-310） | 全体に `SET LOCAL lock_timeout = '5s'`（:9）・`statement_timeout`（:10）。`ADD COLUMN IF NOT EXISTS`（:58・:153・:264）と、型が int ならスキップする分岐（:49-50・:258-259）で守られる。型が UUID のときは DROP COLUMN→RENAME→ADD CONSTRAINT を `public.products` に流す（:294-305）。試験用 `public.products` の `product_category_id` は UUID（fixtures/public_products_test.sql:15）なので、`product_db` が巻き戻すたびにこの変換が毎回走る（推測。実行は未確認） |
| 15 | `20260922_030000_product_format_game_links.sql`（:88-92） | `public.type_master`・`product_formats`・`product_format_game_links` | 全 `CREATE TABLE IF NOT EXISTS`（:9-12）・`CREATE INDEX IF NOT EXISTS`（:19-20）。冪等 |
| 16 | `20261016_190000_create_product_blank_confirmations.sql`（:88-92） | `public.product_blank_confirmations`（recon.md §3 の相手） | `CREATE TABLE IF NOT EXISTS`（:4）・`COMMENT`（:17）・`ENABLE`／`FORCE ROW LEVEL SECURITY`（:20-21）・`DROP POLICY IF EXISTS`→`CREATE POLICY`（:23-24・:28-29）。全文が冪等（`DROP POLICY IF EXISTS`＋再作成は、2回流しても壊れないが、その間だけ policy が無い瞬間がある＝推測） |

判定材料（事実）: 上の表のうち、`IF NOT EXISTS`／`CREATE OR REPLACE`／`DROP … IF EXISTS`／存在確認つき DO ブロックのいずれでも守られていない文は、#4 の表作成部分（本文を全部は読んでいない）と #10 の `COMMENT ON VIEW`（:45）のほかに見つからなかった。
別の事実: #9・#12・#14 は `public.products` に ALTER／外部キーを張る。#14 は共有 DB の他の `tenant_*` schema にも手を出す（migration :24-31）。

### A-2 巻き戻し前提・共有 DB・public の表に DDL を流す試験（`product_db` 以外）

| 試験 | DDL の行 | 巻き戻し／確定 | 札 |
|---|---|---|---|
| `backend/tests/test_tcg_distribution_pg.py` `create_schema`（:41-106）・`distribution_db`（:109-126）・:243-251 | `_PUBLIC_PRODUCTS_DDL`（:46-49）・suppliers DDL（:50-53）・`ALTER TABLE IF EXISTS public.products ADD COLUMN IF NOT EXISTS work_id`（:67）・085/086/20260921_060000/20260921_070000（:70-78）・`20260919_020000`（:83）・`CONDITION_VALUE_STATEMENTS`（:84-85）・`20260926_010000`（:99） | 1つの transaction を最後に rollback（:118・:124・:243・:249）。途中で失敗したら SAVEPOINT へ戻す（:45・:55） | 単一整数鍵の session 鍵 `pg_advisory_lock(2147483647)` を DDL の一部だけ囲む（:43・:56）。`public_bootstrap_lock`（2整数鍵 20260623/1）とは別の鍵。共有の xact 鍵は取らない |
| `backend/tests/test_value_migrations_neutralized.py` :99-121（countries）・:126-152（aggregation rules）・:157-185（type_master 085/086） | `public.countries`／`inventory_aggregation_rules`／`type_master` の migration を巻き戻す transaction の中で流す（:109-112・:136-141・:167-172）。:170 では行も消す | `trans.rollback()`（:117・:148・:183） | 先に `bootstrap_*`（自分で `public_bootstrap_lock` を取り、戻る時に放す）を呼ぶが、巻き戻す transaction の本体（:108-117 など）は札の外 |
| `backend/tests/test_product_packagings_pg.py:36-40`・`backend/tests/test_products_required_fields_pg.py:33-37` | `ALTER TABLE public.products ADD COLUMN IF NOT EXISTS …`（31列。それぞれ :39・:37） | `product_db` の transaction の中（巻き戻す） | `product_db` の共有 xact 鍵に従う |
| `backend/tests/test_product_packagings_pg.py:242` | `20260626_130000_force_rls_public_products.sql` を流す | `product_db` の transaction の中（巻き戻す） | 同上 |
| `backend/tests/test_tcg_product_list_pg.py:173` | `create_product_schema(await db.connection(), other)` | 同じ transaction の中 | 同上 |
| `backend/tests/test_tcg_condition_review.py:548` | `ALTER TABLE public.conditions ADD COLUMN IF NOT EXISTS effect …` | autocommit（:56・:63）＝巻き戻さない。DB が共有か使い捨てかは未確認 | 未確認 |

共有 DB で DDL を「確定」させる側（巻き戻さない・参考）: `backend/tests/rls_bootstrap.py` の `bootstrap_public_products`（:351-367）・`bootstrap_tenant_schema`（:370-427）・`ensure_product_packagings`（:111-149。`LOCK TABLE public.products IN ACCESS EXCLUSIVE MODE`・:139。`lock_timeout = '60s'`・:137）・`backend/tests/test_inventory_aggregated.py:167・:357`（`public_bootstrap_lock` の中で `CREATE TABLE IF NOT EXISTS public.products` ほか）・`backend/tests/test_product_blank_confirmations_pg.py:28-36・:214`。

別の接続先（共有ではない）: `backend/tests/test_tcg_work_matching_integration.py:373・:393-400`（使い捨ての別 DB・recon.md §3）。`backend/tests/test_line_conditions_value_group_rerun_pg.py:28-68` は `public.conditions` を改名するが、同ファイル :36 が「使い捨て DB」と書く（`pg` fixture の DB 名は読んでいない）。

### A 節の未確認
- `20260902_110000_tcg_classification_masters.sql` の表作成部分（:12-84）の全文。
- 実際に2回流して壊れないかは未検証（試験を回していない。上の「冪等」は文面の読みであり実測ではない）。
- #14 の phase3（`tenant_%` 全 schema を回す）が、ほかの試験の `tenant_NNN` schema に実際に触れて待ち合いを起こしているかは、DB の記録を見ていないので未確認。
- `ALTER TABLE … ADD COLUMN IF NOT EXISTS` が、列が既にあるときも ACCESS EXCLUSIVE を取るかは、この環境では実測していない（PostgreSQL の仕様に基づく推測）。
- `test_tcg_condition_review.py:548` が使う DB が共有か使い捨てか。
- `COMMENT ON VIEW public.tcg_type_master`（#10 :45）が、view でなく表だった場合に失敗するか。

---

## B 請求書の表: 札の取り方・放し方と、札の外の文

### B-1 札の実体（`backend/tests/rls_bootstrap.py`・事実）

| 札 | 行 | 接続 | 種類 | 鍵 | 放す所 |
|---|---|---|---|---|---|
| `public_bootstrap_lock` | :59-80 | 専用の接続（`admin_engine.connect()`・:62）。作業の接続とは別 | **session**（`pg_advisory_lock`・:64） | (20260623, 1)（:54-55） | `finally` で同じ接続に `pg_advisory_unlock`（:74）。失敗しても `suppress(Exception)` で握りつぶす（:73） |
| `tenant_schema_lock` | :333-348 | 専用の接続（:336） | **session** | (20260623, tenant_id)（:56・:339） | `finally` で unlock（:345）。`suppress(Exception)`（:344） |
| `bootstrap_tenant_schema` の外側の札 | :372-376 | `lock_conn`（:372） | **session** | (20260623, 0)（:374-375） | `finally` で unlock（:423-425）。`suppress(Exception)`（:422） |
| `product_db` の札（参考） | `test_tcg_product_list_pg.py:110-113` | 作業と同じ接続 | **xact・共有**（`pg_advisory_xact_lock_shared`） | (20260623, 1) | transaction の rollback で自動（:118） |

排他の session 鍵 (20260623, 1) と、共有の xact 鍵 (20260623, 1) は同じ鍵なので、`public_bootstrap_lock` を持つ間、`product_db` 系は待つ（PostgreSQL の advisory lock の仕様。実測はしていない）。

### B-2 `test_new_tenant_shape_equals_migration_and_rules_hold` の流れ（`backend/tests/test_tenant_issuer_tables_pg.py:297-340`・順に）

テナントは 963（:39-40）。
1. :300 `tenant_schema_lock(admin_engine, 963)` を取る（session・(20260623, 963)）。以降 :335 の `finally` を抜けるまで持つ。
2. :302 `bootstrap_tenant_schema(admin_engine, 963)`。中身（rls_bootstrap.py:370-427）:
   - :372-376 `lock_conn` で (20260623, 0) を session で取る。
   - :378 `public_bootstrap_lock`（(20260623, 1)・別接続）を取る。
   - :379 `admin_engine.begin()` の transaction を開き、:380-420 を同じ transaction で流す: `_bootstrap_public_shared`（:314-330）・`_ensure_public_users`（:238-290）・`_PG_AFTER_TENANTS_MIGRATIONS`（:383-386。`BEGIN;`・`COMMIT;` を取り除いて流す）・`customer_statuses_seed_sql`（:389）・`public.tenants` の INSERT（:391-415）・**`DROP SCHEMA IF EXISTS tenant_963 CASCADE`（:417）**・`create_tenant_schema`（:418）・`_TENANT_BOOTSTRAP_MIGRATIONS`（:419-420）。
   - `begin()` ブロックを抜けた所で commit（:420 の次）。その後 `public_bootstrap_lock` を放す（:378 の `async with` を抜ける）。最後に `finally` で (20260623, 0) を放す（:421-426）。
3. :304-305 `admin_engine.connect()` で `_shape` を読む（読むだけ）。**この時点で持っている札は (20260623, 963) だけ**。
4. :306-308 `before` の assert（DB に触れない）。
5. :310 `public_bootstrap_lock` を取り、:311 `admin_engine.begin()` の transaction を開く。この中:
   - :312-313 `for table in reversed(_TABLES): DROP TABLE tenant_963.<表>`。`_TABLES` は `tenant_issuer_profiles`・`tenant_invoice_payment_methods`・`tenant_invoice_payment_bank`・`tenant_invoice_payment_wise` の順（:41-46）なので、逆順では `tenant_invoice_payment_wise`→…→**`tenant_issuer_profiles`（最後）**。**この `tenant_963.tenant_issuer_profiles` を消す文は :313 で、`public_bootstrap_lock`（(20260623,1) の session 排他）の中、かつ `tenant_schema_lock`（(20260623,963)）の中にある。**
   - :314 `ALTER TABLE tenant_963.invoices DROP COLUMN issuer_region`。:316-317 `DROP FUNCTION tenant_963.<3関数>`。
   - :318-321 `_apply_migration_on_conn` を4回（`20261112_160000` を2回・`20261115_100000` を2回）。`schema_name=_SCHEMA` で 963 だけに絞る（rls_bootstrap.py:202-222）。
   - `begin()` を抜けて commit し、その後 `public_bootstrap_lock` を放す。
6. :322-324 `admin_engine.connect()` で `_shape` を読み `before == after`。**`public_bootstrap_lock` は持っていない**（(20260623, 963) だけ）。
7. :326-334 別の接続 `conn` で transaction を開き、`_check_rules`（:238-289。INSERT・外部キー違反の確認）を流して **rollback**。**`public_bootstrap_lock` は持っていない**。`_check_rules` は `public.countries`・`public.prefectures` を外部キーで指す表に INSERT する（:71-72・:257 の `23503`）。外部キー先の行ロックを取る（PostgreSQL の仕様に基づく推測）。
8. :335-338 `finally` で `public_bootstrap_lock` を取り直し、`DROP SCHEMA IF EXISTS tenant_963 CASCADE`（:338）。transaction は commit。その後 `public_bootstrap_lock`、最後に `tenant_schema_lock` を放す。

### B-3 札の外で流れる文・別の接続・放したあと（事実）

札 (20260623, 1) を持っていない区間（試験が 963 を握っている間）:
- :304-305・:322-323 `_shape` の読み（`information_schema` 等。読むだけ）。
- :326-334 `_check_rules` の DML（rollback される）。`tenant_963` の4表と、外部キー先の `public.countries`／`public.prefectures` に触れる。
- 依頼文の :309-312・:318-324 に当たる行は、実際は上のとおり :309（コメント）・:310-321（札の中）・:322-324（札の外）。

別の接続（札を持つ接続と作業の接続が別）:
- `public_bootstrap_lock`・`tenant_schema_lock` は、鍵を持つためだけの専用接続（rls_bootstrap.py:62・:336）で、作業は `admin_engine.begin()` の別接続（試験 :311・:337）。鍵の持ち主の接続は pool に属する。`finally` の unlock 失敗は `suppress`（:73・:344）なので、unlock が失敗すると session 鍵は接続が閉じるまで残る（`engine.dispose()` は :340）。失敗の起きた実例は見ていない（未確認）。

札を放したあと:
- :310-321 の transaction が commit された後、:322 の `_shape` までのあいだは (20260623, 1) を持たない。
- :335 の `finally` の `DROP SCHEMA` も `public_bootstrap_lock` の中だが、その後は鍵を放す。

recon.md §4 の相手（ADR-1061 便2-2a の public 9表の migration）を共有 DB に流すのは、`bootstrap_tenant_schema`（:383-386）が `20261112_150000_create_viewer_contract_public_tables.sql` を含む `_PG_AFTER_TENANTS_MIGRATIONS`（:41-49）を流す所だけ。その他に同 migration を読む試験は `backend/tests/ops/test_ai_cloud_views.py:747`（使い捨ての DB を `_new_db` で作る・:775）と `backend/tests/test_viewer_contract_public_tables_pg.py:32`（使い捨て DB・:83-94）。どちらも共有 DB ではない（前者は事実、後者は `conn.info.dbname` を使うことまで確認）。

`bootstrap_tenant_schema` を呼ぶ試験（35ファイルが `create_tenant_schema|bootstrap_tenant_schema` に一致。数えたのは出現数）は、どれも (20260623, 0) と (20260623, 1) の排他を取って public 側の migration を流す（rls_bootstrap.py:372-386）。したがって、public 側の migration を流す側どうしは直列になるはず。それでも相手のログに両方が出た理由は、**まだ確かめていない**。

### B 節の未確認
- run 44096043994・44203948916・44849233250・44854143246 の DB の記録で、相手（`Process N:`）が実際にどの試験・どの文だったか（今回は DB の記録を読んでいない）。
- `_check_rules`（試験 :326-334）が札の外で取る実際のロックと、`DROP TABLE tenant_963.tenant_issuer_profiles`（:313）がどの表のロックを要するか（外部キー先の `public.countries`／`public.prefectures` を含むか）は、実測していない。
- `suppress(Exception)` で握りつぶされた unlock の失敗が、実際に起きたか。
- 共有 DB で動く他の試験のうち、`public.countries`／`public.prefectures` に札なしで触るものの全数（`test_value_migrations_neutralized.py:105-121` と `test_countries_master.py:131-145` は確認したが、網羅はしていない）。

---

## C カルテ: `create_tenant_schema` の入口と、`public.users` に書く・消す試験

### C-1 「Phase 1 再設計: スタッフ・bot」の所在（事実）
- `backend/app/services/tenant.py:596`（`_TENANT_TABLES_SQL`・:194 から）。:599-619 の `{schema}.staff` は `user_id INTEGER NOT NULL UNIQUE REFERENCES public.users(id)`（:602）。つまり **`public.users` への外部キー**を持つ。
- 続く表（:628 `staff_emails` など）は `{schema}.staff` を指す。
- 同ファイルに「Phase 1 再設計」の語がほかに :550（updated_at トリガ）・:2392・:2568（staff / bots）にある。

### C-2 `create_tenant_schema`（tenant.py:2926）を実 PG に流す入口

| 入口 | 行 | 実 PG か |
|---|---|---|
| `bootstrap_tenant_schema` | `backend/tests/rls_bootstrap.py:418`（`create_tenant_schema(conn, tenant_id, admin_db=conn)`） | 実 PG。呼び元は `tenant_schema_lock`／`public_bootstrap_lock` の中（:372-420） |
| `backend/tests/test_channel_type_control.py:73` | `create_tenant_schema(db, 7, admin_db=ddl_db)` | DDL を `_execute_statements_preserving_do_blocks` の差し替えで記録するだけ（:65）。実 PG には流れないと見られる（`ddl_db` の中身は未確認） |
| `backend/tests/test_system_roles.py:182` | `create_tenant_schema(db, 7, admin_db=ddl_db)` | 同上（:172 で noop に差し替え）。実 PG には流れないと見られる |
| `backend/tests/test_check_template_needs_migration.py:38` | 同名の関数を試験内で定義（別物） | 対象外 |

`bootstrap_tenant_schema` を呼ぶ試験（出現数つき・`create_tenant_schema|bootstrap_tenant_schema` の count。`rls_bootstrap.py` 自身を含む）: test_ai_cloud_views(22)・test_customer_conversion_pg(5)・test_invoice_totals_pg(4)・test_permission_resolution_pg(4)・test_tenant_login_requests(4)・ほか各2〜3（test_assistant_karte_pg・test_calendar_categories・test_calendar_owner_color_key・test_calendar_owner_preferences_pg・test_calendar_sync_tenant_reset_pg・test_calendar_team_share・test_customer_statuses_pg・test_discord_role_link_ddl・test_duty_rules_pg・test_google_config_rls・test_lead_merge_pg・test_priority_prospects_pg_rls・test_rls_auth_audit・test_rls_bootstrap_ordering・test_rls_secretary_resolve・test_roles_system_key_ddl・test_staff_join_discord・test_staff_join_invites_rls・test_tenant_duty_rules_pg・test_tenant_issuer_tables_pg・test_tenant_payment_versioning_pg・test_tenant_user_ref_guard_pg・test_tenants_rls・ops/test_ai_job_assignments_db）。共有 DB か使い捨て DB かの仕分けは、下の表に載せた分だけ確認した。

### C-3 `public.users` へ書く・消す文と持つ札（`backend/tests` を Grep・事実）

共有 DB（`RLS_ADMIN_DATABASE_URL` の `jarvis_test_db`）に確定させるもの:

| 試験:行 | 文 | 持つ札 |
|---|---|---|
| `test_assistant_karte_pg.py:57` | 消す（`_cleanup`・:47-59。`id IN (989の2人)`） | `public_bootstrap_lock`（:50）の中 |
| `test_assistant_karte_pg.py:78` | 書く（`_setup`・:62-104。テナント 989） | `bootstrap_tenant_schema`（:69。中で (…,0)(…,1)）の後、`public_bootstrap_lock`（:70）の中。`tenant_schema_lock` は無し。**試験本体（:117 以降）は札なし**（`public_bootstrap_lock` の出現が :50・:70 だけ） |
| `test_calendar_sync_tenant_reset_pg.py:82` | 消す（`_cleanup`・:72-84） | **札なし**（`admin_engine.begin()` だけ・:75） |
| `test_calendar_sync_tenant_reset_pg.py:105` | 書く | `bootstrap_tenant_schema`（:94）の後。`public_bootstrap_lock`（:95-100）は migration 適用だけ。INSERT（:101-）は**札の外**（ブロックを抜けたあと） |
| `test_calendar_categories.py:95`・`test_calendar_owner_color_key.py:92`・`test_calendar_owner_preferences_pg.py:95`・`test_calendar_team_share.py:101` | 書く | `bootstrap_tenant_schema` の後、`public_bootstrap_lock`（それぞれ :84・:80・:83・:90）。INSERT の字下げが札のブロックの内側であることまでは見たが、ブロック全体は読んでいない |
| `test_staff_join_discord.py:587` | 消す（`_cleanup_pg`・:582-592。autocommit の psycopg2・:609。`DROP SCHEMA tenant_973`・:586、`public.tenants` の消し・:590 も同関数） | **札なし**（`shared_pg` の teardown・:615 からも呼ぶ） |
| `test_staff_join_discord.py:644` | 書く（`_prep_pg`・:620-） | `bootstrap_tenant_schema`（:625）と `public_bootstrap_lock`（:626-628）は migration 適用だけ。:633 以降は**札の外** |
| `test_tenant_user_ref_guard_pg.py:160` | 書く | `public_bootstrap_lock`（:77）・`tenant_schema_lock`（:141）・`bootstrap_tenant_schema`（:143）。:160 がどの札のブロックかは未確認 |
| `test_rls_passkey_enroll_skips.py:67` | 書く（共有 DB 既定・:24-25） | `public_bootstrap_lock`（:54） |
| `rls_bootstrap.py:282` | 書く（`_ensure_public_users`・:238-290。`ON CONFLICT DO NOTHING`・:288） | `bootstrap_tenant_schema` の中なので (…,0)＋(…,1) の中 |

共有 DB か使い捨て DB か未確認、または札が見つからなかったもの:
- `test_issue_initial_passwords.py:167`（書く。env の gate は RLS_ADMIN／RLS_TEST・:158。札なし。DB は未確認）
- `test_shifts_pg.py:57`（`ON CONFLICT DO NOTHING`。札なし。DB は未確認）
- `test_meta_channels.py:362・:383・:416`（`db_session` 経由。SQLite か PG か未確認）
- `test_export_inventory_for_sheet.py:75`（未確認）
- `ops/test_ai_job_assignments_db.py:244・:258・:347・:399-401・:415`、`ops/test_ai_ro_views.py:75`（`cluster`／`_new_db` を使う型で使い捨て DB と見られるが、この調べでは読んでいない）

使い捨て DB（`CREATE DATABASE`）で動くもの（共有 DB に影響しない）:
- `test_tenant_login_requests.py:92`（:77）、`test_tenants_rls.py:94`（:73）、`test_users_rls.py` の複数（:95）、`test_line_import_devices_pg.py:39`（:31）、`test_secretary_rules_tables_pg.py:69`・`test_secretary_voice_pg.py:45`（`conn.info.dbname` を使って「同じ使い捨て DB」へ・rules :51）。

### C-4 recon.md §4 の C への事実の当てはめ
- recon.md §3 の C の失敗試験 `test_assistant_karte_pg.py::test_read_meet_available_failed_sql_keeps_transaction_usable` は、`_setup`（:62-106）が `bootstrap_tenant_schema`（:69）で `create_tenant_schema` を流した後に、`public.users` へ INSERT する（:78）。`public.users` を指す外部キーを持つ `{schema}.staff`（tenant.py:602）の作成は、`create_tenant_schema` の一部（:2961-2969）。
- `DELETE FROM public.users` を札なしで流す試験は **`test_calendar_sync_tenant_reset_pg.py:82`**（`_cleanup`）と **`test_staff_join_discord.py:587`**（`_cleanup_pg`）。`test_assistant_karte_pg.py:57` は `public_bootstrap_lock` の中。したがって recon.md §4 の「DELETE を流す側は `test_assistant_karte_pg.py` と見られる」は、**札を持つ側であり、札なしの DELETE 側は別の2ファイル**である（DB の記録の `Process N:` を見ていないので、実際の相手が3つのうちどれかは未確認）。

### C 節の未確認
- run 44024988826・44686062120・44854143246 の DB の記録の `DELETE FROM public.users` と「Phase 1 再設計: スタッフ・bot」の migration の実際の持ち主。
- `test_calendar_*` 4本・`test_tenant_user_ref_guard_pg.py:160` の INSERT が札のブロックの内か（字下げと行番号からの読み）。
- C-3 の「共有か使い捨てか未確認」の5件の DB の向き先。
- `create_tenant_schema` を実 PG に流す入口が、`bootstrap_tenant_schema` 経由の35ファイル以外にないか（`test_channel_type_control.py:73`・`test_system_roles.py:182` の `ddl_db` の中身は読んでいない）。
- `bootstrap_tenant_schema` を呼ぶ35ファイルそれぞれの、共有 DB／使い捨て DB の仕分け（C-3 に載せた分以外）。

---

## E テナント998/999: schema を作る・消す行

### E-1 2つの試験（事実。どちらも共有 DB の `jarvis_test_db`）

| 試験 | schema を作る行 | schema を消す行 | その他（表・行） | `public_bootstrap_lock` | `tenant_schema_lock` |
|---|---|---|---|---|---|
| `backend/tests/test_rls_tenant_meta_config.py` | :88-90 `CREATE SCHEMA IF NOT EXISTS tenant_998／tenant_999`（`setup_schemas`・:77-152。module 単位・:61-69。`admin_engine.begin()`・:87） | :155-157 `DROP SCHEMA IF EXISTS tenant_998／tenant_999 CASCADE`（module の teardown・:152 の `yield` の後） | :92-98 `staff`、:100-119 `tenant_meta_config`（`public.users(id)` を外部キーで指す・:111）、RLS・policy・GRANT（:121-150）。各試験の前に :174-175 で2表の行を消す（`pg_conn`・:160-178） | **なし**（Grep で `lock` の当たりなし） | **なし** |
| `backend/tests/test_countries_master.py` | :147-150 `CREATE SCHEMA IF NOT EXISTS tenant_998／tenant_999`（`admin_engine.begin()`・:147） | **このファイルには無い**（`DROP SCHEMA` の当たりなし） | :151-176 `country_probe` の作成・RLS・policy・GRANT・行の削除と挿入 | `bootstrap_public_countries`（:86・:145）の中でだけ（rls_bootstrap.py:298-303）。:147 以降は**札なし** | **なし** |

### E-2 そのほかに 998／999 の schema を作る・消す試験（`backend/tests` を Grep）

- 998／999 の `CREATE SCHEMA`／`DROP SCHEMA` を直接書くのは上の2ファイルだけ（Grep の結果）。
- 間接: `bootstrap_tenant_schema(admin_engine, N)` は `DROP SCHEMA IF EXISTS tenant_N CASCADE` してから作る（rls_bootstrap.py:416-418）。N に 998／999 を直接書いた呼び出しは Grep で見つからなかった。N を変数で渡す呼び出しの値の全数は確認していない（`_TENANT`＝989〔test_assistant_karte_pg.py:35〕、963〔test_tenant_issuer_tables_pg.py:39〕、973〔test_staff_join_discord.py〕などは確認。998／999 でない）。
- 近い番号の別の試験（998／999 ではない）: `test_meta_channels.py:725・:755`（`tenant_997`）、`test_products_cross_tenant_fk.py:31-33`（コメントで「998／999 とぶつからない」ように `tenant_99998` を使うと書いてある）、`test_analytics_conversion_by_attribute_rls.py:25`（`tenant_998_w2_attr`）、`test_priority_prospects_pg_rls.py:198`（`tenant_998_pp_rls`）。名前が別なので schema の取り合いにはならない。

### E-3 別扱い: schema ではなく「行」「列の既定値」「名前だけ」

schema の作り消しではないので、E の重なりの対象とは分けて書く。
- 行: `backend/tests/rls_bootstrap.py:253-262` が `public.tenants` に `999 / 'tenant_999'` を `ON CONFLICT (id) DO UPDATE` で入れる（`_ensure_public_users`。`bootstrap_tenant_schema` の中）。`:286-288` が `public.users` に id 999。`test_secretary_rules_tables_pg.py:64-70・:77`・`test_secretary_voice_pg.py:42-45` は `public.tenants`／`public.users` に 998 の行を入れる（使い捨て DB・`conn.info.dbname`）。
- 列の既定値: `backend/tests/rls_bootstrap.py:268`（`public.users.tenant_id … DEFAULT 999`）、`backend/tests/conftest.py:82・:403・:433・:545` ほか多数の `tenant_id INTEGER NOT NULL DEFAULT 999`（Grep の先頭25件を見た。全数は未集計）、`test_rls_tenant_meta_config.py:95・:103` と `test_countries_master.py:154` の `DEFAULT {tid}`。
- 値としての 999／998（モックの利用者の `tenant_id = 999` など。`test_celery.py`・`test_conversations.py` ほか多数）は、DB の schema を作らない。数えていない。
- ファイルのパス名 `tenant_998/…`（`test_attachment_serve.py:67・:83・:95・:105`）はファイルシステムの名前で、DB ではない。

### E-4 事実から言えること（推測として分けて書く）
- 事実: `test_rls_tenant_meta_config.py` は module 終了時に `tenant_998`／`tenant_999` を `CASCADE` で消す（:155-157）。`test_countries_master.py` は同じ schema 名に `country_probe` を作り、消さない（:147-176）。両方とも札を持たない。
- 推測: 別の worker で `test_countries_master.py` が動いている最中に `test_rls_tenant_meta_config.py` の teardown が走ると `country_probe` が消える。逆に `test_countries_master.py` が作った `tenant_998`／`tenant_999` が残っている間は `test_rls_tenant_meta_config.py` の `CREATE SCHEMA IF NOT EXISTS` が既存の schema を再利用する。実際にこの順で落ちた記録は読んでいない。
- 事実（recon.md §1）: 落ちた試験は `test_rls_tenant_meta_config.py::test_rls_visible_when_app_tenant_id_matches`、相手は「テナント998の schema を消す文」。`DROP SCHEMA … tenant_998` を書くファイルは `test_rls_tenant_meta_config.py` 以外に Grep で見つからなかった（`bootstrap_tenant_schema(…, 998)` の変数経由の呼び出しを除く）。

### E 節の未確認
- run 44686062120 の DB の記録の「テナント998の schema を消す文」の実際の持ち主（`DROP SCHEMA` を書く試験が `test_rls_tenant_meta_config.py` 以外に見つからないため、同ファイルの teardown か、変数で 998 を渡す `bootstrap_tenant_schema` のどちらか）。
- N を変数で渡す `bootstrap_tenant_schema` 呼び出しのうち、998／999 になるものがあるか（全数未確認）。
- `test_countries_master.py` の `tenant_998`／`tenant_999` が、ほかの場所（`conftest.py` の teardown など）で消されているか。
- `conftest.py` の `DEFAULT 999` の全数、およびそれが共有 DB の PG に流れるのか SQLite だけかの仕分け。
- `test_rls_tenant_meta_config.py` の `RLS_TEST_DATABASE_URL`（アプリの役割の接続）と `_ADMIN_URL` が、CI で同じ DB を指しているかの確認（既定値は `jarvis_test_db`・:46-49。CI の環境変数は読んでいない）。
