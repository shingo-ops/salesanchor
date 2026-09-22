# Design: fix-phase2c-fk-type-guard

## 対象ADR

ADR-1002

## KGI

デプロイが `20260922_040000_fix_phase2c_fk_blocker.sql` でエラーなく完了する（COMMIT が出力される）

| 基準 | 検証方法 |
|------|---------|
| COMMIT 出力 | デプロイログで `COMMIT` が表示される |
| エラーなし | `ERROR:` が含まれない |
| NOTICE: Skipped | `product_id` が INTEGER の場合は NOTICE で skip を報告 |

## 変更内容

`migrations/20260922_040000_fix_phase2c_fk_blocker.sql` の DO ブロックに型チェックガードを追加。

### 変更前

`product_id` カラムの存在のみチェックし、型チェックなしで FK 追加。

### 変更後

`product_id` の `atttypid` を `pg_attribute` で取得し、UUID でない場合は FK 追加をスキップして NOTICE を出力。

## 外部事例

同パターンの型ガード:
- PR #3672: `20260914_140000` Step2 の work_id 型チェック
- PR #3676: `20260914_140000` Step3 の各テーブル型チェック

## 守り手

- 既存 FK の DROP（`DROP CONSTRAINT IF EXISTS`）は影響なし
- FK 追加のみスキップ（データ変更・DDL 変更なし）
- 冪等: FK が存在する場合もスキップ
