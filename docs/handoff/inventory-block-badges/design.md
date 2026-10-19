# design: 同じ商品のまとまりの中で、最安値の行と在庫最多の行に小さいバッジを付ける

recon: docs/handoff/inventory-block-badges/recon.md
関連 ADR: ADR-1014（改訂を足す）・ADR-1019・ADR-067・ADR-027・ADR-144・ADR-1015
前提の PR:
- 便4（#4520、b0299d3fc でマージ済み）が `_build_inventory_view_sql` に `__expiry_s` を足した。この便は b0299d3fc 以降の main を土台にする。最終の列の並びは「変更前 → 変更後」1 に固定する。
- 並び順の修正（#4519、963712e6d でマージ済み）。触る関数は違うが、ファイルの単位では viewerFilter.ts・viewerFilter.test.ts・ADR-1014・GAS の index.html が重なる。アプリ側は main を土台にする。GAS の土台は #4519 の GAS 反映（PO の承認待ち）の後に clasp pull し直したものにする。GAS（11・B10）は #4519 の GAS 反映が終わるまで着手しない。

## 目的（PO の言葉）
- PO（2026-10-19）「それと同じ商品ブロック内で最安値と在庫が1番多いものに小さいバッジを付けることは出来る？見づらくならないように小さいものが良い」
- PO 決定（2026-10-19）「y」。決定の文面は recon の末尾にある。

## 区分
A（ADR-1015）。理由は、新しい API の項目（行の2項目）と ADR の改訂を足すため。GO は POの委任に基づく Claude Opus 発行（ADR-1003）。DB の変更、migrations、deploy.yml、scripts、nginx は触らない。GAS は reference_tcg_client_viewer の手順で、テスト版 → 本番版の順に反映する。

## 判定の規則（3画面で同じ）
比べる単位は「まとまり」と呼ぶ。まとまりの中の行のうち、比べる対象は利用者が絞り込んだ後の行。ページで切る前の行で比べる。

| 規則 | 中身 |
|---|---|
| 最安 | まとまりの中で、価格が空でない行の最小値と等しい行に付ける |
| 在庫最多 | まとまりの中で、数量が空でない行の最大値と等しい行に付ける |
| 同じ値 | 最小値（最大値）と等しい行が複数あれば、全部に付ける |
| 空の値 | 価格が空の行は最安の比べから外し、数量が空の行は在庫最多の比べから外す |
| 付けない場合 | 値のある行が1行以下のときと、値のある行が全部同じ値のときは付けない（PO 決定 2026-10-19「y」） |
| まとめモード | 画面に出ている値（数量は合計、単価は最大）で比べる |
| 値の丸め | 画面に出る値と同じく、整数に丸めた値で比べる（SQL は `ROUND(d.price_num)`・`ROUND(d.qty_num)`。閲覧ページと GAS の値は作り置きの時点で `ROUND()::bigint::text`、`backend/app/services/tcg_distribution_svc.py:290-291`）。丸める前の値で比べると、100.40 と 100.00 で在庫表だけ結果が変わるため |

まとまりの決め方:
- 在庫表（サーバー）では product_id。product_id が空の行には付けない。
- 閲覧ページと GAS の行には product_id が無い（recon §2・§3）。そこで「発売日・英語名・日本語名が全て同じ」行を1つのまとまりとする。これは ADR-1014 改訂 2026-10-18 の並び順のまとまり（閲覧ページは題名2つまで、ADR-1014:44）と同じ。
- 違いが出るのは「発売日・英語名・日本語名が全て同じ別の商品」だけで、今からある既知の差（ADR-1014 改訂 2026-10-19、#4519 で追記）。

## 見た目
- 部品は既存の金型 `Badge`（`frontend/src/components/Badge.tsx`）を、size="sm"（高さ 20px）、appearance="soft" で使う。新しい部品、新しいトークン、色の直書きは作らない。
- 色:
  - 最安は variant="success"（薄い緑の地に緑の文字）。
  - 在庫最多は variant="info"（薄い青の地に青の文字）。
- 置き場所は値の右隣で、同じセル・同じ1行に置く（価格のセルに「最安」、数量のセルに「在庫最多」）。
  - 間隔は新しいクラス `.inventory-cell__badge { margin-inline-start: var(--space-1); }` で取る。置き場所は `frontend/src/features/inventory/inventoryColumns.css`。
  - 行の高さ 44px（tokens.css:509）に収まる。
- 文言（ADR-027）:
  - アプリの辞書（frontend/src/locales/ja.json と en.json）に、`inventory.badge.cheapest`（ja「最安」、en「Lowest」）と `inventory.badge.mostStock`（ja「在庫最多」、en「Most stock」）を足す。
  - 閲覧ページの辞書（frontend/src/locales/viewer/ja.json と en.json）には `viewer.badge.cheapest` と `viewer.badge.mostStock` を、同じ文言で足す。
- GAS はアプリの金型を使えない。GAS 既存の `.badge`（index.html:461-473）に、小さい版の修飾クラス `.badge-mini` を足す。
  - 色の組は GAS 既存の変数だけを使う。最安は `background: var(--success-bg); color: var(--success-text)`、在庫最多は `background: var(--info-bg); color: var(--info-text)`（index.html:468-470 の組）。
  - `.badge-mini` は、既存 `.badge` より小さくする差分だけを書く（`font-size` と `padding` を GAS 既存の変数で下げ、`margin-left: var(--space-1)`）。実装役は pull した実体の `.badge` の定義を見て、既存の変数で書く。新しい色の値は書かない。

## 変更前 → 変更後
### backend
1. `backend/app/routers/inventory_offers.py` の `_build_inventory_view_sql`
   - 最終の列の並び（3枝とも同じ）: `__kind, __total, <行の列>, __ord, __badge_cheapest, __badge_most_stock, __expiry_s, __f_*×5`。
     - rows_pg の SELECT（今の :304-305）で、`ROW_NUMBER() ... AS __ord` の直後に次の2列を足す。q_page（:318-320）は `pg.*` を展開するので、`__ord` の次にこの2列が来て、その後に便4の `NULL::bigint`（`__expiry_s`）が続く。
     - q_total（:312-316）では、`__ord` に当たる `NULL::bigint` の直後（`__expiry_s` に当たる `NULL::bigint` の前）に `NULL::boolean AS __badge_cheapest, NULL::boolean AS __badge_most_stock` を置く。
     - q_facet（:322-325）は `nx.*, NULL::bigint, NULL::bigint, fd.…`（:323）の形で別名が無い。1つ目の `NULL::bigint`（`__ord`）と2つ目の `NULL::bigint`（`__expiry_s`）の間に `NULL::boolean, NULL::boolean` を入れる。
     ```sql
     (d.product_id IS NOT NULL AND d.price_num IS NOT NULL
       AND COUNT(d.price_num) OVER (PARTITION BY d.product_id) >= 2
       AND MIN(ROUND(d.price_num)) OVER (PARTITION BY d.product_id) < MAX(ROUND(d.price_num)) OVER (PARTITION BY d.product_id)
       AND ROUND(d.price_num) = MIN(ROUND(d.price_num)) OVER (PARTITION BY d.product_id)) AS __badge_cheapest,
     (d.product_id IS NOT NULL AND d.qty_num IS NOT NULL
       AND COUNT(d.qty_num) OVER (PARTITION BY d.product_id) >= 2
       AND MIN(ROUND(d.qty_num)) OVER (PARTITION BY d.product_id) < MAX(ROUND(d.qty_num)) OVER (PARTITION BY d.product_id)
       AND ROUND(d.qty_num) = MAX(ROUND(d.qty_num)) OVER (PARTITION BY d.product_id)) AS __badge_most_stock
     ```
     （`COUNT>=2` と `MIN<MAX` は「付けない場合」の PO 決定（2026-10-19「y」）による。）
   - docstring の列の並びを上の並びに直す。
   - ページの行を取り出す所（今の :420、`{k: v for k, v in row.items() if not k.startswith("__")}`）を、次の形に1つに決める。"__" の列を外す規則そのものは変えない。
     ```python
     {
         **{k: v for k, v in row.items() if not k.startswith("__")},
         "badge_cheapest": bool(row["__badge_cheapest"]),
         "badge_most_stock": bool(row["__badge_most_stock"]),
     }
     ```
   - `_project_inventory_rows`（:153-185、呼び出し元は :428 の1か所）で、`badge_cheapest=bool(row.get("badge_cheapest"))` と `badge_most_stock=bool(row.get("badge_most_stock"))` を入れる（読むキーは "__" の付かない名前）。
1b. `backend/tests/test_inventory_distribution_rows.py:107` の指紋の試験（1文全体の長さと sha256 を `_VIEW_SQL_BEFORE`（:118-122）と比べる）は、SQL が変わるので必ず落ちる。`_VIEW_SQL_BEFORE` の `False`（:119）と `True`（:120）の2組とも、長さと sha256 を変更後の SQL から出した値に直し、説明のコメント（:115-117）に「ADR-1014 改訂 2026-10-19（2）でバッジの2列を足した」と書き足す。同じファイルの :141 の `ORDER BY ... == 2` の数は窓関数が ORDER BY を持たないので変わらない（変わったら止めて報告する）。
2. `backend/app/schemas/inventory_offers.py` の InventoryRow（:129-160）
   - `badge_cheapest: bool = False` と `badge_most_stock: bool = False` を、merged_count の後に足す。
   - 説明は「同じ商品のまとまり（絞り込み後・ページ前）で最安／在庫最多か（ADR-1014 改訂）」とする。
2b. `frontend/api-contract/openapi.json` を出し直してコミットする（InventoryRow に2項目が増えるため。`.github/workflows/api-contract-check.yml:50-53` が差分を止める）。出し直しの手順はこのファイルを最後に更新した PR（`git log -1 -- frontend/api-contract/openapi.json`）と同じ方法で行い、手で編集しない。

### frontend
3. 新規 `frontend/src/features/inventory/blockBadges.tsx`
   - 2画面で同じ描画を使うための小さな関数を置く（新しい金型ではなく、Badge を並べるだけ）。
     ```tsx
     // Badge は data-testid などの残りの props を受け取らない（Badge.tsx:20-34）。testid は包む span に付ける
     export function BlockBadge({ kind, label }: { kind: "cheapest" | "mostStock"; label: string }) {
       return (
         <span className="inventory-cell__badge" data-testid={kind === "cheapest" ? "block-badge-cheapest" : "block-badge-most-stock"}>
           <Badge size="sm" variant={kind === "cheapest" ? "success" : "info"}>{label}</Badge>
         </span>
       );
     }
     ```
4. `frontend/src/features/inventory/inventoryColumns.tsx`
   - 行の型に `badge_cheapest?: boolean; badge_most_stock?: boolean` を足す（任意。既存の試験が型付きで行を作っているため。無いときは付けない）。
   - 価格のセル（:126、列は :119-127）の最終の形:
     ```tsx
     <span className="inventory-cell__nowrap">
       {/* 既存の値の表示（今の中身のまま） */}
       {it.badge_cheapest && <BlockBadge kind="cheapest" label={t("inventory.badge.cheapest")} />}
     </span>
     ```
     既存の値の要素が既に `inventory-cell__nowrap` の span なら、その中の末尾に BlockBadge を足すだけにして、二重に包まない。
   - 数量のセル（:137-146）も同じ形で、値の後に在庫最多を足す。まとめ件数の2行目（:140-144）はその下のまま。
5. `frontend/src/pages/viewer/viewerFilter.ts`
   - `export type BlockFlags = { badge_cheapest: boolean; badge_most_stock: boolean }` と、`export function markBlockBadges<T extends ViewerRow>(rows: T[]): (T & BlockFlags)[]` を足す（idx など T の項目を落とさない）。
   - まとまりのキーは `release_date + "\u0000" + english_title + "\u0000" + japanese_title`。
   - unit_price と quantity は文字列。空（''）は対象から外す。数は既存の `inRange`（:68-76）と同じく `Number(s)` に通し、`Number.isFinite` でないものも外す。
   - 規則は上の表どおり。
6. `frontend/src/pages/viewer/InventoryView.tsx:91-98`（:91-95 の `const sorted = useMemo(() => sortRows(filterRows(...)))` と :98 の `pageRows`）
   - `markBlockBadges(sortRows(filterRows(...), ...))` の順に呼び、そのあとページを切る。並べ替えは行の集合を変えないので、判定は「絞り込み後・ページ前」の行で行われる。sortRows は変えない（#4519 が触る関数のため）。
7. `frontend/src/pages/viewer/viewerColumns.tsx`
   - 価格（:74-80）と数量（:82-88）に、4 と同じ形で BlockBadge を足す。文言は `viewer.badge.*`。
   - `buildViewerColumns` の行の型（:26）を `ViewerTableRow & Partial<BlockFlags>` に揃える。
8. `frontend/src/features/inventory/inventoryColumns.css` に `.inventory-cell__badge` を足す（トークンだけを使う）。
9. 辞書の4ファイルにキーを足す（ja と en に同じキー）。

### ADR
10. `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md` に「改訂 2026-10-19（2）」を足す（Opus が書く）。中身は判定の規則、3画面で揃えること、まとまりの決め方の差。

### GAS（リポジトリの外。テスト 1Tb → 本番 1hc）
11. index.html。土台は、直前に別のディレクトリへ clasp pull した実体にする。
    - render() で、絞り込み後の行（ALL_ROWS を絞った配列、:1356 付近）について、5 と同じ規則で最安・在庫最多の行を決める。
      - キーは 発売日・English Title・Japanese Title。
      - 値は COL.unitPrice と COL.quantity を、既存の `parseFilterNumber`（:1130）で数にしたもの。数にならない値と空は外す。
      - 結果は `Set`（最安の行の集合、在庫最多の行の集合。行の配列そのものを要素にする）2つに入れ、`renderTable(rows, badges)` の第2引数で渡す（#4519 反映前の実体では呼び出しが `renderTable(filtered)` :1436、定義が :1441。行番号は pull し直した実体で確かめる）。行の配列に列を足さない（14列のまま）。
    - renderTable の数値セル（:1501-1503。`col.numeric` は価格と数量の両方に当たるので、`col.idx === COL.unitPrice`／`col.idx === COL.quantity` で分ける）で、価格のセルの値の後に `<span class="badge badge-mini badge-cheapest">最安</span>` を、数量のセルの値の後に `<span class="badge badge-mini badge-most">在庫最多</span>` を出す。
    - CSS に `.badge-mini`、`.badge-cheapest`、`.badge-most` を足す。
    - GAS の文言は、GAS 既存の書き方（日本語の直書き）に合わせる。GAS は ADR-027 の対象外の別のプロジェクト。

## 触らない範囲
- 並び順（`_build_view_order_by`、`sortRows`）、件数、ページ、絞り込みの候補、配信行の定義。
- Badge の金型そのもの、tokens.css、DataTable。
- 状態列やステータス列の表示。
- DB、migrations、deploy.yml、scripts、nginx。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| B1 SQL: 同じ商品に 100・200・100 の3行があれば、100 の2行が最安になり、200 の行は最安にならない | pytest（PG）`backend/tests/test_inventory_distribution_rows_pg.py` に足す |
| B2 SQL: 1行だけの商品、全部同じ価格の商品、価格が空の行には最安が付かない。在庫最多も同じ | 同上 |
| B3 SQL: 絞り込みで行を減らすと、残った行の中で決まる。ページをまたいでも、まとまり全体で決まる（per_page=1 で2ページ目の行も正しい） | 同上。既存の `_new_single_statement`（:338-357）は変えない。前例 `_view_items`（:471-494）と同じ形（同期の Session で `_build_inventory_view_sql` を直接流す）の新しい補助関数 `_badge_rows(session, *, merge, where, params, limit, offset)` を同じファイルに足す。where/params は `_build_view_filters` の値。返す値は page の行（`__kind` が page のもの）の `(__ord, __badge_cheapest, __badge_most_stock, 識別に使う列)` を `__ord` の順に並べたもの。B1〜B3b はこの関数で判定する |
| B3b SQL: まとめモード（merge=True）で、まとめた組の合計数量が他の行を上回る商品では、「在庫最多」がまとめた行に付く（画面に出ている値で比べる） | 同上（`_badge_rows` を merge=True で呼ぶ）。まとめた組は既存の `test_t2_ranks_of_the_same_post_become_one_row`（:166）と同じく、`_add_row` の `basis` 引数（:71-73）で根拠の違う2行を同じ投稿に入れて作る |
| B3d 写し替え: `_project_inventory_rows` に `badge_cheapest: True`・`badge_most_stock: True` を持つ行を渡すと `InventoryRow.badge_cheapest is True` と `badge_most_stock is True` になり、キーが無い行では両方 False になる | pytest（`backend/tests/test_inventory_distribution_rows.py` に1つ足す。DB 不要） |
| B3c 指紋の試験 `backend/tests/test_inventory_distribution_rows.py:107` が、直した `_VIEW_SQL_BEFORE` で通る | pytest |
| B4 3枝の列の並びが `…, __ord, __badge_cheapest, __badge_most_stock, __expiry_s, __f_*×5` で揃い、`backend/tests/test_inventory_distribution_rows_pg.py:348` の列名の完全一致をこの並びに直したうえで通る | 同上 |
| B5 在庫表の価格のセルに最安のバッジが、数量のセルに在庫最多のバッジが出る。false・項目なしのときは出ない | vitest（inventoryColumns の試験。parity の試験も通る） |
| B5b 閲覧ページの価格・数量のセルにも同じく出る | vitest `frontend/src/pages/viewer/viewerColumns.cells.test.tsx` |
| B5c openapi.json が出し直されている | CI の API contract チェック |
| B6 閲覧ページの `markBlockBadges` が B1〜B3 と同じ結果を返す（'' と NaN を外し、キーで分ける） | vitest `frontend/src/pages/viewer/viewerFilter.test.ts` |
| B7 i18n のキーが ja と en で揃い、ハードコードした日本語が無い | 既存の i18n チェック（CI） |
| B8 CI の必須チェックが全て緑（閲覧ページの bundle 上限 300KB の check-viewer-bundle.js を含む） | gh pr checks |
| B9 本番で反映を確かめる。①変更を含むコミットが、Deploy が成功したコミットの祖先である。②配信 JS に `block-badge-cheapest` の文字列がある。③閲覧ページの作り置き（reader 鍵で読める行）から、B6 と同じ規則で数えた最安の行の数が0より多く、全行より少ない | ①git と gh。②curl と grep。③reader 鍵の SELECT で作り置きの行を取り、ローカルで `markBlockBadges` と同じ規則で数える。作り置きを reader 鍵で読めなければ「未観測・保留」と書き、B1〜B6 で判定する |
| B10 GAS のテスト版、次に本番版で、価格が安い順にしたとき、価格が2種類以上ある商品の先頭の行に「最安」が出る（全部同じ価格の商品には出ない） | clasp pull し直して、差分が意図どおりか確かめる。Playwright で画面を確かめ、使えないときはその事実を書いて、コードの差分で判定する |

## 負荷
- ウィンドウ関数は rows_f に対して、product_id ごとに1回の集計をするだけ。rows_f は ORDER BY で既に全件を並べている。
- 追加の時間は、デプロイ後 24h の /api/v1/inventory の中央値で測る（便2・便3 と同じ方法）。1.0 秒以下を合格とする。

## リスクと対処
| リスク | 対処 |
|---|---|
| 列の並びのずれで UNION ALL が壊れる | 3枝の同じ位置に足し、B4 の試験で固定する |
| バッジで行が2行になり、見づらくなる | sm（20px）を値と同じ span に入れ、折り返さない（768px 以上） |
| 3画面で結果がずれる | 規則を ADR に書き、B1〜B3 と B6 で同じ例を試験する。まとまりの決め方の差は ADR に既知の差として書く。比べる値は3画面とも整数に丸めた値にそろえる |
| 在庫表は価格が空の行を「¥0」と出す（`backend/app/routers/inventory_offers.py:172`、inventoryColumns.tsx:126） | 空の行は比べる対象から外すので、「¥0」の行にはバッジが無く、「¥100」の行に「最安」が付く見た目になる。今からある表示で今回は変えない。既知の差として ADR に書く |
| 色の組が隣の状態の列（GAS の `.badge-sealed`・`.badge-case`、アプリの状態の文字色）と同じ success・info | バッジは価格・数量のセルの中だけに置き、文言で区別する。PO の画面確認で見間違えると言われたら、別の便で色を見直す |

## 維持の仕組み
- 守り手: backend/tests/test_inventory_distribution_rows_pg.py（B1〜B4 の判定の規則を固定する。CI の pytest で毎回走る）。閲覧ページは frontend/src/pages/viewer/viewerFilter.test.ts で固定する。
- 規則は ADR-1014 の改訂に1か所で書く。実装は、サーバーの SQL（在庫表）、viewerFilter（閲覧ページ）、GAS の3か所にある。3か所にある理由は、並び順と同じで、閲覧ページと GAS がブラウザで絞り込むため。
- 戻し方: PR を revert する。GAS は前の版に redeploy する。

## 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。理由は、PO が決めた表示の規則を自社の画面に足すだけで、外部の数値を根拠にする判断が無いため。
- 過去事例（自社）: 数量のセルの「まとめ件数」の小さい2行目（inventoryColumns.tsx:140-144、ADR-1027）で、セルの中に補足を足しても、表の行の高さの範囲に収まった。
- 応用: 今回は2行目ではなく同じ1行に、高さ 20px の sm バッジを置く。行の高さは変えない。

## 審査記録
- 1回目（2026-10-19、reviewer・opus）: REVISE。骨組み（rows_pg の窓関数、区分 A、Badge sm/soft、閲覧ページの判定位置）は正しいと判定された。
  - PO 確認: 「付けない場合」が PO 決定の文面に無い条件だったため PO に y/n を問い、2026-10-19「y」で確定した。
  - 反映した点: 便4との列の並びを固定（2）、openapi.json を追加（3）、閲覧ページの型を総称にして sortRows の後に判定（4）、行の項目を任意に（5）、testid は包む span に（6）、値を整数に丸めてそろえる（7）、「¥0」の既知の差（8）、ADR の参照と前提の PR（9）、B9 の確かめ方（10）、閲覧ページの試験と GAS の渡し方・parseFilterNumber（11）、GAS の色の組（12）、行番号と B10 の文言。
- 判定（Opus）: PO の回答が出るまで実装に渡さない。回答後に「付けない場合」を確定し、ADR-1014 改訂を #4519 マージ後に書いてから、2回目の審査に出す。
- 2026-10-19: PO「y」で「付けない場合」を確定。土台を #4519・#4520 のマージ後の main（b0299d3fc）に揃え、ADR-1014 改訂 2026-10-19（2）を書いた。2回目の審査に出す。
- 2回目（2026-10-19、reviewer・opus）: REVISE。まとめモードでも画面の値で比べること、ADR 改訂との一致、トークン・金型・i18n は合格。反映した点: F1 "__" 列を外した後に読む食い違い→:420 で "__" の付かないキーに入れる形に固定、F2 指紋の試験の定数を変更一覧（1b）と B3c に追加、F3 まとめモードの B3b を追加、B3 の補助関数、行番号（rows_pg :304、取り出し :420、InventoryView :91-98、GAS :1436）、q_facet の挿入位置、GAS のセルの分け方。
- 参考（審査の指摘）: dist_base が `price_normalized IS NOT NULL` で絞るため、在庫表に「¥0」の行は今の SQL では出ない。リスク表の「¥0」の行は起きた場合の扱いとして残す。3回目の審査に出す。
- 3回目（2026-10-19、reviewer・opus）: REVISE。F1・F2・F3・行番号は合格。反映した点: B3/B3b の検証を前例 `_view_items` と同じ形の補助関数 `_badge_rows`（案 a）に固定、写し替えを縛る B3d を追加、指紋の定数は False/True の2組とも直す、inventoryColumns.tsx の行番号。4回目の審査に出す。
- 4回目（2026-10-19、reviewer・opus）: APPROVE。実装役への注意: `_badge_rows` は `sort_col=_SORT_COLUMNS["release_date"]`・`order_dir="DESC"` を中で固定（前例 `_expiry_s` :556）、年齢の窓は `_ARGS`（:32、窓なし）を使う、「識別に使う列」は `row_key`。
- 判定（Opus）: 設計合格。アプリ側（1〜10）を Sonnet に実装委任する（PO「y」2026-10-19 で実装・マージ・本番反映まで承認済み）。GAS（11・B10）は #4519 の GAS 反映後に別便で行う。
