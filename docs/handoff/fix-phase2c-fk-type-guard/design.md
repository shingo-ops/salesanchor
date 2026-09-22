# Design: fix-phase2c-fk-type-guard

## 対象ADR

ADR-1002

## KGI

デプロイが `migrations/20260922_040000_fix_phase2c_fk_blocker.sql` でエラーなく完了する（COMMIT が出力される）

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

## 外部・過去事例の参照と我々への応用

同パターンの型ガード（本プロジェクト内）:
- PR #3672: `20260914_140000` Step2 の work_id 型チェック（`pg_attribute.atttypid` で UUID 判定）
- PR #3676: `20260914_140000` Step3 の各テーブル型チェック（product_search_keywords 等 4テーブル）

応用: 同じ `pg_attribute.atttypid = pg_type.oid WHERE typname='uuid'` パターンを `public.analysis_results` の FK 追加前チェックに適用。

## 維持の仕組み

守り手: 人手で守る（型ガードは永続的に有効・追加メンテ不要）

- 本マイグレーションは冪等（FK 存在確認済み・DROP IF EXISTS）
- 型変換後の状態では「Skipped」NOTICE が出力され、次回デプロイも安全に通過する
- 将来 `product_id` が UUID に戻ることはないため、このガードは永続的に有効

## 守り手

- 既存 FK の DROP（`DROP CONSTRAINT IF EXISTS`）は影響なし
- FK 追加のみスキップ（データ変更・DDL 変更なし）
- 冪等: FK が存在する場合もスキップ
