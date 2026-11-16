---
mode: handoff
---
# 実装カード：読めなかった理由を残す（deploy-db-stall 段7 (c) の直し・第3.4版・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（理由を残す直しと、その試験だけ） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/deploy-lock-count-diag`） | ○ |
| 6 | 書式は実例で示す（出力の形は design.md §19-15 の決め3） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順5〜7） |
| 8 | 件数と名前を対で出す | ○（手順5） |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は前後の文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write/Edit で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/deploy-db-stall/design.md` §19-15（第3.4版。このブランチにある）。§19-4 と §19-15 を全部読んでから作る。設計とこのカードが食い違ったら設計を正とし、記録して続ける。設計に無い変更はしない。
- 第3.3版は本線にある（6bc263b42）。試験17件は合格済み。今回はそれを壊さずに足す。
- PO 承認: 2026-11-13「1」と、2026-11-14「PRマージ、デプロイまで完走させてくれ」。
- 触るのは次の2ファイルだけ: `scripts/ops/count-deploy-lock-failures.sh`、`backend/tests/ops/test_deploy_lock_count.py`。

## 作りの決め（Opus が決めた。この形で作る）
- `fetch` の `gh api` の標準エラーを `/dev/null` でなく `${WORK}/fetch-err.txt` に受ける。失敗したら、空でない最初の行から `?` 以降を消し、160字で切った文を変数 `LAST_FETCH_REASON` に入れる（空なら `理由なし`）。`--from-dir` でファイルが無いときは `作り物なし`。成功したら `LAST_FETCH_REASON` は空にする。
- `mark_unreadable` に引数を1つ足す（段の名前: `回`・`job一覧`・`記録`・`一覧`・`未完了`・`時刻なし`）。呼ぶ所すべてで段の名前を渡す。中で連想配列 `REASONS["<段> / <理由>"]` を1つ増やす。理由は、fetch の失敗なら `LAST_FETCH_REASON`、それ以外（未完了・時刻なし・1,000件・jq の読めない）は `-`。
- 出力: 「読めなかった: N」の次の行に `読めなかった理由:`、その下に `  <段> / <理由>: <件数>` を sort して並べる。
- 知らせの本文: 「読めなかった N: …」の行の次に、同じ行を最大5行足す。
- 表の行（7列）は変えない。
- 試験 D7 を足す（§19-15 のとおり）。名前は `test_d7_unreadable_reasons_from_fixture` と `test_d7_reason_strips_query_from_gh_error`。2つ目は、`tmp_path/bin/gh` に「標準エラーへ `HTTP 403: x (https://a.example/b?sig=SECRET)` を書いて 1 で終わる」小さな bash を置き、PATH の先頭にして `--from-dir` なしで流す（`GH_TOKEN` は空でない作り物の値）。出力に `SECRET` が無く、`https://a.example/b` が有ることを確かめる。今の17件は変えない。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 読めなかった理由を残す（段7 (c) の直し・第3.4版）の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` のあと、`git branch --list release/deploy-lock-count-diag` を記録。無ければ `bash scripts/new-worktree.sh release/deploy-lock-count-diag`（`--claude` なし）、あればそのフォルダを使う。以後の Bash は `cd $HOME/worktrees/salesanchor/release-deploy-lock-count-diag && ` で始める。`git merge --no-edit origin/release/deploy-lock-count-diag` を流す（ぶつかりが出たら **停止**）。`git log -1 --format=%H` を記録する。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前と同じ。記録して続ける）。
4. design.md §19-15 を Read し、上の「作りの決め」のとおり2ファイルを Edit で直す。
5. カード `docs/handoff/deploy-db-stall/card-c.md` の手順7と同じ方法で Python 3.12 の環境を作り、`/tmp/v312/bin/python -m pytest backend/tests/ops/test_deploy_lock_count.py -p no:cacheprovider -o addopts="" -q` の全文を記録する。試験の名前と結果を1行ずつ並べる（19件が期待）。赤があれば直す。直しても赤なら記録して続ける。
6. `bash -n scripts/ops/count-deploy-lock-failures.sh` と、使えれば `shellcheck` の出力を記録する。
7. 赤の実演8: 削除の命令を使わず、新しいフォルダ `/tmp/red/8` に台本と試験を写し、写しの台本から `REASONS` を1つ増やす行だけを消して試験を流す。D7 の1つ目が赤になることを記録する（壊した行の差分・赤になった試験の名前・期待どおりか ○×）。作業フォルダの台本は壊さない。最後に `git status --short` を記録する。
8. `git add` を上の2ファイルだけに流し、`git diff --cached --stat` を記録する。
9. commit（文は Write で `/tmp/impl/commit-msg.txt` に書いて `git commit -F /tmp/impl/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `fix(ops): keep the reason when a deploy log cannot be read`。
10. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/deploy-lock-count-diag`（force は禁止）。push の出力の全文を記録する。
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
