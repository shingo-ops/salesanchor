# 設計: DataTable 標準化パイロット — InvoicesPage

> **作成日**: 2026-06-09  
> **ステータス**: Accepted  
> **参照**: recon = `docs/handoff/datatable-standardization/recon.md` / ADR-122

---

## KGI

| | before | after |
|--|--------|-------|
| InvoicesPage の raw `<table>` | **1件** | **0件** |
| 標準 `DataTable` 採用（実ページ） | 0件 | 1件 |
| 通貨 `renderCell` テンプレ確立 | なし | あり（再利用可能パターン） |

---

## 技術 How

### 置換方針

`frontend/src/pages/invoices/InvoicesPage.tsx:90` の生テーブルを `DataTable<Invoice>` に置換する。

```
<table className="data-table">          →  <DataTable<Invoice>
  <thead><tr><th>...</th>...</tr></thead>     columns={columns}
  <tbody>{invoices.map(...)}</tbody>          data={invoices}
</table>                                      rowKey={(inv) => String(inv.id)}
                                              emptyState={...}
                                           />
```

### columns 定義（9列）

| key | header i18n | renderCell |
|-----|-------------|-----------|
| `invoice_number` | `invoices.invoiceCode` | `<span className="mono">` でモノスペース維持 |
| `currency` | `common.currency` | 文字列そのまま（renderCell 不要） |
| `total_amount` | `common.amount` | `fmt(inv.total_amount, inv.currency)` |
| `amount_jpy` | `invoices.jpyEquiv` | `¥${inv.amount_jpy.toLocaleString()}` |
| `status` | `common.status` | `<span className="badge badge-{variant}">` |
| `issued_at` | `invoices.issuedAt` | `new Date(...).toLocaleDateString()` |
| `due_date` | `invoices.dueDate` | 文字列そのまま（or `-`） |
| `paid_at` | `invoices.paidAt` | `new Date(...).toLocaleDateString()` |
| `actions` | `common.actions` | `<button className="btn-sm">` |

### DataTable 機能ギャップ（本パイロットでは問題なし）

`docs/handoff/datatable-standardization/recon.md` 参照。`InvoicesPage` はソート/選択/ページネ/行クリックを一切使用しないため、DataTable の現状機能で完全に対応できる。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| InvoicesPage に `<table` が残っていない | `grep "<table" InvoicesPage.tsx` → 0件 |
| `<DataTable` が1件ある | `grep "<DataTable" InvoicesPage.tsx` → 1件 |
| 9列が維持されている | columns 配列の length === 9 |
| 通貨整形が現状と同じ | Evaluator ビジュアル確認（`¥1,000` / `$1,000.00` 等） |
| ステータス badge が現状と同じ | Evaluator ビジュアル確認（badge 色・ラベル一致） |
| 「詳細」ボタンで `/invoices/:id` 遷移 | Evaluator 動作確認 |
| 0件時に noInvoices メッセージ表示 | Evaluator 確認（emptyState prop） |
| API・状態管理変更なし | `git diff` で API 呼び出しに変更なし |
| `git revert HEAD` で元に戻る | `git revert HEAD` 実行後に build が通る |

---

## 外部・過去事例の参照と我々への応用

shadcn/ui・Mantine・Ant Design Table など主要 UI ライブラリはすべて「列定義（columns）+ データ（data）+ rowKey」の分離パターンを採用している。raw `<table>` から columns 定義モデルへの段階移行は React エコシステムで確立されたパターン。通貨フォーマット等のカスタムセルは `renderCell`（shadcn でいう `cell: (row) => <>`）パターンで対応する。

InvoicesPage のような「特殊機能なし・シンプル 9 列」ページをパイロットとして先行置換し、置換テンプレ（特に `renderCell` の通貨整形）を確立してから残 26 件の実ページへ展開するのは「仕様を固めてからスケール」の原則に合致する。
