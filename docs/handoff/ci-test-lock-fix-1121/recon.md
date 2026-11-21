# recon: CI 試験のたまたま落ちる3件（2026-11-21）

設計: docs/handoff/ci-test-lock-fix-1121/design.md

既存 ADR の検索: 試験ファイルの冒頭が指す ADR-1052（backend/tests/ops/test_unmask_http.py:1）・ADR-1078（backend/tests/test_assistant_karte_pg.py:1）・ADR-1079（backend/tests/test_tenant_issuer_tables_pg.py:5）。docs/adr に public_bootstrap_lock・advisory lock を扱う ADR は無い（git grep -il origin/main -- docs/adr で 0 件）。

## 2 現在地（事実・すべて origin/main と CI の生記録）

### 2-1 test_unmask_http（PR の 2 回目の実行・run 44882846668 attempt 2）
- 6 件すべて落ちた。落ちた確認は `backend/tests/ops/test_unmask_http.py:218` `assert "abc" not in audit.sent[0]`。
- 監査の行: `request_id=91dee4e0-c6dd-431f-abc5-69d471fc4237 ... sqlstate=57014`。乱数の request_id（`:19` `RID = str(uuid.uuid4())`）に "abc" が入っていた。
- "abc" は `:33` のにせのエラー文 `k='abc'` が漏れていないかを確かめるための印。印が 16 進の文字だけなので、乱数とたまたま一致する。

### 2-2 test_tenant_issuer_tables_pg（main run 44854143246 と 44849233250 の 2 回とも）
- DB の記録（run 44854143246）:
  - Process 7029: `DROP TABLE tenant_963.tenant_issuer_profiles` が relation 674987 の AccessExclusiveLock を待つ（相手 6986）
  - Process 6986: `migrations/20261112_150000_create_viewer_contract_public_tables.sql`（public の 9 表を作る）を流し、relation 675203 の ShareUpdateExclusiveLock を待つ（相手 7029）
- 試験の DROP 区間 `backend/tests/test_tenant_issuer_tables_pg.py:310-319` は tenant_schema_lock の中だが public_bootstrap_lock の外。消す表は public.countries・public.prefectures を参照する（`migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql:46,48`）。
- 片付けの `DROP SCHEMA`（`:335-337`）はすでに public_bootstrap_lock の中。
- run 44849233250 も同じ試験・同じ型（AccessExclusiveLock 待ち・相手 6908）。

### 2-3 test_assistant_karte_pg（main run 44854143246）
- Process 7357: `public.users` の行を消す文（`_cleanup`・`backend/tests/test_assistant_karte_pg.py:47-58`）が relation 675162 の RowExclusiveLock を待つ（相手 7371）
- Process 7371: 「Phase 1 再設計: スタッフ・bot」の移行（public.users を参照する表を作る）を流し、relation 674848 の ShareRowExclusiveLock を待つ（相手 7357）
- `_setup` の users を入れる区間（`:73` から）と `_cleanup` は public_bootstrap_lock の外。移行の区間（`:69-72`）だけが中。

### 2-4 PR の 1 回目（run 44882846668 attempt 1）
- 87% の行で F が 1 つ（08:07:09Z）。91% の行（08:08:11Z）のあと出力が止まり、08:16:25Z に 15 分の時間切れ（`.github/workflows/test.yml:125` timeout-minutes: 15）で止められた。
- 止まっている間（08:08:03〜）の DB の記録は checkpoint 以外 0 行。止められたので F の試験の名前は記録に出ていない。【未確認】F の名前と、止まった理由。

### 2-5 main の直近 30 回（test.yml・2026-11-21 02:07Z まで）
- success 23・failure 6・cancelled 1。直近 2 回が failure（上の 2-2・2-3）。

### 2-6 既存の記録
- 先例: 片付けの DROP を public_bootstrap_lock の中へ入れた直し（2026-11-05・2026-11-06 合流）。札の順番は tenant → public。
- 同じ 3 件を扱う作業の記録は見つからない（`git grep` origin/main の .claude-pipeline と docs/handoff で試験名を検索）。


### 2-7 止まり（91% のあと 15 分の時間切れ）の原因（2026-11-21 14:20Z 追記）
同じ形の止まりを 3 回の CI で読んだ（生記録は手元の作業場所に保存）。3 回とも同じ順で起きている。
| CI の回 | ブランチ | deadlock の時刻（UTC） | 消す側 | 札を外す文の失敗 |
|---|---|---|---|---|
| 44882846668 attempt 1 | release/adr-1063-bin8-docs | 08:07:08.461 [5265] | [5262] public.suppliers を id で消す文 | 08:07:08.466 [5265] `SELECT pg_advisory_unlock($1, 0)` → current transaction is aborted |
| 44910038503 | release/migration-backup-guard-5-4 | 13:48:18.413 [5318] | [5315] 同じ文 | 13:48:18.418 [5318] 同じ |
| 44911665488 | release/ci-test-lock-fix-1121（この PR） | 14:09:53.054 [5563] | [5559] 同じ文 | 14:09:53.060 [5563] 同じ |
- 負けた側（5265・5318・5563）の文は 062（`migrations/062_create_inventory_movements_and_budget.sql`）の冒頭。062 を共有 DB で流すのは `backend/tests/rls_bootstrap.py:22`（_PG_BOOTSTRAP_MIGRATIONS）。
- `SELECT pg_advisory_unlock($1, 0)` を出すのは `backend/tests/rls_bootstrap.py:366-422` の bootstrap_tenant_schema だけ（`git grep -n "pg_advisory_lock" backend/tests` で (namespace, 0) はこの 1 か所）。札 (20260623, 0) を、移行を流す transaction と同じ接続 `conn` で取っている（:368-372）。移行が deadlock で止められると transaction が失敗の状態になり、finally の札を外す文（:417-421）も拒まれる。拒まれた失敗は `suppress(Exception)` で黙って捨てられる。
- PostgreSQL の決まり（公式「13.3.5 Advisory Locks」、Context7 /websites/postgresql で確認）: session 単位の札は、明示に外すか接続が終わるまで持たれ続け、transaction の巻き戻しでは外れない。よって (20260623, 0) が外れず、次に bootstrap_tenant_schema を呼ぶ別の担当が待ち続ける。`pg_advisory_lock` に待ちの上限は付いていない（lock_timeout の既定は 0＝上限なし、同じ公式文書）。
- 3 回とも deadlock の約 1 分後から pytest の出力が止まり、時間切れまで DB の記録は checkpoint と少数の行だけ（今回: 14:11:06 より後は 0 行）。
- 消す側: CI では TEST_PG_URL を設定していない（`.github/workflows/test.yml:238-247`）。TEST_PG_URL が無いと skip される test_inventory_search.py・test_super_admin_suppliers.py・test_purge_expired_inventory_offers.py は CI で流れない。CI で public.suppliers を id で消すのは `backend/tests/test_inventory_aggregated.py:356-368` の片付けだけ（`_PG_URL = TEST_PG_URL or RLS_ADMIN_DATABASE_URL`、:25）。この片付けは public_bootstrap_lock の外。同じ fixture の準備（:167）は札の中。
- 同じ形の潜み（今回は観測なし）: `backend/tests/test_tcg_product_list_pg.py:50-55` も札を transaction の接続で取る。例外のとき外す文に届かない。今回の対象外とし、記録だけ残す。
