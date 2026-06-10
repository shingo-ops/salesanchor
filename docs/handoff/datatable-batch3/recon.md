# DataTable 標準化 バッチ3 — Recon

## 対象ファイル（変更前の raw table 位置）

| ファイル | raw table 行 | 列数 | 特記 |
|---------|------------|------|------|
| `frontend/src/pages/deals/DealsPage.tsx:338` | line 338 | 8列 | badge(getStatusPresentation) / fmt() / companyName() |
| `frontend/src/pages/companies/CompaniesPage.tsx:398` | line 398 | 6列 | Link列(name/viewDetail) / status-badge status-{status} / row-pending-dedup |
| `frontend/src/pages/contacts/ContactsPage.tsx:325` | line 325 | 9列 | STATUS_ICONS.check / ContactChannelLinks / row-pending-dedup |
| `frontend/src/pages/teams/TeamsPage.tsx:200` (members) | line 200 | 4列 | Modal 内メンバー管理テーブル |
| `frontend/src/pages/teams/TeamsPage.tsx:225` (teams) | line 225 | 5列 | メインチーム一覧テーブル |

## 追加変更

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/components/DataTable.tsx:84` | `rowClassName?: (row: T) => string` prop を追加 |
| `frontend/src/components.css:424` | `.comp-table__row.row-pending-dedup:hover .comp-table__td` セレクタを追加（既存 `.data-table tr.row-pending-dedup:hover td` と並列） |

## DataTable コンポーネント参照

- `frontend/src/components/DataTable.tsx` — rowClassName prop 追加版
- `DataTableColumn<T>` 型: key, header, renderCell?, width?, sortable?

## パターン参照

- `docs/handoff/datatable-standardization/recon.md` — 全ページ recon（バッチ2まで適用済み）
- `docs/handoff/datatable-batch2/design.md` — バッチ2（ADR-067）の設計パターン

## 各ファイルの特記事項

### DealsPage.tsx
- `fmt()` / `companyName()` は component body 内の関数 → renderCell クロージャで参照
- `getStatusPresentation("deal", d.status).badgeVariant` で badge クラス決定

### CompaniesPage.tsx
- `Link` コンポーネントで name 列と viewDetail ボタンを実装
- `status-badge status-{status}` は独自クラス（badge badge-{variant} とは別系統）— そのまま保持
- `row-pending-dedup` クラスを `rowClassName` prop で指定（DataTable の新 prop）

### ContactsPage.tsx
- `STATUS_ICONS.check` / `ICON.sm` を isPrimary 列で使用
- `ContactChannelLinks` コンポーネントを channels 列の renderCell 内で使用
- `row-pending-dedup` を rowClassName で指定
- `pendingDedupCount` / `setDedupConfirmTarget` などの状態・ハンドラは変更対象外

### TeamsPage.tsx
- 2テーブル: members（Modal 内）+ teams（メインリスト）
- Modal 内テーブルも IIFE パターンで定義
- `removeMember` / `openMembers` は component スコープ関数
