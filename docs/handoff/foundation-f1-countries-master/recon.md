# Foundation F1 recon

測定日: 2026-06-21

## 事実

- 既存の shared public master の前例は `public.permissions` と `public.supplier_prompts`。
  - `migrations/002_add_permissions_master.sql:9-23`
  - `migrations/087_create_supplier_prompts.sql:11-38`
- 国 SSOT は frontend に既存し、`frontend/src/constants/countries.ts:1-18` と `:20-215` に ISO alpha-2 / dial code の一覧がある。
- 会社住所の `country_code` は 2 文字前提で扱われている。
  - `backend/app/schemas/company.py:70`
  - `migrations/030_create_company_contact_subtables.sql:55`
- 既存の読み取りマスタ API は `channel-masters` にあり、FastAPI で一覧を返す read-only ルータの前例になる。
  - `backend/app/routers/conv_logs.py:177-209`

## 判断

- `public.countries` は tenant_id を持たない共有 master として追加する。
- seed は `frontend/src/constants/countries.ts` の内容と一致させる。
- 本 PR は追加のみ。既存の `country_code` 入力や backfill は次 PR。
