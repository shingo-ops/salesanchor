# recon: v102 の既定の指示書を raw_copy_v101_f_ct に切り替え

## 事実（根拠つき）

- 既定の指示書 key の決定点は1か所: `/Users/tanizawashingo/salesanchor/backend/app/services/line_analysis_v102_svc.py:53`（`V102_PROMPT_KEY`）。
  - 本番: `/Users/tanizawashingo/salesanchor/backend/app/services/line_analysis_v102_svc.py:393-394`（`run_v102_extraction` が `load_prompt_from_db` と `build_prompt_version` に渡す）
  - 試作版: `/Users/tanizawashingo/salesanchor/backend/app/tools/prompt_ab.py:304`（`V102_PROMPT = V102_PROMPT_KEY`）、`/Users/tanizawashingo/salesanchor/backend/app/tools/prompt_ab.py:473-474`
- key を保持する環境変数・migration はない: `git grep -n "raw_copy_v101_f_c" -- ':!backend' ':!docs'` の結果は 0 件。
- `V102_ENGINE_VERSION`（`/Users/tanizawashingo/salesanchor/backend/app/services/line_analysis_v102_svc.py:51`）は同ファイル :753 で analysis_results.engine_version に書くだけ。`git grep -n -E "V102_ENGINE_VERSION|v102-f_c" -- . ':!backend/tests'` で、テスト以外にこの文字列を比較する箇所はない（docs/handoff/v102-prod-switch/ の過去記録のみ）。
- `backend/app/services/gemini_raw_copy_v101.py` の `DEFAULT_V102_PROMPT_NAME` は変更しない。
- 残すテスト内の文字列: `backend/tests/test_v102_human_decisions.py:121,232` は偽データの prompt_version 文字列で、既定 key とは無関係のため変更しない。

## 本番 DB 事前確認（読み取りのみ・2026-10-11）

```
raw_copy_v101_f_c|t|1|d2a6447faf0842dad134337a302ed9c9bb7b8ac9c8731bc25860a56b9d037d21
raw_copy_v101_f_ct|t|1|fe50593fa362da213e33663f85110381a6f3f97465553443e87ae0f0df8515fd
```
（列: prompt_key / is_active / version / 本文の sha256。本文そのものはリポジトリに置かない）

## 既存 ADR 検索

- `git grep -il "prompt" docs/adr/ | head` → ADR-039, 042, 048, 050, 051, 053, 056, 085, 1004, 154。このうち指示書の DB 管理に関わるのは ADR-085（supplier-prompts）。key の既定値を規定した ADR はない。
- `docs/adr/FEATURE-INDEX.md` で LINE解析 / v102 を grep: 該当行なし（既定 key を定めた ADR はなし）。
- 関連の正本: `/Users/tanizawashingo/salesanchor/docs/specs/line-analysis-tuning/README.md`
