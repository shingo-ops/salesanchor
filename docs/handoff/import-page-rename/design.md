# 設計 — import-page-rename

**対象ADR**: ADR-027（i18n）、ADR-144（UIガバナンス）
**recon**: `docs/handoff/import-page-rename/recon.md`
**日付**: 2026-09-20
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし: hub-shell レイアウトへの統合は本プロジェクト内の AnalysisRulesPage で実績があり、同じパターンを適用する。外部事例の参照は不要と判断。

---

## 受け入れ基準

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | ページ名が「インポート」に変更されている | サイドバーのラベルを目視確認 |
| 2 | グローバルサイドバーからインポート項目が消えている | SaaS管理者アコーディオンを展開して確認 |
| 3 | 解析管理サイドバーの解析状況セクションに「インポート」がある | 解析管理ページを開いて確認 |
| 4 | インポートページに hub-shell レイアウトとサイドバーが表示される | /super-admin/tcg-line-import を開いて確認 |
| 5 | サイドバーの他の項目クリックで解析管理ページに遷移する | インポートページのサイドバーで「完売ルール」をクリック |
| 6 | i18n: 日本語/英語の両方で正しいラベル | 言語切替で確認 |

---

## 技術 How

### 変更内容

1. i18n キー変更（ja.json/en.json）: ページ名を「インポート」/「Import」に変更、サイドバーキー追加
2. DesktopShell.tsx: saasAdminItems からインポート項目を削除
3. AnalysisRulesSidebar.tsx: "import" を AnalysisRulesSidebarKey に追加、navItem を解析状況セクションの先頭に配置
4. AnalysisRulesPage.tsx: import 選択時に useNavigate で /super-admin/tcg-line-import に遷移
5. TcgLineImportPage.tsx: hub-shell レイアウトに変換、AnalysisRulesSidebar を共有、navKey を解析管理に変更

---

## 弊害・トレードオフ

| リスク | 影響 | 対策 |
|--------|------|------|
| インポートページのブックマークが無効になる | URLは /super-admin/tcg-line-import のまま変更なし | 影響なし |
| PageLayout の titleText がなくなる | サイドバーの「インポート」ラベルで現在地がわかる | 解析管理ページと同じパターン |

---

## 維持の仕組み

守り手: AnalysisRulesSidebarKey 型定義（TypeScript が型不一致を検出）、hub-shell.css 金型クラス（ADR-144）

---

## 変更対象ファイル

### 触るファイル

| ファイル | 変更内容 |
|---------|---------|
| frontend/src/locales/ja.json | ページ名変更 + サイドバーキー追加 |
| frontend/src/locales/en.json | 同上（英語） |
| frontend/src/components/DesktopShell.tsx | saasAdminItems からインポート削除 |
| frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx | import キー追加 |
| frontend/src/pages/super-admin/AnalysisRulesPage.tsx | import 遷移ハンドラ追加 |
| frontend/src/pages/super-admin/TcgLineImportPage.tsx | hub-shell レイアウト変換 |
| frontend/src/pages/super-admin/TcgSoldOutPage.test.tsx | サイドバーテスト修正 |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| frontend/src/App.tsx | ルーティング変更なし（URLそのまま） |
| backend/ | バックエンド変更なし |
