# recon — deal-removal-track-a

**仕事名**: deal-removal-track-a  
**日付**: 2026-06-23  
**対象ADR**: ADR-121  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/dashboard.py:31-205` | dashboard API から deal 系応答を除去し、converted_deal_id ベースの成約率は維持 |
| `backend/app/tasks/dashboard.py:35-111` | dashboard cache 側でも deal 集計を除去し、API と整合 |
| `backend/tests/test_dashboard.py:64-71` | dashboard API の期待値から deal 系を外したテスト |
| `backend/tests/test_celery.py:74-123` | dashboard cache の期待値から deal 系を外したテスト |
| `frontend/src/pages/dashboard/DashboardPage.tsx:88-618` | ダッシュボードから商談 KPI・停滞商談導線を除去し、W-2①と成約率を維持 |
| `frontend/tests-e2e/fixtures/mock-dashboard.json:1-41` | ダッシュボード fixture を新レスポンスに合わせて更新 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | dashboard 以外に deal ボード系表示の消費者が残っていないか | `rg -n "summary\\.deals|pipeline_by_stage|recent_deals|deal_count|deal_open_count|deal_won_count|deal_total_amount|deal_won_amount|/deals"` | ✅ 解消済み |
| 2 | ルーティング/テストが新レスポンスで壊れないか | `pytest` + frontend build + Playwright | ✅ 解消済み |

**未解決ゼロ確認**: 該当なし

---

## 補足

Track A は dashboard の見える参照外しに限定し、`deals` テーブル・`/deals` ルート・成約率（`converted_deal_id`）・W-2① は維持する。
