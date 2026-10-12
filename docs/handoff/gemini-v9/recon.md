# Recon: gemini-v9（v8 の指示を残し、v9 の指示と受け取りを足す）

- この文書は何か（1行）: v9 を設計する前に、今のコードと指示書がどうなっているかを、事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-v9/design.md
- 起点: origin/main = 1584d4a679a6029492dadfeccfa5403db61a3d76（worktree 作成時の HEAD。PR #3922 のマージ）
- 出典: worktree 上で `git show origin/main:<path>` と `cat -n` を使い、行番号を確認した（2026-10-02）。評価・提案は書かない。

## 既存ADRの検索
- 検索した語：raw_copy、書き写し、gemini（`git grep -il` を docs/adr/ に対して実行。FEATURE-INDEX.md でも検索し、該当は0件）。
- 該当したADR：ADR-014、ADR-075、ADR-080、ADR-085、ADR-100、ADR-1004、ADR-110、ADR-154、ADR-SA-17。
- このうち関係するもの
  - docs/adr/ADR-085-supplier-prompts.md：仕入先別の Gemini プロンプト管理。v9 は仕入元の書き方（build_supplier_note_v8）を v8 と同じものとして使う。
  - docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md：取り込み・解析のパイプライン。v9 は本番の経路に入れない。
  - docs/adr/ADR-1004-llm-usage-ledger.md：費用の台帳。prompt_ab の記録先で、変えない。
- そのほかは、翻訳・在庫・監視・秘密情報・GAS 移行のADRで、この作業には関係しない。

## 指示書 v8（変更しない）
- backend/app/prompts/raw_copy_v8.txt:3 「価格が書かれた行を1件として」
- backend/app/prompts/raw_copy_v8.txt:6 価格の行ごとに1件。状態違い・梱包違いは別の1件にする。
- backend/app/prompts/raw_copy_v8.txt:11 price・quantity・unit・state は、その件の行と注記の行から写す。
- backend/app/prompts/raw_copy_v8.txt:12 「完売」「残りN」などは、書かれている位置の欄にそのまま写す。
- backend/app/prompts/raw_copy_v8.txt:13 ship は、その件の行か見出しからだけ写す。投稿全体の注意書きは写さない。
- backend/app/prompts/raw_copy_v8.txt:14 範囲に見出しの行を含めない。
- backend/app/prompts/raw_copy_v8.txt:15 heading は、商品名を写した見出しの行。無ければ null。
- backend/app/prompts/raw_copy_v8.txt:18-44 例1〜例3。
- backend/app/prompts/ にあるファイルは raw_copy_v8.txt の1つだけ。

## v8 の受け取り（backend/app/services/gemini_raw_copy_v8.py）
- :4-5 比較試験の道具専用。本番の経路からは呼ばれない。
- :23 `_PROMPT_PATH`（raw_copy_v8.txt）、:64-65 `load_v8_prompt`
- :25-27 必須の欄の定数。
- :29-56 `V8_RESPONSE_SCHEMA`。heading_line_* は ["integer","null"]。
- :94-108 `build_supplier_note_v8`（既定の単位を除く）
- :111-117 `build_prompt_v8(raw_text, *, prompt_text, ...)`。指示書の本文は引数で受け取る。
- :165-217 `call_gemini_raw_copy_v8`。:189-191 で、use_schema のときに `V8_RESPONSE_SCHEMA` を固定で渡す。
- :229-245 `_check_fields`、:248-251 `_span_error`、:254-255 `_overlaps`、:258-265 `_to_item`、:268-280 `_validate_one`
- :283-324 `parse_v8_response`
  - :308-311 全件の見出しの範囲を集める。
  - :316-317 範囲が、どれかの件の見出しの範囲と重なれば、その件を捨てる（自分の見出しも含む）。
  - :318-319 範囲がほかの件と重なれば捨てる。

## 比較試験の道具（backend/app/tools/prompt_ab.py）
- :34-39 v8 の関数を import する。
- :160-169 `_parse`。v7 以外は parse_v8_response を使う。
- :184-188 dry-run の表示で、config が v8 のときは build_prompt_v8 を使う。
- :205 config が v8 のときだけ load_v8_prompt を読む。
- :234-241 v7 以外は call_gemini_raw_copy_v8 を呼ぶ。
- :288 `--config` の選択肢は ("v7","v8")。
- :301-304 v8 専用の設定は、v7 と一緒に使うとエラーになる。

## 既存の試験
- backend/tests/test_gemini_raw_copy_v8.py
  - :137 `test_parse_v8_response_detects_overlap_with_own_heading`（範囲 2-4、見出し 2-2 で捨てる）
  - :143 他の件の見出しとの重なり
  - :230 `cfg.response_json_schema == v8.V8_RESPONSE_SCHEMA`
  - :284 指示書ファイルの存在
- backend/tests/test_prompt_ab.py
  - :195 v8 の設定の受け渡し
  - :289 `test_parse_args_rejects_v8_options_for_v7`
  - :304 共有の pg fixture を使う試験（CI 専用）

## PO の過去の決定（変えない前提）
- docs/handoff/gemini-v8/design.md:15-24 ①〜⑥（完売・単位・状態ごとの価格の行・投稿全体の発送・範囲に見出しを入れない・考えた過程）。
- 完売の判定の修正（S1）の設計（社外秘の分析記録・リポジトリ外）：/tmp/CC報告ファイル/product-classification/design-system-fixes.md
  - :199 変更は数量の欄を足すことだけ。
  - :218 標本20件中19件は raw_state=none、raw_quantity=完売。

## T1 の集計（社外秘・リポジトリ外。集計値だけを design.md §2 に転記した）
- /tmp/CC報告ファイル/gemini-v8-t1/fidelity.md（全件の機械点検）
- /tmp/CC報告ファイル/gemini-v8-t1/manual_sheet.md（目視50件）
- /tmp/CC報告ファイル/gemini-v8-t1/v8_instruction_compliance.md（判定のまとめ）

## 守り手
- 守り手: .github/workflows/process-artifacts-gate.yml
- 守るもの: v8 の指示書と本番の v7・v6 が変わっていないこと（PR 本文の git diff が空であることの証明と、v8 の受け取りの結果が変更の前後で一致すること）。
