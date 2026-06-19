# recon: Advisor Phase 1 / PR-1 顧客別受注履歴 API

**仕事名**: Advisor Phase 1 / PR-1 顧客別受注履歴 API
**日付**: 2026-06-19
**対象ADR**: ADR-139
**担当**: architect

## file:line 引用表

| 引用先 path:line | 確認内容 |
|------------------|---------|
| backend/app/routers/orders.py:165 | orders に company_id がある |
| backend/app/routers/orders.py:229 | orders に created_at がある |
| backend/app/routers/orders.py:233 | orders に total_amount がある |
| backend/app/routers/analytics.py:912-933 | period と scope の既存バリデーションがある |
| backend/app/routers/analytics.py:939-999 | funnel の scope=mine 実装例がある |
| backend/app/routers/analytics.py:1113-1243 | follow-ups の scope=mine 実装例がある |
| backend/app/routers/analytics.py:1301-1460 | revenue-summary の scope=mine 実装例がある |
| backend/app/routers/analytics.py:1484-1586 | channels の scope=mine 実装例がある |
| backend/app/routers/analytics.py:1614-1645 | reasons の scope=mine 実装例がある |
| backend/app/routers/analytics.py:1330-1336 | mine は deals.assigned_to で絞る |
| backend/app/routers/analytics.py:1136-1138 | mine の絞り込み例がある |
| backend/tests/conftest.py:1264-1274 | SQLite インメモリのテスト基盤がある |
| backend/tests/conftest.py:1379-1383 | tenant / user override のテスト基盤がある |
| backend/tests/test_analytics.py:409-527 | orders / deals / leads を直接投入する既存テストがある |
| backend/tests/test_analytics.py:544-627 | 既存の analytics テストがある |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | customer-orders の最終的なレスポンス列が追加で必要か | 実装後の pytest で確認 | 解消済み |
| 2 | period 1m の境界を UTC 日付で見るか JST 月初で見るか | 既存 analytics の期間境界に合わせて確認 | 解消済み |

**未解決ゼロ確認**: 全て解消済み

## 補足

- read-only の集計 API 追加で、DB migration は不要。
- scope=mine は orders.deal_id から deals.assigned_to による既存流儀に合わせる。
- period は 1m / 3m / 6m / 12m を採用する。
