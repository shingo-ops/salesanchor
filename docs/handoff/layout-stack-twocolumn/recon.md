# recon: 並べ方の金型（Stack / TwoColumn）新設

## 問題の実測確認

- PR #4094 の2画面（features/tcg-analysis-review の編集モーダルと確認ドロワー）に、縦積みと2列の直書き style が計4箇所ある。ADR-144 は「金型がなければ止めて PO 許可後に新設」と定める（`docs/adr/ADR-144-ui-component-governance.md:59-62`）。PO は新設を承認済み（2026-10-10）。
- origin/main の `frontend/src/components/` 内に Stack / Grid / Columns / FormRow / FieldRow / Layout 系の名前を持つ部品は `frontend/src/components/PageLayout.tsx` のみ（ページ見出し用で並べ方の部品ではない）。検索生出力: /tmp/CC報告ファイル/layout-mold-search.txt
- `flex-direction: column` / `gridTemplateColumns` を含む既存部品は、いずれも各部品の内部実装（`frontend/src/components/Callout.css:8`、`frontend/src/components/FormField.css:19`、`frontend/src/components/Modal.css:34`）か、固有列数の詳細パネル（`frontend/src/components/ShippingDetailPanel.tsx:395`）で、汎用の並べ方部品として使えるものはない。

## 金型の登録手順（文書で特定）

- 作法: Xxx.tsx + Xxx.css（var() のみ）+ Xxx.stories.tsx（`docs/CC_UI_GOVERNANCE.md:15`）。
- 一覧・index への登録先は無い。Storybook は stories から自動収集、stories 欠落は `frontend/scripts/check-stories-count.js:24-32` が検出。
- 手本: `frontend/src/components/Callout.tsx`（クラス名 `comp-*`、variant をクラスに変換）。
- 間隔トークン: `frontend/src/tokens.css:68-74`（--space-1〜--space-8）。

## 置き換え対象（PR #4094 側・本PRには含まない）

- 縦積み gap=var(--space-3): モーダル本体、ドロワー本体の2箇所
- 縦積み gap=var(--space-2): モーダル右列の1箇所
- 2列（1fr 2fr、gap=var(--space-3)、alignItems start）: モーダルの1箇所
- 置き換え差分: /tmp/CC報告ファイル/v102-cd2-mold-replace.diff（#4094 に適用するのは設計者）

## ADR参照

- 該当ADR: ADR-144（金型ガバナンス）、ADR-067（デザイントークン強制）
- 既存ADRの検索: `git grep -il "stack\|two-column" docs/adr/` に該当する並べ方金型のADRなし
