# recon: import match rate CTA

## 調査対象ファイル

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:507-522` — 名前の一致率行（ImportTabContent内）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:207` — onNavigate prop定義
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:538-545` — 既存CTA（要対応行・pendingCount > 0条件）
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:19` — "supplier-master" キー（AnalysisRulesSidebarKey型）
- `frontend/src/locales/ja.json:3949` — "importReviewCta": "確認する →"（既存CTAテキスト）
- `frontend/src/locales/en.json:3949` — "importReviewCta": "Review →"（既存CTAテキスト）

## 既存ADR調査

- ADR-027: i18n強制 — 全UI文字列はt("key")経由必須
- ADR-067: デザイントークン — analysis-dashboard-cta-btn クラスは既存スタイルトークン準拠
- ADR-144: UIガバナンス — 既存金型（Card/Badge/button クラス）のみ使用

## matchRate計算箇所

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:417`
```
const matchRate = (1 - (data.unresolved_rate ?? 0)) * 100;
```

100%未満: unresolved_rate > 0（未解決名あり）→ サプライヤーマスタで修正可能
