#!/usr/bin/env python3
"""ADR-072 Phase 3: tenant schema 修飾 linter (PoC).

検出ルール:
  - Rule A: tenant スキーマ内テーブル名が `text("... FROM <bare-table> ...")` 形式で
    出現し、かつ同 endpoint で `tenant_table_ref(...)` も `reset_tenant_context(...)`
    も呼ばれていない → 案 A / 案 B どちらの対応もない違反。
  - Rule B: write 系 endpoint (`@router.post|put|patch|delete`) で
    `await db.commit()` を呼んでいるのに、関数内の `reset_tenant_context(...)` 呼び出し
    回数が commit 数に満たない → 案 B 違反 (Issue #563 と同根のバグ候補)。
  - Rule C: backend/app/ 全体 (routers の外も) の async 関数で、`await db.commit()` の
    後に実行されうる文のうち、最初に `db` を使う文が `await reset_tenant_context(db, ...)`
    (または set_tenant_context) でない → commit 後の会社付け直し漏れ (RLS のある表が
    別接続で見えなくなる)。対象は「tenant_id が Depends(get_current_tenant) の router
    endpoint」か「引数に db と tenant_id の両方を持つ async 関数」。

PoC は `--mode warning` (default) で違反を stderr 出力するが exit 0 を返す。
Phase 4 で `--mode strict` に切り替えて required check 昇格する。

Usage:
  python3 scripts/lint_tenant_schema.py
  python3 scripts/lint_tenant_schema.py backend/app/routers/staff.py
  python3 scripts/lint_tenant_schema.py --mode strict backend/app/

参照:
  - docs/adr/ADR-072-tenant-schema-prefix-enforcement.md §4 (CI linter)
  - Issue #773 (tracker)
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple


# tenant スキーマ内のテーブル名 allowlist (ADR-072 §4 で「allowlist で管理」と決定)。
# 将来は migrations/ から自動抽出するが、PoC では固定リストで開始する。
TENANT_TABLES: frozenset[str] = frozenset(
    {
        "audit_logs",
        "bots",
        "companies",
        "contacts",
        "deals",
        "google_calendar_config",
        "goals",
        "inventory_movements",
        "invoice_items",
        "invoices",
        "leads",
        "meta_messages",
        "order_commissions",
        "order_financials",
        "order_purchase_details",
        "order_shipping_details",
        "orders",
        "products",
        "purchase_order_items",
        "purchase_orders",
        "quote_items",
        "quotes",
        "role_permissions",
        "roles",
        "shifts",
        "staff",
        "staff_permissions",
        "staff_ui_preferences",
        "supplier_discord_routing",
        "suppliers",
        "tenant_commission_settings",
        "tenant_meta_config",
        "tenant_profile",
        "user_roles",
    }
)


TENANT_TABLE_REF = "tenant_table_ref"
RESET_TENANT_CONTEXT = "reset_tenant_context"
WRITE_METHODS = frozenset({"post", "put", "patch", "delete"})


# SQL 内の bare-table 抽出パターン (FROM / INTO / UPDATE / JOIN / DELETE FROM)。
# テーブル参照は `<identifier>` が単独で来た場合のみマッチ (`tenant_NNN.xxx` /
# `public.xxx` / f-string 内の `{var}` は処理側で除外)。
_BARE_TABLE_PATTERNS = [
    re.compile(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
    re.compile(r"\bINTO\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
    re.compile(r"\bJOIN\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.IGNORECASE),
]


class Violation(NamedTuple):
    file: str
    line: int
    function: str
    rule: str  # "A" / "B" / "C" / "SYNTAX"
    message: str


def _is_router_endpoint(node: ast.AsyncFunctionDef) -> tuple[bool, bool]:
    """関数の decorator から `(is_endpoint, is_write)` を判定する。

    `@router.get(...)` / `@router.post(...)` 等の decorator を持つ async 関数のみ
    endpoint と認識。write は POST/PUT/PATCH/DELETE。
    """
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            if (
                isinstance(dec.func.value, ast.Name)
                and dec.func.value.id == "router"
            ):
                method = dec.func.attr.lower()
                if method in WRITE_METHODS or method == "get":
                    return True, method in WRITE_METHODS
    return False, False


def _has_tenant_id_dep(node: ast.AsyncFunctionDef) -> bool:
    """関数引数に `tenant_id: int = Depends(get_current_tenant)` があるか。

    super_admin_*.py 等の **URL path param で tenant_id を受ける** endpoint は
    本来 public スキーマ操作で reset_tenant_context 不要なため、本判定で
    `Depends(get_current_tenant)` 経由のみを対象として扱う (false positive
    防止)。`URL path param の tenant_id` や `Query param の tenant_id` は
    除外する。

    判定: `tenant_id` 名の引数があり、かつ **default 値が
    `Depends(get_current_tenant)` の Call ノードである場合のみ True**。
    """
    # positional args / keyword-only args いずれも対象
    all_args = list(node.args.args) + list(node.args.kwonlyargs)
    # default 値は positional args の末尾と kwonlyargs それぞれにマッピング
    # ast.arguments.defaults は positional args 末尾の引数に対応する
    # ast.arguments.kw_defaults は kwonlyargs に 1:1 対応 (None の場合あり)
    pos_defaults: list[ast.expr | None] = list(node.args.defaults)
    pos_default_offset = len(node.args.args) - len(pos_defaults)
    defaults_by_arg: dict[str, ast.expr | None] = {}
    for i, a in enumerate(node.args.args):
        if i >= pos_default_offset:
            defaults_by_arg[a.arg] = pos_defaults[i - pos_default_offset]
    for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults):
        defaults_by_arg[a.arg] = d

    for arg in all_args:
        if arg.arg != "tenant_id":
            continue
        default = defaults_by_arg.get("tenant_id")
        # default 値が `Depends(get_current_tenant)` の場合のみ依存とみなす
        if (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id == "Depends"
            and len(default.args) == 1
            and isinstance(default.args[0], ast.Name)
            and default.args[0].id == "get_current_tenant"
        ):
            return True
    return False


def _extract_text_strings(func: ast.AST) -> list[tuple[int, str]]:
    """関数内の `text("...")` 引数を集める。f-string は `{var}` を `<VAR>` に
    置換した文字列を返す (bare-table 誤検出を避けるため)。"""
    results: list[tuple[int, str]] = []
    for child in ast.walk(func):
        if not (isinstance(child, ast.Call) and isinstance(child.func, ast.Name)):
            continue
        if child.func.id != "text" or not child.args:
            continue
        arg = child.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            results.append((arg.lineno, arg.value))
        elif isinstance(arg, ast.JoinedStr):  # f-string
            parts: list[str] = []
            for s in arg.values:
                if isinstance(s, ast.Constant):
                    parts.append(s.value)
                else:
                    parts.append("<VAR>")
            results.append((arg.lineno, "".join(parts)))
    return results


def _find_bare_tenant_tables(sql: str) -> set[str]:
    """SQL 文字列内に出現する bare な tenant スキーマ内テーブル名を返す。

    `tenant_NNN.xxx` / `public.xxx` / `<VAR>` (f-string 変数) は patterns の
    `\\b<keyword>\\s+([id])` で先頭文字を縛っているため間接的に除外される。
    """
    found: set[str] = set()
    for pat in _BARE_TABLE_PATTERNS:
        for m in pat.finditer(sql):
            name = m.group(1)
            if name in TENANT_TABLES:
                # 直前が `.` ならスキーマ修飾済 (e.g. `tenant_006.bots`) なのでスキップ
                start = m.start(1)
                if start >= 1 and sql[start - 1] == ".":
                    continue
                found.add(name)
    return found


def _count_commit_and_reset(func: ast.AST) -> tuple[int, int]:
    """関数内の `await db.commit()` と `reset_tenant_context(...)` の呼び出し数。"""
    commits = 0
    resets = 0
    for child in ast.walk(func):
        if not isinstance(child, ast.Call):
            continue
        # await db.commit()
        if (
            isinstance(child.func, ast.Attribute)
            and child.func.attr == "commit"
            and isinstance(child.func.value, ast.Name)
            and child.func.value.id == "db"
        ):
            commits += 1
        # reset_tenant_context(...)
        elif (
            isinstance(child.func, ast.Name)
            and child.func.id == RESET_TENANT_CONTEXT
        ):
            resets += 1
    return commits, resets


def _has_tenant_table_ref_call(func: ast.AST) -> bool:
    for child in ast.walk(func):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == TENANT_TABLE_REF
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Rule C: commit の後の会社付け直し漏れ (設計: docs/handoff/services-tenant-reset-after-commit/design.md 3-1)
# ---------------------------------------------------------------------------

RESET_FUNC_NAMES = frozenset({"reset_tenant_context", "set_tenant_context"})
_DEPS_MODULE = "app.auth.dependencies"

# 実行の列: (文, その文の位置で break したときの飛び先の列) のリスト
_Seq = list


def _is_commit_stmt(s: ast.stmt) -> bool:
    """式文 `await db.commit()` か。"""
    return (
        isinstance(s, ast.Expr)
        and isinstance(s.value, ast.Await)
        and isinstance(s.value.value, ast.Call)
        and isinstance(s.value.value.func, ast.Attribute)
        and s.value.value.func.attr == "commit"
        and isinstance(s.value.value.func.value, ast.Name)
        and s.value.value.func.value.id == "db"
    )


def _wrap(stmts: list[ast.stmt], brk: _Seq) -> _Seq:
    return [(x, brk) for x in stmts]


def _collect_commits(
    body: list[ast.stmt],
    after: _Seq,
    brk: _Seq,
    out: list[tuple[ast.stmt, _Seq]],
) -> None:
    """body の中の `await db.commit()` ごとに「その後に実行されうる文の列」を集める。

    入れ子の関数・クラスの中にはもぐらない。複合文の中は commit を探すためだけに
    もぐり、後続の列には複合文を 1 つの文として積む。
    """
    for i, s in enumerate(body):
        rest = _wrap(body[i + 1 :], brk) + after
        if _is_commit_stmt(s):
            out.append((s, rest))
        elif isinstance(
            s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            continue
        elif isinstance(s, ast.If):
            _collect_commits(s.body, rest, brk, out)
            _collect_commits(s.orelse, rest, brk, out)
        elif isinstance(s, (ast.For, ast.AsyncFor, ast.While)):
            # break は一番内側のループの後ろへ。continue はそこで止める (次の回は見ない)。
            _collect_commits(s.body, rest, rest, out)
            _collect_commits(s.orelse, rest, brk, out)
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            _collect_commits(s.body, rest, brk, out)
        elif isinstance(s, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            fin = _wrap(s.finalbody, brk)
            els = _wrap(s.orelse, brk)
            _collect_commits(s.body, els + fin + rest, brk, out)
            _collect_commits(s.orelse, fin + rest, brk, out)
            for h in s.handlers:
                _collect_commits(h.body, fin + rest, brk, out)
            _collect_commits(s.finalbody, rest, brk, out)
        elif isinstance(s, ast.Match):
            for case in s.cases:
                _collect_commits(case.body, rest, brk, out)


def _uses_db(stmt: ast.AST) -> bool:
    return any(isinstance(n, ast.Name) and n.id == "db" for n in ast.walk(stmt))


def _first_db_stmt(seq: _Seq) -> ast.stmt | None:
    """列をたどって最初に名前 `db` を含む文を返す。無ければ None (合格)。"""
    i = 0
    while i < len(seq):
        st, brk = seq[i]
        if isinstance(st, ast.Continue):
            return None
        if isinstance(st, ast.Break):
            seq, i = brk, 0
            continue
        if _uses_db(st):
            return st
        if isinstance(st, (ast.Return, ast.Raise)):
            return None
        i += 1
    return None


def _reset_names(tree: ast.Module) -> frozenset[str]:
    """付け直し関数として扱う名前 (別名 import を含む)。"""
    names = set(RESET_FUNC_NAMES)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _DEPS_MODULE:
            for a in node.names:
                if a.name in RESET_FUNC_NAMES and a.asname:
                    names.add(a.asname)
    return frozenset(names)


def _is_reset_stmt(st: ast.stmt, names: frozenset[str]) -> bool:
    """`await <名前>(db, ...)` だけの式文か。"""
    if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Await)):
        return False
    call = st.value.value
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id in names
        and bool(call.args)
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "db"
    )


def _is_rule_c_target(func: ast.AsyncFunctionDef) -> bool:
    if _is_router_endpoint(func)[0]:
        return _has_tenant_id_dep(func)
    arg_names = {a.arg for a in func.args.args} | {
        a.arg for a in func.args.kwonlyargs
    }
    return "db" in arg_names and "tenant_id" in arg_names


def _check_rule_c(tree: ast.Module, path: Path) -> list[Violation]:
    names = _reset_names(tree)
    found: list[Violation] = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.AsyncFunctionDef):
            continue
        if not _is_rule_c_target(func):
            continue
        commits: list[tuple[ast.stmt, _Seq]] = []
        _collect_commits(func.body, [], [], commits)
        for commit, seq in commits:
            st = _first_db_stmt(seq)
            if st is None or _is_reset_stmt(st, names):
                continue
            found.append(
                Violation(
                    str(path),
                    commit.lineno,
                    func.name,
                    "C",
                    "await db.commit() の後、db を使う前に "
                    "reset_tenant_context(db, tenant_id) がない "
                    f"(:{st.lineno}で db を使用)",
                )
            )
    return found


def lint_file(path: Path) -> list[Violation]:
    """1 ファイルを ast.parse して違反を返す。"""
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        return [
            Violation(str(path), e.lineno or 0, "?", "SYNTAX", f"parse failed: {e}")
        ]

    violations: list[Violation] = []

    for func in ast.walk(tree):
        if not isinstance(func, ast.AsyncFunctionDef):
            continue
        is_endpoint, is_write = _is_router_endpoint(func)
        if not is_endpoint:
            continue
        # tenant_id 依存を持たない endpoint は public スキーマ専用 / super_admin
        # 系として除外する (ADR-072 §「リスク」/ Phase 3 PoC 設計)。
        if not _has_tenant_id_dep(func):
            continue

        fn_name = func.name
        texts = _extract_text_strings(func)
        has_helper = _has_tenant_table_ref_call(func)
        commits, resets = _count_commit_and_reset(func)

        # Rule A: bare-table 検出 (commit を含む endpoint のみ違反扱い)。
        # read endpoint は commit 前なので search_path は維持されており、bare-table
        # でも実害がないため除外 (ADR-072 §4 の意図に合わせる)。
        for lineno, sql in texts:
            bare = _find_bare_tenant_tables(sql)
            if bare and commits > 0 and not has_helper and resets == 0:
                violations.append(
                    Violation(
                        str(path),
                        lineno,
                        fn_name,
                        "A",
                        f"bare tenant table(s) {sorted(bare)} in text() and no "
                        f"tenant_table_ref/reset_tenant_context (commit={commits})",
                    )
                )

        # Rule B: write endpoint の commit/reset 対称性。
        # ただし `tenant_table_ref` を使っている = 案 A 採用済なので除外。
        if (
            is_write
            and commits > 0
            and resets < commits
            and not has_helper
        ):
            violations.append(
                Violation(
                    str(path),
                    func.lineno,
                    fn_name,
                    "B",
                    f"write endpoint has {commits} `await db.commit()` but only "
                    f"{resets} `reset_tenant_context()` call(s)",
                )
            )

    violations.extend(_check_rule_c(tree, path))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ADR-072 tenant schema linter (Phase 3 PoC)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["backend/app"],
        help="ファイル or ディレクトリ (default: backend/app)",
    )
    parser.add_argument(
        "--mode",
        choices=["warning", "strict"],
        default="warning",
        help="warning (default): exit 0 で stderr に違反出力 / "
        "strict: 違反があれば exit 1 (Phase 4 で required check 昇格時に使用)",
    )
    args = parser.parse_args(argv)

    targets: list[Path] = []
    for p_str in args.paths:
        path = Path(p_str)
        if path.is_file() and path.suffix == ".py":
            targets.append(path)
        elif path.is_dir():
            targets.extend(sorted(path.rglob("*.py")))
        else:
            sys.stderr.write(f"skip: {p_str} (not a .py file or dir)\n")

    all_violations: list[Violation] = []
    for t in targets:
        all_violations.extend(lint_file(t))

    if all_violations:
        for v in all_violations:
            sys.stderr.write(
                f"{v.file}:{v.line} [Rule {v.rule}] {v.function}: {v.message}\n"
            )
        sys.stderr.write(f"\n{len(all_violations)} violation(s) found.\n")

        fix_howto = (
            "  await db.commit() の直後に必ず以下を追加してください:\n"
            "    await reset_tenant_context(db, tenant_id)\n"
            "  インポート: from app.auth.dependencies import reset_tenant_context\n"
            "  参照: docs/adr/ADR-072-tenant-schema-prefix-enforcement.md\n"
        )
        if any(v.rule == "B" for v in all_violations):
            sys.stderr.write("\n[Rule B 修正方法]\n" + fix_howto)
        if any(v.rule == "C" for v in all_violations):
            sys.stderr.write("\n[Rule C 修正方法]\n" + fix_howto)

        if args.mode == "strict":
            sys.stderr.write(
                "mode=strict: failing CI (ADR-072 Phase 4 enforcement)\n"
            )
            return 1
        sys.stderr.write(
            "mode=warning: not failing CI yet (ADR-072 Phase 3 PoC)\n"
        )
        return 0

    sys.stderr.write(f"ADR-072 lint: OK ({len(targets)} file(s) scanned)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
