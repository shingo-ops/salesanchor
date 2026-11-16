---
mode: handoff
---
# 実装カード：毎週の数えの呼び出しを減らす（deploy-db-stall 段7 (c) の直し・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（呼び出しを減らす直しと、その試験・timeout だけ） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/deploy-lock-count`） | ○ |
| 6 | 書式は実例で示す（動きは design.md §19-4 の 2b. にそのまま） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順5〜7） |
| 8 | 件数と名前を対で出す | ○（手順5） |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は前後の文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write/Edit で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/deploy-db-stall/design.md` §19 第3.3版（このブランチにある）。作る中身は §19-4 の 2b.（決まり (i)〜(iii)）、D6、赤の実演の7つ目、`timeout-minutes: 30`。§19-4 と §19-8 を全部読んでから作る。設計とこのカードが食い違ったら設計を正とし、記録して続ける。設計に無い変更はしない。
- 1回目の実装（077a2e388、カード `card-c.md`）は済んでいる。試験15件は合格、赤の実演6つは期待どおり。今回はそれを壊さずに足す。
- PO 承認: 2026-11-13「1」と、2026-11-14「PRマージ、デプロイまで完走させてくれ」。
- 触るのは次の3ファイルだけ: `scripts/ops/count-deploy-lock-failures.sh`、`.github/workflows/weekly-deploy-lock-count.yml`、`backend/tests/ops/test_deploy_lock_count.py`。

## 作りの決め（Opus が決めた。この形で作る）
- `list_day` が `runs.tsv` に書く列を、`id`・`created_at`・`run_attempt` に `run_started_at`・`status` を足した5列にする（`jq` の `(.run_started_at // "")`・`(.status // "")`）。
- 主の繰り返しで、`run_started_at` が空でなく、それを秒にした値が `SINCE_E` より小さい run は、`process_attempt` を呼ばずに飛ばす。`created_at` を秒にした値が `UNTIL_E` 以上の run も飛ばす。飛ばした run は出力に出さず、どの数にも入れない。
- `process_attempt` に引数を2つ足す（一覧の `run_started_at` と `status`）。回の番号が一覧の `run_attempt` と同じで、2つとも空でないときは、回の API（`attempts/${n}`）を呼ばず、その2つを `started`・`status` に使う。それ以外（前の回、または一覧に値が無い）は今のとおり回の API で読む。
- `.github/workflows/weekly-deploy-lock-count.yml` の job `count` に `timeout-minutes: 30` を足す（`runs-on` の次の行）。
- 試験 D6 を足す（§19-4 の D6 のとおり、`--from-dir` の作り物で）。名前は `test_d6_skips_out_of_window_runs_without_calls` と `test_d6_last_attempt_uses_list_fields`。今の15件は変えない（作り物の一覧に `run_started_at` が無い試験は、決まり (iii) で今と同じ読み方になる）。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 毎週の数えの呼び出しを減らす（段7 (c) の直し）の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` のあと、`git branch --list release/deploy-lock-count` を記録。無ければ `bash scripts/new-worktree.sh release/deploy-lock-count`（`--claude` なし）、あればそのフォルダを使う。以後の Bash は `cd $HOME/worktrees/salesanchor/release-deploy-lock-count && ` で始める。`git merge --no-edit origin/release/deploy-lock-count` を流す（ぶつかりが出たら **停止**）。`git log -1 --format=%H` を記録する。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前回と同じ。記録して続ける）。
4. design.md §19-4 と §19-8 を Read し、上の「作りの決め」のとおり3ファイルを Edit で直す。
5. カード `card-c.md` の手順7と同じ方法で Python 3.12 の環境を作り、`/tmp/v312/bin/python -m pytest backend/tests/ops/test_deploy_lock_count.py -p no:cacheprovider -o addopts="" -q` の全文を記録する。試験の名前と結果を1行ずつ並べる（17件が期待）。赤があれば直す。直しても赤なら記録して続ける。
6. `bash -n scripts/ops/count-deploy-lock-failures.sh` と、使えれば `shellcheck` の出力を記録する。
7. 赤の実演7（K19-3）: 削除の命令を使わず、新しいフォルダ `/tmp/red/7` に台本と試験を写し、写しの台本から「期間の外の run を飛ばす」処理だけを消して試験を流す。D6 の1つ目が赤になることを記録する（壊した行の差分・赤になった試験の名前・期待どおりか ○×）。作業フォルダの台本は壊さない。最後に `git status --short` を記録する。
8. `git add` を上の3ファイルだけに流し、`git diff --cached --stat` を記録する。
9. commit（文は Write で `/tmp/impl/commit-msg.txt` に書いて `git commit -F /tmp/impl/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `fix(ops): skip out-of-window deploy runs to stay under the API rate limit`。
10. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/deploy-lock-count`（force は禁止）。push の出力の全文を記録する。
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
