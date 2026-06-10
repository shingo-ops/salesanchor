# DataTable 標準化 バッチ1 — 設計

> **作成日**: 2026-06-10
> **ステータス**: Accepted
> **参照**: recon = `docs/handoff/datatable-standardization/recon.md` / ADR-067

---

## KGI

| | before | after |
|--|--------|-------|
| バッチ1対象5ページの raw `<table>` | **5件** | **0件** |
| 標準 `DataTable` 採用（実ページ） | 1件（InvoicesPage） | 6件 |

---

## 技術 How

### 置換パターン

```
raw <table className="data-table"> → <DataTable columns={columns} data={...} rowKey={(r) => String(r.id)} emptyState={...} />
```

- columns 定義は component 関数内（props/state へのクロージャが必要なため）
- loading 分岐内で columns を定義し DataTable を返す

### 対象ファイル（バッチ1）

| ファイル | 列数 | 特記 |
|---------|------|------|
| `orders/OrdersTable.tsx:69` | 9 | shippings/purchases クロージャ・phase badge・NavLink・data-testid |
| `staff/StaffPage.tsx:292` | 5 | status badge・permission-gated buttons・emails +N |
| `bots/BotsPage.tsx:247` | 7 | purposeLabel/statusLabel・permission-gated buttons |
| `shifts/ShiftsPage.tsx:74` | 6 | shift_type badge（badge-negotiating） |
| `archives/ArchivesPage.tsx:33` | 5 | restored_at 条件分岐（restore button or restored badge） |

### data-testid 保持

OrdersTable の data-testid 属性（8種: ship-cell-to-\*, flow-cell-\*, mark-paid-\*, mark-purchased-\*, issue-label-\*, mark-unpaid-\*, open-shipping-\*, open-purchase-\*）はすべて renderCell 内の要素に移動して保持。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 5ページの raw `<table className="data-table">` が残存しない | `grep "data-table" src/pages/{orders,staff,bots,shifts,archives}` → 0件 |
| TypeScript エラーなし | `tsc --noEmit` — 0件 |
| ESLint エラーなし | `npm run lint` — 0 errors |
| data-testid 属性すべて保持 | grep で全 testid 確認 |
| 表示・列・値が現状と parity | Evaluator 視覚差分確認 |
| `git revert HEAD` で元に戻る | revert 後 build が通る |

---

## 外部・過去事例の参照と我々への応用

shadcn/ui・Mantine・Ant Design Table など主要 UI ライブラリはすべて「列定義（columns）+ データ（data）+ rowKey」の分離パターンを採用している。raw `<table>` から columns 定義モデルへの段階移行は React エコシステムで確立されたパターン。

InvoicesPage（PR #1841）をパイロットとして型を確立した。本バッチ（BatchF1）はそのテンプレを OrdersTable/StaffPage/BotsPage/ShiftsPage/ArchivesPage の5ページへ横展開する。renderCell クロージャで props/state を参照するパターン（OrdersTable の shippings/purchases）も、React のコンポーネント設計原則に合致する確立済み手法。
