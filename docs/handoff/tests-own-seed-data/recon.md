# recon：試験が自分で seed を用意する（ADR-1007 段2）

この文書は何か（1行）: 試験と CI が「値を書く migration」のデータに頼っている箇所と、直したあとの試験結果を、行番号つきの事実だけで記録したもの。

親: ADR-1007（PR #3985、main にマージ済み dee9b0705。migration は構造の変更だけ・1回だけ流す）。設計: docs/handoff/tests-own-seed-data/design.md
実測時の origin/main: 9a2b06ecd（2026-10-06）。以下の「変更前」の行番号はこの SHA のもの。
既存 ADR の検索: 機能キーワード（migration seed、countries、type_master、inventory_aggregation）で docs/adr/ と docs/adr/FEATURE-INDEX.md を引いた結果、直接の ADR は ADR-155（migration で値を操作しない）と ADR-1007（PR #3985、main にマージ済み dee9b0705）。

## 1. CI で動く PG 試験と動かない PG 試験

- .github/workflows/test.yml:222 RLS_TEST_DATABASE_URL、:224 RLS_ADMIN_DATABASE_URL を設定。TEST_PG_URL は設定しない（:227-231 のコメント「CI workflow に TEST_PG_URL を明示 export すると、以前は skip されていた inventory 系テストが PG migration / seed 未投入で大量に失敗するため…」）。
- backend/pyproject.toml:65 addopts は「-n auto --dist=loadfile --cov=app --cov-report=term-missing --cov-fail-under=60」（ファイル単位で worker に振り分け。ファイル同士の実行順は保証されない）。
- backend/tests の 49 ファイルが URL 系の環境変数を読む。TEST_PG_URL だけで skip を決めるファイルは 20、RLS_ADMIN／RLS_TEST／併用で動くファイルは 24、PG 試験でないものは 5。
- CI の実測（run 37278803676、head 10550ab42、test.yml の pytest-run-internal）: 4506 passed, 76 skipped。skip の内訳は未確認（-rs なし）。

## 2. 変更前の依存（file:line、origin/main 9a2b06ecd）

| # | 依存 | 場所 |
|---|---|---|
| 1 | countries 190 行を、migration を流した結果から読む | backend/tests/test_countries_master.py:139（_apply_migration）、:198（同）、:158・:240・:250（190 の assert） |
| 2 | 国の loader が 2 か所にある | backend/tests/conftest.py:118、backend/tests/test_countries_master.py:54 |
| 3 | public.countries の 190 行を数えるが、migration を自分では流さない（他ファイルが先に流した状態に頼る） | backend/tests/test_lead_country_control.py:151-154。同ファイル :84-86 は tenant_006 が無いと pytest.skip |
| 4 | 集計ルール 4 行を、migration を流した結果から読む | backend/tests/test_inventory_aggregation.py:13（MIGRATION_FILE）、:155（skipif は TEST_PG_URL だけ）、:157 |
| 5 | 同じ migration を流して表を作る | backend/tests/test_inventory_aggregated.py:230（:25 は TEST_PG_URL か RLS_ADMIN_DATABASE_URL） |
| 6 | 集計ルールが空なら、アプリは既定に戻らない | backend/app/services/inventory_aggregated_service.py:142-143、backend/app/services/inventory_aggregation.py:383-399（空なら []）、:78-82（既定 4 行は rules 省略時の引数 :309 でだけ使う） |
| 7 | type_master の行を 085・086 から得る | backend/tests/rls_bootstrap.py:18-19、backend/tests/test_products_tcg_type_fk.py:36-37、backend/tests/test_tcg_distribution_pg.py:69-70、backend/tests/test_tcg_product_list_pg.py:58-59、backend/tests/test_tcg_condition_review.py:60-61、backend/tests/test_tcg_work_matching_integration.py:231-232。rename は rls_bootstrap.py:31、test_products_tcg_type_fk.py:48、test_tcg_distribution_pg.py:72、test_tcg_product_list_pg.py:71、test_tcg_condition_review.py:63、test_tcg_work_matching_integration.py:244 |
| 8 | PC_BOX・PC_SINGLE を、テナント側 migration の seed からコピー | backend/tests/test_tcg_work_matching_integration.py:248-252 |
| 9 | SQLite の試験 DB はすでに自前で seed | backend/tests/conftest.py:718（国）、:732（type_master） |

## 3. 実施した変更（ブランチ release/tests-own-seed-data、コミット 4db82a964 と b3c370ce7）

- 新規 backend/tests/seed_data.py: 国・type_master の loader（conftest から移動）、国・type_master・集計ルール・商品区分（PC_BOX・PC_SINGLE）の seed SQL（すべて ON CONFLICT で冪等）。
- backend/tests/rls_bootstrap.py: seed_type_master、bootstrap_public_countries、bootstrap_inventory_aggregation_rules を追加。_bootstrap_public_shared と bootstrap_public_products で type_master を seed。
- 国: test_countries_master.py と test_lead_country_control.py が bootstrap_public_countries を使う。
- 集計ルール: test_inventory_aggregation.py の skipif を「TEST_PG_URL か RLS_ADMIN_DATABASE_URL」に変更。test_inventory_aggregated.py が bootstrap_inventory_aggregation_rules を使う。
- type_master と PC_BOX: test_products_tcg_type_fk.py、test_tcg_condition_review.py、test_tcg_distribution_pg.py、test_tcg_product_list_pg.py、test_tcg_work_matching_integration.py に、rename の後で seed を足した。
- migrations/ と本番は変更していない（migration の本文を変えるのは段3）。新規の CREATE TABLE は無い。

## 4. 試験結果（生出力の末尾）

### 4-1 SQLite・DB なし（コマンド: PYTHONPATH にリポジトリ直下を指定し、backend で pytest -n0 --no-cov -q）
対象: test_seed_data、test_countries_master、test_inventory_aggregation、test_inventory_aggregated、test_rls_bootstrap_ordering、test_lead_country_control
- 基準（origin/main 9a2b06ecd、test_seed_data を除く 5 ファイル）: 16 passed, 9 skipped, 32 warnings in 4.47s
- 変更後（b3c370ce7）: 23 passed, 9 skipped, 32 warnings in 4.70s

### 4-2 ローカルの使い捨て PostgreSQL 16（CI と同じ環境変数。GITHUB_ACTIONS=true、RLS_ADMIN_DATABASE_URL、RLS_TEST_DATABASE_URL。TEST_PG_URL は未設定）
対象 12 ファイル: test_countries_master、test_lead_country_control、test_inventory_aggregation、test_inventory_aggregated、test_rls_bootstrap_ordering、test_products_tcg_type_fk、test_tcg_distribution_pg、test_tcg_product_list_pg、test_tcg_condition_review、test_tcg_work_matching_integration、test_tcg_completion_safety、test_tcg_product_roundtrip_pg（変更後は test_seed_data を加えた 13 ファイル）
- 基準: 6 failed, 206 passed, 2 skipped, 268 warnings in 88.39s
- 変更後: 6 failed, 214 passed, 1 skipped, 277 warnings in 98.04s
- 失敗した 6 本は、基準と変更後で同じ名前:
  - tests/test_rls_bootstrap_ordering.py::test_rls_bootstrap_schema_and_migration_share_one_transaction[None]
  - tests/test_rls_bootstrap_ordering.py::test_rls_bootstrap_schema_and_migration_share_one_transaction[tenant_9951]
  - tests/test_products_tcg_type_fk.py::test_products_tcg_type_validation_and_fk_enforcement_under_tenant_006
  - tests/test_tcg_condition_review.py::test_raw_update_waits_for_review_source_lock
  - tests/test_tcg_work_matching_integration.py::test_condition_note_lock_timeout
  - tests/test_tcg_work_matching_integration.py::test_interrupted_recovery_lock_timeout_and_settings
- 差の内訳: passed が 206 → 214（+8）。新規の test_seed_data の 7 本と、test_inventory_aggregation の PG 試験（基準では TEST_PG_URL 未設定で skip、変更後は RLS_ADMIN_DATABASE_URL で実行）の 1 本。skipped が 2 → 1。
- 6 本の失敗の原因は調べていない（基準でも同じ名前で失敗するため、本 PR の変更とは別）。未確認。
- 注: 同じ変更後の試験を、ディスク満杯の状態で 1 度実行したところ、PG の「ディスクの空き容量をチェックしてください」で 36 errors が出た。その実行の結果は採用していない。上の変更後の値は、空き容量を確かめて新しいクラスタで再実行したもの。

### 4-3 順序依存の解消（test_lead_country_control）
対象: test_channel_type_control と test_lead_country_control のみ（test_countries_master を流さない）。
- 基準（origin/main 9a2b06ecd）: 1 failed, 4 passed（FAILED tests/test_lead_country_control.py::test_lead_country_backfill_and_rls_readability_under_tenant_006）
- 変更後: 5 passed

### 4-4 他の検査
- scripts/check_test_schema_dup.py（BASE_SHA=origin/main、HEAD_SHA=HEAD）: 「テストへの新規スキーマ複製なし(pass)」
- ruff check（変更した 7 ファイル）: All checks passed。test_inventory_aggregated.py:368 の I001 は origin/main でも同じ指摘（本 PR の変更ではない）。

## 5. 未確認
- 76 件の skip の内訳（CI）。
- 4-2 の 6 本の失敗の原因。
- CI（RLS_ADMIN_DATABASE_URL を持つ test.yml）での変更後の結果。
- 全件の pytest スイート（関連する PG ファイルだけを実行した）。
- 20260902_110000 が入れる他の行（MK001・DIV01 など）に依存する試験。本 PR では PC_BOX・PC_SINGLE だけを試験側に持たせた（test_tcg_work_matching_integration.py:1400、:1513 付近）。
