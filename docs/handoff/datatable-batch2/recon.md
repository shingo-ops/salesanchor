# DataTable 標準化 バッチ2 Recon

> **作成日**: 2026-06-10
> **担当**: Hikky-dev
> **ステータス**: 完了

---

## 対象ファイル（file:line）

| ファイル | 対象行 | 内容 |
|----------|--------|------|
| `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:203` | 203 | `<table className="data-table" data-testid="purchase-orders-table">` → DataTable 置換 |
| `frontend/src/pages/sales/SalesPage.tsx:110` | 110 | `<table className="data-table">` → DataTable 置換 |
| `frontend/src/pages/inventory/OwnInventoryPage.tsx:120` | 120 | `<table className="data-table">` → DataTable 置換（pagination UIは変更なし） |
| `frontend/src/pages/notifications/NotificationsPage.tsx:70` | 70 | `<table className="data-table">` → DataTable 置換 |
| `frontend/src/pages/erp/ERPPage.tsx:58` | 58 | `<table className="data-table">` → DataTable 置換 |

---

## DataTable コンポーネント参照

`frontend/src/components/DataTable.tsx:28` — `DataTableColumn<T>` 型定義  
`frontend/src/components/DataTable.tsx:44` — `DataTableProps<T>` 型定義  
`frontend/src/components/DataTable.tsx:101` — `DataTable<T>` 関数コンポーネント本体

---

## 各ページの列構成

### PurchaseOrdersPage（6列）

| key | header | 特記事項 |
|-----|--------|---------|
| `po_number` | `t("purchaseOrders.poNumber")` | `mono` class |
| `total_amount` | `t("common.amount")` | `¥${toLocaleString()}` or "-" |
| `status` | `t("common.status")` | `getStatusPresentation("purchaseOrder", ...)` + `STATUS_LABELS` |
| `ordered_at` | `t("purchaseOrders.orderedAt")` | `toLocaleDateString()` or "-" |
| `received_at` | `t("purchaseOrders.receivedAt")` | `toLocaleDateString()` or "-" |
| `actions` | `t("common.actions")` | 複合ボタン（data-testid: po-unreceive-*, po-pdf-*, po-send-email-*, po-resend-email-*） |

`frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:80` — STATUS_LABELS 定義

### SalesPage（7〜8列）

| key | header | 特記事項 |
|-----|--------|---------|
| `order_number` | `t("orders.orderNumber")` | |
| `name` | `t("common.name")` | `contact_display_name ?? company_name ?? "-"` |
| `revenue_amount` | `t("sales.revenue")` | `data-testid="sales-revenue-{order_id}"` |
| `cost_total` | `t("sales.cost")` | |
| `gross_profit` | `t("sales.grossProfit")` | `data-testid="sales-gross-{order_id}"` |
| `gross_profit_rate` | `t("sales.grossProfitRate")` | `data-testid="sales-rate-{order_id}"` |
| `created_at` | `t("common.createdAt")` | `toLocaleDateString("ja-JP")` |
| `actions` | `t("common.actions")` | `canEdit` が true のときのみ追加。`data-testid="sales-edit-{order_id}"` |

`frontend/src/pages/sales/SalesPage.tsx:42` — `fmt` 関数  
`frontend/src/pages/sales/SalesPage.tsx:46` — `fmtRate` 関数  
`frontend/src/pages/sales/SalesPage.tsx:54` — `canEdit = hasPermission("orders.update")`

### OwnInventoryPage（8列）

| key | header | 特記事項 |
|-----|--------|---------|
| `product_id` | `t("ownInventory.col.productId")` | |
| `condition` | `t("ownInventory.col.condition")` | `?? "-"` |
| `physical_qty` | `t("ownInventory.physicalQty")` | `qty-cell` class |
| `reserved_qty` | `t("ownInventory.reservedQty")` | `qty-cell` class |
| `available_qty` | `t("ownInventory.availableQty")` | `availableQty(row)` 関数呼び出し, `qty-cell qty-available` class |
| `unit_price` | `t("ownInventory.col.unitPrice")` | `toLocaleString()` or "-" |
| `status` | `t("ownInventory.col.status")` | `status-badge status-{status}` class（`badge badge-*` でなく独自クラス） |
| `actions` | `t("ownInventory.col.actions")` | reserve/release/ship ボタン（aria-label付き） |

`frontend/src/pages/inventory/OwnInventoryPage.tsx:98` — `availableQty()` 関数  
テーブルは `<div className="table-container">` の内側。その後の `<div className="pagination">` は未変更。

### NotificationsPage（4列）

| key | header | 特記事項 |
|-----|--------|---------|
| `channel_name` | `t("settings.channelName")` | |
| `webhook_url` | `"Webhook URL"` | `mono` class + `maxWidth: var(--col-width-url)` |
| `status` | `t("common.status")` | `badge badge-won` or `badge badge-lost`（`is_active` boolean、`status-ssot-exempt`） |
| `actions` | `t("common.actions")` | `notifications.manage` 権限ゲート削除ボタン |

### ERPPage（7列）

| key | header | 特記事項 |
|-----|--------|---------|
| `sync_type` | `t("erp.colType")` | |
| `direction` | `t("erp.colDirection")` | `export` or `import` 判定 |
| `record_count` | `t("erp.colCount")` | |
| `status` | `t("common.status")` | `getStatusPresentation("erpJobStatus", ...)` |
| `started_at` | `t("erp.colStartedAt")` | `toLocaleString()` |
| `completed_at` | `t("erp.colCompletedAt")` | `toLocaleString()` or "-" |
| `error_message` | `t("common.error")` | `color: var(--danger)`, `maxWidth: var(--col-width-medium)` |

---

## 参照 ADR

- `docs/adr/ADR-067-design-tokens.md` — デザイントークン強制ルール
