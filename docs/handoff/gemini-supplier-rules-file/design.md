# design: 比較試験の道具に「仕入元ルールを差し替える」切り替えを足す

- 作成：2026-10-06 Opus（設計）
- PO 承認（2026-10-06）
  - 質問：「2社分のルール案を、試しA・B（約 1.1 USD）で確かめてよいですか？」
  - 答え：「y」
  - 承認の範囲：比較試験の道具に、ルールを差し替える機能を足す PR を出し、GO を受けてから試しを流す。本番の仕入元ルールは変えない。
- recon：docs/handoff/gemini-supplier-rules-file/recon.md
- 関係する ADR：ADR-100、ADR-1004、ADR-085、ADR-154
- 前の版：docs/handoff/gemini-omit-supplier-field/design.md、docs/handoff/gemini-prompt-e/design.md

## 1. 目的（KGI）
- 仕入元ルールを、指示書 e と同じ形（手順への当てはめ＋実際に誤りが出た形の原文例と出力例）で書くと、Gemini の行選びの誤りが減るかどうかを、本番のルールを変えずに確かめる。
- 判定（指示書 e＋今のルールとの比較）
  - 試験A：まとめ書きの行がある5投稿×5回で、まとめ書きの行を入れた回数。今は 2/25、合格は 0/25。
  - 試験B：素直な19投稿で、正解の行と合う件数。今は 40/40、合格は 2回とも 40/40。

## 2. 現在地（事実。詳細は手元のみ：/tmp/CC報告ファイル/supplier-analysis/）
- 指示書 e（PR #3999）の結果
  - 試験A は 2/25。残った誤りは d800fd79（仕入元 25524）の親の見出しだけ。
  - 試験B は 40/40。
- 仕入元ルールの発送日の欄を付けた場合と外した場合で、差は無かった（9/25 と 9/25。指示書 c で測定、PR #3990）。
- 今のルールにある「」の例文 212個のうち、146個は原文に出てこない書き方の型だった（compare/quote_report_v2.md）。
- prompt_ab には、仕入元ルールの欄を外す --omit-supplier-field はある（backend/app/tools/prompt_ab.py）。差し替える切り替えは無い。
- 案の出どころ：Fable の案（fable/proposal.md §4・§5）。設計者が確かめた。

## 3. 変更（prompt_ab.py のみ）
- 引数 `--supplier-rules-file <path>` を足す。
- ファイルの中身は JSON。仕入元の id（文字列）を鍵にし、値に extraction_* の欄の辞書を置く。
- 投稿の仕入元の id がファイルにあるとき
  - ctx.supplier_context を、ファイルの欄の値で上書きした新しい辞書にして、Gemini の呼び出しと dry-run に渡す。
  - ファイルに書かれていない欄は、DB の値のまま残す。
  - 値が null の欄は、欄を外したのと同じに扱う。
  - 元の ctx は変えない。
- 投稿の仕入元の id がファイルに無いときは、今と全く同じに動く。
- JSONL の行に `supplier_rules_override`（{"file_sha256": …, "supplier_id": …, "fields": [上書きした欄の名前]}）を書く。差し替えたときだけ書く。
- 欄の名前は ^extraction_[a-z_]+$ だけを認め、それ以外はエラーにする。
- ファイルが読めない、または JSON として不正なときは、Gemini を呼ぶ前にエラーで止める。
- --omit-supplier-field と同時に指定したときは、差し替えのあとに外す。
- --config v7 と同時に指定したら、エラーにする（--omit-supplier-field と同じ理由）。
- 仕入元の id の取り方は、ctx に supplier_id がある前提（tcg_extraction.py の ExtractionContext）。実物で確かめる。

## 4. 触らない
- 本番の抽出経路（gemini_extraction_svc.py、tcg_extraction.py）
- gemini_raw_copy_v8.py の関数の中身
- 指示書
- DB と仕入元ルール
- migrations、deploy.yml、scripts/、フロントエンド

## 5. 試験と受入条件
### 5-1. 試験（マージと本番反映の後）
- ルールのファイル
  - 第1段：25524 の案だけ（fable/proposal.md §4.1）
  - 第2段：25524 と 25522（§4.2）
  - 第1段で試験A・試験Bを流し、第2段で試験Bを流す。
- 指示書：e（--config v102 --prompt-name raw_copy_v101_e）
- 費用の上限：合計 1.1 USD
  - 試験A 0.30
  - 試験B 0.20 を2回
  - 第2段の試験B 0.20 を2回

### 5-2. 受入条件
| 基準 | 検証方法 |
|---|---|
| 指定しないときの動きが変わらない | 既存の test_prompt_ab.py がすべて通る |
| ファイルにある id の欄だけが上書きされ、無い欄は DB の値のまま、null の欄は外れる。元の辞書は変わらない | test_prompt_ab.py に足すテスト |
| ファイルに無い id は、今と同じ | test_prompt_ab.py |
| 不正なファイル・不正な欄名・v7 との同時指定はエラー | test_prompt_ab.py |
| JSONL に supplier_rules_override が書かれる | test_prompt_ab.py |
| 本番の経路が変わらない | 差分のファイルが prompt_ab.py・tests・docs・台帳だけ |
| CI が緑 | gh pr checks |

## 6. 外部・過去事例の参照と我々への応用
- 過去事例（社内）
  - PR #3990 の --omit-supplier-field と同じ作り（元の ctx を変えずに写しを渡す）にする。
  - 指示書 e の試験では、書き方を「手順＋例」に変えると誤りが 9/25 から 2/25 に減った。
- 外部事例：Google の公式資料（Context7、2026-10-06）
  - Gemini 3 で答えをそろえたいときは、指示に明確な決まりを書く（https://ai.google.dev/gemini-api/docs/gemini-3）。
  - 例は「正しくできた姿」を見せる（https://ai.google.dev/gemini-api/docs/prompting-strategies）。
- 我々への応用：仕入元ルールも同じ形にし、本番のデータを変えずに、道具の中だけで効き目を測る。

## 7. リスクと戻し方
- リスク：指定しないときの動きが変わるおそれ。
  - 対策：既定は「差し替えなし」にし、既存のテストで守る。
- 戻し方：この PR を revert する。

## 維持の仕組み
- 記録：JSONL の supplier_rules_override（ファイルの sha256 と欄の名前）で、どのルールで流したかを後から確かめられる。
- 守り手: backend/tests/test_prompt_ab.py が CI で毎回通ること。
- 担当：本番の仕入元ルールを書き換えるときは、PO の許可を得て別に行う。
