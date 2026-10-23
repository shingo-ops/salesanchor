#!/usr/bin/env python3
"""共用商品の新規登録ルールを必ず読ませるフック（PreToolUse / UserPromptSubmit）。

設計: docs/handoff/master-register-rules-hook/design.md §4-2
標準ライブラリのみ。ルール文書は MRR_RULES_FILE（試験用）か origin/main から読む。
"""
import hashlib
import json
import os
import re
import subprocess
import sys

REPO = os.environ.get("CLAUDE_PROJECT_DIR") or "/Users/tanizawashingo/salesanchor"
RULES_PATH = "docs/specs/product-master/registration-rules.md"
TITLE = "共用商品の新規登録ルール（必読）"
TARGETS = (
    "create_product(",
    "INSERT INTO public.products",
    "INSERT INTO products",
    "/tcg/products/create",
)
EXEMPT_PATHS = ("/backend/", "/frontend/", "/docs/", "/migrations/", "/tests/")
READ_ONLY_CMDS = {"git", "grep", "rg", "cat", "sed", "head", "tail", "less"}
PROMPT_RE = re.compile(r"マスタ[^。\n]{0,40}登録|登録[^。\n]{0,20}マスタ")
PROMPT_LIMIT = 9000


def load_rules():
    path = os.environ.get("MRR_RULES_FILE")
    if path:
        with open(path, "rb") as f:
            return f.read()
    return subprocess.run(
        ["git", "-C", REPO, "show", "origin/main:" + RULES_PATH],
        check=True, capture_output=True, timeout=20,
    ).stdout


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.flush()


def deny(reason):
    emit({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }})


def pre_tool_use(data):
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    if tool == "Write":
        text, fpath = ti.get("content", ""), ti.get("file_path", "")
    elif tool == "Edit":
        text, fpath = ti.get("new_string", ""), ti.get("file_path", "")
    elif tool == "Bash":
        text, fpath = ti.get("command", ""), ""
    else:
        return
    if not isinstance(text, str) or not any(t in text for t in TARGETS):
        return
    if tool in ("Write", "Edit") and any(p in fpath for p in EXEMPT_PATHS):
        return
    if tool == "Bash":
        words = text.split()
        writes = (">" in text) or ("<<" in text) or ("tee" in text.split())
        if words and words[0] in READ_ONLY_CMDS and not writes:
            return
    try:
        raw = load_rules()
    except Exception:
        deny("ルール文書が読めないため止めました（origin/main の " + RULES_PATH + " を確認してください）。")
        return
    ack = hashlib.sha256(raw).hexdigest()[:8]
    if ("rules-ack: " + ack) in text:
        return
    deny(
        TITLE + "\n\n" + raw.decode("utf-8", "replace") + "\n\n"
        "読んだら台本に `# rules-ack: " + ack + "` を書いて、もう一度実行してください。"
    )


def user_prompt_submit(data):
    prompt = data.get("prompt", "")
    if not isinstance(prompt, str) or not PROMPT_RE.search(prompt):
        return
    try:
        body = load_rules().decode("utf-8", "replace")
    except Exception:
        return
    if len(body) > PROMPT_LIMIT:
        body = body[:PROMPT_LIMIT] + "\n\n（続きは origin/main の " + RULES_PATH + "）"
    emit({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": TITLE + "\n\n" + body,
    }})


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ev = data.get("hook_event_name", "")
    try:
        if ev == "PreToolUse":
            pre_tool_use(data)
        elif ev == "UserPromptSubmit":
            user_prompt_submit(data)
    except Exception:
        if ev == "PreToolUse":
            deny("フック内部エラーのため安全側で止めました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
