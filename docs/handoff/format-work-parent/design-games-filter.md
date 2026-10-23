# design 細分類一覧の「使えるゲーム」まとめ表示と作品の絞り込み（画面のみ）

> 設計の正本: [design.md](design.md)（docs/handoff/format-work-parent/design.md）。この書類に新しい設計判断はない。PO 依頼は 2026-10-23。
> 現在地: [recon-games-filter.md](recon-games-filter.md)（docs/handoff/format-work-parent/recon-games-filter.md）／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

守り手: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx

## 変更前後の要約
- 変更前: 一覧の「使えるゲーム」は全件を ", " でつなぐ。絞り込みは無い。
- 変更後: tcgTypes の順に並べ、先頭 3 件（GAME_PREVIEW_COUNT）＋「他 N 件」。全件はセルの title に入れる。ContentToolbar の left に SelectControl（すべての作品＋有効な作品）を置き、選ぶと画面の中だけで items を絞る（API の取り直しなし）。
- 変えないもの: API、DB、ドロワー、保存、チェック一覧、CSS ファイル。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|K1: 使えるゲームが先頭 3 つ＋「他 N 件」で出る（本番で 16 件の行は「他 13 件」）|vitest（ProductFormatsMasterPanel.test.tsx の「first 3 games」「orders games by tcgTypes」）。PO 目視は反映後|
|K2: 絞り込みで作品を選ぶと、その作品で使える細分類だけが出る|vitest（「filters rows by the selected game」「does not offer inactive games in the filter」）|
|K3: 金型以外の部品、新しい CSS、直値が 0 件|`git diff --name-only` に CSS が無い。eslint・UI ガバナンス・トークンの検査が緑|
|ja と en が同じキー|check:i18n-missing-keys が緑|

## 外部・過去事例の参照と我々への応用
数値つきの外部事例はない（docs/handoff/format-work-parent/design.md §10 のとおり）。過去事例は SelectControl を ContentToolbar left に置く frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx。

## 維持の仕組み
- 守り手: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx。
- 戻し方: この PR を revert する（画面のみ、DB・API は触らない）。

## 解析の正答率への影響
影響する経路は無い。画面（frontend/）の変更だけで、解析コード（backend/app/tasks、scripts/accuracy、gas/）を触らない。`git diff --name-only origin/main...HEAD` で変更ファイルが frontend/src と docs/handoff/format-work-parent だけであることを PR で示す。
