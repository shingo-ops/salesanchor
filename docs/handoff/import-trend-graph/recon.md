# recon: import-trend-graph

## 現在地

### 既存コード参照

- `backend/app/services/tcg_analysis_dashboard_svc.py:171-250` — `get_pipeline_trend()` 関数（days バリデーション・f-string INTERVAL パターン）
- `backend/app/routers/tcg_analysis_dashboard.py:104-126` — `TrendDayItem` / `get_pipeline_trend_endpoint` パターン
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:682-720` — ExtractionTabContent 内トレンドグラフ（LineChart 金型）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:242-258` — インポートサマリー lazy-load useEffect パターン
- `frontend/src/locales/ja.json:3933` — `analysisRules.dashboard` セクション末尾（追加位置）
- `frontend/src/locales/en.json:3933` — 同上

### ADR 検索結果

- ADR-027: i18n 強制（全 UI 文字列は `t()` 経由）
- ADR-067: CSS デザイントークン強制（色の直値禁止）
- ADR-144: UI 金型遵守（Card/DataTable/recharts のみ）

## 確認事項

- `--color-warning` / `--color-success` は `frontend/src/index.css:145,530` で定義済み
- `import_jobs` テーブルには `created_at`, `message_count`, `unresolved_count` カラムが存在（get_import_summary で確認済み）
- INTERVAL パラメータバインド非対応: `get_pipeline_trend` と同様に int 検証後 f-string 補間を使用
