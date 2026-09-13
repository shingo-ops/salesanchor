# converted_deal_id 置換 recon

対象ADR: ADR-121。

- `backend/app/routers/dashboard.py:98-110` は converted_deal_id 非NULLを転換率に使っていた。
- `backend/app/routers/goals.py:421-436` も同じ集計だった。
- `backend/app/routers/analytics.py:1016-1033` は status 欠落時に converted_deal_id をフォールバックに使っていた。
- `backend/app/routers/leads.py:2418-2548` は統合 loser の converted_deal_id 非NULLを拒否していた。
- `frontend/src/pages/leads/LeadsPage.tsx:500-504` は converted_deal_id 非NULLで商談化・統合を隠していた。

tenant_006 の実証により、転換率は negotiating / existing_customer / lost を分子、全リードからアーカイブ相当と disqualified を除いた件数を分母とする。商談化 API は `backend/app/routers/leads.py:770-838` で deals を作らず status を negotiating にする。統合は lead 状態の loser のみ許可する。
