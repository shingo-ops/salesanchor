"""m8_scan2.py — m8_scan.py の補い。中で commit する補助関数（名前で突き合わせ）を呼んだ後に、
同じ session をまた使う箇所を拾う（近似。同名の別関数は取り違える）。調査台本（製品コードではない）。"""
import ast
import os
import sys

root = sys.argv[1]
SESS = {"db", "session", "s", "sess", "admin_db"}
RESET = {"set_tenant_context", "reset_tenant_context", "set_tenant_context_sync"}
files = []
for dp, _, fs in os.walk(root):
    for f in fs:
        if f.endswith(".py"):
            p = os.path.join(dp, f)
            try:
                files.append((p, ast.parse(open(p, encoding="utf-8").read())))
            except SyntaxError:
                pass


def calls(fn):
    cs = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
    cs.sort(key=lambda c: (c.lineno, c.col_offset))
    return cs


def nm(c):
    f = c.func
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)


def is_commit(c):
    f = c.func
    return isinstance(f, ast.Attribute) and f.attr == "commit" and isinstance(f.value, ast.Name) and f.value.id in SESS


def uses(c, sess):
    return any(isinstance(a, ast.Name) and a.id == sess for a in list(c.args) + [k.value for k in c.keywords])


committers = {}
for p, t in files:
    for fn in ast.walk(t):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = {a.arg for a in fn.args.args}
            if any(is_commit(c) and c.func.value.id in params for c in calls(fn)):
                committers.setdefault(fn.name, []).append(f"{os.path.relpath(p, os.path.dirname(root))}:{fn.lineno}")
print("commit する補助関数（session を引数に取る）:", len(committers))
rows = []
for p, t in files:
    for fn in ast.walk(t):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        cs = calls(fn)
        for i, c in enumerate(cs):
            n = nm(c)
            if n in committers and n != fn.name:
                for s in SESS:
                    if uses(c, s):
                        later = []
                        for d in cs[i + 1:]:
                            if nm(d) in RESET and uses(d, s):
                                break
                            if is_commit(d):
                                continue
                            f = d.func
                            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == s and f.attr in ("execute", "add", "flush", "refresh", "get", "scalar", "scalars", "merge"):
                                later.append((d.lineno, f"{s}.{f.attr}"))
                            elif uses(d, s):
                                later.append((d.lineno, f"{nm(d)}({s},..)"))
                        if later:
                            rows.append((os.path.relpath(p, os.path.dirname(root)), c.lineno, fn.name, n, later))
for r in sorted(rows):
    print(f"{r[0]}:{r[1]} fn={r[2]} calls_committer={r[3]} later={r[4][:4]}")
print("TOTAL", len(rows))
