---
mode: handoff
---
# 実装カード 便2b: コマンドで読んだときも、その場所の決まりを見せる（R2・R3）

親: [design.md](./design.md) §3 便2b・§3 便2・§4（R2・R3 の行）

- 状態: カード作成済み（2026-11-21 Opus）。PO の方向の承認: 2026-11-21 チャット「1」（「写すときも声をかけるように直し、もう一度20回解かせて確かめる」への回答）。マージの判断は Opus（GO 委任）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・マージ判断。
- 区分: B（見張りの台本・その試験・`.claude/settings.json` の1行だけ）。
- 枝: `release/requirement-library-bin2b`。着手の前提: 便2（`.claude/hooks/requirement-context.py`・`"PostToolUse"` 節）が origin/main にあること。無ければ止める。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（クラウドは push まで） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（Bash で読んだファイルにも見張りを広げるだけ） | ○ |
| 5 | 起点の明示（origin/main から新しい枝） | ○（§5 手順1） |
| 6 | PR 欄の書式 | ○（§6。Opus が書く） |
| 7 | 合格基準を出力まで縛る（削除 0 件・settings.json は1行の差し替えだけ） | ○（§5 手順7） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（件数の停止なし） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式（停止の3点・終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない | ○ |
| 12 | 停止は不可逆・本番影響のものだけ | ○（§4） |
| 13 | 委任文の定型4点 | ○（§4） |

## 1. 目的（便2b で見える変化）

- AI が `sed -n 370,470p backend/app/routers/companies.py` のようなコマンドで、索引の「コードの場所」に当たるファイルを読むと、その直後に便2 と同じ「この場所には決まりがあります: ADR-060・ADR-058・ADR-097・…。計画の前に docs/specs/customer-management/README.md・docs/specs/db-ssot/deal-removal/design.md を読んでください。」が AI に渡る。
- 同じ行の文は1つの会話で1回だけ（便2 と同じ印を使う）。`Read` などで開いたときの動きは変えない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `.claude/hooks/requirement-context.py` | `Bash` のときにコマンドからファイルを拾う処理を足す |
| `.claude/hooks/test_requirement_context.py` | 試験を 5 つ足す（今の 5 つは変えない） |
| `.claude/settings.json` | `"PostToolUse"` の `matcher` の1行を差し替える |

触らないもの: `scripts/ci/feature_index_lib.py`・`docs/adr/FEATURE-INDEX.md`・`.claude/hooks/requirement-bug-claim.py`・`.github/workflows/agent-hooks-test.yml`（今の step がこの試験の台本を流す）・`.claude/settings.json` のほかの行・製品コード。

## 3. 作るものの決まり（design.md §3 便2b が正）

### 3-1. 見張り `requirement-context.py`

- 入力: `session_id`・`cwd`・`tool_name`・`tool_input`（`Bash` では `tool_input.command`）。公式の hooks の説明（共通の入力に `cwd`、Bash の `tool_input.command`）を Context7 か公式ページで確かめ、出典を報告に書く。
- 照らす元のファイルの一覧を作る:
  - `tool_input.file_path` が文字列であれば `[file_path]`（今と同じ。絶対パスでなければ何もしない）。
  - そうでなく `tool_name == "Bash"` で `tool_input.command` が文字列なら、§3-2 の決まりでファイルを拾う。
  - どちらでもなければ何も出さない。
- 一覧の各ファイルに、今の照らし方（親フォルダで `git rev-parse --show-toplevel`・直下からの相対・`docs/adr/FEATURE-INDEX.md` を `feature_index_lib.read_index`・`feature_index_lib.match_glob`）をかける。`git rev-parse` の結果は同じ親フォルダごとに1回だけ流して使い回す。索引は同じ直下ごとに1回だけ読む。
- 印・文の形・`hookSpecificOutput` の出し方・失敗で終了コード 0 は今と同じ。1回の呼び出しで当たった行は、全部のファイルを通して機能キーワードで1つにまとめる。
- Python 3.12 の標準ライブラリだけ。

### 3-2. コマンドからファイルを拾う決まり

1. `lx = shlex.shlex(command, posix=True, punctuation_chars=True)`・`lx.whitespace_split = True` で語に分ける。`ValueError` なら `command.split()` を使う。語は先頭から 200 個まで。
2. 空の語と `-` で始まる語は飛ばす。
3. 語が絶対パスでなければ、入力の `cwd`（文字列で絶対パスのときだけ）とつなぐ。`cwd` が使えなければ、その語は飛ばす。
4. `*`・`?`・`[` のどれかを含む語は `glob.glob(つないだパス)` で広げ、先頭の 50 件まで使う。含まない語はそのまま使う。
5. `os.path.isfile` が真のものだけ残す（フォルダは使わない）。同じパスは1つにまとめ、50 個まで。

### 3-3. 登録 `.claude/settings.json`

- `"PostToolUse"` 節の `"matcher": "Read|Edit|Write|MultiEdit"` を `"matcher": "Read|Edit|Write|MultiEdit|Bash"` に替える。ほかは1文字も変えない。
- 替えたあと `python3 -I -c 'import json,sys; json.load(open(sys.argv[1]))' .claude/settings.json` が成功すること。

### 3-4. 試験 `test_requirement_context.py`（足す 5 つ）

今の見本のリポジトリの作り方を使い、入力に `"tool_name": "Bash"`・`"cwd": <見本の直下>`・`"tool_input": {"command": ...}` を渡す。

1. `sed -n 1,5p backend/app/x.py` → `additionalContext` に ADR 番号が入る。
2. `cat backend/app/*.py` → 同じく入る。
3. `grep -rn foo backend/app` → 何も出ない（フォルダだけ）。
4. `grep -n "backend/app/nothing.py" backend/app/missing.py`（どちらのファイルも見本に作らない）→ 何も出ない（実在しないファイルは使わない）。
5. `sed -n 1p 'backend/app/x.py`（引用符が閉じていない）→ 終了コード 0（出るかどうかは問わない）。

## 4. 委任の決まり

- 長く待たない（`sleep` で待たない）。ファイルは Write・Edit で書く。
- 見張り（フック）に止められたら、言い換えて同じことをしない。止められた文と理由を報告する。
- PR は作らない（push まで）。`--no-verify` を使わない。
- 止めるのは次のときだけ: 着手の前提（便2 の合流）が満たされない／`feature_index_lib.py` を直さないと作れない／公式の説明で `cwd` か `tool_input.command` が §3-1 と違う／push が拒否された。

## 5. 手順（1 手順 1 コマンド。各コマンドは作業場所のフルパスへの cd で始める）

1. `cd /home/user/salesanchor && git fetch origin main` のあと `bash scripts/new-worktree.sh release/requirement-library-bin2b --claude`（最後の Claude 起動の失敗は無視してよい）。以降は表示された作業場所で行う。
2. 前提の確認: `git ls-tree --name-only origin/main .claude/hooks/requirement-context.py` に1行出ること。`grep -c 'Read|Edit|Write|MultiEdit"' .claude/settings.json` が 1 であること。違えば止める。
3. `git show origin/main:docs/handoff/requirement-library/design.md` の §3 便2b と、今の `.claude/hooks/requirement-context.py`・`.claude/hooks/test_requirement_context.py` を読む。公式の hooks の説明で `cwd` と Bash の `tool_input.command` を確かめる。
4. §3-1・§3-2・§3-4 を作り、`python3 -I .claude/hooks/test_requirement_context.py 2>&1 | tail -20` が成功すること（10 件）。
5. 本物の索引での確かめ（どちらも `<作業場所>` は手順1 で表示された実際のパスに置き換える）:
   - `printf '%s' '{"session_id":"card-check-b1","cwd":"<作業場所>","tool_name":"Bash","tool_input":{"command":"sed -n 370,470p backend/app/routers/companies.py"}}' | python3 -I .claude/hooks/requirement-context.py` の出力に `ADR-097` と `deal-removal` が入ること。
   - `printf '%s' '{"session_id":"card-check-b2","cwd":"<作業場所>","tool_name":"Bash","tool_input":{"command":"git status"}}' | python3 -I .claude/hooks/requirement-context.py` が何も出さないこと。
6. §3-3 を替え、JSON の読み込み確認を流して commit する（1 commit でよい）。
7. `git diff --stat origin/main...HEAD | tail -6`・`git diff --diff-filter=D --name-only origin/main...HEAD | head -5`（0 件）・`git diff origin/main...HEAD -- .claude/settings.json`（`-` 1行・`+` 1行で、違いは `|Bash` だけ）を報告に貼る。
8. `git -C <作業場所> push -u origin release/requirement-library-bin2b` を単独で流す。

## 6. PR（Opus が作る）

- Opus が `gh pr create --base main --head release/requirement-library-bin2b` で作る。クラウドは作らない。

## 7. 完了報告

- 冒頭に「便2b 完了報告」か「便2b 停止報告」。
- 貼るもの（生のまま）: 手順2 の出力・手順3 で確かめた公式の出典と入力の形・手順4 の試験の出力・手順5 の出力全文（2つ）・手順7 の出力・push の結果の最後 5 行・`git log --oneline origin/main..HEAD`。
- 停止のときは 3 点: どの手順で・何が出たか・何をしていないか。
- 最後の行に `DONE` か `BLOCKED: <理由>`。
