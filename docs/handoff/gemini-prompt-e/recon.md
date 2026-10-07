# Recon: gemini-prompt-e（指示書 e：手順を上から順に実行する形に組み直す）

- この文書は何か（1行）: 指示書 e を足す前に、触る道具（prompt_ab）と比べる相手（指示書 c）の今の姿を事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-prompt-e/design.md
- 起点: origin/main = 9c1b457ced651019eddcf74092a7f91f1923eea2（worktree 作成時の HEAD、2026-10-06）。行番号はこの時点のもの。評価・提案は書かない。社外秘の仕入元名・原文は書かない。
- 設計仕様書（あるべき姿）: 該当なし（比較試験の指示書の追加。本番の経路・データ構造・マスタに触れない）。

## 既存ADRの検索
- 実行: git grep -n -i -E "raw_copy|prompt_ab" -- docs/adr → 0件（該当なし）。
- 設計が参照する ADR（ファイルの実在を ls docs/adr で確認）
  - docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
  - docs/adr/ADR-1004-llm-usage-ledger.md
  - docs/adr/ADR-085-supplier-prompts.md
  - docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
- 前の版: docs/handoff/gemini-prompt-d/design.md（ADR ではない）。

## prompt_ab の --prompt-name（file:line）
- backend/app/tools/prompt_ab.py:9（起動の書式に --prompt-name raw_copy_v9_NAME|raw_copy_v101_NAME）
- backend/app/tools/prompt_ab.py:78-82（_PROMPT_NAME_RES。v101・v102 は V101_PROMPT_NAME_RE）
- backend/app/tools/prompt_ab.py:457（p.add_argument("--prompt-name", ...)。v102 は既定 raw_copy_v101_c と書かれている）
- backend/app/services/gemini_raw_copy_v101.py:27（V101_PROMPT_NAME_RE = ^raw_copy_v101_[a-z0-9_]+$）
- 実物の確認: backend/app/prompts/ には raw_copy_v101_a.txt・b.txt・c.txt・d.txt があり、e.txt は無い（この PR で足す）。

## resolve_prompt_path（file:line）
- backend/app/tools/prompt_ab.py:270-280
  - 271: 説明文（形が違う・ファイルが無いときは ValueError）
  - 272-274: config に対応する正規表現が無ければ ValueError
  - 275-276: 名前が正規表現に fullmatch しなければ ValueError
  - 277-280: _PROMPTS_DIR / f"{prompt_name}.txt" が無ければ ValueError、あれば Path を返す
- backend/app/tools/prompt_ab.py:283-290（_load_prompt_text が resolve_prompt_path を使う）
- 既存テスト: backend/tests/test_prompt_ab.py:409（raw_copy_v9_trial1 の解決）、backend/tests/test_prompt_ab.py:583-585（v101 の a・b の存在）、backend/tests/test_prompt_ab.py:588-596（d の解決）

## 指示書 c の構成（backend/app/prompts/raw_copy_v101_c.txt）
- 見出しは【】で種類ごとに並べる書き方。番号付きの手順は無い。
  - :6【1件の決め方】
  - :13【lines に入れる行】
  - :19【価格と価格の間の行】
  - :25【lines に入れない行（どの件にも入れない）】（:26 冒頭・末尾の連絡、:27 まとめて置かれた行、:28 親の見出しの行）
  - :30【各欄】
  - :35【例】
- 「# 役割と目的」の見出しは無い。
