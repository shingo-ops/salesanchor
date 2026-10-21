# コード審査: GAS 在庫一覧の表を閲覧ページと同じ形にする（設計 第2版に対する実装）

審査: Reviewer（Opus）／2026-10-19／読み取りのみ（clasp 未実行・ファイル変更なし）
対象: G2=~/CC報告ファイル-keep/inventory-gas-table-parity/gas/test_stage/index.html（基準 testpull/index.html）
照合先: origin/main 83948a58f（viewerColumns.tsx・conditionBadge.ts・inventoryColumns.css・locales/viewer/ja.json・index.css・tokens.css・tcg_distribution_svc.py）
自分で回した検査の出力: /tmp/CC報告ファイル/inventory-gas-table-parity/review-code/（script.js・harness.js・rerun.txt・xss.js・xss.txt・xss_rendered.html・rendered_review.html）

## 1. 設計3章との一致（T8_diff.txt の全ての塊を設計に当てた）

| 設計 | 実装（test_stage 行） | 判定 |
|---|---|---|
| 3-1 トークン4つ・:8 コメント | :8 コメントに「追加4つは origin/main 9c7bbb917」、:10-13 に4値 | ○ 値は 9c7bbb917・83948a58f どちらの index.css:55/:125・tokens.css:392/:393 とも一致。:root 内で重複定義なし |
| 3-2 th/td 左寄せ・th.align-right | th/td `text-align:left`、`th.align-right` 追加、thead で `col.align==='right'` に付与 | ○ |
| 3-3 固定列を col-sticky へ・:786・:794 | :433-439・:451 を col-sticky に、:787 と :795 にセレクタ追加、col-title はスマホカード用（:747-759）に残置 | ○ |
| 3-4 商品名 | `.title-cell__ja` semi（色指定なし）／`.title-cell__en` secondary・sm。描画は JA 常に上・EN は値があるときだけ | ○ inventoryColumns.css:1-10・viewerColumns.tsx:57-62 と一致 |
| 3-5 文字色クラス・.supplier-cell・badge 削除・コメント | 9クラス追加、.badge 系削除、:476 コメント「金型 Badge sm と同じトークン」 | ○ inventoryColumns.css:23-49 と同名・同トークン |
| 3-6 列定義・mobileLabel 削除・th/td クラス | 10列の順・見出し・align・sortable・mobileOrder・mobileHidden・stickyCol が設計の表と一字一句一致。data-label は col.label | ○ locales/viewer/ja.json の col と一致 |
| 3-7 セル中身 | offerCell（完全一致 'In Stock'/'Pre-order'、他は値か '-'）、conditionClass/conditionCell、型番・発売日 '-'、単価 Number+isFinite+¥、数量そのまま、提供者 supplier-cell＋下段、postedAt 分岐削除、formatPostedAt 空文字 | ○ conditionBadge.ts:17-35 と同じ12値・同じ割り当て。OFFER_TYPE_TO_STATUS（tcg_distribution_svc.py:277）と同じ値 |

範囲外の変更: なし。【事実】`diff -rq testpull test_stage` は index.html のみ。差分の塊はすべて上表のどれかに当たる。並び替え（toggleSort・applySortValue・compareRows・markBlockFlags）・絞り込み・紺ブロックの色値・塗り（cell-value）は未変更。

## 2. 閲覧ページとの一致で残る差（すべて設計で対象外または設計どおり。判定に影響なし）
- 閲覧は各セルに `inventory-cell__nowrap`（PC で折り返さない）。GAS は商品名とステータス列以外に nowrap を付けていない。設計の対象に含まれない既存の差。
- 閲覧は投稿日時が空でも下段の div を出す。GAS は空なら出さない（設計 3-7 の指定どおり。見た目は同じ）。
- 単価の区切りは閲覧が `toLocaleString()`、GAS が `toLocaleString('ja-JP')`（日本語環境なら同じ表示）。

## 3. escHtml（XSS）
- 【事実】新しく作った HTML は、セルの値をすべて escHtml を通している（商品名 JA/EN、提供者、投稿日時、コンディション、ステータスのその他値、型番・発売日、単価・数量）。offerCell の「在庫」「予約」と CSS クラス名は固定文字列。
- 【事実】自分で試した: 全項目に `<img src=x onerror=alert(1)>"'&` を入れて renderTable → 生の `<img` 0件、`&lt;img` 19件（review-code/xss.txt）。19件＝1行目10項目（単価は数値でないため空、投稿日時は読めないため空）＋2行目9項目で、全項目が逃がされている。

## 4. スマホ・固定列・紺見出し・並び替え・絞り込み
- 固定列: PC の sticky は `th.col-sticky, td.col-sticky`（ステータス列だけ）。スマホではステータス列は mobile-hidden（:754）。スマホの td.col-title の static 指定は残るが無害。
- 紺見出し: `th.col-sticky` の白背景（:438、詳細度 0,1,1）は後ろの navy `th.col-sticky`（:795、同じ詳細度で後勝ち）に上書きされる。hover は `th.sortable:hover`（0,2,1）が勝つ。
- 右寄せ見出し: `th.align-right`（0,1,1）が `th`（0,0,1）に勝ち、navy ブロックは text-align を書かないのでぶつからない。
- スマホの並び: mobileOrder 1〜7＝商品名→コンディション→単価→数量→備考→発送→提供者、型番・ステータス・発売日は非表示。提供者は supplier-cell 1要素に包まれ、2列グリッドの値側に入る。
- 並び替え: 列の idx は COL のままで、toggleSort(col.idx) も変わらない。投稿日時の見出しは消えたが、選択肢 `0_desc 投稿が新しい`（:845）は残る。
- 絞り込み: 24時間以内の絞り込み（:1362）は parsePostedAt を直接使い、formatPostedAt 変更の影響なし。【事実】formatPostedAt の呼び出しは :1577 のみ。

## 5. 受入台本は本当に検査になっているか
- 【事実】harness.js は index.html から取り出した script を vm で実行し、本物の renderTable の出力 HTML を完全一致または包含で照合している（見出し10個の並び、th のクラス、各セルの HTML）。
- 【事実】自分で test_stage/index.html の :935-1759 を取り出し直し（担当の script.js とは先頭の空行1つだけ違う）、`node --check` rc=0、同じ台本を実行 → 24項目すべて OK・rc=0（review-code/rerun.txt）。
- 【事実】T4: 自分で grep した結果、badge 系は0件、`COL.postedAt` は :1362・:1577 の2件だけ（設計どおり）。
- 台本が見ていない点: mobileOrder/mobileHidden の値、`num` クラス。差分を目で照合して設計どおりと確認済み。スマホの見た目は T7（PO 目視）で見る。

## 6. 配備台本
| 確認 | deploy_test.sh | deploy_prod.sh |
|---|---|---|
| 期待版 | `@26( \|$)` で照合、合わなければ中止 | `@17( \|$)` で照合、合わなければ中止 |
| DEPLOY_ID | test_deployments.txt の @26 の ID と一致 | prod_deployments.txt の @17 の ID と一致（テストの ID とは別） |
| 事前照合先 | testpull（1Tb）。pull_now_test と差なし | prodpull（1hc）。pull_now_prod と差なし |
| push 元 | test_stage（.clasp.json scriptId 1Tb…） | prod_stage（1hc…）。index.html は test_stage と同じ、Code.js・appsscript.json は prodpull と同じ |
| 版メモ・戻し方 | 設計6章どおり／版26へ redeploy | 設計6章どおり／版17へ redeploy |
- 事前 pull の一時フォルダは G2 直下に作るので、push 元フォルダの下には入らない。
- 旧 sort-3choices/gas/deploy_prod.sh は新しい台本から呼ばれていない。

## 7. 指摘
- 直すべき点: なし。
- 任意（判定に影響なし）: 上の2章の nowrap の差は、閲覧と完全に揃えたいなら別便で扱う。

VERDICT: APPROVE
