# DataTable 標準化 バッチ5 設計書

> **参照: recon = docs/handoff/datatable-batch5/recon.md / docs/handoff/datatable-standardization/recon.md / ADR-067**
> **作成日**: 2026-06-10
> **担当**: Hikky-dev

---

## KGI・KPI

| 基準 | 検証方法 |
|------|---------|
| `frontend/src/pages/suppliers/SuppliersPage.tsx` の `<table className="data-table">` が0件 | `grep -r 'class.*data-table' frontend/src/pages/suppliers/` で0件確認 |
| TypeScript エラー 0件 | `./node_modules/.bin/tsc --noEmit` でエラーなし |
| 外部 `<div className="pagination" data-testid="suppliers-pagination">` が残存すること | grep 確認 |
| 行クリック→編集モーダル動作が DataTable `onRowClick` で再現されること | Evaluator 視覚確認 |

---

## 設計方針

バッチ1〜4と同一パターンを踏襲。SuppliersPage 固有の点:

1. `<table className="data-table">` を `<DataTable<Supplier>>` に置換
2. `onRowClick`: DataTable の `onRowClick?: (row: T) => void` prop を使用
   - `hasPermission("suppliers.update")` が true の場合のみ渡す（false 時は undefined）
   - DataTable 内蔵の `isInteractiveTarget` が button/a クリックの二重発火を自動防止
3. 外部 `<div className="pagination">`: DataTable の外側にあり、**変更対象外**
   - DataTable 組み込み pagination (`page`/`hasNextPage`/`onPageChange`) は使用しない
   - 既存 sticky 下部スタイリングと `data-testid` をすべて保持

**省略項目**:
- `data-testid="supplier-row-{id}"`: E2E テスト未使用、DataTable が tr を expose しないため省略
- `title={t("suppliers.openDetail")}`: DataTable は tr に title を付与しない → 省略（視覚的 tooltip のみで screen reader 非必須）

---

## 外部・過去事例の参照と我々への応用

参照: `docs/handoff/datatable-batch5/recon.md`（SuppliersPage の行クリック・pagination 特記事項）および `docs/handoff/datatable-standardization/recon.md`（全体 recon）。

DataTable の `onRowClick` prop（バッチ3で recon 更新済み、DataTable 本体は既実装）は、React のコールバックパターンに合致した controlled design。shadcn/ui Table・Ant Design Table など主要ライブラリが `onRowClick` を標準 prop として持つ確立済み設計。外部 pagination の保持は「DataTable 標準化 = テーブル内の DOM 置換のみ、周辺 UX は現状維持」という本プロジェクトの一貫した方針に従う。

---

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| `data-testid="supplier-row-{id}"` の消失 | E2E テストで未使用（grep 確認済み）→ 影響なし |
| `title` 属性の消失 | 視覚的 tooltip のみ。スクリーンリーダーは aria-label で代替（DataTable の `aria-label="data table"` が存在） |
| DataTable の `isInteractiveTarget` がカバーしない要素でのクリック | `button, a, input, select, textarea, label` をカバー。現在の actions 列はすべてボタン → 問題なし |
