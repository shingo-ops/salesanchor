# Recon: gemini-v10（Gemini は行番号・価格・数量だけ、ほかはシステムが原文から取る）

- この文書は何か（1行）: v10 を作る前に、今のコードと設計の前提を事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-v10/design.md
- 起点: origin/main = a34381937 を含む worktree 作成時の HEAD（PR #3973 のマージ）。行番号は origin/main 時点のもの（prompt_ab.py は本 PR で変更するため）。出典: git show origin/main:<path> と grep -n（2026-10-05）。評価・提案は書かない。

## 既存ADRの検索
- 実行: git grep -n -i -E "書き写し|raw.copy|prompt_ab" -- docs/adr → 0件（grep 済み・該当なし）。
- docs/adr/FEATURE-INDEX.md を同じ語で grep → 0件。
- 設計が参照する ADR（ファイルの実在を ls docs/adr で確認）
  - docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
  - docs/adr/ADR-1004-llm-usage-ledger.md
  - docs/adr/ADR-085-supplier-prompts.md
  - docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
- 関連する先行 handoff（ADR ではない）: docs/handoff/gemini-v8/design.md §6、docs/handoff/gemini-v9/design.md §5-1、docs/handoff/gemini-v9-trial1/design.md §3。

## 設計 §2 の事実（設計書に記載の試算は費用0円・手元のみの記録。ここには値だけを書き、仕入元名・原文は書かない）
- 状態・単位を原文の行から取った場合の一致：162/162件。発送：164/164件。見出しからの商品名：157/164件。
- trial1（PR #3967）の結果：その件だけの行が範囲外に置かれた件 31件 → 0件。
- 本番の判定の材料: backend/app/services/extraction_shadow_svc.py:251-317（_judge_block）。
  - 単位・状態・ステータスは Gemini の写し（block_item["raw_unit"]・["raw_state"]）を使う（同:265-275 付近）。
  - 発送・商品照合・価格数量は原文のブロックを使う。

## 触る・使う関数の事実（file:line、origin/main）
- 呼び出し: backend/app/services/gemini_raw_copy_v8.py:165-175（call_gemini_raw_copy_v8。response_schema 引数で型を差し替えられる）、同:193（response_json_schema に渡す）。
- 受け取りの部品（v10 が import して使う）: backend/app/services/gemini_raw_copy_v8.py:227（_is_int）、同:285（_load_items）。
- v9 の型の作り方（変更しない）: backend/app/services/gemini_raw_copy_v9.py:35（V9_RESPONSE_SCHEMA）、同:145（parse_v9_response）。
- 道具の分岐（変更する）
  - backend/app/tools/prompt_ab.py:171（_parse。config で v7/v9/v8 を分ける）
  - backend/app/tools/prompt_ab.py:201（_load_prompt_text。--prompt-name は v9 のみ）
  - backend/app/tools/prompt_ab.py:214（_print_dry_run）
  - backend/app/tools/prompt_ab.py:234（run_ab）、同:276（V9 の型を渡す箇所）
  - backend/app/tools/prompt_ab.py:326-329（parse_args。--config の choices は v7|v8|v9）
- マスタの読み込み（既存の関数をそのまま呼ぶ）
  - backend/app/services/tcg_analyzer_svc.py:646（load_condition_entries）
  - backend/app/services/tcg_analyzer_svc.py:1094（load_status_master）
  - backend/app/services/tcg_analyzer_svc.py:68（load_lookup_maps。6つ目が unit_alias_to_info）
  - 本番での呼び方: backend/app/services/extraction_shadow_svc.py:421
- 判定の関数（そのまま呼ぶ）
  - backend/app/services/tcg_analyzer_svc.py:759（resolve_unit_v2）
  - backend/app/services/tcg_analyzer_svc.py:787（resolve_condition_v2）
  - backend/app/services/tcg_analyzer_svc.py:1138（resolve_status_v2）
  - backend/app/services/extraction_judgement_svc.py:515（resolve_price_quantity）
  - backend/app/services/extraction_judgement_svc.py:333（order_from_pattern）
  - 仕入元の並びの出どころ: backend/app/services/extraction_shadow_svc.py:422（supplier_context の extraction_order_pattern）

## 触るファイル
- backend/app/services/gemini_raw_copy_v10.py（新規）
- backend/app/prompts/raw_copy_v10.txt（新規。設計者が書いた本文をそのまま置く）
- backend/app/tools/prompt_ab.py
- backend/tests/test_gemini_raw_copy_v10.py（新規）
- backend/tests/test_prompt_ab.py
- docs/handoff/gemini-v10/design.md（新規）
- docs/handoff/gemini-v10/recon.md（新規）
- .claude-pipeline/active-work.d/release-gemini-v10-line-only.md（新規）

## 触らないファイル
- backend/app/services/gemini_raw_copy_v8.py・gemini_raw_copy_v9.py
- backend/app/prompts/raw_copy_v8.txt・raw_copy_v9.txt・raw_copy_v9_trial1.txt
- 本番の抽出経路（tcg_extraction・extraction_shadow_svc・gemini_extraction_svc）
- DB の構造・マスタの中身・migrations・deploy.yml・scripts/・フロントエンド
