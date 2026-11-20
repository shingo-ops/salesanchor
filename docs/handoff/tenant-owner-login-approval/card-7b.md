# card: 便7b AI が PO の名前で GO を書く操作を止める（手元とクラウドの見張り・K10 の補い）

状態: カード第3版（Opus、2026-11-20）。PO の実装承認は2つ。設計全体は 2026-11-06「1」。便7 を「間違いを止める関所」として作り、AI 側の見張りを足す形は 2026-11-20「1」。
審査: 2回目 REVISE（クラウドの設計審査役、2026-11-20 01:22 UTC、commit 343eee1c3）。重は無し。中1 は (a) を単引用符の本文と決まった文字だけの --body-file に絞った（L3 を単引用符に変え、L30 を足した）。中2 は (b) を語に分けて許す印だけを通す形にした（L31〜L36）。中3 はクラウドで本文をファイルで渡す道を読むようにした（C13〜C18）。中4 で見えた範囲の試験の抜け（-t・--user=・単引用符の (a) に && や | や ` を付けたもの）は L37〜L41 で足した。中4 の残りと中5 は、記録の表示で切れて読めていない。3回目の審査で出し直してもらった。
審査: 3回目 REVISE（クラウドの設計審査役、2026-11-20 01:50 UTC、commit c69f7d61a）。重1 と中10・軽8。
- 重1（guard.py の本文が install-guard.sh の語の検査 `_ga_words_ok` に当たる）: 3-1 の「語の決まり」を足し、L49 と V6 で確かめる。
- 中1（unittest だと install-guard.sh が渡す guard.py の道を試験名と読む）: 4 の試験の形を install-form-guard/test_guard.py と同じにした。
- 中2（札と語の試験が無い）: L49。
- 中3（`gh pr comment -F f.md` が抜ける。`gh help pr comment` に `-F, --body-file file` と出ることを Opus も 2026-11-20 に確かめた）: 3-3 の読む印に足した。C19。
- 中4（引用符の中の `|` を本物の `|` と同じに扱う）: (b) を、引用符を見て分ける形に変えた。L44。
- 中5（`-ushingo-ops` の詰めた形）: 4 の「PO の鍵を使う」に `gh auth token` を含む命令を全部入れた。L42・L43。
- 中6（C11・C12 に hook_event_name が無い）: 入力に足した。
- 中7（クラウドの決まりは active-work.d を commit しない）: 1 から外し、登録は Opus が行う。
- 中8（相対の道の基準が無い）: 入力 JSON の cwd を基にする。L45・L46・C23。
- 中9（手元の GitHub の MCP の道具）: Opus が 2026-11-20 に `claude mcp list` を流し、GitHub の道具が無いことを確かめた。限界に書く。
- 中10（`--body "$(cat f.md)"` が抜ける）: 3-3 で、書き込みの形の命令に `$(` か `` ` `` があれば止める。C20。
- 軽（MultiEdit がクラウドに届かない・MCP の文書送り・GO を探す読むだけの命令・Edit の一部書き換え・普通でないファイル・`-t` の探し方・クラウドの内部エラーの試験・試験の禁止語）: 2・3・4・6 にそれぞれ書いた。L47・L48・C21・C22・C24・C25。
4回目の審査の結果をこの下に書き足す。未審査の間は実装に渡さない。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。手元の settings.json への導入は Opus が共通の台本で行い、このカードの範囲外。PR は作らない（Opus が作る）。
基準: 枝 release/tenant-owner-bin7b-go-identity-guard（Opus が origin/main から作って渡す）。

設計の節: docs/handoff/tenant-owner-login-approval/design.md「### 便7b」。この PR は便7 より先に合流する。便7 の守る一覧（組A）に、この PR の5つの新しいファイルが入るため。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）と照合（Opus、2026-11-20）
- 00-common.md: プレースホルダを残さない → 名前・決まり・文はすべて書き切った。
- 03-file.md: 新規5件。既存2件（dispatch.sh・agent-hooks-test.yml）は下に書いた場所だけ変える。
- 10-executor.md: カードに無い確認は足さず、外れたら停止する。
- 12-guard-authoring.md: 目的・影響・誤検知・代替案・戻し方・守り手は design.md 便7b と下の「5」に書いた。通す例と止める例は「3. 試験」に書いた。手本は scripts/agent-hooks/install-form-guard/（札の形・試験の形）と scripts/agent-hooks/cloud/python_version_guard.py（クラウドの見張りの形）。

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin7b-go-identity-guard HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 `ls scripts/agent-hooks/go-identity-guard scripts/agent-hooks/cloud/go_comment_guard.py` が両方「No such file」。
- P2 `grep -c "for G in python_version_guard.py subagent_bash_wait_guard.py; do" scripts/agent-hooks/cloud/dispatch.sh` が 1。
- P3 `grep -c "name: install-form-guard test" .github/workflows/agent-hooks-test.yml` が 1。
- P4 `cat scripts/agent-hooks/install-form-guard/guard-manifest.json` の鍵が name・files・hooks・tests の4つ。
- P5 `python3 --version` が 3.10 以上。

## 1. 触るファイル（これ以外は触らない）
1. scripts/agent-hooks/go-identity-guard/guard.py（新規）
2. scripts/agent-hooks/go-identity-guard/guard-manifest.json（新規）
3. scripts/agent-hooks/go-identity-guard/test_guard.py（新規）
4. scripts/agent-hooks/cloud/go_comment_guard.py（新規）
5. scripts/agent-hooks/cloud/test_go_comment_guard.py（新規）
6. scripts/agent-hooks/cloud/dispatch.sh（1行だけ変える）
7. .github/workflows/agent-hooks-test.yml（job を2つ足す）

登録（.claude-pipeline/active-work.d/）は commit しない。クラウドの決まり（scripts/agent-hooks/cloud/rules.md:12）に従う。登録は Opus が手元で行う（審査3回目の中7）。

## 2. 共通の決まり（2つの見張りで同じ関数を書く。共有のファイルは作らない）
- `norm(s)`: `'` と `"` を消す。空白の連続（改行を含む）を1つの空白にまとめる。小文字にする。
- 「同じ名前の検査」の決まり（W）: 道具が Write か Edit で、file_path に `/.github/workflows/` か `.github/workflows/`（先頭）を含み、ファイル名が `guard-files-gate.yml` でない。そして書く文（Write は content、Edit は new_string。MultiEdit があれば各 edits の new_string）を norm したものが `guard-files gate` を含む → 止める。
  - Edit は、file_path の今の中身を読み、old_string を new_string に置き換えた後の全文（replace_all が true なら全部）を norm して比べる。名前の一部だけを書き換えて「guard-files gate」にする形も止めるため（審査3回目の軽）。MultiEdit は edits を順に当てた後の全文で比べる。ファイルが読めないときは new_string だけで比べる。
  - Bash でのファイル書き込みには当てない。理由は2つ。1つは、`grep "guard-files gate" .github/workflows/` のような読むだけの命令を誤って止めるため。もう1つは、合流の前に便7 の gate の判定4（同じ名前の検査を足す PR を落とす）が同じものを止めるため。
- 「GO の文字」の決まり（G）: 正規表現 `\bGO\s*#\s*\d`（大文字小文字を区別する）。
- 「ファイルを読む」の決まり（R）: 道が相対なら、入力 JSON の `cwd` を基に解決する。`cwd` が無ければ止める（審査3回目の中8）。`os.stat` で普通のファイル（`stat.S_ISREG`）のときだけ読む。`/dev/stdin`・名前付きパイプ・機器のファイル・フォルダは読まずに止める（待ち続けて時間切れになるため。審査3回目の軽）。読めないときも止める。

## 3. 作るもの

### 3-1. scripts/agent-hooks/go-identity-guard/guard.py（手元の見張り・PreToolUse）
- 形は scripts/agent-hooks/install-form-guard/guard.py に合わせる。標準ライブラリだけ、ログは同じ jsonl、hook の名前は `go-identity-guard`。
- 環境変数 `GO_IDENTITY_GUARD_LOG` でログの場所を変えられる。
- 内部エラーのときは止める（exit 2）。install-form-guard と違う点。ログの type は hook_internal_error。
- 語の決まり（審査3回目の重1）: install-guard.sh は guard.py の全文を `scripts/dev/consent-audit.py` の `_ga_words_ok` で調べ、当たれば入れない。そこで guard.py の中（注釈・文字列・止める文も含む）に、次の小文字の並びを1つも書かない: `approve`・`updatedInput`・`updatedPermissions`・`updatedToolOutput`・`behavior`・`additionalContext`。`permissionDecision` と `allow` を同じ行に書かない。
  - (a) の印は `APPROVE_FLAG = "--appr" + "ove"` のように分けて組み立て、正規表現には `re.escape(APPROVE_FLAG)` で入れる。
  - 止める文の「Approve」は大文字の A で書く（小文字の並びにならないので当たらない）。
- 入力の tool_name が Bash のとき、command に次を順に当てる。
  1. `gh\s+auth\s+switch` → 止める。
  2. `gh\s+auth\s+status` と、空白で区切られた語としての `--show-token` か `-t`（正規表現 `(^|\s)(--show-token|-t)(=|\s|$)`）が両方ある → 止める。文字の一部では探さない（審査3回目の軽）。
  3. `find-generic-password` を含む、または `.config/gh/hosts.yml` を含む → 止める（鍵を直接読む道）。
  4. 「PO の鍵を使う」= 命令に `gh\s+auth\s+token` がある、または正規表現 `(-u|--user)(\s+|=)?["']?shingo-ops\b` に合う（`-ushingo-ops` の詰めた形も入る。審査3回目の中5）。どちらでもなければ通す（exit 0）。`gh auth token` は名前を付けない形も、shingo-cc の形も、ここに入る。
  5. 合うときは、次の (a) か (b) に完全一致すれば通す。どちらでもなければ止める。
     - (a) Approve の形。`^GH_TOKEN="\$\(gh auth token --user shingo-ops\)" gh pr review [0-9]+ --approve (--body '[^']*'|--body-file [A-Za-z0-9_./-]+)$`。
       - 本文は単引用符だけ。二重引用符の本文は通さない。中の `$(` と `` ` `` をシェルが実行するため（審査2回目の中1）。
       - 本文に G の文字があれば止める。
       - `--body-file` のときは決まり R でファイルを読んで G を確かめる。道は英数字と `_` `.` `/` `-` だけ。
       - 単引用符の本文の中の `;`・`|`・改行などは文字なので許す。本文の外に何かが付けば、正規表現の `$` で合わなくなる。
     - (b) 読むだけの gh api。`^GH_TOKEN="\$\(gh auth token --user shingo-ops\)" gh api ` で始まる。残りを次の順に調べ、全部に当たれば通す（審査2回目の中2・3回目の中4）。
       - 残りの元の文字に、改行・`` ` ``・`$(` があれば止める（`$(` は先頭の GH_TOKEN の1つだけを許す）。
       - 残りを1字ずつ読む小さな関数で、引用符の外の記号を探す。単引用符の中は全部文字。二重引用符の中は `\` の次の1字を文字とする。引用符の外の `\` も次の1字を文字とする。
         - 引用符の外の `;` と `&` と、入出力を向ける2つの記号（小なりと大なり）があれば止める。`||` も止める。
         - 引用符の外の `|` で、残りを部分に分ける。引用符の中の `|` では分けない（`--jq "|"` は1つの語のまま）。
         - 引用符が閉じていなければ止める。
       - 部分ごとに `shlex.split(部分, posix=True)` で語に分ける。エラーが出れば止める。
       - 最初の部分（gh api の引数）は、次の語だけを許す:
         - `-` で始まらない語（道）。ちょうど1つ。
         - `--jq` と `-q` と、その次の1語。
         - `--paginate`・`--slurp`・`-i`・`--include`・`--silent`。
         - `-X GET`・`-XGET`・`--method GET`・`--method=GET`。
         - ほかの `-` で始まる語が1つでもあれば止める。`-fbody=x`・`-XPOST`・`--method=POST`・`-F`・`--input` や、印を詰めた語もここで止まる。
       - 2つ目からの部分は許す。後ろの命令に GH_TOKEN は渡らない。ただし、その語に `gh` か `curl` があれば止める。
- 入力の tool_name が Write か Edit（MultiEdit も）のとき: 決まり W に当たれば止める。
- 手元には GitHub の MCP の道具が無い（Opus が 2026-11-20 に `claude mcp list` で確かめた。審査3回目の中9）。そのため札の matcher に `mcp__github__` は入れない。後で入れたときは、この見張りの外になる（下の6 の限界）。
- それ以外の道具は通す。
- 止めるときの文（標準エラー、1行）: `🚫 BLOCKED [go-identity-guard]: PO（shingo-ops）の名前で書く操作は、決まった Approve の形と読むだけの gh api だけ通します。GO は PO 本人が書きます（設計: docs/handoff/tenant-owner-login-approval/design.md 便7b）。`
  - 決まり W で止めたときは、別の文にする: `🚫 BLOCKED [go-identity-guard]: guard-files-gate.yml 以外の workflow に「guard-files gate」の名前は書けません（便7 の判定4・便7b）。`

### 3-2. scripts/agent-hooks/go-identity-guard/guard-manifest.json
```
{"name": "go-identity-guard",
 "files": ["guard.py"],
 "hooks": [{"event": "PreToolUse", "matcher": "Bash", "interpreter": "python3", "file": "guard.py"},
           {"event": "PreToolUse", "matcher": "Write|Edit|MultiEdit", "interpreter": "python3", "file": "guard.py"}],
 "tests": ["test_guard.py"]}
```

### 3-3. scripts/agent-hooks/cloud/go_comment_guard.py（クラウドの見張り）
- 形は scripts/agent-hooks/cloud/python_version_guard.py に合わせる（標準入力の JSON を読み、止めるときは exit 2 と標準エラーの日本語）。内部エラーは exit 1。dispatch.sh が止める側に扱う。手本の python_version_guard.py は内部エラーで exit 0（止めない）なので、そこは写さない（審査3回目の軽）。
- tool_name が `mcp__github__` で始まる: tool_input の中の文字の値を全部（入れ子の dict・list も）調べ、G の文字があれば止める。道具の名前では絞らない。
- tool_name が Bash: command に `(^|[\s;|&(])gh\s` か `api.github.com` があり、さらに G の文字もあれば止める。
  - 同じ命令が本文をファイルで渡すときは、決まり R でファイルも読む（審査2回目の中3）。
  - 印と値の探し方: 命令を `shlex.split(posix=True)` で語に分ける（エラーなら止める）。印は `--body-file`・`-F`・`--field`・`--input`・`-T`・`-d`・`--data`・`--data-binary`。値は次の語、または `印=値` の `=` の後ろ、または `-d@X` のように詰めた後ろ。
  - 値から読むファイル X を決める:
    - 値に `@` があれば、`@` の後ろが X。
    - `--body-file`・`--input`・`-T` は、値がそのまま X。
    - `-F`・`--field` で値に `=` が無ければ、値がそのまま X（`gh pr comment -F f.md` の形。`gh help pr comment` に `-F, --body-file file` とある。審査3回目の中3）。値に `=` があり `@` が無ければ文字の値なので、G だけを確かめる。
  - X の中身に G の文字があれば止める。X が `-`（標準入力）のときも止める。
  - 書き込みの形の命令（`gh (pr|issue) (comment|review|create|edit)`、`gh api` に `-f`・`-F`・`--field`・`--raw-field`・`--input` か GET 以外の `-X`/`--method` があるもの、`api.github.com` を含む curl に `-d`・`--data`・`--data-binary`・`-T` か GET 以外の `-X` があるもの）に、`$(` か `` ` `` があれば止める。`--body "$(cat f.md)"` は命令に GO の文字が出ないため（審査3回目の中10）。止める文は「本文はファイルに書いて --body-file で渡してください」とする。
- tool_name が Write・Edit: 決まり W に当たれば止める。G の文字では止めない（試験のファイルに GO の文を書けるように）。クラウドの `.claude/settings.json:81` の matcher は `Write|Edit` で、MultiEdit は dispatch.sh に届かない。settings.json はこのカードでは変えない（審査3回目の軽。下の6 の限界）。
- 止めるときの文: `BLOCKED(cloud): クラウドの担当は GitHub に GO を書きません。GO は PO（組A）か Opus（組B）が書きます（design.md 便7b）。` 決まり W では手元と同じ文。

### 3-4. scripts/agent-hooks/cloud/dispatch.sh
- 変える行は1つだけ:
  - 前 `    for G in python_version_guard.py subagent_bash_wait_guard.py; do`
  - 後 `    for G in python_version_guard.py subagent_bash_wait_guard.py go_comment_guard.py; do`
- ほかの行は1字も変えない。

### 3-5. .github/workflows/agent-hooks-test.yml
- `on.pull_request.paths` は今の `scripts/agent-hooks/**` で足りるので変えない。
- 末尾に job を2つ足す。形は install-form-guard の job と同じ（checkout@v5・fetch-depth 0・contents: read・timeout 10）。
  - `go-identity-guard:`、name `go-identity-guard test`、run `python3 scripts/agent-hooks/go-identity-guard/test_guard.py`
  - `go-comment-guard:`、name `go-comment-guard test`、run `python3 scripts/agent-hooks/cloud/test_go_comment_guard.py`
- 今ある job は1字も変えない。

## 4. 試験（外へは繋がない。ログは一時ファイルへ）
- 形は scripts/agent-hooks/install-form-guard/test_guard.py と同じにする（審査3回目の中1）。unittest は使わない。
  - `GUARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'guard.py')`。install-guard.sh は置き場に写した guard.py の道を引数で渡す（`scripts/agent-hooks/install-guard.sh:130`）。
  - 件ごとに `check(名前, 真偽)` で結果をためる。最後に件数と落ちた件の名前を出し、1件でも落ちたら終了コード 1。
  - install-guard.sh は `python3 -I` で、HOME と PATH だけの環境で流す。試験は自分で一時のフォルダと環境変数（GO_IDENTITY_GUARD_LOG）を作って guard.py に渡す。
- 試験のファイルには、`skip`・`xfail`・`exit 0`・`exit(0)`・`set +e` の文字を書かない（注釈も含む）。後で試験を直すとき、consent-audit.py の `_GA_PLUS_RES` が足した行のこの文字で止めるため（審査3回目の軽）。終了コード 0 を確かめるときは `== 0` と書く。
- test_go_comment_guard.py（クラウド）も同じ形にする（引数が無いときは同じフォルダの go_comment_guard.py）。

test_guard.py（手元）では、各件を subprocess で guard.py に JSON を流して終了コードを見る。Bash の件の入力 JSON には `cwd`（一時のフォルダ）を入れる。
通すもの（exit 0）:
- L1 `gh pr view 1`。
- L2 `gh api repos/shingo-ops/salesanchor/pulls/1`（repo の名前の shingo-ops は「PO の鍵」に当たらない）。
- L3 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh pr review 12 --approve --body 'POの恒久委任に基づく Claude Opus の判断。CI 緑・審査 APPROVE・HEAD abc1234'`。
- L4 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/shingo-ops/salesanchor/rulesets/15777895`。
- L5 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/x/y/pulls/1 --jq .state | head -1`。
- L6 L3 の `--body-file` 版。中身に GO の文字が無い一時ファイルを使う。
- L7 Write で scripts/tests/x.js に `GO #12 abc1234` を書く。
- L8 Write で .github/workflows/guard-files-gate.yml に `name: guard-files gate` を書く。
- L9 shingo-cc の `gh pr comment 5 --body "GO #5 abcdef1"`（組B の GO は Opus が shingo-cc で書くので通す）。
- L31 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api -X GET repos/x/y/pulls --paginate -q '.[].number'`。
- L32 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api --method=GET repos/x/y/rulesets/1 --jq .rules`。
- L45 L6 で、`--body-file b.md`（相対の道）。入力の `cwd` の一時のフォルダに b.md（GO の文字なし）を置く。
- L49 札と語: test_guard.py が `importlib.util.spec_from_file_location` で `os.path.join(HERE, '..', '..', 'dev', 'consent-audit.py')` を読み、`_ga_manifest(札の全文, 'go-identity-guard')` が None でなく、`_ga_words_ok(guard.py の全文)` が True（手本の F9 と同じ）。
止めるもの（exit 2）:
- L10 `gh auth switch --user shingo-ops`。
- L11 `gh auth switch`（引数なし）。
- L12 `gh auth token --user shingo-ops`（鍵を画面に出す）。
- L13 `gh auth token -u shingo-ops`。
- L14 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh pr comment 12 --body "GO #12 abc1234"`。
- L15 L3 の本文に `GO #12 abc1234` を入れたもの。
- L16 L6 で、ファイルの中身に `GO #12 abc1234` があるもの。
- L17 L6 で、ファイルが無いもの。
- L18 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api -X POST repos/x/y/issues/1/comments -f body=hi`。
- L19 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/x/y/issues/1/comments --method PATCH`。
- L20 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/x/y/issues/1/comments -F body=@f`。
- L21 L3 の後ろに `; gh pr merge 12` を付けたもの。
- L22 `T=$(gh auth token --user shingo-ops); curl -H "Authorization: token $T" https://api.github.com/x`。
- L23 `gh auth status --show-token`。
- L24 `security find-generic-password -s gh:github.com -w`。
- L25 `cat ~/.config/gh/hosts.yml`。
- L26 Write で .github/workflows/x.yml に `name: "Guard-Files   Gate"` を書く。
- L27 Edit で .github/workflows/test.yml の new_string に `name: guard-files gate` を書く。
- L28 入力が JSON でない（内部エラーで止める）。
- L29 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/x/y | gh pr comment 1 --body-file -`。
- L30 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh pr review 12 --approve --body "ok $(gh pr comment 12 --body hi)"`（二重引用符の本文）。
- L33 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/x/y/issues/1/comments -fbody=hi`。
- L34 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api -XPOST repos/x/y/issues/1/comments`。
- L35 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api --method=POST repos/x/y/issues/1/comments`。
- L36 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/x/y/pulls/1 > /tmp/o.json`。
- L37 `gh auth status -t`。
- L38 `gh auth token --user=shingo-ops`。
- L39 L3 の後ろに ` && gh pr merge 12` を付けたもの。
- L40 L3 の後ろに ` | cat` を付けたもの。
- L41 L3 の本文の後ろ（引用符の外）に `` `id` `` を付けたもの。
- L42 `gh auth token -ushingo-ops`。
- L43 `GH_TOKEN="$(gh auth token)" gh pr comment 1 --body hi`（名前を付けない gh auth token）。
- L44 `GH_TOKEN="$(gh auth token --user shingo-ops)" gh api repos/x/y --jq "|" -X POST -f body=x`（引用符の中の `|`）。
- L46 L45 で、b.md の中身に `GO #12 abc1234` があるもの。
- L47 L6 で、`--body-file /dev/stdin`（普通のファイルでない）。
- L48 Edit で、中身が `name: guard-files check` の一時の .github/workflows/z.yml の old_string `check` を new_string `gate` にする。

test_go_comment_guard.py（クラウド）では、各件を subprocess で go_comment_guard.py に流す。入力 JSON には `hook_event_name: "PreToolUse"` と `cwd`（一時のフォルダ）を入れる。dispatch.sh 経由の件は `CLAUDE_CODE_REMOTE=true` を付けて流す。dispatch.sh は hook_event_name が PreToolUse でないと見張りを呼ばない（`scripts/agent-hooks/cloud/dispatch.sh:56-67`。審査3回目の中6）。
- C1 mcp__github__add_issue_comment の body が `GO #12 abc1234` → 2。
- C2 mcp__github__pull_request_review_write の body の2行目が `> GO #12 abc1234` → 2。
- C3 道具の名前が未知の mcp__github__new_tool で、入れ子の dict の中に `GO #3 abcdef1` → 2。
- C4 mcp__github__get_pull_request（GO の文字なし）→ 0。
- C5 Bash `gh pr comment 1 --body "GO #1 abcdef1"` → 2。
- C6 Bash `curl -X POST https://api.github.com/repos/x/y/issues/1/comments -d '{"body":"GO #1 abc"}'` → 2。
- C7 Bash `grep -n "GO #" docs/x.md` → 0（gh も api.github.com も無い）。
- C8 Write で scripts/tests/test-guard-files-gate.js に `GO #12 abc1234` → 0。
- C9 Write で .github/workflows/y.yml に `name: guard-files gate` → 2。
- C10 Bash `grep -rn "name: guard-files gate$" .github/workflows/` → 0。
- C11 dispatch.sh 経由で C1 の入力（hook_event_name 入り）→ 2。
- C12 dispatch.sh 経由で C4 の入力（hook_event_name 入り）→ 0。
- C13 Bash `gh pr comment 1 --body-file f.md`、f.md の中身に `GO #1 abcdef1` → 2。
- C14 C13 で、f.md の中身に GO の文字が無い → 0。
- C15 Bash `gh pr comment 1 --body-file missing.md`（ファイルが無い）→ 2。
- C16 Bash `gh pr comment 1 --body-file -` → 2。
- C17 Bash `gh api repos/x/y/issues/1/comments -F body=@f.md`、f.md に `GO #1 abcdef1` → 2。
- C18 Bash `curl -X POST https://api.github.com/repos/x/y/issues/1/comments --data @f.json`、f.json に `GO #1 abcdef1` → 2。
- C19 Bash `gh pr comment 1 -F f.md`、f.md に `GO #1 abcdef1` → 2。
- C20 Bash `gh pr comment 1 --body "$(cat f.md)"` → 2。
- C21 壊れた入力（JSON でない文字）を go_comment_guard.py に直接流す → 1。
- C22 Edit で、中身が `name: guard-files check` の一時の .github/workflows/z.yml の old_string `check` を new_string `gate` にする → 2。
- C23 Bash `gh pr comment 1 --body-file b.md`（相対の道）、入力の `cwd` の b.md に `GO #1 abcdef1` → 2。
- C24 Bash `gh pr view 12 --json body --jq .body | grep "GO #[0-9]"` → 0（GO を探す読むだけの命令の書き方。下の6）。
- C25 Bash `gh api repos/x/y/issues/1/comments -F body=hi` → 0（`=` があり `@` の無い文字の値で、GO の文字が無い）。

## 5. 確かめ方（実行役が流し、生出力を返す）
- V1 `python3 scripts/agent-hooks/go-identity-guard/test_guard.py` が全部 OK（数を書く）。
- V2 `python3 scripts/agent-hooks/cloud/test_go_comment_guard.py` が全部 OK（数を書く）。
- V3 `bash scripts/agent-hooks/cloud/test.sh` を流し、今ある件が前と同じ結果であること（表を返す）。
- V4 `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/agent-hooks-test.yml'))"` が成功。
- V5 `git diff origin/main --stat` に、「1. 触るファイル」の7件だけが出る。dispatch.sh は `1 insertion(+), 1 deletion(-)`。
- V6 `grep -cE 'approve|updatedInput|updatedPermissions|updatedToolOutput|behavior|additionalContext' scripts/agent-hooks/go-identity-guard/guard.py` が 0。`grep -c 'permissionDecision.*allow\|allow.*permissionDecision' scripts/agent-hooks/go-identity-guard/guard.py` が 0。
- V7 `grep -cE 'skip|xfail|exit 0|exit\(0\)|set \+e' scripts/agent-hooks/go-identity-guard/test_guard.py` が 0。

## 想定分岐
- P のどれかが外れる → BLOCKED: と生出力を返す。
- V3 で今ある件の結果が変わる → 止めて NEEDS_DECISION:。直さない。
- 正規表現で L のどれかが通す・止めるを両立できない → 止めて NEEDS_DECISION:。その件を消したり変えたりしない。

## 6. 弊害と戻し方
- 手元の Opus の操作で変わること:
  - shingo-ops の鍵で書けるのは、委任の Approve だけになる。
  - ruleset の変更は、PO が `!` で台本を流す形に変わる（design.md 便7）。
  - 今の Approve の形（L3）は通るので、今の委任は変わらない。
- クラウドの担当は、GO の文字を含む GitHub への書き込みができなくなる。PR の本文の GO記録の転記は Opus が手元で書くので、影響しない。
- クラウドで、GO の例を含む文書（このカードなど）を `mcp__github__` の道具（push_files・create_or_update_file など）で送ると止まる。文書は git の push で送る（クラウドの決まり rules.md の手順のまま）。
- クラウドで、gh の読むだけの命令に `GO #12` のような文字を書くと止まる（`gh pr view 12 --json body | grep "GO #12"` など）。探すときは `GO #[0-9]` の形で書く（C24）。
- クラウドで、書き込みの形の gh の命令に `$(` を使うと止まる。本文はファイルに書いて `--body-file` で渡す。
- 止めきれないもの（design.md 便7b の限界に足す）:
  - クラウドの MultiEdit は見張りに届かない（`.claude/settings.json:81` の matcher が `Write|Edit`）。
  - 手元に GitHub の MCP の道具を後から入れると、この見張りの外になる。入れるときは、この見張りの札に matcher を足す PR を先に出す。
- 誤って止めたとき: Opus は言い換えずに止まり、止めた文と命令の形を PO に報告する。
- 戻し方:
  - 手元: PO が `!` で settings.json の控えから戻す（共通の台本は外す処理を持たない。guard-add-by-ai design.md §8）。
  - クラウド: dispatch.sh の1語を外す PR を出す。便7 の合流の後は組B なので、Opus の GO で合流する。

## 受入（PO が見る形）
| 基準 | 検証方法 |
|---|---|
| agent-hooks-test の2つの新しい job が緑 | PR の検査の欄（Opus が gh pr checks の生出力を保存） |
| 手元で shingo-ops の GO の命令が止まる | 導入後に Opus が L14 の形を、存在しない PR 番号 999999 で流した生出力（見張りの文が出る。もし通っても gh が「not found」で何も書かれない） |
| 手元で今の Approve の形と読むだけの gh api が通る | 導入後の生出力（Approve は実際には付けない。存在しない PR 番号 999999 で流し、見張りの文が出ずに gh の「not found」が返ること） |

END OF CARD
