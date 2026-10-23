# コード審査 — ai-ro-restore-on-failure（PR #4618）

- 対象: head 035cc8c5a（branch release/ai-ro-restore-on-failure）
- 照合: docs/handoff/ai-ro-restore-on-failure/design.md §3、card.md、review-design.md（APPROVE）、docs/adr/ADR-1024-ai-readonly-db-path.md 改訂欄
- 審査者: Reviewer（Opus）／2026-10-21
- 判定: REVISE（必須1件。文書の直しだけで足りる）

## 1. design §3 との1文字照合

【事実】
- design.md §3「変更後」のコードブロックと、台本の `^AI_RO_CREATE_SQL=` から最初の `^}$` までを diff → 差分0（FN_SAME）。
- design.md §3「コメント（:121-124）」のブロックと台本 :121-125 を diff → 差分0（CM_SAME）。
- `git diff origin/main...HEAD -- scripts/run_all_migrations.sh` のハンクは1つ（@@ -118,29 +118,31 @@）。numstat 15 追加 / 13 削除。変更はコメント・変数1行・関数の中だけで、ほかの行に変更は無い。
- `bash -n scripts/run_all_migrations.sh` OK。`shellcheck -S warning`（台本・試験）出力なし。

## 2. 終了コード（K3）

【事実】
- `local rc=$?` が関数の最初の文。`trap - EXIT` で再入を止めている。
- 抜け道は3つ（SQL が無い／作成失敗／作成成功）で、すべて `exit "${rc}"`。旧コードの `exit 0` は rc=0 の回にしか届かなかったので、成功回の終了コードは今と同じ。
- set -e: 作成の `docker exec` は `if !` の条件の中なので errexit の対象外。`[ ! -f ... ]` も if の条件。trap の中で set -e が効いても、作成の失敗で関数が途中終了する道は無い。
- 試験の実測（run 39598850269）: T1 rc=3、T2 rc=0、T3 rc=3、T4 rc=0、T7 rc=3。

## 3. 秘密列の漏れ道

【事実】
- 作成 SQL・拒否リストはこの PR で変わっていない（diff の対象に migrations/ が無い）。
- 列はカタログの列名で拒否リストに当てる（create SQL :34-41）。途中まで進んだ DB にも同じ判定が当たる。
- T1: 拒否リストに当たる列（api_token）はビューに0列、ビューは存在（has_sb_items=1）。
- 失敗時だけの新しい読み取りの道は見つからなかった（review-design.md :43 と同じ結論）。

## 4. 試験 tests/sandbox/ai-ro-restore-on-failure.sh

【事実】
- 本物の切り出し: :39 で `scripts/run_all_migrations.sh` から awk で `^AI_RO_CREATE_SQL=`〜`^trap _ai_ro_create_on_exit EXIT` を切り出し、子の bash で eval している。関数の写しは持っていない。ログ「T6 extracted lines ... 22」「first: AI_RO_CREATE_SQL=...」「last: trap _ai_ro_create_on_exit EXIT」。始まりの行が無ければ空になり、:46 で FAIL になる。
- 何もしない関数で PASS になる判定の有無:
  - T1: rc=3 ＋「recreating」行 ＋ N が空でない ＋ N=ビュー数 ＋ ビューあり ＋ 秘密列0。空の関数では落ちる。旧コードでも落ちる。
  - T3: 警告の行が要るので、空の関数・旧コード（警告を出さずに skip）では落ちる。
  - T7: 10秒以内が要る。上限が無ければ相手の鍵（pg_sleep(20)）を約18秒待つので落ちる。
  - T2・T4: 旧コードでも通る（成功回の動きが変わらないことの確認なので妥当）。空の関数では T2（ビューあり）・T4（警告）が落ちる。
- T5 は、読み取りが作成の DDL と重なった時刻に走ったかは確かめていない（下の任意 N2）。

## 5. 公開リポのログ

【事実】run 39598850269 のログ（T7、statement_timeout の打ち切り）:

```
ERROR:  canceling statement due to statement timeout
CONTEXT:  SQL statement "CREATE VIEW ai_ro.public__sb_items AS SELECT id, name FROM public.sb_items"
```

- 打ち切りの回は、psql の既定の VERBOSITY（default）で CONTEXT 行が出て、その時に流していた CREATE VIEW の文面（表名と、拒否リストを通った列名）がログに出る。
- 値は出ない。秘密列の名前も出ない（拒否リストを通った後の列だけ）。
- 旧コードにはこの道が無かった（ビュー1本ずつの失敗は WHEN others に飲まれて、文は出ない）。

【事実】design.md「弊害・トレードオフ」は「値や SQL 文は出ない（件数と表名だけ）」と書いている。打ち切りの回については、これは実際の動きと合わない。

## 6. sandbox-test と 035cc8c5a との差

【事実】
- `gh run view 39598850269`: workflow「Sandbox test (manual)」、headSha d4152e0a3410c5b6a1ab1dbf3ae6520298333163、status completed、conclusion success。ログの最後は「ALL PASS (T1-T7)」。
- `git diff d4152e0a3 035cc8c5a --stat`: docs/adr/ADR-1024-ai-readonly-db-path.md だけ（5行追加）。コード・試験の差は無い。
- ADR に写した数字（161ms／56ms／3秒／rc=3／views=0／T8 child_rc=143、bash 5.2.21）は、run のログと合う。

## 7. PR 本文のファイル欄

【事実】`git diff origin/main...HEAD --numstat` は9ファイル。
- 「触るファイル」の9件は name-status の9件と一致。
- 「削除するファイル」（1行でも削除・変更した行があるファイル。PULL_REQUEST_TEMPLATE.md :34、scripts/check-process-artifacts.js :898）: 削除行のあるファイルは usage.md（1/1）と run_all_migrations.sh（15/13）の2件だけ。本文の2件と一致。

## 指摘

### 必須

- M1 ログに SQL の文面が出る道がある（§5）。打ち切り（57014）の回は、psql の CONTEXT 行に CREATE VIEW の文面（表名と秘密でない列名）が出る。design.md「弊害」の「値や SQL 文は出ない」と、実際の動きが合わない。直し方は、次のどちらか一つ。
  - (a) 文書だけ直す: design.md「弊害」と ADR-1024 改訂欄に、「打ち切りの回だけ、そのとき流していた CREATE VIEW 文が1本出る（表名と、拒否リストを通った列名。値と秘密列名は出ない）」と書く。T7 のログ行を根拠にする。台本は変えない。
  - (b) 出さないようにする: 作成の psql に `-v VERBOSITY=terse` を足す。design §3 の改訂と再審査が要る。
  - どちらにするかは Opus が決める。列名は公開済みの migrations に既にあるので、(a) で足りるかどうかの判断になる。

### 任意

- N1 `migrations/20261017_125900_drop_ai_ro_views.sql:5-6` のコメント「スクリプトが正常終了したときだけ EXIT trap で最後に流す」が、今回の変更で古くなった。migrations/ は危険パスで、この設計の対象外なので、別件で直す。
- N2 T5 は、読み取り（sleep 0.1 の後）が作成の DDL と同じ時刻に重なったかを確かめていない。重なったかどうかは、まだ確かめていない（作成の全体は161ms。うち DDL がいつ流れたかはログに無い）。K2 の根拠を強くしたいなら、作成中に pg_locks を取る等。
- N3 T8 の記録: SIGTERM の回は trap の中の rc が0として扱われ（「失敗」の行が出ない）、作成は流れ、子の終了コードは143だった。範囲外と ADR に書いてあるとおり。次に信号の扱いを決めるときの材料になる。

VERDICT: REVISE

## Planner の対応（2026-10-21）
- M1: 案 (b) を採る。表名には、テナントの区画の名前が入りうる。打ち切りの回だけでも、公開ログに SQL 文を出さない方に倒す。
  - design §3 で、作成の psql に `-v VERBOSITY=terse` を渡すように改めた。
  - 根拠は PostgreSQL 16 公式文書 libpq-control の「In TERSE mode, returned messages include severity, primary text, and position only」（2026-10-21 確認）。
  - T7 の合格条件に「CONTEXT: と SQL statement が0行」を足した。ADR-1024 の改訂欄にも書いた。
- N1: migrations/ の古いコメントは、この設計の対象外。別件で直す（本 PR では触らない）。
- N2: T5 は「作成の最中に読みが重なったか」を確かめていない。設計の受け入れ基準にある数値（作成3000ms未満・読み取り1000ms未満）は満たしている。重なりの確かめは、まだ確かめていないと記録する。
- N3: 了解（ADR に記録済み、範囲外）。
- この直しの後に、もう一度コード審査を受ける。

## 再審査（head f3db29faf、2026-10-21）

- 判定: REVISE（必須1件。PR 本文だけの直しで、コード・試験・文書の中身には指摘なし）

### 確かめたこと

【事実】
- 台本と design §3: design.md「変更後」ブロック（22行）と台本 `^AI_RO_CREATE_SQL=`〜最初の `^}$` を diff → 差分0。コメント（:121-125）も差分0。`git diff origin/main...HEAD -- scripts/run_all_migrations.sh` のハンクは1つ（numstat 16/13）。035cc8c5a からの台本の差は、コメント1行の追加と、作成の行の `${PSQL}` の直後に ` -v VERBOSITY=terse` を足したことだけ。`bash -n` OK、`shellcheck -S warning`（台本・試験）出力なし。
- K3 への影響: `-v VERBOSITY=terse` は psql の変数を1つ足すだけで、`if !` の構造と3つの `exit "${rc}"` は変わっていない。
- terse で成功回の作成結果の行が残るか: sandbox run 39600086141 の T1 に `NOTICE:  ai_ro views created: 1, columns excluded: 1, failed: 0 []` があり、`T1 rc=3 created_N=1 view_count=1 has_sb_items=1 api_token_cols=0`、PASS。T2・T5・T8 でも同じ行が出た。
- T7: `ERROR:  canceling statement due to statement timeout` だけが出て、CONTEXT 行と SQL statement 行は無い。`T7 elapsed_sec=3 rc=3 views=0 context_lines=0 sql_statement_lines=0`、PASS。
- T7 の判定が甘くないか:
  - 足した2条件（`grep -ac 'CONTEXT:'`・`grep -ac 'SQL statement'` が 0）は、前回の run 39598850269 の t7 ログでは各1行あったので、terse が無ければ落ちる。
  - `grep -c` は0件のとき「0」を出して rc=1 で終わり、`|| true` で値は「0」のまま残る。空文字になって通る道は無い。
  - 残りの条件（10秒以内・rc=3・警告・ビュー0本）は前回と同じ。
- sandbox: `gh run view 39600086141` は workflow「Sandbox test (manual)」、headSha 4df4308d709ab7dba24228681f443eef8a055049、completed / success。ログの最後は「ALL PASS (T1-T7)」。T6 の切り出しは23行（コメント1行が増えた分）。
- 4df4308d7 から f3db29faf まで: `git diff --name-only` は docs/adr/ADR-1024-ai-readonly-db-path.md だけ（1行の追加/置換）。台本・試験の差は無い。ADR に書いた結果（CONTEXT と SQL 文が0行で、残ったのは「canceling statement due to statement timeout」だけ）は run のログと合う。
- design・card の追補: design §3 の理由・受け入れ基準 T7・弊害の文が、台本と試験の中身と合っている。

### 必須

- M2 PR 本文の「触るファイル」に `docs/handoff/ai-ro-restore-on-failure/review-code.md` が無い。
  - `git diff origin/main...HEAD --numstat` は10ファイルで、review-code.md（96/0）が新しく入っている。
  - 本文の「触るファイル」は9件のまま。
  - CI「process-artifacts gate」が fail している（run 39600360138: 「❌ 宣言外のファイルを変更しています: - docs/handoff/ai-ro-restore-on-failure/review-code.md」）。
  - 直し方: PR 本文の「触るファイル」に review-code.md を足す。「削除するファイル」は今のままで合っている（行を削除したファイルは usage.md 1/1 と run_all_migrations.sh 16/13 だけ。review-code.md は追加だけ）。
  - コードの head は変わらないので、本文を直して gate が緑になれば、この審査は f3db29faf にそのまま当たる。

### 任意

- N4 PR 本文の試験の記録が、前の run 39598850269（head d4152e0a3）のままになっている。run 39600086141（head 4df4308d7）と T7 の context_lines=0 / sql_statement_lines=0 を書き足すとよい。
- N5 T7 は、警告の原因が打ち切り（57014）であることを文面では確かめていない（10秒以内・ビュー0本・ai_reader ありで間接的に絞っている）。`canceling statement due to statement timeout` が1行あることを条件に足すと、より固くなる。
- N1〜N3 は前回のまま（Planner の対応どおり、範囲外または記録）。

VERDICT: REVISE
