# deal-removal service B recon

## 実測

- `backend/app/routers/companies.py:190-196` は `v_company_stats` から会社詳細の集計を取得していた。`total_deal_amount` は入金済み請求書の合計、`deal_count` は `deals` の件数である。
- `backend/app/schemas/company.py:197-203` と `frontend/src/pages/company-detail/company-detail.types.ts:62-66` は、この集計を会社詳細のAPI契約として定義していた。
- `frontend/src/pages/company-detail/CompanyBasicTab.tsx:103-119` は商談金額と商談数を表示していた。
- `backend/app/routers/leads.py:2444-2503` はリード統合時に `deals.lead_id` をmasterへ付け替えていた。
- `backend/app/routers/leads.py:2477-2486` の loser status guard は `lead` 以外を拒否するため、この便では変更しない。

## 境界

`v_company_stats` 自体の `LEFT JOIN deals` と `deal_count` 列の削除はDB変更であり便Dで行う。この便では会社APIが該当列を読まず、画面・型も表示しない状態にする。ビューに一時的に余分な列が残っても、APIがSELECTしないためレスポンス契約には現れない。
