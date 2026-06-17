# recon — conv-logs-route-fix

**仕事名**: conv-logs-route-fix  
**日付**: 2026-06-17  
**対象ADR**: ADR-096  
**担当**: Terminal CC（architect recon）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/companies.py:1031` | `@router.get("/{company_id}/conv-logs", ...)` — バグ箇所。`/companies/` プレフィックスが欠落し `/api/v1/6/conv-logs` に解決されていた |
| `backend/app/routers/companies.py:1032` | ルートパス文字列 `"/{company_id}/conv-logs"` → 修正後 `"/companies/{company_id}/conv-logs"` |
| `backend/app/main.py:245` | `app.include_router(companies.router, prefix="/api/v1", ...)` — マウントプレフィックスが `/api/v1` であることを確認 |
| `frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:49` | フロントが呼ぶパス: `/api/v1/companies/${companyId}/conv-logs` — バックエンドの誤パスとの不一致を確認 |
| `backend/tests/test_company_conv_logs.py:14` | 既存テスト3件（関数直接呼び出し）。HTTP ルートパスの検証がなかったため今回追加 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `conversation_logs.company_id` カラムが本番 schema に存在するか | `SA-02-plan.md:78` に `migrations/20260604_090000_create_conversation_logs.sql:34` で company_id 定義済みと記載 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 修正対象はルートパス1行（`companies.py:1032`）のみ
- DB・migration・フロントエンド変更なし
- 既存エンドポイント（`GET /companies`, `PATCH /companies/{id}` 等）には影響なし
