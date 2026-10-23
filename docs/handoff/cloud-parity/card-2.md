# card-2: クラウドでも手元と同じ見張りを効かせる（段階1 便2）

状態: 設計案作成済み／設計審査済み（同一AIの自己審査・§10）／方針は Opus 決定（PO 委任に基づく。PO 2026-10-23「離席するので、このセッションだけで最後まで完結させる」）／実装未着手
親: design.md §4（移すもののうち「master-register-rules-guard（#6, #40）」「python-version-guard（#43）」「subagent-bash-wait-guard（#47）」「card-lint-hook（#4）」）。便1は card-1.md（#4666 で本線取込済・試行3/3b で K1〜K5 実地合格）。

## 1. 目的
手元（Mac）の `~/.claude/settings.json` にしかない見張り4本（5件）を、クラウドでも同じ条件で止める・知らせるようにする。

| 元 | 手元の時点 | 手元の動き |
|---|---|---|
| #6 master-register-rules-guard | UserPromptSubmit | 依頼文に「マスタ…登録」があれば、登録ルール文書を会話に足す |
| #40 同上 | PreToolUse Write\|Edit\|Bash | 商品作成の命令（TARGETS・:17-22）を含む書込・Bash を、`# rules-ack: <8桁>` が無ければ止める（JSON の deny） |
| #43 python-version-guard | PreToolUse Bash | 3.12 以外の venv 作成・pip install を exit 2 |
| #47 subagent-bash-wait-guard | PreToolUse Bash | 担当（agent_id あり）の Bash で timeout>240000 を exit 2 |
| #4 card-lint-hook | UserPromptSubmit | 依頼文に `END OF CARD` があれば scripts/card-lint.sh で検査し、違反（rc=1）なら exit 2 |

手元の配線（実測 2026-10-23・`~/.claude/settings.json`）:
- UserPromptSubmit: `/Users/tanizawashingo/.claude/scripts/card-lint-hook.sh`、`python3 "$HOME/.claude/scripts/master-register-rules-guard.py"`（timeout 30）
- PreToolUse Write|Edit|Bash: `python3 "$HOME/.claude/scripts/master-register-rules-guard.py"`（timeout 30）
- PreToolUse Bash: `/usr/local/bin/python3 /Users/tanizawashingo/.claude/scripts/python-version-guard.py`（timeout 5）、同 `subagent-bash-wait-guard.py`（timeout 5）

## 2. クラウドで動かない理由（実物の行）
- master-register-rules-guard.py:14 `REPO = "/Users/tanizawashingo/salesanchor"` — ルール文書を `git -C REPO show origin/main:...` で読む（:34-37）。クラウドにこのパスは無い → PreToolUse は「ルール文書が読めない」で常に止まる（:75-77）。
- python-version-guard.py:7-8 `ROOT`/`WT` が Mac の絶対パス。`in_scope`（:22-33）がクラウドの場所を対象外と判定し、何も止めない。
- card-lint-hook.sh:20-23 が `/tmp/card-lint-called.log`・`/tmp/last-hook.json` に書く（試し用の残り）。:25,:46 が `/usr/bin/python3` 直書き。:56-62 の検査本体の探し方が `$HOME/salesanchor` 依存。
- subagent-bash-wait-guard.py は Mac 依存なし。ログ先 `~/.claude/logs/agent-events.jsonl` が無ければ書込を黙って諦める（:27-31）。

## 3. 方針（Opus 決定）
- **正本を1か所にする（データ分散の禁止）**:
  - master-register-rules-guard は、リポジトリの `scripts/agent-hooks/master-register-rules-guard.py` を**そのまま呼ぶ**（写しを作らない）。直すのは :14 の1行だけ。
  - card-lint の検査本体は、リポジトリの `scripts/card-lint.sh` を**そのまま呼ぶ**（写しを作らない）。
  - python-version-guard・subagent-bash-wait-guard・card-lint-hook の3本は、手元の `~/.claude/scripts/` にしか無いため、design.md §5 のとおり `scripts/agent-hooks/cloud/` に写しを置き、先頭に「元: ~/.claude/scripts/<名>」と書く（便1と同じ扱い。差分の点検は design.md §7 の週次点検）。
- **クラウドでは場所の条件を外す**: python-version-guard の写しは、作業場所の判定（ROOT/WT）を持たず、常に対象とする。理由: クラウドの作業機は Sales Anchor 専用（routine の repo は shingo-ops/salesanchor だけ）。
- **止め方は元の見張りと同じにする**: #43・#47・#4 は exit 2、#40 は JSON の deny（exit 0）、#6 は additionalContext（exit 0）。内部エラー時の扱いも元のまま（#40 の PreToolUse は止める側、#43・#47・#4・#6 は素通し）。ただし dispatch.sh は、各見張りの終了コードが 0・2 以外なら止める（便1の既存の決まり・dispatch.sh:20-25 と同じ）。

## 4. 変更するファイル（これ以外は触らない）
### 4-1. `scripts/agent-hooks/master-register-rules-guard.py`（1行）
変更前 :14
```python
REPO = "/Users/tanizawashingo/salesanchor"
```
変更後 :14
```python
REPO = os.environ.get("CLAUDE_PROJECT_DIR") or "/Users/tanizawashingo/salesanchor"
```
（`os` は :9 で import 済み。手元の `~/.claude/scripts/` の写しは変えない。）

### 4-2. 新規 `scripts/agent-hooks/cloud/python_version_guard.py`
- `~/.claude/scripts/python-version-guard.py`（194行）の写し。先頭に `# 元: ~/.claude/scripts/python-version-guard.py（クラウド用の写し。作業場所の判定を外した）` を1行足す。
- 変更点は次の3つだけ:
  1. :7-8 の `ROOT`・`WT` と :22-33 の `in_scope_path`・`in_scope` を削除し、`decide`（:136-143）の `not in_scope(command, cwd)` の条件を外す（`if not isinstance(command, str): return None`）。
  2. :9 の MSG を `'本番は Python 3.12 です。python3.12 -m venv <場所>（または uv venv --python 3.12 <場所>）で作り、その venv の pip を使ってください（py312-guard）'` にする（`/usr/local/bin` は Mac の場所のため外す）。
  3. :6 の LOG の既定を `'/tmp/agent-events.jsonl'` にする（`PY312_GUARD_LOG` で上書き可は残す）。
- それ以外の判定（split_parts・tokens・venv_version・bad_part・mask）は1字も変えない。

### 4-3. 新規 `scripts/agent-hooks/cloud/subagent_bash_wait_guard.py`
- `~/.claude/scripts/subagent-bash-wait-guard.py`（58行）の写し。:1 の「設計:」行の前に `# 元: ~/.claude/scripts/subagent-bash-wait-guard.py（クラウド用の写し）` を足す。
- 変更点は :16 のログ既定を `'/tmp/agent-events.jsonl'` にすることだけ。

### 4-4. 新規 `scripts/agent-hooks/cloud/card_lint_hook.sh`
- `~/.claude/scripts/card-lint-hook.sh`（91行）の写しから、次を変える:
  1. 先頭コメントに `# 元: ~/.claude/scripts/card-lint-hook.sh（クラウド用の写し）` を足す。
  2. :20-23（`/tmp/card-lint-called.log`・`/tmp/last-hook.json` への書込）を削除。`INPUT="$(cat)"` は残す。
  3. `/usr/bin/python3` を `python3` にする。
  4. :45-62 の検査本体の探し方を、`LINT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/card-lint.sh"` の1か所だけにする（`[ -f "$LINT" ] || exit 0` を置く）。
  5. warn モード（:18 の MODE と :80, :86-91）を削除し、rc=1 なら常に exit 2（stderr に「card-lint がカードの不備を検出しました。修正してから貼り直してください。」と検査出力）。
- 「END OF CARD を含まなければ素通し」「プロンプトが取れなければ素通し」「検査本体が無い・落ちた（rc≠1）なら素通し」は元のまま。

### 4-5. `scripts/agent-hooks/cloud/dispatch.sh`
`PreToolUse)` の節を次に置き換え、`UserPromptSubmit)` の節を足す（他の節は変えない）:
```bash
  PreToolUse)
    printf '%s' "$INPUT" | python3 "$DIR/guard_pre_tool.py"
    RC=$?
    if [ "$RC" -ne 0 ] && [ "$RC" -ne 2 ]; then
      echo "BLOCKED(cloud): 見張りの内部エラーのため止めます（終了コード ${RC}）。" >&2
      exit 2
    fi
    [ "$RC" -eq 2 ] && exit 2
    for G in python_version_guard.py subagent_bash_wait_guard.py; do
      printf '%s' "$INPUT" | python3 "$DIR/$G"
      RC=$?
      [ "$RC" -eq 0 ] && continue
      [ "$RC" -eq 2 ] || echo "BLOCKED(cloud): 見張り ${G} の内部エラーのため止めます（終了コード ${RC}）。" >&2
      exit 2
    done
    # 商品登録ルールの見張りは止めるとき JSON（permissionDecision: deny）を標準出力に出す。そのまま流す。
    printf '%s' "$INPUT" | python3 "$DIR/../master-register-rules-guard.py"
    RC=$?
    if [ "$RC" -ne 0 ]; then
      echo "BLOCKED(cloud): 見張り master-register-rules-guard の内部エラーのため止めます（終了コード ${RC}）。" >&2
      exit 2
    fi
    exit 0
    ;;
  UserPromptSubmit)
    printf '%s' "$INPUT" | bash "$DIR/card_lint_hook.sh"
    [ $? -eq 2 ] && exit 2
    printf '%s' "$INPUT" | python3 "$DIR/../master-register-rules-guard.py"
    exit 0
    ;;
```
- 先頭の `[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0`（:2）は変えない（K6）。

### 4-6. `.claude/settings.json`
- `PreToolUse` に `{ "matcher": "Write|Edit", "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/agent-hooks/cloud/dispatch.sh\"", "timeout": 10 } ] }` を足す（`Bash` と `mcp__github__.*` の項目は変えない）。
- `UserPromptSubmit` を新設し、同じ dispatch.sh を timeout 10 で1つだけ配線する。
- 既存の hooks（SessionStart・SubagentStop・TeammateIdle・SubagentHandback・Stop）は1字も変えない。permissions も変えない。

### 4-7. `scripts/agent-hooks/cloud/test.sh`
既存のケースを残したまま、次の B1〜B8 を足す。各ケースは dispatch.sh に JSON を流し、exit コード・標準出力・時間を表にする（既存の書き方に倣う）。商品作成の命令名は台本に直接書かず、`master-register-rules-guard.py` の TARGETS を import して組み立てる（危険語を danger_ops.json から組み立てる便1の書き方と同じ）。
| No | 入力 | 期待 |
|---|---|---|
| B1 | PreToolUse Bash `python3 -c "<TARGETS[0]>1)"`、`MRR_RULES_FILE`=一時ファイル | exit 0、標準出力に `"permissionDecision": "deny"` |
| B1b | 同じ命令の末尾に `# rules-ack: <一時ファイルの sha256 先頭8桁>` | exit 0、標準出力なし |
| B1c | `MRR_RULES_FILE` なし・`CLAUDE_PROJECT_DIR`=作業中の worktree、B1 と同じ命令 | exit 0、deny の本文に `共用商品マスタ 新規登録ルール` が入る（origin/main から読めた証拠。「ルール文書が読めない」にならない） |
| B2 | PreToolUse Write、file_path `/tmp/x.py`、content に TARGETS[0] | deny |
| B2b | 同じで file_path が `/repo/docs/a.md` | 標準出力なし |
| B3 | UserPromptSubmit、prompt「マスタに商品を登録して」 | exit 0、標準出力に `additionalContext` |
| B4 | PreToolUse Bash `python3.11 -m venv .venv` / `pip install requests` / `virtualenv x` | 各 exit 2、標準エラーに `py312-guard` |
| B4b | `python3.12 -m venv .venv` / `uv venv --python 3.12 .venv` / `git status` | 各 exit 0 |
| B5 | PreToolUse Bash、`agent_id` あり、timeout 300000 | exit 2、標準エラーに `subagent-bash-wait-guard` |
| B5b | `agent_id` なし timeout 300000 ／ `agent_id` あり timeout 240000 | 各 exit 0 |
| B6 | UserPromptSubmit、prompt「手順1\n  ls\nEND OF CARD」（受領確認なし） | exit 2、標準エラーに `card-lint` |
| B6b | prompt「こんにちは」 | exit 0、出力なし |
| B7 | B1〜B6b を `CLAUDE_CODE_REMOTE` 未設定で流す | 全て exit 0・標準出力なし・標準エラーなし（K6） |
| B8 | B1〜B6b の各時間 | 1秒以内（K7） |

## 5. 成功条件（便2）
| No | 基準 | 検証方法 |
|---|---|---|
| K8 | クラウドで、#6・#40・#43・#47・#4 が手元と同じ入力で同じ結果（止める・知らせる・通す）になる | test.sh の B1〜B6b が全て期待どおり（手元で `CLAUDE_CODE_REMOTE=true` を付けて実行）。マージ後のクラウド試行4で B1・B3・B4・B6 相当を実地で1回ずつ試し、記録（get_run_log）に止めた文言・足された文が出る |
| K6 | 手元では新しい見張りが一切動かない | test.sh B7 |
| K7 | 新しい依存なし・各1秒以内 | test.sh B8。追加ファイルは python3 標準ライブラリと bash のみ |
| K9 | 既存の見張りと試験を壊さない | test.sh の既存ケースが全て従来どおり。`bash scripts/agent-hooks/test_master_register_rules_guard.sh` が全て合格 |

## 6. リスクと対処
- クラウドに python3.12 が無いと、venv を作る・pip install が全部止まる → 手元と同じ決まり（本番は 3.12）なので止めるのが正しい。クラウド試行4で `python3.12 --version`・`uv --version` を記録し、無ければ別カードで「クラウドの環境設定で 3.12 を入れる」を扱う（今回の対象外）。
- クラウドで `origin/main` が無いと、#40 は商品作成の命令を全部止める → 元の設計どおり（止める側）。試行4で確かめる。
- 写し3本が手元と食い違っていく → design.md §7 の週次点検で差分を見る（便1と同じ）。
- リポジトリは公開 → 足すファイルに秘密・社外秘は無い（見張りの本文と MSG のみ）。

## 7. 戻し方
1 commit の Revert。手元は `CLAUDE_CODE_REMOTE` で素通しのため影響なし。master-register-rules-guard.py:14 も Revert で元に戻る（手元の `~/.claude/scripts/` の写しは今回触らない）。

## 8. 触らない範囲
- `~/.claude/`（手元の見張り・設定）／`guard_pre_tool.py`・`guard_stop.py`・`session_start.py`・`rules.md`・`danger_ops.json`・`sync_danger_ops.py`／`scripts/card-lint.sh`／CI 設定／製品コード（backend・frontend・migrations）。

## 9. 外部・過去事例
便1と同じ（design.md §9）。Anthropic 公式の CLAUDE_CODE_REMOTE による切り分けに従う。数値つきの導入事例は使わない。効果は K6〜K9 とクラウド試行4で測る。

## 10. 審査（Architect・同一AIの自己審査）
判定: APPROVE。
- 根拠: 5件の手元依存は §2 の行で実物を確認した。正本の再利用（#6/#40・card-lint 本体）で分散を増やさない。止め方は元と同じで、K6 の素通しは便1で実地合格済みの入口を使う。
- 未解決（実装の妨げにならない）: クラウドの python3.12 の有無、クラウドで `origin/main` が読めるか → 試行4で記録する（§6）。

<!-- この文書は見張りの設計書で、商品登録の操作ではない。登録ルール本文は確認済み。 rules-ack: d5738ef7 -->
