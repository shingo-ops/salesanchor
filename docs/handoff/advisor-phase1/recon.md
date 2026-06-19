# Recon: Advisor Phase 1 / PR-1 顧客別受注履歴 API

**測定日**: 2026-06-19

## 目的
read-only の集計 API 1本で、顧客別の受注履歴と再受注予測の土台を返せるかを現コードで確認する。

## 事実

- `orders` には `company_id / created_at / total_amount` がある。
  - `backend/app/routers/orders.py:165`
  - `backend/app/routers/orders.py:229`
  - `backend/app/routers/orders.py:233`
- `analytics.py` には既存の期間・スコープ処理がある。
  - `period` の分岐: `backend/app/routers/analytics.py:912-927`
  - `scope` バリデーション: `backend/app/routers/analytics.py:930-933`
  - `scope=mine` の実装例:
    - `/analytics/funnel`: `backend/app/routers/analytics.py:939-999`
    - `/analytics/follow-ups`: `backend/app/routers/analytics.py:1113-1243`
    - `/analytics/revenue-summary`: `backend/app/routers/analytics.py:1301-1460`
    - `/analytics/channels`: `backend/app/routers/analytics.py:1484-1586`
    - `/analytics/reasons`: `backend/app/routers/analytics.py:1614-1645`
- `mine` は既存実装では `deals.assigned_to` 経由で担当者に絞る。
  - `backend/app/routers/analytics.py:1330-1336`
  - `backend/app/routers/analytics.py:1136-1138`
- テスト基盤は SQLite インメモリ + override user/tenant で動く。
  - `backend/tests/conftest.py:1264-1274`
  - `backend/tests/conftest.py:1379-1383`
- 既存テストは `orders` / `deals` / `leads` を直接投入する流れがある。
  - `backend/tests/test_analytics.py:409-527`
  - `backend/tests/test_analytics.py:544-627`

## 実装判断

- 新規 migration は不要。
- `/analytics/customer-orders` は read-only で、既存の `dashboard.view` 系の read-only 集計群に揃える。
- `scope=mine` は `orders.deal_id -> deals.assigned_to` の結合で既存流儀に合わせる。
- `period` は `1m / 3m / 6m / 12m` を採用する。

