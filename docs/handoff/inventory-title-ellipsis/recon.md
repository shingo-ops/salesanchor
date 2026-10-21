# recon: 在庫表の商品名を「…」で省く

実測時の origin/main: f16d4c400（Merge pull request #4549）。生出力の原本は /tmp/CC報告ファイル/inventory-title-ellipsis/recon/。事実のみ。

## 既存 ADR 検索
- ADR-1014（docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md）: 在庫表の正本 ADR。改訂 2026-10-19（7）が docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:135-144。
- ADR-067（docs/adr/ADR-067-design-token-enforcement.md:66-69）: トークン表。`--col-width-wide` が表では 240px、実物は 360px。

## 現在地
- 商品名セル: frontend/src/features/inventory/inventoryColumns.tsx:100-105、frontend/src/pages/viewer/viewerColumns.tsx:57-62（上段 `inventory-cell__title`、下段 `inventory-cell__sub`）。
- 備考・発送: frontend/src/features/inventory/inventoryColumns.tsx:169・:178、frontend/src/pages/viewer/viewerColumns.tsx:107・:113（`inventory-cell__nowrap`）。
- 折り返し禁止（768px 以上）: frontend/src/features/inventory/inventoryColumns.css:12-20。
- DataTable の `ellipsis` は JSX の中身だと title が付かない: frontend/src/components/DataTable.tsx:446。
- トークン: frontend/src/tokens.css:426（`--col-width-medium: 200px`）、:427（`--col-width-wide: 360px`）。
- 縮める仕組み: frontend/src/hooks/useFitTableZoom.ts（アプリ）、GAS `fitTableZoom`。
- 表は width:100%: frontend/src/components/DataTable.css:13-22。
- 本番24時間の文字数（products の名前、1145行。/tmp/CC報告ファイル/inventory-title-ellipsis/recon/lengths.tsv）: 日本語 p50 9・p90 31・最大47、英語 p50 15・p90 38・最大60、発送 最大34。備考は全行空。
- GAS（リポジトリ外。版18=テスト版27 で一致）: 商品名 index.html:1569-1575、備考・発送 :1599-1600、列定義 :1533-1545、table nowrap :405、PC 用 media :782-788。
