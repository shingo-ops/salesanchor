# recon: 最安・在庫最多を「塗りの角丸」にする（ADR-1014 改訂（4））

基準: `git fetch` 後の origin/main（1deed5451、#4524 マージ 809abe52a を含む）。

## 既存 ADR の検索
- `git grep -n 'comp-value-frame'` の結果、ADR は次の2件だけ。
  - `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:95-106`（改訂 2026-10-19（3）: 見た目・色・守り）
  - `docs/adr/ADR-067-design-token-enforcement.md:156-163`（表「カラートークン（tokens.css — 在庫表の最安・在庫最多の枠 / ADR-1014）」2行）
- 金型 Badge の形と色は `frontend/src/components/Badge.css` が正本（ADR-067「全カラーは CSS 変数参照のみ」）。

## 現在の実物（#4524 本番反映済み、Deploy 39184107505 success）
- `/Users/tanizawashingo/worktrees/salesanchor/release-inventory-block-pill/frontend/src/features/inventory/inventoryColumns.css:51-63`
  - `.inventory-cell__value { display:inline-block; padding: var(--space-1px) var(--space-1); border-radius: var(--radius-sm); }`
  - `--cheapest` / `--most-stock` は `box-shadow: inset 0 0 0 var(--space-2px) var(--comp-value-frame-*)`（細い線の枠、塗りなし）
- `frontend/src/tokens.css:395-397`（ライト）・`:595-597`（ダーク）に `--comp-value-frame-cheapest`・`--comp-value-frame-most-stock`
- `git grep comp-value-frame` で、コードでの使用は inventoryColumns.css:59・:62 と tokens.css の定義だけ（他の docs は handoff と ADR）。
- `frontend/src/features/inventory/blockBadges.tsx:5-13` `BlockValue` はクラス `inventory-cell__value--cheapest` / `--most-stock`、testid、title を付ける（変えない）。
- 試験はクラス名と testid を見る（`frontend/src/features/inventory/inventoryColumns.test.tsx:85-107`、`frontend/src/pages/viewer/viewerColumns.cells.test.tsx:68-88`）。CSS の中身は見ない。

## 金型 Badge の形（`frontend/src/components/Badge.css`）
- 角: `border-radius: var(--comp-badge-radius)`（tokens.css:497 = `var(--radius-full)` の丸ピル）
- sm の余白: `padding: var(--space-2px) var(--space-2)`、`min-height: var(--comp-badge-height-sm)`（20px）
- soft の色: info = `background: var(--info-bg); color: var(--info-text)`、success = `var(--success-bg)` / `var(--success-text)`
- 文字: `font-size: var(--font-xs)`（12px）、`line-height: 1`
- 色の値: `--info-bg` ライト #bee3f8・ダーク #1e3a5f、`--success-bg` ライト #c6f6d5・ダーク #14432b（`frontend/src/index.css:56・109・249・298`。ライトは `:root`、ダークは `:root.force-dark`）。ライト・ダークとも定義済み。
- 文字と塗りのコントラスト（設計審査で計算、/tmp/CC報告ファイル/inventory-block-pill/design-review/contrast.txt）: ライト info 4.01:1、ライト success 7.30:1、ダーク info 6.38:1、ダーク success 9.28:1。

## PO の言葉（2026-10-19）
- 「バッジと同じ囲み方を想定していた」「スプレッドシートのデータ入力規則のプルダウンみたいに囲って色付けするやつ」
- Opus の理解（角丸・薄い水色／薄い緑の塗り・数字は濃い色・文字は足さない・列幅は変えない）に「y」。
