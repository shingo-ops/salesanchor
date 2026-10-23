# design 細分類一覧の「他 N 件」だけを青文字にする（画面のみ）

> 設計の正本: [design.md](design.md)（docs/handoff/format-work-parent/design.md）。PO 依頼は 2026-10-23（#4673 の目視は合格）。
> 現在地: [recon-games-more-blue.md](recon-games-more-blue.md)（docs/handoff/format-work-parent/recon-games-more-blue.md）
> 前段: [design-games-filter.md](design-games-filter.md)（docs/handoff/format-work-parent/design-games-filter.md）／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

守り手: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx

## 現在地（recon）
- frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:222-232 の renderGames は、`<span title={all}>` の中で preview と gamesMore を1本の文字列にしていた。
- frontend/src/index.css:33 に `--accent`（ダークは :237 で切り替わる）。
- frontend/src/locales/ja.json:5207 と frontend/src/locales/en.json:5207 に gamesMore（キー追加なし）。
- 文中の文字にトークンで色を付ける既存の形: frontend/src/pages/badges/BadgesPage.tsx:102、frontend/src/pages/inbox/InboxConversationRows.tsx:68。eslint.config.js:39 は var() の参照を勧めている。

## 設計判断
- 色は `var(--accent)`（frontend/src/index.css:33）。
- `--link`（frontend/src/index.css:35）は使わない。ナビゲーションリンク用で、この文字は押せないため。
- `--info-text` は使わない。通知用の色で、主要色の青と見た目がずれるため。
- 新しい CSS は作らない。外側の `<span title={all}>` は残す。

## 変更前後の要約
- 変更前: 「Pokemon, One Piece, Dragon Ball, 他 13 件」が全部同じ色。
- 変更後: 「他 N 件」だけが `<span style={{ color: "var(--accent)" }}>`。ゲーム名、0 件の "-"、3 件以下、並び順、絞り込みは変えない。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|K1: 一覧の「他 N 件」だけが青く、ゲーム名は今の色のまま|vitest（ProductFormatsMasterPanel.test.tsx の「colors only the 'more' count」「first 3 games」）。PO 目視は反映後|
|K2: 新しい CSS、色の直値、ui-allow が 0 件|`git diff --name-only` に CSS が無い。eslint・UI ガバナンス・トークンの検査が緑|
|ja と en が同じキー|check:i18n-missing-keys が緑|

## 外部・過去事例の参照と我々への応用
数値つきの外部事例はない（docs/handoff/format-work-parent/design.md §10 のとおり）。過去事例はfrontend/src/pages/badges/BadgesPage.tsx:102 と frontend/src/pages/inbox/InboxConversationRows.tsx:68 のトークン参照のインライン style。

## 維持の仕組み
- 守り手: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx。
- 戻し方: この PR を revert する（画面のみ、DB・API は触らない）。

## 解析の正答率への影響
影響する経路は無い。画面（frontend/）の変更だけで、解析コード（backend/app/tasks、scripts/accuracy、gas/）を触らない。
