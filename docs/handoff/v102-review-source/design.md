# design: 試作版 v102 の要確認に出どころ（source）を付ける

この文書は何か：要確認の一つ一つに「システムが出したか、Gemini が出したか」の欄を付け、Gemini の要確認も要確認の一覧に入れる設計。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
現状の事実：[recon.md](./recon.md)（フルパス：docs/handoff/v102-review-source/recon.md）
関係する ADR：
- [ADR-154](../../adr/ADR-154-tcg-parity02-gas-python-migration.md)（`:70` 配信は needs_review=false の行に限定）。§6 の引き渡し先。
- [ADR-014](../../adr/ADR-014-inventory-management.md)（`:29` 解析ロジックの秘匿）。原文の文字を載せない。
- [ADR-027](../../adr/ADR-027-ui-internationalization.md)。理由は文章でなく kind で持つ。
- 前の設計：[../v102-no-silent-drop/design.md](../v102-no-silent-drop/design.md)（要確認の形）、[../v102-gemini-unsure/design.md](../v102-gemini-unsure/design.md)（Gemini の要確認）。

PO 決定（2026-10-09「y」）：要確認の出どころは「誰が要確認を出したか」で決める。Gemini の要確認も要確認の一覧に入れ、Gemini かシステムかが見え、DB にも記録できる形にする。試作版の照合を担当する別セッションの提案（PO 経由 2026-10-09）に沿う形で、review の要素に source の欄が増える。

## 1. 目的（KGI）
判定（○×）：
1. v102 の結果の各件の `review` の全要素と、`v102_flags["post_review"]` の全要素に `source`（`"system"` か `"gemini"`）がある。
2. Gemini が unsure に書いた行（kind `gemini_unsure`）が、price_line が candidates に入る各件の `review` の末尾に `source: "gemini"` で入る。候補でない件には入らない。
3. 形が壊れた unsure（`gemini_unsure_invalid`）が `post_review` の末尾に `source: "system"` で入る。
4. 件の `gemini_review` 欄と `v102_flags["gemini_review"]` は変わらない。unsure の無い応答では、source の付加以外の出力が変わらない。v101・他の config は変わらない。

## 2. 現在地
recon.md §1〜§2。

## 3. 変更（`backend/app/tools/prompt_ab.py` の `_v102_row_fields` の最後の段とその試験だけ）
新しい dict を作る（元を書き換えない）。
1. `review` の各要素：すでに `source` があれば変えない。無ければ `"system"`。
2. `gemini_review` の正しい要素（kind `gemini_unsure`）ごとに、price_line が candidates に入る各件の `review` の末尾に `{"line": n, "kind": "gemini_unsure", "candidates": [...], "source": "gemini"}` を足す。
3. `post_review` の各要素：`source` が無ければ `"system"`。`gemini_unsure_invalid` は `post_review` の末尾に `{"kind": "gemini_unsure_invalid", "error": ..., (line・candidates があれば), "source": "system"}` として写す（応答の形が壊れていることを見つけたのはシステムなので system）。
4. extract_exception の経路でも `post_review` の要素に `source: "system"` を付ける。
- 原文の文字は載せない。`gemini_review` 欄は #4050 のまま残す。
- 触らない：`gemini_raw_copy_v101.py`、`gemini_raw_copy_v102_product_first.py`、prompt_ab_recompute.py、スキーマ、指示書、migration、`.github/workflows/`、画面。

## 4. 試験と受入条件
| 基準 | 検証方法 |
|---|---|
| source が無い要素に system が付く／ある要素は変えない | `backend/tests/test_v102_review_source.py::test_review_element_without_source_gets_system`・`test_review_element_with_source_is_not_changed`・`test_post_review_element_with_source_is_not_changed` |
| gemini_unsure が候補の件の review に gemini で入り、候補でない件には入らない | 同上 `test_gemini_unsure_is_appended_as_gemini_to_items_whose_price_line_is_a_candidate_only`、`backend/tests/test_prompt_ab_recompute.py::test_gemini_unsure_enters_review_of_candidate_items_with_source_gemini` |
| gemini_unsure_invalid が post_review に system で入る | 同上 `test_invalid_unsure_goes_to_post_review_as_system_and_marks_no_item`、`test_prompt_ab_recompute.py::test_invalid_unsure_enters_post_review_with_source_system` |
| gemini_review 欄は不変 | 同上 `test_gemini_review_field_of_item_and_flags_stay_as_they_were` |
| 元の dict を書き換えない | 同上 `test_does_not_mutate_the_input` |
| unsure の無い応答では source の付加以外が変わらない | 同上 `test_without_unsure_only_source_is_added`・`test_flags_without_post_review_get_no_post_review_key` |
| recompute の経路でも付く | `test_prompt_ab_recompute.py::test_recompute_route_adds_source_to_review_and_post_review` |
| extract_exception の経路で付く | `test_prompt_ab_recompute.py::test_extract_exception_post_review_has_source_system` |
| 既存の試験がすべて通る・CI 必須が緑 | CI |
| 本番反映後に s6 r1/r2・fg1 を recompute して、review と post_review の全要素に source があり、gemini の要素は0件（f_c・f_g とも unsure が無いため）。source を除けば前回の計算し直し（~/CC報告ファイル-keep/stage-hs-verify-20261009/）と一致 | Opus が確認 |

## 5. 外部・過去事例の参照と我々への応用
- 過去事例（このリポジトリ）：[../v102-gemini-unsure/design.md](../v102-gemini-unsure/design.md)。Gemini の要確認をシステムの要確認とは別に残した。本件はその別の欄を残したまま、一覧にも出どころ付きで入れる。
- 外部事例：不要。試作版の結果の形の内部設計で、外部の数値で比べる対象ではないため。

## 6. システム側への引き渡し（このPRでは作らない。担当は切り替えの新セッション）
- 要確認ページに出どころの列を足す（i18n の `t()`・デザインシステムの部品）。
- DB の `analysis_results.review_reasons` に `source` を残す。
- 要確認への対応後に「誤りの元（Gemini／システム／原文があいまい）」を記録する欄を設ける（PO 2026-10-09 の要望。今の DB にあるかは別途確認中）。

## 7. リスクと戻し方
- リスク：`review` に Gemini の要素が入るため、review を数える道具は Gemini の要確認も数える。source で分けられる。
- リスク：source を除けば前回と同じ、を受入条件で確かめる。
- 戻し方：PR を revert（試作版の結果の形だけが戻る。本番は無関係）。

## 維持の仕組み
- 守り手: backend/tests/test_v102_review_source.py
- 対象: review と post_review の全要素に source があること、Gemini の要確認が候補の件にだけ gemini で入ること、gemini_review 欄と他の出力が変わらないこと。
