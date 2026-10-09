# design: 試作版 v102 で、見出しの直下の発送日の行が2件目以降にも入った件に要確認の理由を付ける

この文書は何か：Gemini が見出しの直下の発送日の行を、自分の発送日の行を持つ2件目以降の件にも入れたとき、その件に要確認の理由を付ける設計（行は消さない・直さない）。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
現状の事実：[recon.md](./recon.md)（フルパス：docs/handoff/v102-heading-ship-review/recon.md）
関係する ADR：
- [ADR-154](../../adr/ADR-154-tcg-parity02-gas-python-migration.md)（`:70` 配信は needs_review=false の行に限定）。§6 の引き渡し先。
- [ADR-014](../../adr/ADR-014-inventory-management.md)（`:29` 解析ロジックの秘匿）。結果に原文の文字を載せない。
- [ADR-027](../../adr/ADR-027-ui-internationalization.md)。理由は文章でなく kind で持つ。
- 前の設計：[../v102-no-silent-drop/design.md](../v102-no-silent-drop/design.md) §3-1（件ごとの kind の表。本件で1行追記）。

## 1. 目的（KGI）
- PO の決定（2026-10-07 個別13）：それぞれの発送日の行は、すぐ下の価格の件にだけ入れる。前提は、2件目以降にも自分の発送日の行があること。これを受け取り側で確かめる。
- 判定（○×）：
  1. 見出し・発送A・価格1・発送B・発送C・価格2 の形で、2件目の lines に発送A が入っていれば、2件目の `review` に `heading_ship_with_own_ship` が1要素付く。1件目には付かない。
  2. 発送A が2件目に入っていない、2件目に自分の発送の行が無い、まとまりが1件だけ、発送の文字が価格の行にある、のどれかなら付かない。
  3. `review_reasons=False` の出力、v101 の出力、既存の `review` の要素と順番は1文字も変わらない（新要素は末尾）。

## 2. 現在地
recon.md §1〜§3。

## 3. 変更（`backend/app/services/gemini_raw_copy_v101.py` とその試験だけ。v102 で review_reasons=True のときだけ動く）
- 新しい関数 `_heading_ship_reasons(rows)`（`_item_reasons` の次）。extracted 全体を受け、件ごとの理由のリストを返す。元の dict は書き換えない。`_extract_v102` が `review` の末尾に足す。
- 規則：
  1. 件を「lines の最小の行番号 h」でまとめる（落とした件 rejected は見ない）。件が2つ以上のまとまりだけ見る。まとまりの中で price_line が最小の件を F とする。
  2. F 以外の各件 B について：
     - H = B の lines のうち、roles が "ship"、かつ h < 行 < F の price_line の行。
     - O = B の lines のうち、roles が "ship"、かつ F の price_line < 行 < B の price_line、かつ同じまとまりの B 以外のどの件の lines にも無い行。
     - H と O がどちらも空でなければ、H の各行 s ごとに B の `review` に `{"line": s, "kind": "heading_ship_with_own_ship", "own_lines": sorted(O)}` を足す。
- 原文の文字は載せない。新しい言葉・正規表現は足さない（発送の見分けは既存の roles。固定の `_SHIP_RE`（`backend/app/services/gemini_raw_copy_v101.py:55`）で、マスタ由来ではない。マスタ化は別途 PO 判断）。
- kind の表（`docs/handoff/v102-no-silent-drop/design.md` §3-1）に1行追記する。
- 触らない：prompt_ab.py、prompt_ab_recompute.py、スキーマ、指示書、migration、`.github/workflows/`、画面。

## 4. 試験と受入条件
| 基準 | 検証方法 |
|---|---|
| (a) 見出し・発送A・価格1・発送B・発送C・価格2 で、2件目に発送A が入っていれば2件目に1要素（line=発送A、own_lines=[発送B,発送C]）、1件目には付かない | `backend/tests/test_v102_heading_ship_review.py::test_marks_second_item_that_took_the_heading_ship_line_and_has_its_own_ship_lines` |
| (b) 2件目に発送A が入っていなければ付かない | 同上 `test_does_not_mark_when_second_item_did_not_take_the_heading_ship_line` |
| (c) 2件目に自分の発送の行が無ければ付かない | 同上 `test_does_not_mark_when_second_item_has_no_own_ship_line` |
| (d) まとまりの件が1つだけなら付かない | 同上 `test_does_not_mark_when_the_group_has_only_one_item` |
| (e) 発送の文字が価格の行（役目 price）にあれば付かない | 同上 `test_does_not_mark_when_the_ship_text_is_on_the_price_line` |
| (f) 既存の review が残り新要素は末尾、元の dict を書き換えない | 同上 `test_keeps_existing_review_items_first_appends_new_one_last_and_does_not_mutate_input` |
| (g) review_reasons=False の出力が変わらない | 同上 `test_review_reasons_false_output_has_no_new_kind`、既存 `test_without_review_reasons_the_v102_output_has_no_new_keys` |
| 既存の試験がすべて通る・CI 必須が緑 | CI |
| 本番反映後に保存済み JSONL を recompute：f_c の s6-r1-merged.jsonl・s6-r2-merged.jsonl（~/CC報告ファイル-keep/stage-s6-20261008/）で新 kind が0件 | Opus が確認 |
| f_g の fg1-g-20261009.jsonl（~/CC報告ファイル-keep/stage-fg1-20261009/）で新 kind がちょうど1件（3b685d67 の回5、price_line 23、line 13、own_lines [19,21]）、ほかの欄は不変 | Opus が確認 |

## 5. 外部・過去事例の参照と我々への応用
- 過去事例（このリポジトリ）：[../v102-no-silent-drop/design.md](../v102-no-silent-drop/design.md) §3-1・§3-2。件ごとの理由を `review` の末尾に `{"line": n, "kind": ...}` の形で足し、既存の印を消さない。本件も同じ形。
- 外部事例：不要。試作版の結果の形の内部設計で、外部の数値で比べる対象ではないため。

## 6. システム側への引き渡し（このPRでは作らない。担当はシステム解析の別セッション）
- この kind が付いた件は配信せず、人の要確認に回す（ADR-154 の「配信は needs_review=false の行に限定」につなぐ。切り替えのとき `analysis_results.review_reasons` に写す）。

## 7. リスクと戻し方
- リスク：発送の見分けが固定の正規表現（`:55`）のため、発送の言葉が増えれば見落とす。今回は言葉を足さない（マスタ化は別途 PO 判断）。
- リスク：見出しの共有を「lines の最小の行番号が同じ」で近似しているため、見出しが別の2群が同じ最小行になる形では誤って付く可能性がある。f_c の保存済み出力で0件、f_g で1件になることを受入条件で確かめる。
- 戻し方：PR を revert（試作版の結果の形だけが戻る。本番は無関係）。

## 維持の仕組み
- 守り手: backend/tests/test_v102_heading_ship_review.py
- 対象: 見出しの発送の行が2件目以降にも入った件に kind が付くこと、付かない形で付かないこと、review_reasons=False と既存の review が変わらないこと。
