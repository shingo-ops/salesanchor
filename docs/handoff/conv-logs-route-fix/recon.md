# recon — conv-logs-route-fix

**仕事名**: conv-logs-route-fix  
**日付**: 2026-06-17  
**対象ADR**: ADR-096  
**担当**: Terminal CC（architect recon）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/companies.py:1031` | ルートパス定義箇所。バグ原因: /companies/ プレフィックスが欠落しており /api/v1/6/conv-logs に解決されていた |
| `backend/app/routers/companies.py:1032` | バグ行: ルートパス文字列。修正後は /companies/{company_id}/conv-logs |
| `backend/app/main.py:245` | companies.router のマウント先: prefix="/api/v1"。完全パスは /api/v1/companies/{id}/conv-logs になる必要がある |
| `frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:49` | フロントが呼ぶパス: /api/v1/companies/${companyId}/conv-logs。バックエンドの誤パスとの不一致を確認 |
| `backend/tests/test_company_conv_logs.py:14` | 既存テスト3件（関数直接呼び出し）。HTTP ルートパスの検証がなかったため今回追加 |
| `migrations/20260604_090000_create_conversation_logs.sql:34` | conversation_logs テーブル定義。company_id カラムが存在することを確認済み |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | conversation_logs.company_id カラムが本番 schema に存在するか | migration ファイルの定義を確認（上記 file:line 参照） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 修正対象はルートパス1行のみ
- DB・migration・フロントエンド変更なし
- 既存エンドポイント（GET /companies、PATCH /companies/{id} 等）には影響なし
