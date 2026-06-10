# DataTable 標準化 バッチ1 — 設計

## ADR 参照

- **ADR-122**: DataTable 標準化（Phase E）— `docs/adr/ADR-122-datatable-standardization.md`
- **ADR-067**: デザイントークン強制 — `docs/adr/ADR-067-design-tokens.md`

## Recon 参照

`docs/handoff/datatable-batch1/recon.md`

## 設計方針

### 置換パターン

```
raw <table className="data-table"> → <DataTable columns={columns} data={...} rowKey={(r) => String(r.id)} emptyState={...} />
```

- columns 定義は component 関数内（closures over props/state が必要なため）
- loading 分岐内 (`loading ? ... : (...)`) で IIFE `(() => { const columns = ...; return <DataTable .../>; })()` パターンを採用

### emptyState

各ファイルの既存 `<td colSpan={N} className="empty">` を `emptyState` prop へ移行。
DataTable が内部で `colSpan={columns.length}` を自動計算するため colSpan は不要。

### data-testid 保持

OrdersTable の `data-testid` 属性（8種）はすべて renderCell 内の要素に移動して保持。

| 基準 | 検証方法 |
|------|---------|
| raw `<table>` が残存しない | `grep -r "data-table" src/pages/` で 0件 |
| TypeScript エラーがない | `tsc --noEmit` — 既存エラーなし（worktree は node_modules 非共有のため main repo で確認） |
| lint エラーがない | `eslint` — 0 errors |
| data-testid 保持 | grep で全 testid が存在 |

## 外部事例

- InvoicesPage（PR #1841）: パイロット実装。columns を component body 内で定義し、`DataTable` へ渡すパターンを確立。本バッチはこのパターンをそのまま踏襲。

## 弊害・リスク

- IIFE パターンは readable だが、loading/error 分岐がさらに増える場合は専用サブコンポーネントへの切り出しを検討する（YAGNI: 現時点では不要）
- API 呼び出し・状態管理は一切変更なし → 動作影響なし

## 変更サマリ

| ファイル | 変更内容 |
|---------|---------|
| `orders/OrdersTable.tsx` | 9列 DataTable へ置換（phase/status badge, NavLink, fmtCurrency, conditional actions） |
| `staff/StaffPage.tsx` | 5列 DataTable へ置換（status badge, permission-gated buttons） |
| `bots/BotsPage.tsx` | 7列 DataTable へ置換（status badge, permission-gated buttons, rotateKey） |
| `shifts/ShiftsPage.tsx` | 6列 DataTable へ置換（shift_type badge） |
| `archives/ArchivesPage.tsx` | 5列 DataTable へ置換（conditional restore） |
