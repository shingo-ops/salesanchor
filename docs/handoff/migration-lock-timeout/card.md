# 実装カード — migration-lock-timeout 便1（Sonnet）

- 設計: docs/handoff/migration-lock-timeout/design.md（§4 が正）。審査: review-design.md（APPROVE）。
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-migration-lock-timeout（ブランチ release/migration-lock-timeout）。git は必ず `git -C <この絶対パス>` で使う。cd と $変数入りのパスは使わない（フックが展開しない）。
- 最初に `bash /Users/tanizawashingo/worktrees/salesanchor/release-migration-lock-timeout/scripts/dev/executor-preflight.sh` を実行し、出力をファイルに保存する。落ちたら BLOCKED。

## やること
1. `scripts/run_all_migrations.sh` の `SQL_DEADLOCK_MAX_ATTEMPTS=3` の直前のコメント2行〜 run_sql の終わり `}` を、design.md §4-1 のコードブロックに**そのまま**置き換える（Edit ツールで）。ほかの行は1文字も変えない。
2. `tests/sandbox/migration-run-sql-retry.sh` を新規作成（Write ツール。Bash の heredoc はフックに止められる）。design.md §4-2 の T1〜T6 を実装。
   - 起動・待ち・後片付けは `tests/sandbox/lock-timeout-repro.sh` の書き方に合わせる。
   - run_sql は `sed -n '/^SQL_LOCK_TIMEOUT=/,/^}/p' scripts/run_all_migrations.sh` で抜き出して eval か source で読み込む（写しを書かない）。抜き出した行数を表示する。
   - 試験ごとに `SQL_RETRY_*` を上書きするときは、run_sql を呼ぶ直前に変数を設定し、終わったら既定値（抜き出した行を読み直す）に戻す。SQL_RETRY_USED も試験ごとに 0 に戻す。
   - T4/T6 の「n回目まで失敗する」SQL は一時ファイル（mktemp）に作り、`CREATE SEQUENCE IF NOT EXISTS` ＋ DO ブロックで `IF nextval('<名前>') <= n THEN RAISE EXCEPTION USING ERRCODE = '40P01', MESSAGE = 'deadlock detected'; END IF;`。試験ごとに別の sequence 名を使う。REPO_DIR を一時ディレクトリにし、そこからの相対パスで渡すか、REPO_DIR 基準の相対パスにする（run_sql は `${REPO_DIR}/${file}` を読む）。
   - T1 の C 測定はバックグラウンドで0.5秒ごと、最大値と全測定値を出す。
   - 各試験 `PASS T1 ...` / `FAIL T1 ...` を1行で出し、最後に `RESULT: PASS`（全部 PASS）か `RESULT: FAIL` で exit 1。
   - パスワードは試験専用の固定値（既存試験と同じ）。secrets・本番には触れない。
3. `bash -n` で両ファイルの構文を確かめる。shellcheck があれば流し、結果を保存（新しく出た警告だけ報告）。
4. commit（`git -C ... add` は次の7つだけ）:
   scripts/run_all_migrations.sh、tests/sandbox/migration-run-sql-retry.sh、docs/handoff/migration-lock-timeout/{recon,design,review-design,card}.md、docs/adr/ADR-1037-migration-lock-timeout.md、.claude-pipeline/active-work.d/release-migration-lock-timeout.md
   その後 `node scripts/generate-adr-index.js`（作業場所で。cwd を変えられないなら `node /Users/tanizawashingo/worktrees/salesanchor/release-migration-lock-timeout/scripts/generate-adr-index.js` で、出力先が作業場所の docs/adr/README.md になることを確かめる）→ docs/adr/README.md も add。
   メッセージ: `feat: migration のロック待ちを1秒で諦めて流し直す (ADR-1037)`。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
5. push（`git -C ... push origin release/migration-lock-timeout`）。拒否されたら言い換えず BLOCKED で止まる。
6. `gh workflow run sandbox-test.yml --ref release/migration-lock-timeout -f test=migration-run-sql-retry` → run ID を取り、完了まで待つ（長い待ちは避け、数分おきに `gh run view <id> --json status,conclusion`）。ログ全文を /tmp/CC報告ファイル/migration-lock-timeout/impl/sandbox-log.txt に保存。
7. FAIL があれば、原因が試験の書き方なら試験だけを直して再実行してよい（最大2回）。run_sql の本体を変えたくなったら止めて NEEDS_DECISION。

## 想定分岐
- T1 の C 最大値が 1500ms を超えた → 試験を直さず、全測定値を添えて NEEDS_DECISION。
- psql のエラー文が想定と違い grep に当たらない → 実際の文面を添えて NEEDS_DECISION。
- 抜き出した行数が想定（約45行）と大きく違う → BLOCKED。

## 報告（/tmp/CC報告ファイル/migration-lock-timeout/impl/report.md）
- preflight の結果、`git -C ... diff origin/main --stat` と run_all_migrations.sh の diff 全文（ファイル保存）、commit SHA、sandbox run ID と T1〜T6 の行（ログから抜粋せずそのまま）、shellcheck 結果。
- 最後の行に DONE / BLOCKED:<理由> / NEEDS_DECISION:<内容>。
