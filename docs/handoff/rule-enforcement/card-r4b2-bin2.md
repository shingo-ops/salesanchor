# 実装カード R4b-2 第2便：記録していないファイルだけが残るときは、HEAD のきれいな写しで確認を流す

## カード発行前チェック（design-partner.md §5.5。設計パートナーが照合）
| 項目 | 結果 | 中身 |
|---|---|---|
| 0 照合結果を出す | ○ | この表 |
| 1 記号を壊さない | ○ | パス・正規表現・変数は `` ` `` で囲んだ。表の中の `\|` は台本では `|` |
| 2 下書き禁止 | ○ | PR は実装役は作らない。設計パートナーが ready で作る（§9） |
| 3 報告の宛先 | ○ | `docs/handoff/rule-enforcement/impl-report-r4b2-bin2.md` と最後の返事（§10） |
| 4 1便1目的 | ○ | 記録していないファイルだけのときに写しで流す（3 ファイル＋報告） |
| 5 既存ブランチは起点明示 | ○ | 起点 `origin/release/r4b2-bin2-impl`（このカードと台帳を設計パートナーが commit 済み。土台 origin/main 81387fb2e） |
| 6 書式は実例で | ○ | 変更後の台本の文をそのまま示した（§3・§4） |
| 7 合格基準を出力まで | ○ | 試験名・列の値・写しが残らないこと・差分が対象ファイルだけであること（§8） |
| 8 数だけで止めない | ○ | 落ちた試験は名前と生出力を出す（§7-4） |
| 9 出力量に上限 | ○ | `tail`・`grep -c`・`--stat` で絞る |
| 10 報告様式 3 点 | ○ | §0 受領確認・§10 冒頭の一文・停止時の 3 点・終端合図 |
| 11 期待値は実測から | ○ | 置き換えは前後の文字の一致で指定。行番号は目安（origin/main 81387fb2e で確認） |
| 12 停止は 2 段 | ○ | 止まるのは §11 の場合だけ。数の食い違いは記録して続ける |
| 13 委任文 4 点 | ○ | sleep しない・Write/Edit で書く・validate-pr-body は設計パートナーが PR 前に流す・見張りに止められたら言い換えず BLOCKED: |

## §0 受領確認
報告ファイルの 1 行目に「本報告はカード card-r4b2-bin2.md の実行結果である。受領：§0〜§11 を読んだ」と書く。

## §1 目的
提出前の入口（`scripts/dev/check-before-submit.sh`）は、記録していないファイル（`git status` で `??` の行）が残っていると終了コード 2 で何も確かめずに終わり、push が素通りしていた。記録していないファイル「だけ」が残るときは、HEAD の切り離しの写しを一時フォルダ（名前 `cbs-copy.*`）に作り、同じ引数で写しの中で入口を流し、その終了コードを返す。追跡中の変更（dirty-tracked）は今までどおり 2。
設計の正本：`docs/handoff/rule-enforcement/design.md` の「## R4b-2 第2便」節（決め 1〜10・受入条件 L1〜L11）。このカードと設計が食い違えば設計が正で、`NEEDS_DECISION:` で止まる。

## §2 触るファイル（これ以外は触らない）
- `scripts/dev/check-before-submit.sh`
- `scripts/tests/test_check_before_submit.py`
- `scripts/new-worktree.sh`（1 行だけ）
- `docs/handoff/rule-enforcement/impl-report-r4b2-bin2.md`（新規・報告）

触らない：`frontend/.husky/pre-push`・`scripts/dev/validate-pr-body.sh`・`scripts/reaper-worktree.sh`・CI の設定・記録ファイルの場所と列の数（8 列のまま）。

## §3 `scripts/dev/check-before-submit.sh` の変更

### 3-1 台本の中だけの変数を 3 つ初期化する（決め 2）
今（:33-35）：
```bash
CBS_MODE="-"
CBS_REASON="-"
HEAD_SHA=""
```
後（`HEAD_SHA=""` の次に 3 行足す。外の環境変数の値を引き継がないため、必ずここで代入する）：
```bash
CBS_MODE="-"
CBS_REASON="-"
HEAD_SHA=""
CBS_COPY_OK=0
CBS_ORIG_GITDIR_OK=""
CBS_SKIP_LOG=0
```

### 3-2 記録の関数 `_cbs_log` を 3 か所変える（決め 4）
| 今の文（一致で探す） | 変更後 |
|---|---|
| `  local rc=$? t1 secs common head branch caller reason` | その行の次に `  test "$CBS_SKIP_LOG" = 1 && return $rc` を足す |
| `  branch=$(git branch --show-current 2>/dev/null)` | その行の次に `  test -n "$branch" \|\| { test "$CBS_COPY_OK" = 1 && branch="${CBS_ORIG_BRANCH:-}"; }` を足す |
| `  test "$rc" = "2" && reason="$CBS_REASON"`（`reason="-"` の次の行） | `  case "$rc" in 0\|1) test "$CBS_COPY_OK" = 1 && reason=untracked-copy ;; 2) reason="$CBS_REASON" ;; *) test "$CBS_REASON" = copy-rc && reason=copy-rc ;; esac` に置き換える |

`reason="-"` の行と printf の行は変えない。

### 3-3 引数を保存する（決め 6）
`trap _cbs_log EXIT` の行と `FULL=0` の行の間に、次の 2 行を入れる（引数は :58-71 の shift で消えるため、その前に保存する）：
```bash
# 写しへそのまま渡すため、読み取る前の引数を保存する（R4b-2 第2便 決め 6）
CBS_ARGS=("$@")
```

### 3-4 写しの中で流れているかを 1 回だけ決める（決め 2 の CBS_COPY_OK）
流し方を決める所（`# 流し方（記録の 7 列目）。` で始まる if〜fi、今の :90-97）の閉じの `fi` の次、`# --- commit していない変更があれば止める` の行の前に、次をそのまま入れる：
```bash
# 写しの中で流れているかを 1 回だけ決める（R4b-2 第2便 決め 2）。4 つがそろったときだけ 1 にする。
# ① CBS_IN_COPY が 1 ② 枝の名が空 ③ 一番上のフォルダの名が cbs-copy. で始まる
# ④ CBS_ORIG_GITDIR が空でなく、解いた場所が共通の git の場所そのものか、その worktrees/ の下
if test "${CBS_IN_COPY:-}" = "1" && test -z "$(git branch --show-current 2>/dev/null)"; then
  case "$(basename "$(pwd -P)")" in
    cbs-copy.*)
      if test -n "${CBS_ORIG_GITDIR:-}"; then
        cbs_g=$(cd "${CBS_ORIG_GITDIR:-}" 2>/dev/null && pwd -P)
        cbs_c=$(cd "$(git rev-parse --git-common-dir 2>/dev/null)" 2>/dev/null && pwd -P)
        if test -n "$cbs_g" && test -n "$cbs_c"; then
          case "$cbs_g" in
            "$cbs_c"|"$cbs_c"/worktrees/*) CBS_COPY_OK=1; CBS_ORIG_GITDIR_OK="$cbs_g" ;;
          esac
        fi
      fi
      ;;
  esac
fi
```

### 3-5 記録していないファイルだけなら写しで流す（決め 1・2・3・8）
今（:99-106）：
```bash
CBS_PORC=$(git status --porcelain)
if test -n "$CBS_PORC"; then
  if printf '%s\n' "$CBS_PORC" | grep -qv '^??'; then CBS_REASON=dirty-tracked; else CBS_REASON=dirty-untracked; fi
  echo "commit していない変更があります。commit してから流してください（終了コード 2）。"
  git status --short | head -20
  exit 2
fi
```
後：
```bash
CBS_PORC=$(git status --porcelain)
if test -n "$CBS_PORC"; then
  if printf '%s\n' "$CBS_PORC" | grep -qv '^??'; then CBS_REASON=dirty-tracked; else CBS_REASON=dirty-untracked; fi
  # R4b-2 第2便: 記録していないファイルだけなら、HEAD の切り離しの写しを一時フォルダに作り、その中で同じ引数で流す。
  # --list-fixtures のときと、写しの中（外から CBS_IN_COPY=1 が来たときも含む）では作らない
  if test "$CBS_REASON" = "dirty-untracked" && test "$LIST_FIX" = "0" && test "${CBS_IN_COPY:-}" != "1"; then
    git status --short | head -20
    echo "記録していないファイルがあります。HEAD の写しで流します（約 40 秒増えます）"
    cbs_branch=$(git branch --show-current 2>/dev/null)
    cbs_gitdir=$(git rev-parse --path-format=absolute --git-dir 2>/dev/null)
    cbs_dir=$(mktemp -d "${TMPDIR:-/tmp}/cbs-copy.XXXXXX" 2>/dev/null) || { CBS_REASON=copy-fail; echo "写しの一時フォルダが作れません（終了コード 2）"; exit 2; }
    if ! git worktree add -q --detach "$cbs_dir" "$(git rev-parse HEAD)" >/dev/null 2>&1; then
      rmdir "$cbs_dir" 2>/dev/null || true
      CBS_REASON=copy-fail
      echo "HEAD の写しが作れません（終了コード 2）"
      exit 2
    fi
    if ! test -f "$cbs_dir/scripts/dev/check-before-submit.sh"; then
      git worktree remove --force "$cbs_dir" >/dev/null 2>&1 || true
      CBS_REASON=copy-fail
      echo "HEAD に入口の台本がありません（終了コード 2）"
      exit 2
    fi
    (cd "$cbs_dir" 2>/dev/null || exit 3; CBS_IN_COPY=1 CBS_ORIG_BRANCH="$cbs_branch" CBS_ORIG_GITDIR="$cbs_gitdir" bash scripts/dev/check-before-submit.sh ${CBS_ARGS[@]+"${CBS_ARGS[@]}"} </dev/null)
    cbs_rc=$?
    case "$cbs_rc" in
      0|1|2) CBS_SKIP_LOG=1 ;;
      *) CBS_REASON=copy-rc ;;
    esac
    git worktree remove --force "$cbs_dir" >/dev/null 2>&1 || true
    exit $cbs_rc
  fi
  echo "commit していない変更があります。commit してから流してください（終了コード 2）。"
  git status --short | head -20
  exit 2
fi
```
順番（決め 3）を変えない：写しの中で流す → `cbs_rc=$?` → `CBS_SKIP_LOG` か `copy-rc` → 片付け → `exit $cbs_rc`。

### 3-6 印の行き先（決め 2・5）
今（:418）：
```bash
  STAMP_DIR=$(git rev-parse --path-format=absolute --git-dir 2>/dev/null)
```
後：
```bash
  if test "$CBS_COPY_OK" = "1"; then
    STAMP_DIR="$CBS_ORIG_GITDIR_OK"
  else
    STAMP_DIR=$(git rev-parse --path-format=absolute --git-dir 2>/dev/null)
  fi
```
その前後の `if test -z "$ONLY"; then` と、`if test -n "$STAMP_DIR" && printf ...` からの行は変えない。

## §4 `scripts/new-worktree.sh` の変更（決め 10）
今（:71）：
```bash
WORKTREE_COUNT=$(git worktree list | tail -n +2 | wc -l | tr -d ' ')
```
後（行の頭の空白は今のまま）：
```bash
WORKTREE_COUNT=$(git worktree list | tail -n +2 | grep -v '/cbs-copy\.' | wc -l | tr -d ' ')
```
ほかの行は変えない。

## §5 試験 `scripts/tests/test_check_before_submit.py` の変更
### 5-1 補助
- `import glob` を足す（`import os` の前）。
- `run_script` を、追加の環境と流す場所を受け取れる形にする（今の呼び方はそのまま動く）：
```python
    def run_script(self, *args, extra_env=None, cwd=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["TMPDIR"] = self.tmp  # 入口のログ置き場も、終わりに消す一時フォルダの中に作らせる
        env.update(extra_env or {})
        r = subprocess.run(["bash", SCRIPT_REL] + list(args), cwd=cwd or self.wt, env=env,
                           capture_output=True, text=True, timeout=900)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
```
- `log_rows` の次に足す（L7 の確かめ）：
```python
    def copy_state(self):
        # 作業場所の一覧の行数と、一時フォルダに残った cbs-copy.* の数
        return (len(git(self.wt, "worktree", "list").splitlines()),
                len(glob.glob(os.path.join(self.tmp, "cbs-copy.*"))))
```

### 5-2 試験（書き換え 2 本・新規 8 本。既存のほかの確かめは消さない）
| L | 試験 | 中身 |
|---|---|---|
| L1・L7 | `test_untracked_only_runs_in_copy`（`test_uncommitted_change_exits_2` を名前ごと置き換え） | `git(self.wt, "checkout", "-q", "-b", "zz-orig")`→`before = self.copy_state()`→`self.put("docs/zz-uncommitted.md", "x\n")`→`rc, out = self.run_script()`。rc 0・出力に `HEAD の写しで流します`・`rows = self.log_rows()` が 1 行・8 列・`rows[0][1] == "zz-orig"`・`rows[0][3] == "0"`・`rows[0][5] == "manual"`・`rows[0][6] == "full"`・`rows[0][7] == "untracked-copy"`・`self.read_stamp() == HEAD の SHA`・`self.copy_state() == before` |
| L2 | `test_untracked_file_is_not_in_copy`（新規） | 見本の場所は既存 `test_tenant_schema_violation_fails` と同じ `src`。`self.put("backend/app/routers/zz_fixture_router.py", src=src)`（commit しない）→`run_script("--only", "tenant-lint")` が rc 0・最後の行の 8 列目 `untracked-copy`。続けて `self.commit(...)` →同じ流しで rc 1・出力に `× lint_tenant_schema (strict)` |
| L3・L7 | `test_prepush_stops_when_copy_fails_check`（新規） | 違反の見本を `put`→`self.install_prepush()`（commit される）→`before = self.copy_state()`→`self.put("docs/zz-uncommitted.md", "x\n")`→`run_prepush(self.push_line())`。rc 1・出力に `push を中断しました`・1 行・`(rows[0][3], rows[0][5], rows[0][7]) == ("1", "pre-push", "untracked-copy")`・`read_stamp() is None`・`copy_state() == before` |
| L4 | `test_prepush_runs_in_copy_on_untracked`（`test_prepush_does_not_stop_on_uncommitted_change` を名前ごと置き換え） | `install_prepush()`→`put("docs/zz-uncommitted.md", "x\n")`→`run_prepush(self.push_line())`。rc 0・出力に `HEAD の写しで流します`・1 行・8 列・`(rows[0][3], rows[0][5], rows[0][7]) == ("0", "pre-push", "untracked-copy")` |
| L5 | `test_dirty_tracked_manual_exits_2`（新規。既存 `test_prepush_dirty_tracked_reason` は変えない） | `put("docs/zz-tracked.md", "x\n")`→`commit`→`before = copy_state()`→`put("docs/zz-tracked.md", "y\n")`→`run_script()`。rc 2・出力に `commit していない変更`・最後の行の 8 列目 `dirty-tracked`・`copy_state() == before` |
| L6・L7 | `test_copy_fail_when_tmpdir_missing`（新規） | `before = copy_state()`→`put("docs/zz-uncommitted.md", "x\n")`→`run_script(extra_env={"TMPDIR": os.path.join(self.tmp, "no-such-dir")})`。rc 2・1 行・`(rows[0][3], rows[0][7]) == ("2", "copy-fail")`・`copy_state() == before` |
| L8 | `test_outside_values_do_not_change_path`（新規・4 つを順に） | (d) きれいな状態で `run_script("--only", "rule-registry", extra_env={"CBS_SKIP_LOG": "1"})` が rc 0 で、`log_rows()` が 1 行増える。(a) `put("docs/zz-uncommitted.md", "x\n")`→`run_script("--only", "rule-registry", extra_env={"CBS_IN_COPY": "1"})` が rc 2・最後の行の 8 列目 `dirty-untracked`・`copy_state()` が流す前と同じ。終わったら `os.remove` でそのファイルを消す。(b) `fake = os.path.join(self.tmp, "cbs-copy.fake")`・`git(self.wt, "worktree", "add", "-q", "--detach", fake, "HEAD")`・`other = os.path.join(self.tmp, "other")` を `os.makedirs`→`run_script(extra_env={"CBS_IN_COPY": "1", "CBS_ORIG_GITDIR": other}, cwd=fake)`（--only なし）が **rc 0**（0 でなければ失敗にする）・最後の行の 8 列目が `untracked-copy` でない・`other/check-before-submit.ok` が無い。(c) 先に `os.makedirs(os.path.join(self.wt, "x"))`→`orig = os.path.realpath(os.path.join(self.wt, ".git"))`→`run_script(extra_env={"CBS_IN_COPY": "1", "CBS_ORIG_GITDIR": orig + "/worktrees/../../x"}, cwd=fake)`（--only なし）が **rc 0**・最後の行の 8 列目が `untracked-copy` でない・`self.wt/x/check-before-submit.ok` が無い |
| L9 | `test_new_worktree_count_skips_copies`（新規） | `ROOT/scripts/new-worktree.sh` を読み、`strip()` した行が `WORKTREE_COUNT=` で始まる行を 1 つ取り出す（1 つでなければ失敗）。`git(self.wt, "worktree", "add", "-q", "--detach", os.path.join(self.tmp, "cbs-copy.x"), "HEAD")`。`subprocess.run(["bash", "-c", line + '; printf "%s" "$WORKTREE_COUNT"'], cwd=self.wt, env=git_env(), capture_output=True, text=True)` の出力が `"0"`。さらに `os.path.join(self.tmp, "normal")` に切り離しの作業場所を足すと `"1"`（空振りでないこと）。前提として `git worktree list` が足した数どおりの行であること |
| L9b | `test_list_fixtures_does_not_copy`（新規） | `before = copy_state()`→`put("docs/zz-uncommitted.md", "x\n")`→`run_script("--list-fixtures")`。rc 2・最後の行の `[6:] == ["list", "dirty-untracked"]`・`copy_state() == before` |
| L9c・L7 | `test_copy_unexpected_exit_code_is_copy_rc`（新規） | `self.wt` の `SCRIPT_REL` を `"#!/usr/bin/env bash\nexit 5\n"` の 2 行だけに書き換え（`open(..., "w")`）→`commit`→`before = copy_state()`→`put("docs/zz-uncommitted.md", "x\n")`→外側は HEAD の外の本物の台本で流す：`subprocess.run(["bash", os.path.join(ROOT, SCRIPT_REL)], cwd=self.wt, env=<run_script と同じ: GIT_* を外し TMPDIR=self.tmp>, capture_output=True, text=True, timeout=900)`。rc 5・`log_rows()` が 1 行・`(rows[0][3], rows[0][7]) == ("5", "copy-rc")`・`copy_state() == before` |

試験の数：今 33 本 → 41 本（書き換え 2・新規 8）。

## §6 作業の決まり
- Bash は 1 命令ずつ。毎回 `cd /root/worktrees/salesanchor/<作業場所> && ` で始める。sleep しない。
- ファイルの作成と編集は Write・Edit ツールで行う。ヒアドキュメント（`<<`）・`sed -i`・`python -c` で書かない。
- rebase・force push・PR 作成・マージはしない。本番・DB・secrets に触れない。
- 見張り（フック・自動判定）に止められたら、言い換えて試さない。止まった手順・最後のコマンド・理由の原文を報告して `BLOCKED:` で終える。
- 本店に写した台帳（active-work.d）は commit しない。

## §7 確かめ（生出力を報告ファイルに貼る）
1. `bash -n scripts/dev/check-before-submit.sh` と `bash -n scripts/new-worktree.sh` の rc（どちらも 0）
2. `grep -c 'CBS_SKIP_LOG' scripts/dev/check-before-submit.sh`（期待 3：初期化・_cbs_log・写しの後）・`grep -c '^CBS_ARGS=("\$@")' scripts/dev/check-before-submit.sh`（期待 1）・`grep -c "grep -v '/cbs-copy" scripts/new-worktree.sh`（期待 1）。違っても記録して続ける
3. `bash --version | head -1`（クラウドの bash の版）
4. 試験：`python3 -m pytest scripts/tests/test_check_before_submit.py -q 2>&1 | tail -n 15`。落ちた試験があれば名前ごとに `-x` で流し直した生出力の最後の 40 行
5. `git worktree list | grep -c cbs-copy`（試験の後に写しが残っていないこと。期待 0）
6. `git diff --stat origin/main...HEAD`
7. `git diff origin/main...HEAD | grep -c '^-[^-]'` と `git diff --numstat origin/main...HEAD`

## §8 合格基準
- §7-1 がどちらも 0
- 試験がすべて pass（41 本。L1〜L9c）
- §7-5 が 0
- 変えたファイルが §2 の 4 つ（＋カードと台帳は設計パートナーの commit 済み）だけ。消した行は `scripts/dev/check-before-submit.sh`・`scripts/new-worktree.sh`・`scripts/tests/test_check_before_submit.py` の中だけ
- L10（CI）・L11（反映 7 日後）は設計パートナーが確かめる

## §9 commit と push
- commit は 1 つ。文は Write で一時ファイル（例 `/tmp/r4b2-bin2-msg.txt`）に書き `git commit -F /tmp/r4b2-bin2-msg.txt`。1 行目 `feat(rule-enforcement): R4b-2 第2便 記録していないファイルだけなら HEAD の写しで確認を流す`。最後の行 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- push はほかの命令とつなげず単独で：`git push origin release/r4b2-bin2-impl`。push の前の入口が流れる（約 90〜190 秒）。入口が × で止めたら、直さずに報告して `BLOCKED:`
- PR は作らない（設計パートナーが ready で作り、作る前に `scripts/dev/validate-pr-body.sh` の exit 0 を確かめる）

## §10 報告
- `docs/handoff/rule-enforcement/impl-report-r4b2-bin2.md` に：1 行目の受領確認（§0）、§7 の各確かめの生出力（要約しない・推測で埋めない）。報告ファイルも同じ commit に入れる
- 最後の返事（1000 字以内）の 1 行目「本報告はカード card-r4b2-bin2.md の実行結果である」。続けて push 後の `git rev-parse HEAD`、`git log -3 --oneline`、`git diff --name-only origin/main...HEAD`、pytest の結果の行、push の出力の最後の 3 行
- 止まったときは「止まった手順の番号／最後に流したコマンド／止まった理由の原文」の 3 点
- 最後の行は `DONE` / `BLOCKED: 理由` / `NEEDS_DECISION: 理由` のどれか 1 つ

## §11 想定分岐
| 場面 | どうするか |
|---|---|
| §3・§4 の「今の文」が一致で見つからない | 書き換えず `NEEDS_DECISION:`（見つからない文を原文で） |
| bash 3.2 と 5 で動きが違いそうな所 | クラウドの bash で流した結果を記録して続ける（判定は設計パートナー） |
| 書き換え 2 本以外の既存の試験が 1 本でも落ちる | 判定を変えていないはずなので、直さずに生出力を貼って `NEEDS_DECISION:` |
| L8 (b)(c) が rc 0 にならない（偽の写しの中で全部の検査が通らない） | 何の検査が落ちたかの生出力を貼って `NEEDS_DECISION:`（試験の確かめを弱めない） |
| 新しい試験が落ち、台本の直しがこのカードの文の外に出る | 直さずに生出力を貼って `NEEDS_DECISION:` |
| 試験の後に `cbs-copy` の作業場所が残る（§7-5 が 0 でない） | `git worktree list` の生出力を貼って `NEEDS_DECISION:` |
| §7-2 の数が期待と違う | 数と `grep -n` の生出力を記録して続ける |
| push の入口が終了コード 2 で通った | 表示の理由を報告に書いて続ける |
| push が送り先に断られた | 出力の最後の 10 行を貼って `BLOCKED:` |
