# recon: Gemini thoughts_token_count を出力トークン・費用に含める

## 事実（設計者検証済み・実装者は grep で再確認）

### 公式料金表
- https://ai.google.dev/gemini-api/docs/pricing
  - gemini-3.1-flash-lite: `Output price (including thinking tokens) $1.50`
  - gemini-3.5-flash-lite: 同様に `(including thinking tokens)` 表記
  - → Gemini の出力単価は thinking tokens（内部思考トークン）を含む。

### google-genai SDK の usage_metadata 定義
- google-genai SDK の types.py: `total_token_count = prompt_token_count + candidates_token_count + tool_use_prompt_token_count + thoughts_token_count`
- → `candidates_token_count` は thoughts を**含まない**別カウンタ。

### 現状の実装（origin/main、本 recon 時点で再確認）
`git grep -n candidates_token_count origin/main -- backend/app` の結果:
- `backend/app/services/gemini_extraction_svc.py:447` (`call_gemini_extraction` 内)
- `backend/app/services/gemini_extraction_svc.py:526` (`call_gemini_raw_copy` 内)
- `backend/app/services/inventory_parser_llm.py:318` (`parse_with_gemini` 内)
- `backend/app/services/message_translator.py:426` (`_call_gemini_translation` 内)

いずれも `output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)` の形で
`candidates_token_count` のみを出力トークンとして読んでおり、`thoughts_token_count` は
本 recon 時点で backend 全体で 0 参照だった（`git grep -n thoughts_token_count backend/app` = 該当なし）。

`calculate_cost` は `backend/app/services/llm_budget.py:130` にあり、
`output_tokens * pricing["output_per_token"]` で費用計算する。
つまり現状は thinking tokens 分の費用が `cost_usd` / `tenant_llm_budgets.current_month_usd` に
計上されない（公式料金表と齟齬）。

### 直近の関連コミット履歴（4ファイル + llm_budget.py）
```
8b25bb96f Merge branch 'main' into release/remove-legacy-supplier-rule-paths
275beffa8 Merge remote-tracking branch 'origin/main' into release/remove-legacy-supplier-rule-paths
fd65e460b chore: remove unused gemini-egress tunnel, record ADR-080 drift, fix model docstring
aebaf2dd5 refactor: remove supplier_prompts and skip_condition registration paths (PR-CLEAN, staged 2026-09-28)
df1d08162 fix: read Gemini output tokens via candidates_token_count, not response_token_count
```
直近の関連修正 (df1d08162) は「response_token_count という誤属性名から candidates_token_count へ修正」
した回であり、今回の thoughts 加算とは別論点（属性名の正しさ vs 課金範囲の正しさ）。

## 未確認
- gemini-3.1-flash-lite / gemini-3.5-flash-lite が既定（temperature=0 呼び出し時）で
  thinking を行うか、常に thoughts_token_count > 0 になるかは公式資料に明記なし。
  → 本修正は「thoughts が存在すれば加算する」形にしており、0 の場合は従来と同じ値になる
  （後方互換・過剰課金リスクなし）。
