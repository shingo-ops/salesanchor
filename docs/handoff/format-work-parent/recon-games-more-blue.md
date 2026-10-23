# recon 細分類一覧の「他 N 件」だけを青文字にする（画面のみ）

> 親の書類: [recon.md](recon.md)（docs/handoff/format-work-parent/recon.md）。設計: [design-games-more-blue.md](design-games-more-blue.md)（docs/handoff/format-work-parent/design-games-more-blue.md）。
> 基準: origin/main 5d9c30286。PO 依頼（2026-10-23）。対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）。

## 現在地（変更前）
- frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:222-232 の renderGames は、`<span title={all}>` の中で preview と gamesMore を1本の文字列にしている。
- frontend/src/index.css:33 に `--accent`。frontend/src/index.css:35 の `--link` はナビゲーションリンク用。
- frontend/src/locales/ja.json:5207 / frontend/src/locales/en.json:5207 に gamesMore。
- トークン参照のインライン style の既存例: frontend/src/pages/badges/BadgesPage.tsx:102、frontend/src/pages/inbox/InboxConversationRows.tsx:68。
- frontend/eslint.config.js:39 は var() の参照を勧めている。
