# 実装カード 便S1: 点検が控えのフォルダを数えない（設計 §13 改訂8）

発行: Claude Opus（設計統括）2026-10-27
根拠: design.md §4-2（hook_files は「.backup を除く」）・§13（改訂8）
PO 承認: 設計を作る（2026-10-27「1」）。実装の承認（2026-10-27「1」直しを作る）
作業場所: クラウドで `bash scripts/new-worktree.sh release/consent-audit-skip-backup`（--claude なし）で作った作業場所（branch release/consent-audit-skip-backup）。この外では書かない。

## やること
1. `scripts/dev/consent-audit.py`
   - 新しい関数 `_backup_path_hashes(hook_dir)` を collect_permissions（:615）の前に足す。`os.walk(hook_dir)` で、相対パスのどこかの段のフォルダ名に `.backup` を含むファイル（シンボリックリンクと通常ファイル以外は除く）の、相対パスの `sha8` の集合を返す。読めないときは空の集合。
   - collect_permissions の `for root, dirs, names in os.walk(p["hook_dir"]):`（:626）の直後の `dirs.sort()`（:627）を `dirs[:] = [d for d in sorted(dirs) if ".backup" not in d]` に替える。ファイル名の `if ".backup" in n: continue`（:629-630）はそのまま残す。
   - run_permissions の `old, old_ts = load_snapshot(snap_path)`（:989）の直後に、old が None でなく `"hook_files"` を持つときだけ、`bk = _backup_path_hashes(p["hook_dir"])` を取り、`old["hook_files"] = [x for x in old["hook_files"] if x.split("|", 1)[0] not in bk]` にする。ほかのキーと比べ方は変えない。
2. `scripts/dev/permission-delegation-tests.py`
   - design §13-3 の A21-1・A21-2・A21-3・A21-5 を足す。一時 HOME で行う。A21-2 は「直す前の式」（`.backup` フォルダの中も数える式）で写しの hook_files を作り、それを前回の写しとして書いてから run_permissions を流し、B に `hook_files` が出ないことを確かめる。A21-3 はその後に `.backup/<時刻>/` を消して、その要素が「減」の行に出ることを確かめる。
   - 試験の補助（mutate など）は今の書き方に合わせる。
3. 試験を流す: `python3 -I -B scripts/dev/permission-delegation-tests.py` と `python3 -I -B scripts/dev/consent-unit-tests.py`。生出力は /tmp/CC報告ファイル/permission-delegation/s1/tests.txt に保存する。
4. コミットと push（クラウドで行うのは push まで）
   - コミット文は fix: の型で、末尾に空行と `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
   - `git push -u origin release/consent-audit-skip-backup`。PR は作らない（手元で Opus が shingo-cc 名義で作る）。
   - design.md・本カード・`.claude-pipeline/active-work.d/` は変えない・commit しない。

## 触らない
- ~/.claude/ 配下、~/.codex/ 配下、~/.salesanchor-tools 配下、agent-console の実物、本店 ~/salesanchor の作業ツリー。
- consent-audit.py の A〜E の判定、写しの形とキー名、出力の形、同意の照合。perm-change.py。

## 止まる条件（BLOCKED: / NEEDS_DECISION: で Opus に戻す）
- 実物の行番号が本カードと合わない。
- 試験が通らない原因が設計にある。
- フックに止められた（言い換えて再試行しない）。
- design.md に無い条件が必要になった。

## 報告
最後の返事は `DONE: PR #<番号> 試験 <合格数>/<総数>` か `BLOCKED: <理由1行>` か `NEEDS_DECISION: <1行>` の1行だけ。
