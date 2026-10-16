# 実装カード: py312-guard（手元の Python 部品入れを 3.12 に揃える見張り）

設計: [design.md](design.md)（§2 K1〜K7・§3）。根拠: [recon.md](recon.md)。PO 実装承認: 2026-10-16 チャット「y」（この設計で実装に進める）。

## 守ること
- 触ってよいのは §変更 のファイルだけ。既存の hook・Mac の PATH・本番・CI は触らない
- cd を使わない（絶対パス）。Sales Anchor の作業場所で 3.12 以外の venv を作らない
- /Users/tanizawashingo/.claude/settings.json は変更前に /Users/tanizawashingo/.claude/settings.json.bak-py312-guard-<YYYYmmddHHMMSS> へ控えを取り、変更後に `python3.12 -m json.tool` で形を確かめる。形が壊れたら控えから戻して BLOCKED:
- 迷ったら全停止して `NEEDS_DECISION:`。報告は DONE / BLOCKED: / NEEDS_DECISION: で始め、生出力の保存パス（/tmp/CC報告ファイル/py312-guard/impl/）を添える

## 実物点検（最初に）
1. /Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh の `_hook_blocked_log` の呼び方と、その関数の定義場所・agent-events.jsonl に書く 1 行の形を読む
2. /Users/tanizawashingo/.claude/scripts/launch_guard_for_sim.py の stdin の読み方・終了の仕方・settings.json での登録の書き方（command・timeout）を読む
3. Bash の hook 入力 JSON に `cwd` があること（既存 hook の読み方で確認）。無ければ NEEDS_DECISION:

## 変更
### 1. 新規 /Users/tanizawashingo/.claude/scripts/python-version-guard.py
- design §3 の判定 1〜5 をそのまま。判定は純関数 `decide(command: str, cwd: str) -> str | None`（拒否文言か None）に分け、main は stdin JSON → decide → 拒否なら記録＋標準エラー＋exit 2、それ以外 exit 0
- 例外はすべて捕まえて exit 0（K4）
- 記録は 1 で読んだ形と同じ 1 行（hook 名 `python-version-guard`）。記録に失敗しても判定は変えない
- 対象の場所（K3）: cwd が `/Users/tanizawashingo/salesanchor` そのものか配下、または `/Users/tanizawashingo/worktrees/salesanchor/` 配下。命令に `cd <その配下>` を含むときも対象
- 拒否文言（1 行）: `本番は Python 3.12 です。/usr/local/bin/python3.12 -m venv <場所> で作り、その venv の pip を使ってください（py312-guard）`
- 先頭に設計パスのコメント 1 行

### 2. 新規 /Users/tanizawashingo/.claude/scripts/tests/test_python_version_guard.py
- unittest（標準ライブラリのみ）。K1 の 12 形を拒否、K2 の 10 形を通過、K3 の場所外 2 本、K4（壊れた JSON を stdin に与えて終了 0、読めない pyvenv.cfg）、K5（文言 120 字以内・`/usr/local/bin/python3.12 -m venv` を含む）
- venv の形は一時ディレクトリに `pyvenv.cfg`（`version = 3.14.3` / `version = 3.12.8`）と `bin/` だけ作る
- K1 の recon P2 の形は recon.md P2 の命令（`…` は実在の worktree 配下の仮パスに置き換え）

### 3. 変更 /Users/tanizawashingo/.claude/settings.json
- PreToolUse の matcher `Bash` の既存の並びの最後に 1 本: command は `/usr/local/bin/python3 /Users/tanizawashingo/.claude/scripts/python-version-guard.py`（2 で読んだ既存 Python hook と同じ書き方に合わせる）、timeout 5
- 変更前後の PreToolUse 件数（26 → 27）を記録

### 4. 文書（salesanchor worktree `/Users/tanizawashingo/worktrees/salesanchor/release-py312-guard`）
- `AGENTS.md:45` の Python 3.12 の行の直後に 1 行: 「手元の venv は `/usr/local/bin/python3.12 -m venv <場所>` で作る。Sales Anchor の作業場所で 3.12 以外の venv 作成・pip install は見張り（/Users/tanizawashingo/.claude/scripts/python-version-guard.py）が止める。変数経由などは防げない」
- コミット `docs: 手元の Python は 3.12 で venv を作る決まりと見張りを AGENTS.md に追記`（末尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）して push。PR は作らない

## 完了の確認
1. `/usr/local/bin/python3.12 -m unittest discover -s ~/.claude/scripts/tests -p 'test_python_version_guard.py' -v` 全合格
2. 手で 2 本: `echo '{"tool_input":{"command":"python3 -m venv /tmp/x"},"cwd":"/Users/tanizawashingo/salesanchor"}' | <hook>` → 終了 2、`…"/usr/local/bin/python3.12 -m venv /tmp/x"…` → 終了 0
3. settings.json の json.tool 合格と件数 27
4. K6・K7 の実機は Opus が行う（担当はしない）

## 想定分岐
- 既存 hook に Python 版の選び方の決まりがあり `/usr/local/bin/python3` と違う → 既存に合わせ、報告に書く
- AGENTS.md:45 が Python 3.12 の行でない → 行を探して直後に入れ、行番号を報告
- 試験のどれかが設計どおりに書くと落ちる（設計の矛盾） → 期待値を変えず NEEDS_DECISION:
