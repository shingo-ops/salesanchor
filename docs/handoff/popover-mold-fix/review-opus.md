# review-opus: 浮かぶ選択肢パネルの土台（Popover 金型）の直し — 独立審査

> この文書は何か（1行）: 実装（`Popover.tsx` ほか3ファイル）と設計書を、設計担当（Opus）が自分で動かした検査の結果だけを根拠に点検した記録。

**日付**: 2026-10-26
**審査対象**: 作業ツリー `release/popover-mold-fix`（土台 `03cb7cae5` ＝ `origin/main`）
**設計**: `docs/handoff/popover-mold-fix/design.md`／**recon**: 同 `recon.md`

## 1. 自分で動かした一次情報

| 何を | コマンド | 結果 |
|---|---|---|
| 新しい単体テスト | `npx vitest run src/components/Popover.test.tsx` | **9件すべて緑**（直す前は9件すべて赤＝design ⑤ C16） |
| 既存の `MultiSelect` 単体 | `npx vitest run src/components/MultiSelect.test.tsx` | **18件すべて緑**（C11） |
| 型検査 | `npx tsc --noEmit` | **0件**（C14） |
| 手元の関所一式 | `npm run check:all` | **EXIT=0**（C15。警告59件はすべて変更前から在るもので、本便の変更ファイルは0） |
| 全単体テスト（unit プロジェクト） | `npm run test:unit` | **146ファイル・1723件中 1720件緑／3件赤**。赤3件はすべて `Test timed out in 5000ms`＝この端末の遅さで、`--testTimeout=30000` を付けると全件緑（§3 R9） |
| 変更ファイルの警告0 | `npx eslint --max-warnings=0 src/components/Popover.tsx src/components/Popover.test.tsx` | **0件**（C15） |
| トークンの値 | `grep -- "--space-2:\|--space-4:\|--space-6:\|--dropdown-min-width" src/tokens.css` | `--space-2: 8px`・`--space-4: 16px`・`--space-6: 24px`・`--dropdown-min-width: 400px`＝**design 4-3 の前提どおり** |
| 先例の最低間隔 | `sed -n '75,95p' src/components/ContextMenu.tsx` | `const margin = 8;`（`:82`）＝実装のコメントの参照先は正しい |

## 2. 重大な指摘（1件・この審査で直した）

### R1. 影響範囲の記述が誤っていた（閲覧ページの PC 幅も Popover を使う）

recon §4 と design ① は「閲覧ページは Popover を使っていないので無影響」と書いていた。**誤り**。

- `frontend/src/pages/viewer/InventoryView.tsx:201-212`（`providerSelect`）・`:214-225`（`conditionSelect`）は
  **`layout` を渡していない＝既定の popover**。
- 描画されるのは PC 枝だけ（`:547` の `isMobile ?` の else・`:597-598` の `bottomLeft`）。
  スマホ幅は `layout="row"`/`"inline"`（`:228` 以降）なので**スマホは無影響という結論だけが正しかった**。
- コード内のコメント `:228` 自身が「PC 側（上の popover 版 providerSelect/conditionSelect）」と書いており、
  **現物を読めば分かる誤り**だった。

**直した所**: `recon.md` §4 の表と注記、`design.md` ①（影響画面）・②（K5 を追加）・4-5（触らないもの）。

**この誤りが設計を変えるか**: 変えない（直し方は同じ）。ただし次の2点で意味がある。

1. **良い方向に効く**: 閲覧ページを PC で下へ送ってから絞り込みを開いたときのずれも同時に直る（K5）。
2. **歯止めが既にある**: 既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:336-349`（A18）が
   「PC 1280 では `.comp-popover` の幅 >= 400」を固定している。CSS の `min()` 化で PC が縮んでいたら**既存検査が赤になる**。
   1280 幅では `min(400px, 1280-24=1256px) = 400px` なので縮まない（計算で確認）。

## 3. 残す指摘（直さない・起票する）

| # | 指摘 | 判断 |
|---|---|---|
| R2 | `.comp-popover` の `max-width: calc(100vw - var(--space-4))` の `100vw` は**縦スクロールバーの幅を含む**。パネルが画面より広くて上限が効く場面（狭い画面）では、右端が最大で数 px スクロールバーの下に入り得る | **今回は直さない**。上限が効くのは画面幅 < 424px のときで、その幅ではスクロールバーは重ならない形（モバイル）。本番で popover が出るのは非モバイル幅のみ（下の R4）なので実害が無い。⑫ **C-sb** として起票 |
| R3 | 下に入らないときパネルがボタンに重なる（`top` を画面内へ寄せるだけで上下反転はしない） | PO 決定で今回は見送り。⑫ **C-up** として既に起票済み |
| R4 | トリガーが画面の外へスクロールして行ったとき、パネルは**画面の端に貼りついて残る**（置き去りにはならないが、押したボタンが見えないのにパネルが見える） | 今回の範囲外。本番で popover が出るのは非モバイル幅のみで、縦に長い一覧の上にある操作台なので起きにくい。⑫ **C-out** として起票 |
| R5 | スクロール中は1イベントごとに位置計算＋再描画が走る | 購読は開いている間だけ・passive・計算は算術のみ。⑫ **C-perf** として既に起票済み |
| R6 | 単体テストが `HTMLElement.prototype.offsetWidth/offsetHeight` を差し替えて戻していない | `frontend/vite.config.ts:31,61,78` に `isolate: false` が無い＝**テストファイルごとに環境が作り直される**ので他ファイルへ漏れない。全単体テストを通して確認（§1） |

### R7. 設計の C9（選択肢1行44px以上・不変）が現物と合っていなかった

`MultiSelect.css` で 44px（`--size-icon-btn-lg`）が付いているのは `--inline`（`:42-45`）と空文言（`:77`）だけで、
**popover 層の `.comp-multiselect__option`（`:28-36`）には `min-height` が無い**（便1 の実測も30px）。
「不変」と書いたまま spec で 44px を要求すると**直していない所を赤にする**ので、C9 を取り下げ、⑫ **C-tap** として起票した。
新 spec は6本（B1・B2・B3・B4×2・B6）。

### R8. `tests-e2e/` は eslint の対象外（C15 の書き方が実態と合っていない）

`frontend/eslint.config.js` の `files` は `src/**/*.{ts,tsx}` だけ。`tests-e2e/` のファイルに
`--max-warnings=0` を掛けると**既存 spec でも**「File ignored because no matching configuration was supplied」の
警告1件で落ちる。本便固有の欠陥ではないので、C15 の但し書きとして記録し、新 spec は `tsc --noEmit` で確認した。

### R9. この端末の単体テストは既定5秒上限で時間切れになるものがある（本便とは無関係）

全単体（`npm run test:unit`）で `SoldOutResultsPanel.test.tsx` 1件・`InventoryPage.toolbar.test.tsx` 2件が赤。
**どちらも `--testTimeout=30000` を付けると全件緑**（前者9/9・後者5/5）。失敗理由は `Test timed out in 5000ms` で、
読み込みに8〜10秒かかる端末の遅さ。`InventoryPage.toolbar.test.tsx` は在庫表の操作台＝`MultiSelect` を使う所なので
**本便の影響でないことを確かめる価値があった**（確かめた結果、無関係）。

## 4. 実装そのものの点検（設計との一致）

| 設計 | 実装 | 一致 |
|---|---|---|
| 4-1 `scrollY`/`scrollX` を8か所すべて削除 | `Popover.tsx:52-70`（4 placement）。`window.scroll` の参照は `calcPosition` に**1つも残っていない** | ○ |
| 4-2 ContextMenu と同じ寄せ方・最低間隔8px | `Popover.tsx:72-82`。`ContextMenu.tsx:82-94` と**同じ順序・同じ式** | ○ |
| 4-3 CSS は `max-width` と `min()` の2か所・トークン参照のみ | `Popover.css` に `max-width: calc(100vw - var(--space-4))`、`MultiSelect.css:12-16` に `min-width: min(var(--dropdown-min-width), calc(100vw - var(--space-6)))`。**直値は無い** | ○ |
| 4-4 開いている間だけ `resize`/`scroll` を購読・時間に頼る後片付けをしない | `Popover.tsx:110-133`。`removeEventListener` で後始末。`setTimeout` は**使っていない** | ○ |
| 4-5 公開 props を増やさない | `PopoverProps` は変更なし（`:23-36`）＝呼び出し側の書き換え0 | ○ |

**既定の見た目が変わらないこと**（K4）: `calcPosition` の寄せ処理は `left + panelW + margin > innerWidth` 等の
**はみ出すときだけ**値を書き換える条件付き。スクロール量0・画面内に収まっている場合の返り値は旧コードと同じ式。

## 5. 判定

**条件付き合格**。残るのは `frontend/tests-e2e/visual-language/popover-mold.spec.ts`（新設）だけで、
これが入り CI の画面検査3幅が緑になれば main へ出して良い。
R1 の訂正は本審査で書類に反映済み。R2・R4 は ⑫ に起票して次便へ送る。
