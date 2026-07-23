# design: orders.deal_id コード側除去

> この文書は、注文を会社へ直接つなぎ、商談IDを注文から外す設計です。
>
> 親: [deal-removal design](../../specs/db-ssot/deal-removal/design.md)

## 方針

注文の正本となる関係をcompany_idへ統一する。

- OrderCreate / OrderUpdate / OrderResponseからdeal_idを除去する。
- 注文routerのdeal存在確認、INSERT、SELECT、レスポンスからdeal_idを除去する。
- 注文画面の型、初期値、payload、編集復元からdeal_idを除去する。
- テストfixtureはlead→company→orderへ変更する。
- 商談紐付けそのものを検査するテストは削除する。
- DB列とFKは次便で削除し、本便では触らない。

## 削除した検査

以下はorders.deal_id機能そのものの検査なので削除した。

- test_orders.pyの作成レスポンスdeal_id一致
- test_orders.pyのdeal_id省略可
- test_orders.pyの不正deal_id拒否
- test_orders.pyのOrderResponse deal_idフィールド
- test_quotes.pyの見積商談紐付け
- txn backbone内の商談作成・商談company紐付け・注文deal_id検証
- test_deals.pyの注文・商談紐付けによる商談削除409検査（4通りの対照実行で今回起因と確認）

商談API自体のtest_deals.pyは別便の対象であり、本便では変更していない。

## 維持した検査

- company_id必須
- contact_idの会社所属検証
- lead→company→orderの作成順
- orderのcompany_id直参照
- 注文番号重複、状態、金額、検索、一覧、集計、権限、支払、発送、財務、仕入、手数料、注文アイテム
- 商談なしの見積作成と見積本体のCRUD
- dashboardのskip中テスト

## 弊害・トレードオフ

- 注文から商談を逆引きできなくなる。
- 注文作成時のdeal_id存在検証はなくなる。
- 既存DBの列とFKは本便では残るため、コードとDB定義が一時的に異なる。
- 本番のordersは26行、deal_id非NULLは0件なので、次便の列/FK削除によるデータ損失はない。

## 受入基準

- orders APIがdeal_idを受付・保存・返却しない。
- 注文画面の型・payload・編集復元にdeal_idがない。
- helpers_txn.pyにcreate_deal定義がない。
- backend/testsのcreate_deal呼び出しがない。
- 注文関連テストがcompany_id直参照で成立する。
- 今回変更に起因した2件のテストがgreenになる。
- backend/app/services/tenant.pyの新規DDLと既存DBの列/FKは次便まで変更しない。

## テスト失敗への対応

create_deal廃止時に誤って削除した、analytics用のDB session解決ヘルパーと注文アイテム検査用の`db_session` fixture・SQLAlchemy `text` importを復元した。検証内容や期待値は変更していない。audioop不足、event loop、日付依存の既存3件には触れていない。

## 維持の仕組み

- 守り手: .github/workflows/のprocess-artifacts gate
- 対象: 注文へのdeal_idおよび商談依存の注文テスト補助が再混入すること
- 次便で既存tenantのFK・列削除と新規tenant DDL更新を行う。
