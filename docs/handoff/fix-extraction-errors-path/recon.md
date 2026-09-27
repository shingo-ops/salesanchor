# recon: エラーログAPIパス二重prefix修正

## 問題箇所

- `backend/app/routers/tcg_analysis_dashboard.py:358` — `"/api/v1/tcg/extraction-errors"` と定義
- `backend/app/main.py:681` — `app.include_router(tcg_analysis_dashboard.router, prefix="/api/v1", ...)` で登録
- 実際のパス: `/api/v1/api/v1/tcg/extraction-errors`（二重prefix）

- `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx:50` — `api.get("/api/v1/tcg/extraction-errors?...")` と呼び出し
- `frontend/src/lib/api.ts:29` — `const API_BASE = "/api/v1"` で自動付与
- 実際のリクエスト先: `/api/v1/api/v1/tcg/extraction-errors`（二重prefix）

## 影響範囲

- `backend/app/routers/tcg_analysis_dashboard.py` — 1行のみ変更
- `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx` — 1行のみ変更

## 関連ADR

なし（パス文字列バグ修正）

## 既存ADR検索結果

`git grep -i "extraction-errors" docs/adr/` — 結果なし（ADR対象外）
