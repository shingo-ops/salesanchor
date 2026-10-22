# design 使えるゲーム一覧の常時表示: 細分類の編集スライド（画面のみ）

> 設計の正本: [design.md](design.md)（docs/handoff/format-work-parent/design.md）。この書類に新しい設計判断はない。PO 依頼は 2026-10-23。
> 現在地: [recon-games-inline.md](recon-games-inline.md)（docs/handoff/format-work-parent/recon-games-inline.md）／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

守り手: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx

## 変更前後の要約
- 変更前: 使えるゲームは MultiSelect（ボタンで開く一覧）。一覧がスライドの裏に回り半分隠れる。
- 変更後: スライドの中に、見出しと金型 Checkbox（size="sm"）を折り返して並べる。外枠は 2 列の格子をぶち抜く form-group（gridColumn 1 / -1）。checked は form.game_ids に含まれるか、onChange は外すときは除き付けるときは末尾に足す（MultiSelect と同じ動き）。
- 変えないもの: 選択肢の取得元（GET /super-admin/tcg/types）、保存（submit、PUT /games）、API、MultiSelect.tsx 本体、CSS ファイル。
- 消すもの: MultiSelect 専用の文言 gamesClear・gamesNone・gamesCount（ja・en 両方）。「選択をクリア」ボタンは置かない。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|K1: スライドを開くと、押さなくてもゲームのチェック一覧がスライドの中に見え、裏に回らない|vitest（ProductFormatsMasterPanel.test.tsx の「ボタン無しで全部の有効ゲームが見える」「保存済みにチェック」）。PO 目視（○×）は反映後|
|K2: チェックを付け外しして更新すると、一覧表の「使えるゲーム」に反映される|vitest（作成時に games を置き換える・並べ替えて送る）。PO 目視は反映後|
|K3: 金型以外の部品、新しい CSS、直値が 0 件|`git diff origin/main --name-only` に CSS ファイルが無い。eslint・UI ガバナンス・デザイントークンの検査が緑|
|MultiSelect 本体を壊さない|MultiSelect.test.tsx が緑|
|ja と en が同じキー|i18n の検査が緑|

## 外部・過去事例の参照と我々への応用
数値つきの外部事例はない（docs/handoff/format-work-parent/design.md §10 のとおり）。過去事例は Checkbox を折り返し並べにする frontend/src/pages/inventory/InventoryFilterPanel.tsx:212-214 と、格子をぶち抜く frontend/src/pages/note-master/NoteMasterPage.tsx:320。

## 維持の仕組み
- 守り手: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx（ボタン無しの常時表示、無効ゲームが出ない、保存済みのチェック、作成時の置き換え、変更なしなら呼ばない、並べ替え、409 の表示）。
- 戻し方: この PR を revert する（画面のみ、DB・API は触らない）。

## 解析の正答率への影響
影響する経路は無い。画面（frontend/）の変更だけで、解析コード（backend/app/tasks、scripts/accuracy、gas/）を触らない。`git diff --name-only origin/main...HEAD` で変更ファイルが frontend/src と docs/handoff/format-work-parent だけであることを PR で示す。
