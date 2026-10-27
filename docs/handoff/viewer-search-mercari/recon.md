# recon: 検索欄をお手本と同じ作りにする（便12a）

> この文書は何か（1行）: 閲覧ページ（/viewer/）の検索欄を、お手本（メルカリ）と同じ
> 「押すと検索の画面に移り、確定してはじめて一覧が絞られる」作りにするための現物調査。

**土台**: `release/viewer-search-mercari`（`origin/main` = 4f3a6e471＝便11 #4821 を含む）／調査日 2026-10-27
**対象**: `frontend/src/pages/viewer/InventoryView.tsx`（アプリの `/inventory` とは別コード。ADR-1019）

## 1. お手本（実機で測った一次情報・2026-10-27 23:44〜23:45）

**測り方**: 実機の ADB で状態を3つに切り分け、`uiautomator dump` の要素と
`dumpsys input_method` の `mInputShown` を機械で読んだ（スクショ頼みにしない）。

| 状態 | やったこと | 候補の行(`search_hint_item`) | 入力欄 | キーボード | 画面に出るもの |
|---|---|---|---|---|---|
| A | ホーム（何もしない） | 0件 | 無し | false | 検索欄は「商品をさがす」 |
| B | **検索欄をタップしただけ** | **0件** | 空・カーソル有 | **true** | **「検索履歴」の一覧**＋丸ボタン「カテゴリー」「ブランド」＋左に「←」 |
| C | **1文字打った** | **6件** | "p" | true | **一覧が履歴から候補に入れ替わる**＋入力欄の右端に**丸い✕が出現** |

**＝「タップで画面が変わる」「打つと一覧が履歴→候補に切り替わる」の2段構え**。
（初版の調査で「タップすると候補が出る」と書いたのは誤り。タップ直後は履歴。PO の指摘で測り直した）

### 寸法（dp。この端末は 1dp = ブラウザの 1px = 実画素3px）

| 何 | 実測 |
|---|---|
| 検索バー | **304×48dp**（結果画面では x=48..352、検索画面では x=48..340＝右にカメラの印がある分だけ狭い） |
| バーの中の並び | 左に虫眼鏡 → 文字 → **丸い✕（文字があるときだけ出る）** |
| 「←」 | 24dp（押せる範囲は 48×48dp）・バーの左 |
| 履歴の見出し「検索履歴」 | 文字 **19.7dp箱**・左から16dp |
| 履歴の行 | **68.7dpピッチ**・文字は**左から64dp**（左の丸い印が48dp分を占める） |
| 候補の行 | **68.7dp**・画面の全幅（x=0..360）・文字は左から64dp・右端に「→」 |
| 候補の文字 | 主 **17.7dp箱**（実体≒14.8）／補足 **16.3dp箱**（実体≒13.6）。2段になる候補がある |
| 結果画面の札 | 語が「**ポケモン ✕**」の小さな札になる。札 ≒84×28dp・✕の押せる範囲は48×48dp |
| キーボードの確定キー | **虫眼鏡（検索）** |

**文字の読み替え規則**（便10 で確立・`docs/handoff/viewer-control-tap-size/recon.md`）:
お手本の「文字○dp」は Android の文字の箱の高さで、実体は約1.2で割る。
17.7→**14.8dp**（最近傍の既存トークンは `--font-base` 14.4px）／16.3→**13.6dp**（`--font-sm`）／19.7→**16.4dp**。

## 1b. 操作ごとの実測（2026-10-28 00:10〜00:30・ADB で1手ずつ切り分け）

**測り方**: メルカリアプリを ADB で開き、**1手ごとに** `uiautomator dump`（要素と座標）と
`dumpsys input_method` の `mInputShown`（キーボードの有無）を読む。スクショの目視に頼らない。

| # | 操作 | 測れた結果 |
|---|---|---|
| E1 | ホームの検索欄をタップ | 検索画面へ。入力は**空**・キーボード true・見出し**「検索履歴」**・候補(`search_hint_item`)は**0件**。丸ボタン「カテゴリー」「ブランド」が48dp |
| E2 | 履歴の行を押す | **その語で検索が走り結果画面へ**。`search_bar` に語＋`削除`（48×48dp）。キーボード false。一覧は187dpから |
| E3 | 結果画面の**札の✕**を押す | **語だけ消えて入力待ち**（キーボード true・バーは案内文に戻る）。**一覧は前の結果のまま**（いいね9件が残る）＝**全件には戻らない** |
| E4 | そのまま打つ | 候補11件が出て結果は隠れる。このとき入力は `search_bar` 側 |
| E5 | バー右端の**丸い✕** | 打っていた文字が全消し・候補が消え・**結果画面に戻る**（結果は前のまま） |
| E8 | 文字＋キーボードの検索キー（Enter） | 確定。結果画面に戻りキーボード false。**語が札になる**（語の幅に合わせて伸びる。例「psa」は10dp幅、✕は48×48dp） |
| E9 | 結果画面のバーを押す | **語が入ったまま入力状態**になり、**その語の候補**が出る（履歴ではない） |
| E10 | 履歴を見る | 確定した語が**先頭に積まれる**。行は**68.7dp**・文字は左から64dp・**行に♡(48dp)と⋮(48dp)**。**語＋そのときの絞り込み条件**を1件として覚える（2段の行＝補足は14dp箱）。別節「保存した検索条件」もある |
| E11-12 | 後片付け | 測定で足した語を⋮→削除で消し、元の履歴（6件）に戻したことを確認 |

**この表で訂正できた思い込み2件**:
1. 「検索欄を押すと候補が出る」→ **誤り**。押しただけでは**履歴**（候補は打ってから）。
2. 「札の✕で全件に戻る」→ **誤り**。**語を消して入力待ちにするだけ**で一覧は動かない。

**未確認（推測で埋めない）**: 履歴の上限件数（観測できたのは6件で、上限に達していない）／
候補の行の右端「→」を押したときの挙動／空のまま確定したときの挙動。

## 2. いまの閲覧ページの現物

### 2-1. 検索欄（`frontend/src/pages/viewer/InventoryView.tsx:360-370`）

```jsx
const searchField = (
  <TextFieldControl
    type="search"
    className="field-h-md field-h-tap field-w-md viewer-toolbar__search"
    placeholder={t("viewer.search.placeholder")}
    aria-label={t("viewer.search.placeholder")}
    data-testid="viewer-search"
    value={query}
    onChange={(e) => reset(setQuery)(e.target.value)}
  />
);
```

- 状態は `const [query, setQuery] = useState("")`（同 `:73`）。
- `onChange` は `reset(setQuery)`（同 `:142-145`）＝値を入れてページを1に戻す。
- **絞り込みは `query` を直接見ている**（同 `:129` の `useMemo` の依存）＝**打つたびにその場で絞られる**。
- **実機の実測（DevTools）**: 328×48px・角丸 **6px**・枠線 1px solid #e2e8f0・白地・padding 8px 12px・文字14.4px。
  中にアイコンは無い。

### 2-2. 金型の側

| 何 | 場所 | 値 |
|---|---|---|
| 入力欄の角丸 | `frontend/src/components/FormField.css:46-62` の `border-radius: var(--comp-input-radius)` | `--comp-input-radius` = `var(--radius-md)` = **6px**（`frontend/src/tokens.css:484`） |
| 枠線・背景 | 同 `:53`・`:57` | `1px solid var(--border)` ／ `var(--bg-surface)` |
| スマホ48px | `frontend/src/components/field-size.css:34-38` | `@media (max-width:767px)` の中の `.field-h-tap` |
| 丸い形の先例 | `frontend/src/tokens.css:96-97` | `--radius-pill: 20px` ／ `--radius-full: 9999px`。**受信箱のスマホ検索欄が `--radius-full` を使っている**（`InboxPage.css:2116`） |
| 入力欄の種類 | `frontend/src/components/TextField.tsx:36` | `variant` は standard / karte / **search** / schedule / composer / login / product-edit。`search` は受信箱の見た目の写し（`FormField.css:360-378`・角丸6px・左に16px の余白を空けるが**アイコン自体はページ側の背景画像**） |
| 入力欄の中にアイコンや消すボタンを置く金型 | — | **無い**（`comp-field__icon` 相当は社内に存在しない） |

### 2-3. アイコン

- `frontend/src/constants/icons-base.tsx:50` に **`X`（✕）はある**。
- **虫眼鏡は無い**（`MagnifyingGlass` は `icons.tsx:145` にあるが、閲覧ページが読むのは `icons-base.tsx` のみ＝
  `InventoryView.tsx:15` は `import { ChevronRight } from "../../constants/icons-base"`）。
  **足すなら `icons-base.tsx` に1行**。閲覧ページ JS は 260.9KB／上限300KB（`frontend/scripts/check-viewer-bundle.js`）。

### 2-4. 右から出る画面の金型

`Drawer`（`frontend/src/components/Drawer.tsx`）が既にある。便2 で `onBack`+`backLabel`・`onEscape` を追加済み。
`data-testid="supplier-drawer"`・開いているときだけ `comp-drawer-panel--open`（同 `:123`・`:127`）。
**スマホでは全幅**。絞り込みはこの金型で「右から入れ替わる」形にして PO 承認済み（便2）。

### 2-5. いまの検索欄に当たっている検査

| 場所 | 記号 | 何を測っているか |
|---|---|---|
| `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts:126-133` | B4 | 上部の検索欄の高さが **48px ちょうど** |
| 同 `:252-265` | B4b | PC では `field-h-tap` が効かない |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:104` ほか | A2・A3・A4 | 上部の配置 |
| `frontend/src/pages/viewer/InventoryView.test.tsx:59`・`:81` | T5・T6 | 自動読み直し／**503 のときに検索の文字が保たれる** |

### 2-6. 辞書

`frontend/src/locales/viewer/ja.json:26-28` ＝ `search.placeholder`「商品名・型番・キーワードで検索」。
en も同じ構造。**「消す」「履歴」「最近使った語」に相当するキーは無い**（新設が要る）。
`viewer.filter.clear` は「選択をクリア」＝絞り込みパネル用で、検索欄とは別。

## 3. この便で決める必要があった点（PO 決定・2026-10-27）

| # | 問い | PO の決定 |
|---|---|---|
| 1 | 見た目だけ合わせるか、打ち方（動き）も同じにするか | **動きも同じ**＝確定するまで一覧は絞らない |
| 2 | 「←（戻る）」を付けるか | 結果画面には**付けない**（戻る先が無いため）。検索画面には付ける |
| 3 | タップ直後に何を出すか | **最近使った語（履歴を端末に保存）** |
| 4 | 作業の分け方 | **2便**。便12a＝検索画面＋札、便12b＝候補の一覧 |

## 関連
- 設計: docs/handoff/viewer-search-mercari/design.md
- 便11（直前の便）: docs/handoff/viewer-filter-row-mercari/design.md
- お手本の正本: docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md
