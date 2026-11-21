#!/usr/bin/env python3
"""PostToolUse: 索引の「コードの場所」に当たるファイルを開いたら、その場所の決まりを AI に渡す。

設計: docs/handoff/requirement-library/design.md §3 便2。
入出力の出典: https://code.claude.com/docs/en/hooks （PostToolUse の入力 session_id・tool_name・tool_input.file_path、
出力 hookSpecificOutput.hookEventName / additionalContext）。
どんな失敗でも終了コード 0 で何も出さない。
"""
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ci"))
    import feature_index_lib as fil

    data = json.loads(sys.stdin.read())
    file_path = (data.get("tool_input") or {}).get("file_path")
    session_id = str(data.get("session_id") or "")
    if not file_path or not session_id:
        return
    fp = Path(file_path)
    if not fp.is_absolute():
        return
    parent = fp.parent
    while not parent.is_dir() and parent != parent.parent:
        parent = parent.parent
    r = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(parent), capture_output=True, text=True, timeout=3,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return
    top = Path(r.stdout.strip()).resolve()
    try:
        rel = fp.resolve().relative_to(top).as_posix()
    except ValueError:
        return

    index = top / "docs" / "adr" / "FEATURE-INDEX.md"
    rows, _ = fil.read_index(index.read_text(encoding="utf-8"))

    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)
    mark_dir = Path(os.environ.get("TMPDIR") or "/tmp") / "requirement-context"
    mark = mark_dir / safe
    seen = set(mark.read_text(encoding="utf-8").splitlines()) if mark.exists() else set()

    sentences = []
    shown = []
    for row in rows:
        code = row["code"].strip()
        if code == "-" or not code:
            continue
        globs = [g.strip() for g in code.split("、") if g.strip()]
        if not any(fil.match_glob(g, rel) for g in globs):
            continue
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
        sentences.append(f"この場所には決まりがあります: {label}（{kw}）。{tail}")
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
