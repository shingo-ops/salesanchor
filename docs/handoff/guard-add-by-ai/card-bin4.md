# 実装カード 便4: 共通の台本の命令の形を見張る install-form-guard（ADR-1072）

- 版: 第1版（2026-11-10。design.md §13-14 第18版）
- 設計: docs/handoff/guard-add-by-ai/design.md §5-0・§5-5・§13-14
- PO の決定: 2026-11-10 の返事「1」（「見張りを足す方法に変える」を選んだ）。ADR-1072 と実装開始は 2026-11-09 の「1」
- 基準: origin/main 2bf29d9eb3c9c46dce7006a7ebdad6a56a1dc4b7
- 担当: クラウドの Sonnet（実装・試験）。Opus は審査・マージ・導入・PO への案内
- 担当が行わないこと: マージ、~/.claude と ~/.salesanchor-tools に触ること、この見張りを本物の settings.json に入れること、共通の台本（scripts/agent-hooks/ 直下の .sh）を流すこと

## 0. 実物の確かめ（基準の版で、担当は最初にこの表と同じことを確かめる。1行でも違えば NEEDS_DECISION: で止まる）

| 場所 | 中身（行頭） |
|---|---|
| `scripts/dev/consent-audit.py:928` | `_GA_WORDS = ("approve", "updatedInput", "updatedPermissions", "updatedToolOutput", "behavior",` |
| `scripts/dev/consent-audit.py:940` | `def _ga_manifest(text, name):` |
| `scripts/dev/consent-audit.py:972` | `def _ga_words_ok(text):` |
| `scripts/dev/consent-audit.py:1959` | `if __name__ == "__main__":` |
| `scripts/agent-hooks/mac-test-guard/guard.py:26` | `    return os.path.expanduser(os.environ.get('MAC_TEST_GUARD_LOG') or '~/.claude/logs/agent-events.jsonl')` |
| `scripts/agent-hooks/mac-test-guard/guard.py:260` | `            'hook': 'mac-test-guard',` |
| `scripts/agent-hooks/mac-test-guard/test_guard.py:96` | `print('OK %d/%d' % (ok, total))` |
| `.github/workflows/agent-hooks-test.yml:55` | `  install-guard:` |
| `.github/workflows/agent-hooks-test.yml:66` | `        run: python3 scripts/agent-hooks/test_install_guard.py`（ファイルの最終行） |

- `scripts/agent-hooks/install-form-guard/` が無いことを確かめる。あれば止まる。

## 1. 目的
- Opus が手元で共通の台本を流すとき、決まった1行の形（`bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh <名前>`）だけを通し、前に環境変数を付けた形などを、自動判定より前に止める（design.md §13-14 の経緯）。

## 2. 触るファイル（これ以外は触らない）
1. `scripts/agent-hooks/install-form-guard/guard-manifest.json`（新規）
2. `scripts/agent-hooks/install-form-guard/guard.py`（新規）
3. `scripts/agent-hooks/install-form-guard/test_guard.py`（新規）
4. `.github/workflows/agent-hooks-test.yml`（変える。末尾に job を1つ足すだけ）

触らないもの: `scripts/agent-hooks/` のほかの全部（`install-guard.sh`・`mac-test-guard/` を含む）、`scripts/dev/` の全部、`docs/` の全部、台帳。`install.sh`・`rollback.sh` は作らない（入れるのは共通の台本だけ）。

## 3. guard-manifest.json（この中身で1文字も変えない。末尾に改行1つ）
```
{"name": "install-form-guard",
 "files": ["guard.py"],
 "hooks": [{"event": "PreToolUse", "matcher": "Bash", "interpreter": "python3", "file": "guard.py"}],
 "tests": ["test_guard.py"]}
```

## 4. guard.py（標準ライブラリだけ。mac-test-guard/guard.py の書き方に合わせる）
- 冒頭の説明に `# 設計: docs/handoff/guard-add-by-ai/design.md §13-14` と、何を止めるかを2〜3行で書く。
- 定数:
  - `ALLOW = re.compile(r'bash ~/\.salesanchor-tools/scripts/agent-hooks/install-guard\.sh [a-z0-9-]+')`（使うときは `ALLOW.fullmatch(command)`。`^`・`$` は書かない。fullmatch なので末尾の改行も通さない）
  - `NEEDLES = ('install-guard', '.salesanchor-tools/scripts/agent-hooks')`
  - `MSG`: `🚫 BLOCKED [install-form-guard]: 見張りを入れる共通の台本は、決まった1行の形でだけ流します（前に環境変数や cd を付けない・引数は名前1つ・ほかの命令をつながない）。形: bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh <名前>。中を読むだけなら Read ツールを使ってください（決まり: docs/handoff/guard-add-by-ai/design.md §13-14）。`
- `log_path()`: 環境変数 `INSTALL_FORM_GUARD_LOG` があればそれ、無ければ `~/.claude/logs/agent-events.jsonl`（expanduser）。
- `targeted(command)`: `command` から `'`・`"`・`\` を全部取り除き、`.lower()` した文字列に、NEEDLES のどれかが含まれれば True。
- `log_event(kind, command, reason)`: mac-test-guard の log_event と同じ形（`ts`・`type`・`hook` は `install-form-guard`・`reason`・`cmd_head`（先頭120字））。`matched_part` は書かない。書けなくても例外を外に出さない。
- `main()`:
  1. 標準入力を `json.loads`。dict でなければ、または `tool_input` の `command` が文字列でなければ 0 を返す。
  2. `targeted(command)` が False なら 0。
  3. `ALLOW.fullmatch(command)` が一致すれば 0。
  4. それ以外は `log_event('hook_blocked', command, 'install form mismatch')`、標準エラーに `MSG + '\n'`、2 を返す。
  5. 1〜3 の途中の例外は `log_event('hook_internal_error', command, type(e).__name__)` して 0（fail-open。mac-test-guard と同じ）。
- `if __name__ == '__main__':` は mac-test-guard の 312〜318 行と同じ形（`sys.exit(rc)`）。
- 許可券の道は作らない（`permits` という語も書かない）。
- §5-5 の語を書かない: `approve`・`updatedInput`・`updatedPermissions`・`updatedToolOutput`・`behavior`・`additionalContext`。`permissionDecision` と `allow` を同じ行に書かない。大文字小文字を区別した部分一致で当たるので、変数名・説明・文字列のどれにも書かない（`ALLOW` は大文字なので当たらない。`allow` を小文字で書かない）。

## 5. test_guard.py（標準ライブラリだけ。使い方: `python3 test_guard.py [guard.py のパス]`。mac-test-guard/test_guard.py の形に合わせる）
共通: guard.py を `subprocess.run([sys.executable, GUARD], input=<JSON>, capture_output=True, text=True, env=<os.environ の写しに INSTALL_FORM_GUARD_LOG=<一時のファイル>>)` で流す。JSON は `{"tool_name": "Bash", "tool_input": {"command": <命令>}}`。本物の ~/.claude には書かない。最後に `print('OK %d/%d' % (ok, total))`、1件でも FAIL なら exit 1。

以下で `S = 'bash ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh'`。

| 番号 | 命令 | 期待 |
|---|---|---|
| F1 通す | `S + ' mac-test-guard'`・`S + ' install-form-guard'`・`S + ' a-1'` | exit 0・標準エラーが空 |
| F2 止める（前に付ける） | `'CLAUDE_DIR=/Users/x/.claude ' + S + ' mac-test-guard'`・`'PATH=/usr/bin:/bin ' + S + ' mac-test-guard'`・`'HOME=/tmp/h ' + S + ' x'`・`'env ' + S + ' x'`・`'cd /tmp && ' + S + ' x'`・`' ' + S + ' x'`・`'command ' + S + ' x'`・`'sh ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x'`・`'bash $HOME/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x'`・`'bash /Users/x/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x'` | exit 2・標準エラーに `[install-form-guard]` |
| F3 止める（後ろ・引数） | `S`・`S + ' '`・`S + ' a b'`・`S + ' x\n'`・`S + ' x; ls'`・`S + ' x && ls'`・`S + ' x | cat'`・`S + ' x > /tmp/o'`・`S + ' x 2>&1'`・`S + ' $(echo x)'`・`S + ' `echo x`'`・`S + ' X'`・`S + ' x_y'`・`S + ' x &'` | exit 2 |
| F4 止める（ほかの台本・読み方） | `'bash ~/.salesanchor-tools/scripts/agent-hooks/mac-test-guard/install.sh'`・`'bash ~/.salesanchor-tools/scripts/agent-hooks/mac-test-guard/rollback.sh'`・`'cat ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh'`・`'git show origin/main:scripts/agent-hooks/install-guard.sh'`・`'grep -n x scripts/agent-hooks/install-guard.sh'`・`"bash ~/.salesanchor-tools/scripts/agent-hooks/install-gu''ard.sh x"`・`'bash ~/.salesanchor-tools/scripts/agent-hooks/install-gu\\ard.sh x'`（Python の文字列で \ が1つ）・`'BASH ~/.salesanchor-tools/scripts/agent-hooks/install-guard.sh x'`・`'bash ~/.SALESANCHOR-TOOLS/scripts/agent-hooks/x.sh'` | exit 2 |
| F5 止めない（関係ない命令） | `'git status'`・`'ls'`・`'python3 scripts/agent-hooks/test_install_guard.py'`・`'python3 scripts/agent-hooks/install-form-guard/test_guard.py'`・`'cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py sync'`・`'git diff -- scripts/agent-hooks/mac-test-guard/'`・`'echo installguard'` | exit 0・標準エラーが空 |
| F6 記録 | F2 の1件目を流す前と後で、一時の記録ファイルの行数 | 1 増え、最後の行の JSON の `hook` が `install-form-guard`・`type` が `hook_blocked` |
| F7 記録しない | F1 の1件目・F5 の1件目 | 記録ファイルの行数が増えない |
| F8 壊れた入力 | 入力 `not json`／`{"tool_input": {"command": 5}}`／`{"tool_input": "x"}`／`[]` | どれも exit 0 |
| F9 札と語 | `scripts/dev/consent-audit.py` を `importlib.util.spec_from_file_location` で読み込み、`_ga_manifest(<guard-manifest.json の中身>, "install-form-guard")` が None でない。`_ga_words_ok(<guard.py の中身>)` が True | 両方満たす |

- F9 のパスはこの試験ファイルの場所から `../../dev/consent-audit.py` で決める（`HERE` からの相対）。
- 1つの番号で複数の命令を流すときは、命令ごとに ok/FAIL を数える（ラベルに命令を入れる）。

## 6. .github/workflows/agent-hooks-test.yml の変更
- 66 行目の後ろに、次の job を足す（`install-guard` の job と同じ形。`if`・`continue-on-error`・`|| true` を書かない）。
```

  install-form-guard:
    name: install-form-guard test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - name: Run install-form-guard tests
        run: python3 scripts/agent-hooks/install-form-guard/test_guard.py
```
- 3行目の説明の `install-guard: ADR-1072）` を `install-guard・install-form-guard: ADR-1072）` に変える。ほかの行は触らない。

## 7. 止まる条件（NEEDS_DECISION: で止まり、Opus に返す）
- §0 の表と実物が1行でも違う。
- F1〜F9 のどれかが、guard.py を §4 のとおりに書いても通らない（期待の表と guard の決まりが食い違う）。
- F9 で `_ga_manifest` が None になる・`_ga_words_ok` が False になる。
- `python3 scripts/agent-hooks/mac-test-guard/test_guard.py` と `python3 scripts/agent-hooks/test_install_guard.py` が、変える前と後で結果が違う。
- §2 に無いファイルを触りたくなった。

## 8. 想定する分かれ道
| 起きること | どうするか |
|---|---|
| F3 の `S + ' x\n'` で、fullmatch が末尾の改行を通してしまう | `re.fullmatch` は末尾の改行を通さない。通るなら `$` を書いていないか見直す。それでも通るなら止まる |
| F4 の引用符・\ の形が、取り除いた後に当たらない | `targeted` の取り除きの順と対象（`'`・`"`・`\` の3つ）を見直す。直らなければ止まる |
| F9 で consent-audit.py の読み込みが失敗する（import の副作用など） | 1959 行の `if __name__` の下にしか実行が無いはず。失敗するなら止まる（consent-audit.py は触らない） |
| guard.py に書きたい語が §5-5 の語に当たる | 言い換える。`allow` は小文字で書かない |

## 9. 提出
- commit は §2 のファイルだけ。commit の文は英語で、末尾に `Co-Authored-By: Claude Sonnet` の行を付ける。commit の文に台本の名前（`install-guard`）を書かない（導入後に手元の見張りが当たるため。`install-form-guard` は書いてよい）。
- push は `release/install-form-guard` に1回。PR は作らない（Opus が作る）。
- 返す報告: 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` のどれか。§0 の確かめの結果、`python3 scripts/agent-hooks/install-form-guard/test_guard.py` の出力、§7 の既存2試験の変える前と後の出力、push した HEAD を書く。生の出力はそのまま貼る。
