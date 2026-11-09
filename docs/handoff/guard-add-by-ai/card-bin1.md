# 実装カード 便1: AI が PR で入れた見張りを、週次点検が記録で説明できるようにする（点検と記録の道具）

> What this document is, in one line:
> The weekly permission audit should accept a guard hook that AI installed from a reviewed and merged PR, but only when the change adds or strengthens a guard, and it must still report every removal or weakening. These are the instructions for the audit and ledger side of that work.

- 親: design.md（同じフォルダ）§5・§10・§13。ADR-1072 は PO 承認済み（2026-11-09「1」。承認と実装の開始を選んだ返事）
- 基準: origin/main 98a4fb4c5。行番号はすべて、この版で Opus が読んで確かめた。bb87bf0b1 から対象の5ファイルに差が無いことも `git diff --stat` で確かめた
- ブランチ: `release/guard-add-by-ai-bin1`（`bash scripts/new-worktree.sh release/guard-add-by-ai-bin1 --claude`）
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・04-worktree.md・05-pr.md・10-executor.md
- 受領確認: 着手の前に、§0 を満たしたかを1行で返してから始める
- 起票: Opus が手元で行う。担当は push までとする
  - `--base main`、`shingo-cc` 名義で起票する
  - `migrations/`・`deploy.yml`・本番の `scripts/` を含まない。`scripts/dev/` の点検の道具だけを変える
  - マージと本番の反映（~/.salesanchor-tools の更新）は担当が行わない

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

- origin/main の次の行が、下の表の「基準の中身」と同じであること
  - 確かめ方の例: `git show origin/main:scripts/dev/consent-audit.py | sed -n '878p'`
  - 1つでも違えば、BLOCKED: で差を返す

| 場所 | 基準の中身（先頭の語） |
|---|---|
| `scripts/dev/consent-audit.py:450` | `LEDGER_ONLY_KEYS = (` |
| `scripts/dev/consent-audit.py:589` | `items.append("%s|%s|%s" % (event, matcher, item_sha8(ent)))` |
| `scripts/dev/consent-audit.py:656` | `files.append("%s|%s" % (sha8(os.path.relpath(fp, p["hook_dir"])), digest))` |
| `scripts/dev/consent-audit.py:801` | `PR_ONLY_TARGETS = ("repo-allow", "repo-hooks")` |
| `scripts/dev/consent-audit.py:878` | `def record_ok(home, row, held, key, h, since, rows, gh_view, git_run, v):` |
| `scripts/dev/consent-audit.py:906` | `if b_target and row.get("target") not in PR_ONLY_TARGETS:` |
| `scripts/dev/consent-audit.py:922` | `def judge_change(home, key, h, op, since, rows, gh_view, git_run=None, v=None):` |
| `scripts/dev/consent-audit.py:997` | `def run_permissions(home, out, now=None, commit=False, gh_view=None, git_run=None):` |
| `scripts/dev/consent-audit.py:1033` | `v = judge_change(home, k, h, op, old_ts, led["rows"], gh_view, git_run, tstate.get("v"))` |
| `scripts/dev/perm-change.py:660` | `def cmd_record(a, home, now, audit):` |
| `scripts/dev/perm-change.py:739` | `r.add_argument("--target", required=True)` |
| `scripts/dev/perm-change.py:745` | `r.add_argument("--actor", default="opus", choices=["opus", "po-script"])` |
| `scripts/dev/permission-delegation-tests.py:1251` | `def main():` |
| `scripts/dev/permission-delegation-tests.py:80` | `def git(cwd, *args):` |
| `scripts/dev/permission-delegation-tests.py:475` | `prefix, rest = key.split(":", 1)` |
| `scripts/dev/permission-delegation-tests.py:503` | `chk("A5-0", "写しのキーは設計の表の24種` |
| `scripts/dev/permission-delegation-tests.py:565` | `def merge_pr(e, edits, branch="feat"):` |
| `.claude/agents/reviewer.md:45` | `- 審査結果を SubagentHandback で返すとき、` |

## 1. 事実（Opus が確かめたこと。担当は確かめ直さなくてよい）

- 写しの hook_files の要素は `sha8(~/.claude/scripts からの相対パス)|中身の sha256 先頭8桁`（consent-audit.py:643-657）。例: `~/.claude/scripts/mac-test-guard/guard.py` の相対パスは `mac-test-guard/guard.py`。
- 写しの user:hooks の要素は `event|matcher|item_sha8(組の dict)`（consent-audit.py:589）。
- 今の判定は要素の末尾の8桁だけを使う（consent-audit.py:1032 `h = element_hash(el)`、:690 は末尾の `|` の後ろを返す）。
- 今は user-hooks・hook-files の行に `PR#n` を書いても、:906 で必ず通らない（B）。
- 前回の写しに無いキーは「（初回）」と出して判定しない（consent-audit.py:1019-1021）。
- `run_permissions` の `tstate.get("v")` は GitHub main の sha（ls-remote）。
- 台帳の行は make_row（perm-change.py:367）で作り、append_ledger（:375）で足す。
- 試験の補助: `Env(tmp, name, with_git=True)`（GitHub 役の bare リポジトリと ~/.salesanchor-tools の clone を作る）、`merge_pr(e, edits, branch)`（--no-ff で取り込み、取り込みの sha を返す）、`pr_view(mc, ...)`、`run_audit(env, now, commit, gh, git_run)`、`reasons(lines)`、`seed_row(env, now, **kw)`、`run_pc(env, argv, now=...)`。既にある試験は test_a1〜test_a21 で、名前 A1〜A21 を使っている。
- この試験のファイルは CI では流れていない（今もそう）。

## 2. 設計書の §13 で決めたこと（この便で作る範囲）

- §13-2: judge_change と record_ok に、既定値 None のキーワード引数 `el` と `now` を足し、run_permissions から渡す。
- §13-3: 写しのキー `guard_installer`・`guard_judge` と、TARGET_KEYS の2つの target。
- §13-4: §5 の分岐の細部。
- §13-5: record の3つの欄。
- §13-6: 試験の番号 G1〜G5・G8・G10〜G14。
- この便では install-guard.sh を作らない。mac-test-guard の札も作らない。CI の設定も変えない（便2）。

## 3. やること（この順）

1. クラウドの事前確認として、`git config user.name shingo-cc` と `git rev-parse --verify origin/main` を流す。どちらかが失敗したら停止し、BLOCKED: で返す。gh の確認と PR の起票は、Opus が手元で行う。
2. §0 を確かめ、受領確認を1行で返す。
3. §4 perm-change.py の record の欄
4. §5 consent-audit.py の写しのキーと §5 の分岐
5. §6 reviewer.md の2行
6. §7 試験を足して流す
7. §8 の検索を流す
8. commit と push。命令は次の3行だけを使う（WT は new-worktree.sh が出した worktree の絶対パス。ROW_TS は行の時刻、N は PR 番号、REST はフォルダの中の残りのパス、T_PATHS は T の各試験のパスを指す）。

```bash
cd "$WT" && git add scripts/dev/consent-audit.py scripts/dev/perm-change.py scripts/dev/permission-delegation-tests.py .claude/agents/reviewer.md
cd "$WT" && git commit -m "feat(consent-audit): record AI-installed guards by merged PR when they only add or strengthen (ADR-1072 bin1)"
cd "$WT" && git push -u origin release/guard-add-by-ai-bin1 && git log --oneline -3
```

## 4. record の欄（`scripts/dev/perm-change.py`）

### 4-1. 引数（:738-745 の record の subparser に足す）

```python
    r.add_argument("--replaced-by", default="")
    r.add_argument("--batch", default="")
    r.add_argument("--old-json", default="")
```

### 4-2. cmd_record（:660）の検査（今の検査の後、append_ledger の前に足す）

- `--replaced-by` が空でなければ `^[0-9a-f]{8}$`。違えば `Exit(EXIT_FAIL, ...)`。
- `--batch` が空でなければ `^batch:[0-9a-f]{16}$`。
- `--old-json` が空でなければ:
  - target が `user-hooks` で op が `remove` のときだけ受ける。
  - `json.loads` で object（dict）になること。
  - `audit.item_sha8(old)` が `--item-hash` と同じこと。
  - 組の `hooks` の各 `command` を空白で区切った語に、`=` を含む語、または `^[A-Za-z0-9_-]{32,}$` に当たる語があれば拒む（秘密の値の疑い）。拒む文に値を出さない。
- `--replaced-by` と `--old-json` は、両方あるか両方無いかのどちらか。片方だけなら拒む。
- `--batch` は `--replaced-by` があるときは必須。

### 4-3. 行に欄を足す

- 3つの値が空でないときだけ、行の dict に `replaced_by`・`batch`・`old_json`（読んだ dict のまま）を足す。空なら欄を作らない（今の行と同じ形のまま）。
- make_row の引数は変えない。cmd_record の中で、make_row が返した dict に足す。

## 5. 点検（`scripts/dev/consent-audit.py`）

### 5-1. TARGET_KEYS（:411-437）に2つ足す

```python
    "guard-installer": "guard_installer",
    "guard-judge": "guard_judge",
```

LEDGER_ONLY_KEYS（:450）と PR_ONLY_TARGETS（:801）には足さない。

### 5-2. 写しに2つのキー（collect_permissions の、`snap["hook_files"] = sorted(files)`（:657）の直後）

- `snap["guard_installer"]`: `<p["tools"]>/scripts/agent-hooks/install-guard.sh` があれば、その中身の sha256 先頭8桁を1つ持つ一覧。無ければ空の一覧。
- `snap["guard_judge"]`: `<p["tools"]>/scripts/dev/consent-audit.py` を読み、`# >>> ADR-1072 guard-add judge` の行と `# <<< ADR-1072 guard-add judge` の行に挟まれた行（印の行は含めない）を、出てきた順に改行でつないだ文字列の sha8 を1つ持つ一覧。印が1組も無い・印の数が合わない・ファイルが読めないときは空の一覧。
- 2つとも NOT_MATCHED_KEYS には足さない（差は判定に回る）。

### 5-3. 引数を渡す

- `judge_change(home, key, h, op, since, rows, gh_view, git_run=None, v=None, *, el=None, now=None)` にする。
- `record_ok(home, row, held, key, h, since, rows, gh_view, git_run, v, *, el=None, now=None)` にする。
- judge_change の中の record_ok の呼び出しに `el=el, now=now` を足す。
- run_permissions の :1033 を `judge_change(home, k, h, op, old_ts, led["rows"], gh_view, git_run, tstate.get("v"), el=el, now=now)` にする。

### 5-4. 分かれ目（record_ok の :906 の行の直前に置く）

```python
    # >>> ADR-1072 guard-add judge
    if ref.startswith("PR#") and row.get("target") in ("hook-files", "user-hooks"):
        return guard_add_ok(home, row, held_ts, key, h, since, rows, gh_view, git_run, v, el, now)
    # <<< ADR-1072 guard-add judge
```

- `guard_add_ok` の関数そのものも、同じ印の組で囲む（印の組は2つになる。§5-2 は全部の組をつなぐ）。
- 関数は record_ok の直前に置く。
- この分かれ目に入った行は、今の :906 以降の流れを通らない（今の「マージが前回の写しより後」の検査も使わない）。

### 5-5. `guard_add_ok` が確かめること（1つでも満たさなければ False。例外も False）

設計書 §5-0〜§5-5 と §13-4 のとおり。ここでは順番と値の取り方だけを書く。

0. 使う op は record の行の `op`（`row["op"]`）。下の 9. に挙げていない target と op の組（`user-hooks` の `modify` など）は False。
   - 印の外の関数で呼んでよいのは `sha8`・`item_sha8`・`parse_ts`・`perm_paths`・`load_json` と、引数の `gh_view`・`git_run`、標準ライブラリだけ。`_git_text` など、ほかの部品は呼ばない。要る部品は印の中に新しく書く（印の外の部品を書き換えて判定を弱めても、写し `guard_judge` が変わらないため）。
1. `el` と `now` が None でない。`v` が空でない。
2. 浅い取得でない: `git rev-parse --is-shallow-repository` の出力が `false`（tools のリポジトリで流す）。
3. PR: `gh_view(N)` が dict で `state == "MERGED"`。`mergedAt` が読める。`mergeCommit.oid` が `^[0-9a-f]{7,64}$`。`git merge-base --is-ancestor mc v` が 0。
4. 時刻: `merged < row_ts`。`base = held_ts（あれば） / since` として、base が None でなければ `base < row_ts`。`row_ts < now`。
5. 候補のフォルダ: `git diff --name-only mc^1 mc -- scripts/agent-hooks/` の各行で、`scripts/agent-hooks/<name>/REST` の形のものの `<name>` を集める（`REST` が無い＝直下のファイルは捨てる）。0件なら False。
6. 各 `<name>` の札: `git show mc:scripts/agent-hooks/<name>/guard-manifest.json` を JSON で読み、§5-0 の検査を全部当てる。
   - 欄は `name`・`files`・`hooks`・`tests` だけ。`hooks` の各項目の欄は `event`・`matcher`・`interpreter`・`file`・`after` だけ（`after` は任意）。
   - `name` が `^[a-z0-9-]+$` でフォルダ名と同じ。
   - `files`・`tests`・`hooks[].file` の各名前が `^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$` で、`/` 区切りの各部分が `.` でも `..` でもない。
   - `hooks[].event` は `PreToolUse` か `Stop`。`interpreter` は `python3` か `bash`。`after` は `^[A-Za-z0-9_.-]+$`。
   - `hooks[].file` は `files` に入っている。
   - 札が読めない・検査に外れる札が1つでもあれば、そのフォルダは候補から外す（外した結果0件なら False）。
7. §5-5 の語の検査: 候補に使う札の `files` と `hooks[].file` の各ファイルを mc の版で読み、大文字と小文字を区別して、次のどれかがあればそのフォルダは使わない: 同じ行に `permissionDecision` と `allow`、`approve`、`updatedInput`、`updatedPermissions`、`updatedToolOutput`、`behavior`、`additionalContext`（どれも部分一致）。
8. いちばん新しい版: `git log --first-parent <v> --until=ROW_TS -1 --format=%H -- scripts/agent-hooks/<name>/` の出力が mc と同じ（7〜64桁の前方一致でなく、`git rev-parse mc` の40桁と比べる）。
9. 種類ごとの検査:
   - target `hook-files`・op `add`（§5-1）: 要素 `el` の `|` の前（パスの sha8）が sha8(`<name>/<file>`) と同じ `files` の名前があり、`git show mc:scripts/agent-hooks/<name>/<file>` の sha256 先頭8桁が `h`。
   - target `hook-files`・op `remove`（§5-4。中身の書き換えの減の側）:
     - パスの sha8 が当たる `<name>/<file>` があり、今の `<home>/.claude/scripts/<name>/<file>` があって、その中身の sha256 先頭8桁が mc の版の中身の8桁と同じ（入れた先が新しい版になっている）。無ければ False（外す変更は B）。
     - P を探す: `git log --first-parent --format=%H mc^1 -- scripts/agent-hooks/<name>/` を上から順に見て、`git show <c>:scripts/agent-hooks/<name>/<file>` の sha256 先頭8桁が `h` の最初の `<c>`。無ければ False。
     - P の版の札が読めて §5-0 の検査を通る。無ければ False。
     - T = P の札の `tests` ∪ mc の札の `tests`。P の札の `tests` にあって mc の札の `tests` に無い名前が1つでもあれば False。
     - `git diff --no-renames P mc -- T_PATHS` で、`---` を除く `-` で始まる行が1行でもあれば False。
     - 同じ diff の `+++` を除く `+` で始まる行に、次の正規表現のどれかが当たれば False: `\bskip\b`・`\bxfail\b`・`\bexit 0\b`・`\bexit\(0\)`・`\bset \+e\b`。
     - CI の検査: `git show <v>:.github/workflows/agent-hooks-test.yml` を PyYAML（`yaml.safe_load`）で読む。`import yaml` は関数の中で行い、ImportError なら False。mc の札の `tests` の各パス `scripts/agent-hooks/<name>/<t>` が、どれかの job のどれかの step の `run` の値の、`#` で始まらない行（前の空白を除いて見る）に含まれること。含まれない試験が1つでもあれば False。T の試験を呼ぶ各 step について、`run` の値に `|| true`・`|| :`・`; true`・`|| exit 0`・`set +e`・` -k `・`--deselect` のどれかがある、step か job に `continue-on-error` が true、step か job に `if` の欄がある、のどれかなら False。
   - target `hook-files`・op `modify`: False（使わない）。
   - target `user-hooks`・op `add`（§5-2）:
     - `el` を分ける: `event, rest = el.split("|", 1)`、続けて `matcher, gsha = rest.rsplit("|", 1)`。matcher には `|` が入ることがある（例: `.claude/settings.json:81` の `Write|Edit`）。`rsplit("|", 2)` は使わない。user-hooks の減の側でも同じ分け方にする。
     - 今の `<home>/.claude/settings.json` の `hooks[event]` の組で、`matcher` が同じで `item_sha8(組) == h` のものを探す。無ければ False。
     - 組の `hooks` の各フックが、候補の札のどれかの `hooks` の項目から作るフック `{"type": "command", "command": "<interpreter> <home>/.claude/scripts/<name>/<file>"}` と、欄の全部が同じ（欄の数も同じ）で、その項目の event・matcher が組と同じ。1つでも当たらなければ、次の「入れ替えの増の側」を確かめる。
     - 入れ替えの増の側: 同じ PR 番号で、`replaced_by == h` の減の行（target `user-hooks`・op `remove`）が台帳にあり、その行で下の「減の側」が通るなら True。
   - target `user-hooks`・op `remove`（§5-3。入れ替えの減の側）:
     - 行に `replaced_by`・`batch`・`old_json` がある。`item_sha8(old_json) == h`。
     - 同じ PR 番号・同じ batch で、item_hash が `replaced_by` の、op `add` の record の行が台帳にある。
     - 今の settings.json に、event・matcher が `el` と同じで `item_sha8(組) == replaced_by` の組 E_new がある。
     - E_new と old_json で、`hooks` 以外の欄が全部同じ。
     - old_json の `hooks` の各フックが、E_new の `hooks` に、全部の欄が同じ形で同じ順に入っている（順を保った部分列）。
     - E_new の `hooks` のうち old_json に無いフックが、全部 op add の上の札の形に当たる。
10. ここまで全部通れば True。

- 同じ po_ref と item_hash の組は1回（今の :886-891 の検査）は、分かれ目より前にあるのでそのまま効く。
- 関数の中の git は全部 `git_run(args, tools)`（tools は `perm_paths(home)["tools"]`）で呼ぶ。試験で差し替えられるようにするため。

## 6. 審査役の定義（`.claude/agents/reviewer.md`）

:45 の行の直後に、次の2行を足す（ほかの行は変えない）。

```markdown
- 見張りのフォルダ（`scripts/agent-hooks/` の下の見張りごとのフォルダ）を変える PR では、次の2つを確かめ、当てはまれば REQUEST_CHANGES にする: 「この PR は見張りの止める範囲を狭めていないか」。
- 同じ PR で: 「確認を飛ばす返事（allow・approve）や、実行する中身を書き換える返事を返す道を作っていないか」（ADR-1072）。
```

## 7. 試験（`scripts/dev/permission-delegation-tests.py`）

- 既にある test_a1〜test_a21 は変えない。例外は次の2か所だけ（写しのキーが2つ増えるため。§5-1）:
  - :503 の A5-0: `len(ALL_KEYS) == 24` を `len(ALL_KEYS) == 26` に、文の「24種」を「26種」にする。ほかの条件は変えない。
  - :464 の mutate: :475 の `key.split(":", 1)` の前に2つの分かれを足す。
    - `key == "guard_installer"`: `<env.tools>/scripts/agent-hooks/install-guard.sh` を（フォルダを作って）`#!/bin/bash\necho new\n` で書き、return。
    - `key == "guard_judge"`: `<env.tools>/scripts/dev/consent-audit.py` を（フォルダを作って）次の3行で書き、return: `# >>> ADR-1072 guard-add judge`・`x = 1`・`# <<< ADR-1072 guard-add judge`。
  - A5 の繰り返しは、この2つのキーでも今の期待（B が出る）のまま通ること。
- 新しい関数の名前は `test_g1` のように G を付ける。main（:1251）の一覧の最後に足す。
- 時刻は T0（:25）を使わず、試験の中で固定する（設計書 §10 の A2: 前回の写しは 2026-11-09T04:00:00Z、マージは 05:00:00Z、record の行は 06:00:00Z、点検の now は 07:00:00Z）。ほかの G も、特に書いていなければ同じ時刻を使う。
- git の commit の日時も固定する。§5-5 の 8. の `--until` は commit の日時で選ぶので、今の時計で commit すると G1・G2・G10 が誤って B になる（2026-11-09 09:44 UTC にクラウドの審査で実行して確かめ済み）。
  - 新しい補助 `git_at(cwd, when, *args)` を足す。中身は :80 の `git` と同じで、`env=dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)` を付けて流す（`when` は `2026-11-09T05:00:00Z` の形の文字列）。
  - 新しい補助 `merge_pr_at(e, edits, when, branch="feat")` を足す。中身は :565 の `merge_pr` と同じで、commit と merge の2つだけ `git_at(..., when, ...)` で流す。
  - G の中でマージを作るときは、全部 `merge_pr_at` を使う。`merge_pr` と `e.advance` は使わない。前の版（§5-5 の 9. の P）を作るマージは `2026-11-09T03:00:00Z` にする。
  - 偽の gh_view の `mergedAt` は、同じ PR の `merge_pr_at` の `when` と同じ時刻にする。
- 一時の HOME の中に、`.claude/scripts/<name>/` と `.claude/settings.json` を試験が書く（台本は便2 で作るので、この便では試験が台本の手順 5・7 と同じことをする）。
- 見張りの見本の中身は試験の中に文字列で書く。本物の mac-test-guard を読む必要は無い（中身は §5-5 の語を含まないこと）。札の見本は設計書 §5-0 の形。
- CI の見本: 一時の git リポジトリに `.github/workflows/agent-hooks-test.yml` を置き、試験のパスを `run:` で呼ぶ形にする。
- 記録の行は `run_pc(env, ["record", ...], now=...)` か seed_row で書く。G2 は設計書 §10 の A2 のとおり perm-change の main を now 付きで呼ぶ。
- PyYAML: `python3 -c "import yaml"` が失敗したら `python3 -m pip install pyyaml==6.0.3` を1回だけ流す。それも失敗したら停止し、BLOCKED: で生の出力を返す。

| 試験 | 中身（設計書 §10 の基準） | 期待 |
|---|---|---|
| G1 | A1: §5-1〜3 を満たす増・入れ替え | B に出ない |
| G2 | A2: 今週の3件と同じ形の3行。あわせて札の無い版の番号の行 | 3行は B 0件。札の無い版は B |
| G3 | A3: 組から命令を抜く入れ替え／既にあるフックの timeout を縮める入れ替え（2件） | どちらも B |
| G4 | A4 の点検の側: PR に無い中身／札の無いフォルダ／直下のファイル／札に `../` か `/` で始まる名前／event が PreToolUse と Stop 以外（5件） | どれも B |
| G5 | A5（5件。設計書 §10 のとおり） | どれも B |
| G8 | A8 の点検の側: 語ごとの7件は B。止めない見本2件（試験ファイルだけの `--approve`・本体の大文字の `APPROVE`）は B にならない | 7件 B・2件 B なし |
| G10 | A10（2件。now を固定） | 1件目 B なし・2件目 B |
| G11 | A11 の点検の側（2件）＋浅い取得で B（1件） | どれも B |
| G12 | A12（7件。設計書 §10 のとおり） | 6件 B・`skipping` の1件は B なし |
| G13 | §13-3: ①前回の写しに `guard_judge` が無い→「（初回）」で B なし ②値が変わり記録なし→B ③値が変わり `PR#n` の record→B ④install-guard.sh が無い（空の一覧）から有る→記録なしで B | 期待のとおり |
| G14 | §13-5: `--old-json` の item_sha8 が違う／target が user-hooks でない／片方だけ／`=` を含む語／32字以上の語／batch の形が違う は拒む。正しい形は1行書け、行に3つの欄がある | 期待のとおり |

- 流す命令（クラウドで。Mac では流さない）:

```bash
cd "$WT" && python3 scripts/dev/permission-delegation-tests.py > /tmp/pd-tests-out.txt 2>&1; echo "rc=$?"; tail -n 5 /tmp/pd-tests-out.txt
```

- 合格: `FAIL=0`。既にある試験の PASS の数が減っていないこと（変える前の main でも1回流し、`PASS=` の行を報告に入れる）。

## 8. 終わったときの検索（PR の枝で流し、結果を報告に入れる）

```bash
# 印の組（4行: 開き2・閉じ2）
cd "$WT" && git grep -n "ADR-1072 guard-add judge" -- scripts/dev/consent-audit.py
# 2つの target（2件）
cd "$WT" && git grep -n -e '"guard-installer"' -e '"guard-judge"' -- scripts/dev/consent-audit.py
# PR_ONLY_TARGETS は変えていない（1件。中身は §0 の表と同じ）
cd "$WT" && git grep -n "^PR_ONLY_TARGETS" -- scripts/dev/consent-audit.py
# record の3つの欄（3件）
cd "$WT" && git grep -n -e '"--replaced-by"' -e '"--batch"' -e '"--old-json"' -- scripts/dev/perm-change.py
# 試験 G（11件）
cd "$WT" && git grep -n "^def test_g" -- scripts/dev/permission-delegation-tests.py
# 日時を固定する補助（2件）と、A5-0 の数（1件。26）
cd "$WT" && git grep -n -e "^def git_at" -e "^def merge_pr_at" -- scripts/dev/permission-delegation-tests.py
cd "$WT" && git grep -n 'len(ALL_KEYS) == 26' -- scripts/dev/permission-delegation-tests.py
# 既にある試験の差は §7 の例外2か所だけ（- の行は A5-0 の1行だけ）
cd "$WT" && git diff origin/main...HEAD -- scripts/dev/permission-delegation-tests.py | grep '^-[^-]'
# 変えたファイル（4件）
cd "$WT" && git diff origin/main...HEAD --name-only
```

## 9. 想定される分かれ道（こうなったらこうする）

| 起きたこと | どうする |
|---|---|
| §0 の行が基準と違う | 停止し、BLOCKED: で差を返す |
| 既にある試験（test_a1〜test_a21）が1つでも落ちる | §7 の例外2か所（A5-0 の数・mutate の2つの分かれ）のほかは書き換えない。停止し、BLOCKED: で生の出力を返す |
| 設計書 §5・§13 と、この カードの §5-5 が食い違う | 書き手の判断で決めない。NEEDS_DECISION: で両方の文を返す |
| G の期待を満たすには §5-5 に無い条件が要る | 条件を足さない。NEEDS_DECISION: で返す |
| 試験の中で実物の GitHub に触れたくなる（gh を本当に呼ぶ等） | 呼ばない。gh_view と git_run は偽物か一時のリポジトリに向ける |
| `~/.claude`・`~/.salesanchor-tools`・agent-console を読む・書く必要が出た | 触らない。停止し、BLOCKED: で返す（この便は一時の HOME の中だけで完結する） |
| PyYAML が入らない | 停止し、BLOCKED: で生の出力を返す |
| Mac で試験を回したくなる | 回さない。クラウドで流す |

## 10. 触らない

- `~/.claude` の全部（settings.json・フック・permits・scripts）と `~/.salesanchor-tools`、agent-console
- `scripts/agent-hooks/` の全部（install-guard.sh と札は便2）
- `.github/workflows/` の全部（CI の追加は便2）
- `.claude/agents/reviewer.md` の §6 の2行以外、`docs/agents/reviewer.md`
- consent-audit.py の :906 以降の今の判定の中身（分かれ目の後ろの流れ）、`pr_diff_ok`、`PR_ONLY_TARGETS`、`LEDGER_ONLY_KEYS`
- perm-change.py の apply・review・sync と startup_checks

## 11. 終わりの報告

- `DONE`／`BLOCKED: 理由`／`NEEDS_DECISION: 問い` のどれかで始める
- 停止したときは、その場で手を止める。`BLOCKED:` で始めて、止まった手順・命令・生の出力を返す。自分で回り道を作らない
- 報告に入れるもの:
  - push した HEAD（40桁）と `git log --oneline -3` の生の出力
  - §7 の試験の生の出力の最後の5行（変える前の main と、変えた後の両方）と、`FAIL` を含む行の全部
  - §8 の6つの検索の生の出力
- 推測で埋めない。読めなかった出力は「読めなかった」と書く

## 12. 反映の後（Opus と PO が行う。担当はしない）

- マージ前: 新しく起動した opus の審査役の APPROVE（ADR-1029）。
- マージの後の最初の週次点検で、Opus が次を確かめて記録に残す。
  - `guard_installer`・`guard_judge` が「（初回）」と出て、B が増えていないこと。
  - 定期作業の python3 で PyYAML が読めるか（設計書 §13-4 の未確認）。
- 便2 のカードは、この便のマージの後に書く。

END OF CARD
