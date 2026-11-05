# recon: 共有の札の外で DROP している試験 3 本

- 基準: `origin/main` 3977ffd1e（worktree `release/test-drop-public-lock`）
- 生の行番号一覧: `/tmp/CC報告ファイル/test-roles-ddl-scope/recon3-lines.txt`
- 前の便: PR #5169（`docs/handoff/test-roles-ddl-scope/design.md` §11）。roles 試験の DROP を `public_bootstrap_lock` の中へ入れて、デッドロック 0 件にした

## 既存 ADR・仕様の検索
- `git grep -il "advisory_lock\|public_bootstrap_lock" docs/adr/` → 0 件。試験の札の決まりは ADR でなく `backend/tests/rls_bootstrap.py` と前の便の design.md にある
- `docs/adr/FEATURE-INDEX.md` に「試験の共有 DB」の項目は無い

## 札（advisory lock）の実物
- `backend/tests/rls_bootstrap.py:39-41` 名前空間 20260623、public の札は鍵 1
- `backend/tests/rls_bootstrap.py:44-54` `public_bootstrap_lock`（自分の接続で `pg_advisory_lock(20260623, 1)`）
- `backend/tests/rls_bootstrap.py:309-323` `tenant_schema_lock`（鍵 = テナント番号）
- `backend/tests/rls_bootstrap.py:345-353` `bootstrap_tenant_schema` は鍵 0 → 鍵 1 の順で取る
- 決まり: 札は tenant → public の順。tenant の表は public.users・public.products・public.permissions を外部キーで指す（migrations 002・062）。DROP SCHEMA CASCADE はその外部キーを外すので、public の表に鍵がかかる。public の札の外で流すと、同時に動く bootstrap とデッドロックする（#5169 で観測）

## 対象 1: `backend/tests/test_rls_auth_audit.py`
- `:22` import は `bootstrap_tenant_schema, tenant_schema_lock` だけ
- `:30` テナント 991（他の試験で 991 を使う箇所は 0 件）
- `:54-62` `_remove_test_tenant_rows`: `:56` DROP SCHEMA CASCADE、`:59` public.tenant_settings の DELETE、`:62` public.tenants の DELETE
- `:65-81` 自動の準備: `:68` tenant の札の中で `:70` と `:81` から `_remove_test_tenant_rows` を呼ぶ。public の札は取っていない

## 対象 2: `backend/tests/test_discord_oauth_rls.py`
- `:28` テナント 99（`tenant_099`）。他の試験で使う箇所は 0 件。この中の試験 2 本は同じファイルなので、`--dist=loadfile` で同じワーカーが順に流す
- `:33-105` `_bootstrap_minimal_schema`: `:41` `CREATE TABLE IF NOT EXISTS public.tenants`、public.tenants への INSERT、`tenant_099.audit_logs` の作成。札は無い
- `:120`・`:182` 準備の呼び出し。`:153-161`・`:208-216` の finally で DROP SCHEMA（`:156`・`:210`）と public.tenants の DELETE（`:158`・`:212`）。札は無い
- `tenant_099.audit_logs` は public への外部キーを持たない（`:65-75`）。DROP で public の表に鍵はかからない。ただし `CREATE TABLE IF NOT EXISTS public.tenants` と DELETE は public の表を触るので、public の札の外にある

## 対象 3: `backend/tests/test_permission_resolution_pg.py`
- `:25-33` import は `public_bootstrap_lock`・`tenant_schema_lock` を含む
- `:37` テナント 998
- `:56-64` `_remove_test_tenant_rows`: `:58` DROP、`:61`・`:64` DELETE
- `:96` tenant の札 → `:98-99` で `_remove_test_tenant_rows`（public の札の外）→ `:101` public の札
- `:237-242` finally: tenant の札も public の札も出た後で `_remove_test_tenant_rows` と public.permissions の DELETE

## テナント 998 の重なり
- `backend/tests/test_rls_tenant_meta_config.py:88` と `backend/tests/test_countries_master.py:148` が tenant_998 / tenant_999 を札なしで作る。`backend/tests/test_rls_tenant_meta_config.py:156` は札なしで `DROP SCHEMA tenant_998 CASCADE`
- 3 本目が 998 を使う限り、別のファイル（別のワーカー）が同じスキーマを消しうる
- 空いている番号: `grep -rnE "994" backend/tests` → 番号としての使用は 0 件（`backend/tests/test_tcg_analysis_review_sql_snapshot.py:53` の hash の中の文字だけ）
- 3 本目の利用者番号 9801〜9805 は、他のファイルで 0 件

## 観測していないこと
- この 3 本が CI でデッドロックを起こした記録は、main の直近 14 回では 0 件（`/tmp/CC報告ファイル/test-roles-ddl-scope/main-deadlock-history.txt`）。危険は形の上の話で、起きた回数は 0 回
