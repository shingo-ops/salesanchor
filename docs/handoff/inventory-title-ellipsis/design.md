# 設計: 在庫表の商品名を「…」で省き、表が縮まないようにする（第3版）

第2版の変更: 審査 review-design.md の A1〜A5 と B1・B3〜B6 を反映した（第1版は design-v1.md）。
第3版の変更: 再審査 review-design-v2.md の A1〜A3・B1〜B3 を反映した（第2版は design-v2.md）。

状態: 設計案（Opus）。PO 決定 2026-10-20「1」（商品名は1行のまま幅の上限を決め、超えた分は「…」、マウスを乗せると全文、備考・発送は折り返す）。

## 1. 目的・利用者に見える変化
- 今: 全て・ワンピース・ポケモンのタブだけ表全体が小さくなる。原因は、PC 幅では文字を折り返さない設定のため、長い文字で表が横に広がり、`fitToWidth`（アプリ `frontend/src/hooks/useFitTableZoom.ts`、GAS `fitTableZoom`）が表全体を縮めること。
- 後: 商品名（日本語の段・英語の段）は1行のまま、上限幅を超えた分は末尾が「…」になる。マウスを乗せると、その段の全文が出る。備考・発送は上限幅で折り返す。表の横幅が抑えられ、縮みにくくなる。
- 対象: アプリの在庫表（/inventory）、閲覧ページ（/viewer/）、GAS 在庫一覧（テスト→本番）。
- 対象外: スマホ幅（767px 以下のカード表示。今のまま折り返す）、縮める仕組み自体（窓が狭いと他の列のために縮むことは残る）、見出し、ほかの列。

## 2. 根拠（recon: docs/handoff/inventory-title-ellipsis/recon.md、生データ /tmp/CC報告ファイル/inventory-title-ellipsis/recon/）
- 商品名セル: `frontend/src/features/inventory/inventoryColumns.tsx:100-105`、`frontend/src/pages/viewer/viewerColumns.tsx:57-62`（上段 `inventory-cell__title`、下段 `inventory-cell__sub`）。
- 備考・発送: inventoryColumns.tsx:169・:178、viewerColumns.tsx:107・:113（`inventory-cell__nowrap`）。`inventory-cell__nowrap` は型番などほかの列でも使うので変えない。
- 折り返し禁止: `frontend/src/features/inventory/inventoryColumns.css:12-20`（768px 以上）。
- DataTable の `ellipsis` は、中身が JSX だと title が付かない（DataTable.tsx:446）。2段の商品名には使わず、列側の CSS で行う。
- トークン: `--col-width-wide: 360px`（tokens.css:427）、`--col-width-medium: 200px`（:426）。
- 本番24時間の文字数（近似。products の名前、1145行。lengths.tsv）: 日本語 p50 9・p90 31・最大47文字、英語 p50 15・p90 38・最大60文字、発送 最大34文字。
- GAS（本番版18 = テスト版27、cmp 一致）: 商品名 :1569-1575（`.title-cell__ja`・`.title-cell__en`）、備考・発送は素のテキスト（:1599-1600）、列定義 :1533-1545、table 全体が nowrap（:405）、CSS :458-460。

## 3. 変更内容
### 3-1 トークン（frontend/src/tokens.css の --comp-table 群の近く）
```
--comp-inventory-title-max-w: var(--col-width-wide);   /* 商品名1段の上限幅 */
--comp-inventory-text-max-w: var(--col-width-medium);  /* 備考・発送の折り返し幅 */
--comp-inventory-text-min-w: calc(var(--col-width-medium) / 2);  /* 備考・発送の最小幅（A1: 1文字幅まで細らない） */
```
ダーク用の再定義は要らない（色ではない）。
- A3: ADR-067 のトークン表（ADR-067:123-128 付近）に3つを足す（最小幅は calc の式と計算後の 100px を並べて書く）。同じ便で表の `--col-width-wide` の値を実物の 360px に直す（ADR-067:68。B6）。PR 本文の「デザイントークン変更時」チェック欄を全部埋める（scripts の check-new-tokens.js:79-110 が見る）。

### 3-2 CSS（inventoryColumns.css の 768px 以上の @media の中に追加）
```
.inventory-cell__clip {
  max-width: var(--comp-inventory-title-max-w);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;   /* B1: 自分で持つ */
}
.inventory-cell__wrap {
  display: block;
  max-width: var(--comp-inventory-text-max-w);
  white-space: normal;
  overflow-wrap: anywhere;
}
.inventory-cell__wrap:not(:empty) {
  min-width: var(--comp-inventory-text-min-w);  /* 第3版 A1: 空のセルでは列を広げない */
}
```
- 12-13行のコメントを「商品名は上限幅で…省略、備考・発送は上限幅で折り返す。それでもはみ出す分は fitToWidth が縮める」に直す。
- 767px 以下には足さない（カード表示は今のまま）。

### 3-3 列（inventoryColumns.tsx と viewerColumns.tsx。同じ形）
- 商品名: 上段 `<div className="inventory-cell__title inventory-cell__clip" title={<上段の文字>}>`、下段 `<div className="inventory-cell__sub inventory-cell__clip" title={<下段の文字>}>`。title に入れる文字は表示と同じ（在庫表は `it.product_name ?? \`#${it.product_id}\``、閲覧ページは `it.japanese_title`。下段は name_en / english_title）。
- 備考・発送: `inventory-cell__nowrap` を `inventory-cell__wrap` に替える（4か所）。
- 全文は、省略されていなくても title で出る（ブラウザ標準の吹き出し）。省略したときだけ出す処理は足さない（簡単さを優先）。

### 3-4 GAS（index.html。テスト版27を元に stage を作る）
- 作業前に本番とテストを clasp pull（Opus が読み取りで実行）し直し、index.html の sha が版18・版27と同じか確かめる（B3）。違えば止めて報告。
- :root にトークンを写す: `--comp-inventory-title-max-w: 360px; --comp-inventory-text-max-w: 200px; --comp-inventory-text-min-w: 100px;`（「正本 tokens.css の写し」とコメントを付ける）。
- CSS は既存の PC 用 `@media (min-width:768px)`（GAS :782-788）の中に入れる（A2）。スマホのカード表示には何も効かせないので、打ち消しは要らない:
  - `.title-cell__ja, .title-cell__en { max-width: var(--comp-inventory-title-max-w); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }`
  - `td.col-wrap { white-space: normal; overflow-wrap: anywhere; }`、`td.col-wrap .cell-wrap { display:block; max-width: var(--comp-inventory-text-max-w); }`、`td.col-wrap .cell-wrap:not(:empty) { min-width: var(--comp-inventory-text-min-w); }`（空の値は escHtml('') で span の中身が空になる）。
- 列定義: 備考・発送に `wrapCol: true`。td に `col-wrap` を足す。中身を `<span class="cell-wrap">` で包むのは、最後の else 分岐（:1598-1600）の中だけにする（B4）。
- 商品名の2つの span に `title="<escHtml した同じ文字>"`。escHtml は `"` を逃がす（GAS :1748-1754 で確認済み）。

### 3-5 試験
- inventoryColumns.test.tsx と viewerColumns.cells.test.tsx に、次を確かめる検査を足す。
  - 商品名の2つの段に `inventory-cell__clip` と、全文の title が付く。
  - 備考・発送に `inventory-cell__wrap` が付き、`inventory-cell__nowrap` が付かない。
  - 備考・発送の値が空なら、wrap の span の中身が空（:not(:empty) の最小幅が効かない形）。
  - 在庫表で product_name が空なら、上段の title が `#<product_id>` になる。英語名が無ければ下段は出ない（B5）。
- 既存の試験は全部通ること。

### 3-6 記録
- ADR-1014 の末尾に「## 改訂 2026-10-20（商品名を1行のまま「…」で省き、備考・発送は折り返す）」を追記する（その日の最初の改訂は番号なし。ADR-1014:40・:68）。並びは改訂 2026-10-19（7）（:135-144）と同じで、PO 決定・内容・正本・GAS で出せないもの（無ければ省く）・反映・戻し方・記録。
- docs/handoff/inventory-title-ellipsis/（recon・design・審査）。

## 4. 代替案
- 折り返し（PO が却下）。縮めを止めて横スクロール（PO が選ばず）。DataTable の `ellipsis`（JSX では title が付かず、2段を1つの枠で切るので「…」が出ない）。Tooltip 部品（GAS では使えず、揃わなくなる）。

## 5. リスクと対処
- 日本語 p90 は31文字。360px では一部の名前で末尾が隠れる（隠れる件数は未測定）。対処: 上限はトークン1つで変えられる。PO の目視で調整。
- 窓が狭いと、ほかの列のためにまだ縮むことがある（設計どおり。縮める仕組みは残す）。
- 備考・発送が折り返した行は高くなる。
- A1: 表は width:100%（DataTable.css:13-22、GAS :400-402）。最小幅（100px）を付けないと、縮む前に備考・発送の列が1文字幅まで細る。最小幅で防ぐ。空のセルには最小幅を付けない（本番24時間の備考は全行空。付けると備考の列が広がり、目的と逆になる）。
- 発送が100px未満の短い文字だけのタブでは、発送の列が100pxまで少し広がる（許容）。
- 360px は日本語でおよそ26文字。24時間の日本語名 p90 が31文字なので、1割以上の名前の末尾が「…」になる（B2。完了報告で PO に伝える）。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 商品名の2つの段に clip と全文の title | 試験（在庫表・閲覧） |
| K2 備考・発送が wrap、nowrap でない | 試験 |
| K3 CSS とトークンは直書きなし、ADR-067 のチェックが通る | CI 全緑 |
| K4 本番の配信 CSS に `inventory-cell__clip` と `--comp-inventory-title-max-w` | 本番の配信物を取得して grep |
| K5（任意）縮み倍率の自動計測。GAS は Google のログインと外側のページの枠の中に出るため、計測できなければ「未計測」と記録し、K6 で判定する | 担当が試みる |
| K6 PO 目視（GAS テスト版28、普段使う画面の幅）: (a) タブ「全て」と「ドラゴンボール」（PO の画面写しのタブ列にある）の文字の大きさが同じ (b) 「全て」の「30th CELEBRATION カードセット9種セット プロモのみ（27枚）」の行（PO の画面写し 2026-10-20 に写っている。日本語で約37文字＞上限の約26文字）の日本語の段が「…」で終わる (c) その段にマウスを乗せると全文が出る | PO が ○× |
| K7 アプリの在庫表と閲覧ページで K6 の (a)〜(c) | PO が ○×（本番反映後） |
| K8 GAS 本番版19の中身が stage と差0 | clasp pull して照合 |

## 7. 戻し方
- アプリ: PR を revert。GAS: 本番は版18、テストは版27へ戻す（版番号は反映時の実際の値を記録する）。

## 8. 外部・過去事例の参照と我々への応用
- 該当なし。ブラウザ標準の text-overflow と title だけを使い、新しい仕組みを入れないため、外部事例を根拠にする必要がない。
- 過去事例: GAS 在庫一覧の表を閲覧ページの形に揃えた便（ADR-1014 改訂 2026-10-19（7））と同じく、アプリと GAS を同じ設計で揃え、GAS は stage を差0で照合してから反映する。

## 9. 維持の仕組み
- 守り手: frontend/scripts/check-css-hardcoded-values.js（CI と commit 前の検査で CSS の数値直書きを止める。上限幅は tokens.css の3つのトークンだけで決まり、ADR-067 のトークン表に記載）
- GAS の :root にある写し（360px・200px・100px）は、正本トークンを変えたときに一緒に直す（ADR-1014 改訂 2026-10-20 に記載）。
