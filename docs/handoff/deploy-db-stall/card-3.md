# 実装カード — deploy-db-stall 段3 控えの pg_dump にロック待ちの上限（第2.1版・Sonnet）

受領確認: 着手前に「カード deploy-db-stall 段3 を受領」と1行返す。

- 設計: docs/handoff/deploy-db-stall/design.md §15 第2.1版（このブランチにある。Architect 条件付き APPROVE、条件は反映済み）。§15-3・§15-4・§15-5 を全部読んでから作る。設計とこのカードが食い違ったら設計を正とし、止めて NEEDS_DECISION。
- PO 承認: 2026-10-29「1」（正式な設計にまとめ、審査に通してから1つずつ直す）と、同日の「PRマージ、デプロイまで完走させてくれ」。
- 作業場所（作成済み）: /Users/tanizawashingo/worktrees/design-inbox-brushup/release-deploy-db-stall-stage3（ブランチ release/deploy-db-stall-stage3、origin/main 47e0954f7 起点）。git は必ず `git -C <この絶対パス>` で使う。cd と変数入りのパスは使わない。
- 最初に作業場所で `./scripts/dev/executor-preflight.sh` を実行し、出力を /tmp/CC報告ファイル/deploy-db-stall/impl-stage3/preflight.txt に保存する。落ちたら BLOCKED。
- ファイルの編集は Edit/Write ツールで行う。生出力はすべて /tmp/CC報告ファイル/deploy-db-stall/impl-stage3/ に保存する。

## やること
1. `scripts/backup.sh` を §15-3 の 1〜5 のとおりに変える。
   - PG_DUMP_LOCK_WAIT_MS=120000 を冒頭の定数に置き、pg_dump に `--lock-wait-timeout=${PG_DUMP_LOCK_WAIT_MS}` を付ける。
   - SALESANCHOR_BACKUP_DIR・SALESANCHOR_BACKUP_COMPOSE_FILE で保存先と compose ファイルを外から変えられるようにする（既定値は今と同じ）。
   - mkdir の直後で、1日より古い `salesanchor_db_*.sql.gz.partial` を find で消す。
   - BACKUP_FILE を決めた後に trap を置く。EXIT では最初に rc を取り、自分の `${BACKUP_FILE}.partial` だけを消し、rc≠0 なら backup.log に「Backup FAILED rc=<rc>」を書き、exit rc。INT→exit 130、TERM→exit 143、HUP→exit 129。
   - pg_dump の前に umask 077。出力は `.partial` に書き、成功したら mv。chmod 600 は残す。
   - 変えないもの（§15-3 の 7）を守る。特に `write_success_timestamp() {` の見出し行。
2. 試験本体を新しく作る: scripts/tests/test-backup-lock-wait.sh（B1・B2・B4。§15-4 のとおり）。B3 は既存の2本をそのまま呼ぶ。
3. `.github/workflows/backup-script-test.yml` を新しく作る。手本は `.github/workflows/deploy-script-test.yml`。対象のパスが変わった PR と workflow_dispatch で走らせ、必須チェックにはしない。
4. 確かめる: bash -n（変えたシェル全部）、shellcheck が使えれば流す。手元で docker が使えなければ、手元では B2・B3 だけを流す。B1・B4 は PR の CI で確かめる。
5. commit・push・PR は3段に分け、各段のあとで確かめる。
   - commit: 「fix: 控えの pg_dump にロック待ちの上限を付け、書き途中を残さない」。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。設計書とこのカードも同じ PR に含める（設計担当が書いた変更が作業場所にある。消さない）。
   - push: `git -C <作業場所> push -u origin release/deploy-db-stall-stage3` を単独で流す。
   - PR: `bash scripts/gh-pr-create-safe.sh` で起票する。本文は Write で作ったファイルを --body-file で渡す。shingo-cc 名義であることを確かめる。本文には次を書く。
     - recon・設計（§15 第2.1版）・対象 ADR（ADR-1037 の拡張）・PO 承認
     - 触るファイル全部と削除するファイル（git diff origin/main --stat で確かめる）
     - Evaluator は画面の変更が無いので Skip
     - GO 記録の欄は作らない
6. PR の CI で backup-script-test が緑になるのを gh pr checks で確かめる。sleep で待たない。終わっていなければ、その事実を報告して止まる。
7. 赤の実演（K3-1b）: push しない一時の写し（作業場所の外の一時フォルダ）で行う。
   - backup.sh から `--lock-wait-timeout` を外した版で、B2 の引数の判定が赤になることを示す。
   - trap を外した版で、B2 の失敗の項が赤になることを示す。
   - B4b の赤は CI でしか確かめられない。その場合は、一時ブランチ release/deploy-db-stall-stage3-red を push し、gh workflow run で backup-script-test を流して結果を取る。PR は作らない。片付けは設計担当が判断する。

## 想定される分岐
- B1b で pg_locks の granted=false が作れない → 止まって NEEDS_DECISION。
- B4b の所要が120〜180秒に入らない → 測った値を添えて NEEDS_DECISION。
- 「CI設定整合性チェック」などの既存の検査が、新しいワークフローの登録を求めて赤になる → その検査が求める登録だけを足す。ほかの変更が要るなら NEEDS_DECISION。
- 既存の test-backup-timestamp.sh が赤になる → 見出し行を変えていないかを確かめる。直らなければ NEEDS_DECISION。
