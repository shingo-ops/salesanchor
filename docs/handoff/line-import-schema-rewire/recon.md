# recon — line-import-schema-rewire

**仕事名**: line-import-schema-rewire
**日付**: 2026-09-22
**対象ADR**: ADR-156（商品分類ツリーと共用マスタ分離。Phase 4/5 のスキーマ移行が本件の背景）
**担当**: implementer

---

## 障害事実（事前調査済み・本recon実施前に確定）

- `POST https://api.salesanchor.jp/api/v1/tcg/line-devices/import` が HTTP 500
  `{"detail":"データベースエラーが発生しました。"}` を返す。無効トークンでは 401 が返るため
  API・認証経路自体は正常。
- 最後の成功 2026-09-21 16:46:44、最初の失敗 17:01:43。
- 16:52 に PR #3628（`migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`）が
  マージされ、`tenant_004` のパイプライン用テーブル（`source_messages` 等）が DROP された。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_line_import_svc.py:35` (修正前は `from app.tcg_config import TCG_SCHEMA`) | 修正前は `TCG_SCHEMA` を `tenant_004` 既定の `backend/app/tcg_config.py` から輸入しており、DROP 済みテーブルを指し続けていた |
| `backend/app/tcg_config.py:19` | `TCG_SCHEMA` の既定値は `os.getenv("TCG_SCHEMA", "tenant_004")` — 環境変数未設定時は `tenant_004` |
| `backend/app/routers/tcg_line_import.py:54-56` | 既に移行済みの他モジュールと同じ書き方: `# Step 4/5: TCG テーブルは public スキーマに移行済み。` コメント + `TCG_SCHEMA = "public"` のモジュール内定数定義（`app.tcg_config` を import しない） |
| `backend/app/services/tcg_import_progress.py:13-15` | 同上パターンの別例（`TCG_SCHEMA = "public"` を直接定義） |
| `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:1-49` | `tenant_004.source_messages` / `supplier_channels` / `import_jobs` / `import_job_messages` / `extraction_jobs` / `extraction_items` / `analysis_results` 等を DROP。PR #3628 の実体 |
| `migrations/20260921_110000_pipeline_tables_public.sql:9-16` | `public.supplier_channels` CREATE TABLE（Category C-1） |
| `migrations/20260921_110000_pipeline_tables_public.sql:19-31` | `public.source_messages` CREATE TABLE（Category C-2） |
| `migrations/20260921_110000_pipeline_tables_public.sql:39-53` | `public.import_jobs` CREATE TABLE（Category B-1） |
| `migrations/20260921_110000_pipeline_tables_public.sql:57-66` | `public.import_job_messages` CREATE TABLE（Category B-2） |
| `migrations/20260921_110000_pipeline_tables_public.sql:78-88` | `public.extraction_jobs` CREATE TABLE（Category A-1） |

## tcg_line_import_svc.py が参照する5テーブルの実在確認（1つずつ）

| テーブル（`{TCG_SCHEMA}.<table>`） | 参照箇所（修正前ファイル行） | `public` に実在するか |
|---|---|---|
| `supplier_channels` | `_write_source_messages` 内 SELECT/JOIN、自動登録時の INSERT | 実在（`migrations/20260921_110000_pipeline_tables_public.sql:9`） |
| `source_messages` | 冪等チェック SELECT・INSERT・supersede UPDATE | 実在（同ファイル:19） |
| `extraction_jobs` | INSERT（source_message ごとに1件） | 実在（同ファイル:78） |
| `import_job_messages` | `_link_message` の INSERT | 実在（同ファイル:57） |
| `import_jobs` | 冪等チェック SELECT・メインINSERT・`messages_linked_at` UPDATE | 実在（同ファイル:39） |

5テーブルとも `public` に実在。存在しないテーブルなし（作業1の停止条件に該当なし）。

## 既に `TCG_SCHEMA = "public"` へ書き換え済みの15モジュール（実測）

```
grep -rln 'TCG_SCHEMA = "public"' backend/app
```

結果15件（tcg_line_import_svc.py 修正後を含む）:

- `backend/app/routers/tcg_line_import.py:56`
- `backend/app/services/line_source_names.py:9`
- `backend/app/services/tcg_analysis_review_svc.py:17`
- `backend/app/services/tcg_analysis_dashboard_svc.py:13`
- `backend/app/services/tcg_condition_review_svc.py:30`
- `backend/app/services/tcg_diagnostics_svc.py:22`
- `backend/app/services/tcg_analyzer_svc.py:54`
- `backend/app/services/tcg_distribution_svc.py:41`
- `backend/app/services/tcg_extraction_record_svc.py:17`
- `backend/app/services/tcg_import_progress.py:15`
- `backend/app/services/tcg_parallel_report_svc.py:25`
- `backend/app/services/tcg_unit_recovery_svc.py:38`
- `backend/app/services/tcg_supplier_quality_svc.py:13`
- `backend/app/services/tcg_sold_out_results_svc.py:11`
- `backend/app/tasks/tcg_extraction.py:46`

（本PRで `backend/app/services/tcg_line_import_svc.py:36` を追加し16件目にする）

## 作業2: `from app.tcg_config import TCG_SCHEMA` を使う残存モジュール（修正はしない・報告のみ）

```
grep -rln "from app.tcg_config import TCG_SCHEMA" backend/app
```

ヒット9件のうち `backend/app/tcg_config.py` 自身を除く8件がユーザー指定の対象。加えて grep で
`backend/app/services/line_import_devices.py` も1件ヒットしたため、壊れているかを確認した
（下表末尾に記載）。

| モジュール | 参照する `{TCG_SCHEMA}.<table>` | 由来 | `public` に同名テーブルが存在するか | 状態 |
|---|---|---|---|---|
| `backend/app/line_import_admin.py` | `import_jobs`（:97）, `source_messages`（:119）, `supplier_channels`（:120） | 直書きSQL | 3件とも実在（`migrations/20260921_110000_pipeline_tables_public.sql`） | **壊れている**（パイプライン系DROPと同じ理由） |
| `backend/app/routers/tcg_product_import.py` | `analysis_results`（:421） | 直書きSQL | 実在 | **壊れている** |
| `backend/app/services/tcg_product_detail_svc.py` | `audit_log`（:195）／ `LOOKUPS = {"manufacturer_id": "tcg_manufacturers"}`（:15-17, :90 で `{TCG_SCHEMA}.{table}`) | 直書きSQL／辞書経由 | `audit_log` は実在（`migrations/20260921_110000_pipeline_tables_public.sql`）。`tcg_manufacturers` は tenant_004 に現存（未DROP、`migrations/20260913_210000_tcg_cardset_bundle_registration.sql:42` で参照され続けている運用テーブル） | `audit_log` 参照箇所のみ**壊れている**。`tcg_manufacturers` 参照は影響なし |
| `backend/app/services/tcg_product_import_svc.py` | `tcg_product_import_jobs`（:419）, `tcg_product_import_rows`（:437）／ `LOOKUP_TABLES = {"division_code": "tcg_major_categories", "manufacturer_code": "tcg_manufacturers", "product_category_code": "tcg_product_categories"}`（:179 で `{TCG_SCHEMA}.{table}`） | 直書きSQL／辞書経由 | `tcg_product_import_jobs`/`tcg_product_import_rows` は実在（`migrations/20260921_110000_pipeline_tables_public.sql`）。**別件**: `tcg_major_categories`/`tcg_product_categories` は `migrations/20260921_130000_drop_tenant004_master_copies.sql` で tenant_004 から別途DROP済み（ADR-156 Phase5・本件のパイプライン系DROPとは別PR）。`tcg_manufacturers` は現存 | パイプライン2テーブルは**壊れている**。加えて `tcg_major_categories`/`tcg_product_categories` も**別理由で壊れている**（本PRのスコープ外・追加調査が必要と思われる） |
| `backend/app/services/tcg_product_master_svc.py` | `analysis_results`（:58）, `extraction_items`（:56）, `extraction_jobs`（:57）, `analysis_runs`（:567）, `analysis_run_snapshots`（:583） | 直書きSQL | 5件とも実在（`migrations/20260921_110000_pipeline_tables_public.sql`） | **壊れている** |
| `backend/app/services/tcg_product_roundtrip_svc.py` | `tcg_product_import_jobs`（:313）, `tcg_product_import_rows`（:363） | 直書きSQL | 2件とも実在 | **壊れている** |
| `backend/app/services/tcg_work_comparison_svc.py` | `import_jobs`（:117）, `import_job_messages`（:120）, `source_messages`（:121）, `extraction_jobs`（:122）, `extraction_items`（:124）, `analysis_results`（:125）, `item_corrections`（:126）（`read_snapshot` 内、:114-126） | 直書きSQL | 7件とも実在 | **壊れている**。同ファイル内の `_PUBLIC_MASTER`（マスタ系8テーブル）は既に ADR-156 Phase 5 で public 化済み（コメント:127-128）だが、`read_snapshot` のパイプライン系はコード分離されており未修正のまま残存 |
| `backend/app/tasks/tcg_mirror.py` | `source_messages`（:195）, `extraction_jobs`（:196）, `extraction_items`（:197）, `analysis_results`（:198）（サプライヤー別サマリ集計クエリ内、:184-203） | 直書きSQL | 4件とも実在 | **壊れている**。同ファイル `_fetch_db_structure`（:206以降）は既に `table_schema = 'public'` ハードコードへ書き換え済み（コメント:225「ADR-156 Phase 5: keyword/alias master tables moved to public schema (SSOT)」）だが、サプライヤー別サマリ関数は未修正のまま残存 |
| `backend/app/services/line_import_devices.py`（ユーザー指定8本には未記載・grep追加検出） | `TCG_SCHEMA` は `public.line_import_devices` テーブルの `schema` 列へ**値として保存**するのみ（:59, :81, :100）。SQL のスキーマ修飾には未使用（全SQLは `public.line_import_devices` 直書き） | — | — | **壊れていない**。TCG_SCHEMA を「発行時のスキーマ設定値の記録」用途で使うだけで、テーブル参照には使っていないため今回のDROPの影響を受けない |

**まとめ**: ユーザー指定8モジュールは全て「同じ理由（tenant_004パイプラインテーブルDROP）で壊れている」との前提が事実と一致した。加えて tcg_product_detail_svc.py と tcg_product_import_svc.py は一部テーブル参照（`tcg_manufacturers`）は無事、tcg_product_import_svc.py の `tcg_major_categories`/`tcg_product_categories` は**別migration（20260921_130000）による別理由**で追加的に壊れている可能性がある（本PRでは未修正・別PR行き）。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | tcg_line_import_svc.py が参照する5テーブルが `public` に実在するか | `migrations/20260921_110000_pipeline_tables_public.sql` を1テーブルずつ grep で確認 | ✅ 解消済み（全5件実在） |
| 2 | 作業2の8モジュールが本当に「同じ理由」で壊れているか | 各モジュールの `{TCG_SCHEMA}.<table>` 参照を洗い出し、tenant_004 DROP migration と public CREATE migration に照合 | ✅ 解消済み（8件とも該当。ただし2件で別理由の追加破損も確認） |
| 3 | `backend/app/services/line_import_devices.py` も同じ理由で壊れているか（grep で追加検出） | ソースを読み、TCG_SCHEMA の使途を確認 | ✅ 解消済み（値保存のみで非該当と判明） |

**未解決ゼロ確認**: 全て解消済み。

---

## 補足

- tcg_config.py 自体（`from app.tcg_config import TCG_SCHEMA` の定義元）は変更していない。他の未移行モジュールが引き続き参照するため。
- 本PRは `backend/app/services/tcg_line_import_svc.py` のコード修正とテスト修正のみ。migration 追加・DB操作は行っていない（両migrationとも既に本番適用済み＝今回の障害の原因そのもの）。
