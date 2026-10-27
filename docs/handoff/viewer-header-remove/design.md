# design: 閲覧ページのヘッダーを丸ごと消す（便4）

> この文書は何か（1行）: スマホの上部にある帯（題「在庫一覧」・最終更新・言語）を無くして商品をさらに上から見せ、最終更新と言語は絞り込み画面の中へ移す便の設計。

**日付**: 2026-10-26
**親（あるべき姿）**: `docs/specs/design-system/visual-language/README.md`
**recon**: `docs/handoff/viewer-header-remove/recon.md`
**お手本の実測**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:35`（一覧が始まるまで 146dp ＝ 48×3）
**前便**: 便5 `docs/handoff/viewer-choice-sheet/design.md`（PR #4759）／便3 `docs/handoff/viewer-top-compact/design.md`（PR #4752・本番反映済み）
**対象ADR**: ADR-1019（閲覧ページ）／ADR-144（UI 金型ガバナンス）／ADR-140（タップ領域44px）／ADR-067（トークン参照のみ）／ADR-027（文言は t() 経由）／ADR-137（スマホ判定は `useIsMobile`）

## ① 区分：A（見た目と操作の変更）

| 項目 | 内容 |
|---|---|
| PO 決定（2026-10-25） | **「ヘッダーを丸ごと消す」**＝「最終更新」も「言語」も絞り込み画面の中へ送る（3案から選択）。弊害（データの鮮度が一目で分からなくなる）は提示済み |
| 着手指示（2026-10-26） | 次にやる便として「1」（＝本便）を受領 |
| 金型 | **新設・変更なし**（`SelectControl`・`Drawer` はそのまま使う） |

## ② KGI（PO が実機で○×を判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | 上部の帯が**消える** | スマホで「在庫一覧」「最終更新 HH:MM」「言語」の帯が無く、検索欄が一番上にある |
| K2 | 商品が**さらに上から**始まる | 便5 より1行ぶん（68px）上がる（192px → 124px の計算） |
| K3 | 「最終更新」が**絞り込み画面の中**で見られる | 絞り込みを開くと一番下に「最終更新 HH:MM」がある |
| K4 | 「言語」も**絞り込み画面の中**で切り替えられる | 同じ場所で日本語/English を選べて、画面の文字が切り替わる |
| K5 | PC は**今のまま** | パソコンでは帯が残り、最終更新と言語も今の場所にある |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 合否 |
|---|---|---|
| 上部の高さ | 先頭カード（`.comp-table__card`）の y をスクロールせずに測る | **128 以内**（計算値124・現状192） |
| 帯の有無（スマホ） | `.viewer-header` の数 | **0 件** |
| 帯の有無（PC） | `.viewer-header` の数 | **1 件**（不変） |
| 最終更新の位置 | 絞り込みを開いたとき、`viewer-updated` が**開いているパネルの中**にあるか | ある |
| 言語の位置 | 同様に `viewer-lang` | ある・高さ **>= 44** |
| 見出し | ページの `h1` の数と文字 | **1 件**・「在庫一覧」（ただし見た目の幅は **<= 1px**） |
| 横はみ出し | `documentElement.scrollWidth <= innerWidth` | 収まること |
| 閲覧ページの JS | `frontend/scripts/check-viewer-bundle.js` | **300KB 以内**（便5 実測260.0KB） |

## ④ 設計（How）

### 4-1. 帯はスマホだけ消す（`frontend/src/pages/viewer/InventoryView.tsx:408-424`）

いまの帯は `isMobile` の分岐の外にあり **PC でも同じものが出ている**（recon §2）。
そこで帯全体を **`{!isMobile && ( … )}`** で囲む。中身（題・最終更新・言語）は**1行も書き換えない**。

### 4-2. 読み上げ用の見出しを残す（**クラスは共通の置き場に1つだけ**・PO 決定）

帯を消すと**ページから `h1` が消える**（recon §3）。「見た目は消して読み上げには残す」用法は、
デザインシステムの正本が**題名の金型の対象外として明記**している（`docs/specs/design-system/component-ssot/page-title/design.md:24`
の「LoginPage の sr-only（視覚表示なしの読み上げ用）」）＝**金型の新設は不要**。
専用の部品（金型）は現時点で存在しない（`frontend/src/components/` に該当なし。2026-10-26 に全件確認）。

**PO 決定（2026-10-26）**: 「**共通の置き場に1つにまとめる**」。同じ作りの定義を2か所に持たない（SSOT）。

| 手順 | 変更 |
|---|---|
| ① 共通ファイルを新設 | `frontend/src/components/sr-only.css` に `.sr-only` の定義を**そのまま移す**（内容は一字一句変えない）。冒頭に出典コメント（元の場所と、閲覧ページが本体 CSS を読まない理由） |
| ② 両方のバンドルから読む | `frontend/src/index.css:1-2` の `@import` に1行追加（`./components/field-size.css` と同じ層＝**閲覧ページとアプリ本体が共通で使えるユーティリティの既存の置き場**。閲覧ページの検索欄が実際に `field-h-md field-w-md` を使っている＝先例） |
| ③ 元の定義を消す | `frontend/src/pages-layout.css:227-238` の `.sr-only` を削除し、1行の案内コメントだけ残す（**定義が1か所になる**） |
| ④ 閲覧ページで使う | スマホのときだけ `<h1 className="sr-only">{t("viewer.title")}</h1>` を `main` の直前に置く（文言キーは既存の `viewer.title`） |

**この変更が及ぶ範囲（事実）**: `.sr-only` の利用箇所はアプリ本体の2か所だけ
（`frontend/src/pages/login/LoginPage.tsx:79` の `h1`・`frontend/src/pages/inbox/InboxMessageThread.tsx:803`・`:850`）。
定義の**中身は変えず置き場だけ**変える。アプリ本体の入口も `index.css` を読む（`frontend/src/main.tsx:4`）ため、両方に届く。

**守り手（SSOT が崩れないように）**: `.sr-only` の**定義が src 全体で1か所だけ**であることを単体テストで固定する（⑤ C17）。
**正直に書く**: この2か所（ログイン・受信箱）を見ている自動検査は**存在しない**
（`frontend/tests-e2e/login.spec.ts` は CI の必須ジョブでは走らない＝`Playwright E2E (chromium)` が skipping）。
したがって**ログイン画面と受信箱の目視確認を PO にお願いする**（PO 了承済み）。

### 4-2b. 関所 `check:nav-sync` の除外に閲覧ページを入れる（実装中に判明・2026-10-26）

`frontend/scripts/check-nav-title-sync.js` は「`h1`/`h2` の題名は `t("nav.xxx")` か `usePageTitle()` を使う」を強制する。
4-2④ の隠し見出し（`<h1 className="sr-only">{t("viewer.title")}</h1>`）はこれに当たって赤になる
（既存の PC 側の帯 `viewer-header__title` は、除外語の並び（`frontend/scripts/check-nav-title-sync.js:48`）に
`title` が含まれるため**偶然**見逃されていただけ）。

**閲覧ページではこの規則が原理的に満たせない**（確認した事実）:
- 閲覧ページの辞書のトップレベルは `common` / `suppliers` / `viewer` だけで、**`nav` 名前空間が無い**（`frontend/src/locales/viewer/ja.json`）
- 閲覧ページは**サイドバーを持たない別アプリ**（入口 `frontend/viewer/index.html`・ADR-1019）
- 関所には**ディレクトリ単位の「ナビ外ページ」除外枠**が既にあり、`register` 等が入っている（`frontend/scripts/check-nav-title-sync.js:35-39`）
- デザインシステムの正本も「ナビ枠外画面」を題名金型の対象外としている（`docs/specs/design-system/component-ssot/page-title/design.md:24`）

→ **`EXCLUDE_DIRS` に `viewer` を1行足す**（ファイル名単位ではなくディレクトリ単位＝同名ファイルの取り違えが起きない）。
関所の方針を変えるのではなく、**既にある区分に当てはめる**変更。実測: 追加後 `node scripts/check-nav-title-sync.js` は PASSED。

### 4-3. 最終更新と言語は絞り込み画面の一番下へ

絞り込みドロワーの最初の画面（`filterView === "root"` の `.viewer-filter-body`）の**一番下**に、
区切り線を1本引いた上で置く。ドロワーは `isMobile &&` の中（`frontend/src/pages/viewer/InventoryView.tsx:558`）なので
**スマホのときだけ描かれる**＝PC の帯と**同じ目印が同時に存在しない**（recon §4）。

| 要素 | 形 | 目印 |
|---|---|---|
| 最終更新 | `span`（文言・値は帯と同じ `t("viewer.lastUpdated", { time: formatUpdatedAt(data.updated_at) })`） | `viewer-updated`（帯と同じ名前。PC と排他なので衝突しない） |
| 言語 | 帯と同じ `SelectControl size="sm"`・`aria-label={t("viewer.language.label")}`・`changeLang` | `viewer-lang` |

CSS は viewer.css に1クラス追加（ADR-067 で var() のみ）:

| クラス | 指定 | 理由 |
|---|---|---|
| `.viewer-filter-meta` | `display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); padding-top: var(--space-3); margin-top: var(--space-2); border-top: 1px solid var(--border); font-size: var(--font-sm); color: var(--text-secondary);` | 絞り込みの項目と見分けがつくよう区切る。言語の部品の高さは 767px 以下で 44px になる（`frontend/src/components/FormField.css:534-539`） |

### 4-4. 上部の高さの基準を更新する

便3 の spec が持っている「192px 以内」（`frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` の `MAX_TOP_Y`）と
便5 の spec の同じ値（`frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts` の `MAX_TOP_Y`）を、
**128** に更新する（計算値124・余裕4px）。**基準を緩めるのではなく厳しくする**変更。

### 4-5. 触らないもの

PC の帯・`ContentToolbar`・`Tabs`／金型ファイル／便2 の絞り込みの状態機械／便5 のパネル／
`Popover` 金型（C2 の宿題のまま）／アプリ側 `/inventory`／バックエンド・DB・`.github/`／`viewer.title` 以外の文言。

## ⑤ Acceptance Criteria

**測り方の共通の決まり**: `scrollIntoView` を使わずに測る。スマホは 360・390 の両方。開いているパネルは `.comp-drawer-panel--open` で絞る（便5 と同じ）。

| # | 基準 | 検証方法 |
|---|---|---|
| C1 | 先頭カードの y が **128 以内** | 新 spec |
| C2 | スマホに `.viewer-header` が **0 件** | 新 spec |
| C3 | 絞り込みを開くと `viewer-updated` が**開いているパネルの中**に見え、文字に時刻（`:`）が入る | 新 spec |
| C4 | 同じ場所に `viewer-lang` があり、高さ **44px 以上** | 新 spec |
| C5 | `viewer-lang` を `en` にすると**画面の文言が英語になる**（絞り込みボタンが `Filter` を含む） | 新 spec |
| C6 | ページの `h1` が **1 件**で文字は「在庫一覧」、**見た目の幅は 1px 以下**（読み上げには残る） | 新 spec |
| C7 | 横はみ出しが 0 | 新 spec |
| C8 | PC（1280px）は不変＝`.viewer-header` が 1 件・その中に `viewer-updated` と `viewer-lang` が見える | 新 spec |
| C9 | 便3・便5 の上部の高さ基準を **128** に更新しても緑（A1・B11） | 既存 `viewer-top-compact.spec.ts`・`viewer-choice-sheet.spec.ts` |
| C10 | 便2 の絞り込み副画面（A1〜A18）が壊れていない | 既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` |
| C11 | 単体テストが通る（`viewer-updated` を見る既存3件は PC 経路のまま） | `frontend/src/pages/viewer/ViewerApp.test.tsx`・`frontend/src/pages/viewer/InventoryView.test.tsx` |
| C12 | スマホ経路の単体テストで帯が無いこと・ドロワーの中に最終更新があることを固定 | `frontend/src/pages/viewer/InventoryView.test.tsx`（追加） |
| C17 | `.sr-only` の**定義が `frontend/src` 全体で1か所だけ**（SSOT。2か所に増えたら赤） | `frontend/src/components/srOnlySsot.test.ts`（新設・CSS を読んで数える） |
| C18 | 閲覧ページの隠し見出しが**効いている**（C6 と同じ・共通ファイルが閲覧ページに届いている証拠） | 新 spec |
| C13 | 辞書のキーは**増えない**（ja/en 一致） | `cd frontend && npm run check:all` |
| C14 | 閲覧ページの JS が 300KB 以内 | `frontend/scripts/check-viewer-bundle.js` |
| C15 | 型検査が通る | `cd frontend && npx tsc --noEmit` |
| C16 | 手元検査が通る（変更ファイルは警告0） | `cd frontend && npm run check:all` ＋ `npx eslint --max-warnings=0 <変更ファイル>` |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/pages/viewer/InventoryView.tsx` | 帯を `!isMobile` で囲む／隠し `h1`／ドロワー最下部に最終更新・言語 |
| `frontend/src/components/sr-only.css` | **新設**（`.sr-only` の定義をそのまま移す） |
| `frontend/src/index.css` | `@import "./components/sr-only.css";` の1行追加 |
| `frontend/src/pages-layout.css` | `.sr-only` の定義を削除（案内コメントのみ残す） |
| `frontend/src/components/srOnlySsot.test.ts` | **新設**（定義が1か所だけであることの守り手・C17） |
| `frontend/scripts/check-nav-title-sync.js` | `EXCLUDE_DIRS` に `viewer` を1行追加（下記 4-2b の理由） |
| `frontend/src/pages/viewer/viewer.css` | `.viewer-filter-meta` の1クラス（隠しクラスは共通ファイルに置くため viewer.css には作らない） |
| `frontend/src/pages/viewer/InventoryView.test.tsx` | C12 の追加 |
| `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts` | **新設**（C1〜C8） |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts`・`viewer-choice-sheet.spec.ts` | `MAX_TOP_Y` を 192 → **128** |
| `docs/handoff/viewer-header-remove/recon.md`・`design.md` | 新規 |
| `.claude-pipeline/active-work.d/release-viewer-header-remove.md` | 台帳 |

## ⑦ 戻し方

この PR を revert するだけ。金型に触らないので他画面への影響は無い。

## ⑧ 削除するファイル

無し（既存ファイルの行の書き換えはある。PR 本文の「削除するファイル:」に列挙する）。

## ⑨ 外部・過去事例の参照と我々への応用

| 事例 | 我々への応用 |
|---|---|
| メルカリ（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:35`） | 一覧が始まるまで **146dp**。アプリ名や更新時刻の帯を一覧の上に置いていない。本便で 124px になり**お手本より小さくなる** |
| `frontend/src/pages/login/LoginPage.tsx:79` | 見た目を消しても `h1` を残す作法（`.sr-only`）。閲覧ページには本体 CSS が届かないため、**同じ作りのクラスを閲覧ページ側に1つ置く**（design 4-2） |
| 便5（`docs/handoff/viewer-choice-sheet/design.md`） | パネルの中に項目を足す形・開いているパネルの絞り方（`.comp-drawer-panel--open`）。本便の最終更新・言語も同じ場所に足す |
| 便3（`docs/handoff/viewer-top-compact/design.md`） | 上部の高さを spec で固定する作法。**基準値も一緒に更新する**（便3 ⑫D2 の注意そのもの） |

## ⑩ 弊害・トレードオフ

- **最終更新が1タップ奥になる**（PO が選択時に了承済み）。「いつ時点のデータか」を知るには絞り込みを開く必要がある。
- **言語の切り替えも1タップ奥**になる。言語は一度決めたら変えない設定なので影響は小さい。
- 画面に見える題が無くなる（PWA のタイトルバー「Sales Anchor Viewer」が担う）。読み上げ用の `h1` は残す。
- **工事範囲がアプリ本体の CSS にも及ぶ**（`.sr-only` の置き場を共通へ移すため）。中身は変えず置き場だけだが、
  利用2か所（ログイン画面の見出し・受信箱の送信ボタンの読み上げ文字）に**自動検査が無い**ため、目視確認が必要（PO 了承済み）。
- 戻すときは本 PR の revert 1回で、`.sr-only` も元の場所に戻る。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts`（CI の集約ジョブ `visual-language` で毎 PR 走る。`frontend/playwright.config.ts` の `testMatch` が `visual-language/` 配下に限るため、**ここに置かないと1本も走らない**）

| 守ること | 関所 | 外すと |
|---|---|---|
| 上部が128px 以内 | 上記 spec（C1）＋既存2本の `MAX_TOP_Y` | 赤 |
| スマホに帯が戻らない | 上記 spec（C2） | 赤 |
| 最終更新・言語が絞り込み画面で使える | 上記 spec（C3・C4・C5） | 赤 |
| 読み上げ用の見出しが残る | 上記 spec（C6） | 赤 |
| PC が今のまま | 上記 spec（C8） | 赤 |
| 便2 の絞り込みが壊れない | `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | 赤 |
| 閲覧ページの JS が 300KB 以内 | `frontend/scripts/check-viewer-bundle.js` | 赤 |
| `.sr-only` の定義が1か所だけ（SSOT） | `frontend/src/components/srOnlySsot.test.ts` | 赤 |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| E1 | 48px 行・16px 文字への底上げ（お手本と同じ）。上部の基準（128px）も同時に見直す | PO の実機確認の次の候補（便5 ⑫D2） |
| E2 | シリーズのパネルに候補を絞る検索欄を足すか | PO の使用感次第（便5 ⑫D1） |
| E3 | 閉じた `Drawer` の中身が Tab で辿れる・読み上げに乗る（金型側） | 便5 ⑫D5 のまま |
| E4 | `Popover` 金型の2欠陥（便2 C2） | そのまま |
