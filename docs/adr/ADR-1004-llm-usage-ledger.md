# ADR-1004: LLM 使用量台帳（llm_usage_events）新設

| 項目 | 内容 |
|------|------|
| ステータス | Accepted by PO direction 2026-09-30 |
| 作成日 | 2026-09-30 |
| 起案 | Claude Opus（設計） + しんごさん（PO 方針承認） |
| 関連 | ADR-110（翻訳）、ADR-135/ADR-136（危険PRとGO）、ADR-072（テナント文脈） |
| 置き換え | PR #3883（`release/gemini-thinking-tokens-cost`、thoughts を output_tokens に畳み込む案）は closed。helper とテストの考え方を本 ADR の実装に取り込んだ |

---

## Context（design.md §2 recon の事実）

- Gemini 呼び出しは本番経路で4つ（抽出・試運転・在庫解析の補完・翻訳）。5つ目 `tcg_work_comparison_svc.call_work_model` はテストからしか呼ばれない未結線経路のため対象外。
- 使用量の記録は3系統に分散していた: `extraction_attempts`（input/output/cost）、`extraction_shadow_runs`（同、全件 NULL）、`tenant_llm_budgets`（テナント別の月合計金額のみ）。翻訳と在庫解析には1回ごとの記録が無かった。
- どの経路も `prompt_token_count` と `candidates_token_count` しか読まず、`thoughts_token_count`/`cached_content_token_count`/`tool_use_prompt_token_count`/`total_token_count` は捨てていた。
- 公式料金表: `gemini-3.1-flash-lite` / `gemini-3.5-flash-lite` の出力単価は "including thinking tokens"（thoughts が課金対象に含まれる）。SDK の `total_token_count = prompt + candidates + tool_use_prompt + thoughts`（`candidates_token_count` 自体は thoughts を含まない）。
- PO の指示（本ADRの直接の根拠）:「使用量は最大限細分化してくれるとどこで多く消費しているとか適切かどうかも判断しやすい」。

詳細な file:line 根拠は `docs/handoff/llm-usage-ledger/recon.md` を参照。

## Decision（design.md §3、詳細は design.md 本文を正とする）

1. **新表 `public.llm_usage_events`**（1行 = Gemini の応答1回）を新設する。`purpose`（使いみち）・`tenant_id`・`model`・`sdk`・6種のトークン数列（`prompt_tokens`/`cached_content_tokens`/`candidates_tokens`/`thoughts_tokens`/`tool_use_prompt_tokens`/`total_tokens`、すべて Optional）・`cost_usd`・`extraction_attempt_id`/`extraction_shadow_run_id`/`discord_inbound_message_id`/`source_ref`（参照先を経路ごとに使い分け）・`backfilled` を持つ。SDK が返さない値は NULL のまま記録し、0 と推測して埋めない。
2. **書く場所**: 応答を受け取り usage を読めた時点で、呼び出し元と同じトランザクションで1行書く。`line_extraction` は `AttemptRecorder.complete()`/`fail()`、`line_extraction_shadow` は `extraction_shadow_svc`（`insert_shadow_run()` の直後）、`inventory_parse_fallback` は `record_cost` の隣、`translation_inbound`/`translation_inbound_escalation`/`translation_outbound` は `message_translator` の3箇所の `record_cost` の隣。呼び出し自体が例外で応答が無い場合は usage 不明のため行を作らない。応答後のパース失敗は行を作る。
3. **費用の式**: `cost = prompt_tokens × 入力単価 + (candidates_tokens + thoughts_tokens) × 出力単価`（NULL は 0 として計算、両方 NULL なら cost も NULL、単価表に無いモデルは NULL）。単一の関数 `llm_budget.calculate_usage_cost()` に集約。
4. **SSOT への切り替え**: `extraction_attempts`/`extraction_shadow_runs` の token/cost 列には本PR以降書き込まない（列は残置、DROP は別途 PO 本人の GO が必要）。過去分は migration で台帳へ写す（`backfilled=true`、`extraction_attempt_id` で重複防止の冪等 `INSERT ... SELECT ... WHERE NOT EXISTS`）。集計 API `GET /tcg/analysis-dashboard/cost-summary` は台帳から読むよう切り替え、`input_bytes/3` の推定を廃止する。
5. **対象外**: 画面での内訳表示（PR-B で別途）、`tenant_llm_budgets` の月次リセットが翻訳経路で呼ばれない件（別課題）、旧列の DROP。
6. **実装時変更（PR #3884 CI対応）**: `extraction_shadow_run_id` は FK を張らない（列・インデックスは維持）。CI の `migration-test-run` 差分実行ベースラインに `public.extraction_shadow_runs` が登録されておらず、REFERENCES すると CI のみで失敗するため。試運転（`extraction_shadow_runs` への書き込み）自体が `EXTRACTION_SHADOW_ENABLED`（既定無効、#3864）で現在停止中のため実害はない。

## Consequences

- 台帳への INSERT 失敗は同一トランザクション内のため、従来の token UPDATE と同じ失敗面。新たな外部依存は増えない。
- 旧 SDK（`google-generativeai`）は thoughts 等を返さないため、対応する列は常に NULL で記録される（推測しない）。
- 戻し方: 本 PR を revert すれば台帳への書き込みが止まり、旧列への書き込みが復元される（台帳の表自体は残る）。台帳表の DROP は PO 本人の GO が必要。
- 維持の仕組み: 書き込みは `llm_budget.record_usage_event`/`record_usage_event_sync` の1箇所に集約し、各経路はそれを呼ぶだけ。守り手は `backend/tests` の台帳テストと `migration-guard.yml` / migration 登録チェック（CI）。
- 在庫解析の補完（inventory_parse_fallback）の台帳書き込み：backend/app/services/inventory_parser.py は condition vocab gate（scripts/check-condition-vocab.js、変更ファイルの全文を旧語彙で検査・例外なし）により、既存の旧語彙を含むため編集できない。本番の在庫解析の実績は discord_inbound_messages の最終行が 2026-06-25（直近7日0件、2026-09-30 読み取り）。旧語彙の整理後に別PRで結線する。purpose の値と CHECK 制約は先に用意しておく。
- inventory_parse_fallback 経路は 2026-10-02 に機能ごと削除（purpose 値は互換のため残置）。詳細: docs/handoff/remove-discord-inventory-parse/design.md

## 受入条件（design.md §5）

| 基準 | 検証方法 |
|---|---|
| 4経路すべてで応答1回につき台帳1行 | 単体テスト（各経路で fake usage → 行の各列が期待値） |
| thoughts が費用に入る | `calculate_usage_cost` のテスト（prompt=1000, candidates=100, thoughts=50） |
| SDK が返さない値は NULL | テスト（usage に属性なし → 列 NULL） |
| 旧列へ書き込まない | grep: extraction_attempts / extraction_shadow_runs への input_tokens・output_tokens・cost_usd の SET/INSERT が0件 |
| 過去分の写しが完全 | 反映後の本番読み取り: backfilled 行数 = 対象 attempt 数、sum(cost_usd) が一致 |
| 反映後の新規抽出が台帳に入る | 反映後の本番読み取り: 新しい attempt 数 = 新しい line_extraction 行数 |
| migration が冪等 | CI のマイグレーション実行テスト＋同じ migration を2回流して行数不変 |

詳細設計・全文は `docs/handoff/llm-usage-ledger/design.md`、recon 根拠は `docs/handoff/llm-usage-ledger/recon.md` を参照。
