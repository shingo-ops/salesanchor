# recon: 試作版 v102 の既定の指示書

この文書は何か：試作版の試験の道具が、指示書を指定しないときにどの指示書を使うかの、現状の事実。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
設計：[design.md](./design.md)

調査日：2026-10-08。基準：origin/main 95f8a5c5c。Opus が確認した。

## 1. 既定の決まり方
- `backend/app/services/gemini_raw_copy_v101.py:38` `DEFAULT_V102_PROMPT_NAME = "raw_copy_v101_e"`。
- `backend/app/tools/prompt_ab.py:342-343` `_load_prompt_text`：`--config v102` で名前も key も無いとき、ファイル `raw_copy_v101_e.txt` を読む。
- `backend/app/tools/prompt_ab.py:507-509` 結果の行の `prompt_name` は、key が無ければ `DEFAULT_V102_PROMPT_NAME`。
- `backend/app/tools/prompt_ab.py:305` `_PROMPT_KEY_CONFIGS = ("v101", "v102")`、`:318` `load_prompt_from_db`（PR #4030）。
- `backend/app/tools/prompt_ab.py:502` 指示書は Gemini を呼ぶ前に読む。

## 2. 採用した指示書
- `public.extraction_prompt_config` の key `raw_copy_v101_f_c`（sha256 d2a6447faf0842dad134337a302ed9c9bb7b8ac9c8731bc25860a56b9d037d21、本番 DB の照合で一致済み）。調整記録 `docs/specs/line-analysis-tuning/README.md:17`。

## 3. 既定 e を前提にしている試験
- `backend/tests/test_prompt_ab.py:684`・`:685`・`:689`・`:893`（v102 の既定が e であること）。
- `backend/tests/test_prompt_ab.py:921-929`（e のファイルが v101・v102 で読めること。名前を指定した読み方なので、既定とは別）。
- `backend/tests/test_prompt_ab_recompute.py:28`・`:105`（試験の入力の行の値。既定の決まりとは無関係）。

## 4. ADR 検索
- `docs/adr/ADR-014-inventory-management.md:29`（解析ロジックの秘匿）。既定の指示書を DB の key にすると、本文がリポジトリに無いまま既定にできる。
- 試作版の既定の指示書を扱う ADR：該当なし。
