# recon: quotes.deal_id コード側除去

> この文書は、見積から商談IDを外すときに、どこを直すかを実物で確認した記録です。
>
> 親: [deal-removal design](../../specs/db-ssot/deal-removal/design.md)

## 鮮度

- `git fetch --prune` 実行済み
- worktree: `release/deal-removal-quotes-dealid`
- origin/main: `4338b71e7ad935154169a14b770d8c6f9a22057c`
- HEAD: `4338b71e7ad935154169a14b770d8c6f9a22057c`
- 作業開始時の `git status`: 空

## バックエンド

### API

| file:line | 実測内容 | 分類 |
|---|---|---|
| backend/app/routers/quotes.py:44 | 共通SELECT列に`deal_id` | X |
| backend/app/routers/quotes.py:80 | 一覧APIで`deal_id`クエリを受付 | X |
| backend/app/routers/quotes.py:98-100 | `q.deal_id`で一覧フィルタ | X |
| backend/app/routers/quotes.py:106,122 | 一覧SELECT・レスポンスに共通列を展開 | X |
| backend/app/routers/quotes.py:137,145 | 詳細SELECT・レスポンスに共通列を展開 | X |
| backend/app/routers/quotes.py:186-198 | 作成時のdeal存在・lead整合性検証 | X |
| backend/app/routers/quotes.py:214,219,226 | INSERT列・値・payloadに`deal_id` | X |
| backend/app/routers/quotes.py:275,278 | 作成後再取得・レスポンスに共通列を展開 | X |
| backend/app/routers/quotes.py:294,315,328 | 更新前取得・RETURNING・レスポンスに共通列を展開 | X |
| backend/app/routers/quotes.py:344,356 | send後RETURNING・レスポンスに共通列を展開 | X |
| backend/app/routers/quotes.py:372,385 | approve後RETURNING・レスポンスに共通列を展開 | X |
| backend/app/routers/quotes.py:401,413 | reject後RETURNING・レスポンスに共通列を展開 | X |
| backend/app/routers/quotes.py:428 | delete時の旧値取得に共通列を展開 | X |

`backend/app/services/` 配下、および他router・serviceに`quotes.deal_id`を読む箇所はなかった。

### スキーマ

| file:line | 実測内容 | 分類 |
|---|---|---|
| backend/app/schemas/quote.py:41 | `QuoteCreate`で`deal_id`を受付・検証 | X |
| backend/app/schemas/quote.py:93 | `QuoteResponse`に`deal_id`を返却 | X |

### DDL（本便では変更しない）

| file:line | 実測内容 |
|---|---|
| backend/app/services/tenant.py:819-823 | 新規テナントの`quotes.deal_id`列と`deals(id)` FK |
| backend/app/services/tenant.py:844-846 | quotesのインデックスはcompany/contact/leadのみ。deal_id専用インデックスなし |

DDLと既存DBの列・FK削除は次便の対象とする。

## フロントエンド

| file:line | 実測内容 | 分類 |
|---|---|---|
| frontend/src/pages/quotes/QuotesPage.tsx:24 | 一覧用型に`deal_id` | X |
| frontend/src/pages/quote-detail/QuoteDetailPage.tsx:38 | 詳細用型に`deal_id` | X |

画面上の入力欄・表示欄・API送信処理は存在しなかった。作成API送信は`frontend/src/pages/quote-create/QuoteCreatePage.tsx:111-128`で、payloadに`deal_id`は含まれていない。

## テスト

### X：deal_id機能そのものの検査

| file:line | 実測内容 |
|---|---|
| backend/tests/test_quotes.py:367-376 | `test_deal_not_found`。存在しない`deal_id`の作成要求が404になることを検査 |

### Y：補助的に使っているだけ

| file:line | 実測内容 |
|---|---|
| backend/tests/test_quotes.py:408 | QuoteResponse fixtureの`deal_id: None`。主目的はcontact_id NULL耐性 |
| backend/tests/conftest.py:824 | SQLiteテスト用quotes DDLの`deal_id`列・FK |

`backend/tests/conftest.py:1190`などの`deal_close_reasons.deal_id`、`converted_deal_id`、analytics上の別概念の`deal_id`はquotes.deal_idではない。

## 本番データ実測（read-only）

prod1の`/home/ubuntu/salesanchor`でSQLファイルをコンテナへ`docker cp`し、`psql -f`で照会した。

| tenant | quotes行数 | deal_id非NULL |
|---|---:|---:|
| tenant_001 | 0 | 0 |
| tenant_003 | 0 | 0 |
| tenant_004 | 0 | 0 |
| tenant_005 | 0 | 0 |
| tenant_006 | 0 | 0 |

tenant_002にはquotes relationがない。

FKは5本。

- tenant_001.quotes_deal_id_fkey
- tenant_003.quotes_deal_id_fkey
- tenant_004.quotes_deal_id_fkey
- tenant_005.quotes_deal_id_fkey
- tenant_006.quotes_deal_id_fkey

定義はいずれも`FOREIGN KEY (deal_id) REFERENCES <tenant>.deals(id)`。deal_id専用インデックスは0本。

## 本便の境界

本便はAPI・スキーマ・画面型・テストからのコード側除去のみ。`backend/app/services/tenant.py:819-823`の新規DDL、既存テナントの列/FK削除、本番DB変更は次便で扱う。
