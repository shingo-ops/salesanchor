#!/usr/bin/env python3
"""PostToolUse: 索引の「コードの場所」に当たるファイルを開いたら、その場所の決まりを AI に渡す。

設計: docs/handoff/requirement-library/design.md §3 便2。
入出力の出典: https://code.claude.com/docs/en/hooks （PostToolUse の入力 session_id・tool_name・tool_input.file_path、
出力 hookSpecificOutput.hookEventName / additionalContext）。
どんな失敗でも終了コード 0 で何も出さない。
"""
import glob
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


def pick_files(command: str, cwd) -> list:
    """Bash のコマンドから、実在するファイルの絶対パスを最大 50 個拾う（フォルダは使わない）。"""
    try:
        lx = shlex.shlex(command, posix=True, punctuation_chars=True)
        lx.whitespace_split = True
        words = list(lx)
    except ValueError:
        words = command.split()
    out = []
    for w in words[:200]:
        if not w or w.startswith("-"):
            continue
        if not os.path.isabs(w):
            if not (isinstance(cwd, str) and os.path.isabs(cwd)):
                continue
            w = os.path.join(cwd, w)
        cands = glob.glob(w)[:50] if any(c in w for c in "*?[") else [w]
        for c in cands:
            if os.path.isfile(c) and c not in out:
                out.append(c)
        if len(out) >= 50:
            break
    return out[:50]


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ci"))
    import feature_index_lib as fil

    data = json.loads(sys.stdin.read())
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    session_id = str(data.get("session_id") or "")
    if not session_id:
        return
    is_bash = False
    if isinstance(file_path, str) and file_path:
        fp0 = Path(file_path)
        if not fp0.is_absolute():
            return
        files = [fp0]
    elif data.get("tool_name") == "Bash" and isinstance(tool_input.get("command"), str):
        is_bash = True
        files = [Path(x) for x in pick_files(tool_input["command"], data.get("cwd"))]
    else:
        return
    if not files:
        return
    start = time.monotonic()
    tops = {}
    indexes = {}
    hit_rows = []
    hit_kw = set()
    for fp in files:
        if is_bash and time.monotonic() - start > 3:
            break
        parent = fp.parent
        while not parent.is_dir() and parent != parent.parent:
            parent = parent.parent
        if parent not in tops:
            try:
                r = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=str(parent), capture_output=True, text=True,
                    timeout=1 if is_bash else 3,
                )
                tops[parent] = Path(r.stdout.strip()).resolve() if r.returncode == 0 and r.stdout.strip() else None
            except Exception:
                tops[parent] = None
        top = tops[parent]
        if top is None:
            continue
        try:
            rel = fp.resolve().relative_to(top).as_posix()
        except ValueError:
            continue
        if top not in indexes:
            try:
                idx = top / "docs" / "adr" / "FEATURE-INDEX.md"
                indexes[top] = fil.read_index(idx.read_text(encoding="utf-8"))[0]
            except Exception:
                indexes[top] = []
        for row in indexes[top]:
            code = row["code"].strip()
            if code == "-" or not code or row["keyword"] in hit_kw:
                continue
            globs = [g.strip() for g in code.split("、") if g.strip()]
            if any(fil.match_glob(g, rel) for g in globs):
                hit_kw.add(row["keyword"])
                hit_rows.append(row)
    rows = hit_rows

    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)
    mark_dir = Path(os.environ.get("TMPDIR") or "/tmp") / "requirement-context"
    mark = mark_dir / safe
    seen = set(mark.read_text(encoding="utf-8").splitlines()) if mark.exists() else set()

    sentences = []
    shown = []
    for row in rows:
        kw = row["keyword"]
        if kw in seen:
            continue
        # 表示は索引の書いた形（ADR-097）のまま。番号の正規化（先頭の 0 を落とす）は表示に使わない
        adrs = list(dict.fromkeys(fil.ADR_REF_RE.findall(row["adr"])))
        label = "・".join("ADR-" + a for a in adrs) or "ADR"
        spec_paths = []
        for m in re.finditer(r"\]\(([^)]+)\)", row["spec"]):
            target = m.group(1).split("#")[0]
            if target:
                spec_paths.append(posixpath.normpath(posixpath.join("docs/adr", target)))
        if spec_paths:
            tail = "計画の前に " + "・".join(spec_paths) + " を読んでください。"
        else:
            tail = "計画の前に、その ADR を docs/adr/ で読んでください。"
        note = row["note"].strip()
        if not note or note == "-":
            sentences.append(f"この場所には決まりがあります: {label}。{tail}")
        else:
            if note.endswith("。"):
                note = note[:-1]
            if len(note) > 400:
                note = note[:400] + "…"
            sentences.append(f"この場所には決まりがあります: {label}。決まりの要旨: {note}。{tail}")
        shown.append(kw)
    if not sentences:
        return
    mark_dir.mkdir(parents=True, exist_ok=True)
    with mark.open("a", encoding="utf-8") as f:
        for kw in shown:
            f.write(kw + "\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                              "additionalContext": "\n".join(sentences)}},
                     ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    sys.exit(0)
