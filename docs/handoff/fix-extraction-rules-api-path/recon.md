# recon — fix-extraction-rules-api-path

**仕事名**: fix-extraction-rules-api-path
**日付**: 2026-09-24
**対象ADR**: なし（バグフィックスのみ）
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:110` | `api.get("/api/v1/super-admin/suppliers/extraction-overview")` — `/api/v1` 重複 |
| `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:137` | `api.get("/api/v1/super-admin/suppliers/${id}/extraction-rules")` — `/api/v1` 重複 |
| `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:184` | `api.patch("/api/v1/super-admin/suppliers/${selectedSupplier.id}/extraction-rules")` — `/api/v1` 重複 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | api.get() が API_BASE を自動付加するか | frontend/src/lib/api.ts を確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

`api.get()` / `api.patch()` は内部で `API_BASE="/api/v1"` を自動付加する実装になっているため、
パスに `/api/v1` を含めると `/api/v1/api/v1/...` という形になり 404 が発生していた。
修正は文字列の削除のみ。ロジック・型・テスト変更なし。
