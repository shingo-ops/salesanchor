# 正答率の採点の道具（便2）

- 正解表とシステム結果の写しを照らし合わせ、項目ごとの正答率を出す。読み取り専用・標準ライブラリのみ。DB には接続しない。
- 実行: `python3 -I scripts/accuracy/score_v102.py --gold <gold_v1.tsv> --snapshot-dir <snapshot/> --out-dir <出力先>`
- 出力先はリポジトリの外だけ（中を指すと拒否）。`result.tsv`（集計）・`errors.tsv`（違う件。社外秘）・`inputs.sha256` ができる。
- 同じ入力なら出力の sha256 は一致する。想定外の値（A4・除外・列不足・綴り違い）があると、`STOP:` を出して終了コード2で止まる。
- 正解表・写し・出力はリポジトリに入れない。テスト: `python3 -m pytest scripts/accuracy -q`（作り物のデータだけ）。
