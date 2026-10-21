<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     リポジトリ外のパス（/tmp/... など）にはバッククォートを付けない。 -->
# recon — まとめ売り（例: 40パックセット/¥24,000 残り15）対応の現状把握

**仕事名**: bundle-sale  
**日付**: 2026-10-17  
**基準**: origin/main（fetch 済み。引用行はすべて `git show origin/main:<path>` で再確認した行番号）  
**対象ADR**: ADR-1021（置き換え対象の候補）、ADR-1023、ADR-158、ADR-1014、ADR-1019、ADR-027  
**担当**: 調査担当（Sonnet）。製品コードは編集していない。本番には触れていない。

ラベル: 【事実】= 読んだ行・出力が根拠 / 【推測】/ 【未確認】= 確かめていない。  
下調べ材料（リポジトリ外・出典）: /tmp/CC報告ファイル/bundle-sale/recon-code.md、recon-display.md（生出力 recon-display-raw/）、evidence.md、sim/summary.md、classify/summary.md。本書の file:line は、これらを origin/main で読み直して写した。

「部品」の定義（この領域）: ①まとめ売りを読む処理（書き写し・換算）②保存先の列 ③配信・表示の経路 ④単位マスタ、の4種。

---

## 観点1 全体像（どこに何があるか・データの流れ）

### 1-1 流れ（【事実】各段のコードは下の file:line）
1. Gemini が原文を書き写す → `backend/app/prompts/raw_copy_v101_e.txt`:5,13,94-95（価格は行ごとに1件。価格が2つあれば1件にまとめ「／」でつなぐ。数量は「残り」付きも原文のまま。無ければ none）
2. 数値化 → `backend/app/services/gemini_raw_copy_v101.py`:864-875（_single_number: 数字の塊がちょうど1つのときだけ数値。「残り15」→15。単位語は数量にならない）、:893-968（_extract_one。gemini_trust のとき価格・数量はこの数値）、`backend/app/services/line_analysis_v102_svc.py`:348（gemini_trust=True を渡す）
3. 保存 → `backend/app/services/line_analysis_v102_svc.py`:995-1044（_write_results）→ analysis_results（観点1-3）
4. 配信行 → `backend/app/services/tcg_distribution_svc.py`:286-386（distribution_rows_parts）→ 在庫表API・閲覧キャッシュ・GAS用シート
5. 表示 → アプリ在庫表 / 閲覧ページ / 比較表（観点1-6）

### 1-2 今のバルク換算（÷N・×N）
- 規則本体: `backend/app/services/v102_bulk_price_svc.py`:50-109（_analyze）。「N枚(セット|バルク|被りなし)」と「バルクN枚」（N>=2）を大きさの印（:54-60）、「セット」「束」「まとめ」を has_set_word（:62）、1枚印（×N、N枚@X、円/枚 など :66-78）。決まらない理由は R_X円/N枚_2way, R_multiple_set_sizes, R_set_size_and_piece_mark 等（:50-109 内）。
- 数量の単位判定: `backend/app/services/v102_bulk_price_svc.py`:112-139（_qty_unit。piece/set/unknown）。価格数: :142-153（_price_numbers）。
- 換算: `backend/app/services/v102_bulk_price_svc.py`:161-189（convert）。SET は数量単位=set かつ割り切れるときだけ、`BulkPrice(DECISION_SET, size, _rnd(price/size), _rnd(qty*size), note="{size}枚セット単位（1セット{price:,}円）")`（:187-189）。
- 適用: `backend/app/services/line_analysis_v102_svc.py`:956-973（_apply_bulk_price）。対象は product_category==バルク系 かつ pid_resolved の行だけ（:961）。SET は単位を Piece（:933）・価格を単価・数量を qty×N・note_ja・price_basis=「V102:bulk:set:N」（:935,972）に上書き。PIECE は単位だけ Piece・price_basis=「V102:bulk:piece」（:934,969）。決まらない行は _bulk_review（:951）で要確認の理由を足す。
- _write_results の実際の順番（`backend/app/services/line_analysis_v102_svc.py`）:
  1. _analysis_values（:1013。定義 :672-706、note_ja は None、price_basis は :705）
  2. _apply_bulk_price（:1014-1017。原文ブロックは _source_block :938）
  3. apply_value_overrides ＋ _without_bulk_reason_if_human_priced（:1019-1023。人の直しはバルク換算の後に重なる）
  4. _buyback_units（:1024）
  5. _unit_price_mismatches（:1025。定義 :913-930）
  6. 行ごと: _with_unit_price_reason → _apply_decisions → _apply_soldout_targets（:1026-1031）→ _inherit_price（:1032。定義 :1185-1230、is_bulk なら引き継がない :1186-1191）→ UPSERT（:1033-1037）
- ÷N・×N を固定しているテスト（`backend/tests/test_v102_bulk_price.py`、:22 から数えた def 行）:
  - :22 test_set_is_converted_to_per_piece_with_note（26000 / 5 → n=100、単価260、数量500、備考「100枚セット単位（1セット26,000円）」）
  - :28 test_set_of_1000（30000 / 2 → 単価30、数量2000）
  - :44 test_fullwidth_is_normalized（全角でも 100・260）
  - :102 test_set_row_is_converted（_apply_bulk_price 経由で 260・500・Piece・unit_id 12・note・price_basis "V102:bulk:set:100"）
  - :152 test_write_results_converts_from_the_source_block_of_the_item_lines（_write_results 経由で 260・500・Piece）
  - 付随（piece と他区分）: :110 test_piece_row_keeps_price_and_quantity_and_sets_piece_unit、:163 test_write_results_non_bulk_is_untouched（箱系は 26000・5・Set のまま）、:189 test_inherit_price_does_not_read_for_bulk、:61 test_undecidable_goes_to_review、:128 test_without_piece_unit_id_is_review_not_guessed、:172/:177/:182 人の直しで理由が外れる/残る、:211 test_reason_is_non_ackable
- 【事実】「残りNセット」と「Nセット」の区別は数量の値に効かない（_single_number は数字1つを取るだけ）。区別が効くのは _qty_unit（割り算の可否判定）だけ。

### 1-3 保存先 analysis_results の列と、列を足す手順
- 【事実】ORM モデルは無い。生SQLで読み書きする（書き込みは `backend/app/services/line_analysis_v102_svc.py`:709-732 の _UPSERT_SQL）。`git ls-tree origin/main` に alembic を含む名前は無い。
- 作成時の27列: `migrations/20260921_110000_pipeline_tables_public.sql`:214-243（id, extraction_item_id, pid_resolved, pid_basis, unit_canonical, unit_resolved, condition_canonical, condition_basis, quantity_normalized NUMERIC(14,2), price_normalized NUMERIC(14,2), note_ja, status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, unit_inferred, unit_basis, unit_confidence, unit_infer_reason, product_id, unit_id, condition_id, work_id, is_current）。
- 後から足した列: price_basis VARCHAR(100) → `migrations/20261011_150000_add_analysis_results_price_basis.sql`:2、ship_ja・ship_en TEXT → `migrations/20261013_140000_add_analysis_results_ship_ja_ship_en.sql`:2-3。migration 読みで合計30列。
- 【事実】_UPSERT_SQL の挿入列は25（`backend/app/services/line_analysis_v102_svc.py`:709-732: id から ship_en まで）。列幅の定数は :119-125（_PRICE_BASIS_MAX=100、_NUMERIC_LIMIT=10^12）。
- 【事実】まとめの数を入れる専用の数値列は無い。今の保持先は price_basis（「V102:bulk:set:N」）と note_ja（自由文）だけ。
- 列を足す手順（price_basis の前例に沿った実測。1列1migrationで行われている）:
  1. migrations/ に「YYYYMMDD_HHMMSS_説明.sql」の名前で作る。中身は「構造のみ・値の操作なし（ADR-1007）・冪等」の ALTER TABLE ... ADD COLUMN IF NOT EXISTS ＋ COMMENT（前例 `migrations/20261011_150000_add_analysis_results_price_basis.sql`:1-4）。命名規則: `backend/CLAUDE.md`:50、additive-only: :49。
  2. `scripts/run_all_migrations.sh` に run_sql を1行足す（前例 :932-933 と :957。直近の登録 :997）。migration の唯一の実行経路は `.github/workflows/deploy.yml`:222-224（新 migration は run_all_migrations.sh に追記）。登録の検査: `.github/workflows/migration-guard.yml`:119-132（deploy.yml か run_all_migrations.sh のどちらかにあれば可）。
  3. `backend/app/services/line_analysis_v102_svc.py`:709-732 の _UPSERT_SQL（INSERT 列・VALUES・ON CONFLICT の3か所）と、値を作る _analysis_values（:672-706）に列を足す。
  4. テストが migration を読み込む箇所に足す（前例 `backend/tests/test_line_analysis_v102_pg.py`:44-45。ship_ja は `backend/tests/test_tcg_condition_review.py`:96 と `backend/tests/test_tcg_work_matching_integration.py`:334）。
- 【食い違い（事実）】`backend/CLAUDE.md`:51 は「deploy.yml に psql 行を追記必須」と書くが、`.github/workflows/deploy.yml`:223 は「deploy.yml ではなく run_all_migrations.sh に追記する」。price_basis・ship_ja の migration は deploy.yml に無く run_all_migrations.sh にある（`git grep` で確認）。
- 【未確認】実テーブルの列数（本番に触れていない）。他に analysis_results へ列を足す migration を全走査していない（当たったのは unit_* の `migrations/20260901_120000_add_unit_inference_columns_t004.sql`:56-86、`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`:320、`migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql`:58,153 の ALTER。CREATE 文と重複する順序は未精査）。

### 1-4 配信（DIST）
- 14列: `backend/app/services/tcg_distribution_svc.py`:48-63（DIST_HEADERS: 投稿日時 / Mark / Japanese Title / English Title / Condition / Unit Price / Quantity / Note_JA / Status / Release Date / Series / 提供者 / Search Keywords / Ship_JA）。出力列の並び :252-255（_GAS_COLUMNS）。
- 【事実】単位の列は14列に無い。unit_canonical は最終 SELECT（:275）と dist_base（:324）にあるが、GAS 列にも閲覧キャッシュにも出ない。
- 商品名列: `COALESCE(p.name,'') AS japanese_title`（:304）、英語名 :305。p は `LEFT JOIN public.products p`（:340 付近）。行ごとに運べる文字は note_ja（:309）のみ。
- 価格・数量: price_num=ar.price_normalized（:307）、qty_num=ar.quantity_normalized（:308）。最終 SELECT は `ROUND(...)::bigint::text`（:268-278 の _distribution_final_select。:272-273）。
- gkey: :326-328（concat_ws(job, product, condition, unit, note_ja, ship_ja, status)）。
- 集約: dist_groups :359-367（can_merge = COUNT>=2 かつ basis が全て異なる）、qty_agg=SUM :376、price_agg=MAX :377、group_n :378。
- 絞り込み: WHERE :346-354（pid_resolved、is_current、cr.needs_review IS FALSE、exclusion、unit_resolved、price_normalized IS NOT NULL ほか）。【未確認】cr.needs_review（状態の確認表側）と ar.needs_review の関係。まとめ売り行は needs_review=True が多い（観点1-8）ので、配信に載る条件の突き合わせが要る。
- 呼び出し: fetch_output_rows :405-427 → build_distribution_rows :867-928 → _write_tab_sync :592-663 / _write_to_target_sync :665-672 / run_distribution :931-。

### 1-5 閲覧キャッシュと閲覧ページ
- 作り置き: `backend/app/tasks/viewer_inventory_cache.py`:28（CACHE_KEY）、:33（TTL 86400）、:38-45（to_cache_rows: _GAS_COLUMNS の14キー＋offer_type=15キー）、:72-99（refresh_once。Redis set :91）。読む側 `backend/app/routers/viewer.py`:240、許可表 `backend/app/auth/viewer_allowlist.py`:14。
- 【事実】キャッシュ行に unit も、note_ja 以外の行内項目も無い。項目を足すなら _GAS_COLUMNS（`backend/app/services/tcg_distribution_svc.py`:252-255）・最終 SELECT・to_cache_rows・`frontend/src/pages/viewer/types.ts`:11-27（ViewerRow）が連動する。
- 列定義: `frontend/src/pages/viewer/viewerColumns.tsx`:26-119。商品名 :36-47（japanese_title :43、english_title :44）、数量 :77（it.quantity）、単価 :85（formatPrice。定義 :14-19）、備考 :103（it.note_ja）。単位列は無い（:5 のコメント）。
- 閲覧用の文言: `frontend/src/locales/viewer/ja.json`:47-53（title「商品名」:49、quantity「数量」:52、unitPrice「単価」:53）。

### 1-6 アプリ在庫表・比較表
- アプリ在庫表 API: `backend/app/routers/inventory_offers.py`:152-184（_project_inventory_rows）。product_name=japanese_title（:161）、name_en（:162）、unit=unit_canonical（:166）、unit_price=round_half_up(price_num)（:171）、quantity=round_half_up(qty_num)（:172）、note_ja（:177）、merged_count（:180）。型 `backend/app/schemas/inventory_offers.py`:129-160（unit_price: int、quantity: int|None）。並べ替え `_SORT_COLUMNS` :115-127、一覧 list_inventory_view :316-。
- アプリ在庫表の画面: `frontend/src/features/inventory/inventoryColumns.tsx`。商品名 :63-71（product_name ?? #id :70、name_en :71）、単位 :89-93（it.unit ?? "-"）、数量 :124-134（merged_count>=2 で mergedCount 表示 :134）、単価 :144-149（`¥${unit_price.toLocaleString()}`）、備考 :170-173。
- 行ドロワー: `frontend/src/features/inventory/InventoryRowDrawer.tsx`:65-67（/tcg/analysis-results を呼ぶ）→ ReviewItemDrawer。
- 比較表（analysis_results 1件ずつ）: API `backend/app/routers/tcg_analysis_review.py`:117-、型 GeminiFields :38-45、SystemFields :48-61、AnalysisResultItem :81-94（system: SystemFields :88）。値の組み立て `backend/app/services/tcg_analysis_review_svc.py`:268-287（SELECT: product_title :271、unit_canonical :276、note_ja :281、quantity_normalized :284、price_normalized :285）、system 辞書 :343-360（product_title :347、unit :352、note :356、quantity :358、price :359）。
- 画面: `frontend/src/features/tcg-analysis-review/ItemComparison.tsx`:44（quantity/price は system の値があればそれを出す）、:45（product_title）、:47（unit）、:49（note）。`frontend/src/features/tcg-analysis-review/ReviewValueFixForm.tsx`:28-29（system.quantity / system.price）。`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`:130（gemini の name か product_title）。`backend/app/services/tcg_sold_out_results_svc.py`:35、`backend/app/services/tcg_analysis_dashboard_svc.py`:634（raw_product_name 集計）、`frontend/src/features/tcg-import-workflow/importWorkflowApi.ts`:38-47（raw_product_name・note_ja・quantity_normalized・price_normalized）。
- 【事実】どの画面も商品名は products.name（マスタ）か Gemini の書き写し（raw_product_name）で、「商品名＋40パックセット」を載せる行内項目は無い。行ごとに運べる文字は note_ja だけ。
- 【食い違い（事実）】比較表 SystemFields（`backend/app/routers/tcg_analysis_review.py`:48-61）に quantity と price のフィールドが無い。一方 svc は system 辞書に入れ（`backend/app/services/tcg_analysis_review_svc.py`:358-359）、フロントは読む（`frontend/src/features/tcg-analysis-review/ReviewValueFixForm.tsx`:28-29、`frontend/src/features/tcg-analysis-review/ItemComparison.tsx`:44）。手元の pydantic 2.13.0 で `S.model_validate({'a':'1','price':'9'}).model_dump()` → `{'a': '1'}`（未宣言キーは捨てられる）を確認済み（下調べ時）。【未確認】FastAPI の response_model 経由で実際の応答に quantity/price が載るか（実行していない）。まとめ売りで数量・価格を比較表に出す設計では、先にこの実応答を確かめること。

### 1-7 GAS
- 【事実】GAS のコードは本リポジトリに無い（外部 shingo-ops/tcg-client-viewer。`docs/handoff/gas-viewer-fresh-fast/recon.md`:22-23）。GAS は14列（ALLOWED_HEADERS）を表示する（`docs/handoff/gas-viewer-fresh-fast/design.md`:34）。
- 【未確認】GAS 側コードの中身（列の意味づけ・商品名の組み立て）。

### 1-8 本番の試し結果の要約（出典: /tmp/CC報告ファイル/bundle-sale/evidence.md、sim/summary.md、classify/summary.md。数値はそのまま引用。本リポジトリのコードでは再現していない）
- 母数: v102・is_current 全 4804 行 / 1007 投稿（ADR-1024 の reader の道で取得）。
- 規則 R（B1 `N+単位語+セット|バルク|被りなし|ランダム|まとめ|束|組`、B2 `バルク|まとめ+N+単位語`、直後「入」除外、N>=2）の判定: single 152 行 / 95 投稿、multi 0、none 4652。本文 md5 で 90 種。(a)35・(b)23 は全て single（漏れ 0）。
- 90 種を全件目視した結果: 正しい 84、誤り 3（商品の中身の説明 2 種 = #9・#81、1枚単価＋在庫 1 種 = #42）、本文だけでは決まらない 3（#21・#44・#69）。B2 だけで一致した行は #42 のみ（B2 を外しても取りこぼし 0）。括弧内の一致を除くと #9・#81 が外れる。
- R' （B1 のみ・括弧内除外・N>=2・直後「入」除外）は目視からの集計の想定結果で、再試しは実装時の受入試験で行う（evidence.md §3）。
- 対象外の形: B3「100枚 / 50セット @24,000」型 8 行（sim/summary.md の B3 参考は 14 行、evidence.md は目視で 8 行）、(c)「N入り」「カートン(NBOX入り)」28 行（今は Piece / Case）、×N 565 行（「N個まとめて1つの値段」と読める行は 0）。
- 今の保存: single 152 行の単位は piece×Set 83 / piece×Piece 55 / ko×Set 8 / pack×Pack 4 / ko×個 1 / ko×Box 1。バルク系区分 19 行のうち 13 行は price_basis=V102:bulk:set:N（set:100 が 12、set:1000 が 1）で ÷N・×N 済み（例 #75: 本文 ¥38,000 → 価格列 380・数量 1300）。needs_review=True は 139 / 152。
- 【事実】single 152 行のうち N が quantity_normalized と等しい行は 3（sim/summary.md「気づき」）。

---

## 観点2 共用部品（共通利用される部品・定義元と参照元）

### 2-1 単位マスタと単位の解決
- 表: public.units（id / code / canonical / kubun / is_active / created_at / updated_at）→ `migrations/20260919_020000_master_ssot_public_tables.sql`:62-70。public.unit_aliases（id / unit_id / alias_text / lang / updated_at）→ 同 :108-130。unique(alias_text, lang) の初出 `migrations/20260906_120000_create_tcg_tables_t001.sql`:348。
- 【事実】units は line_units に改名され、public.units は互換 VIEW（`migrations/20260922_080000_rename_line_analysis_tables.sql`:20,32。unit_aliases も同 :40 以降）。コードは今も public.units / public.unit_aliases を読む（`backend/app/services/tcg_analyzer_svc.py`:70-75 の _UNIT_ALIAS_SQL、:103-129）。書き込みは `backend/app/routers/super_admin_units.py`:154、`backend/app/routers/units.py`:137（INSERT INTO public.units）。【未確認】VIEW か実表か、tenant_id 列の有無（本番の実体を見ていない）。
- 値: migration に値の INSERT は無い（運営者が UI/CSV で登録: `backend/app/routers/super_admin_units.py`:154,418、`backend/app/routers/units.py`:137,330）。コード側の固定表の写し: `backend/app/services/tcg_unit_recovery_svc.py`:70-120（_UNIT_MASTER_ROWS。GAS 由来 8 件）
  - id9 Case（箱系大）/ id10 Box（箱系）/ id11 Pack（パック系）/ id12 Piece（枚系）/ id13 Set（セット系）/ id14 本（除外）/ id15 点（数量専用）/ id16 個（条件つき）。
  - 別名の例: Pack = "pack,PACK,Pack,パック,ﾊﾟｯｸ"、Piece = "piece,PIECE,Piece,pcs,PCS,Pcs,枚"、Set = "set,SET,Set,セット,ｾｯﾄ"。
  - 【事実】Booklet は backend/app・migrations・frontend/src に当たりなし（`git grep -i booklet`）。ただし sim/summary.md の「今の unit_canonical」には Booklet 29 行・MasterCarton 8 行がある（本番の値。units の実体の値は【未確認】）。
- コード定数: UNIT_SET_CODE="UN0005"（`backend/app/services/gemini_raw_copy_v102_product_first.py`:69）、_PIECE_UNIT="Piece"（`backend/app/services/line_analysis_v102_svc.py`:933）。
- 解決: マスタ読み込み `backend/app/services/tcg_analyzer_svc.py`:103-129（unit_alias_to_info。有効行のみ :74,121）→ resolve_unit_v2 :804-829（完全一致→小文字→無ければ (raw,'不明',False)）。行から別名を探す `backend/app/services/gemini_raw_copy_v101.py`:456-474（find_unit_alias）、位置条件 :443-453（_unit_position_ok）、v102 は `backend/app/services/gemini_raw_copy_v102_product_first.py`:492-519（find_unit_product_first）、_resolve_unit_from_state :621-647、resolve_product_first :650-692。「パック」→Pack は別名表の引きで決まる（コードに直書きの照合は無い）。

### 2-2 単位の日本語表示
- 【事実】public.units に表示名の列は無い（canonical / kubun のみ）。画面は unit_canonical の文字（Pack 等）をそのまま出す（`frontend/src/features/inventory/inventoryColumns.tsx`:93）。
- 【事実】i18n に単位名のキーがある: `frontend/src/locales/ja.json`:1534-1540（inventory.unit = piece「個」/ pack「パック」/ box「Box」/ case「Case」/ set「セット」）。同 :2787-2793 の unitOptions（piece「シングル (1枚)」/ pack「パック」/ box「ボックス」/ case「ケース / カートン」/ set「セット」）。
- 【事実】`git grep` で inventory.unit.* の静的な参照は見つからない（frontend/src の locales 以外に当たらず、`frontend/src/pages/inventory/InventoryFilterPanel.tsx`:231 の data-testid のみ）。【未確認】動的キーによる使用の有無。
- 【事実】閲覧キャッシュには unit が無いので、閲覧ページで単位名を出すには行の項目を足す必要がある（観点1-5）。

### 2-3 単価の確かめ
- `backend/app/services/v102_unit_price_check_svc.py`:54-68（_MARKET_SQL）: GROUP BY ar.product_id, ar.unit_canonical（:67）。(商品, 単位) ごとの price_normalized の中央値（percentile_cont 0.5 :56）。条件: engine 'v102%'・is_current・price_normalized と unit_canonical が非NULL・INHERIT 行除外（:64）・自分の投稿と同じ本文(md5)を除外（:65-66）・DISTINCT 投稿数で数える（:57）。
- 判定: `backend/app/services/v102_unit_price_check_svc.py`:123-142（is_unit_price_mismatch。自単位の中央値との比が上限を超え、別単位の中央値の方が近いとき。別単位が無ければ規則B = 高い側のみ）。設定キー :21-24。呼び出し側 `backend/app/services/line_analysis_v102_svc.py`:913-930（product_id・unit_canonical・price_normalized で Candidate を作る）。
- 【事実】キーに「まとめの数」は入っていない。まとめ1つの値段を中身の単位（Pack 等）で保存すると、同じ (商品, 単位) に「1個の値段」と「まとめ1つの値段」が混ざる。
- 買取単位: `backend/app/services/v102_buyback_unit_svc.py`:134-143（is_candidate。セット系を除く）。バルク系は Bulk 状態（`backend/app/services/gemini_raw_copy_v102_product_first.py`:83 のコメント）で候補外。

### 2-4 人の直し
- `backend/app/services/v102_human_decisions_svc.py`:43-54（直せる項目 quantity / price / unit / note / status）、:524-551（apply_value_overrides: quantity_normalized・price_normalized・unit_*・note_ja を置換）、:574-628（save_value_override。analysis_results を直接更新）。
- 【事実】apply_value_overrides は _apply_bulk_price の後に走る（`backend/app/services/line_analysis_v102_svc.py`:1014-1023）。まとめの表記を note_ja に持たせると、人が note を直した時点で表記が消える。note_ja は gkey に入る（`backend/app/services/tcg_distribution_svc.py`:326-328）。

### 2-5 バルク系区分の判定
- 【事実】判定は区分名の文字列一致。PRODUCT_KUBUN_BULK="バルク系"（`backend/app/services/gemini_raw_copy_v102_product_first.py`:48）、状態 Bulk の比較 :584、CN0014 :82。価格換算 `backend/app/services/line_analysis_v102_svc.py`:961,1015,1032。区分値の取得 `backend/app/services/tcg_analyzer_svc.py`:162-180（load_product_kubun_type_map）、v102 側 `backend/app/services/gemini_raw_copy_v102_product_first.py`:352。
- 【事実】商品区分 id=9 はコードに直書きされていない（`docs/handoff/g28-bulk-price/recon.md`:25 の記述のみ）。【未確認】tcg_product_categories の現在の行（本番）。

---

## 観点3 非共用部品（個別実装・本来共用にできそうな候補）

- 【事実】まとめ売りの読みは v102_bulk_price_svc.py 専用の正規表現（`backend/app/services/v102_bulk_price_svc.py`:50-109）で、バルク系区分の行にだけ適用される（`backend/app/services/line_analysis_v102_svc.py`:961）。他区分のまとめ売り（試しで single 152 行のうち区分が空 127・シングル系 6・バルク系 19。sim/summary.md）には適用されない。
- 【事実】「V102:bulk:*」を読む処理は backend/app・frontend/src・scripts に無い（定数 `backend/app/services/line_analysis_v102_svc.py`:934-935、書き込み :969,972 のみ）。price_basis を扱うのは INHERIT 判定（:1170、`backend/app/services/v102_unit_price_check_svc.py`:64）だけ。印は書くだけ。
- 【事実】比較表 SystemFields の食い違い（観点1-6）。
- 【事実】price_normalized の読み手は 45 か所ある（行一覧 /tmp/CC報告ファイル/bundle-sale/pn_refs.txt）。主な読み手: `backend/app/services/tcg_analysis_dashboard_svc.py`:471,472,479、`backend/app/services/tcg_analysis_review_svc.py`:285,359、`backend/app/services/tcg_condition_review_svc.py`:95,233,240、`backend/app/services/tcg_import_progress.py`:34,134、`backend/app/services/tcg_product_master_svc.py`:866,890、`backend/app/services/analysis_error_report_svc.py`:33,41、`backend/app/services/tcg_result_order.py`:34、`backend/app/services/tcg_distribution_svc.py`:307,351,465,496。精査の結果は下の「本番の試し（規則 R'・マスタの語）と審査後の確認」。
- 候補（【推測】設計の入口）: 商品名欄に出す文字は、products.name を変えずに行内項目を新設して作るのが最小の変更面になりうる。note_ja の流用は gkey・人の直しとの副作用がある（観点2-4）。

---

## 観点4 ルールの所在（ADR・正本・lint・CI）

### 4-1 既存ADR検索の結果
- 実行: `git grep -il "バルク\|まとめ売り\|bulk" origin/main -- docs/adr/` → 4件
  - `docs/adr/ADR-1021-bulk-condition-state.md`（本体のステータス表 :5 は「Proposed（便1 の実装 PR 付き。KGI B1〜B3 と便2 の KGI は PO 承認待ち）」）
  - `docs/adr/ADR-1023-condition-value-rank.md`（Accepted :5。ADR-1021 を参照 :9、Bulk は順位なし :39。衝突なし）
  - `docs/adr/ADR-067-design-token-enforcement.md`（無関係。`--inbox-bulk-icon-color`）
  - `docs/adr/README.md`（索引。:202 が ADR-1021 の行）
- `docs/adr/FEATURE-INDEX.md`（62行）に bulk / バルク / まとめ / ADR-1021 の行は無い（grep 0件）。近い行は :18（在庫 → ADR-099 / ADR-093 / ADR-014）、:20（取り込み・解析 → ADR-100 / ADR-014）。v102 / 在庫表（ADR-1014）/ 閲覧（ADR-1019）の行も無い。
- 【事実】新方針と衝突する決定は ADR-1021 の便2だけ。`docs/adr/ADR-1021-bulk-condition-state.md`:20（「価格（便2）: 単価を1枚の値段にそろえ、セット情報は備考に出す」）、:27-38（便2 の決まり）。:33 set = 単価 ÷N（割り切れなければ review）・数量 ×N・単位 Piece・note_ja「N枚セット単位（1セットX円）」・price_basis「V102:bulk:set:N」、:34 piece、:35 review（bulk_price_basis_unknown、NON_ACKABLE）、:36 価格引き継ぎ除外、:37 note_en の列は無い、:38 反映は2回、戻し方 :40 以降。「まとめ1つの値段のまま・数量=まとめの数・中身の単位」とは逆向き。置き換えには新ADR（Amends/Supersedes の明記）が要る（ADR 側の維持ルールは `docs/adr/README.md`:9 以降）。
- 【事実・食い違い】ADR-1021 本体は Proposed（:5）だが、`docs/adr/README.md`:202 は Accepted と表示している。原因（読んだ行と実行で確認）: `scripts/generate-adr-index.js`:51-52 が表の行からステータス文字列を取り、:59 の `/accept|承認|採択|完了|実装済|done/` が :60 の `/propos|提案/` より先に判定される。ステータス文字列に「PO 承認待ち」が含まれるため「Accepted」になる。同じ文字列で判定ロジックを node で実行して Accepted を確認した。ADR-1021 のステータスの正は本体の Proposed と読める（【推測】。PO 判断は【未確認】）。
- 他に git で当たった ADR（ADR-093、1014、1006、1016、1019、154、158）は「行の値の意味」を決めていない【未確認: 全文は精読していない】。ADR-158（`docs/adr/ADR-158-product-level-supersession.md`）は is_current の定義で、配信は is_current=TRUE（`backend/app/services/tcg_distribution_svc.py`:347 付近の WHERE）。衝突なし。
- ADR-027（i18n）: 新しい画面文言は t() 経由・ja/en 同一キー（`CLAUDE.md` の i18n 強制）。ja.json:3952 と en.json:3952 に bulk_price_basis_unknown のラベルがあり、`backend/app/data/review_reason_labels_ja.json`:17 と対。

### 4-2 その他の正本
- 標準フロー: `docs/STANDARD-WORKFLOW.md`:25（recon は file:line・既存ADR検索・docs/handoff/<仕事名>/recon.md）、:80（recon の完了定義）。recon 観点: `docs/specs/recon-standard/kgi.md`（7観点）。
- 関連文書: `docs/handoff/g28-bulk-price/design.md`、`docs/handoff/g28-bulk-price/recon.md`（便2の設計。:25 に id=9 の記述）。

---

## 観点5 維持の仕組み（今何が守っているか・守り手が無い箇所）

- 【事実】÷N・×N の挙動はテストが固定している（観点1-2 のテスト一覧）。新方針に変えるとこれらのテストは意図的に書き換わる（置き換え対象）。
- 【事実】列の追加は migration-guard が登録漏れを止める（`.github/workflows/migration-guard.yml`:119-132）。列を足したのに _UPSERT_SQL とテストの migration 読み込みを直し忘れた場合を止める関所は見つかっていない（【未確認】。実際にテストで落ちるかは未実行）。
- 【事実】閲覧と在庫表の列のそろいは `frontend/src/pages/viewer/viewerColumns.parity.test.tsx`:9-20 が見る。比べるのは key の並びと sortable / align / stickyLeft / mobileOrder / mobileHidden だけで、セルの中身は比べない。unit 列は除いて比べる（:9 の filter）。中身の検査は viewerColumns.cells.test.tsx（【未確認】未読）。
- 【事実】ADR 索引は CI「ADR index is up to date」が必須（`CLAUDE.md`）。上記の Proposed/Accepted の食い違いはこの CI を通っているので、CI は表示の正しさを見ていない（【推測】）。
- 【事実】`V102:bulk:*` の印を読んで守る処理は無い（観点3）。まとめ売りの印が壊れても検知する守り手は無い。
- 守り手が無い箇所（名指し）: ①単価の確かめがまとめの数を区別しないこと（観点2-3）、②比較表 SystemFields と svc/フロントの食い違い（観点1-6）、③ここに挙げた関連テストの網羅（`backend/tests` のうち test_v102_bulk_price.py 以外の bundle 例の有無は【未確認】。ファイル名のみ把握: test_line_analysis_v102_svc.py、test_line_analysis_v102_pg.py、test_v102_unit_price_check.py、test_tcg_distribution.py、test_tcg_distribution_pg.py、test_inventory_distribution_rows.py、test_inventory_offers_rbac.py、test_v102_human_decisions.py、test_v102_value_overrides.py、test_v102_price_inherit_pg.py、test_v102_buyback_unit.py、test_gemini_raw_copy_v101.py、test_viewer_inventory_cache.py、test_viewer_api.py。frontend は inventoryColumns.test.tsx、viewerColumns.parity.test.tsx ほか）。

---

## 観点6 設計図との対照（一致／不足／余剰）

設計図 = PO 指定の出し方（/tmp/CC報告ファイル/bundle-sale/kgi-proposal.md の草案。PO 承認前）。現状値は上の観点の file:line。

| 項目 | あるべき（PO指定・草案） | 現状値 | 判定 |
|---|---|---|---|
| 商品名の欄 | 商品名＋「40パックセット」（数と中身の単位から機械で作る） | products.name のみ（`backend/app/services/tcg_distribution_svc.py`:304）。行内に運べる文字は note_ja のみ（:309） | 不足 |
| 単位 | 中身の単位（パック→Pack、枚→Piece） | バルク系 SET は強制 Piece（`backend/app/services/line_analysis_v102_svc.py`:965）。バルク系以外の single は Set 83 / Piece 55 など不揃い（sim/summary.md） | 不足 |
| 単位の日本語表示 | （指定なし。「40パックセット」の組み立てに単位名が要る） | マスタに表示名列なし。画面は canonical のまま（`frontend/src/features/inventory/inventoryColumns.tsx`:93）。i18n の inventory.unit.* に参照が見つからない（`frontend/src/locales/ja.json`:1534-1540） | 不足 |
| 状態 | 今の決め方のまま | 変更面なし（`backend/app/services/gemini_raw_copy_v102_product_first.py`:570-589、ADR-1023 と矛盾なし） | 一致 |
| 値段 | まとめ1つの値段（割らない） | バルク系だけ ÷N（`backend/app/services/v102_bulk_price_svc.py`:189）。他区分は書き写した価格のまま | 余剰（÷N 経路は置き換え対象） |
| 数量 | まとめの数（残り15 → 15） | 書き写しは数字1つを取る（`backend/app/services/gemini_raw_copy_v101.py`:864-875）。バルク系 SET は ×N（`backend/app/services/v102_bulk_price_svc.py`:189） | 一致（バルク系以外）／余剰（×N） |
| まとめの数 N の保持 | 数と中身の単位から「40パックセット」を作る | 専用列なし。price_basis「V102:bulk:set:N」と note_ja のみ。印を読む処理なし（観点3） | 不足 |
| 相場との比べ | 同じまとめの数どうしで比べる | キーは (商品, 単位)。まとめの数なし（`backend/app/services/v102_unit_price_check_svc.py`:67） | 不足 |
| 3画面の出し方 | 在庫表・GAS・閲覧ページで「商品名 40パックセット／Pack／24,000円／15」 | 閲覧キャッシュは単位なし（`backend/app/tasks/viewer_inventory_cache.py`:38-45）。GAS は14列で単位なし（`docs/handoff/gas-viewer-fresh-fast/design.md`:34）。在庫表は単位あり（`frontend/src/features/inventory/inventoryColumns.tsx`:93） | 不足 |
| 比較表の数量・価格 | （設計に出す場合は必須） | SystemFields に宣言なし。実応答は【未確認】（観点1-6） | 不足（要確認） |
| 既存の決定 | ADR-1021 便2 を新ADRで置き換え | ADR-1021 本体 Proposed・README Accepted（観点4-1） | 不足（新ADR）／食い違い（表示） |
| 対象の範囲 | 「数＋単位語＋セット／バルク等」がある全商品・全区分 | 換算はバルク系区分だけ（`backend/app/services/line_analysis_v102_svc.py`:961） | 不足 |
| 人の直し | （指定なし） | note を直すと note_ja の表記は消える（観点2-4） | 余剰（note_ja 流用案を採るなら対策が要る） |

---

## 観点7 ノイズと境界

### 7-1 数え上げの仕分け
- 「bulk」の grep 当たりのうち `docs/adr/ADR-067-design-token-enforcement.md` は無関係（アイコン色の変数名）。`docs/adr/README.md` は索引（生成物）で、決定の本体ではない。
- ×N 565 行は「在庫数の書き方」で、まとめ売りではない（classify/summary.md の分類。「N個まとめて1つの値段」と読める行 0）。(c)「N入り」28 行も R の対象外。
- 試しの母数は本番の v102・is_current 全 4804 行。コードの動作は本リポジトリで実行して再現していない（読んだ行からの事実と、本番の取得結果の引用を分けた）。

### 7-2 今回見ない範囲
- GAS（外部 shingo-ops/tcg-client-viewer）のコード。
- 本番 DB の実体（units / tcg_product_categories / analysis_results の実列数）。
- 設計（How）・KGI の確定。成功条件案 K1〜K6 は docs/specs/bundle-sale/kgi.md の草案で、PO 承認前。
- ADR-1021 便2 を適用済みの本番行（Piece＋1枚単価で保存済み）を再解析で置換するか。【未確認】。

---

## 【未確認】一覧
1. 実応答で比較表の system に quantity / price が載るか（SystemFields 未宣言。FastAPI 経由を未実行）
2. 本番 units / unit_aliases の実体の値、VIEW か実表か、tenant_id 列の有無、Booklet・MasterCarton の登録
3. tcg_product_categories の現在の行（id=9・kubun_type）
4. 実テーブル analysis_results の列数（migration 読みは30）、unit_* ALTER と CREATE の重複順序
5. inventory.unit.* の動的参照の有無
6. GAS 側コード（列の意味づけ・商品名の組み立て）
7. cr.needs_review と ar.needs_review の関係（まとめ売り行の配信への載り方）
8. price_normalized の45読み手が「1個単価」前提かの精査
9. ADR-093、1014、1006、1016、1019、154 の全文（行の値の意味を決めているか）
10. viewerColumns.cells.test.tsx 等、test_v102_bulk_price.py 以外のテストの中身（bundle 例の有無）
11. ADR-1021 のステータスの正（PO 判断）
12. ADR-1021 便2 適用済みの本番行を再解析で置換するか
13. 列追加で _UPSERT_SQL などの直し忘れを止める関所の有無（実行していない）

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 比較表の実応答に quantity / price が載るか | FastAPI の応答を実行して確認（設計前に実施） | 未解決 |
| 2 | 本番の units / 区分マスタの実体 | reader の道で SELECT | 未解決 |
| 3 | GAS 側の商品名組み立て | 外部 repo を読む | 未解決 |
| 4 | ADR-1021 のステータスの正 | PO 判断 | 未解決 |

**未解決ゼロ確認**: 未解決あり（上の4件と【未確認】一覧）。設計（design.md）の前提として明記する。

## 本番の試し（規則 R'・マスタの語）と審査後の確認（2026-10-17）

- 【事実】design.md §5-2 の規則を、本番の単位マスタ・別名マスタ（/tmp/CC報告ファイル/bundle-sale/prod-units/q3.txt・q4.txt、別名 46 語。canonical が Set の「セット」「set」は単位の語に使わない。残り 22 語）で全 4,804 行に当てた。台本 /tmp/CC報告ファイル/bundle-sale/replay2/replay.py（rc=0）、生出力 replay2/out2/summary.txt・rows.tsv。
  - 決まる 144 行 / 82 種 / 89 投稿、決まらない 5 行 / 5 種（#21・#44・#50 割り切れ、#51・#69 値段なし）、当たらない 4,655 行。当たりのある投稿は 92。
  - 旧 R の当たり 152 行との差: 外れたのは #9・#42・#81 の 3 行、新しく当たった行は 0。
  - 換算済み（V102:bulk:set:N）13 行は数量を ÷N して Gemini の読みに戻して判定し、13 行とも決まる。バルク系で piece の 5 行は当たらない。
  - 例の行 8d9eea15 は N=40・Pack で決まる。
  - 「N＋別名に無い語＋まとめの語」の 135 行の語（replay2/gen_words.txt）: 種 106・種カートン 9・人の最強 6・thカード 3・セット 2・種まとめ 2 ほか 7。単位のまとめ売りは 0。
- 【事実】NON_ACKABLE_REASON_CODES（backend/app/services/review_reason_codes_svc.py:22）は condition_unknown・bulk_price_basis_unknown。入る理由は「このままで良い」が出ず API も 422（backend/app/services/v102_human_decisions_svc.py:435-439）。入らない理由は ack が item_corrections に残り再解析で外れる（backend/app/services/line_analysis_v102_svc.py:814-823）。
- 【事実】配信が見る cr.needs_review は ar から毎回作る式（backend/app/services/tcg_condition_review_svc.py:228-255、:242）。書き戻しは状態選択の保存時だけ（:378-394）。
- 【事実】price_normalized の読み手は backend/app で 66 行。「1 個の値段」前提で影響が出るのは相場（backend/app/services/v102_unit_price_check_svc.py:54-65、backend/app/services/line_analysis_v102_svc.py:913-918）・引き継ぎ（:1161-1225）・買取（backend/app/services/v102_buyback_unit_svc.py:140・215）。配信の SUM/MAX は backend/app/services/tcg_distribution_svc.py:377。詳細 /tmp/CC報告ファイル/bundle-sale/replay2/facts.md。
- 【事実】再解析は ON CONFLICT (extraction_item_id) の UPSERT（backend/app/services/line_analysis_v102_svc.py:709-732）。is_current は最後に _merge_supplier_products（:1380）が付け直す。人の直しは後から重なって勝つ。
- 【事実】理由コードの整合テストが既にある: backend/tests/test_review_reason_codes_consistency.py、backend/tests/test_review_reason_labels_ja_sync.py（.github/workflows/test.yml:242 の pytest 全体で毎回）。
- 【未確認】本番の換算済み 13 行に人の直しがあるか（便3 の始めに読み取りの道で数える）。GAS 側の価格の使い方（配信の列を読むだけという recon の表示経路の範囲まで確認）。
