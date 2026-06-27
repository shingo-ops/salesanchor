# design — inventory-ui-tweaks

**対象ADR**: ADR-093 (`docs/adr/ADR-093-inventory-table-product-master-redesign.md`)
**recon**: `docs/handoff/inventory-ui-tweaks/recon.md`
**変更種別**: フロント表示調整のみ（migrations/・deploy.yml なし＝危険変更なし）
**日付**: 2026-06-25

---

## 変更概要（3件）

### #1 警告をタブ行の右端へ（recon :414, :466）
- `:414-418` の警告 `<p>` を削除（独立行から移動）。
- タブ行コンテナを `display:flex; gap:var(--space-sm); alignItems:flex-start` に変更。
- 既存タブ群（4ボタン + select）を内側 `<div style="display:flex; gap:var(--space-xs); flexWrap:wrap; flex:1; alignItems:center">` でラップ。
- 警告 `<p>` を隣に `margin:0; marginLeft:auto; flexShrink:0; fontSize:var(--font-xs); color:var(--text-secondary); whiteSpace:nowrap` で配置。
- 文言頭に `※` を付与（JSX で `{"※"}{t("inventory.expiryWarning")}`）。

### #2 検索行の高さ1.5倍（recon :383, :395, :398, :403）
- H 算出: padding×2=8px + font-size×line-height=12×1.6=19.2px + border=2px = **29.2px → 29px**
- 新高さ: round(29.2×1.5) = **44px**
- 検索input + 検索/リセット/詳細フィルタ の4要素に `height:"44px"` を inline 付与。ボタンは `display:"inline-flex"; alignItems:"center"` を追加。
- `btn-sm` クラス本体は変更しない（共有クラスのためスコープ外）。

### #3 その他selectをアプリ標準枠線に統一（recon :492）
- 追加: `border:"1px solid var(--border)"; borderRadius:"var(--radius-sm)"; background:"var(--bg-surface)"`
- padding/font-size は現状維持（`var(--space-1) var(--space-10px)` / `var(--font-xs)`）。

---

## KPI 検証基準

| 基準 | 検証方法 |
|------|---------|
| 警告がタブ行右端に表示（※付き・xs文字） | 画面目視：タブ行の右側に灰色小テキストが出ること |
| タブ折返し時も警告は右上 | 画面幅を狭めて折返し確認 |
| 検索input・3ボタンの高さが約44px | Chrome DevTools で4要素の clientHeight を確認 |
| 「その他」selectに枠線・角丸が付く | 画面目視：OSデフォルト外観でなくアプリ統一フォームに見えること |
| タブ切替・検索・絞り込み・ソートが従来どおり動作 | 画面操作 |
| diff に migrations/ / deploy.yml が出ない | `gh pr diff --name-only` で確認 |
| tsc エラーなし | `tsc --noEmit` が 0 exit |
| i18n キー変更なし（新キー追加なし） | ja.json / en.json に差分なし |

---

## 外部・過去事例の参照と我々への応用

- 過去事例（社内）: ADR-093 が /inventory を全オファー明細ビューとして確定。PR #2564（発売日列）・PR #2581（タブ集約・警告移動・往復フロー全廃）に続く仕上げ調整。
- 外部事例（一般UI）:
  - 補足注意は一覧本文でなく「行端の控えめ注記」が可読性の定石（Nielsen Norman Group "Secondary information placement"）。警告の右上小型化はこれに倣う。
  - 主操作の入力欄・ボタンは十分な打点高さを確保することで操作ミスが減る（Apple HIG: minimum tap target 44pt）。検索行高さ44pxはこの基準と一致。
  - フォーム要素は OS 標準でなくアプリのデザイントークンに統一することで視覚的一貫性が維持できる（Material Design "Consistent form styling"）。その他selectの枠線統一はこれに倣う。
