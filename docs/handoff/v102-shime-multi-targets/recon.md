# recon: v102 の〆（完売）で複数の商品・状態を完売にする（便2）

- 調べた日: 2026-10-10。基準 origin/main 7477019c3。調査は Sonnet（読み取りのみ）、本番の読み取り（SELECT のみ）と結論は Opus。
- 仕入元の原文は社外秘のため、件の中身は手元の記録（~/CC報告ファイル-keep/session-20261007b/）にだけ置き、ここには集計と商品 id だけを書く。

## 0. 既存 ADR の検索
- `git grep -il "〆\|soldout\|sold_out\|完売" origin/main -- docs/adr/` → docs/adr/ADR-158-product-level-supersession.md の1件。docs/adr/FEATURE-INDEX.md に該当行なし。
- ADR-158（Status: Proposed）。Decision 2 は「新メッセージにも存在する product_id の行を is_current=FALSE」。実装（e77a696f6、2026-09-25）は (product_id, condition_id) の組ごと: backend/app/services/tcg_analyzer_svc.py:1813-1816 `PARTITION BY ar.product_id, ar.condition_id ORDER BY sm.received_at DESC, ar.computed_at DESC`。本便は組の単位を変えない。

## 1. PO の要求（原文の要旨、2026-10-10）
- 「30th 両方〆」「ドラゴンボール全て〆」のように、複数の商品をまとめて完売にする仕組み（便2）。ドラゴンボールは中分類 ID で判断できると考える（10-09）。
- 人間であれば、前の投稿で状態の違う2つが出ていたと認識し、その2つがあれば完売に切り替える（10-09）。
- 進め方（10-10）: 推測禁止・事実確認・SSOT 遵守・データの分散禁止・分からないことは聞く・確立したなら進める・マージとデプロイまで。

## 2. 今の作り（事実）
### 2-1. 〆の件を決める部品（#4106）
- backend/app/services/gemini_raw_copy_v102_soldout_ref.py:122-147 `_decide_one`。:126-129 複数を指す言葉（knowledge_rules followup_plural_word）があれば None。:143 当たった在庫の行の商品が1つでなければ None。決まると `SoldoutRefDecision(product_id, ref_message_id, ref_line, tokens)`（:49-54）。状態（condition）は扱わない（`condition` の語はこのファイルに0件）。
- backend/app/services/gemini_raw_copy_v101.py:1087-1110 `_apply_soldout_ref`。決まった件は `build(i, product_id)` で作り直し、match_status=matched_soldout_ref。
- 決まった件の状態は〆の行の文字から決まる: gemini_raw_copy_v101.py:833 `block` → gemini_raw_copy_v102_product_first.py:456-469 `_resolve_condition(block, …)`。参照した在庫の行の状態を引き継ぐ処理は無い。
- 複数を指す言葉は本番 knowledge_rules id 55〜58（両方・全部・全て・どちらも、2026-10-10 12:2xZ 読み取り）。列は id, category, pattern_type, pattern, normalized_to, priority, language, is_active, description, created_by, created_at, updated_at。

### 2-2. 書き込み（1件＝1行）
- backend/app/services/line_analysis_v102_svc.py:488-507 `_map_to_rows`（v102 の件と extraction_items を1対1、件数違いは _MappingError）。:641-668 `_write_results` が件ごとに `_UPSERT_SQL`（:564-583、`ON CONFLICT (extraction_item_id)`）。
- 制約: migrations/20260921_110000_pipeline_tables_public.sql:242 `UNIQUE (extraction_item_id)`、migrations/20260923_050000_add_indexes_public_analysis_results.sql:8。
- 本番の外部キー（pg_constraint、2026-10-10 読み取り）: analysis_results.condition_id → line_conditions(id)、extraction_item_id → extraction_items(id) ON DELETE CASCADE、unit_id → line_units(id)。product_id に外部キーは無い。RLS 無効。salesanchor_app に DELETE,INSERT,SELECT,UPDATE。public の既定権限 jarvis→salesanchor_app=arwd。

### 2-3. 1件に analysis_results を2行持たせた場合に壊れる箇所（案A を退けた根拠）
- 本番タブの行キーが extraction_item_id: frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:463。一覧の土台 backend/app/services/tcg_analysis_review_svc.py:36-46,194-201（ar の id を返さない）。
- 人の訂正は件の id で UPDATE: backend/app/services/item_corrections_svc.py:64-73、backend/app/services/tcg_condition_review_svc.py:238-239 `.scalar_one_or_none()`、:283-292（2行で例外または両行を書き換え）。
- 投稿タブ: backend/app/services/v102_transcription_svc.py:40-46（LEFT JOIN で件が重複）、backend/app/routers/tcg_v102_posts.py:107-112（id 重複を拒否）。

### 2-4. extraction_items に「子の件」を足した場合に影響する箇所（案B を退けた根拠）
- extraction_items を読む SQL は backend/app に約30か所（Sonnet 調査の分類表）。件数・並び・gemini_index を前提にするもの: line_analysis_v102_svc.py:802,812（gemini_index NULL で _MappingError）、v102_transcription_svc.py:42-45,64,373、件数を数えるもの: tcg_analysis_dashboard_svc.py:83,204-211、tcg_import_progress.py:183、tcg_diagnostics_svc.py:107、tasks/tcg_mirror.py:190-198 ほか。

### 2-5. 在庫一覧の決め方（ADR-158 マージ）
- tcg_analyzer_svc.py:1744-1854 `_merge_supplier_products(session, job_id, schema, extra_pairs=())`。:1779-1789 この job の組、:1791 extra_pairs、:1800-1827 同じ supplier_channel_id の行を組ごとに順位付けし、1位だけ is_current=TRUE（:1830-1835、行 id 単位）。status は見ない。
- 呼び出し: line_analysis_v102_svc.py:830（`extra_pairs=previous_pairs`、previous_pairs は :690-701 `_load_resolved_pairs`）、v102_transcription_svc.py:374-375（`extra_pairs=removed_pairs`、:311-327 `_delete_missing` と `_PAIRS_OF_ITEMS_SQL`）、tcg_analyzer_svc.py:1736（v6）。
- 配信: backend/app/services/tcg_distribution_svc.py:260-267（is_current・pid_resolved・`ar.exclusion IS DISTINCT FROM 'excluded'`・price_normalized 非 NULL・状態が FLAG_ でない）。〆の行は exclusion='excluded' で配信されず、同じ組の古い在庫の行を is_current=FALSE にすることで配信から消す。

### 2-6. 中分類
- products.work_id → type_master.id（backend/app/routers/buyback_prices.py:416、gemini_raw_copy_v102_product_first.py:116,135）。v102 のマスタ ProductEntry に work_id あり（backend/app/services/extraction_judgement_svc.py:109-115、読み込み extraction_shadow_svc.py:86-114）。中分類の名前は v102 のマスタに載っていない。
- 本番 type_master（2026-10-10 読み取り、14行・全て is_active）: id 3 dragon_ball「ドラゴンボール」/Dragon Ball TCG（有効商品76）ほか。other「その他」は商品0。中分類名と検索語の対応表は無い（migrations の grep で0件）。

### 2-7. デプロイの順番
- .github/workflows/deploy.yml:348-397 でコンテナを作り直して起動した後、:504-518 で `bash scripts/run_all_migrations.sh`。→ 新しい表を読むコードを表と同じ便で出すと、表ができるまでの間マージ処理が失敗する。

### 2-8. 本番の解析の版
- celery-worker の LINE_ANALYSIS_ENGINE=v102（2026-10-10 12:22Z 読み取り）。extraction_jobs 2,448 のうち v102 は46、最新 12:14:53Z。1投稿につき job は1つ（source_message_id ごとの job 数＝1 が 2,451）。
- #4106 デプロイ（2026-10-09 23:44:40Z）以降の v102 の結果に pid_basis=V102:matched_soldout_ref は0件。

## 3. 事実の測定（本番・SELECT のみ）
- is_current の〆の行 146（v6 141・v102 5）のうち、同じ仕入元・同じ商品で状態の違う在庫の行が、〆の前48時間以内の投稿に is_current のまま残る〆は 11（v6 10・v102 1）、組で12。残った在庫の行の状態の内訳は FLAG_SINGLE 6（配信されない）、Sealed box 6、Searched pack 1、Case 1（重複あり）。測定 SQL は手元 scratchpad/e1.sql・e2.sql。
- 手元の写し（2,403投稿）の試算 sim3-48h: 〆の行 1,626 のうち、複数を指す言葉の行で決まる候補3（「30th関連全て〆」→2商品、「30th全て〆」→1商品、「ドラゴンボール全て〆」→2商品）、決めない「30th 両方〆」1。
- 「30th 両方〆」の1分前の投稿の 30th の行は「30th セレブレーション BOX」と「30th FUTURISTIC BOX」の2商品（状態違いではない）。前者は検索ワードに「セレブレーション」が無く商品が決まらない。
- 試算の1商品34件が当たった在庫の行の状態の印（試算独自の印）は [通常]33・[No shrink box]1・[ST01]1・[問]1（1件で複数の行に当たるものがあり合計36。sim3-48h decided_all.tsv）。
