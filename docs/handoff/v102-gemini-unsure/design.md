# design: 試作版 v102 で Gemini の「どちらの件か決まらない」(unsure) を捨てずに残す

この文書は何か：Gemini が「この行は上下どちらの件か決まらない」と申告したとき、受け取り側がそれを捨てずに、システムの要確認とは別の「Gemini の要確認」として結果に残す設計。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
現状の事実：[recon.md](./recon.md)（フルパス：docs/handoff/v102-gemini-unsure/recon.md）
関係する ADR：
- [ADR-154](../../adr/ADR-154-tcg-parity02-gas-python-migration.md)（`:70` 配信は needs_review=false の行に限定）。Gemini の要確認が付いた件は、この正本の手前で人に回す（§7）。
- [ADR-014](../../adr/ADR-014-inventory-management.md)（`:29` 解析ロジックの秘匿）。結果に原文の文字を載せない。
- [ADR-027](../../adr/ADR-027-ui-internationalization.md)。理由は文章でなく種類（kind）で持つ。
- 前の設計：[../v102-no-silent-drop/design.md](../v102-no-silent-drop/design.md)（黙って消さない方針と、原文を載せない方針）。

## 1. 目的（KGI）
- PO の決定（2026-10-09 原文）：「y：設計書を作り、レビューにかけてから」（離席中の完走を一任）。
- 判定（○×）：
  1. 試作版 v102 の Gemini の応答に unsure があるとき、その内容が結果（`v102_flags["gemini_review"]`）に残り、捨てられない。
  2. unsure の candidates に price_line が入る件には、件ごとの `gemini_review` に印が付く。
  3. unsure の無い応答では、`gemini_review` が空配列であることを除き、結果が今までと1文字も変わらない。

## 2. 現在地
recon.md §1〜§4。スキーマに欄が無く（`backend/app/services/gemini_raw_copy_v101.py:62-74`）、受け取りも最上位の `items` しか読まない（同 `:175-215`）。

## 3. 変更（v102 の経路だけ。v101 の出力、本番 v6・v7、f_c の既定 `V102_PROMPT` は変えない）
### 3-1 `backend/app/services/gemini_raw_copy_v101.py`
- `V102_RESPONSE_SCHEMA` を足す：`V101_RESPONSE_SCHEMA` の深いコピーに、最上位の `properties.unsure`（array、要素は object `{line: integer, candidates: array of integer}`、要素の required は `line`・`candidates`）を足す。最上位の `required` は V101 と同じ `["items"]`（unsure は必須にしない）。`V101_RESPONSE_SCHEMA` 自体は変えない。
- `parse_v102_unsure(response_text, line_count, price_lines) -> list[dict]` を足す。`v8._load_items` と同じ JSON の読み方で最上位の `unsure` を読む。

| 入力 | 戻り値の要素 |
|---|---|
| 正しい要素 | `{"kind": "gemini_unsure", "line": n, "candidates": [a, b, ...]}`（candidates は重複除去・昇順） |
| 正しくない要素 | `{"kind": "gemini_unsure_invalid", "error": <コード>}`（整数で取れた範囲の `line`・`candidates` を足す。原文の文字は載せない） |
| unsure が無い・空・null・応答が読めない | `[]`（読めない応答は post_review の `response_unreadable` が別に知らせる） |
| unsure が配列でない | `[{"kind": "gemini_unsure_invalid", "error": "unsure_not_list"}]` |

- エラーコードと判定の順：`not_object`（要素が object でない）→ `line_not_int`（bool も不可）→ `line_out_of_range`（1〜行数の外）→ `candidates_not_list` → `candidate_not_int`（1つでも整数でない）→ `candidate_not_price_line`（price_lines に無い候補がある）→ `candidates_too_few`（重複を除いて2未満）。
- `price_lines`：その投稿の `v102_items` の `price_line`（整数のもの）の集合。`line_count`：原文を `\n` で分けた行数（`parse_v101_response` の範囲検査と同じ数え方）。

### 3-2 `backend/app/tools/prompt_ab.py`
- `schemas` の `"v102"` を `V102_RESPONSE_SCHEMA` にする（`"v101"` は `V101_RESPONSE_SCHEMA` のまま）。
- `_v102_row_fields`：`v102_flags["gemini_review"] = parse_v102_unsure(...)` を必ず入れる（無ければ `[]`）。各件に `gemini_review` を必ず付ける（既定 `[]`）。正しい `gemini_unsure` ごとに、`price_line` が candidates に入る件の `gemini_review` に `{"kind": "gemini_unsure", "line": n}` を足す。
- 新しい dict を作る形（`{**item, ...}`・`{**flags, ...}`）にして、元の dict を書き換えない。既存の `review`・`post_review`・ほかの `v102_flags` の印は消さない・変えない。
- 取り出しの例外のとき（`extract_exception`）は `v102_flags` に `gemini_review: []` を足す。この場合は件が無く、投稿ごと `post_review` で要確認になっているため。
- `backend/app/tools/prompt_ab_recompute.py` は変えない（`_v102_row_fields` 経由で自動的に付く。recon §3）。

### 3-3 触らない
- v101 の経路（config `v101`）、本番 v6・v7、`prompt_ab_recompute.py`、`backend/app/services/gemini_raw_copy_v102_product_first.py`、migration、`.github/workflows/`、画面、`V102_PROMPT` と DB の指示書。

## 4. 試験と受入条件
| 基準 | 検証方法 |
|---|---|
| `parse_v102_unsure` が正常（重複除去・昇順）・各エラーコード・unsure 無し・空・null・配列でない・読めない応答を、§3-1 の表どおりに返す | 単体試験 `backend/tests/test_v102_gemini_unsure.py` |
| 正しくない記録に原文の文字が入らない | 同上（`test_invalid_records_carry_no_raw_text`） |
| `V102_RESPONSE_SCHEMA` に unsure があり、items の定義は V101 と同じ。V101 スキーマは不変（`:140-143` の既存試験が通る） | 同上＋`backend/tests/test_gemini_raw_copy_v101.py` |
| v102 が V102 スキーマを Gemini に渡し、v101 は V101 を渡す | `backend/tests/test_prompt_ab.py` |
| 候補の件に `gemini_review` が付き、候補でない件は `[]`、`v102_flags["gemini_review"]` が入る | `backend/tests/test_prompt_ab_recompute.py` |
| unsure の無い応答で、`gemini_review` を除いて出力が変わらない。unsure があっても既存の review・フラグは変わらない | 同上（`test_without_unsure_output_is_unchanged_except_empty_gemini_review`・`test_unsure_does_not_change_existing_review_or_flags`） |
| 再計算（recompute）の道でも付く | 同上（`test_recompute_route_also_adds_gemini_review`） |
| 既存の試験がすべて通る・CI 必須が緑 | CI |
| 本番デプロイ後、保存済みの JSONL（f_c の s6）を recompute すると、`gemini_review` が全件 `[]` で、それ以外の出力が変わらない | Opus が確認（recompute の出力を変更前と比べる） |
| 指示書 f_e で 3d539fc8 を流すと、unsure か正しい割り当てが出る | Opus が確認（Gemini を呼ぶ実行） |

## 5. 外部・過去事例の参照と我々への応用
- 過去事例（このリポジトリ）：[../v102-no-silent-drop/design.md](../v102-no-silent-drop/design.md) §3-2。投稿ごとの理由を `{**flags, "post_review": [...]}` の形で足し、既存の印を消さない。本件も同じ形で `gemini_review` を足す。
- 外部事例：不要。試作版の結果の形の内部設計で、外部の数値で比べる対象ではないため。

## 6. リスクと戻し方
- リスク：Gemini が unsure を多用すると、人に回る件が増える。→ 件数は recompute と実行で数え、f_e の評価で見る（本設計では上限を設けない。数字の根拠が無いため）。
- リスク：スキーマが変わるので、v102 の Gemini 応答の形がわずかに変わる（unsure の欄が使える）。→ unsure は必須でないため、f_c のように unsure を書かない指示書の応答は今までどおり。
- 戻し方：PR を revert（試作版の結果の形だけが戻る。本番は無関係）。

## 7. システム側への引き渡し（このPRでは作らない。担当はシステム解析の別セッション）
1. `gemini_review` に `gemini_unsure` が付いた件は配信せず、人の要確認に回す（ADR-154 の「配信は needs_review=false の行に限定」につなぐ。切り替えのとき `analysis_results.review_reasons` に写す）。
2. 人が、その unsure の行をどちらかの件に割り当てる。
3. 割り当て後に、その件をシステム解析に流す。
- `gemini_unsure_invalid` は、Gemini の申告が読めなかった印。件に付けず投稿ごとに残るため、投稿を人が見る入口に使う。

## 維持の仕組み
- 守り手: backend/tests/test_v102_gemini_unsure.py
- 対象: unsure を捨てないこと、V101 スキーマと v101 の出力が変わらないこと、unsure の無い応答で既存の出力が変わらないこと。
