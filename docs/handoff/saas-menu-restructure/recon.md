# recon: SAAS管理者メニュー改善

## 対象ファイル

- `frontend/src/locales/ja.json:266` — `nav.superAdminAnalysisRules: "解析管理"`
- `frontend/src/locales/ja.json:3959` — `analysisRules.page.title: "解析管理"`
- `frontend/src/locales/en.json:266` — `nav.superAdminAnalysisRules: "Analysis Management"`
- `frontend/src/locales/en.json:3959` — `analysisRules.page.title: "Analysis Management"`
- `frontend/src/components/DesktopShell.tsx:191-195` — `saasAdminItems` 配列定義
- `frontend/src/components/DesktopShell.tsx:372-386` — SidebarAccordion で saasAdminItems を表示
- `frontend/src/components/MobileShell.tsx:162-183` — isSuperAdmin ブロックで resolveItem 3件

## 変更前の状態

### DesktopShell.tsx saasAdminItems（変更前）
```
{ to: "/super-admin/analysis-rules", labelKey: "nav.superAdminAnalysisRules" },
{ to: "/super-admin/fx-rate",        labelKey: "nav.superAdminFxRate" },
{ to: "/buyback-prices",             labelKey: "nav.buybackPrices" },
```
- SidebarAccordion コンポーネントでトグル表示

### MobileShell.tsx isSuperAdmin items（変更前）
```
analysisRules → supplierExtractionRules → buybackPrices
```

## 参照ADR

- ADR-027: i18n 強制（全 UI 文字列を t("key") 経由）
- ADR-137: Adaptive Shell Architecture（DesktopShell/MobileShell 分離）
- ADR-144: UIガバナンス（金型コンポーネント使用必須）
