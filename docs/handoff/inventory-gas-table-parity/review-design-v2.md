# 設計再審査: GAS 在庫一覧の表を閲覧ページと同じ形にする（design.md 第2版）

審査: Reviewer（Opus）／2026-10-19／読み取りのみ
照合: `diff design-v1.md design.md`、G=~/CC報告ファイル-keep/inventory-sort-3choices/gas/test_stage/index.html、origin/main 83948a58f、test_deployments.txt・prod_deployments.txt・pull_now_test/・pull_now_prod/
判定: APPROVE（指摘はすべて反映済み。新しい問題は見つからず、直すかどうか任意の点が1件だけ）

## 前回の指摘ごとの反映

| 番号 | 反映箇所（design.md 第2版） | 確認結果 |
|---|---|---|
| A1 | 3-5 に `.supplier-cell`（flex column）を追加。3-7 の提供者セルを `<div class="supplier-cell"><span>…</span><span class="inventory-cell__sub">…</span></div>` に。T7 に「時刻がラベル側に落ちない」を追加 | ○。td の子は ::before と包み1つの2要素になり、2列グリッド（G:721-727）に収まる |
| A2 | T4 を `grep -nE '\.badge\b\|badge-(sealed\|…)\|badgeCondition\|badgeStatus'` に変更 | ○。今のファイルで試した当たり: G:461、G:468-473、G:475、G:1576、G:1578、G:1696-1709 だけ。どれも 3-5・3-7 で消すか直す行。`--comp-badge-*`（G:25・26・464・476・570）は当たらない。変更後は 0 件になれる |
| A3 | 3-7 に「:1573-1574 を削除」と追加。T4 を「`COL.postedAt` は2件だけ（絞り込み :1361 と提供者セル）」に変更 | ○。今の場所は G:1361・1532・1573。colDefs の行と分岐を消し、提供者セルを足すと2件になる |
| A4 | 6章に事前確認（テスト @26・本番 @17、pull 照合で差0）を追加 | ○。【事実】test_deployments.txt は `@26`、prod_deployments.txt は `@17`。`diff -rq -x .clasp.json pull_now_test test_stage` → 差なし、`diff -rq -x .clasp.json pull_now_prod prodpull` → 差なし（審査で再実行） |
| B1 | `.title-cell__ja` は色を指定しない（td の --text-secondary を受け継ぐ） | ○。inventoryColumns.css:1-4、DataTable.css:49 と一致 |
| B2 | `th.align-right` を追加し、`col.align === 'right'` の見出しに付ける | ○。詳細度（0,1,1）が `th`（0,0,1）に勝つ。navy-trial（G:794-802）と PC 幅の調整（G:785）は text-align を書いていないので、ぶつからない |
| B3 | 3-2 を th :406-416・td :436-443 に、3-4 を :452-455 に、OFFER_TYPE_TO_STATUS を :278 に修正。閲覧側の行番号は「付近」と書く形に | ○（下の任意1を除く） |
| B4 | 単価は `Number(val)` と `isFinite` で判定し、parseFloat は使わない。T0 に '1200'→¥1,200、'abc'→空、''→空 | ○。viewerColumns.tsx:17-21 と同じ |
| B5 | 数量は3桁区切りしない。mobileLabel '価格' を削除して「単価」に。formatPostedAt は読めないとき空文字 | ○。【事実】formatPostedAt を呼ぶのは G:1574 だけ（grep で確認。G:959 は定義）なので、変更の影響は提供者セルだけ。24時間以内の絞り込み（G:1361）は parsePostedAt を直接使うので影響なし |
| B6 | :475 のコメントを「金型 Badge sm と同じトークン」に | ○。inventoryColumns.css:51 と同じ言い方 |
| 推奨（前回 C） | 前回の deploy_prod.sh は実行しないと 6章に明記 | ○ |

## 新しい点（第2版で増えた記述）

- 新しい問題はなし。
- T3 に「Sold out→色なし」が増えた。閲覧の offer_type が null のときの見せ方（viewerColumns.tsx:36-38 `it.status || "-"`）と同じ。
- 任意1（直さなくても判定は変わらない）: 3-7 のステータスの根拠が viewerColumns.tsx:37-44 のまま。実物は :36-43。他の閲覧側の行番号は「付近」に直してあるので、ここだけ揃っていない。
