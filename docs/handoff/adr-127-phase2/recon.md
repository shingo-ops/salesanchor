# recon — ADR-127 Phase 2: 第1層ゲート（新規登録の二重発行防止）

**仕事名**: adr127-phase2-dual-gate
**日付**: 2026-06-11
**対象ADR**: ADR-127 §4
**担当**: generator

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:90` | `billingAddresses` — addresses 配列から billing フィルタ済み。登録済み判定に使用 |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:112-120` | 「登録リンク生成」ボタン: `type: "register"` 固定。`disabled={regLinkLoading}` のみで登録済みゲートなし |
| `frontend/src/pages/company-detail/company-detail.types.ts:22` | `CompanyAddress.is_default: boolean` — 型定義済み |
| `backend/app/routers/registration_tokens.py:65-114` | `POST /registration-tokens`: 登録済みゲートなし。`create_registration_token` を無条件呼び出し |
| `backend/app/routers/registration_tokens.py:104-108` | URL分岐: `add_address` → `/register/address`、else → `/register` |
| `backend/app/routers/registration_tokens.py:197-198` | `SELECT id FROM companies WHERE lead_id = :lead_id` — company_id 取得パターン |
| `backend/app/schemas/registration_token.py:26-28` | `TokenType` Enum: `register` / `add_address` の2種 |
| `frontend/src/locales/en.json:2322` | `registration.generateLink` — 既存キー（隣に新規キーを追加） |

## 不明点リスト

未解決なし。
- companies テーブルは `lead_id` を SSOT として持つ（`leads に company_id 列はない`、`registration_tokens.py:145` コメント）
- `company_addresses.is_default` + `address_type='billing'` で登録済み判定可能（ADR-127 §4 方針と一致）
