# recon: orders.deal_id コード側除去

> この文書は、注文から商談IDを外すときに、どこを直すかを実物で確認した記録です。
>
> 親: [deal-removal design](../../specs/db-ssot/deal-removal/design.md)

## 鮮度

- worktree: release-deal-removal-create-deal
- origin/main: 6459e9bbfc51a24c0b385906eb56bbaf29fbe915
- HEAD: 6459e9bbfc51a24c0b385906eb56bbaf29fbe915（origin/mainをfast-forward取り込み）
- git status: 前便の変更を保全した状態で継続

## バックエンド

### API

| file:line | 実測内容 |
|---|---|
| backend/app/routers/orders.py:112 | 注文レスポンス列にdeal_id |
| backend/app/routers/orders.py:119 | deal_idを変更禁止FKとして記載 |
| backend/app/routers/orders.py:250 | 一覧SQLでo.deal_idをSELECT |
| backend/app/routers/orders.py:455,460-464 | dealsテーブルを参照しdeal_idの存在を400検証 |
| backend/app/routers/orders.py:485,490,500 | INSERT列・値・payloadにdeal_id |
| backend/app/schemas/order.py:50-52 | OrderCreateでdeal_id受付 |
| backend/app/schemas/order.py:66-69 | OrderUpdateにdeal_id定義 |
| backend/app/schemas/order.py:132 | OrderResponseにdeal_id |

### 新規テナントDDL

| file:line | 実測内容 |
|---|---|
| backend/app/services/tenant.py:495 | orders.deal_idとdeals(id) FKを作成 |

本便ではDB便の対象外なので変更していない。

## フロントエンド

| file:line | 実測内容 |
|---|---|
| frontend/src/pages/orders/orders.types.ts:9 | OrderListItem.deal_id |
| frontend/src/pages/orders/orders.types.ts:51 | emptyForm.deal_id |
| frontend/src/pages/orders/OrdersFormModal.tsx:17 | form propのdeal_id型 |
| frontend/src/pages/orders/useOrdersState.ts:264 | API payloadにdeal_id |
| frontend/src/pages/orders/useOrdersState.ts:293 | 編集フォームへのdeal_id復元 |

画面上の入力欄・表示欄はなく、状態管理とAPI送信・編集復元だけだった。

## テスト分類

### X: deal_id機能そのものの検査

backend/tests/test_orders.py:

- :26-45 作成レスポンスのdeal_id一致
- :47-58 deal_id省略可とレスポンスnull
- :88-96 不正deal_idの400
- :663-680 OrderResponseのdeal_idフィールド

本便で削除した。

### Y: 補助fixtureとして使用

以下はdeal_id自体を検証せず、注文・発送・財務・仕入・手数料・注文アイテム等を検証していた。

- backend/tests/test_orders.py:60-660,709-832
- backend/tests/test_order_shipping_details.py:23-39
- backend/tests/test_order_financials.py:19-35
- backend/tests/test_order_purchase_details.py:20-36
- backend/tests/test_order_commissions.py:327-348
- backend/tests/test_order_items_ben2.py:20-73
- backend/tests/helpers_txn.py:15-21

create_lead + create_companyで会社を作り、注文payloadからdeal_idを除いた。

### Z: 取引背骨

backend/tests/test_txn_backbone_constraints.py:42-75は、lead→company→orderの作成順、company_id必須、注文のcompany_id直参照を残し、商談作成・商談へのcompany紐付け・deal_id検証を削除した。

backend/tests/test_txn_backbone_constraints.py:17-32のlead必須company検査とcompany必須order検査は変更していない。

### 商談系テスト

- backend/tests/test_quotes.py:73-87の見積商談紐付けテストは、商談機能廃止の対象として削除。
- backend/tests/test_dashboard.py:24-35の商談seedブロックは削除。
- backend/tests/test_dashboard.py:60-63のskip中test_dashboard_with_dataは未変更。
- backend/tests/test_deals.py:209-220の`test_delete_deal_with_order_returns_409`は、4通りの対照実行で今回起因と確定したため削除した。他のテストは変更していない。

## テスト失敗の切り分け

前便で今回起因と判定した2件を、指定修正後に個別再実行した。

| file:line | 事象 | 修正 | 結果 |
|---|---|---|---|
| backend/tests/helpers_txn.py:3-16、backend/tests/test_analytics.py:54-75 | `_resolve_db_session`削除によりanalyticsのseedがimport error | create_dealとは無関係なDB session解決ヘルパーを保持 | `test_funnel_with_data` green |
| backend/tests/test_order_items_ben2.py:64-106 | `db_session` fixtureとSQLAlchemy textの除去によりsplit検査が成立しない | fixture・text importを保持し、create_deal依存だけ除去 | `test_split_purchase_links` green |

既存3件（audioop不足、event loop、日付依存）は本便で触らず、mainでも同結果だった。

### test_deals.py 対照実行

| 実行対象 | 結果 | 実測 |
|---|---|---|
| 作業ツリー・対象テスト単体 | 赤 | `assert 204 == 409` |
| 作業ツリー・test_deals.py全体 | 赤 | 1 failed, 18 passed |
| origin/main・対象テスト単体 | 緑 | 1 passed |
| origin/main・test_deals.py全体 | 緑 | 19 passed |

注文APIからdeal_idを除去した結果、対象テストの注文作成payloadに残るdeal_idは保存されず、商談削除が409ではなく204になる。注文と商談の紐付け検査自体が廃止対象のため、`backend/tests/test_deals.py:209-220`を削除した。

## 本番データ実測

read-only transactionで実測した。

| tenant | orders | deal_id非NULL |
|---|---:|---:|
| tenant_001 | 0 | 0 |
| tenant_003 | 0 | 0 |
| tenant_004 | 0 | 0 |
| tenant_005 | 0 | 0 |
| tenant_006 | 26 | 0 |

全5テナントにorders_deal_id_fkeyが存在するが、非NULLデータは0件だった。

## 本便の境界

本便はAPI・画面・テストからのコード側除去のみ。backend/app/services/tenant.py:495の新規DDL、既存テナントの列/FK削除、migration登録は次便で扱う。
