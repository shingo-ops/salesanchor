# クラウドで練習問題を流す手順（クラウドの担当が読む）

> この文書は何か: クラウドの使い捨て環境で練習問題を流し、結果を枝に置くまでの手順。親: [../quiz.md](../quiz.md)

引数: `PHASE`（before か after）・`REV`（測る版の commit。依頼文で渡す）。下の手順の `<PHASE>`・`<REV>` を置き換える。

1. リポジトリの直下で `git fetch origin release/requirement-library-design main`。
2. 練習問題の道具を写す: `mkdir -p /tmp/quiz && for f in runall.sh prompts.tsv count.py; do git show origin/release/requirement-library-design:docs/handoff/requirement-library/quiz/$f > /tmp/quiz/$f; done`
3. 測る版の写しを2つ作る: `git worktree add --detach /tmp/qb1 <REV>` と `git worktree add --detach /tmp/qb2 <REV>`。写しの中は何も変えない。
4. `mkdir -p /tmp/out` のあと、2回分を並べて流す: `nohup bash /tmp/quiz/runall.sh /tmp/out /tmp/qb1 1 > /tmp/run1.log 2>&1 &` と `nohup bash /tmp/quiz/runall.sh /tmp/out /tmp/qb2 2 > /tmp/run2.log 2>&1 &`。
5. 5分おきに `cat /tmp/out/exits.txt` を見る。`ALLDONE` が2行になるか、`/tmp/out/DIRTY.txt` ができたら次へ。150 分たっても終わらなければ、そこまでの分で次へ進み、終わらなかったことを書く。
6. `python3 /tmp/quiz/count.py /tmp/out` を流し、出力全文をそのまま返事に貼る。
7. 結果を置く: `bash scripts/new-worktree.sh release/requirement-library-quiz-<PHASE> --claude` で作業場所を作り、その中へ cd する。`docs/handoff/requirement-library/quiz/<PHASE>/` を作り、`/tmp/out` の `result.tsv`・`exits.txt`・`DIRTY.txt`（あれば）・`*.answer.txt` を写す。`*.jsonl` と `*.err` は `tar czf raw.tgz` にまとめて同じ所へ置く。
8. その作業場所で commit し、`git push -u origin release/requirement-library-quiz-<PHASE>`。PR は作らない。
9. 最後の返事: 手順6の出力全文、push した commit、各段の成否。推測で埋めない。止まったら止まった所と生のエラーを書いて終える。

守ること: 製品のコード・設定・`.claude/` を変えない。秘密の値を表示しない。
