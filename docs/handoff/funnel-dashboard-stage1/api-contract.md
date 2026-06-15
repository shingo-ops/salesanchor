# Funnel Dashboard Stage 1 — API Contract

## 概要

フロントエンド `funnel-dashboard-frontend` が必要とする5本の API を定義する。

PR4（`feature/morimoto/funnel-dashboard-live-contract`）にて実装完了。

---

## 1. GET /api/v1/analytics/funnel

ファネル4ステージ（リード獲得 → 商談化 → 進行中 → 成約/失注）

**変更点（PR4）**: `closed_at` 基準に変更（`updated_at` 代替を廃止）

```json
{
  "month": "2026-06",
  "month_elapsed_pct": 50,
  "leads": { "target": 30, "actual": 12 },
  "conversion": { "target_rate": 20, "actual_rate": 25, "converted": 3 },
  "active": {
    "count": 5,
    "amount": 1500000,
    "coverage_pct_of_remaining_target": 80
  },
  "closed": {
    "won_target": 10,
    "won": 2,
    "won_rate": 67,
    "lost": 1
  }
}
```

- `active.coverage_pct_of_remaining_target`: 進行中商談 amount / (revenue目標 − 既成約 amount) × 100
- closed集計の条件: `deals.closed_at >= start AND closed_at < end AND closed_at IS NOT NULL AND status IN ('won', 'lost')`

---

## 2. GET /api/v1/analytics/follow-ups

要フォロー顧客3区分

**変更点（PR4）**: won_no_order が `closed_at` 基準に変更

```json
{
  "items": [
    {
      "customer_id": 1,
      "name": "取引先A",
      "segment": "won_no_order",
      "days": 35,
      "last_order_at": null,
      "last_contact_at": null,
      "assignee": "yamada"
    }
  ]
}
```

---

## 3. GET /api/v1/analytics/revenue-summary

月次売上サマリー（新規エンドポイント）

```json
{
  "revenue": { "target": 5000000.0, "actual": 2000000.0, "pace": "behind" },
  "split": { "new": 1200000.0, "repeat": 800000.0 },
  "new_customers": { "target": 0, "actual": 3 },
  "active_existing_customers": 5,
  "gross_margin": { "amount": 800000.0, "uncosted_orders": 2 }
}
```

- `revenue.pace`: `"ahead"` / `"on_track"` / `"behind"`（文字列 enum）
  - `achievement_pct = actual / target * 100`
  - `ahead`: `achievement_pct > elapsed_pct + 10`
  - `on_track`: `|achievement_pct - elapsed_pct| <= 10`
  - `behind`: `achievement_pct < elapsed_pct - 10`
  - `target <= 0` の場合: `actual > 0` → `ahead`、`actual == 0` → `on_track`
- `split.new`: 当月が初回発注の顧客の売上合計
- `gross_margin.amount`: `Σ revenue - Σ cost_total`（purchase_cost IS NOT NULL のみ）
  - `cost_total` = purchase_cost + purchase_shipping + paypal_fee + wise_fee + exchange_fee + outsource_fee + packing_fee + ad_cost + return_fee + refund_amount
- `gross_margin.uncosted_orders`: `order_financials` が未紐付け or `purchase_cost IS NULL` の注文数

---

## 4. GET /api/v1/analytics/channels

チャネル別集計（新規エンドポイント）

```json
{
  "rows": [
    {
      "initiative": "inbound",
      "channel": "instagram",
      "leads": 20,
      "conversion_rate": 40.0,
      "win_rate": 37.5,
      "avg_order_value": 300000.0,
      "gross_margin": 120000.0
    }
  ]
}
```

- `initiative`: `leads.initiative`（`'inbound'` / `'outbound'`）
- `channel`: `leads.channel_type`（NULL は `"unknown"` にまとめる）
- `conversion_rate`: `converted / leads * 100`（リードから商談化した割合）
- `win_rate`: `won / total_deals * 100`（商談のうち成約した割合）
- `avg_order_value`: 成約商談の平均金額
- `gross_margin`: 粗利額（lead → deal → order → order_financials で計算。全コスト列合算）
- `initiative IN ('inbound', 'outbound')` 以外のリードは集計除外

---

## 5. GET /api/v1/analytics/reasons

成約/失注理由別集計（新規エンドポイント）

クエリパラメータ:
- `type=won|lost`（省略時は両方）

```json
{
  "reasons": [
    {
      "label": "在庫・品揃え",
      "primary_count": 5,
      "secondary_count": 2
    }
  ],
  "memos": [
    {
      "deal_id": 123,
      "primary_label": "在庫・品揃え",
      "memo": "品揃えが豊富でした",
      "closed_at": "2026-06-10"
    }
  ]
}
```

- `reasons.primary_count`: `deal_close_reasons.is_primary = 1` の件数
- `reasons.secondary_count`: `deal_close_reasons.is_primary = 0` の件数
- `memos`: 主因（is_primary=1）を持つ商談の `close_reason_memo` 最新20件（`closed_at DESC`）
- `type` フィルタ: `close_reasons.type` で絞り込み

---

## 実装メモ

- SQLite / PostgreSQL 両互換: `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` を使用（`FILTER (WHERE ...)` 不使用）
- 日付境界: `app.services.time._jst_month_range_utc(year, month)` で JST 月次境界を UTC に変換
- scope 422: `_validate_scope(scope)` ヘルパーで検証（team / mine 以外は 422）
- scope=mine の orders: `orders` に `assigned_to` がないため `deals.assigned_to` 経由で JOIN

---

依存 PR: PR2（ファネルEP追加）、PR3（`closed_at` migration）
