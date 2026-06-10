# DataTable 標準化 バッチ5 — Recon

## 対象ファイル

| ファイル | raw table 行 | 列数 | 特記 |
|---------|------------|------|------|
| `frontend/src/pages/suppliers/SuppliersPage.tsx:101` | line 101 | 6列 | 行クリック→編集モーダル / 外部 pagination div |

## 特記事項

### SuppliersPage.tsx
- 行クリック（`onRowClick`）: DataTable の `onRowClick` prop に移行。`hasPermission("suppliers.update")` 時のみ設定。
  DataTable 内蔵の二重発火防止（`isInteractiveTarget`）により、button/a クリック時は `onRowClick` は発火しない。
  元コードの手動 `closest("button")` ガードは DataTable の実装に代替される。
- `data-testid="supplier-row-{id}"`: tr 要素に付いていたが DataTable は tr を expose しない → 省略（E2E テストで未使用、grep 確認済み）
- `title={t("suppliers.openDetail")}`: DataTable は tr に title を付与しない → 省略（スクリーンリーダー非必須・視覚的 tooltip のみ）

## pagination 扱い

外部 `<div className="pagination" data-testid="suppliers-pagination">` は DataTable の外側に存在し、変更対象外。
DataTable の組み込み pagination（`page`/`hasNextPage`/`onPageChange`）は使用しない。
理由: 既存 pagination の sticky bottom スタイリング（`position: sticky; bottom: 0; background: var(--bg-surface); ...`）と `data-testid` をそのまま保持するため。

## パターン参照

- `docs/handoff/datatable-standardization/recon.md` — 全体 recon（SuppliersPage の onRowClick 記載あり）
