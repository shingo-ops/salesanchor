# recon: import-tab-summary-card

## 概要
インポートタブの4枚KPIカードを1枚のサマリーカードに統合するUX改善。

## 対象ファイル（file:line）

- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:399-574 — ImportTabContent 関数（4KPIカード → サマリーカード1枚）
- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:29-38 — インポートタブのCSS
- frontend/src/locales/ja.json — analysisRules.dashboard キー群
- frontend/src/locales/en.json — analysisRules.dashboard キー群

## 既存ADR検索結果

- ADR-027: UI文字列の i18n 強制 — 適用済み
- ADR-067: デザイントークン強制 — 適用済み
- ADR-144: UIガバナンス（Card/Badge 金型使用） — 適用済み

## 現状の課題

PO指摘: 4枚のKPIカードは非エンジニアには読みにくい。
- 「インポート総数297件」→ 内部的な処理回数で意味不明
- 「未解決名率0.2%」→ ネガティブフレーミングで良好時も不安に見える
- 4枚を順番に読んで状態を判断する必要がある

## 変更方針

- 4枚 → 1枚のサマリーカードに統合
- 信号灯ヘッダーで即時状態判断
- matchRate = (1 - unresolved_rate) * 100 でポジティブフレーミング
- CTAボタンは pendingCount > 0 の場合のみ表示
- トレンドグラフ・直近インポート一覧はそのまま維持
