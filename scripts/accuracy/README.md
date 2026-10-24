# 正答率の採点の道具（便2）

- 正解表とシステム結果の写しを照らし合わせ、項目ごとの正答率を出す。読み取り専用・標準ライブラリのみ。DB には接続しない。
- 実行: `python3 -I scripts/accuracy/score_v102.py --gold <gold_v1.tsv> --snapshot-dir <snapshot/> --out-dir <出力先>`
- 出力先はリポジトリの外だけ（中を指すと拒否）。`result.tsv`（集計）・`errors.tsv`（違う件。社外秘）・`inputs.sha256` ができる。
- 同じ入力なら出力の sha256 は一致する。想定外の値（A4・除外・列不足・綴り違い）があると、`STOP:` を出して終了コード2で止まる。
- 正解表・写し・出力はリポジトリに入れない。テスト: `python3 -m pytest scripts/accuracy -q`（作り物のデータだけ）。

## クラウドで測る（ADR-1043）
- 正解表は本番 DB に置いてある。クラウドでは次の 2 行で測る（`fetch_gold.py` は読むだけの窓口から取り出し、sha256 と行数が版の記録と一致したときだけファイルにする）。
  1. `python3 scripts/accuracy/fetch_gold.py --version gold_v1 --out /tmp/gold_v1.tsv`
  2. `python3 -I scripts/accuracy/score_v102.py --gold /tmp/gold_v1.tsv --snapshot-dir <snapshot/> --out-dir <出力先>`
- 止まったとき: 「sha256 が違う」＝取り出しが壊れた（ファイルは書かれない。もう一度）。「版がありません」＝まだ投入前。
- 正解表の投入は Opus が行う（`gold_to_sql.py` で作った投入 SQL をリポジトリの外で流す）。

## 写しを窓口から作る（fetch_snapshot.py）
- 使い方（1 行）: `python3 -I scripts/accuracy/fetch_snapshot.py --gold-version gold_v1 --out-dir <DIR>`（`--engine` 既定 `v102-f_ct`、`--batch` 既定 25）。正解表の投稿ごとに `<DIR>/<投稿id>.tsv`（14 列）を作る。0 行の投稿はファイルを作らない。
- 出力先 `<DIR>` はリポジトリの外に置く（クラウドは scratchpad）。写しは社外秘。共有しない・GitHub に載せない。
- 最後の 1 行: `posts=… with_rows=… rows=… fetched_at=… engine=…`（投稿id・値は出さない）。
- 止まる条件（`STOP:` を出して終了コード 1、ファイルは 1 つも書かない）: HTTP が 200 でない／rc が 0 でない／見出しが想定の 15 列と違う／返った行数が limit 以上／値に `\` を含む／値が 10240 文字以上／投稿数が版の記録と違う／`<DIR>` に既に .tsv がある／投稿id が UUID の形でない。
