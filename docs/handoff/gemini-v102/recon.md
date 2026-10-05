# Recon: gemini-v102（v10.1 の残った誤りの確認と直し F1〜F6）

- この文書は何か（1行）: v10.2 を作る前に、設計 §2 と、触るファイルの今の姿を事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-v102/design.md
- 起点: origin/main = 3f4dbbdf95d406b97062ea2da74d25c4eadecdf6（PR #3984 のマージ）の worktree 作成時の HEAD。行番号は origin/main 時点のもの（git show origin/main:<path> と grep -n。2026-10-05）。評価・提案は書かない。
- 設計仕様書（あるべき姿）: 該当なし（比較試験の道具の追加。本番の経路・データ構造・マスタに触れない）。

## 既存ADRの検索
- 実行: git grep -n -i -E "書き写し|raw.copy|prompt_ab" -- docs/adr → 0件（該当なし）。
- docs/adr/FEATURE-INDEX.md を同じ語で grep → 0件（該当なし）。
- 設計が参照する ADR（ファイルの実在を ls で確認）
  - docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
  - docs/adr/ADR-1004-llm-usage-ledger.md
  - docs/adr/ADR-085-supplier-prompts.md
  - docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
- 前の版: docs/handoff/gemini-v101/design.md、docs/handoff/gemini-v101/recon.md（ADR ではない）。

## 設計 §2 の事実
- 試験の数値（147投稿・19投稿×2回・R1〜R6 の件数）は設計書に記載。元の記録は手元のみ（社外秘。仕入元名・原文はここに書かない）。
- 誤りの形（設計 §2 の再掲。原文は書かない）
  - R1: 名前の無い価格の行の件に、前の価格の行の名前が付かない（2投稿・7件）。
  - R2: 親の見出しが9件の lines に入り、発送が親の見出しの文字になる（2投稿・18件）。
  - R3: まとめ書きの行が名前に入る（1投稿・1件）。
  - R4: 数量の文字に数字が無い（1投稿・3件）。
  - R5: 末尾の連絡の行が最後の件の lines に入る。possible_missing_item の範囲が末尾まで広がる（1投稿）。
  - R6: quantity_not_in_text が、カンマ付きの数を原文に無いと判定した（10件・すべて誤検知）。

## 触る関数の事実（file:line、origin/main）
- backend/app/services/gemini_raw_copy_v101.py（変更する）
  - :24 DEFAULT_V101_PROMPT_NAME、:25 V101_PROMPT_NAME_RE
  - :38 _SHIP_RE（発送|出荷|入荷|発売|着）
  - :249 line_role、:264 assign_roles、:316 _shared_line_numbers、:347 _neighbors、:423 reassign_ambiguous
  - :498 _price_line_name、:550 _product_name、:560 _is_alias_only_line、:643 _ship_for
  - :663 _quantity_not_in_text（カンマは quantity 側だけ除く。原文側は除かない）
  - :672 _extract_one（name・quantity_not_in_text・価格数量を作る）
  - :707 _possible_missing_lines（範囲は最初の件の最初の行〜最後の件の最後の行）
  - :717 extract_v101_items（引数 reassign。戻り値は (件ごとの辞書, {"possible_missing_item": [...]})）
- backend/app/tools/prompt_ab.py（変更する）
  - :76 _PROMPT_NAME_RES、:192 _parse、:233 _v101_row_fields、:254 resolve_prompt_path、:267 _load_prompt_text
  - :282 _master_row_fields、:290 _print_dry_run、:318 row_prompt_name、:355 schemas、:410 --config の choices（v7|v8|v9|v10|v101）
- v10.1（PR #3981）の出力（--config v101）は変えない。テスト: backend/tests/test_gemini_raw_copy_v101.py、backend/tests/test_prompt_ab.py、backend/tests/test_gemini_raw_copy_v10.py。
- 本番の経路から v101 は呼ばれない（gemini_raw_copy_v101.py の docstring :6）。

## 指示書
- backend/app/prompts/raw_copy_v101_c.txt は設計者（Opus）が書いた本文をそのまま置く（cmp で一致を確認）。既存の raw_copy_v101_a.txt・raw_copy_v101_b.txt は変えない。
