# design — 手元の担当（サブエージェント）の書き換え・保存・送り出しをフックで止める

- 状態: 設計案（第6版 2026-10-26）。
  - 第1版は審査役（reviewer・opus）が REQUEST_CHANGES（指摘 1〜12）。第2版で反映した。
  - 第2版（026ab0a25）も REQUEST_CHANGES（指摘 A〜I、/tmp/CC報告ファイル/local-subagent-guard/review-2.md）。第3版で反映した。
  - 第3版（4abf275ae）も REQUEST_CHANGES（A〜I は直ったが、台本を流し込む形の素通りと、grep などの誤った止めが残った。/tmp/CC報告ファイル/local-subagent-guard/review-3.md）。第4版で反映した。
  - 第4版（101b154bf）も REQUEST_CHANGES（3-1〜4 は直ったが、注釈 `#` のあとの行が判定されないなど、普段の書き方の抜けが残った。/tmp/CC報告ファイル/local-subagent-guard/review-4.md）。第5版で反映した。
  - 第5版（3e61daa71）も REQUEST_CHANGES（R1〜R6 は直ったが、gemini の起動と、引用符の無い heredoc の本文の `$( )` が判定されない。/tmp/CC報告ファイル/local-subagent-guard/review-5.md）。第6版で反映した。
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
| K-b | 導入後、本体の操作がこの見張りに止められた件数 = 0 | 試験は K2。実地では、本体の道具の結果に「ADR-1045」の文が出たら、本体がその場で記録する |
| K-c | 導入後 1 週の ~/.claude/logs/local-subagent-guard.log の件数と、規則ごとの内訳 | 誤った止めがあれば表A・表B・表C を直す |

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
  - クラウドの guard_pre_tool.py の embedded_commands・TOO_DEEP・heredoc の式を使い回す（recon.md §5）。scan_text は引用符を気にせずに割るので使わない（§6）。

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

- 止めたときだけ、`~/.claude/logs/local-subagent-guard.log`（rollback でも消さない） に 1 行足す（UTC の時刻・agent_type・tool_name・規則名）。
  - 命令文そのものは書かない。秘密が混じることがあるため。
  - log に書けなくても、止めることは変えない。

### 5-3. Bash・Monitor の命令の判定

**前処理**

1. 見る文の一覧を作る。
   - 一覧は、元の command と、`guard_pre_tool.embedded_commands(command)` の各要素。
   - embedded_commands が返すのは、命令の中に埋め込まれた命令の中身。対象は `$( )`・逆引用符・`( )` の殻・`bash/sh/zsh/dash -c`・eval（guard_pre_tool.py:331-352）。パイプや `<` で解釈系に渡す中身は対象外なので、表C で扱う。
   - 要素に `guard_pre_tool.TOO_DEEP` があれば、止める（規則 `too-deep`）。
2. 一覧の文を 1 つずつ見る。
   1. heredoc（`<<EOF` 〜 `EOF`）の本文を扱う。
      - `<<` のある行（`<<` の前と後ろの両方。例: `cat <<EOF > /tmp/x.sh; bash /tmp/x.sh`）に、シェル（bash・sh・zsh・dash・ksh・fish）か eval・source・`.` の語があるときは、本文を残す（本文は命令として判定する）。
      - それ以外（`python3 <<EOF`・`cat > f <<EOF`・`git commit -F - <<EOF` など）は本文を消す。Python などの本文はシェルの命令ではないため。
      - 本文の見つけ方は guard_pre_tool.py:46 と同じ正規表現 `(<<-?\s*['"]?(\w+)['"]?[^\n]*\n).*?\n\s*\2\b` を使う。見つける前に、行の続き（`\` と改行）を空白 1 つにする（`bash \` の次の行の `<<EOF` のため）。
      - 印に引用符が無い heredoc（`<<EOF`。`<<'EOF'`・`<<"EOF"` ではない）の本文では、bash が `$( )` と逆引用符を実行する。そのため本文を消すときも、本文に `guard_pre_tool.embedded_commands` を当てて取り出した中身を、前処理 1 の一覧に足す（`cat > /tmp/n.txt <<EOF` の本文の `$(git push)` は止まる。`<<'EOF'` の本文は文字のままなので見ない）。
      - 第3版の scan_text は使わない。scan_text は引用符を気にせずに `|`・`;` で割るため（guard_pre_tool.py:70）、grep の正規表現の `\|` などで誤って止めていた（第3版の審査 3-2）。
   2. 文を語と区切りに分ける。
      - 先に次の 3 つを直す。
        - 行の続き（`\` と改行）を空白 1 つにする（`git \` の次の行の `push` のため）。
        - `$'` を `'` に、`$"` を `"` にする（`$'git' push` のため）。
        - 注釈を捨てる。引用符の外で、語の頭（文の頭か、空白・改行・`;&|(<>` の直後。`)` の直後は語の続きなので含めない。`$(pwd)#` の `#` は文字）にある `#` から、改行の手前までを捨てる。改行は残す。語の途中の `#`（`a#b`・`--format=%h#%s`）と引用符の中の `#` は文字のまま。bash と同じ扱い。
      - `shlex.shlex(文, posix=True, punctuation_chars=";&|<>()\n")` に、`whitespace = " \t\r"`（改行は区切りとして残す）・`whitespace_split = True`・`commenters = ""` を設定して使う。`commenters` を空にしないと、shlex は `#` から改行までを改行ごと読み捨て、次の行が前の区間に混ざる（第4版の審査 R1）。
      - 引用符の中は 1 語のままで、区切りとして扱わない。`"$WT"`・`${WT}` も 1 語になる。
      - shlex が例外を出したら（引用符の閉じ忘れなど）、`"` と `'` を消してから同じ方法で分け直す。
   3. 区切りの語を見て、区間に分ける。
      - `(` を含み、`<` か `>` も含む語（`<(`・`>(`。中で命令を動かす形）は区切り。`>(` のとき、次の区間は「パイプの後ろ」とする（`tee >(bash)` のため）。
      - `;`・`&`・`|`・`\n`・`(`・`)` だけでできた語は区切り。区切りに `|`（`||` を除く）を含むとき、次の区間は「パイプの後ろ」とする。
      - `<<<` の次の語は「文字の入力」として覚え、その語を命令として判定する（`bash <<< "git push"` のため）。
      - `<<`・`<<-` の次の語（heredoc の印）は捨て、区間に「heredoc あり」と覚える。
      - この 2-3 の決まりは語の順に 1 つずつ当てる。`(` を含む語の決まりは、下の `<`・`>` の決まりより先に当たる。
      - `<` の次の語は「`<` の入力」として覚え、語からは外す。ただし次の語が `<(` などの `(` を含む語なら、`<` だけを捨てて次の語は区切りとして扱う（`wc -l < <(./x.sh)` の中の台本は、次の区間として判定される）。
      - `>` を含む語（`>`・`>>`・`>&`・`&>`）の次の語は捨てる。ただし次の語が `>(` などの `(` を含む語なら捨てない（`cat x > >(bash)` のため）。
      - 数字だけの語の次が `<` か `>` を含む語（`2>`・`2>&1` の `2`）なら、数字の語を捨てる（`2>/dev/null ./x.sh` の頭の語を、数字ではなく台本の道にするため）。
   - 語の「名前」は、最後の `/` より後ろの部分（例: `/usr/bin/git` → `git`）。

**頭の語**: 区間の先頭から、次の語を読み飛ばした後の最初の語。

- 変数の代入（`A=1`）
- 前置きの語: env・nohup・time・exec・nice・timeout・xargs・stdbuf・caffeinate・command・builtin・`{`・then・do・else・elif・if・while・until・`!`・arch・watch・parallel（`{` は `{ ./x.sh; } > o.txt` の囲みのため）
- `function` とその後ろの 1 語（関数の名前。`function f {` のため。その後ろの `{` は前置きの語として飛ぶ）
- 前置きの語の後ろにある、`-` で始まる語・代入・数字（`10`・`5s`）。ただし次のちょうどその語は、次の 1 語も飛ばす: `-I`・`-L`・`-n`・`-P`・`-s`・`-d`・`-E`・`-a`・`-u`・`-k`・`-C`・`--signal`・`--kill-after`・`--max-args`・`--replace`・`--max-procs`・`--delimiter`・`--arg-file`・`--unset`・`--chdir`（`xargs -I {} ./x.sh`・`timeout --signal KILL 5 ./x.sh` のため）

**区間の判定**（上から順に見る）

1. 先頭の代入を除いた語が無い → 先頭の代入に `GIT_` で始まる名前があれば止める（規則 `git-env`）。無ければ通す。
   - この手順と手順 3 の `GIT_` の代入では、`GIT_PAGER=cat` と `GIT_PAGER=`（空）だけは除く（ページャーを止める普段の書き方で、別の命令を動かさないため）。
2. 頭の語より前に env があり、その後ろ（頭の語まで）に `-S`・`--split-string`（`-S…`・`--split-string=…` の形も含む）がある → その値と後ろの語をつないだ文を、この §5-3 の判定に最初からかける。止まれば止める（`env -S 'git push'` のため）。
3. 先頭の代入と、頭の語より前の語（`env GIT_SSH_COMMAND=…` など）に `GIT_` で始まる代入がある → 止める（規則 `git-env`）。git は GIT_ の環境変数で別の命令を動かせるため。区間の先頭の語が export・declare・typeset・local・readonly で、語のどれかが `GIT_` で始まる代入のときも止める。頭の語より後ろの引数（`git log -S 'GIT_DIR='`）は見ない。
4. 区間の先頭の語が `command` で、次の語が `-v`・`-V` → 通す。
5. 調べるだけの区間 → 通す。ただし rg に `--pre`（`--pre=` を含む）があれば止める（規則 `script`。rg は --pre で別の命令を動かすため）。
   - 頭の語の名前が次のどれか: ls・file・stat・which・du・pgrep・ps・realpath・readlink・basename・dirname・wc・echo・printf・type・grep・egrep・fgrep・rg・ag・jq・cat・head・tail・cd・pushd・popd（頭の語で見るので、`xargs grep -l bash` も通る）
6. 頭の語の名前が sudo・su・doas → 止める（規則 `sudo`）。security（Mac の鍵の保管庫）→ 止める（規則 `keychain`）。trap → 次の語（合図のときに動かす命令）を、この §5-3 の判定に最初からかけ、止まれば止める（`trap './x.sh' EXIT` のため）。
7. 表C（台本の実行）に当たる → 止める（規則 `script`）。
8. 語を前から順に 1 つずつ見て、最初に当たったもので決める（規則の名前は、先に出た語のものになる）。
   - 名前が claude・codex・gemini → 止める（規則 `agent`、表D）。ただし、その後ろの語が 1 つ以上あり、全部が `--version`・`-v`・`--help`・`-h` なら次の語へ進む。
   - 名前が ollama → 止める（規則 `agent`、表D）。ただし、後ろの語が上と同じく `--version` などだけのときと、`-` で始まらない最初の語が list・ls・ps・show・help のときは次の語へ進む。
   - 名前が `git` → その後ろの語を表A で判定する。読むだけでなければ止める（規則 `git-<動詞>` など）。
   - 名前が `gh` → その後ろの語を表B で判定する。読むだけでなければ止める（規則 `gh-<語>`）。
9. どれにも当たらなければ通す。

手順 8 では、find の `-exec`・`-execdir`・`-ok`・`-okdir` から終わりの `;`・`+` までの語は外す（その部分は表C で判定済みのため）。

**表A git**

- 読み飛ばし:
  - `git` の後ろで、`-` で始まる語を選択肢として飛ばす。
  - `-C`・`-c`・`--git-dir`・`--work-tree`・`--namespace`・`--config-env`・`--super-prefix` のちょうどその語のときは、次の 1 語も飛ばす。
  - `-C/a`・`--git-dir=/a`・`-P`・`--no-pager` は 1 語として扱う。
- 次のときは止める。
  - `-c` の値が `core.quotepath=…` か `color.…=…` でない（規則 `git-c`）。`core.pager`・`core.fsmonitor`・`diff.external`・`alias.*` などは、読むだけの動詞でも別の命令を動かせるため。
  - `--config-env`（`=` 付きも含む）がある（規則 `git-config-env`）。
  - 動詞の後ろに、`--upload-pack`・`--receive-pack`・`--exec` で始まる語がある（規則 `git-exec`）。
  - 動詞が grep で、後ろに `--open-files-in-pager` で始まる語か、`-` 1 つで始まり `O` を含む語（`-O`・`-nO`・`-O'vim'`）がある（規則 `git-grep-pager`。指定した命令でファイルを開くため）。
  - 飛ばした後に語が無い（規則 `git-noverb`）。

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
| remote | `-` で始まらない最初の語が無いか、show・get-url なら通す（`git remote -v add …` は止まる） |
| config | 後ろに --get・--get-all・--get-regexp・--list・-l・--get-urlmatch のどれかがあるか、`-` で始まらない最初の語が get・list なら通す（`git config core.pager get` は止まる）。`-` で始まらない語がちょうど 1 つ（`git config user.name`。名前だけは値を読む形）で、書き込みの選択肢 --unset・--unset-all・--add・--replace-all・--rename-section・--remove-section・-e・--edit が無ければ通す |
| symbolic-ref | -d・--delete があれば止める。それ以外は、`-` で始まらない語が 1 つ以下なら通す |
| branch | ① 後ろの語（`=` の前）に、書き込みの選択肢 -d・-D・-m・-M・-c・-C・-f・--delete・--move・--copy・--force・-u・--set-upstream-to・--unset-upstream・--edit-description・--track・-t・--create-reflog があれば止める。② `-` で始まらない語があり、一覧の選択肢 -l・--list・--contains・--no-contains・--merged・--no-merged・--points-at・--all・--remotes・--show-current がどれも無ければ止める（枝を作る形）。-v・--verbose は枝を作る形でも働くので一覧の選択肢に入れない（`git branch -v newb` は枝を作る。2026-10-26 の審査役の実測）。`-a`・`-r` に名前を付けた形は git が断るので通してよい。③ それ以外は通す |
| tag | branch の書き込みの選択肢に -a・--annotate・-s・--sign・-F・--file を足して、同じ判定をする。一覧の選択肢には branch のものに -n・-v・--verify を足す（`git tag -n newtag` は一覧を出すだけで、札を作らない。同じ実測） |
| 上に無い動詞（commit・push・merge・rebase・cherry-pick・revert・am・pull・checkout・switch・restore・reset・clean・add・rm・mv・apply・init・clone・update-ref・gc・prune・別名（alias）など全部） | 止める |

**表B gh**

- 読み飛ばし:
  - `gh` の後ろと、第 1 語の後ろで、`-` で始まる語を飛ばす。
  - `-R`・`--repo` のときは、次の 1 語も飛ばす。
  - `--version` は飛ばさずに第 1 語として扱う。
- 後ろの語が 1 つ以上あり、全部が `--version`・`-v`・`--help`・`-h`・`version` なら通す（`gh --help`）。
- 第 1 語が auth で、後ろの語のどれかが `-t`・`--show-token`（`=` 付きも含む）なら止める（規則 `gh-token`。`gh auth status --show-token` は鍵を表示するため）。auth 以外の `-t` は `--template`（表示の形の指定）なので見ない（`gh pr view 1 -t '{{.title}}'` は通る）。
- 飛ばした後に語が無ければ止める（規則 `gh-noverb`）。

| 第 1 語 | 通す第 2 語 |
|---|---|
| pr | view・list・checks・diff・status（review・comment・create・merge・edit などは止める） |
| issue | view・list・status |
| run | view・list・watch |
| repo | view |
| release・workflow | view・list |
| auth | status（`gh auth token` と `--show-token` も止まるので、gh から鍵を取り出して curl で書く形も止まる） |
| label・secret・cache・extension・alias | list |
| variable・config | list・get |
| gist | view・list |
| ruleset | list・view・check |
| search・status・help・version・--version | 第 2 語を問わず通す |
| 上に無い第 1 語（拡張・別名を含む） | 止める |

gh api は、後ろの語を見て次の順に判定する。

1. `-X`・`--method` がある（`-XPOST`・`-X=POST`・`--method=post` の形も含む） → 値が GET（大文字小文字は問わない）なら通す。それ以外は止める。
2. 値つきの選択肢 `-f`・`-F`・`--field`・`--raw-field`・`--input`（`=` 付きも含む）を集める。`-ftitle=x`・`-Ftitle=x` のように値がくっついた形も、くっついた部分を値として集める。
3. `graphql` の語がある → 次のどれかに当たれば止め、どれにも当たらなければ通す。
   - 元の command 全体に語 `mutation` がある。
   - `--input` がある。
   - 集めた値（`=` の後ろ）が `@` で始まる（ファイルから読む形）。
   - `query=` の値に `$(` か逆引用符がある（`query="$(cat m.graphql)"` のように、ファイルの中身を入れる形）。
4. それ以外 → 集めた値があれば止め（gh は値を付けると POST にするため）、無ければ通す。

区間ごとに見るので、`gh api … | jq -f x` の jq の `-f` には当たらない。

**表C 台本の実行**（区間ごとに判定する。「一時の場所」は、文字どおり `/tmp/` か `/private/tmp/` で始まり、`..` の段を含まない道。`"$S/x.py"` のように変数で書いた道は、中身が見えないので一時の場所として扱わない）

- 頭の語の名前が source か `.` で、後ろに語がある → 止める。
- 頭の語が `{}`（find・xargs で見つけたファイルそのものを動かす形）→ 止める。
- 頭の語に `/` が含まれる（例: `./scripts/dev/executor-preflight.sh`・`scripts/dev/executor-preflight.sh`・個人の記録帳の save 台本の絶対パス）→ 止める。ただし次は除く。
  - `/bin/`・`/usr/bin/`・`/usr/sbin/`・`/sbin/`・`/opt/homebrew/bin/`・`/usr/local/bin/` で始まる語。
  - 名前が git・gh・claude・codex・gemini・ollama の語（表A・表B・表D で判定する）。
  - 一時の場所の台本（審査役などが調べるための使い捨ての台本。§7）。
- 頭の語の名前が eval で、後ろの語に `$(` か逆引用符がある → 止める（`eval "$(cat x.sh)"`。ファイルの中身は見えないため）。
- 頭の語の名前が npx・bunx・make・just・task・rake・invoke・uv・uvx・pipx・poetry、または試験や入れ物を動かすもの（pytest・playwright・vitest・jest・tox・nox・pre-commit・docker・alembic・cargo・go）→ 止める。ただし、後ろの語が 1 つ以上あり、全部が `--version`・`-V`・`-v`・`--help`・`-h`・`version` なら通す。
- 頭の語の名前が npm・pnpm・yarn → 止める。ただし次のときは通す。
  - `-` で始まらない最初の語が ls・list・view・info・outdated・why のとき。
  - `-v`・`--version` があるとき。
- find の `-exec`・`-execdir`・`-ok`・`-okdir` の後ろ（終わりの `;`・`+` まで）を 1 つの区間として、この節の判定（区間の判定 1〜9）をする。`find … -exec ./x.sh {} \;` は止まり、`find … -exec wc -l {} +` は通る。
- 頭の語の名前が、次の解釈系に当たる → その後ろの、`-` で始まる語を飛ばして最初の語を見る（`-c`・`-e`・`--eval`・`-` は飛ばさない）。頭の語だけを見るので、引数にある解釈系の名前（`find . -name python3`・`lsof -c node`・`brew info python3`）では止めない。
  - 解釈系: bash・sh・zsh・dash・ksh・fish・python・python2/3（`python3.12` も含む）・pypy・node・deno・bun・tsx・ts-node・ruby・perl・php・osascript
  - 飛ばすときの決まり:
    - `-X`・`-W`（Python の値つきの選択肢）は、次の 1 語も飛ばす。
    - `-r`・`--require`・`--import`・`--loader`・`--experimental-loader`（node などが先にファイルを読む選択肢）は、値（`=` の後ろか次の語）が一時の場所でなければ止める。一時の場所なら値も飛ばす。
    - シェルで、`-` 1 つで始まり `c` で終わる語（`-c`・`-lc`・`-ec`）は `-c` と同じに扱う。
    - シェルで、`-` か `+` 1 つで始まり `o` で終わる語（`-o`・`-euo`）は、次の 1 語（`pipefail` などの名前）も飛ばす。
    - シェルの `-n`（文の形を確かめるだけで、動かさない）は通す。
    - perl・ruby で、`-` 1 つで始まり `e` で終わる語（`-e`・`-ne`・`-lne`・`-pe`）は `-e` と同じに扱う。
    - Python で、`-` 1 つで始まり、値の無い選択肢の文字（`b`・`B`・`d`・`E`・`h`・`i`・`I`・`O`・`P`・`q`・`s`・`S`・`u`・`v`・`V`・`x`）の後ろに `m` がある語（`-m`・`-mfoo`・`-Im`）は、`m` の値（くっついた部分か、次の語）が json.tool なら通し、それ以外は止める。

  | 最初の語 | 判定 |
  |---|---|
  | `-c`・`-e`・`--eval`（上の `-lc`・`-ne` などを含む） | 次の語に `$(` か逆引用符があれば止める（`bash -c "$(cat x.sh)"`。ファイルの中身は見えないため）。無ければ通す（中身は前処理 1 の埋め込みとして判定される） |
  | 無い、または `-` | 区間に `<<<` の入力があれば、その値に `$(` か逆引用符があれば止め、無ければ通す（`bash <<< "$(cat x.sh)"` は止まる。値そのものは前処理 2-3 で命令として判定済み）。区間に heredoc があれば通す（本文は前処理 2-1 で扱う）。`<` の入力があれば、その道が一時の場所なら通し、それ以外は止める。パイプの後ろなら止める（`cat x.sh \| bash`）。どれでもなく、語が無ければ通し、`-` なら止める |
  | それ以外（台本のファイル） | 一時の場所なら通す。それ以外は止める |

- 台本の名前の一覧は持たない。どの台本が GitHub へ書くかに関係なく、担当は台本を動かさない。そのため、新しい台本を足しても見張りを直す必要が無い。

**表D 別の AI**: claude・codex・gemini。起動された側は新しい本流の会話になり、agent_id が無いので、この見張りの外で書き換えられるため止める。gemini はこの Mac の ~/.npm-global/bin にあり（0.44.0）、`-p` と `--yolo`（確かめずに道具を動かす）を持つ（第5版の審査役が `gemini --help` で確かめた）。名前の一覧は 2026-10-26 に ~/.npm-global/bin・/opt/homebrew/bin・~/.local/bin・/usr/local/bin を見て作った（recon.md §6）。ollama（0.17.7）は `ollama launch claude`・`ollama launch codex` のように別の AI（Claude Code・Codex・OpenCode など）を起動できる（`ollama launch --help` で確かめた）ので、一覧を見る使い方（list・ls・ps・show・help・`--version`）のほかは止める。npx・bunx・`npm exec`・`pnpm dlx` で起動する形は表C で止まる。`claude --version` のように、後ろが `--version`・`-v`・`--help`・`-h` だけのときは通す。

**設計者の当て試験**

- 上の判定を Python で書いた試作に、[cases.md](cases.md) の止める例 229・通す例 198 を当てた。誤りは 0。
- cases.md には、第3版の審査役が当てた 46 の例（rv4795v3/probe.py）、第4版の審査役が当てた例（rv4795v4/probe.py・comment_probe.py。awk と ssh を除く。§7）、第5版の審査役が当てた例（rv4795v5/probe5.py。§7 に書いたものと、実測で git が断る・一覧を出すだけと分かったものを除く）、設計者が足した例を入れた。
- 試作: /tmp/CC報告ファイル/local-subagent-guard/proto-v6-judge.py
- 結果: /tmp/CC報告ファイル/local-subagent-guard/proto-v6-out.txt（cases.md）、proto-v6-probes.txt（審査役の例。外れは §7 に書いたものと、`git branch --all newb`・`git tag -n newtag` の 2 つ。この 2 つは実測で枝・札を作らないので通すのが正しい）
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
  - 評価役の本来の仕事である試験の実行（`npx playwright`・`playwright test`・`pytest`・`vitest run`・`npm run test`・`docker compose up` など）も、表C で止まる。評価役の試験はクラウドで動かす（PO の決定「1」：実装と試験はクラウド）。手元の評価役は、クラウドの試験の結果（PR の checks・記録）を読んで判定する。
- 審査役が調べるための使い捨ての台本
  - 一時の場所（/tmp・/private/tmp）にある台本は動かせる（表C）。審査役が設計の試作を写して当てる、といった調べものを止めないため。道は文字どおりの絶対パスで書く（`python3 /private/tmp/…/probe.py` は通り、`python3 "$S/probe.py"` は止まる）。
  - リポジトリの台本は動かせない。
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
  - ~/.claude/logs/local-subagent-guard.log は消さない（K-c の記録を残すため）。

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
| 区間に分けるのに scan_text を使う（第3版） | 引用符を気にせずに割るので、grep の正規表現の `\|` などで誤って止めた（第3版の審査 3-2）。第4版は shlex の区切りで分ける |
| Bash の書き換え（`>`・`sed -i`）も全部止める | 担当の作法（調べものの生の出力を /tmp に残す）が壊れる |
| 止めずに記録だけ取る | PO の決定「１」は止めること |

## 7. 受け入れるリスク

- シェルでの直接の書き換え
  - 担当は、Bash の命令文でファイルを書き換えられる（`>`・`sed -i` など）。
  - 本体と同じ作業場所で動けば、本体の未保存の変更を上書きして消せる。消えた変更は git status に出ない。
  - git の命令での書き換えや消去（checkout・restore・reset・clean・stash など）は表A で止まるので、残るのはシェルでの直接の書き換えだけ。
  - シェルで .git/config や .gitattributes を書き換えれば、読むだけの git の命令（status・diff）に別の命令を動かさせることもできる。わざと見張りを外す形で、次の 3 つと同じ種類として受け入れる。
- 解釈系の中で書いた命令
  - `python3 -c`・`node -e`・`python3 - <<EOF` の本文の中で、ライブラリや subprocess の配列（`["git","push"]`）を使って書き込む形は見抜けない。awk の `system("…")` も同じ（Mac の awk にもある）。
  - perl・ruby の `-e`・`-ne` の中の `system("…")` も同じ（`perl -ne 'print if /foo/'` のような読む使い方を止めないため）。
  - 担当の数え作業（Python で数える）を止めないため、受け入れる。
- 別の命令を後で動かさせる設定
  - `BROWSER=./x.sh gh pr view 1 --web` のように、読むだけの命令に、開くための命令を環境変数で渡す形。`open x.command` のように、Mac の「開く」で台本を動かす形。
  - どちらも、わざと見張りを外す形として、上と同じく受け入れる。
- 一時の場所の台本
  - /tmp・/private/tmp の台本は動かせる（表C）。担当がリポジトリの台本をそこへ写せば動かせる。上と同じく、わざと見張りを外す形として受け入れる。
- 変数で組み立てた命令（`G=git; $G push`）と、隠した命令（base64 など）は見抜けない。
- GNU sed の `e` 命令（`sed -n "1e git push"`）は見抜けない。
  - 引用符の中の `1e git push` は 1 語になり、名前が git の語にならない。
  - Mac の標準の sed は BSD 版で、`e` 命令が無い。GNU sed を入れたときだけ起きうる。
- curl などで、GitHub 以外の外の受け口へ書くことは止めない。
  - GitHub への書き込みに要る鍵は、gh からは取り出せない（`gh auth token`・`gh auth status --show-token` は表B で止まる）。Mac の鍵の保管庫を読む security も止める（区間の判定 6）。
  - gh は鍵をファイルに置いていない。2026-10-26 に本体が確かめた: ~/.config/gh/hosts.yml に `oauth_token` の行は 0 件（`grep -c` の件数だけを見て、値は出していない）。gh の設定が変わってファイルに置くようになると、cat で読める。
  - 【未確認】agent-console に、手元から会話を起こせる受け口があるか。あれば curl で表D の外に出られる。導入後の点検で確かめる。
- ssh は止めない。
  - 手元の担当がサーバーを見る道として残す。担当が使える鍵は制限付き鍵（ForceCommand で決まった命令しか動かない）で、無制限鍵は PO の都度の許可が要る（CLAUDE.md「VPS 直作業禁止」）。
- 担当が Agent の道具で別の担当を起こすこと
  - 起こされた担当にも agent_id が入るので、同じ見張りで止まる。
  - 起こし先をクラウドにする（isolation remote）と、クラウドで書き込める。クラウドは書き込む場所なので（PO の決定「1」）、止めない。
- 入力の JSON が読めないときは通す（本体を止めないため）。
- 担当だけに起きる誤った止め
  - 調べるだけの命令（§5-3 区間の判定 5）以外の命令の引数に、名前が git・gh・claude・codex・gemini の語があるとき（例: `find . -name gh`・`sed -n 1p ~/x/git`）。
  - 引数の無い `claude`・`codex`・`gemini`・`ollama`。`ollama run`（手元のモデルとの会話）。
  - `docker ps` など、試験や入れ物を動かす道具の読むだけの使い方（表C は名前で止める。`--version` などだけは通す）。
  - 一時の場所でも、`env -C /tmp ./x.sh` のように道の形が `./` のものは止まる。`python3 "$S/x.py"` のように道を変数で書いたものも止まる（中身が見えないため。文字どおりの絶対パスで書けば通る）。
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
| K7 止めたとき ~/.claude/logs/local-subagent-guard.log に 1 行が足され、命令文は含まれない | test_guard.sh（HOME を一時ディレクトリにする） |
| K8 install.sh を一時の HOME で 2 回流しても、項目は 1 つ。installed-from.txt がある。rollback.sh で項目と写しが消え、他の項目と log は残る | test_guard.sh（HOME を一時ディレクトリにして流す） |
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
  - 件数は ~/.claude/logs/local-subagent-guard.log に残る。
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
  - 命令文の読み方は、引用符を正しく扱わないと、すり抜けと誤った止めの両方が出る（第3版の審査）。第4版は shlex の区切りで分ける。

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
- 第3版（4abf275ae）の指摘（A〜I は直っていると確認された）
  - 3-1 台本を流し込む形が素通りする（source・`.`・`| bash`・`python3 - < file`・find -exec・xargs -I）
  - 3-2 読むだけの調べもので止まる（`python3 <<'EOF'`・grep の `\|`・`claude --version`）
  - 3-3 git の -c・GIT_ の環境変数で別の命令を動かせる
  - 3-4 graphql の mutation をファイルから読む形
  - 3-5 評価役の試験の実行も手元で止まることが書かれていない
  - 3-6 未確認（agent-console の受け口・Agent の道具）
  - §8 K-b が測れない。rollback で log が消える
  - design.md の「`-` の中身は埋め込みとして判定される」は事実と違う
- 第4版での直し
  - 3-1: 表C に source・`.`・`{}`・パイプや `<` で解釈系に渡す形・find -exec の中・xargs の値つき選択肢を足した
  - 3-2: 区間の分け方を shlex の区切りに替え、heredoc の印を台本の名前とみなさないようにした（前処理 2）。調べるだけの命令に grep・rg・jq・cat などを足した。表D に `--version` などの例外を足した
  - 3-3: 表A に -c の値の決まり・--config-env・--upload-pack などを足し、区間の判定 3（GIT_ の代入）を足した
  - 3-4: 表B の graphql に `query=` の `$(` を足した
  - 3-5: §5-4 に評価役の試験と、一時の場所の台本を書いた
  - 3-6: §7 に書いた
  - K-b と log の置き場所を直した（§3・§5-2・§5-5）
  - 誤った説明は §5-3 前処理 1 で直した
- 第4版（101b154bf）の指摘（3-1〜4 は直っていると確認された）
  - R1 行の終わりの注釈 `#` のあとの行と、語の途中の `#` のあとが判定されない（shlex の注釈の扱い）
  - R2 `{ …; }` の囲みの中の台本が通る
  - R3 `bash -c "$(cat x.sh)"`・`eval "$(…)"`・`<<< "$(…)"`・`tee >(bash)`・`> >(bash)` が通る
  - R4 §5-4 の「評価役の試験は表C で止まる」が一部事実と違う（pytest・playwright など）
  - R5 `gh auth status --show-token` で鍵を取り出せる。security は未確認
  - R6 `env -S '…'`・`git grep -O` が通る
  - §5-3 の文と試作の食い違い（heredoc の行の見方・`<(`・`>(`・手順 6〜8 の順）
  - 軽微: `xargs grep`・`bash -lc`・`python3 -X utf8 -c`・`gh --help`・`uv --version`・`git log -S 'GIT_DIR='` の誤った止め。`/tmp/../`・`timeout --signal`・`builtin source`・`python3 -mfoo`・`node --import=`・`git remote -v add`・`git config core.pager get`・`$'git'`・行の続き の素通り
- 第5版での直し
  - R1: 前処理 2-2 に、注釈を引用符の外の語の頭の `#` だけ捨てることと、`commenters = ""` を書いた
  - R2: 前置きの語に `{`・builtin を足した
  - R3: 表C の解釈系に `-c` の値・`<<<` の値・eval の `$(` を足した。前処理 2-3 に `<(`・`>(` を足した
  - R4: 表C に pytest など試験や入れ物を動かす道具を足し、§5-4 の例を直した
  - R5: 表B に `-t`・`--show-token` を、区間の判定 6 に security を足し、gh の鍵がファイルに無いことを確かめて §7 に書いた
  - R6: 区間の判定 2 に env -S を、表A に git grep の `-O` を足した
  - 食い違い: heredoc は `<<` の行の全体を見る形に揃えた。区間の判定 8 を「語の順に 1 回で見る」に書き直した
  - 軽微: 素通りは全部直した（`$'`・行の続き・`..` の道・前置きの長い選択肢・remote と config の決まり・解釈系の選択肢）。誤った止めは全部直した。awk と ssh は §7 に書いた
- 第5版（3e61daa71）の指摘（R1〜R6 は直っていると確認された）
  - N1 gemini（`-p`・`--yolo` を持つ）が表D に無い
  - N2 引用符の無い heredoc の本文の `$( )`・逆引用符が判定されない
  - 食い違い: `< <(…)` でどちらの決まりが先か読めない。`$(pwd)#` の `#` の扱い
  - 軽微の素通り: `git branch -v newb`・elif・`function f {`・`2>/dev/null ./x.sh`・`arch -arm64`・trap・`bash \` の後の heredoc・`gh api -ftitle=x`。BROWSER と open は §7 に書けばよい
  - 軽微の誤った止め: `gh pr view -t`・`git config user.name`・`GIT_PAGER=cat git log`・`perl -ne`・`bash -o pipefail -c`・`bash -n`・引数の解釈系の名前・`python3 -Im json.tool`。変数で書いた一時の場所の道は §5-4・§7 に書く
- 第6版での直し
  - N1: 表D と表C の除外に gemini を足し、道具の洗い出しを recon.md §6 に書いた。ADR にも足した。洗い出しで、ollama が `ollama launch claude` などで別の AI を起動できると分かったので、ollama も表D に足した
  - N2: 前処理 2-1 に、引用符の無い heredoc の本文の埋め込みを一覧に足すことを書いた。行の続きを本文を見つける前に直す
  - 食い違い: 前処理 2-3 に決まりを当てる順（`(` を含む語が先）と、`<` が `<(` を飲まないことを書いた。注釈の頭の判定から `)` を外した
  - 軽微の素通り: 前置きの語（elif・arch・watch・parallel・function）、数字つきの向け先、trap、gh api のくっついた値、branch の一覧の選択肢を直した（-v・--verbose を外す。-n・-v・--verify は tag だけ）。BROWSER と open は §7 に書いた
  - 軽微の誤った止め: 表B の `-t` は auth だけ、表A の config の名前 1 つ、GIT_PAGER=cat、解釈系の選択肢（`-ne`・`-o`・`-n`・`-Im`）、解釈系は頭の語だけで見る、を直した。変数で書いた道は表C の定義と §7 に書いた
