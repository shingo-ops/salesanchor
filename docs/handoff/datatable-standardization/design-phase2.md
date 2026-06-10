# 設計: DataTable 標準化 フェーズ2 — 管理系テーブルロールアウト

**対象ADR**: ADR-067  
**recon**: docs/handoff/datatable-standardization/recon-phase2.md  
**作成日**: 2026-06-11  
**ステータス**: In Progress

---

## 外部・過去事例の参照と我々への応用

- 事例1: Shopify Polaris DataTable（[polaris.shopify.com](https://polaris.shopify.com/components/tables/data-table)）— `rowStatus` prop でハイライト色を返す設計。我々の `rowClassName` は同パターンを採用。CSS クラス返しにすることでデザイントークン変更に強くなる。
- 事例2: フェーズ1（顧客向けページ 9件）— raw `<table>` → `<DataTable>` 変換実績あり。同じ `renderCell` テンプレートを管理系にも適用できることをパイロットで実証。
- 事例3: Tanstack Table v8（OSS）— 複合機能（drag, hidden columns, dynamic columns）は独自 prop 追加より専用ライブラリが適切という知見 → 今回の例外 4件の理由と合致。

---

## KGI

| | before | after |
|--|--------|-------|
| 管理系 raw `<table>` 残存数 | **14件** | **0件** |
| 例外（現状維持）記録済み | 0件 | **4件** |
| DataTable `rowClassName` ハイライト実証 | なし | あり（SupplierParseStatsTab） |

---

## 確定例外 4件（PO承認済み）

| ページ | 理由 |
|--------|------|
| **InventoryPage** | `hiddenColumns` による列表示切替 + 見積往復モード複合ロジック。DataTable 非対応機能（hiddenColumnKeys）の追加が必要で工数大 |
| **ProductMastersTab** | drag-and-drop 行並び替えが必須機能。DataTable に `draggable` 対応なし |
| **ParseReviewPage** | 各行に picker/メモのサブ行（Fragment + colSpan）。DataTable の行モデルと非互換 |
| **InventoryVisibilityPage** | 列数が API レスポンス依存で動的。セル内チェックボックスは「権限のON/OFF操作」であり DataTable の selectable（行選択）と意味が異なる |

---

## バッチ構成

### Pilot: SupplierParseStatsTab
- 7列、特殊機能なし、`rowClassName` で danger/warning ハイライト
- DataTable.css に `.comp-table__row--danger` / `.comp-table__row--warning` 追加
- テンプレート実証後、残り13件を展開

### Batch 1（シンプル・表示系）
- `StaffReportsPage.tsx` — 5列、表示のみ
- `BadgesPage.tsx` — 4列、リーダーボード
- `BuddyPage.tsx` — 5列+4列 2テーブル
- `CompanyAddressesTab.tsx` — 7列×2テーブル（同構造）
- `CompanyContactsTab.tsx` — 6〜7列、canEdit 動的アクション列

### Batch 2（アクション系）
- `TcgSeriesTab.tsx` — 8列、テーブル外インラインフォーム
- `LLMBudgetTab.tsx` — 9列、外部インラインフォーム連携
- `CommissionSettingsPage.tsx` — 4列、form 内テーブル

### Batch 3（複合機能系）
- `KnowledgeAliasesTab.tsx` — 2テーブル（8列+5列）、一括削除チェックBox
- `SuppliersAdminTab.tsx` — 7列、チェックBox＋ページネーション
- `InventoryOffersPage.tsx` — 10列、チェックBox＋ページネーション＋行クリック
- `DiscordInboundPage.tsx` — 6列＋モーダル内テーブル
- `DexTab.tsx` — 5〜6列（kind依存）、2-up 並列表示

---

## 技術パターン（Phase 1 からの継承）

```tsx
// 列定義テンプレート
const columns: DataTableColumn<T>[] = [
  { key: "code",   header: t("…"), renderCell: (r) => <span className="mono">{r.code}</span> },
  { key: "amount", header: t("…"), renderCell: (r) => <span style={{ display:"block", textAlign:"right" }}>{fmt(r.amount)}</span> },
  { key: "status", header: t("…"), renderCell: (r) => <span className={`badge badge-${variant}`}>{label}</span> },
  { key: "actions",header: t("…"), renderCell: (r) => <button className="btn-sm" onClick={…}>{t("…")}</button> },
];
```

---

## 受け入れ基準（パイロット）

| 基準 | 検証方法 |
|------|---------|
| `<table` が 0件 | `grep "<table" SupplierParseStatsTab.tsx` → 0件 |
| `<DataTable` が 1件 | `grep "<DataTable" SupplierParseStatsTab.tsx` → 1件 |
| danger/warning ハイライト行が正しく表示 | Evaluator ビジュアル確認 |
| 数値列が右寄せ | Evaluator ビジュアル確認 |
| 仕入元セレクトで絞込が動作 | Evaluator 動作確認 |
| `git revert HEAD` で元に戻る | revert 後に build 通過 |
