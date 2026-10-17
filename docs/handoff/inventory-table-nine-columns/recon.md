# recon — 在庫表を9列にして折り返しをなくす

**仕事名**: inventory-table-nine-columns  
**日付**: 2026-10-17  
**対象ADR**: ADR-144、ADR-093、ADR-1014、ADR-027  
**担当**: architect（Opus、調査は Sonnet に委任。基準 origin/main db2302943 以前の fetch 済み main）

---

## PO の依頼（原文）

- 「在庫表だけど形態は表示しなくて良いチェックボックスも左端についているがこれも不要」
- 「型番、タイトル、状態、単価、数量、備考、発送、仕入元、発売日だけ表示」
- 「列が多くて行に収まらず折れてしまうのだが対策案はある？商品名が長いと折れてしまう」
- 「下に英語名も表示させるから折り返しはまずしたくない」
- 案（9列を言われた順・形態/在庫・予約/チェック欄を外す・どの列も折り返さず表全体を縮めて収める）に「y、テストとしてどんな画面になるか見せてほしい」（2026-10-17）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/features/inventory/inventoryColumns.tsx:48` | 列定義の配列 `all` の開始。現在の順は 型番→タイトル→状態→形態→在庫・予約→数量→単価→仕入元→備考→発送→発売日 |
| `frontend/src/features/inventory/inventoryColumns.tsx:86` | 形態列（key `unit`、i18n `inventory.col.unit`） |
| `frontend/src/features/inventory/inventoryColumns.css:1` | `.inventory-cell__title` が `overflow-wrap: anywhere`（商品名がどこでも折り返す） |
| `frontend/src/features/inventory/inventoryColumns.css:6` | `.inventory-cell__sub`（英語名など副表示）も `overflow-wrap: anywhere` |
| `frontend/src/components/DataTable.css:37` | th は `white-space: nowrap`。td には white-space 指定なし（通常の折り返し） |
| `frontend/src/components/DataTable.css:280` | `zoom: var(--comp-table-fit-zoom,1)`（fitToWidth の縮小） |
| `frontend/src/hooks/useFitTableZoom.ts:40` | 表の自然幅が枠より広いと倍率を下げて収める。下限なし。768px 未満では無効 |
| `frontend/src/constants/tableFit.ts:3` | 縮小計算は GAS 在庫一覧と同じ値 |
| `frontend/src/pages/inventory/InventoryPage.tsx:97` | 列の表示切替対象 HIDEABLE_COLUMNS（unit, offerType を含む） |
| `frontend/src/pages/inventory/InventoryPage.tsx:595` | DataTable に `selectable`（左端チェック欄） |
| `frontend/src/pages/inventory/InventoryPage.tsx:611` | `fitToWidth` 指定済み |
| `frontend/src/pages/inventory/InventoryPage.tsx:612` | `mobileCards`（767px 以下はカード表示） |
| `frontend/src/pages/inventory/InventoryFilterPanel.tsx:222` | 詳細フィルタの形態条件（showUnits）。列とは別機能 |
| `frontend/src/features/inventory/inventoryColumns.test.tsx:20` | 列順を expect（unit を含む） |
| `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx:44` | thead の順を expect（先頭のチェック欄を slice(1) で除外） |
| `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx:122` | F3: 行チェックをクリックしてもドロワーが開かない試験 |
| `frontend/src/pages/viewer/viewerColumns.parity.test.tsx:9` | 閲覧画面との列比較（既に unit を除外） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | チェック欄の選択を使う機能があるか | InventoryPage 内の selectedIds 参照を全件 grep。初期値と DataTable への受け渡しだけで、一括操作・削除・CSV は無い | ✅ 解消済み |
| 2 | 見積からの往復で preselectedInventoryIds を渡す側があるか | origin/main を grep。送り元のコードは無い | ✅ 解消済み |
| 3 | DataTable 本体を変えずに在庫表だけ変えられるか | selectable を使う他ページあり。在庫表は InventoryPage の prop 削除と列定義で完結 | ✅ 解消済み |
| 4 | 形態の表示を義務づける仕様があるか | ADR-093/1014 は形態をデータ（行の識別）に使うと定めるだけで列表示の義務なし。データ・API は変えない | ✅ 解消済み |
| 5 | 列を減らし折り返しを止めた後の縮み具合 | 実装後に同じ試験データで前後の画面を撮って比べる（design.md 受け入れ基準） | 実装後に観測 |

**未解決ゼロ確認**: 実装前に解消すべき不明点は全て解消済み。5 は実装後の観測項目。

---

## 補足

- 生出力: /tmp/CC報告ファイル/inventory-cols-recon/
- 形態の絞り込み（詳細フィルタ）・保存済みの列設定（hidden_columns の unit/offerType）・バックエンドは今回触らない
