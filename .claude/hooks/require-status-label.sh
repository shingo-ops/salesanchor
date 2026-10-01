#!/usr/bin/env bash
# サブエージェントの完了報告に DONE / BLOCKED: <理由> / NEEDS_DECISION: <質問> のいずれかが
# 無ければ終了させない見張りフック（「Waiting for CI.」で8時間止まった事故の再発防止）。
# 対応イベント: SubagentStop / PreToolUse(SubagentHandback) / TeammateIdle（記録のみ）
# - agent_type が空（内部エージェント）は絶対にブロックしない
# - スクリプト異常は必ず exit 0（フェイルオープン）。異常は stderr とログへ
# - 同じ agent を連続 MAX_BLOCKS 回までしかブロックしない（無限ループ防止）

set -uo pipefail

LOG_DIR="/tmp/CC報告ファイル"
LOG_FILE="${LOG_DIR}/hook-test.log"
mkdir -p "${LOG_DIR}" 2>/dev/null || true

python3 -c '
import json, os, re, sys, time

LOG = sys.argv[1]
MAX_BLOCKS = 3
LABEL = re.compile(r"^[\s>*`_#-]{0,8}(DONE\b|BLOCKED:\s*\S|NEEDS_DECISION:\s*\S)", re.M)
REASON = (
    "完了報告に DONE / BLOCKED: <理由> / NEEDS_DECISION: <質問> のいずれかの行がありません。"
    "「Waiting for CI.」等で止まらないこと。CI待ちなら同じターン内で `gh pr checks <PR番号> --watch` を実行して"
    "結果が出るまで作業を続け、最後の報告の行頭を DONE / BLOCKED: <理由> / NEEDS_DECISION: <質問> のどれかにすること。"
)

def log(event, agent, decision, note=""):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s event=%s agent_type=%r decision=%s %s\n" % (
                time.strftime("%Y-%m-%dT%H:%M:%S"), event, agent, decision, note))
    except Exception as e:
        print("require-status-label: log failed: %s" % e, file=sys.stderr)

def over_cap(key):
    path = "/tmp/CC報告ファイル/hook-count-%s" % re.sub(r"[^A-Za-z0-9_-]", "_", key or "none")
    try:
        n = int(open(path).read()) if os.path.exists(path) else 0
    except Exception:
        n = 0
    if n >= MAX_BLOCKS:
        return True
    try:
        open(path, "w").write(str(n + 1))
    except Exception:
        pass
    return False

def handback_labelled(transcript):
    try:
        raw = open(os.path.expanduser(transcript), encoding="utf-8").read()
    except Exception:
        return False
    return "SubagentHandback" in raw and bool(re.search(r"(?:\"|\\\\n)\s*(DONE\b|BLOCKED:|NEEDS_DECISION:)", raw))

try:
    d = json.load(sys.stdin)
    ev = d.get("hook_event_name", "")
    agent = d.get("agent_type", "")
    if ev == "SubagentStop":
        msg = d.get("last_assistant_message") or ""
        key = d.get("agent_id") or d.get("session_id")
        if not agent:
            log(ev, agent, "allow", "internal agent")
        elif LABEL.search(msg):
            log(ev, agent, "allow", "label found")
        elif handback_labelled(d.get("agent_transcript_path") or ""):
            log(ev, agent, "allow", "label found in handback transcript")
        elif over_cap(key):
            log(ev, agent, "allow", "cap reached (fail-safe)")
        else:
            log(ev, agent, "block", "msg_len=%d head=%r tail=%r" % (len(msg), msg[:200], msg[-80:]))
            print(json.dumps({"decision": "block", "reason": REASON}, ensure_ascii=False))
    elif ev == "PreToolUse" and d.get("tool_name") == "SubagentHandback":
        msg = (d.get("tool_input") or {}).get("message") or ""
        key = "hb-" + str(d.get("agent_id") or d.get("session_id"))
        if LABEL.search(msg):
            log(ev, agent, "allow", "handback label found")
        elif over_cap(key):
            log(ev, agent, "allow", "handback cap reached (fail-safe)")
        else:
            log(ev, agent, "deny", "handback msg_len=%d head=%r tail=%r" % (len(msg), msg[:200], msg[-80:]))
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "deny", "permissionDecisionReason": REASON}}, ensure_ascii=False))
    elif ev == "TeammateIdle":
        # 入力にメッセージが無く判定不能（未確認）。記録のみで必ず許可
        log(ev, d.get("teammate_name", ""), "allow", "log-only (no message in input)")
    else:
        log(ev, agent, "allow", "ignored event")
except Exception as e:
    print("require-status-label: error (fail-open): %s" % e, file=sys.stderr)
    log("error", "", "allow", "exception=%s" % e)
' "${LOG_FILE}" || echo "require-status-label: python failed (fail-open)" >&2
exit 0
