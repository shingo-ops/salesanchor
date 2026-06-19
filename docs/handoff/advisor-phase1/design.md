# Advisor Phase 1 / PR-1 design

**測定日**: 2026-06-19

## 目的
`GET /api/v1/analytics/customer-orders` を追加し、顧客別の受注履歴から以下を返す。

- 受注件数
- 初回受注日 / 最終受注日
- 最終受注からの経過日数
- 継続期間
- 平均受注額
- 合計受注額
- 平均受注間隔
- 次回受注予測日

## 仕様

- ルート: `/api/v1/analytics/customer-orders`
- 認可: `dashboard.view`
- クエリ:
  - `period`: `1m / 3m / 6m / 12m`
  - `scope`: `team / mine`
- レスポンス:
  - `items: list[...]`
  - 各 item に `company_id`, `company_name`, `order_count`, `first_order_at`, `last_order_at`, `days_since_last_order`, `continuation_days`, `avg_interval_days`, `avg_order_amount`, `total_amount`, `predicted_next_order_at`

## 実装方針

1. 既存 `analytics.py` の `scope` バリデーションと期間境界の書き方に合わせる。
2. `scope=mine` のときは `orders.deal_id` から `deals.assigned_to = current_user.id` に絞る。
3. 集計は SQL の戻りを Python 側で会社単位にまとめ、日付差分で以下を計算する。
   - `continuation_days`
   - `avg_interval_days`
   - `predicted_next_order_at`
4. 受注 1 件の会社は返却するが、`avg_interval_days` と `predicted_next_order_at` は `null` にする。
5. `period` が不正なら 422 を返す。

## テスト

- 空データで 200 / `items=[]`
- 会社別に複数注文を入れたときの集計が正しい
- 1 件のみの会社で interval / prediction が `null`
- `scope=mine` で担当外会社が混ざらない

## 運用メモ

- migration なし
- deploy.yml 変更なし
- process-artifacts gate では本ファイルと `recon.md` を参照する

