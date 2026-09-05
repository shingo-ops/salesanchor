# design: tenant_006 テーブル作成（QA-01）

## 目的

本 PR は **006 にテーブルを作るのみ**。
004 には一切影響しない。既存 migration は変更しない。

---

## 設計判断: 1 本に集約する理由

_t004 の migration は 11 本のスキーマ変更ファイルに分割されている（CREATE TABLE + ALTER TABLE ADD COLUMN の組み合わせ）。

006 用に同じ分割構成を複製すると：
- 実行順依存が 11 ファイルにまたがる
- ALTER TABLE の前に CREATE TABLE が必要という依存が増える
- 006 用ファイルのメンテナンスコストが 11 倍になる

006 は新規スキーマのため、すべてのテーブルが存在しない。
ALTER TABLE による列追加を「最終形」として CREATE TABLE に内包できる。

**結論: 1 本ファイルに全テーブルを CREATE TABLE IF NOT EXISTS で集約する。**

---

## 作成テーブル一覧（27 本）

### 独立テーブル
| テーブル | 備考 |
|---------|------|
| `audit_log` | 変更履歴ログ |
| `conditions` | コンディションマスタ（最終形: priority/search_kw/exclude_kw 含む） |
| `tcg_major_categories` | 大分類マスタ（FK 参照元のため先に作成） |
| `tcg_series` | 作品マスタ |
| `tcg_manufacturers` | メーカーマスタ |
| `tcg_product_categories` | 商品区分マスタ |
| `tcg_products` | TCG商品マスタ（最終形: mark/english_title + FK 制約含む） |
| `tcg_suppliers` | 仕入先マスタ |
| `units` | 単位マスタ |
| `import_jobs` | アップロード履歴（最終形: review_stage 5 列含む） |
| `item_corrections` | 修正履歴（FK 制約なし） |
| `tcg_distribution_targets` | 配信先マスタ |
| `tcg_distribution_settings` | 配信全体設定 |

### FK 1 階層
| テーブル | 親テーブル |
|---------|-----------|
| `condition_aliases` | conditions |
| `product_exclude_keywords` | tcg_products |
| `product_search_keywords` | tcg_products |
| `products_logistics` | tcg_products |
| `supplier_channels` | tcg_suppliers |
| `unit_aliases` | units |

### FK 2 階層以降
| テーブル | 親テーブル |
|---------|-----------|
| `source_messages` | supplier_channels |
| `extraction_jobs` | source_messages |
| `extraction_items` | extraction_jobs |
| `analysis_results` | extraction_items, tcg_products, units, conditions |
| `item_notes` | extraction_items |
| `unparsed_lines` | extraction_items |
| `analysis_runs` | extraction_jobs |
| `analysis_run_snapshots` | analysis_runs |

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| migration 実行後に tenant_006 スキーマが存在する | RAISE NOTICE でスキーマ名が出力される |
| テーブル数が 27 本である | RAISE NOTICE `テーブル数 = 27` を目視確認。27 以外なら EXCEPTION で即停止 |
| テスト仕入元 3 件が登録されている | RAISE NOTICE `SP9001/SP9002/SP9003 + LINE チャンネル各 1 件` |
| tenant_004 に影響がない | migration は `_schema = 'tenant_006'` 固定。_t004 ファイル変更なし |

---

## 外部事例

該当なし（QA テナント作成という性質上、外部事例の参照は不要）。

---

## 弊害・リスク

| リスク | 対処 |
|--------|------|
| 本番でも tenant_006 スキーマが作られる | `CREATE SCHEMA IF NOT EXISTS` で冪等。本番に 006 テナントが存在しない前提（VPS DB 確認済み） |
| 既存 _t004 ファイルへの影響 | なし（ファイル変更なし・スキーマ名は `tenant_006` 固定） |
| テーブル数 != 27 | `IF _table_count <> 27 THEN RAISE EXCEPTION` で即停止 |

---

## 戻し方

1. `migrations/20260906_100000_create_tcg_tables_t006.sql` を削除する migration を作成（`DROP SCHEMA tenant_006 CASCADE`）。
2. `scripts/run_all_migrations.sh` から該当 `run_sql` 行を削除。
3. 本番 DB で tenant_006 スキーマが存在する場合のみ実行が必要（存在しなければ不要）。

---

## 守り手

人手で守る（migration 実行後の RAISE NOTICE ログを目視確認）。
自動化は本 PR のスコープ外。
