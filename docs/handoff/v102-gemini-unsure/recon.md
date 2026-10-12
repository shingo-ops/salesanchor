# recon: 試作版 v102 で Gemini の「どちらの件か決まらない」を受け取る

この文書は何か：Gemini が上下どちらの件か決められない行を申告しても、今の受け取り側は捨ててしまう、という現状の事実の一覧。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
設計：[design.md](./design.md)

調査日：2026-10-09。基準：origin/main 1c2981a7e。調査は Opus（事実）、行番号は Sonnet が実物で再確認した。
社外秘：投稿の原文・仕入元の名前・指示書の本文は、この文書に書かない。unsure を書かせる指示書は DB の key `raw_copy_v101_f_e` に入れてある（本文はリポジトリに置かない）。

## 1. 応答の形（スキーマ）は v101 と v102 で共有
- `backend/app/services/gemini_raw_copy_v101.py:62-74` `V101_RESPONSE_SCHEMA`：最上位は `items` だけ（`:73` `"required": ["items"]`）、各件は `lines`・`price`・`quantity`。
- `backend/app/tools/prompt_ab.py:559-560`：`"v101": V101_RESPONSE_SCHEMA, "v102": V101_RESPONSE_SCHEMA`。`:562` で `response_schema` として Gemini に渡す。
- よって v102 で Gemini が unsure を書きたくても、スキーマに欄が無い。
- 固定する試験：`backend/tests/test_gemini_raw_copy_v101.py:140-143`（V101 スキーマの欄は lines・price・quantity だけ）。

## 2. 受け取り側は知らない項目を捨てる
- `backend/app/services/gemini_raw_copy_v101.py:175-215` `parse_v101_response`：`:187` で `v8._load_items`（`backend/app/services/gemini_raw_copy_v8.py:304-312`）が `items` 配列だけを取り出し、`:213` で件を `lines`・`price`・`quantity`・`price_line` の4キーで作り直す。最上位のほかの項目は読まない。
- `backend/app/tools/prompt_ab.py:263-284` `_v102_row_fields`：`:278` は `{"v102_items": extracted, "v102_flags": flags}` を返すだけで、応答の `items` 以外は結果に載らない。

## 3. 再計算の道も同じ関数を通る
- `backend/app/tools/prompt_ab_recompute.py:77-78`：保存済みの `response_text` から `pab._v102_row_fields` を呼んで行を作り直す。
- よって `_v102_row_fields` を直せば、保存済みの応答の再計算にも自動的に反映される。コードを足す必要はない。

## 4. 既存の「要確認」との関係
- 件ごとの `review` と投稿ごとの `v102_flags["post_review"]` は、システムが決める要確認（`docs/handoff/v102-no-silent-drop/design.md` §3）。Gemini の申告はこれと混ぜない（誰が言った要確認か分かる形で別に持つ）。
- `backend/app/tools/prompt_ab.py:277` `post_review` の作り方（`{**flags, ...}` で新しい dict を作る）が、既存の書き方。本件も同じ形で足す。
- 正しくない値を受け取るときの方針：原文の文字を結果に載せない（`docs/handoff/v102-no-silent-drop/design.md` §1・ADR-014・ADR-027）。

## 5. 衝突の確認
- `backend/app/services/gemini_raw_copy_v101.py`・`backend/app/tools/prompt_ab.py` を触る開いた PR：PR 作成前に `gh pr list --state open` で再確認する（結果は PR 本文に記載）。
- `backend/app/tools/prompt_ab_recompute.py`・`backend/app/services/gemini_raw_copy_v102_product_first.py` は本件で変えない。

## 6. ADR 検索
- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`：配信は needs_review=false の行に限定する（引き渡しの向き先）。
- `docs/adr/ADR-014-inventory-management.md:29`：解析ロジックの秘匿。
- `docs/adr/ADR-027-ui-internationalization.md`：文章は結果に入れない（画面で t() から作る）。
- 試作版の Gemini の申告（unsure）を直接扱う ADR：該当なし（docs/adr/FEATURE-INDEX.md と本文を、要確認・unsure・試作・v102 で検索）。
