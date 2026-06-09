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
| `columns` | `DataTableColumn<T>[]` | 列定義（key/header/width/sortable/renderCell） | `DataTable.tsx:26-37` |
| `data` | `T[]` | 表示データ配列 | `DataTable.tsx:43` |
| `rowKey` | `(row: T) => string` | 行識別子ファクトリ（必須） | `DataTable.tsx:46` |
| `sortKey` | `string?` | 現在ソート中の列 key | `DataTable.tsx:48` |
| `sortDir` | `'asc' \| 'desc'` | ソート方向（既定 asc） | `DataTable.tsx:50` |
| `onSort` | `(key, dir) => void` | ソートクリック時コールバック | `DataTable.tsx:52` |
| `selectable` | `boolean` | チェックボックス列表示 | `DataTable.tsx:54` |
| `selectedKeys` | `Set<string>` | 選択済み rowKey 集合 | `DataTable.tsx:56` |
| `onSelectChange` | `(keys) => void` | 選択変更コールバック | `DataTable.tsx:58` |
| `density` | `'compact' \| 'default' \| 'relaxed'` | 行高さバリアント | `DataTable.tsx:60` |
| `emptyState` | `ReactNode` | 0件時表示スロット | `DataTable.tsx:62` |
| `className` | `string` | ラッパー追加クラス | `DataTable.tsx:63` |

### 実装済み機能（file:line）

- **全行選択 / 個別選択**（indeterminate 対応）: `DataTable.tsx:90-108`
- **ソートクリックハンドラ**（asc/desc トグル）: `DataTable.tsx:110-115`
- **カスタムセルレンダラー**（`renderCell` prop）: `DataTable.tsx:213-217`
- **density バリアント**: `DataTable.tsx:117-121`
- **空状態スロット**: `DataTable.tsx:181-189`
- **水平スクロール**（`.comp-table` ラッパー）: `DataTable.tsx:124`

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
| `quotes/QuotesPage.tsx` | `QuotesPage.tsx:161` | 9 | ✅クライアント | なし | なし | なし（ボタン） | useMemo ソート・全8列sortable |
| `invoices/InvoicesPage.tsx` | `InvoicesPage.tsx:90` | 9 | なし | なし | なし | なし（ボタン） | 通貨フォーマット |
| `orders/OrdersTable.tsx` | `OrdersTable.tsx:69` | 9 | なし | なし | なし | なし（ボタン） | OrdersPage 専用コンポーネントに分離済み |
| `leads/LeadsPage.tsx` | `LeadsPage.tsx:362` | 8+1条件 | なし | なし | なし | ✅（編集） | 優先度スコア列（条件表示） |
| `companies/CompaniesPage.tsx` | `CompaniesPage.tsx:398` | 7 | なし | なし | なし | なし（リンク） | `<a>` リンク列あり |
| `contacts/ContactsPage.tsx` | `ContactsPage.tsx:325` | 10 | なし | なし | なし | なし（ボタン） | 電話/メール表示 |
| `deals/DealsPage.tsx` | `DealsPage.tsx:338` | 9 | なし | なし | なし | なし（ボタン） | badge ステータス |
| `staff/StaffPage.tsx` | `StaffPage.tsx:292` | 6 | なし | なし | なし | なし（ボタン） | |
| `teams/TeamsPage.tsx` (2件) | `TeamsPage.tsx:200,225` | 3+3 | なし | なし | なし | なし（ボタン） | チーム一覧 + メンバー管理テーブル |
| `bots/BotsPage.tsx` | `BotsPage.tsx:247` | 8 | なし | なし | なし | なし（ボタン） | |
| `suppliers/SuppliersPage.tsx` | `SuppliersPage.tsx:101` | 6 | なし | なし | なし | ✅（modal） | 行 onClick → 編集モーダル |
| `purchase-orders/PurchaseOrdersPage.tsx` | `PurchaseOrdersPage.tsx:203` | 7 | なし | なし | なし | なし | |
| `sales/SalesPage.tsx` | `SalesPage.tsx:110` | 8 | なし | なし | なし | なし | |
| `commissions/CommissionsPage.tsx` (3件) | `CommissionsPage.tsx:172,193,224` | 各4-7 | なし | なし | なし | なし | 3集計テーブル（スタッフ別/ロール別/受注別） |
| `inventory/OwnInventoryPage.tsx` | `OwnInventoryPage.tsx:120` | 9 | なし | なし | なし | なし | A在庫（自社） |
| `shifts/ShiftsPage.tsx` | `ShiftsPage.tsx:74` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|
| `notifications/NotificationsPage.tsx` | `NotificationsPage.tsx:70` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|
| `archives/ArchivesPage.tsx` | `ArchivesPage.tsx:33` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|
| `erp/ERPPage.tsx` | `ERPPage.tsx:58` | 不明 | なし | なし | なし | 不明 | 精査未完（ファイル未読）|

### 3-B. 例外・複雑ページ（別枠）

| ページ | file:line | 理由 |
|--------|-----------|------|
| `inventory/InventoryPage.tsx` | `InventoryPage.tsx:617` | 列非表示・独自選択・ページネ・ソート複合→置換困難 |
| `products/ProductsPage.tsx` | `ProductsPage.tsx:562` | 2段ヘッダー・行ドラッグ並び替え・独自選択→DataTable 改修必要 |

### 3-C. フォーム内明細テーブル（置換対象外）

| ファイル | file:line | 理由 |
|---------|-----------|------|
| `invoice-create/InvoiceCreatePage.tsx` | `InvoiceCreatePage.tsx:279,344` | 入力行を動的追加するフォーム明細—テーブルではなくフォームコンポーネント |
| `invoice-detail/InvoiceDetailPage.tsx` | `InvoiceDetailPage.tsx:218` | 詳細表示の読み取り専用明細 |
| `quote-create/QuoteCreatePage.tsx` | `QuoteCreatePage.tsx:198` | 入力行動的追加フォーム明細 |
| `quote-detail/QuoteDetailPage.tsx` | `QuoteDetailPage.tsx:172` | 詳細表示の読み取り専用明細 |
| `purchase-orders/PurchaseOrdersFormModal.tsx` | `PurchaseOrdersFormModal.tsx:146` | モーダル内フォーム明細 |

### 3-D. 管理ページ（/admin 配下タブ・スーパー管理者のみ）

| ファイル | file:line |
|---------|-----------|
| `admin/InventoryVisibilityPage.tsx` | `InventoryVisibilityPage.tsx:132` |
| `super-admin/DiscordInboundPage.tsx` | `DiscordInboundPage.tsx:282,391` |
| `super-admin/InventoryOffersPage.tsx` | `InventoryOffersPage.tsx:376` |
| `super-admin/ParseReviewPage.tsx` | `ParseReviewPage.tsx:506` |
| `super-admin/KnowledgeAliasesTab.tsx` | `KnowledgeAliasesTab.tsx:352,430` |
| `super-admin/LLMBudgetTab.tsx` | `LLMBudgetTab.tsx:121` |
| `super-admin/ProductMastersTab.tsx` | `ProductMastersTab.tsx:261` |
| `super-admin/SuppliersAdminTab.tsx` | `SuppliersAdminTab.tsx:241,348` |
| `super-admin/TcgSeriesTab.tsx` | `TcgSeriesTab.tsx:331` |
| `super-admin/DexTab.tsx` | `DexTab.tsx:343` |
| `commission-settings/CommissionSettingsPage.tsx` | `CommissionSettingsPage.tsx:189` |
| `company-detail/CompanyAddressesTab.tsx` | `CompanyAddressesTab.tsx:30` |
| `company-detail/CompanyContactsTab.tsx` | `CompanyContactsTab.tsx:53` |

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

### 推奨: `invoices/InvoicesPage.tsx`（`InvoicesPage.tsx:90`）

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
| `inventory/InventoryPage.tsx:617` | 列非表示トグル（hiddenColumns）/ ページネーション / 独自チェックボックス複合。DataTable に「列非表示」機能が未実装 |
| `products/ProductsPage.tsx:562` | 2段ヘッダー（rowSpan/colSpan 必須）/ 行ドラッグ並び替え（drag events）。DataTable では構造的に実装不可 |

### 5-B. 慎重扱い（機能追加が必要なもの）

| ページ | 追加必要な DataTable 機能 |
|--------|--------------------------|
| `leads/LeadsPage.tsx:362` | 行クリック（`onRowClick`）— DataTable に未実装。renderCell のボタンで代替も可だが UX 変化あり |
| `suppliers/SuppliersPage.tsx:101` | 行クリック（`onRowClick`）— 同上 |
| `contacts/ContactsPage.tsx:325` | 行クリック（`onRowClick`）— 同上 |
| `commissions/CommissionsPage.tsx:172,193,224` | 3テーブルが集計ロジックと一体化。置換よりも集計ロジックの整理が先決 |

### 5-C. フォーム内明細テーブル

`InvoiceCreatePage`, `QuoteCreatePage`, `PurchaseOrdersFormModal` の明細テーブルは「入力行追加/削除」機能を持つフォームコンポーネント。DataTable（表示専用）の置換対象ではない。

---

## 6. 不明点

| 項目 | 状況 |
|------|------|
| `shifts/ShiftsPage.tsx:74` の列数・機能 | ファイル未精読（単純テーブルと推定するが未確認） |
| `notifications/NotificationsPage.tsx:70` の列数・機能 | 同上 |
| `archives/ArchivesPage.tsx:33` の列数・機能 | 同上 |
| `erp/ERPPage.tsx:58` の列数・機能 | 同上 |
| DataTable に `onRowClick` を追加するか / renderCell ボタンで代替するか | PO 判断待ち（UX トレードオフあり） |

---

## 7. recon サマリ

- **全 raw table 件数: 47件**（置換候補メインアプリ27件 + 例外2件 + フォーム5件 + 管理タブ13件）
- **DataTable 実採用: 0件**（design-preview のデモのみ）
- **パイロット推奨: `InvoicesPage.tsx`**（最小・副作用なし・renderCell パターン確立）
- **確定例外: `InventoryPage` / `ProductsPage`**（DataTable 改修なしでは不可）
- **要注意: `onRowClick` ギャップ**（LeadsPage/SuppliersPage/ContactsPage に影響）
