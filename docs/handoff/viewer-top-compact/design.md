# design: 24時間フィルタを絞り込み画面へ／シリーズを並び替えの左へ（便3）

> この文書は何か（1行）: 閲覧ページのスマホ上部を1行ぶん短くする便の設計。24時間の絞り込みを奥（絞り込み画面）へ移し、空いた場所にシリーズの選択を入れて「シリーズ・並び替え・絞り込み」を1行に並べる。

**日付**: 2026-10-25
**recon**: `docs/handoff/viewer-top-compact/recon.md`
**お手本の実測**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41`
**前便**: `docs/handoff/viewer-filter-subscreen/design.md`（便2・PR #4740・本番反映済み）
**対象 ADR**: ADR-1019（閲覧ページ）／ADR-144（UI 金型ガバナンス）／ADR-140（タップ領域44px）／ADR-067（トークン参照のみ）／ADR-027（文言は t() 経由）

## ① 区分：A（見た目と操作の変更）

| 項目 | 内容 |
|---|---|
| PO 指示（原文・2026-10-25） | 「24時間のフィルタを詳細画面に移動、中分類の絞り込み機能を並び替えの左側に配置」 |
| 言葉の対応 | `docs/handoff/viewer-top-compact/recon.md` §1 の表（24時間のフィルタ＝`viewer-fresh-toggle`／詳細画面＝絞り込みドロワー／中分類＝「シリーズ」の選択） |
| **PO の判断** | **指示そのものを受領**（上記原文）＋「進める」を受領（2026-10-25）。A 区分は PO が判断する（`docs/adr/ADR-1015-autonomy-b-class-no-po-approval.md:62`・`docs/STANDARD-WORKFLOW.md:23`・`:79`）。指示は対象と置き場まで具体的なため、これを判断の根拠として実装に着手する。**② の K1〜K6 は実装後に実機で確かめてもらう**。ただし **K5（絞り込みボタンの件数表示）は PO 指示に無い追加**なので、4-3 のとおり単独で外せる形にする |
| ヘッダー（68px）の扱い | **本便では触らない**。「ヘッダーを消すと『最終更新』と『言語』の置き場が要る」は PO 判断待ちのまま（⑫ D1） |

## ② KGI（PO が判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | 上部が**1行ぶん短く**なる | 商品カードが今より上から始まる（数値では 236px → 192px） |
| K2 | 「24時間以内」が**上部から消える** | 検索欄の下の行が「シリーズ／並び替え／絞り込み」の3つになる |
| K3 | 「24時間以内」が**絞り込み画面の中にある**し、効く | 絞り込みを開くと先頭に「24時間以内」があり、切ると一覧の件数が変わる |
| K4 | **シリーズが並び替えの左**に並ぶ | 同じ行に左から「シリーズ」「並び替え」「絞り込み」 |
| K5 | 絞り込みが効いているか**一目で分かる** | 絞り込みボタンに有効な数が出る（既定は「絞り込み (1)」＝24時間以内がオン） |
| K6 | **最初に見える中身が今までと同じ** | 開いた直後は24時間以内がオンのまま（並びも件数も今と同じ） |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 合否 |
|---|---|---|
| 上部の高さ | 一覧の先頭カード（`.comp-table__card`）の y をスクロールせずに測る | **192 以内**（現状236） |
| 操作台の行数 | シリーズ・並び替え・絞り込みの y が同じ | **3つとも同じ y**（＝1行） |
| 右端 | 3つのうち一番右の `x + width` | **画面幅以内** |
| タップ目標 | 3つそれぞれの height | **>= 44** |
| 横はみ出し | `documentElement.scrollWidth <= innerWidth` | 収まること |
| 上部の24時間ボタン | 上部に `viewer-fresh-toggle` が存在するか（スマホ幅） | **0 件** |

## ④ 設計（How）

### 4-1. 「24時間以内」を絞り込み画面の先頭へ

- 絞り込みドロワーの**最初の画面**（便2 の `filterView === "root"`。`docs/handoff/viewer-filter-subscreen/design.md` 4-4）の
  **先頭**に1行追加する。並びは「24時間以内 → 提供者 → コンディション → 価格の範囲 → 数量の範囲」。
- 形は**チェック欄1行**。金型は `frontend/src/components/CheckboxControl.tsx`（`div`/`label` を増やさない設計）を
  `label` で包み、**行の高さは `var(--size-icon-btn-lg)`（44px）以上**にする（ADR-140）。
  便2 で入れた `.comp-multiselect__option--inline`（`frontend/src/components/MultiSelect.css`）と同じ見え方に合わせる。
- 文言は**既存キーを再利用**（`viewer.freshOnly` = 「{{hours}}時間以内」）。新しいキーは増やさない。
- `data-testid="viewer-fresh-check"`（上部のボタンの `viewer-fresh-toggle` とは**別の名前**にする。
  便2 の教訓＝同じ testId を層で共有すると strict mode violation になる。`docs/handoff/viewer-filter-subscreen/design.md` 4-4b）。
- **スマホの上部からは消す**。PC（`ContentToolbar` 側）は**今のまま**（`frontend/src/pages/viewer/InventoryView.tsx:467` の `freshButton` は残す）。
- 状態（`freshOnly`）・既定（オン）・判定に使う「今」の取り直しは**変えない**（`frontend/src/pages/viewer/InventoryView.tsx:67`・`:58`・`:106-107`）。

### 4-2. シリーズの選択を操作台の中（並び替えの左）へ

- `frontend/src/pages/viewer/InventoryView.tsx:407-418` の「スマホだけ出すシリーズ選択」を、
  `:420-428` の `.viewer-toolbar` の中へ移す。並びは **検索欄（1行目） → シリーズ・並び替え・絞り込み（2行目）**。
- **1行に収まることを運任せにしない**（`frontend/src/pages/viewer/viewer.css:26-32` は `flex-wrap: wrap` のため、幅が足りなければ勝手に折り返す）:

| 要素 | 指定 | 理由 |
|---|---|---|
| 検索欄 | `flex: 1 1 100%` | 1行目を独占する（今は「280 + 84 が入らないから折り返している」という偶然に頼っている） |
| シリーズ | `flex: 1 1 0; min-width: 0` ＋ はみ出しは `…` で省略 | **残った幅に合わせて縮む**。360px での残りは 328 − 108 − 72 − 24 = **124px**（recon §4） |
| 並び替え・絞り込み | `flex: 0 0 auto` | 文字が切れないよう自然幅を保つ |

- 読み上げ名は今のまま（`aria-label={t("viewer.tabSelect")}` ＝「シリーズ」）。省略記号で文字が切れても名前は残る。
- `data-testid="viewer-tab-select"` は**変えない**（既存の検査・PC 側と共通の名前）。

### 4-3. 絞り込みが効いていることの手がかり（安全策）

24時間以内は**既定オン**なので、奥へ移すと「既定で絞られているのに画面に手がかりが無い」状態になる（recon §7）。
そこで**絞り込みボタンに有効な数を出す**。

- 数え方: `(24時間以内 ? 1 : 0) + (提供者を選んでいる ? 1 : 0) + (コンディションを選んでいる ? 1 : 0) + (価格に入力がある ? 1 : 0) + (数量に入力がある ? 1 : 0)`
- 文言は新キー1つ: `viewer.filter.buttonWithCount` = 「絞り込み ({{count}})」／en 「Filter ({{count}})」。**0 件のときは今までどおり「絞り込み」**。
- 金型は増やさない（`frontend/src/components/Badge.tsx` は使わず、ボタンの文字に含める）。
- **これは PO 指示に無い追加**なので、不要と判断された場合は**この1点だけ外せる**ようにする（他の変更から独立）。

### 4-4. 触らないもの

- ヘッダー（題・最終更新・言語）＝⑫ D1 の PO 判断待ち
- PC（1280px）の上部（タブ＋24時間ボタン＋並び替え＋絞り込みのまま）
- `Popover` 金型（前便 C2 の宿題のまま）／アプリ側 `/inventory`／バックエンド／DB／`.github/`

## ⑤ Acceptance Criteria

**測り方の共通の決まり**: A1〜A4 は **`scrollIntoView` を使わずに測る**（便2 の教訓＝流用すると常に真になる）。

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 一覧の先頭カードの y が **192 以内**（360・390 の両方） | spec |
| A2 | シリーズ・並び替え・絞り込みの y が**同じ**（1行に並ぶ） | spec |
| A3 | 3つの右端が画面幅以内・高さが **44px 以上** | spec |
| A4 | 検索欄が**単独で1行**（シリーズと y が違う） | spec |
| A5 | スマホの上部に `viewer-fresh-toggle` が **0 件** | spec |
| A6 | 絞り込み画面の先頭に `viewer-fresh-check` があり、**高さ44px 以上** | spec |
| A7 | `viewer-fresh-check` を切ると**一覧の件数が増える**（24時間より古い行が出る） | spec |
| A8 | **開いた直後は24時間以内がオン**（`viewer-fresh-check` が checked） | spec＋`frontend/src/pages/viewer/InventoryView.test.tsx` |
| A9 | 絞り込みボタンの文字が既定で「絞り込み (1)」、すべて外すと「絞り込み」 | spec |
| A10 | シリーズを選ぶと**一覧の件数が変わる** | spec |
| A11 | ページ全体の横はみ出しが 0 | spec |
| A12 | PC（1280px）は**今のまま**（上部に `viewer-fresh-toggle` が居る・タブが出る） | spec |
| A13 | 絞り込み副画面（便2 の A1〜A18）が**壊れていない** | 既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` |
| A14 | ja/en の辞書に同じキーが揃っている | `npm run check:all` |
| A15 | 閲覧ページの JS 合計が 300KB 以内 | `frontend/scripts/check-viewer-bundle.js`（CI 必須） |
| A16 | 型検査が通る | `cd frontend && npx tsc --noEmit` |
| A17 | 手元検査が通る | `cd frontend && npm run check:all` |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/pages/viewer/InventoryView.tsx` | 24時間をドロワーへ移す／シリーズを操作台へ移す／絞り込みボタンの件数 |
| `frontend/src/pages/viewer/viewer.css` | 操作台の折り返しを決める指定（検索欄は1行独占・シリーズは縮む） |
| `frontend/src/pages/viewer/InventoryView.test.tsx` | A8 と「上部に24時間ボタンが無い」「件数の文字」 |
| `frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json` | `viewer.filter.buttonWithCount` の1キー |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | **新設**（A1〜A12） |
| `docs/handoff/viewer-top-compact/recon.md`・`docs/handoff/viewer-top-compact/design.md` | 新規 |
| `.claude-pipeline/active-work.d/release-viewer-top-compact.md` | 台帳 |

## ⑦ 戻し方

この PR を revert するだけ。金型（`Drawer`・`MultiSelect`・`CheckboxControl`）には手を入れないので、他画面への影響は残らない。

## ⑧ 削除するファイル

無し（既存ファイルの行の書き換えはある。PR 本文の「削除するファイル:」に列挙する）。

## ⑨ 外部・過去事例の参照と我々への応用

| 事例 | 我々への応用 |
|---|---|
| メルカリ（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41`） | 3行目が「販売中のみ／おすすめ順／絞り込み」＝**絞り込みの種類・並び替え・絞り込みが1行**。本便で作る「シリーズ／並び替え／絞り込み」と同じ形。お手本は枠線の無いボタンで 48dp に文字をゆったり入れている（同 `:43`） |
| 便2（`docs/handoff/viewer-filter-subscreen/design.md`） | 奥の画面に項目を増やすときの形（1行ずつ・44px 以上・testId は層ごとに分ける）。`filterView === "root"` の先頭に足すだけで済む |
| 便2 の審査（`docs/handoff/viewer-filter-subscreen/review-opus.md`） | 「常に真になる検査」を置かない／既定で隠れる状態は手がかりを残す（本便 4-3 の件数表示はこの学びの適用） |
| 便0（`docs/handoff/inventory-mobile-responsive/design.md`） | 寸法は**CI の spec で測って固定**する。実機が無くても一次情報が取れる |

## ⑩ 弊害・トレードオフ

- **24時間の切り替えが1タップ遠くなる**（上部 → 絞り込みを開く）。PO 指示による交換で、代わりに上部が1行短くなる。
- お手本は3行目に「販売中のみ」を**残している**。我々はそこをシリーズに置き換える形になるため、**鮮度の切り替えは奥**になる。
  手がかりが消える弊害は 4-3 の件数表示で埋める（それでも「何で絞られているか」はボタンの数字だけなので、開いて確かめる必要はある）。
- シリーズの選択は幅 124px まで縮むため、**長いシリーズ名は `…` で切れる**（読み上げ名は残る）。
- 絞り込みボタンの文字が「絞り込み (1)」と長くなり、幅が数px 増える（1行に収まることは A2・A3 で固定する）。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts`（CI の集約ジョブ `visual-language` で毎 PR 走る。`frontend/playwright.config.ts:64`・`:69`・`:74` の `testMatch` が `visual-language/` 配下に限るため、**ここに置かないと1本も走らない**）

| 守ること | 関所 | 外すと |
|---|---|---|
| 上部が192px 以内 | 上記 spec（A1） | 赤 |
| シリーズ・並び替え・絞り込みが1行に並ぶ | 上記 spec（A2・A3・A4） | 赤 |
| 24時間が上部に戻らない／奥で効く | 上記 spec（A5・A6・A7） | 赤 |
| 既定の中身が変わらない（24時間オン） | 上記 spec（A8）＋ `frontend/src/pages/viewer/InventoryView.test.tsx` | 赤 |
| 絞り込みが効いている手がかり | 上記 spec（A9） | 赤 |
| PC が今のまま | 上記 spec（A12） | 赤 |
| 絞り込み副画面（便2）が壊れない | `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | 赤 |
| 閲覧ページの JS が 300KB を超えない | `frontend/scripts/check-viewer-bundle.js` | 赤 |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| D1 | **ヘッダー（68px）をどうするか**＝上部を 192 → 144 にする最後の一手。**PO 判断待ち**: ヘッダーを消すと「最終更新」と「言語」の置き場が要る（題「在庫一覧」は PWA のタイトルバー「Sales Anchor Viewer」と二重。`frontend/viewer/index.html`） | 数値の根拠は取得済み（recon §2） |
| D2 | 48px 行への統一（お手本は 48・我々は 44）。トークンは**新設不要**で `--space-12`／`--comp-btn-height-lg` が既にある（recon §3） | 便2 design ⑫C6（A6 の余裕1行）と合わせて判断 |
| D3 | 枠線の無いボタン（お手本 `:43`）にするか | 金型（`Button`）の話になるため別便 |
| D4 | 便2 の持ち越し: C2（`Popover` 金型の2欠陥）・C8（フォーカスが `<body>` に落ちる） | そのまま |
