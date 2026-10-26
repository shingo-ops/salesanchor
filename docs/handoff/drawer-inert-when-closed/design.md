# design: 閉じているパネルを「無い物」として扱う（宿題 D5）

> この文書は何か（1行）: 閉じている `Drawer`／`Sheet` に `inert`（その枝をまるごと無効にする印）を付けて、
> **Tab の通り道からも読み上げからも外す**設計。見た目は変えない。
> recon: `docs/handoff/drawer-inert-when-closed/recon.md`（この設計の事実の出所。節番号で相互参照する）

**日付**: 2026-10-27 ／ **土台**: `release/drawer-inert-when-closed`（`origin/main` = `fbc8e3086`）

## ① 区分：A（操作の変更。見た目は変わらない）

キーボードと読み上げの挙動が変わる。色・寸法・文言・レイアウト・アニメーションは一切変えない（**CSS は触らない**）。

**影響する画面**: `Drawer` 35ファイル・`Sheet` 2ファイル（recon §3 の実測）。`Modal` は閉じると DOM から消えるので対象外。

## ② KGI（PO が実機で○×を判定できる粒度）

| # | 判定内容 |
|---|---|
| K1 | 閲覧ページ（スマホ）を開いた直後に Tab を押し続けても、**閉じているパネルの中身（シリーズの43行など）に入らない**。検索欄→シリーズ→並び替え→絞り込み→一覧…と画面に見えているものだけを順に辿れる |
| K2 | パネルを開けば今までどおり中身を Tab で辿れ、Esc・✕ で閉じられる（**開いているときの操作は何も変わらない**） |
| K3 | 開くとき・閉じるときのアニメーション（右から／下から滑る動き）が今までどおり |

**目視確認の範囲（PO 決定・2026-10-27）**: ADR-144 の結論部（`docs/adr/ADR-144-ui-component-governance.md:79`）は
「見た目の自動回帰検出が無く、**金型変更時は PO 目視依存**」と定めているが、本便は **CSS を1行も触らない**ため
見た目が変わる理由が無い。PO 決定により**目視確認は閲覧ページ（スマホ）だけ**とし、
`Drawer` を使う他の34画面・`Sheet` の2画面は機械検査（単体＋CI の画面検査3幅）で代える。

## ③ KPI（機械で測る値）

| # | 測る値 | 目標 |
|---|---|---|
| P1 | 閲覧ページ（390px）を開いた直後に「閉じたパネルの外の要素数＋3回」Tab を押したときの、**閉じたパネル内に入った回数** | **0回**（直す前は入る＝赤。⑤ の「作り方」参照） |
| P2 | 閉じている `.comp-drawer-panel`（`--open` が無いもの）の `inert` | **すべて true** |
| P3 | 開いている `.comp-drawer-panel--open` の `inert` | **false**（開いている側は無効化しない） |
| P4 | 開いているときの出口封じ・回り込み（便7 の C2〜C6・B1〜B2'） | **変化なし** |
| P5 | 閲覧ページ JS | 300KB 以下（`frontend/scripts/check-viewer-bundle.js:21`） |

## ④ 設計（How）

### 4-1. なぜ `inert` か（3案の比較）

| 案 | 中身 | 判定 |
|---|---|---|
| **A: `inert` を付ける（採用）** | 閉じている間、パネルの要素に `el.inert = true`。Tab の通り道・読み上げ・クリックの3つが**1つの指定でまとめて無効**になる | **採用**。`transition` に一切触らないので**アニメーションを壊す余地がない**（recon §6）。DOM の性質としては型定義があり型の細工も不要 |
| B: CSS に `visibility: hidden` を足す | 閉じている間だけ見えなくする | **不採用**。`transition` は `transform` だけに掛かっているため**閉じるアニメーションが途中で消える**。遅延指定には 280ms 単体のトークンが必要で、**無い**（recon §6）＝新トークン＋アニメーションの作り変えになり、見た目を変えない便の範囲を超える |
| C: `aria-hidden="true"` を付ける | 読み上げから外す | **不採用**。**Tab の通り道からは外れない**（読み上げだけの対策で、不具合の半分しか直らない） |

**`inert` の下支え**: ブラウザの標準機能（Chrome 102・Safari 15.5・Firefox 112 以降）。CI の Chromium も対象内。
万一 `inert` を解さない閲覧環境では**今までと同じ挙動に戻るだけ**（悪化しない）。

### 4-2. 置き場は便7 の共通ファイル（複製を作らない）

`frontend/src/hooks/useFocusTrap.ts` に**関数を1つ足す**（便7 で作った「かぶせて出すパネル共通のキーボード処理」の置き場）。

```
useInertWhenClosed(open, containerRef, ready)
  → ready（＝描き先が決まったか）と open が変わるたびに
    containerRef の要素に open の裏返しを入れる（閉じている間だけ無効化）
```

**`ready` を引数に取る理由（便7 で分かっている罠を避ける）**: `Drawer`／`Sheet` は描き先（`portalTarget`）を
後から決める2段構えで、**1回目の描画では要素がまだ無い**。`open` だけを頼りにすると、
**最初から閉じている回（＝まさに今回直したい状態）で1度も実行されない**
（便7 の ⑫ E5 と同じ罠。`frontend/src/components/Drawer.tsx:66,105`）。
`portalTarget` を `ready` として渡せば、描き先が決まった直後にもう一度実行される。

**`useLayoutEffect` にする（独立審査 B-1 の直し・設計の訂正）**: 無効化の解除は、金型の
「開いたらパネル内の先頭へフォーカスを移す」処理（`frontend/src/components/Drawer.tsx:81-87`・
`frontend/src/components/Sheet.tsx:62-68`）より**必ず先**に走らなければならない。
React は同種の effect を**書いた順**に流すため、通常の `useEffect` だと閉→開の回に
「先頭へフォーカス」→「無効化を解除」の順になり、**まだ無効な枝へ focus して不発に終わる**
（HTML 標準では inert な枝はフォーカス可能領域ではなく `focus()` は何もしない）。
結果、カーソルが開いたパネルの外に取り残され、**キーボードだけで使う人が開いたパネルに入れなくなる**
＝37画面に効く退行だった。`useLayoutEffect` は通常の effect より先に走るので
**呼び出し側で何行目に書いても順序が保たれる**（先例 `frontend/src/components/CheckboxControl.tsx:35`）。
この順序は C8 で機械的に固定する。

### 4-3. 2つの金型から1行ずつ呼ぶ

| ファイル | すること |
|---|---|
| `frontend/src/components/Drawer.tsx` | `useFocusTrap(open, panelRef)`（`:103`）の隣に `useInertWhenClosed(open, panelRef, portalTarget)` を足す |
| `frontend/src/components/Sheet.tsx` | 同じ（`:84` の隣。`panelRef` と `portalTarget` は同名で既にある） |

**公開プロパティは1つも増やさない／変えない**＝呼び出し側（35＋2 ファイル）の書き換えは **0**。

### 4-4. 触らないもの（この便の境界）

- **CSS は1行も触らない**（`Drawer.css`・`Sheet.css`・`tokens.css`）。アニメーションも不変。
- **`Modal`** は閉じると DOM から消えるので何もしない（recon §3）。
- **開いているときの出口封じ**（便7 の `useFocusTrap`）は変更しない。P4 で退行を見張る。
- 便7 から持ち越しの **E1**（初期フォーカスの共通化）・**E5**（最初から `open=true` でマウントすると付かない）・
  **E6**（2枚開いているとき最前面が勝つ）は**別便**。ただし 4-2 の `ready` は E5 と同根なので、
  **この便で入れる関数だけは E5 の罠を踏まない形**にしておく（E5 本体＝初期フォーカスと出口封じ側は別便）。
- 文言・辞書・DB・配線（API）は触らない。

## ⑤ Acceptance Criteria

`C` は単体、`B` は画面検査。**`inert` の「実際にフォーカスを拒む」挙動は jsdom に無い**ので、
単体では**印が付いているか**（仕組み）を、画面検査では**本物のブラウザで Tab がどう動くか**（挙動）を測る。この分担を守る。

| # | 基準 | 測り方 |
|---|---|---|
| C1 | 閉じた `Drawer` のパネルの `inert` が true | 単体（**直す前は赤**） |
| C2 | 開いた `Drawer` のパネルの `inert` が false | 単体（**直す前も赤**＝未設定は `undefined` のため。独立審査 N2 の訂正） |
| C3 | 閉じる→開く→閉じるで C1・C2 が追従する | 単体（取り残しが無いこと。**直す前も赤**） |
| C4 | `Sheet` でも C1〜C3 が同じ結果になる | 単体（**直す前は赤**） |
| C8 | **開いた直後、フォーカスがパネルの中にある**（無効化の解除が「先頭へフォーカス」より先に走る） | 単体（**この便の最重要。独立審査 B-1 の再発防止**。`useLayoutEffect` を `useEffect` に戻すと 2金型で赤） |
| C5 | 便7 の既存20件（出口封じ・回り込み）が緑のまま | 単体（P4・退行防止） |
| C6 | 型検査 `npx tsc --noEmit` が 0 件 | 手元 |
| C7 | `npm run check:all` が終了0 | 手元 |
| B1 | 閲覧ページ（390px・本物の Chromium）を開いた直後、**閉じた `.comp-drawer-panel` が2枚あり、両方の `inert` が true**（前提の固定） | 画面検査・3 project（**直す前は赤**） |
| B2 | その状態で **「閉じたパネルの外にあるフォーカスできる要素の数＋3回」** Tab を押し、**毎回の現在地が「閉じたパネルの中」に入らない**（0回） | 画面検査・3 project（**直す前は赤**） |
| B3 | 絞り込みを開くと、**開いた側の `inert` は false**・その中の要素に Tab で入れる（K2 の機械確認） | 画面検査・3 project |
| B4 | 閲覧ページ JS が 300KB 以下 | CI（`check-viewer-bundle.js`） |

**B1・B2 の作り方（確定事項）**:
- 置き場は `frontend/tests-e2e/visual-language/`（ここ以外は CI で1本も走らない）。
- **「3幅」ではなく「3 project で同じ 390px を3回」**（独立審査 N5 の訂正）: 対象のパネルは
  `isMobile`（767px 以下）のときだけ存在するため、`frontend/tests-e2e/visual-language/viewer-helpers.ts` の `gotoViewer` が
  既定で 390×844 を強制する。tablet・desktop の project でも 390px で走るのが正しい。
- **前提を必ず assert する**（便6・便7 の教訓）: 「閉じたパネルが2枚ある」「その中にフォーカスできる要素が
  **10個以上ある**」を先に確かめる。ここを測らないと、中身が空のときに**何も確かめずに緑**になる。
  **実測は11個**（絞り込み側9＋シリーズ側2。独立審査が現物から数えて一致を確認）＝**余裕は1個**なので、
  将来この画面から操作部品が2つ減ると前提の assert が赤になる（意図どおり。理由はこの行）。
- **押す回数を固定にしてはいけない（設計の訂正・2026-10-27）**。初版は「20回」と書いていたが、
  閉じたパネルは `document.body` の末尾へ描かれる（ポータル）ため **DOM 順で画面の部品より後ろ**にあり、
  手前の部品が20個より多いと**閉じたパネルまで届かないまま「入った回数0」が成立する**＝
  **直す前でも緑になり得る**（便6・便7 と同じ「空振りで緑」）。
  **「閉じたパネルの外にあるフォーカスできる要素の数＋3回」**にすれば、Tab は DOM 順に進むので
  **外側を使い切った次の回は必ず閉じたパネルに入る**＝**直す前は赤**になることが作りで保証される。
  回数が 200 を超えたら前提が崩れていると見なして赤にする（黙って打ち切らない）。
- **B2 は「入った回数が0」だけでなく、Tab が実際に進んでいること**（現在地が複数の場所に動いたこと）も assert する。
  フォーカスがどこにも行かない状態でも「0回」は成立してしまうため。
- 疑似応答は `frontend/tests-e2e/visual-language/viewer-helpers.ts` の `gotoViewer`（固定の応答）で足りる。**「取得回数」で切り替える形は使わない**
  （便7 で踏んだ罠。`React.StrictMode` で初期取得が2回走る）。

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| frontend/src/hooks/useFocusTrap.ts | `useInertWhenClosed` を追加（既存の2つの関数と `useFocusTrap` は触らない） |
| frontend/src/hooks/useFocusTrap.test.tsx | C1〜C4 を追加（既存20件はそのまま＝C5） |
| frontend/src/components/Drawer.tsx | 1行追加 |
| frontend/src/components/Sheet.tsx | 1行追加 |
| frontend/tests-e2e/visual-language/drawer-inert-closed.spec.ts | **新規**（B1・B2・B3） |
| docs/handoff/drawer-inert-when-closed/recon.md | 調査記録（済） |
| docs/handoff/drawer-inert-when-closed/design.md | 本書 |
| docs/handoff/drawer-inert-when-closed/review-opus.md | 実装後に設計担当が記録 |
| .claude-pipeline/active-work.d/release-drawer-inert-when-closed.md | 担当機能エリアの記入 |

## ⑦ 戻し方

この PR を revert 1回。公開プロパティを変えていないので呼び出し側の巻き戻しは不要。

## ⑧ 削除するファイル

なし（既存ファイルからの行削除も無い＝追加だけ）。

## ⑨ 外部・過去事例の参照と我々への応用

- **WAI-ARIA Authoring Practices の Modal Dialog パターン**: ダイアログの外側は操作できてはならない、という要件の裏返しで、
  **閉じているダイアログの中身も操作できてはならない**。便7 で「開いている間に外へ出さない」を直したので、本便はその対（閉じている側）。
- **社内の過去事例（便7・PR #4800）**: 共通化の置き場（`frontend/src/hooks/useFocusTrap.ts`）と、
  **「2段構えのマウントで `open` だけを頼りにすると1度も実行されない」罠**（⑫ E5）。本便は `ready` 引数でこれを避ける（4-2）。
- **社内の過去事例（便6・便7）**: 「空振りで緑」を前提の assert で暴く。本便は B1 と「フォーカスできる要素が10個以上」で担保（⑤）。
- **正直な限界**: `inert` を解さない古い閲覧環境では何も変わらない（悪化もしない）。
  また **jsdom は `inert` を実装していない**（`'inert' in el` が false・属性にも反映されない）ので、
  C1〜C4 が保証しているのは「**hook が値を代入したこと**」だけで、属性が付いたことも挙動も測っていない
  （独立審査 N1 の訂正）。「本当に Tab が拒まれるか」は**画面検査（本物のブラウザ）が唯一の一次情報**。
  例外は C8 で、**本物のブラウザの決まり2つ（inert は属性に反映される／inert な枝では `focus()` は何もしない）を
  検査の中で模す**ことで、順序の罠だけは単体で固定できる。

## ⑩ 弊害・トレードオフ

| # | 弊害 | 判断 |
|---|---|---|
| T1 | 閉じているパネルの中身は**クリックもできなくなる**（`inert` は pointer events も止める） | 画面の外にあるので実害なし。むしろ事故防止 |
| T2 | 閉じる動き（280ms）の最中、中身はもう無効 | 閉じる操作をした直後なので実害なし。見た目は不変（K3・B 系で見張らない代わりに CSS を1行も触らないことで担保） |
| T3 | `Drawer` 35ファイル・`Sheet` 2ファイルに一度に効く | 変わるのは「閉じている間の Tab と読み上げ」だけ。C5 で開いているときの退行を見張り、B3 で開いた側が無効化されないことを機械で固定 |
| T4 | `inert` はリポジトリ初使用 | 標準機能で、解されない環境では現状と同じ。4-1 に根拠 |

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/drawer-inert-closed.spec.ts`（CI の画面検査で毎 PR・3幅）＋ `frontend/src/hooks/useFocusTrap.test.tsx`（`npm run test:unit` と pre-commit の単体）

- `inert` を外すと C1・C4 と B1・B2 が赤になる。
- 新しくパネルを足した画面でも、金型を使っていれば**自動で無効化される**（呼び出し側の作業は不要）。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| F1 | 便7 の **E1**（初期フォーカス・復帰の共通化）・**E5**（最初から `open=true` でマウントすると出口封じも初期フォーカスも付かない）・**E6**（2枚開いているときは最前面が勝つ）・**E7**（選択子の定義1か所の歯止めを強める） |
| F2 | **D2＝メルカリの表示サイズ感**（操作部分の文字 12px→16px・行 44px→48px）。PO 決定（2026-10-27）で「**まず操作部分→本番で見て一覧も直すか判断**」「**他の宿題のあと**」 |
| F3 | 便6 からの **C-up**（下が狭いとき上へ反転）・**C-out**・**C-sb**・**C-perf**・**C-tap**（popover 層の選択肢が44px未満） |
| F4 | `Modal`・`Sheet` に単体テストが1件も無い（便7 の E4）。本便で `Sheet` には C4 が入るので、残りは `Modal` |
| F6 | **`FOCUSABLE_SELECTOR` の写しが `tests-e2e/` 側に2つある**（`frontend/tests-e2e/visual-language/viewer-focus-trap.spec.ts`・本便の `frontend/tests-e2e/visual-language/drawer-inert-closed.spec.ts`）。便7 の C11（定義は1か所）は `src/` 配下しか見ない（`frontend/src/hooks/useFocusTrap.test.tsx` の `SRC_ROOT`）ため、検査側の写しは**歯止めの外で静かにずれる**（独立審査 N3） |
| F7 | **`tests-e2e/` は既定の型検査・lint の対象外**（`frontend/tsconfig.json` の `include` が `["src"]`・`npm run lint` は `eslint src`）。本便の新 spec は**手で型検査して0件**を確認したが、仕組みとしては野放し。CI か手順に組み込む（独立審査 N4） |
| F8 | `useInertWhenClosed` の `ready` は依存配列専用で effect 本文では使っていない。`if (!ready) return;` の形にすると自己説明的になる（独立審査 N7） |
| F5 | **`frontend/src/components/loading/Drawer.tsx`・`frontend/src/components/Modal.tsx`（使われていないもう一つの実装）を正本へ接続する**。PO 決定（2026-10-27）で**本便は対象外**。事実: 入口 `frontend/src/components/loading/index.ts` から export され README にも記載があるが、**名前で取り込んでいるファイルは0件**。閉じたときは `aria-hidden={!open}`（`frontend/src/components/loading/Drawer.tsx:29`）で読み上げからは外れるが **Tab の通り道からは外れない**（同じ穴が半分ある）。正本 `docs/specs/design-system/design.md:269` が「同名だからと直ちに削除しない／公開入口を既存正本へ接続する」と定めているため、削除・export 外しは正本側の変更を伴う別便 |

## 対象 ADR

- **ADR-144**（UI 共通部品の遵守ガバナンス）: §1。金型の内部だけを直すので §4 の「金型新設」には当たらない。
- **ADR-027**（i18n 強制）: 文言は1つも追加・変更しない。
- **ADR-067**（デザイントークン強制）: **CSS を1行も触らない**ため対象外（案 B を採らない理由の1つ）。
