# design: 比較試験の道具で v9 の試験版指示書を使えるようにする（trial1・商品ブロックの中だけ）

- 作成：2026-10-05 Opus（設計）
- PO 承認
  - 2026-10-05「商品ブロックごとに区切れているので gemini にはそれだけ依頼したい」
  - 「y→実行して動作確認まで完了させる、正答率の変化が見たい」
- recon：同じフォルダの recon.md（実装担当が作る）

## 1. 目的（KGI）
- Gemini の書き写しで、発送（ship）・状態（state）を「その商品のブロックの中の行」からだけ写すように、指示書を変える。
- 変えたときの正答率を、v9 と同じ投稿・同じ正解で比べる。
- 本番の経路は変えない。比較試験の道具（prompt_ab）だけで試す。

## 2. 現在地（事実）
- prompt_ab の --config v9 は、`backend/app/prompts/raw_copy_v9.txt` を固定で読む。
  - origin/main:backend/app/services/gemini_raw_copy_v9.py:18
  - origin/main:backend/app/tools/prompt_ab.py:186-189
- 別の指示書で試す手段が無い。
  - prompt_ab の引数は --config v7|v8|v9 だけ（origin/main:backend/app/tools/prompt_ab.py:306-316）。
- prompt_ab は本番の表には書かない。費用の台帳（llm_usage_events）だけに書く。
  - origin/main:backend/app/tools/prompt_ab.py:8-10
- v9 は本番の経路から呼ばれない（origin/main:backend/app/services/gemini_raw_copy_v9.py:5）。

## 3. 変更（これだけ）
1. `backend/app/tools/prompt_ab.py` に引数 `--prompt-name NAME` を足す。
   - --config v9 のときだけ使える。v7・v8 で指定したら、引数エラーで止める。
   - NAME は正規表現 `^raw_copy_v9_[a-z0-9_]+$` に合うものだけ受け付ける。パスの区切りや「..」は通さない。
   - `backend/app/prompts/<NAME>.txt` が無ければ、Gemini を呼ぶ前にエラーで止める。
   - 指定したときは、その本文を v9 の指示書の代わりに使う。受け取り（parse_v9_response）・型・設定は v9 のまま。
   - 指定しないときは、今と全く同じ動き（raw_copy_v9.txt）。
   - 出力の JSONL の各行に `"prompt_name"` を足す。指定なしのときは "raw_copy_v9"。どの指示書の結果か後から分かるようにする。
   - --dry-run でも、指定した指示書で組み立てた先頭の行を表示する。
2. `backend/app/prompts/raw_copy_v9_trial1.txt` を足す。
   - 本文は設計者（Opus）が用意したものを、そのまま置く。中身を変えない。
3. テストを足す（backend/tests/test_prompt_ab.py）。
   - 指定なし：raw_copy_v9.txt の本文が使われる。
   - --prompt-name raw_copy_v9_trial1：trial1 の本文が使われる。
   - 名前の形が違う（例 `../x`、`raw_copy_v8_x`、`raw_copy_v9_A`）：止まる。
   - 存在しない名前：止まる。
   - --config v8 との組み合わせ：止まる。
   - JSONL の行に prompt_name が入る。

## 4. 触らない
- gemini_raw_copy_v8.py・gemini_raw_copy_v9.py の処理
- raw_copy_v9.txt の本文
- 本番の抽出経路（tcg_extraction・extraction_shadow_svc・gemini_extraction_svc）
- DB・マイグレーション・deploy.yml・scripts/

## 5. 試験のしかた（マージと本番反映の後、PO 実行）
- 対象：11投稿（extraction_shadow_runs.id）。
  - 10投稿：v9 で、その商品だけの行がブロックの外に置かれた投稿。
  - 1投稿：投稿の冒頭の発送日を商品に写した投稿。悪くなっていないかを見る確認用。
- 実行
  - コマンド：`python -m app.tools.prompt_ab --config v9 --prompt-name raw_copy_v9_trial1 --thinking-level high --repeat 1 --max-cost-usd 0.5 --test-id trial1-v9t1 --out-dir /tmp/prompt_ab/trial1-v9t1`
  - 費用の目安：v9 high の実測は 1投稿あたり約 0.0147 USD。試験版は指示書が約1.7倍に長くなるので、入力の分だけ増える。上限は 0.5 USD で止める。
- 採点
  - 正解表（社外秘・手元のみ）と、v9 の既存の出力・試験版の出力を、同じ採点の決まりで比べる。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| 指定なしで動きが変わらない | テスト：指定なしで raw_copy_v9.txt の本文が使われる。既存のテストがすべて通る |
| trial1 の本文が使われる | テスト＋dry-run の表示 |
| 不正な名前・存在しない名前・v8 との組み合わせで止まる | テスト（Gemini を呼ばない） |
| 出力に prompt_name が残る | テスト＋試験後の JSONL を確認 |
| 本番の経路が変わらない | 差分が prompt_ab.py・prompts/raw_copy_v9_trial1.txt・テスト・docs だけ |
| CI が緑 | gh pr checks |

## 7. 外部・過去事例の参照と我々への応用
- Google の公式の説明（Context7 で確認、2026-10-05）
  - 出典：https://ai.google.dev/gemini-api/docs/prompting-strategies
  - 例（few-shot）は「正しくできた姿」を見せるもので、入れることを勧めている。
  - 例が多すぎると、例に過学習する。
  - 例どうしの形式を揃える。
- この事例から、試験版の例は、正しい書き出し（JSON）付きで、形式を v9 と同じにした。
- 試験の投稿の文をそのまま例にしない（点数が実力より高く出るのを避ける）。
  - 例の47行のうち、試験の11投稿と同じ文の行は「シュリ無し」「発送日相談」の2行だけ。どちらも短い一般的な言葉で、「シュリ無し」は v9 の例にもともとある。

## 8. リスクと戻し方
- リスク：試験の道具の変更なので、本番の解析への影響は無い。
- 戻し方：この PR を revert する。

## 維持の仕組み
- 記録: JSONL の prompt_name で、どの指示書の試験結果かを後から確かめられる。v9 のときだけ入れる。v7・v8 の行は今のまま。
- 守り手: test_prompt_ab.py のテスト（名前の検査・存在の検査・v9 限定・未指定時の既定）が、CI で毎回通ること。
- 担当: 試験版の指示書を本採用するときは、別の設計と PR で raw_copy_v9.txt か DB の指示書へ移す。trial1 のファイルは、そのまま本番の経路で使わない。
