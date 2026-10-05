# Recon: gemini-v9-trial1（比較試験の道具で v9 の試験版指示書を指定できるようにする）

- この文書は何か（1行）: 道具を変える前に、今のコードがどうなっているかを事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-v9-trial1/design.md
- 起点: origin/main = 225c0c0ad292a13173a7b1bef5de8f484215faae（worktree 作成時の HEAD。PR #3964 のマージ）
- 出典: worktree 上で git show origin/main:<path> と grep -n で行番号を確認した（2026-10-05）。評価・提案は書かない。

## 既存ADRの検索
- 実行: git grep -n -i -E "prompt_ab|書き写し|raw_copy" -- docs/adr → 出力なし（該当0件）。
- docs/adr/FEATURE-INDEX.md を同じ語で grep → 該当0件。
- 関連する先行 handoff（ADR ではない）: docs/handoff/gemini-v8/design.md §6、docs/handoff/gemini-v9/design.md §5-1。

## 設計 §2 の事実（file:line）
- v9 の指示書は固定で読まれる。
  - /Users/tanizawashingo/worktrees/salesanchor/release-prompt-ab-prompt-name/backend/app/services/gemini_raw_copy_v9.py:18（_PROMPT_PATH = .../prompts/raw_copy_v9.txt）
  - /Users/tanizawashingo/worktrees/salesanchor/release-prompt-ab-prompt-name/backend/app/services/gemini_raw_copy_v9.py:38-39（load_v9_prompt）
  - /Users/tanizawashingo/worktrees/salesanchor/release-prompt-ab-prompt-name/backend/app/tools/prompt_ab.py:186-192（変更前の _load_prompt_text。v9 は load_v9_prompt()）
- 別の指示書を指定する引数は無い。
  - /Users/tanizawashingo/worktrees/salesanchor/release-prompt-ab-prompt-name/backend/app/tools/prompt_ab.py:306-316（変更前。--config は v7|v8|v9 の選択のみ）
- prompt_ab は本番の表に書かず、費用の台帳だけに書く。
  - /Users/tanizawashingo/worktrees/salesanchor/release-prompt-ab-prompt-name/backend/app/tools/prompt_ab.py:8-10（変更前）
- v9 は本番の経路から呼ばれない。
  - /Users/tanizawashingo/worktrees/salesanchor/release-prompt-ab-prompt-name/backend/app/services/gemini_raw_copy_v9.py:5

## 触るファイル
- backend/app/tools/prompt_ab.py
- backend/app/prompts/raw_copy_v9_trial1.txt（新規）
- backend/tests/test_prompt_ab.py
- docs/handoff/gemini-v9-trial1/design.md（新規）
- docs/handoff/gemini-v9-trial1/recon.md（新規）
- .claude-pipeline/active-work.d/release-prompt-ab-prompt-name.md（新規）

## 触らないファイル
- backend/app/services/gemini_raw_copy_v8.py・gemini_raw_copy_v9.py
- backend/app/prompts/raw_copy_v9.txt・raw_copy_v8.txt
- 本番の抽出経路（tcg_extraction・extraction_shadow_svc・gemini_extraction_svc）
- DB・migrations・deploy.yml・scripts/
