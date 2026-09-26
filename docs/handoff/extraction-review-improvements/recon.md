# Recon: extraction-review-improvements

## 対象ADR
- ADR-158: 商品マッチング精度改善

## 調査結果

### _resolve_pid 現状
- `backend/app/services/tcg_analyzer_svc.py`（L1273-1284付近）
- 現在: None/""/"−" → None, 直接validate → 成功なら返す, product_code_to_id フォールバック → validate
- 問題: 非整数（"M1L", "OP-15" 等）が誤マッチする可能性がある
- product_code_to_id は L1215 で定義、L1224 の rawcode_to_id.update() でも使用されている（残置必要）
- rawcode_to_id は L1436 で使用中

### 要確認一覧API
- GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW
- レスポンス: AnalysisResultsResponse (items, total, item_total, offset, limit, providers, works)
- AnalysisResultItem 型: extraction_item_id, source_message_id, provider, raw_text, gemini{}, system{}, review_issues[], condition_review{}
- 既存参照: `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx`（L52）

### フロントエンドパターン
- ページパターン: `frontend/src/pages/super-admin/TcgSoldOutPage.tsx`（DataTable + ページネーション）
- ルート追加: `frontend/src/App.tsx`（L302-304 近辺）
- ナビ追加: `frontend/src/components/DesktopShell.tsx`（L192-196）、`frontend/src/components/MobileShell.tsx`（L162-183）
- i18n: nav.superAdminNeedsReview キー追加

### 未使用変数確認
- product_code_to_id: L1215(定義), L1224(rawcode_to_id.update), L1281(_resolve_pid内)
- L1281 のみ削除。L1215/L1224 は残置（rawcode_to_id が L1436 で使用中）
