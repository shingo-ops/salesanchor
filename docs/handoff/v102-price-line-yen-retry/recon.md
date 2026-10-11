# recon: v102 で価格の写しに「円・¥」が付くと価格の行が見つからず件が落ちる

調査 2026-10-11（Opus 設計・Sonnet 調査）。社外秘のため原文・仕入元名は書かない（形は数字を # に伏せる）。

## 事実（根拠つき）
- 価格の行の特定は `backend/app/services/gemini_raw_copy_v101.py:150-158` `_priced_line`。Gemini が写した price の文字を、件の行の中で `_first_line_containing` で探す（`:143-147`、空白・記号を詰めた形の部分一致）。見つからず「／」（v102 は半角「/」も）でつないでいれば最初の価格で探し直す。それ以外の探し直しは無い。
- `_priced_line` の呼び出しは `backend/app/services/gemini_raw_copy_v101.py:180`（`_price_line`）だけ。`_price_line` の呼び出しは `backend/app/services/gemini_raw_copy_v101.py:229`（`parse_v101_response`）だけ。v102 は `keep_rejected=True` で呼ぶ（`backend/app/services/line_analysis_v102_svc.py:264`、`backend/app/services/line_analysis_v102_svc.py:794`）。
- 見つからない件は `price_not_in_lines` として落とした件になり、値は空・要確認（`docs/handoff/v102-no-silent-drop/design.md:24`、`docs/handoff/v102-no-silent-drop/design.md:45`）。
- 投稿の件が全部落ちると、取りこぼし検知 `possible_missing_item` は走らない（`backend/app/services/gemini_raw_copy_v101.py:1285-1289`）。
- Gemini の件は1件ずつ extraction_items に保存され（`backend/app/services/line_analysis_v102_svc.py:328-339`）、件の review の種類が analysis_results.review_reasons に入る（`backend/app/services/line_analysis_v102_svc.py:580`）。

## 試験データでの観測（手元・Gemini の保存済み応答。集計値のみ）
- 原文の価格が「#,### × #」のように円の無い書き方の投稿で、Gemini が price を「#,###円」と写すことがある。このとき価格の行が見つからず、その件は落ちる。
- 本番の指示書 f_ct（DB key raw_copy_v101_f_ct）の試験 bs1（7投稿×3回）：1投稿で 16件全部が `price_not_in_lines`（3回中1回）。
- 旧指示書 f_c の試験 s7-r1・s7-r2：1投稿で 14件全部（各1回）。
- 保存済み応答 1,021回の `price_not_in_lines` 48件のうち、写しの形は「#,###円」37・「###円」7 ほか。

## 本番 DB 事前確認（読み取りのみ・2026-10-11 04:26Z 時点）
```
v102 の extraction_jobs 85 件、v102 の analysis_results 1,814 件（engine_version v102-f_c 28 / v102-f_ct 1,786）
analysis_results.review_reasons に price_not_in_lines を含む行: 0
extraction_items で analysis_results の無い行: 0
```

## 既存 ADR 検索
- 実行：`git grep -n -i -E "price_line|価格の行|price_not_in_lines|rejected|no-silent-drop|_priced_line|写し" origin/main -- docs/adr/` と `docs/adr/FEATURE-INDEX.md`。
- 結果：直接の ADR は無い（「写し」の別用法のみ：`docs/adr/ADR-1004-llm-usage-ledger.md:49`、`docs/adr/ADR-1007-migration-structure-only-run-once.md:73`、`docs/adr/ADR-101-sa-quotation-invoice-generation.md:6`）。FEATURE-INDEX に LINE解析の行は無い。
- 関連：ADR-014（解析ロジックの秘匿。理由に原文を入れない）、ADR-154（配信は needs_review=false に限る）。正本は `docs/specs/line-analysis-tuning/README.md` と `docs/handoff/v102-no-silent-drop/`。

## 既存の試験（`backend/tests/test_gemini_raw_copy_v101.py`）
- `price_not_in_lines` の試験：`:801`、`:830`（例の写し「9,999円」は原文に 9,999 自体が無い）。
- 半角「/」の v102 限定の試験：`:869`（v10.1 以前は今までどおり、を確かめる型）。
