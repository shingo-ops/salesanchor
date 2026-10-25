# design: 「シリーズ」「並び替え」を枠なしボタン＋パネル選択にする（便5）

> この文書は何か（1行）: 閲覧ページのスマホで、シリーズと並び替えを「箱に入ったプルダウン」から「枠のない文字のボタン → 押すと右からパネルが出て1つ選ぶ」形（メルカリと同じ）に変える便の設計。

**日付**: 2026-10-25
**親（あるべき姿）**: `docs/specs/design-system/visual-language/README.md`
**recon**: `docs/handoff/viewer-choice-sheet/recon.md`
**お手本の実測**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41`・`:43`
**前便**: 便3 `docs/handoff/viewer-top-compact/design.md`（PR #4752・本番反映済み）／便2 `docs/handoff/viewer-filter-subscreen/design.md`（PR #4740）
**対象ADR**: ADR-1019（閲覧ページ）／ADR-144（UI 金型ガバナンス）／ADR-140（タップ領域44px）／ADR-067（トークン参照のみ）／ADR-027（文言は t() 経由）／ADR-1014（並びの既定）

## ① 区分：A（見た目と操作の変更）

| 項目 | 内容 |
|---|---|
| PO 指示（原文・2026-10-25） | 「ポケモンなどの絞り込みと並び替えの絞り込み機能のプルダウンがでかすぎて見づらい、修正できる？メルカリみたいに」 |
| PO 判断（同日） | 選択肢を提示して **「両方（メルカリの形へ）」を受領**＝①押す前は枠なしの文字ボタン ②押した後は OS 標準プルダウンではなく自分たちのパネル |
| 金型の新設 | **しない**。`Button variant="ghost"`・`RadioControl`・`Drawer` の**既存3つの組み合わせ**で作る（recon §3）。ADR-144 の「金型が無い場合の手順」（`docs/adr/ADR-144-ui-component-governance.md:60-65`）に入らないため PO 許可待ちは発生しない |
| 金型への props 追加 | **しない**（便1・便2 と違い、今回は金型に手を入れない） |

## ② KGI（PO が実機で○×を判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | 「シリーズ」「並び替え」の**箱（枠）が消える** | 3つとも枠のない文字だけになっている（絞り込みも揃える） |
| K2 | 押したときに **OS 標準の長い一覧が出ない** | 押すと右から自分たちのパネルが出る（絞り込みと同じ見た目） |
| K3 | パネルの中で**1つ選ぶと即反映して閉じる** | 行を押した瞬間にパネルが閉じ、一覧が変わる |
| K4 | ボタンの文字で**いま何が選ばれているか分かる** | シリーズは「ポケモン」等、並び替えは選んだ名前（既定のときは「並び替え」） |
| K5 | 件数の表示が**邪魔をしない** | ボタンには件数を出さない。件数はパネルの各行に出る |
| K6 | **並び替えを既定に戻せる** | パネルの先頭に「発売日が新しい順（既定）」があり、選ぶと元の並びに戻る |
| K7 | PC は**今のまま** | パソコンの画面は1か所も変わらない |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 合否 |
|---|---|---|
| 枠の有無 | 3つのボタンの `backgroundColor` と `borderColor` | **どちらも透明**（`rgba(0, 0, 0, 0)`） |
| ネイティブのプルダウン | スマホ幅で `main` の中の `select` 要素の数 | **0 件** |
| 1行に並ぶ | 3つの `y` が同じ | 一致 |
| タップ目標 | 3つの高さ／パネルの行の高さ | すべて **>= 44** |
| 右端 | 一番右の `x + width` | 画面幅以内 |
| 一度に見える行数 | パネルの表示領域 ÷ 行の高さ | **>= 8** |
| 上部の高さ | 先頭カードの y（スクロールせず） | **192 以内**（便3 の値を維持） |
| 閲覧ページの JS | `frontend/scripts/check-viewer-bundle.js` | **300KB 以内**（便3 実測258.0KB・アイコンを足さないので増えない見込み） |

## ④ 設計（How）

### 4-1. スマホの操作台＝枠なしのボタン3つ（`frontend/src/pages/viewer/InventoryView.tsx:429-453`）

| 要素 | 変更前 | 変更後 |
|---|---|---|
| シリーズ | `SelectControl`（`:429-440`） | `Button variant="ghost" size="sm"`・`layoutClassName="viewer-toolbar__series"`・`data-testid="viewer-tab-select"`（**変えない**）・`aria-label={t("viewer.tabSelect")}`。中身は `<span className="viewer-toolbar__label">{現在のシリーズ名}</span>` ＋ `<ChevronRight className="viewer-toolbar__caret" aria-hidden />` |
| 並び替え | `sortMenu`（`:366-390`）をスマホ・PC で共用 | **スマホ用に新しい変数 `sortTrigger` を作る**。`Button variant="ghost" size="sm"`・`layoutClassName="viewer-toolbar__fixed"`・`data-testid="viewer-sort-menu"`（**変えない**）・中身は現在の並びの名前＋同じ `caret`。**`sortMenu`（`<select>`）は PC 側（`:486`）に残す＝PC 不変** |
| 絞り込み | `Button variant="secondary"`（`:442-453`） | `variant="ghost"` に変えるだけ（size・testId・文言・件数は不変） |

- 現在のシリーズ名 ＝ `tab === TAB_ALL ? t("viewer.tabAll") : tab`（`TAB_ALL` は `"all"`。`frontend/src/pages/viewer/viewerFilter.ts:10`）。**件数は付けない**（recon §7 の幅計算）。
- 現在の並びの名前 ＝ `sortMenuValue`（`:331`）が `SORT_MENU_VALUES`（`frontend/src/pages/viewer/viewerFilter.ts:15`）に含まれればその選択肢の文言、含まれなければ `t("viewer.sort.placeholder")`（＝「並び替え」）。
- 押したときの動き ＝ `openChoicePanel("series")` / `openChoicePanel("sort")`（4-2）。

### 4-2. パネル＝2つ目の `Drawer`（既存の絞り込みの仕組みには触らない）

```
type ChoicePanel = "none" | "series" | "sort";
const [choicePanel, setChoicePanel] = useState<ChoicePanel>("none");
const openChoicePanel = (p: "series" | "sort") => setChoicePanel(p);
const closeChoicePanel = () => setChoicePanel("none");
```

- **`drawerOpen`・`filterView`・`handleFilterEscape`・`filterDrawerTitle/BackProps/Footer`（`:79`・`:139-166`・`:307-330`）には1行も触らない**。
  便2 の「Esc だけ一段戻る」「開くときに初期化」の仕組みを壊さないため、**別の `Drawer` インスタンス**を足す。
- `<Drawer open={choicePanel !== "none"} onClose={closeChoicePanel} title={choicePanel === "sort" ? t("viewer.sort.placeholder") : t("viewer.tabSelect")}>`
  - **`onBack`・`backLabel`・`footer`・`onEscape` は渡さない**。操作台から直接開くので「戻り先」が無く、✕・背景クリック・Esc はすべて「閉じる」でよい
    （便2 の教訓＝読み上げ名「閉じる」と動きを食い違わせない）。
  - スマホのみ描く（`isMobile &&`。既存の絞り込みドロワーと同じ条件・`:557`）。
- 中身は `<div className="viewer-choice-list">` に行を並べる。行は共通の描き方を1つ作って両方で使う:

```
<label className="viewer-choice-row" key={value}>
  <RadioControl
    name={choicePanel === "sort" ? "viewer-sort-choice" : "viewer-series-choice"}
    value={value}
    checked={checked}
    data-testid={testId}
    onChange={() => { pick(); closeChoicePanel(); }}
  />
  <span className="viewer-choice-row__label">{label}</span>
</label>
```

| パネル | 行 | testId | 選んだときの処理 |
|---|---|---|---|
| シリーズ | 1行目「すべて (総件数)」 | `viewer-series-option-all` | `reset(setTab)(TAB_ALL)` |
| シリーズ | 2行目以降 `seriesTabs(data.rows)` の各件「名前 (件数)」 | `viewer-series-option-<名前>` | `reset(setTab)(名前)` |
| 並び替え | 1行目「発売日が新しい順（既定）」 | `viewer-sort-option-default` | `setSortKey(DEFAULT_SORT_KEY)` ＋ `setSortDir(DEFAULT_SORT_DIR)` ＋ `setPage(1)` |
| 並び替え | 2〜4行目 `SORT_MENU_VALUES` の3択 | `viewer-sort-option-<値>` | `setSortKey(k)` ＋ `setSortDir(d)` ＋ `setPage(1)` |

- **並び替えの1行目は必須**。いまプルダウンの空欄が担っている「既定に戻す」操作（`:374-383`）を失わないため（recon §2）。
- 文言は**新キー1つだけ**: `viewer.sort.default` ＝「発売日が新しい順（既定）」／en 「Newest release date (default)」。ほかは既存キーを使い回す。

### 4-3. 選んだ瞬間に反映する（「決定する」は付けない）

お手本の並び替えは**選んだ瞬間に反映**（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41` の `sort_menu`）。
1つだけ選ぶ操作に確定ボタンは不要で、タップ数も1回少ない。
**複数選べる絞り込み（便2）は「決定する」のまま**＝「1つ選ぶ＝即時／複数選ぶ＝決定する」で使い分ける（お手本も同じ使い分け）。
PO が「決定する」に揃えたい場合は、`Drawer` に `footer` を渡すだけで戻せる（この便の中で独立した1点）。

### 4-4. CSS（`frontend/src/pages/viewer/viewer.css` に追加・ADR-067 で var() のみ）

| クラス | 指定 | 理由 |
|---|---|---|
| `.viewer-toolbar__label` | `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` | 長いシリーズ名を `…` で切る（ボタンの中の `span` なので `<select>` と違い確実に効く） |
| `.viewer-toolbar__caret` | `transform: rotate(90deg); flex-shrink: 0;` | **下向きの山形アイコンを足さずに** `ChevronRight` を回して使う（recon §3・JS 300KB 上限） |
| `.viewer-choice-list` | `display: flex; flex-direction: column;` | 行を縦に並べる |
| `.viewer-choice-row` | `display: flex; align-items: center; gap: var(--space-2); width: 100%; min-height: var(--size-icon-btn-lg); padding: var(--space-1) var(--space-2); font-size: var(--font-sm); color: var(--text-primary); cursor: pointer;` | 44px 以上（ADR-140）。便2・便3 の選択肢の行と**同じ見え方**にそろえる（値は同じトークン） |
| `.viewer-choice-row:hover` | `background: var(--bg-hover);` | 押せることが分かる |

既存の `.viewer-toolbar > .viewer-toolbar__series`（`frontend/src/pages/viewer/viewer.css:37-48`・`flex: 1 1 0; min-width: 0`）は**そのまま使う**。
ただし `Button` には `layoutClassName` で渡す（`className` は型で受け付けない。`frontend/src/components/Button.tsx:38`）。

### 4-5. 触らないもの

PC（1280px）の上部・`ContentToolbar`・`Tabs`／金型ファイル（`Button`・`RadioControl`・`Drawer`・`MultiSelect`・`Select`）／
絞り込みドロワーの中身と状態機械／`Popover` 金型（便2 C2 の宿題のまま）／アプリ側 `/inventory`／バックエンド・DB・`.github/`。

## ⑤ Acceptance Criteria

**測り方の共通の決まり**: `scrollIntoView` を使わずに測る（便2 の教訓＝流用すると常に真になる）。スマホは 360・390 の両方。

| # | 基準 | 検証方法 |
|---|---|---|
| B1 | 3つのボタンの背景と枠が**透明**（`rgba(0, 0, 0, 0)`） | 新 spec（`getComputedStyle`） |
| B2 | 3つの `y` が同じ（1行に並ぶ）・高さ **44px 以上**・右端が画面幅以内 | 新 spec |
| B3 | スマホの `main` の中に `select` が **0 件** | 新 spec |
| B4 | シリーズを押すと**パネルが開き**、題が「シリーズ」 | 新 spec |
| B5 | パネルの行が **44px 以上**で、**一度に8行以上**見える | 新 spec |
| B6 | シリーズの行を選ぶと**パネルが閉じ**、一覧の件数が変わる | 新 spec |
| B7 | ボタンの文字が選んだシリーズ名になる（押す前と後で変わる） | 新 spec |
| B8 | シリーズのボタンの文字に**件数が入っていない**（`(` を含まない） | 新 spec |
| B9 | 並び替えのパネルが**4行**（既定＋3択）・「既定」を選ぶと並びが既定に戻る | 新 spec |
| B6b | **すでに選ばれている行**を押してもパネルが閉じる（審査 R1） | 新 spec |
| B10 | パネルは **Esc と ✕** で閉じる。スマホは `Drawer` が全幅（`frontend/src/components/Drawer.css:114-118`）で**背景を押せる場所が無い**ため、閉じる手段はこの2つ（パネル幅＝画面幅を測って固定する）。CI 1回目の実測で判明し、当初の「背景クリックでも閉じる」から訂正 | 新 spec |
| B11 | 上部の高さ（先頭カードの y）が **192 以内**を保つ | 新 spec |
| B12 | 横はみ出しが 0 | 新 spec |
| B13 | PC（1280px）は不変＝`viewer-sort-menu` が `select` のまま・タブが出る・`viewer-tab-select` が無い | 新 spec |
| B14 | 便2 の絞り込み副画面（A1〜A18）が壊れていない | 既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` |
| B15 | 便3 の寸法検査が通る（A10 は新しい操作手順に書き換える） | 既存 `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` |
| B16 | 単体テストが通る（スマホのシリーズ・並び替えの経路を新しい形に書き換え） | `frontend/src/pages/viewer/InventoryView.test.tsx` |
| B17 | ja/en の辞書のキー数が一致（`viewer.sort.default` を両方に） | `cd frontend && npm run check:all` |
| B18 | 閲覧ページの JS が 300KB 以内 | `frontend/scripts/check-viewer-bundle.js` |
| B19 | 型検査が通る | `cd frontend && npx tsc --noEmit` |
| B20 | 手元検査が通る（警告0で pre-commit を通過） | `cd frontend && npm run check:all` ＋ `npx eslint --max-warnings=0 <変更ファイル>` |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/pages/viewer/InventoryView.tsx` | 操作台の3ボタン・`choicePanel` 状態・2つ目の `Drawer`・行の描き方 |
| `frontend/src/pages/viewer/viewer.css` | 4-4 の5クラス |
| `frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json` | `viewer.sort.default` の1キー |
| `frontend/src/pages/viewer/InventoryView.test.tsx` | スマホのシリーズ・並び替えの経路を書き換え（B16） |
| `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts` | **新設**（B1〜B13） |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | A10 の操作手順だけ書き換え（B15） |
| `docs/handoff/viewer-choice-sheet/recon.md`・`design.md` | 新規 |
| `.claude-pipeline/active-work.d/release-viewer-choice-sheet.md` | 台帳 |

## ⑦ 戻し方

この PR を revert するだけ。**金型に手を入れないので他画面への影響は原理的に無い**（変更は閲覧ページの4ファイルと検査のみ）。

## ⑧ 削除するファイル

無し（既存ファイルの行の書き換えはある。PR 本文の「削除するファイル:」に列挙する）。

## ⑨ 外部・過去事例の参照と我々への応用

| 事例 | 我々への応用 |
|---|---|
| メルカリ（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41`・`:43`） | 3行目は**枠線のないボタン**で「並び替え」「絞り込み」が並ぶ。本便の3ボタンはこの形。並び替えは**選んだ瞬間に反映**（4-3） |
| メルカリ（同 `:30`） | 「パネルの上にさらに小さなパネルを浮かせる形は存在しない」＝ネイティブのプルダウンも浮かぶ層。**パネルで選ぶ形にすれば便1 の重なり事故が原理的に起きない** |
| 便2（`docs/handoff/viewer-filter-subscreen/design.md`） | 「右から出るパネルで選ぶ」形と、✕・Esc・背景クリックの扱い。**今回は戻り先が無いので3経路すべて「閉じる」に統一**（便2 は親画面があるので Esc だけ分けた） |
| 便3（`docs/handoff/viewer-top-compact/design.md`） | 操作台が1行に収まる CSS（`flex: 1 1 0; min-width: 0`）をそのまま使う。寸法は CI の spec で固定する |
| 受信箱の `Sheet` 金型（`frontend/src/components/Sheet.tsx:1-20`） | 「下から出す」形は既に金型がある。閲覧ページは便2 で PO が「右から」を承認済みなので**使わない**（形を混ぜない） |

## ⑩ 弊害・トレードオフ

- **文字が小さくなる**（`size="sm"` ＝ 12px）。既にある「絞り込み」ボタンと同じ大きさに揃える判断で、
  お手本（16.3dp）よりは小さい。48px 行・16px 文字への底上げは ⑫ D2 として別便に分ける（上部の高さ基準 192px を同時に直す必要があるため）。
- **シリーズを選ぶのに1タップ増える**（プルダウンは押してその場で選べた）。代わりに OS 標準の長い一覧が出なくなり、
  44px の行・件数つきで選べる。
- **シリーズが43件あるとパネルは縦に長くなる**（43×44＝約1892px のスクロール）。便2 の提供者と同じ状況だが、
  本便では**候補を絞る検索欄を付けない**（1つ選ぶだけなので）。長すぎると PO が感じたら ⑫ D1 で足す。
- ボタンの文字から件数が消えるため、「いま何件か」はパネルを開くか一覧の下の「全 N 件」を見ることになる。
- **スマホではパネルを閉じる手段が ✕ と Esc だけ**（全幅で背景が無いため）。便1・便2 と同じ条件で、本便で悪化させてはいない。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts`（CI の集約ジョブ `visual-language` で毎 PR 走る。`frontend/playwright.config.ts:63-77` の `testMatch` が `visual-language/` 配下に限るため、**ここに置かないと1本も走らない**）

| 守ること | 関所 | 外すと |
|---|---|---|
| 3つのボタンに枠が戻らない | 上記 spec（B1） | 赤 |
| ネイティブのプルダウンが戻らない | 上記 spec（B3） | 赤 |
| 1行に並ぶ・44px・画面内 | 上記 spec（B2） | 赤 |
| パネルで選べて即反映・閉じる | 上記 spec（B4〜B9） | 赤 |
| 閉じる3経路 | 上記 spec（B10） | 赤 |
| 上部192px を保つ | 上記 spec（B11）＋ `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | 赤 |
| PC が今のまま | 上記 spec（B13） | 赤 |
| 便2 の絞り込みが壊れない | `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | 赤 |
| 閲覧ページの JS が 300KB 以内 | `frontend/scripts/check-viewer-bundle.js` | 赤 |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| D1 | シリーズのパネルに**候補を絞る検索欄**を足すか（43件で長いと感じるか） | PO の使用感次第 |
| D2 | 48px 行・16px 文字への底上げ（お手本と同じ）。上部の高さ基準（192px）も同時に直す | 別便 |
| D3 | **ヘッダーを丸ごと消す（便4）**＝上部 192px → 約146px。PO 決定済み・未着手 | `docs/handoff/viewer-header-remove/`（recon 済み） |
| D4 | 便2 からの持ち越し: C2（`Popover` 金型の2欠陥）・C8（フォーカスが `<body>` に落ちる） | そのまま |
| D5 | **閉じた `Drawer` の中身が Tab で辿れる・読み上げに乗る**（`frontend/src/components/Drawer.css:37-40` が `translateX(100%)` だけで、`visibility`/`inert` を使っていない）。本便でパネルを1つ増やしたため、閉じているときに余分な行（シリーズ最大43行）が Tab の経路に入る。**便2 の C8 と同根の金型側の話**で、直すと35ファイルに効くため別便 | 新規に起票（本便では直さない） |
