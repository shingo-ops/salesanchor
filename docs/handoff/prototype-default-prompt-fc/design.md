# design: 試作版 v102 の既定の指示書を f_c（DB の key）にする

この文書は何か：試験の道具が、指示書を指定しないときに、採用した f_c を使うようにする設計。
親（仕様書）：[../../specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)
現状の事実：[recon.md](./recon.md)（フルパス：docs/handoff/prototype-default-prompt-fc/recon.md）
関係する ADR：[ADR-014](../../adr/ADR-014-inventory-management.md)（`:29` 解析ロジックの秘匿。本文をリポジトリに置かずに既定にする）

## 1. 目的（KGI）
- PO の決定（2026-10-08 原文）：「f-cを採用」（試作版の既定の指示書を f_c にするか、への答え）。
- 判定（○×）：`--config v102` で `--prompt-name` も `--prompt-key` も付けないとき、DB の key `raw_copy_v101_f_c` の本文が指示書になり、結果の行に `prompt_name="raw_copy_v101_f_c"`・`prompt_source="db"` が残る。

## 2. 変更（`backend/app/tools/prompt_ab.py` と試験だけ）
- 定数 `DEFAULT_V102_PROMPT_KEY = "raw_copy_v101_f_c"` を足す（`:305` の近く）。
- `run_ab`（`:502` の前）：`config == "v102"` で `prompt_name` も `prompt_key` も None のとき、`prompt_key = DEFAULT_V102_PROMPT_KEY` として、以降は `--prompt-key` を付けたときと同じ道（DB から読む・行が無ければ Gemini を呼ぶ前に止まる・`prompt_source="db"`・sha256 のログ）を通る。
- `--prompt-name` の help（`:615`）の「v102 は既定 raw_copy_v101_e」を「v102 は既定 DB の key raw_copy_v101_f_c」に直す。
- `backend/app/services/gemini_raw_copy_v101.py:38` の `DEFAULT_V102_PROMPT_NAME` は残す（`--prompt-name raw_copy_v101_e` で前の版を明示して使えるようにするため、e のファイルも残す）。`_load_prompt_text` の既定の分岐（`:342-343`）は `run_ab` の外から呼ばれたときのために変えない。

## 3. 触らない
- 指示書のファイル（`backend/app/prompts/`）、DB の行、本番の解析（v6・v7）、試作版の解析の処理（`backend/app/services/gemini_raw_copy_v101.py` の取り出し）、`backend/app/tools/prompt_ab_recompute.py`（指示書を読まない）。
- 別セッションが担当するシステムの解析側のファイル。

## 4. 試験と受入条件
| 基準 | 検証方法 |
|---|---|
| v102 で名前も key も無いとき、DB の key raw_copy_v101_f_c の本文が指示書になる | 単体試験（`backend/tests/test_prompt_ab.py`、偽の session が key を受け取ったことと本文を確かめる） |
| その結果の行が prompt_name=raw_copy_v101_f_c・prompt_source=db | 単体試験 |
| key の行が無ければ Gemini を呼ぶ前に止まる | 単体試験 |
| `--prompt-name raw_copy_v101_e` を付ければ e のファイルを使う（prompt_source=file） | 単体試験 |
| v101・v9 など他の config の既定は変わらない | 既存の試験が通る（CI） |
| 本番で動く | マージ・デプロイ後に `--config v102 --dry-run`（名前・key なし）で、ログの sha256 が d2a6447f… になる |

## 5. 外部・過去事例の参照と我々への応用
- 過去事例（このリポジトリ）：PR #4030 の `--prompt-key` と同じ読み込みの道を使う。新しい読み込みは作らない。
- 外部事例：不要。道具の既定値の切り替えで、外部の数値で比べる対象ではないため。

## 6. リスクと戻し方
- リスク：既定に頼って v102 を流している別の試験の結果が、e から f_c に変わる。→ 調整記録に既定の変更を書き、結果の行の prompt_name・prompt_sha256 で区別できる（PR #4030）。
- 戻し方：PR を revert（既定が e のファイルに戻る）。

## 維持の仕組み
- 守り手: backend/tests/test_prompt_ab.py
- 対象: v102 の既定が DB の key raw_copy_v101_f_c であること、行が無いときに Gemini を呼ぶ前に止まること。
