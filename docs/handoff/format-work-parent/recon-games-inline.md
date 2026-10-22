# recon 使えるゲーム一覧の常時表示: 細分類の編集スライド（画面のみ）

> 親の書類: [recon.md](recon.md)（docs/handoff/format-work-parent/recon.md）。この書類は今回の現在地だけ。
> 基準: origin/main 13576c09c。worktree release/format-games-inline の実物を読んだ結果。
> PO 依頼（2026-10-23）: 「項目欄が裏に入っている、チェックボックスで選択式でいいからスライドページにデフォルトに表示させてくれ」。
> ADR 検索: 対象 ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）。

## 1. 今の形（変更前）
- 使えるゲームの欄は MultiSelect（ボタンを押すと一覧が開く）。実物 frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:322-333（変更前）。
- 一覧は Popover で開く。Popover の z-index は --z-dropdown 50、スライドは --z-drawer 301 のため、一覧がスライドの裏に回る（調査: 調査フォルダの zindex 記録）。
- 選択肢 gameOptions は tcgTypes（GET /super-admin/tcg/types）由来で、有効なゲームと、すでに選ばれているゲームだけ（frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:210-212）。
- 保存は frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:147-184 の submit。form.game_ids を昇順にして PUT /super-admin/product-formats/{id}/games。

## 2. 金型 Checkbox
- props: label・size・error・description と素の input の props（frontend/src/components/Checkbox.tsx:21-30）。checked・onChange・disabled・data-testid は素の props として input に渡る（同 :36-37 の rest 展開、:51-58）。

## 3. 縦または折り返しで並べる既存の形（0-3）
- 使う形: `<div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>` の中に Checkbox を並べる。実物 frontend/src/pages/inventory/InventoryFilterPanel.tsx:212-214（同 :181-186、:243、:262 にも同じ形）。トークンだけで、新しい CSS ファイルや色・px の直値は無い。
- 他の候補: frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:412 と frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:261 は単独の Checkbox で、並べる枠の前例ではない。

## 4. 2 列の格子を横いっぱいにする既存の形（0-4）
- 使う形: `<div className="form-group" style={{ gridColumn: "1 / -1" }}>`。実物 frontend/src/pages/note-master/NoteMasterPage.tsx:320。同じ階層の frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:338 にも `style={{ gridColumn: "1 / -1" }}` がある。
- 格子本体は frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:283（変更後の行番号）。

## 5. 消す文言の使い手（0-5）
- gamesClear・gamesNone・gamesCount は frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx の MultiSelect 呼び出しだけが使っていた（`git grep -n "gamesClear\|gamesNone\|gamesCount" origin/main` の結果）。
- MultiSelect.tsx は他の 4 画面が使うため触らない。
