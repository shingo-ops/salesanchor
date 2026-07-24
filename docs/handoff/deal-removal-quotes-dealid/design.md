# design: quotes.deal_id コード側除去

> この文書は、見積APIと画面の型から商談IDを外す設計です。
>
> 見積から商談IDを外しても、見積そのものや会社・担当者・リードの情報は残ります。
>
> 親: [deal-removal design](../../specs/db-ssot/deal-removal/design.md)

**対象ADR**: ADR-121

**recon**: [docs/handoff/deal-removal-quotes-dealid/recon.md](recon.md)

## 方針

- `QuoteCreate`から`deal_id`の受付・検証を除去する。
- quotes一覧の`deal_id`フィルタを除去する。
- quotesのSELECT・INSERT・RETURNING・レスポンスから`deal_id`を除去する。
- 一覧・詳細画面の型宣言から`deal_id`を除去する。
- deal_id機能そのものを検査する`test_deal_not_found`を削除する。
- 補助fixtureの`deal_id`だけを除去し、他の検証内容・期待値は変更しない。
- 新規テナントDDL、既存DBの列・FK削除は次便で実施する。

## 外部・過去事例の参照と我々への応用

外部事例の追加参照は不要。本便は、#3073で実施した`orders.deal_id`除去と同じ手順の延長であり、reconで使用箇所を確定し、API・型・テストをコード側から除去してから、DB列・FKを次便で削除する。

- #3073: orders.deal_idのコード側除去。今回もDB定義を次便に分離する。
- ADR-121: deal-removal段階の設計正本。本便はquotesを対象にしたコード側の一便である。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| quotes APIがdeal_idを受付・検証・保存・返却しない | `rg -n "deal_id" backend/app/routers/quotes.py backend/app/schemas/quote.py` が0件 |
| 見積一覧・詳細の型にdeal_idがない | `rg -n "deal_id" frontend/src/pages/quotes/QuotesPage.tsx frontend/src/pages/quote-detail/QuoteDetailPage.tsx` が0件 |
| deal_id機能そのもののテストがない | `backend/tests/test_quotes.py:367-376`のtest_deal_not_found削除とfixture確認 |
| テスト用quotes DDLにdeal_idがない | `backend/tests/conftest.py:824`の列削除を確認 |
| 既存の見積検証内容を緩めていない | backend全体テストの結果を確認 |
| フロントエンド型チェック・ビルドが成功する | `npm run build`の生出力を確認 |
| 本番DBを書き換えていない | 本便では本番DBへの接続・書き込みを実施しない |

## 変更対象

- `backend/app/routers/quotes.py`
- `backend/app/schemas/quote.py`
- `frontend/src/pages/quotes/QuotesPage.tsx`
- `frontend/src/pages/quote-detail/QuoteDetailPage.tsx`
- `backend/tests/test_quotes.py`
- `backend/tests/conftest.py`
- `docs/handoff/deal-removal-quotes-dealid/recon.md`
- `docs/handoff/deal-removal-quotes-dealid/design.md`
- `.claude-pipeline/active-work.md`

`backend/app/services/tenant.py`は次便のDB変更対象であり、本便では変更しない。

## 維持の仕組み

- 守り手: `.github/workflows/` の process-artifacts gate
- 対象: 見積への`deal_id`再混入
- reconとdesignをPR本文の標準ワークフロー確認で宣言し、変更ファイルの範囲と成果物をゲートで確認する。
- DB列・FKの削除は別便に分離し、コード側とDB側の変更境界を維持する。
