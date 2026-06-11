# recon — sa-03-change-billing

**仕事名**: SA-03 change_billing 一式実装（ADR-127 A-1〜A-3, B-1/B-2, E-1/E-2）  
**日付**: 2026-06-12  
**対象ADR**: ADR-127  
**担当**: Terminal CC

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/schemas/registration_token.py:26` | TokenType enum — change_billing 追加前は register/add_address 2種のみ |
| `migrations/20260604_080000_create_registration_tokens.sql:11` | DB CHECK制約 — 変更前は 2種のみ（'register', 'add_address'） |
| `backend/app/routers/registration_tokens.py:125` | URL分岐 — change_billing ブランチが存在しなかった箇所 |
| `frontend/src/App.tsx:118` | /register ルート存在確認 — change-billing ルートなし |
| `frontend/src/pages/company-detail/CompanyDetailPage.tsx:75` | handleGenerateRegLink — register タイプのみ発行 |
| `frontend/src/pages/inbox/InboxKartePanel.tsx:263` | overflow menu — 空スタブ（コメントのみ） |
| `backend/app/services/registration_token.py:120` | verify_token 3点検証（hash / used_at / expires_at） |
| `frontend/src/pages/register/RegisterPage.tsx:62` | resolveErrorCode / KNOWN_ERROR_CODES パターン（参考実装） |
| `frontend/src/pages/register/RegisterPage.tsx:314` | CountryCombobox + dial code 分割パターン（参考実装） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 案B（降格+INSERT）の実行順序 — is_default UNIQUE制約があるか | `company_addresses` テーブル DDL を確認。UNIQUE制約なし → UPDATE→INSERT 順でも安全 | ✅ 解消済み |
| 2 | migration-test.yml の baseline に registration_tokens が不要か | 新 migration は ALTER TABLE なので baseline に CREATE TABLE が必要 | ✅ 解消済み（本PRで追加） |

**未解決ゼロ確認**: 全て解消済み
