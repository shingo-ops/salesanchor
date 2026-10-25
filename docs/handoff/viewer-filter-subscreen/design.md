# design: 閲覧ページの絞り込みを「項目をタップ → 次の画面で選ぶ」に変える（便2）

> この文書は何か（1行）: 絞り込みパネルを、メルカリと同じ「項目が1行ずつ並ぶ → 押すと右から選択画面に入れ替わる」形にする便の設計。

**日付**: 2026-10-25
**recon**: `docs/handoff/viewer-filter-subscreen/recon.md`
**お手本の実測**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md`
**前便**: `docs/handoff/viewer-inventory-mobile-filter/design.md`（PR #4731・本番反映済み）
**対象 ADR**: ADR-1019（閲覧ページ）／ADR-144（UI 金型ガバナンス）／ADR-140（タップ領域44px）／ADR-067（トークン参照のみ）／ADR-027（文言は t() 経由）

## ① 区分：A（新機能）。PO 指示と形の承認を受領済み

`docs/handoff/devflow-autonomy-b/design.md:61`「今は無い状態を作るもの」に当たるため **A 区分**。
便1 で `layout="inline"` を足したときは「見えないものを見えるように戻す不具合修正」だったが、
本便は**画面の行き来という今は無い作りを足す**ので、素直に A とする。

| 項目 | 内容 |
|---|---|
| PO 指示（原文・2026-10-25） | 「2で『項目をタップ → 次の画面で選ぶ』形（メルカリと同じ）に変える、使いづらい」 |
| PO 承認（形の決定・2026-10-25） | 2案を図で提示し「**右から入れ替わる（メルカリと同じ）**」を選択。下から出すシート案は不採用 |
| **KGI の承認** | **受領（2026-10-25 PO「承認」）**。根拠: `docs/adr/ADR-1015-autonomy-b-class-no-po-approval.md:62`「A 区分の進め方（今までどおり PO が判断する）」／`docs/STANDARD-WORKFLOW.md:23`・`:79`。形の承認では代替できないため、② の K1〜K6 をそのまま提示して承認を得た |

## ② KGI（PO が判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | 絞り込みを開いた直後に、項目が**1行ずつ**並ぶ | 「提供者」「コンディション」「価格の範囲」「数量の範囲」が1画面に収まって見える |
| K2 | 項目を押すと**選択画面に入れ替わる** | 「提供者」を押すと提供者だけの画面になり、左上に「←」が出る |
| K3 | コンディションに**すぐ行ける** | 提供者を何件スクロールしても辿り着けない状態が解消する |
| K4 | 選んだ結果が**親の行で分かる** | 2件選ぶと「提供者」の行に選んだ名前が出る |
| K5 | 候補が多くても**探せる** | 選択画面の検索欄に文字を入れると候補が絞られる |
| K6 | 便1 で直した点が**壊れていない** | 選択肢が見える・画面に収まる・行の高さ44px以上・複数選べる |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 合否 |
|---|---|---|
| 最初の画面の高さ | 「数量の範囲」の下端の y | **画面の高さ（672）以内** |
| コンディションの行の位置 | 親の画面での y | **672 以内**（便1 は 2024 だった） |
| 選択画面の行の高さ | 行の `boundingBox().height` | **>= 44** |
| 選択画面で一度に見える件数 | 画面内に収まる行の数 | **>= 8**（お手本は約12） |
| 浮かぶパネル | ドロワーが開いている間 `document` 全体の `.comp-popover` | **0 件** |
| 横はみ出し | `documentElement.scrollWidth <= innerWidth` | 収まること |

## ④ 設計（How）

### 4-1. `Drawer` 金型に「← 戻る」を足す（任意・既定は今のまま）

`frontend/src/components/Drawer.tsx`

```ts
/** 「← 戻る」を押したときの処理。渡したときだけヘッダの左に「←」が出る（省略時は今までどおり出ない） */
onBack?: () => void;
/** 「←」の読み上げ名（ADR-027: 文言は呼び出し側が t() で渡す） */
backLabel?: string;
```

- 渡さなければ**1pxも変わらない**。`Drawer` は **35 ファイル**で使われているため、既定を動かさない
  （`grep -rl 'components/Drawer"' frontend/src --include=*.tsx | grep -v 'test\|stories' | wc -l` = 35。
  `frontend/src/components/Sheet.tsx:5` の「22 ページ」は古い値なので引用しない）。
- ヘッダは `frontend/src/components/Drawer.css:56-64`（`display:flex; justify-content:space-between`）と
  `:66-73`（`.comp-drawer-title{flex:1}`）で、`nth-child` 等の「題がひとつ」前提の指定は**無い**（grep 0件）ため、
  条件付きで「←」を足しても既存の並びは変わらない。
- 「←」のアイコンは **`frontend/src/constants/icons-base.tsx` に新設**する（§4-3）。題の**左**に置く（お手本 §3 と同じ）。
- `data-testid="drawer-back"`（既存の `drawer-close` と同じ並び）。

### 4-1b. 独立審査の修正1・3（実装後の2回目の審査で判明。`frontend/src/components/Drawer.tsx` の追加分）

当初案（上の §4-1 執筆時点）は「`onClose` に『`root` 以外なら戻る／`root` なら閉じる』を入れる」だった（下の §4-4 Esc の行も当時の記述）。
これは Esc・背景クリック・✕ の**3経路すべてが同じ `onClose` を呼ぶ**ため、✕ を押しても一段戻るだけになり、
✕ の読み上げ名「閉じる」と動作が食い違う不具合を生んだ（2回目の独立審査で指摘）。そこで次の2点を追加する。

```ts
/** Esc を押したときの処理。渡したときだけ onClose の代わりに呼ばれる（省略時は今までどおり onClose）。
 *  「一段戻る」を Esc に割り当てたい画面のため */
onEscape?: () => void;
```

- Esc のハンドラだけを `(onEscape ?? onClose)()` にする。**背景クリックと ✕ ボタンは常に `onClose`**（＝本当に閉じる）のまま変えない。
- 閲覧ページ側は `onClose` に本当に閉じる関数（`() => setDrawerOpen(false)`）を渡し、`onEscape` に「選択画面なら root へ戻る／root なら閉じる」（旧 `handleDrawerClose` を改名した `handleFilterEscape`）を渡す。
- あわせて、`onBack` と `backLabel` を union にして**片方だけでは渡せない**ようにする（`onBack` だけ渡すと `aria-label={undefined}` の名前の無いボタンが型検査を通ってしまっていた）:

```ts
type DrawerBackProps =
  | { onBack: () => void; backLabel: string }
  | { onBack?: undefined; backLabel?: undefined };
```

既存の呼び出し元（35ファイル）はどちらも渡していないため影響は無い（`npx tsc --noEmit` で確認）。

### 4-2. `MultiSelect` 金型に「行」の形を足す

`frontend/src/components/MultiSelect.tsx` の `layout` に `"row"` を足す（今は `"popover" | "inline"`）。

| layout | 見た目 | 使う場所 |
|---|---|---|
| `"popover"`（既定） | ボタン＋浮かぶ一覧 | PC。**変更なし** |
| `"inline"`（便1） | その場にチェックボックスの一覧 | **選択画面の中身**。そのまま使い回す |
| `"row"`（本便で追加） | 1行：左にラベル／右に現在値／右端に「>」 | 絞り込みパネルの最初の画面 |

- `"row"` は押せる1行。`onOpen: () => void` を受け取り、押すと呼ぶ（選択は `"row"` では行わない）。
- 現在値の文字: 0件なら `allLabel`（「すべて」）、1件以上なら**選んだ名前をカンマでつなぐ**
  （お手本 §2-1 の実測「IRWIN, AEG」に合わせる。`countLabel` は使わない。便1 の `inline` と同じ規則）。
- 行の高さは `var(--size-icon-btn-lg)`（44px）以上。**お手本は 52.7 だが、48px のトークン新設は次便（上部の高さ）でまとめて起案する**
  （`docs/specs/design-system/visual-language/benchmark/README.md` の PO決定1 の手順）。
- `data-testid`: `${testId}-row`。
- **新しい金型は作らない**（ADR-144）。「ラベル＋現在値＋>」は複数選びの見せ方の一つなので `MultiSelect` の中に収める。

**あわせて直す2点（審査の指摘）**

1. **選んだ名前は、候補を絞っても正しく出す。** 今の `frontend/src/components/MultiSelect.tsx:81` は
   `options.find(...)?.label ?? v` で、**検索で `options` を絞ると選択済みの名前が生の値に化ける**。
   そこで `MultiSelect` に `allOptions?: MultiSelectOption[]`（名前を引くための全件。省略時は `options`）を足し、
   **名前の解決は常に全件から行う**。表示の一覧だけを `options` で絞る。
2. **候補が0件のときの表示を金型が持つ。** `emptyLabel?: string` を足し、
   `options` が空なら一覧の代わりにその文字を出す（今は空の `<div>` を描くだけ＝`:101`）。

### 4-3. アイコンは `frontend/src/constants/icons-base.tsx` に足す（閲覧ページの 300KB 上限のため）

| 足すもの | 名前 | 置き場 |
|---|---|---|
| 「←」 | `ArrowLeft` | `frontend/src/constants/icons-base.tsx` |
| 「>」 | `ChevronRight` | 同上 |

- **`frontend/src/constants/icons.tsx` には足さない。** 閲覧ページは JS 合計 **300KB** が上限で（`frontend/scripts/check-viewer-bundle.js:21`）、
  超えると CI が落ちる。`frontend/src/constants/icons-base.tsx:2-3` に「閲覧ページが使う最小のアイコン。**定義はここだけ**。
  icons.tsx が再 export する」と明記されている。`Drawer` 金型自身も `icons-base` から読んでいる
  （`frontend/src/components/Drawer.tsx:21`。本便で `ArrowLeft` を足したため1行増えた位置）。
- 包み方は既存と同じ `hi(HeroIcon)`（`frontend/src/constants/icons-base.tsx:8`・`:27`）。
  `frontend/src/constants/icons.tsx` 側は**再 export だけ**を足す（`X`・`ArrowTopRight` と同じ扱い）。
- `ICON` は**アイコンの大きさ**の定数（`frontend/src/constants/iconSizes.ts:5`・生成物）なので、ここには足さない。
- `--icon-*` のトークンは変えないため `npm run generate:icon-sizes` の再生成は不要
  （`frontend/scripts/check-icon-sync.js` は大きさの一致だけを見る）。

### 4-4. 閲覧ページ側（`frontend/src/pages/viewer/InventoryView.tsx`）

絞り込みドロワーに**どの画面を出しているか**の状態を1つ持つ。

```ts
const [filterView, setFilterView] = useState<"root" | "provider" | "condition">("root");
const [optionQuery, setOptionQuery] = useState("");   // 候補を絞る欄（画面ごとの一時的な状態）
```

| 画面 | Drawer の題 | ヘッダ左 | 本体 | フッタ |
|---|---|---|---|---|
| `root` | 「絞り込み」 | （なし） | 提供者の行／コンディションの行／価格の範囲／数量の範囲 | （なし） |
| `provider` | 「提供者」 | **←**（`root` へ） | 候補を絞る検索欄 ＋ `layout="inline"` の提供者 | **「決定する」** |
| `condition` | 「コンディション」 | **←** | 同上（コンディション） | **「決定する」** |

**決めること（審査の指摘に対応）**

| 論点 | 決定 |
|---|---|
| 選択の反映 | **即時反映**（便1 と同じ）。「決定する」と「←」はどちらも `root` に戻るだけ。押し忘れで選択が消えることは無い |
| 候補を絞る欄の寿命 | **画面を離れるたびに空に戻す**（`←`・「決定する」・ドロワーを閉じる・項目を開く の全経路で `setOptionQuery("")`）。残して「候補が少ない」と誤解させない |
| 候補が0件のとき | **`MultiSelect` が描く**（§4-2）。呼び出し側は `emptyLabel` を渡すだけ |
| 画面が変わったときのフォーカス | `filterView` が `root` 以外になったら**「←」へ**、`root` に戻ったら**元の行へ**移す（`useEffect` ＋ `ref`）。`frontend/src/components/Drawer.tsx:80-86` の初期フォーカスは `open` が変わらないと再実行されないため、**押した行が消えてフォーカスが `<body>` に落ち、Tab がダイアログの外へ逃げる**（`frontend/src/components/Drawer.tsx:101-130` のトラップは `activeElement` が端のときしか効かない） |
| Esc | `root` 以外では**`root` に戻る**（ドロワーごと閉じない）。**✕ は常に閉じる**（§4-1b・修正1）。当初案は `Drawer` の `onClose` に分岐を入れるものだったが、`onClose` は Esc・背景クリック・✕ の3経路すべてで呼ばれるため ✕ まで「戻る」になってしまう不具合を2回目の審査で指摘された。そこで `Drawer` に `onEscape?: () => void` を足し、**Esc だけ**その処理を呼ぶ形に変更（§4-1b）。`onClose` には本当に閉じる関数を渡す |
| ドロワーを閉じたとき | `root` へ戻すのは**閉じ終わってから**（`--transition-slow` ぶん遅らせる）。`frontend/src/components/Drawer.tsx:144-147` のとおり DOM は常にあるので、即座に戻すとスライドアウト中に題と中身が切り替わって見える |
| 自動読み直し（60秒） | `frontend/src/pages/viewer/useViewerAutoRefresh.ts` が `data` を差し替えても `filterView` は別の状態なので画面は維持される。選択肢が消えた場合は下の「選んだ名前」の規則で守る |

### 4-4b. testId を層ごとに分ける（strict mode violation の予防）

便1 では popover 版と inline 版が同じ `viewer-provider-filter` を共有していた（`frontend/src/pages/viewer/InventoryView.tsx:117`・`:146`）。
本便で3層になるため分ける。

| 層 | testId |
|---|---|
| PC（popover） | `viewer-provider-filter` |
| 最初の画面（row） | `viewer-provider-row` |
| 選択画面（inline） | `viewer-provider-options` |

### 4-5. 文言（ADR-027: `frontend/src/locales/viewer/ja.json` と `frontend/src/locales/viewer/en.json` に同じキー）

| キー | ja | en |
|---|---|---|
| `viewer.filter.back` | 戻る | Back |
| `viewer.filter.apply` | 決定する | Done |
| `viewer.filter.searchOptions` | 絞り込む | Filter options |
| `viewer.filter.noOptions` | 見つかりません | No matches |

### 4-6. 触らないもの

- PC の絞り込み（`layout="popover"` のまま）
- `Popover` 金型（`frontend/src/components/Popover.tsx`。前便 C4 の宿題のまま）
- `Sheet` 金型（PO が「右から入れ替わる」を選択したため使わない）
- アプリ側 `/inventory`・バックエンド・DB・`.github/`

## ⑤ Acceptance Criteria

**測り方の共通の決まり**: A1・A4・A6 は **`scrollIntoView` を使わずに測る**（既存 spec の `scrollIntoViewIfNeeded()` を
流用すると常に真になる）。「見えている」は `boundingBox()` が `0 <= y` かつ `y + height <= innerHeight` を満たすこと。

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 最初の画面に4項目が収まる（「数量の範囲」の下端 <= `innerHeight`。スクロールせずに測る） | spec |
| A2 | 「提供者」の行を押すと選択画面になり、`drawer-back` が出る。**押す前は `drawer-back` が無い** | spec |
| A3 | 「←」で最初の画面に戻る（題が「絞り込み」に戻り、`drawer-back` が消える） | spec |
| A4 | コンディションの行が**スクロールせずに画面内**にある（便1 の 2024 → `innerHeight` 以内） | spec |
| A5 | 選択画面の行の高さが 44px 以上・`x>=0` かつ `x+width<=innerWidth` | spec |
| A6 | 選択画面で**スクロールせずに見える行が 8 件以上、かつ 20 件以下**（上限も見ないと「全部出しただけ」と区別できない） | spec |
| A7 | 2件選ぶと一覧が絞られ、**親の行に選んだ名前がカンマつなぎで出る** | spec |
| A8 | 検索欄に文字を入れると候補が絞られ、消すと件数が元に戻る | spec |
| A9 | **検索で候補を絞っている間も、親の行の名前が生の値に化けない**（§4-2 の1） | `frontend/src/components/MultiSelect.test.tsx`（spec ではなく単体テスト。理由: 閲覧ページは `frontend/src/pages/viewer/InventoryView.tsx:88-95` が `{value: v, label: v}` を作るため value と label が同じ文字列で、e2e では名前が生の値に化ける退行を**原理的に観測できない**。実際の守り手は単体テスト。審査で指摘） |
| A10 | **候補が0件になる語を入れると `noOptions` の文字が出る**（§4-2 の2） | spec |
| A11 | **「決定する」を押すと最初の画面に戻り、選択は残っている** | spec |
| A12 | 選択画面で **Esc を押すと最初の画面に戻る**（ドロワーは閉じない） | spec |
| A13 | 選択画面で **Tab を10回押してもフォーカスがドロワーの外に出ない** | spec |
| A14 | 画面が変わった直後のフォーカスが「←」にある | spec |
| A15 | ドロワーが開いている間、`document` 全体で `.comp-popover` が 0 件（**A5 と対で意味を持つ**。単独ではボタンを押さない限り常に真） | spec |
| A16 | ページ全体の横はみ出しが 0（`documentElement.scrollWidth <= innerWidth`） | spec |
| A17 | ドロワーを閉じて開き直すと最初の画面に戻り、**検索欄が空**になっている | spec |
| A18 | PC（1280px）は popover のまま・一覧の幅 400px 以上 | spec（既存 `:171-195` をそのまま使う） |
| A19 | `onBack` を**渡さない**既定で `drawer-back` が描かれない | `frontend/src/components/Drawer.test.tsx` |
| A20 | `MultiSelect` の `layout` 省略時が popover のまま | `frontend/src/components/MultiSelect.test.tsx` |
| A21 | ja/en の辞書に同じキーが揃っている | `npm run check:all` |
| A22 | **閲覧ページの JS 合計が 300KB 以内** | `frontend/scripts/check-viewer-bundle.js`（CI の必須チェック） |
| A23 | 型検査が通る | `cd frontend && npx tsc --noEmit` |
| A24 | 手元検査が通る | `cd frontend && npm run check:all` |

### 5-1. 便1 の spec（旧 A4〜A13）との対応

`frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` を本便で書き換える。

| 旧 | 中身 | 本便での扱い |
|---|---|---|
| 旧A4〜A9（`:79-110`） | root に選択肢が見える／収まる／44px／横はみ出し／popover 0件／2件選ぶと絞られる | **書き換え**。行をタップしてから測る。新 A5・A7・A15・A16 に対応 |
| 旧A10（`:112-123`） | 総数一致・最後まで見える | **書き換え**。検索欄が空のときに限る条件を明記。新 A6・A8 |
| 旧A11（`:125-136`） | スクロール後に開く | **書き換え**（タップを挟む） |
| 旧A12（`:138-167`） | コンディション | **書き換え**＋本便の主眼である新 A4（画面内にある）を追加 |
| 旧A13（`:171-195`） | PC popover | **そのまま**（新 A18） |
| ヘルパー `:29-42`・`:64-70` | ドロワーを開く・横はみ出し | 流用 |
| ヘルパー `:44-55` `optionRowBox` | `el.closest("label")` 前提 | **row 層は `<button>` なので別ヘルパーを足す** |
| ヘルパー `:72-75` | popover 0件 | 流用（A15 として A5 と対にする） |
| 冒頭コメント `:5` | 旧 design を指す | **本 design を指すよう書き換える** |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/constants/icons-base.tsx` | `ArrowLeft`・`ChevronRight` を新設 |
| `frontend/src/constants/icons.tsx` | 上の2つを再 export |
| `frontend/src/components/Drawer.tsx` | `onBack` / `backLabel` を追加（既定は今のまま）。2回目の審査対応（§4-1b）で `onEscape` を追加し、Esc だけ分岐・背景クリックと✕は常に `onClose`。`onBack`/`backLabel` を union 化して片方だけ渡せないようにする |
| `frontend/src/components/Drawer.css` | 「←」の置き場 |
| `frontend/src/components/Drawer.test.tsx` | A19 |
| `frontend/src/components/Drawer.stories.tsx` | 「←」付きの見本 |
| `frontend/src/components/MultiSelect.tsx` | `layout="row"`・`onOpen`・`allOptions`・`emptyLabel` |
| `frontend/src/components/MultiSelect.css` | `row` の見た目・0件の文字 |
| `frontend/src/components/MultiSelect.test.tsx` | A20・row の描画・名前の解決・0件 |
| `frontend/src/components/MultiSelect.stories.tsx` | `row` の見本 |
| `frontend/src/pages/viewer/InventoryView.tsx` | `filterView`・`optionQuery`・3画面の出し分け・フォーカス・Esc |
| `frontend/src/pages/viewer/viewer.css` | 行・検索欄・フッタの配置 |
| `frontend/src/pages/viewer/InventoryView.test.tsx` | 画面の行き来 |
| `frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json` | §4-5 の4キー |
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | §5-1 のとおり書き換え |
| `docs/handoff/viewer-filter-subscreen/recon.md`・`docs/handoff/viewer-filter-subscreen/design.md`・`docs/handoff/viewer-filter-subscreen/review-opus.md` | 新規 |
| `.claude-pipeline/active-work.d/release-viewer-filter-subscreen.md` | 台帳 |

## ⑦ 戻し方

この PR を revert するだけ。`Drawer` の `onBack` と `MultiSelect` の `layout="row"` はどちらも
**渡したときだけ効く**ので、戻しても他画面に影響は残らない。便1（`layout="inline"`）は残る。

## ⑧ 削除するファイル

無し（既存ファイルの行の書き換えはある。PR 本文の「削除するファイル:」に列挙する）。

## ⑨ 外部・過去事例の参照と我々への応用

| 事例 | 我々への応用 |
|---|---|
| メルカリ（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` §2-1・§3） | 親の行は「ラベル＋現在値＋>」。進んだ先は「←／題／クリア」「候補を絞る検索欄」「行まるごと押せるチェック欄」「下に固定の決定ボタン」 |
| 便1（`docs/handoff/viewer-inventory-mobile-filter/design.md`） | 金型に**任意のプロパティ**を足して既定を変えないやり方。審査でも呼び出し元全数を確認して安全と確認済み |
| 便1 の審査（`docs/handoff/viewer-inventory-mobile-filter/review-opus.md`） | 「常に真になる検査」を置かない。fixture は空振りしない形に固める |
| `frontend/src/components/Sheet.tsx` の冒頭コメント | 既存金型を改造すると波及が広い場合は別金型を作る、が前例。今回は**任意プロパティで既定不変**にできるので改造を選ぶ |

## ⑩ 弊害・トレードオフ

- 絞り込みの操作が**1タップ増える**（項目を押してから選ぶ）。その代わり最初の画面に全項目が収まり、コンディションへ即座に行ける。PO の実使用の判断（「使いづらい」）がこの交換を選んだ根拠。
- `Drawer` 金型に分岐が1つ増える（22ページに影響しない任意プロパティだが、金型は複雑になる）。
- 「決定する」は実際には「戻る」と同じ働きになる（選択は即時反映のため）。お手本の見た目に合わせつつ、押さなくても選択が消えないので誤解による損失は無い。**PO が使ってみて違和感があれば、次便で「決定するまで反映しない」に変えられる**（その場合は一時的な選択状態を持つ作りが要る）。
- 読み上げを使う人には「決定する」という言葉が実態（＝戻る）と食い違う。**PO に2択で確認し「決定する」を選択（2026-10-25）**＝
  お手本の見た目に忠実な方を採る。英語も `Done` とする。実態との差は、押さなくても選択が消えない作りで害が出ないことで受け入れる。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts`（CI の集約ジョブ `visual-language` で毎 PR 走る）

| 守ること | 関所 | 外すと |
|---|---|---|
| 最初の画面に全項目が収まる（スクロールせずに） | 上記 spec（A1・A4） | 赤 |
| 画面の行き来ができる | 上記 spec（A2・A3・A11・A17） | 赤 |
| 選択画面で8〜20件見える・44px 以上 | 上記 spec（A5・A6） | 赤 |
| 浮かぶパネルを作らない | 上記 spec（A15・A5 と対） | 赤 |
| 検索で候補を絞っても親の行の名前が生の値に化けない（A9） | `frontend/src/components/MultiSelect.test.tsx`（spec ではない。理由は⑤ A9 の行と同じ: 閲覧ページは value と label が同じ文字列のため e2e では退行を観測できない） | 赤 |
| PC が popover のまま | 上記 spec（A18）＋ `frontend/src/components/MultiSelect.test.tsx` | 赤 |
| キーボードだけで操作できる（Esc・Tab・フォーカス） | 上記 spec（A12〜A14） | 赤 |
| 既定の Drawer に「←」が出ない | `frontend/src/components/Drawer.test.tsx`（A19） | 赤 |
| ✕ は選択画面からでも必ず閉じる（Esc は戻るだけ） | `frontend/src/components/Drawer.test.tsx`・`frontend/src/pages/viewer/InventoryView.test.tsx`（修正1） | 赤 |
| **閲覧ページの JS が 300KB を超えない** | `frontend/scripts/check-viewer-bundle.js`（CI 必須） | 赤 |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| C1 | **便3: 上部の高さを詰める**（実測 236px → 144px）。48px トークンの新設もここで起案。**PO 判断待ち: ヘッダーを無くすと「最終更新」と「言語」の置き場が要る** | 根拠の数値は取得済み（`docs/handoff/viewer-inventory-mobile-filter/recon.md` §4-1） |
| C2 | `Popover` 金型の2つの欠陥（スクロール二重加算・画面端で折り返さない） | 前便 C4 のまま。金型を使う全画面に波及するため影響の全数調査から |
| C3 | アプリ側 `/inventory` の絞り込みも同じ形にするか | 別便。閲覧ページでの PO の使用感を見てから |
| C4 | 「決定するまで反映しない」にするか | PO の使用感次第（⑩ 参照） |
| C5 | 下のボタンの文言 | **決着済み**（PO 2026-10-25「決定する」） |
| C6 | **A6（選択画面で8件以上見える）の余裕が約1行しかない**。360×700 でヘッダ・フッタ・検索欄・見出しを引くと 44px 行で約9行、下限は8。ヘッダやフッタが数十px 太ると赤になるため、**太らせる変更をするときは同時に下限（`MIN_VISIBLE_OPTIONS`）を見直すこと** | 審査（抜き取り検証）で判明。対応は見送り・次に太らせる便で見直す |
| C7 | `frontend/src/pages/viewer/InventoryView.tsx` が **606行**。`frontend/scripts/check-page-size.js` の800行の関所は ファイル名が Page.tsx で終わるもの という名前のファイルしか見ないため**この画面には掛かっていない**（review-opus.md §3 の訂正）。分割するかは別便で判断 | 対応は見送り（本便の範囲外） |
