# CI 試験のたまたま落ちる3件の直し（2026-11-21）

状態: 設計案作成済み（Opus）。PO「1」（2026-11-21・試験が落ちる原因を別の作業として調べて直す）に基づく。試験コードだけ。製品コード・DB・workflow・migration は触らない。

対象ADR: ADR-1052（unmask の試験）・ADR-1078（予定のカルテの試験）・ADR-1079（発行元の表の試験）。試験が守る中身は変えず、試験どうしのぶつかりだけを直す。recon は §2 に含める（別の recon.md は作らない）。

## 1 目的と成功条件

| 基準 | 検証方法 |
|---|---|
| K1 `backend/tests/ops/test_unmask_http.py::test_other_db_failures_are_503_without_value` が request_id の乱数に左右されない | 試験の中の「漏れていない」確認の文字が 16 進の文字（0-9a-f）とハイフンだけで出来ていないことを diff で読む。手元ではなく CI の pytest で 6 件とも緑 |
| K2 `backend/tests/test_tenant_issuer_tables_pg.py::test_new_tenant_shape_equals_migration_and_rules_hold` の表を消して作り直す区間が public_bootstrap_lock の中で流れる | diff を読む。札の順番は tenant_schema_lock → public_bootstrap_lock（決まりどおり tenant → public） |
| K3 `backend/tests/test_assistant_karte_pg.py` の public.users を書く・消す区間（_setup の入れる区間・_cleanup）が public_bootstrap_lock の中で流れる | diff を読む |
| K4 この PR の CI で pytest-run-internal が緑 | gh pr checks |
| K5 マージ後、main の test.yml の次の 5 回で上の 2 本のデッドロックが 0 件 | gh run view --log-failed を grep "deadlock detected" |

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

## 3 変更（試験コードだけ）

### 3-1 backend/tests/ops/test_unmask_http.py
- `:33` の既定のエラー文の印を、16 進に無い文字を含む印に変える: `k='abc'` → `k='leak-qz'`
- `:217-218` の `"abc"` を `"leak-qz"` に変える。
- 触らない: RID・他の試験・本体 `ops` のコード。

### 3-2 backend/tests/test_tenant_issuer_tables_pg.py
- `:310` の `async with admin_engine.begin() as conn:`（DROP と移行 4 回の区間）を `async with public_bootstrap_lock(admin_engine):` で包む。中身は変えない。
- 札の順番: 外側に tenant_schema_lock（既存）、内側に public_bootstrap_lock。
- 触らない: _shape・_check_rules・片付けの区間。

### 3-3 backend/tests/test_assistant_karte_pg.py
- `_setup` の users と tenant_google_calendar_config を書く `async with admin_engine.begin()` 区間を、移行と同じ `async with public_bootstrap_lock(admin_engine):` の中へ移す（1 つの札の中で 移行 → 書き込み）。
- `_cleanup` の本体を `async with public_bootstrap_lock(admin_engine):` で包む。
- `bootstrap_tenant_schema` は札の外のまま（自分で札を取るため。`backend/tests/rls_bootstrap.py:124` の注意）。

## 4 代わりの案と選んだ理由
- 落ちた試験を流し直すだけ（retry）: 原因が残り、main で 30 回中 6 回落ちる状態が続く。不採用。
- 試験を 1 つのワーカーに寄せる（xdist の group）: CI 時間が延びる。既存の決まり（札で直列化）と違う形になる。不採用。
- 採用: 先例と同じ public_bootstrap_lock。札の順番の決まりを守る。

## 5 弊害と対処
- public の札を持つ時間が延び、他の試験の待ちが少し増える。区間は DROP 数本と移行 4 回・INSERT 数本で短い。K4 で CI の時間を前の回（10 分 5 秒前後）と比べる。
- 札の中で bootstrap_* を呼ぶと二重取りで止まる。3-3 で bootstrap_tenant_schema を外に置くことで避ける。

## 6 戻し方
- PR を revert する（試験コードだけ）。

## 7 外部・過去事例の参照と我々への応用
- 外部事例: 不要。PostgreSQL の advisory lock は既存の試験の仕組みをそのまま使い、新しい技術を入れないため。
- 過去事例: 先例の直し（commit ab8d83f6f「3 本の試験の片付けを public_bootstrap_lock の中へ」・bb38918d7「roles移行試験の片付けDROPを public_bootstrap_lock の中で流す」）。bb38918d7 は commit の本文に「共有の準備（public移行）と片付けのDROP SCHEMAが互いのロックを待つデッドロックを避けるため」とある。ab8d83f6f は準備と片付けを public の札の中へ移した（札の順は tenant → public）。我々への応用: 今回の 2 本も同じ型（札の外の DROP・書き込みと、別の試験の public 移行がぶつかる）なので、同じ直し方を当てる。

## 8 維持の仕組み
- 先例の記録（共有 DB の試験で DROP や移行を足すときは札の順番と範囲をそろえる）に今回の 2 本を足す。
- K5 で main の 5 回を数える。
