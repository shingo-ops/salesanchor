# 実装カード R4b-2 第3便：pre-push で直しかけの変更が残るときも、HEAD の写しで確認を流す

## カード発行前チェック（design-partner.md §5.5。設計パートナーが照合）
| 項目 | 結果 | 中身 |
|---|---|---|
| 0 照合結果を出す | ○ | この表 |
| 1 記号を壊さない | ○ | パス・正規表現・変数は `` ` `` で囲んだ。表の中の `\|` は台本では `|` |
| 2 下書き禁止 | ○ | PR は実装役は作らない。設計パートナーが ready で作る（§9） |
| 3 報告の宛先 | ○ | `docs/handoff/rule-enforcement/impl-report-r4b2-bin3.md` と最後の返事（§10） |
| 4 1便1目的 | ○ | pre-push で直しかけの変更が残るときに写しで流す（2 ファイル＋報告） |
| 5 既存ブランチは起点明示 | ○ | 起点 `origin/release/r4b2-bin3-impl`（設計パートナーが origin/main から作る。このカードは設計 PR で main に入っている） |
| 6 書式は実例で | ○ | 変更後の台本の文をそのまま示した（§3・§4） |
| 7 合格基準を出力まで | ○ | 試験名・列の値・写しが残らないこと・差分が対象ファイルだけであること（§8） |
| 8 数だけで止めない | ○ | 落ちた試験は名前と生出力を出す（§7-4） |
| 9 出力量に上限 | ○ | `tail`・`grep -c`・`--stat` で絞る |
| 10 報告様式 3 点 | ○ | §0 受領確認・§10 冒頭の一文・停止時の 3 点・終端合図 |
| 11 期待値は実測から | ○ | 置き換えは前後の文字の一致で指定。行番号は目安（origin/main 40e846570 で確認。第2便の後この 2 ファイルは変わっていない） |
| 12 停止は 2 段 | ○ | 止まるのは §11 の場合だけ。数の食い違いは記録して続ける |
| 13 委任文 4 点 | ○ | sleep しない・Write/Edit で書く・validate-pr-body は設計パートナーが PR 前に流す・見張りに止められたら言い換えず BLOCKED: |

## §0 受領確認
報告ファイルの 1 行目に「本報告はカード card-r4b2-bin3.md の実行結果である。受領：§0〜§11 を読んだ」と書く。

## §1 目的
提出前の入口（`scripts/dev/check-before-submit.sh`）は、記録済みのファイルに直しかけの変更（`git status --porcelain` で `??` 以外の行）があると、pre-push から呼ばれても終了コード 2 で何も確かめずに終わり、push が素通りしていた。pre-push から呼ばれたとき（環境変数 `CHECK_BEFORE_SUBMIT_CALLER` が `pre-push`）だけ、第2便と同じ HEAD の写しの道で流す。記録の 8 列目は `tracked-copy`。手で流したとき（manual）は今までどおり 2。
設計の正本：`docs/handoff/rule-enforcement/design.md` の「## R4b-2 第3便」節（決め 1〜7・受入条件 M1〜M7）。このカードと設計が食い違えば設計が正で、`NEEDS_DECISION:` で止まる。

## §2 触るファイル（これ以外は触らない）
- `scripts/dev/check-before-submit.sh`
- `scripts/tests/test_check_before_submit.py`
- `docs/handoff/rule-enforcement/impl-report-r4b2-bin3.md`（新規・報告）

触らない：`frontend/.husky/pre-push`・`scripts/new-worktree.sh`・`scripts/dev/validate-pr-body.sh`・CI の設定・記録ファイルの場所と列の数（8 列のまま）・写しの作り方と片付け（:135-157 の第2便の文は §3-5・§3-6 の 2 か所以外変えない）。

## §3 `scripts/dev/check-before-submit.sh` の変更（決め 1・3・4・7）

### 3-1 冒頭の終了コードの説明（今 :10-11。決め 7）
今：
```bash
# 終了コード: 0 = 流した検査が全部 ○ / 1 = 1 つでも × / 2 = 入口が使えない
#   （commit していない変更・origin/main が無い・必須一覧が読めないか 0 件・--only の値が無いか知らない id・流した検査が 0 件）
```
後（2 行目の次に 1 行足す）：
```bash
# 終了コード: 0 = 流した検査が全部 ○ / 1 = 1 つでも × / 2 = 入口が使えない
#   （commit していない変更・origin/main が無い・必須一覧が読めないか 0 件・--only の値が無いか知らない id・流した検査が 0 件）
#   ただし commit していない変更のうち、記録していないファイルだけのとき（R4b-2 第2便）と、pre-push から呼ばれたときの直しかけの変更（第3便）は、HEAD の写しで流す
```

### 3-2 記録の説明（今 :31-32。決め 7）
今：
```bash
# --- 記録（R4b・R4b-2）: どの道で終わっても 1 行足す。書けなくても入口の結果は変えない ---
# 引数の読み取りより前に置く（引数の誤り・--help でも 1 行残す）。7 列目 流し方・8 列目 終了コード 2 の理由
```
後（2 行目の次に 1 行足す）：
```bash
# --- 記録（R4b・R4b-2）: どの道で終わっても 1 行足す。書けなくても入口の結果は変えない ---
# 引数の読み取りより前に置く（引数の誤り・--help でも 1 行残す）。7 列目 流し方・8 列目 終了コード 2 の理由
# 写しで 0・1 のときの 8 列目: untracked-copy = 記録していないファイルだけ / tracked-copy = pre-push で直しかけの変更あり（第3便）
```

### 3-3 `_cbs_log` の 8 列目（今 :53。決め 4）
今の行（一致で探す）：
```bash
  case "$rc" in 0|1) test "$CBS_COPY_OK" = 1 && reason=untracked-copy ;; 2) reason="$CBS_REASON" ;; *) test "$CBS_REASON" = copy-rc && reason=copy-rc ;; esac
```
後（この 1 行を置き換える。`CBS_COPY_KIND` は `${X:-}` で読む。`CBS_COPY_OK` が 0 なら読まない）：
```bash
  case "$rc" in 0|1) if test "$CBS_COPY_OK" = 1; then reason=untracked-copy; test "${CBS_COPY_KIND:-}" = tracked && reason=tracked-copy; fi ;; 2) reason="$CBS_REASON" ;; *) test "$CBS_REASON" = copy-rc && reason=copy-rc ;; esac
```

### 3-4 commit していない変更の注記（今 :126 と :130-131。決め 7）
今：
```bash
# --- commit していない変更があれば止める（見本の runner は commit 済みの HEAD から写しを作るため） ---
```
後：
```bash
# --- commit していない変更があれば止める（見本の runner は commit 済みの HEAD から写しを作るため）。記録していないファイルだけ、または pre-push から呼ばれたときは HEAD の写しで流す ---
```
今：
```bash
  # R4b-2 第2便: 記録していないファイルだけなら、HEAD の切り離しの写しを一時フォルダに作り、その中で同じ引数で流す。
  # --list-fixtures のときと、写しの中（外から CBS_IN_COPY=1 が来たときも含む）では作らない
```
後：
```bash
  # R4b-2 第2便・第3便: 記録していないファイルだけ、または pre-push から呼ばれたとき（直しかけの変更があっても送るのは HEAD）なら、
  # HEAD の切り離しの写しを一時フォルダに作り、その中で同じ引数で流す。手で流したときの直しかけの変更は今までどおり 2（HEAD の 0 を「直しかけも通った」と読み違えないため）。
  # --list-fixtures のときと、写しの中（外から CBS_IN_COPY=1 が来たときも含む）では作らない
```

### 3-5 写しの道に入る条件と表示（今 :132-134。決め 1・3・4）
今：
```bash
  if test "$CBS_REASON" = "dirty-untracked" && test "$LIST_FIX" = "0" && test "${CBS_IN_COPY:-}" != "1"; then
    git status --short | head -20
    echo "記録していないファイルがあります。HEAD の写しで流します（約 40 秒増えます）"
```
後（3 行を次の 9 行に置き換える。`cbs_kind` はどちらの道でも必ず値を入れる）：
```bash
  if { test "$CBS_REASON" = "dirty-untracked" || { test "$CBS_REASON" = "dirty-tracked" && test "${CHECK_BEFORE_SUBMIT_CALLER:-manual}" = "pre-push"; }; } && test "$LIST_FIX" = "0" && test "${CBS_IN_COPY:-}" != "1"; then
    git status --short | head -20
    cbs_kind=untracked
    test "$CBS_REASON" = dirty-tracked && cbs_kind=tracked
    if test "$cbs_kind" = tracked; then
      echo "直しかけの変更があります。push するのは HEAD なので、HEAD の写しで流します（直しかけの変更は確かめていません。約 40 秒増えます）"
    else
      echo "記録していないファイルがあります。HEAD の写しで流します（約 40 秒増えます）"
    fi
```

### 3-6 写しを呼ぶ所（今 :150。決め 4）
今：
```bash
    (cd "$cbs_dir" 2>/dev/null || exit 3; CBS_IN_COPY=1 CBS_ORIG_BRANCH="$cbs_branch" CBS_ORIG_GITDIR="$cbs_gitdir" bash scripts/dev/check-before-submit.sh ${CBS_ARGS[@]+"${CBS_ARGS[@]}"} </dev/null)
```
後（`CBS_ORIG_GITDIR="$cbs_gitdir"` の後に `CBS_COPY_KIND="$cbs_kind"` を足すだけ）：
```bash
    (cd "$cbs_dir" 2>/dev/null || exit 3; CBS_IN_COPY=1 CBS_ORIG_BRANCH="$cbs_branch" CBS_ORIG_GITDIR="$cbs_gitdir" CBS_COPY_KIND="$cbs_kind" bash scripts/dev/check-before-submit.sh ${CBS_ARGS[@]+"${CBS_ARGS[@]}"} </dev/null)
```

:159-161（「commit していない変更があります。commit してから流してください（終了コード 2）。」）は変えない（手で流したときの道として残る）。

## §4 試験の説明の文（`scripts/tests/test_check_before_submit.py` の冒頭。o5）
今（:12）：
```
  4 commit していない変更があると終了コード 2
```
後：
```
  4 手で流して直しかけの変更があると終了コード 2（記録していないファイルだけのとき・pre-push から呼ばれたときは HEAD の写しで流す）
```
今（:19）：
```
  10 pre-push: 印が HEAD と同じなら入口を流さず通す / commit していない変更でも止めない / HEAD と違う中身・削除の push は流さない / × なら止める
```
後：
```
  10 pre-push: 印が HEAD と同じなら入口を流さず通す / commit していない変更（記録していないファイル・直しかけの変更）は HEAD の写しで流し、HEAD が × なら止める / HEAD と違う中身・削除の push は流さない / × なら止める
```
今（:23）：
```
設計: docs/handoff/rule-enforcement/design.md の R4a / R4b / R4c 便3
```
後：
```
設計: docs/handoff/rule-enforcement/design.md の R4a / R4b / R4b-2 第2便・第3便 / R4c 便3
```

## §5 試験（書き換え 1 本・新規 3 本。既存のほかの試験と確かめは消さない・変えない）
見本の場所（既存 `test_tenant_schema_violation_fails` と同じ形）：
- `FAIL = os.path.join(ROOT, "scripts/tests/rule-fixtures/tenant-schema/fail-commit-without-reset/files/backend/app/routers/zz_fixture_router.py.fixture")`
- `PASS = os.path.join(ROOT, "scripts/tests/rule-fixtures/tenant-schema/pass-commit-with-reset/files/backend/app/routers/zz_fixture_router.py.fixture")`
（試験の中の局所変数として書く。クラスの外に定数を足してもよい）

| M | 試験 | 中身 |
|---|---|---|
| M1・M6 | `test_prepush_runs_in_copy_on_dirty_tracked`（`test_prepush_dirty_tracked_reason` を名前ごと置き換え・同じ場所） | `put("docs/zz-tracked.md", "x\n")`→`commit`→`install_prepush()`→`before = copy_state()`→`put("docs/zz-tracked.md", "y\n")`（追記で直しかけにする）→`put("docs/zz-uncommitted.md", "x\n")`（記録していないファイルも混ぜる）→`rc, out = run_prepush(self.push_line(), extra_env={"CBS_COPY_KIND": "untracked"})`。rc 0・出力に `直しかけの変更があります` と `HEAD の写しで流します`・`rows = log_rows()` が 1 行・8 列・`(rows[0][3], rows[0][5], rows[0][7]) == ("0", "pre-push", "tracked-copy")`・`read_stamp() == git(self.wt, "rev-parse", "HEAD")`・`copy_state() == before` |
| M2 | `test_dirty_tracked_change_is_not_in_copy`（新規。`test_untracked_file_is_not_in_copy` の次に置く） | `put("backend/app/routers/zz_fixture_router.py", src=PASS)`→`commit`→`put("backend/app/routers/zz_fixture_router.py", src=FAIL)`（作業場所だけ違反の中身に書き換え。commit しない）→`rc, out = run_script("--only", "tenant-lint", extra_env={"CHECK_BEFORE_SUBMIT_CALLER": "pre-push"})`。rc 0・`log_rows()[-1][5] == "pre-push"`・`log_rows()[-1][7] == "tracked-copy"`。続けて `commit`→同じ流しで rc 1・出力に `× lint_tenant_schema (strict)` |
| M3・M6 | `test_prepush_stops_when_head_fails_with_dirty_tracked`（新規。`test_prepush_stops_when_copy_fails_check` の次に置く） | `put("backend/app/routers/zz_fixture_router.py", src=FAIL)`→`put("docs/zz-tracked.md", "x\n")`→`install_prepush()`（両方 commit される）→`before = copy_state()`→`put("docs/zz-tracked.md", "y\n")`→`run_prepush(self.push_line())`。rc 1・出力に `push を中断しました`・1 行・`(rows[0][3], rows[0][5], rows[0][7]) == ("1", "pre-push", "tracked-copy")`・`read_stamp() is None`・`copy_state() == before` |
| M4 | 既存 `test_dirty_tracked_manual_exits_2` | 変えない。そのまま pass |
| M5 | 既存 `test_prepush_runs_in_copy_on_untracked` ＋ `test_untracked_copy_kind_not_taken_from_outside`（新規。`test_untracked_only_runs_in_copy` の次に置く） | 既存は変えない。新規：`put("docs/zz-uncommitted.md", "x\n")`→`rc, out = run_script("--only", "rule-registry", extra_env={"CBS_COPY_KIND": "tracked"})`。rc 0・`log_rows()[-1][5] == "manual"`・`log_rows()[-1][7] == "untracked-copy"` |

試験の数：今 41 本（CheckBeforeSubmit 36・PrepareHooksPath 5）→ 44 本（書き換え 1・新規 3）。

## §6 作業の決まり
- 作業場所は必ず `bash scripts/new-worktree.sh release/r4b2-bin3-impl` で作る（clone のまま commit しない）。Bash は 1 命令ずつ。毎回 `cd <作った作業場所の絶対パス> && ` で始める。sleep しない。
- ファイルの作成と編集は Write・Edit ツールで行う。ヒアドキュメント（`<<`）・`sed -i`・`python -c` で書かない。
- rebase・force push・PR 作成・マージはしない。本番・DB・secrets に触れない。
- 見張り（フック・自動判定）に止められたら、言い換えて試さない。止まった手順・最後のコマンド・理由の原文を報告して `BLOCKED:` で終える。
- 本店に写した台帳（active-work.d）は commit しない。

## §7 確かめ（生出力を報告ファイルに貼る）
1. `bash -n scripts/dev/check-before-submit.sh` の rc（0）
2. `grep -c 'CBS_COPY_KIND' scripts/dev/check-before-submit.sh`（期待 2：_cbs_log・写しを呼ぶ所）・`grep -c 'cbs_kind' scripts/dev/check-before-submit.sh`（期待 4：初期化・道の決め・表示の分け・写しを呼ぶ所）・`grep -c 'tracked-copy' scripts/dev/check-before-submit.sh`（期待 2：説明・_cbs_log）。違っても `grep -n` の生出力を記録して続ける
3. `bash --version | head -1`（クラウドの bash の版）
4. 試験：`python3 -I scripts/tests/test_check_before_submit.py -v 2>&1 | tail -n 25`。落ちた試験があれば名前ごとに流し直した生出力の最後の 40 行
5. `git worktree list | grep -c cbs-copy`（試験の後に写しが残っていないこと。期待 0）
6. `git diff --stat origin/main...HEAD`
7. `git diff origin/main...HEAD | grep -c '^-[^-]'` と `git diff --numstat origin/main...HEAD`

## §8 合格基準
- §7-1 が 0
- 試験がすべて pass（44 本。M1〜M5）
- §7-5 が 0
- 変えたファイルが §2 の 3 つだけ。消した行は `scripts/dev/check-before-submit.sh`（:53・:126・:130-131・:132-134・:150 の置き換え分）と `scripts/tests/test_check_before_submit.py`（:12・:19・:23 と書き換え 1 本の分）の中だけ
- M7（CI）は設計パートナーが確かめる

## §9 commit と push
- commit は 1 つ。文は Write で一時ファイル（例 `/tmp/r4b2-bin3-msg.txt`）に書き `git commit -F /tmp/r4b2-bin3-msg.txt`。1 行目 `feat(rule-enforcement): R4b-2 第3便 pre-push で直しかけの変更が残るときも HEAD の写しで確認を流す`。最後の行 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- push はほかの命令とつなげず単独で：`git push origin release/r4b2-bin3-impl`。push の前の入口が流れる（約 90〜190 秒）。入口が × で止めたら、直さずに報告して `BLOCKED:`
- PR は作らない（設計パートナーが作り、作る前に `scripts/dev/validate-pr-body.sh` の exit 0 を確かめる）

## §10 報告
- `docs/handoff/rule-enforcement/impl-report-r4b2-bin3.md` に：1 行目の受領確認（§0）、§7 の各確かめの生出力（要約しない・推測で埋めない）。報告ファイルも同じ commit に入れる
- 最後の返事（1000 字以内）の 1 行目「本報告はカード card-r4b2-bin3.md の実行結果である」。続けて push 後の `git rev-parse HEAD`、`git log -3 --oneline`、`git diff --name-only origin/main...HEAD`、試験の結果の行、push の出力の最後の 3 行
- 止まったときは「止まった手順の番号／最後に流したコマンド／止まった理由の原文」の 3 点
- 最後の行は `DONE` / `BLOCKED: 理由` / `NEEDS_DECISION: 理由` のどれか 1 つ

## §11 想定分岐
| 場面 | どうするか |
|---|---|
| §3・§4 の「今の文」が一致で見つからない | 書き換えず `NEEDS_DECISION:`（見つからない文を原文で） |
| M2 の前半（PASS を commit した直後）で、作業場所を書き換える前に流しても tenant-lint が × になる（PASS の見本が違反扱い） | 生出力を貼って `NEEDS_DECISION:`（試験の確かめを弱めない） |
| bash 3.2 と 5 で動きが違いそうな所 | クラウドの bash で流した結果を記録して続ける（判定は設計パートナー） |
| 書き換え 1 本以外の既存の試験が 1 本でも落ちる | 判定を変えていないはずなので、直さずに生出力を貼って `NEEDS_DECISION:` |
| 新しい試験が落ち、台本の直しがこのカードの文の外に出る | 直さずに生出力を貼って `NEEDS_DECISION:` |
| 試験の後に `cbs-copy` の作業場所が残る（§7-5 が 0 でない） | `git worktree list` の生出力を貼って `NEEDS_DECISION:` |
| §7-2 の数が期待と違う | 数と `grep -n` の生出力を記録して続ける |
| push の入口が終了コード 2 で通った | 表示の理由を報告に書いて続ける |
| push が送り先に断られた | 出力の最後の 10 行を貼って `BLOCKED:` |
