# recon: API 呼び出しの /api/v1 二重

実測時の origin/main SHA: e6923ba61

## 事実
- frontend/src/lib/api.ts:29 `const API_BASE = "/api/v1";`。api クライアントは内部で付与する。
- frontend/src/components/ChannelTypeCombobox.tsx:43 `api.get("/channel-masters")` が正しい例。
- 二重になっている6か所（修正前）:
  - frontend/src/pages/admin/ChannelMastersPage.tsx:36 `/api/v1/channel-masters`
  - frontend/src/pages/admin/ChannelMastersPage.tsx:54 `/api/v1/admin/channel-masters`
  - frontend/src/pages/admin/ChannelMastersPage.tsx:68 `/api/v1/admin/channel-masters/${id}`
  - frontend/src/pages/inbox/ManualRecordSection.tsx:46 `/api/v1/channel-masters`
  - frontend/src/pages/inbox/ManualRecordSection.tsx:76 `/api/v1/leads/${leadId}/conv-logs`
  - frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:50 `/api/v1/companies/${companyId}/conv-logs${params}`
- backend の経路（実在）: backend/app/routers/conv_logs.py:190 `/channel-masters`、backend/app/routers/conv_logs.py:226 `/leads/{lead_id}/conv-logs`、backend/app/routers/companies.py:1065 `/companies/{company_id}/conv-logs`。
- 対象外: fetch( 直書き、useSSE の endpoint。
- 既存 ADR 検索（`git grep -il API_BASE docs/adr`）: docs/adr/ADR-152-frontend-api-path-no-prefix.md が同一パターンを扱う。決定は「api.get/post/put/patch/delete のパスは /api/v1 なしで書く」。ADR-152 が推奨する機械検出（Consequences の最終行）は未実装のため、本便の追加テストがそれにあたる。
