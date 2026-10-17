#!/usr/bin/env python3
"""review-gate record.py — PostToolUse (matcher: SubagentHandback)

審査役 (reviewer, model opus) の報告の最後の VERDICT 行を読み、APPROVE で、
かつ sha が PR の今の HEAD と一致するときだけ記録を残す。
設計: docs/handoff/review-gate-hook/design.md §5-2 / ADR-1029
常に exit 0 (審査役の報告を妨げない)。標準ライブラリのみ。
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

VERDICT_RE = re.compile(
    r"^VERDICT: (APPROVE|REQUEST_CHANGES|REJECT) on ([0-9a-f]{40}) PR #(\d+)\s*$",
    re.M,
)


def gate_dir():
    return os.path.abspath(
        os.path.expanduser(os.environ.get("REVIEW_GATE_DIR") or "~/.claude/review-gate")
    )


def gh_path():
    env = os.environ.get("REVIEW_GATE_GH")
    if env:
        return env
    return shutil.which("gh") or "/opt/homebrew/bin/gh"


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(entry):
    try:
        d = gate_dir()
        os.makedirs(d, mode=0o700, exist_ok=True)
        entry = dict(entry)
        entry["at"] = now()
        entry["hook"] = "record"
        with open(os.path.join(d, "log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def meta_path(transcript_path, agent_id):
    ident = agent_id[len("agent-"):] if agent_id.startswith("agent-") else agent_id
    base = os.path.basename(transcript_path)
    parent = os.path.dirname(transcript_path)
    if base.startswith("agent-") and base.endswith(".jsonl") and os.path.basename(parent) == "subagents":
        return ident, os.path.join(parent, "agent-%s.meta.json" % ident)
    stem = transcript_path[: -len(".jsonl")] if transcript_path.endswith(".jsonl") else transcript_path
    return ident, os.path.join(stem, "subagents", "agent-%s.meta.json" % ident)


def check_model(transcript_path, agent_id):
    """(ok, meta_model, reason)"""
    if not transcript_path or not agent_id:
        return False, None, "no transcript_path or agent_id"
    ident, mpath = meta_path(transcript_path, agent_id)
    try:
        with open(mpath, encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return False, None, "meta.json not found"
    model = str(meta.get("model") or "")
    if meta.get("agentType") != "reviewer" or "opus" not in model.lower():
        return False, model, "meta is not reviewer/opus"
    jpath = os.path.join(os.path.dirname(mpath), "agent-%s.jsonl" % ident)
    if os.path.isfile(jpath):
        try:
            with open(jpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("type") != "assistant":
                        continue
                    m = (rec.get("message") or {}).get("model")
                    if m is not None and not str(m).startswith("claude-opus"):
                        return False, model, "assistant model %s is not opus" % m
        except Exception:
            pass
    return True, model, ""


def repo_from_url(url):
    m = re.match(r"https?://[^/]+/([^/]+)/([^/]+)/pull/\d+", url or "")
    return (m.group(1), m.group(2)) if m else None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "SubagentHandback" or data.get("agent_type") != "reviewer":
        return 0
    agent_id = str(data.get("agent_id") or "")
    message = (data.get("tool_input") or {}).get("message") or ""
    transcript = data.get("transcript_path") or ""
    cwd = data.get("cwd") or os.getcwd()

    ok, meta_model, why = check_model(transcript, agent_id)
    if not ok:
        log({"result": "skip", "reason": why, "agent_id": agent_id})
        return 0
    found = VERDICT_RE.findall(message)
    if not found:
        log({"result": "skip", "reason": "no VERDICT line", "agent_id": agent_id})
        return 0
    verdict, sha, pr = found[-1]
    if verdict != "APPROVE":
        log({"result": "skip", "reason": "verdict " + verdict, "pr": int(pr), "agent_id": agent_id})
        return 0
    try:
        out = subprocess.run(
            [gh_path(), "pr", "view", pr, "--json", "headRefOid,url"],
            cwd=cwd if os.path.isdir(cwd) else None,
            capture_output=True, text=True, timeout=60,
        )
        info = json.loads(out.stdout)
    except Exception:
        log({"result": "skip", "reason": "gh pr view failed", "pr": int(pr)})
        return 0
    ownrepo = repo_from_url(info.get("url"))
    if not ownrepo or info.get("headRefOid") != sha:
        log({"result": "skip", "reason": "sha mismatch or bad url", "pr": int(pr)})
        return 0
    owner, repo = ownrepo
    rec_dir = os.path.join(gate_dir(), "records")
    try:
        os.makedirs(rec_dir, mode=0o700, exist_ok=True)
        os.chmod(gate_dir(), 0o700)
        os.chmod(rec_dir, 0o700)
        path = os.path.join(rec_dir, "%s__%s-%s-%s.json" % (owner, repo, pr, sha))
        rec = {
            "pr": int(pr), "repo": "%s/%s" % (owner, repo), "head": sha,
            "verdict": "APPROVE", "agent_id": agent_id,
            "meta_model": meta_model, "recorded_at": now(),
        }
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.chmod(path, 0o600)
    except Exception as e:
        log({"result": "skip", "reason": "write failed: %s" % type(e).__name__})
        return 0
    log({"result": "recorded", "pr": int(pr), "head": sha, "agent_id": agent_id})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
