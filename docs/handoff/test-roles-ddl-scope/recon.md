# recon: 試験どうしのぶつかり（roles の移行試験が他の試験のテナントに触れて落ちる）

- 基準: `origin/main` 335389444（2026-11-05 23:08 JST）。worktree `~/worktrees/salesanchor/release-test-roles-ddl-scope`
- 生出力: `/tmp/CC報告ファイル/test-race/`（81〜100）・`/tmp/CC報告ファイル/services-reset/70-・71-`

## 1. 観測した不具合（事実）

| 時刻（UTC） | どこで | 出来事 | 根拠 |
|---|---|---|---|
| 2026-11-05 13:16:31.348 | CI の PostgreSQL ログ | `ALTER TABLE tenant_991.roles ADD COLUMN IF NOT EXISTS system_key TEXT` が失敗 | `/tmp/CC報告ファイル/services-reset/70-pytest-internal-5164.txt:16005` |
| 2026-11-05 13:17:16 | pytest | `FAILED tests/test_roles_system_key_ddl.py::test_new_tenant_has_system_key_and_migration_is_idempotent - ... schema "tenant_991" does not exist` | 同 `:1711` |
| 2026-11-05 13:29:18.298 | CI の PostgreSQL ログ | 同じ ALTER TABLE tenant_991.roles が失敗（2回目） | `/tmp/CC報告ファイル/services-reset/71-pytest-internal-5164-rerun.txt:16029` |
| 2026-11-05 13:29:56 | pytest | 同じ試験が同じ理由で FAILED | 同 `:1711`、`:761` |

- 3回目の実行で緑（docs の PR は 2026-11-05 23:08 JST にマージ済み）。
- 2026-11-03 の run 41587942918 でも同じ文言が出た（42本のログを走査、`schema "tenant_... does not exist"` は tenant_991 の15件だけ。`/tmp/CC報告ファイル/test-race/72-`〜`78-`）。
- 記録が無いこと: tenant_991 を DROP した文そのものは PostgreSQL ログに出ていない（DDL ログを取っていない）。DROP したのが誰かは、次の 2 のコードから決めた。

## 2. 仕組み（コードの事実）

- CI は全試験を1つの DB（jarvis_test_db）で4つのワーカーに分けて回す: `backend/pyproject.toml:65` の addopts `-n auto --dist=loadfile`、`.github/workflows/test.yml:236`（RLS_ADMIN_DATABASE_URL）。`TEST_PG_URL` は CI に無い（`.github/workflows/test.yml:239-241` のコメント）。
- 落ちた試験 `backend/tests/test_roles_system_key_ddl.py`:
  - `:23` `_TENANT_ID = 997`、`:24` `_SCHEMA = f"tenant_{_TENANT_ID:03d}"`
  - `:69` `async with tenant_schema_lock(admin_engine, _TENANT_ID):`（997 の札だけを持つ）
  - `:74-75` 移行 SQL をそのまま2回流す `await conn.exec_driver_sql(migration_sql)`
  - `:96` 後片付けで `DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE`（札の外）
- 流す移行 `migrations/20261005_150000_add_roles_system_key.sql` は `nspname ~ '^tenant_\d+$'` で**全部の数のテナント**を回る（選ぶ条件はこのファイルに1回。`/tmp/CC報告ファイル/test-race/81-regex-check.txt`「matches: 1」）。
- 同じ時に別ワーカーで `backend/tests/test_rls_auth_audit.py`（`_TENANT_ID = 991`）が、札 991 の中で tenant_991 を作って DROP する（`/tmp/CC報告ファイル/test-race/83-991.txt`）。
- `tenant_schema_lock`（`backend/tests/rls_bootstrap.py:308`）は番号ごとの札。997 と 991 は互いを待たない。→ roles の移行が tenant_991 を見つけた直後に tenant_991 が消され、ALTER が失敗する。
- 既にある直し方（正本）: `backend/tests/rls_bootstrap.py:154-196`
  - `:156` `_TENANT_LOOP_SELECTOR_RE`、`:157-172` `_TENANT_LOOP_MIGRATIONS`（14件、ファイル名→選ぶ条件の回数）
  - `:175-182` `_scope_tenant_migration` が条件の後ろに `AND nspname = '<schema>'` を足し、1つのテナントだけにする。回数がずれたら止める
  - `:198-208` `_apply_migration_on_conn(conn, filename, *, schema_name=None)` が上を通して asyncpg の生接続で流す
  - lead_merge・calendar の試験はこれを使っている（`backend/tests/test_lead_merge_pg.py`、`backend/tests/test_calendar_sync_tenant_reset_pg.py`）

## 3. 同じ種類の危険の全数点検（事実）

全テナントを回す移行（広い定義 `(nspname|schema_name|schemaname|table_schema)\s*(~|LIKE|~~)\s*'^?tenant_`）は 116 本。名前で参照する試験ファイルは 22（`/tmp/CC報告ファイル/test-race/100-crosscheck-head.txt`）。

| 種類 | ファイル | 共有 DB で全テナントを回すか |
|---|---|---|
| 1つのテナントに絞って流す | rls_bootstrap.py・test_lead_merge_pg.py・test_calendar_sync_tenant_reset_pg.py | 回さない |
| 使い捨て DB を作る（`CREATE DATABASE`、または test_tcg_work_matching_integration から借りる） | test_leads_assignment_opened_at_pg・test_suppliers_rls・test_tcg_condition_review・test_tcg_extraction_record_pg・test_tcg_import_progress_pg・test_tcg_product_list_pg・test_tcg_sold_out_results・test_tcg_work_comparison_pg・test_tcg_work_matching_integration | 回さない（別 DB） |
| 文字として読むだけ・SQLite・コメント | conftest.py（`:214`・`:590` コメント）・condition_value_columns.py（`:6` コメント）・test_inbox_new_assignment_badge（SQLite でわざと落とす）・test_value_migrations_neutralized（実行するのは全テナントを回らない4本）・test_value_migrations_neutralized_3c・test_lead_merge_pg の drop_deals/drop_customers（`:76-79` 文字の照合だけ） | 回さない |
| TEST_PG_URL があるときだけ動く（CI では skip） | test_inventory_sprint8_migrations（069）・test_inventory_visibility_permissions（063、`:19-25`） | CI では回さない。TEST_PG_URL を足すと回る＝潜在 |
| **絞らずに共有 DB で流す** | **test_roles_system_key_ddl.py** | **回す（今回の原因・ただ1つ）** |

## 4. テナント番号の重なり（事実・潜在）

`/tmp/CC報告ファイル/test-race/84-`・`91-`・`92-`:
- 997: test_roles_system_key_ddl（札あり）と test_meta_channels（`:719-755` 札なしで CREATE/DROP SCHEMA tenant_997）。
- 998: test_permission_resolution_pg（札あり）と test_rls_tenant_meta_config（`:79-157` 札なしで tenant_998/999 を作って消す）。
- まだ CI で落ちた記録は無い（42本のログで tenant_997/998 の「does not exist」は0件）。
- 試験・移行のどこにも出てこない番号: 989・992・994・995（`995` は `backend/tests/test_tcg_keyword_matching.py` の行番号 9995 と `backend/tests/test_rls_bootstrap_ordering.py:28` の `tenant_9951` だけで、テナント 995 としては0件）。

## 5. ADR の検索
- `git grep -il "tenant_schema_lock\|xdist\|loadfile\|_TENANT_LOOP_MIGRATIONS" -- docs/adr` → 0件。`docs/adr/FEATURE-INDEX.md` に「xdist / 並列 / テナント番号」0件。
- 追加の検索（2026-11-06）: `git grep -l "system_key" -- docs/adr` → ADR-147（roles.system_key の決まり）。全テナントへ移行を回す決まりは ADR-034（`docs/adr/ADR-034-tenant-migration-automation.md`）。どちらも今回は変えない（試験の流し方だけを直す）。
- 試験の土台だけの直しで製品の判断を含まないため、新しい ADR は作らない。
