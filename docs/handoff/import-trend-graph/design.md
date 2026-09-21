# design: import-trend-graph

## 参照 ADR

- ADR-027: i18n 強制
- ADR-067: デザイントークン強制
- ADR-144: UI 金型遵守

## recon 参照

- `backend/app/services/tcg_analysis_dashboard_svc.py` の `get_pipeline_trend()` 関数（days バリデーション・f-string INTERVAL パターン）
- `backend/app/routers/tcg_analysis_dashboard.py` の `TrendDayItem` / `get_pipeline_trend_endpoint` パターン
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` の ExtractionTabContent 内 LineChart 金型

## あるべき姿（KGI/KPI）

| 基準 | 検証方法 |
|------|---------|
| Import タブに 7 日分の折れ線グラフが表示される | UI で Import タブを開いて折れ線グラフが表示されることを確認 |
| グラフに job_count と message_count の 2 本の線がある | Legend に 2 エントリが表示される |
| データなしの場合はグラフが非表示になる | trend 配列が空のとき Card が描画されない |
| テキストは t() 経由（ハードコード日本語なし） | ESLint pass / i18n キー両言語一致 |
| 色は CSS トークン（直値なし） | コード上 var(--color-*) のみ使用 |

## 変更方針

### Backend

1. `backend/app/services/tcg_analysis_dashboard_svc.py` に `get_import_trend(db, days=7)` 追加
   - days: `max(1, min(int(days), 90))` で検証
   - JST 変換 + MM-DD フォーマットで返却
   - import_jobs テーブルを日別 GROUP BY

2. `backend/app/routers/tcg_analysis_dashboard.py` に `ImportTrendItem` Pydantic モデルと `GET /tcg/analysis-dashboard/import-trend` エンドポイント追加
   - `Query(default=7, ge=1, le=90)` でバリデーション

### Frontend

1. `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` に `ImportTrendDay` 型を追加
2. `importTrend` state を追加
3. Import タブ lazy-load の useEffect で summary と trend を Promise.all で並列取得
4. `ImportTabContent` に `trend` prop を追加、グラフを KPI カード後・DataTable 前に挿入
5. LineChart: job_count (--color-warning) / message_count (--color-success)

### i18n

- `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` に `importTrendTitle` / `importTrendJobCount` / `importTrendMessageCount` を追加

## 外部・過去事例の参照と我々への応用

recharts LineChart — 既存の Extraction タブ・Analysis タブで同一パターン（ResponsiveContainer + LineChart + CartesianGrid + Legend）を使用済み。同一コンポーネント・同一設定で実装することで新規依存なし・デザイン統一を維持。

## 影響範囲

- 追加のみ（既存機能変更なし）
- Import タブのレンダリングのみ影響
- `AnalysisDashboardPanel.tsx` のうち `ImportTabContent` 関数・その props のみ変更

## 戻し方

`git revert` で実装コミット（1件）を戻すだけで完全復旧

## 維持の仕組み

- 守り手: Hikky-dev
- 同じパターン（ExtractionTabContent のグラフ）が壊れたら合わせて修正する
- i18n キーは ja.json / en.json 同時追加が ADR-027 の要件（CI でチェック済み）
