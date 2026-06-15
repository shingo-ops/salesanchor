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
  "active": { "count": 5, "amount": 1500000 },
  "closed": {
    "won": 2, "lost": 1, "won_rate": 67,
    "won_target": 10, "coverage_pct": 80
  }
}
```

closed集計の条件: `deals.closed_at >= start AND closed_at < end AND closed_at IS NOT NULL AND status IN ('won', 'lost')`

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
  "month": "2026-06",
  "target": 5000000.0,
  "actual": 2000000.0,
  "pace": 80,
  "split": { "new": 1200000.0, "repeat": 800000.0 },
  "new_customers": 3,
  "active_existing_customers": 5,
  "gross_margin": 42.5,
  "uncosted_orders": 2
}
```

- `pace`: `actual / (target * elapsed_pct / 100) * 100`（整数）
- `split.new`: 当月が初回発注の顧客の売上合計
- `gross_margin`: `(Σ revenue - Σ purchase_cost) / Σ revenue * 100`（purchase_cost IS NOT NULL のみ）
- `uncosted_orders`: `order_financials` が未紐付け or `purchase_cost IS NULL` の注文数

---

## 4. GET /api/v1/analytics/channels

チャネル別集計（新規エンドポイント）

```json
{
  "month": "2026-06",
  "channels": [
    {
      "channel": "instagram",
      "leads": 20,
      "deals": 8,
      "won": 3,
      "revenue": 900000.0
    }
  ]
}
```

- `channel`: `leads.channel_type`（NULL は "unknown" にまとめる）
- `deals`/`won`/`revenue`: `deals.closed_at` が当月範囲内かつ `closed_at IS NOT NULL`

---

## 5. GET /api/v1/analytics/reasons

成約/失注理由別集計（新規エンドポイント）

```json
{
  "month": "2026-06",
  "reasons": [
    {
      "reason_id": 1,
      "label": "在庫・品揃え",
      "outcome": "won",
      "count": 5,
      "memos": ["メモ1", "メモ2"]
    }
  ]
}
```

- `outcome`: `close_reasons.type`（"won" or "lost"）
- `memos`: `deals.close_reason_memo` の最新10件（`closed_at DESC`）

---

## 実装メモ

- SQLite / PostgreSQL 両互換: `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` を使用（`FILTER (WHERE ...)` 不使用）
- 日付境界: `app.services.time._jst_month_range_utc(year, month)` で JST 月次境界を UTC に変換
- scope 422: `_validate_scope(scope)` ヘルパーで検証（team / mine 以外は 422）
- scope=mine の orders: `orders` に `assigned_to` がないため `deals.assigned_to` 経由で JOIN

---

依存 PR: PR2（ファネルEP追加）、PR3（`closed_at` migration）
