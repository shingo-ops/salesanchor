---
mode: handoff
---
# 実装カード 段1: 採点の道具に、行ごとの正誤を書き出す出口を足す

親: [design-regression.md](./design-regression.md) §5 段1・§9

この文書は何か: 正解表の1行ずつについて「合っていたか・間違えたか」をファイルに書き出す機能を、今の採点の道具に足すための作業指示です。

- 状態: カード作成済み・カード自己審査済み（§8）・PO 実装承認 未
- 担当: Sonnet（クラウドで実装〜push）。PR は手元で shingo-cc 名義。Opus は審査・マージ判断。
- 社外秘: 仕入元の名前・投稿の原文・投稿 id・行ごとの判定は、リポジトリにも PR にも入れない。試験は作り物のデータだけを使う。

## 読んだ節と照合（Opus、2026-10-31）

- docs/handoff/design-partner-card-ops/guards/00-common.md: プレースホルダを残さない（§5 のパスは実名で書いた）・出力に上限（報告は数だけ）・報告に無い出力を成功と扱わない（§7 で git log を確かめる）。○
- docs/handoff/design-partner-card-ops/guards/03-file.md・docs/handoff/design-partner-card-ops/guards/05-pr.md: 触るファイルを §1 で全部挙げた。PR は手元で shingo-cc 名義（Sonnet は push まで）。○
- docs/handoff/design-partner-card-ops/guards/10-executor.md: 散文で組み立てを頼まない（§2・§4 で形と期待値を全部書いた）。○
- 受領確認: 着手前に、報告の1行目へ「受領確認: card-regression-bin1 を読んだ」と書く。

## 1. 作るもの・触らないもの

- `scripts/accuracy/score_v102.py`（変更。任意の引数 `--verdicts-out` を足す）
- `scripts/accuracy/test_score_v102.py`（追記。§4 の試験）
- `scripts/accuracy/README.md`（追記。使い方を2行）

触らないもの: ほかの `scripts/accuracy/*.py`、`backend/`・`frontend/`・`migrations/`・`.github/`。DB への書き込みは無し。

## 2. 引数と出力

```
python3 -I scripts/accuracy/score_v102.py --gold G.tsv --snapshot-dir DIR --out-dir OUT [--verdicts-out V.tsv]
```

- `--verdicts-out` を付けないとき: 今と1バイトも同じ出力（`result.tsv`・`errors.tsv`・`inputs.sha256`・画面の2行）。
- 付けたとき: 上に加えて V.tsv を書く。V.tsv の置き場所も `check_out_dir()`（`score_v102.py:312-324`）と同じ検査を通す。リポジトリの中なら `STOP:` で終了コード2、何も書かない。
- V.tsv の形: タブ区切り・UTF-8・改行 `\n`・最後の行にも改行。1行目は見出し `key	項目	判定`（`scripts/accuracy/by_group.py` の判定表と同じ見出し。ただし判定に `SKIP` を含むため、by_group.py にはそのまま渡せない。段2の計算専用）。
  - key: 正解表のデータ行の番号（`read_tsv()` が返す `gold` の並びで 1 から数える）。
  - 判定: `OK` / `NG` / `NOWORD` / `SKIP`。`ok`→`OK`、`ng`→`NG`、`na`→`NOWORD`、`skip`→`SKIP`。
- 除外が `ALL` の行（`score_v102.py:214-215`）は1行も書かない。
- それ以外の正解表の行は、項目 `C1` を必ず1行書く。システムがその行を出していない（`score_v102.py:207-210` の投稿まるごと無し、`:217-219` の対応なし）なら `NG`、対応があれば `OK`。
- 対応があった行は、続けて次の8項目を1行ずつ書く。どの段の判定を使うかは固定する。
  - `E1`: 段 Gemini の判定（`:229` の `rec("Gemini", "E1", ...)` と同じ値）
  - `E2`・`E3`: 段 システム の判定。E1 が ok でないときは段 システム が記録されない（`:243-244`）ので `SKIP`。
  - `A1`〜`A5`: 段 通し の判定（`:274` の `rec("通し", fld, ...)` と同じ値）。`judge()` が skip を返した項目は `SKIP`。
- 並び: key の昇順。同じ key の中は `C1, E1, E2, E3, A1, A2, A3, A4, A5` の順。

## 3. 書き方の決まり

- `score()` の戻り値の形は変えない。判定を集める入れ物は、`score()` に任意の引数（例 `verdicts=None`）を足して受け取る。`None` のときは何もしない。
- 正解表の行の番号は、`score()` の最初で `gold` の並びから作る（`{id(g): i for i, g in enumerate(gold, 1)}` で作り、`id(g)` で引く。`gold` の行の辞書は採点の間に作り直さない）。`by_post` の作り方は変えない。
- 集計（`T`）・`errors` の中身と並びは変えない。
- 書く前に §5 V2 の照合を自分で行う。合わなければ V.tsv だけを書かずに（`result.tsv`・`errors.tsv`・`inputs.sha256` はいつもどおり書く） `STOP: 判定の数が集計と合いません` に続けて項目名 で終了コード2。

## 4. 試験（作り物のデータだけ）

既存の `test_score_v102.py` の作り物の作り方をそのまま使う。

- T1 付けないとき: 既存の `test_deterministic_outputs` と同じ入力で、`--verdicts-out` 無しの出力の sha256 が、変更前の本線の道具で作った出力の sha256 と一致する（変更前の値は、変更前のファイルで一度流して試験に書き込む）。
- T2 付けたとき: 2投稿・5行（うち1行は除外 ALL、1行は読み落とし、1行は A1 の除外、1行は E1 が違う）の作り物で、V.tsv の全行が手で書いた期待どおり。
- T3 照合: T2 の V.tsv を項目ごとに数え、`result.tsv` の E1(Gemini)・E2/E3(システム)・A1〜A5(通し) の 正しい・違う・答え無し と、`C1読み落とし` の数に一致。
- T4 V.tsv の置き場所がリポジトリの中なら終了コード2・何も書かない。
- T5 同じ入力を2回流して、V.tsv の sha256 が一致。
- 流し方: `python3 -m pytest scripts/accuracy -q`（既存の試験も全部通る）。結果の全文を PR 本文に貼る。

## 5. 本番での確かめ（クラウドで1回・読むだけ）

`scripts/accuracy/README.md` の「クラウドで測る」「写しを窓口から作る」の手順で、gold_v1 を `$SCRATCH/gold_v1.tsv` に、写しを `$SCRATCH/snapshot` に取り出し、次を1回流す。`$SCRATCH` はシステム指示の scratchpad の絶対パス。

```
python3 -I scripts/accuracy/score_v102.py --gold "$SCRATCH/gold_v1.tsv" --snapshot-dir "$SCRATCH/snapshot" --out-dir "$SCRATCH/out" --verdicts-out "$SCRATCH/out/verdicts.tsv"
```

- V1: `--verdicts-out` 無しでも1回流し、`result.tsv`・`errors.tsv` の sha256 が付けたときと一致。
- V2: V.tsv の数が `result.tsv` と一致（§4 T3 と同じ照合）。
- 報告に書くのは次の数だけ（投稿 id・値・行番号は書かない）:
  - 正解表の行数・除外 ALL の行数・V.tsv に出た key の数
  - 誤りの行の数（key ごとに NG が1つでもある数）と、そのうち C1 が NG の数
  - 項目ごとの NG の数
  - V.tsv・result.tsv・errors.tsv の sha256
- 出力ファイルはクラウドの scratchpad にだけ置く。持ち帰りは `scripts/accuracy/README.md` の「結果の持ち帰り」の手順（本人だけが見られるページ）。

## 6. 停止する条件（停止したら、その時点で報告して終わる）

- 本線の `score_v102.py` の行番号が §2 と5行以上ずれている → 実装せず `BLOCKED: 行がずれている`。
- 窓口の取り出しが `STOP:`・429 で止まる → 1回だけやり直す。それでも止まれば `BLOCKED:`。
- 照合（V2）が合わない → 原因を推測で直さず `NEEDS_DECISION: 照合が合わない` に続けて項目と数。

## 7. 終わりの条件

- `python3 -m pytest scripts/accuracy -q` が全部通る。
- §5 の数が報告にある。
- リポジトリの差分は §1 の3ファイルだけ（`git diff --name-only origin/main...HEAD`）。
- 報告の最後の行は `DONE` / `BLOCKED:` ＋理由 / `NEEDS_DECISION:` ＋内容 のどれか。

## 8. カードの自己審査（2026-10-31 Opus。同じ AI による自己審査）

- 判定: APPROVE
- 設計との整合: design §5 段1（付けないときは同じ・行ごとの判定・誤りの数を数える）を §2・§4 T1・§5 で満たす。結果の列の決め方（design §4: 違うが1つでもあれば誤り・読み落としも誤り）は、V.tsv の C1 と各項目から機械的に作れる。
- 実物との照合: 行番号は origin/main 67ae676b3 の `scripts/accuracy/score_v102.py` で確かめた（:161-178 judge、:181-282 score、:207-219 読み落とし、:229・:243-244・:274 の判定の記録、:312-324 check_out_dir、:334-365 main）。
- 残る未確認: 誤りの行の数（§5 で分かる）。30 行未満なら design §6 の決まりで段2へ進まない。

END OF CARD
