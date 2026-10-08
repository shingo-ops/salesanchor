# design: 試作版 v102 で、黙って消える件と印をすべて要確認に回す

この文書は何か：試作版の結果から件や印が人に知らされずに消えないよう、すべてを要確認の理由として結果に残す設計。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
現状の事実：[recon.md](./recon.md)（フルパス：docs/handoff/v102-no-silent-drop/recon.md）
関係する ADR：
- [ADR-154](../../adr/ADR-154-tcg-parity02-gas-python-migration.md)（`:70` 配信は needs_review=false の行に限定）。本設計の要確認は、切り替えのときこの正本に載せる前提で形をそろえる。
- [ADR-014](../../adr/ADR-014-inventory-management.md)（`:29` 解析ロジックの秘匿）。理由には原文を入れず、行番号と写しの文字だけを持つ。

## 1. 目的（KGI）
- PO の決定（2026-10-08 原文）：「『その件が黙って消える』は最悪、要確認に回さないと人間が気づかず不具合が慢性化する」「黙って消えるものは取り急ぎ全て要確認に回す」
- 判定（○×）：
  1. 試作版の結果で、Gemini が返した件の数と、結果に残る件の数が、どの投稿でも同じ（消える件 0）。
  2. recon §2・§3 の各箇所が起きたとき、必ず要確認の理由が結果に残る。

## 2. 現在地
recon.md §2〜§4。消える箇所 D1〜D5、保存されない印3種、理由の無い単位 none・分類「不明」。

## 3. 変更（`gemini_raw_copy_v101.py`・`prompt_ab.py` とその試験だけ。v102 の経路だけで動かし、v10.1 以前の出力は変えない）
### 3-1 要確認の理由の形（件ごと：`review` の要素。既存の `{"line": n, "kind": ...}` と同じ形）
| kind | いつ | 足す欄 |
|---|---|---|
| `item_shape_invalid` | D1 | `error`（既存の検査の文） |
| `price_not_in_lines` | D2 | `field: "price"`、`copied`（写しの文字） |
| `duplicate_price_line` | D3 | — |
| `quantity_no_number` | 既存の印 quantity_no_number の行を持つ件 | — |
| `possible_footer_line` | 既存の印 possible_footer_line の行を持つ件 | — |
| `unit_unknown` | 件の `unit` が none | — |
| `category_unknown` | `match_status` が matched で `product_category` が「不明」 | — |
- 文章は入れない（画面で i18n の `t()` から作るため。ADR-027）。原文も入れない（ADR-014）。

### 3-2 投稿ごとの理由（`v102_flags["post_review"]`、要素は `{"kind": ..., ...}`）
| kind | いつ | 足す欄 |
|---|---|---|
| `response_unreadable` | D4 | `error` |
| `extract_exception` | D5 | `error`（例外の種類と文） |
| `no_items` | Gemini の件が0 | — |
| `possible_missing_item` | 既存の印 possible_missing_item の各行 | `line` |
| `possible_footer_line` | 印の行がどの件の lines にも無いとき | `line` |
- 既存の `v102_flags` の3つの印は消さない（今の読み手を壊さないため）。

### 3-3 落とした件を残す
- `parse_v101_response` に引数 `keep_rejected: bool = False` を足す。True のときだけ、D1〜D3 の件を捨てずに、`{"rejected": <kind>, "gemini_index": i, "lines": <整数だけ>, "price": <写し or None>, "quantity": <写し or None>, "price_line": <D3 はその行、ほかは None>, "error": <既存の文>}` として戻り値の items の後ろに足す。False のときの動き（v10.1 以前）は1文字も変えない。
- `_extract_v102` は、`rejected` の件を通常の処理（役割・共有行・抜けの印）から外し、結果の最後に、通常の件と同じ欄名を持つ件として足す。値は `name` 等を "none"、数値欄を None、`review` に 3-1 の理由、`rejected` と `gemini_index` を残す。通常の件の値は変えない。
- `prompt_ab._v102_row_fields`（`backend/app/tools/prompt_ab.py:262-272`）は `keep_rejected=True` で呼び、例外のときは `v102_flags = {"post_review": [{"kind": "extract_exception", "error": ...}]}` を返す（`v102_items_error` は残す）。

### 3-4 半角「/」の不具合
- `_priced_line`（`:117-122`）：v102 の経路（`keep_rejected=True` のとき）だけ、全角「／」に加えて半角「/」でも最初の価格で探し直す。v10.1 以前は変えない。

### 3-5 触らない
- `backend/app/services/gemini_raw_copy_v102_product_first.py`（開いた PR #4038 が触っているため）。分類の判定は v101 側で `product_category` と `match_status` を読むだけ。
- 本番の解析（v6・v7）、`analysis_results`、migration、`deploy.yml`、画面。
- 既存の試験の期待値（v10.1 以前の経路）。

## 4. 試験と受入条件
| 基準 | 検証方法 |
|---|---|
| D1・D2・D3 の件が結果に残り、各 `review` に kind が付く。結果の件数＝Gemini の件数 | 単体試験（`backend/tests/test_gemini_raw_copy_v101.py` に追加） |
| D4・件0・D5 で `post_review` に kind が付く | 単体試験（同上・`backend/tests/test_prompt_ab.py`） |
| 3つの印の行が、件の `review` か `post_review` に必ず載る | 単体試験 |
| `unit` none の件に `unit_unknown`、照合済みで分類「不明」の件に `category_unknown` | 単体試験 |
| 半角「/」の2つの価格で価格の行が見つかる（v102）。v10.1 では今までどおり | 単体試験 |
| `keep_rejected=False` の出力が変更前と同じ | 既存の試験がすべて通る（CI）、`test_v102_fixes_false_output_has_no_new_keys_and_is_unchanged_by_default` |
| 通常の件の値が変わらない（理由の追加だけ） | 手元の4回分の Gemini の答えで、変更前後の結果を比べる（デプロイ後、`prompt_ab_recompute` で。Gemini は呼ばない） |
| 消える件 0 | 同じ比べで、全投稿の件数＝Gemini の件数 |

## 5. 外部・過去事例の参照と我々への応用
- 過去事例（このリポジトリ）：状態の訂正（`backend/app/services/tcg_condition_review_svc.py:219-292`）は、要確認の理由を1か所で決めて保存する。本件も理由を結果の1か所（件の `review` と投稿の `post_review`）に集め、切り替えのとき `analysis_results.review_reasons` に写せる形にする。
- 外部事例：不要。試作版の結果の形の内部設計で、外部の数値で比べる対象ではないため。

## 6. リスクと戻し方
- リスク：`rejected` の件は価格の行が None になる。手元の採点の道具などが price_line を前提にしている場合、数え方が変わる。→ `rejected` の欄で通常の件と区別できるようにする。採点は Gemini の答え（response_text）で行うので、採点の値は変わらない。
- リスク：要確認の件数が増える（単位 none は e の2回で各約850件）。→ 理由の種類で絞って見られる形にする（画面は切り替えの設計で作る）。
- 戻し方：PR を revert（試作版の結果の形だけが戻る。本番は無関係）。

## 維持の仕組み
- 守り手: backend/tests/test_gemini_raw_copy_v101.py
- 対象: 結果の件数が Gemini の件数と一致すること、各箇所で要確認の理由が付くこと、v10.1 以前の出力が変わらないこと。
