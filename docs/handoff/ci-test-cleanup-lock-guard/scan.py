"""調査用の台本（試験コード・製品コードは変えない・DB に繋がない）。

backend/tests/ の .py を ast で全部読み、関数（def・async def・入れ子も）ごとに、
その関数自身の本文（入れ子の関数の本文は除く）の文字列に「後片付けの文」があり、
かつ関数の原文に「札の語」が無いものを出す。

流し方（リポジトリの根から）:
    python3 docs/handoff/ci-test-cleanup-lock-guard/scan.py

出力: ファイル:行:関数名:当たった文の種類[,種類...]  （行は def の行。最後に全件数とファイル数）
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TESTS = ROOT / "backend" / "tests"

# 後片付けの文の種類（正規表現は大文字小文字を区別しない）
KINDS = {
    "drop_schema": re.compile(r"\bDROP\s+SCHEMA\b", re.I),
    "drop_role": re.compile(r"\bDROP\s+(?:ROLE|USER|OWNED)\b", re.I),
    "drop_public_table": re.compile(r"\bDROP\s+TABLE\b(?:\s+IF\s+EXISTS)?\s+(?:ONLY\s+)?\"?public\"?\.", re.I),
    "delete_public_rows": re.compile(r"\bDELETE\s+FROM\s+(?:ONLY\s+)?\"?public\"?\.", re.I),
    "truncate": re.compile(r"\bTRUNCATE\b", re.I),
}

# 参考（件数には入れない）: public. も schema も付けない DELETE（search_path 次第で public を指す）
REF_UNQUALIFIED = re.compile(r"\bDELETE\s+FROM\s+(?!(?:ONLY\s+)?\"?[A-Za-z_0-9{}]+\"?\.)", re.I)

LOCK_WORDS = ("public_bootstrap_lock", "pg_advisory_lock", "pg_advisory_xact_lock", "_public_lock")


def own_strings(fn: ast.AST):
    """関数自身の文字列（入れ子の def・lambda でない関数の中身は除く）を (行, 文字列) で返す。"""
    stack = list(fn.body)  # type: ignore[attr-defined]
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # 入れ子は別の関数として数える
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value
        stack.extend(ast.iter_child_nodes(node))


def main() -> int:
    rows = []
    ref_rows = []
    errors = []
    files_scanned = 0
    funcs_scanned = 0
    for path in sorted(TESTS.rglob("*.py")):
        files_scanned += 1
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except SyntaxError as e:
            errors.append(f"{rel}: 構文を読めない {e}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            funcs_scanned += 1
            kinds = {}
            ref = False
            for lineno, s in own_strings(node):
                for k, rx in KINDS.items():
                    if rx.search(s):
                        kinds.setdefault(k, lineno)
                if REF_UNQUALIFIED.search(s):
                    ref = True
            segment = ast.get_source_segment(text, node) or ""
            has_lock = any(w in segment for w in LOCK_WORDS)
            if kinds and not has_lock:
                rows.append((rel, node.lineno, node.name, kinds))
            elif ref and not kinds and not has_lock:
                ref_rows.append((rel, node.lineno, node.name))
    rows.sort(key=lambda r: (r[0], r[1]))
    for rel, line, name, kinds in rows:
        kind_txt = ",".join(f"{k}@{ln}" for k, ln in kinds.items())
        print(f"{rel}:{line}:{name}:{kind_txt}")
    files_hit = {r[0] for r in rows}
    print(f"# 読んだ .py: {files_scanned} ファイル / 関数: {funcs_scanned}")
    for e in errors:
        print(f"# 読めなかった: {e}")
    print(f"# 参考（件数外）: public. 無しの行削除だけの関数 {len(ref_rows)} 件")
    print(f"# 全件数: {len(rows)} 関数 / {len(files_hit)} ファイル")
    return 0


if __name__ == "__main__":
    sys.exit(main())
