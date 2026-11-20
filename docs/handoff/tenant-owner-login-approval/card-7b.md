# card: 便7b AI が PO の名前で GO を書く操作を止める（手元とクラウドの見張り・K10 の補い）

状態: カード第2版（Opus、2026-11-20）。PO の実装承認は2つ。設計全体は 2026-11-06「1」。便7 を「間違いを止める関所」として作り、AI 側の見張りを足す形は 2026-11-20「1」。
審査: 2回目 REVISE（クラウドの設計審査役、2026-11-20 01:22 UTC、commit 343eee1c3）。重は無し。中1 は (a) を単引用符の本文と決まった文字だけの --body-file に絞った（L3 を単引用符に変え、L30 を足した）。中2 は (b) を語に分けて許す印だけを通す形にした（L31〜L36）。中3 はクラウドで本文をファイルで渡す道を読むようにした（C13〜C18）。中4 で見えた範囲の試験の抜け（-t・--user=・単引用符の (a) に && や | や ` を付けたもの）は L37〜L41 で足した。中4 の残りと中5 は、記録の表示で切れて読めていない。3回目の審査で出し直してもらう。3回目の審査の結果をこの下に書き足す。未審査の間は実装に渡さない。
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
8. .claude-pipeline/active-work.d/release-tenant-owner-bin7b-go-identity-guard.md（登録）

## 2. 共通の決まり（2つの見張りで同じ関数を書く。共有のファイルは作らない）
- `norm(s)`: `'` と `"` を消す。空白の連続（改行を含む）を1つの空白にまとめる。小文字にする。
- 「同じ名前の検査」の決まり（W）: 道具が Write か Edit で、file_path に `/.github/workflows/` か `.github/workflows/`（先頭）を含み、ファイル名が `guard-files-gate.yml` でない。そして書く文（Write は content、Edit は new_string。MultiEdit があれば各 edits の new_string）を norm したものが `guard-files gate` を含む → 止める。
  - Bash でのファイル書き込みには当てない。理由は2つ。1つは、`grep "guard-files gate" .github/workflows/` のような読むだけの命令を誤って止めるため。もう1つは、合流の前に便7 の gate の判定4（同じ名前の検査を足す PR を落とす）が同じものを止めるため。
- 「GO の文字」の決まり（G）: 正規表現 `\bGO\s*#\s*\d`（大文字小文字を区別する）。

## 3. 作るもの

### 3-1. scripts/agent-hooks/go-identity-guard/guard.py（手元の見張り・PreToolUse）
- 形は scripts/agent-hooks/install-form-guard/guard.py に合わせる。標準ライブラリだけ、ログは同じ jsonl、hook の名前は `go-identity-guard`。
- 環境変数 `GO_IDENTITY_GUARD_LOG` でログの場所を変えられる。
- 内部エラーのときは止める（exit 2）。install-form-guard と違う点。ログの type は hook_internal_error。
- 入力の tool_name が Bash のとき、command に次を順に当てる。
  1. `gh\s+auth\s+switch` → 止める。
  2. `gh\s+auth\s+status` と `--show-token`（または `-t`）が両方ある → 止める。
  3. `find-generic-password` を含む、または `.config/gh/hosts.yml` を含む → 止める（鍵を直接読む道）。
  4. 「PO の鍵を使う」= 正規表現 `(-u|--user)(\s+|=)["']?shingo-ops\b` に合う。合わなければ通す（exit 0）。
  5. 合うときは、次の (a) か (b) に完全一致すれば通す。どちらでもなければ止める。
     - (a) Approve の形。`^GH_TOKEN="\$\(gh auth token --user shingo-ops\)" gh pr review [0-9]+ --approve (--body '[^']*'|--body-file [A-Za-z0-9_./-]+)$`。
       - 本文は単引用符だけ。二重引用符の本文は通さない。中の `$(` と `` ` `` をシェルが実行するため（審査2回目の中1）。
       - 本文に G の文字があれば止める。
       - `--body-file` のときはファイルを読んで G を確かめる。読めなければ止める。道は英数字と `_` `.` `/` `-` だけ。
       - 単引用符の本文の中の `;`・`|`・改行などは文字なので許す。本文の外に何かが付けば、正規表現の `$` で合わなくなる。
     - (b) 読むだけの gh api。`^GH_TOKEN="\$\(gh auth token --user shingo-ops\)" gh api ` で始まる。残りを `shlex.shlex(残り, posix=True, punctuation_chars=True)` に `whitespace_split=True` を付けて語に分け、次の全部に当たれば通す（審査2回目の中2）。分けるときにエラーが出れば止める。
       - 残りの元の文字に、改行・`` ` ``・`$(` があれば止める（`$(` は先頭の GH_TOKEN の1つだけを許す）。
       - 語に `;`・`&`・`&&`・`||`・`>`・`<` などの記号の語（punctuation_chars が作る語のうち `|` 以外）があれば止める。
       - 最初の `|` の語より前（gh api の引数）は、次の語だけを許す:
         - `-` で始まらない語（道）。ちょうど1つ。
         - `--jq` と `-q` と、その次の1語。
         - `--paginate`・`--slurp`・`-i`・`--include`・`--silent`。
         - `-X GET`・`-XGET`・`--method GET`・`--method=GET`。
         - ほかの `-` で始まる語が1つでもあれば止める。`-fbody=x`・`-XPOST`・`--method=POST`・`-F`・`--input` や、印を詰めた語もここで止まる。
       - `|` の後ろは許す。後ろの命令に GH_TOKEN は渡らない。ただし `|` の後ろの語に `gh` か `curl` があれば止める。
- 入力の tool_name が Write か Edit（MultiEdit も）のとき: 決まり W に当たれば止める。
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
- 形は scripts/agent-hooks/cloud/python_version_guard.py に合わせる（標準入力の JSON を読み、止めるときは exit 2 と標準エラーの日本語）。内部エラーは exit 1。dispatch.sh が止める側に扱う。
- tool_name が `mcp__github__` で始まる: tool_input の中の文字の値を全部（入れ子の dict・list も）調べ、G の文字があれば止める。道具の名前では絞らない。
- tool_name が Bash: command に `(^|[\s;|&(])gh\s` か `api.github.com` があり、さらに G の文字もあれば止める。
  - 同じ命令が本文をファイルで渡すときは、ファイルも読む（審査2回目の中3）。対象の印は `--body-file X`・`--body-file=X`・`-F k=@X`・`--field k=@X`・`--input X`・`-d @X`・`--data @X`・`--data-binary @X`・`-T X`。
  - 読んだ中身に G の文字があれば止める。ファイルが読めないとき、または X が `-`（標準入力）のときも止める。
  - この印があるかは文字の形で探す（`(--body-file|--input|-T)(\s+|=)(\S+)` と `(-F|--field|-d|--data|--data-binary)\s+\S*@(\S+)` と `(-d|--data|--data-binary)@?(\S+)` のうち @ で始まるもの）。引用符は外して読む。
- tool_name が Write・Edit・MultiEdit: 決まり W に当たれば止める。G の文字では止めない（試験のファイルに GO の文を書けるように）。
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

## 4. 試験（unittest。外へは繋がない。ログは一時ファイルへ）
test_guard.py（手元）では、各件を subprocess で guard.py に JSON を流して終了コードを見る。
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

test_go_comment_guard.py（クラウド）では、各件を subprocess で go_comment_guard.py に流す。dispatch.sh 経由の件は `CLAUDE_CODE_REMOTE=true` を付けて流す。
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
- C11 dispatch.sh 経由で C1 の入力 → 2。
- C12 dispatch.sh 経由で C4 の入力 → 0。
- C13 Bash `gh pr comment 1 --body-file f.md`、f.md の中身に `GO #1 abcdef1` → 2。
- C14 C13 で、f.md の中身に GO の文字が無い → 0。
- C15 Bash `gh pr comment 1 --body-file missing.md`（ファイルが無い）→ 2。
- C16 Bash `gh pr comment 1 --body-file -` → 2。
- C17 Bash `gh api repos/x/y/issues/1/comments -F body=@f.md`、f.md に `GO #1 abcdef1` → 2。
- C18 Bash `curl -X POST https://api.github.com/repos/x/y/issues/1/comments --data @f.json`、f.json に `GO #1 abcdef1` → 2。

## 5. 確かめ方（実行役が流し、生出力を返す）
- V1 `python3 scripts/agent-hooks/go-identity-guard/test_guard.py` が全部 OK（数を書く）。
- V2 `python3 scripts/agent-hooks/cloud/test_go_comment_guard.py` が全部 OK（数を書く）。
- V3 `bash scripts/agent-hooks/cloud/test.sh` を流し、今ある件が前と同じ結果であること（表を返す）。
- V4 `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/agent-hooks-test.yml'))"` が成功。
- V5 `git diff origin/main --stat` に、「1. 触るファイル」の8件だけが出る。dispatch.sh は `1 insertion(+), 1 deletion(-)`。

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
