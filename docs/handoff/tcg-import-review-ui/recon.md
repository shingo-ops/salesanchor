# recon — tcg-import-review-ui（確認工程 フロントエンド UI）

**仕事名**: TCG LINE import 確認工程 フロントエンド UI  
**日付**: 2026-09-05  
**対象ADR**: ADR-027, ADR-144  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/TcgLineImportPage.tsx:1` | 変更対象ページ（ドロップゾーン・履歴テーブル実装済み） |
| `backend/app/routers/tcg_line_import.py:1` | ImportResultResponse に review_status 追加済み（#3306） |
| `backend/app/routers/tcg_diagnostics.py:68` | GET /tcg/diagnostics/{key} — key='suppliers' で仕入元一覧取得 |
| `backend/app/services/tcg_diagnostics_svc.py:44` | suppliers クエリ → rows: [{code, name, is_active}] |
| `frontend/src/locales/ja.json:3301` | tcgLineImport セクション（変更前: 31キー） |
| `frontend/src/locales/en.json:3301` | 同上（英語版） |
| `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx:1` | 既存フィーチャーコンポーネントのパターン参照 |

---

## 1. #3306 API レスポンス形状（確認済み）

### POST /tcg/line-import
```
ImportResultResponse {
  status: "imported" | "already_imported"
  review_status: "ok" | "pending_review"
  message_count: int
  provider_count: int
  unresolved_count: int
  unresolved_display_names: list[str]
  import_job_id: str
}
```

### GET /tcg/line-import/pending
```
list[PendingJobDetail] {
  id: str
  filename: str
  message_count: int
  unresolved_count: int
  unresolved_names: list[str]
  window_start: str | null
  window_end: str | null
  review_status: str
  created_at: str
}
```

### POST /tcg/line-import/{id}/resolve
```
body: { display_name: str, action: "assign"|"create", supplier_code?: str }
response: { success: bool, remaining_unresolved: int }
```

### POST /tcg/line-import/{id}/commit
```
response: { status: str, provider_count: int, enqueued_count: int }
```
409 if still unresolved

---

## 2. diagnostics/suppliers レスポンス形状（確認済み）

```
DiagnosticsResponse {
  ok: bool
  key: str
  rows: [{ code: str, name: str, is_active: bool }]
}
```
SQL: `SELECT code, name, is_active FROM tenant_004.tcg_suppliers ORDER BY code`

---

## 3. 既存パターン確認

- `frontend/src/features/tcg-analysis-review/` — フィーチャーコンポーネントの配置場所
- `TcgLineImportPage.tsx` は inline style + CSS変数（var(--color-*)）を使用
- `ui-allow` コメント必須（super-admin専用フォーム）
- i18n: `t("tcgLineImport.*")` 名前空間を使用

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | diagnostics/suppliers のレスポンス形状 | `tcg_diagnostics_svc.py:44` を確認 | ✅ 解消済み |
| 2 | api.post の引数形 | `frontend/src/lib/api.ts:196` 確認 | ✅ 解消済み |
| 3 | フィーチャーコンポーネントの配置先 | `frontend/src/features/tcg-analysis-review/` パターンを確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
