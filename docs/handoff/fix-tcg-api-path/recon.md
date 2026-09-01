# recon — fix-tcg-api-path

**仕事名**: fix-tcg-api-path
**日付**: 2026-09-01
**対象ADR**: ADR-152
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/TcgParallelReportPage.tsx:70` | `api.get("/api/v1/tcg/parallel-report")` — `/api/v1` が重複 |
| `frontend/src/lib/api.ts:1` | `api` クライアントのベース URL に `/api/v1` が含まれる（他のAPI呼び出しは `/tcg/...` 形式） |
| `backend/app/routers/tcg_parallel_report.py:1` | `@router.get("/tcg/parallel-report")` — パスに `/api/v1` なし |
| `backend/app/main.py:556` | `tcg_parallel_report.router, prefix="/api/v1"` — prefix で `/api/v1` を付与 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 本番バックエンドで route が存在するか | `curl https://api.salesanchor.jp/api/v1/tcg/parallel-report` → 401 で実在確認 | ✅ 解消済み |
| 2 | 404 の原因 | バックエンドログ `GET /api/v1/api/v1/tcg/parallel-report 404` で重複パス確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
