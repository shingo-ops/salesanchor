# design: 最安・在庫最多をバッジから色の枠に変え、比べる単位にステータスと状態を足す

recon: docs/handoff/inventory-block-frames/recon.md
関連 ADR: ADR-1014（改訂（3）を足す）・ADR-067（トークン）・ADR-144（UI 金型）・ADR-027（i18n）・ADR-1015（区分）
前の便: #4521（docs/handoff/inventory-block-badges/design.md）。今回の土台は origin/main 1df98028b。

## 目的（PO の言葉）
- PO（2026-10-19）「バッジだと見づらいから最安値の価格を水色の枠で囲む、在庫最多の在庫数を緑色の枠で囲むように出来る？列がズレて見づらいので、またステータスや状態違いは判別してそれぞれで囲いを作ってほしいが理解できるか？」
- Opus の確認文（2026-10-19）「バッジをやめ、最安の価格を水色の枠、在庫最多の数量を緑の枠で囲みます。比べる単位は『同じ商品・同じステータス・同じ状態』ごとにします。枠は列の幅を変えない作りにして、列がずれないようにします。」→ PO「y」（設計・審査・実装を進め、アプリの在庫表と閲覧ページの本番反映まで行う。GAS 在庫一覧は別便）。

## 区分
A（ADR-1015）。GO は POの委任に基づく Claude Opus 発行（ADR-1003）。DB・migrations・deploy.yml・scripts・nginx は触らない。API の項目名（`badge_cheapest`・`badge_most_stock`）は変えない（意味の説明文だけ変える）。

## 変更前 → 変更後

| 項目 | 変更前（#4521） | 変更後 |
|---|---|---|
| 比べる単位（在庫表） | `PARTITION BY d.product_id`（backend/app/routers/inventory_offers.py:306-316 の8か所） | `PARTITION BY d.product_id, d.status, d.condition`（同じ8か所） |
| 比べる単位（閲覧ページ） | キー `release_date \0 english_title \0 japanese_title`（frontend/src/pages/viewer/viewerFilter.ts:237） | キー `release_date \0 english_title \0 japanese_title \0 status \0 condition` |
| 見た目 | 値の右隣に金型 Badge「最安」（success 緑）「在庫最多」（info 水色）。文字の分だけセルが広がり、右寄せの値が左へずれる | Badge を出さない。最安は価格の値を水色の枠、在庫最多は数量の値を緑の枠で囲む。枠の有無でセルの幅は変わらない |
| 意味の伝え方 | Badge の文字 | 枠の付いた値に `title`（マウスを乗せると「最安」「在庫最多」）。既存の辞書キー `inventory.badge.*`・`viewer.badge.*` をそのまま使う（キーの追加・削除なし） |

他の規則（空の値は外す、値のある行が1行以下・全部同じ値なら付けない、同じ値は全部に付ける、整数に丸めて比べる、絞り込み後・ページ前で比べる、まとめモードは画面の値）は #4521 から変えない。

ステータスと状態の意味:
- ステータス = 行の `status`（在庫表 SQL の `d.status` は `COALESCE(ar.status,'')`、backend/app/services/tcg_distribution_svc.py:329。閲覧ページは `ViewerRow.status`、frontend/src/pages/viewer/types.ts:19）。在庫・予約で別のまとまりになる。値が空の行どうしは1つのまとまり。
- 状態 = 行の `condition`（在庫表 SQL の `d.condition` は `cr.canonical`、tcg_distribution_svc.py:325。窓に入る行では NULL にならない（同 :236-238 の cond_filter で落ちる）。閲覧ページは `ViewerRow.condition`、types.ts:15）。画面の「状態」列（Sealed box・Case など）に出る値と同じ。
- 在庫表と閲覧ページは同じ2つの値を使うので、両者の結果は #4521 の既知の差（商品の決め方）以外では同じ。

## 列がずれない作り
原因（事実）: 値の右隣に Badge の文字を置いたため、その行だけ値の中身が広がる。価格・数量の列は右寄せ（inventoryColumns.tsx:129・:145、viewerColumns.tsx:79・:92）なので、Badge のある行だけ値の位置が左へずれる。

変更後:
- 価格と数量の値は、枠の有無にかかわらず全部の行で同じ入れ物 `<span class="inventory-cell__value">` に入れる。入れ物は全行で同じ余白を持つ。枠は `box-shadow: inset`（内側に描く影）で描くので、幅も高さも変わらない（前例 frontend/src/pages/schedule.css:89 `box-shadow: inset 0 0 0 1px var(--accent)`）。
- 結果として、枠のある行とない行で値の右端の位置が同じになる。

CSS（frontend/src/features/inventory/inventoryColumns.css。既存の `.inventory-cell__badge`（:51-54）は消す）:
```css
/* 価格・数量の値の入れ物。枠の有無で幅を変えないため、全行で同じ余白を持つ（ADR-1014 改訂 2026-10-19（3）） */
.inventory-cell__value {
  display: inline-block;
  padding: var(--space-1px) var(--space-1);
  border-radius: var(--radius-sm);
}
/* 同じ商品・ステータス・状態のまとまりの最安（水色）と在庫最多（緑）。内側の影で描き、幅を変えない */
.inventory-cell__value--cheapest {
  box-shadow: inset 0 0 0 var(--space-2px) var(--comp-value-frame-cheapest);
}
.inventory-cell__value--most-stock {
  box-shadow: inset 0 0 0 var(--space-2px) var(--comp-value-frame-most-stock);
}
```

色のトークン（frontend/src/tokens.css に2つ足す。金型への登録で、直書きではない）:
- 事実: 水色（sky・cyan）のトークンは無い（recon §6）。既存の `--info` は #2563eb（青）、`--info-bg` は #bee3f8（白地で 2px の線には薄すぎる）。在庫の文字色 `--offer-instock-text` は `--info-text` の青なので、枠も青にすると「在庫」の青と見分けにくい。
- そこで水色のトークンを足す。緑は既存の `--success` を指す別名にする（緑の値を2か所に持たない）。
- 置き場所は在庫表の文字色 `--offer-*-text` の前例（tokens.css:391-393 ライト、:587-589 ダーク。ADR-067 の「tokens.css — グラフ系列」表と同じく tokens.css に置く色の前例）に並べる。ライト・ダークの両方に2つとも書く:
  - tokens.css:393 の直後（ライト）:
    ```css
      /* ---- 在庫表・閲覧ページの最安（水色）・在庫最多（緑）の枠（ADR-1014 改訂 2026-10-19（3）） ---- */
      --comp-value-frame-cheapest:   #0ea5e9;  /* sky-500: 白地 2.8:1。PO 指定の「水色」。意味は title でも伝える */
      --comp-value-frame-most-stock: var(--success);
    ```
  - tokens.css:589 の直後（ダーク）:
    ```css
      /* 最安・在庫最多の枠（ダーク） */
      --comp-value-frame-cheapest:   #38bdf8;  /* sky-400 */
      --comp-value-frame-most-stock: var(--success);
    ```
- 水色の値の理由: 白地で 3:1（文字以外の目安、WCAG 1.4.11）に届く #0284c7（sky-600）は青に近く、在庫の文字色（青）と見分けにくくなり、PO の「水色」から離れる。#0ea5e9 は 2.8:1 で目安にわずかに届かないが、枠は飾りで、意味は `title` でも伝え、値の文字そのものの読みやすさ（文字色は変えない）には影響しない。PO の画面確認（F9）で見えにくいと言われたら、別便で #0284c7 に替える。
- docs/adr/ADR-067-design-token-enforcement.md の「カラートークン（tokens.css — グラフ系列 …）」表の後ろに、同じ形の表「カラートークン（tokens.css — 在庫表の最安・在庫最多の枠 / ADR-1014）」を足す（2行: `--comp-value-frame-cheapest` 用途「最安の値の枠（水色）」、`--comp-value-frame-most-stock` 用途「在庫最多の値の枠（緑。--success の別名）」）。Opus が書く。
- tokens.css は check:css-colors の除外対象（frontend/scripts/check-css-hardcoded-colors.js:20）。`--comp-` は check:color-token-sync の対象外（frontend/scripts/check-color-token-sync.js:45）。
- PR 本文に、`.github/PULL_REQUEST_TEMPLATE.md:51-55` の欄を文言そのままで入れて全部に印を付ける（frontend/scripts/check-new-tokens.js が部分一致で照合する）:
  ```
  ### デザイントークン変更時（tokens.css / index.css を変更した場合）
  - [x] 新しいトークンを追加した場合、その**理由**を概要欄に記載した
  - [x] 色トークンは `:root`（ライト）と `:root.force-dark`（ダーク）の両方に追加した
  - [x] `npm run check:dark-parity` でパリティ確認済み
  - [x] 既存トークンで代替できないか確認した（トークン重複防止）
  ```
  概要欄には上の「水色の値の理由」と「既存に水色が無い」ことを書く。`npm run check:dark-parity` は実際に実行して通ることを確かめる。ただしこの検査は index.css しか見ない（frontend/scripts/check-dark-parity.js:19）ので、tokens.css の2トークンがライト・ダークの両方にあることは差分の目視（F6）で確かめる。

## 触るファイルと中身

1. backend/app/routers/inventory_offers.py
   - :306-316 の `PARTITION BY d.product_id` 8か所を全部 `PARTITION BY d.product_id, d.status, d.condition` に替える。他の文字は変えない（列名・列数・3枝の NULL 埋めは同じ）。
   - :290-291 の docstring と、バッジ計算の直前のコメントがあれば「同じ product_id のまとまり」を「同じ product_id・status・condition のまとまり」に直す。
2. backend/app/schemas/inventory_offers.py:160-161 の `badge_cheapest`・`badge_most_stock` に付いた `#` コメントだけを「同じ商品・ステータス・状態のまとまり（絞り込み後・ページ前）で最安／在庫最多か（ADR-1014 改訂 2026-10-19（3））」に書き換える。Field の description は無い（openapi.json:12113-12122 にも説明は無い）ので、openapi.json は再生成せず触らない。項目名・型・既定値は変えない。
3. backend/tests/test_inventory_distribution_rows.py:117-123 の `_VIEW_SQL_BEFORE` 2組（長さと SHA256）を新しい SQL で再生成する。:117-118 のコメントに「改訂（3）で PARTITION BY に status・condition を足した後の値」と足す。`_GOLDEN`（:268-273）は変わらないはず。変わったら止めて報告する。
4. backend/tests/test_inventory_distribution_rows_pg.py に試験を2つ足す（既存の B1〜B3b は変えない）。`_add_row` の `status=`・`canonical=`・`unit=` と `ids.case` を使う（前例 :465-466）。
   - F1 ステータス違い: 同じ p1・box で、In Stock の行 価格100/200・数量5/9 と、Pre-order の行 価格300/400・数量1/3。期待: In Stock の100が最安・9が在庫最多、Pre-order の300が最安・3が在庫最多。他の行は False。
   - F2 状態違い: 同じ p1、In Stock で、Sealed box（ids.box）の行 価格100/200・数量5/9 と、Case（ids.case、canonical="Case"、unit="Case"）の行 価格500/600・数量1/3。期待: Sealed box の100が最安・9が在庫最多、Case の500が最安・3が在庫最多。他は False。
   - F2b 1行だけのまとまり（別の試験）: p1・In Stock で、Sealed box 2行（価格100/200・数量5/9）と Case 1行（ids.case、canonical="Case"、unit="Case"、価格500・数量50）。期待: Case の行は (False, False)、Sealed box の100が最安・9が在庫最多。旧規則なら数量50 の行に在庫最多が付くので新旧を見分けられる。
   - F1・F2・F2b は merge の False と True の両方で回す（`@pytest.mark.parametrize`。basis を入れなければ行はまとまらないので期待値は同じ）。
   - 判定は既存の補助 `_badge_rows`（:734）・`_badges_by_key`（:761）を使う。
5. frontend/src/tokens.css に上の2トークン（ライト2つ・ダーク2つ。:393 の直後と :589 の直後）。
6. frontend/src/features/inventory/blockBadges.tsx を書き直す（ファイル名は変えない。中身は枠の入れ物）:
   ```tsx
   /** 価格・数量の値の入れ物。同じ商品・ステータス・状態のまとまりの最安は水色の枠、在庫最多は緑の枠で囲む（ADR-1014 改訂 2026-10-19（3））。在庫表と閲覧ページで同じ描画を使う。枠の有無で幅を変えない。 */
   import type { ReactNode } from "react";
   import "./inventoryColumns.css";

   export function BlockValue({ frame, label, children }: { frame: "cheapest" | "mostStock" | null; label?: string; children: ReactNode }) {
     const cls = frame === "cheapest" ? " inventory-cell__value--cheapest" : frame === "mostStock" ? " inventory-cell__value--most-stock" : "";
     const testid = frame === "cheapest" ? "block-frame-cheapest" : frame === "mostStock" ? "block-frame-most-stock" : undefined;
     return (
       <span className={`inventory-cell__value${cls}`} data-testid={testid} title={frame ? label : undefined}>
         {children}
       </span>
     );
   }
   ```
   `BlockBadge` の export は消す（使う所は 7・8 だけ、recon §5）。
7. frontend/src/features/inventory/inventoryColumns.tsx
   - :8 の import を `BlockValue` に替える。
   - 価格セル（:131-136）: `<span className="inventory-cell__nowrap"><BlockValue frame={it.badge_cheapest ? "cheapest" : null} label={t("inventory.badge.cheapest")}>{`¥${it.unit_price.toLocaleString()}`}</BlockValue></span>`
   - 数量セル（:147-159）: 値の span を `<span className="inventory-cell__nowrap"><BlockValue frame={it.badge_most_stock ? "mostStock" : null} label={t("inventory.badge.mostStock")}>{it.quantity ?? ""}</BlockValue></span>` にする。「2行分」の div（:152-157）は値の入れ物の外のまま変えない。
8. frontend/src/pages/viewer/viewerColumns.tsx の価格セル（:75-87）・数量セル（:88-100）を 7 と同じ形にする（辞書は `viewer.badge.cheapest`・`viewer.badge.mostStock`）。:10 の import を `BlockValue` に替える。
9. frontend/src/pages/viewer/viewerFilter.ts:237 の `keyOf` を `${r.release_date}\u0000${r.english_title}\u0000${r.japanese_title}\u0000${r.status}\u0000${r.condition}` にする。関数の説明コメント（:229-234 付近）の「まとまり」の説明に status・condition を足す。他は変えない。
10. 試験
    - frontend/src/features/inventory/inventoryColumns.test.tsx:76-97 を書き直す: (a) badge_cheapest=true の行の価格セルに `[data-testid=block-frame-cheapest]` があり、クラスに `inventory-cell__value--cheapest`、`title` が "inventory.badge.cheapest"。数量も同様（`block-frame-most-stock`、`inventory-cell__value--most-stock`、"inventory.badge.mostStock"）。(b) フラグが false/undefined の行でも価格・数量の値が `.inventory-cell__value` に入っていて、`--cheapest`・`--most-stock` のクラスと `title` が無い。(c) 価格・数量セルに `.comp-badge` が無い。describe 名は英語（`local/no-japanese-literal` のため）。
    - frontend/src/pages/viewer/viewerColumns.cells.test.tsx:64-80 を同じ観点で書き直す。
    - frontend/src/pages/viewer/viewerFilter.test.ts:117-160 に2つ足す: 同じ発売日・題名で status が "In Stock" と "Pre-order" の行はそれぞれのまとまりで決まる（F1 と同じ数）。condition が "Sealed box" と "Case" の行も同様（F2 と同じ数、Case 1行だけなら付かない）。既存の試験は変えない（全行が同じ status・condition のため結果は同じ）。
11. docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md に「改訂 2026-10-19（3）」を足す。docs/adr/ADR-067-design-token-enforcement.md に枠のトークンの表を足す（どちらも Opus が書く。済み。実装担当は触らない）。その後 `node scripts/generate-adr-index.js` で docs/adr/README.md を再生成する（変化が無ければそのまま）。

触らないもの: 並び順・件数・ページ・絞り込みの候補・配信行の定義・API の項目名・辞書キー・index.css・Badge の金型・「2行分」の表示・GAS 在庫一覧（別便。GAS にバッジはまだ入っていない＝#4521 で別便とした）。

## 代替案と選んだ理由
| 案 | 結果 |
|---|---|
| `border` で枠を描く | 枠の分だけ幅が変わり、列がずれる（今回の不満と同じ）。全行に透明な border を付ければずれないが、box-shadow inset の方が1つの宣言で済む。不採用 |
| `outline` で描く | 幅は変わらないが、値の外側に出て隣の列や上下の行に被る。不採用 |
| 枠の色を既存の `--info`（青）にする | 在庫の文字色（青）と見分けにくく、PO の「水色」と違う。不採用 |
| ステータスは offer_type（在庫・予約の2種）で分ける | SQL に offer_type の列が無く（recon §1）、Python で写している。status の値で分けても、在庫・予約は別の値なので結果は同じ。対応外の status も混ぜずに分けられる。status を採用 |

## リスクと対処
| リスク | 対処 |
|---|---|
| 枠が文字に近すぎて読みにくい | 全行に `--space-1px`（上下）・`--space-1`（左右）の余白を持たせる。PO の画面確認で見づらいと言われたら別便で調整 |
| 余白を足したことで、全行の値が少し左に寄る | 全行で同じだけ寄るので列はそろう。列の幅は表の自動調整（fitToWidth）に任せる |
| 枠の意味が色だけで伝わる | `title` に「最安」「在庫最多」を出す |
| 指紋の試験（`_VIEW_SQL_BEFORE`）の更新を見落とす | 3 で更新。CI の pytest が落ちれば分かる |

## 受入条件

| 基準 | 検証方法 |
|---|---|
| F1 在庫表: 同じ商品でもステータスが違えば別々に最安・在庫最多が決まる | CI の pytest（PG 試験 F1） |
| F2 在庫表: 状態が違えば別々に決まる。1行だけのまとまりには付かない | CI の pytest（PG 試験 F2・F2b、merge の False/True） |
| F3 既存の規則（B1〜B3b）が変わらない | CI の pytest（既存 PG 試験がそのまま通る） |
| F4 閲覧ページ: F1・F2 と同じ結果 | vitest viewerFilter.test.ts |
| F5 見た目: 最安は水色の枠、在庫最多は緑の枠、Badge は出ない。枠のない行も同じ入れ物に入る（＝列がずれない） | vitest inventoryColumns.test.tsx・viewerColumns.cells.test.tsx |
| F6 色はトークンだけ（直書きなし）。新トークンはライト・ダークの両方に値がある | CI の check:css-colors・check:css-values・check:new-tokens・stylelint、目視で tokens.css の差分 |
| F7 CI の必須チェックが全部緑 | gh pr checks |
| F8 本番: マージコミットが、成功した Deploy の head の祖先（`git merge-base --is-ancestor <merge> <deploy head>`）。配信の CSS に `inventory-cell__value--cheapest` と `--comp-value-frame-cheapest` があり、配信の JS に `block-frame-cheapest` がある（アプリと閲覧ページの両方の入口） | `gh run list --workflow deploy.yml` で成功した run の head を取る。`https://app.salesanchor.jp/` と `https://app.salesanchor.jp/viewer/` の HTML から asset の URL を抜き、各ファイルを curl して grep する（/tmp/CC報告ファイル/inventory-block-frames/prod/ に保存） |
| F9 PO の画面確認: 水色・緑の枠が見え、列がそろっている | PO 目視（未観測の間は保留と書く） |

## 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。理由: 表の中の値を色の枠で強調する見た目の変更で、効果を数値で示す外部事例が判断に要らない。効果は PO の目視（F9）で判定する。
- 過去事例（自社）: #4521 の値の右隣のバッジは、その行だけ値の中身が広がり、右寄せの列で値の位置がずれた（PO の画面写真 2026-10-19）。
- 応用: 全行を同じ入れ物に入れ、枠は幅を持たない内側の影で描く（前例 frontend/src/pages/schedule.css:89）。

## 維持の仕組み
- 規則は ADR-1014 改訂（3）に書く。
- 守り手: backend/tests/test_inventory_distribution_rows_pg.py（F1・F2・F2b、CI の pytest で毎回走る）、frontend/src/pages/viewer/viewerFilter.test.ts（閲覧ページの規則）、frontend/src/features/inventory/inventoryColumns.test.tsx・frontend/src/pages/viewer/viewerColumns.cells.test.tsx（入れ物が全行にあること）、frontend の CSS 検査（トークンだけ）。

## 審査記録
- 1回目（Reviewer エージェント・opus、1df98028b 土台）: REVISE。指摘 1 色トークンの置き場所が ADR-067 と違う・ダーク側に片方を書かない → tokens.css の --offer-* の前例どおりライト・ダーク両方に書き、ADR-067 に表を足し、PR 本文の欄を文言そのままで設計に記載。2 #0ea5e9 は白地 2.8:1 → 値は PO の「水色」を優先して据え置き、理由と見えにくい場合の替え先（#0284c7）を記載。3 F2 の1行だけの確認が新旧を見分けない → F2b に分け、数量で見分ける形にした。4 schemas は `#` コメントだけ → 明記し openapi は触らない。5 F8 は祖先で判定・取り方を記載。推奨（merge の False/True で回す・区分の表に無い status の差を ADR に書く）も取り入れた。
- 2回目（Reviewer エージェント・opus）: APPROVE。迷いどころ3点（検査の場所は frontend/scripts/、check:dark-parity は tokens.css を見ないので目視で補う、F2b の Case 行の引数）を設計に反映した。
