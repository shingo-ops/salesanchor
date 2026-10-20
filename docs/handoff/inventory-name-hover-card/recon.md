# recon: 在庫表の商品名を「切れているときだけ浮くカード」で見せる

- 基準: origin/main 64fd420a9（2026-10-20 fetch 後）。生データは /tmp/CC報告ファイル/inventory-name-card/（recon-raw.md と行番号つき全文）。
- 前の便: docs/handoff/inventory-title-ellipsis/design.md（PR #4552。商品名を1行「…」にし、全文はブラウザ標準の title で出す）。

## 1. 既存 ADR の検索
- `git grep -i -E "tooltip|ツールチップ|popover" docs/adr` の結果は1件だけ: docs/adr/ADR-067-design-token-enforcement.md:120（opacity 0/1 の直書きを許可する例として tooltip を挙げている）。
- docs/adr/ADR-144-ui-component-governance.md、docs/CC_UI_GOVERNANCE.md、docs/adr/FEATURE-INDEX.md には tooltip / popover の記述がない（0件）。
- 関係する ADR: ADR-1014（在庫表の見え方。改訂 2026-10-20 で「…」と title を記載）、ADR-067（トークン）、ADR-144（金型の先確認）、ADR-027（i18n。今回は新しい UI 文字列なし）。

## 2. 既存の金型
- frontend/src/components/Tooltip.tsx:22-31 props は children, content:string, placement, delay（既定150）。内容は文字列1つだけで、2段の表示はできない（:26）。
- frontend/src/components/Tooltip.tsx:42,46,52 位置計算で scrollX/scrollY を足している。一方 frontend/src/components/Tooltip.css:7 は position:fixed。
- frontend/src/components/Tooltip.tsx:114-121 トリガーは `<span style="display:inline-flex">`。「切れているときだけ出す」仕組みはない。
- frontend/src/components/Tooltip.css:6-26 は黒い帯の見た目（--tooltip-bg、--font-2xs、--radius-sm、nowrap）。
- frontend/src/components/Popover.tsx:23-36 はクリックで開閉する制御式で、ホバーの遅延はない。
- frontend/src/components/Popover.css:15-31 は白い面のスタイル（--bg-surface、--border、--shadow-lg、scale(.97)）。
- 利用箇所:
  - Tooltip は frontend/src/pages/inbox/MessageReactionBadges.tsx:9 だけ。
  - Popover は frontend/src/components/MultiSelect.tsx:14 だけ。
  - features/inventory と pages/viewer では、どちらも使っていない。

## 3. 商品名セル（変更対象）
- frontend/src/features/inventory/inventoryColumns.tsx:100-114（key "name"）。
  - 日本語: :103 `inventory-cell__title inventory-cell__clip`、:104 `title={it.product_name ?? #product_id}`。
  - 英語: :108-109。name_en があるときだけ出し、`title={it.name_en}`。
- frontend/src/pages/viewer/viewerColumns.tsx:57-68。
  - 日本語: :59 `title={it.japanese_title}`。
  - 英語: :62-63 `title={it.english_title}`。
- frontend/src/features/inventory/inventoryColumns.css:15-27。`@media (min-width:768px)` の中で `.inventory-cell__clip` に max-width:var(--comp-inventory-title-max-w)・ellipsis・nowrap を指定している。
- 列定義の利用先:
  - frontend/src/pages/inventory/InventoryPage.tsx:27,177（buildInventoryColumns）。
  - frontend/src/pages/viewer/InventoryView.tsx:14,78（buildViewerColumns）。
- 試験:
  - frontend/src/features/inventory/inventoryColumns.test.tsx:125-133（clip と title を検証）。
  - frontend/src/pages/viewer/viewerColumns.cells.test.tsx:101-109（同上）。

## 4. トークン（行番号は origin/main）
- 面・文字・線（ダーク版もあり）:
  - frontend/src/index.css:17 --bg-surface（ダーク :224）。
  - :28 --border（ダーク :233）。
  - :23 --text-primary（ダーク :229）。
  - :24 --text-secondary（ダーク :230）。
- 影（ダーク版もあり）: frontend/src/index.css:72 --shadow-xl（ダーク :264）。
- 角丸: frontend/src/tokens.css:94 --radius-xl 12px。
- z-index: frontend/src/tokens.css:122 --z-dropdown 50。
- 動き:
  - frontend/src/tokens.css:134 --duration-base 200ms。
  - :144 --transition-fast 150ms ease。
  - :148 --transition-slow 280ms cubic-bezier(0.4,0,0.2,1)。
  - :151-153 --ease-standard・--ease-enter・--ease-exit。
  - 少し行き過ぎて戻る easing（overshoot）のトークンはない。
- 文字:
  - frontend/src/tokens.css:14 --font-xs、:16 --font-base。
  - :31 --font-weight-semi。
  - :36 --line-height-base。
- 余白: frontend/src/tokens.css:69 --space-1、:70 --space-2。
- ぼかし用のトークンはない。前例は frontend/src/pages/schedule.css:1166-1168 だけ（`color-mix(in srgb, var(--bg-surface) 96%, transparent)` と `backdrop-filter: blur(12px)`）。

## 5. GAS 在庫一覧（テスト版28 = stage と同じ中身。~/CC報告ファイル-keep/inventory-title-ellipsis/gas/test_stage/index.html）
- :1581-1583 `<div class="title-cell">` の中に `<span class="title-cell__ja" title=…>` と `<span class="title-cell__en" title=…>`。
- :792 `.title-cell__ja, .title-cell__en` に max-width:var(--comp-inventory-title-max-w)・ellipsis・nowrap。:78 にその値 360px。
- :9- の `:root` に CSS 変数を1行ずつ置いている。ダーク用の定義はない（grep 0件）。
- 独自の吹き出し部品はない。title 属性は :1582-1583（商品名）と :1604-1606（最安・在庫最多の印）だけ。
- 反映状況:
  - テスト版は28（商品名「…」入り）。
  - 本番は18のまま。商品名「…」入りの19は未反映（deploy_prod.sh は未実行）。

## 6. 未確認
- GAS の index.html に --radius-xl・--shadow-xl・backdrop-filter があるか。実装時に担当が grep で確かめ、無ければ :root に写しを足す。
