import ast, sys, pathlib
root = pathlib.Path(sys.argv[1])
TARGETS = {"set_tenant_context", "set_tenant_context_sync", "reset_tenant_context"}
rows = []
def dep_name(default):
    if isinstance(default, ast.Call) and getattr(default.func, "id", None) == "Depends" and default.args:
        a = default.args[0]
        return getattr(a, "id", None) or getattr(a, "attr", None)
    return None
for p in sorted(root.rglob("*.py")):
    src = p.read_text()
    tree = ast.parse(src)
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for f in funcs:
        params = {}
        a = f.args
        allargs = a.posonlyargs + a.args + a.kwonlyargs
        defaults = [None]*(len(a.posonlyargs + a.args) - len(a.defaults)) + list(a.defaults) + list(a.kw_defaults)
        for arg, d in zip(allargs, defaults):
            params[arg.arg] = dep_name(d) if d is not None else "(引数)"
        for n in ast.walk(f):
            if isinstance(n, ast.Call):
                name = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                if name in TARGETS and f.name not in TARGETS:
                    # only innermost function
                    inner = [g for g in funcs if g is not f and g.lineno >= f.lineno and getattr(g, "end_lineno", 0) <= f.end_lineno and g.lineno <= n.lineno <= g.end_lineno]
                    if inner: continue
                    arg = ast.unparse(n.args[1]) if len(n.args) > 1 else "(なし)"
                    base = arg.split(".")[0].split("[")[0]
                    src_kind = params.get(base, "関数内で作る")
                    if src_kind == "get_current_tenant": cls = "A:ログインの札"
                    elif src_kind == "get_current_user" and arg.endswith(".tenant_id"): cls = "A:ログインの札"
                    else: cls = "B:要確認"
                    rows.append((cls, str(p.relative_to(root)), n.lineno, name, f.name, arg, src_kind))
for r in rows: print("\t".join(map(str, r)))
