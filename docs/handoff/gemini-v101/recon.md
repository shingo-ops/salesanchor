# Recon: gemini-v101（Gemini は商品ごとの行番号・価格・数量だけ／ラベル無し）

- この文書は何か（1行）: v10.1 を作る前に、今のコードと設計の前提を事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-v101/design.md
- 起点: origin/main = 41d65666f8ac6b8b8a9a6b7116a88a743c48a4c3（PR #3980 のマージ）の worktree 作成時の HEAD。行番号は origin/main 時点のもの（backend/app/tools/prompt_ab.py は本 PR で変更するため）。出典: git show origin/main:<path> と grep -n（2026-10-05）。評価・提案は書かない。
- 設計仕様書（あるべき姿）: 該当なし（比較試験の道具の追加。本番の経路・データ構造・マスタに触れない）。

## 既存ADRの検索
- 実行: git grep -n -i -E "書き写し|raw.copy|prompt_ab" -- docs/adr → 0件（grep 済み・該当なし）。
- docs/adr/FEATURE-INDEX.md を同じ語で grep → 0件。
- 設計が参照する ADR（ファイルの実在を ls で確認）
  - docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
  - docs/adr/ADR-1004-llm-usage-ledger.md
  - docs/adr/ADR-085-supplier-prompts.md
  - docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
- 関連する先行 handoff（ADR ではない）: docs/handoff/gemini-v10/design.md、docs/handoff/gemini-v9-trial1/design.md §3。

## 設計 §2 の事実
- 試験の数値（147投稿・117投稿・2,222件・迷う行 51行/23行・217件中213件）は設計書に記載。元の記録は手元のみ（社外秘。仕入元名・原文はここに書かない）。

## 触る・使う関数の事実（file:line、origin/main）
- v10（変更しない・部品を流用）
  - backend/app/services/gemini_raw_copy_v10.py:50（load_v10_prompt）、同:179-181（_EDGE_CHARS・_SHIP_WORD_RE・_BRACKET_RE）
  - 補助関数: 同:188（_unit_aliases）、同:259（_strip_price_line_name）、同:247（_remove_stock_words）
  - 取り出し本体: 同:360（extract_v10_items）
- 受け取りの部品: backend/app/services/gemini_raw_copy_v8.py:227（_is_int）、同:285（_load_items）、同:165（call_gemini_raw_copy_v8。response_schema 引数で型を差し替えられる）
- 判定の関数（そのまま呼ぶ）
  - backend/app/services/tcg_analyzer_svc.py:759（resolve_unit_v2）
  - backend/app/services/tcg_analyzer_svc.py:787（resolve_condition_v2）
  - backend/app/services/tcg_analyzer_svc.py:1138（resolve_status_v2）
  - backend/app/services/extraction_judgement_svc.py:515（resolve_price_quantity）
  - 状態の単品・空箱の除外に使う定数: backend/app/services/tcg_empty_box_rules.py:6-7（EMPTY_CODE・EMPTY_CANONICAL）
- マスタの読み込み（既存の関数をそのまま呼ぶ）: backend/app/services/tcg_analyzer_svc.py:646（load_condition_entries）、同:1094（load_status_master）
- 道具の分岐（変更する）
  - backend/app/tools/prompt_ab.py:68（_PROMPT_NAME_RE。--prompt-name は v9 のみ）
  - backend/app/tools/prompt_ab.py:180（_parse）、同:196（_load_v10_masters）、同:223（resolve_prompt_path）、同:233（_load_prompt_text）、同:248（_print_dry_run）
  - backend/app/tools/prompt_ab.py:268（run_ab）、同:276（row_prompt_name）、同:311（schemas）
  - backend/app/tools/prompt_ab.py:363-388（parse_args。--config の choices は v7|v8|v9|v10）
- 既存のテスト: backend/tests/test_gemini_raw_copy_v10.py、backend/tests/test_prompt_ab.py（v10 の fixture: v10_fakes）

## 指示書
- backend/app/prompts/raw_copy_v101_a.txt・raw_copy_v101_b.txt は設計者（Opus）が書いた本文をそのまま置く（cmp で一致を確認）。
