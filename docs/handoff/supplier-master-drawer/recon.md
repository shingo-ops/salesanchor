# recon: 仕入元マスタ Drawer化・ボタン整理

## 対象ファイル（変更前の状態）

- `frontend/src/pages/super-admin/SupplierMasterPage.tsx:1-435` — 改修対象。Modal/ConfirmModal/selectable/一括削除ボタン/行編集ボタン使用
- `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:1-262` — Drawerパターンのお手本
- `frontend/src/components/Drawer.tsx:1-197` — Drawer コンポーネントのインターフェース確認
- `frontend/src/components/Button.tsx:1-89` — Button variant確認（primary/secondary/ghost/danger/outline/tab）
- `frontend/src/pages/super-admin/TcgProductMasterPage.tsx:1-95` — ページ側Drawer使用パターン確認
- `frontend/src/locales/ja.json:2447-2477` — superAdmin.suppliersAdmin 既存キー
- `frontend/src/locales/en.json:2447-2477` — superAdmin.suppliersAdmin 既存キー（en）

## 既存 ADR 検索結果

- ADR-027: i18n強制 — 全UI文字列 `t()` 経由必須
- ADR-144: UIガバナンス — 生select/生input禁止・例外は `ui-allow` コメント必須

## 既存の課題

- 検索ボタンが ContentToolbar right に存在（PO指示: 削除）
- ヘッダーに「削除」ボタンが存在（PO指示: 削除）
- DataTable に selectable/チェックボックスあり（PO指示: 削除）
- 行編集 (`_edit`) 列あり（PO指示: 削除）
- 詳細表示が Modal（PO指示: Drawer に変更）
