# design: かぶせて出すパネルの出口封じを1か所にまとめ、行が消えても外へ出さない（宿題 C8）

> この文書は何か（1行）: 宿題 C8 を「`Drawer`・`Modal`・`Sheet` の3つに複製されている出口封じ（フォーカストラップ）を
> 共通の1か所へまとめ、現在地が消えたときに Tab でパネル内へ連れ戻す」形で直す設計。
> recon: `docs/handoff/viewer-focus-trap/recon.md`（この設計の事実の出所。節番号で相互参照する）

**日付**: 2026-10-26 ／ **土台**: `release/viewer-focus-trap`（`origin/main` = `840eea949`）

## ① 区分：A（操作の変更。見た目は変わらない）

キーボード操作の挙動が1点だけ変わる。色・寸法・文言・レイアウトは一切変えない（CSS は触らない）。

**影響する画面**: `Drawer` 35ファイル・`Modal` 43ファイル・`Sheet` 2ファイル（recon §2 の実測）。
ただし**変わるのは「現在地がどこでもない状態で Tab を押したとき」だけ**で、それ以外の挙動は現状と同一。

## ② KGI（PO が実機で○×を判定できる粒度）

| # | 判定内容 |
|---|---|
| K1 | 閲覧ページの絞り込みパネルで候補を選んでいる間に在庫が入れ替わっても、**Tab を押したときにパネルの外（後ろの画面）へ出て行かない** |
| K2 | 今までのキーボード操作が変わっていない（パネルを開くと先頭に移る／Tab で中を回る／Esc で閉じる／閉じると元のボタンへ戻る） |
| K3 | 確認窓（`Modal`）と下から出るパネル（`Sheet`）でも K1・K2 が同じように成り立つ |

## ③ KPI（機械で測る値）

| # | 測る値 | 目標 |
|---|---|---|
| P1 | 現在地が `<body>` の状態で Tab を押したあとの `document.activeElement` | **パネルの中**（`panel.contains(active)` が true） |
| P2 | 現在地がパネル外の**別の要素**（他のポータル等）に在るときの Tab | **何もしない**（フォーカスは動かない） |
| P3 | 既存の回り込み（先頭で Shift+Tab → 末尾／末尾で Tab → 先頭） | 変化なし |
| P4 | フォーカス可能要素の選択子の定義箇所数 | **3 → 1** |
| P5 | 閲覧ページ JS | 300KB 以下（`frontend/scripts/check-viewer-bundle.js:21`） |

## ④ 設計（How）

### 4-1. 共通の置き場を1つ新設する（`frontend/src/hooks/useFocusTrap.ts`・新規）

recon §6 の作法に合わせ、**DOM に触る再利用処理は `frontend/src/hooks/`** に置く（`useIsMobile.ts`・
`useFitTableZoom.ts` の先例。単体テストを同居させる作法も既存どおり）。この1ファイルに次の3つだけを置く。

| 公開するもの | 中身 |
|---|---|
| `FOCUSABLE_SELECTOR`（非公開） | recon §2 の3つと**完全に同じ並び**をそのまま移す（値は変えない） |
| `getFocusableElements(container)` | recon §2 の3つと同じ本体をそのまま移す（`[aria-hidden='true']` の除外も同じ） |
| `getFirstFocusable(container)` | 同上 |
| `useFocusTrap(open, containerRef)` | 出口封じの `useEffect`。`open` が false の間は購読しない（現状と同じ） |

**UI 金型の新設ではない**（`.tsx`＋`.css`＋`.stories.tsx` を伴う部品を作らない）ので ADR-144 §4 の
「金型新設」手順の対象外。ただし共通化の是非は PO 承認済み（2026-10-26・3案から「1か所にまとめて3つ全部直す」）。

### 4-2. 出口封じに「現在地がどこでもない」枝を足す（これが C8 の直し）

`useFocusTrap` の中の Tab 処理は、現状（recon §1）に**枝を1本だけ足した形**にする。

```
Tab 以外 → 何もしない（現状どおり）
フォーカス可能要素が0件 → preventDefault（現状どおり）
現在地がパネルの中 → 先頭/末尾のときだけ回り込む（現状どおり・P3）
現在地がパネルの外:
  ├ <body> か <html> か null（＝行が消えて居場所が無い） → preventDefault して
  │   Tab なら先頭、Shift+Tab なら末尾へ入れる（C8 の直し・P1）
  └ それ以外の要素（他のポータルに居る） → 何もしない（P2）
```

**「それ以外の要素なら何もしない」を必ず入れる理由**: `Popover`（`frontend/src/components/Popover.tsx`）や
`Modal` は `document.body` 直下へ別に描かれる。パネルの中から浮かぶ選択肢や確認窓を開いた画面で
フォーカスを奪い返すと、**直していない所を壊す**。recon §2 のとおり `Modal` は43ファイルで使われているため、
ここを限定しないと影響が読めない。

**この限定だけでは足りない場合（独立審査 N-1・正直な限界）**: パネルが2枚**同時に開いている**とき
（例: `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:298-392` のドロワーの中の
`:385` から `:395-441` の確認窓を開く経路）、両方が `document` の `keydown` を購読する。
呼ばれる順は登録順＝**先に開いた背面のパネルが勝つ**ので、現在地がどこでもない回の Tab は
**前面ではなく背面の先頭**へ入る。直す前も同じ回は外へ出ていたため**新たに不可能になる操作は無い**
（Esc で両方閉じる経路も不変）が、「限定すれば他を壊さない」という上の説明は入れ子では成り立たない。
**最前面だけが連れ戻す**形は ⑫ **E6** に起票（この便の境界外）。

### 4-3. 3つの金型を共通の1か所に繋ぎ替える

| ファイル | すること |
|---|---|
| `frontend/src/components/Drawer.tsx` | 自前の `FOCUSABLE_SELECTOR`・`getFocusableElements`・`getFirstFocusable`（`:212-229`）と出口封じの `useEffect`（`:101-129`）を削除し、`useFocusTrap(open, panelRef)` ＋ `getFirstFocusable` の import に置き換える |
| `frontend/src/components/Modal.tsx` | 同じ（`:158-175` と `:82-110`。`dialogRef` を渡す） |
| `frontend/src/components/Sheet.tsx` | 同じ（`:166-183` と `:82-110`） |

（行範囲は独立審査の指摘で末尾を1行ずつ訂正済み＝`getFirstFocusable` の閉じ括弧まで含む）

**公開プロパティは1つも増やさない／変えない**＝呼び出し側（35+43+2 ファイル）の書き換えは **0**。

### 4-4. 触らないもの（この便の境界）

- **初期フォーカス（開いたら先頭へ）と復帰（閉じたら元へ）の `useEffect`**（`Drawer.tsx:68-86`・
  `Modal.tsx:49-67`・`Sheet.tsx:49-67`。いずれも実物で確認）は**3つに残したまま**にする。欠陥が無く、まとめると
  43ファイルで使う確認窓の初期フォーカス経路まで差分に入り、審査と検査の範囲が広がるため。⑫ **E1** に起票。
- **消えた瞬間に戻す**（`focusout` 購読）は**やらない**。PO 決定（2026-10-26・「Tab を押したときに戻す」）。
  理由: 要素が DOM から外れたときに `focusout` が飛ぶかはブラウザ依存で**この端末では測れない**（CI 1往復が必要）。
  ⑫ **E2** に起票。
- CSS・トークン・文言・辞書（`ja.json`/`en.json`）・DB・配線（API）は一切触らない。
- 便5 の `viewer-choice-row` の金型昇格は**別便**（PO 決定。⑫ **E3**）。

## ⑤ Acceptance Criteria

RED-first（直す前のコードで実行して赤になること）を単体で記録する。`C` は単体、`B` は画面検査。

| # | 基準 | 測り方 |
|---|---|---|
| C1 | 開いた `Drawer` の2つ目にフォーカス → その要素を DOM から外す → `document.activeElement` が `<body>` になる | 単体（前提の固定。ここが崩れたら以降は何も測っていないので赤にする） |
| C2 | C1 の状態で Tab を送ると**パネル内の先頭**にフォーカスが移る | 単体（**直す前は赤**） |
| C3 | C1 の状態で Shift+Tab を送ると**パネル内の末尾**にフォーカスが移る | 単体（**直す前は赤**） |
| C4 | パネルの外に在る**別の要素**にフォーカスがあるとき、Tab でフォーカスが動かない | 単体（P2・退行防止） |
| C5 | 先頭で Shift+Tab → 末尾／末尾で Tab → 先頭（既存の回り込み） | 単体（P3・現状維持。いまテストが無いのでここで追加する） |
| C6 | `open` が false の間は Tab を送っても何も起きない | 単体（購読していないことの確認） |
| C7 | C2〜C6 が `Modal`・`Sheet` でも同じ結果になる | 単体（金型ごとに同じ表を回す） |
| C8 | `getFocusableElements` が `[aria-hidden='true']` の中を除く（移設で壊れていない） | 単体 |
| C9 | 型検査 `npx tsc --noEmit` が 0 件 | 手元 |
| C10 | `npm run check:all` が終了0 | 手元 |
| C11 | フォーカス可能要素の選択子の定義が**リポジトリ全体で1か所**（`grep -rn "FOCUSABLE_SELECTOR" frontend/src` が `useFocusTrap.ts` のみ） | 単体（P4 を機械で固定する） |
| B1 | 閲覧ページ（本物の Chromium）で、絞り込み → 提供者の選択画面 → 候補にフォーカス → 自動読み直しでその候補が消える → **`document.activeElement` が `<body>` になる**（前提の固定） | 画面検査3幅 |
| B2 | B1 の直後に Tab を押すと、フォーカスが**パネル内の先頭そのもの**（`drawer-back`）に在る | 画面検査3幅（**直す前は赤**） |
| B2' | B1 の直後に Shift+Tab を押すと、フォーカスが**パネル内の末尾そのもの**（`viewer-filter-apply`）に在る | 画面検査3幅（**直す前は赤**） |
| B3 | 閲覧ページ JS が 300KB 以下 | CI（`check-viewer-bundle.js`） |

**B2 を「パネルの中に居る」で測ってはいけない（独立審査 B-1 の指摘・反映済み）**: 本物のブラウザは
消えた要素の位置を**順次フォーカス移動の起点**として覚えているため、素の Tab でも
**消えた候補の次の候補**（＝パネルの中）へ入り得る＝**直す前でも緑になり得る**（便6 と同じ「空振りで緑」）。
そこで**先頭／末尾そのもの**を assert する。先頭 `drawer-back` は消えた候補より DOM 順で前なので
**前方向の素の Tab では到達できない**。末尾 `viewer-filter-apply`（footer）は
**後方向の素の Shift+Tab では到達できない**。どちらも「連れ戻した」ときだけ成立する＝赤になる理由が作りで保証される。
パネル内の先頭／末尾が何かも同時に assert するので、将来 DOM 順が変わったら黙って緑にならず赤で気づける。

**B1・B2 の作り方（確定事項）**:
- 自動読み直しは60秒間隔（recon §3）でテストの制限時間（30秒）を超えるため、**`page.clock` で時計を進める**
  （`package-lock.json` が固定している版は **1.59.1**、入っている型定義に `clock: Clock` と
  `fastForward(ticks: number|string)`・`install(options?)` が実在することを 2026-10-26 に実物で確認）。
  `await page.clock.install({ time: <現在時刻> })` → `await page.clock.fastForward(60_000)`。
- 2回目の応答だけ候補を減らすため、`frontend/tests-e2e/utils/api-mock.ts` の `MockEntry` が
  **関数（`(route) => ...`）を受け付ける**ことを使い、呼ばれた回数で返す中身を変える。
- spec の置き場は `frontend/tests-e2e/visual-language/` 配下（ここ以外は CI で1本も走らない。
  [[salesanchor-ci-blind-spots]] §tests-e2e 直下の落とし穴）。
- 窓スクロールは使わないので `makePageScrollable` 相当は不要。

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| frontend/src/hooks/useFocusTrap.ts | **新規**（共通の出口封じ＋フォーカス可能要素の集め方） |
| frontend/src/hooks/useFocusTrap.test.tsx | **新規**（C1〜C8・C11 を3金型ぶん） |
| frontend/src/components/Drawer.tsx | 自前の複製を削除し共通へ繋ぎ替え |
| frontend/src/components/Modal.tsx | 同上 |
| frontend/src/components/Sheet.tsx | 同上 |
| frontend/tests-e2e/visual-language/viewer-focus-trap.spec.ts | **新規**（B1・B2・B2'） |
| frontend/tests-e2e/visual-language/viewer-helpers.ts | `installViewerToken` に `export` を足すだけ（トークン投入の写しを作らない・独立審査 N-4。既存の呼び出しは不変） |
| docs/handoff/viewer-focus-trap/recon.md | 本便の調査記録（済） |
| docs/handoff/viewer-focus-trap/design.md | 本書 |
| docs/handoff/viewer-focus-trap/review-opus.md | 実装後に設計担当が記録 |
| .claude-pipeline/active-work.d/release-viewer-focus-trap.md | 担当機能エリアの記入 |

## ⑦ 戻し方

この PR を revert 1回。公開プロパティを変えていないので呼び出し側の巻き戻しは不要。

## ⑧ 削除するファイル

なし（`Drawer.tsx`・`Modal.tsx`・`Sheet.tsx` の中の複製コードは削除するが、ファイルは残る）。

## ⑨ 外部・過去事例の参照と我々への応用

- **WAI-ARIA Authoring Practices の Modal Dialog パターン**（https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/ ・2026-10-26 に取得して原文確認）:
  キーボード操作の節に **"Tab and Shift + Tab do not move focus outside the dialog."** と明記されている。
  現状の実装は「現在地がパネル内の端のときだけ」留めるので、**現在地が消えた回はこの要件を満たさない**。本便はその穴をふさぐ。
  **正直な限界**: 同ページは「フォーカス中の要素が消えた場合」については何も書いていない（閉じたときの復帰先として
  "The invoking element no longer exists. Then, focus is set on another element that provides logical work flow." と
  述べているだけ）。したがって**「どこへ戻すか」は本便の設計判断**であり、外部指針の引き写しではない
  （本便は Tab なら先頭・Shift+Tab なら末尾＝進行方向に合わせる）。
- **社内の過去事例（便2・PR #4740）**: 「状態の後片付けを時間（`setTimeout` 280ms）に頼ると、閉じて
  280ms 以内に開き直した回に壊れる」という失敗を経験している（CI の A17 が6件赤で検出）。
  本便は**時間に頼らない**（`keydown` の瞬間に判定するだけ）。
- **社内の過去事例（便6・PR #4780）**: 同じ金型の直しで「検査が空振りで緑」になっていた。
  本便は**前提そのものを assert する**（C1・B1）ことで空振りを防ぐ。

## ⑩ 弊害・トレードオフ

| # | 弊害 | 判断 |
|---|---|---|
| T1 | `Modal` は43ファイルで使われており、出口封じの差し替えは影響範囲が広い | 挙動は「現在地がどこでもないときの Tab」だけ変わる。C5・C6 で既存挙動を固定し、C7 で3金型すべてを同じ表で測る |
| T2 | 現在地が消えてから次に Tab を押すまでの間、現在地は迷子のまま | PO 決定（事故＝外へ出ることは防げる）。即時復帰は ⑫ E2 |
| T3 | 初期フォーカス・復帰の複製が3つ残る | ⑫ E1 に起票（本便の境界は 4-4 に明記） |
| T4 | `page.clock` を使う画面検査は、時計を止めるため他の時間依存表示（24時間以内の判定）に影響し得る | 24時間窓に対し60秒進めるだけなので判定は変わらない。B1 で「候補が消えた」ことを直接確かめるので空振りしない |

## ⑪ 維持の仕組み

- **C11 が「選択子の定義は1か所」を機械で固定する**ので、将来また複製すると単体テストが赤になる。
- 3金型の出口封じは `useFocusTrap` の1か所だけになるため、次に直すときは**1回で済む**。
- 画面検査 B1・B2 は `visual-language/` 配下に置くので CI の必須経路（`画面検査（内部）`）で毎回走る。
- 単体テスト `useFocusTrap.test.tsx` は `npm run test:unit` と pre-commit の両方で走る。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| E1 | 初期フォーカス・復帰の `useEffect` も `useFocusTrap` に寄せる（3金型の複製解消の残り） |
| E2 | 「行が消えた瞬間に先頭へ戻す」（`focusout` が DOM 除去で飛ぶかを CI の本物の Chromium で実測してから判断） |
| E3 | 便5 の `viewer-choice-row` を共通金型へ昇格（在庫表への横展開の下準備・ADR-144 §4 の PO 許可が必要） |
| E4 | `Modal`・`Sheet` に単体テストが1件も無い（recon §5）。最低限の歯止めを別便で足す |
| E5 | **`Drawer`/`Sheet` を最初から `open=true` でマウントすると出口封じも初期フォーカスも1回も付かない**（既存の穴・この便の退行ではない）。`portalTarget` を `useEffect` で解決する2段構え（`Drawer.tsx:64-66`）のため、初回は ref が null、解決後の再描画では `open` が変わらず effect が再実行されない。**現在の呼び出し元 35+2 ファイルはすべて「常時マウント＋`open` を切り替える」形なので今日の実害は0**。到達経路の例: 閲覧ページ（`InventoryView.tsx:668-670` の `{isMobile && …}`）でスマホ幅で開く → PC 幅に広げる → スマホ幅へ戻す。直すなら依存に `portalTarget` を足す／`containerRef` を state 化する。単体テストの `openMold`（`useFocusTrap.test.tsx:71-75`）がこの穴を避けて false→true で開いているのは**この作りに合わせたもの**で、`{x && <Drawer open />}` と書かれても現状のテストは1件も赤くならない |
| E6 | **パネルが2枚同時に開いているとき、最前面だけが連れ戻す**ようにする（4-2 の追記・独立審査 N-1）。いまは登録順＝背面が勝つ。モジュール内に重なり順を1本持つ形で10行程度 |
| E7 | `C11`（選択子の定義は1か所）は **`const FOCUSABLE_SELECTOR =` という名前の完全一致**しか数えないので、別名で複製されると通る（独立審査 N-3）。歯止めを強めるなら選択子の**文字列そのもの**を探す形へ |

## 対象 ADR

- **ADR-144**（UI 共通部品の遵守ガバナンス）: §1「`pages/` 配下の UI は原則 `components/` の共通金型を使う」。
  本便は金型そのものの内部を1か所にまとめる作業で、§4 の「金型新設」には当たらない（4-1 に理由）。
- **ADR-027**（i18n 強制）: 文言は1つも追加・変更しない。
- **ADR-067**（デザイントークン強制）: CSS を触らないため変更なし。
- recon との相互参照: 本書の事実はすべて `docs/handoff/viewer-focus-trap/recon.md` の §1〜§7 に対応する。
