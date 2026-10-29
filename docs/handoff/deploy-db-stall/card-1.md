# 実装カード — deploy-db-stall 段1 作り直し（第8.1版・Sonnet）

受領確認: 着手前に「カード deploy-db-stall 段1 作り直しを受領」と1行返す。

- 設計: docs/handoff/deploy-db-stall/design.md 第8.1版（§4・§6・§14。このブランチに commit 済み、Architect APPROVE）。設計の文面がこのカードと食い違ったら設計を正とし、止めて NEEDS_DECISION。
- PO 承認: 2026-10-29「1」（正式な設計にまとめ、審査に通してから1つずつ直す）。
- 経緯: 第7版の実装 PR #4861（merge 46f2009b）は run_py の `$!` の wait で本番反映が止まり、PR #4862（merge fd85b946）で戻した。今回は #4861 を入れ直し、run_py の標準エラーの扱いと試験だけを変える。
- 作業場所（作成済み）: /Users/tanizawashingo/worktrees/design-inbox-brushup/release-py-migration-lock-timeout-v2（ブランチ release/py-migration-lock-timeout-v2、origin/main fd85b946 起点）。git は必ず `git -C <この絶対パス>` で使う。cd と変数入りのパスは使わない。
- 最初に作業場所で `./scripts/dev/executor-preflight.sh` を実行し、出力を /tmp/CC報告ファイル/deploy-db-stall/impl-v2/preflight.txt に保存する。落ちたら BLOCKED。
- ファイルの編集は Edit/Write ツールで行う（git revert を除く）。
- 生出力はすべて /tmp/CC報告ファイル/deploy-db-stall/impl-v2/ に保存する。

## やること
1. #4861 を入れ直す: `git -C <作業場所> revert --no-edit fd85b946a132f466a1358e44cc1e20f4340c7ac8`。衝突したら止めて BLOCKED。終わったら git log -2 と git show --stat HEAD を保存。
2. docs/handoff/deploy-db-stall/card-1.md を、このカードの全文で上書きする（Write）。
3. scripts/run_all_migrations.sh の run_py（§4-2・§14-2）:
   - 標準エラーを `2>"${errlog}" || rc=$?` で一時ファイルに書き、次の行で `cat "${errlog}" >&2`。run_sql（同じファイルの run_sql の該当行）と同じ形にする。
   - tee・プロセス置換・`$!`・wait を消す。共通関数に出す場合も、抜き出し範囲（`^SQL_LOCK_TIMEOUT=` 〜 run_sql の閉じ括弧）の中のコメント以外に `$!`・`>(`・単語の wait が残らないこと。コメントにもこの3つを書かない。
   - ほか（入口経由・再試行・開始行の echo 等）は #4861 のまま変えない。
4. S3 を .github/workflows/migration-test.yml の S2 と同じ段に足す（§4-3）: 抜き出し範囲をコメント行（`^[[:space:]]*#`）を除いて取り、`grep -F '$!'`・`grep -F '>('`・`grep -wE 'wait'` のどれかが当たれば失敗。一時コピーで第7版の行（`git show 46f2009b:scripts/run_all_migrations.sh`）に対して流すと赤、今の版で緑になることを手元で示し保存する。
5. R5 を tests/sandbox/migration-read-probe.sh に足す（§4-3 の R5 の項を全部読んでから作る）:
   - 偽 docker は PATH の先頭に置く外部の実行ファイル。シェル関数は使わない。
   - BACKEND は固定名（例 sb-fake-backend）。引数にその名前がある呼び出しだけ偽物にし、ほかは PATH を変える前に `command -v docker` で取った本物の絶対パスへ渡す。
   - 動きの切り替え（rc 0／1回目 lock timeout→2回目 rc 0）と回数は export した環境変数かファイルで渡す。
   - make_parent と同じく別の bash で「抜き出しを eval → read_probe_start → run_py」を流し、その bash を `timeout 30` で包む。BACKEND・DATABASE_URL は R5 の側で足す。`SQL_RETRY_SLEEP_SEC=1`。
   - 判定: 30秒以内に rc 0、"lock conflict; retry" の回数が期待どおり、終わった後に裏の輪が残っていない。
   - R1〜R4 は #4861 のまま（tests/sandbox/migration-run-sql-retry.sh）。
6. ADR-1037 と docs/handoff/migration-lock-timeout/design.md の追記は #4861 のまま。足りなければ「第8版で run_py の標準エラーを run_sql と同じ形にした（docs/handoff/deploy-db-stall/design.md §14）」を ADR-1037 の追記に1行足す。ADR を変えたら `node scripts/generate-adr-index.js`。
7. 確かめる: bash -n（変えたシェル全部）、`node scripts/tests/test-process-artifacts.js`、S3 の赤緑（手順4）。
8. commit・push・PR を3段に分け、各段のあとで確かめる。
   - commit: 「feat: Python の移行にもロック待ち1秒と再試行を付ける（作り直し・待ち方を直す）」。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。git log -3 で確かめる。
   - push: `git -C <作業場所> push -u origin release/py-migration-lock-timeout-v2` を単独で。
   - PR: `bash scripts/gh-pr-create-safe.sh` で起票。本文は Write で作ったファイルを --body-file で渡す。shingo-cc 名義を確かめる。本文に recon・設計（第8.1版）・対象ADR ADR-1037・PO承認・#4861/#4862 との関係・触るファイル全部（設計書を含む）・削除するファイル（git diff origin/main --stat で確かめる）。Evaluator は画面の変更なしで Skip。GO 記録の欄は作らない（設計担当が書く）。.pr-number と gh pr list --head の番号が一致するか確かめる。
9. sandbox 試験を GitHub で流す: `gh workflow run sandbox-test.yml --ref release/py-migration-lock-timeout-v2` で migration-read-probe（R5 を含む）と migration-run-sql-retry を流す（入力名は sandbox-test.yml を読んで決める）。完了は gh run list --json で確かめ、sleep で待たない。終わっていなければその事実を報告して止まる。
10. 赤の実演（K5b）: 一時ブランチ（push しない）か一時コピーで run_py を第7版の形（`git show 46f2009b:scripts/run_all_migrations.sh` の run_py）に戻し、R5 が rc=124 で赤になることを sandbox-test で1度示す。GitHub で流すため一時ブランチを push する必要があるなら、release/py-migration-lock-timeout-v2-red という名前で push し、結果を取ったら報告に書く（消すのは設計担当が判断する）。PR は作らない。

## 想定される分岐
- 手順10の実演が rc=124 にならない → 試験を直して赤にしようとせず止まり、NEEDS_DECISION（bash 5.x の `$!` の動きが設計の前提と違う可能性）。
- R5 の緑の側が30秒を超える → NEEDS_DECISION。
- S3 が今の版で赤になる → 当たった行を報告して NEEDS_DECISION。
- revert の再適用で衝突 → BLOCKED。
- P1〜P3・S1・S2 が #4861 のときと違って赤になる → 試験の書き方の誤りなら直して再実行（最大2回）。設計どおりの部分を変えたくなったら NEEDS_DECISION。
- push・PR 起票が見張りに止められる → 言い換えず BLOCKED。

## 停止と報告
- DONE / BLOCKED: 理由 / NEEDS_DECISION: 問い のどれかで返す。
- 報告には、作業場所の絶対パス、HEAD、PR 番号、各試験（S1〜S3・P1〜P3・R1〜R5・既存 T1〜T8/T1〜T9）の PASS/FAIL と run の番号、赤の実演の rc、保存したファイルのパスを書く。生出力のみ。推測で埋めない。

## 禁止
- 移行21本と migrations/ の中身を変えない。本番に触らない。マージしない。force push しない。main/develop に push しない。

END OF CARD
