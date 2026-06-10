# DataTable 標準化 バッチ2 設計書

> **参照: recon = docs/handoff/datatable-standardization/recon.md / ADR-067**
> **作成日**: 2026-06-10
> **担当**: Hikky-dev

---

## KGI・KPI

| 基準 | 検証方法 |
|------|---------|
| 対象5ファイルの `<table className="data-table">` が0件になること | `grep -r 'class.*data-table' frontend/src/pages/purchase-orders/ frontend/src/pages/sales/ frontend/src/pages/inventory/OwnInventoryPage.tsx frontend/src/pages/notifications/ frontend/src/pages/erp/` で0件確認（`InventoryPage.tsx` は DataTable 未対応の確定例外: 列非表示・独自チェック複合） |
| TypeScript エラー 0件 | `./node_modules/.bin/tsc --noEmit` でエラーなし |
| 既存 data-testid（po-unreceive-*, po-pdf-*, po-send-email-*, po-resend-email-*, sales-revenue-*, sales-gross-*, sales-rate-*, sales-edit-*）が保持されること | コード差分の目視確認 |
| OwnInventoryPage の pagination UI が未変更であること | `<div className="pagination">` が残存することを確認 |

---

## 設計方針

バッチ1（InvoicesPage、PR #1841）と同一パターンを踏襲:

1. `<table className="data-table">` を `<DataTable<T>>` に置換
2. `DataTableColumn<T>[]` を component body 内で定義（props/state/hooks を参照する必要があるため）
3. `emptyState` prop に既存 i18n キーを流用（新規キー追加なし）
4. `rowKey` は `(row) => String(row.id)` または各型の主キーを使用
5. API 呼び出し・状態管理・pagination UI は一切変更しない

---

## ファイルごとの設計メモ

### PurchaseOrdersPage

- `STATUS_LABELS` は component scope で定義済みのため columns 定義内で参照可能
- `data-testid="purchase-orders-table"` はラッパーに付いていたが DataTable に `className` として移動しない（テストで不要なら省略）
- `data-testid={`po-row-${p.id}`}` は `<tr>` に付いていたが DataTable は tr の data-testid を expose しないため省略。rowKey で識別可能。
- actions セルの各ボタン data-testid はすべて保持

### SalesPage

- `canEdit` フラグで actions 列を条件付き追加: `const columns = [...baseColumns, ...(canEdit ? [actionsCol] : [])]`
- `rowKey={(o) => String(o.order_id)}` （`id` ではなく `order_id`）

### OwnInventoryPage

- `status-badge status-{status}` クラスは `badge badge-{variant}` と異なる独自クラス — そのまま保持
- テーブルは `<div className="table-container">` の内側に DataTable を配置
- `<div className="pagination">` は DataTable の外側にあり、変更対象外

### NotificationsPage

- `is_active` boolean による badge は `status-ssot-exempt` コメント付き — そのまま保持
- `webhook_url` セルの `maxWidth` / `overflow` / `textOverflow` スタイルは `renderCell` 内 span に付与

### ERPPage

- `error_message` セルのインラインスタイル（`color: var(--danger)` 等）は `renderCell` 内 span に付与

---

## 外部・過去事例の参照と我々への応用

参照: `docs/handoff/datatable-standardization/recon.md`（バッチ1・InvoicesPage のパターン定義と DataTable コンポーネント詳細調査）および `docs/adr/ADR-067-design-tokens.md`（デザイントークン強制ルール）。

バッチ1で確立した「component body 内で columns 配列を定義する」パターンをバッチ2でも採用した。columns 定義が props/state/hooks クロージャ内に収まり、`import type { DataTableColumn }` による型安全が保証される。各ページの状態管理ロジックへの影響はゼロ。

条件付き columns の扱い（SalesPage の `canEdit`）はスプレッド演算子パターンで対応:
```ts
const columns = [...baseColumns, ...(canEdit ? [actionsCol] : [])];
```
shadcn/ui・Mantine・Ant Design Table など主要 UI ライブラリはすべて「列定義（columns）+ データ（data）+ rowKey」の分離パターンを採用しており、本バッチもその確立済み手法に準拠する。

---

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| 既存テストが `<table>` セレクタに依存している場合 | DataTable は `<table>` タグを内部で使用するため影響なし |
| `data-testid="purchase-orders-table"` の消失 | E2E で必要なら DataTable の `className` prop で代替可能（現状は省略） |
| `data-testid="po-row-{id}"` の消失 | DataTable は tr を expose しないが、各ボタンの data-testid で識別可能 |
