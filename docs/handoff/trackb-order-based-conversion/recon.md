# recon - trackb-order-based-conversion

**仕事名**: trackb-order-based-conversion  
**日付**: 2026-06-23  
**対象ADR**: ADR-142  
**担当**: architect

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `docs/adr/ADR-142-order-based-conversion-definition.md:1-40` | 成約を受注ベースに一本化し、`converted_deal_id` を商談化の別概念として残す |
| `backend/app/routers/dashboard.py:100-119` | dashboard の conversion_rate が `lead_has_successful_order_sql('l')` で算出される |
| `backend/app/routers/analytics.py:93-122` | 担当者別 conversion が `lead_has_successful_order_sql("l")` で算出される |
| `backend/app/routers/analytics.py:1512-1520` | goals 集計の再ポイント確認 |
| `backend/app/routers/analytics.py:1795-1805` | priority prospects の ease/rank 入口 |
| `backend/app/routers/goals.py:425-435` | goals の conversion_rate が `lead_has_successful_order_sql('l')` を参照する |
| `backend/app/services/priority_scoring.py:183-185` | invoice 勝ち判定が `status != 'voided'` に揃っている |
| `backend/tests/test_analytics_conversion_by_attribute_rls.py:141-180` | tenant_006 の PG/RLS 実走で attribute conversion を検証する |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 成約定義が order ベースに統一されているか | ADR-142 と各 router の `lead_has_successful_order_sql` を確認 | ✅ 解消済み |
| 2 | tenant_006 の RLS 実走が実際に通るか | `backend/tests/test_analytics_conversion_by_attribute_rls.py` を実走 | ✅ 解消済み |

**未解決ゼロ確認**: 該当なし

## 補足

- migration は不要。既存列 join で算出する。
- `converted_deal_id` は削除せず、商談化の別概念として残す。
