#!/usr/bin/env python3
"""許可保守の手順1: 止まった記録を過去7日分、形ごとに数える（読み取りだけ）。

形 = (入口, 理由の分類名, コマンドの先頭2語)。試験した時間帯の記録は除く。
入口: permission-denied（自動判定の停止）/ hook_blocked（フックの停止）。
標準ライブラリだけ。python3 -I で動く。

使い方:
  python3 -I sm_count.py [--denied P] [--events P] [--test-runs P]
                         [--now ISO] [--days 7] [--format md|json|both]
既定のパスは ~/.claude/logs/ 配下の本物。--now は試験用（既定: 現在時刻 UTC）。
"""
import argparse
import datetime
import json
import os
import re
import sys

LOG_DIR = os.path.expanduser("~/.claude/logs")
DEFAULT_DENIED = os.path.join(LOG_DIR, "permission-denied.jsonl")
DEFAULT_EVENTS = os.path.join(LOG_DIR, "agent-events.jsonl")
DEFAULT_TEST_RUNS = os.path.join(LOG_DIR, "test-runs.log")

ENTRY_DENIED = "permission-denied"
ENTRY_HOOK = "hook_blocked"
NO_EXPLANATION = "no explanation"
MAX_EXAMPLES = 3
EXAMPLE_LEN = 120

REASON_RE = re.compile(r"Reason:\s*\[([^\]]+)\]")
BRACKET_RE = re.compile(r"\[([^\]]+)\]")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
MASK_PATTERNS = [
    re.compile(r"(?i)(token|secret|password|passwd|api_key|apikey)[A-Za-z_]*\s*[=:]\s*\S+"),
    re.compile(r"Bearer\s+\S+"),
    re.compile(r"https://discord(app)?\.com/api/webhooks/\S+"),
    re.compile(r"\b[0-9a-fA-F]{32,}\b"),
]


def mask(text):
    for pat in MASK_PATTERNS:
        text = pat.sub("***", text)
    return text


def parse_ts(value):
    if not isinstance(value, str):
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def read_jsonl(path):
    """壊れた行は数えて飛ばす。ファイルが無ければ (None, 0)。"""
    if not os.path.isfile(path):
        return None, 0
    rows, bad = [], 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                bad += 1
    return rows, bad


def read_test_windows(path):
    """各行の先頭2語（開始・終了の時刻）を時間帯として読む。"""
    if not os.path.isfile(path):
        return []
    windows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            start, end = parse_ts(parts[0]), parse_ts(parts[1])
            if start and end and start <= end:
                windows.append((start, end))
    return windows


def in_windows(ts, windows):
    return any(start <= ts <= end for start, end in windows)


def first_two_words(command):
    """環境変数の代入と `cd … &&` を除いた最初の2語。"""
    text = command.strip()
    while True:
        m = re.match(r"^cd\s+\S+\s*&&\s*", text)
        if not m:
            break
        text = text[m.end():]
    words = text.split()
    while words and ENV_ASSIGN_RE.match(words[0]):
        words = words[1:]
    return " ".join(words[:2]) if words else "(empty)"


def denied_command(rec):
    ti = rec.get("tool_input")
    if isinstance(ti, dict):
        cmd = ti.get("command") or ti.get("file_path")
        if isinstance(cmd, str) and cmd.strip():
            return cmd
    tool = rec.get("tool_name")
    return tool if isinstance(tool, str) and tool else "(unknown)"


def denied_reason_class(rec):
    """tool_input 以外の全項目(入れ子を含む)から `Reason: [X]` を探す。"""
    rest = {k: v for k, v in rec.items() if k != "tool_input"}
    m = REASON_RE.search(json.dumps(rest, ensure_ascii=False))
    return m.group(1).strip() if m else NO_EXPLANATION


def hook_reason_class(rec):
    reason = rec.get("reason")
    if isinstance(reason, str):
        m = BRACKET_RE.search(reason)
        if m:
            return m.group(1).strip()
    hook = rec.get("hook")
    return hook if isinstance(hook, str) and hook else NO_EXPLANATION


def shape_of(entry, rec):
    if entry == ENTRY_DENIED:
        cls, cmd = denied_reason_class(rec), denied_command(rec)
    else:
        cls = hook_reason_class(rec)
        head = rec.get("cmd_head")
        cmd = head if isinstance(head, str) and head else "(unknown)"
    return (entry, cls, first_two_words(cmd)), cmd


def count(rows, entry, since, until, windows, stats):
    shapes = {}
    for rec in rows:
        if entry == ENTRY_HOOK and rec.get("type") != ENTRY_HOOK:
            continue
        ts = parse_ts(rec.get("ts"))
        if ts is None:
            stats["no_ts"] += 1
            continue
        if ts < since or ts > until:
            continue
        if in_windows(ts, windows):
            stats["excluded_test"] += 1
            continue
        key, cmd = shape_of(entry, rec)
        slot = shapes.setdefault(key, {"count": 0, "examples": []})
        slot["count"] += 1
        if len(slot["examples"]) < MAX_EXAMPLES:
            slot["examples"].append(mask(cmd.replace("\n", " "))[:EXAMPLE_LEN])
    return shapes


def build(args):
    now = parse_ts(args.now) if args.now else datetime.datetime.now(datetime.timezone.utc)
    if now is None:
        raise SystemExit("ERROR: --now を読めない: %s" % args.now)
    since = now - datetime.timedelta(days=args.days)
    windows = read_test_windows(args.test_runs)
    stats = {"no_ts": 0, "excluded_test": 0, "bad_lines": 0}
    missing = []
    shapes = {}
    for entry, path in ((ENTRY_DENIED, args.denied), (ENTRY_HOOK, args.events)):
        rows, bad = read_jsonl(path)
        stats["bad_lines"] += bad
        if rows is None:
            missing.append(path)
            continue
        shapes.update(count(rows, entry, since, now, windows, stats))
    items = [
        {"entry": k[0], "reason_class": k[1], "command_head": k[2],
         "count": v["count"], "examples": v["examples"]}
        for k, v in shapes.items()
    ]
    items.sort(key=lambda i: (-i["count"], i["entry"], i["reason_class"], i["command_head"]))
    return {
        "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "until": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days": args.days,
        "test_windows": len(windows),
        "excluded_test_records": stats["excluded_test"],
        "records_without_ts": stats["no_ts"],
        "bad_lines": stats["bad_lines"],
        "missing_files": missing,
        "total_denied": sum(i["count"] for i in items if i["entry"] == ENTRY_DENIED),
        "total_hook_blocked": sum(i["count"] for i in items if i["entry"] == ENTRY_HOOK),
        "shapes": items,
    }


def to_markdown(result):
    lines = [
        "# 止まった記録の集計（%s 〜 %s）" % (result["since"], result["until"]),
        "",
        "- permission-denied の件数: %d" % result["total_denied"],
        "- hook_blocked の件数: %d" % result["total_hook_blocked"],
        "- 試験の時間帯: %d 件／除いた記録: %d 件" % (result["test_windows"], result["excluded_test_records"]),
        "- 時刻が読めない記録: %d 件／壊れた行: %d 件" % (result["records_without_ts"], result["bad_lines"]),
        "- 見つからないファイル: %s" % (", ".join(result["missing_files"]) or "なし"),
        "",
        "| 入口 | 理由の分類名 | コマンドの先頭2語 | 件数 | 代表例（伏せ字） |",
        "|---|---|---|---|---|",
    ]
    for it in result["shapes"]:
        ex = " ／ ".join(e.replace("|", "\\|") for e in it["examples"])
        lines.append("| %s | %s | %s | %d | %s |" % (
            it["entry"], it["reason_class"], it["command_head"].replace("|", "\\|"), it["count"], ex))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--denied", default=DEFAULT_DENIED)
    ap.add_argument("--events", default=DEFAULT_EVENTS)
    ap.add_argument("--test-runs", default=DEFAULT_TEST_RUNS)
    ap.add_argument("--now", default=None, help="試験用。ISO 8601")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--format", choices=("md", "json", "both"), default="both")
    args = ap.parse_args(argv)
    result = build(args)
    if args.format in ("md", "both"):
        sys.stdout.write(to_markdown(result))
    if args.format == "both":
        sys.stdout.write("\n")
    if args.format in ("json", "both"):
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
