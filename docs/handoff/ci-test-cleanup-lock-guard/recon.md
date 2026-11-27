# 共有 DB の後片付けを札の外で流す試験 — 現在地（recon）

調べた役: 調査役（Sonnet）。試験コード・製品コードは変えていない。本番に繋いでいない。DB を使う試験は回していない（読むだけ）。

## 0. 頭書き

| 項目 | 内容 |
|---|---|
| 調べた origin/main の sha | `65934286b36b3298aafc4478f0212f0aafeaa5f2`（Merge pull request #5799）。作業枝 `release/ci-test-cleanup-lock-guard` の先頭は `f937d8f53cce80ef66d84a43d5d6cd1408f7c3b3`（main との差は design.md のみ）。 |
| scan.py の流し方 | リポジトリの根から `python3 -I docs/handoff/ci-test-cleanup-lock-guard/scan.py`（ast で `backend/tests/` の .py 514 本・関数 10,808 個を読む。DB に繋がない） |
| 全件数 | **86 関数 / 60 ファイル** |
| 分類ごとの件数 | A=39 ／ B=2 ／ C=36（うち CI で動く 15・CI では skip 21）／ D=9 （合計 86） |

当たりの種類の内訳（関数数・重複あり）: public の行削除 67 ／ スキーマを消す 11 ／ TRUNCATE 9 ／ 役割を消す 2 ／ public の表を消す 1。

札の語（どれも関数の原文に無いものだけを出す）: `public_bootstrap_lock`・`pg_advisory_lock`・`pg_advisory_xact_lock`・`_public_lock`。
後片付けの文（その関数自身の本文の文字列。入れ子の関数の本文は別の関数として数える）: スキーマを消す・役割を消す（ROLE/USER/OWNED）・`public.` の表を消す・`public.` の行を消す・TRUNCATE。

### 前のテーマとの差（recon §6-5 の 53ファイル・76関数）

- 旧い条件（スキーマを消す文 か `public.` の行削除）で本台本を絞ると **ちょうど 76 関数 / 53 ファイル**＝前回と一致（事実・台本で再現）。
- 今回の 86 関数 / 60 ファイルは、旧条件に **TRUNCATE・役割を消す・public の表を消す**を足したため。増えた 10 関数は: `backend/tests/ops/test_ops_case_db.py:524`・`backend/tests/test_llm_usage_events_migration_pg.py:61`・`backend/tests/test_meta_channels.py:759`・`backend/tests/test_rls_tenant_meta_config.py:164`・`backend/tests/test_tenant_isolation_daily_check.py:199,226`・`backend/tests/test_tenant_payment_versioning_pg.py:199`・`backend/tests/test_tenant_user_ref_guard_pg.py:121`・`backend/tests/test_viewer_discord_trial.py:960,991`。このうち新しくファイルが加わるのは 7（`backend/tests/test_meta_channels.py` は旧条件でも当たっていた）。

## 1. CI の接続先（分類の前提・事実）

- 共有 DB = CI の1つの PostgreSQL `jarvis_test_db`。`RLS_ADMIN_DATABASE_URL`（jarvis）と `RLS_TEST_DATABASE_URL`（salesanchor_app）はどちらもこの DB（`.github/workflows/test.yml:240,242`）。
- `TEST_PG_URL` は CI で **未設定**（`.github/workflows/test.yml:243-249`・`backend/tests/conftest.py:22-29`）。`TEST_PG_URL` だけで動く試験は CI では skip（手元で設定すると共有 DB に当たる）。
- `DATABASE_URL` は conftest が SQLite（メモリ）に差し替える（`backend/tests/conftest.py:18`）。
- 使い捨て DB の作り方は2つ: 各試験ファイルの `_fresh()`/`_new_db()`/`scratch_db` が `CREATE DATABASE`、または `backend/tests/test_tcg_work_matching_integration.py:384-436` の `pg` fixture（`CREATE DATABASE` :398 → 終わりに `DROP DATABASE` :434）。
- 札: `public_bootstrap_lock` = `pg_advisory_lock(20260623, 1)`（`backend/tests/rls_bootstrap.py:54-80`）。`tenant_schema_lock` = `pg_advisory_lock(20260623, <tenant_id>)`（`backend/tests/rls_bootstrap.py:334-347`）は **別の鍵**。

## 2. 分類表

凡例: A=使い捨て／B=札の中（呼び出し元が持つ）／C=共有 DB で札の外（直す対象）／C-skip=C と同じだが CI では skip（`TEST_PG_URL` 未設定のため）／D=決められない。
種類の略: row=public の行削除、schema=スキーマを消す、trunc=TRUNCATE、role=役割を消す、tbl=public の表を消す。

### 2-1. A（39）

| file:line | 関数 | 当たった文 | 分類 | 根拠 file:line |
|---|---|---|---|---|
| ops/test_ai_job_assignments_db.py:239 | test_d_history_is_append_only | row,trunc | A | `db` fixture が `CREATE DATABASE`（同:102）。文は `_fails`（失敗する前提）と使い捨て DB 内 |
| ops/test_ai_job_assignments_db.py:289 | test_f_get_ai_assignment_reads_choice_and_raises_when_missing | row | A | 同:102（`db`）、削除は `db.cursor()`（:309） |
| ops/test_ai_job_assignments_db.py:393 | test_h_history_names_fall_back | row | A | 同:102、削除は `db.cursor()`（:415） |
| ops/test_ops_case_db.py:524 | test_t6_app_cannot_change_read_count | trunc | A | `pg` は `_new_db`（:135 → :91 `CREATE DATABASE`）。TRUNCATE は拒否の確認（:529 `_denied`） |
| test_channel_masters_shared_pg.py:159 | test_deleting_tenant_removes_its_rows_in_both_tables | row | A | `_fresh()` が `CREATE DATABASE`（:58）、使用 :162 |
| test_discord_config_rls.py:259 | test_update_delete_other_tenant_rows_affect_nothing | row | A | `_fresh()`（:124）、使用 :262 |
| test_discord_server_records_rls.py:213 | test_update_delete_other_tenant_rows_affect_nothing | row | A | `_fresh()`（:88）、使用 :216 |
| test_google_webhook_subscriptions_rls.py:216 | test_update_delete_other_tenant_rows_affect_nothing | row | A | `_fresh()`（:74）、使用 :219 |
| test_inventory_distribution_rows_pg.py:206 | test_b5_item_id_lookup_includes_inactive_posts_with_current_rows_but_the_plain_list_does_not | row | A | `pg` fixture（:27 の import → test_tcg_work_matching_integration.py:398）。削除は `pg[0]`（:254） |
| test_inventory_movements_rls.py:186 | test_update_delete_other_tenant_rows_affect_nothing | row | A | `_fresh()`（:67）、使用 :189 |
| test_llm_usage_events_migration_pg.py:61 | test_extraction_shadow_run_id_has_no_fk | tbl | A | `pg` fixture（:22 の import → test_tcg_work_matching_integration.py:398）。表を消すのは `pg` の接続（:69-71） |
| test_meta_channels.py:759 | pg_conn_scopes | trunc | A | 当たりは docstring の語（:760）。実際の削除は `tenant_997` の表の行削除（:764）で、台本の対象外（§4 参照） |
| test_paypal_regtoken_rls.py:211 | test_other_tenant_and_no_context_cannot_write | row | A | `_fresh()`（:61）、使用 :215 |
| test_paypal_regtoken_rls.py:273 | test_own_tenant_can_insert_update_delete | row | A | 同:61、使用 :276 |
| test_paypal_regtoken_rls.py:342 | test_tenant_delete_cascades_to_both_tables | row | A | 同:61、使用 :345 |
| test_product_format_game_links_pg.py:23 | fmt_pg | row | A | `edit_pg`（test_tcg_product_detail_pg.py:106）→ `pg`（test_tcg_work_matching_integration.py:398） |
| test_product_format_game_links_pg.py:165 | test_db_rejects_removing_link_in_use | row | A | 同上（`fmt_pg`）。削除は FK 違反で拒否される前提（:170） |
| test_product_format_game_links_pg.py:179 | test_physical_delete_of_format_in_use_is_rejected | row | A | 同上。拒否される前提（:187） |
| test_product_format_game_links_pg.py:294 | test_create_ignores_legacy_type_master_id_and_does_not_return_it | row | A | 同上。削除は `fmt_pg["connection"]`（:307） |
| test_rls_tenant_meta_config.py:164 | pg_conn | trunc | A | 当たりは docstring の語（:172）。実際の削除は `tenant_946/947` の表の行削除（:177-178）で台本の対象外（§4 参照） |
| test_secretary_rules_tables_pg.py:200 | test_app_role_cannot_delete | row | A | `pg` fixture（:17 の import → test_tcg_work_matching_integration.py:398）。削除は拒否の確認（:211 `42501`） |
| test_tcg_condition_review.py:181 | set_max_age_hours | row | A | `pg` fixture が `CREATE DATABASE`（同:60） |
| test_tcg_import_progress_pg.py:396 | test_later_tcg_schema_provisioning | schema | A | `pg` fixture が `CREATE DATABASE`（同:59）。消すのは使い捨て DB 内の `tenant_873`（:409） |
| test_tenant_budget_settings_rls.py:238 | test_update_delete_other_tenant_rows_affect_nothing | row | A | `_fresh()`（:79）、使用 :241 |
| test_tenant_deletion.py:276 | test_physical_delete_success | schema | A | SQLite のメモリ（conftest.py:18）と mock（同:293-294）。文字列を読むだけ（:322-323） |
| test_tenant_service.py:72 | test_named_dollar_tag_function_body | row | A | SQL を文字列として分割関数へ渡すだけで流さない（同:77-92） |
| test_tenants_rls.py:205 | test_tenant_context_and_no_context_cannot_write | row | A | `_fresh()`（:73）、使用 :209 |
| test_tenants_rls.py:239 | test_operator_context_can_insert_update_delete | row | A | 同:73、使用 :242 |
| test_tenants_rls.py:258 | test_operator_delete_cascades_to_children | row | A | 同:73、使用 :261 |
| test_users_rls.py:224 | test_no_context_cannot_write | row | A | `_fresh()`（:95）、使用 :228 |
| test_users_rls.py:259 | test_tenant_context_writes_only_own_rows | row | A | 同:95、使用 :263 |
| test_users_rls.py:309 | test_operator_context_can_write_any_tenant | row | A | 同:95、使用 :312 |
| test_users_rls.py:335 | test_operator_delete_tenant_cascades_to_users | row | A | 同:95、使用 :338 |
| test_viewer_billing_form_pg.py:139 | test_deleting_viewer_deletes_profile | row | A | `pg` fixture（:30 の import → test_tcg_work_matching_integration.py:398） |
| test_viewer_contract_public_tables_pg.py:173 | test_public_tables_rls_and_viewer_delete_sets_null | row | A | `pg` fixture（:25 → :398）。アプリ接続も `conn.info.dbname` の同じ使い捨て DB（:82-84） |
| test_viewer_discord_trial.py:960 | test_cli_set_config_upserts_single_row | trunc | A | `pg` fixture（:29 → test_tcg_work_matching_integration.py:398）、`_prep`（:771） |
| test_viewer_discord_trial.py:991 | test_list_viewers_returns_channel_url | trunc | A | 同上 |
| test_viewer_password.py:89 | execute | row | A | 偽の session クラスの `execute` が文字列で振り分けるだけ（同:89-123）。DB に繋がない |
| test_viewer_signup.py:78 | execute | row | A | 同上（偽の session・同:78-103） |

### 2-2. B（2）

| file:line | 関数 | 当たった文 | 分類 | 根拠 file:line |
|---|---|---|---|---|
| test_permission_resolution_pg.py:56 | _remove_test_tenant_rows | schema,row | B | 呼び出し元 :98-100 と :241-243 がどちらも `public_bootstrap_lock(admin_engine)` の中（外側に `tenant_schema_lock`）。接続は `RLS_ADMIN_DATABASE_URL`（:35） |
| test_rls_auth_audit.py:54 | _remove_test_tenant_rows | schema,row | B | 呼び出し元 :69-71 と :81-83 がどちらも `public_bootstrap_lock(admin_engine)` の中。接続は `_ADMIN_URL`（:26 付近の `RLS_ADMIN_DATABASE_URL`） |

### 2-3. C（CI で動く・15）— 直す対象

| file:line | 関数 | 当たった文 | 分類 | 根拠 file:line | 直す案（どの札で囲むか） |
|---|---|---|---|---|---|
| test_adr119_backfill_source_guard.py:99 | _drop_schema | schema | C | 共有 DB（`PG_URL`＝`RLS_ADMIN_DATABASE_URL` :25、engine :45-49）。呼び出し :151,:188,:222 に札なし。固定名 `test_adr119_*` | `public_bootstrap_lock(engine)` で3つの後片付けを囲む |
| test_analysis_error_report_tables_rls.py:51 | _cleanup | row | C | `ADMIN_PG_URL`（:12-15）。`_setup` の札は migration だけ（:46-47）。呼び出し :120 は札の外 | `_cleanup` 内を `public_bootstrap_lock(admin_engine)` で囲む |
| test_analytics_conversion_by_attribute_rls.py:110 | test_conversion_by_attribute_rls_team_and_mine_under_tenant_006 | schema | C | `ADMIN_PG_URL`（:19・engine :111）。`DROP SCHEMA` は固定名 `tenant_006_w2_attr`/`tenant_998_w2_attr`（:24-25,:264-265）。札なし | 後片付け（:250-265）を `public_bootstrap_lock(admin_engine)` で囲む |
| test_google_config_rls.py:67 | _cleanup | row | C | `ADMIN_PG_URL`（:26-28）。`_setup` で札のブロック（:60-62）の**外**から呼ぶ（:63）。`_teardown`（:78-80）も札なし | `_cleanup` 内を `public_bootstrap_lock(admin_engine)` で囲む |
| test_inventory_aggregated.py:526 | seed_draft_four | row | C | `_PG_URL`（:25）の共有 DB。兄弟の fixture は終わりの削除を札の中で流す（:357）が、こちら（:569-572）は札なし | :569-572 を `public_bootstrap_lock(eng)` で囲む（:357 と同じ形） |
| test_meta_channels.py:718 | pg_setup_scopes_schema | schema | C | `_ADMIN_URL`（:687-690）＝CI の共有 DB。`DROP SCHEMA tenant_997`（:755）に札なし。作る側（:724-750）も札なし | 作成（:724）と削除（:754）を `public_bootstrap_lock(pg_admin_engine_for_scopes)` で囲む |
| test_ops_incident_tables_rls.py:52 | _cleanup | row | C | `ADMIN_PG_URL`（:13-15）。札は `_setup` の migration だけ（:47-48） | `_cleanup` 内を `public_bootstrap_lock(admin_engine)` で囲む |
| test_ops_router.py:144 | _clear_control | row | C | `ADMIN_PG_URL`（:17-19）。札は `env` fixture の migration だけ（:94）。`ops_control` を消す（:148） | `_clear_control` 内を `public_bootstrap_lock(env.admin_engine)` で囲む |
| test_product_blank_confirmations_pg.py:56 | _drop_product | row | C | `ADMIN_PG_URL`（:12-14）。`public.products` の1行削除（:60）。札なし | `_drop_product` 内を `public_bootstrap_lock(admin_engine)` で囲む |
| test_products_cross_tenant_fk.py:57 | setup_cross_tenant_tables | schema | C | `_ADMIN_URL`（:25-28）＝CI の共有 DB。`DROP SCHEMA tenant_99998`（:67,:103）。札なし | 作成〜削除を `public_bootstrap_lock(admin_engine)` で囲む |
| test_rls_bootstrap_ordering.py:29 | test_rls_bootstrap_schema_and_migration_share_one_transaction | schema | C | `ADMIN_PG_URL`（:17）。`DROP SCHEMA tenant_9951`（:97）は `tenant_schema_lock`（:33-92）の**外**の finally（:93-99） | :95-97 を `public_bootstrap_lock(admin_engine)` で囲む |
| test_staff_join_invites_rls.py:64 | _cleanup | row | C | `ADMIN_PG_URL`（:21）。`_setup` で札の外から呼ぶ（:60、札は :57-59）。`_teardown`（:74-76）も札なし | `_cleanup` 内を `public_bootstrap_lock(admin_engine)` で囲む |
| test_super_admin_unit_ignore_phrases.py:77 | pg_client | row | C | `ADMIN_PG_URL`（:20）。終わりの削除（:97-102）に札なし | :97-102 を `public_bootstrap_lock(admin_engine)` で囲む |
| test_tenant_schema_integrity.py:98 | test_schemas | schema | C | `_ADMIN_URL`（:54-57）＝CI の共有 DB。`DROP SCHEMA`（:104-105,:124-125）固定名 `test_schema_integrity_a/b`。札なし | 作成（:103）と後片付け（:123）を `public_bootstrap_lock(admin_engine)` で囲む |
| test_value_migrations_neutralized.py:157 | test_type_master_migrations_do_not_reinsert_deleted_rows | row | C | `ADMIN_PG_URL`（:17）の共有 DB。`public.type_master` の行削除（:170）と 085/086 の流し直し（:171-172）を札の外で流す（取引は rollback :183）。`bootstrap_public_products`（:165）は内部で札を取る | :166-183 を `public_bootstrap_lock(engine)` で囲む |

### 2-4. C-skip（21）— CI では skip。`TEST_PG_URL` を共有 DB に向けると C と同じ

全関数が `TEST_PG_URL` だけで動く（`os.getenv("TEST_PG_URL")`）。CI では未設定のため skip（§1）。後片付けは `public.` の行削除で札なし。

| file:line | 関数 | 当たった文 | 分類 | 根拠 file:line | 直す案 |
|---|---|---|---|---|---|
| test_export_inventory_for_sheet.py:147 | _cleanup | row | C-skip | `TEST_PG_URL`（:22-30）、engine :42 | `public_bootstrap_lock(engine)` で `_cleanup` 内を囲む |
| test_inventory_search.py:50 | seed_search_dataset | row | C-skip | `TEST_PG_URL`（:29-35）、後片付け :153-163 | :153-163 を `public_bootstrap_lock(engine)` で囲む |
| test_inventory_search_perf.py:51 | bulk_seed | row | C-skip | `TEST_PG_URL` かつ `RUN_PERF`（:22-36）、削除 :88-91 | :88 以降を `public_bootstrap_lock(engine)` で囲む |
| test_phase_gate.py:68 | _cleanup | row | C-skip | `TEST_PG_URL`（:18-24）、削除 :72-75 | `_cleanup` 内を `public_bootstrap_lock(engine)` で囲む |
| test_phase_gate.py:78 | test_get_phase_returns_a_when_no_row | row | C-skip | 同上、削除 :89-93 | 同上 |
| test_phase_gate.py:179 | test_set_phase_upserts | row | C-skip | 同上、削除 :192 付近 | 同上 |
| test_product_masters.py:71 | test_product_attribute_masters_crud_round_trip | row | C-skip | `TEST_PG_URL`（:53-58）、削除 :83-85,:104-106 | 削除2か所を `public_bootstrap_lock(engine)` で囲む |
| test_purge_expired_inventory_offers.py:31 | test_purge_deletes_only_expired_offers | row | C-skip | `TEST_PG_URL`（:18-22,:28）、削除 :100-107 | :100-107 を `public_bootstrap_lock` で囲む（同期の engine のため同期版の札が要る【推測】） |
| test_super_admin_aliases.py:36 | test_supplier_aliases_unique_constraint | row | C-skip | `TEST_PG_URL`（:17-23）、削除 :60-63,:89-92 | 削除を `public_bootstrap_lock(engine)` で囲む |
| test_super_admin_aliases.py:96 | test_csv_import_xmax_counts_inserted_vs_skipped | row | C-skip | 同上、削除 :129-132,:184-187 | 同上 |
| test_super_admin_aliases.py:191 | test_supplier_aliases_different_language_allowed | row | C-skip | 同上、削除 :212-215,:239-242 | 同上 |
| test_super_admin_dex.py:34 | test_pokemon_dex_update_round_trip | row | C-skip | `TEST_PG_URL`（:15-21）、削除 :48-51,:71 | 同上 |
| test_super_admin_knowledge.py:94 | test_create_then_select_then_delete_rule | row | C-skip | `TEST_PG_URL`（:19-25）、削除 :125 | 同上 |
| test_super_admin_phase_switch.py:113 | test_get_phase_returns_a_default | row | C-skip | `TEST_PG_URL`（:19-25）、削除 :141-144 | 同上 |
| test_super_admin_phase_switch.py:148 | test_put_phase_to_a_succeeds | row | C-skip | 同上、削除 :179-182 | 同上 |
| test_super_admin_phase_switch.py:186 | test_put_phase_to_b_blocked_v1_2 | row | C-skip | 同上、削除 :223-226 | 同上 |
| test_super_admin_phase_switch.py:230 | test_put_phase_invalid_value_400 | row | C-skip | 同上、削除 :247-250 | 同上 |
| test_super_admin_phase_switch.py:254 | test_rbac_non_super_admin_403 | row | C-skip | 同上、削除 :276-279 | 同上 |
| test_super_admin_suppliers.py:66 | test_supplier_discord_routing_unique | row | C-skip | `TEST_PG_URL`（:20-26）、削除 :115-121 | 同上 |
| test_super_admin_suppliers.py:159 | _cleanup_suppliers | row | C-skip | 同上、削除 :162 | `_cleanup_suppliers` 内を囲む |
| test_super_admin_tcg.py:46 | test_tcg_series_crud_round_trip | row | C-skip | `TEST_PG_URL`（:15-21）、削除 :58-61,:86 | 同上 |

### 2-5. D（9）— 決められない

| file:line | 関数 | 当たった文 | 分類 | 理由・根拠 file:line | 札の案 |
|---|---|---|---|---|---|
| test_analysis_error_report_tables_rls.py:147 | test_event_update_and_delete_denied_even_with_operator_flag | row | D | 共有 DB（:12-15）。当たりは**拒否される前提の DELETE**（:155、`42501` を確認 :163）で後片付けではない | 台本から外す／分類 `denied_check`（流しても成功しない文）を新設。札は不要の見込み |
| test_ops_incident_tables_rls.py:178 | test_delete_denied_even_with_operator_flag | row | D | 共有 DB（:13-15）。拒否される前提の DELETE（:190、`42501` :191）。取引は rollback（:193） | 上と同じ |
| test_permissions_rls.py:64 | test_permissions_writes_denied_without_operator_flag | row | D | 共有 DB（:11-13）。`DELETE ... WHERE id > 0` は行が見えず0行の確認（:91-92）で rollback（:94）。後片付けではない | 上と同じ |
| test_lead_merge_pg.py:322 | env | trunc,row | D | 共有 DB（:39）。`tenant_schema_lock(engine, _TENANT_ID)`（:341）の中で、テナント専用スキーマの TRUNCATE（:353）と `public.registration_tokens` の行削除（:355）。札は別の鍵（`public_bootstrap_lock` ではない） | `tenant_schema_lock` を「同じ鍵」と認めるか決める。認めないなら :351-355 を `public_bootstrap_lock(engine)` でも囲む |
| test_tenant_user_ref_guard_pg.py:121 | env | trunc | D | 共有 DB（:44）。`tenant_schema_lock`（:141）の中でテナント専用スキーマを TRUNCATE（:167-169）。`public_bootstrap_lock` は別関数（:77） | 上（lead_merge）と同じ |
| test_tenant_payment_versioning_pg.py:199 | _check_rules | trunc | D | 呼び出し元 :302 は `tenant_schema_lock`（:305）の中。TRUNCATE は拒否される前提（:292-294）で取引は rollback（:341）。`public_bootstrap_lock` は finally の削除だけ（:345） | 上と同じ（かつ `denied_check`） |
| test_priority_prospects_pg_rls.py:66 | test_priority_prospects_pg_rls_all_requirements | schema | D | 共有 DB（:38）。`@pytest.mark.skip`（:62-64、flaky）で**無条件に skip**。`tenant_schema_lock`（:111）の中で `DROP SCHEMA tenant_998_pp_rls`（:291） | 分類 `skipped` を認める。再開するなら `public_bootstrap_lock` で囲む |
| test_tenant_isolation_daily_check.py:199 | test_b2_bypass_role | role | D | `scratch_db` は使い捨て DB（:162）だが、`DROP ROLE`（:217）の役割はクラスタ共通。名前は uuid で一意（:200） | 使い捨て DB 扱い（A）＋理由つき、または分類 `cluster_role_unique` を新設。札は不要の見込み |
| test_tenant_isolation_daily_check.py:226 | test_b3_plain_role | role | D | 同上（:162,:254、名前 :227） | 同上 |

## 3. 分類ごとの件数

| 分類 | 件数 |
|---|---|
| A 使い捨て | 39 |
| B 札の中 | 2 |
| C 札の外（CI で動く） | 15 |
| C-skip 札の外（CI では skip） | 21 |
| D 決められない | 9 |
| 合計 | 86 |

設計 G4（共有 DB・札の外が0件）の対象は、C の15件＋C-skip の21件＝36件。D の9件は設計側の判断待ち（`tenant_schema_lock` を札と認めるか／拒否確認の DELETE と skip・役割の扱い）。

## 4. 台本の取りこぼし・限界（事実と未確認）

- 台本が数えるのは `public.` を付けた行削除・スキーマ/役割を消す・TRUNCATE・`public.` の表を消すだけ。`public.` を付けない行削除は件数外。参考として `public.` 無しの行削除だけの関数が 40 件ある（`docs/handoff/ci-test-cleanup-lock-guard/scan.py` の出力 `# 参考` 行。**中身は Read していない＝未確認**）。例: `backend/tests/test_meta_channels.py:764`（`tenant_997` の表）・`backend/tests/test_rls_tenant_meta_config.py:177-178`（`tenant_946/947` の表）は共有 DB で札の外だが、台本の対象外。
- 札の有無は、その関数自身の原文に札の語があるかで判定。呼び出し元が札を持つ場合（§2-2 の B）は台本では当たるため、分類で B に振った。入れ子の関数が外側の札の中にあるものは、今回の当たりには出なかった（未確認の取りこぼしは無いと断言できない）。
- 呼び出し元の札を追ったのは §2-2 の2件と、§2-3 の `_cleanup` 系（呼び出し行を確認したもの）だけ。C-skip 21件の関数本体は、後片付けの行と接続先（`TEST_PG_URL`・engine）を Read で確認したが、試験全体の流れまでは読んでいない。
- 実際の CI で並行実行時にどれが衝突するかは**未確認**（本テーマは調べるだけで試験を回していない）。

## 5. 既存の見張り `_REVIEWED` の形と、新しい見張りに使えるか（3行以内）

`backend/tests/test_tenant_loop_migration_guard.py` の `_REVIEWED` は `dict[ファイル名, (分類, 理由, frozenset[移行名])]`（分類は `scoped`/`own_database`/`text_only`/`pg_url_only`）で、`_actual()` と `_expected()` の差を「分類表に無い」「実物に無い」の両方向で落とす（:373-408）。
新しい見張りも同じ2方向比較が使える。ただし鍵を「ファイル名」から「ファイル::関数名」に変え（この86件は同一ファイル内で関数名の重複なし＝台本で確認）、集合は「当たった文の種類」か「呼び出し元 file:line」に替える。
分類は `own_database`（`CREATE DATABASE` の存在確認 :418-421）・`pg_url_only`（`TEST_PG_URL` の確認 :424-426）・`text_only` をそのまま流用でき、`locked`（札の中）・`fixed`（直した）・`denied_check`（D の案）を足す形が自然（案であり実装は未確認）。

## 6. 結果（実装役・Sonnet・設計 §4〜§6 に従う）

### 6-1. 直した38件（file:関数）— すべて `public_bootstrap_lock` で囲んだ（backend/tests/ 配下）

形: 消す文（と同じ接続の commit）を `async with public_bootstrap_lock(engine), engine.begin() as conn:` の中に入れた。後片付けの関数が `conn` を受けていたもの2つ（`_drop_schema`・`_cleanup_suppliers`）は、`engine` を受けて自分で札と `engine.begin()` を開く形に変え、呼び出し元（adr119 4か所・suppliers 3か所）を合わせた。消す文の中身・順は変えていない。

C・CI で動く（15）
- test_adr119_backfill_source_guard.py:`_drop_schema`（呼び出し4か所も変更）
- test_analysis_error_report_tables_rls.py:`_cleanup`
- test_analytics_conversion_by_attribute_rls.py:`test_conversion_by_attribute_rls_team_and_mine_under_tenant_006`
- test_google_config_rls.py:`_cleanup`
- test_inventory_aggregated.py:`seed_draft_four`
- test_meta_channels.py:`pg_setup_scopes_schema`（作成と削除の両方）
- test_ops_incident_tables_rls.py:`_cleanup`
- test_ops_router.py:`_clear_control`
- test_product_blank_confirmations_pg.py:`_drop_product`
- test_products_cross_tenant_fk.py:`setup_cross_tenant_tables`（作成と削除の両方）
- test_rls_bootstrap_ordering.py:`test_rls_bootstrap_schema_and_migration_share_one_transaction`（`tenant_schema_lock` の外の finally だけ）
- test_staff_join_invites_rls.py:`_cleanup`
- test_super_admin_unit_ignore_phrases.py:`pg_client`
- test_tenant_schema_integrity.py:`test_schemas`（作成と削除の両方）
- test_value_migrations_neutralized.py:`test_type_master_migrations_do_not_reinsert_deleted_rows`（`bootstrap_public_products` は札の外で先に呼び、消す・流し直す・rollback を札の中に）

C-skip・CI では skip（21）
- test_export_inventory_for_sheet.py:`_cleanup`
- test_inventory_search.py:`seed_search_dataset`
- test_inventory_search_perf.py:`bulk_seed`
- test_phase_gate.py:`_cleanup`・`test_get_phase_returns_a_when_no_row`・`test_set_phase_upserts`
- test_product_masters.py:`test_product_attribute_masters_crud_round_trip`（削除2か所）
- test_purge_expired_inventory_offers.py:`test_purge_deletes_only_expired_offers`（同期 engine。同じ接続で `pg_advisory_lock(20260623, 1)`（`_PUBLIC_BOOTSTRAP_LOCK_NAMESPACE`・`_KEY` を import）を取り、finally で `pg_advisory_unlock`）
- test_super_admin_aliases.py:`test_supplier_aliases_unique_constraint`・`test_csv_import_xmax_counts_inserted_vs_skipped`・`test_supplier_aliases_different_language_allowed`
- test_super_admin_dex.py:`test_pokemon_dex_update_round_trip`
- test_super_admin_knowledge.py:`test_create_then_select_then_delete_rule`
- test_super_admin_phase_switch.py:`test_get_phase_returns_a_default`・`test_put_phase_to_a_succeeds`・`test_put_phase_to_b_blocked_v1_2`・`test_put_phase_invalid_value_400`・`test_rbac_non_super_admin_403`
- test_super_admin_suppliers.py:`test_supplier_discord_routing_unique`・`_cleanup_suppliers`（呼び出し3か所も変更）
- test_super_admin_tcg.py:`test_tcg_series_crud_round_trip`

D のうち札で囲んだ（2）
- test_lead_merge_pg.py:`env`（`tenant_schema_lock` の内側で `public_bootstrap_lock`。順は tenant → public）
- test_priority_prospects_pg_rls.py:`test_priority_prospects_pg_rls_all_requirements`（`DROP SCHEMA` の finally。skip のまま）

呼び出し元の確認（設計 §4-3 (5)）: `_cleanup`・`_drop_product`・`_clear_control` などの呼び出し元を Grep で全部読み、いずれも `public_bootstrap_lock` の外から呼ばれていた（既に札の中なら BLOCKED のところ、該当なし）。`backend/tests/test_ops_incident_tables_rls.py`・`backend/tests/test_ops_router.py` の一部は別の鍵 `ops_control_lock`（鍵 1012002）の中から `_cleanup`/`_clear_control` を呼ぶ。順は ops_control_lock → public_bootstrap_lock で、逆に取る所はこの2ファイルに無い（Grep で確認）。

### 6-2. 分類表の件数（`_REVIEWED`・backend/tests/test_shared_db_cleanup_lock_guard.py）

| 分類 | 件数 |
|---|---|
| own_database | 35（recon §2-1 の DB を使う33＋test_tenant_isolation_daily_check.py の2） |
| text_only | 6（test_meta_channels.py:pg_conn_scopes・test_rls_tenant_meta_config.py:pg_conn・test_tenant_deletion.py:test_physical_delete_success・test_tenant_service.py:test_named_dollar_tag_function_body・test_viewer_password.py:execute・test_viewer_signup.py:execute） |
| caller_locked | 2 |
| tenant_locked | 1 |
| denied_check | 4 |
| 合計 | 48（= 86 − 直した38） |

（件数は `_REVIEWED` を ast で数えた実測: own_database 35・text_only 6・caller_locked 2・tenant_locked 1・denied_check 4＝48。recon §2-1 の A 39件は own_database 33＋text_only 6。）

### 6-3. 確かめ（生出力の要点）

(1) `python3 -I docs/handoff/ci-test-cleanup-lock-guard/scan.py`（見張りの試験ファイルを足した後）
```
# 読んだ .py: 515 ファイル / 関数: 10815
# 参考（件数外）: public. 無しの行削除だけの関数 40 件
# 全件数: 48 関数 / 34 ファイル
```
表の件数 48 と一致（86 − 38 = 48）。

(2) 変えた .py（29本）と新しい見張りを `python3 -m py_compile` → `COMPILE_OK`。

(3) 指示どおりの `python -m pytest tests/test_shared_db_cleanup_lock_guard.py -q -p no:cacheprovider` は、このクラウドの環境では動かなかった（`python` に pytest が無い・`pytest` は `pytest_asyncio` と pyproject の addopts（xdist・cov）が無い）。設定と conftest を外した形 `pytest -c /dev/null --rootdir=. --noconftest tests/test_shared_db_cleanup_lock_guard.py -q -p no:cacheprovider` では `4 passed`。CI の形（`-n --dist=loadfile --cov`）での実行は未確認。DB を使う試験（直した38件の中身）は、このクラウドに PostgreSQL が無いため回していない＝動きは未確認（C-skip 21件は CI でも skip）。

(4) わざと札なしの後片付け関数（一時ファイル backend/tests/test_zz_tmp_probe_unlocked.py。確かめた後に消した）を足すと、見張りが落ちた:
```
FAILED tests/test_shared_db_cleanup_lock_guard.py::test_every_shared_db_cleanup_is_classified
該当: test_zz_tmp_probe_unlocked.py::_tmp_probe_cleanup（delete_public_rows）
1 failed, 3 passed
```
一時ファイルは消し、`git status` に残っていないことを確認（戻した後は `4 passed`）。

(5) `git diff --name-only origin/main...HEAD` は backend/tests/ と docs/handoff/ci-test-cleanup-lock-guard/ と台帳（.claude-pipeline/active-work.d/）だけ（commit 後に再確認）。製品コード・migrations・CI 設定・rls_bootstrap.py・conftest.py は変えていない。
