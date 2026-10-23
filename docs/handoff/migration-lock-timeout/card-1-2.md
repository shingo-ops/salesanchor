# 実装カード — migration-lock-timeout 便1.2（Sonnet）

- 設計: docs/handoff/migration-lock-timeout/design.md §14（§14-4〜§14-6 が正）。審査: review-design-1-2.md（APPROVE）。PO 承認: 2026-10-22「1」（K7 の数え方）。
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-k7-read-probe（ブランチ release/k7-read-probe）。
  - git は必ず `git -C <この絶対パス>` で使う。cd と $変数入りのパスは使わない（フックが展開しない）。
  - Bash の文字列に「docker」「psql」「<」が同時に入ると、フックが本番書き込みと誤判定して止める。ファイルの編集は Edit/Write ツールで行い、Bash の heredoc・sed・python で書き換えない。
- 最初に `bash /Users/tanizawashingo/worktrees/salesanchor/release-k7-read-probe/scripts/dev/executor-preflight.sh` を実行し、出力をファイルに保存する。落ちたら BLOCKED。

## やること
1. `scripts/run_all_migrations.sh` を Edit ツールで変える（§14-4 のとおり。ほかの行は1文字も変えない）。
   - `preflight_registered_files() {`（今の :107）の直前に、`# >>> read-probe begin` 〜 `# <<< read-probe end` で囲んだブロックを入れる。中身は `READ_PROBE_*` の4行（§14-4、表は §14-5 の14表をこの順で空白区切り）と `read_probe_start` / `read_probe_stop`。
   - `_ai_ro_create_on_exit` の `trap - EXIT` の次の行に `if declare -F read_probe_stop >/dev/null; then read_probe_stop || true; fi`（字下げは周りと同じ空白2つ）。
   - `trap _ai_ro_create_on_exit EXIT` の次の行に `read_probe_start` の呼び出し（コメント1行を付けてよい）。
   - 関数名・変数名は `run_` で始めない。
2. `tests/sandbox/migration-read-probe.sh` を新しく作る（§14-6 の T1〜T9・T4b、slow 行の書式確認）。作りは `tests/sandbox/ai-ro-restore-on-failure.sh` と `tests/sandbox/migration-run-sql-retry.sh` にそろえる。入れ物は jarvis / jarvis_db で起動。
3. `backend/tests/test_read_probe_tables.py` を新しく作る（§14-5 の「ずれを止める試験」のとおり。ROOT は `backend/tests/test_supply_category.py:22` と同じ書き方）。
4. 確かめる（生出力は /tmp/CC報告ファイル/k7-probe/impl/ に保存）
   - `bash -n` で2つのシェルの構文。shellcheck があれば流し、新しく出た警告だけ報告する。
   - `cd` せずに `python -m pytest` を backend を作業ディレクトリとして `tests/test_read_probe_tables.py` だけ流す（手元で流せなければ、その事実と理由を書く）。
   - 試しに `READ_PROBE_TABLES` から1表を抜いた場合と1表を足した場合に試験が落ちることを、ファイルを変えずに確かめられる方法（monkeypatch か一時コピー）で確かめる。確かめられなければ未確認と書く。
5. commit（add は次のファイルだけ）:
   - scripts/run_all_migrations.sh
   - tests/sandbox/migration-read-probe.sh
   - backend/tests/test_read_probe_tables.py
   - docs/handoff/migration-lock-timeout/design.md
   - docs/handoff/migration-lock-timeout/review-design-1-2.md
   - docs/handoff/migration-lock-timeout/card-1-2.md
   - docs/adr/ADR-1037-migration-lock-timeout.md
   - docs/adr/README.md（`node /Users/tanizawashingo/worktrees/salesanchor/release-k7-read-probe/scripts/generate-adr-index.js` を実行して差分があれば。本店 /Users/tanizawashingo/salesanchor の README が変わっていないことも確かめる）
   - .claude-pipeline/active-work.d/release-k7-read-probe.md（無ければ、ほかの active-work.d のファイルの形で作る）
   - メッセージ: `feat: 移行中に読み取りの待ちを測ってログに出す (ADR-1037 便1.2)`。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
6. push（`git -C ... push origin release/k7-read-probe`）。拒否されたら言い換えず BLOCKED で止まる。
7. `gh workflow run sandbox-test.yml --repo shingo-ops/salesanchor --ref release/k7-read-probe -f test=migration-read-probe` を実行する。続けて同じ形で `-f test=migration-run-sql-retry` と `-f test=ai-ro-restore-on-failure` も流す（T9）。
   - run ID を取り、数分おきに `gh run view <id> --json status,conclusion` で完了を待つ。
   - ログ全文を /tmp/CC報告ファイル/k7-probe/impl/sandbox-<試験名>.txt に保存する。
8. FAIL があり、原因が試験の書き方なら、試験だけを直して再実行してよい（最大2回）。`scripts/run_all_migrations.sh` の設計どおりの部分を変えたくなったら止めて NEEDS_DECISION。

## 想定される分岐
- prod1 と同じく GitHub の runner も bash 5 のはず。`$EPOCHREALTIME` が空なら T1 の invalid=0 で落ちる → 止めて NEEDS_DECISION（設計の前提が崩れる）。
- T7 の下限（max≥300 と Lock 待ちの観測）が時々外れる場合は、保持時間を延ばしてよい（6秒→10秒まで）。それでも外れたら NEEDS_DECISION。
- T5 で `Terminated` の行に SQL が出た場合は、試験を直さず NEEDS_DECISION（本番のログに出るため）。

## 触らない範囲
- `scripts/run_all_migrations.sh` の run_sql・log_lock_holders・migration の一覧・ai_ro の作成処理の中身。
- 既存の試験ファイル（`tests/sandbox/ai-ro-restore-on-failure.sh`、`tests/sandbox/migration-run-sql-retry.sh`）。
- deploy.yml・.env・migrations/。

## 報告
- 変えたファイルと差分の行数、各確認の生出力のパス、sandbox の run ID と結論、最後の commit の 40 文字の sha。
- 最後の行は DONE / BLOCKED:<理由> / NEEDS_DECISION:<内容>。
