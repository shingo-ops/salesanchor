# recon: 数字だけの値が金額の一部に当たる件（「151」と「@151,000円」）

- 基準: origin/main 91310d6db（2026-10-16 JST）
- 調べた人: Sonnet（読み取り）／確認: Opus（下記の行を実物で再読）

## 1. 既存 ADR・設計の検索結果
- `git grep -i "数字境界\|word boundary\|has_word_boundary" docs/adr/` の結果、関係するのは ADR-154 の1か所だけ。
  - `docs/adr/ADR-154*.md:90`「…数字境界…の未確定契約を維持する」。境界の決まりを守るとだけ書いてあり、今回の変更と食い違わない。
- 既存の設計: `docs/handoff/line-match-short-boundary/design.md`（PR-3b）
  - `docs/handoff/line-match-short-boundary/design.md:8`「数字だけ」の値は前後が英字・数字でないときだけ一致。
  - `docs/handoff/line-match-short-boundary/design.md:9` 除外ワードは変えない。
  - `docs/handoff/line-match-short-boundary/design.md:16` 受け入れ基準「「151」が金額に当たらない」。ただし `,` や `@` は英数字ではないため、「@151,000円」の形では満たされていない（下記 3.）。

## 2. 対象コード（実物）
- `/Users/tanizawashingo/worktrees/salesanchor/release-line-match-price-digit-boundary/backend/app/services/extraction_judgement_svc.py:57-59` `_needs_boundary`：2文字以下、または数字だけの値は境界を条件にする。
- `.../backend/app/services/extraction_judgement_svc.py:62-67` `has_word_boundary`：正規表現 `(?<![a-z0-9])` + needle + `(?![a-z0-9])`。
- `.../backend/app/services/extraction_judgement_svc.py:70-75` `has_left_word_boundary`：除外ワード用（今回触らない）。呼び出しは同ファイル `:318`。
- `.../backend/app/services/extraction_judgement_svc.py:201-215` `_value_hits`：`has_word_boundary` を呼ぶ唯一の場所（`:214`）。品番・記号と検索ワードの各トークンの両方がここを通る。
- `match_text_g2` を呼ぶ5か所（すべて上の関数を共有）:
  - `backend/app/services/gemini_raw_copy_v102_product_first.py:647-648`
  - `backend/app/services/gemini_raw_copy_v102_followup.py:48`
  - `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:169`
  - `backend/app/services/v102_gap_lines.py:175`・`:202`
- 本流以外の4経路には Gemini の価格の情報が渡らない（Sonnet の読み取り、/tmp/CC報告ファイル/price-strip-design/recon-raw.md・社外秘のため repo 外）。そのため「Gemini の価格を照合文から消す」方式は全経路に効かない。

## 3. 観測した事実（本番の写し 2492行での試算・集計のみ）
- 事例: ナイトワンダラーのカートンの行（item 02e97dba）。照合文に「…@151,000円」がある。
  - 商品 106 の検索ワード「151」が「151,000」の「151」に当たり、候補が 77 と 106 の2件になって未特定（ambiguous）。
  - 「151」の前は `@`、後ろは `,` で、どちらも英数字ではないため、今の境界の決まりでは当たりになる。
- NFKC で ＠→@、￥→¥、＄→$、，→,、．→. になることを実行で確認（`fold_for_match` は NFKC を含む）。
- 試算（案P、下記 design.md）: 2492行のうち結果が変わるのは 1行（02e97dba：ambiguous[77,106] → matched 77）。境界の判定だけ変わって結果が同じ行が 10行（トークン 24・6・151・1）。根拠: /tmp/CC報告ファイル/price-strip-design/simP/summary.txt（集計のみ。原文は repo に入れない）。

## 4. 既存の試験
- `backend/tests/test_extraction_judgement_svc.py:542` `TestMatchProductShortBoundary`
  - `:568-569` product_code="151" が「151BOX 15,100円」「新品 15100」に当たらない。
  - `:583-584` 「151 カートン」「◆151」「151カートン」には当たる。
  - `:609` 「1 5 1」「15-1」を 151 とみなさない。
- `backend/tests/test_extraction_judgement_svc.py:691-692` mark="2025" が「EX 12025x」に当たらない。
- `backend/tests/test_gemini_raw_copy_v102_score_select.py:72-73` 検索語「名前 SV2a 151」。
- 静的に読んだ範囲で、案Pで結果が変わる既存試験は無い（実行は実装時に行う）。
