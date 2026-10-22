#!/usr/bin/env python3
"""元: ~/.claude/scripts/agent-danger-hook.sh（K1）、review-gate gate.py のマージ止め（K2）、
pr-body-guard.sh（K4）。PR 作成の範囲の止め（K3）は新規。PreToolUse。
止めるときは exit 2、理由は日本語で標準エラーへ。許可券・会話同意の例外は持たない。
危険語の一覧は danger_ops.json（sync_danger_ops.py が手元の正本から書き出す）を読む。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BODY_MARK = "### 標準ワークフロー確認"
READONLY_CMDS = {"grep", "egrep", "fgrep", "rg", "ag", "cat", "head", "tail", "less"}


def block(msg: str) -> int:
    print("BLOCKED(cloud): " + msg, file=sys.stderr)
    return 2


# ---------- 前処理 ----------
def strip_heredoc_bodies(cmd: str) -> str:
    """heredoc の本文だけを取り除く（開始行は残す）。psql への流し込み検査は元の文字列で行う。"""
    return re.sub(r"(<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n).*?\n\s*\2\b", r"\1", cmd, flags=re.S)


def strip_message_quotes(seg: str) -> str:
    """git commit / gh の区間では、引用符の中身（コミット文・PR 本文・題名）を取り除く。"""
    if re.match(r"\s*(git\s+commit\b|gh\s+(pr|issue)\b)", seg):
        seg = re.sub(r'"(?:[^"\\]|\\.)*"', '""', seg)
        seg = re.sub(r"'[^']*'", "''", seg)
    return seg


def is_readonly_segment(seg: str) -> bool:
    s = seg.strip()
    if not s or "\n" in s or "$(" in s or "`" in s:
        return False
    m = re.match(r"([\w./-]+)", s)
    if not m:
        return False
    name = m.group(1).split("/")[-1]
    if name in READONLY_CMDS:
        return True
    return name == "sed" and re.search(r"(^|\s)-n(\s|$)", s) is not None


def scan_text(cmd: str) -> str:
    cmd = strip_heredoc_bodies(cmd)
    parts = re.split(r"(&&|\|\||;|\|)", cmd)
    out = []
    for p in parts:
        if p in ("&&", "||", ";", "|"):
            out.append(p)
        elif is_readonly_segment(p):
            out.append("")
        else:
            out.append(strip_message_quotes(p))
    return "".join(out)


# ---------- (a) 危険操作 K1 ----------
def load_ops():
    with open(os.path.join(HERE, "danger_ops.json"), encoding="utf-8") as f:
        ops = json.load(f)
    if not isinstance(ops, list) or not ops:
        raise ValueError("danger_ops.json の形が違います")
    return [o for o in ops if isinstance(o, str) and o]


# 書込系 SQL は語の並びの正規表現で照合する（一覧と同じ文字列は作らない）
_SQL_WRITE = re.compile(
    r"\b(insert\s+into|update\s+\w+\s+set|delete\s+from|create\s+\w+|alter\s+\w+|drop\s+\w+|truncate\b|grant\s+\w+|revoke\s+\w+)",
    re.I,
)


def check_danger(cmd: str):
    scanned = scan_text(cmd)
    low = scanned.lower()
    try:
        ops = load_ops()
    except Exception as e:  # 一覧が読めないときは全て止める（黙って続行しない）
        return "危険語の一覧(danger_ops.json)を読めないため止めます: " + str(e)
    for op in ops:
        if op.lower() in low:
            return f"'{op}' は不可逆操作です。クラウドでは行えません。手元で PO の承認を得て実行してください。"
    # 本番 DB への書込
    raw = cmd  # 流し込みの検査は取り除く前の文字列で行う
    if re.search(r"\bpsql\b[^\n]*<", raw) or re.search(r"\|\s*(?:ssh\b[^|]*|docker\b[^|]*)?\bpsql\b", raw):
        return "psql への流し込みは中身を問わず止めます（本番 DB への書込はクラウドでは行えません）。"
    if re.search(r"\bpsql\b[^|&;\n]*\s(-f|--file)\b", raw):
        return "psql のファイル実行は止めます（本番 DB への書込はクラウドでは行えません）。"
    m = re.search(r"\bpsql\b[^|&;\n]*?(?:-c|--command)[ =]+(\"([^\"]*)\"|'([^']*)')", raw, re.I)
    if m and _SQL_WRITE.search(m.group(2) or m.group(3) or ""):
        return "psql の書込系 SQL は止めます（本番 DB への書込はクラウドでは行えません）。"
    if re.search(r"\bssh\b[^|;&\n]*\bprod", scanned, re.I):
        return "本番サーバーへの ssh はクラウドでは行えません。"
    return None


# ---------- (b) マージ K2 ----------
def check_merge(tool: str, cmd: str):
    if tool == "mcp__github__merge_pull_request":
        return "PR のマージはクラウドでは行いません（マージの GO と照合は手元の Opus が行います）。"
    if tool == "Bash":
        s = scan_text(cmd)
        if re.search(r"\bgh\s+pr\s+merge\b", s):
            return "gh pr merge はクラウドでは行いません（マージは手元で行います）。"
        if re.search(r"\bgh\s+api\b", s) and re.search(r"(-X|--method)[ =]*PUT\b", s, re.I) and re.search(r"/merge(\s|$|[\"'?])", s):
            return "gh api によるマージ(PUT …/merge)はクラウドでは行いません。"
    return None


# ---------- (c)(d) PR 作成 K3 / K4 ----------
def is_pr_create(tool: str, cmd: str) -> bool:
    if tool == "mcp__github__create_pull_request":
        return True
    if tool != "Bash":
        return False
    s = scan_text(cmd)
    if re.search(r"\bgh\s+pr\s+create\b", s):
        return True
    if re.search(r"\bgh\s+api\b", s) and re.search(r"repos/[^\s\"']+/pulls(\s|$|[\"'?])", s):
        explicit = re.search(r"(-X|--method)[ =]*(\w+)", s, re.I)
        if explicit:
            return explicit.group(2).upper() == "POST"
        return re.search(r"(\s-f\s|\s-F\s|--field|--raw-field|--input)", s) is not None
    return False


def changed_files(cwd: str):
    r = subprocess.run(
        ["git", "-C", cwd, "diff", "--name-only", "origin/main...HEAD"],
        capture_output=True, text=True, timeout=10,
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip()[:200])
    return [x for x in r.stdout.splitlines() if x.strip()]


def is_doc_path(p: str) -> bool:
    return p.startswith("docs/") or p.startswith(".claude-pipeline/") or p.endswith(".md")


def body_text(tool: str, ti: dict, cmd: str) -> str:
    if tool != "Bash":
        b = ti.get("body")
        return b if isinstance(b, str) else ""
    text = cmd
    for m in re.finditer(r"(?:--body-file|-F)[ =]+(?:body=@)?(\S+)", cmd):
        path = m.group(1).strip("\"'")
        try:
            with open(path, encoding="utf-8") as f:
                text += "\n" + f.read()
        except Exception:
            pass
    return text


def check_pr_create(tool: str, ti: dict, cmd: str, cwd: str):
    try:
        files = changed_files(cwd)
    except Exception as e:
        return "枝の変更ファイルを git で取れなかったため止めます: " + str(e)
    code = [f for f in files if not is_doc_path(f)]
    if code:
        return ("コード変更を含む枝は push までにし、PR は手元で shingo-cc 名義で作ってください。"
                "（コード側の変更: " + ", ".join(code[:5]) + (" ほか" if len(code) > 5 else "") + "）")
    if BODY_MARK not in body_text(tool, ti, cmd):
        return f"PR 本文に「{BODY_MARK}」の節がありません。入れてから作り直してください。"
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    if not (tool == "Bash" or tool.startswith("mcp__github__")):
        return 0
    ti = data.get("tool_input") or {}
    cmd = ti.get("command", "") if tool == "Bash" else ""
    if tool == "Bash" and not cmd:
        return 0
    cwd = data.get("cwd") or os.getcwd()

    if tool == "Bash":
        r = check_danger(cmd)
        if r:
            return block(r)
    r = check_merge(tool, cmd)
    if r:
        return block(r)
    if is_pr_create(tool, cmd):
        r = check_pr_create(tool, ti, cmd, cwd)
        if r:
            return block(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
