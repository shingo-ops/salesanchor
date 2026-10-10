# AY-2j recon: 完売の結果の原文を Drawer で開く・列の整理

実測時の origin/main: 0c1dca8dc。調査全文は /tmp/CC報告ファイル/super-admin-menu/sold-out-drawer-recon.md。
既存 ADR の検索: 画面の構成を定める ADR は調査では見つかっていない。関連は ADR-027（i18n）と ADR-144（UI 金型）。

## 1. 現在地（変更前）
- frontend/src/pages/super-admin/components/SoldOutResultsPanel.tsx の SourceDetail は details と summary の中に、dl（原文の商品名・状態語・備考）、invalidSpan の p、pre（該当行は mark）を持つ。
- 列は8本（判定の固定表示と原文表示を含む）。DataTable に onRowClick は無い。
- frontend/src/components/Drawer.tsx は open・onClose・title・children を受け、Esc・外側クリック・× で閉じる。
- frontend/src/components/DataTable.tsx は列の width と onRowClick を持つ。onRowClick は行を tabIndex=0 にし、Enter と Space にも反応する。
- 前例: frontend/src/pages/super-admin/components/NoteMasterPanel.tsx（Drawer）、frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx（onRowClick）。
- 試験 frontend/src/pages/super-admin/components/SoldOutResultsPanel.test.tsx は列の位置と details を検査していた。

## 2. PO の決定（2026-10-10）
- 原文の表示を、右から出る Drawer にする（y）。
- 判定列と原文表示列をなくし、行のどこを押しても原文が出る。商品名の列に幅の上限を付ける（y）。

## 3. 画面幅
PO の表示幅は CSS 換算で約1450px と推定（推定、実測ではない）。検証は幅1280と1440で行う。
