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

