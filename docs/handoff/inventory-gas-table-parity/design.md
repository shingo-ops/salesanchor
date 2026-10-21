# 設計: GAS 在庫一覧の表を閲覧ページと同じ形にする（第2版：審査 REVISE の A1〜A4・B1〜B6 を反映）

作成: Opus（Planner）／2026-10-19／PO 承認: 2026-10-19「y」（GASの表を閲覧ページと同じ形にしてよいか）
基準: origin/main 9c7bbb917（recon: /tmp/CC報告ファイル/inventory-gas-table-parity/recon/）
GAS の土台: ~/CC報告ファイル-keep/inventory-sort-3choices/gas/test_stage/index.html（＝テスト GAS @26 に push した内容。deploy_test.log「Created version 26」「Redeployed … @26」）

## 1. 目的（PO の言葉）
「データテーブルの表示もsaアプリと同じに出来る？」→ GAS の表を、SA アプリの閲覧ページ（frontend/src/pages/viewer/viewerColumns.tsx）と同じ列順・同じ文字・同じ色にする。
閲覧ページは在庫表（frontend/src/features/inventory/inventoryColumns.tsx）と同じ金型・同じ色で、見出しの言葉だけお客様向け（viewerColumns.tsx:1-7 のコメント）。GAS もお客様向けなので閲覧ページに合わせる。

## 2. 対象と対象外
対象（GAS index.html のみ。SA アプリのコードは変えない）
- 列順・見出し・揃え・商品名の上下・ステータスとコンディションの文字色・単価の ¥・提供者の下に投稿日時・空の型番/発売日を「-」・左固定列をステータスへ

対象外（変えない）
- 並び替えの動き（toggleSort・applySortValue・compareRows・markBlockFlags）。商品名見出しを押したときの並び（英語名→日本語名）も今のまま
- 絞り込み・検索・シリーズタブ・自動縮小・スマホのカード表示の作り（並び順 mobileOrder は列の並べ替えに合わせて閲覧と同じ値を維持）
- 見出しの紺色（navy-trial ブロック index.html:789-）。PO が試作中の配色で、今回の依頼に含まれない
- 単価・数量の塗り（最安・在庫最多。#4526 で合わせ済み）
- GAS で出せないもの（シートに元データが無い）: 予約の補足（ship_timing）・「N行分」・行クリックの詳細・ダーク表示

## 3. 変更前→変更後（index.html。行番号は土台ファイル）

### 3-1. トークンの写し（:8-100 の :root）
正本にあって GAS に無い4つを、正本と同じ値で足す（ADR-067。独自の値を作らない）。
- `--warning-text: #744210;`（frontend/src/index.css:55）
- `--purple-text: #553c9a;`（frontend/src/index.css:125）
- `--offer-instock-text: var(--info-text);`（frontend/src/tokens.css:392）
- `--offer-preorder-text: #b45309;`（frontend/src/tokens.css:393）
:8 のコメントの正本コミットに「追加4つは origin/main 9c7bbb917」を書き足す。値は担当が `git show origin/main:frontend/src/index.css` / `tokens.css` で照合して報告する。

### 3-2. 見出し・セルの揃え（th :406-416, td :436-443）
- 変更前: `th { … text-align: center; … }` / `td { … text-align: center; … }`
- 変更後: 両方 `text-align: left;`（金型 DataTable.css:33 `.comp-table__th { text-align: left }`、td も既定は左）。数字列は今の `td.num`（右）のまま。
- 単価・数量の見出しは右寄せ（閲覧は align: right の列で見出しにも右寄せクラスを付ける DataTable.tsx:53・:230）。`th.align-right { text-align: right; }` を足し、renderTable の th で `col.align === 'right'` のときこのクラスを付ける。

### 3-3. 左固定列（:427-434, :446, :746-758, :786）
- 変更前: 固定は `th.col-title, td.col-title`（商品名）
- 変更後: PC の固定（position: sticky; left: 0 と背景・z-index、:428-434 と :446 の hover）を新しいクラス `col-sticky` に移し、ステータス列に付ける（閲覧の stickyLeft はステータス列 viewerColumns.tsx:36）。`col-title` は商品名のスマホカード見出しの見た目（:746-758）と :786 の nowrap 用に残す。:786 は `th.col-sticky, td.col-sticky` も同じ nowrap に含める。スマホではステータス列は mobile-hidden のため固定の影響なし。
- navy-trial の `th, th.col-title { background: var(--accent) }`（:794）は固定見出しの背景も紺にしている。`th.col-sticky` も同じ紺になるよう、:794 のセレクタに `th.col-sticky` を足す（紺色の範囲は変えず、固定列だけ白に戻らないようにするため）。

### 3-4. 商品名セル（:452-455）
- 変更前: 英語が上（--text-primary）、日本語が下（--text-muted / --font-xs）
- 変更後（閲覧 inventoryColumns.css:1-10 と同じ）:
  - `.title-cell__ja { font-weight: var(--font-weight-semi); }`（上。色は指定せず td の --text-secondary を受け継ぐ＝閲覧と同じ。DataTable.css:49）
  - `.title-cell__en { color: var(--text-secondary); font-size: var(--font-sm); }`（下）
- 描画（:1565-1572）は日本語を上、英語は値があるときだけ下。閲覧と同じく日本語が空でも上の段は出す（viewerColumns.tsx:59-63）。

### 3-5. 文字色クラス（:460-473 を置き換え）
- :475 のコメントの「.badge と同じトークン」は正本 inventoryColumns.css:51 と同じ言い方「金型 Badge sm と同じトークン」に直す。
- 削除: `.badge` と `.badge-sealed/-damaged/-case/-stock/-soldout/-default`（:460-473）。担当が `grep -n "badge" index.html` で他の参照が無いことを確認（filterCount の変数名 `badge` :1123-1126 は CSS クラスではない）。
- 追加（閲覧 inventoryColumns.css:22-50 と同じクラス名・同じトークン）:
```
.inventory-cell__offer--instock  { color: var(--offer-instock-text); }
.inventory-cell__offer--preorder { color: var(--offer-preorder-text); }
.inventory-cell__condition--info    { color: var(--info-text); }
.inventory-cell__condition--success { color: var(--success-text); }
.inventory-cell__condition--warning { color: var(--warning-text); }
.inventory-cell__condition--purple  { color: var(--purple-text); }
.inventory-cell__condition--danger  { color: var(--danger-text); }
.inventory-cell__sub { font-size: var(--font-sm); color: var(--text-secondary); }
.supplier-cell { display: flex; flex-direction: column; gap: var(--space-2px); text-align: left; }
```
- `.supplier-cell` は提供者と時刻を1つに包む入れ物（審査 A1。スマホの td は2列グリッド :721-727 で、包まないと時刻がラベル列に落ちる。商品名の `.title-cell` :452 と同じ作り）。
（neutral は色クラスなし＝td の既定色。閲覧も neutral 用のクラス定義は無い。）

### 3-6. 列定義（:1531-1543）
変更後（順・見出しは viewer-ja.json "col" と viewerColumns.tsx の順）:
```
{ label: 'ステータス',     idx: COL.status,        align: 'left',  numeric: false, sortable: true,  stickyCol: true, mobileHidden: true },
{ label: '型番',           idx: COL.mark,          align: 'left',  numeric: false, sortable: true,  mobileHidden: true },
{ label: '商品名',         idx: COL.englishTitle,  align: 'left',  numeric: false, sortable: true,  titleCol: true, mobileOrder: 1 },
{ label: 'コンディション', idx: COL.condition,     align: 'left',  numeric: false, sortable: true,  mobileOrder: 2 },
{ label: '単価',           idx: COL.unitPrice,     align: 'right', numeric: true,  sortable: true,  mobileOrder: 3 },
{ label: '数量',           idx: COL.quantity,      align: 'right', numeric: true,  sortable: true,  mobileOrder: 4 },
{ label: '備考',           idx: COL.noteJa,        align: 'left',  numeric: false, sortable: false, mobileOrder: 5 },
{ label: '発送',           idx: COL.shipJa,        align: 'left',  numeric: false, sortable: false, mobileOrder: 6 },
{ label: '提供者',         idx: COL.supplier,      align: 'left',  numeric: false, sortable: true,  mobileOrder: 7 },
{ label: '発売日',         idx: COL.releaseDate,   align: 'left',  numeric: false, sortable: true,  mobileHidden: true }
```
- スマホカードのラベルも「単価」にする（mobileLabel '価格' を削除。閲覧は見出しと同じ DataTable.tsx:326）。
- 投稿日時の列は無くなり、提供者の下の段に出す（閲覧 viewerColumns.tsx:116-126）。投稿日時の並びは並び替えの選択肢「投稿が新しい」から今まで通り使える（applySortValue は変えない）。
- 見出し `th` のクラス（:1547）: `col.stickyCol` なら `col-sticky` を足す。`col.titleCol` は今まで通り `col-title`。
- セル `td` のクラス（:1560）: `col.stickyCol` なら `col-sticky` を足す。`align === 'left'` なら `align-left`（今のまま）。

### 3-7. セルの中身（:1564-1588）
| 列 | 変更後 | 根拠（閲覧） |
|---|---|---|
| ステータス | 値が `'In Stock'` なら `<span class="inventory-cell__offer--instock">在庫</span>`、`'Pre-order'` なら `<span class="inventory-cell__offer--preorder">予約</span>`、それ以外は値そのもの（空なら `-`）を色なしで | viewerColumns.tsx:36-43。対応は backend OFFER_TYPE_TO_STATUS（tcg_distribution_svc.py:277、完全一致）と同じ |
| 型番 | 値、空なら `-` | viewerColumns.tsx:51 |
| 商品名 | 3-4 | viewerColumns.tsx:56-64 |
| コンディション | `conditionClass(val)` で `inventory-cell__condition--{info/success/warning/purple/danger}` を付けた span。neutral はクラスなし | conditionBadge.ts:16-37（trim・小文字・完全一致。値の表をそのまま写す） |
| 単価 | 空文字なら空。それ以外は `var n = Number(val)` で `isFinite(n)` なら `'¥' + n.toLocaleString('ja-JP')`、でなければ空（parseFloat は使わない）。塗りの span（cell-value）は今のまま | viewerColumns.tsx formatPrice（:17-21 付近） |
| 数量 | 値をそのまま（3桁区切りしない。閲覧と同じ）。塗りの span は今のまま | viewerColumns.tsx quantity 列（:98 付近） |
| 備考・発送 | 今のまま（値そのもの） | |
| 提供者 | `<div class="supplier-cell"><span>提供者</span><span class="inventory-cell__sub">formatPostedAt(投稿日時)</span></div>`。時刻が空なら下の span は出さない | viewerColumns.tsx supplier 列（:116-126 付近）。形 MM-DD HH:mm は GAS formatPostedAt :959-964 と同じ |
| 発売日 | 値、空なら `-` | viewerColumns.tsx:133 |

- `badgeCondition`・`badgeStatus`（:1696-1711）は削除し、`conditionClass(val)` と `offerCell(val)` を同じ場所に置く。コメントに「正本: frontend/src/features/inventory/conditionBadge.ts（ADR-1023）。値が増減したら正本と同時に直す」と書く。
- 文字列はすべて今の `escHtml` を通す。
- 投稿日時の分岐（:1573-1574 `else if (col.idx === COL.postedAt)`）は削除する（列が無くなるため）。
- `formatPostedAt`（:959-964）は読めないとき元の文字列ではなく空文字を返すように変える（閲覧 formatPostedAt と同じ）。呼び出しは :1574 だけ（審査で確認）で、変更後は提供者セルだけになる。

## 4. 代替案
- A（採用）: 閲覧ページに合わせる。お客様向けの見出し、同じ色・同じ順。
- B: 在庫表（社内）に合わせる。見出しがタイトル/状態/仕入元になり、お客様向けの GAS では言葉が社内向けになる → 不採用。
- C: 色だけ合わせる → PO の「表示も同じに」に足りない → 不採用。

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| 色の割り当てが正本とずれる | conditionClass は conditionBadge.ts と同じ並び・同じ値で写し、担当が両方を並べて報告。審査で照合 |
| 固定列を変えて見出しの紺が欠ける | 3-3 の :794 セレクタ追加。T6 で目視 |
| 古いクラス（badge）の取り残し | 削除後 `grep -n "badge-\|badgeCondition\|badgeStatus"` が0件 |
| スマホ表示が崩れる | mobileOrder・mobileHidden は閲覧と同じ値。T7 で目視 |
| テスト配備で事前照合が止まる | 6章のとおり新フォルダで testpull を今の @26 の内容から作る |

## 6. 作業場所と配備
- 新フォルダ G2=~/CC報告ファイル-keep/inventory-gas-table-parity/gas/
  - test_stage/ ← ~/CC報告ファイル-keep/inventory-sort-3choices/gas/test_stage/ を丸ごと複写し、ここを編集
  - testpull/ ← 同じ test_stage（＝テスト @26 に push 済みの内容）を編集前に複写（照合の基準）
  - prod_stage/ ← 編集後の test_stage の index.html・コード.js・appsscript.json と、本番の .clasp.json（sort-3choices/gas/prod_stage/.clasp.json）
  - prodpull/ ← sort-3choices/gas/prodpull を複写（本番 @17 の内容）
- 事前確認（実施済み 2026-10-19、Opus の読み取り clasp）: テストの公開版 @26・本番 @17（/tmp/CC報告ファイル/inventory-gas-table-parity/test_deployments.txt・prod_deployments.txt）。今のテスト・本番の中身を pull して照合し、テスト＝sort-3choices/gas/test_stage、本番＝sort-3choices/gas/prodpull と差0（SAME_TEST・SAME_PROD）。deploy_test.log で @25 と出たのは redeploy 直後の表示で、今は @26。
- 前回の sort-3choices/gas/deploy_prod.sh は実行しない（実行すると本番が 18 になり新しい台本が中止する）。本番へは新しい deploy_prod.sh で一度に出す。
- deploy_test.sh: 期待版 26、版メモ「表を閲覧ページと同じ形に(ADR-1014改訂10-19(7))」、戻し方「版26へ redeploy」。PO が ! で実行。
- deploy_prod.sh: 期待版 17、版メモ「並び順＋塗り＋状態のまとまり固定＋並び替え3択＋表を閲覧ページと同じ形に(ADR-1014改訂10-19)」、戻し方「版17へ redeploy」。テストの PO 目視○の後、PO 承認を得て PO が ! で実行。
- 担当（Sonnet）は clasp を一切実行しない。

## 7. 受入条件
| 基準 | 検証方法 |
|---|---|
| T0 見た目以外の数 | node 台本で: 単価 '1200'→¥1,200、'abc'→空、''→空／数量 '1200'→'1200'／formatPostedAt('x')→'' |
| T1 構文 | index.html の `<script>` 部分を取り出して `node --check` が成功 |
| T2 列順・見出し | 描画を node で試す小さな台本（renderTable に既知の3行を渡して thead の文字を並べる）で「ステータス,型番,商品名,コンディション,単価,数量,備考,発送,提供者,発売日」と一致 |
| T3 セル | 同じ台本で: In Stock→「在庫」+instock クラス／Pre-order→「予約」+preorder クラス／Sold out→「Sold out」色なし／Case→success、damaged case→warning、no shrink box→purple、searched pack→danger、Bulk→クラスなし／型番・発売日 空→「-」／提供者セルが supplier-cell で包まれ MM-DD HH:mm の下段／単価・数量の th に align-right |
| T4 取り残し0 | `grep -nE '\.badge\b|badge-(sealed|damaged|case|stock|soldout|default)|badgeCondition|badgeStatus' index.html` が0件（`--comp-badge-*` は対象外）。`grep -n 'COL.postedAt' index.html` が2件だけ: 絞り込み（変更前 :1361）と提供者セル |
| T5 トークン | 足した4値が origin/main の index.css / tokens.css と一致（担当が git show 出力を添える） |
| T6 PO 目視（PC） | テスト GAS で: 左端がステータスで横に送っても残る／在庫=青・予約=橙の文字／商品名は日本語が上で太字／コンディションが文字色（Case=緑 など）／単価に¥／提供者の下に時刻／見出しは紺のまま |
| T7 PO 目視（スマホ） | カードの並びが 商品名→コンディション→単価→数量→備考→発送→提供者、提供者の行で名前の下に時刻が出る（ラベル側に落ちない） |
| T8 差分の範囲 | test_stage と testpull の diff が index.html だけ、変更箇所は 3章の範囲だけ |

## 8. 維持の仕組み
守り手: 人手で守る（GAS はリポジトリ外のため CI の関所を置けない。ADR-1014 改訂（7）に正本と写しの場所を明記し、正本を変える便で GAS の写しも直す）
- ADR-1014 に改訂（7）として「GAS の表は閲覧ページと同じ列順・見出し・色。正本は viewerColumns.tsx・conditionBadge.ts・inventoryColumns.css。変えるときは GAS の写しも同じ便で直す」と書く（docs PR）。
- GAS の写しの場所（~/CC報告ファイル-keep/inventory-gas-table-parity/gas/）を ADR-1014 に書く。

## 9. 外部・過去事例の参照と我々への応用
不要。社内の既存画面（閲覧ページ）に写すだけで、新しい方式を選ぶ判断が無いため。
