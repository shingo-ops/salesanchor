# Recon: 抽出タブ 3段構成リデザイン

recon: docs/handoff/extraction-tab-redesign/recon.md
作業日: 2026-09-28

## 現在地把握

### 課題

抽出タブに9種以上の要素（ランキング・KPIカード・ボトルネックヒーロー・エラーテーブル・コストセクション等）が混在しており、
インポートタブの3段構成と乖離している。整理・統一が必要。

### 調査結果（事実）

#### フロントエンド（メインファイル）

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1` — メインコンポーネントファイル（858行・ExtractionTabContent 含む）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:1` — スタイルシート（ランキングCSS等含む）
- `frontend/src/locales/ja.json:1` — i18nファイル（ja）
- `frontend/src/locales/en.json:1` — i18nファイル（en）

#### インポートタブ（参照パターン）

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1` — ImportTabContent コンポーネント（3段構成の参照実装）

#### 既存ADR

- ADR-027: i18n強制（全UI文字列はt()経由必須）
- ADR-067: デザイントークン強制（CSS変数経由・色直値禁止）
- ADR-144: UIガバナンス（金型遵守・生select/input禁止）

## まとめ

- 抽出タブは既存APIをそのまま使用（バックエンド変更なし）
- インポートタブ（3段構成）をパターンとして踏襲する方針
- 削除対象: ランキング・ボトルネックヒーロー・KPIカード×4・アラートバッジ・CTAボタン・エラーテーブル・コストセクション
- 追加対象: 正常性カード・推移グラフ・総数テーブルの3段

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | バックエンドAPIのレスポンス型 | AnalysisDashboardPanel.tsx の useAnalysisDashboard フックを確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
