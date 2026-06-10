# recon: Record Drawer ロールアウト

> 作成: 2026-06-10 | 担当: architect | 変更なし・読み取り専用調査

---

## 1. Suppliers パイロット機構の解剖

### 1-1. ファイル構成（Suppliers パターン）

| ファイル | 役割 |
|---------|------|
| `frontend/src/pages/suppliers/SuppliersPage.tsx` | 一覧＋Drawer統合 |
| `frontend/src/pages/suppliers/SupplierFormFields.tsx` | フォームフィールド共通部品 |
| `frontend/src/pages/suppliers/SupplierEditPage.tsx` | フルページ編集（/suppliers/:id/edit） |
| `frontend/src/components/Drawer.tsx` | Drawerコンポーネント本体 |
| `frontend/src/components/DataTable.tsx` | onRowClick対応テーブル |

### 1-2. 共通化できる部分（全ページ同一ロジック）

S0 リファクタ後の現行実装（`useRecordDrawer` フック利用済み）。

| 役割 | file:line | 実装内容 |
|------|-----------|---------|
| フック呼び出し（開閉＋ID＋フォーム） | `frontend/src/pages/suppliers/SuppliersPage.tsx:43` | `useRecordDrawer<Supplier, SupplierFormState>({ toForm, emptyForm })` |
| `<Drawer>` マウント | `frontend/src/pages/suppliers/SuppliersPage.tsx:129` | `open` / `onClose` / `title` / `onOpenFullPage` |
| フルページ遷移 | `frontend/src/pages/suppliers/SuppliersPage.tsx:134` | `onOpenFullPage: closeDrawer + navigate` |
| 権限ガード (行クリック) | `frontend/src/pages/suppliers/SuppliersPage.tsx:167` | `onRowClick={hasPermission("suppliers.update") ? handleRowClick : undefined}` |
| 権限ガード (編集ボタン) | `frontend/src/pages/suppliers/SuppliersPage.tsx:157` | `hasPermission("suppliers.update") &&` |
| フック本体（共通ロジック） | `frontend/src/hooks/useRecordDrawer.ts:1` | `drawerOpen` / `editId` / `editForm` / `handleRowClick` / `closeDrawer` |

### 1-3. ページ固有部分（各ページが差し込む）

| 役割 | Suppliers での実装 | 他ページでの必要作業 |
|------|-----------------|-----------------|
| フォーム状態型 | `SupplierFormState` (`frontend/src/pages/suppliers/SupplierFormFields.tsx:10`) | `*FormState` 型を定義 |
| フォームフィールド UI | `<SupplierFormFields>` | `*FormFields` コンポーネント作成 or インライン |
| API パス | `/suppliers`, `/suppliers/:id` | エンティティ別パス |
| 保存後コールバック | `frontend/src/pages/suppliers/SuppliersPage.tsx:87` | `closeDrawer(); load();` |
| Drawer タイトル | `t("suppliers.editSupplier")` | i18n キー追加 |
| フルページ route | `/suppliers/:id/edit` | 各エンティティで追加 |
| EditPage コンポーネント | `SupplierEditPage.tsx` | `*EditPage` 作成（FormFields 再利用） |
| 権限キー | `"suppliers.update"` | `"entities.update"` |

### 1-4. Drawer コンポーネント Props（共通部品）

`frontend/src/components/Drawer.tsx:22-30`

```typescript
interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  onOpenFullPage?: () => void;  // 省略時はボタン非表示
  footer?: ReactNode;
}
```

### 1-5. DataTable の onRowClick

`frontend/src/components/DataTable.tsx:71`

```typescript
onRowClick?: (row: T) => void;
```

セル内ボタンクリック時は非発火（`stopPropagation` 不要・DataTable 側で制御済み）。

---

## 2. 対象ページ一覧

> 対象条件: DataTable を持ち、`*.update` 権限での編集 UI が存在するページ。

| ページ | ファイル | DataTable | 現状の編集UI | 既存 FormFields | フルページ route | 権限キー | Drawer 優先度 |
|--------|---------|-----------|------------|----------------|----------------|---------|-------------|
| **Suppliers** ✅ | `pages/suppliers/SuppliersPage.tsx` | ✅ | **Drawer 実装済み** | `SupplierFormFields.tsx` ✅ | `/suppliers/:id/edit` ✅ | `suppliers.update` | **完了** |
| Companies | `pages/companies/CompaniesPage.tsx` | ✅ | Modal（29 inputs） | なし | `/crm/companies/:id` 詳細ページあり | `customers.update` | **A（詳細ページ連携・複雑）** |
| Contacts | `pages/contacts/ContactsPage.tsx` | ✅ | Modal（14 inputs） | なし | なし | `customers.update` | **A** |
| Deals | `pages/deals/DealsPage.tsx` | ✅ | Modal（25 inputs） | なし | なし | `deals.update` | **A** |
| Leads | `pages/leads/LeadsPage.tsx` | ✅ | Modal（31 inputs） | なし | なし | `leads.update` | **A** |
| Teams | `pages/teams/TeamsPage.tsx` | ✅ | Modal（8 inputs） | なし | なし | `teams.update` | **B（フォームが軽量）** |
| Staff | `pages/staff/StaffPage.tsx` | ✅ | Modal（24 inputs） | なし | なし | `staff.update` | **B** |
| Bots | `pages/bots/BotsPage.tsx` | ✅ | Modal（14 inputs） | なし | なし | `bots.update` | **B** |
| Purchase Orders | `pages/purchase-orders/PurchaseOrdersPage.tsx` | ✅ | Modal（特殊: 1 input） | なし | なし | `purchase_orders.update` | **C（PO 特有の複合UI）** |
| Sales | `pages/sales/SalesPage.tsx` | ✅ | インライン編集あり | なし | なし | `orders.update` | **C（受注特有）** |
| Commissions | `pages/commissions/CommissionsPage.tsx` | ✅ | 担当者割当パネル | なし | なし | `orders.update` | **C（特殊パネルUI）** |

---

## 3. 対象外ページ一覧

| ページ | ファイル | 対象外の理由 |
|--------|---------|------------|
| Products | `pages/products/ProductsPage.tsx` | 行クリック → **直接 `/admin/products/:id/edit` へ navigate**（Drawer 不使用の別パターン。現状維持） |
| Invoices | `pages/invoices/InvoicesPage.tsx` | 編集 UI なし。行クリック → `/invoices/:id` 詳細閲覧のみ |
| Orders | `pages/orders/OrdersPage.tsx` | DataTable なし（独自テーブル）。編集は専用 Panel（`editId` 状態あるが Drawer とは別構造） |
| Companies（詳細） | `pages/company-detail/CompanyDetailPage.tsx` | 詳細ページ自体が5タブ構成の閲覧・編集 UI。一覧からは `/crm/companies/:id` へ遷移 |
| Schedule | `pages/schedule/SchedulePage.tsx` | FullCalendar ベース。一覧テーブルなし |
| Roles | `pages/roles/RolesPage.tsx` | 左列サイドバー＋右パネルの独自レイアウト |
| Channels | `pages/channels/ChannelsPage.tsx` | OAuth 接続管理。CRUD なし |
| Dashboard | `pages/dashboard/DashboardPage.tsx` | 集計・概覧のみ |
| AdminHub 系 | `pages/admin/*` | テナント設定・SaaS 管理者向け設定ページ |
| Shifts | `pages/shifts/ShiftsPage.tsx` | `hasPermission("shifts.manage")` あるが、シフト管理は時間軸 UI の特性あり（要別検討） |
| Notifications | `pages/notifications/NotificationsPage.tsx` | 通知は閲覧・既読管理が主目的（編集不要） |
| Inventory（Own） | `pages/inventory/OwnInventoryPage.tsx` | 在庫数量更新は専用アクション。テキストフォーム編集ではない |
| Archives | `pages/archives/ArchivesPage.tsx` | 読み取り専用 |
| StaffReports | `pages/staff-reports/StaffReportsPage.tsx` | レポート閲覧のみ |
| Inbox | `pages/inbox/InboxPage.tsx` | メッセージング UI（会話ベース） |
| Buddy | `pages/buddy/BuddyPage.tsx` | AI 機能 |
| Design系 | `pages/design-*/*` | 開発用 |

---

## 4. 各対象ページの準備状況詳細

### Companies (`pages/companies/CompaniesPage.tsx`)
- フォーム: **29 inputs（住所・多言語・複数セクション）** — フォームが最も複雑
- 特記: `/crm/companies/:id` に **5タブ詳細ページ（CompanyDetailPage）が既存**。`onOpenFullPage` の遷移先はここが自然
- フルページ route: `/crm/companies/:id` ✅（詳細ページとして存在）
- **要検討**: Drawer 内は要約フォーム（主要フィールドのみ）→ フルページで全タブ編集、という分割が適切

### Contacts (`pages/contacts/ContactsPage.tsx`)
- フォーム: 14 inputs
- フルページ route: なし（要追加）
- Companies と同じ `customers.update` 権限

### Deals (`pages/deals/DealsPage.tsx`)
- フォーム: 25 inputs + `CompanyContactSelector` コンポーネント使用（`DealsPage.tsx` 内で import）
- フルページ route: なし（要追加）

### Leads (`pages/leads/LeadsPage.tsx`)
- フォーム: 31 inputs（最大級）
- フルページ route: なし（要追加）
- `SalesPage.tsx` に近い構造

### Teams (`pages/teams/TeamsPage.tsx`)
- フォーム: 8 inputs（最も軽量）
- フルページ route: なし（要追加）
- **ADR-122 で 2件の modal-overlay を Modal に置換済み**（モーダルパターンが最新化）

### Staff (`pages/staff/StaffPage.tsx`)
- フォーム: 24 inputs
- フルページ route: なし（要追加）

### Bots (`pages/bots/BotsPage.tsx`)
- フォーム: 14 inputs
- フルページ route: なし（要追加）

---

## 5. App.tsx の /:id/edit ルート一覧（現状）

`frontend/src/App.tsx`

| route | コンポーネント | line |
|-------|-------------|------|
| `/admin/products/new` | `ProductEditPage` | 150 |
| `/admin/products/:id/edit` | `ProductEditPage` | 151 |
| `/suppliers/:id/edit` | `SupplierEditPage` | 193 |

**それ以外はすべて未追加**。各ページ展開時に追加が必要。

---

## 6. 権限キー一覧（pages 配下 grep 結果）

| エンティティ | 権限キー |
|------------|---------|
| suppliers | `suppliers.update` / `suppliers.delete` / `suppliers.create` |
| teams | `teams.update` / `teams.delete` / `teams.create` |
| staff | `staff.update` / `staff.delete` / `staff.create` |
| bots | `bots.update` / `bots.delete` / `bots.create` |
| contacts | `customers.update` / `customers.delete` / `customers.create` |
| companies | `customers.update` / `customers.delete` / `customers.create` |
| deals | `deals.update` / `deals.delete` / `deals.create` |
| leads | `leads.update` / `leads.delete` / `leads.create` |
| purchase_orders | `purchase_orders.update` / `purchase_orders.delete` / `purchase_orders.create` |
| commissions/sales | `orders.update` / `orders.view` |
| products | `products.update` / `products.delete` / `products.create` |

---

## 7. 共通化の設計案（recon レベル）

### A案: 薄いラッパーフック `useRecordDrawer<T>`

```typescript
// 各ページがこれだけで使える想定
const { drawerOpen, editId, editForm, handleRowClick, closeDrawer } =
  useRecordDrawer<MyFormState>({
    toForm: (record) => ({ name: record.name, ... }),
    emptyForm,
  });
```

**共通化できる**: `drawerOpen`, `editId`, `editForm`, `handleRowClick`, `closeDrawer`

**共通化できない**: フォーム型定義・フォーム UI・API パス・保存ロジック

### B案: 現状通り各ページにコピー（Suppliers パターンを template として）

コード量は増えるが、各ページが独立・revert 容易。現在の Suppliers 実装がほぼコピー元として完成しているため、diff は小さい。

**現状の実装コスト見積もり（B案）**:
- 1ページあたり: `useState` 4行 + `handleRowClick` 5行 + `<Drawer>` 17行 + `onRowClick` 1行 = **約25行追加**
- FormFields 抽出: ページ固有フォームを `*FormFields.tsx` へ切り出し（各20〜80行）
- EditPage: `SupplierEditPage` に倣って作成（約60行テンプレート）
- App.tsx: route 1行追加

---

## 8. 不明・要確認事項

| # | 不明点 | 影響ページ |
|---|--------|---------|
| 1 | Companies は詳細ページ（5タブ）が既存。Drawer でどのフィールドまで編集させるか（全項目 vs 主要項目のみ）| Companies |
| 2 | Deals / Leads のフォームは 25〜31 inputs と大きい。Drawer 内に全部収まるか（スクロール可だが UX 要確認）| Deals, Leads |
| 3 | `CompanyContactSelector`（Deals 内で使用）は Drawer サイズで動作するか | Deals |
| 4 | `useRecordDrawer` フック化 vs コピーパターン — どちらを選ぶか（設計判断）| 全ページ |
| 5 | Products は現状「行クリック → `/admin/products/:id/edit` へ直接 navigate」。Drawer を入れるか現状維持か | Products |
| 6 | Shifts は `shifts.manage` 権限（update とは別）。対象に含めるか | Shifts |
