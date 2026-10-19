# recon: 最安・在庫最多をバッジから枠へ／比べる単位に「ステータス・状態」を足す

調べた土台: origin/main 1df98028b（2026-10-19）。調べた担当: Sonnet（読み取りのみ）。パスはリポジトリ直下からの相対パス。

## 既存 ADR の検索
- `git grep -i "最安\|在庫最多\|badge_cheapest" docs/adr/` → ADR-1014 改訂 2026-10-19（2）（docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:79-94）だけ。デザイン系は ADR-067（トークン）、ADR-144（UI 金型）、ADR-027（i18n）。

パスは worktree 直下からの相対（先頭 /Users/tanizawashingo/worktrees/salesanchor/release-inventory-block-frames/ を省略）。

## 1. backend/app/routers/inventory_offers.py
【事実】窓関数(PARTITION BY)は rows_pg CTE 1か所だけに入る。q_total / q_page / q_facet の3枝は列を揃える NULL 埋めのみ。
- :282 `_build_inventory_view_sql` 定義。:290-291 docstring（「同じ product_id のまとまり」）
- :303 `rows_f AS (SELECT * FROM rows_x d {where})`（絞り込み後の行）
- :306-310 badge_cheapest 原文:
  "(d.product_id IS NOT NULL AND d.price_num IS NOT NULL "
  "AND COUNT(d.price_num) OVER (PARTITION BY d.product_id) >= 2 "
  "AND MIN(ROUND(d.price_num)) OVER (PARTITION BY d.product_id) < MAX(ROUND(d.price_num)) OVER (PARTITION BY d.product_id) "
  "AND ROUND(d.price_num) = MIN(ROUND(d.price_num)) OVER (PARTITION BY d.product_id)) AS __badge_cheapest"
- :312-316 badge_most_stock 原文: 同形（d.qty_num、最後は = MAX(ROUND(d.qty_num))、AS __badge_most_stock）
- PARTITION BY d.product_id の出現数: cheapest 4回(:308,:309(2回),:310) + most_stock 4回(:314,:315(2回),:316) = 合計8回（grep -c で再確認可）
- :318-321 `rows_pg AS (SELECT d.*, ROW_NUMBER() OVER ({order_by}) AS __ord, {badge_cheapest}, {badge_most_stock} FROM rows_f d {order_by} LIMIT :limit OFFSET :offset)`
  窓関数は LIMIT/OFFSET より前に評価される（SQL の評価順）ので、ページをまたいでも rows_f 全体で比べる。試験 test_b3_badges_are_decided_across_pages が固定。
- 3枝の位置:
  - q_total :327-333。:329 `NULL::bigint AS __ord, NULL::boolean AS __badge_cheapest, NULL::boolean AS __badge_most_stock,`
  - q_page :334-337。`rows_pg pg CROSS JOIN rows_nx nx`（pg.* に badge 2列が入る）
  - q_facet :338-342。:339 `NULL::bigint, NULL::boolean, NULL::boolean, NULL::bigint, fd.supplier_id, ...`
- 取り出し :433-440: page 枝で `{k: v for k,v in row.items() if not k.startswith("__")}` に `"badge_cheapest": bool(row["__badge_cheapest"])`(:438)、`"badge_most_stock": bool(row["__badge_most_stock"])`(:439) を足す。
- `_project_inventory_rows` :153。:182-183 `badge_cheapest=bool(row.get("badge_cheapest"))`, `badge_most_stock=bool(row.get("badge_most_stock"))`。:157 `status_value = row.get("status") or None`、:166 `condition=str(row.get("condition") or "")`、:168 `offer_type=status_to_offer_type(status_value)`、:176 `status=status_value`。
- スキーマ backend/app/schemas/inventory_offers.py:144 `condition: str`、:158 `status: str | None`、:159 `merged_count`、:160-161 badge_cheapest / badge_most_stock（bool, 既定 False）。

### 各枝でステータス・状態を表す列（rows_f / rows_pg に載る列。3枝とも同じ列名で並ぶ）
- 状態: 列名 `condition` = backend/app/services/tcg_distribution_svc.py:325 `cr.canonical AS condition`。cr は review_joins(fenced=True)（:366）。canonical は backend/app/services/tcg_condition_review_svc.py:261-263 の CASE（確認済み condition の canonical / empty_box の canonical / それ以外は `cr_data.ar->>'condition_canonical'`）。
  NULL になり得るか【事実】SQL 上は NULL もあり得る式だが、同 svc :236-238 の `cr.canonical NOT LIKE 'FLAG_%'` は NULL だと真にならず、dist_base の WHERE(:373 `{cond_filter}`)で落ちる。よって rows_f に載る行の condition は非 NULL。空文字は【未確認】（実データ未検査）。
  アプリ API 側は schemas :144 で str（`str(row.get("condition") or "")`）。
- ステータス: 列名 `status` = tcg_distribution_svc.py:329 `COALESCE(ar.status, '') AS status`。NULL にならない（空文字 '' はあり得る）。API 側で `or None` により空文字は None になる（:157）。
  区分 offer_type は status から写す: tcg_distribution_svc.py:276-283 `OFFER_TYPE_TO_STATUS = {"in_stock": "In Stock", "pre_order": "Pre-order"}`。対応外の status は offer_type None。
  → 「予約/在庫」は window のキーに `d.status` をそのまま使うと 'In Stock' 'Pre-order' 他（Sold out は :248 の _sold_out_filter で除外済み）が別グループになる。offer_type 相当にしたい場合は `d.status` から式で導出する必要がある【推測】（現コードの SQL に offer_type 列は無い。API 側 Python で写している）。
- 商品: `d.product_id`（:337 近辺、dist_base :345 付近 `ar.product_id AS product_id`）。
- 参考: 配信行のまとめキー gkey（tcg_distribution_svc.py:345-347）は ej.id, product_id, condition_id, unit_canonical, note_ja, ship_ja, status, bundle_size。つまりまとめた行は同じ status・同じ condition_id を持つ。

### まとめモード(merge)
- :296-299 ctes: merge=True のとき rows_main の元は dist_merged（tcg_distribution_svc.py:379-406 dist_groups/dist_keyed/dist_agg/dist_merged）。price_num = MAX(price_num) over ekey（:398 price_agg）、qty_num = SUM(qty_num) over ekey（:397 qty_agg）、merged_count = group_n。rn=1 の行の status/condition を持つ（同じ gkey なので status・condition_id は同一）。
- 窓関数は rows_f（rows_main 由来）に対して動くので、まとめ後の画面の値で比べる。試験 B3b が固定。
- facet は rows_xp（まとめなし）から作る（:301 facet_src）。バッジの窓には無関係。

## 2. 試験
### backend/tests/test_inventory_distribution_rows.py
- :117-123 `_VIEW_SQL_BEFORE`（在庫表の1文・max_age=48・既定並び。バッジ列追加後の値）:
  - False: (27700, "b1b603f8889e08e742528430598c4392c074032c8fd85fef74d0055b989356b9") :120
  - True: (29617, "f264917c99d05a840c8eaa21bd031448fef13a271ad3564aee53db9b2070f595") :121
  - 使用 :107 `assert (len(sql), sha256) == _VIEW_SQL_BEFORE[same_post]`。コメント :117-118 に「バッジの2列を足した後の値」。
  - → rows_pg の SQL 文字列を変えるとこの2組が変わる（再生成が必要）。
- :268-273 `_GOLDEN`（distribution_rows_sql 本体の4組）: (False,False)…(True,True)。使用 :276-285。バッジは distribution_rows_sql の外（inventory_offers.py 側）なので、窓関数だけの変更ではこの4組は変わらない【事実: _GOLDEN は svc.distribution_rows_sql を直接ハッシュ。:282】。
  他に :84 で `_view_sql` の呼び出し回数、:369-381 `test_project_inventory_rows_copies_block_badges`（_project_inventory_rows が badge を写す）。
### backend/tests/test_inventory_distribution_rows_pg.py（839行。CI の GITHUB_ACTIONS=true でのみ動く :30）
- 補助 :31 `_ARGS`、:37-55 `ids` fixture（p1=C_A/T_A の商品、p2、box=Sealed box、case=Case）、:58 `_add_job`、:71-87 `_add_row(pg, job, product_id, condition_id, *, unit="Box", note=None, ship=None, status="In Stock", basis=None, price=1000, qty=1, canonical="Sealed box")`。
  ステータスは `status=` 引数（既定 "In Stock"）、状態は第4引数 condition_id と `canonical=`（既定 "Sealed box"。condition_id は ids.box/ids.case）で入れる。status は analysis_results.status 列、canonical は condition_canonical 列に入る（:84-86）。
- :348 列並び試験 `["__kind","__total","__ord","__badge_cheapest","__badge_most_stock","__expiry_s","__f_*"...]`（列を増減しない限り変わらない）。
- :734 `_badge_rows`、:752 `_badge_filters`、:761 `_badges_by_key`。
- B1 :768 test_b1_cheapest_and_most_stock_mark_every_row_equal_to_the_extreme（p1/box 3行 価格100/200/100・数量10/20/20、全部 status 既定 In Stock・状態 Sealed box）
- B2 :779 / :788 / :799（同価格・1行だけ・数量空）
- B3 :808 絞り込み後で決まる / :819 ページをまたぐ
- B3b :831 まとめモード（p1/box、note X 2行→数量7・単価1200 と note Y）。ファイル末尾(:839)。
- 【事実】B3c・B3d という名前の試験はこの worktree のこのファイルに存在しない（grep `def test_b[0-9]` の結果は上記。:184,:193,:206 は別機能の b1,b2,b5）。design.md(docs/handoff/inventory-block-badges/design.md:187)に「B3c（指紋の試験の定数）」への言及はあるが、実装側にはまだ無い【未確認: 別 worktree/未マージの可能性】。
- 試験データは全行 status="In Stock"・状態 "Sealed box" が既定。ステータス/状態違いを同商品に混ぜる試験は現状ゼロ【事実】。新規に `status="Pre-order"`、`ids.case`+`canonical="Case"`,`unit="Case"` の行を足す必要がある（:465-466 に case 行の作り方の前例: `_add_row(pg, job, ids.p2, ids.case, status="In Stock", basis="R2:乙", canonical="Case", unit="Case")`）。

## 3. フロント（アプリ在庫表）
### frontend/src/features/inventory/blockBadges.tsx 全文（17行）
```
1 /** 同じ商品のまとまりの中の「最安」「在庫最多」バッジ（ADR-1014 改訂 2026-10-19（2））。在庫表と閲覧ページで同じ描画を使う。金型 Badge を値の右隣に並べるだけで、新しい部品ではない。 */
5 import { Badge } from "../../components/Badge";
6 import "./inventoryColumns.css";
8 // Badge は data-testid などの残りの props を受け取らない（Badge.tsx）。testid は包む span に付ける
9 export function BlockBadge({ kind, label }: { kind: "cheapest" | "mostStock"; label: string }) {
10   return (
11     <span className="inventory-cell__badge" data-testid={kind === "cheapest" ? "block-badge-cheapest" : "block-badge-most-stock"}>
12       <Badge size="sm" variant={kind === "cheapest" ? "success" : "info"}>
13         {label}
14       </Badge>
15     </span>
16   );
17 }
```
（全文は `cat -n frontend/src/features/inventory/blockBadges.tsx` で再現可）
注意【事実】: バッジの色は 最安=success(緑)、在庫最多=info(水色)。PO の新要望は 最安=水色枠、在庫最多=緑枠 なので **色の割り当てが逆になる**。
### frontend/src/features/inventory/inventoryColumns.tsx
- :8 `import { BlockBadge } from "./blockBadges";`
- :23-39 InventoryRow 型。:26 merged_count、:28 `badge_cheapest?: boolean`、:29 `badge_most_stock?: boolean`、:36 unit_price: number、:37 quantity: number | null。（status は :3x にある `status`、condition は string）
- :123-138 価格セル: key "unit_price"、`align: "right"`(:129)、mobileOrder 3。renderCell :131-136:
  `<span className="inventory-cell__nowrap">{`¥${it.unit_price.toLocaleString()}`}{it.badge_cheapest && <BlockBadge kind="cheapest" label={t("inventory.badge.cheapest")} />}</span>`
- :139-161 数量セル: key "quantity"、`align: "right"`(:145)、mobileOrder 4。renderCell :147-159:
  Fragment 内に ①`<span className="inventory-cell__nowrap">{it.quantity ?? ""}{it.badge_most_stock && <BlockBadge kind="mostStock" .../>}</span>` ②`it.merged_count >= 2` のとき `<div data-testid={`inventory-row-${it.id}-merged`} className="inventory-cell__sub">{t("inventory.mergedCount", { count: it.merged_count })}</div>`（これが「2行分」の補足。数量の値の下の2行目に出る）。
- 幅の指定は列側に無い【事実】: DataTable は `align` だけ受ける（components/DataTable.tsx:54 `align?: 'left'|'right'|'center'`、:230 でクラス `comp-table__cell--align-right`、components/DataTable.css:187-189 `text-align: right`）。td は `padding: 0 var(--comp-table-cell-px)`、`height: var(--comp-table-row-h-default)`、`vertical-align: middle`（DataTable.css:46-51）。PC幅は `.inventory-cell__nowrap{white-space:nowrap}`（inventoryColumns.css:14-20、768px 以上）で折り返さず、はみ出す分は DataTable の fitToWidth が表ごと縮める（同 :12-13 コメント）。
### frontend/src/features/inventory/inventoryColumns.css（54行）のバッジ関連
- :51-54 `/* 価格・数量のセルで、値の右隣に置く「最安」「在庫最多」バッジの間隔（ADR-1014 改訂 2026-10-19（2）） */ .inventory-cell__badge { margin-inline-start: var(--space-1); }` これだけ。枠の CSS はまだ無い。
- 他: :1-10 title/sub、:14-20 nowrap、:23-49 offer / condition の文字色（--offer-instock-text, --info-text, --success-text, --warning-text, --purple-text, --danger-text）
### frontend/src/features/inventory/inventoryColumns.test.tsx のバッジ試験
- :76-97 `describe("block badges (ADR-1014 rev 2026-10-19 (2))")`: :82 「shows the cheapest badge in the price cell and the most-stock badge in the quantity cell」(:84 testid block-badge-cheapest の textContent == "inventory.badge.cheapest"、:88 block-badge-most-stock == "inventory.badge.mostStock")、:91 `it.each([false, undefined])("shows no badge when the flag is %s")`（`.comp-badge` が null）。
- 他の関連 :43-48 / :56-68 は条件・区分が「Badge なしの色付き文字」であることの試験（.comp-badge null）。

## 4. 閲覧ページ（frontend/src/pages/viewer/。frontend/viewer/ は index.html だけ）
### frontend/src/pages/viewer/viewerFilter.ts
- :221 `export type BlockFlags = { badge_cheapest: boolean; badge_most_stock: boolean };`
- :224-228 roundedOrNull（'' や数でない値は null、数は Math.round）
- :235-264 markBlockBadges 全文（原文は以下）:
```
export function markBlockBadges<T extends ViewerRow>(rows: T[]): (T & BlockFlags)[] {
  const groups = new Map<string, { prices: (number | null)[]; qtys: (number | null)[] }>();
  const keyOf = (r: T) => `${r.release_date}\u0000${r.english_title}\u0000${r.japanese_title}`;
  const parsed = rows.map((r) => ({ price: roundedOrNull(r.unit_price), qty: roundedOrNull(r.quantity) }));
  rows.forEach((r, i) => { const key = keyOf(r); const g = groups.get(key) ?? { prices: [], qtys: [] };
    g.prices.push(parsed[i].price); g.qtys.push(parsed[i].qty); groups.set(key, g); });
  const extremes = (vals) => { const nums = vals.filter((v): v is number => v !== null); if (nums.length < 2) return null;
    const lo = Math.min(...nums); const hi = Math.max(...nums); return lo < hi ? { lo, hi } : null; };
  const stats = new Map(); for (const [key, g] of groups) stats.set(key, { price: extremes(g.prices), qty: extremes(g.qtys) });
  return rows.map((r, i) => { const s = stats.get(keyOf(r))!;
    return { ...r, badge_cheapest: s.price !== null && parsed[i].price === s.price.lo,
                   badge_most_stock: s.qty !== null && parsed[i].qty === s.qty.hi }; });
}
```
  （上は :235-264 を行を詰めて写したもの。厳密な原文は `sed -n 221,264p`）
- まとまりキー = `release_date + "\0" + english_title + "\0" + japanese_title`（:237）。product_id は ViewerRow に無い（types.ts:11-27）。
- ViewerRow（frontend/src/pages/viewer/types.ts:11-27）のステータス・状態フィールド: `status: string`（:19、'' あり）、`condition: string`（:15）、`offer_type: "in_stock"|"pre_order"|null`（:26, ViewerOfferType :9）。unit_price/quantity は string（無いとき ''）。
- viewerColumns.tsx: :10 import BlockBadge、:75-87 価格セル（`align:"right"` :79、:84 `{it.badge_cheapest && <BlockBadge kind="cheapest" label={t("viewer.badge.cheapest")} />}`）、:88-100 数量セル（`align:"right"` :92、:97 `{it.badge_most_stock && <BlockBadge kind="mostStock" label={t("viewer.badge.mostStock")} />}`）。閲覧ページの数量セルには「2行分」の補足は無い（quantity は span 1つのみ）。ずれの検査は viewerColumns.parity.test.tsx（並び順・sortable・align・stickyLeft・mobileOrder・mobileHidden を縛る。viewerColumns.tsx:4）。
- InventoryView.tsx:23 import markBlockBadges、:91-96 `markBlockBadges(sortRows(filterRows(allRows, filters, now), sortKey, sortDir))`（絞り込み後・ページ前）。
- 試験: viewerFilter.test.ts:4 import、:117-160 `describe("markBlockBadges ...")`（B1 :121、B2 :133/:140、まとまり B3 :148-157、丸め :158）。viewerColumns.cells.test.tsx:64-80 `describe("viewer block badges ...")`（:66-72 testid と ja.viewer.badge.* の文言、:74-80 無しの確認）。viewerColumns.parity.test.tsx / InventoryView.test.tsx に badge の語は無い（grep -i badge で該当なし）。

## 5. ロケール（バッジ用キー）
- frontend/src/locales/ja.json:1501-1504 `inventory.badge`: cheapest="最安", mostStock="在庫最多"
- frontend/src/locales/en.json:1501-1504 `inventory.badge`: cheapest="Lowest", mostStock="Most stock"
- frontend/src/locales/viewer/ja.json:48-51 `viewer.badge`: cheapest="最安", mostStock="在庫最多"
- frontend/src/locales/viewer/en.json:48-51 `viewer.badge`: cheapest="Lowest", mostStock="Most stock"
- 使用箇所 grep（node_modules 除外、locales 以外）【事実】: inventoryColumns.tsx:133,:150 / viewerColumns.tsx:84,:97 / 試験 inventoryColumns.test.tsx:84,:88 / viewerColumns.cells.test.tsx:67,:71 のみ。他では使われていない。キーを消すなら上の4か所の呼び出しと2つの試験の文言期待を同時に直す。ja/en は同一キー必須（ADR-027）なので4ファイル同時削除。
- 注意: 枠だけにすると、枠の意味を示す凡例・aria 用の文言（例 title）が必要かは設計判断【推測】。
- API: frontend/api-contract/openapi.json:12113 badge_cheapest、:12118 badge_most_stock（項目名を変える/足すなら openapi も更新）。

## 6. デザイントークン
定義ファイル: frontend/src/index.css（:root :8〜、ダーク :root.force-dark :216〜）、frontend/src/tokens.css（:root :11〜、:root.force-dark :578〜）。
### 水色（info）
- --info-bg: ライト #bee3f8（index.css:109）／ダーク #1e3a5f（:298）
- --info-text: ライト #2b6cb0（:110）／ダーク #93c5fd（:299）
- --info（solid）: ライト #2563eb（:116）／ダーク #3b82f6（:305）
- 派生: --offer-instock-text = var(--info-text)（tokens.css:392 / :588）
- 【事実】sky / cyan / teal / aqua / light-blue を名前に持つトークンは無い（grep 結果 0 件）。「水色」に近いのは --info-bg(#bee3f8 は水色寄り)、--info-text(#2b6cb0 青)、--info(#2563eb 青)。index.css:108 コメントが「info バッジ（水色系）」と呼んでいる。枠線用の `--info-border` も無い。
### 緑（success）
- --success: ライト #2e7d32（index.css:143）／ダーク #4ade80（:342）
- --success-bg: #c6f6d5（:56）／#14432b（:249）
- --success-text: #22543d（:57）／#bbf7d0（:250）
- --success-bg-subtle: rgba(72,187,120,.05)（:85）／rgba(74,222,128,.10)（:276）
- --color-success: #15803d（tokens.css:559）／var(--success)=#4ade80（:607）
- --color-success-bg: #f0fdf4（:560）／rgba(34,197,94,.12)（:608）
- --color-success-border: #86efac（:561）／rgba(34,197,94,.4)（:609）← 枠線用の既存トークンは緑だけにある
- --comp-badge-success-solid: var(--success)（ライト）／#15803d（ダーク index.css:300 近辺）
### その他の枠・影・間隔トークン
- --accent #1e3a8a / ダーク #5b8dd9（index.css:33,237）、--accent-bg-subtle（:83,:274）、--focus-ring-shadow（:93,:283）、--border #e2e8f0 / #334155（:28,:233）、--border-strong（:29,:234）
- --space-1..12（tokens.css:69-78: 4,8,12,16,20,24,32,36,40,48px）、--space-1px / --space-2px / --space-3px（tokens.css:81-83）、--radius-2xs 3px / xs 2px / sm 4px / md 6px / lg 8px / xl 12px（:89-94）、--radius-badge 10px（:95）、--comp-btn-focus-width 2px（:458）
- 【事実】`--border-width` 系のトークンは無い（grep 0 件）。
### 前例（セルの値/要素を枠で囲む・強調）
- 実線の枠（1〜2px solid var(--色)）: pages/schedule.css:947,:1210 `border: 1px solid var(--success)`、features/tcg-distribution/distribution.css:123,:261 `border: 1px solid var(--accent)`、pages/dashboard/DashboardPage.css:112、pages/integrations/CarrierIntegrationPage.css:13 `border: 2px solid var(--accent)`、pages/integrations/FedexLabelValidationTab.css:392
- outline: components/Card.css:61、FormField.css:320,:404、pages/dashboard/DashboardPage.css:322 などは `outline: 2px solid var(--accent)`（フォーカス用）
- box-shadow の内側リング: pages/schedule.css:89,:194 `box-shadow: inset 0 0 0 1px var(--accent)`（レイアウトを動かさない枠の前例）、:1098 `0 0 0 2px var(--accent)`、features/tcg-analysis-review/source-raw-pane.css:65 `0 0 0 2px var(--accent-bg-subtle)`
- 【事実】`var(--info*)` / `var(--success)` を枠として使う前例: pages/schedule.css:947 の `border: 1px solid var(--success)` 他。`--info`/`--info-text` を枠にした前例は pages/integrations/FedexLabelValidationTab.css:373 `border-left: 3px solid var(--info-text, var(--accent))`（ただしこれは var() の第2引数フォールバックで、scripts/check-css-var-fallbacks.js は var(--x, #hex) だけを禁止するので通っている）。
- 【事実】「表のセルの値だけを枠で囲む」前例は見つからなかった（grep の範囲: src 下 css の outline/box-shadow/border の var(--accent/info/success) 使用）。
- 枠で列がずれない方法（技術的な選択肢。設計は別）【推測】: ①`box-shadow: inset 0 0 0 var(--space-2px) var(--色)`（レイアウトに影響しない）、②`outline` + outline-offset（同様に影響しない）、③常に透明な border を全セルに付けて対象だけ色を変える（幅は常に同じ）。②は nowrap の span の外側に出るので隣の列に被る可能性がある（td padding は --comp-table-cell-px）。
### デザイントークン強制の検査（frontend/package.json:15-46 の scripts。check:all が一括 :46）
- check:css-colors = scripts/check-css-hardcoded-colors.js: src の .css に hex（`#[0-9a-fA-F]{3,8}`）と `rgb(`/`rgba(` の直書きを禁止。index.css・tokens.css のみ除外
- check:css-values = scripts/check-css-hardcoded-values.js: opacity の中間値(0.1-0.9)、border-radius の px 直書き、z-index の数値、animation の ms、padding/margin/gap の 4px 以上の直書き、width/height/min/max の 4px 以上の直書き、font-size の 4px 以上の直書き。→ `border: 2px solid var(--..)` は検査対象のパターンに無い（border の幅は禁止対象外。`(?<![a-zA-Z-])` により border-width も sizing 検査から除外）。`box-shadow: inset 0 0 0 2px var()` も対象外。`border-radius: 4px` のような px は禁止（var(--radius-sm) を使う）。
- check:css-var-fallbacks = scripts/check-css-var-fallbacks.js: `var(--xxx, #hex)` のフォールバック hex を禁止（.css/.tsx/.ts）
- check:dark-parity = scripts/check-dark-parity.js: index.css の :root と :root.force-dark の変数が一致すること（新トークンを index.css に足すならダーク値も必須）
- check:color-token-sync = scripts/check-color-token-sync.js: index.css :root の bg/text/accent/border/success/warning/danger/info 接頭辞のトークンが src/pages/design-system/DesignSystemPage.tsx の COLOR_TOKENS に全部あること（新トークン追加時は DesignSystemPage も更新）
- check:new-tokens = scripts/check-new-tokens.js: CI で tokens.css / index.css に新トークンが増えたら PR 本文のチェックリストが全部 ✅ であることを要求（ローカルはスキップ）
- check:stylelint = `stylelint "src/**/*.css"`、設定 frontend/.stylelintrc.json は `{"rules": {"no-descending-specificity": true}}` のみ
- check:css-class-naming（クラス名規約）、check:i18n-missing-keys（ja/en のキー不足）、lint = eslint src。
- 結論【事実】: 既存トークン（--info / --info-text / --info-bg、--success / --color-success-border など）だけで書けば新トークン不要で上記検査を通る。水色の枠線専用トークンは無い。

## 7. ADR-1014 と design.md
- docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md（94行）: 「## 改訂 2026-10-19（2）（同じ商品のまとまりの中で「最安」「在庫最多」の小さいバッジを付ける）」は :79 から :94（ファイル末尾）。直前の「## 改訂 2026-10-19（価格などで並べても…）」は :68-78。
  :79 見出し、:81 PO 決定文、:83-87 判定の規則（比べる単位=商品のまとまり、:84-87 の4項目）、:88 見た目（Badge size=sm soft、最安 success / 在庫最多 info）、:89 実装の場所、:90-92 既知の差（product_id / ¥0）、:93 変えないもの、:94 守り。
  ※改訂は書き換えず新しい節を足す運用（:81 に「前の改訂節の本文は書き換えない」）。ADR 変更後は node scripts/generate-adr-index.js が必要（CLAUDE.md）。
- docs/handoff/inventory-block-badges/design.md: 191 行（同ディレクトリに recon.md あり）。

## 8. GAS
- 【事実】このリポジトリ（worktree）には GAS ソースが無い。`git ls-files` の gs/GAS 関連は docs/feedback_form_to_github.gs と docs 配下の文書のみ。`grep -rn "最安\|在庫最多"`（*.html *.gs *.js）はヒット 0 件。
- 【事実】GAS 在庫一覧の本体は別リポジトリ shingo-ops/tcg-client-viewer（ADR-1014:74,:89）。`gh api repos/shingo-ops/tcg-client-viewer` は 404（この環境の認証では見えない）。
- 【未確認】main の GAS ソースにバッジ文言があるか。根拠側の情報: ADR-1014:89 は GAS の render() にも実装すると書き、design.md:123-131 は GAS 反映手順(テスト 1Tb → 本番 1hc)を持つが、MEMORY の inventory_speed 記載は「バッジ#4521本番反映済(10/19・GASは別便)」＝GAS は別便で未反映の可能性が高い【推測】。確かめるには clasp pull した実体で `grep -n "最安\|在庫最多\|badge-mini" index.html` が必要。

## 追加で変更時に効く事実（まとめ）
1. SQL: 変更箇所は rows_pg の2つの文字列(:306-316)のみ。列数・列名は変わらない（q_total/q_facet の NULL 埋めも不変）。PARTITION BY を `d.product_id, <status式>, d.condition` に替える。status は NULL 不可（COALESCE ''）、condition は rows_f では非 NULL。
2. 試験: `_VIEW_SQL_BEFORE` 2組（test_inventory_distribution_rows.py:120-121）の再生成が必要。_GOLDEN 4組は不変。pg 試験は B1〜B3b に加え、同商品で status 違い・状態違いの行を足す新規試験が要る（現状ゼロ）。
3. フロント: viewer の markBlockBadges のキーに status と condition を足す（ViewerRow.status / .condition / .offer_type あり）。アプリは API の flags をそのまま使うので、backend の窓関数を直せば同じ意味になる。
4. 色の割り当ては現行と逆（現行 最安=success緑、在庫最多=info水色。新要望 最安=水色、在庫最多=緑）。
5. 数量セルの merged_count 補足(:152-157)は span の外の別 div。枠は値の span にだけ付ければ補足の行と干渉しない。

DONE
