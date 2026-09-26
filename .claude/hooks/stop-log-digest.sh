#!/usr/bin/env bash
# 昨日の自動ストップ要約を表示する読み取り専用フック。
# - 破壊操作なし
# - 失敗しても exit 0

set -uo pipefail

LOG_FILE="${HOME}/.claude/logs/agent-events.jsonl"

python3 - "$LOG_FILE" <<'PY'
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

log_path = Path(sys.argv[1])
if not log_path.exists():
    print("ログなし")
    raise SystemExit(0)

type_re = re.compile(r'"type"\s*:\s*"((?:\\.|[^"])*)"')
ts_re = re.compile(r'"ts"\s*:\s*"((?:\\.|[^"])*)"')

known_types = {
    "gh_scope_blocked",
    "worktree_bypass_blocked",
    "danger_detected",
    "access_blocked",
    "stop",
}


def unescape_json_string(raw: str) -> str:
    try:
        return bytes(raw, "utf-8").decode("unicode_escape")
    except Exception:
        return raw


def extract_fields(line: str):
    line = line.strip()
    if not line:
        return None

    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj.get("type"), obj.get("ts")
    except Exception:
        pass

    type_match = type_re.search(line)
    ts_match = ts_re.search(line)
    if not type_match and not ts_match:
        return None

    typ = unescape_json_string(type_match.group(1)) if type_match else None
    ts = unescape_json_string(ts_match.group(1)) if ts_match else None
    return typ, ts


def parse_ts(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


today = datetime.now().astimezone().date()
yesterday = today - timedelta(days=1)
stale_cutoff = today - timedelta(days=2)

counts = Counter()
latest_ts = None
recovered_any = False

try:
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            extracted = extract_fields(line)
            if not extracted:
                continue
            typ, ts_raw = extracted
            recovered_any = True

            dt = parse_ts(ts_raw)
            if dt and (latest_ts is None or dt > latest_ts):
                latest_ts = dt

            if not dt or dt.astimezone().date() != yesterday:
                continue

            key = typ if typ in known_types else "other"
            counts[key] += 1
except Exception:
    print("集計できませんでした")
    raise SystemExit(0)

if not recovered_any:
    print("集計できませんでした")
    raise SystemExit(0)

total = sum(counts.values())

print(f"== 昨日の自動ストップ要約 [{yesterday.isoformat()}] ==")
print(f"対象期間: {yesterday.isoformat()} 00:00:00 - {yesterday.isoformat()} 23:59:59 (local)")
for key in ["gh_scope_blocked", "worktree_bypass_blocked", "danger_detected", "access_blocked", "stop", "other"]:
    print(f"{key}: {counts.get(key, 0)}件")

top3 = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:3]
if top3:
    print("トップ3:")
    for idx, (key, value) in enumerate(top3, 1):
        print(f"{idx}. {key} {value}件")
else:
    print("トップ3: なし")

print(f"前日の総ストップ件数: {total}件")

if latest_ts and latest_ts.astimezone().date() <= stale_cutoff:
    print("※ログ更新が止まっている可能性")

raise SystemExit(0)
PY

exit 0
