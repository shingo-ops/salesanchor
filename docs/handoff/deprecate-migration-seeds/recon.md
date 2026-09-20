# Recon: deprecate-migration-seeds

## 対象ファイル（全12本）

| ファイル | DDL有無 | 除去対象 |
|---|---|---|
| `migrations/20260901_090000_add_condition_resolution_columns.sql:98-157` | あり (ALTER TABLE ADD COLUMN x3, CREATE INDEX) | UPDATE conditions SET app_kubun/priority/search_kw/exclude_kw |
| `migrations/20260902_110000_tcg_classification_masters.sql:84-128` | あり (CREATE TABLE IF NOT EXISTS x4) | INSERT tcg_major_categories/tcg_series/tcg_manufacturers/tcg_product_categories |
| `migrations/20260903_130000_tcg_note_master_t004.sql:44-348` | あり (CREATE TABLE IF NOT EXISTS tcg_note_master) | INSERT 22件 (NJ001-NJ022) + 件数検証 |
| `migrations/20260903_150000_tcg_status_master_t004.sql:47-148` | あり (CREATE TABLE IF NOT EXISTS tcg_status_master) | INSERT 9件 (ST0001-ST0014) + COUNT検証 |
| `migrations/20260905_120000_register_15_suppliers_t004.sql` | なし | INSERT tcg_suppliers 15件 (SP0188-SP0202) + supplier_channels |
| `migrations/20260905_150000_record_manual_supplier_fixes_t004.sql` | なし | UPDATE SP0007/SP0184 + INSERT SP0203/SP0204 + supplier_channels + 検算 |
| `migrations/20260906_120000_create_tcg_tables_t001.sql:569-642` | あり (CREATE TABLE IF NOT EXISTS x27 + CREATE INDEX) | INSERT 分類マスタ4テーブル + テスト仕入元3件 + supplier_channels |
| `migrations/20260907_100000_tcg_note_master_expand_t004.sql:27-79` | なし（ALTER TABLE はなし、この時点では既存列） | INSERT 26件 (NJ023-NJ056) + UPDATE NJ004/NJ014 + 件数検証 |
| `migrations/20260909_130000_tcg_note_b2_t004.sql:43-136` | あり (ALTER TABLE ADD COLUMN match_type/search_pattern/label_template) | UPDATE tcg_normalization_rules + INSERT tcg_normalization_rules 13件 + INSERT tcg_note_master 25件 + UPDATE NJ023 + 件数検証 |
| `migrations/20260910_200000_tcg_condition_note_delivery_t004.sql` | なし | UPDATE conditions CN0007 + UPDATE tcg_note_master NJ041 + INSERT NJ079 |
| `migrations/20260913_150000_tcg_empty_box_condition.sql` | なし | INSERT conditions CN0011 |
| `migrations/20260913_200000_tcg_cardset_exclusion.sql` | なし | INSERT product_exclude_keywords PM0263 |

## 保持したDDL

- `20260901_090000`: ALTER TABLE conditions ADD COLUMN priority/search_kw/exclude_kw, CREATE INDEX idx_conditions_priority
- `20260902_110000`: CREATE TABLE IF NOT EXISTS tcg_major_categories/tcg_series/tcg_manufacturers/tcg_product_categories
- `20260903_130000`: CREATE TABLE IF NOT EXISTS tcg_note_master
- `20260903_150000`: CREATE TABLE IF NOT EXISTS tcg_status_master
- `20260906_120000`: CREATE TABLE IF NOT EXISTS 27本すべて + CREATE INDEX各種
- `20260909_130000`: ALTER TABLE tcg_note_master ADD COLUMN IF NOT EXISTS match_type/search_pattern/label_template

## 関連ADR

- `docs/adr/ADR-155-*.md` (値管理をapp UI/CSV経由に移行)
