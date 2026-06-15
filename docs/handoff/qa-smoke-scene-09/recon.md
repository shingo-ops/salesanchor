# recon — QA Smoke Suite Scene 09: ADR-108 B-1 販売形態複数選択 検収

**仕事名**: QA Smoke Suite に ADR-108 B-1 post-deploy 検収シーン追加  
**日付**: 2026-06-14  
**対象ADR**: ADR-038 / ADR-108 / ADR-045 / ADR-027  
**担当**: Hikky-dev

---

## ADR 検索結果

| ADR | 関連 |
|-----|------|
| ADR-038 | QA Smoke Suite — 本スクリプトが準拠する QA 基盤。self-hosted runner / tenant_006 専用 |
| ADR-108 | カルテ再設計 Phase B-1 — 販売形態複数選択の実装元。scene-09-A の検証対象 |
| ADR-045 | additive-only 方針 — tenant_006 seed は ON CONFLICT DO NOTHING で冪等 |
| ADR-027 | i18n 強制 — scene-09-A は UI ラベルではなく data-testid を使ってセレクタを安定化 |

---

## file:line 引用表

### テスト対象コンポーネント

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:99` | `data-testid="sales-form-multi-select"` — コンポーネントルート |
| `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:111` | `data-testid="sales-form-trigger"` — ドロップダウン開閉ボタン（scene-09 で使用） |
| `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:123` | `data-testid="sales-form-dropdown"` — 選択肢リスト |
| `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:131` | `data-testid="sales-form-option-{value}"` — 個別選択肢 |
| `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:155` | `data-testid="sales-form-other-input"` — 「その他」自由記述欄 |
| `frontend/src/pages/inbox/InboxKartePanel.tsx:464` | SalesFormMultiSelect 配置（company タブ） |

### テスト基盤

| 引用先 | 確認内容 |
|--------|---------|
| `tests/qa-smoke/playwright.config.ts:27` | `baseURL = https://app.salesanchor.jp` — 本番 frontend 直叩き |
| `tests/qa-smoke/playwright.config.ts:63` | `runs-on: [self-hosted, salesanchor-vps]` — runner 要件 |
| `tests/qa-smoke/fixtures/qa-tenant-creds.ts:36` | `QA_TENANT_CODE = "tenant-review"`, `QA_TENANT_ID = 6` |
| `tests/qa-smoke/utils/real-backend.ts:27` | `login()` — 実 Firebase ログイン |
| `tests/qa-smoke/utils/db-assert.ts:48` | `psqlRows()` — psql 直叩き（DATABASE_URL 必須） |

### Seed

| 引用先 | 確認内容 |
|--------|---------|
| `scripts/qa/seed-tenant.sql:322` | tenant_006 sales_form_options seed 挿入箇所（本PR追加） |
| `migrations/20260614_100000_create_sales_form_tables.sql:89` | tenant_004 のみ初期データあり。tenant_006 は seed が必要 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | data-testid が実装と一致するか | `SalesFormMultiSelect.tsx:111` を grep で確認 → `sales-form-trigger` が正しい | ✅ 解消済み |
| 2 | tenant_006 に sales_form_options がない | migration は tenant_004 のみ投入 → reset-tenant.sh / seed-tenant.sql に冪等 seed を追加 | ✅ 解消済み |
| 3 | self-hosted runner の要求ラベル | `qa-smoke.yml` の `runs-on: [self-hosted, salesanchor-vps]` を確認 | ✅ 解消済み（runner 復旧は PO 側作業） |

**未解決ゼロ確認**: 全て解消済み
