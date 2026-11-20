---
mode: handoff
---
# 実装カード 便3: 要件の書類を読まずに「不具合」と言いかけたら止める（R4）

親: [design.md](./design.md) §3 便3・§4（R4 の行）・§6・§8

- 状態: カード作成済み（2026-11-21 Opus）。設計は審査 5 回目で APPROVE（design §9）。PO の実装承認: 2026-11-21 のチャットで、KGI の選択肢1に「…PRマージ、デプロイまで完走させてくれ。」（全文は会話記録）。マージの判断は Opus（GO 委任）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・マージ判断。
- 区分: B（見張りの台本・その試験・週次点検の台本・`.claude/settings.json`・試験の workflow だけ。`migrations/`・`deploy.yml` を触らない）。
- 枝: `release/requirement-library-bin3`（origin/main から新しく作る）。便1 と同時に進めてよい（触るファイルが重ならない）。便2 は本便の合流後に作る（`.claude/settings.json` と `agent-hooks-test.yml` が重なるため）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（クラウドは push まで） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（「読まずに不具合」の見張りと週次の数えだけ） | ○ |
| 5 | 起点の明示（origin/main から新しい枝） | ○（§5 手順1） |
| 6 | PR 欄の書式 | ○（§6。Opus が書く） |
| 7 | 合格基準を出力まで縛る（削除 0 件） | ○（§5 手順7） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（件数の停止なし） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式（停止の3点・終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない | ○ |
| 12 | 停止は不可逆・本番影響のものだけ | ○（§4） |
| 13 | 委任文の定型4点 | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・04-worktree.md・05-pr.md。

基準: origin/main 6fb18f607（2026-11-21）。行番号はその時点の目印。

## 1. 目的（便3で見える変化）

- AI が会話の中で `docs/adr/` か `docs/specs/` を1度も読まずに、最後の返事で「不具合」「バグ」と書いて終わろうとすると、1回だけ止められ「要件の書類を読んでから判定してください」と返される。
- 止めた回が記録に1行ずつ残り、毎週月曜の点検で過去 7 日の数が出る。1 以上なら点検が NG になる。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `.claude/hooks/requirement-bug-claim.py`（新規） | Stop の見張り |
| `.claude/hooks/test_requirement_bug_claim.py`（新規） | 見張りの試験 |
| `.claude/settings.json` | `"Stop"` 配列の後ろに2つ目の要素を足す |
| `.github/workflows/agent-hooks-test.yml` | job を1つ足し、`on.pull_request.paths` に2行足す |
| `scripts/dev/doc-entry-weekly-check.sh` | `BUG_CLAIMS_7D` の節を足す |
| `scripts/dev/test_doc_entry_weekly_check.sh` | `BUG_CLAIMS_7D` の試験を足す |

触らないもの: 既存の見張り（`scripts/agent-hooks/` の下・`.claude/hooks/` の既存3本）・`.claude/settings.json` の既存の要素・agent-console の定期作業の設定・製品コード・`workflow-lint.yml`。

## 3. 作るものの決まり（design.md が正）

### 3-1. 見張り `requirement-bug-claim.py`

- 入力（標準入力の JSON）: `session_id`・`transcript_path`・`stop_hook_active`。仕様は Claude Code の公式の hooks の説明（Stop）を Context7 か公式ページで確かめてから書く。確かめた出典を報告に書く。
- `stop_hook_active` が真なら何もせず終了コード 0。
- transcript（JSONL）を読み、最後の assistant の返事の文に「不具合」か「バグ」があるかを見る。
- 同じ transcript の tool_use のうち、Read の `file_path`、または Bash・Grep・Glob の入力の文字列に `docs/adr/` か `docs/specs/` を含むものが1つでもあれば「読んだ」とする。
- 「不具合・バグ」があり「読んだ」が無いときだけ、標準出力に `{"decision": "block", "reason": "要件の書類を読んでから判定してください。docs/adr/FEATURE-INDEX.md でこの場所の ADR と設計書を引き、読んでから、決まりどおりの動きか不具合かを書き直してください。"}` を出す。
- 同時に `~/.claude/requirement-library/bug-claims.log` に1行（日本時間の `YYYY-MM-DD HH:MM`・タブ・session_id・タブ・返事の最初の 40 字。改行とタブは空白に置き換える）を書き足す。フォルダが無ければ作る。記録の場所は環境変数 `REQUIREMENT_LIBRARY_LOG` があればそれを使う（試験用）。
- どんな失敗（入力が壊れている・transcript が無い・書けない）でも終了コード 0 で何も出さない。
- Python 3.12 で動く標準ライブラリだけ。

### 3-2. 登録 `.claude/settings.json`

- 今の `"Stop"` 配列（中は `dispatch.sh` の要素1つ）の後ろに、2つ目の要素を足す。既存の要素は1文字も変えない:

```json
      { "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/requirement-bug-claim.py\"", "timeout": 10 }
      ] }
```

- 足したあと `python3 -I -c 'import json,sys; json.load(open(sys.argv[1]))' .claude/settings.json` が成功すること。

### 3-3. 試験 `test_requirement_bug_claim.py`（unittest・`python3 -I` で流れる）

- 一時フォルダに transcript の見本を作り、見張りを `subprocess` で流す。記録先は `REQUIREMENT_LIBRARY_LOG` で一時フォルダに向ける。
- 4 つ: 読まずに「不具合」→ `decision: block` が出て記録が1行増える／`docs/adr/ADR-097-x.md` を Read してから「不具合」→ 何も出ない／`stop_hook_active: true` → 何も出ない／壊れた入力（JSON でない）→ 終了コード 0 で何も出ない。
- transcript の見本の形は、公式の説明と、手元の実物の形（Claude Code が書く JSONL の `type: assistant` の `message.content` の `tool_use`・`text`）に合わせる。どの形を使ったかを試験の冒頭のコメントに書く。

### 3-4. 試験の workflow `agent-hooks-test.yml`

- `on.pull_request.paths` に `'.claude/hooks/requirement-*'` と `'.claude/hooks/test_requirement_*'` を足す。
- job を1つ足す（既存の job の形に合わせる）:

```yaml
  requirement-hooks:
    name: requirement hooks test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run requirement-bug-claim tests
        run: python3 -I .claude/hooks/test_requirement_bug_claim.py
```

### 3-5. 週次の数え `doc-entry-weekly-check.sh`

- `LINE_COPY` の節の後ろ、`if [ -z "$NG" ]` の前に節を足す:
  - 記録の場所は `${REQUIREMENT_LIBRARY_LOG:-$HOME_DIR/.claude/requirement-library/bug-claims.log}`。
  - 記録が無ければ `BUG_CLAIMS_7D=0`。あれば、先頭の日付が `TODAY` から 7 日以内（`days_between` を使う・0〜6 日）の行を数える。
  - `echo "BUG_CLAIMS_7D=<数>"`。1 以上なら `add_ng "BUG_CLAIMS_7D=<数>"`。
- `test_doc_entry_weekly_check.sh` に、記録が無い→0・7 日以内に 2 行と 8 日前に 1 行→2 で NG、の 2 つを足す（既存の試験の書き方に合わせる）。

## 4. 委任の決まり

- 長く待たない（`sleep` で待たない）。ファイルは Write・Edit で書く。
- 見張り（フック）に止められたら、言い換えて同じことをしない。止められた文と理由を報告する。
- PR は作らない（push まで）。`--no-verify` を使わない。
- 止めるのは次のときだけ: push が拒否された／公式の説明で Stop の入力・出力の形が §3-1 と違い、どちらに従うか決められない。

## 5. 手順（1 手順 1 コマンド。各コマンドは作業場所のフルパスへの cd で始める）

1. `cd /home/user/salesanchor && git fetch origin main release/requirement-library-design` のあと `bash scripts/new-worktree.sh release/requirement-library-bin3 --claude`（最後の Claude 起動の失敗は無視してよい）。以降は表示された作業場所で行う。
2. `git show origin/release/requirement-library-design:docs/handoff/requirement-library/design.md` の §3 便3 を読む。公式の hooks の説明で Stop の入力と `decision: block` の形を確かめる。
3. §3-1・§3-3 を作り、`python3 -I .claude/hooks/test_requirement_bug_claim.py 2>&1 | tail -20` が成功すること。
4. §3-2・§3-4 を足す。JSON の読み込み確認を流す。
5. §3-5 を足し、`bash scripts/dev/test_doc_entry_weekly_check.sh 2>&1 | tail -20` が成功すること。
6. commit する（1 commit でよい）。
7. `git diff --stat origin/main...HEAD | tail -8` と `git diff --diff-filter=D --name-only origin/main...HEAD | head -5`（0 件）を報告に貼る。
8. `git push -u origin release/requirement-library-bin3` を単独で流す。

## 6. PR（Opus が作る）

- Opus が `gh pr create --base main --head release/requirement-library-bin3` で作る。クラウドは作らない。

## 7. 完了報告

- 冒頭に「便3 完了報告」か「便3 停止報告」。
- 貼るもの（生のまま）: 手順2 で確かめた公式の出典と Stop の入出力の形・手順3 と手順5 の試験の出力・`git diff origin/main...HEAD -- .claude/settings.json` 全文・手順7 の出力・push の結果の最後 5 行・`git log --oneline origin/main..HEAD`。
- 停止のときは 3 点: どの手順で・何が出たか・何をしていないか。
- 最後の行に `DONE` か `BLOCKED: <理由>`。
