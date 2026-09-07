# design: tenant_001 TCG テーブル作成（QA-03）

## 目的

本 PR は **tenant_001 に TCG テーブルを作るのみ**。
tenant_004 / 006 には一切影響しない。既存 migration は変更しない。

---

## 設計判断

### テナント選定: tenant_001

- contacts=0・ユーザー 2 名・最終ログイン不明（NULL）
- STANDARD-WORKFLOW.md:93 に「空テスト」と明記済み
- テーブル数 68 本（CRM 系のみ）= TCG テーブル未存在

tenant_006 は Meta App Review 撮影専用（contacts=8 あり）→ QA 禁止

### t006 migration の削除

`migrations/20260906_100000_create_tcg_tables_t006.sql` を削除する。

理由: 本番デプロイで毎回 RAISE EXCEPTION が発火し続けている。
対象 tenant_006 が Meta App Review 専用で QA には使わないと確認されたため。
DB への影響: なし（migration は一度も正常実行されていない・rollback 済み）

### 1 本に集約する理由

t004 の migration は 11 本に分割されているが、001 は新規テーブルのため
ALTER TABLE を最終形として CREATE TABLE に内包できる。

### 検算の方法（PR #3317 の教訓を反映）

全件カウント（スキーマ内全テーブル）は使用禁止。
`AND table_name IN (...)` で今回作成した 27 テーブルのみを限定カウントする。

---

## 作成テーブル一覧（27 本）

| 分類 | テーブル |
|------|---------|
| 独立 | audit_log, conditions, tcg_major_categories, tcg_series, tcg_manufacturers, tcg_product_categories, tcg_products, tcg_suppliers, units, import_jobs, item_corrections, tcg_distribution_targets, tcg_distribution_settings |
| FK 1階層 | condition_aliases, product_exclude_keywords, product_search_keywords, products_logistics, supplier_channels, unit_aliases |
| FK 2階層以降 | source_messages, extraction_jobs, extraction_items, analysis_results, item_notes, unparsed_lines, analysis_runs, analysis_run_snapshots |

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| migration 実行後に tenant_001 の TCG テーブルが 27 本存在する | RAISE NOTICE `TCG テーブル数 = 27` を目視確認。27 以外なら EXCEPTION で即停止 |
| テスト仕入元 3 件が登録されている | RAISE NOTICE `SP9001/SP9002/SP9003 + LINE チャンネル各 1 件` |
| tenant_004 / 006 に影響がない | migration は `_schema = 'tenant_001'` 固定。他テナントファイル変更なし |
| t006 migration が deploy で失敗しなくなる | deploy.yml の migration ステップが緑で完了する |

---

## 外部事例

該当なし（QA テナント作成という性質上、外部事例の参照は不要）。

---

## 弊害・リスク

| リスク | 対処 |
|--------|------|
| tenant_001 に既存 CRM データが存在した場合 | contacts=0 を実測済み（2026-09-06）。影響なし |
| t006 migration 削除で PR #3317 の差分が無意味になる | #3317 は対象ファイル削除により実質クローズ扱い。DBへの影響なし |
| テーブル数 != 27 | `IF _table_count <> 27 THEN RAISE EXCEPTION` で即停止 |

---

## 戻し方

1. `migrations/20260906_120000_create_tcg_tables_t001.sql` を削除する migration を作成（`DROP TABLE ... CASCADE` を 27 本分）。
2. `scripts/run_all_migrations.sh` から該当 `run_sql` 行を削除。
3. 本番 DB で tenant_001 に TCG テーブルが存在する場合のみ実行が必要。

---

## 守り手

人手で守る（migration 実行後の RAISE NOTICE ログを目視確認）。
自動化は本 PR のスコープ外。
