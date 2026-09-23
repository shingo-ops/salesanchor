# Recon: analysis-rules-master-panels

**設計**: docs/handoff/analysis-rules-master-panels/design.md

## 調査日
2026-09-19

## ADR調査
- ADR-027: `docs/adr/ADR-027-ui-internationalization.md` — 全UI文字列 t("key") 強制
- ADR-144: `docs/CC_UI_GOVERNANCE.md` — UI部品金型クラス強制

## 変更対象ファイル（file:line）

### 読み取り元（変更なし）
- `frontend/src/pages/super-admin/TcgProductMasterPage.tsx:1-95` — 商品マスタページ全体
- `frontend/src/pages/super-admin/SupplierMasterPage.tsx:1-462` — 仕入元マスタページ全体

### 作成
- `frontend/src/pages/super-admin/components/ProductMasterPanel.tsx` — 新規作成（TcgProductMasterPage からPageLayout除去・useSuperAdmin除去・ContentToolbar追加）
- `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx` — 新規作成（SupplierMasterPage からPageLayout除去・useSuperAdmin除去・ContentToolbar追加）

### 編集
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-14` — AnalysisRulesSidebarKey に "product-master" | "supplier-master" 追加
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:66-75` — マスタ管理グループ（hub-subnav-section）追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:21-22` — ProductMasterPanel / SupplierMasterPanel import 追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:134-135` — 2パネルの条件レンダリング追加
- `frontend/src/components/DesktopShell.tsx:190-196` — saasAdminItems から supplier-master / tcg-product-master を削除（2項目）
- `frontend/src/locales/ja.json:3778` — subtitle・sidebar.groupMasterManagement・productMaster・supplierMaster 追加
- `frontend/src/locales/en.json:3778` — 同上（英語）

## 触らないファイル
- `frontend/src/pages/super-admin/TcgProductMasterPage.tsx` — 既存スタンドアロンルート維持
- `frontend/src/pages/super-admin/SupplierMasterPage.tsx` — 既存スタンドアロンルート維持
- `frontend/src/App.tsx` — ルート定義変更なし
