# design: LLM 使用量台帳（llm_usage_events）— PR-A

- 状態: 設計案（Opus）→ Architect 審査（Opus 自己審査、独立レビューではない）→ PO 方針承認済み（2026-09-30「y」、原文は PR の GO記録）
- recon: docs/handoff/llm-usage-ledger/recon.md
- 関連ADR: ADR-1004（本設計で新設・LLM 使用量台帳）、ADR-110（翻訳）、ADR-135/136/1003（危険PRとGO）、ADR-072（テナント文脈）
- 置き換え: PR #3883（thoughts を output_tokens に畳み込む案）は閉じ、helper とテストを本設計に取り込む

## 1. 目的（PO の言葉）
「使用量は最大限細分化してくれるとどこで多く消費しているとか適切かどうかも判断しやすい」
→ Gemini を呼ぶたびに1行、量の種類ごと・使いみちごとに記録し、どこで何に使ったかを1か所（SSOT）で集計できるようにする。

## 2. 現状（recon の事実）
- Gemini 呼び出しは本番経路で4つ（抽出・試運転・在庫解析の補完・翻訳）。5つ目 tcg_work_comparison_svc.call_work_model はテストからしか呼ばれない。
- 使用量の記録は3系統に分散：extraction_attempts（input/output/cost）、extraction_shadow_runs（同、全件NULL）、tenant_llm_budgets（テナント別の月合計金額のみ）。翻訳と在庫解析は1回ごとの記録なし。
- どの経路も prompt_token_count と candidates_token_count しか読まない。thoughts/cached/tool_use/total は捨てている。
- 公式料金表：gemini-3.1-flash-lite / 3.5-flash-lite の出力単価は「including thinking tokens」。SDK：total = prompt + candidates + tool_use_prompt + thoughts（candidates は thoughts を含まない）。

## 3. 決定
### 3-1. 新しい表 public.llm_usage_events（1行 = Gemini の応答1回）
| 列 | 型 | 意味 |
|---|---|---|
| id | uuid PK default gen_random_uuid() | |
| occurred_at | timestamptz not null default now() | 応答を受け取った時刻 |
| purpose | text not null, CHECK in ('line_extraction','line_extraction_shadow','inventory_parse_fallback','translation_inbound','translation_inbound_escalation','translation_outbound') | 使いみち |
| tenant_id | integer null | テナントが分かる経路のみ（抽出・試運転は運営共通パイプラインのため NULL） |
| model | text not null | 実際に指定したモデル名 |
| sdk | text not null, CHECK in ('google-genai','google-generativeai') | どの SDK の値か |
| prompt_tokens | integer null | usage.prompt_token_count |
| cached_content_tokens | integer null | usage.cached_content_token_count |
| candidates_tokens | integer null | usage.candidates_token_count |
| thoughts_tokens | integer null | usage.thoughts_token_count |
| tool_use_prompt_tokens | integer null | usage.tool_use_prompt_token_count |
| total_tokens | integer null | usage.total_token_count |
| cost_usd | numeric(12,6) null | 3-3 の式。単価表に無いモデルは NULL |
| extraction_attempt_id | uuid null FK public.extraction_attempts(id) ON DELETE SET NULL | |
| extraction_shadow_run_id | uuid null FK public.extraction_shadow_runs(id) ON DELETE SET NULL | |
| discord_inbound_message_id | 型は discord_inbound_messages.id に合わせる, null（FK は張らない：テーブルは運用停止中で型差異の危険を避ける） | |
| source_ref | text null | 翻訳の message_id など、上の FK で表せない参照 |
| backfilled | boolean not null default false | 過去データを写した行 |
- SDK が返さなかった値は NULL（0 と区別する。推測で埋めない）。
- インデックス：(occurred_at)、(purpose, occurred_at)、(extraction_attempt_id)。
### 3-2. 書く場所（応答を受け取り usage を読めた時点で、呼び出し元と同じトランザクションで1行）
| purpose | 書く箇所 | セッション |
|---|---|---|
| line_extraction | tcg_extraction_record_svc.AttemptRecorder（complete / fail で今 input_tokens 等を UPDATE している箇所を置き換え） | sync |
| line_extraction_shadow | extraction_shadow_svc（insert_shadow_run で tokens/cost を入れている箇所を置き換え、run_id を紐付け） | sync |
| inventory_parse_fallback | inventory_parser._maybe_apply_llm_fallback の record_cost 呼び出しの隣 | async |
| translation_inbound / _escalation / translation_outbound | message_translator の record_cost 呼び出し3か所の隣 | async |
- 呼び出しが例外で応答が無いときは usage が無いので行を作らない（課金の有無は不明、推測で作らない）。応答後にパースで失敗した場合は行を作る。
- call_work_model（テスト専用）は対象外。本番経路に結線するときに purpose を追加する。
### 3-3. 費用の式（単一の関数：llm_budget.calculate_usage_cost）
cost = prompt_tokens × 入力単価 + (candidates_tokens + thoughts_tokens) × 出力単価（NULL は 0 として計算、両方 NULL なら cost も NULL）。
- cached_content_tokens の割引単価は、キャッシュを使っていないため今回は扱わない（未使用であることは台帳の値で監視できる）。
- tenant_llm_budgets への record_cost は、予算の上限判定のために従来どおり続ける（本PRでは変えない）。record_cost に渡す出力量は candidates + thoughts に揃える。
### 3-4. SSOT への切り替え（データを分散させない）
- extraction_attempts.input_tokens/output_tokens/cost_usd と extraction_shadow_runs の同3列には、本PR以降書き込まない（列は残す。DROP は別途 PO 本人の GO が必要なので本PRでは行わない）。
- 過去分は migration で台帳へ写す（backfilled=true、extraction_attempt_id で重複防止の冪等 INSERT ... SELECT ... WHERE NOT EXISTS）。写す条件：input_tokens IS NOT NULL OR output_tokens IS NOT NULL OR cost_usd IS NOT NULL。candidates_tokens ← output_tokens、prompt_tokens ← input_tokens、cost_usd ← cost_usd、purpose='line_extraction'、sdk='google-genai'、model ← requested_model、occurred_at ← coalesce(response_received_at, finished_at, started_at)。
- 集計 API GET /tcg/analysis-dashboard/cost-summary（backend/app/routers/tcg_analysis_dashboard.py）は台帳から読むよう切り替える（input_bytes/3 の推定は、台帳に行が無い古い attempt の表示用としてのみ残すかは recon で呼び出し元0件のため、推定を廃止し台帳の実値のみとする）。

## 4. 対象外
- 画面での内訳表示（PR-B で別に行う）。
- tenant_llm_budgets の月次リセットが翻訳経路で呼ばれない件（別課題として記録）。
- 旧列の DROP。

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| 4経路すべてで応答1回につき台帳1行 | 単体テスト（各経路で fake usage → 行の各列が期待値）|
| thoughts が費用に入る | calculate_usage_cost のテスト（prompt=1000, candidates=100, thoughts=50 → 1000×0.25e-6 + 150×1.5e-6）|
| SDK が返さない値は NULL | テスト（usage に属性なし → 列 NULL）|
| 旧列へ書き込まない | grep：extraction_attempts / extraction_shadow_runs への input_tokens・output_tokens・cost_usd の SET/INSERT が0件 |
| 過去分の写しが完全 | 反映後の本番読み取り：backfilled 行数 = 対象 attempt 数、sum(cost_usd) が一致 |
| 反映後の新規抽出が台帳に入る | 反映後の本番読み取り：新しい attempt 数 = 新しい line_extraction 行数、thoughts_tokens が NULL でない（SDK が返す場合）|
| migration が冪等 | CI のマイグレーション実行テスト＋同じ migration を2回流して行数不変 |

## 6. リスクと対処
- 台帳への INSERT 失敗で抽出が失敗する → 同一トランザクションなので従来の token UPDATE と同じ失敗面。新たな外部依存は増えない。
- 旧 SDK（google-generativeai）が thoughts 等を返さない → NULL で記録。
- 戻し方：PR を revert（台帳は残るが書き込みが止まり、旧列への書き込みが戻る）。台帳の表の削除は PO 本人の GO が必要。

## 7. 外部・過去事例
該当事例の引用なし。理由：Google 公式の料金表と SDK の型定義（recon §7）を直接の根拠とし、事例による裏付けを要しない設計（1回の API 応答を1行で記録する台帳）。

## 8. 維持の仕組み
- 書き込みは llm_budget の関数1か所（record_usage_event の sync/async 版）に集約し、各経路はそれを呼ぶだけ。
- 守り手: backend/tests の台帳テスト、migration-guard とマイグレーション登録チェック（CI）
