# DataTable Step 2 Recon — onRowClick + controlled pagination

> **作成日**: 2026-06-09  
> **担当**: architect（読み取り専用。アプリコード変更0件）  
> **背景**: DataTable パイロット（#1841 InvoicesPage）完了後、実ページへの展開に向けて  
>           行クリック・ページネーションが必要なページを特定する。

---

## 1. onRowClick が必要なページ（grep 調査）

`grep -rn "tr onClick\|<tr.*onClick" frontend/src/pages` で調査した結果:

| ページ | file:line | 現状 |
|--------|-----------|------|
| SuppliersPage | `frontend/src/pages/suppliers/SuppliersPage.tsx:115` | `<tr onClick>` → 編集モーダル開閉 |

**メインアプリで `<tr onClick>` を使っているページは SuppliersPage のみ**。  
LeadsPage・ContactsPage は「編集」ボタン列（renderCell）で対応済み。

---

## 2. ページネーションが必要なページ（サーバー側制御）

| ページ | file:line | 型 |
|--------|-----------|---|
| SuppliersPage | `frontend/src/pages/suppliers/SuppliersPage.tsx:87` | サーバーサイド controlled（page/hasNextPage） |

クライアントサイドページネーションを持つページは現状なし（全件取得 → 表示）。

---

## 3. ギャップ分析

| 機能 | DataTable 現状 | 必要ページ数 |
|------|--------------|:----------:|
| `onRowClick` | **未実装** | 1（SuppliersPage のみ） |
| controlled pagination | **未実装** | 1（SuppliersPage のみ） |

---

## 4. 結論

両機能とも影響ページは **SuppliersPage の 1 件のみ**。  
- `onRowClick`: optional prop で後方互換性を維持して追加  
- ページネーション: `page/hasNextPage/onPageChange` controlled モデル（サーバーサイド対応）  
- 二重発火防止: `isInteractiveTarget()` ガード（`button, a, input, select, textarea, label`）  
- キーボードアクセシビリティ: `tabIndex={0}`, Enter/Space で `onRowClick` 発火
