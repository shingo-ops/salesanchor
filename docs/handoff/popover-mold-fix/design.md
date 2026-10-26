# design: 浮かぶ選択肢パネルを画面の中に正しく出す（Popover 金型・宿題 C2）

> この文書は何か（1行）: 絞り込みの選択肢が「ページを下げてから開くと下へずれる」「画面の端で外に出る」の2点を土台（Popover 金型）で直し、開いている間に画面を動かしてもボタンに付いてくるようにする便の設計。

**日付**: 2026-10-26
**recon**: `docs/handoff/popover-mold-fix/recon.md`
**由来**: 便2（PR #4740）審査で C2 として起票、便3・便4・便5 で持ち越し
**前便**: 便4 `docs/handoff/viewer-header-remove/design.md`（PR #4764・本番反映済み・SHA 一致で確認）
**対象ADR**: ADR-144（UI 金型ガバナンス）／ADR-067（CSS はトークン参照のみ）／ADR-140（タップ領域44px）

## ① 区分：A（見た目と操作の変更）

| 項目 | 内容 |
|---|---|
| PO 決定（2026-10-26） | 3案から **「記録の2欠陥＋スクロール追従」** を選択＝(a)ずれ・(b)画面外に加えて、開いている間のスクロール/リサイズでも位置を測り直す。「下に入らないときは上に出す」は**今回やらない**（⑫へ） |
| 金型 | **`Popover` 金型の中身を直す**（新設なし・公開 props も増やさない＝呼び出し側の書き換え0） |
| 影響画面 | アプリ側の在庫表 `/inventory`（操作台の絞り込み2つ・フィルタパネル）。**閲覧ページは Popover を使っていないので無影響**（recon §4 で全数確認） |

## ② KGI（PO が実機で○×を判定できる粒度）

| # | 確かめること | ○× の基準 |
|---|---|---|
| K1 | ページを下へ送ってから絞り込みを開く | 選択肢の一覧が**押したボタンのすぐ下**に出る（今は画面の下の方／画面外へずれる） |
| K2 | スマホで絞り込みを開く | 一覧の**左右が画面の中に収まる**（文字が切れない・横スクロールが出ない） |
| K3 | 開いたまま画面を上下に動かす | 一覧が**ボタンに付いてくる**（置き去りにならない） |
| K4 | PC で今までどおり | スクロールしていない状態で開いたときの見た目・位置は**今と同じ** |

## ③ KPI（機械で測る値）

| 指標 | 測り方 | 合否 |
|---|---|---|
| 開いた位置（スクロール後） | 400px スクロール後に開き、パネルの `top` − ボタンの `bottom` | **6px ±2**（`gap = 6`） |
| 左端 | パネルの `left` | **>= 8**（画面端との最低間隔） |
| 右端 | パネルの `right` | **<= 画面幅 − 8** |
| パネル幅 | パネルの `width` | **<= 画面幅 − 16** |
| 横はみ出し | `documentElement.scrollWidth <= innerWidth` | 収まること |
| 追従 | 開いたまま 200px スクロールした後の `top` − ボタンの `bottom` | **6px ±2** |
| 選択肢1行の高さ | 既存基準（ADR-140） | **44px 以上**（不変） |

## ④ 設計（How）

### 4-1. スクロール分の足し算をやめる（`frontend/src/components/Popover.tsx:38-70`）

`calcPosition` の `window.scrollY` / `window.scrollX` を**すべて消す**（4つの placement ＝ 8か所）。
理由は recon §1。パネルは `position: fixed`、基準の矩形は `getBoundingClientRect()` ＝どちらも画面基準なので足す必要がない。

**スクロール量が 0 のときの結果は今と一文字も変わらない**＝PC で上にいるときの見た目は不変（K4）。

### 4-2. 画面の中へ収める（同ファイル・`calcPosition` の最後）

先例 `frontend/src/components/ContextMenu.tsx:78-95` と**同じ考え方・同じ最低間隔（8px）**に揃える。

```
左: left + panelW + margin > innerWidth なら innerWidth - panelW - margin
上: top + panelH + margin > innerHeight なら innerHeight - panelH - margin
さいごに left = max(margin, left) / top = max(margin, top)
```

- `margin` は 8px（`--space-2` と同値）。ContextMenu が `const margin = 8;` と書いている先例に合わせ、**JS 側は定数＋コメント**（CSS 直値禁止は CSS の話）。
- 置き方（placement）は変えない。**位置を画面内へ寄せるだけ**で、上下の入れ替えはしない（⑫ C-up）。

### 4-3. パネルが画面より広いときは幅に上限を付ける（CSS）

寄せるだけでは、パネル自体が画面より広い場合（`--dropdown-min-width: 400px` > 画面 360px）は直らない。

- `frontend/src/components/Popover.css` の `.comp-popover` に
  `max-width: calc(100vw - var(--space-4))`（左右 8px ずつ）を足す。
- `frontend/src/components/MultiSelect.css:12-14` の `.comp-multiselect__menu--popover` の最小幅を
  `min-width: min(var(--dropdown-min-width), calc(100vw - var(--space-6)))` に変える。
  **理由（CSS の罠）**: `min-width` は `max-width` より強いので、`min()` で包まない限り 400px が勝って画面外に残る。
- どちらも**トークン参照のみ**（ADR-067）。`--space-4` = 16px・`--space-6` = 24px であることを実装時に `tokens.css` で確認し、違っていたら合う名前に差し替える。
- 画面が十分広いとき（PC）は `min()` が `--dropdown-min-width` を選ぶので**今と同じ 400px**（K4）。

### 4-4. 開いている間は測り直す（`Popover.tsx:98-107`）

位置計算の `useEffect` の中で、開いている間だけ `resize` と `scroll` を購読して同じ計算を呼ぶ。

- `scroll` は**捕獲（capture: true）＋ passive** で `window` に付ける（中のスクロール箱でも拾えるように）。
- 後片付けは `removeEventListener`。**時間に頼る後始末は作らない**（便2 の教訓＝280ms タイマーの罠）。
- 測り直しは「位置だけ」。開閉状態・フェードイン（`visible`）には触らない。

### 4-5. 触らないもの

- `Popover` の公開 props（呼び出し側は書き換え0）。
- `ContextMenu.tsx`・`SchedulePageImpl.tsx`（どちらも自前で画面内に収めている・recon §4）。
- 閲覧ページ（`pages/viewer/`）。Popover を使っていない。
- `--dropdown-min-width` トークンの値（400px のまま。使い方だけ変える）。

## ⑤ Acceptance Criteria

**測り方の共通の決まり**: `scrollIntoView` は使わない。開いているパネルは `.comp-popover` で取る。スマホ幅は 390（CI の vl-mobile-390）と、単体テストで 360 を作る。

| # | 基準 | 検証方法 |
|---|---|---|
| C1 | スクロール 400px の状態で開くと `top` がボタンの下 **6px ±2** | 新 spec・単体 |
| C2 | 画面幅 360 で開いたとき `left >= 8` | 単体（`innerWidth` を 360 にして測る） |
| C3 | 右端のボタンで開いても `right <= 画面幅 − 8` | 単体 |
| C4 | パネル幅が **画面幅 − 16 以内** | 新 spec（3幅） |
| C5 | 開いたまま 200px スクロールするとパネルが付いてくる（`top` が **6px ±2** のまま） | 新 spec・単体 |
| C6 | 画面幅を変える（リサイズ）と位置が測り直される | 単体 |
| C7 | placement = top / left / right でも scroll 分を足さない | 単体 |
| C8 | 横はみ出しが 0（`scrollWidth <= innerWidth`） | 新 spec（3幅） |
| C9 | 選択肢1行の高さが 44px 以上（ADR-140・不変） | 新 spec |
| C10 | PC（1280px）でスクロールせずに開いた位置が**今と同じ**（ボタン中央そろえ・下 6px） | 新 spec |
| C11 | 既存の `MultiSelect` 単体（A20 ほか）が緑 | `frontend/src/components/MultiSelect.test.tsx` |
| C12 | 閲覧ページの既存検査（便1〜便5）が緑＝無影響の証拠 | `viewer-inventory-mobile-filter.spec.ts`・`viewer-top-compact.spec.ts`・`viewer-choice-sheet.spec.ts`・`viewer-header-remove.spec.ts` |
| C13 | 在庫表の既存検査が緑 | `tests-e2e/visual-language/inventory-mobile-baseline.spec.ts`・`inventory-raw-text-mobile.spec.ts`・`tests-e2e/inventory-table-layout.spec.ts` |
| C14 | 型検査が通る | `cd frontend && npx tsc --noEmit` |
| C15 | 手元検査が通る（変更ファイルは警告0） | `cd frontend && npm run check:all` ＋ `npx eslint --max-warnings=0 <変更ファイル>` |
| C16 | **直す前に赤いこと**（RED-first）を記録する | 新 `Popover.test.tsx` を**先に**書いて `npx vitest run src/components/Popover.test.tsx` の赤い出力を design に貼る |

### RED-first の記録（C16・直す前のコードで実行）

`origin/main`（`03cb7cae5`）の `Popover.tsx`（scroll 分を足す・画面内に収めない・resize/scroll を購読しない）に対して
`frontend/src/components/Popover.test.tsx` を実行した結果。**9件中9件が赤**（想定どおり）。

```
 FAIL  src/components/Popover.test.tsx > C1: スクロール400px後に開くと top はボタンの下 6px
   expected 736 to be 336   // scrollY(400) が足された分だけ余分にずれる
 FAIL  > C7: placement=top でも scrollY/scrollX を足さない
   expected 594 to be 194
 FAIL  > C7: placement=left でも scrollY/scrollX を足さない
   expected 665 to be 265
 FAIL  > C7: placement=right でも scrollY/scrollX を足さない
   expected 665 to be 265
 FAIL  > C2: 画面幅360で左端に近いボタンでも left >= 8
   expected -88 to be >= 8   // 画面内に収める処理が無い
 FAIL  > C3: 右端のボタンで開いても right <= 画面幅 - 8
   expected 450 to be <= 352
 FAIL  > C5: 開いたまま scroll すると、トリガーの新しい位置に追従する
   expected 336 to be 136   // 測り直しの購読が無い
 FAIL  > C6: 開いたまま resize すると位置が測り直される
   expected 450 to be <= 352
 FAIL  > 閉じると resize/scroll の購読を後始末する
   expected false to be true

 Test Files  1 failed (1)
      Tests  9 failed (9)
```

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/components/Popover.tsx` | 4-1（scroll 分を削除）・4-2（画面内へ収める）・4-4（開いている間の測り直し） |
| `frontend/src/components/Popover.css` | 4-3（`max-width`） |
| `frontend/src/components/MultiSelect.css` | 4-3（`min-width` を `min()` で包む） |
| `frontend/src/components/Popover.test.tsx` | **新設**（C1〜C7・C16） |
| `frontend/tests-e2e/visual-language/popover-mold.spec.ts` | **新設**（C1・C4・C5・C8・C9・C10。`visual-language/` 配下でないと CI で1本も走らない） |
| `docs/handoff/popover-mold-fix/{recon,design,review-opus}.md` | 本書類 |
| `.claude-pipeline/active-work.d/release-popover-mold-fix.md` | 台帳 |

## ⑦ 戻し方

本 PR の revert 1回。公開 props を変えないので呼び出し側の巻き戻しは不要。

## ⑧ 削除するファイル

なし。

## ⑨ 外部・過去事例の参照と我々への応用

- 社内の先例 `ContextMenu.tsx:78-95`（画面内へ収める・最低間隔8px）をそのまま踏襲。**新しい流儀を増やさない**。
- `position: fixed` に `scrollY` を足さないのは `getBoundingClientRect()` の定義どおり（画面基準）。予定表 `SchedulePageImpl.tsx:119-141` も足していない＝社内2例が既に正しい形。

## ⑩ 弊害・トレードオフ

| 弊害 | 程度・対応 |
|---|---|
| スクロール中に位置計算が毎フレーム走る | 購読は**開いている間だけ**・passive。計算は `offsetWidth` 読み＋算術のみ。重ければ次便で `requestAnimationFrame` 間引き（⑫） |
| スマホで一覧の幅が 400px から画面幅−24px（390幅なら366px）に縮む | 文字が切れるより良い。中身は縦に並ぶので折返しだけ |
| 「下に入らないときに上へ出す」は未対応 | 画面内へ寄せるので外には出ないが、下が狭いとボタンに重なることがある。⑫ C-up として起票 |

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/popover-mold.spec.ts`（CI の集約ジョブ `visual-language` で毎 PR・3幅）＋ `frontend/src/components/Popover.test.tsx`（`npm run check:all` の単体）

| 守ること | 関所 | 外すと |
|---|---|---|
| スクロールしてから開いてもボタンの下に出る | 上記 spec（C1）・単体 | 赤 |
| 画面の端で外に出ない | 単体（C2・C3）・spec（C4・C8） | 赤 |
| 開いたまま動かしても付いてくる | spec（C5）・単体 | 赤 |
| PC の見た目が変わらない | spec（C10） | 赤 |
| 閲覧ページ・在庫表の既存の形 | 既存 spec 群（C12・C13） | 赤 |

## ⑫ 継続（この便の後）

| # | 項目 | 状態 |
|---|---|---|
| C-up | 下に入らないときは上に出す（placement の自動反転） | PO 判断で今回は見送り。起票のみ |
| C-perf | スクロール追従の間引き（`requestAnimationFrame`） | 実測で重ければ |
| C8（便2 から） | 自動読み直しでフォーカス中の候補が消えると `<body>` に落ちる（`Drawer` 金型の `focusout`） | 未着手 |
