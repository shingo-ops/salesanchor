# design: スマホの在庫カードから原文を見られるようにする（便1）

> この文書は何か（1行）: スマホ（767px 以下）の在庫一覧のカードに「原文」ボタンを置き、押すと詳細を全画面で開けるようにする便の設計。

**PO 決定（2026-10-21）**: ①スマホで在庫の原文が見られない問題に着手する（3件のうち1件目）②開くきっかけは**カードに「原文」ボタン**（カード全体を押す案は不採用）③入れ物は**全画面**（受信箱のカルテと同じ見え方）。

## ① KGI（PO が画面で ○× を一義に判定できる粒度）

| # | 画面で確かめること | ○× の基準 |
|---|---|---|
| K1 | スマホ幅（375px）の在庫一覧で、各カードに「原文」のボタンが1つ出る | 出る／押せる大きさが 44x44 以上 |
| K2 | そのボタンを押すと詳細が**画面全体**に出る | 上端から下端まで覆い、下部のタブも隠れる |
| K3 | カードの他の場所（商品名・数量など）を押しても何も開かない | 開かない（誤タップで開かない） |
| K4 | 閉じると元の一覧に戻る | 戻る／一覧の位置が飛ばない |
| K5 | パソコン幅（768px 以上）は今と変わらない | 行クリックで開く・カードのボタンは出ない |

### KPI（機械で測る）

| 指標 | 測り方 | 合格 |
|---|---|---|
| ボタンの数（スマホ） | e2e 375px で `[data-testid^="inventory-raw-text-"]` を数える | 表示行数と同数 |
| ボタンの大きさ | e2e 375px で `boundingBox()` | 幅・高さとも 44 以上 |
| 全画面 | e2e 375px でパネルの `boundingBox()` を viewport と比較 | 上下左右すべて画面と一致 |
| 覆えているか | e2e 375px で `document.elementFromPoint(下部タブの中心)` | 返るのはパネル側の要素（タブではない） |
| ボタンの数（PC） | e2e 1440px で同じセレクタを数える | 0 |
| カードのはみ出し | 既存 `frontend/tests-e2e/inventory-table-layout.spec.ts` の 375px 検査 | 横スクロールなし（現状維持） |

## ② 現在地（recon の要点。引用は `docs/handoff/inventory-mobile-raw-text/recon.md` に全件）

| 事実 | 意味 |
|---|---|
| 詳細は `frontend/src/features/inventory/InventoryRowDrawer.tsx` が `Drawer` 金型で出している | 入れ物は既存。原文タブ・解析タブの中身は作り直さない |
| `Drawer` はスマホ幅で `width: 100%`、`top: 0`・`height: 100dvh`・`z-index: var(--z-drawer)`(301) | **すでに全画面**。全画面化のための新しい部品は要らない |
| `frontend/src/pages/inventory/InventoryPage.tsx` が行クリックをスマホで無効にしている | 原文に到達できない原因。ボタンを足して到達させる |
| `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx` の F2b が「スマホでは誰も開けない」を固定している | 意図が変わるので**書き換える**（削除ではない） |
| 前便の「触らない範囲」に `docs/handoff/inventory-row-drawer/design.md:39`「スマホのカード表示（`mobileCards`）からの開閉。PC の表のクリックだけを対象にする」 | スマホ無効化は**禁止ではなく範囲外**だった＝本便は素直な続き |
| `frontend/src/components/DataTable.tsx` のカード表示は `mobileHidden`・`mobileOrder` で列を出し分け、**セル内のボタンでは行クリックが発火しない** | ボタンはセルの中に置くのが素直。押し間違いで行クリックが起きない |
| 列の指定に「PC で隠す」はない（`mobileHidden`／`mobileOrder`／`mobileLabel` のみ） | 列の配列を `isMobile` で組み替える（金型は変えない） |
| `Button` 金型は `size="lg"` ＋ `iconOnly` で 44px（`--size-icon-btn-lg`） | 独自の寸法指定は書かない |
| アイコンの唯一の置き場は `frontend/src/constants/icons.tsx` | 新しい SVG は描かず、既存の絵柄を公開グループに足して使う |

## ③ 設計（How）

### 3-1. スマホのときだけ「原文」列を1本足す

- `frontend/src/features/inventory/inventoryColumns.tsx` に列定義を1本追加する（`key: "rawText"`）。
  - `header` は空（カード表示では `mobileLabel` も付けない＝ラベル行を増やさない）
  - `renderCell` で `Button`（`size="lg"` ＋ `iconOnly`）を描く。`data-testid={`inventory-raw-text-${row.id}`}`
  - 読み上げ名は i18n キー（3-5）から取る
- `frontend/src/pages/inventory/InventoryPage.tsx` の `columns` の `useMemo` で、**`isMobile` のときだけ**この列を足す（PC は列数が変わらない＝PC の見た目は1画素も動かない）。`useMemo` の依存に `isMobile` を足す。

### 3-2. 押すと詳細を開く

- ボタンの `onClick` で既存の `setDrawerRow(row)` を呼ぶ（state・API・パネルの中身はすべて既存のまま）。
- **行クリックは今のままスマホで無効**にする（`onRowClick={!isMobile ? ... : undefined}` を変えない）。PO 決定②のとおり、開くのはボタンだけ。

### 3-3. 全画面は既存の指定で達成する（部品を変えない）

- `Drawer` のスマホ幅の指定（`width: 100%`／`height: 100dvh`／`z-index: 301`）がそのまま全画面になる。**`Drawer` と `Sheet` の既定は変えない**（スマホ用の上書きを金型の既定に入れると、アプリ全体の全ドロワーに波及する。先例＝ポップアップのスマホ用上書きを撤回した便〈93ファイルに影響〉）。
- 下部のタブを覆えているかは**測って確かめる**（KPI の `elementFromPoint`）。覆えていない場合に限り、在庫の呼び出し側で覆うための指定を足す（金型の既定は触らない）。その判断は実装中に実測して design に追記する。

**実測結果（2026-10-21・実装時）**: この worktree の実行環境（Termux/proot-distro、`ubuntu26.04-arm64`）では `npx playwright install chromium` が
`ERROR: Playwright does not support chromium on ubuntu26.04-arm64` で失敗し、代替の Chromium/Chrome 実行体もシステムに無い（`find / -iname "*chromium*" -o -iname "*chrome*"` で実行ファイルを確認できず）。そのため `document.elementFromPoint` を使う A3・A4（と R1 のカード高さ before/after）の実測は、**本便の実装時には未確認**のまま残る。

- z-index の数値比較（`Drawer` 301 > `.mobile-tabbar` 100・両方 `position: fixed` で body 直下の同じスタッキングコンテキスト）からは覆えている可能性が高いが、recon（§8「未確認」）の指摘どおり数値比較だけでは確定しない。
- 判断: 実測できない以上、「覆えていない場合に限り呼び出し側で対処する」の分岐を実装時点では選べない。**推測で対処を入れない**＝金型（`Drawer`/`Sheet`）の既定にも呼び出し側（`InventoryRowDrawer.tsx`・`InventoryPage.tsx`）にも、タブを覆うための上書きは追加しない。
- 代わりに、新規 e2e `frontend/tests-e2e/inventory-raw-text-mobile.spec.ts` に A1〜A4・A6 の検査（375px でのボタン数・44px・全画面の `boundingBox()`・`elementFromPoint`、1440px でボタン0個）をすべて書いた。Playwright が動く環境（GitHub Actions ubuntu-latest 等）で CI が走った時点でこの判定が確定する。CI が赤になった場合は、金型の既定を変えずに呼び出し側だけで対処する別便を立てる（この節の方針は変えない）。
- R1（カードの高さ before/after の実測）も同じ理由で未確認。既存 `inventory-table-layout.spec.ts` の 375px 検査（カードのはみ出し・枚数）は本便でも変更せず再利用しているため、はみ出しの回帰は CI で検出できる。高さの具体的な px 差分は CI 実行後に別途記録する。

### 3-4. タブと権限は既存のまま

- 解析タブ／原文タブの出し分け（権限による分岐）は既存の実装をそのまま使う。スマホのための別扱いはしない。

### 3-5. i18n（ADR-027・ja/en で同じキー）

- ボタンの読み上げ名のキーを1つ追加し、`frontend/src/locales/ja.json` と `en.json` の両方に入れる（片方だけだと `check:i18n-missing-keys` が赤）。

### 3-6. 閉じ方

- `Drawer` の既存の閉じ方（閉じるボタン・背景・ESC）をそのまま使う。閉じたあと一覧の位置が保たれることを K4 で確かめる。

## ④ リスクと対策

| # | リスク | 対策 | 検証方法 |
|---|---|---|---|
| R1 | カードに要素が増えて縦に伸び、1画面に入る件数が減る | ボタンは1行（アイコンのみ・44px） | 375px の既存はみ出し検査＋カードの高さを実測して before/after を記録 |
| R2 | 詳細が下部のタブを覆わない（タブが前面に残る） | 覆えていなければ呼び出し側で対処（金型の既定は変えない） | `elementFromPoint` で下部タブの中心を調べる |
| R3 | 誤タップで詳細が開く | 行クリックはスマホで無効のまま・ボタンだけで開く | ユニットでカード本体のクリックで API が呼ばれないことを固定 |
| R4 | PC 側に影響が出る | 列は `isMobile` のときだけ足す | 1440px でボタン0個・既存の PC 側テストが緑 |
| R5 | 既存テスト F2b の意図が変わったのに気づかれない | F2b を「行クリックでは開かない／原文ボタンでは開く」に書き換える | 書き換え後のテスト名に理由を残す |
| R6 | 閲覧ページ・GAS 在庫一覧との差が開く | 本便は**アプリのスマホだけ**が対象。閲覧ページ・GAS は対象外と明記（下記 ⑨） | ADR-1014 の改訂に対象画面を明記 |

## ⑤ Acceptance Criteria

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 375px で各カードに原文ボタンが1つ出る | e2e（新規） |
| A2 | ボタンは 44x44 以上 | e2e（新規・`boundingBox()`） |
| A3 | 押すと詳細が画面全体に出る | e2e（新規・`boundingBox()` を viewport と比較） |
| A4 | 下部のタブが覆われている | e2e（新規・`elementFromPoint`） |
| A5 | カード本体を押しても開かない | ユニット（`InventoryPage.rowdrawer.test.tsx` の F2b 書き換え） |
| A6 | 1440px でボタンが0個・PC の行クリックは今のまま開く | e2e（新規）＋既存 F1/F2 |
| A7 | 375px でカードが横にはみ出さない | 既存 `inventory-table-layout.spec.ts` の 375px 検査 |
| A8 | ja/en のキー数が一致 | `npm run check:i18n-missing-keys` |
| A9 | 金型の規則違反なし（生 select/input/checkbox/radio・自作タブ） | `scripts/check-ui-governance.js` |
| A10 | 手元検査が通る | `npm run check:all` ＋ `npx tsc --noEmit`（`check:all` に型検査は含まれないため別に流す） |
| A11 | 実機（SC-51G）でボタンを押して原文が読める | 実機で撮影して記録 |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/features/inventory/inventoryColumns.tsx` | 原文ボタンの列を1本追加 |
| `frontend/src/pages/inventory/InventoryPage.tsx` | `isMobile` のときだけその列を足す |
| `frontend/src/constants/icons.tsx` | 既存の絵柄を公開グループに1行足す（新しい SVG は描かない） |
| `frontend/src/locales/ja.json`／`en.json` | ボタンの読み上げ名を1キー追加 |
| `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx` | F2b を書き換え・ボタンで開くテストを追加 |
| `frontend/tests-e2e/`（既存の在庫 spec か新規） | A1〜A4・A6 の検査を追加 |
| `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md` | 改訂として追記（対象はアプリのスマホのみ） |
| `docs/handoff/inventory-mobile-raw-text/` | recon・design・審査記録 |

## ⑦ 戻し方

| 段階 | 戻し方 |
|---|---|
| ボタンだけ止める | `InventoryPage.tsx` で列を足す分岐を外す（列定義は残っても無害） |
| 全部戻す | この PR を revert（DB もサーバも触らないため、戻しても残骸は出ない） |

## ⑧ 削除するファイル

なし。

## ⑨ 触らない範囲（明示）

- **お客様向け閲覧ページ（viewer）と GAS 在庫一覧**。原文は社内向けの情報なので対象外。`viewerColumns.tsx` は触らない＝GAS の写しを直す必要もない。
- `Drawer`／`Sheet` 金型の既定の見た目。
- 行クリックの挙動（PC は今のまま開く／スマホは今のまま開かない）。
- 詳細パネルの中身（解析タブ・原文タブ・権限の出し分け・API）。

## ⑩ 外部・過去事例の参照と我々への応用

| 事例 | 我々への応用 |
|---|---|
| 受信箱のカルテをスマホで全画面にした便（`docs/handoff/` の受信箱の設計カード） | 全画面にすると前後関係（z-index）で操作が奪われることがある。`elementFromPoint` で「狙いの要素の真上に別要素が無い」ことを検査する手法をそのまま借りる |
| ポップアップのスマホ用上書きを撤回した便 | 金型の**既定**をスマホ用に上書きすると、アプリ全体（93ファイル）に波及する。だから本便は呼び出し側で足す |
| スマホの押しどころを 44px 以上にした便 | `Button` 金型の `size="lg"` ＋ `iconOnly` で 44px になる（独自寸法を書かない） |

## ⑪ 維持の仕組み（CI の関所）

守り手: `frontend/tests-e2e/inventory-raw-text-mobile.spec.ts`（375px/1440px の検査本体）。ほかに `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx`・`npm run check:i18n-missing-keys`・`scripts/check-ui-governance.js`・`frontend/tests-e2e/inventory-table-layout.spec.ts` が下表の各行を受け持つ。

| 守ること | 関所 | 外すと |
|---|---|---|
| スマホでボタンが出て全画面で開く | 新規 e2e（375px） | 赤 |
| PC にボタンが出ない | 新規 e2e（1440px） | 赤 |
| カード本体では開かない | `InventoryPage.rowdrawer.test.tsx` | 赤 |
| ja/en のキー一致 | `check:i18n-missing-keys` | 赤 |
| 金型の規則 | `check-ui-governance.js` | 赤 |
| カードのはみ出し | `inventory-table-layout.spec.ts`（既存） | 赤 |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| C1 | 便2: スマホの上部の操作の整理（1段に何を出し、何を絞り込みの中に置くか） | PO 着手承認済み・設計未着手 |
| C2 | 便3: スマホの商品名の見せ方（折り返しのままか・PC と同じ「…」＋全文の見せ方にそろえるか） | PO 着手承認済み・設計未着手 |
| C3 | GAS 在庫一覧に未反映の1件（最安・在庫最多の塗りの角丸＝ADR-1014 改訂19(4)） | PC 側の宿題として残っている |
