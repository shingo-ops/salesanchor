# 便1 金型 コード審査（Opus・2026-10-15）

対象: release/inventory-table-bin1 b4d1ad3f7（実装は Sonnet。設計 design.md「便1 金型」1-0〜1-6）

判定: **APPROVE**

## 照合した点（実物）
- 1-0 既存 DOM: frontend/src/components/DataTable.tsx の `!useFrame` 分岐は `<div class="comp-table comp-table--{density}" role="region">` に table とページ送り（従来と同じ）。DataTable.bin1.test.tsx 先頭で assert。
- 1-0b: frontend/src/hooks/useIsMobile.ts は初期値と useEffect の両方で matchMedia の有無を見る。useFitTableZoom も同じ判定。
- 1-1: rowTestId は tr とカード、paginationTestIds は前へ・次へ・件数、paginationDisabled は `page <= 1 || paginationDisabled` / `!hasNextPage || paginationDisabled`。align は th と td にクラス。
- 1-2: DataTable.css の書く順は 本文固定列 → 見出し → 見出しの角 → 行の色（danger / warning / selected / hover / selected:hover）で設計の詳細度どおり。新トークン --comp-table-sticky-max-h は tokens.css の --comp-table-* の並び。
- 1-3: constants/tableFit.ts の3定数が GAS と同値。lib/tableFitZoom.ts は設計の式どおり。hooks/useFitTableZoom.ts は測る前に removeProperty、border はスクロール箱、ResizeObserver（無ければ resize）・matchMedia change・rows 変化を rAF で間引く。style 属性は使わず setProperty のみ。N-r3-7（無効時・ref null で何もしない）を満たす。
- 1-4: カードは div・role=list/listitem、mobileOrder / mobileHidden / mobileLabel、カードでは sticky・fit を効かせない。カード値に overflow-wrap: anywhere（N-r3-5）。
- 1-5: MultiSelect は Popover 土台、0/1/2件のボタン表示、クリア、testid 3種。文言は呼び出し側。
- 使用した色・間隔の変数はすべて frontend/src/index.css または tokens.css に定義あり。ただし `--primary`（チェックの色）は index.css に無く feature 側の CSS にだけある。既存 DataTable.css:152 と同じ書き方のため本便では揃えたまま（今の見た目と同じ）。

## 検査（Sonnet 実行・生出力 /tmp/CC報告ファイル/inventory_bin1/）
- lint 0 / tsc 0 / check:all 0 / check:new-tokens 0 / build-storybook 0。
- vitest 全体: 1222 件中 6 件失敗（4ファイル・waitFor の時間切れ）。4ファイル単独の再実行は全件成功。CI の結果で最終確認する。

## 残す点
- zoom の内側の max-height が見た目で z 倍になるか（1-3 の【未確認】）は便2 の e2e で実測する。
