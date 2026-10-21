# 設計審査: 在庫表の商品名を「…」で省く（design.md 第1版）

審査役: Opus（読み取りのみ）。起点 origin/main = 95e623fd3。GAS は pull_after_prod18/index.html（sha 8d63c62f2b8e。pull_after_test27・keep の test_stage/prod_stage と同じ sha）。

## 確認できたこと（【事実】）
- 行番号は全部合っている: inventoryColumns.tsx:100-105・:169・:178、viewerColumns.tsx:57-62・:107・:113、inventoryColumns.css:12-20、DataTable.tsx:446（`title={typeof content === 'string' ? content : undefined}`）、tokens.css:426・:427、GAS :405・:458-460・:1533-1545・:1569-1575・:1599。
- 「…」の効き方: 同じ形（td の中の block div に max-width＋overflow:hidden＋text-overflow:ellipsis＋nowrap）が既に DataTable の ellipsis 列で使われている（frontend/src/components/DataTable.css:58-68 `.comp-table__cell-ellipsis`）。table-layout は auto（DataTable.css:21-24 に table-layout 指定なし）。max-width が px なので、セルの幅の計算でも上限で頭打ちになり、上段・下段とも各段で省略される。上段・下段の nowrap は inventoryColumns.css:15-18 が付ける。
- GAS の `.title-cell` は flex の縦並び（GAS :458）。中の span は flex の子なので block 扱いになり、省略が効く。
- アプリのスマホ表示: 新しい規則は 768px 以上の @media の中だけ（inventoryColumns.css:14）なので、カード表示（DataTable.css:287-323）は変わらない。
- escHtml は `"` を `&quot;` に変える（GAS :1748-1754）。
- 試験ファイルは実在する: frontend/src/features/inventory/inventoryColumns.test.tsx、frontend/src/pages/viewer/viewerColumns.cells.test.tsx。並びの対称性の試験 viewerColumns.parity.test.tsx:19-23 は className を見ないので、壊れない。
- 色は使っていない。値は var() だけなので check-css-hardcoded-values.js（opacity/radius/z-index/時間だけを見る）にもかからない。

## 必須の修正

### A1 備考・発送の列が1文字幅まで細くなる場合がある
- 根拠: 表は `width:100%` で、横スクロール枠の中にある（DataTable.css:13-14・:21-22、GAS :400-402）。今は全部のセルが nowrap なので、セルの最小幅と最大幅が同じになり、入りきらない分は横にはみ出して fitToWidth が縮める（useFitTableZoom.ts:41-44、GAS :1637-1641）。設計 3-2・3-4 の `white-space:normal; overflow-wrap:anywhere` にすると、備考・発送の最小幅は約1文字になる（日本語はどの文字の間でも改行でき、anywhere は最小幅の計算にも効く）。表の自動の幅決めは、はみ出す前に「最小幅と最大幅の差がある列」＝備考・発送だけを細くする。窓が狭いと、2〜3文字ずつ改行された縦長の行になってから縮みに入る。
- 直し方: `.inventory-cell__wrap`（GAS は `.cell-wrap`）に下限の幅を付ける（新トークンか既存の幅トークン）。または、この動きを受け入れるなら「5. リスク」と受入条件に明記する。どちらにするかを設計に書く。

### A2 GAS の新しい CSS を 768px 以上だけに効かせる場所を決める
- 根拠: 設計 3-4 は「PC 幅だけに効く書き方」と書きながら、示した規則は @media の外にあり、スマホでは商品名だけ打ち消す。`.cell-wrap { max-width: 200px }` はスマホのカードにも効く（GAS のスマホ用 td の規則 :722-738 は max-width を戻さない）。アプリ側は 768px 以上だけ（inventoryColumns.css:14）なので、スマホの備考・発送の幅がアプリと GAS で食い違う。
- 直し方: 新しい規則は全部、既存の PC 用ブロック `@media (min-width: 768px)`（GAS :782-788）の中に入れる、と書く。そうすればスマホの打ち消しは要らなくなり、アプリと同じ形になる。

### A3 新しいトークンの手順が抜けている
- 根拠: ADR-067 の「新規トークン追加手順」の4番目「この ADR の『コンポーネントトークン』表を更新」（docs/adr/ADR-067-design-token-enforcement.md:123-128。表は :45-77）。CI の check-new-tokens.js:79-110 は、新しいトークンがあると PR 本文の「デザイントークン変更時」チェック欄が全部 [x] でないと止める。
- 直し方: 3-6 の記録に「ADR-067 の表に2行足す」を入れる。PR 本文にトークンのチェック欄（理由・既存トークンで足りない理由も）を書くことを、作業の手順に入れる。

### A4 K5 が ○× で判定できない
- 根拠: 設計 5 にも「窓が狭いと縮む」とある。窓の幅を決めないと「ほかのタブと同じ大きさ」かどうかが決まらない。変える前の基準値もない（~/.claude/CLAUDE.md「測る前に基準値を取る」）。
- 直し方: 窓の幅を決める（例: PO が普段使う幅と 1440px）。その幅で、変える前と後の縮み倍率（アプリは `.comp-table-fit__card` の `--comp-table-fit-zoom`、GAS は `.table-card` の `style.zoom`）をタブごとに記録する。合格は「全て・ワンピース・ポケモンの倍率が 1（未設定）、またはほかのタブと同じ」。「…」は長い名前の具体的な行を1つ決めて確かめる。

### A5 ADR-1014 の見出しが既存の形と合わない
- 根拠: 改訂の番号は日付ごとに振り直している（ADR-1014:40「改訂 2026-10-18」→ :50「（2）」→ :59「（3）」、:68「改訂 2026-10-19」→ :135「（7）」）。2026-10-20 の改訂はまだ無い。
- 直し方: 見出しを「## 改訂 2026-10-20（商品名を上限幅で…に省き、備考・発送を折り返す）」にする（「（8）」は付けない）。本文は :135-144 と同じ並びにする: PO 決定の原文、「前の節の本文は書き換えない」、内容・正本（GAS の写しも同じ便で直す）・反映（テスト版／本番版の番号）・戻し方・記録。

## 推奨

- B1 `.inventory-cell__clip` に `white-space: nowrap` も書く。今は inventoryColumns.css:15-18 の title/sub の規則に頼っているので、ほかの要素に付けると「…」が出ない。GAS 案は既に nowrap を書いている。
- B2 省かれる量を書く。商品名は表の文字の大きさ `--font-sm` 0.85rem = 13.6px（tokens.css:15）で、360px ÷ 13.6px ≈ 26文字。日本語の p90 は 31文字（recon/lengths.tsv）なので、24時間の日本語名の1割以上が「…」になる。英語は約50文字前後で、p99 の 58 が省かれる。PO の目視の前に伝える。
- B3 GAS の :root の写しは 360px／200px と直接書く案でよい（GAS :9-40 に `--col-width-*` は無い）。コメントには正本「tokens.css `--comp-inventory-title-max-w: var(--col-width-wide)`」を書く。
- B4 GAS の作業の前に、本番とテストをもう一度 pull して、sha 8d63c62f2b8e（版18／版27）のままか確かめる。違ったら止める。
- B5 GAS のセルの包み方は、最後の else 分岐（:1598-1600）の中でだけ行う、と書く。supplier（:1576-1580）・numeric（:1587-1597）などの分岐に手を入れないことがはっきりする。
- B6 試験に、`product_name` が null のとき title が `#<id>` になること、`name_en` が空のとき下段が出ないことを足す。
- B7 ADR-067 の表は `--col-width-wide` を 240px と書いているが、実物は 360px（ADR-067:68 と tokens.css:427 が違う）。A3 で表を触るとき、同じ便で直すとよい。

VERDICT: REVISE
