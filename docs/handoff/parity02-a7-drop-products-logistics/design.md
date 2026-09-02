# design: PARITY-02 A-7 products_logistics 廃止

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

GAS・Python 双方で実質参照ゼロの `tenant_004.products_logistics` テーブルを廃止する。
2列（product_id, created_at）のみで意味のあるロジスティクスデータは存在しない。
PO 廃止承認済み（CC_TASK_PARITY-02_full_migration.md §着手順序 A-7）。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| `tenant_004.products_logistics` テーブルが存在しない | migration 実行後 VPS で `\d tenant_004.products_logistics` がエラーになる |
| 2回実行しても migration が成功する | VPS で2回実行し `already absent, skipping` で正常終了確認済み |
| `ingest_to_prod.py` が `products_logistics` を参照しない | grep で確認 |
| `write_mirror_once.py` が `products_logistics` を参照しない | grep で確認 |
| CI が通過する | GitHub Actions 確認 |

---

## 設計判断

### CREATE migration は変更しない

`20260831_110000_create_tcg_analysis_tables_t004.sql` の CREATE TABLE は履歴保全のため変更しない。
本 DROP migration が後続で実行されるため、最終状態は「存在しない」となる（run_all_migrations.sh の順序で保証）。

### CI ガード

DROP 系 migration も A-2/A-3 と同様に `tenant_004` 不在ガードを先頭に追加。
CI 環境ではスキップ、VPS 本番では正常実行。

---

## 外部事例

当プロジェクト既存踏襲: DROP TABLE は `IF EXISTS` で冪等にするパターン。

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 弊害・リスク

- **データ喪失**: `products_logistics` の 267 行（product_id, created_at のみ）が削除される。ロジスティクス実データなし・PO 承認済み。
- **ロールバック不可**: DROP TABLE は不可逆。ロールバックが必要な場合は `20260831_110000` migration の該当 CREATE TABLE 部分を再実行（267件の product_id は tcg_products に存在するため再 INSERT 可能だがデータは失われる）。

---

## 戻し方

`tenant_004.products_logistics` を再作成するには `20260831_110000` migration の products_logistics 部分を抽出して再実行（product_id/created_at のみ再作成・行データは失われる）。
