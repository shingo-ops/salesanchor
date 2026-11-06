# 実装カード R4b-2 第1便：push の前の確認の「抜け道」を記録に残す（記録だけ・判定は変えない）

## カード発行前チェック（design-partner.md §5.5。設計パートナーが照合）
| 項目 | 結果 | 中身 |
|---|---|---|
| 0 照合結果を出す | ○ | この表 |
| 1 記号を壊さない | ○ | パス・正規表現・ref は `` ` `` で囲んだ |
| 2 下書き禁止 | ○ | PR は実装役は作らない。設計パートナーが ready で作る（§9） |
| 3 報告の宛先 | ○ | `docs/handoff/rule-enforcement/impl-report-r4b2-bin1.md` と最後の返事（§10） |
| 4 1便1目的 | ○ | 記録を足すだけ（3 ファイル＋報告） |
| 5 既存ブランチは起点明示 | ○ | 起点 `origin/release/r4b2-push-gap-bin1`・台帳の写し手順は依頼文の 2/4 |
| 6 書式は実例で | ○ | 変更後の台本を全文の形で示した（§3・§4） |
| 7 合格基準を出力まで | ○ | 試験名・列の値・main との差分に消した行が対象 3 ファイルの中だけであること（§8） |
| 8 数だけで止めない | ○ | 失敗した試験は名前と生出力を出す（§8） |
| 9 出力量に上限 | ○ | `git diff --stat`・`grep -c`・`tail` で絞る |
| 10 報告様式 3 点 | ○ | §0 受領確認・§10 冒頭の一文・停止時の 3 点・終端合図 |
| 11 期待値は実測から | ○ | 置き換えは前後の文字の一致で指定。行番号は目安（origin/main c481f5e7d で確認） |
| 12 停止は 2 段 | ○ | 止まるのは §11 の場合だけ。数の食い違いは記録して続ける |
| 13 委任文 4 点 | ○ | sleep しない・Write/Edit で書く・validate-pr-body は設計パートナーが PR 前に流す・見張りに止められたら言い換えず BLOCKED: |

## §0 受領確認
報告ファイルの 1 行目に「本報告はカード card-r4b2-bin1.md の実行結果である。受領：§0〜§11 を読んだ」と書く。

## §1 目的
push の前の確認（提出前の入口）を通らずに push が通った場面を、記録ファイル 1 つに 1 行ずつ残す。止める・通すの判定は 1 つも変えない。
設計の正本：`docs/handoff/rule-enforcement/design.md` の「## R4b-2」節（受入条件 K1〜K8 はこのカードの §8）。

## §2 触るファイル（これ以外は触らない）
- `frontend/.husky/pre-push`
- `scripts/dev/check-before-submit.sh`
- `scripts/tests/test_check_before_submit.py`
- `docs/handoff/rule-enforcement/impl-report-r4b2-bin1.md`（新規・報告）

触らない：`scripts/dev/validate-pr-body.sh`（記録の行は 6 列のまま）・CI の設定・`scripts/agent-hooks/cloud/rules.md`・記録ファイルの場所。

## §3 `scripts/dev/check-before-submit.sh` の変更

### 3-1 記録の部分を引数の読み取りより前へ移し、8 列にする
今の `set -u` の次の行 `FULL=0` の前に、次をそのまま入れる：

```bash
# --- 記録（R4b・R4b-2）: どの道で終わっても 1 行足す。書けなくても入口の結果は変えない ---
# 引数の読み取りより前に置く（引数の誤り・--help でも 1 行残す）。7 列目 流し方・8 列目 終了コード 2 の理由
CBS_MODE="-"
CBS_REASON="-"
HEAD_SHA=""
_cbs_now() { perl -MTime::HiRes=time -e 'printf "%.2f", time'; }
CBS_T0=$(_cbs_now)
_cbs_log() {
  local rc=$? t1 secs common head branch caller reason
  t1=$(_cbs_now)
  secs=$(perl -e 'printf "%.1f", $ARGV[1] - $ARGV[0]' "$CBS_T0" "$t1" 2>/dev/null)
  common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return $rc
  head="$HEAD_SHA"
  test -n "$head" || head=$(git rev-parse HEAD 2>/dev/null)
  branch=$(git branch --show-current 2>/dev/null)
  caller="${CHECK_BEFORE_SUBMIT_CALLER:-manual}"
  reason="-"
  test "$rc" = "2" && reason="$CBS_REASON"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$branch" "$head" "$rc" "$secs" "$caller" "$CBS_MODE" "$reason" \
    >> "${common}/check-before-submit.log" 2>/dev/null
  return $rc
}
trap _cbs_log EXIT
```

そして今の `cd "$(git rev-parse --show-toplevel)" || exit 2` の後ろにある、`# --- 記録（R4b）: どの道で終わっても 1 行足す。` の行から `trap _cbs_log EXIT` の行まで（`_cbs_now`・`CBS_T0`・`_cbs_log`・`trap`）を消す。`REQ_FILE=...` の行は残す。
`_cbs_now`・`_cbs_log`・`CBS_T0`・`trap` が台本の中にそれぞれ 1 回だけあること（§8 の確かめ）。

### 3-2 終了コード 2 の出口ごとに理由を入れる（出口の直前で `CBS_REASON` に入れる。別の表は作らない）
下の表の `\|` は表の区切りと分けるための書き方で、台本の中では `|`（`\` は付けない）。
| 今の文（一致で探す） | 変更後 |
|---|---|
| `echo "--only には検査の id（カンマ区切り）を渡してください。終了コード 2"; exit 2` | `CBS_REASON=bad-arg; echo "--only には検査の id（カンマ区切り）を渡してください。終了コード 2"; exit 2` |
| `-h\|--help) sed -n 2,16p "$0"; exit 0 ;;` | `-h\|--help) CBS_MODE=help; sed -n 2,16p "$0"; exit 0 ;;` |
| `*) echo "不明な引数: $1" >&2; exit 2 ;;` | `*) CBS_REASON=bad-arg; echo "不明な引数: $1" >&2; exit 2 ;;` |
| `cd "$(git rev-parse --show-toplevel)" \|\| exit 2` | `cd "$(git rev-parse --show-toplevel)" \|\| { CBS_REASON=cd-fail; exit 2; }` |
| --only の知らない id の `exit 2`（`使える id:` の echo の次の行） | その `exit 2` の前の行に `    CBS_REASON=unknown-id` |
| `echo "必須チェックの一覧が読めません: ...` の次の `exit 2` | 前に `  CBS_REASON=req-unreadable` |
| `echo "必須チェックの一覧が 0 件です: ...` の次の `exit 2` | 前に `  CBS_REASON=req-empty` |
| `MAIN_SHA=$(git rev-parse --verify -q origin/main) \|\| { echo` | `\|\| { CBS_REASON=no-origin-main; echo` |
| `BASE_SHA=$(git merge-base origin/main HEAD) \|\| { echo` | `\|\| { CBS_REASON=no-merge-base; echo` |
| 見本のフォルダの名前が select の echo の次の `exit 2` | 前に `  CBS_REASON=select-dir` |
| `echo "結果: 流した検査が 0 件でした。...` の次の `exit 2` | 前に `  CBS_REASON=zero-checks` |

`HEAD_SHA=$(git rev-parse HEAD)`（今の :100）は変えない（3-1 で空に初期化してあるので、ここで決まった後は記録の 3 列目がこの値になる）。

### 3-3 流し方（7 列目）を決める
--only の id を確かめる `if test -n "$ONLY"; then ... fi` の閉じの `fi` の次（`# --- commit していない変更があれば止める` の前）に入れる：

```bash
# 流し方（記録の 7 列目）。--only と --list-fixtures を一緒に渡すと list の道で終わるので list
if test "$LIST_FIX" = "1"; then
  CBS_MODE=list
elif test -n "$ONLY"; then
  CBS_MODE=only
else
  CBS_MODE=full
fi
```
（--only の知らない id で終わったときは、ここより前なので 7 列目 `-`・8 列目 `unknown-id`。）

### 3-4 commit していない変更の理由を 2 つに分ける
今：
```bash
if test -n "$(git status --porcelain)"; then
  echo "commit していない変更があります。commit してから流してください（終了コード 2）。"
```
後：
```bash
CBS_PORC=$(git status --porcelain)
if test -n "$CBS_PORC"; then
  if printf '%s\n' "$CBS_PORC" | grep -qv '^??'; then CBS_REASON=dirty-tracked; else CBS_REASON=dirty-untracked; fi
  echo "commit していない変更があります。commit してから流してください（終了コード 2）。"
```
残りの行（`git status --short | head -20`・`exit 2`・`fi`）は変えない。

## §4 `frontend/.husky/pre-push` の変更（`sh` で動く。bash だけの書き方を使わない）
`if [ -f "$CBS_SCRIPT" ]; then` から最後の `fi` まで（今の :40〜:72）を次に置き換える。表示の文は今と同じ。

```sh
if [ -f "$CBS_SCRIPT" ]; then
  CBS_HEAD="$(git rev-parse HEAD 2>/dev/null)"
  CBS_SKIP=""
  CBS_LINES=0
  CBS_PUSHED=""
  while read -r CBS_LREF CBS_LSHA CBS_RREF CBS_RSHA; do
    [ -z "$CBS_LSHA" ] && continue
    CBS_LINES=$((CBS_LINES + 1))
    CBS_PUSHED="${CBS_PUSHED}${CBS_LSHA} ${CBS_RREF}
"
    case "$CBS_LSHA" in
      *[!0]*) [ "$CBS_LSHA" = "$CBS_HEAD" ] || CBS_SKIP=1 ;;
      *) CBS_SKIP=1 ;; # local sha が全部 0 = 削除
    esac
  done
  # 記録（R4b-2）: 入口を流さずに通す push も 1 行ずつ残す。書けなくても判定は変えない
  CBS_COMMON="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
  cbs_row() { # 1=4列目 2=7列目 3=8列目
    [ -n "$CBS_COMMON" ] || return 0
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git branch --show-current 2>/dev/null)" \
      "$CBS_HEAD" "$1" "-" "pre-push" "$2" "$3" >> "${CBS_COMMON}/check-before-submit.log" 2>/dev/null || true
  }
  if [ "$CBS_LINES" = "0" ] || [ -n "$CBS_SKIP" ]; then
    echo "手元の確認（提出前の入口）は飛ばした: push する中身が今の HEAD と違う（または削除・変更なし）。CI で確かめる。"
    if [ "$CBS_LINES" = "0" ]; then
      cbs_row skip-empty - -
    else
      printf '%s' "$CBS_PUSHED" | while read -r CBS_S CBS_R; do
        case "$CBS_R" in
          refs/tags/*) cbs_row skip-tag "$CBS_S" "$CBS_R"; continue ;;
        esac
        case "$CBS_S" in
          *[!0]*) ;;
          *) cbs_row skip-delete - "$CBS_R"; continue ;;
        esac
        if [ "$CBS_S" = "$CBS_HEAD" ]; then
          cbs_row skip-head "$CBS_S" "$CBS_R"
        else
          cbs_row skip-otherhead "$CBS_S" "$CBS_R"
        fi
      done
    fi
  else
    CBS_STAMP="$(git rev-parse --absolute-git-dir)/check-before-submit.ok"
    if [ -f "$CBS_STAMP" ] && [ "$(cat "$CBS_STAMP" 2>/dev/null)" = "$CBS_HEAD" ]; then
      echo "提出前の入口: 流した印あり（今の HEAD と同じ）。入口は流さずに通す。"
      cbs_row stamp "$CBS_HEAD" -
    else
      （今の :59〜:69 の echo・コメント・入口を流す行・CBS_RC=$?・if 1 / elif 2 をそのまま残す）
      elif [ "$CBS_RC" != "0" ]; then
        echo "入口が想定外の終わり方をした（終了コード ${CBS_RC}）。止めずに通す。CI が止める"
      fi
    fi
  fi
fi
```
「（今の :59〜:69 …）」の行は説明であり、そこには今の文をそのまま置く。`elif [ "$CBS_RC" = "2" ]; then` の echo の後ろ、閉じの `fi` の前に `elif [ "$CBS_RC" != "0" ]` の 2 行を足す。`exit` は足さない（rc 0 で通す）。
タグの行は `skip-tag` の 7 列目にその行の手元の SHA を書く（設計の表に 7 列目の決めが無いので、push の行の手元の SHA を書く決まりに合わせる）。

## §5 試験 `scripts/tests/test_check_before_submit.py` の変更
- `import time` を足す。
- 既存の確かめは消さない。下の 2 本（K1・K3）だけ `log_rows() == []` の行を置き換える。

| K | 試験 | 中身 |
|---|---|---|
| K1 | `test_prepush_skips_when_pushed_content_differs_from_head`（書き換え） | 最後の `self.assertEqual(self.log_rows(), [])` を消し、`rows = self.log_rows()` が 3 行・各行 8 列・4 列目が順に `skip-otherhead`・`skip-delete`・`skip-empty`・6 列目すべて `pre-push`。1 行目の 7 列目が `HEAD~1` の SHA・8 列目 `refs/heads/x`。2 行目の 7 列目 `-`・8 列目 `refs/heads/x`。3 行目の 7・8 列目 `-`。入口の行（6 列目が `manual`/`pre-push` で 4 列目が数）が無いこと＝3 行だけ |
| K2 | `test_prepush_logs_skip_head_and_otherhead`（新規） | `install_prepush()` の後、`"refs/heads/x <HEAD> refs/heads/x <ZERO>\nrefs/heads/y <HEAD~1> refs/heads/y <ZERO>\n"` を渡す。rc 0・「飛ばした」・2 行：`skip-head`（7 列目 HEAD・8 列目 `refs/heads/x`）・`skip-otherhead`（7 列目 HEAD~1・8 列目 `refs/heads/y`） |
| K2 | `test_prepush_logs_skip_tag`（新規） | `"refs/tags/v1 <HEAD~1> refs/tags/v1 <ZERO>\n"` を渡す（タグの SHA を HEAD にしない）。rc 0・1 行・4 列目 `skip-tag`・8 列目 `refs/tags/v1` |
| K3 | `test_prepush_skips_check_when_stamp_matches_head`（書き換え） | `run_prepush` の前後を `time.monotonic()` で測り 5 秒未満。`log_rows() == []` を消し、1 行・8 列・4 列目 `stamp`・6 列目 `pre-push`・7 列目 HEAD・8 列目 `-` |
| K4 | `test_prepush_does_not_stop_on_uncommitted_change`（足す） | 既存の確かめの後に `len(rows[0]) == 8`・`rows[0][7] == "dirty-untracked"` |
| K4 | `test_prepush_dirty_tracked_reason`（新規） | `self.put("docs/zz-tracked.md", "x\n")`→`self.commit(...)`→`install_prepush()`→`self.put("docs/zz-tracked.md", "y\n")`（追記で追跡中の変更）→ `run_prepush(self.push_line())`。rc 0・1 行・4 列目 `2`・8 列目 `dirty-tracked` |
| K5 | `test_bad_arg_and_help_are_logged`（新規） | `run_script("--no-such-arg")` → rc 2・最後の行の 4 列目 `2`・7 列目 `-`・8 列目 `bad-arg`。`run_script("--help")` → rc 0・最後の行の 4 列目 `0`・7 列目 `help`・8 列目 `-` |
| K6 | `test_prepush_unexpected_exit_code_passes`（新規） | `self.tmp` に `#!/bin/bash\nexit 3\n` を書いたファイルを作り、`install_prepush()` の後 `self.put(SCRIPT_REL, src=<そのファイル>)`→`self.commit(...)`。`run_prepush(self.push_line())` → rc 0・出力に `想定外の終わり方` と `終了コード 3` |
| K7 | `test_only_run_does_not_write_stamp`（足す） | `rows[0][6] == "only"`・`rows[0][7] == "-"` |
| K7 | `test_fixture_selected_only_when_script_or_folder_touched`（足す） | 最後に `self.log_rows()[-1][6] == "list"` |
| K7 | `test_clean_copy_passes_and_shows_every_name`（足す） | `len(rows[0]) == 8`・`rows[0][6] == "full"`・`rows[0][7] == "-"` |
| K7 | `test_old_stamp_is_kept_when_run_exits_2`（足す） | `self.log_rows()[-1][6:] == ["-", "unknown-id"]` |

validate-pr-body の行を見る試験（`len(got[0]) == 6` の所）は変えない。

## §6 作業の決まり
- Bash は 1 命令ずつ。毎回 `cd /root/worktrees/salesanchor/<作業場所> && ` で始める。sleep しない。
- ファイルの作成と編集は Write・Edit ツールで行う。ヒアドキュメント（`<<`）・`sed -i`・`python -c` で書かない。
- rebase・force push・PR 作成・マージはしない。本番・DB・secrets に触れない。
- 見張り（フック・自動判定）に止められたら、言い換えて試さない。止まった手順・最後のコマンド・理由の原文を報告して `BLOCKED:` で終える。
- 本店に写した台帳（active-work.d）は commit しない。

## §7 確かめ（生出力を報告ファイルに貼る）
1. `bash -n scripts/dev/check-before-submit.sh` と `sh -n frontend/.husky/pre-push` の rc（どちらも 0）
2. `grep -c '^trap _cbs_log EXIT' scripts/dev/check-before-submit.sh`・`grep -c '^_cbs_now()' scripts/dev/check-before-submit.sh`・`grep -c '^CBS_T0=' scripts/dev/check-before-submit.sh`（どれも 1）
3. `grep -c 'CBS_REASON=' scripts/dev/check-before-submit.sh`（期待 13 行：初期化 1・dirty の 1 行（2 つが同じ行）・bad-arg 2・cd-fail・unknown-id・req-unreadable・req-empty・no-origin-main・no-merge-base・select-dir・zero-checks。違っても記録して続ける）
4. 試験：`python3 -m pytest scripts/tests/test_check_before_submit.py -q 2>&1 | tail -n 15`。落ちた試験があれば名前ごとに `-x` で流し直した生出力の最後の 40 行
5. `git diff --stat origin/main...HEAD`
6. `git diff origin/main...HEAD | grep -c '^-[^-]'`（消した行の数）と、消した行のあるファイル名 `git diff --numstat origin/main...HEAD`

## §8 合格基準
- §7-1 が 0、§7-2 がどれも 1
- 試験がすべて pass（K1〜K7。新規 6 本を含む）
- 変えたファイルが §2 の 4 つ（＋カードと台帳は設計パートナーの commit 済み）だけ。消した行は `scripts/dev/check-before-submit.sh`・`frontend/.husky/pre-push`・`scripts/tests/test_check_before_submit.py` の中だけ
- K8（CI）は設計パートナーが PR で確かめる

## §9 commit と push
- commit は 1 つ。文は Write で一時ファイル（例 `/tmp/r4b2-msg.txt`）に書き `git commit -F /tmp/r4b2-msg.txt`。1 行目 `feat(rule-enforcement): R4b-2 第1便 push の前の確認の抜け道を記録に残す`。最後の行 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- push はほかの命令とつなげず単独で：`git push origin release/r4b2-push-gap-bin1`。push の前の入口が流れる（約 90〜190 秒）。入口が × で止めたら、直さずに報告して `BLOCKED:`
- PR は作らない（設計パートナーが ready で作り、作る前に `scripts/dev/validate-pr-body.sh` の exit 0 を確かめる）

## §10 報告
- `docs/handoff/rule-enforcement/impl-report-r4b2-bin1.md` に：1 行目の受領確認（§0）、§7 の各確かめの生出力（要約しない・推測で埋めない）。報告ファイルも同じ commit に入れる
- 最後の返事（1000 字以内）の 1 行目「本報告はカード card-r4b2-bin1.md の実行結果である」。続けて push 後の `git rev-parse HEAD`、`git log -3 --oneline`、`git diff --name-only origin/main...HEAD`、pytest の結果の行、push の出力の最後の 3 行
- 止まったときは「止まった手順の番号／最後に流したコマンド／止まった理由の原文」の 3 点
- 最後の行は `DONE` / `BLOCKED: 理由` / `NEEDS_DECISION: 理由` のどれか 1 つ

## §11 想定分岐
| 場面 | どうするか |
|---|---|
| §3・§4 の「今の文」が一致で見つからない | 書き換えず `NEEDS_DECISION:`（見つからない文を原文で） |
| bash 3.2 と 5 で動きが違いそうな所 | クラウドの bash で流した結果を記録して続ける（判定は設計パートナー） |
| 既存の試験が 1 本でも落ちる（K1・K3 以外） | 判定を変えていないはずなので、直さずに生出力を貼って `NEEDS_DECISION:` |
| K3 の 5 秒を超える | 秒を記録して `NEEDS_DECISION:` |
| §7-3 の数が 13 でない | 数と `grep -n 'CBS_REASON=' scripts/dev/check-before-submit.sh` の生出力を記録して続ける |
| push の入口が終了コード 2 で通った | 表示の理由を報告に書いて続ける |
| push が送り先に断られた | 出力の最後の 10 行を貼って `BLOCKED:` |
