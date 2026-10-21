# 実装カード — migration-lock-timeout 便1.1（Sonnet）

- 設計: docs/handoff/migration-lock-timeout/design.md §13（§13-4・§13-5 が正）。審査: review-design-1-1.md（APPROVE）。
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-migration-lock-timeout-1-1（ブランチ release/migration-lock-timeout-1-1）。
  - git は必ず `git -C <この絶対パス>` で使う。cd と $変数入りのパスは使わない（フックが展開しない）。
  - Bash の文字列に「docker」「psql」「<」が同時に入ると、フックが本番書き込みと誤判定して止める。ファイルの編集は Edit/Write ツールで行い、Bash の heredoc・sed・python で書き換えない。
- 最初に `bash /Users/tanizawashingo/worktrees/salesanchor/release-migration-lock-timeout-1-1/scripts/dev/executor-preflight.sh` を実行し、出力をファイルに保存する。落ちたら BLOCKED。

## やること
1. `scripts/run_all_migrations.sh` を Edit ツールで変える（design §13-4 のとおり。ほかの行は1文字も変えない）。
   - `SQL_RETRY_MAX_ATTEMPTS` の既定を 10 → 40。
   - `SQL_RETRY_USED=0` の次の行に、§13-4 の `log_lock_holders` 関数（コメント2行を含む）をそのまま入れる。
   - run_sql の中の2か所に1行ずつ足す。
2. `tests/sandbox/migration-run-sql-retry.sh` を Edit ツールで変える（design §13-5）。
   - 抽出範囲を変える。`^SQL_LOCK_TIMEOUT=` から始めて、`^run_sql() {` の後の最初の `^}` まで取る。例: `awk '/^SQL_LOCK_TIMEOUT=/{p=1} p{print} p&&/^run_sql\(\) \{/{r=1} r&&/^}/{exit}'`。抽出行数を表示する。
   - T3 に足す判定は2つ: ログに `lock holders (xact > 1s):` があり、`products:AccessShareLock` を含む行があること。かつ、ログに `pg_sleep` が無いこと。
   - T7: 既定値の確認。reset_defaults の直後に `SQL_RETRY_MAX_ATTEMPTS` = 40、`SQL_RETRY_BUDGET` = 40。
   - T8: T4 と同じ形（1回目だけ deadlock。別の sequence 名）で、ログ中の `lock holders (xact > 1s):` が1回だけ。
   - T1〜T6 の今の判定は変えない。
   - T3 は今 `SQL_RETRY_MAX_ATTEMPTS=3` を明示しているので、そのまま上限到達の試験になる。
3. `bash -n` で両ファイルの構文を確かめる。shellcheck があれば流し、新しく出た警告だけ報告する。
4. commit（`git -C ... add` は次のファイルだけ）:
   - scripts/run_all_migrations.sh
   - tests/sandbox/migration-run-sql-retry.sh
   - docs/handoff/migration-lock-timeout/design.md
   - docs/handoff/migration-lock-timeout/review-design-1-1.md
   - docs/handoff/migration-lock-timeout/card-1-1.md
   - docs/handoff/migration-lock-timeout/review-code.md（便1の再審査の追記。Opus が写したもの。中身は変えない）
   - docs/adr/ADR-1037-migration-lock-timeout.md
   - .claude-pipeline/active-work.d/release-migration-lock-timeout-1-1.md

   その後、作業場所で `node /Users/tanizawashingo/worktrees/salesanchor/release-migration-lock-timeout-1-1/scripts/generate-adr-index.js` を実行する。
   - 出力先が作業場所の docs/adr/README.md であることを `git -C ... status` で確かめ、本店（/Users/tanizawashingo/salesanchor）の README が変わっていないことも確かめる。
   - 差分があれば README も add する。
   - メッセージ: `fix: migration の流し直しを1ファイルでも全体予算まで使い、鍵の持ち主をログに出す (ADR-1037 便1.1)`。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
5. push（`git -C ... push -u origin release/migration-lock-timeout-1-1`）。拒否されたら言い換えず BLOCKED で止まる。
6. `gh workflow run sandbox-test.yml --repo shingo-ops/salesanchor --ref release/migration-lock-timeout-1-1 -f test=migration-run-sql-retry` を実行する。
   - run ID を取り、数分おきに `gh run view <id> --json status,conclusion` で完了を待つ。
   - ログ全文を /tmp/CC報告ファイル/migration-lock-timeout/impl-1-1/sandbox-log.txt に保存する。
7. FAIL があり、原因が試験の書き方なら、試験だけを直して再実行してよい（最大2回）。run_sql 本体を変えたくなったら止めて NEEDS_DECISION。

## 想定分岐
- 抽出した範囲に run_sql の終わりの `}` が入らない、または余計な関数まで入る → BLOCKED（行数と先頭・末尾の行を添える）。
- T3 で `products:AccessShareLock` が出ない → 持ち主の一覧の生の行を添えて NEEDS_DECISION（試験も本体も直さない）。
- `pg_sleep` の文字がログに出る → 本体の問題なので NEEDS_DECISION。

## 報告（/tmp/CC報告ファイル/migration-lock-timeout/impl-1-1/report.md）
- preflight の結果。
- `git -C ... diff origin/main --stat`。run_all_migrations.sh の diff 全文はファイルに保存する。
- commit SHA、sandbox run ID、T1〜T8 の行（ログからそのまま写す）、shellcheck の結果。
- 最後の行に DONE / BLOCKED:<理由> / NEEDS_DECISION:<内容>。
