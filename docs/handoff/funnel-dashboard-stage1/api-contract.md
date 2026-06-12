# API Contract — ファネルダッシュボード 第1弾

**正本**: このファイルがバックエンド・フロントエンド両セッションの唯一の真実  
**更新ルール**: PR2/3 でレスポンス形状を変える場合は **このファイルを先に更新してコミット**。黙ってズラさない。  
**参照**: `docs/handoff/funnel-dashboard-stage1/design.md` / `docs/adr/ADR-138-funnel-dashboard-stage1.md`

---

## CHANGELOG

| Date | PR | 変更内容 | 担当 |
|---|---|---|---|
| 2026-06-12 | — | 初版作成（15項目 recon + design.md 基準） | Hikky-dev |

---

## 凡例

- `→ EXTEND` : 既存 EP のレスポンスに**フィールドを追加**（既存フィールドは変更しない）
- `→ NEW`    : 新規エンドポイント
- `→ UNCHANGED` : このコントラクトで変更しない（フロントは現行実装を参照）

---

## 1. 既存エンドポイント（→ UNCHANGED）

以下は PR1〜6 の範囲で **形状変更なし**。フロントは現行実装を参照。

| EP | 現行レスポンス型 | 備考 |
|---|---|---|
| `GET /analytics/stalled-deals` | `StalledDealsReport` | 停滞案件（days_stalled ベース） |
| `GET /analytics/followups` | `FollowUpReport` | タスクリマインド（next_action_date ベース）。要フォロー顧客とは別概念 |
| `GET /analytics/forecast` | `ForecastResponse` | 今月着地予測 |
| `GET /analytics/monthly-revenue` | `RevenueChartResponse` | 受注グラフ |
| `GET /goals/summary` | — | PR4 で `won_count`/`gross_profit` 目標値を返すが形状拡張のみ（後述 §5） |

---

## 2. GET /analytics/summary → EXTEND（PR2）

**変更**: `orders` オブジェクトに `gross_profit` / `gross_profit_margin` / `cost_coverage_rate` を追加。  
`customers` オブジェクトを新規追加。  
**既存フィールドは変更しない。**

### Request

```
GET /analytics/summary?period={period}&tab={tab}&user_id={user_id}
```

| param | 型 | デフォルト | 値 |
|---|---|---|---|
| `period` | string | `"1m"` | `1w` / `1m` / `3m` / `6m` / `12m` |
| `tab` | string | `"team"` | `"team"` / `"individual"` |
| `user_id` | integer? | null | individual 時のユーザーID（省略時は自分） |

### Response（変更後）

```jsonc
{
  "period": "1m",
  "start_date": "2026-05-13",
  "end_date": "2026-06-12",

  // 既存（変更なし）
  "leads": {
    "total": 15,
    "converted": 8,
    "excluded": 1,
    "conversion_rate": 53.3
  },

  // 既存（変更なし）
  "deals": {
    "total": 10,
    "active": 7,
    "won": 3,
    "win_rate": 30.0
  },

  // 既存フィールドは変更なし。以下を追加
  "orders": {
    "total_revenue": 1500000.0,
    "order_count": 10,
    "active_count": 3,
    // ↓ PR2 で追加
    "gross_profit": 450000.0,          // purchase_cost 入力済み受注のみ集計
    "gross_profit_margin": 30.0,       // %。null = 受注ゼロ
    "cost_coverage_rate": 100.0        // purchase_cost IS NOT NULL(≠0) な受注 / 全受注 %
  },

  // ↓ PR2 で追加（新規オブジェクト）
  "customers": {
    "new_count": 4,                    // 期間内に初回受注があった company の数
    "active_existing_count": 6         // 期間内に2回目以降の受注があった company の数
  },

  // 既存（変更なし）
  "comparison": {
    "leads_total":    { "pct": 25.0, "direction": "up" },
    "leads_cv_rate":  { "pct": -5.0, "direction": "down" },
    "deals_active":   { "pct": null, "direction": "flat" },
    "deals_won":      { "pct": 50.0, "direction": "up" },
    "deals_win_rate": { "pct": 10.0, "direction": "up" },
    "orders_revenue": { "pct": 20.0, "direction": "up" },
    "orders_count":   { "pct": 15.0, "direction": "up" }
  }
}
```

**フロント注意**:
- `cost_coverage_rate < 100` の場合、粗利カードに注記 UI を表示する（設計 §2a）
- `gross_profit` は `purchase_cost > 0（または IS NOT NULL）` な受注のみ計上（NULL許容化後）

---

## 3. GET /analytics/funnel → NEW（PR2）

ファネル段階別の実績・目標対比。ボトルネック強調に使う `is_bottleneck` を含む。

### Request

```
GET /analytics/funnel?period={period}&tab={tab}&user_id={user_id}
```

params は `/analytics/summary` と同じ。

### Response

```jsonc
{
  "period": "1m",
  "tab": "team",

  // ファネル4ステージ（固定順序）
  "stages": [
    {
      "key": "leads",            // i18n: t("funnel.leads") = "リード獲得"
      "actual": 15,              // 期間内に作成されたリード数
      "target": 20,              // goals テーブルの月次目標（kpi_type="lead_count"）。未設定は null
      "achievement_rate": 75.0,  // actual/target*100。target が null の場合は null
      "is_bottleneck": false     // achievement_rate が最低のステージ（target あり中）に true
    },
    {
      "key": "conversion",       // i18n: t("funnel.conversion") = "商談化"
      "actual": 8,               // 期間内に converted_deal_id が付いたリード数
      "target": null,
      "achievement_rate": null,
      "is_bottleneck": false
    },
    {
      "key": "in_progress",      // i18n: t("funnel.in_progress") = "進行中"
      "actual": 7,               // 現時点でのオープン商談数（期間非依存スナップショット）
      "target": null,
      "achievement_rate": null,
      "is_bottleneck": false
    },
    {
      "key": "won",              // i18n: t("funnel.won") = "成約"
      "actual": 3,               // 期間内に status='won' になった商談数（closed_at ベース。PR1以前は updated_at で近似）
      "target": 5,               // kpi_type="won_count"
      "achievement_rate": 60.0,
      "is_bottleneck": true      // 達成率が最低
    }
  ],

  // ステージ間の転換率
  "conversion_rates": {
    "lead_to_deal": 53.3,        // stage[conversion].actual / stage[leads].actual * 100
    "deal_to_won": 37.5          // stage[won].actual / stage[conversion].actual * 100
  }
}
```

**フロント注意**:
- `stages` の順序は固定（leads → conversion → in_progress → won）
- `is_bottleneck` は `target` が設定されているステージの中で `achievement_rate` が最低の1件のみ `true`。全ステージ `target=null` の場合は全件 `false`
- `in_progress` の `actual` は期間フィルタなしのリアルタイム件数

---

## 4. GET /analytics/channel → NEW（PR3）

チャネル別のリード数・転換率・粗利分析（下層ページ用）。

### Request

```
GET /analytics/channel?period={period}
```

| param | 型 | デフォルト | 備考 |
|---|---|---|---|
| `period` | string | `"1m"` | `1w` / `1m` / `3m` / `6m` / `12m` |

※ チャネル分析は team のみ（tab パラメータなし）

### Response

```jsonc
{
  "period": "1m",
  "channels": [
    {
      "channel_type": "instagram",       // leads.channel_type の値。"unknown" = その他・不明
      "initiative": "inbound",           // "inbound" / "outbound" / null（未分類）
      "lead_count": 10,
      "converted_count": 6,              // converted_deal_id IS NOT NULL
      "deal_conversion_rate": 60.0,      // converted_count / lead_count * 100
      "won_count": 3,
      "won_rate": 50.0,                  // won_count / converted_count * 100
      "avg_deal_amount": 350000.0,       // 成約商談の平均 amount
      "gross_profit": 120000.0,          // 期間内受注の粗利合計（coverage_rate < 100 なら注記対象）
      "gross_margin_rate": 34.3          // gross_profit / revenue * 100。受注ゼロなら null
    },
    {
      "channel_type": "messenger",
      "initiative": "inbound",
      "lead_count": 5,
      "converted_count": 3,
      "deal_conversion_rate": 60.0,
      "won_count": 2,
      "won_rate": 66.7,
      "avg_deal_amount": 280000.0,
      "gross_profit": 90000.0,
      "gross_margin_rate": 32.1
    },
    {
      "channel_type": "unknown",         // event / manual / null などの未分類まとめ
      "initiative": null,
      "lead_count": 5,
      "converted_count": 1,
      "deal_conversion_rate": 20.0,
      "won_count": 0,
      "won_rate": 0.0,
      "avg_deal_amount": null,
      "gross_profit": 0.0,
      "gross_margin_rate": null
    }
  ]
}
```

**フロント注意**:
- `channel_type` の表示名は i18n キー `channel.{channel_type}` で引く（例: `channel.instagram` = "Instagram"）
- `initiative` の表示は `initiative.{value}_short`（例: `initiative.inbound_short` = "顧客起点"）
- `channel_type="unknown"` は常に末尾に表示する

---

## 5. GET /analytics/follow-ups → NEW（PR3）

要フォロー顧客の3区分カウント（第1層カード用）。  
⚠️ 既存の `GET /analytics/followups`（タスクリマインド）とは**別 EP・別概念**。混同しないこと。

### Request

```
GET /analytics/follow-ups?tab={tab}&user_id={user_id}
```

### Response

```jsonc
{
  "tab": "team",

  // しきい値（パラメータ化・後から調整可能）
  "thresholds": {
    "post_won_days": 30,
    "order_interval_multiplier": 1.5,
    "first_order_days": 45
  },

  "categories": {
    // 成約後・未発注（成約から30日超・受注ゼロ）
    "post_won_no_order": {
      "count": 4
    },
    // 発注が止まった（その顧客の平均発注間隔×1.5 を超過）
    "order_interval_exceeded": {
      "count": 5
    },
    // 初回後フォロー要（初回受注後45日・リピートなし）
    "first_order_followup": {
      "count": 3
    }
  },

  "total": 12   // 3区分の重複排除合計（1社が複数区分に該当しても1回カウント）
}
```

---

## 6. GET /analytics/follow-ups/list → NEW（PR3・下層用）

要フォロー顧客の一覧（下層ページのドリルダウン）。

### Request

```
GET /analytics/follow-ups/list?category={category}&tab={tab}&user_id={user_id}
```

| param | 値 |
|---|---|
| `category` | `post_won_no_order` / `order_interval_exceeded` / `first_order_followup` |

### Response

```jsonc
{
  "category": "post_won_no_order",
  "items": [
    {
      "company_id": 1,
      "company_name": "ABC Trading",
      "deal_id": 10,                       // トリガーになった商談 ID（ドロワー接続用）
      "days_elapsed": 42,                  // 経過日数（区分ごとの意味は異なる）
      "last_order_at": "2026-04-20",       // null = 受注なし
      "last_meta_contact_at": "2026-05-10", // meta_messages ベース。null = 接触なし
      "assigned_to_id": 3,
      "assigned_to_username": "tanaka"
    }
  ],
  "total": 4
}
```

**フロント注意**:
- `deal_id` / `company_id` は既存ドロワー（`useRecordDrawer`）の接続 ID に使う
- `last_meta_contact_at` は参考表示のみ（第1弾）。cross-channel 統合は第2弾

---

## 7. PATCH /deals/{id} → EXTEND（PR3）

won/lost 遷移時に `close_reason_memo` と `close_reasons` を受け取る。  
**既存フィールドは変更しない。**

### Request body（追加フィールドのみ記載）

```jsonc
{
  // 既存フィールド（変更なし）
  "status": "won",

  // ↓ PR3 で追加（status が "won"/"lost" の場合のみ有効）
  "close_reason_memo": "在庫が揃っていてスピードが決め手だった",  // null 許容（既存データ後方互換）
  "close_reasons": [                 // null / 空配列 許容（既存データ後方互換）
    { "reason_id": 2, "is_primary": true },   // 主因（1件）
    { "reason_id": 5, "is_primary": false }   // 副因（0件以上）
  ]
}
```

### Response（追加フィールドのみ記載）

```jsonc
{
  // 既存フィールド（変更なし）
  // ↓ PR1（deals.closed_at 追加）以降
  "closed_at": "2026-06-12T14:30:00+09:00"  // null = 未確定（open状態）
}
```

**バリデーション**:
- `close_reasons` に `is_primary: true` が2件以上ある場合は 422
- `reason_id` がそのテナントの `close_reasons` に存在しない場合は 422
- 既存の won/lost レコードへの再 PATCH で `close_reasons` を省略しても既存レコードは消えない

---

## 8. POST /leads, PATCH /leads/{id} → EXTEND（PR3）

### Request body（追加フィールドのみ）

```jsonc
{
  // ↓ PR3 で追加
  "initiative": "inbound",     // "inbound" / "outbound" / null
  "channel_type": "instagram"  // "instagram" / "messenger" / "web_form" / "sns" / "referral" / "unknown" / null
}
```

### Response（追加フィールドのみ）

```jsonc
{
  // 既存フィールド（変更なし）
  // ↓ PR3 以降に追加
  "initiative": "inbound",
  "channel_type": "instagram"
}
```

---

## 9. GET /close-reasons → NEW（PR3）

理由マスタ取得（フォームのセレクトボックス用）。

### Request

```
GET /close-reasons?type={type}
```

| param | 値 |
|---|---|
| `type` | `won` / `lost` |

### Response

```jsonc
{
  "type": "won",
  "reasons": [
    { "id": 1, "label": "在庫・品揃え", "sort_order": 1, "is_active": true },
    { "id": 2, "label": "価格",         "sort_order": 2, "is_active": true },
    { "id": 7, "label": "その他",       "sort_order": 99, "is_active": true }
  ]
}
```

**フロント注意**:
- `is_active: false` の項目はフォームに表示しない（既存 won/lost レコードのドロワーには表示可）
- 並び順は `sort_order ASC`

---

## 10. GET /goals/summary → EXTEND（PR4）

`kpi_type` に `won_count` / `gross_profit` が追加される。  
**既存の kpi_type（revenue / deal_count / close_rate / lead_count / conversion_rate）の形状は変更しない。**

### 追加される kpi_type

| kpi_type | 意味 | 単位 |
|---|---|---|
| `won_count` | 成約件数 | 件 |
| `gross_profit` | 粗利 | 円（float） |

レスポンス形状の変更なし（kpi_type の値が増えるだけ）。

---

## 11. i18n キー（フロント側で追加が必要なもの）

| キー | ja | en |
|---|---|---|
| `funnel.leads` | リード獲得 | Lead Acquisition |
| `funnel.conversion` | 商談化 | Deal Conversion |
| `funnel.in_progress` | 進行中 | In Progress |
| `funnel.won` | 成約 | Won |
| `funnel.lost` | 失注 | Lost |
| `initiative.inbound` | お客様から問い合わせ | Customer Inquiry |
| `initiative.outbound` | こちらから営業 | Outbound Sales |
| `initiative.inbound_short` | 顧客起点 | Inbound |
| `initiative.outbound_short` | 自社起点 | Outbound |
| `channel.instagram` | Instagram | Instagram |
| `channel.messenger` | Messenger | Messenger |
| `channel.web_form` | Webフォーム | Web Form |
| `channel.sns` | その他SNS | Other SNS |
| `channel.referral` | 紹介経由 | Referral |
| `channel.unknown` | その他・不明 | Other / Unknown |
| `followup.post_won_no_order` | 成約後・未発注 | Post-Won, No Order |
| `followup.order_interval_exceeded` | 発注が止まった | Order Lapse |
| `followup.first_order_followup` | 初回後フォロー要 | Post-First-Order |
| `nav.funnelDashboard` | ファネルダッシュボード | Funnel Dashboard |

---

## 12. 未定義エンドポイント（第2弾以降）

以下は **このコントラクトのスコープ外**。PR1〜6 で実装しない。

- チャネル横断接触記録統合
- 担当者別目標・個人目標対比
- 要フォロー顧客の失注理由ベース再アプローチ候補
