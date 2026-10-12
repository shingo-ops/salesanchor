# Recon: gemini-prompt-d（指示書 d：まとめ書きの行の決まりを見た目で確かめられる形にする）

- この文書は何か（1行）: 指示書 d を足す前に、触る道具（prompt_ab）と比べる相手（指示書 c）の今の姿を事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-prompt-d/design.md
- 起点: origin/main = 2361373d954956abe72ca78376258d17706d592e（worktree 作成時の HEAD、2026-10-06）。行番号はこの時点のもの。評価・提案は書かない。社外秘の仕入元名・原文は書かない。
- 設計仕様書（あるべき姿）: 該当なし（比較試験の指示書の追加。本番の経路・データ構造・マスタに触れない）。

## 既存ADRの検索
- 実行: git grep -n -i -E "raw_copy|prompt_ab" -- docs/adr → 0件（該当なし）。
- 設計が参照する ADR（ファイルの実在を ls docs/adr で確認）
  - docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
  - docs/adr/ADR-1004-llm-usage-ledger.md
  - docs/adr/ADR-085-supplier-prompts.md
  - docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
- 前の版: docs/handoff/gemini-v102/design.md、docs/handoff/gemini-omit-supplier-field/design.md（ADR ではない）。

## prompt_ab の --prompt-name（file:line）
- backend/app/tools/prompt_ab.py:9（起動の書式に --prompt-name raw_copy_v9_NAME|raw_copy_v101_NAME）
- backend/app/tools/prompt_ab.py:78-82（_PROMPT_NAME_RES。v101・v102 は V101_PROMPT_NAME_RE）
- backend/app/tools/prompt_ab.py:457（p.add_argument("--prompt-name", ...)。v102 は既定 raw_copy_v101_c と書かれている）
- backend/app/services/gemini_raw_copy_v101.py:27（V101_PROMPT_NAME_RE = ^raw_copy_v101_[a-z0-9_]+$）
- 実物の確認: backend/app/prompts/ には raw_copy_v101_a.txt・b.txt・c.txt があり、d.txt は無い。

## resolve_prompt_path（file:line）
- backend/app/tools/prompt_ab.py:270-280
  - 271: 説明文（形が違う・ファイルが無いときは ValueError）
  - 272-274: config に対応する正規表現が無ければ ValueError
  - 275-276: 名前が正規表現に fullmatch しなければ ValueError
  - 277-280: _PROMPTS_DIR / f"{prompt_name}.txt" が無ければ ValueError、あれば Path を返す
- backend/app/tools/prompt_ab.py:283-290（_load_prompt_text が resolve_prompt_path を使う）
- 既存テスト: backend/tests/test_prompt_ab.py:409（raw_copy_v9_trial1 の解決）、backend/tests/test_prompt_ab.py:583-585（v101 の a・b の存在）

## 指示書 c のまとめ書きの節（backend/app/prompts/raw_copy_v101_c.txt）
- :25【lines に入れない行（どの件にも入れない）】
- :26 投稿の冒頭・末尾の連絡
- :27 複数の商品の上にまとめて置かれた行（言葉と例で示すのみ。見た目で確かめる手順の記述は無い）
- :28 親の見出しの行
- 例の説明文（まとめ書きの行を入れない旨）: :65、:77、:130、:153
