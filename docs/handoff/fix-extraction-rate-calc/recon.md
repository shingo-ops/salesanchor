# recon: fix-extraction-rate-calc

## 対象ファイル

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:839-842` — extractionSuccessRate 計算
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:852-862` — トレンドグラフの extractionRate / errorRate 計算
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:864-872` — extractionSupplierRows（ランキング）

## 問題

### 1. KPI成功率の計算式に empty が含まれる

`extractionSuccessRate` の分母が `data.extraction.total`（全ジョブ数）。
`total` は `done + error + empty + pending + running` の合計。

挨拶・LINE通知などの商品データのないメッセージは `empty` ステータスになる。
分母に empty が入ると、empty が多い提供者の成功率が過小評価される。

**現状**: `done / (done + error + empty + pending + running)` — `data.extraction.total` を使用
**問題**: empty は処理成功でも失敗でもない。成功率の評価対象外

### 2. トレンドグラフも同様の問題

`extraction_total`（= COUNT(*) 全ステータス）を分母に使用。
TrendDay 型に `extraction_empty` フィールドがないため、exactly done+error に絞れていなかった。

### 3. empty のみの提供者がランキングに表示される

`extractionSupplierRows` が全提供者を表示。
商品不在メッセージしか持たない提供者（`done == 0 && error == 0`）も表示され、
視覚的に問題ありと誤解される。

## ADR

- ADR-138（抽出パイプライン設計・TCGダッシュボード）を確認。成功率の定義変更に該当。
