# DataTable 標準化 バッチ1 — Recon

## 対象ファイル（変更前の raw table 位置）

| ファイル | raw table 行 | 列数 |
|---------|------------|------|
| `frontend/src/pages/orders/OrdersTable.tsx:69` | line 69 | 9列 |
| `frontend/src/pages/staff/StaffPage.tsx:292` | line 292 | 5列 |
| `frontend/src/pages/bots/BotsPage.tsx:247` | line 247 | 7列 |
| `frontend/src/pages/shifts/ShiftsPage.tsx:74` | line 74 | 6列 |
| `frontend/src/pages/archives/ArchivesPage.tsx:33` | line 33 | 5列 |

## DataTable コンポーネント

- `frontend/src/components/DataTable.tsx` — 汎用 DataTable（Task 4C）
- `frontend/src/components/DataTable.css` — スタイル
- `DataTableColumn<T>` 型: key: string, header, renderCell?, width?, sortable?

## パイロットテンプレート参照

- `frontend/src/pages/invoices/InvoicesPage.tsx:63` — columns 定義パターン（PR #1841）

## 依存ユーティリティ

- `frontend/src/utils/statusPresentation.ts` — `getStatusPresentation(entity, status)`
- `frontend/src/pages/orders/useOrdersState.ts` — `fmtCurrency`, `orderPhase`
- `frontend/src/hooks/usePermissions.ts` — `hasPermission(key)`

## 各ファイルの特記事項

### OrdersTable.tsx
- `shippings` / `purchases` props を renderCell クロージャ内で参照
- `PHASE_LABELS` は `t()` を使うため component body 内で定義
- `data-testid` 属性 7件: `ship-cell-to-*`, `flow-cell-*`, `mark-paid-*`, `mark-purchased-*`, `issue-label-*`, `mark-unpaid-*`, `open-shipping-*`, `open-purchase-*`

### StaffPage.tsx
- loading 分岐内で IIFE パターン（`() => { ... })()`）で columns 定義
- `emails.length > 0` で "+N" インジケーター表示

### BotsPage.tsx
- `purposeLabel` / `statusLabel` は component スコープの関数 → renderCell から参照

### ShiftsPage.tsx
- `shift_type` セルは `badge badge-negotiating` クラスの badge
- `user_id` / `source_id` は数値型 → `String()` 変換して返却

### ArchivesPage.tsx
- `restored_at` 有無で条件分岐（restore ボタン or "restored" badge）
