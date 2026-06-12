# API Contract: ファネルダッシュボード 第1弾

**バージョン**: v1 (ドラフト)  
**作成**: 2026-06-13  
**オーナー**: 両セッション共通（フロント + バックエンド）  
**更新ルール**: バックエンドがレスポンス形式を変更する場合は必ずこのファイルを先に更新すること（黙ってズラさない）。フロントのモック fixture も同形で作ること。

---

## エンドポイント一覧

| EP | 説明 | 月指定 |
|---|---|---|
| GET /analytics/funnel | ファネル段階別 KPI | `?month=YYYY-MM` |
| GET /analytics/revenue-summary | 売上・粗利・顧客数サマリ | `?month=YYYY-MM` |
| GET /analytics/follow-ups | 要フォロー顧客リスト | なし |
| GET /analytics/channels | チャネル別分析 | `?month=YYYY-MM` |
| GET /analytics/reasons | 成約・失注理由 | `?type=won|lost&month=YYYY-MM` |

※ 月指定はすべて JST 基準  
※ プレイヤービューは各 EP に `scope=mine` パラメータを追加（詳細は下記）

---

## GET /analytics/funnel?month=YYYY-MM

```json
{
  "month": "2026-06",
  "month_elapsed_pct": 40,
  "leads": {
    "target": 30,
    "actual": 22
  },
  "conversion": {
    "target_rate": 50,
    "actual_rate": 41,
    "converted": 9
  },
  "active": {
    "count": 18,
    "amount": 8400000,
    "coverage_pct_of_remaining_target": 175
  },
  "closed": {
    "won_target": 10,
    "won": 6,
    "won_rate": 35,
    "lost": 4
  }
}
```

**フィールド定義:**
- `month_elapsed_pct`: 当月の経過率（0-100 整数）
- `leads.target/actual`: 月次リード獲得 目標/実績件数
- `conversion.target_rate/actual_rate`: 商談化率 目標/実績（%・整数）
- `conversion.converted`: 商談化件数
- `active.count`: 現在進行中商談件数
- `active.amount`: 進行中商談 合計金額（円）
- `active.coverage_pct_of_remaining_target`: 残り目標に対する進行中商談カバー率（%・整数）
- `closed.won_target`: 月次成約目標件数
- `closed.won`: 実績成約件数
- `closed.won_rate`: 成約率（%・整数）
- `closed.lost`: 失注件数

**プレイヤービュー**: `?month=YYYY-MM&scope=mine`（`assigned_to = :uid` フィルタ適用）

---

## GET /analytics/revenue-summary?month=YYYY-MM

```json
{
  "revenue": {
    "target": 8000000,
    "actual": 3200000,
    "pace": "on_track"
  },
  "split": {
    "new": 1100000,
    "repeat": 2100000
  },
  "new_customers": {
    "target": 8,
    "actual": 4
  },
  "active_existing_customers": 26,
  "gross_margin": {
    "amount": 960000,
    "uncosted_orders": 0
  }
}
```

**フィールド定義:**
- `revenue.pace`: `"ahead"` | `"on_track"` | `"behind"`（達成率 vs 月経過率の比較）
  - `ahead`: 達成率 > 月経過率 + 10%
  - `on_track`: |達成率 - 月経過率| ≤ 10%
  - `behind`: 達成率 < 月経過率 - 10%
- `split.new/repeat`: 新規顧客/リピート顧客からの売上（円）
  - 新規: 当月が初回発注の会社
  - リピート: 過去発注実績あり
- `active_existing_customers`: 過去12ヶ月以内に発注があった既存顧客数
- `gross_margin.uncosted_orders`: 仕入コスト未入力の発注件数（0より大きい場合にフロントで注記表示）

**プレイヤービュー**: `?month=YYYY-MM&scope=mine`（自担当のみ集計）

---

## GET /analytics/follow-ups

```json
{
  "items": [
    {
      "customer_id": 1,
      "name": "Card Haven LLC",
      "segment": "order_stopped",
      "days": 62,
      "last_order_at": "2026-04-11",
      "last_contact_at": "2026-05-05",
      "assignee": "佐藤"
    }
  ]
}
```

**フィールド定義:**
- `segment`: 区分
  - `"order_stopped"`: 発注停止（最終発注から30日超）
  - `"no_repeat_after_first"`: 初回後未フォロー（初回発注から45日以内に2回目なし）
  - `"won_no_order"`: 成約後未発注（成約後30日超で発注なし）
- `days`: 最終発注 or 成約からの経過日数
- `last_order_at`: ISO 8601 日付文字列（nullable）
- `last_contact_at`: 最終接触日（nullable）
- `assignee`: 担当者名

**プレイヤービュー**: `?scope=mine`（自担当顧客のみ）

---

## GET /analytics/channels?month=YYYY-MM

```json
{
  "rows": [
    {
      "initiative": "inbound",
      "channel": "instagram",
      "leads": 8,
      "conversion_rate": 50,
      "win_rate": 40,
      "avg_order_value": 240000,
      "gross_margin": 64000
    }
  ]
}
```

**フィールド定義:**
- `initiative`: `"inbound"` | `"outbound"`
- `channel`: チャネル種別（文字列。例: `"instagram"`, `"web_form"`, `"messenger"`, `"referral"`, `"unknown"`）
- `conversion_rate/win_rate`: %（整数）
- `avg_order_value/gross_margin`: 円（整数）

**プレイヤービュー**: `?month=YYYY-MM&scope=mine`

---

## GET /analytics/reasons?type=won|lost&month=YYYY-MM

```json
{
  "reasons": [
    {
      "label": "在庫・品揃え",
      "primary_count": 3,
      "secondary_count": 2
    }
  ],
  "memos": [
    {
      "deal_id": 12,
      "primary_label": "在庫・品揃え",
      "memo": "探していたBOXが揃っていた",
      "closed_at": "2026-06-05"
    }
  ]
}
```

**フィールド定義:**
- `type` クエリパラメータ: `"won"` | `"lost"`
- `reasons[].primary_count`: 主因として選択された回数
- `reasons[].secondary_count`: 副因として選択された回数
- `memos[].memo`: 一言メモ（NULL の場合は除外）

---

## 変更ログ

| 日付 | バージョン | 変更内容 | 担当 |
|---|---|---|---|
| 2026-06-13 | v1 | 初版作成（ハンドオフから抽出） | フロントセッション |
