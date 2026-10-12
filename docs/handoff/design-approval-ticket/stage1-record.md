# 段1 実施記録（停止理由の記録）

設計: docs/handoff/design-approval-ticket/design.md §5 段1（PR #4173）。カード STAGE1-LOGGING の実施記録。

## PO の許可（原文・2026-10-13）

「段1許可: ~/.claude/scripts の4フックのバックアップ・permission-denied-log.sh 新規作成・4フックへの停止理由の記録追加・登録スクリプト作成・文書PR を Sonnet が行うことを許可する」

## 実施内容

- 変更前のバックアップ: /Users/tanizawashingo/.claude/scripts/.backup/20261013004946/（4フックを cp -p で写し、cmp で一致を確認）
- 新規: /Users/tanizawashingo/.claude/scripts/permission-denied-log.sh と permission_denied_log.py（標準入力の JSON に ts を足して ~/.claude/logs/permission-denied.jsonl に追記。伏せ字・常に exit 0・標準出力なし）
- 4フックに、止める直前の hook_blocked 記録（~/.claude/logs/agent-events.jsonl に1行追記）を追加。止める・通すの判定は変えていない。記録の失敗は無視する。
- ~/.claude/settings.json は編集していない。登録は PO が po-register-stage1.sh で行う（作っただけで実行していない）。

## 事実: gh-scope-guard.sh は無効化されている

/Users/tanizawashingo/.claude/scripts/gh-scope-guard.sh の2行目が無条件の exit 0 であり、フック全体が動作しない（block に到達しない）。そのため記録の追加は到達しないコードへの追加になり、試験は「通る入力が exit 0 のまま・hook_blocked が増えない」ことだけを確認した。無効化の解除は範囲外で、していない。

## 試験の表

入力は Write ツールでファイルに書き、`bash <フック> < <入力ファイル>` で渡した（コマンドは実行されない）。「増えた行数」は agent-events.jsonl の hook_blocked の増加数。
変更前 = バックアップ、変更後（控え）= .backup/20261013004946/work/、変更後（本物）= 反映後の本物。

| フック | 入力 | exit 変更前 | exit 変更後（控え） | exit 変更後（本物） | 増えた行数（控え / 本物） |
|---|---|---|---|---|---|
| worktree-only-guard | cd $(pwd) && ls（止まる） | 2 | 2 | 2 | +1 / +1 |
| worktree-only-guard | ls（通る） | 0 | 0 | 0 | 0 / 0 |
| agent-danger-hook | rm -rf /tmp/stage1-test-nonexistent（danger_ops） | 2 | 2 | 2 | +1 / +1 |
| agent-danger-hook | ssh prod1 psql < /tmp/stage1-test.sql（psql-write） | 2 | 2 | 2 | +1 / +1 |
| agent-danger-hook | ls /Users/tanizawashingo/.claude/permits（permits 自己発行） | 2 | 2 | 2 | +1 / +1 |
| agent-danger-hook | git clean -fd（本店の破壊的 git） | 2 | 2 | 2 | +1 / +1 |
| agent-danger-hook | ls（通る） | 0 | 0 | 0 | 0 / 0 |
| pr-body-guard | gh pr create --title x --body-file /nonexistent/stage1-test-body.md（止まる） | 2 | 2 | 2 | +1 / +1 |
| pr-body-guard | ls（通る） | 0 | 0 | 0 | 0 / 0 |
| gh-scope-guard | gh pr list（通る。止まる入力は無効化のため作れない） | 0 | 0 | 0 | 0 / 0 |

試験時の注意:
- pr-body-guard は同じディレクトリの extract-pr-body.py を使う。バックアップ側と控え側には試験のために extract-pr-body.py を写した。
- agent-danger-hook の「git -C <path> clean」の形は、フックの正規表現（`git\s+clean`）に当たらず止まらない。止まる形は `git clean -fd`。
- pr-body-guard の `--body "bad body"` は、控えにも extract-pr-body.py が無い状態では「検証スキップ」で exit 0 になった（試験環境の不足であり、上記で解消済み）。

## 変更した各フックの差分（diff -u バックアップ 本物 の全文）

秘密値は含まれない（検索した項目は伏せ字の正規表現のみ）。

```diff
--- /Users/tanizawashingo/.claude/scripts/.backup/20261013004946/worktree-only-guard.sh	2026-09-11 12:59:39
+++ /Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh	2026-10-13 00:51:25
@@ -4,6 +4,42 @@
 # Based on live SHA256 f6238554fe17f73b2c0e5430f4a3c209ba04593dc3cff0bc9f3f40feda89d10f.
 # Does not replace or modify the separate CW01/CW05 guard.
 INPUT=$(cat 2>/dev/null || true)
+
+# 停止理由の記録（設計承認チケット 段1: 記録のみ。止める・通すの判定には影響しない）
+# 使い方: _hook_blocked_log "<フック名>" "<止める理由>"  → agent-events.jsonl に hook_blocked を1行追記
+_hook_blocked_log() {
+  printf '%s' "${INPUT:-}" | HB_HOOK="$1" HB_REASON="$2" python3 -c '
+import sys, os, re, json, datetime
+try:
+    pats = [
+        re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
+        re.compile(r"Bearer\s+\S+"),
+        re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
+    ]
+    def mask(s):
+        for p in pats:
+            s = p.sub("***", s)
+        return s
+    cmd = ""
+    try:
+        d = json.loads(sys.stdin.read())
+        ti = d.get("tool_input", {}) if isinstance(d, dict) else {}
+        cmd = ti.get("command") or ti.get("file_path") or ""
+    except Exception:
+        cmd = ""
+    rec = {
+        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
+        "type": "hook_blocked",
+        "hook": os.environ.get("HB_HOOK", ""),
+        "reason": mask(os.environ.get("HB_REASON", "").split("\n")[0]),
+        "cmd_head": mask(str(cmd))[:120],
+    }
+    with open(os.path.expanduser("~/.claude/logs/agent-events.jsonl"), "a", encoding="utf-8") as f:
+        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
+except Exception:
+    pass
+' >/dev/null 2>&1 || true
+}
 TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
 # Write ツール: ~/.claude/permits/ への書き込みを禁止（PR-P1 2026-08-30）
 if [ "$TOOL_NAME" = "Write" ]; then
@@ -22,6 +58,7 @@
 PYEOF
     )
     if [ "$BLOCKED" = "yes" ]; then
+      _hook_blocked_log "worktree-only-guard" "BLOCKED: ~/.claude/permits/ への書き込みは禁止されています。"
       echo 'BLOCKED: ~/.claude/permits/ への書き込みは禁止されています。(worktree-only-guard)' >&2
       exit 2
     fi
@@ -59,19 +96,23 @@
 except (ValueError, TypeError, AttributeError, OSError, IndexError):
     print("BLOCKED: working directory could not be resolved safely.", file=sys.stderr)
     sys.exit(2)
-') || exit 2
+') || { _hook_blocked_log "worktree-only-guard" "BLOCKED: working directory could not be resolved safely."; exit 2; }
 TARGET_ROOT=$(git -C "$TARGET_DIR" rev-parse --show-toplevel 2>/dev/null || true)
 BRANCH=$(git -C "$TARGET_DIR" branch --show-current 2>/dev/null || true)
 if [[ -z "$BRANCH" ]] && echo "$COMMAND" | grep -qE 'git commit'; then
+  _hook_blocked_log "worktree-only-guard" "BLOCKED: target branch could not be verified."
   echo 'BLOCKED: target branch could not be verified.' >&2; exit 2
 fi
 if [[ "$ROOT" == "/Users/tanizawashingo/crm-app-new" || "$ROOT" == /private/tmp/* || "$TARGET_ROOT" == "/Users/tanizawashingo/crm-app-new" || "$TARGET_ROOT" == /private/tmp/* ]] && echo "$COMMAND" | grep -qE 'git (push|fetch)'; then
+  _hook_blocked_log "worktree-only-guard" "BLOCKED: old clone push/fetch is prohibited."
   echo 'BLOCKED: old clone push/fetch is prohibited.' >&2; exit 2
 fi
 if [[ "$BRANCH" == "develop" || "$BRANCH" == "main" ]] && echo "$COMMAND" | grep -qE 'git commit'; then
+  _hook_blocked_log "worktree-only-guard" "BLOCKED: protected target branch ($BRANCH)."
   printf 'BLOCKED: protected target branch (%s). Target directory: %s\n' "$BRANCH" "$TARGET_DIR" >&2; exit 2
 fi
 if echo "$COMMAND" | grep -qE 'git push.*(--force|--force-with-lease).*(origin )?(develop|main)'; then
+  _hook_blocked_log "worktree-only-guard" "BLOCKED: force push to origin develop/main is prohibited."
   echo 'BLOCKED: force push to origin develop/main is prohibited.' >&2; exit 2
 fi
 exit 0
--- /Users/tanizawashingo/.claude/scripts/.backup/20261013004946/agent-danger-hook.sh	2026-09-30 21:27:05
+++ /Users/tanizawashingo/.claude/scripts/agent-danger-hook.sh	2026-10-13 00:51:47
@@ -12,6 +12,42 @@
 
 # stdin から JSON を読む
 INPUT=$(cat)
+
+# 停止理由の記録（設計承認チケット 段1: 記録のみ。止める・通すの判定には影響しない）
+# 使い方: _hook_blocked_log "<フック名>" "<止める理由>"  → agent-events.jsonl に hook_blocked を1行追記
+_hook_blocked_log() {
+  printf '%s' "${INPUT:-}" | HB_HOOK="$1" HB_REASON="$2" python3 -c '
+import sys, os, re, json, datetime
+try:
+    pats = [
+        re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
+        re.compile(r"Bearer\s+\S+"),
+        re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
+    ]
+    def mask(s):
+        for p in pats:
+            s = p.sub("***", s)
+        return s
+    cmd = ""
+    try:
+        d = json.loads(sys.stdin.read())
+        ti = d.get("tool_input", {}) if isinstance(d, dict) else {}
+        cmd = ti.get("command") or ti.get("file_path") or ""
+    except Exception:
+        cmd = ""
+    rec = {
+        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
+        "type": "hook_blocked",
+        "hook": os.environ.get("HB_HOOK", ""),
+        "reason": mask(os.environ.get("HB_REASON", "").split("\n")[0]),
+        "cmd_head": mask(str(cmd))[:120],
+    }
+    with open(os.path.expanduser("~/.claude/logs/agent-events.jsonl"), "a", encoding="utf-8") as f:
+        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
+except Exception:
+    pass
+' >/dev/null 2>&1 || true
+}
 
 # コマンド文字列を抽出（Bash ツールの場合）
 COMMAND=$(echo "$INPUT" | python3 -c "
@@ -96,6 +132,7 @@
       exit 0
     fi
 
+    _hook_blocked_log "agent-danger-hook" "BLOCKED [psql-write-guard]: psql-write:$REASON"
     echo "🚫 BLOCKED [psql-write-guard]: 本番DBへの直接書き込みは禁止されています。" >&2
     echo "   検知パターン: $REASON" >&2
     echo "   読み取り（-c \"SELECT ...\"）は許可されています。" >&2
@@ -135,6 +172,7 @@
   printf '{"type":"permits_self_issue_blocked","session":"%s","branch":"%s","ts":"%s"}\n' \
     "$SESSION_NAME" "$BRANCH" "$TIMESTAMP" >> "$EVENTS_LOG"
 
+  _hook_blocked_log "agent-danger-hook" "BLOCKED [permits-guard]: permits ディレクトリへの直接アクセス"
   echo "🚫 BLOCKED [permits-guard]: permits ディレクトリへの直接アクセスは禁止されています。" >&2
   echo "   permits の発行・読取は scripts/permit-danger.sh 経由のみ許可されます。" >&2
   exit 2
@@ -288,6 +326,7 @@
         exit 0
       fi
 
+      _hook_blocked_log "agent-danger-hook" "BLOCKED [scope-destruct-guard]: $SCOPE_DESTRUCT_MATCHED"
       echo "🚫 BLOCKED [scope-destruct-guard]: 本店での破壊的 git 操作は禁止されています。" >&2
       echo "   検知操作: $SCOPE_DESTRUCT_MATCHED" >&2
       echo "   worktree 内での実行は許可されています。" >&2
@@ -402,6 +441,7 @@
   /Users/tanizawashingo/.claude/scripts/notify.sh "危険な操作をブロックしました: $MATCHED" "$SPEAKER" &
 
   # ブロックメッセージを stderr に出力（Claude が読む）
+  _hook_blocked_log "agent-danger-hook" "BLOCKED: '$MATCHED' は不可逆操作"
   echo "🚫 BLOCKED: '$MATCHED' は不可逆操作のためブロックされました。" >&2
   echo "   しんごさんの承認が必要です。" >&2
   echo "   許可する場合: bash scripts/permit-danger.sh \"$MATCHED\"" >&2
--- /Users/tanizawashingo/.claude/scripts/.backup/20261013004946/pr-body-guard.sh	2026-09-29 10:56:53
+++ /Users/tanizawashingo/.claude/scripts/pr-body-guard.sh	2026-10-13 00:51:47
@@ -7,6 +7,42 @@
 # stdin から JSON を読み込む
 INPUT="$(cat)"
 
+# 停止理由の記録（設計承認チケット 段1: 記録のみ。止める・通すの判定には影響しない）
+# 使い方: _hook_blocked_log "<フック名>" "<止める理由>"  → agent-events.jsonl に hook_blocked を1行追記
+_hook_blocked_log() {
+  printf '%s' "${INPUT:-}" | HB_HOOK="$1" HB_REASON="$2" python3 -c '
+import sys, os, re, json, datetime
+try:
+    pats = [
+        re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
+        re.compile(r"Bearer\s+\S+"),
+        re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
+    ]
+    def mask(s):
+        for p in pats:
+            s = p.sub("***", s)
+        return s
+    cmd = ""
+    try:
+        d = json.loads(sys.stdin.read())
+        ti = d.get("tool_input", {}) if isinstance(d, dict) else {}
+        cmd = ti.get("command") or ti.get("file_path") or ""
+    except Exception:
+        cmd = ""
+    rec = {
+        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
+        "type": "hook_blocked",
+        "hook": os.environ.get("HB_HOOK", ""),
+        "reason": mask(os.environ.get("HB_REASON", "").split("\n")[0]),
+        "cmd_head": mask(str(cmd))[:120],
+    }
+    with open(os.path.expanduser("~/.claude/logs/agent-events.jsonl"), "a", encoding="utf-8") as f:
+        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
+except Exception:
+    pass
+' >/dev/null 2>&1 || true
+}
+
 # tool_name を取得（Bash 以外はスキップ）
 TOOL_NAME="$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || true)"
 if [[ "$TOOL_NAME" != "Bash" ]]; then
@@ -93,6 +129,7 @@
 # exit 3: --body-file が指定されたが読み込めなかった（未存在・読み取り不可）。
 # 本文を検証できない以上、安全側に倒してブロックする（fail-closed）。
 if [[ "$EXTRACT_RC" -eq 3 ]]; then
+  _hook_blocked_log "pr-body-guard" "BLOCKED [pr-body-guard]: --body-file を読み込めないため PR本文を検証できません。"
   echo "🚫 BLOCKED [pr-body-guard]: --body-file を読み込めないため PR本文を検証できません。" >&2
   echo "   ファイルの存在・パス・読み取り権限を確認してください。" >&2
   exit 2
@@ -111,5 +148,6 @@
 if echo "$PR_BODY" | bash "$VALIDATE_SCRIPT"; then
   exit 0
 else
+  _hook_blocked_log "pr-body-guard" "BLOCKED [pr-body-guard]: validate-pr-body.sh が不合格 (PR本文の検証失敗)"
   exit 2
 fi
--- /Users/tanizawashingo/.claude/scripts/.backup/20261013004946/gh-scope-guard.sh	2026-08-31 13:13:29
+++ /Users/tanizawashingo/.claude/scripts/gh-scope-guard.sh	2026-10-13 00:51:48
@@ -41,6 +41,42 @@
 
 # stdin から JSON を読む
 INPUT=$(cat)
+
+# 停止理由の記録（設計承認チケット 段1: 記録のみ。止める・通すの判定には影響しない）
+# 使い方: _hook_blocked_log "<フック名>" "<止める理由>"  → agent-events.jsonl に hook_blocked を1行追記
+_hook_blocked_log() {
+  printf '%s' "${INPUT:-}" | HB_HOOK="$1" HB_REASON="$2" python3 -c '
+import sys, os, re, json, datetime
+try:
+    pats = [
+        re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
+        re.compile(r"Bearer\s+\S+"),
+        re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
+    ]
+    def mask(s):
+        for p in pats:
+            s = p.sub("***", s)
+        return s
+    cmd = ""
+    try:
+        d = json.loads(sys.stdin.read())
+        ti = d.get("tool_input", {}) if isinstance(d, dict) else {}
+        cmd = ti.get("command") or ti.get("file_path") or ""
+    except Exception:
+        cmd = ""
+    rec = {
+        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
+        "type": "hook_blocked",
+        "hook": os.environ.get("HB_HOOK", ""),
+        "reason": mask(os.environ.get("HB_REASON", "").split("\n")[0]),
+        "cmd_head": mask(str(cmd))[:120],
+    }
+    with open(os.path.expanduser("~/.claude/logs/agent-events.jsonl"), "a", encoding="utf-8") as f:
+        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
+except Exception:
+    pass
+' >/dev/null 2>&1 || true
+}
 if [ -z "$INPUT" ]; then
   exit 0
 fi
@@ -318,6 +354,7 @@
     exit 0
   fi
 
+  _hook_blocked_log "gh-scope-guard" "BLOCKED [gh-scope-guard]: $BLOCKED_REASON"
   echo "" >&2
   echo "🚫 BLOCKED [gh-scope-guard]: 他セッションのブランチ・PRへの操作は禁止されています。" >&2
   echo "   理由    : $BLOCKED_REASON" >&2
```
