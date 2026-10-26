# design — 手元の担当（サブエージェント）の書き換え・保存・送り出しをフックで止める

- 状態: 設計案（第3版 2026-10-26）。
  - 第1版は審査役（reviewer・opus）が REQUEST_CHANGES（指摘 1〜12）。第2版で反映した。
  - 第2版（026ab0a25）も REQUEST_CHANGES（指摘 A〜I、/tmp/CC報告ファイル/local-subagent-guard/review-2.md）。第3版で反映した。
  - 第1版の審査の文は会話の中にだけあり、ファイルには残していない。要点は §11 にまとめた。
- 関連: [recon.md](recon.md)・[cases.md](cases.md)（判定の例の正本）・[ADR-1045](../../adr/ADR-1045-local-subagent-write-guard.md)・ADR-1029（前例）・ADR-1011:39（フックは AI がパッチを書き、PO が `!` で反映する）
- PO の決定（2026-10-26）:
  - 「1」重い実装と試験はクラウドで行う。手元の担当は、Mac の中を見る短い調べものだけにする。
  - 「１」その決まりを仕組みで守らせるため、手元の担当の書き換え・保存・GitHub への上げを全部止める。

## 1. あるべき姿

- 手元の Mac で Opus 本体が呼び出した担当は、読む・数える・一覧を見ることだけができる。担当の model は Sonnet でも Opus でも同じ。fork とチーム機能の仲間（teammate）も同じ扱いにする。
- 担当にできないこと:
  - ファイルを書き換える道具を使う。作業場所を作る道具を使う。
  - git の作業場所や履歴を変える。GitHub へ書き込む。
  - 台本（シェル・Python・Node などのファイル）を動かす。
  - 別の AI を起動して、代わりにやらせる。
- 破ろうとするとフックが止め、「調べた結果を本体に返してください」と表示する。
- Opus 本体とクラウドの作業は、今までどおり。

## 2. KGI（PO の決定「１」から決めた成功条件。○×で判定する）

| # | 成功条件 |
|---|---|
| G1 | 手元の担当が Write・Edit・MultiEdit・NotebookEdit・EnterWorktree・ExitWorktree を使おうとすると止まる |
| G2 | 手元の担当が Bash・Monitor で次のことをしようとすると止まる（§5-3）。①git・gh の、読むだけの一覧（表A・表B）に無い使い方 ②台本の実行（表C） ③別の AI の起動（表D） |
| G3 | Opus 本体が同じ操作をしても止まらない |
| G4 | 手元の担当の読むだけの命令は止まらない（[cases.md](cases.md) の通す例） |
| G5 | マージの関所の流れが今までどおり回る。審査役が gh pr view・git diff で読み、VERDICT を返し、それが記録され、本体がマージする |
| G6 | 試験の台本がリポジトリにあり、CI で自動で流れる |

対象外:

- 担当が、台本を使わずに Bash の命令文でファイルを書き換えること（`>`・`sed -i`・`tee`・`python3 -c` など）は止めない（§7）。
- MCP の書き込み道具は止めない。例: Artifact の公開・Gmail の送信・Google Drive・Figma・Canva への書き込み。PO の決定の範囲（ファイル・git・GitHub）の外にあるため。
- クラウドの見張り（scripts/agent-hooks/cloud/）は変えない。

## 3. KPI

| # | 指標 | 数え方 |
|---|---|---|
| K-a | 導入後、手元の担当の Write/Edit/MultiEdit/NotebookEdit が通った件数 = 0 | 本体が、agent-console の活動記録の PostToolUse から agent_id 付きの行を数える |
| K-b | 導入後、本体の操作が止められた件数 = 0 | guard.log には担当のときだけ行が書かれるので、本体の止めは仕組み上起きない |
| K-c | 導入後 1 週の guard.log の件数と、規則ごとの内訳 | 誤った止めがあれば表A・表B・表C を直す |

## 4. recon の要点（詳細は recon.md）

- 見分け方
  - 担当の呼び出しには agent_id が入り、本体の呼び出しには入らない（recon.md §1・§2）。
  - 根拠は公式文書と、この Mac の実際の記録の件数（Edit 担当 49・本体 131、Write 担当 54・本体 51）。
  - 公式文書には「the subagent or in-process teammate」とあるので、teammate も止まる。
  - フックの入力には model が入らないので、model ではなく agent_id の有無で分ける。
- 審査役が書き込みをしなくても、マージの関所は回る（recon.md §3）。
  - 関所は VERDICT の行の記録（PostToolUse の SubagentHandback）で決まる。
  - reviewer.md:66・:80-81 は `gh pr review` での投稿を手順にしているが、実際には使われていない。最近の PR #4787・#4785 は、どちらも reviews が空だった（/tmp/CC報告ファイル/local-subagent-guard/v3-recon.txt）。
- 前例
  - review-gate の、install・rollback・CI の型（recon.md §5）。
- 命令文の読み方
  - クラウドの guard_pre_tool.py の scan_text と embedded_commands を使い回す（recon.md §5）。

## 5. design

### 5-1. 置くもの（リポジトリ）

| ファイル | 役割 |
|---|---|
| scripts/agent-hooks/local-subagent-guard/guard.py | PreToolUse のフック。matcher は `Write\|Edit\|MultiEdit\|NotebookEdit\|EnterWorktree\|ExitWorktree\|Bash\|Monitor`。§5-2・§5-3 の判定をする |
| scripts/agent-hooks/local-subagent-guard/test_guard.sh | 試験。偽の入力 JSON で §8 の全行を確かめる。本物の ~/.claude には触れない |
| scripts/agent-hooks/local-subagent-guard/install.sh | PO が `!` で実行する（§5-5） |
| scripts/agent-hooks/local-subagent-guard/rollback.sh | PO が `!` で実行する（§5-5） |
| .github/workflows/agent-hooks-test.yml | job を 1 つ足し、`bash scripts/agent-hooks/local-subagent-guard/test_guard.sh` を流す。既存の review-gate の job は変えない。paths は既存の `scripts/agent-hooks/**` で足りる（§5-6） |
| docs/adr/ADR-1045-local-subagent-write-guard.md・docs/adr/README.md | ADR と索引。索引は `node scripts/generate-adr-index.js` で作る |

使うのは Python 3 の標準ライブラリだけ。

### 5-2. guard.py の判定（上から順に見て、最初に当たったものに従う）

1. 標準入力が JSON の辞書として読めない → 何もせず exit 0。本体か担当か分からないので、本体を止めない側に倒す（§7）。
2. `agent_id` が無いか、空文字 → exit 0（Opus 本体）。
3. `tool_name` が Write・Edit・MultiEdit・NotebookEdit・EnterWorktree・ExitWorktree → 止める（規則名 `tool`）。
4. `tool_name` が Bash か Monitor:
   - `tool_input.command` が無い → exit 0（Monitor で command を使わない呼び方）。
   - `tool_input.command` が文字列でない → 止める（規則名 `command-not-string`）。
   - guard_pre_tool の読み込みに失敗していた → 止める（規則名 `import-failed`）。本体は手順 2 で先に通っている。
   - それ以外 → §5-3 で判定する。当たれば止め、当たらなければ exit 0。
5. それ以外の道具 → exit 0。

guard_pre_tool の読み込み:

- 手順:
  1. `sys.path.insert(0, <guard.py のディレクトリ>)` を行う。
  2. そこに guard_pre_tool.py が無ければ、`<guard.py のディレクトリ>/../cloud` も足す。導入後は同じディレクトリにあり、リポジトリでは ../cloud にあるため。
  3. `import guard_pre_tool` を行う。
- 失敗したとき:
  - 例外を捕まえて覚えておき、手順 4 で使う。
  - 読み込みに失敗しても本体を止めないため、手順 1・2 より前には判断しない。
- settings.json に書く命令:
  - `python3 -I <絶対パス>` にする。`-I` で外の PYTHONPATH と今いるディレクトリの影響を消し、読み込み先は上の明示の insert で足す。
  - test_guard.sh で、`-I` を付けた起動で import できることを確かめる（K6）。

止めるときの出し方:

- exit 2 で終わり、stderr に次の 1 行を出す。agent_type が無ければ「名前なし」と書く。

  `手元の担当（<agent_type>）は、ファイルの書き換え・git の作業場所や履歴の変更・GitHub への書き込み・台本の実行・別の AI の起動をしません（ADR-1045・規則 <規則名>）。調べた結果を本体に返してください。書き換えが要る作業はクラウドで行います。`

- 止めたときだけ、`~/.claude/scripts/local-subagent-guard/guard.log` に 1 行足す（UTC の時刻・agent_type・tool_name・規則名）。
  - 命令文そのものは書かない。秘密が混じることがあるため。
  - log に書けなくても、止めることは変えない。

### 5-3. Bash・Monitor の命令の判定

**前処理**

1. 見る文の一覧を作る。
   - 一覧は、元の command と、`guard_pre_tool.embedded_commands(command)` の各要素。
   - embedded_commands が返すのは、命令の中に埋め込まれた命令の中身。対象は `$( )`・逆引用符・`( )` の殻・`bash/sh/zsh/dash -c`・eval。
   - 要素に `guard_pre_tool.TOO_DEEP` があれば、止める（規則 `too-deep`）。
2. 一覧の文を 1 つずつ見る。
   1. `s = guard_pre_tool.scan_text(文)` を求める。
      - scan_text は、ファイルへ書くだけの heredoc の本文と、読むだけの区間（grep など）を消す。
      - git commit・gh pr・gh issue の区間では、引用符の中身を消す。そこにあった `$( )` は、手順 1 の埋め込みとして見る。
   2. `s` を `&&`・`||`・`;`・`|`・`&`・改行で区間に分ける。
3. 区間ごとに、語に分ける。
   - `shlex.split(区間, posix=True)` で分ける。引用符を外して 1 語にし、`"$WT"`・`${WT}` も 1 語になる。
   - shlex が例外を出したら（引用符の閉じ忘れなど）、`"` と `'` を消してから空白で分ける。
   - 語の「名前」は、最後の `/` より後ろの部分（例: `/usr/bin/git` → `git`）。

**頭の語**: 区間の先頭から、次の語を読み飛ばした後の最初の語。

- 変数の代入（`A=1`）
- 前置きの語: env・nohup・time・exec・nice・timeout・xargs・stdbuf・caffeinate・command・then・do・else・if・while・until・`!`
- 前置きの語の後ろにある、`-` で始まる語・代入・数字（`10`・`5s`）

**調べるだけの区間**: 先頭の語（代入を除く）の名前が次のどれかなら、その区間は以下の判定をしない。

- ls・file・stat・which・du・pgrep・ps・realpath・readlink・basename・dirname・wc・echo・printf・type
- `command` で、その次の語が `-v`・`-V` のとき

**区間の判定**: 次のどれかに当たれば止める。

1. 頭の語の名前が sudo・su・doas → 規則 `sudo`。
2. 表C（台本の実行）に当たる → 規則 `script`。
3. 語のどれかの名前が claude か codex である。または、語に `@anthropic-ai/claude-code`・`@openai/codex` が含まれる（表D） → 規則 `agent`。
4. 語のどれかの名前が `git` である → その後ろの語を表A で判定する。読むだけでなければ規則 `git-<動詞>`。
5. 語のどれかの名前が `gh` である → その後ろの語を表B で判定する。読むだけでなければ規則 `gh-<語>`。

**表A git**

- 読み飛ばし:
  - `git` の後ろで、`-` で始まる語を選択肢として飛ばす。
  - `-C`・`-c`・`--git-dir`・`--work-tree`・`--namespace`・`--config-env`・`--super-prefix` のちょうどその語のときは、次の 1 語も飛ばす。
  - `-C/a`・`--git-dir=/a`・`-P`・`--no-pager` は 1 語として扱う。
- 飛ばした後に語が無ければ止める（規則 `git-noverb`）。

| 動詞 | 判定 |
|---|---|
| log・status・diff・show・ls-remote・ls-files・ls-tree・rev-parse・rev-list・merge-base・merge-tree・blame・grep・describe・shortlog・cat-file・for-each-ref・show-ref・name-rev・range-diff・cherry・whatchanged・count-objects・version・help・var・check-ignore・check-attr・verify-commit・verify-tag・fsck・diff-tree・diff-index・diff-files | 通す |
| fetch | `-` で始まらない後ろの語に `:` を含むもの（`+HEAD:refs/heads/main`・`main:main`）があれば止める。無ければ通す |
| stash | 次の語が list・show なら通す |
| worktree | 次の語が list なら通す |
| notes | 次の語が list・show なら通す |
| commit-graph | 次の語が verify なら通す |
| submodule | 次の語が status なら通す |
| reflog | 次の語が無いか、show・exists か、`-` で始まる語なら通す |
| remote | 次の語が無いか、-v・--verbose・show・get-url なら通す |
| config | 後ろに --get・--get-all・--get-regexp・--list・-l・--get-urlmatch・get・list のどれかがあれば通す |
| symbolic-ref | -d・--delete があれば止める。それ以外は、`-` で始まらない語が 1 つ以下なら通す |
| branch | ① 後ろの語（`=` の前）に、書き込みの選択肢 -d・-D・-m・-M・-c・-C・-f・--delete・--move・--copy・--force・-u・--set-upstream-to・--unset-upstream・--edit-description・--track・-t・--create-reflog があれば止める。② `-` で始まらない語があり、一覧の選択肢 -l・--list・--contains・--no-contains・--merged・--no-merged・--points-at・--all・--remotes・--verbose・--show-current・-n・-v・--verify がどれも無ければ止める（枝を作る形）。③ それ以外は通す |
| tag | branch の書き込みの選択肢に -a・--annotate・-s・--sign・-F・--file を足して、同じ判定をする（-v は一覧の選択肢の側） |
| 上に無い動詞（commit・push・merge・rebase・cherry-pick・revert・am・pull・checkout・switch・restore・reset・clean・add・rm・mv・apply・init・clone・update-ref・gc・prune・別名（alias）など全部） | 止める |

**表B gh**

- 読み飛ばし:
  - `gh` の後ろと、第 1 語の後ろで、`-` で始まる語を飛ばす。
  - `-R`・`--repo` のときは、次の 1 語も飛ばす。
  - `--version` は飛ばさずに第 1 語として扱う。
- 飛ばした後に語が無ければ止める（規則 `gh-noverb`）。

| 第 1 語 | 通す第 2 語 |
|---|---|
| pr | view・list・checks・diff・status（review・comment・create・merge・edit などは止める） |
| issue | view・list・status |
| run | view・list・watch |
| repo | view |
| release・workflow | view・list |
| auth | status |
| label・secret・cache・extension・alias | list |
| variable・config | list・get |
| gist | view・list |
| ruleset | list・view・check |
| search・status・help・version・--version | 第 2 語を問わず通す |
| 上に無い第 1 語（拡張・別名を含む） | 止める |

gh api は、後ろの語を見て次の順に判定する。

1. `-X`・`--method` がある（`-XPOST`・`-X=POST`・`--method=post` の形も含む） → 値が GET（大文字小文字は問わない）なら通す。それ以外は止める。
2. 値つきの選択肢 `-f`・`-F`・`--field`・`--raw-field`・`--input`（`=` 付きも含む）を集める。
3. `graphql` の語がある → 次のどれかに当たれば止め、どれにも当たらなければ通す。
   - 元の command 全体に語 `mutation` がある。
   - 集めた値（`=` の後ろ）が `@` で始まる（ファイルから読む形）。
   - `--input` がある。
4. それ以外 → 集めた値があれば止め（gh は値を付けると POST にするため）、無ければ通す。

区間ごとに見るので、`gh api … | jq -f x` の jq の `-f` には当たらない。

**表C 台本の実行**（区間ごとに判定する）

- 頭の語に `/` が含まれる（例: `./scripts/dev/executor-preflight.sh`・`scripts/dev/executor-preflight.sh`・個人の記録帳の save 台本の絶対パス）→ 止める。
  - ただし、次の場所で始まる語は除く: `/bin/`・`/usr/bin/`・`/usr/sbin/`・`/sbin/`・`/opt/homebrew/bin/`・`/usr/local/bin/`。
  - 名前が git・gh・claude・codex のときも除く。これらは表A・表B・表D で判定する。
- 頭の語の名前が npx・bunx・make・just・task・rake・invoke → 止める。
- 頭の語の名前が npm・pnpm・yarn → 止める。ただし次のときは通す。
  - `-` で始まらない最初の語が ls・list・view・info・outdated・why のとき。
  - `-v`・`--version` があるとき。
- 区間の語のどれかの名前が、次の解釈系に当たる → その後ろの、`-` で始まる語を飛ばして最初の語を見る（`-c`・`-e`・`--eval`・`-m`・`-` は飛ばさない）。
  - 解釈系: bash・sh・zsh・dash・ksh・fish・python・python2/3（`python3.12` も含む）・pypy・node・deno・bun・tsx・ts-node・ruby・perl・php・osascript
  - 最初の語が無い → 通す。
  - `-c`・`-e`・`--eval`・`-`（標準入力）→ 通す。中身は前処理 1 の埋め込みとして判定される。
  - `-m json.tool` → 通す。
  - それ以外（台本ファイル・その他の `-m`）→ 止める。
- 台本の名前の一覧は持たない。どの台本が GitHub へ書くかに関係なく、担当は台本を動かさない。そのため、新しい台本を足しても見張りを直す必要が無い。

**表D 別の AI**: claude・codex と、npm のパッケージ `@anthropic-ai/claude-code`・`@openai/codex`。起動された側は新しい本流の会話になり、agent_id が無いので、この見張りの外で書き換えられるため止める。

**設計者の当て試験**

- 上の判定を Python で書いた試作に、[cases.md](cases.md) の止める例 101・通す例 74 を当てた。誤りは 0。
- 試作: /tmp/CC報告ファイル/local-subagent-guard/proto-v3-judge.py
- 結果: proto-v3-out.txt
- 試作は判定を確かめるためのもので、実装はこの節の表から作る。

### 5-4. 今のフックと、担当の定義との関係

- フック
  - 足すのは PreToolUse の 1 項目だけ。既存の項目（worktree-only-guard・review-gate の gate.py・agent-danger-hook など）は変えない。
  - フックは全部が走り、どれか 1 つが止めれば止まる。
- 審査役（reviewer）
  - 審査役の `gh pr review` は止まる。それでもマージの関所は回る。
    - 関所は、審査役の返事の VERDICT の行を、review-gate の record.py（PostToolUse の SubagentHandback）が記録することで成り立つ（ADR-1029）。gh pr review の投稿は使っていない。
    - 実際に最近の PR #4787・#4785 は reviews が空だった（v3-recon.txt）。
  - 審査役は止められると、stderr の文を見て、VERDICT の行を返事に書いて終わる。
- 評価役（evaluator）・統治役（governance）
  - 評価役（evaluator.md:62-63）と統治役（governance.md:165）の `gh pr review` も止まる。
  - この 2 つの役の結果も、返事の文として本体が受け取る。
- 実装役（generator）
  - 手元の generator・fork・teammate も止まる。
  - ~/.claude/agents/generator.md は、commit・push・PR 作成を手順にしている（:3・:62・:78・:95）。
  - そのため generator はクラウド専用になる（PO の決定「1」と同じ）。
- 担当の定義の書き換え
  - reviewer.md・evaluator.md・governance.md・generator.md の手順の書き換えは、この便に入れない（別便）。
  - 止められても、stderr の文で本体に返るため。
- 着手前点検
  - 担当は着手前点検（scripts/dev/executor-preflight.sh）も動かせない。
  - この台本は gh auth switch（:39）と git config user.name の設定（:58）で書き込むので、読むだけではない。
  - 点検は本体が行う。

### 5-5. 導入・戻し方

- install.sh は review-gate/install.sh と同じ型にする（冪等。バックアップを `~/.claude/settings.json.bak-local-subagent-guard-<時刻>` に作る。一時ファイルに書いて JSON として読めるか確かめてから置き換える）。手順:
  1. guard.py と scripts/agent-hooks/cloud/guard_pre_tool.py を、~/.claude/scripts/local-subagent-guard/ へ写す。
  2. 写した元の commit（`git rev-parse HEAD`）と、各ファイルの sha256 を、同じ場所の `installed-from.txt` に書く。
  3. settings.json の PreToolUse に 1 項目を足す。
     - matcher は §5-1 のもの。
     - command は `python3 -I <~ を展開した絶対パス>/.claude/scripts/local-subagent-guard/guard.py`。
     - 同じ command の項目が既にあれば足さない。
- 導入の順番
  1. PR をマージする。
  2. 本店の写しを main に合わせる。
  3. PO が `! bash scripts/agent-hooks/local-subagent-guard/install.sh` を実行する（ADR-1011:39）。
  - 公式文書では、settings.json のフックの変更は、ファイルの見張りで自動で読み直される。それでも K10 は新しい会話でも確かめる。
- rollback.sh
  - バックアップを作ってから行う。
  - settings.json から、足した 1 項目（command が一致するもの）だけを消す。
  - ~/.claude/scripts/local-subagent-guard/ を消す。

### 5-6. CI で流れる範囲

- 第2版は台本の名前の一覧（表C）を持ち、scripts/ を洗い出して照らしていた。しかし、式が狭いことと、scripts/ の変更では CI が走らないことが審査で指摘された（指摘 D）。
- 第3版は台本の実行を名前によらず止めるので、名前の一覧も洗い出しも要らない。
- 見張りの判定が変わるのは scripts/agent-hooks/** が変わったときだけなので、CI の paths は既存のままで足りる。
- 参考: 判定の試作で scripts/ 218 ファイルを 1 行ずつ調べると、30 ファイルに当たった。その中には説明の文や試験の作り物も多く、一覧で保つのは難しいと分かった（/tmp/CC報告ファイル/local-subagent-guard/scan-v3.txt）。

## 6. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| 担当の定義（~/.claude/agents/*.md）の tools から Write/Edit を外す | 名前の無い担当（general-purpose・fork）には効かない。定義を変えれば外れる。Bash の git・gh も止められない |
| 担当の model（sonnet）だけ止める | フックの入力に model が無い（recon.md §1） |
| git・gh を「止める一覧」で持つ（第1版） | 一覧に無い書き方（gh secret set・git checkout -- . など）が素通りした（指摘 5・7） |
| GitHub へ書く台本を名前の一覧で持つ（第2版） | 洗い出しの式が狭く、新しい台本を足しても CI で気づけなかった（指摘 D） |
| 区切りに引用符・`{}`・`()` を使う（第2版） | `git -C "$WT" commit` などの普段の書き方が素通りした（指摘 A）。第3版は shlex で語に分ける |
| Bash の書き換え（`>`・`sed -i`）も全部止める | 担当の作法（調べものの生の出力を /tmp に残す）が壊れる |
| 止めずに記録だけ取る | PO の決定「１」は止めること |

## 7. 受け入れるリスク

- シェルでの直接の書き換え
  - 担当は、Bash の命令文でファイルを書き換えられる（`>`・`sed -i` など）。
  - 本体と同じ作業場所で動けば、本体の未保存の変更を上書きして消せる。消えた変更は git status に出ない。
  - git の命令での書き換えや消去（checkout・restore・reset・clean・stash など）は表A で止まるので、残るのはシェルでの直接の書き換えだけ。
- 解釈系の中で書いた命令
  - `python3 -c`・`node -e`・`python3 -` の中で、ライブラリや subprocess の配列（`["git","push"]`）を使って書き込む形は見抜けない。
  - 担当の数え作業（Python で数える）を止めないため、受け入れる。
- 変数で組み立てた命令（`G=git; $G push`）と、隠した命令（base64 など）は見抜けない。
- GNU sed の `e` 命令（`sed -n "1e git push"`）は見抜けない。
  - scan_text は sed -n を読むだけの区間として消す。
  - Mac の標準の sed は BSD 版で、`e` 命令が無い。GNU sed を入れたときだけ起きうる。
- 入力の JSON が読めないときは通す（本体を止めないため）。
- 担当だけに起きる誤った止め
  - 文字の中の語（`echo` 以外の命令の引数にある `git push` など）。
  - 名前が git の道（`cd ~/x/git`）。
- 写した guard_pre_tool.py は、導入したときの版のまま固まる。クラウド側が直っても、手元は古いまま（「維持の仕組み」で install を流し直す）。
- MCP の書き込み道具は止めない（§2 の対象外）。

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 担当の Write・Edit・MultiEdit・NotebookEdit・EnterWorktree・ExitWorktree が止まる（exit 2、stderr に ADR-1045 と規則 tool） | test_guard.sh: agent_id 付きの入力 6 種 |
| K2 本体（agent_id が無い・空文字）は止まらない（exit 0）。対象は Write と、Bash の `git commit -m x`・`git push`・`claude -p x`・`bash scripts/dev/executor-preflight.sh` | test_guard.sh |
| K3 担当の、[cases.md](cases.md) の止める例が全部止まる（Bash・Monitor の両方）。command が文字列でない入力も止まる | test_guard.sh（cases.md の例を全部、試験に入れる） |
| K4 担当の、cases.md の通す例が全部 exit 0（Bash・Monitor の両方）。Monitor で command が無い入力も exit 0 | test_guard.sh |
| K5 JSON でない入力は exit 0 | test_guard.sh |
| K6 import の確認。① `python3 -I` で、リポジトリの置き方（../cloud）でも、導入後の置き方（同じディレクトリ）でも読み込める ② guard_pre_tool.py が読めない置き方（一時ディレクトリに guard.py だけを写す）では、担当の Bash は止まり（規則 import-failed）、本体の Bash は exit 0 | test_guard.sh |
| K7 止めたとき guard.log に 1 行が足され、命令文は含まれない | test_guard.sh（HOME を一時ディレクトリにする） |
| K8 install.sh を一時の HOME で 2 回流しても、項目は 1 つ。installed-from.txt がある。rollback.sh で項目と写しが消え、他の項目は残る | test_guard.sh（HOME を一時ディレクトリにして流す） |
| K9 CI の agent-hooks-test で test_guard.sh が緑 | PR の checks |
| K10 実地: 導入後の新しい会話で、手元の担当（general-purpose・model sonnet）に次の 3 つを頼むと、全部止まる。① /tmp の試しのファイルへの Write ② 作業場所での `git commit --allow-empty -m test` ③ `bash scripts/dev/executor-preflight.sh`。本体の Write は通る | 本体が会話で試し、結果を記録する |
| K11 実地: 審査役（reviewer・model opus）の審査 → VERDICT の記録 → マージの流れが 1 回通る。審査役が gh pr review を試みて止められても、VERDICT の行は記録される | 次の PR のマージで確かめる |

## 9. 作業の分け方

- 便1（この設計の PR に実装も足す）
  1. クラウドの Sonnet が §5-1 のファイルを作り、test_guard.sh を流して push する。
  2. 本体が審査役の審査を通してからマージする。
  3. PO が `!` で install.sh を実行する。
  4. 本体が K10・K11 を確かめる。
- 別便（後日。入れるかは導入後に決める）
  - reviewer.md・evaluator.md・governance.md・generator.md の手順を、「手元では書き込まない」前提に書き直す。

## 維持の仕組み

- CI
  - scripts/agent-hooks/** が変わる PR では、CI（agent-hooks-test）が試験を流す。
  - 判定の例は cases.md を正本にし、試験と合わせて足す。
- install の流し直し
  - guard.py か scripts/agent-hooks/cloud/guard_pre_tool.py が main で変わったら、本体が PO に install.sh の流し直しを頼む。
  - 気づき方: installed-from.txt の commit・sha256 と main を比べる。
- 止めた件数
  - 件数は guard.log に残る。
  - 導入後 1 週の件数（K-c）を見て、週次の権限点検（ADR-1034）に足すかを決める。

## 10. 外部・過去事例の参照と我々への応用

- 外部事例
  - 該当なし。Claude Code のフックで担当だけを止める公開の事例は探していない。
  - 根拠は、公式文書の仕様（recon.md §1）と、この Mac の実際の記録（recon.md §2）で足りるため。
- 過去事例（社内）
  - ADR-1029（review-gate）を参照した。install・rollback・CI の型をそのまま使う。
  - agent_id で担当を見分けるやり方は、~/.claude/scripts/subagent-bash-wait-guard.py:37 と同じ。
- 審査から学んだこと
  - 「止める一覧」や「台本の名前の一覧」で守ると、漏れが出る（第1版・第2版の審査）。
  - 第3版は、「読むだけの一覧」と「台本は名前によらず動かさない」の形に改めた。

## 11. 審査の経緯（要点）

- 第1版（24e7be05b）の指摘
  1. PR を作る台本が止まらない
  2. claude・codex の起動で外に出られる
  3. Monitor
  4. 読むだけの命令の誤った止め
  5. 止める一覧の形では漏れる
  6. graphql・`-X GET`・jq `-f` の誤った止め
  7. 本体の未保存の作業を消す git の命令
  8. import の場所と失敗時
  9. generator はクラウド専用
  10. `git -P`・`-C/a`
  11. 写しが古くなる
  12. MCP は対象外
- 第2版（026ab0a25）の指摘
  - A 引用符などで区切るため、普段の書き方が素通りする
  - B gh pr の区間の `$( )` が消える
  - C 審査役などの gh pr review が止まる
  - D 台本の一覧の照合が足りない
  - E `command claude`・npx
  - F こまかい誤った止めと素通り
  - G `-I` の理由
  - H 誤記と審査記録のありか
  - I EnterWorktree・ExitWorktree
- 第3版での直し
  - A: shlex で語に分ける（§5-3 前処理 3）
  - B: embedded_commands で埋め込みの中も見る（前処理 1）
  - C: 関所が回る根拠を §4・§5-4 に書き、K11 を足した
  - D: 台本は名前によらず止める（表C・§5-6）
  - E: `command` は `-v`・`-V` のときだけ調べる区間とし、パッケージ名も表D に入れた
  - F: 表A・表B の各行
  - G: `-I` を付ける（§5-2）
  - H: この節と状態欄。gh api の `-X` の書き方
  - I: matcher と G1
