<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — migration-churn-guard（ADR-1005 Stage 0 ①②）

**仕事名**: migration-churn-guard
**日付**: 2026-10-06
**対象ADR**: ADR-1005（docs/adr/ADR-1005-migration-run-once-ledger.md）Stage 0 ①②
**担当**: Sonnet（実装）。設計は Opus（docs/handoff/migration-runner-redesign/design.md §2 Stage 0）で確定済み。本カードは①②の実装と③の調査のみ。

---

## 0. 一言でいうと（PO 向け）

ADR-1005 の Stage 0 は3項目。①「後で消す列を前の手順で足す」組を CI で検出する仕組みを新規作成、②同一ファイルの二重登録（`scripts/run_all_migrations.sh` の旧536行）を削除、③全件ドライランの対象範囲が狭い理由を履歴で確認する（調査のみ、ワークフロー変更なし）。①②を実装し、③は事実のみ確認した。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/run_all_migrations.sh:530` | `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql` 登録（1回目・残す） |
| `scripts/check-migration-registration-exists.sh:1` | 既存の登録存在チェックの書式（bash・`--mode host\|container`） |
| `scripts/tests/test-migration-registration-exists.js:1` | 既存チェックの回帰テストの書式（node・spawnSync・一時ファイル） |
| `scripts/check-dangling-routes.js:1` | 既存の Node.js 製チェックスクリプトの書式（JSDoc・モジュール分割・テスト用環境変数） |
| `.github/workflows/migration-guard.yml:119` | チェック2（新規 migrations/*.sql 登録確認）: `if: steps.detect_sql.outputs.new_sql == 'true'` によるPR差分ベースのトリガー書式 |
| `.github/workflows/migration-guard.yml:656` | 旧ファイル末尾（チェック9の直後）。本PRで新ステップ（チェック10）を追加した位置 |
| `migrations/20260917_020000_supplier_ssot_migration.sql:92` | `EXECUTE format('ALTER TABLE %I.supplier_channels DROP COLUMN supplier_id', _schema);` という実在する動的SQLの書式（EXECUTE format + %I + 単一引用符） |
| `migrations/20260901_090000_add_condition_resolution_columns.sql:71` | `EXECUTE format($q$ALTER TABLE %I.conditions ADD COLUMN search_kw TEXT NOT NULL DEFAULT ''$q$, _schema);` という dollar-quote 内の実在するADD COLUMN書式 |
| `scripts/migrate_inventory_sprint1.py:52` | run_py が参照する .sql ファイル名のリスト書式（`"056_add_suppliers_type_and_promote_public.sql"` など、スラッシュなし＝migrations/ 相対） |
| `scripts/migrate_meta.py:60` | run_py が `MIGRATIONS_DIR / "012_add_meta_tenant_tables.sql"` で単一ファイルを読む書式 |
| `migrations/20260604_060000_add_lost_reason_code.sql:36` | `tenant.deals.lost_reason_code` の ADD（`ALTER TABLE %I.deals ADD COLUMN IF NOT EXISTS lost_reason_code VARCHAR(30)`）。直前に「deals テーブルが存在しないスキーマはスキップ」の CONTINUE ガードあり（22-29行目） |
| `migrations/20260613_020000_funnel_close_reasons.sql:106` | 同カラムの DROP（`ALTER TABLE %I.deals DROP COLUMN IF EXISTS lost_reason_code`） |
| `migrations/20260729_043520_drop_deals.sql:1` | 全テナントの `deals` テーブル本体を永久 DROP（本番適用済み・2026-07-29）。以後 `deals` を再作成する migration は repo 内に0件（`grep -rl "CREATE TABLE.*\.deals\b" migrations/` 結果0件） |
| `migrations/20260909_000000_public_products_phase2b_columns.sql:33` | `tcg_uuid` ADD が `DO $guard_tcg_uuid$ IF EXISTS(tcg_uuid) OR NOT EXISTS(work_id AS integer) THEN ADD ... ELSE RAISE NOTICE` でガード済み |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:48` | 同ガードの2つ目の出現（同一ロジック） |
| `migrations/20260919_010000_master_ssot_work_id_recast.sql:1` | `work_id` を UUID→INTEGER に永久変換（上記ガードの ELSE 分岐が以後恒常的に成立する根拠） |
| `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:7` | `public.products.tcg_uuid` の DROP（ADR-1002 Phase C） |
| `migrations/20260924_110000_fix_analysis_run_snapshots_unit_condition_type.sql:19` | `analysis_run_snapshots.unit_id`/`condition_id` の DROP→ADD（型変換）が `IF EXISTS(... data_type='uuid') THEN DROP+ADD ELSE RAISE NOTICE` でガード済み（drop-then-add 警告クラス、exit に影響しない） |
| `.github/workflows/migration-test.yml:1660` | 全件ドライラン1周目の対象フィルタ `^migrations/0|^migrations/2026060[4-9]|^migrations/2026061|^migrations/2026062` |
| `.github/workflows/migration-test.yml:1695` | 同2周目の対象フィルタ（1660と同一） |

---

## ①②の実装内容

- 新規: `scripts/check-migration-column-churn.js`（Node.js、`scripts/check-dangling-routes.js` と同じ書式）。`scripts/run_all_migrations.sh` の登録順に沿って migrations/*.sql と run_py が読む .sql を走査し、同一 (table, column) で ADD の後に DROP が来る組を検出する。EXECUTE format 内の `%I`/`{schema}`/`tenant_NNN` は `tenant.<table>` に正規化、`public.x`/裸の `x` は `public.x` に正規化。
- 新規: `scripts/migration-column-churn-allowlist.json`（table/column/reason/reference の配列）。
- 新規: `scripts/tests/test-migration-column-churn.js`（8ケース: a〜h、全PASS）。
- 新規: `scripts/check-migration-duplicate-registration.sh`（bash、`scripts/check-migration-registration-exists.sh` と同じ書式）。run_sql/run_py の登録パス重複を検出。
- 新規: `scripts/tests/test-migration-duplicate-registration.js`（3ケース、全PASS）。
- 変更: `scripts/run_all_migrations.sh` の536行目（1回目と同一内容の重複登録）を削除。530行目の1回目は残置。
- 変更: `.github/workflows/migration-guard.yml` に「チェック10」を追加。PR差分が「migrations/**」・`scripts/run_all_migrations.sh`・「scripts/migrate_*.py」（グロブパターン）・チェック自身・allowlist のいずれかに触れている場合のみ2チェックを実行（既存のチェック2と同じ `if:` トリガー書式）。

## 検出結果（origin/main 時点、2026-10-06）

- churn候補 2件、いずれもガード済みと確認し allowlist 登録（下記「③以外の判断」参照）。unallowed churn は0件。
- drop-then-add 警告 2件（`analysis_run_snapshots.unit_id`/`condition_id`）。いずれもガード済み（型変換後は no-op）。警告は exit に影響しない設計のため allowlist 不要。
- 既知の「condition/unit/category_classification」ADD（#3958で削除済み）は検出0件を確認（facts通り）。

## allowlist 登録内容（2件）

1. `tenant.deals.lost_reason_code`（ADD: `migrations/20260604_060000_add_lost_reason_code.sql:36` → DROP: `migrations/20260613_020000_funnel_close_reasons.sql:106`）。ガード根拠: ADD側が「deals テーブルが存在しないスキーマはスキップ」の CONTINUE ガードを持ち、`migrations/20260729_043520_drop_deals.sql` が deals テーブル自体を永久 DROP済みで再作成なし。2回目以降の全件再実行では ADD 自体が実行されない。reference: commit a0b849fb3（#1605）/ `migrations/20260729_043520_drop_deals.sql`。
2. `public.products.tcg_uuid`（ADD: `migrations/20260914_140000_unify_tcg_products_to_public.sql:58` → DROP: `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:7`）。ガード根拠: `DO $guard_tcg_uuid$` が `work_id` が INTEGER であることを確認してADDを恒久的にスキップする（`migrations/20260919_010000_master_ssot_work_id_recast.sql` が永久変換）。reference: commit 17582fbd5（ADR-1002 Phase C）/ `docs/handoff/products-column-churn-2/design.md`。

---

## ③ 全件ドライラン対象範囲の調査（事実のみ、ワークフロー未変更）

`git log -L 1655,1670:.github/workflows/migration-test.yml` で確認した変更履歴（新しい順）:

1. commit `c6b68e1a9`（2026-06-13、shingo-ops）「numbered migration を2周目テスト対象に追加（013 vs 103 型バグ検出）」。フィルタを `^migrations/2026060[4-9]|^migrations/2026061|^migrations/2026062` から `^migrations/0|^migrations/2026060[4-9]|^migrations/2026061|^migrations/2026062` に拡張（numbered migration `0` を追加）。**これが直近の変更で、以後フィルタは一度も更新されていない**。
2. commit `a8e7e14a3`（2026-06-12、shingo-ops）「migration 全件ドライランを 2 周連続実行に拡張（冪等性チェック）」。1周目のフィルタを `20260604〜20260629` 相当（`2026060[4-9]|2026061|2026062`）に初めて設定。
3. commit `9e8c20c22`（2026-06-12、shingo-cc、#2051）「全件ドライランジョブ追加（migration-full-dryrun）」。このPR内で3段階の絞り込みが行われた:
   - 当初はタイムスタンプ形式 SQL 全件が対象。
   - 次に「番号付き migration（013-100）は migrate_meta.py 等が作るテーブルに依存するため CI では実行不可」としてタイムスタンプ形式のみに限定。
   - 最後に「20260602_020000_add_products_tcg_type.sql が migration 082 で追加される category 列を参照するため失敗」として `20260604` 以降に限定（`20260601`〜`20260603` を除外。当該ファイルは現在の migrations/ には存在しない＝その後の整理で削除/リネームされた可能性があるが、本PRの調査範囲外）。

事実としてわかったこと:
- 除外範囲は「CI のbase schemaがPython migration（numbered）依存のテーブル/列を再現できない」という技術的制約で設定されたもので、意図的に「2026062以降を除外する」という恒久方針ではない。
- `c6b68e1a9` で `migrations/0` 系（numbered migration）をテスト対象に戻す拡張が1回行われた後、`2026062` を超える範囲（`2026063` 以降、`20260701` 以降など）への拡張コミットは見つからなかった（`git log --oneline --all -- .github/workflows/migration-test.yml` で dryrun 関連コミット11件を全件確認、直近は `cb6872b61` 等 base schema 側の追加で、フィルタ正規表現自体の拡張は無い）。
- フィルタ付近（1600〜1710行）にTODOや「将来拡張」等のコメントは無い（`grep -n "TODO\|拡張\|後続\|将来"` で該当は「後続 migration」という別文脈の1件のみ）。
- 現在 migrations/ には `2026062` より後のタイムスタンプ（`20260701`〜`20260930` 台）のファイルが多数存在する（本PRのallowlist対象2ファイル `20260909`,`20260914`,`20260916`,`20260919`,`20260924` を含む）が、これらは全件ドライランの対象外。

本カードは③を「調査のみ」とする指示のため、フィルタの拡張（対象を戻せるか判断する作業）は行っていない。対象外の162件（recon by Opus, docs/handoff/migration-runner-redesign/recon.md「1. 数の事実」参照）の内訳調査と拡張判断は、別カードで行う前提。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 全件ドライランの対象外162件のうち、どれが拡張可能か | 別カードで1件ずつ CI 実行し失敗要因を分類 | ❌ 未解消（③は調査のみの指示のため本カード対象外） |

**未解決ゼロ確認**: 上記1件は本カードの意図的なスコープ外（指示で「③は投資調査のみ・ワークフロー変更なし」と明示）。①②は未解決ゼロ。

---

## 補足

- allowlist は churn（ADD→DROP）findingのみを対象とし、drop-then-add 警告は allowlist 不要（exitに影響しない設計）。
- `check-migration-column-churn.js` は列名を変数で組み立てている箇所（0件、Opus審査済み・design.md記載）を前提に、文字列の正規表現照合のみで実装した。
