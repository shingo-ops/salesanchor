#!/usr/bin/env python3
"""ひな形（backend/app/services/tenant.py）だけを変えて migrations/ に手順を足さない PR を止める。

設計: docs/handoff/migration-runner-redesign/design.md §5-6・K5-2c
カード: docs/handoff/migration-runner-redesign/card-5-2c.md

動き:
  1. base と head の tenant.py を `git show` で読み、ast で解く（import して動かさない）。
  2. 「ひな形の文字列」= モジュール直下の `_..._SQL` 定数の文字列と、
     関数 create_tenant_schema の中の文字列（docstring・logger 呼び出し・raise 内は除く）。
     SQL の `--` 説明を消し、空白をまとめてから比べる。
  3. 一覧が同じなら成功。違えば、新しく足した migrations/ のファイルが
     scripts/run_all_migrations.sh に登録されているか、許可一覧に PR 番号があれば成功。
  4. どれにも当たらなければ失敗（終わりの番号 1）。

DB には接続しない（git と ast だけ）。
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

TENANT_PY = "backend/app/services/tenant.py"
RUN_ALL = "scripts/run_all_migrations.sh"
ALLOWLIST = "scripts/migration-guard/template-only-allowlist.tsv"
FUNC_NAME = "create_tenant_schema"
CONST_RE = re.compile(r"^_[A-Z0-9_]*_SQL$")
REGISTER_RE = re.compile(r"^run_(sql|py)[ \t]+(\S+)")


class QuoteDashError(Exception):
    """SQL の値（単引用符）の中に `--` が入る行を見つけた。"""


def git_show(sha: str, path: str, repo: Path) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{sha}:{path}"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def normalize(text: str, name: str, lineno: int) -> str:
    """`--` から行末までを消し、空白をまとめて前後を落とす。"""
    out_lines = []
    for i, line in enumerate(text.split("\n")):
        pos = line.find("--")
        if pos >= 0:
            before = line[:pos]
            if before.count("'") % 2 == 1:
                raise QuoteDashError(f"{name} (tenant.py:{lineno + i}): {line.strip()}")
            line = before
        out_lines.append(line)
    return re.sub(r"\s+", " ", "\n".join(out_lines)).strip()


def _collect_strings(node: ast.AST, out: list[tuple[str, int]]) -> None:
    """node の中の str を出てくる順に集める（f 文字列の str の部分を含む）。"""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            out.append((node.value, node.lineno))
        return
    for child in ast.iter_child_nodes(node):
        _collect_strings(child, out)


def _is_logger_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id in ("logger", "logging", "log")
    )


def _collect_function_strings(func: ast.AST) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    body = list(func.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]  # docstring

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.Raise) or _is_logger_call(node):
            return
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                out.append((node.value, node.lineno))
            return
        for child in ast.iter_child_nodes(node):
            visit(child)

    for stmt in body:
        visit(stmt)
    return out


def extract(source: str) -> dict[str, str]:
    """名前 → 正規化した文字列。関数の中は `create_tenant_schema#番号`。"""
    tree = ast.parse(source)
    result: dict[str, str] = {}
    for node in tree.body:
        targets: list[ast.expr] = []
        value = None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        if value is not None:
            for t in targets:
                if isinstance(t, ast.Name) and CONST_RE.match(t.id):
                    parts: list[tuple[str, int]] = []
                    _collect_strings(value, parts)
                    pieces = [normalize(s, t.id, ln) for s, ln in parts]
                    result[t.id] = "\x00".join(pieces)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == FUNC_NAME:
            for idx, (s, ln) in enumerate(_collect_function_strings(node), start=1):
                result[f"{FUNC_NAME}#{idx}"] = normalize(s, f"{FUNC_NAME}#{idx}", ln)
    return result


def base_name(key: str) -> str:
    return key.split("#", 1)[0]


def changed_names(base: dict[str, str], head: dict[str, str]) -> list[str]:
    names: set[str] = set()
    for key in set(base) | set(head):
        if base.get(key) != head.get(key):
            names.add(base_name(key))
    return sorted(names)


def registered_files(run_all_text: str) -> set[str]:
    reg: set[str] = set()
    for line in run_all_text.split("\n"):
        m = REGISTER_RE.match(line)
        if m:
            reg.add(m.group(2).strip("\"'"))
    return reg


def added_migrations(base: str, head: str, repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A", base, head, "--", "migrations/"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff が失敗: {proc.stderr.strip()}")
    return [ln for ln in proc.stdout.split("\n") if ln.strip()]


def allowlisted_prs(text: str) -> set[str]:
    prs: set[str] = set()
    for line in text.split("\n"):
        if not line.strip() or line.startswith("#"):
            continue
        prs.add(line.split("\t", 1)[0].strip())
    return prs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--pr", default="")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    repo = Path(args.repo)

    try:
        base_src = git_show(args.base, TENANT_PY, repo)
        head_src = git_show(args.head, TENANT_PY, repo)
        base_map = extract(base_src) if base_src is not None else {}
        head_map = extract(head_src) if head_src is not None else {}
    except QuoteDashError as e:
        print(f"ERROR: SQL の値（単引用符の中）に `--` が入っている行があり、説明と区別できません: {e}")
        return 1

    names = changed_names(base_map, head_map)
    if not names:
        print("ひな形の変更なし")
        return 0
    print("ひな形（tenant.py）で変わった定数: " + ", ".join(names))

    run_all = git_show(args.head, RUN_ALL, repo) or ""
    registered = registered_files(run_all)
    added = added_migrations(args.base, args.head, repo)
    ok = [f for f in added if f in registered]
    if ok:
        print("登録済みの新しい手順あり: " + ", ".join(ok))
        return 0

    allow_text = git_show(args.head, ALLOWLIST, repo) or ""
    if args.pr and args.pr in allowlisted_prs(allow_text):
        print(f"許可一覧に PR {args.pr} の行あり")
        return 0

    print(
        f"ひな形（tenant.py）の {', '.join(names)} が変わったのに、"
        "migrations/ に登録済みの新しい手順がありません。"
        "今ある会社にも同じ物を足す手順を同じ PR に足してください。"
        "足す必要が無い（説明の直しだけ・登録済みの移行が作る形に合わせるだけ）ときは、"
        f"{ALLOWLIST} に PR 番号と理由を足してください"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
