# 実装カード — ai-ro-restore-on-failure（Sonnet）

- 設計: docs/handoff/ai-ro-restore-on-failure/design.md（§3 が変更の正）。審査: review-design.md（APPROVE が前提）。
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-ai-ro-restore-on-failure（ブランチ release/ai-ro-restore-on-failure）。
  - git は必ず `git -C <この絶対パス>` で使う。cd と $変数入りのパスは使わない（フックが展開しない）。
  - Bash の文字列に「docker」「psql」「<」が同時に入ると、フックが本番書き込みと誤判定して止める。ファイルの編集は Edit/Write ツールで行う。試験の台本も Write ツールで書く。
  - grep はシェル関数が壊れているので `LC_ALL=C /usr/bin/grep -a` を使う。
- 最初に `bash /Users/tanizawashingo/worktrees/salesanchor/release-ai-ro-restore-on-failure/scripts/dev/executor-preflight.sh` を実行し、出力をファイルに保存する。落ちたら BLOCKED。

## やること
1. `scripts/run_all_migrations.sh` を Edit ツールで変える。design §3 のとおりにし、ほかの行は1文字も変えない。
   - コメント :121-124 の4行を、§3 のコメント5行に置き換える。
   - :125（`AI_RO_CREATE_SQL=`）の次の行に、`AI_RO_CREATE_TIMEOUT="${AI_RO_CREATE_TIMEOUT:-30s}"` を足す。
   - 作成の docker exec（:139）の前に、§3 のコメント1行を足す。docker exec 自体には `-e PGOPTIONS="-c statement_timeout=${AI_RO_CREATE_TIMEOUT}"` を足す。
   - `_ai_ro_create_on_exit` の本体を §3 の形にする。変えるのは次の4点だけ。
     - rc≠0 の分岐は echo だけにし、exit を外す。
     - 見つからない分岐は `exit "${rc}"`。
     - 作成失敗の分岐も `exit "${rc}"`。
     - 最後の `exit 0` は `exit "${rc}"`。
   - 警告文の「デプロイは続行。」は §3 のとおり外す。
2. 新しい試験 `tests/sandbox/ai-ro-restore-on-failure.sh` を Write ツールで作る。
   - 型は `tests/sandbox/migration-run-sql-retry.sh` に合わせる（使い捨て postgres:16、pass/fail、cleanup trap）。
   - 本物の切り出し（T6）: `awk '/^AI_RO_CREATE_SQL=/{p=1} p{print} p&&/^trap _ai_ro_create_on_exit EXIT/{exit}' scripts/run_all_migrations.sh`。
     - 切り出した行数と、先頭・末尾の行を表示する。
     - 末尾が `trap _ai_ro_create_on_exit EXIT` でなければ FAIL で止まる。
   - T1〜T5・T7・T8 の各試験の直前に、`migrations/20261017_125900_drop_ai_ro_views.sql` を試験 DB に流す。本番で :119 がビューを外すのと同じ状態から始めるため。外さないと、前の試験のビューが残り、T3・T7 の「0本」が正しく判定できない。
   - 各試験は、切り出しを子の `bash` で動かす。中身は次の順番。
     - `set -e` を置く。
     - POSTGRES・PSQL（`psql -U postgres -d postgres -v ON_ERROR_STOP=1`）・REPO_DIR を設定する。
     - 切り出しを eval する。
     - 最後に `exit 3`（失敗の再現）か `true`（成功の再現）を置く。
     - 終了コードとログを受け取る。
   - 準備: 試験用の表 `public.sb_items(id int, name text, api_token text)` を作る。
     - 先に作成 SQL :23 の拒否リストを読み、api_token が外れる名前であることを確かめる。外れない名前なら、外れる名前に替えて報告する。
     - ai_reader ロールは T3 以外で作る（`CREATE ROLE ai_reader NOLOGIN`）。
   - T1: ai_reader あり・`exit 3`。次の4つを全部満たせば PASS。
     - 終了コードは 3。
     - ログに `recreating ai_ro views anyway` と `ai_ro views created:` がある。
     - ログの `ai_ro views created: N` の N が、作成後の ai_ro のビュー数と同じ。
     - `ai_ro.sb_items` がある。
     - そのビューの列に api_token が無い（`information_schema.columns` で確かめる）。
   - T2: ai_reader あり・`true`。終了コードは 0 で、`ai_ro.sb_items` がある。
   - T3: ai_reader を DROP してから・`exit 3`。次を全部満たせば PASS。
     - 終了コードは 3。
     - ログに `ai_ro views の作成に失敗` がある。
     - 終了後、`ai_ro` スキーマが無いか、ビューが0本。
   - T4: ai_reader あり・`true`。POSTGRES を存在しないコンテナ名にする。終了コードは 0 で、ログに `ai_ro views の作成に失敗` がある。
   - T5: 別の接続で `BEGIN; SELECT count(*) FROM public.sb_items; SELECT pg_sleep(8);` を裏で流し、ACCESS SHARE を持たせる。2秒待ってから T2 と同じ作成を流し、かかったミリ秒を測る。同時に、作成の最中に別の接続で `SELECT count(*) FROM public.sb_items` を流し、かかったミリ秒を測る。次を全部満たせば PASS。
     - 作成は 3000ms 未満（鍵を待てば8秒前後になる）。
     - 読み取りは 1000ms 未満。
     - ミリ秒の値はログに出す。
   - T7: ai_reader あり。別の接続で `BEGIN; LOCK TABLE public.sb_items IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(20);` を裏で流す。2秒待ってから、`AI_RO_CREATE_TIMEOUT=3s` を環境に入れて `exit 3` の試験を流し、かかった秒数を測る。次を全部満たせば PASS。
     - 10秒以内に終わる。
     - 終了コードは 3。
     - ログに `ai_ro views の作成に失敗` がある。
     - 終了後、ai_ro のビューが0本（スキーマが無いのも可）。
     - 裏の接続は終わるまで待つか、pg_terminate_backend で止めてから次へ進む。
   - T8（記録だけ。合否に入れない）: 切り出しの後ろに `sleep 30` を置いた子の bash を裏で起こす。3秒後にその子へ SIGTERM を送り、次をログに出す。
     - 子の終了コード。
     - ログに `recreating ai_ro views anyway` と `ai_ro views created:` が出たか。
   - 最後に T1〜T7 の PASS/FAIL を数え、FAIL が1つでもあれば exit 1。
3. `bash -n` で両方のファイルの構文を確かめる。shellcheck があれば流し、新しく出た警告だけを報告する。
4. commit する。`git -C ... add` するのは次のファイルだけ。
   - scripts/run_all_migrations.sh
   - tests/sandbox/ai-ro-restore-on-failure.sh
   - docs/handoff/ai-ro-restore-on-failure/recon.md
   - docs/handoff/ai-ro-restore-on-failure/design.md
   - docs/handoff/ai-ro-restore-on-failure/review-design.md
   - docs/handoff/ai-ro-restore-on-failure/card.md
   - docs/adr/ADR-1024-ai-readonly-db-path.md
   - docs/handoff/ai-readonly-db-path/usage.md（Opus が1文足したもの。中身は変えない）
   - .claude-pipeline/active-work.d/release-ai-ro-restore-on-failure.md
   - そのあと作業場所で `node /Users/tanizawashingo/worktrees/salesanchor/release-ai-ro-restore-on-failure/scripts/generate-adr-index.js` を流す。差分があれば docs/adr/README.md も add する。本店（/Users/tanizawashingo/salesanchor）の README が変わっていないことを確かめる。
   - メッセージは `fix: 移行が途中で失敗しても ai_ro ビューを作り直す (ADR-1024 改訂)`。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける。
5. push する（`git -C ... push -u origin release/ai-ro-restore-on-failure`）。拒否されたら、言い換えずに BLOCKED で止まる。
6. 試験を流す: `gh workflow run sandbox-test.yml --repo shingo-ops/salesanchor --ref release/ai-ro-restore-on-failure -f test=ai-ro-restore-on-failure`。
   - run ID を取り、数分おきに `gh run view <id> --json status,conclusion` で完了を待つ。
   - ログの全文を /tmp/CC報告ファイル/ai-ro-restore/impl/sandbox-log.txt に保存する。
7. FAIL が出て、原因が試験の書き方にあるなら、試験だけを直して流し直してよい（最大2回）。台本の本体を変えたくなったら止めて NEEDS_DECISION。

## 想定分岐
- 切り出しの末尾が trap 行にならない → BLOCKED。行数と先頭・末尾の行を添える。
- 試験 DB で作成 SQL が ai_reader 以外の理由で失敗する（tenant_* が無い等）→ 作成 SQL のエラー行を添えて NEEDS_DECISION。作成 SQL は変えない。
- T7 で作成が上限で止まらない、または一部のビューだけが残る → ログと pg_locks の行を添えて NEEDS_DECISION（本体の前提が崩れるため）。
- T5 で作成が 3000ms を超える → 測った値と pg_locks の行を添えて NEEDS_DECISION。
- sandbox-test.yml が test 名を受け付けない（一覧の制限など）→ 生のエラーを添えて BLOCKED。

## 報告（/tmp/CC報告ファイル/ai-ro-restore/impl/report.md）
- preflight の結果。
- `git -C ... diff origin/main --stat`。run_all_migrations.sh の diff の全文は、別のファイルに保存する。
- 次をログからそのまま写す。
  - commit SHA
  - sandbox の run ID
  - T1〜T8 の行
  - T5 のミリ秒
  - shellcheck の結果
- 最後の行は DONE / BLOCKED:<理由> / NEEDS_DECISION:<内容> のどれか。
