# recon: 在庫表のタブを表にくっつけ、閲覧ページと GAS もアプリと同じタブにする

基準: `origin/main` 38613d7d7（2026-10-20 fetch 後）。調査の生出力: `/tmp/CC報告ファイル/tabs-attach-recon/`（key_excerpts.txt・recon2_*.txt）。調査は Sonnet、要点の照合は Opus が実物を読んで行った。

## PO の依頼（原文、2026-10-20）
「アプリのPCの在庫表だけどポケモンとかの絞り込みのタブがテーブルに連結されてないから修正できる？ アプリの在庫表と同じ仕様にしたい、アプリの在庫表はその他だけ白い枠がついているからプルダウンを残しつつ透明にできる？→このアプリのタブと同じ仕様に閲覧用のアプリページとGASも修正してほしい」

PO のスクショ（PC）:
- アプリの在庫表: 検索欄2段 → 少し空白 → タブ「すべて／ポケモン／ワンピース／ドラゴンボール」＋白い枠のプルダウン「その他」＋右端に注記「※LINE の投稿から 24 時間以内…」 → 隙間 → 表。
- 閲覧ページ: 見出し → タブ「全て 1221／ポケモン 787／ワンピース 250／…／ホロライ…」（件数の丸・右にはみ出す）→ 検索欄2段 → 表。

## 既存 ADR・設計
- ADR-1019 項8（`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:26`）: 閲覧ページはアプリの在庫表と同じ金型（DataTable・Select・Tabs ほか）で作る。タブの細かい仕様は決めていない。
- ADR-1030（`docs/adr/ADR-1030-drop-products-tcg-type.md:15`）: 在庫表のタブは中分類（type_master）で絞る。
- ADR-144（`docs/adr/ADR-144-ui-component-governance.md:38`）／`docs/CC_UI_GOVERNANCE.md:10,23,27`: 自作タブは Tabs 金型を使う。生 select は Select 金型。例外は `ui-allow`。
- ADR-1014 にタブの配置の決めは無い（GAS の版番号の記録のみ :142）。GAS のタブの設計記録は `docs/handoff/gas-viewer-series-tabs/design.md`（件数を出さない理由: 24時間の切替で件数と表示数がずれる）。
- `docs/adr/FEATURE-INDEX.md` に在庫表タブ専用の行は無い。

## アプリの在庫表（file:line）
- `frontend/src/pages/inventory/InventoryPage.tsx:525-571`: タブは Tabs 金型ではなく生の `<button className="tab">`（:534）。例外コメント `ui-allow: TCG type tab bar ... (#2624)`（:526）。見た目は `frontend/src/company-forms.css:40-77` の `.tabs` を流用。
- 固定の3つ＋すべて: `["all","pokemon_booster_box","one_piece","dragon_ball"]`（:529）。ラベルは GET /products/tcg-types の name_ja（:530-531）。残りの種類は `SelectControl size="sm"`「その他」（:539-555）。残りが0なら出さない（:539）。件数は出さない。選択中の既定は pokemon_booster_box（:126）。
- 白い枠: `frontend/src/components/FormField.css:46-58` `.comp-select__control`（border 1px var(--border)・background var(--bg-surface)）。
- 表との隙間: :527 のインライン `margin: "var(--space-sm) 0"` と `.tabs` の下線 2px（company-forms.css:40-46）。表の枠は `frontend/src/components/DataTable.css:11-17` `.comp-table`（border 1px var(--border)・角丸 var(--comp-table-radius)）。
- 検索欄とタブの間の空白: 読込表示 div（:518-523、`minHeight: 1.5rem`、非表示でも場所を取る）。
- 注記: :556-571 `<p data-testid="inventory-expiry-warning">`（タブ行の右端）。
- テスト: `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx:96` が画面全体で `queryByRole('tab')` が null であることを見ている（今のタブは role=tab でないため通っている）。注記のテスト `InventoryPage.settings.test.tsx:46,79,94`。

## 閲覧ページ（file:line）
- `frontend/src/pages/viewer/InventoryView.tsx:214-237`: PC は `<Tabs variant="underline" size="sm">`、件数つき（count）。スマホは SelectControl。タブは検索欄（ContentToolbar :249〜）より上、表（DataTable :295）とは離れている。
- タブの元: 行の `series` を件数順に全部（`frontend/src/pages/viewer/viewerFilter.ts:212-222` `seriesTabs`）。「その他」は無い。絞り込みは `r.series !== f.tab`（:85）。`TAB_ALL = "all"`（:10）。
- 行の項目（`frontend/src/pages/viewer/types.ts:13-29`）に work_code は無い。series は `type_master.name_ja`（`backend/app/services/tcg_distribution_svc.py:331` `COALESCE(ser.name_ja,'') AS series`、:364-365 `LEFT JOIN public.type_master ser ON ser.id = p.work_id`）。アプリの work_code も同じ type_master の code（`backend/app/routers/products.py:109`）。同じ行の code と name_ja なので、series で絞ってもアプリと同じ行の集まりになる。
- 【事実】本番の name_ja は、PO のスクショでアプリのタブ（name_ja を出す :531）が「ポケモン」「ワンピース」「ドラゴンボール」、閲覧ページのタブ（series を出す）も「ポケモン」「ワンピース」「ドラゴンボール」。
- テスト: タブを直接見るテストは無い。`viewerFilter.test.ts:55-57` が seriesTabs の順。

## GAS 在庫一覧
- ソースはこのリポジトリに無い（正本 shingo-ops/tcg-client-viewer）。最新の写し: `~/CC報告ファイル-keep/inventory-toolbar-two-rows/gas/prod_stage/`（上部2段の変更入り。PO の反映待ち）。
- データはシート「在庫集計」（Code.js:28, :56-63）。列は14（Code.js:10-25）で Series はあるが work_code は無い。
- タブ: index.html:967 `#seriesTabs`（表 #content の直前）、CSS :773-794（Tabs underline/md の写し、スマホはセレクトに切替）、JS :1243-1275 `buildSeriesTabs`（series を件数順に全部、件数は出さない、「その他」は無い）。
- 【未確認】写しが今の本番・テストの実物と同じか（clasp pull での照合は GAS 作業の最初に行う）。

## 部品（金型）
- Tabs（`frontend/src/components/Tabs.tsx:30-45`）: items／activeKey／onChange／variant underline|pill／size sm|md／className。表にくっつける指定や、タブの横に部品を置く口は無い。underline の下線は `.comp-tabs--underline { border-bottom: 1px solid var(--border) }`（Tabs.css:34-37）、タブは `margin-bottom:-1px` で下線に重なる（:89-92）。
- Select（`frontend/src/components/Select.tsx:55-56,74,84`）: variant standard|karte|header|tabbar|product-edit。tabbar（FormField.css:238-258）は Inbox 用で、枠と背景は残る（透明ではない）。使用箇所は InboxMessageThread.tsx:454・InboxPage.tsx:173。
- 表にくっつける前例: `frontend/src/pages/buyback-prices/BuybackPricesPage.module.css:40-50`（Tabs の下に DataTable を置き、表の上の角丸を0にする）。
- DataTable は className を受ける（`frontend/src/components/DataTable.tsx:94,156,218`）。
- Storybook: `frontend/src/components/Tabs.stories.tsx`・`Select.stories.tsx` あり。
