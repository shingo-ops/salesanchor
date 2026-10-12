# Design: Phase 2c の定常状態FKブロックを解消（第5便）

**対象**: デプロイ失敗 2026-10-04（run 37139483973、`migrations/20260915_010000_drop_tcg_products_phase2c.sql` ステップ244/317、`Phase 2c blocked: 2 FK(s) still reference tenant_004.tcg_products`）
**recon**: docs/handoff/products-column-churn-5/recon.md
**関連PR**: #3958〜#3961（第1便〜第4便）
**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装)

---

## 外部・過去事例の参照と我々への応用

該当なし（理由: 自社migration群内の定常状態不整合であり、参照すべき外部のベストプラクティス
文書は無い。PostgreSQLの列数上限に関する外部事例は第1便design.mdで引用済みのため再掲しない）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `scripts/run_all_migrations.sh` の構文が壊れていない | `bash -n scripts/run_all_migrations.sh` → exit 0 |
| `migrations/20260915_010000_drop_tcg_products_phase2c.sql` の既存カウントチェック・DROP文は無変更 | diff で該当2行（`:72-79`,`:86`付近）が変更されていないことを確認 |
| 定常状態（本書の「ウォーク1」）でデプロイが最後まで成功する | 本書「ウォーク1: 定常状態」の全件ウォーク |
| 現在の失敗状態（本書の「ウォーク2」）から次回デプロイで復旧する | 本書「ウォーク2: 現在の失敗後の状態」 |
| 追加した行に `DROP` の直後に `TABLE`/`COLUMN` が続く文字列が無い（process-artifacts gate対応） | `git diff` の追加行を grep で確認（`DROP CONSTRAINT` のみ） |
| CI `migration-full-dryrun` は9月ファイルを除外するため本修正を検証しない（既知のギャップ） | 第1便〜第4便と同じ正規表現確認を再掲 |

---

## 設計方針

coordinator 指定のパターンをそのまま実装: `migrations/20260915_010000_drop_tcg_products_phase2c.sql`
のループ内、既存のFK件数チェック（`:72-79`、無変更）の**前**に、以下の事前クリーンアップを追加した。

```
tcg_uuid が存在しない AND このスキーマの tcg_products が0行
  → tcg_products を参照する各FKについて:
       参照元テーブルが0行 → ALTER TABLE ... DROP CONSTRAINT ...（NOTICEを出す）
       参照元テーブルが1行以上 → 何もしない（既存のEXCEPTIONがそのまま発火する）
```

既存のFK件数チェック・既存の `DROP TABLE %I.tcg_products` 文は一切変更していない
（coordinator指示通り）。追加した行はすべて `ALTER TABLE ... DROP CONSTRAINT ...` のみで、
`DROP` の直後に `TABLE` または `COLUMN` が続く文字列は含まない（`git diff` で確認済み、
下記「変更内容」参照）。

---

## ウォーク1: 定常状態（前回デプロイが tenant_004 コピーを DROP した直後からの次回デプロイ）

開始状態: `tenant_004.tcg_products`・`analysis_results`・`analysis_run_snapshots`・
`product_search_keywords`・`product_exclude_keywords` は**存在しない**（前回の成功デプロイが
`migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`・
`migrations/20260921_130000_drop_tenant004_master_copies.sql` で DROP 済み）。
`tenant_004.products_logistics` は存在し INTEGER（DROP対象リストに無いため永続）。
`public.products.tcg_uuid`／`.condition`／`.unit`／`.category_classification` は存在しない。
`work_id`／`product_category_id` は INTEGER。`public.products` は新規列を割り当てられない
（第2便recon.mdで確認済みの既存列のみ）。

`scripts/run_all_migrations.sh` の全 `run_sql`/`run_py`（317件）を走査し、本条件（tenant_004
テーブルのCREATE/ALTER/DROP・public.productsの列操作・tcg_uuid/tcg_productsへの参照）に
合致するステップのみを以下に列挙する。他の全ステップは第2便〜第4便の全件スキャン
（docs/handoff/products-column-churn/recon.md・docs/handoff/products-column-churn-2/recon.md・docs/handoff/products-column-churn-3/recon.md・docs/handoff/products-column-churn-4/recon.md）
で対象外と確定済みであり、本便で新規に追加された migration は無いため、その結論は不変。

| 登録行 | file:line | 内容 | 定常状態での結果 |
|---|---|---|---|
| 191 | `migrations/20260623_020000_drop_products_category_classification.sql:60` | DROP IF EXISTS category_classification | 既に無し → no-op |
| 216 | `migrations/20260602_000000_add_products_central_columns.sql:17-20` | ADD mark/status/weight/notes | 全て既存 → IF NOT EXISTS でスキップ、新規attnum無し |
| 230 | `migrations/20260602_170000_add_products_master_label_columns.sql:28-33` | ADD volume_weight等6列 | 全て既存 → スキップ |
| 249/261/318 | migrations/20260603_000000_add_products_product_kind.sql・migrations/20260603_040000_add_products_set_type.sql・migrations/20260605_000000_add_products_display_order.sql | ADD 1列ずつ | 全て既存 → スキップ |
| 491 | `migrations/20260629_020000_drop_products_condition_unit.sql:5-6` | DROP IF EXISTS condition/unit | 既に無し → no-op |
| 524 | `migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql:19-40`（Step1） | tcg_uuid列存在チェック→無ければRETURN | tcg_uuid無し → RETURN、何もしない |
| 524 | 同ファイル:42-65（Step2） | tenant_%全体のtcg_products参照FKを無条件DROP | この時点でtcg_productsは**まだ存在しない**（530/536で初めて作られる）→ 対象0件、no-op |
| 527 | `migrations/20260922_050000_fix_phase2c_fk_drop_only.sql:12-16` | public/tenant_004.analysis_resultsの古いFKをDROP IF EXISTS | tenant_004.analysis_resultsもまだ存在しない → `ALTER TABLE IF EXISTS`でno-op |
| **530/536** | `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:156-315` | **CREATE**: tcg_products・analysis_results・product_search_keywords（FK→tcg_products）・product_exclude_keywords（FK→tcg_products） を新規（UUID・0行）で再作成 | tenant_004に4テーブルが「無→UUID・0行・FK付き」で出現 |
| 578 | `migrations/20260903_220000_create_tcg_analysis_history_t004.sql:54-77` | **CREATE**: analysis_run_snapshots（UUID、FK無し） | 「無→UUID・0行」で出現 |
| 628 | `migrations/20260909_000000_public_products_phase2b_columns.sql:18-37` | tcg_uuid ADDガード（PR#3959） | work_id=INTEGER・tcg_uuid無し→両方FALSE→ELSE分岐、ADDしない |
| 628 | 同ファイル:65-144（bootstrap） | tcg_products→public.productsデータコピー | 「work_id already INTEGER」でCONTINUE、コピーしない |
| 651 | `migrations/20260913_200000_tcg_cardset_exclusion.sql:16-37`（PR#3960） | product_search_keywords.product_idの型判定→tcg_uuid分岐→ガード | product_idはまだUUID→ELSE分岐→tcg_uuid無し→RAISE NOTICE+RETURN |
| 652 | `migrations/20260913_210000_tcg_cardset_bundle_registration.sql:18-40`（同上） | 同上 | 同上、RETURN |
| 661 | `migrations/20260914_140000_unify_tcg_products_to_public.sql:48-76`（Step1） | tcg_uuid ADDガード | スキップ（628と同様） |
| 661 | 同ファイル:94-122（Step2） | tcg_uuid型チェック→RETURN | tcg_uuid無し→RETURN、データコピーしない |
| 661 | 同ファイル:301-321（Step3、FK張替え本体） | tcg_uuid型チェック→RETURN | tcg_uuid無し→RETURN。**product_search_keywords/product_exclude_keywords/products_logistics/analysis_resultsのFKはtcg_products参照のまま残る**（本インシデントの直接原因） |
| 661 | 同ファイル:579-611（Step4） | 件数照合、tcg_products不在チェック→tcg_uuid型チェック→RETURN | tcg_productsは存在するが、tcg_uuid型チェックでRETURN |
| 665 | `migrations/20260922_040000_fix_phase2c_fk_blocker.sql:15-20` | public/tenant_004.analysis_resultsの古いFK（`analysis_results_product_id_fkey`）を無条件DROP | 成功。**analysis_resultsのFKはここで解消**（designer確認の「2件」にanalysis_resultsが含まれない理由） |
| 665 | 同ファイル:26-58 | public.analysis_resultsへの新FK追加（型チェックガード） | public.analysis_results.product_idは既にINTEGER→スキップ |
| **668** | `migrations/20260915_010000_drop_tcg_products_phase2c.sql`（本PRの修正箇所） | 事前クリーンアップ→既存FK件数チェック→既存DROP TABLE | tcg_uuid無し・tcg_products0行→事前クリーンアップが発火。残る2FK（product_search_keywords・product_exclude_keywords、いずれも参照元0行）を`DROP CONSTRAINT`→件数0→**`DROP TABLE tcg_products`成功**（修正の核心） |
| 671 | `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`（Table1〜5、PR#3961） | product_id UUID→INTEGER変換、tcg_uuidガード | product_search_keywords/product_exclude_keywords/analysis_results/analysis_run_snapshotsは全て0行・UUID→PR#3961のガードで「0行→joinなしで構造変換」が発火、全てINTEGERに変換完了。products_logisticsは既にINTEGER→スキップ |
| 674 | `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:5-7` | public.products.tcg_uuid関連をDROP IF EXISTS | 既に無し→no-op |
| 698 | `migrations/20260919_020000_master_ssot_public_tables.sql:301-326` | public.product_search_keywords/exclude_keywordsを新規に空でCREATE | tenant_004側のデータに依存しない→成功 |
| 744 | `migrations/20260921_110000_pipeline_tables_public.sql:183-314` | public.analysis_results/analysis_run_snapshotsを新規に空でCREATE | 同上、成功 |
| **747** | `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:17-18` | tenant_004.analysis_run_snapshots/analysis_resultsをDROP TABLE IF EXISTS（無変更） | 671で変換済み（INTEGER・0行）だが型・行数に関わらずDROP TABLE IF EXISTSは無条件成功 |
| **759** | `migrations/20260921_130000_drop_tenant004_master_copies.sql:27-28` | tenant_004.product_search_keywords/exclude_keywordsをDROP TABLE IF EXISTS CASCADE（無変更） | 同上、成功 |

**ウォーク1の結論**: 開始状態に戻る（不動点）。この修正により、定常状態から始まる
あらゆる今後のデプロイが最後まで成功し、終了状態は開始状態と同一になる
（`tenant_004` の5テーブルは再び全て不在、`public.products`は不変）。不確実な
ステップは無かった。

---

## ウォーク2: 現在の失敗後の状態（修正を当てた次回デプロイ）

現在の状態: run 37139483973 は line665（`fix_phase2c_fk_blocker`）まで成功し、line668
で `RAISE EXCEPTION` して停止した。したがって現在、`tenant_004.tcg_products`・
`product_search_keywords`・`product_exclude_keywords` は存在する（いずれも0行、
designer確認）。`analysis_results`のFKは665で既に解消済み（recon.md §2）。
`analysis_run_snapshots`も578で作成済み（0行と推定、未再確認だが構造上FKは無く
本件の影響を受けない）。

次回デプロイはスクリプトを先頭から再実行する。line668 に到達した時点で:
- tcg_uuid無し・tenant_004.tcg_products 0行 → 事前クリーンアップ発火
- 残存FK: product_search_keywords_product_id_fkey・product_exclude_keywords_product_id_fkey
  （designer確認の2件そのもの）、両方とも参照元テーブルが0行 → 両方DROP CONSTRAINT
- 件数チェック→0→`DROP TABLE tcg_products`成功

以降の処理（671のphase_b変換、674、698〜759のDROP）は**ウォーク1と同一**になる
（この時点でtenant_004の状態がウォーク1の「530/536直後」と実質一致するため）。

**ウォーク2の結論**: 次回デプロイで現在の失敗状態から正常に復旧し、ウォーク1と同じ
最終状態（定常状態）に到達する。不確実なステップは無かった。

---

## CI カバレッジ（既知のギャップ、再確認）

第1便〜第4便と同じ。本PRが変更する `migrations/20260915_010000_drop_tcg_products_phase2c.sql`
は9月付けファイルのため `migration-full-dryrun`（対象正規表現が6月4日〜29日のタイムスタンプ
のみ）の対象外。**この「ウォーク1/ウォーク2」の手動シミュレーションが、本修正の正しさを
検証する唯一の手段である**（CIの全件ドライランはこの修正を検証しない）。
`migration-test-run`ジョブ（変更SQLを2回実行）は対象として乗る。

---

## 変更内容

`migrations/20260915_010000_drop_tcg_products_phase2c.sql`:
- DECLARE に `_tcg_uuid_exists BOOLEAN`・`_tcg_products_rows BIGINT`・`fk_record RECORD`・
  `_ref_rows BIGINT` を追加
- ループ開始前に `_tcg_uuid_exists` を一度だけ計算
- ループ内、既存のFK件数チェック（無変更）の直前に事前クリーンアップを追加:
  tcg_uuid無し かつ 当該スキーマのtcg_products0行の場合のみ、tcg_products参照FKを
  1件ずつ確認し、参照元0行なら `ALTER TABLE %I.%I DROP CONSTRAINT %I` + NOTICE、
  1行以上なら何もしない（既存のEXCEPTIONに委ねる）
- 既存のFK件数チェック・既存の `DROP TABLE %I.tcg_products` 文は一切変更なし

追加した行に `DROP` の直後に `TABLE`/`COLUMN` が続く文字列は含まれない（確認コマンド:
`git diff -- migrations/20260915_010000_drop_tcg_products_phase2c.sql | grep "^+" |
grep -iE "drop[[:space:]]+table|drop[[:space:]]+column"` → 0件）。

---

## 変更範囲

| 層 | 変更 |
|---|---|
| migrations | migrations/20260915_010000_drop_tcg_products_phase2c.sql に事前クリーンアップ追加 |
| docs | docs/handoff/products-column-churn-5/recon.md（新規）・docs/handoff/products-column-churn-5/design.md（新規） |
| 台帳 | .claude-pipeline/active-work.d/release-stop-products-column-churn-5.md（main checkout に新規作成、このブランチには含めない） |

## 触るファイル

1. migrations/20260915_010000_drop_tcg_products_phase2c.sql
2. docs/handoff/products-column-churn-5/recon.md（新規）
3. docs/handoff/products-column-churn-5/design.md（新規・本ファイル）

削除するファイル: 無し（`git diff --numstat` で確認済み: 52行追加・0行削除。既存コードの
前に新しい処理を挿入したのみで、既存行の置換・削除は発生していない）。

---

## 維持の仕組み

守り手: 以下はアイデア提案のみで未実装（本PRのスコープ外）
- 第1便〜第4便から継続: ADD/DROP対応表のCI検知案・動的列参照追跡案・
  `migration-full-dryrun`対象範囲拡張案。
- 今回の教訓: 「定常状態（前回デプロイ直後の状態）から次のデプロイが成功するか」を
  明示的にシミュレーションする手順が無かった。複数ファイルにまたがる
  ADD→DROP／CREATE→DROPのサイクルを持つ migration 群を変更する際は、
  「前回成功デプロイの直後から始めて最後まで通るか」の手動ウォーク（本書ウォーク1）を
  標準の確認ステップとして明文化する案（未実装・提案）。
