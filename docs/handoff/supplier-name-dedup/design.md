# Design: 仕入元 name 重複解消

## 受入基準

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | name重複が0件 | `SELECT name, COUNT(*) FROM public.suppliers WHERE is_active=TRUE AND tenant_id IS NULL GROUP BY name HAVING COUNT(*) > 1` → 0行 |
| 2 | 旧21件が全てis_active=FALSE | `SELECT id, is_active FROM public.suppliers WHERE id IN (329, 314, 301, 303, 317, 318, 295, 312, 319, 290, 33, 311, 299, 309, 300, 327, 315, 308, 328, 316, 325)` → 全行 is_active=FALSE |
| 3 | supplier_prompts が新側に存在（旧側0件） | Step 6c の SELECT → 旧ID への参照が0件、新ID への参照が正しく移行 |
| 4 | inventory の supplier_id が新側に付け替え完了 | `SELECT COUNT(*) FROM public.inventory WHERE supplier_id IN (329,314,...,325)` → 0件 |
| 5 | discord_inbound_messages の supplier_id が新側に付け替え完了 | `SELECT COUNT(*) FROM public.discord_inbound_messages WHERE supplier_id IN (329,314,...,325)` → 0件 |

---

## 技術選択

**1トランザクションで FK 再割当て → 旧レコード無効化（物理削除しない）**

- 旧レコードを `is_active=FALSE` に変更し `supplier_code=NULL` にすることで、将来の調査・監査に履歴が残る
- FK 参照を先に移動してから無効化するため、FK 制約違反が発生しない
- `is_active=TRUE` の場合のみ UPDATE する条件で冪等性を保証（2回実行しても副作用なし）
- supplier_prompts は `NOT EXISTS` ガードにより新側に既存レコードがある場合は UPDATE しない（競合回避）

---

## 前回の line_name dedup との違い

- 既存の `supplier_ssot` 設計（PR #3582 / #3585 完了済み）では **line_name の正規化**（line_name=NULL の SUP-xxx を SP-xxxxx に統合）を設計した
- 今回は **name 文字列の重複**が UI・API に表出している問題の解消
- 上記2つは別軸の問題。今回のマイグレーションは line_name dedup の完了を前提とせず独立して適用可能

---

## リスクと対処

| リスク | 対処 |
|--------|------|
| 誤ったIDマッピングでデータが壊れる | DRY-RUN（BEGIN → 確認 → ROLLBACK）を必ず先に実行してマッピング確認クエリ（安全確認）の出力を確認する |
| supplier_prompts の UNIQUE 制約違反 | `NOT EXISTS` ガードにより新側に既存レコードがある場合は UPDATE をスキップ |
| 途中失敗でデータが中途半端な状態になる | 全操作を1トランザクションで包んでいるため、失敗時は自動 ROLLBACK |
| 冪等性の欠如（2回目実行で副作用） | Step 5 で `AND is_active=TRUE` 条件で冪等性を保証 |

### DRY-RUN 手順

```sql
BEGIN;
-- ... マイグレーション SQL の最後を COMMIT の代わりに ROLLBACK に変更 ...
ROLLBACK;
```

`migrations/20260924_060000_cleanup_supplier_name_duplicates.sql` の最終行を `COMMIT;` から `ROLLBACK;` に変更して実行し、Step 6 の検証クエリ結果を確認してから本番実行する。

---

## 維持の仕組み（再発防止）

name 重複の再発防止（DB UNIQUE 制約追加など）は本スコープ外。

理由:
- `name` カラムは意図的に重複可能な場合がある（同名の別人物など）
- 再発防止は ADR レベルの設計判断が必要（ADR-085 の改訂または新 ADR）
- 根本解決は手動インポートスクリプトと LINE 自動登録サービスの登録経路統合（別スコープ）

守り手: Shingo（PO）— ADR-085 改訂時に UNIQUE 制約追加の是非を判断

---

## 外部・過去事例の参照と我々への応用

PostgreSQL の FK 再割当て + ソフト削除パターンは一般的な重複解消手法。
参照: ADR-085（Supplier Master Design）、ADR-090（LINE Import Service Architecture）

過去事例: PR #3582 / #3585（supplier_ssot line_name dedup）で同様の FK 再割当てパターンを採用済み。
今回はその応用として name 重複軸に適用する。
