# 設計: 在庫表のタブを表にくっつけ、閲覧ページと GAS もアプリと同じタブにする

- 状態: 設計案（Opus）。PO 依頼: 2026-10-20（下の原文）。
- 現在地: docs/handoff/inventory-tabs-attach-table/recon.md
- 対象 ADR: ADR-1019 項8（閲覧ページはアプリと同じ金型）、ADR-1030（タブは中分類で絞る）、ADR-144（自作タブ禁止・金型を使う）、ADR-027（UI 文字列は t() 経由・ja/en 同一キー）。

## 1. 目的（PO の言葉）
- 「アプリのPCの在庫表だけどポケモンとかの絞り込みのタブがテーブルに連結されてないから修正できる？」
- 「アプリの在庫表はその他だけ白い枠がついているからプルダウンを残しつつ透明にできる？」
- 「このアプリのタブと同じ仕様に閲覧用のアプリページとGASも修正してほしい」

## 2. 変更前 → 変更後（PC 幅が対象。閲覧ページ・GAS のスマホは変えない。アプリのタブ行はスマホでも同じものを出している（`frontend/src/pages/inventory/InventoryPage.tsx:527-568` は isMobile で分けていない）ため、アプリのスマホのタブ行も金型の見た目になる。スマホのカード表示には表がないので「くっつける」は効かない）
| | 変更前 | 変更後 |
|---|---|---|
| アプリ在庫表のタブと表 | タブ行と表の間に隙間（margin と 2px 下線） | タブ行の下線がそのまま表の上の線になる（隙間 0、表の上の角丸 0） |
| アプリの「その他」 | 白い枠・白い背景のプルダウン | 枠と背景が透明で、文字と ▽ だけのタブと同じ見た目。選んでいる間は他のタブの選択中と同じ青文字＋青い下線 |
| アプリのタブの部品 | 生ボタン（ui-allow 例外） | Tabs 金型（underline／md）。例外コメントを外す |
| 閲覧ページのタブ | 見出しの下・検索欄の上。全シリーズを件数の丸つきで横に並べる（はみ出す） | 検索欄2段の下・表の真上にくっつける。「すべて／ポケモン／ワンピース／ドラゴンボール」＋透明の「その他」プルダウン（残りのシリーズ）。件数は出さない |
| GAS 在庫一覧のタブ | 表の直前。全シリーズを横に並べる | アプリと同じ5つ（すべて／ポケモン／ワンピース／ドラゴンボール／その他▼）。表にくっつける |

## 3. 変更内容（file:line は origin/main 38613d7d7）
### 3-1. Tabs 金型に「横に置く部品」と「表にくっつける」を足す
`frontend/src/components/Tabs.tsx` の TabsProps に2つ足す（既存の使い方 19 か所は何も渡さないので今と同じ描画のまま）:
```ts
/** タブの右隣に置く部品（例: 「その他」プルダウン）。タブ行の中に並ぶ */
extra?: ReactNode;
/** タブ行の右端に置く部品（例: 注記） */
end?: ReactNode;
```
- extra も end も無いとき: 今と同じ（role="tablist" の div 1つ）。
- どちらかがあるとき: 外側に `<div className="comp-tabs-bar comp-tabs-bar--{variant}">` を置き、その中に今の role="tablist" の div（タブボタンだけ）、`<div className="comp-tabs-bar__extra">{extra}</div>`、`<div className="comp-tabs-bar__end">{end}</div>` を並べる。className は外側に付ける。
- `frontend/src/components/Tabs.css` に足す（色・余白はトークンだけ）:
  - `.comp-tabs-bar { display:flex; align-items:flex-end; gap: var(--space-2) }`
  - `.comp-tabs-bar--underline { border-bottom: 1px solid var(--border) }`（灰色の線は外側の1本だけ）
  - `.comp-tabs-bar--underline > .comp-tabs--underline { border-bottom: none; flex: 0 1 auto; min-width: 0 }`
  - `.comp-tabs-bar--underline .comp-tabs--underline .comp-tabs__tab { margin-bottom: 0 }`（`frontend/src/components/Tabs.css:86-89` の `margin-bottom:-1px` は内側の線に重ねるためのもの。bar の中では内側の線が無いので 0 にし、内側の `overflow-x:auto` で下線が切れないようにする。この規則は :86-89 より後に置く）
  - `.comp-tabs-bar__extra { flex-shrink:0; display:flex; align-items:flex-end }`
  - `.comp-tabs-bar__end { margin-left:auto; flex-shrink:0; align-self:center }`
  - stylelint の no-descending-specificity に止められたら、bar の規則を `frontend/src/components/Tabs.css:111-113` の hover 規則より前へ動かす（`check:stylelint` で確かめる）。
  - 縦位置の決め: タブボタンと「その他」はどちらも高さ `var(--comp-tab-h-md)` で下端をそろえ、選択中の青い下線（2px）は灰色の線（1px）のすぐ上に乗る。注記だけは行の縦中央。

### 3-2. DataTable 金型に「上をタブにくっつける」を足す
`frontend/src/components/DataTable.tsx` に `attachedTop?: boolean` を足す。true のとき、表の外枠を描く `.comp-table`（`frontend/src/components/DataTable.css:12-18`。`.comp-table-frame` は width だけで枠を描かない :196-198）の要素、つまり `wrapperCls`（`frontend/src/components/DataTable.tsx:214-219`）にだけ `comp-table--attached-top` を足す。カード表示（スマホ）のときは付けない。`frontend/src/components/DataTable.css` に `.comp-table--attached-top { border-top: none; border-top-left-radius: 0; border-top-right-radius: 0 }`。上の線はタブ行の下線（3-1）が受け持つ。前例: `frontend/src/pages/buyback-prices/BuybackPricesPage.module.css:40-50`（ここは今回触らない）。

### 3-3. Select 金型に「タブの見た目」の種類を足す
`frontend/src/components/Select.tsx:18` の SelectVariant に `"tab"` を足す。`frontend/src/components/FormField.css` の末尾（既存の variant 規則より後）に、次の順で足す:
1. `.comp-select__control.comp-select--tab`:
   - 枠: `border-top-color / border-left-color / border-right-color: transparent`（個別指定）、`border-bottom: var(--comp-tab-underline-w) solid transparent`、`border-radius: 0`、`background-color: transparent`（`background` の一括指定は使わない。▽ の背景画像を消さないため）。
   - 大きさ・文字: `height: var(--comp-tab-h-md)`、`min-height: 0`（スマホで `frontend/src/components/FormField.css:494-500` が掛ける min-height を打ち消す。karte/header/tabbar と同じ :201,222,240）、`padding-top: 0; padding-bottom: 0; padding-left: var(--comp-tab-px-md); padding-right: var(--space-5)`（▽ の分。`frontend/src/components/FormField.css:72-79` の standard と同じ値）、`font-size: var(--font-sm)`、`color: var(--text-secondary)`。
2. `.comp-select__control.comp-select--tab:hover`: `color: var(--accent)`。
3. `.comp-select__control.comp-select--tab:focus`: `box-shadow: none; border-top-color / border-left-color / border-right-color: transparent`（border-bottom には触らない。選んだ直後にフォーカスが残っても選択中の下線を消さないため）。
4. `.comp-select__control.comp-select--tab:focus-visible`: `outline: 2px solid var(--accent); outline-offset: -2px`。
5. `.comp-select__control.comp-select--tab.comp-select--tab-active`（詳細度 (0,3,0) で 1〜3 より強い）: `color: var(--accent); border-bottom-color: var(--accent); font-weight: var(--font-weight-semi)`（Tabs.css の underline の選択中と同じ）。
- 選択中の付け方: variant="tab" で、渡された value が空文字でないとき Select が `comp-select--tab-active` を付ける。
- 既存の tabbar（Inbox 用）は変えない。

### 3-4. Storybook に見本を足す（金型の登録）
- `frontend/src/components/Tabs.stories.tsx` に「その他プルダウンと注記つき・表にくっつけた」見本（Tabs extra/end ＋ Select variant="tab" ＋ DataTable attachedTop）。
- `frontend/src/components/Select.stories.tsx` に variant="tab"（未選択・選択中）。

### 3-5. アプリ在庫表
`frontend/src/pages/inventory/InventoryPage.tsx`:
- ファイルの上の方に `const MAIN_TCG_CODES: readonly string[] = ["pokemon_booster_box", "one_piece", "dragon_ball"];` を置く（`as const` にしない。`.includes(string)` で型エラーになるため）。今の直書き4か所（:529 は "all" を先頭に足した形、:539・:548 は3つ、:542 は "all" を後ろに足した形）を `MAIN_TCG_CODES` で表す（"all" を含む2か所は `["all", ...MAIN_TCG_CODES]` 相当か `code === "all" || MAIN_TCG_CODES.includes(code)`）。
- :525-571 の `<div className="tabs" …>` 一式を Tabs 金型に置き換える:
  - `variant="underline" size="md"`、items は `[{key:"all", label:t("common.all")}, ...MAIN_TCG_CODES.map(code => ({key: code, label: name_ja ?? code}))]`（ラベルの決め方は :530-531 のまま）。activeKey は、activeTab が3つか all のときはそれ、それ以外（その他を選んでいる）ときは `""`（どのタブも選択中にしない）。onChange は今と同じ `setActiveTab(key); setPage(1)`。
  - extra: 今の SelectControl（:539-554）に `variant="tab"` を付け、`size="sm"` は外す。value・onChange・option・0件なら出さない条件は今のまま。
  - end: 今の注記 `<p data-testid="inventory-expiry-warning">`（:555-567）。中身・testid は変えない。margin-left:auto は end 側が持つので p のインラインから外す。
  - `ui-allow` の例外コメント（:526）を消す。
  - スマホでもこのタブ行を出す（今と同じ）。
- DataTable（:570〜）に `attachedTop={!isMobile}` 相当を付ける（カード表示のときは DataTable 側でも付けない）。
- テスト `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx:96` の `screen.queryByRole('tab')` は、引き出しの要素の中（within）だけを見るように直す。
- 検索欄とタブの間の読込表示（:518-523）は変えない。

### 3-6. 閲覧ページ
- `frontend/src/pages/viewer/viewerFilter.ts`:
  - `export const MAIN_SERIES: readonly string[] = ["ポケモン", "ワンピース", "ドラゴンボール"];` を足す。直前に `/* eslint-disable local/no-japanese-literal -- DB の type_master.name_ja と照合する値（画面文言ではない）。アプリ在庫表の MAIN_TCG_CODES の name_ja */` と、直後に `/* eslint-enable local/no-japanese-literal */`（前例 `frontend/src/constants/icons.tsx:167`）。コメントに「閲覧ページの行には code が無いので名前で合わせる（recon 参照）」と書く。テストファイルで日本語のシリーズ名を使う所も同じ形の disable を付ける（lint-staged は `--max-warnings=0`、`frontend/package.json:56`）。
  - `export function otherSeries(rows: ViewerRow[]): string[]` を足す: series が空でなく MAIN_SERIES に無いものを重複なしで名前の順（既存の compareText）に並べる。
  - 絞り込み（:85 `r.series !== f.tab`）は変えない（タブの key がシリーズ名なのでそのまま効く）。
  - `seriesTabs` はスマホのセレクトが使うので残す。
- `frontend/src/pages/viewer/InventoryView.tsx`:
  - PC の Tabs（:226-236）を、ContentToolbar の後・DataTable（:295）の直前へ動かす。中身: `variant="underline" size="md"`、items は `[{key: TAB_ALL, label: t("viewer.tabAll")}, ...MAIN_SERIES.map(s => ({key: s, label: s}))]`（件数 count は渡さない）。activeKey は tab が TAB_ALL か MAIN_SERIES のときはそれ、それ以外は `""`。
  - extra: `otherSeries(data.rows)` が1つ以上のとき、`SelectControl variant="tab"`、`aria-label={t("viewer.tabOther")}`、`data-testid="viewer-tab-other"`、value は tab が「その他」側のときその名前・それ以外は `""`、先頭 option `{value:"", label:t("viewer.tabOther")}`、続けて各シリーズ。onChange は値が空でなければ `reset(setTab)(値)`。
  - DataTable に `attachedTop`（PC のときだけ。スマホは今のまま）。
  - スマホ（:215-224 のセレクト、件数つき）は変えない。
- `frontend/src/locales/viewer/ja.json` と `frontend/src/locales/viewer/en.json`: `viewer.tabAll` の ja を「全て」→「すべて」（アプリの common.all に合わせる。en は今のまま。このキーはスマホのセレクト `frontend/src/pages/viewer/InventoryView.tsx:222` でも使うので、スマホの表記も「すべて」になる）、`viewer.tabOther` を足す（ja「その他」、en「Other」＝アプリの `frontend/src/locales/en.json:1500` と同じ）。

### 3-7. GAS 在庫一覧（別リポジトリ shingo-ops/tcg-client-viewer。反映は PO の `!`）
- 土台: 作業の最初に Opus がテスト版・本番版を別々の空ディレクトリへ `clasp pull`（読み取り）し、`~/CC報告ファイル-keep/inventory-toolbar-two-rows/gas/` の写しとの差を見る。上部2段の版（PO の反映待ち）をまだ反映していなければ、その写しを土台にして今回の変更を重ねる（1回の反映で両方入る）。差に説明できないものがあれば止めて PO に聞く。
- 新しい作業場所 `~/CC報告ファイル-keep/inventory-tabs-attach-table/gas/` に土台を写して直す（Sonnet。clasp は使わない）。
- 土台の確定（2026-10-20 実施済み）: PO が上部2段の版を反映した（テスト版30・本番版20）。Opus が clasp pull し、`~/CC報告ファイル-keep/inventory-toolbar-two-rows/gas/stage`・`prod_stage` と差 0 を確認。新しい作業場所 `~/CC報告ファイル-keep/inventory-tabs-attach-table/gas/stage`・`prod_stage` に写し済み。反映台本はテスト30・本番20を期待版にする。
- index.html の JS（:1243-1275 `buildSeriesTabs`）: 「すべて」＋ `MAIN_SERIES`（閲覧ページと同じ3つの名前、同じコメント）を固定で並べ、残りのシリーズ（名前の順）を透明の「その他」セレクトに入れる。残りが0ならセレクトを出さない。選択中の見た目・絞り込みは 3-6 と同じ考え方。「全て」の表記（スマホのセレクト :1269 を含む）は「すべて」にそろえる。
- index.html の CSS（:773-794）: 3-1 の comp-tabs-bar、3-2 の attached-top、3-3 の tab の見た目を、同じトークン名で写す（GAS 側のトークン定義に無い名前があれば、アプリの tokens.css の値を GAS のトークン定義へ足して使う。色の直書きはしない）。タブ行の下線が表の上の線になるよう、表の外枠の上の線と上の角丸を消す。
- スマホ（<768px のセレクト）は変えない。今 `.series-tabs` に掛けているスマホでの非表示を、新しく足す外側の箱（タブ行全体）にも掛ける。
- 反映の台本（テスト・本番とも push → version → redeploy）を Sonnet が作り、PO が `!` で実行する。

## 4. 触らない範囲
- 閲覧ページ・GAS のスマホの表示。例外: 「全て」→「すべて」の表記はスマホのセレクトにも及ぶ。アプリのタブ行はスマホでも出ているので金型の見た目になる（§2）。
- 既定で選ばれるタブ（アプリはポケモン、閲覧ページ・GAS はすべて）。
- タブの絞り込みの中身・API・DB・migration・deploy.yml・本番 scripts/。
- Tabs を使う他の 19 か所の見た目、Select の他の variant（tabbar を含む）、買取価格ページの前例 CSS。
- 検索欄とタブの間の読込表示。

## 5. 代替案
- A（採用）: 金型に extra/end・attachedTop・variant="tab" を足し、アプリと閲覧ページが同じ金型で同じ見た目を作る。GAS は同じトークン名で写す。
- B: 閲覧ページと GAS の行に work_code を足してコードで分ける。シート「在庫集計」の列・作り置き・型・GAS の列許可を全部変える大きな配線変更になるので今回は採らない。名前で合わせる弱点（名前を画面で変えると3つのタブに入らなくなる）は、外れたシリーズが「その他」に入るだけで行は消えない（§6）。
- C: アプリのページだけの CSS で隙間を消す。閲覧ページと GAS で同じものを作り直すことになり、金型の決まり（ADR-144・ADR-1019 項8）に反するので採らない。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| type_master の名前（ポケモン等）が画面で変えられ、閲覧ページ・GAS のタブと合わなくなる | そのシリーズは「その他」に入るだけで見えなくはならない。名前を変えたら MAIN_SERIES（閲覧ページ・GAS）も直す、とコメントと §9 に書く |
| 「その他」の並びがアプリ（sort_order 順）と閲覧ページ・GAS（名前の順）で違う | 閲覧ページ・GAS は sort_order を持たない。並びの違いは PO 報告に書く |
| 閲覧ページの PC から件数が消える | PO の「アプリと同じ仕様に」に従う（アプリは件数なし）。PO 報告に書き、戻すなら count を渡すだけ |
| アプリのタブの文字が今（font-base）より少し小さくなる（金型 md は font-sm） | 3つの画面を金型 md にそろえる。PO 報告に書く |
| 既定で選ばれるタブがアプリ（ポケモン）と閲覧ページ・GAS（すべて）で違う | 今回は変えない（§4）。PO 報告に書く |
| アプリのスマホのタブ行も見た目が変わる（金型 md・下線の形） | §2 に書き、K5b で確かめる。PO 報告に書く |
| 既存テスト rowdrawer :96 が画面全体の role=tab を見ている | 引き出しの中だけを見るように直す（意図は「引き出しにタブが無い」） |
| GAS の写しが実物と違う | 3-7 の最初に clasp pull で照合する |

## 7. 受入条件
|基準|検証方法|
|---|---|
| K1 アプリ PC: タブ行の下線と表の上の線が重なり、隙間が 0 | Storybook の見本（3-4）を Playwright で開き、getBoundingClientRect で ①タブ行の下端と表の上端の差が 1px 以内 ②選択中タブの下端（青い下線の下）とタブ行の内側の下端（灰色の線の上）の差が 1px 以内 ③「その他」の下端と選択中タブの下端の差が 1px 以内。vitest: InventoryPage の DataTable に attachedTop が渡る |
| K2 「その他」が透明で ▽ が残る | Storybook 見本で、その他の背景色が透明（rgba(0, 0, 0, 0)）・左右上の枠の色が透明・背景画像（▽）が none でない。選択中は文字色が var(--accent) の値 |
| K3 閲覧ページ PC: すべて／ポケモン／ワンピース／ドラゴンボール＋その他、件数なし、表の真上 | vitest（InventoryView）: タブ4つの名前、件数の丸が無い、その他の option が MAIN_SERIES 以外のシリーズ（名前順）、タブ行が DataTable の直前の兄弟 |
| K4 閲覧ページ: その他で選んだシリーズだけが出る | vitest: その他で「ホロライブ」を選ぶと series がホロライブの行だけ。otherSeries の単体テスト |
| K5 閲覧ページのスマホは変わらない（表記「すべて」以外） | vitest: スマホ幅で今のセレクト（件数つき）が出る、タブ行が出ない |
| K5b アプリのスマホ: タブ行が金型で出て、カード表示に attached のクラスが付かない | vitest: スマホ幅で role=tablist が出る、`.comp-table--attached-top` が無い |
| K6 既存の動きは同じ | vitest 全体・build・lint・check:all・Storybook build が合格。InventoryPage のタブ切替・その他選択で work_code が今と同じに送られる |
| K7 GAS: 5つのタブで表にくっつく | 反映後に clasp pull し、写しと差 0。pull した index.html を grep して MAIN_SERIES・comp-tabs-bar・attached-top・tab の見た目のクラスがあること。PO がシートの画面で目視 |
| K8 本番に出る | デプロイ後、配信 JS/CSS に comp-table--attached-top と comp-select--tab が入っている（curl）。PO が画面で目視（再読み込みしてから） |
| K9 CI 全合格 | PR の必須チェック |

## 8. 外部・過去事例の参照と我々への応用
- 社内の前例: 買取価格ページ（`frontend/src/pages/buyback-prices/BuybackPricesPage.module.css:40-50`）が Tabs の下に表を置き、表の上の角丸を0にしてつなげている。今回はこれを金型（DataTable の attachedTop）に上げ、ページごとの CSS を増やさない。
- 外部事例は不要。見た目の小さな変更で、社内の金型と前例だけで決まるため。

## 9. 維持の仕組み
- 守り手: K1〜K6 の vitest と Storybook の見本（CI の frontend テスト・Storybook build で毎回走る）。`scripts/check-ui-governance.js` の「自作タブ禁止」（ADR-144）で、アプリのタブが生ボタンに戻ることを防ぐ（ui-allow を外すため）。
- 「主な3つ」の決めは、アプリは `frontend/src/pages/inventory/InventoryPage.tsx` の MAIN_TCG_CODES、閲覧ページは `frontend/src/pages/viewer/viewerFilter.ts` の MAIN_SERIES、GAS は index.html の MAIN_SERIES。互いにコメントで指し合う。type_master の名前を変えたときは MAIN_SERIES の2か所も直す。
- 戻し方: アプリと閲覧ページはこの PR を Revert。GAS はひとつ前の版へ redeploy（台本に版番号を書く）。
