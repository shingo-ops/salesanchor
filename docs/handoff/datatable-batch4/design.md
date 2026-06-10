# DataTable 標準化 バッチ4 設計書

> **参照: recon = docs/handoff/datatable-batch4/recon.md / docs/handoff/datatable-standardization/recon.md / ADR-067**
> **作成日**: 2026-06-10
> **担当**: Hikky-dev

---

## KGI・KPI

| 基準 | 検証方法 |
|------|---------|
| 対象5テーブルの `<table className="data-table">` が0件になること | `grep -r 'class.*data-table' frontend/src/pages/{quotes,commissions,leads}/` で0件確認 |
| TypeScript エラー 0件 | `./node_modules/.bin/tsc --noEmit` でエラーなし |
| `commissions-assign-{id}` data-testid が保持されること | grep 確認 |
| `commissions-by-staff` / `commissions-by-role` / `commissions-manage-orders` data-testid が wrapper div で保持されること | grep 確認 |
| QuotesPage のソートが DataTable sortKey/sortDir/onSort で動作すること | Evaluator 視覚確認 |

---

## 設計方針

バッチ1〜3と同一パターンを踏襲。追加で QuotesPage のクライアントソートを DataTable のソート props に移行する。

1. `<table className="data-table">` を `<DataTable<T>>` に置換
2. `DataTableColumn<T>[]` を component body 内 IIFE で定義
3. `emptyState` prop に既存 i18n キーを流用
4. API 呼び出し・状態管理は一切変更しない

**QuotesPage ソート移行**:
- 既存 `sortTh()` ヘルパーを削除（DataTable 内蔵ソートボタンに置換）
- `handleSort(field, dir)` を DataTable の `onSort` に渡す
- `sortField`/`sortDir` state・`sortedQuotes` useMemo は変更なし
- `SortDir` 型を DataTable からインポート

**CommissionsPage data-testid 保持**:
- 元テーブル要素の `data-testid` → DataTable を包む `<div data-testid="...">` に移動

**LeadsPage 条件付き列**:
- priority_score 列: バッチ2（SalesPage）の `canEdit` スプレッドパターンと同様
  ```ts
  const columns = [...baseColumns, ...(canEdit ? [col] : []), ...trailingColumns];
  ```

---

## 外部・過去事例の参照と我々への応用

参照: `docs/handoff/datatable-batch4/recon.md`（バッチ4対象ページのファイル:行番号・特記事項）および `docs/handoff/datatable-standardization/recon.md`（全体 recon）。

バッチ1〜3で確立した「IIFE 内で columns 定義」パターンをバッチ4でも踏襲。QuotesPage のクライアントソートを DataTable の制御型ソート（`sortKey`/`sortDir`/`onSort`）に移行することで、ソート状態管理が既存の React state と一体化した controlled component パターンになる。shadcn/ui Table・Ant Design Table など主要ライブラリが採用する controlled sort の標準的なアプローチと同一。CommissionsPage の 3 テーブルは IIFE を 3 回適用する構成で、各テーブルが独立した型定義を持つ。

---

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| QuotesPage の `data-testid="quotes-sort-*"` が消失 | E2E テストで未使用（grep 確認済み）→ 影響なし |
| CommissionsPage の `data-testid` が `<table>` から `<div>` に移動 | E2E テストで未使用（grep 確認済み）。Playwright `getByTestId` はタグ問わず動作 |
| LeadsPage priority 列の条件分岐で列数が変動 | DataTable の `colSpan` は columns 配列長を参照するため自動調整される |
