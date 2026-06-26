# recon — D-1: public.inventory(B在庫) v2形ドリフト正式化と収束migration

**仕事名**: d1-inventory-v2-converge  
**日付**: 2026-06-24  
**対象ADR**: ADR-143  
**担当**: Terminal CC

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/run_all_migrations.sh:176` | HELD: `migrations/20260623_030000_drop_uq_inventory_offer_key.sql`（封印済・未実行） |
| `scripts/run_all_migrations.sh:178` | HELD: `migrations/20260623_050000_drop_inventory_condition_column.sql`（封印済・未実行） |
| `scripts/run_all_migrations.sh:221` | `run_sql migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql`（封印解除後に condition 参照 INDEX を再作成する箇所） |
| `scripts/run_all_migrations.sh:451` | `run_sql migrations/20260624_120000_backfill_meta_messages_original_language.sql`（収束migrationの直前挿入位置） |
| `migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql:76` | `CREATE UNIQUE INDEX uq_inventory_offer_key ON public.inventory (supplier_id, product_id, condition, ...)` — condition 参照INDEX作成元 |
| `migrations/20260623_030000_drop_uq_inventory_offer_key.sql:1` | DROP INDEX uq_inventory_offer_key（HELD・L176） |
| `migrations/20260623_050000_drop_inventory_condition_column.sql:1` | ALTER TABLE DROP COLUMN condition（HELD・L178） |

---

## 確認結果

### A: ドリフト実態

**本番 public.inventory（v2形）**:
- 列数: 22列（condition列なし）
- インデックス: `uq_inventory_offer_v2` あり、`uq_inventory_offer_key` なし
- 件数: 92件

**repo フル実行到達形（旧形）**:
- condition列あり
- uq_inventory_offer_key あり（`20260602_180000:76` が作成）
- uq_inventory_offer_key は条件に condition 列を含む

### B: run_all_migrations.sh 実行順（タイムスタンプ順ではなく記載順）

`run_all_migrations.sh` は `grep -n "run_sql"` 結果より記載順に実行される。タイムスタンプ順ではない。

- L176: HELD `20260623_030000` (DROP INDEX offer_key) ← 封印済
- L178: HELD `20260623_050000` (DROP COLUMN condition) ← 封印済
- L221: `20260602_180000` (offer_key 再作成、condition 参照)

この順序から：HELD を解除してもL221で condition 参照 INDEX が再作成されるため収束しない。
白紙DB実行では L178(condition 削除) → L221(condition 参照 INDEX 作成) で `set -e` により停止する。

### C: 180000 の condition 参照確認

`migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql:76`:
```sql
CREATE UNIQUE INDEX uq_inventory_offer_key ON public.inventory
  (supplier_id, product_id, condition, COALESCE(unit,''), offer_type, COALESCE(ship_timing,''));
```
この1か所のみ。L221より後に condition へ触れる在庫migrationは存在しない（capture-3で確認）。

### D: 関連ADR

- ADR-093: offer_type / ship_timing 追加（20260602_180000 の元設計）
- ADR-143（新規）: 本ドリフト正式化・収束migration設計

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | HELD封印解除で収束可能か | run_all実行順を詳細追跡（L176<L221 かつ L178<L221 であることを確認） | ✅ 解消済み（封印解除では不可） |
| 2 | 末尾convergence以外の案（既存migration修正等）が可能か | ADR-143 §Decision で案ア（改変しない）を選択 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
