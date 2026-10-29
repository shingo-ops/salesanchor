# 実装カード — deploy-db-stall 段1（Sonnet）

受領確認: 着手前に「カード deploy-db-stall 段1 を受領」と1行返す。

読んだ節と照合結果（docs/handoff/design-partner-card-ops/guards/ から）:
- guards/00-common.md: 1手順1コマンド、出力に上限、待つ道具は gh pr checks、報告に無い出力を成功と扱わない → 手順7を commit・push・PR の3段に分け、各段で git log と .pr-number を確かめる形にした。
- guards/05-pr.md: PR は gh-pr-create-safe.sh、触るファイルは同じ行にカンマ区切り、削除するファイルは git diff --cached --stat で確かめて列挙、scripts/ と deploy.yml は危険パスで GO 記録が要る（GO は設計担当が出す。実行役は書かない）。
- guards/07-migration.md: 新しい移行の登録はしない（本件は移行を足さない）。文書 PR の skipping は実行ではない → P1〜P3 が実際に走ったことを CI のログで確かめる。

- 設計: docs/handoff/deploy-db-stall/design.md §4（§4-1〜§4-5）と §6（main に合流済み、PR #4860、第7版 APPROVE）。設計の文面がこのカードと食い違ったら設計を正とし、止めて NEEDS_DECISION。
- PO 承認: 2026-10-29「1」（正式な設計にまとめ、審査に通してから1つずつ直す）。
- 作業場所: origin/main 起点で `bash scripts/new-worktree.sh release/py-migration-lock-timeout` を本店 /Users/tanizawashingo/salesanchor から実行して作る。作業場所の絶対パスは new-worktree.sh の出力から取り、報告に書く。以後 git は必ずその絶対パスを git -C に渡して使う。cd と変数入りのパスは使わない。
- 最初に作業場所で executor-preflight.sh を実行し、出力をファイルに保存する。落ちたら BLOCKED。
- ファイルの編集は Edit/Write ツールで行う。Bash の heredoc・sed・python で書き換えない。

## やること
1. scripts/migration_py_entry.py を新しく作る（§4-1 のとおり）。
   - MIGRATION_LOCK_TIMEOUT が空でないときだけ create_async_engine を差し替える。
   - server_settings の写しに lock_timeout を上書きし、application_name=salesanchor_migration は無いときだけ足す。
   - sys.argv を [本物のパス, *残りの引数] にし、runpy.run_path(本物のパス, run_name="__main__") で動かす。SystemExit を握らない。
   - finally で標準エラーに1行だけ出す。値が1s のときは「migration_py_entry: lock_timeout=1s applied to N engine(s)」。値なしは「migration_py_entry: lock_timeout=unset applied to 0 engine(s)」。
   - logging を設定しない。表・列の削除や大量削除の語をコメントにも書かない。
2. scripts/run_all_migrations.sh を変える（§4-2 のとおり）。
   - run_py の定義を log_lock_holders の後・run_sql の前へ移し、入口経由で動かす。docker exec への指定（"$@"）は -w の前に残す。
   - 再試行の判定文字列・回数・間隔・全体上限を run_sql と共有する。set -e で途中終了しない受け方にする。
   - 標準エラーは tee で写しながら出し、判定の前にプロセス置換の番号を wait する。
   - 開始行の echo の文面、値4つ、log_lock_holders、run_sql の外から見た動き、read-probe、EXIT trap、移行の登録行は変えない。
3. 起動条件の3か所に入口を足す（§4-3 冒頭、K6b）。
   - .github/workflows/migration-test.yml の paths-filter。
   - .github/workflows/deploy.yml の db_migrations と、その説明コメント1行。
   - scripts/check-process-artifacts.js の MIGRATION_PATH_PATTERNS。scripts/tests/test-process-artifacts.js に入口が移行の範囲に入る試験を1件足す。
4. 試験を足す（§4-3）。
   - migration-test.yml の migration-test-run ジョブに S1・S2・P1・P2・P3 を置く。
   - tests/sandbox/migration-run-sql-retry.sh に R1〜R4 を足す（偽 docker 関数は python を含む呼び出しだけ偽物にし、終わったら消す）。
5. 文書（§4-5）。
   - docs/adr/ADR-1037-migration-lock-timeout.md の対象外の行を直し、追記する。
   - docs/handoff/migration-lock-timeout/design.md の2か所をつなぐ。
   - node scripts/generate-adr-index.js で目次を作り直す。
   - このカードを docs/handoff/deploy-db-stall/card-1.md として置く。
6. 確かめる（生出力は /tmp/CC報告ファイル/deploy-db-stall/impl/ に保存）。
   - bash -n で変えたシェルの構文。
   - node scripts/tests/test-process-artifacts.js。
   - K4 の実演: 一時コピーで from sqlalchemy.ext.asyncio.engine import の行を足すと S1 が赤になることを1度示す（本物のファイルは変えない）。示せなければ未確認と書く。
7. commit・push・PR を3段に分け、各段のあとで確かめてから次へ進む。
   - commit: メッセージは「feat: Python の移行にもロック待ち1秒と再試行を付ける (ADR-1037 拡張・段1)」。末尾に Co-Authored-By の行（Claude Opus 5.5、noreply@anthropic.com）を付ける。終わったら git log -1 で確かめる。
   - push: 作業場所の絶対パスを git -C に渡し、push -u origin release/py-migration-lock-timeout を単独で実行する。
   - PR: bash scripts/gh-pr-create-safe.sh で起票し、本文は Write で作ったファイルを渡す。shingo-cc 名義を確かめる。本文に recon・設計・対象ADR ADR-1037・PO承認・触るファイル全部・削除するファイルを書く。Evaluator は画面の変更なしで省略と書く。GO 記録の欄は作らない。終わったら .pr-number と gh pr list --head の番号が一致するか確かめる。
8. sandbox 試験を流す。
   - gh workflow run sandbox-test.yml --ref release/py-migration-lock-timeout で migration-run-sql-retry と migration-read-probe を流す。
   - 完了は gh run list --workflow sandbox-test.yml --branch release/py-migration-lock-timeout --json で確かめる。sleep で待たない。終わっていなければ、その事実を報告して止まる。
   - 結果とログを /tmp/CC報告ファイル/deploy-db-stall/impl/ に保存する。PR の CI の結果は gh pr checks で保存する。
9. 失敗の原因が試験の書き方なら、試験だけ直して再実行してよい（最大2回）。設計どおりの部分を変えたくなったら止めて NEEDS_DECISION。

## 想定される分岐
- P1 の読み取りの最大が1500ms を超える、または失敗まで3秒以上かかる → 設計の前提が崩れるので NEEDS_DECISION。
- S1 が今ある26本のどれかで赤になる → 前提（26本とも同じ取り込み方）が崩れたので NEEDS_DECISION。
- run_py を移した後に read-probe の試験が抜き出しに失敗する → 範囲の置き方を見直す。直せなければ BLOCKED。
- check-process-artifacts が入口を危険な形と判定して止める → 入口の語を見直す。言い換えで逃げず、原因の語を報告する。
- push・PR 起票が見張りに止められる → 言い換えず BLOCKED。

## 停止と報告
- 迷ったら停止し、DONE / BLOCKED: 理由 / NEEDS_DECISION: 問い のどれかで設計担当に返す。
- 報告には、作業場所の絶対パス、HEAD、PR 番号、各試験の PASS/FAIL、保存したファイルのパスを書く。

## 禁止
- 移行21本と migrations/ の中身を変えない。本番に触らない。マージしない。

END OF CARD
