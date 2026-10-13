# design: 確認スライドの比較表を「1つの表・同じ行」にする（review-compare-table）

状態: 設計案（Opus 2026-10-14）。PO 決定「y」（2026-10-14）＝「項目名を左に1回だけ置き、Gemini｜システムを1つの表の同じ行に並べる」。
recon: docs/handoff/review-compare-table/recon.md（基準 origin/main d39e25183）。
お手本: PO 共有2枚（料金プラン3列・スクール比較表）から取り出した基準 = ~/CC報告ファイル-keep/design-references/po-samples/rules-from-po-samples.md（repo 外）。
前作業: docs/handoff/review-drawer-one-line/design.md（#4234。3列化と Drawer wide）。

## 1. 目的（PO の言葉）
「比較する項目が水平に揃っていると見やすい」。今は Gemini 列とシステム列が別々の格子で、行の高さが違い区切り線がずれる。
作品・商品ID・販売状況はシステム側だけにあり、補足「Gemini抽出値を採用」と「L1-9」が折れる（recon.md:14-15, :47-50, :115）。

## 2. KGI（○×で判定。Storybook で Playwright により実測）
| # | 基準 | 検証方法 |
|---|---|---|
| A | 比較の全10行で、Gemini セルとシステムセルの上端 y の差が 0px | 各 `tr` の `td` の getBoundingClientRect().top を比べる |
| B | 行は10行で、順番は 商品名・数量・単価・単位・状態・メモ・原文位置・作品・商品ID・販売状況。値が無い側のセルは「—」 | DOM の行の文字を読む・単体試験 |
| C | すべてのセル（ラベル・値・採用元・L1-9 ボタン）で折り返しが 0 回 | 各セルの内側の span の getClientRects().length ≤ 1、かつ tr の高さ ≤ `--comp-table-row-h-compact`＋1px（罫線 1px の分） |
| D | 10行の高さがすべて同じ（差 0px） | tr の高さの最大と最小の差 |
| E | A〜D を、スライドの 1440px（Drawer wide 1100px）と比較表単体の幅 640px・960px（仕入先詳細を想定）で満たす。1024px（縦積み）でも満たす。4条件とも表の横スクロールなし（.comp-table の scrollWidth = clientWidth） | Storybook 4条件 |
| F | 表示中のバッジの一覧（文言と順）は変更前と同じ | 単体試験 |
| G | 文字は全部 t() 経由で、ja/en のキー数は同じ。色や px の直書きは 0 | grep・既存 CI |

## 3. 対象と対象外
対象（readOnly=true の描画だけ）:
- frontend/src/features/tcg-analysis-review/ItemComparison.tsx の `readOnly` の分岐
- item-comparison-readonly.css
- 新しい ItemComparison.stories.tsx と ItemComparison.test.tsx
- ja/en（必要なキーだけ）

対象外:
- readOnly=false の分岐（呼び出し0件・recon.md:84）。変えない。
- バッジの「要確認」が重なる件（reviewIssues.ts:6 と :16 が同じ文言キー。recon.md:72）。意味の変更になり他の画面に効くので別件にする。今回は表示を変えない。
- バックエンド・API・DB。
- 下段の「直す」と原文ペイン。

## 4. 変更前 → 変更後
変更前（ItemComparison.tsx:36、readOnly 部分）:
- 見出し行 `item-head-grid` → `aligned-fields`（項目ごとに Gemini div とシステム div。ラベル b を2回出す）→ `item-extra-grid`（左に原文位置、右に作品・商品ID・販売状況）。
- 3つの格子が別々で、行の高さが中身ごとに決まる。

変更後（readOnly=true のとき。`readOnly ? <ReadOnlyComparison .../> : 既存の JSX そのまま` で分ける）:
```
<article className="item-comparison item-comparison--readonly">
  <div className="item-comparison__badges">           // 見出し「システム判定」は付けない。既存の issueBadges をそのまま並べる（0件なら div を出さない）
    {issueBadges.map(b => <StatusBadge .../>)}
  </div>
  <DataTable                                           // 既存の金型（components/DataTable.tsx）。新しい金型は作らない
    columns={[                                         // ellipsis prop は使わない（理由: 改訂1-1）。4列とも renderCell で <ComparisonCell> を返す
      { key:'label',  header:t('tcgAnalysisReview.compareColumns.field'),  width:'var(--comparison-label-col-w)',  renderCell },
      { key:'gemini', header:t('tcgAnalysisReview.geminiExtraction'),                                              renderCell },
      { key:'system', header:t('tcgAnalysisReview.systemFinalResult'),                                             renderCell },
      { key:'source', header:t('tcgAnalysisReview.compareColumns.source'), width:'var(--comparison-source-col-w)', renderCell },
    ]}
    data={rows} rowKey={r => r.key} density="compact" className="item-comparison__table" />
</article>
```
行 `rows`（10行。純粋な関数 `buildComparisonRows(item, t)` にして単体試験する）:
| key | label | gemini | system | source（採用元） |
|---|---|---|---|---|
| name/quantity/price | 既存の fieldLabels | `item.gemini[k] \|\| 未解決` | `FinalSystemValue` と同じ値 | `FinalSystemValue` と同じ補足（Gemini抽出値を採用／未解決） |
| unit | 同上 | `item.gemini.unit \|\| 未解決` | `system.unit \|\| 未解決` | System確定／未解決（既存と同じ条件） |
| state | 同上 | `item.gemini.state \|\| 未解決` | `system.condition \|\| 未解決` | System確定／未解決 |
| memo | 同上 | `item.gemini.memo \|\| 未解決` | `system.note \|\| なし` | note があれば System確定、無ければ「—」 |
| sourcePosition | tcgAnalysisReview.sourcePosition | 行番号が取れれば既存の `<button className="line-jump">{span}</button>`（onJumpToSourceLine を呼ぶ）、取れなければ span、空なら 未解決 | — | — |
| work | superAdmin.supplierQuality.workName | — | `system.work_name \|\| 未解決` | — |
| productId | tcgAnalysisReview.productId | — | `system.product_id \|\| 未解決` ＋ productIssueBadges | — |
| saleStatus | tcgAnalysisReview.saleStatus | — | `system.status \|\| 未解決` | — |

- 値の条件は既存の `FinalSystemValue`（:28）と `ComparisonMetadataRow` の呼び方（:36）を写す。条件は変えない（SSOT は既存の関数。新しい判定を足さない）。補足の文字列を返す小さな関数に分け、`FinalSystemValue` から使っている場合はそれも使う形にしてよい（判定を二重に持たない）。
- 「—」は値が「その側に存在しない」ことを表す。「未解決」は「存在するが決まっていない」ことを表すので、意味を混ぜない。
- 商品ID の行のバッジは、値の後ろの同じ行に置く（ellipsis のセル内で横並び。折れない）。
- 採用元の列の文字は `--text-secondary` と `--font-2xs`（既存の small と同じトークン）にする。値の列は既存の本文の色にする。強弱はこの2段だけ（お手本の基準3）。

## 5. 新しいトークンと i18n
- `--comparison-source-col-w`: 採用元の列の幅。tokens.css の `--comparison-label-col-w`（:450）の隣に置く。値は既存の幅トークンを参照すること（例 `var(--col-width-medium)` など。実装者が tokens.css から実在するものを選び、その名前と px を報告する）。直書きの px を新しく作らない。幅が足りず「Gemini抽出値を採用」が省略される場合は、それも報告する（C は title で全文が読めれば省略記号は可。折り返しは不可）。
- i18n: `tcgAnalysisReview.compareColumns.field`（ja「項目」/ en「Field」）、`tcgAnalysisReview.compareColumns.source`（ja「採用元」/ en「Source」）、`tcgAnalysisReview.notApplicable`（ja「—」/ en「—」）。既存に同じ意味のキーがあれば、それを使い報告する。

## 6. CSS
- item-comparison-readonly.css から、readOnly でだけ使っていた格子のセレクタを削る:
  - `.item-head-grid`, `.aligned-fields`, `.item-extra-grid`, `.comparison-field`, `.comparison-extra`, `.system-extra`, `.comparison-metadata-row*`, `.inline-badges`（readOnly の分) 
  - 削る前に `grep -rn` で他の参照が0件であることを確かめ、結果を報告する。
  - readOnly=false 側がこのファイルに頼っていない（`.item-comparison--readonly` の付いたセレクタだけ）ことも確かめる。頼っていたら削らずに止まって報告する。
- 追加: `.item-comparison__badges`（flex・gap `--space-1`・下の余白 `--space-2`）。
- 追加: `.item-comparison__table` の中の採用元の列の文字色と大きさ（クラスは renderCell 側で付ける）。
- 表の線・行の高さ・余白は DataTable の金型のまま。上書きしない。
- `.review-item-source h3` のルール（:39-44）は原文ペインの見出しで使うので残す。

## 7. 影響範囲
- 呼び出し元は2か所（recon.md:79-85）:
  - ReviewItemDrawer.tsx:73
  - SupplierDetailView.tsx:116。仕入先詳細も同じ表になる。行番号ボタンでの移動はそこで実際に動くので、ボタンは残す。
- ReviewItemDrawer.test.tsx は ItemComparison をモックしているので、影響はない（recon.md:126）。
- DataTable の金型そのものは変えない。

## 8. 代替案
- (a) 既存の格子を1つにまとめ、CSS の grid で行をそろえる。金型を使わず、独自の表をもう1つ作ることになるので、ADR-144 の考え方に反する。却下。
- (b) DataTable を使う（採用）。
  - 行は tr なので、上端と高さがそろうことが構造で保証される（A・D）。
  - ellipsis の列で折り返さない（C。#4234 で導入済みの金型の機能）。
- (c) 採用元を値の下に小さく置く（今の形）。行の高さが中身で変わり D を壊す。却下。採用元は別の列にする。

## 9. リスクと対処
- 列が狭いと値が省略される。title で全文が見える（ellipsis の既存の機能）。E の4条件で、省略されたセルの数を記録して報告する。
- 仕入先詳細の幅が狭い。DataTable の外枠は横スクロールする（min-width 480px・recon.md:89）。640px で実測する。
- 戻し方: PR を revert すれば元に戻る。DB・API の変更はない。

## 10. 受入の検証（実装者がやること）
1. `npx vitest run src/features/tcg-analysis-review` が全件合格すること。新しい試験:
   - buildComparisonRows が10行・順番・「—」の位置を返す
   - 補足の条件の4通り
   - line-jump を押すと onJumpToSourceLine(行番号) が呼ばれる
   - バッジの一覧が変わらない（F）
2. 新しい ItemComparison.stories.tsx を作り、次の story を用意する:
   - 長い商品名
   - 値が空（未解決）
   - メモなし
   - 商品マスタ未登録のバッジあり
   - 幅 640 と 960 の入れ物
3. Playwright で A〜E を実測し、表（条件ごとに A〜E の OK/NG と数値）にする。
   - 生出力: ~/CC報告ファイル-keep/review-page-20261013/compare-table-measure.txt
   - スクショ: 同じ場所に 1440 と 640 の2枚
4. frontend の lint・typecheck・i18n キーの検査を実行する。
5. NG があれば直して測り直す。2回直しても NG なら止まって報告する。

## 11. 維持の仕組み
- 単体試験 ItemComparison.test.tsx（B・F）。story を Storybook カタログに載せる（見た目の後退を目で見つけられる）。

## 12. 外部事例（調査 /tmp/CC報告ファイル/design-sense-research-20261014.md）
- 測れる基準（チェックリスト）を作り、描画した画面で審査する方法: 見た目の評価が向上した（S1: 3.0→3.9、S4: 79%→91%）。今回は A〜E を測れる基準にした。
- 汎用の AI に美しさを判定させる方法は弱い（F2: r=0.21）。そのため判定は数値の基準だけで行う。
- 適用の限界: 事例は新規サイトの生成で、既存のデザインシステムの1部品の修正ではない。

## 13. 審査
- 設計審査: Fable（下に追記）

## 改訂1（Fable 設計審査 REVISE 2026-10-14 への対応。上の本文とこの節が違うときはこの節が正）

1. 値の列の幅（Fable の NEEDS_DECISION）。設計者の判断で (i) を選ぶ: 幅に追従させ、横スクロールなし、はみ出しは省略。
   - 理由: (ii) は 1100px のスライドでも横スクロールになる。(iii) は 700px の表で値が 200px で切れ、今より読めなくなる。
   - DataTable の ellipsis prop は、div の max-width に width を直接入れる（DataTable.tsx:290）。割合や未指定だと 200px 固定になる。そのため使わない。
   - 4列とも renderCell で、同じファイル内の小さな部品 `ComparisonCell` を返す:
     `<span className="item-comparison__cell" title={text}>{node ?? text}</span>`
   - CSS（feature 側の自分のクラスだけ。td・th のセレクタは書かない＝金型を上書きしない）:
     `.item-comparison__cell { display:block; width:0; min-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }`
     - span の最小内容幅が 0 になるので、列の幅は th の width と表の幅で決まる。値の2列が残りの幅を分け合う。
   - 実装者はこの方式で E の4条件を実測する。どれかで「横スクロールあり」か「省略されず列が広がる」になったら止まって報告する。td の上書きや DataTable の改変で回り道しない。金型の拡張（例: table-layout fixed の prop）は PO の許可が要るので、設計者が判断する。
2. title: 行データは `{ text: string; node?: ReactNode }` にし、title は必ず text から付ける（button・バッジ入りのセルも同じ）。
3. 採用元の列の幅: 新しいトークン `--comparison-source-col-w: 112px;` を tokens.css の `--comparison-label-col-w`（:450）の次の行に置く。§5 の「直書き px を作らない」は撤回する。
   - 根拠: 「Gemini抽出値を採用」は `--font-2xs` で約101px。100〜140px の既存の列幅トークンは無い（tokens.css:438-441）。
   - 新しいトークンなので、PR 本文の「デザイントークン変更時」チェックリストに理由を書く（frontend/scripts/check-new-tokens.js）。
4. CSS の削除の範囲（§6 を置き換え）:
   - 削る: item-comparison-readonly.css の `.item-comparison--readonly` が付いたセレクタのうち :6-12, :46-51, :53, :56-64, :66-70, :72-78, :81, :83-87, :89 と、:39-44 の中の `.item-comparison--readonly .item-head-grid h3` の部分（`.review-item-source h3` は残す）。
   - 残す: :15-32 の `.comparison-metadata-row*`（スコープされておらず、readOnly=false の分岐でも使う）。:3 の `.item-comparison--readonly { padding }` も残す。
   - 削った後に、各セレクタの名前を grep して他の参照が0件であることを報告する（Fable の審査では、frontend/src・e2e・.storybook で0件を確認済み）。
5. 行ごとの「未解決」のキーは今のものを変えない:
   - 商品名〜メモと原文位置は `tcgAnalysisReview.unresolved`
   - 作品・商品ID・販売状況は `common.unresolved`
   - メモが無いときの採用元は、今の「補足なし」から「—」に変える（意図した変更。F の対象外）。
6. 関数の分け方:
   - `systemCell(item, key, t) → { value: string; source: string | null }` を ItemComparison.tsx に切り出す。既存の FinalSystemValue はこれを呼ぶ形にする（判定を1か所に）。
   - `buildComparisonRows(item, t)` は純データだけを返す（原文位置の行は `line?: number` と span の文字列を持つ）。button と バッジは ItemComparison の中の renderCell で作る（onJumpToSourceLine と productIssueBadges を使う）。
   - 新しい部品は ItemComparison.tsx 内に関数として置く（新ファイルは作らない。試験は buildComparisonRows と systemCell を export して行う）。
7. story: `frontend/src/features/tcg-analysis-review/ItemComparison.stories.tsx`（title 'Features/ItemComparison'）を作る。
   - 入れ物の幅は story の decorator で 640・960 の div にする。幅の値は stories だけで使う既存の書き方に合わせ、直書きの検査に引っかかるなら tokens を使う。
   - 1440 と 1024 は、既存の ReviewItemDrawer.stories.tsx を viewport を変えて測る。
   - バッジ0件の story も作る（F の試験にも0件のケースを入れる）。

## 改訂2（Fable 再審査 REVISE 2026-10-14 への対応。改訂1と食い違うときはこの節が正）

1. ラベル列と採用元列の幅（前提: `* { box-sizing: border-box }` は index.css:419-423、セルの左右 padding 16px は DataTable.css:32, :48）。
   - この2列のセルは ComparisonCell（width:0 の省略）を使わない。同じファイル内の `<span className="item-comparison__fixed" title={text}>{node ?? text}</span>` を返す。
   - CSS は `.item-comparison__fixed { white-space: nowrap; }` だけにする。文字は省略も折り返しもされず、列は文字の幅まで自動で広がる。指定した幅は下限として働く。
   - th の width は内容幅に padding を足す:
     - ラベル列: `calc(var(--comparison-label-col-w) + 2 * var(--comp-table-cell-px))`
     - 採用元列: `calc(var(--comparison-source-col-w) + 2 * var(--comp-table-cell-px))`
     - `--comparison-label-col-w`（72px）の値は変えない。:17 の残置ルールが参照しているため。
   - 新しいトークン `--comparison-source-col-w: 112px;` は内容幅（「Gemini抽出値を採用」約104px より大きい）として残す。
   - 値の2列（gemini・system）だけが ComparisonCell による省略の対象になる。
2. 値の2列は等分にならない（見出しの文字幅の比で余りが配られる。約 98:128）。これは許容し、NG にしない。
3. 行の型 `ComparisonRow` には node を持たせない（text・line? などの純データだけ）。node は renderCell の中で作り、ComparisonCell と fixed の span の props としてだけ渡す。
4. KGI C の折り返しの判定は、tr の高さ ≤ `--comp-table-row-h-compact`＋1px で行う（display:block の span の getClientRects は判定に使わない）。ラベル列と採用元列では、加えて span の scrollWidth ≤ clientWidth（省略されていない）を確かめる。
