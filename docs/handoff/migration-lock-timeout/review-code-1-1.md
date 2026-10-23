# review-package-v1: PR #4613（ADR-1037 便1.1）コード審査

- 審査者: Claude Opus（Reviewer 役。読み取りのみ・コミットなし）
- 対象: PR #4613 head `c3a276375a46fb1a842784ea55906937135a2aad`。`gh pr view 4613 --json headRefOid` と worktree の `git rev-parse HEAD` が一致。origin/main からの commit は b140c1505・c3a276375 の2つ。Draft・base=main
- 判定: **REVISE**（必須の直し1件: R1）
- CI: 判定に含めていない（走行中）。GO 記録の日時・番号・条件③時刻の空欄も判定から除いた（下 7 に記載のみ）

## 1. run_all_migrations.sh の差分と design §13-4 の一致
- 【事実】`git diff origin/main...HEAD -- scripts/run_all_migrations.sh` は +7/−1 行の3か所（コメント1行置換＋`SQL_RETRY_MAX_ATTEMPTS` 10→40、`log_lock_holders` 関数の追加4行＋コメント2行、run_sql 内に2行追加）。
- 【事実】`log_lock_holders` の本文は design.md §13-4 のコードブロック（design.md:178-183）と文字単位で同じ。run_sql 内の2行の置き場所も §13-4 の指定（`if grep -qE ...` の次の行／`retry limit reached` の echo の次の行）どおり（scripts/run_all_migrations.sh:91, :100）。
- 【事実】ほかの行の変更なし。`bash -n` 合格、`shellcheck -S warning` 出力0行。
- 判定: 一致。

## 2. log_lock_holders が移行の成否を変えないか
- set -e（scripts/run_all_migrations.sh:20）と :91 の `[ "${attempt}" -eq 1 ] && log_lock_holders`:
  - 【事実】bash では && の左辺の失敗は errexit の対象外。手元で `set -e; f(){ [ 2 -eq 1 ] && echo x; echo after; }; f; echo cont` を実行し `after`・`cont` が出た。:91 は関数の途中の行なので、関数の戻り値にも効かない（次の if が続く）。
  - 【事実】attempt=1 のとき右辺 `log_lock_holders` が最後の命令になるため、その戻り値が非0なら set -e で止まる。関数の最後の文は `docker exec ... | sed ... || true` で常に0。手元で `set -e; g(){ false | sed s/^/p/ || true; }; [ 1 -eq 1 ] && g; echo survived` が `survived` を出した。
- pipefail: 【事実】scripts/run_all_migrations.sh に `pipefail` は無い（grep 0件）。仮に将来付いても `|| true` がパイプ全体に掛かるので結果は同じ。
- 関数の戻り値: 最初の `echo` と最後の `|| true` のみ。stdout の書き込み失敗以外で非0にならない。
- :100 の `log_lock_holders` の後は `rm -f` → `return "${rc}"` なので、上限到達時の rc（失敗）は変わらない。試験ログ T3 rc=3・T6 rc=3 で確認（下 5）。
- 問い合わせが鍵を取るか: 【事実】pg_stat_activity・pg_locks・pg_class を読むだけで、取るのは AccessShareLock（カタログとビュー）。在庫表の products には鍵を取らない。【推測なしの限界】pg_class に ACCESS EXCLUSIVE を持つ操作（VACUUM FULL pg_class 等）が走っていれば待つが、この問い合わせには lock_timeout/statement_timeout が付いていない（PGOPTIONS なし）。→ 提案 S2。
- docker exec が失敗したとき: 【事実】`2>&1` で失敗文も sed に流れ、`|| true` で0に倒れる。出る文面は docker/psql のエラー（固定の SQL を含みうるが、秘密は含まない）。
- 【推測】`docker exec -i` は stdin をつなぐが、この呼び出しは入力リダイレクトが無いので、スクリプト自身の stdin を受け取る。deploy.yml:566-577 は appleboy/ssh-action の `script:` で呼んでおり、そこから渡る stdin が空かどうかは【未確認】。psql -c は stdin を読まないので実害は確かめていない。→ 提案 S3。
- 判定: 成否を変えない（set -e・&&・|| true の組み合わせは正しい）。

## 3. 公開ログに SQL 文面・接続元・値・秘密が出ないか
- 【事実】出す列は pid・usename・application_name・state・wait_event_type・秒数・cmd・relname:mode。client_addr・query 全文は SELECT に無い。
- **R1（必須）命令の先頭1語に値や文面が入りうる**:
  - 【事実】cmd は `upper(split_part(ltrim(a.query), ' ', 1))`。区切りは半角スペースのみで、英字以外も通す。試験ログ（sandbox-log-2.txt:217 付近）で cmd が `BEGIN;` と記号付きで出ている。
  - 【事実】PostgreSQL の `ltrim(text)` は既定でスペースだけを削る（改行・タブは削らない）。
  - 【事実】backend には `text("""` で改行から始まる SQL が 421 か所ある（`git grep -nE 'text\(\s*"""\s*$|text\("""$' -- backend | wc -l`）。これらは cmd が改行1文字になり、設計の「命令の先頭1語」が出ない（K9 の手がかりが弱くなる）。
  - 【事実】psycopg2 を使うコードがある（backend/app/tasks/refresh_meta_tokens.py 等）。psycopg2 は値を SQL 文面に埋めてから送るため、pg_stat_activity.query に値（トークン等）がそのまま入る。
  - 【推測】先頭の語と値のあいだにスペースが無い SQL（例: `SELECT'…'`、`UPDATE\n\tt\tSET…` のようにタブ・改行だけで区切られたもの）が来ると、次のスペースまでの文面・値が公開ログに出る。今のコードでそうなる SQL があるかは全数を確かめていない【未確認】。ADR-1037 What 5 の「値は出さない」を作りで保証していない。
  - 直し方（案）: `upper(coalesce(substring(a.query from '^[[:space:]]*([A-Za-z]+)'), '-'))` のように、先頭の空白類を飛ばして英字だけを取る。design §13-4 のコードブロックも同じに直す。試験の判定を足すかは設計側で決める（Reviewer は試験を決めない）。
- application_name:
  - 【事実】リポジトリ内で設定しているのは固定文字列だけ（backend/app/database.py:15,70、backend/app/tasks/tcg_extraction.py:790、tcg_extraction_recovery.py:170、viewer_inventory_cache.py:117、scripts/test_rollback_simulation.sh:91）。psql は既定で `psql`。
  - 【未確認】接続文字列（secrets の DATABASE_URL 等）に `application_name=` が入っているか、外部の道具（Grafana・監視・reader 鍵の接続など）が何を名乗るかは見ていない。クライアントは任意の文字列を名乗れるので、秘密が入る経路はリポジトリ外にありうる。
- usename: 【事実】DB のロール名。秘密ではないが内部のロール名が公開ログに出る（migration にも載っている名前なら新しい露出ではない。全ロールの照合は【未確認】）。
- relname:mode: 【事実】relkind r/p/v の表名のみ。表名は migrations/ に載っている。
- 【推測】pg_locks はクラスタ全体の行を返すが、`l.database` で絞っていないため、別 DB の鍵の oid がたまたま jarvis_db の pg_class と一致すると違う表名が出る。秘密の露出ではなく正確さの問題。→ 提案 S1。

## 4. 最悪時間（design §3・§13-2）
- 【事実】再試行の総数は `SQL_RETRY_BUDGET=40` で決まり、便1と同じ。最悪 40×(1+3)=160秒＋通常138秒、5秒待ち8ファイルでも 40×(5+3)+138=458秒（design.md:30）。
- 【事実】log_lock_holders の呼び出しは「衝突したファイルごとに1回目」＋「上限到達で1回」。衝突ファイル数は予算で上限があり（最大41ファイル）、呼び出しは最大42回程度。試験ログの1回あたりは数ms〜数十ms（sandbox-log-2.txt の時刻差）。【推測】本番でも docker exec 1回0.1〜0.3秒程度なら最大十数秒の上乗せで、458秒＋α は ssh-action の打ち切り10分（600秒）に収まる。本番での1回の所要は【未確認】。
- 判定: 収まる（ただし S2 のとおり問い合わせ自体に時間の上限が無い）。

## 5. 試験 tests/sandbox/migration-run-sql-retry.sh
- 抽出範囲: 【事実】awk で `^SQL_LOCK_TIMEOUT=` から始め、`^run_sql() {` を見た後の最初の `^}` で止める。実ファイルでは :65 から :105 まで＝41行（65〜105 で 41 行）。試験ログ両方で `extracted lines ...: 41`。§13-5 の指定どおり。
- T3b・T3c: 【事実】T3 のログに `lock holders (xact > 1s):` と `products:AccessShareLock` がある判定、`pg_sleep` が無い判定。§13-5 どおり。
- T7: 【事実】既定値 MAX_ATTEMPTS=40・BUDGET=40 の判定。§13-5 どおり。
- T8: 【事実】T4 と同じ「1回目だけ deadlock」で `lock holders` 見出しが1回、rc=0。§13-5 どおり。
- T1〜T6: 【事実】差分は抽出行と追加ブロックのみで、T1〜T6 の判定式は変わっていない。
- 試験ログ: 【事実】run 39580339701（headSha b140c1505）と run 39580958172（headSha c3a276375＝今の head）とも conclusion=success、T1〜T8 全 PASS・`RESULT: PASS`。b140c1505→c3a276375 の差は抽出範囲外のコメント1行と design.md 1行。
- 【事実】試験は `set -uo pipefail` で動き、set -e は付いていない。本番の set -e 下での振る舞い（上 2）は試験では確かめておらず、上 2 の手元確認と bash の仕様に基づく。
- 【事実】T3c は `pg_sleep` という1語が出ないことしか見ない。R1 の形（記号・改行の後ろの文面）は捉えない。

## 6. 文書と実装の食い違い
- 【事実】ADR-1037 What 2（1ファイルでも40回まで）・What 5（ファイルごとの1回目と上限到達時に一覧、出す列）・結果欄は、実装と一致。
- 【事実】ADR-1037 What 3「値の正本は run_sql の直前の4行」: 便1.1 で 4行と run_sql のあいだに log_lock_holders が入ったため「直前」ではなくなった。正本の4行自体は変わっていない。軽微（S4）。
- 【事実】What 5 の「値は出さない」は R1 のとおり作りで保証されていない。
- 【事実】design §13-3〜13-7 と実装は一致。

## 7. PR 本文
- 触るファイル: 【事実】本文の8件と `git diff origin/main...HEAD --name-only` の8件が一致。
- 削除するファイル欄: 【事実】3件（ADR-1037・run_all_migrations.sh・試験）は削除ではなく行の削除を含む変更ファイル。`--diff-filter=D` は0件。この欄の書き方がリポジトリの起票ガードの決まり（行削除を含むファイルを並べる）に沿っているかは【未確認】。
- GO 記録: 【事実】GO発行者（ADR-1003 委任・根拠）・日時・GO原文・対象と変更3行サマリ・バックアップ確認（不要と理由）・委任条件①〜④・相乗りなし・戻し方の欄があり、ADR-136 / ADR-1003 の形。
  - 空欄（判定から除外）: 日時、GO原文の番号（`GO #（番号）`）、条件③の報告時刻。マージ直前に埋めること。
- 【事実】`docs/handoff/migration-lock-timeout/review-code.md` の差分は #4610 の再審査記録（+36行）の追記で、便1.1 の内容ではないが「触るファイル」に載っている。範囲外の変更ではあるが害は無い（情報のみ）。

## 8. migrations/・.github/ の変更
- 【事実】`git diff origin/main...HEAD --name-only -- migrations .github` は0件。

## 指摘一覧
| ID | 重さ | 内容 | 場所 |
|---|---|---|---|
| R1 | 必須 | cmd がスペース区切りのみ・英字以外も通すため、改行始まりの SQL では先頭1語が出ず、区切りがスペース以外の SQL では文面・値が公開ログに出うる。英字だけを取る形に直す（design §13-4 も同時に） | scripts/run_all_migrations.sh:74、design.md:182 |
| S1 | 任意 | pg_locks を `l.database = (SELECT oid FROM pg_database WHERE datname = current_database())` で絞る（別 DB の oid 衝突で違う表名を出さない） | scripts/run_all_migrations.sh:74 |
| S2 | 任意 | 一覧の問い合わせに `-e PGOPTIONS="-c lock_timeout=1s -c statement_timeout=5s"` 等で時間の上限を付ける | scripts/run_all_migrations.sh:74 |
| S3 | 任意 | `-i` を外すか `</dev/null` を付け、スクリプトの stdin を docker exec に渡さない | scripts/run_all_migrations.sh:74 |
| S4 | 任意 | ADR-1037 What 3 の「run_sql の直前の4行」を実際の並びに合わせる | docs/adr/ADR-1037-migration-lock-timeout.md:17 |

## 生の材料
- 試験ログ: /tmp/CC報告ファイル/migration-lock-timeout/impl-1-1/sandbox-log.txt、sandbox-log-2.txt
- PR 本文: /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/3a283ede-1595-4313-9392-a3ed5515cfac/scratchpad/prbody.txt

VERDICT: REVISE on c3a276375a46fb1a842784ea55906937135a2aad PR #4613

## 再審査（head e5afcadde668616b5e3c546935dbdc67fe7541bd）

- 審査者: Claude Opus（Reviewer 役。読み取りのみ・コミットなし）
- 対象: PR #4613 head `e5afcadde668616b5e3c546935dbdc67fe7541bd`（`gh pr view 4613 --json headRefOid` と worktree の HEAD・origin のブランチ先頭が一致）。c3a276375 からの commit は e5afcadde の1つ
- 判定: **APPROVE**
- CI と GO 欄の空欄（日時・番号・条件③の時刻）は判定に含めていない。

### 1. 直しと設計の一致・新しい問題
- 【事実】`git diff c3a276375 e5afcadde` は5ファイル: scripts/run_all_migrations.sh（:74 の1行置換）、tests/sandbox/migration-run-sql-retry.sh（T3d の+9行）、ADR-1037（What 3・5 の2行）、design.md（§13-4 のコードブロック置換＋説明5行、§13-5 に T3d 1行）、review-code-1-1.md（前回の審査記録の新規追加）。
- R1: 【事実】cmd は `upper(coalesce(substring(a.query from '^[[:space:]]*([A-Za-z]+)'), '-'))`。scripts/run_all_migrations.sh:74 と design.md §13-4 のコードブロックが文字単位で同じ。→ 解消。
- S1: 【事実】サブクエリに `l.database = (SELECT oid FROM pg_database WHERE datname = current_database())` が入った。→ 解消。
- S2: 【事実】`docker exec -e PGOPTIONS="-c lock_timeout=1s -c statement_timeout=5s"`。→ 解消。
- S3: 【事実】`-i` が無くなった。psql は `-c` なので stdin は要らない。→ 解消。
- S4: 【事実】ADR What 3 は4つの変数名を並べる書き方になった。What 5 は「命令の先頭の英字の並び」「鍵を持つ表名（今の DB の分）」に直り、実装と一致。→ 解消。
- 【事実】run_sql と、set -e・`&&`・`|| true` の組み合わせは変わっていない。前回 2 の結論（移行の成否を変えない）はそのまま当てはまる。問い合わせが時間切れやエラーになっても、`2>&1` で文面がログに出るだけで、`|| true` で0に倒れる。
- 【事実】`bash -n` は両ファイルとも合格。`shellcheck -S warning` は scripts/run_all_migrations.sh で0件。試験ファイルの7件はどれも SC2034（eval で使う変数を「未使用」と誤判定するもの）で、origin/main の同じファイルも7件。増えていない。
- 【事実】T3d は §13-5 の追加行どおり（7列目が `^[A-Z]+$|^-$` で、T3 の持ち主は `BEGIN`）。T1〜T8・T3b・T3c の判定式は変わっていない。
- 軽微（直さなくてよい）: scripts/run_all_migrations.sh:71 と design.md の同じコメントは「命令の先頭1語と表名だけ」のまま。中身（英字の並び）とほぼ同じ意味なので、食い違いとしては扱わない。
- 【推測】時間の上乗せ: 一覧の問い合わせ1回の最長は5秒（statement_timeout。鍵待ちは lock_timeout の1秒が先に効く）。呼び出しは最大42回程度なので、最長の上乗せは理屈では約210秒になる。通常の最悪 160＋138＋210＝508秒は600秒に収まる。5秒待ちの8ファイルと重なる極端な場合は 458＋210＝668秒で、600秒を超えうる。ただし、ミリ秒で終わる pg_stat_activity の問い合わせが毎回5秒かかる状況は確かめておらず、起こりにくい。止めるほどの指摘ではない（情報のみ）。

### 2. PostgreSQL 16 の文法・挙動
- 【事実】手元の使い捨て PostgreSQL 16.15（Homebrew、scratchpad の initdb）で次を実行した。
  - `substring(q from '^[[:space:]]*([A-Za-z]+)')` に upper と coalesce をかけた結果:
    - 改行と空白の後の SELECT → `SELECT`
    - `UPDATE\n\tt SET tok='abc'` → `UPDATE`
    - `SELECT'secret'` → `SELECT`
    - `BEGIN; SELECT pg_sleep(3)` → `BEGIN`
    - `/* c */ SELECT 1`・`(SELECT 1)`・空文字・NULL → どれも `-`
    - タブで始まる `with ...` → `WITH`
    - 値や記号は1件も出なかった。括弧が1組の正規表現は、その部分だけを返す（PostgreSQL の substring の仕様どおり）。
  - `PGOPTIONS="-c lock_timeout=1s -c statement_timeout=5s"` で接続: `show statement_timeout`＝5s、`show lock_timeout`＝1s。`select pg_sleep(6)` は約5秒で「ステートメントのタイムアウトのためステートメントをキャンセルしています」になった。PGOPTIONS は接続の起動時に設定として渡るので、`-c` の1文に効く。
- 【事実】sandbox run 39582639505（headSha e5afcadde、conclusion=success、postgres:16 コンテナ）のログ（/tmp/CC報告ファイル/migration-lock-timeout/impl-1-1/sandbox-log-3.txt）:
  - 抽出は41行。
  - 持ち主の行は `122 | postgres | psql | active | Timeout | 2 | BEGIN | products:AccessShareLock` で、新しい問い合わせが PG16 で通っている。
  - T1〜T8・T3b・T3c・T3d は全部 PASS で、`RESULT: PASS`。
- 【事実】`[[:space:]]` と `'...'` は bash の二重引用符の中で展開されない（`$`・バッククォート・`\` を含まない）。上の sandbox の出力でも、文字のまま psql に届いている。
- 【事実】pg_locks の共有カタログの行は database=0 なので S1 の条件で外れる。対象はふつうの表（relkind r/p/v）なので、出したい情報は減らない。

### 3. PR 本文の触るファイル9件と diff
- 【事実】`git diff origin/main...HEAD --name-only` の9件と、PR 本文「触るファイル」の9件が一致した（review-code-1-1.md が追加）。相乗りの欄も「9件のみ」。
- 【事実】`migrations/`・`.github/` の変更は0件。
- 削除するファイル欄: 起票ガードの決まり（行を削除したファイルを並べる）である、と依頼元から説明を受けた。3件はどれも差分に行の削除がある。前回の【未確認】はこれで閉じる（ガードの実装そのものは読んでいない）。
- 【事実】PR 本文の検証欄に sandbox run 39582639505（head e5afcadd）が載っている。

### 残っている未確認（判定に影響しない）
- リポジトリ外の接続（secrets の接続文字列・監視・reader 鍵など）が application_name に何を名乗るか。
- 本番での一覧の問い合わせ1回の所要時間。

VERDICT: APPROVE on e5afcadde668616b5e3c546935dbdc67fe7541bd PR #4613
