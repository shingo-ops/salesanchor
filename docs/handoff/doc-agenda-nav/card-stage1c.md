# 実装カード 段1c — 商品マスタ登録の見張りの免除を「パスのどこかに含む」から「決まった場所で始まる」に締める

> この文書は何か：doc-agenda-nav 段1c の作業指示書です。商品マスタ登録の見張り（`scripts/agent-hooks/master-register-rules-guard.py`）は、Write/Edit の保存先のパスに `/docs/` や `/tmp/CC報告ファイル/` などが**どこかに含まれていれば**素通りさせます（部分一致）。このため、リポジトリの外の `~/x/docs/a.py` や、記録の置き場に置いた台本 `/tmp/CC報告ファイル/x.py` へ登録の命令を書いても止まりません。これを「リポジトリ（作業場所）の根の直下の決まった段」と「記録の置き場で始まり、拡張子が .md か .txt」のときだけ素通りさせる形に締めます。この Mac の見張りの本体（ホームの `.claude/scripts/` の同名ファイル）への写しは、マージの後に PO が `!` で行います（§8）。

- 設計: docs/handoff/doc-agenda-nav/design.md §31
- recon: docs/handoff/doc-agenda-nav/recon.md（この段の現在地は §2 の表。2026-10-26 Opus が origin/main 2d25c719d で確認）
- 対象ADR: ADR-1040（Accepted）。関連: ADR-076・ADR-113
- 前の段: 段1b（card-stage1b.md、マージ済み）。同じ1行（`EXEMPT_PATHS`）と同じ試験ファイルを触る
- 状態: PO の指示原文「1」に続けて「,2」（2026-10-26。残り4件をまとめて計画して進める。この段はその3件目 C）
- 危険便（ADR-136 の危険パス）: はい。`scripts/` を触るため PR 本文に `### GO記録` が要る。GO は ADR-1003 の委譲名義で Opus が出す
- 担当: 実装と試験はクラウドの担当（PO 2026-10-26「1」＝直しと試験はクラウドで動かす）。push まで。PR は手元で Opus が shingo-cc 名義で作る。審査は Opus（reviewer を model "opus" で新しく起こす）、GO・マージは Opus、見張りの本体への写しは PO

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10。PR は手元で Opus が作る） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（免除の判定だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/doc-agenda-nav-stage1c） |
| 6 | 書式は実例で示した | ○（§4 は完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（試験名と PASS/FAIL を1行ずつ出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（§2） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段1c の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `scripts/agent-hooks/master-register-rules-guard.py` の :23 の1行（`EXEMPT_PATHS`）を、§4-1 の定数4行に置き換える
2. 同じファイルの `deny()` の後（:52 の空行2行の後、`def pre_tool_use` の前）に関数 `exempt()` を足す（§4-2）
3. 同じファイルの :66 の免除の判定を `exempt(fpath)` に変える（§4-3）
4. `scripts/agent-hooks/test_master_register_rules_guard.sh` の T3 の前提・T19 のパスを直し、T22〜T28 を足す（§4-4）

入れない:
- :14 の `REPO`・:25 の `PROMPT_RE`・Bash の判定（:67-71）・印の判定（:72-84）
- ホームの `.claude/settings.json`
- `.github/workflows/agent-hooks-test.yml`
- ホームの `.claude/scripts/` への写し（§8。PO が行う）

## 2. 前提の事実（2026-10-26 Opus が origin/main 2d25c719d で確認）

| # | 事実 | 出典 |
|---|---|---|
| F1 | :23 は `EXEMPT_PATHS = ("/backend/", "/frontend/", "/docs/", "/migrations/", "/tests/", "/CC報告ファイル-keep/", "/tmp/CC報告ファイル/")` | 見張りの実物 |
| F2 | :66 は `if tool in ("Write", "Edit") and any(p in fpath for p in EXEMPT_PATHS):` の次行 `return`。パスのどこかに含めば素通り（部分一致） | 見張りの実物 |
| F3 | :14 は `REPO = os.environ.get("CLAUDE_PROJECT_DIR") or "/Users/tanizawashingo/salesanchor"` | 見張りの実物 |
| F4 | 作業場所は `~/worktrees/salesanchor/<ブランチ名>/` に作られる | `scripts/new-worktree.sh:13` |
| F5 | 試験は T1〜T21（85行、最後の行が `exit $FAIL`）。T3 は `/repo/backend/app/a.py` への Write が素通り、T19 は `/Users/tanizawashingo/CC報告ファイル-keep/x.md`、T20 は `/tmp/CC報告ファイル/x.md` への Write が素通り、T21 は Bash が止まる | 試験の実物 |
| F6 | 試験は CI で動かない（`.github/workflows/agent-hooks-test.yml:24` は review-gate の試験だけ）。担当の実行結果が証拠 | ワークフローの実物 |
| F7 | ホームの見張りの本体と origin/main の版は同じ（`diff` 終了コード 0） | Opus 実測（2026-10-26） |
| F8 | `EXEMPT_PATHS` を使う見張りはこの1本だけ | Opus 実測（2026-10-26。design §31-2） |

決めたこと（design §31-3）:
- リポジトリの中の免除: パスを `os.path.normpath` で整えた後、`REPO` の直下、または `~/worktrees/salesanchor/<名前>/` の直下で、最初の段が `backend`・`frontend`・`docs`・`migrations`・`tests` のどれかのときだけ。`..` を使ってリポジトリの外へ出るパスは整えた後の形で判定するので素通りしない。
- 記録の置き場の免除: 整えた後のパスが `~/CC報告ファイル-keep/`・`/tmp/CC報告ファイル/`・`/private/tmp/CC報告ファイル/` で始まり、かつ `.md` か `.txt` で終わるときだけ。
- 絶対パスでないもの（`/` で始まらない）は免除しない。
- 試験の T3 は、試験の頭で `CLAUDE_PROJECT_DIR=/repo` を置いて、今までどおり `/repo/backend/app/a.py` が素通りすることを見る（試験はこの Mac 以外でも同じ結果になる）。T19 は `$HOME` で書く（`~` の展開と一致させる）。

## 3. 触るファイル（これ以外は触らない）

- 変更: `scripts/agent-hooks/master-register-rules-guard.py`（§4-1〜4-3 だけ）
- 変更: `scripts/agent-hooks/test_master_register_rules_guard.sh`（§4-4 だけ）
- 変更: `docs/handoff/doc-agenda-nav/card-stage1c.md`（このカード。担当は §13 報告欄の追記だけ）

## 4. 作り方

4-1. :23 の次の1行（変更前）:

```python
EXEMPT_PATHS = ("/backend/", "/frontend/", "/docs/", "/migrations/", "/tests/", "/CC報告ファイル-keep/", "/tmp/CC報告ファイル/")
```

を、次の4行にする（他の行は変えない）:

```python
WORKTREES = os.path.expanduser("~/worktrees/salesanchor")
REPO_DIRS = ("backend", "frontend", "docs", "migrations", "tests")
RECORD_DIRS = (os.path.expanduser("~/CC報告ファイル-keep"), "/tmp/CC報告ファイル", "/private/tmp/CC報告ファイル")
RECORD_EXTS = (".md", ".txt")
```

4-2. `def deny(reason):` の関数の後（その関数の最後の行 `    }})` の後の空行2行の後）、`def pre_tool_use(data):` の前に、次を足す（完成形。後ろに空行2行を置く）:

```python
def exempt(fpath):
    """Write/Edit の保存先が免除の場所か。部分一致ではなく、決まった場所で始まるかで見る。"""
    if not isinstance(fpath, str) or not fpath.startswith("/"):
        return False
    p = os.path.normpath(fpath)
    if p.endswith(RECORD_EXTS) and any(p.startswith(d + "/") for d in RECORD_DIRS):
        return True
    for root, skip in ((os.path.normpath(REPO), 0), (WORKTREES, 1)):
        if not p.startswith(root + "/"):
            continue
        parts = p[len(root) + 1:].split("/")[skip:]
        if len(parts) > 1 and parts[0] in REPO_DIRS:
            return True
    return False
```

4-3. :66 の次の1行（変更前）:

```python
    if tool in ("Write", "Edit") and any(p in fpath for p in EXEMPT_PATHS):
```

を、次の1行にする（次の行の `        return` は変えない）:

```python
    if tool in ("Write", "Edit") and exempt(fpath):
```

4-4. 試験ファイルを次のとおり直す（完成形。1字も変えない）。

(a) 7行目 `export MRR_RULES_FILE=...` の次に1行足す:

```bash
export CLAUDE_PROJECT_DIR=/repo
```

(b) T19 の行（変更前）:

```bash
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' /Users/tanizawashingo/CC報告ファイル-keep/x.md | python3 "$G")"
```

を、次の1行にする:

```bash
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' "$HOME/CC報告ファイル-keep/x.md" | python3 "$G")"
```

(c) 最後の `exit $FAIL` の前に、次を足す:

```bash
# T22〜T28: 免除は決まった場所で始まるときだけ（doc-agenda-nav 段1c。docs/handoff/doc-agenda-nav/card-stage1c.md §4-4）
O="$(mk PreToolUse Write content 'create_product(x)' "$HOME/x/docs/a.py" | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T22 リポジトリの外の docs は止まる" $?
O="$(mk PreToolUse Write content 'create_product(x)' /tmp/CC報告ファイル/x.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T23 記録置き場の .py は止まる" $?
O="$(mk PreToolUse Write content 'create_product(x)' "$HOME/worktrees/salesanchor/release-a/docs/a.md" | python3 "$G")"
[ -z "$O" ]; check "T24 作業場所の docs は素通り" $?
O="$(mk PreToolUse Write content 'create_product(x)' /repo/backend/../../tmp/a.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T25 .. で外へ出るパスは止まる" $?
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' /private/tmp/CC報告ファイル/x.md | python3 "$G")"
[ -z "$O" ]; check "T26 記録置き場(/private/tmp)への .md は素通り" $?
O="$(mk PreToolUse Write content 'create_product(x)' backend/a.py | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T27 絶対パスでないものは止まる" $?
O="$(mk PreToolUse Write content 'create_product(x)' /repo/backend | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T28 段の名前そのもの(下に何も無い)は止まる" $?
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `git diff origin/main -- scripts/agent-hooks/master-register-rules-guard.py` の全文（期待: §4-1 の `-` 1行・`+` 4行、§4-2 の `+` 16行（関数14行と空行2行）、§4-3 の `-` 1行・`+` 1行）。
5-2. `bash scripts/agent-hooks/test_master_register_rules_guard.sh; echo "rc=$?"` の全文（期待: PASS が T1〜T8 の8行・T9〜T18 の10行・T19〜T21 の3行・T22〜T28 の7行の計28行。FAIL 0行。最後の行が `rc=0`）。
5-3. わざと元に戻して落ちることを確かめる: §4-3 の1行だけを Edit で変更前の1行に戻し、§4-1 の4行の後に変更前の `EXEMPT_PATHS = ...` の1行を一時的に足して、5-2 を実行する（期待: T22・T23・T25 の3行が FAIL、ほかは PASS、`rc=1`）。確かめたら Edit で一時の1行を消し、§4-3 を変更後の1行に戻し（`git checkout` は使わない）、5-1 と 5-2 をもう一度実行して貼る。
5-4. `python3 -I -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" scripts/agent-hooks/master-register-rules-guard.py; echo "rc=$?"` と `bash -n scripts/agent-hooks/test_master_register_rules_guard.sh; echo "rc=$?"`（どちらも `rc=0`）。
5-5. `git grep -n 'EXEMPT_PATHS' -- scripts/` が0行（古い名前が残っていない）。
5-6. `git diff origin/main --stat` が §3 の3ファイルだけ。

## 6. 分岐ごとの対処

- 5-2 で T1〜T21 のどれかが FAIL → §4 以外を触っていないか 5-1 で確かめ、触っていなければ BLOCKED:（式や試験を変えない）。
- T24 が FAIL → クラウドの `$HOME` と `os.path.expanduser("~")` が違う可能性がある。両方の値を `echo "$HOME"` と `python3 -c 'import os;print(os.path.expanduser("~"))'` で出して BLOCKED:。
- 5-3 の FAIL が T22・T23・T25 の3行でない → 実際の行を貼って NEEDS_DECISION:。
- 見張りに止められた（この試験の文字列自体が監視語に当たる場合を含む） → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| リポジトリの外の `docs` への登録の命令が止まる | §5-2 の T22 が PASS |
| 記録の置き場の台本（.py）が止まる | §5-2 の T23 が PASS |
| `..` で外へ出るパス・絶対パスでないもの・段の名前そのものが止まる | §5-2 の T25・T27・T28 が PASS |
| リポジトリ・作業場所の決まった段と記録の置き場の .md は今までどおり素通り | §5-2 の T3・T19・T20・T24・T26 が PASS |
| 既存の T1〜T21 が通る | §5-2 |
| 試験が元の部分一致では落ちる | §5-3 |
| 変えたのは §4 の場所だけ | §5-1・§5-5・§5-6 |
| ホームの見張りの本体がリポジトリの版と同じになる | §8 の diff の出力が空（`SAME`） |

## 8. 見張りの本体への写し（マージの後。PO が `!` で行う。担当はしない）

- 型は card-stage1b.md §8 と同じ（写す前に .bak → `.new` に書いて空でないことを確かめる → 本体へ → diff で一致）。`.bak-` の後は写す日の日付と `-stage1c` にして、段1・段1b の .bak を上書きしない。
- マージの後、Opus が本店で `git fetch origin` を行い、その1行を台本ファイルにして PO に渡す。
- 期待: 最後の行が `SAME`。
- 反映の確かめ（Opus）: 写した後、`/tmp/CC報告ファイル/` へ監視語を引用した .md を Write して止まらないこと、同じ場所へ監視語入りの .py を Write しようとして止まること。

## 9. 戻し方

- 見張りの本体: PO が `!` で .bak から戻し、repo 版との diff で確かめる。
- repo: この PR の revert を main にマージする。
- 戻すと、部分一致の免除に戻る（段1b と同じ）。

## 10. PR

- 作業の枝は `release/doc-agenda-nav-stage1c`（origin/main 2d25c719d 起点・2026-10-26。このカードと design §31 のコミットが載っている）。担当はこの枝を取ってきて、その上で作業する。新しい枝は作らない。
- push は `git push origin release/doc-agenda-nav-stage1c`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage1c -1 --oneline` で確かめる。
- PR は担当は作らない（コード変更を含むため。scripts/agent-hooks/cloud/rules.md）。Opus が手元で shingo-cc 名義・ready・base main で作る。本文に `### 標準ワークフロー確認`（recon・設計・このカード・`対象ADR: ADR-1040（関連: ADR-076・ADR-113）`）と `### GO記録` を置く。
- `.claude-pipeline/active-work.d/` は commit しない。

## 11. 報告

- 完了報告に: 冒頭の受領文／§5-1〜5-6 の出力／push した commit の番号／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない
- ファイルの作成と編集は Write/Edit ツールで行う
- 担当は PR を作らない（§10）
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

本報告はカード doc-agenda-nav 段1c の実行結果である。

