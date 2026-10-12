# recon: 試作版 v102 の要確認に「誰が出したか」の欄が無い件

この文書は何か：要確認（review・post_review・gemini_review）が、システムが出したものか Gemini が出したものか、結果を見ても分からない、という現状の事実の一覧。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
設計：[design.md](./design.md)

調査日：2026-10-09。基準：origin/main fb036a238（`git rev-parse origin/main`）。調査は Sonnet が実物で確認した。
社外秘：投稿の原文・仕入元の名前・指示書の本文は、この文書に書かない。

## 1. 結果の形（今）
- backend/app/tools/prompt_ab.py:265-268 `_gemini_review`：Gemini の unsure を `parse_v102_unsure` で記録の形にする。
- backend/app/tools/prompt_ab.py:271-282 `_with_gemini_review`：各件の `gemini_review` 欄に `gemini_unsure` を足す。件の `review` には足さない。
- backend/app/tools/prompt_ab.py:285-310 `_v102_row_fields`：`v102_items`・`v102_flags`（`post_review`・`gemini_review`）を返す。`post_review` の要素は response_unreadable・no_items・extract_exception など。
- backend/app/services/gemini_raw_copy_v101.py:267-284 `parse_v102_unsure`：正しい要素は kind `gemini_unsure`（line・candidates）、正しくない要素は kind `gemini_unsure_invalid`（error。line・candidates があれば付く）。
- backend/app/tools/prompt_ab_recompute.py:78：recompute も同じ `_v102_row_fields` を呼ぶ。

## 2. 事実
- 件の `review` と `post_review` の要素に、出どころの欄は無い。
- Gemini の要確認は件の `review`（要確認の一覧）に入らず、`gemini_review` 欄に別に残る。一覧から見ると Gemini の要確認が見えない。
- 形が壊れた unsure（gemini_unsure_invalid）は `v102_flags["gemini_review"]` にだけ残り、`post_review` には出ない。

## 3. ADR 検索
- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`：配信は needs_review=false の行に限定する。
- `docs/adr/ADR-014-inventory-management.md:29`：解析ロジックの秘匿（原文を載せない）。
- `docs/adr/ADR-027-ui-internationalization.md`：理由は文章でなく種類（kind）で持つ。
- 要確認の出どころを直接扱う ADR：該当なし（docs/adr/FEATURE-INDEX.md と本文を、要確認・出どころ・source で検索）。

## 4. 衝突の確認
- `backend/app/tools/prompt_ab.py` を触る開いた PR：PR 作成前に `gh pr list --state open` で再確認する（結果は PR 本文）。
