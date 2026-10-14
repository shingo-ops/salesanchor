# recon: 在庫表を開いた直後の同内容 PATCH

実測時 origin/main: 39296644072884e91ff1b59f0ea0891c532cdc41

## ADR 検索
- git grep -il "inventory-filters" docs/adr → docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md（結果は /tmp/adr.txt 相当。関連言及のみ）
- docs/adr/FEATURE-INDEX.md も該当語を含む

## 現在地（変更前、origin/main の実物）
- frontend/src/pages/inventory/InventoryPage.tsx:131 filtersLoaded 初期 false
- frontend/src/pages/inventory/InventoryPage.tsx:236-271 GET /me/inventory-filters → then で state set → finally で setFiltersLoaded(true)
- frontend/src/pages/inventory/InventoryPage.tsx:273-296 保存 effect。filtersLoaded が依存に含まれ、読込完了直後に同じ値で PATCH が1回出る
- frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx:1 既存テストの流儀（api を vi.mock）
