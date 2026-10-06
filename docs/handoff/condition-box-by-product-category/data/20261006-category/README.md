# 商品マスタ分類（箱/単品）本番反映 データ変更

状態: **実行済み**（2026-10-06 dryrun 05:36Z・apply 05:37Z、出力は下記）

## 目的
`public.products.product_category_id` を、PO 承認済みの分類案で設定する。
設計: `docs/handoff/condition-box-by-product-category/design.md` §4-2

## PO 承認
2026-10-06 PO「y」: 箱系 220・シングル系 11・保留 45 で本番を更新する（保留 45 件は更新しない）。

## 対象と想定件数
| 分類 | product_category_id | 件数 | 操作 |
|---|---|---|---|
| 箱系 PC_BOX | 1 | 220 | NULL -> 1 |
| シングル系 PC_SINGLE | 2 | 11 | NULL -> 2 |
| 保留 | - | 45 | 更新しない |

一覧: `list.csv`（276 行。product_id, product_code, name, new_category）

## 事前確認の実測（2026-10-06・読み取りのみ）
- 対象 231 商品: product_category_id NULL かつ is_active = true が 231 件（他の値なし）
- tcg_product_categories: id=1 PC_BOX 箱系 / id=2 PC_SINGLE シングル系
- products.updated_at あり（migrations/062、更新トリガあり）

## 手順（実行は PO の permit チケット後）
SQL は psql の標準入力で流す。

1. 事前確認: 対象 231 件が全て NULL・active（上記 SELECT の再実行）
2. dryrun: `psql -U jarvis -d jarvis_db -X -v ON_ERROR_STOP=1 < dryrun.sql`
   - 最後に ROLLBACK される。出力の件数が `1=220`・`2=11` であること
3. 件数一致なら apply: 同様に `apply.sql`（dryrun と最後の 1 行以外同一。COMMIT）
4. 事後確認: 対象 231 件の product_category_id 別件数が 1=220・2=11、NULL=0

件数ガードに失敗すると RAISE EXCEPTION で全体が中止され、何も変わらない。

## 戻し方
`rollback.sql`: 件数ガード（1 が 220・2 が 11）後に NULL へ戻す。戻し後は NULL=231。

## 実行記録
### dryrun（ROLLBACK、2026-10-06 05:36Z）
```
BEGIN
DO
UPDATE 220
UPDATE 11
 product_category_id | count 
---------------------+-------
                   1 |   220
                   2 |    11
(2 rows)

ROLLBACK
```

### apply（COMMIT、2026-10-06 05:37Z）
```
BEGIN
DO
UPDATE 220
UPDATE 11
 product_category_id | count 
---------------------+-------
                   1 |   220
                   2 |    11
(2 rows)

COMMIT
```

### 事後確認（読み取り、231件のid）
```
 product_category_id | count 
---------------------+-------
                   1 |   220
                   2 |    11
(2 rows)

```
