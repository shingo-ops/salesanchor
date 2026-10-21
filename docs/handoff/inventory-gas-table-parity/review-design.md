# 設計審査: GAS 在庫一覧の表を閲覧ページと同じ形にする（design.md 第1版）

審査: Reviewer（Opus）／2026-10-19／読み取りのみ
対象: /tmp/CC報告ファイル/inventory-gas-table-parity/design.md
照合先:
- GAS 土台 G=~/CC報告ファイル-keep/inventory-sort-3choices/gas/test_stage/index.html（1727行。recon/gas-index.html と cmp 一致）
- 正本 origin/main（fetch 後 83948a58f）。design の基準 9c7bbb917 との差分は対象ファイル（viewer/・features/inventory/・DataTable.css・index.css・tokens.css・locales/viewer・tcg_distribution_svc.py）で 0 件（git diff --stat 出力が空）

判定: REVISE（必須4件・推奨6件）

---

## A. 必須（直さないと受入判定や実装が壊れる）

### A1. 提供者セルがスマホのカードで崩れる（3-7 提供者）
- 【事実】スマホでは td が2列グリッド: G:721-727 `td … { display: grid; grid-template-columns: calc(...) minmax(0, 1fr); }`、ラベルは G:740-741 `td::before { content: attr(data-label) }`（これもグリッドの1要素）。
- 【事実】design 3-7 の提供者セルは `<div>提供者</div><div class="inventory-cell__sub">…</div>` で、包む要素がない。td の子が ::before＋div＋div の3つになり、2つ目の div（時刻）は2行目の左列（ラベル幅の細い列）に置かれる。商品名は G:1569 `.title-cell` で1つに包んでいるので崩れない。
- 直し方: 2つの div を1つの要素（例 `<div class="supplier-cell">…</div>`）で包むと design に書く。T7 に「提供者の時刻が値の側（右列）に出る」を足す。

### A2. 受入 T4 の「badge」grep が必ず 0 にならない（7章 T4・5章）
- 【事実】`badge-` は消さないトークンにも含まれる: G:25 `--comp-badge-danger-solid`、G:26 `--comp-badge-radius`、G:464・G:476 `var(--comp-badge-radius)`、G:570 `var(--comp-badge-danger-solid)`。
- そのため `grep -c "badge-\|badgeCondition\|badgeStatus"` は変更後も 0 にならず、○×が決まらない。3-5 の「`grep -n "badge"` で他の参照が無い」も、filterCount（G:1123-1126）以外に上記トークンと G:475 のコメントが当たる。
- 直し方: 例 `grep -nE '\.badge|class="badge|badge-(sealed|damaged|case|stock|soldout|default)|badgeCondition|badgeStatus'` が 0 件、と書く。

### A3. 受入 T4 の `COL.postedAt` の期待値があいまい／G:1573 の分岐をどうするか書かれていない（3-7・T4）
- 【事実】今 `COL.postedAt` があるのは G:1361（24時間以内の絞り込み）、G:1532（colDefs）、G:1573（`col.idx === COL.postedAt` の分岐）。並び替えは `0_desc`（G:844）を `applySortValue`（G:1667-1672）が数字のまま読むだけで、`COL.postedAt` は書いていない。
- 変更後、提供者セルで `row[COL.postedAt]` を新しく使う（3-7）。それなのに T4 の「colDefs 以外（絞り込み・並び替え）だけ残る」は、並び替えには元から無く、提供者セルの新しい1件も入っていない。
- G:1573-1574 の分岐は列が無くなると通らない行になる。消すか残すかが 3-7 に無い。
- 直し方: 「G:1573-1574 は削除」と書き、T4 の期待を「`grep -n "COL.postedAt"` は 2 件（絞り込み G:1361 相当と提供者セルの1件）」のように件数と場所で書く。

### A4. テスト GAS の今の公開版が 26 だと言い切れない（冒頭・6章）
- 【事実】~/CC報告ファイル-keep/inventory-sort-3choices/gas/deploy_test.log では「Created version 26」「Redeployed [ID] @26」の直後に `clasp deployments` が `@HEAD` と `@25` を返している（ログの最後の2行）。
- design は「@26」を前提に、期待版 26 と testpull（＝test_stage の複写）を決めている。ログの最後の一覧が @25 なので、今の公開版は【未確認】。
- 違っていても deploy_test.sh の版の確認（`grep -qE "@26( |$)"`、既存 deploy_test.sh:21 と同じ形）で中止になるだけなので危なくはない。ただ、手順が成り立つかは決まらない。
- 直し方: 配備の前に今の公開版を確かめる手順（PO が ! で `clasp deployments` を実行し @26 を見る。または別窓で確認）を 6章に入れる。@25 だった場合の扱い（期待版を 25 にする／先に @26 の反映を確かめる）も書く。

---

## B. 推奨（閲覧ページとのずれ・行番号のずれ）

### B1. 商品名の日本語（上の段）の色が閲覧ページと違う（3-4）
- 【事実】閲覧の上の段は `.inventory-cell__title { font-weight: var(--font-weight-semi); overflow-wrap: anywhere; }`（inventoryColumns.css:1-4）で、色の指定がない。そのため td の `color: var(--text-secondary)`（DataTable.css:46-51 の :49）を受け継ぐ。viewer.css に td の色の上書きはない。
- design 3-4 は `.title-cell__ja { color: var(--text-primary); … }` で、色が違う（#1a202c と #4a5568）。
- 直し方: color を書かない（GAS の td も G:441 で `--text-secondary`）。

### B2. 単価・数量の見出しの寄せが閲覧ページと違う（3-2）
- 【事実】DataTable は th にも寄せのクラスを付ける: DataTable.tsx:53「th と td に comp-table__cell--align-* を付ける」、:230。閲覧の単価・数量は `align: "right"`（viewerColumns.tsx:79・:93）なので、見出しも右寄せ。
- design 3-2 は th をすべて左寄せにし、右寄せは td.num だけ。そのため GAS では単価・数量の見出しだけが左寄せになる。
- 直し方: numeric の列の th に右寄せのクラスを付ける（G:1547 のクラス組み立て）。

### B3. 行番号のずれ（Generator が行番号で探すと迷う）
- 3-4「:449-452」→ 実物は G:452-455（`.title-cell`／`__en`／`__ja`）。G:448-450 は寄せの上書き。
- 3-2「:407-415」→ th のかたまりは G:406-416（text-align は G:412）。td は G:436-443（text-align は G:440）。
- 閲覧側: stickyLeft は viewerColumns.tsx:34（design は :36）、ステータスのセルは :36-43（design は :37-44）、型番は :50（design は :51）、数量は :89-101（design は :92-101）、発売日は :132（design は :133）。OFFER_TYPE_TO_STATUS は tcg_distribution_svc.py:278（design は :277。:277 はコメント）。
- 合っている行: G:8、G:427-434、G:446、G:460-473、G:746-758、G:786、G:794、G:959-964、G:1123-1126、G:1531-1543、G:1547、G:1560、G:1564-1588、G:1696-1711。

### B4. 単価の「数字なら」の判定方法を正本と同じにする（3-7 単価）
- 【事実】正本は `if (unitPrice === "") return ""; const n = Number(unitPrice); return Number.isFinite(n) ? ¥… : ""`（viewerColumns.tsx:17-21）。今の GAS は `parseFloat`（G:1580）。"1200円" のような値では結果が違う（parseFloat は 1200、Number は NaN）。
- 【事実】元データの unit_price は `COALESCE(ROUND(price)::bigint::text, '')`（tcg_distribution_svc.py の _distribution_final_select）なので、実際の値では差は出ない。
- 直し方: 3-7 に「Number(val) と isFinite で判定」と書く。

### B5. 閲覧ページと違うまま残る点を書いておく（2章 対象外か 3-7）
- 数量: 閲覧は値をそのまま出す（viewerColumns.tsx:98 `{it.quantity}`）。GAS は `toLocaleString`（G:1581）で、1000 以上は「1,000」となって閲覧の「1000」と違う。design は「今のまま」でありながら閲覧と同じだと根拠を書いている。
- スマホのカードのラベル: 閲覧は `mobileLabel ?? header`（DataTable.tsx:326）で「単価」。GAS は `mobileLabel: '価格'`（G:1536）のまま。T7 も「価格」。
- 投稿日時が読めないとき: 閲覧の formatPostedAt は ""（viewerColumns.tsx:24-26）。GAS は元の文字列を返す（G:961）。design 3-7 は「同じ」と書いている。
- 合わせるか、対象外として理由を書くか、どちらかに決める。

### B6. G:475 のコメントに消したクラスの名前が残る
- 【事実】G:475「形と余白は .badge と同じトークン」。.badge を消すと、無いクラスを指すコメントになる。正本 inventoryColumns.css:51 は「金型 Badge sm と同じトークン」と書いている。同じ言い方に直す一文を 3-5 に足す。

---

## C. 確認できた点（問題なし）

- トークン4つの値は正本と同じ: `--warning-text: #744210`（index.css:55）、`--purple-text: #553c9a`（index.css:125）、`--offer-instock-text: var(--info-text)`（tokens.css:392）、`--offer-preorder-text: #b45309`（tokens.css:393）。GAS にはどれも無い（grep -c が 0）。参照先の `--info-text`（G:56）・`--success-text`（G:88）・`--danger-text`（G:35）・`--text-secondary`（G:91）は GAS にあり、値も正本と同じ。
- 列の順と見出し: viewer ja.json `col` = ステータス／型番／商品名／コンディション／単価／数量／備考／発送／提供者／発売日、`offerType` = 在庫／予約。3-6 と一致。mobileOrder 1-7 と mobileHidden（ステータス・型番・発売日）も viewerColumns.tsx と一致。
- ステータスの対応: 閲覧は offer_type が null なら `status || "-"`、pre_order なら予約、それ以外は在庫（viewerColumns.tsx:36-43）。offer_type は `_STATUS_TO_OFFER_TYPE.get(status or "")` の完全一致（tcg_distribution_svc.py:278-284）。3-7 の書き方と同じ結果になる。
- コンディションの色: conditionBadge.ts:16-37 の12値と5色、neutral はクラス定義なし（inventoryColumns.css:31-49 に neutral は無い）。3-5 と一致。
- 固定列と navy-trial: :794 に `th.col-sticky` を足すと、固定見出しも紺になる（G:433 相当の `th.col-sticky` と詳細度が同じで、後に書いた方が勝つ）。hover は G:799 `th.sortable:hover`（詳細度 0,2,1）が勝つので効く。スマホではステータス列が mobile-hidden（G:753）なので、固定の影響はない。
- 並び替え: 「投稿が新しい」は `0_desc`（G:844）→ applySortValue（G:1667-1672）→ 汎用の比べ方（G:1448-1466）で、colDefs に頼らない。列を消しても動く。
- 対象外の範囲（2章）ははっきりしている。prod の配備: prodpull は本番 @17（deploy_prod.sh:22 で期待値 17、本番配備のログなし）。sort-3choices の deploy_prod.sh を先に実行すると版が 18 になり、新しい台本は中止になる（安全側）。【推奨】旧 deploy_prod.sh は実行しないと 6章に一文入れる。
- testpull の作り方: 【事実】前回は、pull の結果（prepush_pull_test_1792394400/index.html）と testpull/index.html が cmp で一致した。コード.js と appsscript.json は test_stage と testpull で一致。【未確認】push した中身と、その後の clasp pull の中身が1バイトも違わないか。違っても中止になるだけで安全側（A4 と合わせて確認）。
