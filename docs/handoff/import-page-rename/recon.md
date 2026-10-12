# recon — import-page-rename

**日付**: 2026-09-20
**担当**: Planner

---

## 調査対象

「取込・解析・配信」ページを「インポート」にリネームし、解析管理サブメニューへ移動する。

## 現状

- ページ名: `frontend/src/locales/ja.json:258` — `"superAdminTcgLineImport": "取込・解析・配信"`
- ページタイトル: `frontend/src/locales/ja.json:3434` — `"pageTitle": "取込・解析・配信"`
- グローバルサイドバー: `frontend/src/components/DesktopShell.tsx:191` — saasAdminItems に独立項目として配置
- ページレイアウト: `frontend/src/pages/super-admin/TcgLineImportPage.tsx:270` — 独立 PageLayout（hub-shell なし）
- 解析管理サイドバー: `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — 6項目（import なし）
- 解析管理ページ: `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — hub-shell レイアウト

## 既存ADR

- ADR-027: i18n 強制（全UI文字列は t("key") 経由）
- ADR-144: UIガバナンス（金型クラスのみ使用）

## 関連テスト

- `frontend/src/pages/super-admin/TcgSoldOutPage.test.tsx:114` — サイドバーにインポートリンクの存在を検証するテスト（要修正）
