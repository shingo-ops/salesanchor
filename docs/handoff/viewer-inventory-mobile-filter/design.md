# design: 閲覧ページの在庫表 — スマホで絞り込みを選べるようにする（便1）

> この文書は何か（1行）: スマホの絞り込みパネルで、選択肢の一覧が**パネルの裏に隠れて選べない**不具合を直す便の設計。お手本（メルカリ）と同じく「パネルの中では浮かせず、その場にチェックボックスを並べる」形にする。

**日付**: 2026-10-25（審査 CHANGES-REQUESTED を受けて改訂）
**recon**: `docs/handoff/viewer-inventory-mobile-filter/recon.md`（本番の実機で測った値）
**お手本の実測**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md`
**審査記録**: `docs/handoff/viewer-inventory-mobile-filter/review-opus.md`
**対象 ADR**: ADR-1019（閲覧ページ）／ADR-144（UI 金型ガバナンス）／ADR-140（スマホのタップ領域）／ADR-067（色・余白はトークン参照。px のマジックナンバー禁止）
**PO 指示（原文）**: 「閲覧用の在庫ページだがスマホからの利用ですと、絞り込みができません。『提供者：すべて』『コンディション：すべて』それぞれ『すべて』一択になっているので、改善していただけますと幸いです🙏」「メルカリと同じように選択したらチェックボックスを入れられるようにしたい」

## ① 区分：B-1 相当（不具合修正）。PO 承認は不要

### 1-1. 区分の判定と、PO に確認した点

`docs/handoff/devflow-autonomy-b/design.md:67` の B-1 は「`frontend/src/`・`backend/app/`・テストだけ」と書かれており、本便は `docs/`（お手本の記録と本設計書）と `.claude-pipeline/`（台帳）も含むため、文言どおりなら同 `:74-75`「どちらでもない → PO に y/n を1問」に落ちる。
一方 ADR-1015:2 は B 区分に `docs/handoff/` への記録を**義務付けている**（正本どうしが噛み合っていない）。

そこで PO に2択で確認した。**PO 回答「1」（2026-10-25）＝「このまま1本の PR で進める。B-1 相当・PO 承認は不要と明記する」。**
PR 本文の「区分」欄には `B-1相当（PO 確認済み・2026-10-25「1」）`、「PO承認」欄には `不要（B。区分の食い違いのみ PO に1問確認し「1」を受領）` と書く。

### 1-2.「新機能ではない」ことの根拠

`docs/handoff/devflow-autonomy-b/design.md:61` は「今は無い状態を作るもの」を A とする。本便が足す `layout="inline"` は確かに**今は無い描画の形**である。それでも新機能ではないと判断する理由は次の2つ。

1. **PO から見た機能は増えない。** 「提供者とコンディションをチェックボックスで複数選ぶ」は既に実装済み（`frontend/src/components/MultiSelect.tsx:77-86`）で、選択肢も実在する（実機で **43 件**を確認）。本便は**見えない・押せないを、見える・押せるに戻すだけ**。
2. **新しい画面・入口・表は作らない**（`docs/handoff/devflow-autonomy-b/design.md:62` に当たらない）。`frontend/src/pages/` にファイルは増えない。

### 1-3. 期待値（正本の行）

| # | ADR | file:line | 引用文 |
|---|---|---|---|
| 1 | ADR-1019 | `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:27`（What 節 8） | 「閲覧ページの画面は、アプリの在庫表（/inventory）と同じ金型（DataTable・MultiSelect・Select・Tabs・Badge・Drawer・Button・TextField）と、共有部品（frontend/src/features/inventory/ の normalizeForSearch・conditionBadgeVariant・inventoryColumns.css）で作る。」 |
| 2 | ADR-140 | `docs/adr/ADR-140-mobile-nav-bottom-tabs.md:63`（受け入れ基準（KGI）表の G4 行） | 「タップ領域 高さ≥44px | Playwright `getBoundingClientRect().height >= 44`」 |

1 は「アプリの在庫表と同じ金型で作る」＝**アプリと同じように絞り込みが使える**ことを前提にしている。アプリ側は絞り込みパネルを `Drawer` ではなく画面に直接置く `<section>` で出すため（`frontend/src/pages/inventory/InventoryPage.tsx:486`・`frontend/src/pages/inventory/InventoryFilterPanel.tsx:103-116`）、同じ金型を使っていても**閲覧ページだけが使えない状態**になっている。
2 は下部タブの受け入れ基準として書かれた行で、本件の直接の正本ではない。選択肢の行の高さ 44px の根拠として参照する。

### 1-4. 実際の挙動（recon §2・§3 の要約。すべて実機実測）

絞り込みを開いて「提供者: すべて」を押しても**画面が1画素も変わらない**（押す前後の差分409画素はすべて端末のステータスバー）。支援技術から見えるチェック欄は **0 件**。原因は3つ。

| # | 原因 | 実測 |
|---|---|---|
| ① | 一覧（重なり順 **50**）が、絞り込みパネル（**301**・画面いっぱい 360x672・背景 `rgb(255,255,255)` 不透明）の裏に回る | `frontend/src/tokens.css:122`・`:127`／`frontend/src/components/Drawer.css:31`・`:33`・`:109-112`／`frontend/src/components/Popover.css:16-17` |
| ② | 一覧の最小幅 **400px** が画面 **360px** より広い。実際の位置は **x=-29・幅418** で左右とも画面外 | `frontend/src/components/MultiSelect.css:10` → `frontend/src/tokens.css:447`／`frontend/src/components/Popover.tsx:63-68`（画面端で折り返さない） |
| ③ | `position: fixed` の置き場に `window.scrollY` を二重加算。400px 下げると一覧が **y=550**（正しくは150）に置かれ、画面（高さ672）の下に出る | `frontend/src/components/Popover.tsx:66`（`:50`・`:55`・`:60` も同様）× `frontend/src/components/Popover.css:16` |

あわせて測れた欠陥: 選択肢1行の高さ **30px**（44px 未満）／一覧の表示高さ **200px** に対し中身 **1279px**（43件中 約6.6件しか出せない）。

## ② KGI（PO が判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | スマホで「提供者」の選択肢が**見える** | 絞り込みを開いて提供者を押すと、仕入元の名前がチェックボックス付きで並ぶ |
| K2 | **選べる**（複数） | 2つ選ぶと一覧がその2つだけに絞られる |
| K3 | **指が届く** | 選択肢の行が画面の幅に収まり、行の高さが 44px 以上 |
| K4 | **全部の選択肢に手が届く** | 43件あっても、入れ子のスクロールに閉じ込められず最後まで出せる |
| K5 | 画面を下げてから開いても見える | 一覧を下にスクロールした状態で絞り込みを開いても選択肢が出る |
| K6 | コンディションも同じ | K1〜K5 がコンディションでも成り立つ |
| K7 | パソコンの見た目が変わっていない | PC（1280px）の絞り込みは今までどおり |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 合否 |
|---|---|---|
| 選択肢の見え方 | `viewer-provider-filter-option-*` が `toBeVisible()` | 見えること |
| 画面内に収まるか | 選択肢の行の `boundingBox()` の `x >= 0` かつ `x + width <= innerWidth` | 収まること |
| ページ全体の横はみ出し | `document.documentElement.scrollWidth <= innerWidth` | 収まること |
| 行の高さ | 行の `boundingBox().height` | **>= 44** |
| 全件到達 | 選択肢の総数 === fixture の仕入元の数 | 一致すること |
| 選べるか | 2件押した後、表の行数が減る | 減ること |
| 浮かぶパネルを使っていないこと | **ドロワーが開いている間、`document` 全体で `.comp-popover` が 0 件** | 0 件 |

## ④ 設計（How）

### 4-1. 金型 `MultiSelect` に「その場に出す」形を足す（既定は今のまま）

`frontend/src/components/MultiSelect.tsx` に次を足す。

```ts
/** 選択肢の出し方。既定 "popover"（ボタンを押すと浮かぶ＝今までどおり）。
 *  "inline" は浮かせず、その場にチェックボックスを並べる（浮かせられない場所＝Drawer の中で使う） */
layout?: "popover" | "inline";
```

- **既定は `"popover"`**。プロパティを渡さない呼び出し側は**1pxも変わらない**。呼び出し元は製品コード6か所・テスト2か所・Storybook 1か所（§4-6 に全数）。
- `"inline"` のときは `Popover` も開閉ボタンも使わず、次をその場に描く。
  1. 見出し行：`label`（項目名）と、右に「選択をクリア」（`clearLabel`。選択0件のときは出さない）
  2. 現在の選択の要約：0件なら `allLabel`（「すべて」）、1件以上なら**選んだ名前をカンマでつなぐ**（お手本 §2-1 の実測「IRWIN, AEG」に合わせる。`countLabel` は inline では使わない）
  3. 選択肢の一覧：1件＝1行。**行まるごとが押せる範囲**（`<label>` を全幅にする。お手本 §3）
- `data-testid` は今と同じ（`${testId}-option-${value}` / `${testId}-clear`）。既存テストの資産を壊さない。
- **`${testId}-button` は inline では出ない。** スマホ版の単体テストが押している箇所を §4-6 のとおり付け替える。

### 4-2. CSS（`frontend/src/components/MultiSelect.css`）— 修飾クラス方式

popover 限定の値は**子孫セレクタを使わない**（詳細度が上がって将来の上書きと競合するため）。TSX 側で修飾クラスを付ける。

| クラス | 付く条件 | 中身 |
|---|---|---|
| `.comp-multiselect__menu` | 共通 | 縦並び・`gap` だけを残す |
| `.comp-multiselect__menu--popover` | `layout="popover"` のときだけ TSX が付ける | **`min-width: var(--dropdown-min-width)`（400px）をここへ移す** |
| `.comp-multiselect__list--popover` | 同上 | **`max-height: var(--dropdown-max-h)`（200px）と `overflow: auto` をここへ移す** |
| `.comp-multiselect__option--inline` | `layout="inline"` のときだけ | `width: 100%` ／ `min-height: var(--size-icon-btn-lg)`（44px） |

- **inline には最小幅も高さの打ち切りも付けない。** 親（ドロワーの本文）の幅に従い、縦はドロワー本文のスクロールに任せる（`frontend/src/components/Drawer.css:85-89` が `overflow-y: auto`）。これで recon §3-4 の「43件中6.6件しか出せない」が解消する。
- 44px の根拠トークンは **`--size-icon-btn-lg`（`frontend/src/tokens.css:163`）に一本化**する。同じ 44px の `--field-h-lg`（同 `:166`）は「入力部品の高さ」で意味が違うため使わない。
- **お手本は 48dp だが、本便では既存トークン 44px を使う。** 48px のトークン新設は、上部の高さを詰める**便2**でまとめて起案する（`docs/specs/design-system/visual-language/benchmark/README.md` の PO決定1「既存の段に無い値はトークン追加の提案として design.md に起案する」に従う）。

### 4-3. 閲覧ページは「ドロワーの中だけ」inline にする

`frontend/src/pages/viewer/InventoryView.tsx`

- 今は `providerSelect` / `conditionSelect` を1つ作って PC（`:275-281`）とスマホのドロワー（`:352-353`）の**両方で使い回している**。これを「PC 用（popover）」と「ドロワー用（inline）」の2つに分ける。
- **PC 側（`:275-281`）の記述は変えない。**
- ドロワーの中（`:349-402`）だけ inline を使う。あわせて `:352` の `{isMobile && providerSelect}` の**二重ガードを外す**（`:349` が既に `isMobile &&` のため）。`:353` の `conditionSelect` と対称にする。

### 4-4. 検査は RED-first（不具合の一次証拠を CI で取る）— 手順を具体化

この端末では Playwright のブラウザが動かないため CI のログだけが一次情報。
ただし `.github/workflows/e2e.yml:35-37` に `concurrency: cancel-in-progress: true` があり、
トリガーは `pull_request` のみ（同 `:13-17`）。**まとめて push すると赤が1度も残らない。** 手順を固定する。

| 手順 | すること |
|---|---|
| 1 | 1本目のコミット（spec とヘルパーだけ。`frontend/src` は0行）を push して **PR を開く** |
| 2 | 集約ジョブ **`visual-language`**（`.github/workflows/e2e.yml:226-227`。同 `:224-225` に「必須チェックに入れる場合はこのジョブ名を指定する」と明記）の結論が出るまで**待つ** |
| 3 | 赤になった実行の URL とログの該当行を **PR 本文に貼る**（これが不具合の一次証拠。CI のログは期限で消えるため PR 本文に残す） |
| 4 | 2本目のコミット（直し）を push して緑を確認 |

- 手順1〜3の間、**必須チェックが赤の非 Draft の PR**が一時的に存在する（ADR-1015:36「B 区分の PR は Draft にしない」のため）。PR 本文の冒頭に「**RED-first の1本目です。意図して赤にしています。2本目で緑にします**」と書く。
- `detect-changes` のフィルタは `frontend/**`（同 `:52-53`）なので、1本目が `frontend/tests-e2e/` だけでもジョブは走る。

### 4-5. 検査の中身

- 置き場は `frontend/tests-e2e/visual-language/`（CI で走る唯一の場所。`frontend/playwright.config.ts:64`・`:69`・`:74`）。
- モックは `frontend/tests-e2e/visual-language/viewer-helpers.ts` 1か所に置く（PO 指示「分散させることは禁止」。`frontend/tests-e2e/visual-language/inventory-helpers.ts` と同じ作り）。
- 認証は `frontend/src/pages/viewer/api.ts:7` の `viewer_access_token` を `addInitScript` で `localStorage` に入れるだけ（`frontend/src/pages/viewer/ViewerApp.tsx:60` が有無だけで分岐する）。アプリ本体の `installAuthBypass` は不要。
- 在庫のモックのキーは **`"GET /viewer/inventory"`**（入口は `frontend/src/pages/viewer/api.ts:8` の `/api/v1/viewer/inventory`。`frontend/tests-e2e/utils/api-mock.ts:33`・`:66` が `/api/v1` を外す）。
- **fixture の形**（空振りで緑にならないように固める）
  - 仕入元を **20 件以上**（全件到達の検査のため。実機の実測は43件）
  - コンディションを **2 種類以上**
  - 行は 50 件以上（スクロールして開く経路の検査のため）
- 幅は spec 側で 360 と 390 を指定する。

### 4-6. `MultiSelect` の呼び出し元（全数）と影響

| file:line | 用途 | 本便の影響 |
|---|---|---|
| `frontend/src/pages/viewer/InventoryView.tsx:116` | 閲覧 提供者 | ドロワー用を inline 化（PC 用は popover のまま） |
| `frontend/src/pages/viewer/InventoryView.tsx:129` | 閲覧 コンディション | 同上 |
| `frontend/src/pages/inventory/InventoryFilterPanel.tsx:119`・`:134` | アプリ 絞り込みパネル | 不変 |
| `frontend/src/pages/inventory/InventoryToolbar.tsx:158`・`:168` | アプリ ツールバー | 不変 |
| `frontend/src/components/MultiSelect.test.tsx:16`・`:58` | 単体テスト | 不変（inline の分を追加） |
| `frontend/src/components/MultiSelect.stories.tsx:27` | Storybook（ブラウザテスト対象） | 不変 |

（`frontend/src/pages/inbox/SalesFormMultiSelect.tsx` は金型 `MultiSelect` を使わない別部品＝無関係）

### 4-7. 触らないもの

- `frontend/src/components/Popover.tsx` / `Popover.css`、`--z-dropdown`、`--dropdown-min-width`、`--dropdown-max-h` の**値そのもの**（金型の共通の値は動かさない。他画面への波及を避ける）。原因③の直しは C4 に送る。
- PC の見た目
- アプリ側 `/inventory`（`frontend/src/pages/inventory/`）
- バックエンド・DB・配線・`.github/`・`frontend/playwright.config.ts`

## ⑤ Acceptance Criteria

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | 新 spec が3つの project すべてで収集される | `cd frontend && E2E_NO_WEBSERVER=1 npx playwright test --list --project=vl-mobile-390` |
| A2 | **1本目のコミットで集約ジョブ `visual-language` が赤**（不具合の実在証拠）。実行 URL を PR 本文に記録 | GitHub Actions |
| A3 | 2本目のコミットで `visual-language` が緑 | 同上 |
| A4 | 360px・390px の両方で、提供者の選択肢が見えている | spec（`toBeVisible()`） |
| A5 | 選択肢の行が画面幅に収まる（`x>=0` かつ `x+width<=innerWidth`） | spec |
| A6 | 選択肢の行の高さが 44px 以上 | spec（ADR-140 の G4 と同じ測り方） |
| A7 | **ページ全体の横はみ出しが 0**（`documentElement.scrollWidth <= innerWidth`） | spec |
| A8 | **ドロワーが開いている間、`document` 全体で `.comp-popover` が 0 件** | spec（浮かぶパネルへの先祖返りを止める） |
| A9 | 2件選ぶと表の行数が減る | spec |
| A10 | **選択肢が 20 件以上の fixture で、最後の1件まで `toBeVisible()` にできる**（入れ子スクロールに閉じ込められない） | spec |
| A11 | **一覧を下にスクロールしてから絞り込みを開いても、選択肢が画面内に見える** | spec |
| A12 | コンディション（2種類以上の fixture）でも A4〜A10 が成り立つ | spec |
| A13 | PC（1280px）は popover のまま。**かつ一覧の幅が 400px 以上**（修飾クラスの付け忘れを捕まえる） | spec |
| A14 | ドロワーを開いた直後の初期フォーカスが定まっている（`frontend/src/components/Drawer.tsx:64-70`） | 単体テスト |
| A15 | 単体テスト：スマホでドロワーを開き、提供者を1件選ぶと絞り込まれる | `frontend/src/pages/viewer/InventoryView.test.tsx` |
| A16 | 暗いテーマでも inline の行が読める（背景・文字をトークン参照のみで書く） | 目視＋ CSS に直値が無いこと |
| A17 | 型検査が通る | `cd frontend && npx tsc --noEmit` |
| A18 | 手元検査が通る | `cd frontend && npm run check:all` |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/components/MultiSelect.tsx` | `layout` を追加（既定は今のまま）・修飾クラスを付ける |
| `frontend/src/components/MultiSelect.css` | inline 用クラス追加。`min-width` と `max-height` を popover 用クラスへ移す |
| `frontend/src/pages/viewer/InventoryView.tsx` | ドロワー用と PC 用に分け、ドロワー側だけ `layout="inline"`。`:352` の二重ガードを外す |
| `frontend/src/pages/viewer/InventoryView.test.tsx` | A14・A15 |
| `frontend/src/components/MultiSelect.test.tsx` | inline の描画と、popover が既定のままであることを固定 |
| `frontend/tests-e2e/visual-language/viewer-helpers.ts` | 新規（モックの唯一の置き場） |
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | 新規（合否） |
| `docs/handoff/viewer-inventory-mobile-filter/recon.md`・`design.md`・`review-opus.md` | 新規 |
| `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` | 新規（お手本の実測） |
| `docs/specs/design-system/visual-language/benchmark/README.md` | 子文書の表に1行追加 |
| `.claude-pipeline/active-work.d/release-viewer-inventory-mobile-filter.md` | 台帳 |

## ⑦ 戻し方

この PR を revert するだけ。`layout` の既定は `"popover"` で、足した CSS クラスは TSX が付けたときしか効かないため、戻しても他画面に影響は残らない。

## ⑧ 削除するファイル

無し。

## ⑨ 外部・過去事例の参照と我々への応用

| 事例 | 我々への応用 |
|---|---|
| メルカリの絞り込み（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` §0） | パネルの中では**浮かせない**。選択肢は「その場に横並びのボタンで出す」か「次の画面に進んでチェックボックスの一覧にする」の2通り |
| 同 §2-2（その場に出す形）・§3（次の画面のチェックボックス一覧） | **本便が作るのは第3の形**＝「次の画面のチェックボックス一覧を、画面を増やさずその場に置く」。画面を増やすと新しい画面の追加になり A 区分になるため、この形を採る |
| 同 §3（行まるごとを押せる範囲にする・選択の合図はチェックの塗りだけ） | そのまま採用 |
| 段階2のお手本2本（同 `README.md` 要点1） | WhatsApp・Meta も「行まるごと押させる」。3本目のお手本でも同じ結論＝方針として固い |
| PR #4602 の strict mode violation | パネルは `.comp-drawer-panel--open` で絞ってから測る |
| `frontend/tests-e2e/visual-language/inventory-helpers.ts` | モックの置き場は1本。spec 間で書き写さない |
| `docs/handoff/inventory-mobile-responsive/design.md` §13-5 | この端末では e2e の結果は CI ログだけが一次情報。だから RED-first で証拠を残す |

## ⑩ 弊害・トレードオフ

- 金型 `MultiSelect` の分岐が1つ増える。既定を変えないので影響は閉じているが、**金型の形が2つになる**こと自体は複雑さの増加。ADR-144 の観点では「呼び出し側で独自実装を作らせない」ための分岐なので、金型の外に同じものを作るより良いと判断した。
- 選択肢が多い仕入元ではドロワーが縦に長くなる（実機の実測で 43 件）。ドロワーの本文は縦スクロールする作り（`frontend/src/components/Drawer.css:85-89`）なので破綻しない。**今の 200px 打ち切り（6.6件）よりは確実に良い**が、43件を指で繰るのが実用に耐えるかは PO の実機確認で判断する。耐えないなら便2以降で「次の画面に進む」形（＝A 区分）を起案する。
- お手本の 48dp に対して 44px を使う（4px 低い）。便2 でまとめて見直す。
- 原因③（`Popover` のスクロール二重加算）は本便では直さない。閲覧ページのスマホ経路は inline 化で原因③を通らなくなるが、**PC 側とアプリ側には残る**（C4）。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts`（CI の集約ジョブ `visual-language` で毎 PR 走る）

| 守ること | 関所 | 外すと |
|---|---|---|
| スマホで絞り込みの選択肢が見えて押せる | 上記 spec（A4・A5・A9・A12） | 赤 |
| 絞り込みパネルを開いている間、浮かぶパネルを作らない | 上記 spec（A8） | 赤 |
| タップ領域 44px 以上 | 上記 spec（A6） | 赤 |
| 選択肢が多くても全件に手が届く | 上記 spec（A10） | 赤 |
| スクロール後に開いても使える | 上記 spec（A11） | 赤 |
| ページ全体の横はみ出しが 0 | 上記 spec（A7） | 赤 |
| PC の絞り込みが popover のまま・幅も今までどおり | 上記 spec（A13）＋ `frontend/src/components/MultiSelect.test.tsx` | 赤 |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| C1 | **便2: 上部の高さを詰める**。実測 **236px →** お手本 **146px**（内訳は recon §4・§5）。48px トークンの新設もここで起案 | 根拠の数値は取得済み。本便の後すぐ着手 |
| C2 | アプリ側 `/inventory` のスマホ絞り込み（原因②③④が同じく当てはまる） | 別便 |
| C3 | アプリ側 `/inventory` の上部操作台が画面外に出ている件（`docs/handoff/inventory-mobile-responsive/design.md` §13-2） | 別便 |
| C4 | **`Popover` 金型の2つの欠陥**: ⑴ `position: fixed` に `window.scrollY` を二重加算（`frontend/src/components/Popover.tsx:50`・`:55`・`:60`・`:66` × `frontend/src/components/Popover.css:16`。実測: 400px 下げると 400px ずれる） ⑵ 画面端で折り返さない（同 `:63-68`）。**金型を使う全画面に波及するため、影響の全数調査から始める別便** | 未着手・実測の証拠あり |
| C5 | `frontend/src/components/Popover.css:7-12` の `.comp-popover-overlay` は `Popover.tsx` が一度も描画しない死んだ CSS | 別便（掃除） |
| C6 | 撮影手順書 §0-3（文字入力の禁止）を買い物アプリにも当てはめるか | PO 判断待ち（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` §6） |
