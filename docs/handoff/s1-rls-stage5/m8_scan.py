"""m8_scan.py — commit の後に文脈を入れ直さず同じ session を使う箇所を構文木で拾う調査台本（製品コードではない）。
使い方: python m8_scan.py <backend/app のパス>
判定の範囲: 関数の中で `<名前>.commit()` の後に、同じ名前の session への操作（メソッド呼び出し・引数として渡す）があり、
その間に set_tenant_context / reset_tenant_context / reset_operator_context 相当の呼び出しが無いもの。
分岐・ループは見ず、行番号順で数える（取りこぼしより拾い過ぎを選ぶ）。"""
import ast
import os
import sys

SESS = {"db", "session", "s", "sess", "admin_db", "tenant_db"}
RESET_FUNCS = {"set_tenant_context", "reset_tenant_context", "set_tenant_context_sync"}


def calls_in_order(fn):
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            out.append(n)
    out.sort(key=lambda c: (c.lineno, c.col_offset))
    return out


def recv(c):
    f = c.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return f.value.id, f.attr
    return None, None


def name_of(c):
    f = c.func
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)


def uses_name(c, nm):
    for a in list(c.args) + [k.value for k in c.keywords]:
        if isinstance(a, ast.Name) and a.id == nm:
            return True
    return False


def main(root):
    rows = []
    for dp, _, fs in os.walk(root):
        for f in sorted(fs):
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            try:
                tree = ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError:
                continue
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                cs = calls_in_order(fn)
                for nm in SESS:
                    commits = [c for c in cs if recv(c) == (nm, "commit")]
                    for i, cm in enumerate(commits):
                        later = []
                        reset_line = None
                        for c in cs:
                            if (c.lineno, c.col_offset) <= (cm.lineno, cm.col_offset):
                                continue
                            # 次の commit までを 1 区間とする
                            if recv(c) == (nm, "commit"):
                                break
                            if name_of(c) in RESET_FUNCS and (uses_name(c, nm) or recv(c)[0] == nm):
                                reset_line = c.lineno
                                break
                            r, m = recv(c)
                            if r == nm and m in ("execute", "add", "add_all", "flush", "refresh", "get", "scalar", "scalars", "merge", "delete", "stream", "begin"):
                                later.append((c.lineno, f"{nm}.{m}"))
                            elif uses_name(c, nm) and name_of(c) not in ("isinstance",):
                                later.append((c.lineno, f"{name_of(c)}({nm},..)"))
                        if later:
                            rows.append((os.path.relpath(p, os.path.dirname(root)), fn.name, cm.lineno, later))
    for r in sorted(rows):
        print(f"{r[0]}:{r[2]} fn={r[1]} later={r[3][:6]}{'...' if len(r[3]) > 6 else ''}")
    print("TOTAL", len(rows))


main(sys.argv[1])
