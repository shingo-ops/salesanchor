# DataTable 標準化 Phase 2 Recon

> **作成日**: 2026-06-09  
> **担当**: architect（読み取り専用。アプリコード変更0件）  
> **ステータス**: 完了

---

## 1. 既存 DataTable コンポーネントの機能範囲

`frontend/src/components/DataTable.tsx`

### Props 定義

| prop | 型 | 説明 | file:line |
|------|----|------|-----------|
| `columns` | `DataTableColumn<T>[]` | 列定義（key/header/width/sortable/renderCell） | `frontend/src/components/DataTable.tsx:26` |
| `data` | `T[]` | 表示データ配列 | `frontend/src/components/DataTable.tsx:43` |
| `rowKey` | `(row: T) => string` | 行識別子ファクトリ（必須） | `frontend/src/components/DataTable.tsx:46` |
| `sortKey` | `string?` | 現在ソート中の列 key | `frontend/src/components/DataTable.tsx:48` |
| `sortDir` | `'asc' \| 'desc'` | ソート方向（既定 asc） | `frontend/src/components/DataTable.tsx:50` |
| `onSort` | `(key, dir) => void` | ソートクリック時コールバック | `frontend/src/components/DataTable.tsx:52` |
| `selectable` | `boolean` | チェックボックス列表示 | `frontend/src/components/DataTable.tsx:54` |
| `selectedKeys` | `Set<string>` | 選択済み rowKey 集合 | `frontend/src/components/DataTable.tsx:56` |
| `onSelectChange` | `(keys) => void` | 選択変更コールバック | `frontend/src/components/DataTable.tsx:58` |
| `density` | `'compact' \| 'default' \| 'relaxed'` | 行高さバリアント | `frontend/src/components/DataTable.tsx:60` |
| `emptyState` | `ReactNode` | 0件時表示スロット | `frontend/src/components/DataTable.tsx:62` |
| `className` | `string` | ラッパー追加クラス | `frontend/src/components/DataTable.tsx:63` |

### 実装済み機能（file:line）

- **全行選択 / 個別選択**（indeterminate 対応）: `frontend/src/components/DataTable.tsx:90`
- **ソートクリックハンドラ**（asc/desc トグル）: `frontend/src/components/DataTable.tsx:110`
- **カスタムセルレンダラー**（`renderCell` prop）: `frontend/src/components/DataTable.tsx:213`
- **density バリアント**: `frontend/src/components/DataTable.tsx:117`
- **空状態スロット**: `frontend/src/components/DataTable.tsx:181`
- **水平スクロール**（`.comp-table` ラッパー）: `frontend/src/components/DataTable.tsx:124`

### 現時点で未実装の機能（ギャップ）

| 機能 | 状況 | 影響ページ |
|------|------|-----------|
| `onRowClick`（行クリック） | **未実装** — tr に onClick なし | LeadsPage / SuppliersPage / ContactsPage 等 |
| ページネーション | **未実装** — 呼び出し側責任 | InventoryPage / ProductsPage |
| 2段ヘッダー | **未実装** | ProductsPage のみ |
| 行ドラッグ並び替え | **未実装** | ProductsPage のみ |
| 列非表示トグル | **未実装** | InventoryPage のみ |

> **注意**: `onRowClick` 未実装は最も影響範囲が大きい。行クリックが必要なページでは「アクションボタン列（renderCell）」で代替するか、DataTable 本体に `onRowClick` を追加する必要がある。

---

## 2. 現在 DataTable を使用しているページ

**実ページ（App.tsx ルート）での DataTable 採用: 0件**

```
grep -rn "<DataTable" frontend/src/pages → 0件（design-preview のデモのみ）
```

`frontend/src/pages/design-preview/sections/DataTableSection.tsx:87,105` にデモ実装あり（本番ページへの採用なし）。

---

## 3. raw `<table>` 実装一覧（App.tsx ルート対象）

### 3-A. メインアプリ実ページ（27件）

| ページ | file:line | 列数 | ソート | 選択 | ページネ | 行click | 特記 |
|--------|-----------|:----:|:------:|:----:|:--------:|:-------:|------|
| `quotes/QuotesPage.tsx` | `frontend/src/pages/quotes/QuotesPage.tsx:161` | 9 | ✅クライアント | なし | なし | なし（ボタン） | useMemo ソート・全8列sortable |
| `invoices/InvoicesPage.tsx` | `frontend/src/pages/invoices/InvoicesPage.tsx:90` | 9 | なし | なし | なし | なし（ボタン） | 通貨フォーマット |
| `orders/OrdersTable.tsx` | `frontend/src/pages/orders/OrdersTable.tsx:69` | 9 | なし | なし | なし | なし（ボタン） | OrdersPage 専用コンポーネントに分離済み |
| `leads/LeadsPage.tsx` | `frontend/src/pages/leads/LeadsPage.tsx:362` | 8+1条件 | なし | なし | なし | ✅（編集） | 優先度スコア列（条件表示） |
| `companies/CompaniesPage.tsx` | `frontend/src/pages/companies/CompaniesPage.tsx:398` | 7 | なし | なし | なし | なし（リンク） | `<a>` リンク列あり |
| `contacts/ContactsPage.tsx` | `frontend/src/pages/contacts/ContactsPage.tsx:325` | 10 | なし | なし | なし | なし（ボタン） | 電話/メール表示 |
| `deals/DealsPage.tsx` | `frontend/src/pages/deals/DealsPage.tsx:338` | 9 | なし | なし | なし | なし（ボタン） | badge ステータス |
| `staff/StaffPage.tsx` | `frontend/src/pages/staff/StaffPage.tsx:292` | 6 | なし | なし | なし | なし（ボタン） | |
| `teams/TeamsPage.tsx` (2件) | `frontend/src/pages/teams/TeamsPage.tsx:200` | 3+3 | なし | なし | なし | なし（ボタン） | チーム一覧 + メンバー管理テーブル |
| `bots/BotsPage.tsx` | `frontend/src/pages/bots/BotsPage.tsx:247` | 8 | なし | なし | なし | なし（ボタン） | |
| `suppliers/SuppliersPage.tsx` | `frontend/src/pages/suppliers/SuppliersPage.tsx:101` | 6 | なし | なし | なし | ✅（modal） | 行 onClick → 編集モーダル |
| `purchase-orders/PurchaseOrdersPage.tsx` | `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:203` | 7 | なし | なし | なし | なし | |
| `sales/SalesPage.tsx` | `frontend/src/pages/sales/SalesPage.tsx:110` | 8 | なし | なし | なし | なし | |
| `commissions/CommissionsPage.tsx` (3件) | `frontend/src/pages/commissions/CommissionsPage.tsx:172` | 各4-7 | なし | なし | なし | なし | 3集計テーブル（スタッフ別/ロール別/受注別） |
| `inventory/OwnInventoryPage.tsx` | `frontend/src/pages/inventory/OwnInventoryPage.tsx:120` | 9 | なし | なし | なし | なし | A在庫（自社） |
| `shifts/ShiftsPage.tsx` | `frontend/src/pages/shifts/ShiftsPage.tsx:74` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|
| `notifications/NotificationsPage.tsx` | `frontend/src/pages/notifications/NotificationsPage.tsx:70` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|
| `archives/ArchivesPage.tsx` | `frontend/src/pages/archives/ArchivesPage.tsx:33` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|
| `erp/ERPPage.tsx` | `frontend/src/pages/erp/ERPPage.tsx:58` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|

### 3-B. 例外・複雑ページ（別枠）

| ページ | file:line | 理由 |
|--------|-----------|------|
| `inventory/InventoryPage.tsx` | `frontend/src/pages/inventory/InventoryPage.tsx:617` | 列非表示・独自選択・ページネ・ソート複合→置換困難 |
| `products/ProductsPage.tsx` | `frontend/src/pages/products/ProductsPage.tsx:281` | 2段ヘッダー・行ドラッグ並び替え・独自選択→DataTable 改修必要 |

### 3-C. フォーム内明細テーブル（置換対象外）

| ファイル | file:line | 理由 |
|---------|-----------|------|
| `invoice-create/InvoiceCreatePage.tsx` | `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:279` | 入力行を動的追加するフォーム明細—テーブルではなくフォームコンポーネント |
| `invoice-detail/InvoiceDetailPage.tsx` | `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:218` | 詳細表示の読み取り専用明細 |
| `quote-create/QuoteCreatePage.tsx` | `frontend/src/pages/quote-create/QuoteCreatePage.tsx:198` | 入力行動的追加フォーム明細 |
| `quote-detail/QuoteDetailPage.tsx` | `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:172` | 詳細表示の読み取り専用明細 |
| `purchase-orders/PurchaseOrdersFormModal.tsx` | `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:146` | モーダル内フォーム明細 |

### 3-D. 管理ページ（/admin 配下タブ・スーパー管理者のみ）

| ファイル | file:line |
|---------|-----------|
| `admin/InventoryVisibilityPage.tsx` | `frontend/src/pages/admin/InventoryVisibilityPage.tsx:132` |
| `super-admin/DiscordInboundPage.tsx` | `frontend/src/pages/super-admin/DiscordInboundPage.tsx:282` |
| `super-admin/InventoryOffersPage.tsx` | `frontend/src/pages/super-admin/InventoryOffersPage.tsx:376` |
| `super-admin/ParseReviewPage.tsx` | `frontend/src/pages/super-admin/ParseReviewPage.tsx:506` |
| `super-admin/KnowledgeAliasesTab.tsx` | `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:352` |
| `super-admin/LLMBudgetTab.tsx` | `frontend/src/pages/super-admin/LLMBudgetTab.tsx:121` |
| `super-admin/ProductMastersTab.tsx` | `frontend/src/pages/super-admin/ProductMastersTab.tsx:261` |
| `super-admin/SuppliersAdminTab.tsx` | `frontend/src/pages/super-admin/SuppliersAdminTab.tsx:241` |
| `super-admin/TcgSeriesTab.tsx` | `frontend/src/pages/super-admin/TcgSeriesTab.tsx:331` |
| `super-admin/DexTab.tsx` | `frontend/src/pages/super-admin/DexTab.tsx:343` |
| `commission-settings/CommissionSettingsPage.tsx` | `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:189` |
| `company-detail/CompanyAddressesTab.tsx` | `frontend/src/pages/company-detail/CompanyAddressesTab.tsx:30` |
| `company-detail/CompanyContactsTab.tsx` | `frontend/src/pages/company-detail/CompanyContactsTab.tsx:53` |

### 件数サマリ

| カテゴリ | テーブル件数 |
|---------|:----------:|
| メインアプリ実ページ（置換候補） | **27件** (19ページ) |
| 例外（DataTable 改修要） | **2件** (2ページ) |
| フォーム内明細（置換対象外） | **5件** |
| 管理・タブ配下（後回し） | **13件** |
| **合計** | **47件** |

---

## 4. パイロット推奨

### 推奨: `invoices/InvoicesPage.tsx`（`frontend/src/pages/invoices/InvoicesPage.tsx:90`）

**理由:**

1. **最小の機能集合** — ソートなし・選択なし・ページネなし・行clickなし。DataTable 置換の最小パターンを確立できる
2. **9列・renderCell 活用** — 通貨フォーマット（`fmt()`）を `renderCell` に移設するパターンを示す
3. **1テーブル 1ページ** — ファイルがシンプルで副作用がない（`QuoteCreatePage` などのように複数テーブルを持たない）
4. **日常業務の中心** — 見積と対になる中核ページ。標準化の効果が高い
5. **DataTable の機能ギャップなし** — `onRowClick` 未対応でも「詳細」ボタンが最終列にあるため renderCell で問題なく実装できる

**置換作業量見積もり**: 小（列定義追加 + テーブル部分置換のみ、状態管理・API 変更なし）

**次点: `quotes/QuotesPage.tsx`**（クライアントソートを `onSort` に統合するパターンも示したい場合）  
→ `sortTh()` ヘルパーと useMemo ソートを DataTable の `sortKey/sortDir/onSort` props に置き換えるだけ。ただし既に `sortTh()` 実装が安定しているため「置換の恩恵が薄い」という見方もある。

---

## 5. 例外候補（標準化対象外 / 後回し）

### 5-A. 確定例外（DataTable 本体改修なしでは置換不可）

| ページ | 理由 |
|--------|------|
| `frontend/src/pages/inventory/InventoryPage.tsx:617` | 列非表示トグル（hiddenColumns）/ ページネーション / 独自チェックボックス複合。DataTable に「列非表示」機能が未実装 |
| `frontend/src/pages/products/ProductsPage.tsx:281` | 2段ヘッダー（rowSpan/colSpan 必須）/ 行ドラッグ並び替え（drag events）。DataTable では構造的に実装不可 |

### 5-B. 慎重扱い（機能追加が必要なもの）

| ページ | 追加必要な DataTable 機能 |
|--------|--------------------------|
| `frontend/src/pages/leads/LeadsPage.tsx:362` | 行クリック（`onRowClick`）— DataTable に未実装。renderCell のボタンで代替も可だが UX 変化あり |
| `frontend/src/pages/suppliers/SuppliersPage.tsx:101` | 行クリック（`onRowClick`）— 同上 |
| `frontend/src/pages/contacts/ContactsPage.tsx:325` | 行クリック（`onRowClick`）— 同上 |
| `commissions/CommissionsPage.tsx:172,193,224` | 3テーブルが集計ロジックと一体化。置換よりも集計ロジックの整理が先決 |

### 5-C. フォーム内明細テーブル

`InvoiceCreatePage`, `QuoteCreatePage`, `PurchaseOrdersFormModal` の明細テーブルは「入力行追加/削除」機能を持つフォームコンポーネント。DataTable（表示専用）の置換対象ではない。

---

## 6. 不明点

| 項目 | 状況 |
|------|------|
| `frontend/src/pages/shifts/ShiftsPage.tsx:74` の列数・機能 | ファイル未精読（単純テーブルと推定するが未確認） |
| `frontend/src/pages/notifications/NotificationsPage.tsx:70` の列数・機能 | 同上 |
| `frontend/src/pages/archives/ArchivesPage.tsx:33` の列数・機能 | 同上 |
| `frontend/src/pages/erp/ERPPage.tsx:58` の列数・機能 | 同上 |
| DataTable に `onRowClick` を追加するか / renderCell ボタンで代替するか | PO 判断待ち（UX トレードオフあり） |

---

## 7. recon サマリ

- **全 raw table 件数: 47件**（置換候補メインアプリ27件 + 例外2件 + フォーム5件 + 管理タブ13件）
- **DataTable 実採用: 0件**（design-preview のデモのみ）
- **パイロット推奨: `InvoicesPage.tsx`**（最小・副作用なし・renderCell パターン確立）
- **確定例外: `InventoryPage` / `ProductsPage`**（DataTable 改修なしでは不可）
- **要注意: `onRowClick` ギャップ**（LeadsPage/SuppliersPage/ContactsPage に影響）
