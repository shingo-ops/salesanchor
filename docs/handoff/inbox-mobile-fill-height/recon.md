# recon: 一覧の面を画面の下端まで届かせる（現状把握）

調査日 2026-10-13 / ブランチ `release/inbox-mobile-fill-height`（`origin/main` 起点）

経緯: PR #4184 で配色を直したが、**地の一本化だけ未達**だった（投入後の実機測定）。PO 選択は「(A) 受信箱のスマホ幅だけで伸ばす」。あわせて PO 質問「他の画面はその画面を作るときに考えた方がいい？」「WhatsApp はどうなっている？」に実測で答える。

## A. お手本（WhatsApp・ライト・チャット一覧）の実測

| 指標 | 値 |
|---|---|
| 最大の色 | 白 **79.76%** |
| その色が**全幅を占める範囲** | **y=111〜2129**（画面の上端から下端まで） |
| 最後の行より下（y=1600 / y=2000） | **どちらも白**（＝一覧の面と同じ色） |
| 2段目の面 | 5.96% |
| 強調色（緑） | 1.98% |

**つまり会話が少なくても一覧の面を画面の下端まで敷いている。** 空き領域は「背景」ではなく「まだ行が無い一覧の続き」として同じ色。

## B. 当方（PR #4184 投入後）の実測

| 指標 | 値 |
|---|---|
| 最大の色 | 白 **45.73%** |
| その色が全幅を占める範囲 | **y=141〜1429 で止まる** |
| y=1600 / y=2000 | どちらも `--bg-primary`（別の色） |
| ページの地が全幅を占める帯 | **y=1431〜2125（231dp）** ＝一覧の最後の行より下 |
| 行の左右 | **x=0〜1080（左右対称・達成済み）** |
| 12px の副文字 | **7.53:1**（達成済み・投入前 3.74:1） |
| 受信の吹き出し | `--neutral-bg` **10.82%**（達成済み・純灰は消滅） |

配信CSSに `inbox-wrapper{background:var(--bg-surface);padding-left:0}` が入っていることを確認済み＝**指定は効いているが、届く範囲が足りない**（`.inbox-wrapper` 自身の箱が内容の高さで終わる）。

## C. 高さの鎖（コード上の作り）

| # | 事実 | 根拠 |
|---|---|---|
| C1 | `.page-layout` は縦並びの flex で `height: 100%` | `frontend/src/pages-layout.css` の `.page-layout` 規則 |
| C2 | `.page-layout-content` は `flex: 1; min-height: 0; overflow-y: auto` | 同ファイルの `.page-layout-content` 規則 |
| C3 | 受信箱は `.page-layout-content--no-scroll`（`overflow-y: hidden`・`padding: 0`） | 同ファイル |
| C4 | `.inbox-wrapper` は `height: 100%` | `frontend/src/pages/inbox/InboxPage.css` の `.inbox-wrapper` 規則 |
| C5 | スマホの殻は `.mobile-content { flex: 1; overflow-y: auto; padding-bottom: calc(var(--tabbar-height, 56px) + env(safe-area-inset-bottom, 0px)) }` | `frontend/src/mobile-shell.css` |
| C6 | `.mobile-shell` は `min-height: 100dvh`（`height` ではない） | 同ファイル |
| C7 | **`--tabbar-height` はトークンとして登録されていない**（2箇所とも代替値付きで参照） | `frontend/src/mobile-shell.css` の2箇所のみ |

**鎖はコード上は繋がって見えるのに、実測では切れている。** どの段で切れているかは画素だけでは分からないため、本便では**画面検査に各段の高さを記録させる**（`height-chain` という添付）。

## D. 「他の画面も同じ扱いにすべきか」への答え（実測）

| 事実 | 値 |
|---|---|
| `PageLayout` を使うページ | **84枚** |
| そのうち全画面型（`noScroll`）| **9枚**（`frontend/src/pages/inbox/InboxPage.tsx` を含む） |
| 残り | **75枚が書類型**（カードが上から下へ流れる） |

書類型では「薄く色の付いた地にカードが乗る」**2段構造が正しい設計**で、今回の症状は欠点ではない。全画面型の9枚も中身の作りが違う（受注管理・顧客ハブ・スケジュール等）ため、1つの共通修正で全部が良くなるとは言えない。**よって受信箱だけに入れ、他は各ページを作る/直すときに同じ尺度（画素を数える）で判断する**のが妥当。共通化は同じ症状が並んだ時点で金型へ上げる。

## E. 本便で選ぶ手段と、採らない手段

| 手段 | 判断 |
|---|---|
| **本文の領域に面の色を敷く**（`.page-layout--slim-header .page-layout-content`） | **採用**。`.page-layout-content` は `flex: 1`（C2）で本文の高さを持つ段。`slimHeaderOnMobile` を渡しているのは受信箱だけなので対象は受信箱に限られる |
| `min-height: calc(100dvh - ...)` で伸ばす | 採らない。`--tabbar-height` が未登録（C7）で、`overflow-y: hidden`（C3）のため溢れた分が切れる恐れがある（会話画面では操作行44dpぶん下が切れる） |
| 高さの鎖を整理する | 採らない（PO 選択は (A)）。`frontend/src/pages-layout.css` / `PageLayout` / `MobileShell` に波及する |
| `.mobile-content` に色を敷く | 採らない。全84ページに効いてしまう |
