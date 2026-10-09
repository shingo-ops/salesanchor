# Recon: buyback-master-addition（マスタ追加前の影響試運転）

- 起点: origin/main = 8cb3708fbbecd7f4b033f7b6582c66ba1bbf5280（worktree で `git rev-parse HEAD` 実測、2026-09-30）
- 元計画: ~/.claude/plans/pasted-content-id-63fa-refactored-puzzle.md（起点 c3fce93 で記述。下表の行番号は本 SHA で再確認済み）
- 範囲: 実装カード案 1・2（読むだけの試運転スクリプト＋コードのみの PR）。商品データ登録・本番 DB・migration・deploy.yml・CI 設定・secrets は対象外。

## PO 方針（2026-09-30 回答の原文・そのまま）

「昔の商品を登録する、マスタはSSOTさせたいので、ただし追加する前に解析の影響の有無を調査して確実に不具合を起こさないエビデンスを確立したものからリストを追加していく」

## ADR 検索（着手前）

【事実】`git grep -il -E 'replay|master addition|マスタ追加|買取.*未マッチ|product_search_keywords' -- docs/adr/` の該当:
- docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md
- docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md
- docs/adr/ADR-155-product-master-ssot-csv-app.md
- （別途参照）docs/adr/ADR-157-buyback-price-logger.md（買取マッチャー）、docs/adr/ADR-154-tcg-parity02-gas-python-migration.md（キーワード品質検査）
- docs/adr/FEATURE-INDEX.md に「買取」専用行は無い（`grep -n "買取\|ADR-157\|マスタ" docs/adr/FEATURE-INDEX.md` は在庫・商品マスタ行のみ）。

## 事実（file:line、すべて worktree で再確認）

### A. 旧解析（legacy）の候補集合と照合
- backend/app/services/tcg_analyzer_svc.py:83 — `SELECT id FROM public.products WHERE is_active = TRUE`（候補は有効商品の全件。カテゴリ・作品による読み込み時除外なし）
- backend/app/services/tcg_analyzer_svc.py:68 — `load_lookup_maps`
- backend/app/services/tcg_analyzer_svc.py:156 — `load_product_kubun_type_map`
- backend/app/services/tcg_analyzer_svc.py:177 — `load_product_keywords`（検索語・除外語）
- backend/app/services/tcg_analyzer_svc.py:415 — `load_work_master`
- backend/app/services/tcg_analyzer_svc.py:550 — `match_pid_with_work`（本番の判定）
- backend/app/services/tcg_analyzer_svc.py:924 — `load_normalization_rules`
- backend/app/services/tcg_work_comparison_svc.py:216 — `match_item`（`match_pid_with_work` を呼ぶ。試運転で再利用）
- backend/app/services/tcg_work_comparison_svc.py:200 — `old_work`（保存済み resolved_work_id があれば使い、無ければ `resolve_work_evidence`）
- backend/app/services/tcg_work_comparison_svc.py:230 — `compare_snapshot`（呼び出し口なし。本 PR でも呼ばない）
- backend/app/services/tcg_work_reference.py:78-100 — `load_work_reference`。:99-100 で有効商品の work_id が有効作品に無いと `ValueError("Active product has no active work reference")`
- backend/app/tasks/tcg_extraction.py:387 — `REFERENCE_CHANGED`（解析中にマスタが変わった場合）
- backend/app/services/tcg_analyzer_svc.py:1259 — `Work reference changed; re-extraction required`
- backend/app/services/buyback_scraper/product_matcher.py:19,64 — 買取マッチャーも同じ照合関数・同じ検索語テーブルを使う（関門4は本 PR の範囲外）

### B. 新解析（new）— Gemini＝書き写し／システム＝判定
- backend/app/services/extraction_judgement_svc.py:22 — `normalize_for_match`
- backend/app/services/extraction_judgement_svc.py:46 — `block_text`（行範囲で原文を切り出す）
- backend/app/services/extraction_judgement_svc.py:63 — `ProductEntry`／:73 `MatchResult`（status = matched / ambiguous / unmatched）
- backend/app/services/extraction_judgement_svc.py:115 — `match_product`（AND ワード・品番。作品による絞り込みなし）
- backend/app/services/extraction_shadow_svc.py:63 — `load_product_entries`（有効商品の全件を ProductEntry で読む。試運転で再利用）
- docs/handoff/gemini-extract-role-split/design.md:25 — 「渡すのは、共通の指示・その仕入元のルール・原文だけで、マスタは渡さない」
- migrations/20260928_110000_create_extraction_shadow_tables.sql — `extraction_shadow_runs`／`extraction_shadow_results`（line_start・line_end あり、原文は持たない。原文は extraction_jobs → source_messages.raw_text で引く）

### C. 過去データの所在
- migrations/20260921_110000_pipeline_tables_public.sql:20-30 — `public.source_messages`（`raw_text` NOT NULL、`line_posted_at`・`received_at`・`created_at`、`is_active`、`superseded_by`）
- 同ファイル:80-90 — `public.extraction_jobs`（`source_message_id`、`status`）
- 同ファイル:93-108 — `public.extraction_items`（`line_start`・`line_end`・`raw_product_name`・`raw_unit`・`raw_state`・`raw_memo`・`raw_work_name`・`raw_work_source_line_span`・`resolved_work_id`）

### D. CSV 取り込み・キーワード品質
- backend/app/services/tcg_product_import_svc.py:41 — `CSV_COLUMNS`（10列）／:114 `split_keywords`／:132 `parse_rows`（同期関数。試運転で再利用）
- backend/app/services/tcg_product_import_svc.py:171 — `load_lookup_maps` は `async def`（AsyncSession 専用。同期の試運転からは呼べないため、work_code→id と category→kubun の 2 本だけ小さな SELECT を試運転側に持つ）
- backend/app/services/tcg_keyword_lint.py:63 — `check_r3_shared_kw`（正規化 = `collapse_product_spaces(normalize_en(kw))`。関門1 はこの正規化を使う）
- backend/scripts/check_keyword_quality.py:51 — `FROM {TCG_SCHEMA}.tcg_products`（旧テーブル名を読む。本 PR は変更しない）
- backend/app/routers/tcg_shadow_review.py:69 — `keyword-preview`（既存商品へのワード 1 件追加のみ。新商品追加は試せない）
- backend/app/routers/buyback_alerts.py:60 — `SET LOCAL app.is_operator = 'true'`（public 読み取りの前例）

## 不明点・未確認
- 【未確認】「ポケモンの search_keywords が 0 件」は TEXT 列 `products.search_keywords` と `product_search_keywords` のどちらを数えた値か。実 DB 未接続のため本便では確認しない（登録便の関門1 の前に本番で数え直す）。
- 【未確認】新解析の「Gemini v7 が実際に切るブロックの行範囲」は Gemini を呼ばない試運転では再現できない。原文集団（b）は extraction_items の行範囲を代用ブロックとして `block_text` に渡す（design.md 参照）。
- 【未確認】shadow 試運転が停止中であること（#3864）は設計者からの伝達。本便では確認していない。
- 【未確認】実 DB に対する試運転スクリプトの実行（本便はコードのみ。DB 未接続）。
