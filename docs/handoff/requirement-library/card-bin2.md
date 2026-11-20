---
mode: handoff
---
# 実装カード 便2: ファイルを開いた瞬間に、その場所の決まりを見せる（R2・R3）

親: [design.md](./design.md) §3 便2・§4（R2・R3 の行）・§6・§8

- 状態: カード作成済み（2026-11-21 Opus）。設計は審査 5 回目で APPROVE（design §9）。PO の実装承認: 2026-11-21 のチャットで、KGI の選択肢1に「…PRマージ、デプロイまで完走させてくれ。」（全文は会話記録）。マージの判断は Opus（GO 委任）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・マージ判断。
- 区分: B（見張りの台本・その試験・`.claude/settings.json`・試験の workflow だけ）。
- 枝: `release/requirement-library-bin2`。**着手の前提: 便1（`scripts/ci/feature_index_lib.py` と 5 列の索引）と便3（`.claude/settings.json` の Stop の2つ目・`agent-hooks-test.yml` の job）が origin/main に入っていること。** 入っていなければ止める。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（クラウドは push まで） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（開いた瞬間の見張りだけ） | ○ |
| 5 | 起点の明示（便1・便3 合流後の origin/main から新しい枝） | ○（§5 手順1・2） |
| 6 | PR 欄の書式 | ○（§6。Opus が書く） |
| 7 | 合格基準を出力まで縛る（削除 0 件・既存の要素が変わらない） | ○（§5 手順7） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（件数の停止なし） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式（停止の3点・終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない | ○ |
| 12 | 停止は不可逆・本番影響のものだけ | ○（§4） |
| 13 | 委任文の定型4点 | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・04-worktree.md・05-pr.md。

基準: 便1・便3 合流後の origin/main（発行時は未合流。手順2 で確かめる）。

## 1. 目的（便2で見える変化）

- AI が `backend/app/routers/companies.py` のような、索引の「コードの場所」に当たるファイルを開く（Read・Edit・Write・MultiEdit）と、その直後に「この場所には決まりがあります: ADR-097（…）。計画の前に docs/specs/db-ssot/deal-removal/design.md を読んでください。」という文が AI に渡る。
- 同じ行の文は1つの会話で1回だけ。当たらないファイルでは何も出ない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `.claude/hooks/requirement-context.py`（新規） | PostToolUse の見張り |
| `.claude/hooks/test_requirement_context.py`（新規） | 見張りの試験 |
| `.claude/settings.json` | `"PostToolUse"` 節を新しく足す |
| `.github/workflows/agent-hooks-test.yml` | 便3 の job `requirement-hooks` に step を1つ足し、`on.pull_request.paths` に2行足す |

触らないもの: `scripts/ci/feature_index_lib.py`（便1 のまま使う。直す必要があれば止める）・`docs/adr/FEATURE-INDEX.md`・`.claude/hooks/requirement-bug-claim.py`・`.claude/settings.json` の既存の節・製品コード・`workflow-lint.yml`。

## 3. 作るものの決まり（design.md が正）

### 3-1. 見張り `requirement-context.py`

- 入力（標準入力の JSON）: `session_id`・`tool_name`・`tool_input.file_path`。仕様は Claude Code の公式の hooks の説明（PostToolUse・`hookSpecificOutput.additionalContext`）を Context7 か公式ページで確かめてから書く。出典を報告に書く。
- 部品の読み込み: `sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ci"))` のあと `import feature_index_lib`。失敗したら終了コード 0 で何も出さない。
- `file_path` の親フォルダで `git rev-parse --show-toplevel` を流し（`subprocess`・timeout 3 秒）、その直下からの相対パスにする。リポジトリの外・git が無い・失敗 → 何も出さない。
- 同じ直下の `docs/adr/FEATURE-INDEX.md` を `feature_index_lib.read_index` で読み、「コードの場所」が `-` でない行で、`、` 区切りの glob のどれかに `feature_index_lib.match_glob` で当たる行を集める（`fnmatch` を直接使わない）。
- 印: `${TMPDIR:-/tmp}/requirement-context/<session_id>`（session_id は英数字・`-`・`_` 以外を `_` に置き換える）に、出した行の機能キーワードを1行ずつ書く。印にある行は出さない。
- 出す行が1つ以上あれば、標準出力に次の JSON を1つ出す（行ごとに1文を改行でつなぐ）:

```json
{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "この場所には決まりがあります: ADR-097・ADR-1076（会社 / 顧客情報 …）。計画の前に docs/specs/db-ssot/deal-removal/design.md を読んでください。"}}
```

  - 「ADR-…」は正準 ADR 欄の番号（`feature_index_lib.adr_ids_in`）を `ADR-` つきで `・` でつなぐ。かっこの中は機能キーワード。設計書欄が `-` なら「計画の前に、その ADR を docs/adr/ で読んでください。」にする。設計書欄のリンクは `docs/adr/` からの相対を `posixpath.normpath` で直下からのパスに直す。
- どんな失敗でも終了コード 0。Python 3.12 の標準ライブラリだけ。

### 3-2. 登録 `.claude/settings.json`

- `"hooks"` の中に `"PostToolUse"` 節を新しく足す（置く場所は `"PreToolUse"` の直後）。既存の節は1文字も変えない:

```json
    "PostToolUse": [
      { "matcher": "Read|Edit|Write|MultiEdit", "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/requirement-context.py\"", "timeout": 5 }
      ] }
    ],
```

- 足したあと JSON の読み込み確認（`python3 -I -c 'import json,sys; json.load(open(sys.argv[1]))' .claude/settings.json`）が成功すること。手順1 の時点で `"PostToolUse"` が既にあれば止める。

### 3-3. 試験 `test_requirement_context.py`（unittest・`python3 -I` で流れる）

- 一時フォルダに見本のリポジトリ（`git init`・`docs/adr/FEATURE-INDEX.md` の 5 列の表 1 行・当たるファイル `backend/app/x.py`・`scripts/ci/feature_index_lib.py` は本物をコピー）を作り、見張りを `subprocess` で流す。`TMPDIR` は一時フォルダに向ける。見張りの台本は見本の `.claude/hooks/` にコピーして流す（`parents[2]` が見本の直下になる）。
- 5 つ: 当たる → `additionalContext` に ADR 番号と設計書のパスが入る／当たらない → 何も出ない／同じ session で2回目 → 何も出ない／壊れた入力 → 終了コード 0 で何も出ない／リポジトリの外のファイル → 何も出ない。

### 3-4. 試験の workflow `agent-hooks-test.yml`

- `on.pull_request.paths` に `'scripts/ci/feature_index_lib.py'` と `'docs/adr/FEATURE-INDEX.md'` を足す（`.claude/hooks/requirement-*`・`test_requirement_*` は便3 で足し済み。無ければ足す）。
- 便3 の job `requirement-hooks` の最後に step を足す:

```yaml
      - name: Run requirement-context tests
        run: python3 -I .claude/hooks/test_requirement_context.py
```

## 4. 委任の決まり

- 長く待たない（`sleep` で待たない）。ファイルは Write・Edit で書く。
- 見張り（フック）に止められたら、言い換えて同じことをしない。止められた文と理由を報告する。
- PR は作らない（push まで）。`--no-verify` を使わない。
- 止めるのは次のときだけ: 着手の前提（便1・便3 の合流）が満たされない／`feature_index_lib.py` を直さないと作れない／公式の説明で PostToolUse の入出力が §3-1 と違い、どちらに従うか決められない／push が拒否された。

## 5. 手順（1 手順 1 コマンド。各コマンドは作業場所のフルパスへの cd で始める）

1. `cd /home/user/salesanchor && git fetch origin main release/requirement-library-design` のあと `bash scripts/new-worktree.sh release/requirement-library-bin2 --claude`（最後の Claude 起動の失敗は無視してよい）。以降は表示された作業場所で行う。
2. 前提の確認: `git ls-tree --name-only origin/main scripts/ci/feature_index_lib.py .claude/hooks/requirement-bug-claim.py` に 2 行出ること。`grep -c PostToolUse .claude/settings.json` が 0 であること。違えば止める。
3. `git show origin/release/requirement-library-design:docs/handoff/requirement-library/design.md` の §3 便2 と、`scripts/ci/feature_index_lib.py` を読む。公式の hooks の説明で PostToolUse の入出力を確かめる。
4. §3-1・§3-3 を作り、`python3 -I .claude/hooks/test_requirement_context.py 2>&1 | tail -20` が成功すること。
5. 本物の索引での確かめ: `printf '%s' '{"session_id":"card-check","tool_name":"Read","tool_input":{"file_path":"<作業場所のフルパス>/backend/app/routers/companies.py"}}' | python3 -I .claude/hooks/requirement-context.py` の出力に `ADR-097` と `deal-removal` が入ること（`<作業場所のフルパス>` は手順1 で表示された実際のパスに置き換えて流す）。
6. §3-2・§3-4 を足し、JSON の読み込み確認を流して commit する（1 commit でよい）。
7. `git diff --stat origin/main...HEAD | tail -8`・`git diff --diff-filter=D --name-only origin/main...HEAD | head -5`（0 件）・`git diff origin/main...HEAD -- .claude/settings.json`（足した行だけで、`-` の行が無いこと）を報告に貼る。
8. `git push -u origin release/requirement-library-bin2` を単独で流す。

## 6. PR（Opus が作る）

- Opus が `gh pr create --base main --head release/requirement-library-bin2` で作る。クラウドは作らない。

## 7. 完了報告

- 冒頭に「便2 完了報告」か「便2 停止報告」。
- 貼るもの（生のまま）: 手順2 の出力・手順3 で確かめた公式の出典と PostToolUse の入出力の形・手順4 の試験の出力・手順5 の出力全文・手順7 の出力・push の結果の最後 5 行・`git log --oneline origin/main..HEAD`。
- 停止のときは 3 点: どの手順で・何が出たか・何をしていないか。
- 最後の行に `DONE` か `BLOCKED: <理由>`。
