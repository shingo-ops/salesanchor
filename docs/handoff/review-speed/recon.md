# 要確認一覧 速度 recon-2（基準 origin/main、読み取りのみ）2026-10-13

設計: docs/handoff/review-speed/design.md

## 1 呼び出しの流れ
【事実】
- フロント NeedsReviewTabsPanel.tsx:88-89 → GET /tcg/analysis-results
- ルーター backend/app/routers/tcg_analysis_review.py:115-158 `list_analysis_results`（:137 で fetch_analysis_results を呼ぶ。require_super_admin :132）
- サービス backend/app/services/tcg_analysis_review_svc.py:149 `fetch_analysis_results`。SQL 5本:
  1. 件数 COUNT(*) :180-181（`{source_cte} SELECT COUNT(*) {_BASE_FROM} {where}`）
  2. 提供者 DISTINCT :184-190
  3. 本体 :194-250（result_order_page AS MATERIALIZED :195-201 に LIMIT/OFFSET、最終 SELECT :202-247）
  4. review_reason_codes 読み込み :252（review_reason_codes_svc.load_review_reason_codes）
  5. works 一覧 type_master :320-324
  ※ gap_suspects/with_candidate_names :257 は候補がなければ SQL 0本（test_tcg_analysis_review.py:200 が「候補なしなら問い合わせない」を検証）。測定では 5本。
- where 組み立て :55-112 `_build_where`。NEEDS_REVIEW は :82-85。共通 FROM は :38-48 `_BASE_FROM`（モジュール読み込み時に1回文字列化。:47 で review_joins を埋め込む）。
- 並び順 backend/app/services/tcg_result_order.py:20 付近 `result_order_sql`（本体で2回埋め込み :199, :247）。

## 2 to_jsonb(ar.*)->>'product_id'
【事実】grep（origin/main 全体、docs 除く）で `to_jsonb(ar` は backend/app/services/tcg_condition_review_svc.py の3行のみ:
- :103 `review_joins(analysis_expression="to_jsonb(ar)")` 既定値
- :205 `context_sql(analysis_expression="to_jsonb(ar)")` 既定値
- :219 `reanalysis_condition` の `expression = "to_jsonb(ar)"`
- 実際の結合は :129 `CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar) cr_data`、:130 `LEFT JOIN public.products cr_product ON cr_product.id::text = cr_data.ar->>'product_id'`。同じ cr_data.ar は :143(condition_id), :144, :162-174 等でも `->>` で読まれる。
- 理由の手がかり【事実】:
  - :221-223 再解析では `expression += " || CAST(:candidate AS jsonb)"`（候補値で ar を上書きしたものを評価）。呼び出し元 tcg_analyzer_svc.py:1472, :1666。つまり ar を「jsonb 値」として差し替え可能にする設計。
  - :29 のコメントは「effect 列が無い古い試験 DB でも落ちないよう to_jsonb(行) 経由」（conditions.effect 用。product_id の理由ではない）。
  - product_id 列が無いテナントがある、という記述はコード内に見つからず。 `to_jsonb(ar)` 導入コミット 3301b4f68（git log -S）。
- 型【事実】
  - 同じ svc の :45 `LEFT JOIN public.products p ON p.id = ar.product_id` は型付き直結合。測定 plan では `Index Scan using products_pkey on products p`（measure-out-explain-raw.txt:441, :616）。→ 両者は整数どうしで比較可能。
  - migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:318,364-365 で analysis_results.product_id を UUID→INTEGER に変換（NULL可、:366）。public 側は migrations/20260923_050000_add_indexes_public_analysis_results.sql:30-31 `idx_public_ar_product_id` btree(product_id) あり。
  - products 側は products_pkey あり（上記 plan）。products.id が integer であることを直接示す CREATE TABLE は origin/main の migrations に見つからず（migrations/081_create_inventory.sql:32 のコメント「public.products.id … INTEGER」が間接根拠）。
- 結合キー cr_product.id::text 側にも ::text が付くので、products 側の索引も使えない。plan: Join Filter `(cr_product_1.id)::text = (to_jsonb(ar_1.*)->>'product_id')`、Rows Removed 231,753（recon-facts C-3）。
解消済み: products.id integer・analysis_results.product_id integer（speed-measure-candidateA.txt:25-28、pg_attribute、2026-10-13 本番読み取り）。products の pkey 名・型は plan 上 products_pkey のみ。

## 3 source_cte / review_joins
【事実】
- source_cte 定義 tcg_condition_review_svc.py:60-73（sha256(raw_text) を source_messages is_active 行に対し MATERIALIZED）
- review_joins 定義 :103-202（cr_source :128, cr_product :130, conditions 3本 :131-132/:143-144, item_corrections LATERAL 2本 :133-142, sha256 を含む binding/version :117-126,:147,:184）
- fetch_analysis_results 内の組み立て回数: source_cte 3回（:180, :184, :194）。_BASE_FROM（= review_joins）展開は 件数1 + 提供者1 + 本体2（result_order_page :197 と最終 :244）= 4回。
- 提供者・件数 SQL は同じ where を再評価（1つの結果集合を使い回していない）。

## 4 同じ関数を使う他の呼び出し元（全走査）
【事実】grep origin/main:
- fetch_analysis_results: backend/app/routers/tcg_analysis_review.py:137（API）、backend/app/services/tcg_review_csv_svc.py:75（CSV出力、NEEDS_REVIEW, limit=DIST_ROW_LIMIT）、backend/app/services/tcg_review_sheet_svc.py:108（シート出力、同条件）。
- review_joins / source_cte を直接使う: backend/app/services/tcg_distribution_svc.py:256,292,357,364,377,407（配信出力・件数・除外内訳、include_inactive=True）、backend/app/services/tcg_import_progress.py:129。
- review_joins を context_sql 経由で使う: tcg_condition_review_svc.py:208-212, :283,:286,:299,:320,:325（save_condition_review＝状態保存、各1行 WHERE ei.id=:eid）、:224 reanalysis_condition ← tcg_analyzer_svc.py:1472,:1666。item_corrections.py:27 が save_condition_review を呼ぶ。
- v102 系 backend/app/services/line_analysis_v102_svc.py:51 は REASON_* を import するのみ。v102_human_decisions_svc.py:22 は not_excluded_condition_sql のみ。
→ review_joins を書き換えると配信(tcg_distribution_svc)・取り込み進捗・状態保存・再解析に波及する。fetch_analysis_results だけの変更なら API/CSV/シートの3つ。
- 画面側の別呼び出し元: frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:52, :74（provider 指定・limit=500・strip_raw_text=true）。同じ3本の重い SQL を通る（status_tab 省略=ALL）。

## 5 既存テスト（backend/tests/）
【事実】
- test_tcg_analysis_review.py（fetch を mock。API 形・認証・無効 status_tab・gap_suspect。SQL そのものは検証しない。:104,:147,:169）
- test_tcg_condition_review.py（実 PostgreSQL。:323-343 `test_review_tabs_count_paging_and_preview` が fetch_analysis_results の NEEDS_REVIEW/NORMAL_COMPLETED の total・items・offset ページを比較。:153 context_sql。:517 limit=500。:498 review_reason_details）
- test_tcg_result_order.py（実 PG。並び順・4,097 行ページ境界。:183 test_larger_result_set…）
- test_tcg_review_csv_svc.py / test_tcg_review_sheet_svc.py（CSV・シート。fetch の items を使う純粋関数と mock 中心）
- test_tcg_is_active_filter.py:14,:86（tcg_analysis_review_svc.py の is_active 条件の検査）
- 旧実装と新実装の結果を直接比較する専用テストは見当たらない（【未確認】全 tests/ の中身は精読していない。ファイル名・grep 範囲のみ）。

## 6 フロントの呼び出し回数
【事実】
- NeedsReviewTabsPanel.tsx:75-109: production タブ表示中、/tcg/analysis-results?status_tab=NEEDS_REVIEW&offset&limit=20 を1本（依存 offset/activeTab/reloadKey）。件数・提供者・本体は別 API ではなく1レスポンス（backend 内で SQL 3本）。レスポンスの providers は表示に使われているか: NeedsReviewTabsPanel.tsx:54 に型定義はあるが、表示箇所の grep は :118-120 のセル（item.provider）のみ。providers 配列を使う UI は未確認。
- 保存後は reloadKey 変更でもう1本（:72-81,:164,:182）。
- NeedsReviewTabsPanel.drawer.test.tsx:65 / inline.test.tsx:64 は analysis-results 呼び出しが 2 回であることを期待。
- nginx ログ上は同一 URL が連続して2本出る例あり（recon-facts C-1: 02:56:12(499)+02:56:24、02:56:24+02:56:37 等）。原因は未確認。
- 該当 URL の他の画面利用: SupplierDetailView.tsx（上記、limit=500）。

## 未確認一覧
- 本番の実列型（analysis_results.product_id, products.id）: 解消済み（speed-measure-candidateA.txt:25-28）
- providers/works がフロントのどこで使われているか（NeedsReview では未使用に見えるが全文精読していない）
- 同一 URL が2本続く原因
- 全テストの精読
