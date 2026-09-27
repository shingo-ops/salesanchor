# Recon: extraction-cost-transparency

## 目的
Gemini API呼び出しのトークン消費・コストを記録し、ダッシュボードで可視化する。

## 既存ADR調査

### 検索コマンド
```
git grep -i "llm_budget\|cost.*gemini\|token.*cost" docs/adr/
```

### 結果
- ADR-110: `backend/app/services/llm_budget.py` で翻訳コスト計算を既に実装済み（`docs/adr/ADR-110-sa-translation-subsystem.md:| llm_budget.py | ...`）
- ADR-158: extraction_attemptsテーブルを参照する最新ADR（`docs/adr/ADR-158-product-level-supersession.md`）

## 既存コード調査

### llm_budget.calculate_cost()
- ファイル: `backend/app/services/llm_budget.py`
- 翻訳サービスで既に利用中。モデル名を渡すと入力/出力トークン数からUSDコストを返す

### extraction_attemptsテーブル
- ファイル: `backend/app/services/tcg_extraction_record_svc.py:1-240`
- ExtractionRecorderクラスがDB書き込みを管理
- 既存カラム: id, work_id, supplier_name, model, status, parsed_bytes等

### gemini_extraction_svc.py
- ファイル: `backend/app/services/gemini_extraction_svc.py:390-410`
- Gemini SDK レスポンスから `response.usage_metadata` でトークン数取得可能
- フィールド: `prompt_token_count`（入力）, `response_token_count`（出力）

### tcg_analysis_dashboard ルーター
- ファイル: `backend/app/routers/tcg_analysis_dashboard.py:1-460`
- 既存エンドポイント: /extraction-stats, /extraction-errors 等

### AnalysisDashboardPanel.tsx
- ファイル: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1-800`
- 既存タブ: 解析・抽出・在庫 の3タブ構成

## 変更前後の状態

| ファイル | 変更前 | 変更後 |
|---------|--------|--------|
| extraction_attempts | input_tokens/output_tokens/cost_usdカラムなし | 3カラム追加（NULL許可） |
| gemini_extraction_svc.py:399 | usage_metadata未取得 | prompt/response_token_count取得 |
| tcg_extraction_record_svc.py:177 | コスト記録なし | calculate_cost()でUSD算出→DB保存 |
| tcg_analysis_dashboard.py | cost-summaryエンドポイントなし | GET /tcg/analysis-dashboard/cost-summary追加 |
| AnalysisDashboardPanel.tsx | コストセクションなし | KPI・仕入元別・日別推移コストセクション追加 |
