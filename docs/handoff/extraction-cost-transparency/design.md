# Design: extraction-cost-transparency

## ADR参照
- ADR-110: llm_budget.pyによるLLMコスト計算SSOTの確立（翻訳システム）→ 本PRはこの仕組みをextraction側に横展開

## KGI
ダッシュボード「抽出」タブで当日のGemini APIコスト（USD）が表示される。

## KPI（POが画面で○×を判定できる粒度）

| 基準 | 検証方法 |
|------|----------|
| GET /tcg/analysis-dashboard/cost-summary が200を返す | curl または ブラウザNetworkタブで確認 |
| extraction_attempts.cost_usd に値が入る | psqlで `SELECT cost_usd FROM extraction_attempts ORDER BY id DESC LIMIT 5;` |
| ダッシュボード抽出タブに「APIコスト」セクションが表示される | ブラウザで /super-admin/analysis を開き確認 |

## 設計方針

### DB変更
- `migrations/20260927_130000_add_extraction_token_cost_columns.sql`: ADD COLUMN IF NOT EXISTS（NULL許可・既存行に影響なし）
- 追加カラム: `input_tokens INTEGER`, `output_tokens INTEGER`, `cost_usd NUMERIC(10,6)`

### バックエンド
1. `backend/app/services/gemini_extraction_svc.py`: Gemini SDK `response.usage_metadata` から `prompt_token_count` / `response_token_count` を取得し `recorder.on_response()` に渡す
2. `backend/app/services/tcg_extraction_record_svc.py`: `on_response()` でトークン数を保持し、`finalize()` 時に `llm_budget.calculate_cost()` でUSD算出→DB保存
3. `backend/app/services/inventory_parser_llm.py`: SDKフィールド名修正（`candidates_token_count` → `response_token_count`）
4. `backend/app/routers/tcg_analysis_dashboard.py`: `GET /tcg/analysis-dashboard/cost-summary` を追加（期間指定・仕入元別集計・日別推移）

### フロントエンド
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`: 抽出タブにコストセクション追加（KPIカード・仕入元別テーブル・日別推移チャート）
- i18n: `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` にキー追加

## 影響範囲
- extraction_attempts テーブルのみ（ADD COLUMN、既存行はNULL）
- ExtractionRecorder.on_response() シグネチャ変更（keyword引数追加、後方互換あり）
- 既存のfinalize()/record_failure()はコストカラムが埋まった場合のみ更新

## 弊害
- なし（NULL許可ADD COLUMNのみ・既存ロジックに非破壊的変更のみ）

## 計画
1. migration適用（ADD COLUMN）
2. バックエンドデプロイ
3. 次回extraction実行時にトークン数・コストが記録される
4. ダッシュボードでコストセクションが表示される

## 外部・過去事例の参照と我々への応用
- ADR-110（翻訳サブシステム）で `backend/app/services/llm_budget.py` を用いたLLMコスト計算が実証済み
- 同一の `calculate_cost(input_tokens, output_tokens, model=...)` APIを使い、モデル変更時の一元修正を保証
- Google Cloud Cost Management の usage_metadata 取得パターンをそのまま踏襲

## 維持の仕組み
守り手: `backend/app/services/llm_budget.py` が料金体系を一元管理（モデル変更時もここだけ修正）
