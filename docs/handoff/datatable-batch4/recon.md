# DataTable 標準化 バッチ4 — Recon

## 対象ファイル（変更前の raw table 位置）

| ファイル | raw table 行 | 列数 | 特記 |
|---------|------------|------|------|
| `frontend/src/pages/quotes/QuotesPage.tsx:161` | line 161 | 9列 | クライアントソート(useMemo) / sortable columns |
| `frontend/src/pages/commissions/CommissionsPage.tsx:172` | line 172 | 2列 | by_staff 集計テーブル・data-testid="commissions-by-staff" |
| `frontend/src/pages/commissions/CommissionsPage.tsx:193` | line 193 | 2列 | by_role 集計テーブル・data-testid="commissions-by-role" |
| `frontend/src/pages/commissions/CommissionsPage.tsx:224` | line 224 | 3列 | 受注管理テーブル・data-testid="commissions-manage-orders" / commissions-assign-{id} |
| `frontend/src/pages/leads/LeadsPage.tsx:362` | line 362 | 8列+1条件 | priority_score 列（hasPermission("analytics.customer_priority.view") 条件付き） |

## 特記事項

### QuotesPage
- 既存 `sortTh()` ヘルパー関数と `onSort()` を DataTable の `sortKey`/`sortDir`/`onSort` props で置換
- `data-testid="quotes-sort-*"` は E2E テストで未使用（grep 確認済み）→ 省略
- `sortField`/`sortDir` state および `sortedQuotes` useMemo は変更なし（DataTable に渡すだけ）

### CommissionsPage
- 3テーブル: by_staff（2列）/ by_role（2列）/ manage-orders（3列）
- `data-testid` は元テーブル要素に付いていたが、DataTable はラッパー `<div>` で包む → `<div data-testid="...">` で保持
- `commissions-assign-${o.order_id}` testid はボタンに付与（保持）

### LeadsPage
- priority_score 列: `hasPermission("analytics.customer_priority.view")` による条件付きスプレッド
- `discord_user_id` 有無で Discord badge を条件表示
- `MergeLeadModal` など周辺コンポーネントは変更なし

## DataTable コンポーネント参照

- `frontend/src/components/DataTable.tsx` — rowClassName 追加版（バッチ3で拡張済み）
- `SortDir` 型を `import type { DataTableColumn, SortDir }` でインポート

## パターン参照

- `docs/handoff/datatable-standardization/recon.md` — 全ページ recon
- `docs/handoff/datatable-batch3/design.md` — rowClassName / IIFE パターン
