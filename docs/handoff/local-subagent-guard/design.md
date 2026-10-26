# design — 手元の担当（サブエージェント）の書き換え・保存・送り出しをフックで止める

- 状態: 設計案（第2版 2026-10-26）。第1版は審査役（reviewer・opus）REQUEST_CHANGES（指摘 1〜12、/tmp/CC報告ファイル/local-subagent-guard/review-1.md）。第2版で全件を反映
- 関連: [recon.md](recon.md)・[ADR-1045](../../adr/ADR-1045-local-subagent-write-guard.md)・ADR-1029（前例）・ADR-1011:39（フックは AI がパッチ、PO が `!` で反映）
- PO の決定（2026-10-26）: 「1」重い実装と試験はクラウド、手元の担当は Mac の中を見る短い調べものだけ。「１」その決まりを仕組みで守らせるため、手元の担当の書き換え・保存・GitHub への上げを全部止める

## 1. あるべき姿

手元の Mac で Opus 本体が呼び出した担当（Sonnet・Opus のどちらでも。fork とチーム機能の仲間（teammate）も同じ扱い）は、読む・数える・一覧を見ることはできるが、ファイルを書き換える道具を使えず、git の作業場所・履歴を変えることも、GitHub へ書き込むことも、別の AI を起動して代わりにやらせることもできない。破ろうとするとフックが止め、「調べた結果を本体に返してください」と出る。Opus 本体とクラウドの作業は今までどおり。

## 2. KGI（PO の決定「１」から。○×で判定）

| # | 成功条件 |
|---|---|
| G1 | 手元の担当が Write・Edit・MultiEdit・NotebookEdit を使おうとすると止まる |
| G2 | 手元の担当が Bash・Monitor で、git の読むだけの使い方（§5-3 表A）以外、gh の読むだけの使い方（表B）以外、GitHub へ書く台本（表C）、別の AI の起動（表D）をしようとすると止まる |
| G3 | Opus 本体の同じ操作は止まらない |
| G4 | 手元の担当の読むだけの命令（表A・表B・ls・cat・grep など）は止まらない |
| G5 | 審査役の流れ（審査役が gh pr view・git diff で読み、VERDICT を返す → 記録 → 本体がマージ）が今までどおり回る |
| G6 | 試験の台本がリポジトリにあり、CI で自動で流れる |

対象外:
- 担当が Bash の命令文でファイルを書き換えること（`>`・`sed -i`・`tee`・`python -c` など）は止めない（§7）。
- MCP の書き込み道具（Artifact の公開・Gmail の送信・Google Drive・Figma・Canva への書き込みなど）は止めない。PO の決定の範囲（ファイル・git・GitHub）の外。
- クラウドの見張り（scripts/agent-hooks/cloud/）は変えない。

## 3. KPI

- K-a: 導入後、手元の担当の Write/Edit/MultiEdit/NotebookEdit が通った件数 = 0（agent-console の活動記録の PostToolUse で agent_id 付きの行を数える。数えるのは本体）
- K-b: 導入後、本体の操作が止められた件数 = 0（guard.log の行は担当のときだけ書かれる。本体の止めは仕組み上起きない）
- K-c: 導入後 1 週の guard.log の件数と規則の内訳（誤った止めがあれば表A・表Bを直す）

## 4. recon の要点（詳細は recon.md）

- 担当の呼び出しには agent_id が入り、本体には入らない（公式文書・実際の記録 49/54 件と 131/51 件。recon.md §1・§2）。公式文書の agent_id は「the subagent or in-process teammate」なので teammate も止まる。model は入らないので agent_id の有無で分ける。
- 審査役は SubagentHandback で返すだけで、書き換えも commit も要らない（recon.md §3）。→ 例外の担当を作らず一律に止められる。
- 前例: review-gate の install/rollback/CI の型（recon.md §5）。命令文の前処理はクラウドの guard_pre_tool.py の scan_text を使い回す（import しても標準入力を読まない。読み込み時の副作用は環境変数 CLOUD_GUARD_DEADLINE_SEC の読み取りと定数の定義だけ。審査役が確認）。

## 5. design

### 5-1. 置くもの（リポジトリ）

| ファイル | 役割 |
|---|---|
| scripts/agent-hooks/local-subagent-guard/guard.py | PreToolUse（matcher `Write\|Edit\|MultiEdit\|NotebookEdit\|Bash\|Monitor`）。§5-2・§5-3 の判定 |
| scripts/agent-hooks/local-subagent-guard/test_guard.sh | 試験。偽の入力 JSON で §8 の全行を確かめる。本物の ~/.claude には触れない。§5-6 の台本の洗い出しの照合も行う |
| scripts/agent-hooks/local-subagent-guard/install.sh | PO が `!` で実行。§5-5 |
| scripts/agent-hooks/local-subagent-guard/rollback.sh | PO が `!` で実行。§5-5 |
| .github/workflows/agent-hooks-test.yml | job を 1 つ足し `bash scripts/agent-hooks/local-subagent-guard/test_guard.sh` を流す。既存の review-gate の job は変えない。paths は既存の `scripts/agent-hooks/**` で足りる |
| docs/adr/ADR-1045-local-subagent-write-guard.md・docs/adr/README.md | ADR と索引（`node scripts/generate-adr-index.js`） |

Python 3 標準ライブラリだけ。

### 5-2. guard.py の判定（上から順に、最初に当たったもの）

1. 標準入力が JSON の辞書として読めない → 何もせず exit 0（本体か担当か分からず、本体を止めないため。§7）
2. `agent_id` が無い、または空文字 → exit 0（Opus 本体）
3. `tool_name` が Write・Edit・MultiEdit・NotebookEdit → 止める（規則名 `tool`）
4. `tool_name` が Bash または Monitor:
   - `tool_input.command` が無い（Monitor で command を使わない呼び方）→ exit 0
   - `tool_input.command` が文字列でない → 止める（規則名 `command-not-string`）
   - guard_pre_tool の読み込みに失敗していた → 止める（規則名 `import-failed`。本体は手順 2 で先に通っている）
   - それ以外は §5-3 の判定。当たれば止める。当たらなければ exit 0
5. それ以外 → exit 0

guard_pre_tool の読み込み: `sys.path.insert(0, <guard.py のディレクトリ>)` の後、そこに guard_pre_tool.py が無ければ `<guard.py のディレクトリ>/../cloud` も足して `import guard_pre_tool`（導入後は同じディレクトリ、リポジトリでは ../cloud）。失敗は例外を捕まえて覚えておき、手順 4 で使う（読み込みの失敗で本体を止めないため、手順 1・2 より前には判断しない）。settings.json の命令は `python3 <パス>`（`-I` を付けない。`-I` だと台本のディレクトリが読み込み先から外れるため）。

止めるときは exit 2、stderr に次の 1 行（agent_type が無ければ「名前なし」）:
`手元の担当（<agent_type>）は、ファイルの書き換え・git の作業場所や履歴の変更・GitHub への書き込み・別の AI の起動をしません（ADR-1045・規則 <規則名>）。調べた結果を本体に返してください。書き換えが要る作業はクラウドで行います。`

止めたときだけ `~/.claude/scripts/local-subagent-guard/guard.log` に 1 行（UTC 時刻・agent_type・tool_name・規則名）を足す。命令文そのものは書かない（秘密が混じりうるため）。log が書けなくても止めることは変えない。

### 5-3. Bash・Monitor の命令の判定

前処理:
1. `s = guard_pre_tool.scan_text(command)`（ファイルへ書くだけの heredoc の本文、読むだけの区間（grep 等）、git commit / gh pr・issue の区間の引用符の中身を消す）
2. `s` を次の文字で区切って「区間」に分ける: `$(`・`;`・`&`・`|`・改行・`(`・`)`・`{`・`}`・バッククォート・`'`・`"`（引用符も区切りにするので `bash -c 'git push'`・`eval "git push"` の中も 1 区間として見える）
3. 区間を空白で語に分ける。語の「名前」は最後の `/` より後ろ（`/usr/bin/git` → `git`）

区間の語を左から見て、次のどれかに当たれば止める:

- 名前が表C の台本 → 規則 `script`
- 名前が `claude` か `codex`（表D）で、区間の最初の語の名前が `which`・`type`・`command`・`ls`・`file`・`stat` ではない → 規則 `agent`
- 名前が `git` → その後ろの語を表A で判定。読むだけでなければ規則 `git-<動詞>`
- 名前が `gh` → その後ろの語を表B で判定。読むだけでなければ規則 `gh-<語>`

**表A git**（`git` の後ろの語。先頭の `-` で始まる語は選択肢として飛ばす。`-C`・`-c`・`--git-dir`・`--work-tree`・`--namespace`・`--config-env`・`--super-prefix` のちょうどその語のときは次の 1 語も飛ばす。`-C/a`・`--git-dir=/a`・`-P` は 1 語。飛ばした後に語が無ければ通す）

| 動詞 | 判定 |
|---|---|
| log・status・diff・show・fetch・ls-remote・ls-files・ls-tree・rev-parse・rev-list・merge-base・merge-tree・blame・grep・describe・shortlog・cat-file・for-each-ref・show-ref・name-rev・range-diff・cherry・whatchanged・count-objects・version・help・var・check-ignore・check-attr・verify-commit・verify-tag・fsck・diff-tree・diff-index・diff-files | 通す |
| stash | 次の語が list・show なら通す |
| worktree | 次の語が list なら通す |
| notes | 次の語が list・show なら通す |
| commit-graph | 次の語が verify なら通す |
| submodule | 次の語が status なら通す |
| reflog | 次の語が無いか show なら通す |
| remote | 次の語が無いか -v・show・get-url なら通す |
| config | 後ろに --get・--get-all・--get-regexp・--list・-l・--get-urlmatch のどれかがあれば通す |
| symbolic-ref | `-` で始まらない語が 1 つ以下なら通す |
| branch | 後ろの語（`=` の前）に -d・-D・-m・-M・-c・-C・-f・--delete・--move・--copy・--force・-u・--set-upstream-to・--unset-upstream・--edit-description・--track・-t・--create-reflog があれば止める。`-` で始まらない語があり、かつ -l・--list・--contains・--no-contains・--merged・--no-merged・--points-at・--all・--remotes・--verbose・--show-current・-n のどれも無ければ止める（枝を作る形）。それ以外は通す |
| tag | branch の止める語に -a・--annotate・-s・--sign・-F・--file を足したもので同じ判定 |
| 上に無い動詞（commit・push・merge・rebase・cherry-pick・revert・am・pull・checkout・switch・restore・reset・clean・add・rm・mv・apply・init・clone・update-ref・gc・prune など全部） | 止める |

**表B gh**（`gh` の次の語。api は別扱い）

| 語 | 通す次の語 |
|---|---|
| pr | view・list・checks・diff・status |
| issue | view・list・status |
| run | view・list・watch |
| repo | view |
| release・workflow | view・list |
| auth | status |
| label・secret・cache・extension・alias | list |
| variable・config | list・get |
| gist | view・list |
| ruleset | list・view・check |
| search・status・help・version・--version | 次の語を問わず通す |
| 上に無い語・上の語で通す次の語以外 | 止める |

gh api: 後ろの語に `-X`/`--method`（`-X POST`・`-XPOST` ではなく `-X=POST`・`--method=POST` も）があれば、GET のときだけ通し、それ以外は止める。無ければ、`graphql` の語があるとき、元の command 全体に語 `mutation` があれば止め、無ければ通す。それ以外は、同じ区間に `-f`・`-F`・`--field`・`--raw-field`・`--input`（`=` 付きも）があれば止める（gh は値を付けると POST にするため）。どれでもなければ通す。区間で見るので `gh api … | jq -f x` の jq の `-f` には当たらない。

**表C GitHub へ書く台本**: gh-pr-create-safe.sh・gh-pr-merge-safe.sh・check-pr-merge-ready.py・new-worktree.sh・codex-generator.sh・register-pr.sh・card-lint.sh・perm-change.py・permission-delegation-tests.py・test-agent-hooks.sh・permit-danger.sh・setup-vps-runner.sh・validate-pr-ownership.sh（§5-6 の洗い出しの結果。設計者の洗い出し: /tmp/CC報告ファイル/local-subagent-guard/scripts-writers.txt の 10 件と、名前で足した 3 件）

**表D 別の AI**: claude・codex（起動された側は新しい本流の会話で agent_id が無く、この見張りの外で書き換えられるため）

設計者の当て試験: 上の判定を Python で書いた試作に §8 K3（49 件）・K4（36 件）を当て、誤りは 0（/tmp/CC報告ファイル/local-subagent-guard/proto-v2.py・proto-v2-out.txt）。試作は判定の確認用で、実装はこの表から作る。

### 5-4. 今のフックとの関係

- 足すのは PreToolUse の 1 項目だけ。worktree-only-guard・review-gate gate.py・agent-danger-hook などの既存の項目は変えない。フックは全部が走り、どれか 1 つが止めれば止まる。
- review-gate の record.py は PostToolUse（SubagentHandback）で動き、Write を使わない（ADR-1029 What 2「記録する」はフックの台本が書く）。審査役の流れは変わらない（G5）。
- 手元の generator・fork・teammate も止まる。~/.claude/agents/generator.md は commit・push・PR 作成を手順にしている（:3・:62・:78・:95）ので、generator はクラウド専用になる（PO の決定「1」と同じ）。generator.md の書き換えはこの便に入れない（別便。止められても stderr の文で本体に返る）。

### 5-5. 導入・戻し方

- install.sh（review-gate/install.sh と同じ型。冪等・バックアップ `~/.claude/settings.json.bak-local-subagent-guard-<時刻>`・一時ファイルに書いて JSON として読めるか確かめてから置き換え）:
  1. guard.py と scripts/agent-hooks/cloud/guard_pre_tool.py を ~/.claude/scripts/local-subagent-guard/ へ写す
  2. 写した元の commit（`git rev-parse HEAD`）と各ファイルの sha256 を同じ場所の `installed-from.txt` に書く
  3. settings.json の PreToolUse に matcher `Write|Edit|MultiEdit|NotebookEdit|Bash|Monitor`、command `python3 ~/.claude/scripts/local-subagent-guard/guard.py`（`~` は展開した絶対パスで書く）の 1 項目を足す。同じ command の項目が既にあれば足さない
- 導入の順番: PR マージ後、本店の写しを main に合わせてから PO が `! bash scripts/agent-hooks/local-subagent-guard/install.sh`（ADR-1011:39）。公式文書では settings.json のフックの変更はファイルの見張りで自動で読み直されるが、K7 は新しい会話でも確かめる
- rollback.sh: settings.json から足した 1 項目（command が一致するもの）だけを消し、~/.claude/scripts/local-subagent-guard/ を消す。バックアップを作ってから行う

### 5-6. 台本の洗い出しの照合（表C の維持）

test_guard.sh は、`git grep -lE 'gh +pr +(create|merge)|git +(push|commit)\b|gh +api .*(-X|--method) *(POST|PUT|PATCH|DELETE)' -- 'scripts/*.sh' 'scripts/*.py' 'scripts/**/*.sh' 'scripts/**/*.py'` から `scripts/agent-hooks/` を除いた一覧の名前が、すべて guard.py の表C に入っているかを確かめ、無ければ失敗する（新しい台本を足した PR で CI が落ちて気づく）。表C にあって一覧に無い名前は失敗にしない（名前で足したもの）。実装時にこの照合が表C の 13 件以外の名前を出したら、実装役は表C に足さずに止まって本体へ返す（足すかどうかは本体が台本の中身を読んで決める）。

## 6. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| 担当の定義（~/.claude/agents/*.md）の tools から Write/Edit を外す | 名前の無い担当（general-purpose・fork）には効かず、定義を変えれば外れる。Bash の git・gh も止められない |
| 担当の model（sonnet）だけ止める | フックの入力に model が無い（recon.md §1） |
| git・gh を「止める一覧」で持つ（第1版） | 一覧に無い書き方（gh secret set・git checkout -- . など）が素通りした（審査の指摘 5・7）。第2版は「読むだけの一覧」以外を止める |
| Bash の書き換え（`>`・`sed -i`）も全部止める | 調べものの結果を /tmp に残す担当の作法（生出力をファイルへ）が壊れる |
| 止めずに記録だけ取る | PO の決定「１」は止めること |

## 7. 受け入れるリスク

- 担当は Bash の命令文でファイルを書き換えられる（`>`・`sed -i`・`python -c` など）。本体と同じ作業場所で動けば、本体の未保存の変更を上書きして消すこともでき、消えた変更は git status に出ない。git の命令での書き換え・消去（checkout・restore・reset・clean・stash など）は表A で止まるので、残るのはシェルでの直接の書き換えだけ。
- 変数で組み立てた命令（`G=git; $G push`）・隠した命令（base64 など）・表C に無い台本の中の書き込みは見抜けない。
- 入力の JSON が読めないときは通す（本体を止めないため）。
- 文字の中の語（`echo "git push"`）でも担当は止まる（誤った止め。担当だけ）。
- 写した guard_pre_tool.py は導入したときの版で固まる。クラウド側が直っても手元は古いまま（§維持の仕組み で install を流し直す）。
- MCP の書き込み道具は止めない（§2 対象外）。

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 担当の Write・Edit・MultiEdit・NotebookEdit が止まる（exit 2・stderr に ADR-1045） | test_guard.sh: agent_id 付きの入力 4 種 |
| K2 本体（agent_id 無し・空文字）の Write と Bash `git commit -m x`・`git push`・`claude -p x` は exit 0 | test_guard.sh |
| K3 担当の次の command（Bash・Monitor の両方で）が止まる: `git commit -m x`・`git -C /a commit`・`git -c a=b push`・`cd /a && git push`・`bash -c 'git push'`・`echo $(git push)`・`git merge x`・`git rebase main`・`git tag v1`・`gh pr create`・`gh pr merge 1`・`gh pr comment 1 -b x`・`gh api -X POST repos/a/b/issues`・`gh api repos/a/b/pulls -f title=x`・`bash scripts/gh-pr-merge-safe.sh --merge`・`bash scripts/gh-pr-create-safe.sh --base main`・`claude -p x`・`codex exec x`・`~/.local/bin/claude -p hi`・`git -P push`・`git -C/a push`・`git --work-tree /a commit`・`git checkout -- .`・`git clean -fd`・`git stash`・`git switch x`・`git branch -D x`・`git branch newb`・`git worktree add /x`・`git restore .`・`git reset --hard`・`git add .`・`gh secret set X`・`gh variable set X`・`gh label create x`・`gh pr update-branch 1`・`gh issue delete 1`・`gh gist create f`・`gh repo sync`・`gh run delete 1`・`gh api graphql -f query='mutation{x}'`・`xargs git push`・`eval "git push"`・`git tag -a v1 -m x`・`git pull`・`git cherry-pick a`・`git config user.name x`・`/usr/bin/git push`・heredoc でコミット文を渡す `git commit -m "$(cat <<EOF …)"`。command が文字列でない入力も止まる | test_guard.sh |
| K4 担当の次の command は exit 0: `git log`・`git status`・`git diff origin/main`・`git -C /a log`・`git fetch`・`gh pr view 1`・`gh pr list`・`gh api repos/a/b/pulls`・`ls`・`cat x`・`grep "git push" f`・`git log --grep "commit"`・`git merge-base origin/main HEAD`・`git merge-tree a b`・`git commit-graph verify`・`git tag -l`・`git tag --contains HEAD`・`gh api graphql -f query='{viewer{login}}'`・`gh api -X GET repos/a/b/pulls -F per_page=100`・`gh api repos/a/b --jq .x \| jq -f x`・`git branch`・`git branch -a`・`git branch --contains HEAD`・`git stash list`・`git worktree list`・`git remote -v`・`git config --get user.name`・`which claude`・`gh pr checks 1`・`git rev-parse HEAD`・`git ls-remote origin`・`git show origin/main:x`・`ls ~/.claude/agents`・`gh auth status`・`git -C /a diff --stat origin/main...HEAD`・`gh run view 1 --log`。Monitor で command が無い入力も exit 0 | test_guard.sh |
| K5 JSON でない入力は exit 0 | test_guard.sh |
| K6 guard_pre_tool.py が読めない置き方（一時ディレクトリに guard.py だけを写す）で、担当の Bash は止まり（規則 import-failed）、本体の Bash は exit 0 | test_guard.sh |
| K7 §5-6 の照合が通る。表C から 1 件消した写しでは失敗する | test_guard.sh |
| K8 install.sh を一時の HOME で 2 回流しても項目は 1 つ。installed-from.txt がある。rollback.sh で項目と写しが消え、他の項目は残る | test_guard.sh（HOME を一時ディレクトリにして流す） |
| K9 CI の agent-hooks-test で test_guard.sh が緑 | PR の checks |
| K10 実地: 導入後の新しい会話で、手元の担当（general-purpose・model sonnet）に /tmp の試しのファイルへの Write と、作業場所での `git commit --allow-empty -m test` を頼むと両方止まる。本体の Write は通る | 本体が会話で試し、結果を記録 |
| K11 実地: 審査役（reviewer・model opus）の審査 → VERDICT の記録 → マージの流れが 1 回通る | 次の PR のマージで確かめる |

## 9. 作業の分け方

- 便1（この設計の PR に実装も足す）: クラウドの Sonnet が §5-1 のファイルを作り、test_guard.sh を流して push。本体が審査役の審査 → マージ。PO が `!` で install.sh。本体が K10・K11 を確かめる
- 別便（後日・入れるかは導入後に決める）: ~/.claude/agents/generator.md の手順をクラウド前提に書き直す

## 維持の仕組み

- scripts/agent-hooks/** が変わる PR で CI（agent-hooks-test）が試験を流す。新しい台本が GitHub へ書くようになれば §5-6 の照合で CI が落ちる。
- guard.py・scripts/agent-hooks/cloud/guard_pre_tool.py が main で変わったら、本体が PO に install.sh の流し直しを頼む（installed-from.txt の commit・sha256 と main を比べて気づく）。
- 止めた件数は guard.log。導入後 1 週の件数（K-c）を見て、週次の権限点検（ADR-1034）に足すかを決める。

## 10. 外部・過去事例の参照と我々への応用

外部事例は該当なし。Claude Code のフックで担当だけを止める公開の事例は探していない。根拠は公式文書の仕様（recon.md §1）と、この Mac の実際の記録（recon.md §2）で足りるため。過去事例として社内の ADR-1029（review-gate）を参照し、install・rollback・CI の型と、agent_id で担当を見分けるやり方（~/.claude/scripts/subagent-bash-wait-guard.py:37）をそのまま使う。第1版の審査で「止める一覧」の作りが漏れを生むと分かったので、第2版は「読むだけの一覧」の作りに改めた。
