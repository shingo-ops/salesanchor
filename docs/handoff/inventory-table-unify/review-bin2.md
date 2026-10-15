# 便2 在庫表の載せ替え コード審査（Opus・2026-10-15）

対象: release/inventory-table-bin2 6ef1e543b（実装は Sonnet。設計 design.md「便2 在庫表の載せ替え」2-1〜2-4、審査 N-r3-1・3・4・5・6）

判定: **APPROVE**

## 照合した点（実物）
- 2-1 列: frontend/src/features/inventory/inventoryColumns.tsx の列は mark → name → condition → unit → offer_type → quantity → unit_price → supplier → note → ship → release_date で表どおり。sortable（note・ship 以外）・align right（quantity・unit_price）・stickyLeft（name）・mobileOrder 1〜7・mobileHidden（mark・unit・offer_type・release_date）が一致。category 列なし。セルの中身は元の td（origin/main の InventoryPage.tsx:689-732）と同じで、インライン style を inventoryColumns.css のクラス（var() のみ）に移した。状態だけ Badge（conditionBadgeVariant）。
- N-r3-1: 行の型 InventoryRow を export。
- DataTable の props: InventoryPage.tsx:582-605 が 2-1 の箇条（rowKey・rowTestId・selectable・sort・page・pageInfo・paginationTestIds・paginationDisabled={loading}・stickyHeader・fitToWidth・mobileCards・emptyState）と一致。旧選択欄の testid（inventory-row-…-select）の参照は frontend/src・tests-e2e に 0 件。
- 2-2: SelectControl（testid inventory-sort-menu）が 24時間ボタンの後・詳細フィルタボタンの前。3択・一致しなければ placeholder。resetAll は release_date / desc（InventoryPage.tsx:339-346）。
- 2-3: inventory.sortMenu の4キーを ja / en に同一キーで追加。
- 追加差分に style= / 色の直値 / 生 table・select・input は 0 件（grep）。InventoryPage.tsx は 608 行（上限 800）。

## 検査（Sonnet 実行・生出力 /tmp/CC報告ファイル/inventory_bin2/）
- preflight 0 / lint 0 / tsc 0 / check:all 0。
- vitest 全件: マシンの負荷が高い状態（load average 30 超）で 5 件失敗（在庫表 4 ファイルは「行が 1 秒以内に出ない」待ち時間切れ）。在庫表関係 8 ファイル 36 件は単独実行で全件成功。最終確認は CI。
- e2e（inventory-table-layout.spec.ts、workers=1）: 3 件成功。375px: .mobile-content scrollWidth 375 = clientWidth 375、カードの右端最大 351。900px: --comp-table-fit-zoom 0.875、スクロール箱の高さ 512 = 800 − 18rem(288)（設計 1-3 の【未確認】は「zoom 内側の max-height は見た目で z 倍にならない」で解消）。1440px: zoom 未設定。その後 mock の ship_timing を実在キーに直した版の再実行は CI で確認する。

## 残す点
- 文字が 1 段小さくなる（font-md → font-sm）・折り返し（N-r3-6）は PO 目視（KGI 5）。
