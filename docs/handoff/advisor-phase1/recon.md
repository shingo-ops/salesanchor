# recon: Advisor Phase 1 / PR-2 新規/既存セグメント別 売上サマリーAPI

**仕事名**: Advisor Phase 1 / PR-2 新規/既存セグメント別 売上サマリーAPI
**日付**: 2026-06-20
**対象ADR**: ADR-139
**担当**: architect

## file:line 引用表

| 引用先 path:line | 確認内容 |
|------------------|---------|
| backend/app/routers/analytics.py:97-138 | 期間境界の共通 helper があり、1m / 3m / 6m / 12m を扱える |
| backend/app/routers/analytics.py:366-464 | /analytics/revenue-segments が new / repeat 別の売上・件数・平均単価・顧客数・構成比を返す |
| backend/app/routers/analytics.py:1458-1545 | revenue-summary 既存実装が new / repeat の定義を担っている |
| backend/app/routers/analytics.py:1464-1467 | scope=mine は deals.assigned_to 経由で絞る |
| backend/app/routers/analytics.py:1510-1545 | new / repeat の定義は当月以前に orders があるかで分けている |
| backend/app/schemas/order.py:49-113 | orders に company_id / deal_id / total_amount / created_at がある |
| backend/app/schemas/deal.py:55-124 | deals に assigned_to / company_id / created_at / status がある |
| backend/app/schemas/lead.py:57-114 | leads に assigned_to / monthly_forecast 等の属性がある |
| backend/app/schemas/lead.py:180-195 | leads に converted_deal_id がある |
| backend/tests/conftest.py:1361-1387 | client fixture が SQLite + override user / tenant で動く |
| backend/tests/test_analytics.py:519-664 | segment API の pytest を追加する対象領域 |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | new / repeat の平均単価を order_count=0 のとき null にするか 0 にするか | 既存 API の境界レスポンスを pytest で固定 | 解消済み |
| 2 | 構成比 share の丸め桁を何桁にするか | pytest で数値 assert を固定 | 解消済み |
| 3 | mine スコープの segment 定義を current-period 限定にするか global first-order 基準にするか | revenue-summary の既存定義に合わせる | 解消済み |

**未解決ゼロ確認**: 全て解消済み

## 補足

- read-only の集計 API 追加で、DB migration は不要。
- segment の定義は revenue-summary の既存ロジックを流用し、件数だけ追加集計する。
- PayPal smoke は本PRの必須チェックではないため、マージ判定から除外する。
