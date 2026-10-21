# コード審査 — migration-lock-timeout 便1（PR #4610）

- 審査者: Claude Opus（Reviewer 役。読み取りのみ）
- 対象: PR #4610 `release/migration-lock-timeout` head `fa27ab5b766fc7ef5bf0c67f048cfe9bc3112fa5`（origin/main からの commit は 7314c23f7・fa27ab5b7 の2つ）
- 照合先: design.md §3・§4・§6、recon.md、review-design.md、card.md、ADR-1037、ADR-1003、ADR-136、`git diff origin/main...HEAD`（734行を全部読んだ）、sandbox run 39572828580 のログ（340行を全部読んだ）
- 判定: **REVISE**（直すのは PR 本文の GO 記録1か所だけ。コードと試験は差し戻すところなし）

## 1. 範囲が守られているか
- 【事実】変更は10ファイル。PR の「触るファイル」10件と一致する（`gh pr view 4610 --json files`）。migrations/・deploy.yml・`.github/workflows/` の変更は0件。
- 【事実】`scripts/run_all_migrations.sh` の差分は1か所（:58-97 の範囲）だけ。:25 PSQL、:49-59 run_py、EXIT trap、登録行（`^run_sql` / `^run_py`）はどれも変わっていない。
- 【事実】`tests/sandbox/lock-timeout-repro.sh` は card.md の add 一覧（7件＋README）に入っていないが、別 commit 7314c23f7（recon §4 が根拠に使った再現試験）で入ったもの。recon.md が参照していて、PR 本文にも書かれている。範囲外の変更ではない。
- 【事実】design §4-1 のコードとの照合: `sed -n '/^# 稼働中のアプリとロック/,/^}/p' scripts/run_all_migrations.sh` と design.md の bash ブロックを diff → 差は0（IDENTICAL）。

## 2. 確かめるよう頼まれた5点

### 2-1. run_sql の今までの動きが壊れていないか
- 成功時: rc 0 なら errlog を消して `return 0`（変わっていない）。
- deadlock 以外のエラー: grep に当たらなければ `return "${rc}"`。`run_sql <file>` は最上位で呼ばれ、`set -e`（:20）でその場で止まる。今までと同じ。試験 T5（`SELECT 1/0`）は rc=3、retry 0。
- set -e との関係: `docker exec ... || rc=$?` と `if grep -qE ...` は、どちらも set -e で止まらない書き方（今までと同じ形）。
- STEP/TOTAL: STEP は関数に入ったとき1回だけ増える（再試行では増えない。ログの `[1/1]` のまま再試行していることで確認）。TOTAL は :47 `grep -cE '^run_(sql|py)[[:space:]]'`。新しい行（`SQL_...=`・コメント）はこのパターンに当たらない。`run_sql() {` は `(` が続くので当たらない（今までと同じ）。
- 行を数える・読む他の仕組み: `scripts/check-migration-registration-exists.sh:116` と `scripts/check-migration-duplicate-registration.sh:38`（`^run_(sql|py)[[:space:]]`）、`scripts/check-migration-column-churn.js:58`（`^run_sql[ \t]+`）、`scripts/migration-dryrun-report.py:27` と `scripts/check-migration-value-writes.py:171`（`startswith("run_sql ")`）。新しい行はどれにも当たらない。消えた `SQL_DEADLOCK_MAX_ATTEMPTS` を参照している所はリポジトリに0件（docs/ を除いて grep）。
- shellcheck（-S warning）: 変更後の `scripts/run_all_migrations.sh` も origin/main 版も警告0件。

### 2-2. `docker exec -e PGOPTIONS=... -i` の書き方と .env
- 引数の順は `docker exec [OPTIONS] CONTAINER COMMAND` に合っている（`-e` と `-i` が両方コンテナ名より前）。`PGOPTIONS="-c lock_timeout=${SQL_LOCK_TIMEOUT}"` は二重引用で1つの引数になる。`${PSQL}` は今までどおり引用なし（わざと単語に分けている）。
- 効いていることの観測: sandbox ログ T1・T3 に `ERROR:  canceling statement due to lock timeout`（:214・:235）。PGOPTIONS が psql に届いて lock_timeout が効いている。
- .env の上書き: `source .env`（:31-36、set -a）は SQL_* の行（:65-68）より前にある。`${VAR:-既定}` の形なので、.env に `SQL_LOCK_TIMEOUT` などがあればその値が使われる。
  - 【事実】リポジトリの `.env.example` に `SQL_` / `lock_timeout` を含む行は0件。deploy.yml の移行ステップ（:563-581）には `envs:` が無く、SQL_* は渡していない。
  - 【未確認】本番 VPS の `/home/ubuntu/salesanchor/.env` の中身は見ていない（見られる立場にない）。ADR-1037 What 3 で「.env には書かない」と決めているので、差し戻しにはしない。反映後の最初の入れ替えのログで `(total N/40)` が出ていれば既定値が使われている、と確かめられる（"lock conflict" が出たときだけ）。

### 2-3. 最悪の時間が10分に収まるか
- design §3 の計算: 40回 ×（待ち1秒＋間隔3秒）＝160秒＋通常の最大138秒 ≒ 300秒 < 600秒。
- 【事実】design の計算に入っていない要素が2つある。どちらを足しても 600 秒には届かない:
  1. `SET LOCAL lock_timeout = '5s'` の8ファイル（recon §5）では1回の待ちが5秒になる。40回全部がこの8ファイルで起きても 40×(5+3)=320秒＋138秒＝458秒。
  2. 再試行のたびにファイルを頭から流し直す時間。通常は全約1000本で138秒なので、1本あたりはわずか。
- 判定: 収まる。直すことではないが、ADR-1037 Why の「最悪でも約300秒」は5秒ファイルを入れると約460秒になる。便2で値を見直すときに一緒に直すとよい（今回の判定には入れない）。

### 2-4. 試験が本物の run_sql を使っているか、PASS の基準が甘くないか
- 本物を使っている: `sed -n '/^SQL_LOCK_TIMEOUT=/,/^}/p'` で抜き出して `eval`。ログに `extracted lines ...: 33`、手元で同じ sed を流しても33行。抜き出しの終わりは run_sql の閉じ `}`（1列目）で合っている。card.md の「約45行」は見積もりの誤りで、抜き出し自体は正しい（`defaults: lock_timeout=1s max_attempts=10 sleep=3 budget=40` で既定値も正本から来ていることが分かる）。
- T1: C の測定値 `87 498 82 82 81 80 82 560`、最大 560ms ≤ 1500ms。498・560 は B が待っている間に C が後ろに並んだ回で、B の待ちと重なった測定が実際にある（重なっていない測定だけで通った PASS ではない）。
- T2: rc 0、retry 1、parse_logs が消えている（`to_regclass` が null）の3つを全部見ている。
- T3: rc≠0、"retry limit reached" あり、5268ms < 10000ms。ログでも 2/3 → 3/3 → limit と並ぶ。
- T4: rc 0 かつ retry がちょうど1回。`count_retry` は `lock conflict; retry [0-9]` なので limit の行は数えない。
- T5: rc≠0 かつ retry 0。
- T6: rc≠0 かつ retry がちょうど2回。ログ `retry limit reached (file 3/10, total 2/2)` で、1ファイルの上限ではなく全体の上限で止まったことが分かる。
- run の対象: ログ :91・:105 で checkout が `fa27ab5b766fc7ef5bf0c67f048cfe9bc3112fa5`。審査対象の head と同じ。
- 気になるが差し戻さない点（【事実】）: 準備の `migrations/20260604_130000_create_supplier_parse_stats_view.sql` は、試験の suppliers 表に name 列が無いので毎回 `ERROR:  column s.name does not exist` で失敗している（ログ :206・:228。出力を捨てているので試験は止まらない）。そのため v_supplier_parse_stats ビューが無いまま試験している。本番と違うのは DROP VIEW が空振りになる点だけで、試している products のロック待ちには関係しない。再現試験 `tests/sandbox/lock-timeout-repro.sh` も同じ準備の作り。
- T4・T6 の deadlock は RAISE（ERRCODE 40P01）で作ったもので、本物の deadlock ではない。design §4-2 の指定どおり。grep が見るのはエラー文なので、本番の deadlock と同じ `ERROR:  deadlock detected` の行が出ていることをログで確認した。

### 2-5. GO 記録・委任条件（ADR-1003 / ADR-136）
- 【事実】migration ファイルの追加・変更は0件で、DROP TABLE / DROP COLUMN を含む migration の追加行は無い。workflow-lint.yml の変更も無い。ADR-1003 の例外には当たらず、委任 GO で進めてよい。
- 【事実】GO記録には、GO発行者（「POの委任に基づくClaude Opus発行」、ADR-1003 の書き方どおり）、GO原文、対象と3行サマリ、バックアップ確認、相乗り、戻し方が書かれている。「削除するファイル」に変更したファイル2件を書いているのは、`.github/PULL_REQUEST_TEMPLATE.md:34`（1行でも変えたファイルを全部書く）どおり。
- **直す点（R1）**: PR 本文「委任条件」の③が「PO 承認の範囲に収まる」になっている。ADR-1003「委譲の条件」3 は **「PO に3行まとめ（対象・変更内容・バックアップ確認）を報告済み」** で、ADR-136 ①（マージ前にチャットで対象・変更3行サマリ・直前バックアップ確認を PO に示す）もこれを求めている。今の本文は ADR に無い条件にすり替わっていて、3行まとめを PO に報告したかどうかが記録に残らない。
  - 直し方: 委任条件の③を ADR-1003 の文言にする。マージ前に PO へ3行まとめを報告し、その日時（JST の時刻まで）を GO記録に書く。今の「日時: 2026-10-21 JST」は時刻が無いので、GO を出す時に時刻まで書く。
  - コードと試験は変えなくてよい。PR 本文を直すだけなので head SHA は変わらない。直したあと同じ SHA で再審査すれば APPROVE にできる。

## 3. 安全面
- secrets・本番への接続は差分に無い。試験のパスワード `sandbox` は使い捨てコンテナ用の固定値で、既存の試験と同じ。
- 戻し方: revert で元に戻る。DB の中身は変えない（design §10）。

## 4. Evaluator・マージに渡すこと
- 審査時点（2026-10-21）で必須 CI のうち「マイグレーション全件ドライラン（実DB）」「deprecated 列の新規参照チェック」「pytest-run-internal」はまだ pending（`gh pr checks 4610`）。ADR-1003 条件1 は満たされていない。
- K6・K7（本番の入れ替え3回）は反映後に測る。状態は「測定中」として分けて報告する（review-design.md 6）。

生の材料: /tmp/CC報告ファイル/migration-lock-timeout/review/（diff.txt・pr.json・checks.txt・extract.txt・design-block.txt・sc-run.txt・sc-main.txt）

VERDICT: REVISE on fa27ab5b766fc7ef5bf0c67f048cfe9bc3112fa5 PR #4610
