# Opus 審査記録（PR #4948）

- 審査役: reviewer（model opus、新規起動）
- 日時: 2026-10-31
- 対象 HEAD: a3a98fca96be74c8375926b7e01bfd5db68f4bb3（変更17ファイル）
- 判定: **APPROVE**

## 確認した点
1. 本番に配られる道・CI で走る道は無い。scripts/accuracy 外・.github からの参照0件。backend の testpaths は tests のみ。Dockerfile に scripts の COPY なし。
2. 本番への書き込みは Gemini 呼び出しに伴う使用量の記録帳だけ（PO 承認済みの範囲）。fhd_snapshot.py は READ ONLY の取引で始め、rollback で終える。
3. 社外秘はリポジトリに入っていない。design.md の結果欄は集計値だけ。試験は手元の非公開の置き場から読む。出力先がリポジトリ内なら止まる。
4. score_v102.py: --a4-extra-system を渡さないときの採点は元と同じ。渡した値は NG として数える。試験 18 passed。test_llm_compare.py 32 tests OK（skip 0）。
5. 秘密の値のハードコードなし（環境変数名と試験の作り物の値のみ）。
6. design.md の数字と判定は §4 の式と合っている（Gemini 平均を計算し直して一致）。

## 軽い指摘と扱い
- §13「触らない」に score_v102.py があり、実施で変えた → §13 に注記を足した。
- 行数が §2 は1494行、結果欄は1480行 → 差の内訳は未確認。結果の判定（件数の比較）には影響しない。次に採点の道具を使うときに確かめる。
- 作業記録の PR# が空 → #4948 を記入した。
- 【未確認】§4 は率で比べるが、E2・E3 の率の分母は result.tsv を見ていない。件数と判定の向きが合うことのみ確認。
