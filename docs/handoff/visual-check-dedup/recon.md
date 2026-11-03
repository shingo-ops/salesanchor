# visual-check-dedup 調査（recon）

調査担当の記録。製品コード・試験・設定は変えていない。確かめ方: `cd frontend && npm ci --ignore-scripts` のあと `E2E_NO_WEBSERVER=1 npx playwright test --list --reporter=json --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280`（試験は実行していない）。

## 0. 先に結論（事実だけ）

1. 収集は 816 件 = 272 × 3 project（list の件数。project ごと 272 で一致）。frontend/playwright.config.ts:63-76 の 3 project が frontend/tests-e2e/visual-language/*.spec.ts（23 ファイルのうち spec は 20 本）を全部拾う（testMatch はいずれも playwright.config.ts:64,69,74）。
2. 実行されるのは 733 回、skip は 83 回（816-83）。内訳は 3 節。
3. 分類は A=46 / B=0 / C=222 / D=4（1 project あたりの test 数）。C は 222 test × 3 幅 = 666 回の実行。
4. C の 222 test は、test 自身が最初の goto の前に幅を固定する（gotoViewer / gotoInventory / setViewportSize）ため、3 project で同じ幅・同じ確かめになる。差が出るのは project の isMobile・hasTouch の設定だけで、それを読む test は 0 件（5 節）。
5. 実行時間の内訳（どの test が 14 分のどれだけか）は未確認（時間の計測データが手元に無い）。

## 1. 3 project の設定

- vl-mobile-390: 390x844・isMobile: true・hasTouch: true — frontend/playwright.config.ts:63-66
- vl-tablet-768: 768x1024・Desktop Chrome のまま（触る扱いなし）— frontend/playwright.config.ts:67-71
- vl-desktop-1280: 1280x900・同上 — frontend/playwright.config.ts:72-76
- 画面検査（内部）ジョブ: timeout-minutes: 15（.github/workflows/e2e.yml:158）、実行は `npm run test:e2e:vl`（.github/workflows/e2e.yml:199-205）。
- e2e.yml:150 のコメントは「現状 2 本・テスト 8 件」のままで、実測（20 spec・272 test/project）と合っていない。

## 2. 幅を決め直す部品（helper）

- gotoViewer: 既定 width=390・height=844（frontend/tests-e2e/visual-language/viewer-helpers.ts:137-138）で、goto の前に setViewportSize（viewer-helpers.ts:140）、goto は :142。
- gotoInventory: 既定 390x844（frontend/tests-e2e/visual-language/inventory-helpers.ts:110-111）、setViewportSize は :112、goto は :114。
- openInboxList など受信箱の開き方は幅を決め直さない（frontend/tests-e2e/visual-language/inbox-helpers.ts:90-95。goto は :94）。受信箱の spec は project の幅のまま動く。
- 上記 viewer / inventory 系の spec は、どれも幅を引数か setViewportSize で明示している（表の「幅を決め直すか」列に行番号）。

## 3. skipped 83 件（どれで、なぜ）

実行時の `test.skip(条件)` による。list の段階では全 816 件が「実行予定」で、skip は実行して初めて決まる。条件は実行時の project 幅（projectWidth は testInfo.project.use.viewport を読む。frontend/tests-e2e/visual-language/inbox-single-column.spec.ts:78-82）から機械的に決まるので、件数は次の算出（実行はしていない）:

1. frontend/tests-e2e/visual-language/inbox-single-column.spec.ts のスマホ専用 38 test（`projectWidth > MOBILE_MAX_PX` で skip。例 :95,131,154）→ 768 と 1280 で skip = 76 回。MOBILE_MAX_PX=767（inbox-helpers.ts:24）。
2. 同 spec の「PC・タブレット」6 test（:795,1194,1357,1537,1841,1904 の `projectWidth <= MOBILE_MAX_PX` で skip）→ 390 で skip = 6 回。
3. frontend/tests-e2e/visual-language/app-update-notice.spec.ts:23（TARGET_PROJECTS は 390 と 1280、:19）→ 768 で skip = 1 回。
- 合計 76+6+1 = 83。ほかの spec に test.skip / test.fixme は無い（grep で確認）。
- 注意: 83 は上の条件から計算した値で、CI の実測ログは見ていない（未確認）。ユーザー提示の 83 と一致した。

## 4. アプリ側で「触る・スマホ」で動きが変わる所（frontend/src。frontend/viewer は index.html だけ）

- useIsMobile の判定材料は `matchMedia("(max-width: 767px)")` のみ（frontend/src/hooks/useIsMobile.ts:20,25。767 は frontend/src/constants/breakpoints.ts:20）。触る扱い・userAgent・maxTouchPoints は読まない。
- 使う側: viewer の InventoryView（frontend/src/pages/viewer/InventoryView.tsx:65 ほか）、InventoryPage、受信箱（InboxPage / InboxMessageThread / useInboxState）など（grep で 11 ファイル）。
- 幅でだけ決まる別の判定: useFitTableZoom は `(min-width: 768px)`（frontend/src/hooks/useFitTableZoom.ts:29）。1280 を境にする定義は frontend/src/constants/breakpoints.ts:24-26（DESKTOP_MIN）。
- `@media (hover: hover)` は 4 か所: frontend/src/components/MultiSelect.css:46、frontend/src/pages/viewer/viewer.css:111、frontend/src/pages/inventory/InventoryToolbar.css:61、frontend/src/pages/inbox/InboxPage.css:1873。いずれも hover 時の見た目の規則。
- 長押し: frontend/src/hooks/useLongPress.ts:8 は pointerType で絞らない（マウスでも成立）。frontend/src/pages/inbox/useLongPressReveal.ts:33 は touch のみ。試験の長押しは page.mouse（inbox-single-column.spec.ts:57-58）で行い、touchscreen / tap は使わない。
- `pointer: coarse`・ontouchstart・maxTouchPoints・screen.width/height・device-width の読み取りは frontend/src と frontend/viewer に 0 件（`device-width` は frontend/viewer/index.html:6 の meta viewport のみ。アプリの判定ではない）。userAgent は frontend/src/lib/webPush.ts:18 のみ（通知の可否の判定。画面検査の画面とは別）。
- 未確認: Playwright の isMobile: true / hasTouch: true が Chromium の `hover` / `pointer` メディア特性や meta viewport の扱いをどう変えるか（実機で動かして確かめていない）。

## 5. test 側が project・触る扱いを読む所

- project 名を読む: app-update-notice.spec.ts:23,63,84（390 と 1280 で別の判定、768 は skip）。
- project の viewport を読んで分岐: inbox-single-column.spec.ts（:78 の projectWidth と各 test.skip、:1857 の `< 1280`）、inbox-lead-merge.spec.ts:23-26,83,88,103,117。
- isMobile（変数名）は inbox-lead-merge.spec.ts:83 の「幅 ≤767」の別名で、Playwright の isMobile 設定ではない。
- Playwright の isMobile / hasTouch / tap / touchscreen を読む test: 0 件（grep で確認）。
- 幅を固定する viewer / inventory 系は、project も触る扱いも読まない（表の「project・触る扱いを読むか」列が「なし」）。

## 6. 試験の書き方の決まり（3 幅の扱い）

- 決まりとして明文化されたものは見つからなかった。frontend/tests-e2e に README は無い。ADR に 3 幅（vl-mobile-390 など）の規定は無い（docs/adr を grep で確認）。
- docs/specs/design-system/visual-language/design.md:53 と kgi.md:20（K6）は「3 幅（390/768/1280）の画面検査を作る」という目標で、各 test が 3 幅で別の確かめをするとは書いていない。README.md:24 は「3 幅の画面検査はまだ無い」と書かれたまま（現状と食い違い）。
- 慣行として各便の設計書に書かれている: 「新 spec は必ず setViewportSize で 360 / 390 を明示する（project 既定の幅に頼らない）」— docs/handoff/inventory-toolbar-mercari/design.md:116-118。「3 つの project が全部この spec を収集する」ことへの言及と、重複を許容する旨 — frontend/tests-e2e/visual-language/inventory-raw-text-mobile.spec.ts:14-15、inventory-mobile-baseline.spec.ts:19、viewer-focus-trap.spec.ts:29-33、docs/handoff/viewer-top-compact/review-opus.md:39、docs/handoff/viewer-search-suggestions/review-opus.md:91。
- つまり幅固定が慣行の形で、3 project で同じ確かめが走ることは各所で認識されている。

## 7. 分類と件数

- A=3 幅とも別の確かめ（A の内訳: inbox-single-column の「スマホ専用 38 件（1 幅だけ実行）」と「768/1280 で分岐する 2 件」、app-update-notice 1、inbox-baseline 2、inbox-lead-merge 3）。
- B=タブレットとパソコンが同じ（スマホは触る扱いが違う）。該当 0 件。幅固定の test は 3 project とも同じ幅で、スマホだけ触る扱いが違うが、それを読む test が無いので C にした。
- C=3 幅とも同じ。
- D=判定できない。inbox-single-column の「PC・タブレット」4 test（768 と 1280 で同じ書き方。アプリ側に 1280 を境にする分岐 breakpoints.ts:24-26 はあるが、この 4 test の結果が両幅で同じかは未確認）。

分類ごとの件数（1 project あたりの test 数 / 3 幅での実行回数 / skip）:

| 分類 | test 数 | 実行回数 | skip |
|---|---|---|---|
| A | 46 | 59 | 79 |
| B | 0 | 0 | 0 |
| C | 222 | 666 | 0 |
| D | 4 | 8 | 4 |
| 合計 | 272 | 733 | 83 |

（A の skip 79 = スマホ専用 38 test の 76 + app-update-notice 1 + PC・タブレット 2 test（1537,1841）の 2 回。D の skip 4 = PC・タブレット 4 test の 390 での skip。）

spec ごと:

| spec | A | B | C | D | 1 projectあたりのtest数 | 3幅での実行回数 | skip |
|---|---|---|---|---|---|---|---|
|app-update-notice.spec.ts|1|0|0|0|1|2|1|
|drawer-inert-closed.spec.ts|0|0|3|0|3|9|0|
|inbox-baseline.spec.ts|2|0|0|0|2|6|0|
|inbox-lead-merge.spec.ts|3|0|0|0|3|9|0|
|inbox-single-column.spec.ts|40|0|0|4|44|50|82|
|inventory-mobile-baseline.spec.ts|0|0|4|0|4|12|0|
|inventory-raw-text-mobile.spec.ts|0|0|3|0|3|9|0|
|inventory-series-sort-panel.spec.ts|0|0|21|0|21|63|0|
|inventory-toolbar-mercari.spec.ts|0|0|23|0|23|69|0|
|popover-mold.spec.ts|0|0|6|0|6|18|0|
|viewer-choice-sheet.spec.ts|0|0|17|0|17|51|0|
|viewer-control-tap-size.spec.ts|0|0|21|0|21|63|0|
|viewer-filter-panel-mercari.spec.ts|0|0|26|0|26|78|0|
|viewer-filter-row-mercari.spec.ts|0|0|12|0|12|36|0|
|viewer-focus-trap.spec.ts|0|0|3|0|3|9|0|
|viewer-header-remove.spec.ts|0|0|13|0|13|39|0|
|viewer-inventory-mobile-filter.spec.ts|0|0|22|0|22|66|0|
|viewer-search-mercari.spec.ts|0|0|19|0|19|57|0|
|viewer-search-suggestions.spec.ts|0|0|10|0|10|30|0|
|viewer-top-compact.spec.ts|0|0|19|0|19|57|0|
|**合計**|46|0|222|4|272|733|83|

## 8. 試算（実行はしていない・提案ではなく数字）

- C の 222 test が 1 幅だけで足りる場合の実行回数: 666 → 222（差 444 回）。全体では 733 → 511。時間への換算は未確認（test ごとの所要時間のデータが無い）。
- C を 1 幅に絞ってよいかは PO・設計担当の判断。残る未確認: 4 節の「isMobile / hasTouch の影響」。

## 9. test ごとの表

列: spec:行（開始行）｜試験名｜最初の goto より前に幅を決め直すか（行）｜project・触る扱い・viewportSize・skip を読む行｜分類（備考）。
同じ spec:行が 2 回出る行は、360 と 390 の 2 幅ループで作られた別々の test（試験名に幅は付かない）。
「helper …(page)」は spec 内または import した関数経由。受信箱 spec は幅を決め直さず、helper 内（inbox-helpers.ts:94）で goto する。
読む行の列は `testInfo.project`・`projectWidth(`・`page.viewportSize()`・`isMobile`・`hasTouch`・`.tap(`・`touchscreen`・`test.skip` の grep（コメント行除外）。viewportSize() は読むだけで分岐しない場合もある。

| spec:行 | 試験名 | 幅を決め直すか(行) | project・触る扱いを読むか(行) | 分類 |
|---|---|---|---|---|
|app-update-notice.spec.ts:22|shows the white card at the top (full width on mobile, top-right on desktop) without overflow|25 helper openInboxList(page)|23,62,63,84|A 390と1280で別の判定(63,84行)。768はskip(23行)|
|drawer-inert-closed.spec.ts:110|B1: 開いた直後、閉じた .comp-drawer-panel が3枚あり、すべての inert が true（前提の固定）|111 page.setViewportSize(MOBILE)|なし|C 幅をspecが固定。3 projectで同一|
|drawer-inert-closed.spec.ts:129|B2: 外側を使い切るまで Tab を押しても、現在地が閉じたパネルの中に入らない（0回・かつ現在地は実際に動く）|130 page.setViewportSize(MOBILE)|なし|C 幅をspecが固定。3 projectで同一|
|drawer-inert-closed.spec.ts:162|B3: 絞り込みを開くと、開いた側の inert は false・その中の要素に Tab で入れる|163 page.setViewportSize(MOBILE)|なし|C 幅をspecが固定。3 projectで同一|
|inbox-baseline.spec.ts:128|A: 会話一覧|129 helper openInboxList(page)|なし|A 3幅で別のレイアウトを計測(project幅のまま)。assert弱い(測るだけ)|
|inbox-baseline.spec.ts:133|B: 会話を開いた状態|134 helper openInboxList(page)|なし|A 3幅で別のレイアウトを計測(project幅のまま)。assert弱い(測るだけ)|
|inbox-lead-merge.spec.ts:71|権限あり: 「ほかのリードとまとめる」がメニューに出る|72 helper openWithPermissions(page)|なし|A 開く手順が幅で3通り(59-65行)|
|inbox-lead-merge.spec.ts:76|権限なし（leads.delete が無い）: 項目が出ない|77 helper openWithPermissions(page)|なし|A 開く手順が幅で3通り(59-65行)|
|inbox-lead-merge.spec.ts:82|3手順の写真と、スマホ幅の高さ・はみ出しの測定|84 helper openWithPermissions(page)|83,88,103,117|A 開く手順が幅で3通り(59-65行)|
|inbox-single-column.spec.ts:94|スマホ: 一覧 → 会話 → 一覧 を切り替える|98 helper openInboxList(page)|95|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:130|スマホ: 上部のページ名バーが無く、下部タブバーで移動できる|133 helper openInboxList(page)|131|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:153|スマホ: 会話を開いている間は下部タブバーが隠れ、戻ると見える|157 helper openInboxList(page)|154,162|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:173|スマホ: 一覧ではヘッダーの操作行を出さず、絞り込みはヘッダーの右端に出る|176 helper openInboxList(page)|174|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:226|スマホ: 地が1色・左右対称・12px文字のコントラストが基準以上|229 helper openInboxList(page)|227|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:342|スマホ: 名前と本文に大きさと太さの段差がある|345 helper openInboxList(page)|343|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:421|スマホ: 主要な操作ボタンが44px以上|424 helper openInboxList(page)|422|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:483|スマホ: 検索欄の2つのボタンが別のアイコンで、管理は文言を出さない|486 helper openInboxList(page)|484|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:539|スマホ: 一覧の上にヘッダーが出て、検索欄が横幅いっぱいのピルになる|542 helper openInboxList(page)|540,548|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:643|スマホ: 一覧をスクロールしてもヘッダーが動かない|662 helper openInboxListWithConversations(page)|644,669|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:794|PC・タブレット: 一覧と会話が同時に見え、戻るボタンは出ない|797 helper openInboxList(page)|795|D 768と1280を分けるアプリ側の分岐(breakpoints.ts:20)の影響は未確認。スマホはskip|
|inbox-single-column.spec.ts:831|スマホ: 行を長押しするとメニューが出て、項目は3つ・文言と押す場所が仕様どおり|834 helper openInboxList(page)|832,860|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:876|スマホ: 長押ししただけでは会話が開かない（一覧のまま）|879 helper openInboxList(page)|877|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:889|スマホ: 普通のタップでは今までどおり会話が開く（退行していない）|892 helper openInboxList(page)|890|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:897|スマホ: 外側を押すとメニューが閉じる|900 helper openInboxList(page)|898|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:910|スマホ: 選択モードでは長押しでメニューが出ない|913 helper openInboxList(page)|911|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:922|スマホ: 「未読にする」を押すと mark-unread が呼ばれ、対象 lead id が渡る|926 helper installAuthBypass(page)|923|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:963|スマホ: メニューの左端が画面左から --space-3 の余白に出る（PO 指摘・右側だと押しづらい）|966 helper openInboxList(page)|964,992|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1011|スマホ: 行とメニューに user-select: none が指定されている（文字選択の抑止・実機確認は別途必要）|1014 helper openInboxList(page)|1012|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1056|スマホ: 会話を開くと帯が1本だけになり、各部品の寸法・配置が仕様どおり|1063 helper openInboxList(page)|1057,1059|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1133|スマホ: 「もっと」を押すと4項目（送信先の言語／テンプレート／FAQ／受信箱の設定）が出る|1136 helper openInboxList(page)|1134|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1158|スマホ: 「送信先の言語」を押すとシートが開き、選択肢が3つ・各44px以上・選ぶと閉じる|1161 helper openInboxList(page)|1159|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1193|PC・タブレット: スマホ用の会話ヘッダーは出ず、従来どおり操作行と言語の SelectControl が見える|1196 helper openInboxList(page)|1194|D 768と1280を分けるアプリ側の分岐(breakpoints.ts:20)の影響は未確認。スマホはskip|
|inbox-single-column.spec.ts:1221|スマホ: Discord 未連携のときは名前の下に表示が出て、高さ56pxのまま・ボタン群と重ならない|1224 helper openInboxListWithDiscordUnlinkedConversation(page)|1222|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1255|スマホ: Discord 連携済み（または他プラットフォーム）のときは名前だけで高さ56pxのまま|1260 helper openInboxList(page)|1256|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1288|スマホ: 「もっと」→「テンプレート」で /templates に移動し、「戻る」で元の会話に戻れる（行き止まりの解消）|1291 helper openInboxList(page)|1289|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1322|スマホ: 準備中ページは戻る矢印のぶんだけカードを上に詰める（PO 決定・B案）|1325 helper installAuthBypass(page)|1323|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1356|PC・タブレット: 準備中ページの戻る矢印は出さない（左のメニューで移動できるため）|1359 helper installAuthBypass(page)|1357|D 768と1280を分けるアプリ側の分岐(breakpoints.ts:20)の影響は未確認。スマホはskip|
|inbox-single-column.spec.ts:1365|スマホ: FAQ（もう一方の準備中ページ）でも「戻る」が効く|1371 helper openInboxList(page)|1366|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1385|スマホ: カルテ（顧客情報）ボタンの絵柄がクリップボードから別物に変わっている|1388 helper openInboxList(page)|1386|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1439|スマホ: カルテが画面全体になる（下部タブバーは会話を開いた時点で隠れている）|1442 helper openInboxList(page)|1440,1447|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1484|スマホ: 左上の戻る矢印が44px以上で、押すとカルテが閉じて会話に戻る|1487 helper openInboxList(page)|1485|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1509|スマホ: 固定の操作バー（karte-action-bar）が画面内に見えている|1515 helper openInboxListWithLeadStatus(page)|1510,1523|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1536|PC・タブレット: カルテは全画面にならない（従来どおり）|1539 helper openInboxList(page)|1537,1542,1556|A 768/1280で分岐(1536,1840): スマホはskip|
|inbox-single-column.spec.ts:1607|スマホ: カルテの帯に戻る矢印・顔写真・顧客名が並び、高さ56px・矢印44px以上|1610 helper openInboxList(page)|1608|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1646|スマホ: 「顧客ページを開く」がどこにも無い|1649 helper openInboxList(page)|1647|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1659|スマホ: 「商談化」を押すと中央にポップアップが出て、プルダウンには営業・リーダーだけが並ぶ|1662 helper openInboxListWithLeadStatusAndStaff(page)|1660|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1682|スマホ: 確定・閉じるが横並びで、確定がネイビー（--accent）・閉じるがグレーであること|1685 helper openInboxListWithLeadStatusAndStaff(page)|1683|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1719|スマホ: 確定を押すと PATCH /leads/5001 が status=negotiating・assigned_to付きで呼ばれ、ポップアップが閉じて段階バッジが更新される|1729 helper installAuthBypass(page)|1720|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1788|スマホ: ポップアップが画面の中央に出て、左右に余白がある（PO 決定・2026-10-15）|1791 helper openInboxListWithLeadStatusAndStaff(page)|1789,1800|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1822|スマホ: カルテの帯が画面の幅いっぱいにある（会話画面と同じ見え方）|1825 helper openInboxList(page)|1823,1832|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1840|PC・タブレット: カルテの帯は従来どおりで、顔写真・顧客名の重複表示が出ない|1843 helper openInboxList(page)|1841,1857|A 768/1280で分岐(1536,1840): スマホはskip|
|inbox-single-column.spec.ts:1872|スマホ: 入力欄に案内文が出ず、Enter で改行され送信されない|1876 helper installAuthBypass(page)|1873|A スマホのみ実行(他2幅skip)|
|inbox-single-column.spec.ts:1903|PC・タブレット: 案内文は今のまま出る|1910 helper openInboxList(page)|1904|D 768と1280を分けるアプリ側の分岐(breakpoints.ts:20)の影響は未確認。スマホはskip|
|inventory-mobile-baseline.spec.ts:169|360px: 一覧の計測|171 await gotoInventory(page, { width, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-mobile-baseline.spec.ts:169|390px: 一覧の計測|171 await gotoInventory(page, { width, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-mobile-baseline.spec.ts:321|360px: 詳細パネルの計測（原文1件・タブ無し）|323 await gotoInventory(page, { width, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-mobile-baseline.spec.ts:336|360px: 詳細パネルの計測（原文3件・タブ有り）|338 await gotoInventory(page, { width, height: 800, rawTexts: 3 |なし|C 幅をspecが固定。3 projectで同一|
|inventory-raw-text-mobile.spec.ts:24|375px: 各カードに原文ボタンが1つ・44x44以上（A1/A2）|25 await gotoInventory(page, { width: 375, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-raw-text-mobile.spec.ts:46|375px: 原文ボタンを押すと全画面のパネルが開き下部タブを覆う（A3/A4）|47 await gotoInventory(page, { width: 375, height: 800 }|59|C 幅をspecが固定。3 projectで同一|
|inventory-raw-text-mobile.spec.ts:98|1440px: 原文ボタンは出ない（A6）|99 await gotoInventory(page, { width: 1440, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:74|E1: タブの行（[role=tablist]）が無い／inventory-expiry-warning が詳細フィルタの外に無い|75 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:80|E3: inventory-tab-select と inventory-sort-menu の高さが48px以上で、両方 viewport の中にある|81 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:95|E4: inventory-tab-select の文字がいま選ばれている種別の名前（mock の表示名と一致）|96 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:101|E5: inventory-tab-select を押すとパネルが開き、行が「すべて」＋種別の数（4件）だけ並ぶ|102 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:111|E6: いま選ばれていない行を押すとパネルが閉じ、inventory-tab-select の文字がその名前に変わる|112 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:124|E7: すでに選ばれている行をもう一度押してもパネルが閉じる（K4）|125 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:138|E8: inventory-sort-menu を押すとパネルが開き行が4つ。「価格が安い順」を選ぶと閉じ文字が変わり、「既定」を選ぶと「並び替え」に戻る|139 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:161|E9: パネルの行の押せる高さが44px以上|162 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:174|E10: 「詳細フィルタ」を開くと、その中に inventory-expiry-warning があり、幅がパネルの内側に収まっている（折り返している）|175 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:191|E12: document と .mobile-content の横の超過が0|192 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:196|E13: .inventory-choice-row:hover の規則が @media (hover: hover) の中にある（sticky hover対策・K9）|197 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:242|F1: inventory-tab-select の中の種別の名前が切れていない（scrollWidth <= clientWidth）|243 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:256|F2: inventory-tab-select の中で種別の名前に使える余地が240px以上|257 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:275|F3: 並び替えに「価格が安い順」を選んだ状態でも種別の名前が切れない|276 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:294|F4: inventory-tab-select が1行を独り占めしている（y が inventory-sort-menu と異なる／幅が .inventory-toolbar と同じ／ラベルの左端が並び替えと揃う）|295 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:320|F5: 空振り防止。flex を 1 1 0 に戻すと種別の名前が切れる（scrollWidth > clientWidth）|321 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:340|E2: .inventory-toolbar の子が4つで、全部の右端が画面幅以下|341 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:352|E11: .inventory-toolbar の高さが180px以下（4行に折り返していないこと）|353 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:340|E2: .inventory-toolbar の子が4つで、全部の右端が画面幅以下|341 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:352|E11: .inventory-toolbar の高さが180px以下（4行に折り返していないこと）|353 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-series-sort-panel.spec.ts:363|E14: PC（幅1280px）はタブの行がある／inventory-sort-menu は select 要素／inventory-tab-select は無い／注記は .comp-tabs-bar__end の中にある|364 await gotoInventory(page, { width: PC_WIDTH, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:97|D1: .inventory-toolbar のすべての子要素の右端が画面幅以下（直す前は654pxで赤＝recon.md:25）|98 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:109|D2: 検索欄の幅が .inventory-toolbar の幅の95%以上|110 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:118|D3: 「並び替え」「詳細フィルタ」の高さが48px以上|119 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:129|D4: 「並び替え」「詳細フィルタ」が両方 viewport の中にある（直す前は詳細フィルタが画面外＝recon.md:25）|130 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:144|D5: 上部操作台に inventory-reset-sort と inventory-fresh-toggle が無い（直す前は両方上部に実在＝recon.md:22-23）|145 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:151|D6: 「詳細フィルタ」を押すとパネルが開き、中に inventory-fresh-check と inventory-reset-in-panel がある|152 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:159|D7: パネルの中の inventory-fresh-check の押せる高さが44px以上|160 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:170|D8: 「詳細フィルタ」の文字に数が入る（既定1以上）。24時間以内を切ると数が減る|171 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:184|D9: スマホでは .content-toolbar が無く .inventory-toolbar が1枚だけある（閲覧ページと同じ作り）|185 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:191|D10: .inventory-toolbar の高さが180px以下（4行に折り返していないこと・P5）|192 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:199|D11: document と .mobile-content の横の超過が0|200 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:97|D1: .inventory-toolbar のすべての子要素の右端が画面幅以下（直す前は654pxで赤＝recon.md:25）|98 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:109|D2: 検索欄の幅が .inventory-toolbar の幅の95%以上|110 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:118|D3: 「並び替え」「詳細フィルタ」の高さが48px以上|119 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:129|D4: 「並び替え」「詳細フィルタ」が両方 viewport の中にある（直す前は詳細フィルタが画面外＝recon.md:25）|130 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:144|D5: 上部操作台に inventory-reset-sort と inventory-fresh-toggle が無い（直す前は両方上部に実在＝recon.md:22-23）|145 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:151|D6: 「詳細フィルタ」を押すとパネルが開き、中に inventory-fresh-check と inventory-reset-in-panel がある|152 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:159|D7: パネルの中の inventory-fresh-check の押せる高さが44px以上|160 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:170|D8: 「詳細フィルタ」の文字に数が入る（既定1以上）。24時間以内を切ると数が減る|171 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:184|D9: スマホでは .content-toolbar が無く .inventory-toolbar が1枚だけある（閲覧ページと同じ作り）|185 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:191|D10: .inventory-toolbar の高さが180px以下（4行に折り返していないこと・P5）|192 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:199|D11: document と .mobile-content の横の超過が0|200 await gotoInventory(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|inventory-toolbar-mercari.spec.ts:208|D12: PC（幅1280px）は検索欄の幅・詳細フィルタの min-height / font-size・並びが変わっていない|209 await gotoInventory(page, { width: PC_WIDTH, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|popover-mold.spec.ts:81|B1（C1）スクロールしてから開くと押したボタンのすぐ下に出る|84 await gotoViewer(page, { width: 1280, height: 500 }|なし|C 幅をspecが固定。3 projectで同一|
|popover-mold.spec.ts:113|B2（C5）開いたまま動かすと付いてくる|114 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|popover-mold.spec.ts:146|B3（C10）PC で今までどおりの位置|147 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|popover-mold.spec.ts:175|B4（C4・C8）画面の中に収まる（1280px）|176 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|popover-mold.spec.ts:181|B4（C4・C8）画面の中に収まる（768px）|182 await gotoViewer(page, { width: 768, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|popover-mold.spec.ts:197|B6 既存の形が変わっていないこと（パネル幅400px以上・PC）|198 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:161|B1・B2・B3: 3つのボタンが枠なし。シリーズは単独の行、並び替え・絞り込みは同じ行で、44px以上・画面内、main の中の select は0件|162 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:199|B4・B5: シリーズを押すとパネルが開き題が「シリーズ」。行は44px以上で8行以上見える|200 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:227|B6・B7・B8: シリーズの行を選ぶと即閉じて一覧が絞られ、ボタンの文字が選んだ名前になり件数は入らない|228 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:253|B6b: すでに選ばれている行を押してもパネルが閉じる|254 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:276|B9: 並び替えパネルは4行（既定＋3択）。選ぶと即反映し、既定を選ぶと並びが既定に戻る|277 helper gotoViewerForSort(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:307|B10: パネルは Esc と ✕ で閉じる（スマホは全幅のため背景を押す余地が無い）|308 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:335|B11: 一覧の先頭カードの y が上限以内（MAX_TOP_Y。便4で128へ更新）|336 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:341|B12: 横はみ出しが0|342 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:161|B1・B2・B3: 3つのボタンが枠なし。シリーズは単独の行、並び替え・絞り込みは同じ行で、44px以上・画面内、main の中の select は0件|162 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:199|B4・B5: シリーズを押すとパネルが開き題が「シリーズ」。行は44px以上で8行以上見える|200 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:227|B6・B7・B8: シリーズの行を選ぶと即閉じて一覧が絞られ、ボタンの文字が選んだ名前になり件数は入らない|228 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:253|B6b: すでに選ばれている行を押してもパネルが閉じる|254 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:276|B9: 並び替えパネルは4行（既定＋3択）。選ぶと即反映し、既定を選ぶと並びが既定に戻る|277 helper gotoViewerForSort(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:307|B10: パネルは Esc と ✕ で閉じる（スマホは全幅のため背景を押す余地が無い）|308 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:335|B11: 一覧の先頭カードの y が上限以内（MAX_TOP_Y。便4で128へ更新）|336 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:341|B12: 横はみ出しが0|342 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-choice-sheet.spec.ts:349|B13: PCは今のまま（viewer-sort-menu は select のまま・タブが出る・viewer-tab-select は無い）|350 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:113|B1: 操作ボタン3つの高さが48pxちょうど|114 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:124|B2: 操作ボタン3つの文字が13.6px|125 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:134|B3: 山形2つの幅が16px|135 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:145|B4: 上部の検索欄の高さが48pxちょうど|146 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:154|B5: パネル内の候補を絞る検索欄の高さが48px|155 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:166|B6: 「決定する」の高さが48px|167 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:178|B7a: 既定の表示でシリーズ名が切れていない|179 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:189|B7b: 並び替えに最長の項目を選んだ後も、シリーズのラベル枠が1文字分以上|190 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:206|B8: 3つの高さ・配置（シリーズは単独の行・並び替えと絞り込みは同じ行・右端が画面幅以内・ページの横はみ出し無し）|207 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:113|B1: 操作ボタン3つの高さが48pxちょうど|114 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:124|B2: 操作ボタン3つの文字が13.6px|125 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:134|B3: 山形2つの幅が16px|135 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:145|B4: 上部の検索欄の高さが48pxちょうど|146 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:154|B5: パネル内の候補を絞る検索欄の高さが48px|155 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:166|B6: 「決定する」の高さが48px|167 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:178|B7a: 既定の表示でシリーズ名が切れていない|179 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:189|B7b: 並び替えに最長の項目を選んだ後も、シリーズのラベル枠が1文字分以上|190 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:206|B8: 3つの高さ・配置（シリーズは単独の行・並び替えと絞り込みは同じ行・右端が画面幅以内・ページの横はみ出し無し）|207 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:252|B7c: 長いシリーズ名は全部出るが、flex を 1 1 0 に戻すと切れる|253 helper gotoViewerWithLongSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:278|B7d: flex を 1 1 0 に戻したうえで山形も24pxにすると、シリーズ名が切れる|279 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-control-tap-size.spec.ts:296|B4b: PC幅（1280px）では上部の検索欄に field-h-tap が効かない|297 await gotoViewer(page, { width: PC_WIDTH, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:121|C1: 絞り込みパネルの幅が画面幅の83%±1px、左端xが画面幅の17%±1px|122 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:133|C2: シリーズ／並び替えのパネルは画面幅ちょうど（絞り込みだけ狭めたことの裏取り）|134 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:142|C3: 絞り込みが開いている間、オーバーレイの押せる領域が左に20px以上ある|143 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:160|C4: オーバーレイを押すと絞り込みパネルが閉じる（K2・今までは押す場所が無かった）|161 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:173|C5: 選択画面のチェック行の高さが61px以上・xがパネル左端と一致・幅がパネル幅と一致（直す前は赤=44px）|174 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:206|C6: 行の文字の左端が行の左から48px（直す前は赤=32px）|207 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:223|C7: 行の文字の大きさが14.4px（直す前は赤=13.6px）|224 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:235|C8: 行はどこを押しても選べる（文字の上・左48pxの枠の余白を押しても選択状態が変わる）|236 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:263|C9: 空振り防止 — 行を44pxに戻す／打ち消し幅(bleed)を0に戻すとC5の判定が落ちることを同じ検査の中で確かめる|266 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:305|C10: ページの横はみ出しが無い|306 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:313|C12: root の「24時間以内のみ」の行が変わっていない（4-6の歯止め・61pxになっていないこと）|316 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:332|C13: .comp-multiselect__option:hover の規則が (hover: hover) の中にある（sticky hover対策・K6）|335 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:377|C14: 絞り込みパネルの本文（.comp-drawer-body）に内部の横はみ出しが無い（root画面・提供者の選択画面の両方）|380 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:121|C1: 絞り込みパネルの幅が画面幅の83%±1px、左端xが画面幅の17%±1px|122 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:133|C2: シリーズ／並び替えのパネルは画面幅ちょうど（絞り込みだけ狭めたことの裏取り）|134 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:142|C3: 絞り込みが開いている間、オーバーレイの押せる領域が左に20px以上ある|143 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:160|C4: オーバーレイを押すと絞り込みパネルが閉じる（K2・今までは押す場所が無かった）|161 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:173|C5: 選択画面のチェック行の高さが61px以上・xがパネル左端と一致・幅がパネル幅と一致（直す前は赤=44px）|174 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:206|C6: 行の文字の左端が行の左から48px（直す前は赤=32px）|207 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:223|C7: 行の文字の大きさが14.4px（直す前は赤=13.6px）|224 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:235|C8: 行はどこを押しても選べる（文字の上・左48pxの枠の余白を押しても選択状態が変わる）|236 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:263|C9: 空振り防止 — 行を44pxに戻す／打ち消し幅(bleed)を0に戻すとC5の判定が落ちることを同じ検査の中で確かめる|266 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:305|C10: ページの横はみ出しが無い|306 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:313|C12: root の「24時間以内のみ」の行が変わっていない（4-6の歯止め・61pxになっていないこと）|316 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:332|C13: .comp-multiselect__option:hover の規則が (hover: hover) の中にある（sticky hover対策・K6）|335 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-panel-mercari.spec.ts:377|C14: 絞り込みパネルの本文（.comp-drawer-body）に内部の横はみ出しが無い（root画面・提供者の選択画面の両方）|380 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:47|B1: 提供者・コンディションの行の高さが53pxちょうど（直す前は赤=44px）|48 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:64|B2・B3: 行の左ラベル・右の現在値の文字が14.4px（直す前は赤=13.6px）|65 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:80|B4: 未選択のとき、提供者行の現在値が「指定しない」（直す前は赤=「すべて」）|81 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:89|B5: 0件→1件→2件で提供者行の文字が切り替わる（退行防止）|90 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:114|B5b: 選択画面の要約欄が未選択で「指定しない」・1行のまま（直す前は赤=「すべて」）|115 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:47|B1: 提供者・コンディションの行の高さが53pxちょうど（直す前は赤=44px）|48 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:64|B2・B3: 行の左ラベル・右の現在値の文字が14.4px（直す前は赤=13.6px）|65 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:80|B4: 未選択のとき、提供者行の現在値が「指定しない」（直す前は赤=「すべて」）|81 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:89|B5: 0件→1件→2件で提供者行の文字が切り替わる（退行防止）|90 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:114|B5b: 選択画面の要約欄が未選択で「指定しない」・1行のまま（直す前は赤=「すべて」）|115 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:130|B6: 提供者の浮かぶプルダウンのボタンに「指定しない」が出る（直す前は赤=「すべて」）|131 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-filter-row-mercari.spec.ts:142|B6: コンディションの浮かぶプルダウンのボタンにも「指定しない」が出る|143 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-focus-trap.spec.ts:190|B1: 候補にフォーカス→自動読み直しで消える→activeElement が <body> になる（前提の固定）|81 setViewportSize(MOBILE) in helper(76-81行,goto=107)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-focus-trap.spec.ts:202|B2: B1 の直後に Tab を押すと、パネル内の先頭（戻るボタン）へ連れ戻される（本題）|81 setViewportSize(MOBILE) in helper(76-81行,goto=107)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-focus-trap.spec.ts:222|B2': B1 の直後に Shift+Tab を押すと、パネル内の末尾（決定するボタン）へ連れ戻される|81 setViewportSize(MOBILE) in helper(76-81行,goto=107)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:64|C1: 一覧の先頭カードの y が204px以内|65 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:70|C2: スマホに .viewer-header が0件|71 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:75|C3・C4: 絞り込みを開くと開いているパネルの中に最終更新と言語がある|76 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:95|C5: viewer-lang を en にすると画面の文言が英語になる|96 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:105|C6・C18: ページの h1 は1件・文字は「在庫一覧」・見た目の幅は1px以下|106 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:115|C7: 横はみ出しが0|116 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:64|C1: 一覧の先頭カードの y が204px以内|65 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:70|C2: スマホに .viewer-header が0件|71 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:75|C3・C4: 絞り込みを開くと開いているパネルの中に最終更新と言語がある|76 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:95|C5: viewer-lang を en にすると画面の文言が英語になる|96 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:105|C6・C18: ページの h1 は1件・文字は「在庫一覧」・見た目の幅は1px以下|106 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:115|C7: 横はみ出しが0|116 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-header-remove.spec.ts:123|C8: PCは今のまま（.viewer-header が1件・その中に最終更新と言語が見える）|124 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:106|A1: 最初の画面（root）に4項目が収まる（スクロールせずに測る）|107 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:121|A2・A3・A14: 提供者の行を押すと選択画面になり、← で root に戻る。フォーカスも往復する|122 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:139|A4: コンディションの行がスクロールせずに画面内にある（便1 は 2024 だった）|140 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:149|A5・A6・A15: 選択画面の行が44px以上・画面内に収まり、8〜20件見える。浮かぶパネルは0件|150 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:177|A7・A9: 2件選ぶと一覧が絞られ、親の行に選んだ名前が出る（検索で絞っている間も生の値に化けない）|178 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:206|A8・A10・A17: 検索欄で候補を絞れる・0件表示・画面を離れると空に戻る|207 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:236|A11: 「決定する」を押すと最初の画面に戻り、選択は残っている|237 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:255|A12・A13: Esc で root に戻る（ドロワーは閉じない）。Tab / Shift+Tab は端で回り込む|256 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:280|A17: 選択画面のまま ✕ を押すとドロワーが閉じる。開き直すと最初の画面に戻り、検索欄が空になっている|281 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:298|コンディションでも A5・A7 が成り立つ（本便の主眼である A4 は別テストで確認済み）|299 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:106|A1: 最初の画面（root）に4項目が収まる（スクロールせずに測る）|107 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:121|A2・A3・A14: 提供者の行を押すと選択画面になり、← で root に戻る。フォーカスも往復する|122 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:139|A4: コンディションの行がスクロールせずに画面内にある（便1 は 2024 だった）|140 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:149|A5・A6・A15: 選択画面の行が44px以上・画面内に収まり、8〜20件見える。浮かぶパネルは0件|150 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:177|A7・A9: 2件選ぶと一覧が絞られ、親の行に選んだ名前が出る（検索で絞っている間も生の値に化けない）|178 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:206|A8・A10・A17: 検索欄で候補を絞れる・0件表示・画面を離れると空に戻る|207 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:236|A11: 「決定する」を押すと最初の画面に戻り、選択は残っている|237 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:255|A12・A13: Esc で root に戻る（ドロワーは閉じない）。Tab / Shift+Tab は端で回り込む|256 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:280|A17: 選択画面のまま ✕ を押すとドロワーが閉じる。開き直すと最初の画面に戻り、検索欄が空になっている|281 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:298|コンディションでも A5・A7 が成り立つ（本便の主眼である A4 は別テストで確認済み）|299 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:330|A18: PC は popover のまま。一覧の幅は400px以上|331 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-inventory-mobile-filter.spec.ts:345|A18: コンディションも PC では popover のまま|346 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:77|B1: 検索バーが48px・角丸24px以上・虫眼鏡が1つ|78 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:91|B2: 検索欄を押すと検索画面が開き、入力欄にフォーカスがある|92 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:99|B3: 検索画面で文字を打っても、一覧の件数が変わらない|100 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:107|B4: 確定すると画面が閉じ、一覧の件数が変わる（キーボードの検索キー＝Enter）|108 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:120|B5: 確定後、検索欄に「語」の札と✕が出る（✕は44px以上）|121 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:143|B6: 札の✕を押すと検索画面が開き、入力欄が空になり、件数は変わらない|144 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:161|B7: 開き直すと「最近使った語」にその語がある。押すとその語で絞られる|162 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:183|B8: 「最近使った語」の行が69px・文字の左端が64px・行の中に印が1つ|184 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:209|「すべて消す」で履歴が空になり、次に開いても最近使った語が出ない|210 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:77|B1: 検索バーが48px・角丸24px以上・虫眼鏡が1つ|78 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:91|B2: 検索欄を押すと検索画面が開き、入力欄にフォーカスがある|92 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:99|B3: 検索画面で文字を打っても、一覧の件数が変わらない|100 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:107|B4: 確定すると画面が閉じ、一覧の件数が変わる（キーボードの検索キー＝Enter）|108 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:120|B5: 確定後、検索欄に「語」の札と✕が出る（✕は44px以上）|121 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:143|B6: 札の✕を押すと検索画面が開き、入力欄が空になり、件数は変わらない|144 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:161|B7: 開き直すと「最近使った語」にその語がある。押すとその語で絞られる|162 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:183|B8: 「最近使った語」の行が69px・文字の左端が64px・行の中に印が1つ|184 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:209|「すべて消す」で履歴が空になり、次に開いても最近使った語が出ない|210 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-mercari.spec.ts:229|B9: PC幅（1280px）は打つたびに件数が変わり、検索画面は開かない|230 await gotoViewer(page, { width: PC_WIDTH, height: 800 }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:64|B1+B4: 文字を打つと候補が出て最近使った語は消える。行は69px・左64px・印1つ|65 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:89|B2: 候補を押すと検索画面が閉じ、件数が変わり、札にその語が出る|90 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:107|B3: 入力を空に戻すと候補が消えて最近使った語が戻る|108 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:120|B5: 当たらない語を打つと候補も最近使った語も出ない|121 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:132|B6: 確定した語がある状態で検索欄を押して開き直すと、入力に語が入ったまま候補が出る（最近使った語は出ない）|135 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:64|B1+B4: 文字を打つと候補が出て最近使った語は消える。行は69px・左64px・印1つ|65 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:89|B2: 候補を押すと検索画面が閉じ、件数が変わり、札にその語が出る|90 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:107|B3: 入力を空に戻すと候補が消えて最近使った語が戻る|108 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:120|B5: 当たらない語を打つと候補も最近使った語も出ない|121 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-search-suggestions.spec.ts:132|B6: 確定した語がある状態で検索欄を押して開き直すと、入力に語が入ったまま候補が出る（最近使った語は出ない）|135 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:97|A1: 一覧の先頭カードの y が上限以内（MAX_TOP_Y。便4で128へ更新）|98 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:103|A2・A3・A4: シリーズは単独の行、並び替え・絞り込みは同じ行に並び、検索欄も単独で1行|104 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:139|A5: スマホの上部に viewer-fresh-toggle が0件|140 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:144|A6: 絞り込み画面の先頭に viewer-fresh-check があり、高さ44px以上|145 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:163|A7: viewer-fresh-check を外すと一覧の件数が増える（24時間より古い行がある）|164 await gotoViewer(page, { width, height, fixtureOpts: { stale|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:179|A8: 開いた直後は viewer-fresh-check がオン|180 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:185|A9: 絞り込みボタンの文字が既定で「(1)」を含み、すべて外すと含まない|186 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:200|A10: シリーズを選ぶと一覧の件数が変わる|201 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:216|A11: 横はみ出しが0|217 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:97|A1: 一覧の先頭カードの y が上限以内（MAX_TOP_Y。便4で128へ更新）|98 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:103|A2・A3・A4: シリーズは単独の行、並び替え・絞り込みは同じ行に並び、検索欄も単独で1行|104 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:139|A5: スマホの上部に viewer-fresh-toggle が0件|140 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:144|A6: 絞り込み画面の先頭に viewer-fresh-check があり、高さ44px以上|145 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:163|A7: viewer-fresh-check を外すと一覧の件数が増える（24時間より古い行がある）|164 await gotoViewer(page, { width, height, fixtureOpts: { stale|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:179|A8: 開いた直後は viewer-fresh-check がオン|180 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:185|A9: 絞り込みボタンの文字が既定で「(1)」を含み、すべて外すと含まない|186 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:200|A10: シリーズを選ぶと一覧の件数が変わる|201 helper gotoViewerWithSeries(page)|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:216|A11: 横はみ出しが0|217 await gotoViewer(page, { width, height }|なし|C 幅をspecが固定。3 projectで同一|
|viewer-top-compact.spec.ts:224|A12: PCは今のまま（上部に viewer-fresh-toggle が居る・タブが出る・シリーズ選択は無い）|225 await gotoViewer(page, { width: 1280, height: 900 }|なし|C 幅をspecが固定。3 projectで同一|

DONE
