# 審査記録（Opus Reviewer、設計 第1版〜第3版。原文のまま連結）

---- review-design.md ----
# 設計審査: 並び替えプルダウン 見出し＋3択（design.md 第1版）

審査者: Reviewer（Opus）／2026-10-19／基準: origin/main 70c3eda3d（git fetch 後に rev-parse で確認、design の基準と一致）
変更は一切していない（読み取りのみ）。

## A. 前提・行番号の照合（【事実】）

| 項目 | design の記載 | 実物 | 判定 |
|---|---|---|---|
| Select.tsx placeholder | :100-104 先頭に value="" | frontend/src/components/Select.tsx:100-104 `<option value="" disabled={rest.required}>`。required を渡さなければ disabled にならず選択可能。InventoryPage・InventoryView とも required を渡していない | ○（7章のリスクは発生しない） |
| アプリ SelectControl | InventoryPage.tsx:467-487、選択肢 :481-486、SORT_MENU_VALUES :58、既定 :127-128、placeholder :472、表示値 :473 | 一致 | ○ |
| アプリ resetAll / 見出しクリック | :355-362 / :612-614 | 一致（:353 のコメント「発売日の早い順」は古いが触らない範囲） | ○ |
| アプリ onChange の "" | 「無視/誤処理する場合のみ変更」 | frontend/src/pages/inventory/InventoryPage.tsx:476 `if (!field) return;` で "" を無視する＝変更は必須 | △ 条件付き記述（指摘2） |
| 閲覧 InventoryView | :197-216、表示値 :124/:202 | 一致。onChange は frontend/src/pages/viewer/InventoryView.tsx:205 `if (!k) return;` で "" を無視 | ○（指摘2と同じ） |
| 閲覧 見出しクリック | 記載なし | frontend/src/pages/viewer/InventoryView.tsx:229-233 onSort あり | 指摘1 |
| viewerFilter.ts | 既定 :12-13、SORT_MENU_VALUES :15 | 一致（:14 のコメント「4択」も更新対象） | ○（指摘5） |
| backend | inventory_offers.py:374-379 既定 release_date desc | backend/app/routers/inventory_offers.py:374-379 一致 | ○ |
| i18n アプリ | ja.json/en.json:1563-1568 | 実パスは frontend/src/locales/ja.json・en.json:1563-1568。内容一致 | ○（パス省略のみ） |
| i18n 閲覧 | locales/viewer/ja.json・en.json:28-34 | 一致（placeholder「並べ替え」・postedDesc「投稿が新しい順」、en stockDesc は "Stock: high to low"、アプリ en は "Quantity: high to low"） | ○（指摘5） |
| i18n キーの他参照 | git grep で確認 | `git grep releaseDesc origin/main -- frontend` の .json 以外の参照は InventoryPage.tsx:482 と InventoryView.tsx:211 のみ（docs/handoff の過去設計に文字列はあるがコード参照ではない）→ ja/en 両方から削除可 | ○ |
| GAS 該当箇所 | :840-845 / :938-939 / :1023-1028 / :1187-1189 / :1396 / :1670-1686 | ~/CC報告ファイル-keep/inventory-sort-cond-block/gas/test_stage/index.html で全て一致。test_stage と prod_stage の index.html は diff -q で同一。COL.releaseDate=9（:985）| ○ |
| GAS 初期の並び | 「今のシート順＝sort_ord と同じ順のはず」 | 現行は :1187-1189 で select 初期値 9_desc を読み sortCol=9 desc にしている＝今も開いた直後から発売日の新しい順で並べている（シート順ではない） | △ 前提の書き方が誤り（指摘6） |
| GAS 配備前提 | deploy_test.sh 期待版 25 | deploy_test.log 末尾「Redeployed … @25」でテストは現在 @25。ただし testpull/（13:51）は v25 より前の内容で test_stage と index.html が異なる（diff -rq）→ deploy_test.sh:13-16 の事前照合で「テストが変わっています。中止」になる | × 指摘4 |
| ADR-1014 | :50-55 | docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:55 一致。加えて :46「既定のとき空表示にならないようにした」が今回の方針と逆の理由づけ | △ 指摘7 |
| 試験 | tablelayout.test.tsx:51-69、InventoryView.test.tsx:51-59 | 一致 | ○ |

## B. PO 要望（1章）の充足
- 既定＝発売日の新しい順を維持し、選択肢から外し、未選択時は「並び替え」表示、3画面同形 → 方針として満たす。
- ただし金型の placeholder は選択可能な option なので、開いた一覧には「並び替え」＋3択の4行が出る（GAS も先頭 option を足すので同じ）。PO の「選択肢は3つ」とこの見え方が合うかは design に明記されていない（指摘3）。

## C. SSOT・金型・i18n・ADR
- 金型 Select.tsx を変えず placeholder を使う → ADR-144 と整合。
- i18n: 新キーなし、文言変更と削除のみ、ja/en 同時 → ADR-027 と整合（en の具体値は指摘5）。
- SSOT: アプリ SORT_MENU_VALUES と viewerFilter.ts SORT_MENU_VALUES の二重定義は既存のまま（今回の範囲外、コメントで同一を宣言済み）。
- ADR-1014 改訂（6）追記・README 再生成あり → 整合（指摘7を除く）。

## D. 受入条件の検証可能性
- T1〜T3・T5・T6 は観測可能。T4 は差0判定で一義。T7 は PO 目視だが「何を見て○×か」が無い（指摘3と合わせて記載要）。
- T2 の試験は既定が既に release_date desc のため、「別の値→""」の順で操作し、最後の API 呼び出しが sort=release_date&order=desc であることを見る手順を書かないと、何もしなくても通る試験になりうる（指摘8）。

## 直すべき点（REVISE）

1. 【見出しクリック後に既定へ戻れない】閲覧ページ（InventoryView.tsx:229-233）と GAS（toggleSort :1670-1686）は見出しクリックで3択以外の並び（例: 発売日の古い順・商品名順）になれる。このとき表示値は ""＝「並び替え」が既に選ばれた状態なので、もう一度「並び替え」を選んでも change イベントが起きず、design 3章の「見出しを選び直すのが閲覧ページの戻し方」が成立しない。現行は「発売日が新しい順」を明示的に選べたので、閲覧ページと GAS では戻し方が消える。さらに、既定でないのに「並び替え」（＝既定の意味）が表示される。戻し方（例: 発売日の見出しを押す・再読み込み、または別案）と、既定以外で「並び替え」が出ることを許すかを design に明記し、必要なら PO 確認事項にする。
2. 【条件付き記述をやめる】4-1/4-2 の onChange は「誤処理する場合のみ変更」ではなく、InventoryPage.tsx:476 `if (!field) return;`・InventoryView.tsx:205 `if (!k) return;` が "" を捨てているので変更必須と確定させ、変更前→変更後のコードを書く（CLAUDE.md「Planner が file:line＋変更前後コード」）。
3. 【開いた一覧の見え方を明記し PO 目視の判定に入れる】金型 placeholder は選択可能な option なので、開いた一覧は「並び替え」＋3択の4行になる。これが PO の「選択肢は3つ」に合うことを design に書き、T7 に「閉じた状態で『並び替え』、開くと先頭『並び替え』＋3択、表は発売日の新しい順」のような○×判定を書く。
4. 【GAS テスト配備の事前照合が必ず止まる】testpull/ は v25 配備前の内容（test_stage と index.html が異なる）。deploy_test.sh:13-16 の照合で中止になる。編集前に testpull を現在のテスト（@25）から取り直す手順（PO ! 実行のスクリプトに含める等）と、戻し方の版（テスト 25、本番 17）を 4-4 に書く。
5. 【文言の変更前後を確定させる】viewer en の placeholder/postedDesc/stockDesc を「アプリ側に合わせる（実装者が報告）」ではなく値で指定する（例: stockDesc "Stock: high to low"→"Quantity: high to low" にするか否か）。viewerFilter.ts:14 のコメント「4択」→「3択」も変更対象に入れる。
6. 【GAS 初期の並びの前提を事実に直す】4-4 の「今のシート順＝sort_ord と同じ順のはず」は推測で、かつ現行は :1187-1189 で既に 9_desc（発売日の新しい順）で並べている。「現行も初期化で sortCol=9 desc。変更後は "" を同じ値に解釈するので並びは同一（T4 で差0確認）」と書き直す。
7. 【GAS の見出しクリック時の select 表示を3画面でそろえる】toggleSort で一致する option が無いとき「COL.releaseDate desc なら ''、それ以外は今のまま」だと、直前の選択（例: 価格が安い順）が残ったまま別の並びになる。アプリ・閲覧は一致しなければ常に "" 表示なので、GAS も「一致しなければ ''」にそろえるか、そろえない理由を書く（指摘1の扱いと合わせて決める）。
8. 【ADR 改訂の置き換え範囲】ADR-1014:46「既定のとき空表示にならないようにした」（先頭に発売日を足した理由）も本改訂で置き換える旨を改訂（6）に書く。
9. 【T2/T3 試験の手順を具体化】「別の値（例 unit_price:asc）を選ぶ→"" を選ぶ→最後の /inventory 呼び出しが sort=release_date かつ order=desc、select.value===""」の順を明記（閲覧は captured.props の sortKey/sortDir で同様）。

VERDICT: REVISE

---- review-design-v2.md ----
# 設計再審査: 並び替えプルダウン 見出し＋3択（design.md 第2版）

審査者: Reviewer（Opus）／2026-10-19／基準: git fetch 後の origin/main = 70c3eda3d0d2（design の基準と一致。70c3eda3d..origin/main で対象ファイルの変更なし）
GAS 実物: ~/CC報告ファイル-keep/inventory-sort-cond-block/gas/ の test_stage・prod_stage・pull_v25_1792391192・prodpull・deploy_*.sh・deploy_test.log
何も変更していない（読み取りのみ）。

## A. 第1版の指摘1〜9 の解消状況（【事実】）

| # | 指摘 | 第2版 | 判定 |
|---|---|---|---|
| 1 | 見出しクリック後に既定へ戻れない | 3-1 で「3択→見出し／再読み込み／アプリはリセット」を明記し、既知の制限として ADR 改訂（6）に書く。現行も4値以外は "" 表示である点も事実どおり（InventoryPage.tsx:473、InventoryView.tsx:202） | ○（Opus 判断。PO に伝えるかは任意） |
| 2 | onChange を条件付きでなく確定 | アプリは変更前後コードあり。InventoryPage.tsx:474-480 の実物（:475 split、:476 `if (!field) return;`）と変更前コードが一致。閲覧は文で指定（DEFAULT_SORT_KEY/DIR は InventoryView.tsx:16-17 で import 済み、:63-64 で使用済み）。 | ○（下記 小1） |
| 3 | 開いた一覧の見え方・T7 | 1章「見え方」と T7 の4項目○×で記載。Select.tsx:100-104 は required 無しで選択可能＝記述どおり | ○ |
| 4 | testpull が古く事前照合で止まる | testpull を pull_v25_1792391192 の写しにする。`diff -rq test_stage pull_v25_1792391192` 差0（.clasp.json 含む）。deploy_test.log 末尾 @25、期待版25 と一致 | ○（ただし本番側に新たな漏れ＝指摘B1） |
| 5 | 文言を値で確定・:14 コメント | viewer ja placeholder「並べ替え」→「並び替え」、postedDesc「投稿が新しい順」→「投稿が新しい」、en stockDesc "Stock: high to low"→"Quantity: high to low"。変更後はアプリ側 locales/ja.json・en.json:1563-1568 の値と一致。viewerFilter.ts:14 コメントも対象 | ○ |
| 6 | GAS 初期並びの前提 | 「現行も :1187-1189 で 9_desc を読む」と事実に修正。実物一致 | ○ |
| 7 | GAS toggleSort の表示を3画面でそろえる | 「一致しなければ ''」に統一。実物 :1679-1683 の if に else を足す形で成立（design は :1680-1683 と記載、1行ずれは許容） | ○ |
| 8 | ADR-1014:46 も置き換え | 改訂（6）文案に :46 と :55 を明記。実物 :46「既定のとき空表示にならないようにした」、:55「プルダウンの先頭は release_date:desc」で一致 | ○ |
| 9 | T2/T3 試験手順 | 4-3 に「unit_price:asc→""→最後の /inventory 呼び出し sort=release_date & order=desc、menu.value===""」、閲覧は captured.props で sortKey/sortDir。既存試験（tablelayout.test.tsx:51-69 の invCalls 抽出、InventoryView.test.tsx:51-59 の captured.props）の作法と合う | ○ |

## B. 第2版で新たに見つかった誤り・漏れ

B1.【本番配備の事前照合が必ず止まる】4-4 準備は「test_stage・prod_stage を写す。testpull は pull_v25 の写し。台本を写して G を新しい場所に」とあるが prodpull を写す記述がない。deploy_prod.sh は `diff -rq -x .clasp.json "$T" "$G/prodpull"` で照合するため、新しい G に prodpull が無ければ diff がエラーになり「本番が変わっています。中止」で止まる。さらに prodpull（13:30）が現在の本番 @17 の中身と一致するかは未確認（prod_stage と prodpull の index.html は異なるが、これは prod_stage が未配備の編集を含むためで想定どおり）。→「prodpull も写す（または本番 @17 を取り直して照合元にする）」を準備に追記すること。

B2.【GAS :938-939 の条件付き記述が残っている／書かれた本命どおりにすると壊れる】「初期値 :938-939 も sortCol=COL.releaseDate…（COL が後で定義されるなら 9 のまま…実装者は定義順を確認して報告）」。実物は `var COL = {` が :975 で、:938 より後に実行される。var は宣言だけ巻き上がり値は undefined なので、:938 で `COL.releaseDate` を読むとスクリプト全体が TypeError で止まる。定義順は確定しているので、条件文をやめて「:938 は `var sortCol = 9; // COL.releaseDate（COL は :975 で後から定義）`、:939 は 'desc'」と確定させること（または :938-939 は変えない。初期化 :1187-1189 の applySortValue で必ず上書きされ、それより前に render は呼ばれない）。

## C. 照合して問題なかった点（【事実】）
- アプリ: SORT_MENU_VALUES :58、既定 :127-128、resetAll :355-362、選択肢 :481-486（:482 が release_date:desc）、見出しクリック :612-614 すべて一致。InventoryPage に既定値の定数は無い（"release_date" は :127・:359 の直書き）＝ design の「定数が既にあれば」は実質「文字列を書く」（小1）。
- 閲覧: :197-216、onChange :203-209（:205 `if (!k) return;`）、:211 release_date:desc、見出しクリック :229-233、viewerFilter.ts:12-15 一致。
- i18n: releaseDesc のコード参照は InventoryPage.tsx:482・InventoryView.tsx:211 のみ。「発売日が新しい順」「Release date (newest first)」の frontend/src 内の出現は locales 4か所（削除対象）と viewerFilter.test.ts の試験名のみ＝ T1 の配信 JS 検査は成立する。
- backend inventory_offers.py:374-379 既定 release_date desc、変更不要。
- GAS: :840-845 select（現行先頭は value 9_desc「新しい順」）、:938-939 sortCol=-1/'asc'、:1023-1028 change、:1187-1189 初期化、:1396 `if (sortCol >= 0)`、:1670-1686 toggleSort、COL.releaseDate=9（:980 付近、COL 開始 :975）一致。test_stage と prod_stage の index.html は同一（差は .clasp.json と コード.js/Code.js の名前のみ）。applySortValue('') → 9/desc は現行初期化と同値。toggleSort の '' 設定は先頭 option value="" があるので成立。
- T4 の入力 ~/CC報告ファイル-keep/inventory-sort-cond-block/sheet.csv は実在。
- deploy_test.sh の期待版25、戻し先25（テスト）・17（本番）は deploy_test.log と deploy_prod.sh:3/:22 と整合。deploy_prod.log は無い＝本番は未配備で @17 のまま、の前提とも矛盾しない。

## D. 小さな指摘（任意・REVISE 理由ではない）
小1. 4-1 の「定数が既にあればそれを使う」は不要な条件。定数は無いので文字列 "release_date"/"desc" と確定してよい。
小2. 4-3 のアプリ既存試験名 'sort menu has 4 options and defaults to release_date:desc…' と閲覧 "sort pull-down has exactly 4 options" は名前も更新対象である旨を書くと実装がぶれない。

## 直すべき点（REVISE）
1. B1: 4-4 準備に prodpull の写し（または本番 @17 からの取り直し）を追加。
2. B2: GAS :938-939 を条件文でなく確定値で指定（COL は :975 で後から定義のため COL.releaseDate は使えない）。

いずれも1〜2行の追記で済む。指摘1〜9 は全て解消。

VERDICT: REVISE

---- review-design-v3.md ----
# 設計再審査（差分）: 並び替えプルダウン 見出し＋3択（design.md 第3版）

審査者: Reviewer（Opus）／2026-10-19／対象: 第2版審査（review-design-v2.md）の指摘 B1・B2 と任意2点の反映のみ
何も変更していない（読み取りのみ）。

## 照合結果（【事実】）
| 指摘 | 第3版の記述 | 実物照合 | 判定 |
|---|---|---|---|
| B1 prodpull の写し | design.md:69 「prodpull は ~/CC報告ファイル-keep/inventory-sort-cond-block/gas/prodpull の写し（pull_prod_1792391455 と diff 0、本番 @17）」 | `diff -rq -x .clasp.json pull_prod_1792391455 prodpull` → 出力なし rc=0。pull_prod_1792391455 は 15:30 作成で、.clasp.json・appsscript.json・Code.js・index.html がある | ○ |
| B2 :938-939 | design.md:83 「触らない。var COL は :975 で後から実行、初期化 :1187-1189 で上書き」 | test_stage/index.html:975 `var COL = {`、:938-939 sortCol=-1/'asc'、:1187-1189 初期化 と一致 | ○ |
| 小1 定数 | design.md:55 「:127 と :359 と同じ直書き。定数は無い」 | origin/main InventoryPage.tsx:127・:359 が "release_date" の直書き、DEFAULT_SORT 定数なし | ○ |
| 小2 試験名 | design.md:66 アプリ試験名の「4 options」を書き換えると明記 | 閲覧 InventoryView.test.tsx の試験名 "sort pull-down has exactly 4 options" には触れていない（design.md:67） | △ 任意。見出しも数えれば4つなので名前のままでも誤りではない |

## 新たな誤り
差分（:55・:66・:69・:83）に、行番号・コード・手順の誤りは見つからなかった。ほかの節は第2版から変わっておらず、第2版の審査で照合済み。

## 未確認
- 本番の公開版が @17 だという点は、design の記載（Opus が clasp deployments で確認）に頼っている。その出力ファイルは見ていない。ただし deploy_prod.sh:22 が実行時に @17 を照合して違えば止まるので、配備前に必ず検出される。

VERDICT: APPROVE
