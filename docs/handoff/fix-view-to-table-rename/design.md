# Design: VIEW → TABLE 修正

## 目的
手動作成された4つのVIEWを解消し、後続28本のマイグレーションが正常実行できるようにする。
ADR-025（データ手動DB操作の原則禁止）に基づき、手動作成VIEWを正規マイグレーションで修正する。

## 変更前後
| 対象 | 変更前 | 変更後 |
|------|--------|--------|
| public.units | VIEW → line_units | TABLE (renamed from line_units) |
| public.unit_aliases | VIEW → line_unit_aliases | TABLE (renamed) |
| public.conditions | VIEW → line_conditions | TABLE (renamed) |
| public.condition_aliases | VIEW → line_condition_aliases | TABLE (renamed) |

## 対象と対象外
- 対象: 4 VIEW の DROP + 4 line_* テーブルの RENAME
- 対象外: データ変更、行の追加/削除、スキーマ変更

## 受入条件
| 基準 | 検証方法 |
|------|----------|
| 4つがTABLEになる | `SELECT relkind FROM pg_class WHERE relname IN (...)` → 全て 'r' |
| 行数が変わらない | 修正前後の COUNT(*) 比較 |
| 後続マイグレーションが通る | デプロイ成功（exit 0） |
| FKが維持される | `pg_constraint` で確認 |

## 外部・過去事例の参照と我々への応用
該当なし（PostgreSQL標準DDLのRENAME TABLE・DROP VIEW CASCADE は公式仕様どおりの操作のみ）

## 維持の仕組み
守り手: PO（Shingo）

## リスクと対処
- DROP VIEW CASCADE で意図しない依存が消える → 事前に依存確認済み（pg_dependで他テーブルからの依存なし）
- RENAME後にFKが切れる → PostgreSQLはRENAME時にFKを自動追従（公式仕様）

## recon相互参照
docs/handoff/fix-view-to-table-rename/recon.md
