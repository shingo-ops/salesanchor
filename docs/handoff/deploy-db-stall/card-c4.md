---
mode: handoff
---
# 実装カード：job の記録を引けるようにする（deploy-db-stall 段7 (c) の原因の直し・第3.5版・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（記録を引く直しと、その試験だけ） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/deploy-lock-count-esc`） | ○ |
| 6 | 書式は実例で示す（制御文字の消し方は下の「作りの決め」） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順5〜7） |
| 8 | 件数と名前を対で出す | ○（手順5） |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は前後の文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write/Edit で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/deploy-db-stall/design.md` §19-16（第3.5版。このブランチにある）。§19-4・§19-15・§19-16 を全部読んでから作る。設計とこのカードが食い違ったら設計を正とし、記録して続ける。設計に無い変更はしない。
- 第3.4版は本線にある（180710bff）。試験19件は合格済み。今回はそれを壊さずに足す。
- 原因（実物）: GitHub の実行機の gh が、job の記録に端末の制御文字があるとして出力を断る。理由の文 `the response contains terminal escape sequences; pass --allow-escape-sequences to output it anyway`。
- PO 承認: 2026-11-13「1」と、2026-11-14「PRマージ、デプロイまで完走させてくれ」。
- 触るのは次の2ファイルだけ: `scripts/ops/count-deploy-lock-failures.sh`、`backend/tests/ops/test_deploy_lock_count.py`。

## 作りの決め（Opus が決めた。この形で作る）
- `fetch` の `gh api` 呼び出し: `api_path` が `*/logs` に当たるときだけ `gh api --allow-escape-sequences "${api_path}"`、それ以外は今のまま `gh api "${api_path}"`。失敗の文の受け方（`fetch-err.txt`・`?` 以降を消す・160字）は変えない。
- 記録を引けた直後（`fetch "repos/${REPO}/actions/jobs/${job}/logs" ...` が成功した後、最初の `grep` の前）に、`${lf}` から制御文字を消す関数 `strip_esc` を呼ぶ。中身の形:
  - `local esc; esc="$(printf '\033')"`
  - `LC_ALL=C sed "s/${esc}\[[0-9;]*[A-Za-z]//g" "${lf}" | LC_ALL=C tr -d '\033' > "${lf}.clean"` のあと `mv "${lf}.clean" "${lf}"`
  - `--from-dir` で写したときも同じ所を通る（呼ぶ所は fetch の外の1か所）。
- 数える文言・表の7列・出力の形・知らせの形は変えない。
- 試験を足す。名前は `test_d8_escape_sequences_are_stripped_before_counting` と `test_d8_allow_escape_flag_only_on_log_calls`。今の19件は変えない。
  - 1つ目（`--from-dir`）: 上限失敗の回の作り物の記録を、行の前・途中・後ろに `\x1b[31m` と `\x1b[0m` を入れた形で作る（例: `<時刻> \x1b[31mlock conflict; \x1b[0mretry limit reached`）。上限失敗が 1 と数えられ、出力全体と知らせのファイルに `\x1b` が無いことを確かめる。
  - 2つ目: 1つ目と同じ作り物のフォルダを、今の試験の作り物を作る関数（`--from-dir` に渡しているもの）で作る。`tmp_path/bin/gh` に bash の偽の gh を置く。偽の gh は (1) 受け取った引数全部を1行で環境変数 `FAKE_ARGS` のファイルに足す (2) 最後の引数（API のパス）を、台本の `fetch` の2つ目の引数と同じ名前（`runs/<D>.json`・`runs/<D>-p<N>.json`・`attempts/<key>.json`・`jobs/<key>.json`・`logs/<job>.log`。台本の `fetch "` の行で対応を読む）に直し、環境変数 `FAKE_FIXTURE` のフォルダにそのファイルがあれば中身を出して 0、無ければ標準エラーに `HTTP 404: Not Found` を書いて 1 で終わる。PATH の先頭に置き、`GH_TOKEN` は作り物の値で、`--from-dir` なしで流す。`FAKE_ARGS` の中で、`/logs` で終わる行が1行以上あり、その行すべてに `--allow-escape-sequences` が有り、ほかの行すべてに無いことを確かめる。上限失敗が 1 と数えられることも確かめる。
- 赤の実演9: 写しの台本で `strip_esc` を呼ぶ行を消す → 1つ目が赤。赤の実演10: 写しの台本で `--allow-escape-sequences` を消す → 2つ目が赤。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード job の記録を引けるようにする（段7 (c) の原因の直し・第3.5版）の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` のあと、`git branch --list release/deploy-lock-count-esc` を記録。無ければ `bash scripts/new-worktree.sh release/deploy-lock-count-esc`（`--claude` なし）、あればそのフォルダを使う。以後の Bash は `cd $HOME/worktrees/salesanchor/release-deploy-lock-count-esc && ` で始める。`git merge --no-edit origin/release/deploy-lock-count-esc` を流す（ぶつかりが出たら **停止**。`git switch -C` は使わない）。`git log -1 --format=%H` を記録する。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前と同じ。記録して続ける）。
4. design.md §19-16 を Read し、上の「作りの決め」のとおり2ファイルを Edit ツールで直す（python や sed での書き換えはしない）。
5. カード `docs/handoff/deploy-db-stall/card-c.md` の手順7と同じ方法で Python 3.12 の環境を作り、`/tmp/v312/bin/python -m pytest backend/tests/ops/test_deploy_lock_count.py -p no:cacheprovider -o addopts="" -q` の全文を記録する。試験の名前と結果を1行ずつ並べる（21件が期待）。赤があれば直す。直しても赤なら記録して続ける。
6. `bash -n scripts/ops/count-deploy-lock-failures.sh` と、使えれば `shellcheck` の出力を記録する。
7. 赤の実演9と10: 削除の命令を使わず、新しいフォルダ `/tmp/red/9`・`/tmp/red/10` に台本と試験を写し、上の「作りの決め」の行だけを消して試験を流す。それぞれ壊した行の差分・赤になった試験の名前・期待どおりか ○× を記録する。作業フォルダの台本は壊さない。最後に `git status --short` を記録する。
8. `git add` を上の2ファイルだけに流し、`git diff --cached --stat` を記録する。
9. commit（文は Write で `/tmp/impl/commit-msg.txt` に書いて `git commit -F /tmp/impl/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `fix(ops): read deploy job logs that contain color codes`。
10. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/deploy-lock-count-esc`（force は禁止）。push の出力の全文を記録する。
11. PR は作らない。マージしない。workflow を手で流さない。

## 停止
- 止めるのは手順2のぶつかり、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- Bash に psql の語を書かない。git は1命令ずつ流す。sleep しない。削除の命令（rm）を使わない。
- 台帳の登録ファイルは commit しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 手順2〜10の生出力の全文を `/tmp/impl/手順番号.txt` に保存する（commit しない）。
- 手順ごとの結果は別々の Bash 呼び出しで echo 1つだけ・300字まで・先頭に「手順N:」を付けて出す。
- 最後の1行は `DONE` か `BLOCKED: 理由の1行`（終端合図）。

END OF CARD
