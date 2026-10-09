# AX-2b 実装後の実測（after-real。Chromium 147.0.7727.15、幅1280・light）

実ファイルの CSS と実 DOM（TextareaControl 標準の出力 class、G6 は `comp-textarea--code` 付き、StaffReportsPage.tsx:90 は inline の minHeight を保持）を計測し、事前の before / 事前予測 after（ax2b-visual.json）と照合した。

事前予測側の調整（設計どおりの変更を反映）: G6 ExtractionPromptConfigTab は font-family を `monospace` に、StaffReportsPage.tsx:90 は height/min-height/offsetHeight を 120px に（minHeight を残すため）。

## (1) 標準38件（ProductMasterDrawer.tsx の2件は保留のため除く）: after-real と事前予測 after の差 — 0 条件（比較 513 条件）


## (2) 商品編集 ProductEditPage.tsx:309: before との差（normal・focus・disabled） — 0 条件（比較 6 条件）


## (2') 商品マスタ修正ドロワー ProductMasterDrawer.tsx:217/221（保留。未移管の生 textarea のまま）: before との差 — 0 条件（比較 24 条件）


## (3) 既存 <Textarea> 金型 13 件: before との差 — 許容外 0 条件、許容（MergeCompanyModal.tsx:246 の枠色・disabled 背景）8 条件（比較 141 条件）

- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig0 normal: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240)
- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig0 disabled: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240); background-color: rgb(255, 255, 255) → rgb(226, 232, 240)
- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig1 normal: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240)
- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig1 disabled: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240); background-color: rgb(255, 255, 255) → rgb(226, 232, 240)
- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig2 normal: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240)
- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig2 disabled: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240); background-color: rgb(255, 255, 255) → rgb(226, 232, 240)
- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig3 normal: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240)
- 許容 frontend/src/components/MergeCompanyModal.tsx:246 sig3 disabled: border-top-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-right-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-bottom-color: rgb(203, 213, 224) → rgb(226, 232, 240); border-left-color: rgb(203, 213, 224) → rgb(226, 232, 240); background-color: rgb(255, 255, 255) → rgb(226, 232, 240)

## (4) 同じ祖先の input: before との差 — 0 条件（比較 70 条件）

