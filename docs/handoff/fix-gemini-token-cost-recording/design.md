# design: Gemini トークン・費用の記録修正

recon: `docs/handoff/fix-gemini-token-cost-recording/recon.md`

関連 ADR: `ADR-1003`（GO 発行・マージ判断は Opus へ常時委譲。本 PR の GO/マージ手順は
`docs/adr/ADR-1003-go-delegation-to-opus.md` に従う。技術内容そのものへの制約はない）。

## §B 変更

1. 出力トークンの読み方を、3か所とも `candidates_token_count` に直す
   （`message_translator.py:426` と同じ読み方にそろえる）。
   - 対象: `backend/app/services/gemini_extraction_svc.py:450`（`call_gemini_extraction`）、
     同ファイル `:529`（`call_gemini_raw_copy`）、
     `backend/app/services/inventory_parser_llm.py:318`。
   - `thoughts_token_count` を含めるかどうかは、今回は決めない。
     **未確認事項**として本 design.md の末尾に記載する
     （課金に含まれるかを Google 公式資料で確かめてから、次の便で決める）。

2. 試運転（extraction_shadow_runs）の記録：
   - `insert_shadow_run`（`extraction_shadow_svc.py:97-`）に
     `input_tokens: int | None`・`output_tokens: int | None`・
     `cost_usd: float | None`・`started_at: datetime | None` の引数を追加し、
     INSERT 文の列・VALUES・パラメータ dict にも追加する。
   - `run_shadow_for_job`（同 `:288-`）で、`call_gemini_raw_copy` を呼ぶ直前の
     時刻（`datetime.now(timezone.utc)` 相当）を `started_at` として変数に控える。
   - `raw_copy["input_tokens"]` / `raw_copy["output_tokens"]` を受け取り、
     `calculate_cost(input_tokens, output_tokens, model=_REQUESTED_MODEL)`
     （`llm_budget.py:130`）で費用を計算して `insert_shadow_run` に渡す。
     `ValueError`（未知モデル）の場合は `tcg_extraction_record_svc.py:172-179` と
     同じ扱いで `cost = None` にする。
   - `finished_at` は現状通り INSERT 文中の `now()` のままとし、変更しない。
   - `_record_failed_run`（`extraction_shadow_svc.py:339-`）でも、
     tokens が分かっている場合（Gemini 呼び出し自体は成功したがパース等で
     失敗したケース）は同様に `insert_shadow_run` へ渡す。
     Gemini 呼び出し自体が失敗した場合（`GEMINI_CALL_FAILED`）は tokens 不明のため
     `None` のまま。

3. テスト：
   - `backend/tests/test_inventory_parser_llm.py:59` の `_make_fake_response` の
     モック属性を `usage.response_token_count = candidates_tokens` から
     `usage.candidates_token_count = candidates_tokens` に直す。
   - `backend/tests/test_tcg_gemini_extraction.py` に、
     `call_gemini_extraction` / `call_gemini_raw_copy` が
     `usage_metadata.candidates_token_count` を読み、
     `response_token_count`（旧属性名）を設定しても無視される（0扱いにならず
     正しく `candidates_token_count` 側の値を拾う）ことを確認するテストを追加する。
   - `backend/tests/test_extraction_shadow_svc.py` に、
     `insert_shadow_run` の呼び出しに `input_tokens`・`output_tokens`・
     `cost_usd`・`started_at` が渡ることを確認するテストを追加する
     （`_patch_common` は既に `call_gemini_raw_copy` の戻り値に
     `input_tokens`/`output_tokens` を含めてモックしている）。

4. DB は変えない。`migrations/20260928_110000_create_extraction_shadow_tables.sql`
   に列は既にある（recon §A 参照）。マイグレーション追加は行わない。

## 外部・過去事例

- 本カードの根拠は本番環境での直接検証（google-genai 2.8.0 の
  `model_fields` 実測、recon §A）であり、社外のブログ・Issue 等は参照していない。
  Google 公式の genai SDK リファレンス（`GenerateContentResponseUsageMetadata`）の
  一次情報が最終的な裏取り先になるが、今回のカードでは本番実測を優先した。
- 社内の類似実装（`message_translator.py:426`）が既に `candidates_token_count` を
  正しく使っており、本 PR はそれに他 3 箇所を合わせる形。新規パターンの導入ではない。

## §C 検証

| # | 基準 | 検証方法 |
|---|---|---|
| T1 | 3か所（`gemini_extraction_svc.py` 2箇所・`inventory_parser_llm.py` 1箇所）が `candidates_token_count` を読む | 単体テスト |
| T2 | 試運転の記録（`insert_shadow_run` 呼び出し）に tokens・cost・started_at が渡る | 単体テスト |
| V1 | 本番に反映したあと、新しい extraction_attempts で output_tokens が NULL ではない | 本番DB の読み取り（設計担当が行う。実装便の範囲外） |

## 維持の仕組み

- `message_translator.py` と `gemini_extraction_svc.py` / `inventory_parser_llm.py` は
  いずれも `usage.usage_metadata` から `getattr` で読む同一パターンであり、
  本 PR 後は 4 箇所すべてが `candidates_token_count` に統一される。今後 Gemini SDK
  呼び出しを追加する際は grep `getattr(usage,` で既存箇所を確認すれば揃える先が
  見つかる状態にする。
- 試運転側のテスト（T2）が `insert_shadow_run` の呼び出し引数を固定化するため、
  将来 tokens/cost の受け渡しを誤って削る変更が入れば単体テストで検知できる。

## §D 戻し方・守り手

- 戻し方: `git revert` で本 PR のコミットを戻す（DB スキーマ変更を伴わないため
  revert のみで安全に戻せる）。
- 守り手: Opus 設計担当

## 未確認事項

- `thoughts_token_count` を出力トークン集計・課金対象に含めるべきかどうかは
  今回未確認。Google 公式のトークン計算・課金ドキュメントで裏取りしてから、
  次の便で判断する。
