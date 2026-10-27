# recon: 閲覧ページ スマホの検索欄とプルダウンをお手本と同じにする（便10＝大きさの便）

> この文書は何か（1行）: PO 指示「検索欄とプルダウンをお手本（メルカリ）と全く同じ UI/UX にする」の現物調査。
> **お手本の数値の読み方を訂正した**ので、ここが一番大事（§1）。

**土台**: `release/viewer-control-tap-size`（`origin/main` = 77b40a1ae）／調査日 2026-10-27
**対象**: 閲覧ページ `frontend/src/pages/viewer/InventoryView.tsx`（アプリの `frontend/src/pages/inventory/InventoryPage.tsx` とは別コード。ADR-1019）

## 1. お手本の「文字 16.3dp」は文字の大きさではない（**正本の読み方の訂正**）

`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41` が3行目のボタンの**幅**を実測で載せている:

| お手本のボタン | 文字数 | 実測幅 |
|---|---|---|
| 「おすすめ順」 | 5 | 90.7dp |
| 「絞り込み」 | 4 | 77.3dp |

**差を取ると 1文字 = 90.7 − 77.3 = 13.4dp**。左右の余白と絵文字は両方に同じだけ付くので引き算で消える
（同書 `:43` が「絵文字＋文字だけのボタン」と書いているとおり、どちらにも絵文字がある前提でも成立する）。
3つ目の「販売中のみ」（5文字・98.7dp）はチェックボックス付きで、余白＋印が 31.7dp＝他の2つの 23.7dp より
8dp 広い＝印の違いとして説明がつく（計算が破れない）。

同書 `:47-48` の「文字 16.3dp」は Android の構造データの**文字の箱の高さ**で、既定の行送り（約1.2倍）を含む。
**13.4 × 1.2 = 16.1 ≒ 16.3** で一致する。したがって:

| お手本の記載（箱の高さ） | 文字の大きさ | 我々の既存トークン |
|---|---|---|
| 16.3dp（操作ボタン・副ラベル） | 約 **13.6dp** | `--font-sm` = `frontend/src/tokens.css:15` = **13.6px** |
| 17.7dp（主ラベル） | 約 **14.8dp** | `--font-base` = 同 `:16` = **14.4px** |
| 14dp（札の中） | 約 11.7dp | （本便の対象外） |

**＝お手本に合わせる文字は 13.6px。16px はお手本より大きい**。新しい文字の大きさは作らない。
**高さの数値（48dp・60.7dp など）は箱の高さの実測そのままなので読み替え不要**。

**この逆算が依存している仮定（独立審査の指摘で明記）**: 未知数4・式3なので、13.4dp を決めているのは
**「`sort_menu`（おすすめ順）と `filter`（絞り込み）の余白＋絵文字が同じ幅」**という仮定1つだけ。
同書 `:43` がこの2つだけを「枠線のない、絵文字＋文字だけのボタン」と括っているので最も自然な読みだが、
**唯一解ではない**（別の組を同幅と仮定すれば 15.0dp も数学的には出る）。
同書 `:147` が「**フォントサイズの正確な値は原理的に取得不能**」と明記しており、独立検証はできない。
採用の根拠は**独立な2経路（幅の引き算 13.4dp と、箱の高さ 16.3 ÷ 行送り約1.2 = 13.6dp）が一致すること**。
なお「販売中のみ 98.7dp が計算を破らない」は上の仮定を置けば恒等式になるので、独立した検証ではない。

**PO 決定（2026-10-27）**: 上の事実を示したうえで「**お手本どおり（13.6px）**」を選択。
あわせて「**完全にお手本通り**」（パネルは画面の83%幅・選択肢の行は 60.7dp）も決定。後者は便12 で実施。

## 2. いまの3つの操作ボタン（現物）

スマホのときだけ出る。いずれも `frontend/src/components/Button.tsx` の金型で `variant="ghost"`・`size="sm"`。

| ボタン | 実装 | 渡しているクラス |
|---|---|---|
| シリーズ | `frontend/src/pages/viewer/InventoryView.tsx:411-424` | `viewer-toolbar__series` |
| 並び替え | `frontend/src/pages/viewer/InventoryView.tsx:426-439` | `viewer-toolbar__fixed` |
| 絞り込み | `frontend/src/pages/viewer/InventoryView.tsx:552-563` | `viewer-toolbar__fixed` |

並べている箱は `frontend/src/pages/viewer/viewer.css:26-49`。`flex-wrap: wrap`・`gap: var(--space-3)`（12px）で、
検索欄だけが単独で1行（`flex: 1 1 100%`）、**シリーズだけが縮む側**（`flex: 1 1 0; min-width: 0`）、
並び替えと絞り込みは縮まない（`flex: 0 0 auto`）。

山形は大きさ指定なし＝アダプターの既定 **24px**（`frontend/src/constants/icons-base.tsx:29`）。
`frontend/src/pages/viewer/viewer.css:56-60` は回転と `flex-shrink` だけで大きさに触らない。
`frontend/src/constants/iconSizes.ts` の `md` が 16px。

## 3. 文字と高さを決めている行

| 何 | 決めている行 | 実値 |
|---|---|---|
| sm の文字 | `frontend/src/components/Button.css:40-44` | `frontend/src/tokens.css:14` = **12px** |
| sm の横の余白 | 同 `:42` | `frontend/src/tokens.css:71` = **12px** |
| **枠線（幅の計算に入る）** | `frontend/src/components/Button.css:10`（`border: 1px solid transparent`。`variant="ghost"` は同 `:68-72` で色だけ変え幅を消さない） | **1px × 左右 = 2px／ボタン** |
| 文字とアイコンの隙間 | 同 `:6`（`gap: var(--space-2)`） | **8px** |
| スマホの行の高さ | 同 `:153-157`（`@media (max-width: 767px)` の `.comp-btn`） | `frontend/src/tokens.css:163` = **44px** |
| lg の高さ（スマホ） | 同 `:159-161` | `frontend/src/tokens.css:462` = **48px** |

**`@media` が後勝ちなので、スマホでは size を何にしても `.comp-btn` の 44px が base を上書きする**
（`.comp-btn--lg` だけが同じ `@media` の中で 48px に戻している）。
**新しい size を足すときは `@media` の中にも1行足さないと 44px に負ける**。

## 4. 横幅の算数（**訂正版**。初版は枠線と「(1)」を数え落として約30px 甘かった）

`frontend/src/pages/viewer/InventoryView.tsx:73` が `freshOnly` を `useState(true)` で始め、
同 `:131-136` の `filterActiveCount` が `freshOnly ? 1 : 0` を含むため、
**絞り込みボタンの既定表示は「絞り込み (1)」**（`frontend/src/locales/viewer/ja.json` の
`viewer.filter.buttonWithCount`）。これは既存検査
`frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:181-184`（A9）が固定している事実。

箱の内側幅は 360 − `--space-4`×2（`frontend/src/pages/viewer/viewer.css:23-24`・`frontend/src/tokens.css:72`）= **328px**。
全角1文字 = 1em（CI の Chromium には CJK フォントが入る）。ASCII は `" (1)"` ≈ 文字の大きさ×1.5。

1ボタンの幅 = 余白×2 ＋ 枠線2 ＋ 文字数×文字の大きさ ＋（山形があれば 隙間8 ＋ 山形）。

| 案（余白・文字・アイコン） | 並び替え | 絞り込み (1) | シリーズに必要 | 合計＋隙間24 | 328px |
|---|---|---|---|---|---|
| いま（12/12px/24） | 106 | 92 | 94 | 316 | 入る（**余り12**） |
| lg そのまま（24/16px/24） | 146 | 138 | 130 | 438 | **入らない（−110）** |
| lg＋余白12（12/16px/24） | 122 | 114 | 106 | 366 | **入らない（−38）** |
| lg＋余白12＋アイコン16（12/16px/16） | 114 | 114 | 98 | 350 | **入らない（−22）** |
| **採用（12/13.6px/16）** | 104.4 | 100.8 | 90.8 | **320.0** | **入る（余り8）** |
| 採用だがアイコン24のまま | 112.4 | 100.8 | 98.8 | 336.0 | **入らない（−8）** |

（初版は「いま」の行でシリーズの枠線2pxと隙間24を落として「余り38」と書いていた。
**正しくは現状でも余りは12px しかない**＝余裕はもともと薄い。独立審査の独立計算と一致。
ASCII の `" (1)"` は Liberation Sans でちょうど文字の1.5倍。最悪の DejaVu Sans でも採用案は余り4.8px で入る。）

内訳の例（採用案の並び替え）: 余白12×2 ＋ 枠線2 ＋ 文字13.6×4 ＋ 隙間8 ＋ アイコン16 = 104.4。
シリーズは「すべて」3文字（疑似データは全行 `series: ""`＝既定の `viewer.tabAll`）。

**＝文字13.6px でも、山形を 16px にしないと 360px で8px 足りずシリーズ名が切れる**。
390px では採用案の余りは38px。**360px だけが効く**（お手本を撮った端末も 1080px÷3 = **360dp**）。

## 5. 既存の歯止めは折り返し・はみ出しを捕まえない（**初版の訂正**）

`frontend/src/pages/viewer/viewer.css:37-43` でシリーズは `flex: 1 1 0; min-width: 0; overflow: hidden`。
**flex-basis が 0 なので折り返しの判定に寄与せず**、並び替えと絞り込みが合計 328px 以内なら折り返さない。
シリーズは必要幅まで縮み、中の `.viewer-toolbar__label` が `overflow: hidden` なのでページも溢れない。

→ `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:120-130`（A2 y が同じ・A3 右端が画面幅以内・
高さ44px以上）と同 `:39-45`（ページの横はみ出し）は、**幅が足りない案を入れても全部緑のまま**。
**切れ（シリーズ名が読めるか）を直接測る検査だけが唯一の歯止め**で、それは今1件も無い。

**`.viewer-toolbar__label` は並び替え側にもある**（`frontend/src/pages/viewer/InventoryView.tsx:421`・`:436`）。
並び替えは `flex: 0 0 auto` で絶対に切れないので、**検査で `.first()` のような取り方をすると常に緑の空振り**になる。
`viewer-tab-select` の配下に限ること。

## 6. 上部の高さ

便4 で **124px**。内訳は `frontend/src/pages/viewer/viewer.css:26-32` の上下 `margin: var(--space-3) 0`（12px）と
`gap: var(--space-3)`（12px）から 12＋44（検索欄）＋12＋44（3ボタン）＋12 = **124**（便4 の実測と一致）。
**検索欄も3ボタンも48pxにすると 12＋48＋12＋48＋12 = 132px**。お手本の上部は **146dp**
（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:35`）＝お手本より低いまま。

**`MAX_TOP_Y = 128` は3本に複製されている**:
`frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:27`・
`frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts:30`・
`frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts:25`。**1本だけ直すと残り2本が赤になる**。

## 7. 検索欄の現物（2か所）

| どこ | 実装 | いまの指定 |
|---|---|---|
| 上部 | `frontend/src/pages/viewer/InventoryView.tsx:362` | `className="field-h-md field-w-md viewer-toolbar__search"` |
| 絞り込みパネルの中（候補を絞る） | 同 `:266`（提供者）・`:293`（コンディション） | `className="field-h-md field-w-lg"` |

高さの金型は **3段しかない**（`frontend/src/components/field-size.css:7-9`）:
`--field-h-sm` 28px・`--field-h-md` 36px・`--field-h-lg` 44px（`frontend/src/tokens.css:164-166`）。
**48px の段は無い**。さらに `frontend/src/components/FormField.css:533-540` の `@media (max-width: 767px)` が
**`.comp-field__input`・`.comp-field__select`・`.comp-select__control` の3つ**に
`--comp-input-height-mobile`（`frontend/src/tokens.css:487` = 44px）を当て、
**詳細度が同じで後ろにあるため `.field-h-*` に勝つ**（だから今はどの段を選んでもスマホでは 44px）。

**勝たせ方の先例がある**: 幅の方は `frontend/src/components/field-size.css:14-22` が
`.comp-field__input.field-w-*`（詳細度 0,2,0）を**併記**して金型側の `width: 100%` に勝たせている
（同ファイルのコメントが design.md §AW AW-2b・§AY AY-2p を根拠として挙げる）。
**高さの4段目も同じ型でよい**。

`TextFieldControl` は **80ファイル**で使用中＝`--comp-input-height-mobile` を 44→48 に変える案は全アプリに波及する。
**4段目を足す案なら、使う画面だけに効く**。

## 8. プルダウンの現物（お手本との差）

**すでにお手本と一致している3点**（直す必要が無い）:

| 観点 | お手本 | 現物 |
|---|---|---|
| 選択肢の行の押せる範囲 | 行まるごと | `<label>` が行全体（`frontend/src/pages/viewer/InventoryView.tsx:441-461`・`frontend/src/components/MultiSelect.tsx:95-107`） |
| 選択肢の行の文字 | 約13.6dp | `--font-sm` 13.6px（`frontend/src/pages/viewer/viewer.css:74`・`frontend/src/components/MultiSelect.css:33`） |
| 浮かぶプルダウン | 使わない | **スマホでは使っていない**（提供者・コンディションは行を押して次の画面＝`layout="row"`→`layout="inline"`）。PC だけ popover |

**残る差**:

| # | 観点 | お手本 | 現物 | 便 |
|---|---|---|---|---|
| 1 | 上部の検索欄の高さ | 48dp | 44px | 便10 |
| 2 | パネル内の候補を絞る検索欄 | 268×48dp | 44px | 便10 |
| 3 | 操作ボタン3つの高さ | 48dp | 44px | 便10 |
| 4 | 同 文字 | 約13.6dp | 12px | 便10 |
| 5 | 「決定する」の高さ | 268×48dp・パネル下に固定 | 44px・パネル下に固定（`frontend/src/pages/viewer/InventoryView.tsx:328-339`・`frontend/src/components/Drawer.css:100-108`） | 便10 |
| 6 | 現在値の出し方（複数選択） | 選んだ名前をカンマつなぎ／未選択「指定しない」 | **件数「3件」**（`frontend/src/pages/viewer/InventoryView.tsx:210` → `viewer.filter.count`） | 便11 |
| 7 | 選択肢が少ない項目（2〜6件） | その場に横並びボタン（48dp・間隔8dp・折り返す） | **縦の一覧**（`layout="inline"`） | 便12 |
| 8 | チェックボックス一覧の行 | 幅いっぱい×60.7dp・印が行の左48dpを占める | 44px・印16px（`frontend/src/tokens.css:227`）＋余白8px | 便12 |
| 9 | パネルの幅 | 画面の83%（左に60dp残す） | 全幅 | 便12 |

## 9. 既存の歯止め（便10 に関わるもの）

| ファイル | 記号 | 何を測っているか |
|---|---|---|
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | A1 | 一覧の先頭カードの y ≤ 128（360・390の2幅） |
| 同 | A2・A3・A4 | 3つが1行・右端が画面幅以内・高さ44px以上・横はみ出し無し |
| 同 | A9 | 絞り込みボタンの文字が既定で「(1)」を含む |
| `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts` | B4・B5・B9 | 選択肢の行の高さ44px以上・8行以上見える |
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | A5・A6 | 選択画面の行の高さ44px以上・一度に8〜20件見える |

**無いもの**: 検索欄の高さを測る検査／操作ボタンの**文字の大きさ**を測る検査／
シリーズ名が**切れていない**ことを測る検査／「決定する」の高さを測る検査。

## 10. 取り違えやすい点（次に読む人へ）

- 操作部品が 44px になるのは**タップ端末だからではなく画面幅 767px 以下だから**。CI の3 project のうち
  360・390 で効き、1280 では効かない。
- `frontend/src/components/buttonAppearance.ts:36` は `variant="tab"` のとき **size を無視する**。
  size を足すときはここを通る。
- `frontend/src/components/ButtonLink.tsx:37-42` も同じ `buttonAppearance` を呼ぶ。size は共有される。

## 関連
- ADR-1019（閲覧ページはアプリと別コード）
- 便5 `docs/handoff/viewer-choice-sheet/design.md`（枠なしの文字ボタンにした便）
- 便4 `docs/handoff/viewer-header-remove/design.md`（上部 124px にした便）
- 設計は docs/handoff/viewer-control-tap-size/design.md
