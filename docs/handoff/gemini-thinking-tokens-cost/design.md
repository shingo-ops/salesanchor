# design: Gemini thoughts_token_count を出力トークン・費用に含める

recon: docs/handoff/gemini-thinking-tokens-cost/recon.md

## 目的
Gemini API の実際の課金は `candidates_token_count + thoughts_token_count`（公式料金表の
"including thinking tokens" 表記どおり）だが、現行実装は `candidates_token_count` のみを
`output_tokens` として記録・課金計算している。これにより `tenant_llm_budgets.current_month_usd`
や `extraction_attempts.output_tokens` / `cost_usd` が実際の Gemini 請求額より過小になりうる。
本修正は「記録される output_tokens = 実際の課金対象トークン数」に一致させる。

## 対象と対象外
- 対象: `backend/app/services/llm_budget.py`（新ヘルパー追加）、
  `backend/app/services/gemini_extraction_svc.py`（2箇所）、
  `backend/app/services/inventory_parser_llm.py`（1箇所）、
  `backend/app/services/message_translator.py`（1箇所）
- 対象外:
  - DB スキーマ変更なし。`extraction_attempts.output_tokens` / `cost_usd` 列の**意味**が
    「candidates のみ」→「課金対象合計（candidates + thoughts）」に変わるが、列自体・型は不変。
  - `LLM_PRICING` の単価は変更しない（単価は元々 thinking tokens 込みの公式単価のまま）。
  - `check_budget` / `record_cost` / `calculate_cost` のロジックは変更しない
    （渡される `output_tokens` の値が変わるだけ）。

## 変更前後
```python
# Before (4箇所同型)
output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)

# After
output_tokens = billable_output_tokens(usage)

# llm_budget.py に新規追加
def billable_output_tokens(usage: object) -> int:
    if usage is None:
        return 0
    candidates = int(getattr(usage, "candidates_token_count", 0) or 0)
    thoughts = int(getattr(usage, "thoughts_token_count", 0) or 0)
    return candidates + thoughts
```

## 影響範囲（呼び出し元を全走査）
`billable_output_tokens` を呼ぶ4関数の呼び出し元:
- `call_gemini_extraction`（backend/app/services/gemini_extraction_svc.py 内）: TCG 商品抽出パイプライン本流。
  `recorder.on_response(output_tokens=...)` 経由で `extraction_attempts.output_tokens` に記録。
- `call_gemini_raw_copy`（backend/app/services/gemini_extraction_svc.py 内）: raw_copy 試運転経路（PR-C）。
  戻り値 dict の `output_tokens` を呼び出し側が使用。
- `parse_with_gemini`（backend/app/services/inventory_parser_llm.py 内）: 在庫メッセージ LLM フォールバック解析。
  戻り値 `LLMParseResult.output_tokens` → 呼び出し側 `inventory_parser.parse_inventory_message`
  が `record_cost` に渡す（コード上は本ファイル対象外、値の型・呼び出し方は不変）。
- `_call_gemini_translation`（backend/app/services/message_translator.py 内、行426付近）: 受信/送信翻訳。
  戻り値 tuple の3要素目 `output_tokens` を呼び出し側が `record_cost` に渡す。

いずれも「関数が返す output_tokens の数値が increase しうる」だけで、シグネチャ・呼び出し方・
下流の型は不変。`thoughts_token_count` が存在しない/None の環境では従来と同じ値を返す
（後方互換）。

## 影響が及ぶ運用面
- `tenant_llm_budgets.current_month_usd` の増加ペースが thoughts 分だけ増える可能性
  （hard_stop の発火が早まる方向 = 予算超過を見逃すリスクは減る、資金超過リスクは増えない）。
- `extraction_attempts.cost_usd` が実際の Gemini 請求額に近づく（過小評価の是正）。

## 戻し方
本 PR を revert すれば `output_tokens = candidates_token_count` の従来挙動に戻る。
DB マイグレーション・列削除は伴わないため revert は単純。

## 検証観点
| 基準 | 検証方法 |
|---|---|
| ① 新規テスト（billable_output_tokens 単体 + 4呼び出し元の1つでの統合確認）が緑 | `pytest tests/test_llm_budget.py tests/test_tcg_gemini_extraction.py tests/test_inventory_parser_llm.py tests/test_message_translator.py --no-cov` |
| ② candidates_token_count を直接読むのは backend/app/services/llm_budget.py の billable_output_tokens のみ | `git grep -n candidates_token_count backend/app` の結果が backend/app/services/llm_budget.py の定義・docstring 以外に存在しないこと |
| ③ 反映後の本番 attempt で output_tokens が反映前と同等以上のレンジ、cost_usd が `input*0.25e-6 + output*1.50e-6`（gemini-3.1-flash-lite の場合）と一致 | 反映後の `extraction_attempts` 実レコードを PO 確認環境で抽出し手計算と突合（未実施・本 PR は実装のみ） |

## 外部・過去事例の参照と我々への応用
公式料金ページ（https://ai.google.dev/gemini-api/docs/pricing）の単価表記自体が
「Output price (including thinking tokens)」と明記しており、これは Google が一次情報として
提供する仕様であるため、外部の導入事例調査は不要と判断した。我々への応用は「単価表記を
文字どおり信じ、SDK 側の usage_metadata 定義（candidates と thoughts が別カウンタ）と
突き合わせて計上漏れを機械的に特定する」というアプローチのみで足り、他社事例の要否は
PO 承認（ADR-135 の release ブランチ待機方針）が律速する。

## 維持の仕組み
- 課金対象トークン数の計算ロジックを `billable_output_tokens` という単一箇所に集約したため、
  将来 Gemini SDK に新しいトークン種別（例: `tool_use_prompt_token_count` が output 側に
  再分類される等）が追加されても、変更箇所は1関数 + 4呼び出し元の置換のみで済む。
- backend/tests/test_llm_budget.py の `TestBillableOutputTokens` が None / thoughts欠損 /
  thoughts=None / candidates+thoughts の4ケースを固定化しており、回帰時に即検出できる。
- 守り手: backend/tests/test_llm_budget.py::TestBillableOutputTokens（CI で毎回実行）

## ADR参照
- ADR-135（main マージ＝本番投入可の宣言）: 本変更は課金計算ロジックの是正であり
  `migrations/` を含まないが、`tenant_llm_budgets` の課金額に影響するため release ブランチで
  PO GO 待機とする。
- ADR-158（Gemini bypass fix, PR #3783）: 同じ Gemini 抽出パイプラインに触れる変更だが、
  ADR-158 はプロンプト/マッチングロジックの話で本変更（トークン集計）とは独立。競合なし。
