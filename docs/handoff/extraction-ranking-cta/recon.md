# Recon: extraction-ranking-cta

## 対象ファイル
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx`
- `frontend/src/locales/ja.json`
- `frontend/src/locales/en.json`

## 現状確認

### ランキングセクション（CTAなし）
- `AnalysisDashboardPanel.tsx:1202` — 抽出率ワースト提供者セクション (`analysis-dashboard-ranking-section`)
- `AnalysisDashboardPanel.tsx:1255` — 照合率ワースト商品セクション (`analysis-dashboard-ranking-section`)
- 両セクションとも「詳しく見る」ボタン (Button variant="ghost") と詳細テーブルはあったが、CTAボタンは存在しなかった

### 既存CTAパターン
- `AnalysisDashboardPanel.tsx:1435-1444` — `analysis-dashboard-ctas` div + `analysis-dashboard-cta-btn` ボタン + ArrowRightIcon(size=16)
- `AnalysisDashboardPanel.tsx:1350-1358` — `analysis-dashboard-cta-btn--primary` バリアントの例

### ナビゲーションキー（有効値）
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:16-21`
  - `"extraction-rules"` (line 16)
  - `"product-master"` (line 17)
  - `"supplier-master"` (line 21)

### i18nキー（既存）
- `frontend/src/locales/ja.json:4134-4146` — extractionRank* キー群
- `frontend/src/locales/en.json:4134-4146` — 同上

### onNavigate受け渡し
- `ExtractionTabContentProps` (line 1003) — `onNavigate: (key: AnalysisRulesSidebarKey) => void` 定義済み
- `ExtractionTabContent` コンポーネント (line 1014) — `onNavigate` props受け取り済み

## 関連ADR
- ADR-027: i18n強制（全UIテキストはt("key")経由）
- ADR-138: extraction ranking API設計
- ADR-144: UIガバナンス（既存コンポーネント使用必須）
