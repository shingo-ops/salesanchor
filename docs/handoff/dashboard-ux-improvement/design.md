# Dashboard UX Improvement — Design

**対象ADR**: ADR-027, ADR-067, ADR-144
**recon**: docs/handoff/dashboard-ux-improvement/recon.md

## 目的
非エンジニアが解析パイプラインのボトルネックを一目で理解し、次のアクションに迷わない画面にする。

## 設計（認知科学ベース）

### レイアウト構成（F字パターン）
1. ボトルネックヒーロー — 最悪指標を自動検出し最上部に赤/黄で表示
2. 信号灯KPIカード — 緑≥80% / 黄60-79% / 赤<60%
3. CTAボタン — 要確認一覧・商品マスタ・解析精度管理へ直接遷移
4. トレンドグラフ — 7日間の日別推移（recharts LineChart）
5. 詳細セクション — 理由内訳・エンジン情報・エラー

### 信号灯閾値

| 基準 | 検証方法 |
|------|---------|
| 緑: rate ≥ 80% | KPIカード上辺が緑ボーダー |
| 黄: 60% ≤ rate < 80% | KPIカード上辺が黄ボーダー |
| 赤: rate < 60% | KPIカード上辺が赤ボーダー |

### 変更前後

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| KPIカード | 数値のみ表示 | 信号灯ボーダー付き |
| ボトルネック表示 | なし | 最上部ヒーローバナー |
| 次のアクション | 手動でサイドバー遷移 | CTAボタンで直接遷移 |
| トレンド | なし | 7日間LineChart |
| API | pipeline-summary のみ | +trend エンドポイント |

## 外部・過去事例の参照と我々への応用
- Datadog/Grafana: 信号灯ステータスページ + ヒーロー指標パターン。最悪値を最上部に配置し、ドリルダウンを下部に置く構成を採用。
- Google Material Design: コンテキスト色（赤/黄/緑）は「ステータス」を表す標準UXパターン。我々の閾値（80%/60%）は業務SLA感覚に合わせ設定。

## 維持の仕組み
守り手: frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx の getSignalLevel() 定数 + backend/app/services/tcg_analysis_dashboard_svc.py の days バリデーション
- 信号灯閾値（80%/60%）は定数で管理（AnalysisDashboardPanel.tsx内）。将来の調整は定数変更のみ。
- トレンドAPI の days パラメータは 1-90 に制限（SQLインジェクション対策）。
- onNavigate は optional prop（既存の使用箇所に影響なし）。

## ADR準拠
- ADR-027, ADR-067, ADR-144
