# recon: ハードコードプロンプト廃止 + エラーログページ

## 調査日時
2026-09-27

## 対象ADR
- ADR-158: Gemini extraction bypass fix
- ADR-027: UI internationalization
- ADR-144: UI governance

## 既存コード調査

### PROMPT_TEXT / WORK_ID_PROMPT_TEXT 定数
- `backend/app/services/gemini_extraction_svc.py:82-101` — PROMPT_TEXT 定数
- `backend/app/services/gemini_extraction_svc.py:103-133` — WORK_ID_PROMPT_TEXT 定数
- `backend/app/services/gemini_extraction_svc.py:144-178` — _load_db_prompts() フォールバック付き実装
- `backend/app/services/gemini_extraction_svc.py:628-638` — __all__ に PROMPT_TEXT が含まれる
- `backend/tests/test_tcg_gemini_extraction.py:21` — PROMPT_TEXT import
- `backend/tests/test_tcg_gemini_extraction.py:99` — PROMPT_TEXT を直接使うテスト

### ダッシュボードAPI
- `backend/app/routers/tcg_analysis_dashboard.py:1-339` — 既存エンドポイント群
- `backend/app/services/tcg_analysis_dashboard_svc.py:132-153` — recent_errors クエリ（LIMIT 10）
- `backend/app/services/tcg_analysis_dashboard_svc.py:164-168` — supplier JOIN パターン（source_messages → supplier_channels → suppliers）

### フロントエンド
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-30` — AnalysisRulesSidebarKey 型定義
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:78-82` — 解析状況グループの既存4項目
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:164-184` — activeSection 分岐
- `frontend/src/locales/ja.json:4006` — sidebar.promptConfig キー（追記箇所の基準）
- `frontend/src/locales/en.json:4006` — sidebar.promptConfig キー（追記箇所の基準）

## 変更方針
1. PROMPT_TEXT / WORK_ID_PROMPT_TEXT 定数を完全削除（DB SSOT化）
2. _load_db_prompts() を DB必須化（失敗時は RuntimeError）
3. /api/v1/tcg/extraction-errors エンドポイントを追加
4. ExtractionErrorLogPanel コンポーネントを新設
5. サイドバーに "error-log" キーを追加
