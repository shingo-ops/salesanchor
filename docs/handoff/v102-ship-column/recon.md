# recon: 発送日の専用列（v102）— 発送日が違えば別の件として配信する

基準 origin/main（2026-10-12、8a421f22c。設計審査の指摘で f9a303f0c から更新。差分のうち本件に関わるのは tcg_distribution_svc.py の書き込み関数の分割と run_all_migrations.sh の追記のみ）。本番は読み取りのみ（SET TRANSACTION READ ONLY・READ ONLY 確認済み）。社外秘：投稿の原文・仕入元の名前・商品名と価格の組はこの文書に書かない。生出力（手元）: ~/CC報告ファイル-keep/session-20261011-shime-ref/（tied/・ship_sim/・rank_probe/・c_probe/）。
設計: docs/handoff/v102-ship-column/design.md／前段: docs/handoff/v102-ship-note/design.md（#4161：発送の原文を note_ja に入れた）

## 既存 ADR・仕様
- `git grep -il "is_current\|ship_timing\|offer_type\|発送" docs/adr/`：docs/adr/ADR-158-product-level-supersession.md:21-27（is_current の導入・配信クエリ3か所）、docs/adr/ADR-093-inventory-table-product-master-redesign.md と docs/adr/ADR-143-inventory-public-v2-canonical.md（public.inventory の offer_type / ship_timing。別系統）、docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:26（tcg_note_master を含むマスタ群）、docs/adr/ADR-1007-migration-structure-only-run-once.md（migration は形だけ・値の操作は別手順）。docs/adr/FEATURE-INDEX.md:17 の「発送」は出荷（shipping）の話で別物。
- 仕様: docs/specs/line-analysis-tuning/README.md:59-60（発送日の行は直下の価格の件にだけ入れる）。docs/handoff/condition-level-supersession/design.md:10-16（照合キーを (product_id, condition_id) に拡張した経緯）。

## 1. 現象（本番 2026-10-12 読み取り）
- 同じ仕入元チャンネルの (product_id, condition_id) で、投稿時刻 received_at と計算時刻 computed_at が同じ行が2件以上ある組＝339組・743件（全て同じ投稿の中）。is_current はそのうち1件だけ TRUE、配信はその1件だけ。
- 339組のうち価格が違う組 250・数量が違う組 204・note_ja（発送の文字）が違う組 44。
- 例：見出し1つの下に「発送日要相談」「発売日発送」「10/19発送」の3つの価格（3件とも正しく取り出し済み）→ 配信は1件だけ。

## 2. 1件に絞る処理
- backend/app/services/tcg_analyzer_svc.py:1847-1854
  ```
  (ROW_NUMBER() OVER (
      PARTITION BY c.product_id, c.condition_id
      ORDER BY c.received_at DESC, c.computed_at DESC, (c.id IS NULL)
  ) = 1) AS should_be_current
  ```
  同じ投稿の同じ (商品, 状態) は received_at・computed_at が同値で、順位は決まらない（並びは DB 任せ）。
- 範囲：backend/app/services/tcg_analyzer_svc.py:1824 `WHERE sm.supplier_channel_id = :channel_id`。candidates（:1795-1846）が analysis_results から読む列は id / product_id / condition_id / computed_at と pid_resolved の絞り込みだけ。仮の行（analysis_soldout_extra_targets、id は NULL）も同じ順位付けに入る。
- 呼び出し元3つ：backend/app/services/line_analysis_v102_svc.py:1205（v102）、backend/app/services/tcg_analyzer_svc.py:1736（v6）、backend/app/services/v102_transcription_svc.py:386（人が件を消したとき）。extra_pairs は (product_id, condition_id) の2要素前提（backend/app/services/tcg_analyzer_svc.py:1780, :1845-1846）。
- 配信は is_current = TRUE だけ：backend/app/services/tcg_distribution_svc.py:292（本体）・:363（件数）・:405（除外内訳）。配信に GROUP BY の集約は無い。

## 3. 発送の文字の今の流れ（v102）
- 生成：backend/app/services/gemini_raw_copy_v101.py:809-826 `_ship_for`（件単位。自分の行に発送語が無ければ共有行の発送語を複写）、:963 で件の "ship" に入る。
- 保存：backend/app/services/line_analysis_v102_svc.py:640-645 `ship_note`（none/空→None、" / " ごとに括弧を直す）、:674 `"note_ja": ship_note(item.get("ship"))`、`_UPSERT_SQL` :681-702（23列、ON CONFLICT (extraction_item_id) DO UPDATE）。発送日の専用列は無い。
- 本番の解析経路：docker-compose.yml:218 `LINE_ANALYSIS_ENGINE=${LINE_ANALYSIS_ENGINE:-v102}`、backend/app/tasks/tcg_extraction.py:470-472 で v102 に分岐。過去の v6 の投稿の再解析は backend/app/services/tcg_analyzer_svc.py:1221-1227 で v6 の判定（build_note_ja、:1563）を通る。
- 本番の analysis_results：engine_version 別の行数 v9 35,085・v102 4,207（うち note_ja あり 299）・v8 736・v7 982。

## 4. 書き方をそろえるマスタ（既存）
- public.tcg_note_master（migrations/20260919_020000_master_ssot_public_tables.sql:234-252）。列に category（自由文字列・CHECK 無し）。本番の使用中 76 行・14 分類、うち category='発送時期系' 18 行（LITERAL 10・REGEX 8）。
- 当てる関数：backend/app/services/tcg_analyzer_svc.py:1057-1093 `build_note_ja`（LITERAL は語一致で label_ja、REGEX は捕捉を label_template の $1 に展開、複数当たれば "," でつなぐ）。
- 管理画面で category を含めて追加・編集できる：backend/app/routers/super_admin_note_master.py:120-236（_NOTE_UPDATABLE に category）、frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:183, :210, :272-276。
- コードで category='発送時期系' を参照する箇所は無い（git grep の一致は migrations だけ）。

## 5. 試算：v102 の発送の文字 299 件に「発送時期系」18 行を当てた結果（本番読み取り、手元 ship_sim/out.txt）
- 当たった 240 件・当たらない 59 件（39 種の文字のうち 17 種が当たらない）。
- 当たった値の例：「10/16発送」「【10/16発送】」→ 10/16発送、「到着次第発送」「届き次第発送」→ 入荷次第発送、「発送日相談」→ 発送日要相談。
- 当たらない例：「10/12〜13発送」「11/2〜4発送」（日付範囲で日だけの形）、「10/14入荷」、「✅発送日①（要相談）」、「10月中旬発送予定」、「明日発送予定」、「発売日」。
- 同じ値にそろってしまう例：「2月入荷分 入荷次第注文順に発送」「4月入荷分 …」「6月入荷分 …」→ 3つとも 入荷次第発送（月の違いが消える）。

## 6. 配信シートと読み手
- backend/app/services/tcg_distribution_svc.py:47-61 `DIST_HEADERS` 13列（8列目 Note_JA、13列目 Search Keywords）、SELECT :255-299（:265 `COALESCE(ar.note_ja, '')`）、返却 :304-320（位置固定の13要素）、書き込み backend/app/services/tcg_distribution_svc.py:493 `_write_tab_sync`、:548 `worksheet.clear()`、:550 `worksheet.append_rows(all_rows, value_input_option="RAW")`（毎回全置換）。
- 在庫一覧 GAS（repo 外 ~/tcg-viewer-1hc-release/Code.js:10-24 ALLOWED_HEADERS、:68-71 ヘッダー名で列を探す、:83-85 見つからない列は空）。列が増えても既存表示は壊れない。表示するには ALLOWED_HEADERS と index.html の COL・表の列を同時に直す（GAS の push は PO）。
- テストの列数固定：backend/tests/test_tcg_distribution.py:350（== 13）・:351（DIST_HEADERS[-1] == "Search Keywords"）・:184、backend/tests/test_tcg_result_order.py:104・:328（len(r) == 13）・:344-348（DIST_HEADERS[:12] と [12]）。

## 7. note_ja を読む箇所（判定・統合・配信の絞り込みには使っていない）
- 表示：backend/app/services/tcg_distribution_svc.py:265,313、backend/app/services/tcg_analysis_review_svc.py:229,291、backend/app/services/tcg_import_progress.py:32,133。
- 要確認の版の材料：backend/app/services/tcg_condition_review_svc.py:124（computed_at も材料のため、再解析で版が変わるのは今も同じ）。
- 再解析の履歴：backend/app/services/tcg_product_master_svc.py:668-725（analysis_run_snapshots に列を列挙して複写）。

## 8. 列追加の前例
- migrations/20261011_150000_add_analysis_results_price_basis.sql（`ADD COLUMN IF NOT EXISTS` ＋ COMMENT。値の操作なし）。登録は scripts/run_all_migrations.sh:903（直近は :912）。v102 の PG テストは backend/tests/test_line_analysis_v102_pg.py:44-45 で migration を読んで流す。ORM モデルは無い（生 SQL のみ）。

## 9. 別件で確認した事実（この設計の範囲外）
- 同じ行の二重取り 83 組は、9 月の解析の作り直しで前回の件を消さずに足した旧経路の名残（各 Gemini 応答の中の重複は 0、job の件数＝2回分の合計）。
- 状態「状態：S」「状態：A-」（全角コロン）は状態マスタの語「状態A-」に当たらず Sealed box（R4:単位既定）。状態マスタへの語の追加は別途 PO 判断。
