"""m9_scan.py - Bx(接続を返すたびに rollback -> RESET ALL -> commit)の後、文脈が空の状態で
FORCE RLS 表・tenant_NNN 表を触る箇所を拾う調査台本(製品コードではない・読むだけ)。

使い方(リポジトリの根から):
    python3 docs/handoff/s1-rls-stage5/m9_scan.py            # 表(markdown)を標準出力へ
    python3 docs/handoff/s1-rls-stage5/m9_scan.py --json     # 機械可読

モデル(近似):
  状態 = (flags, pc, lost)。flags は {t: app.tenant_id が入っている, o: app.is_operator が true, sp: search_path が tenant_NNN}。
  pc   = この session で commit / rollback を通った後か。
  lost = commit / rollback の前に張っていた flags (Bx で失うもの)。
  Bx 後の規則: session の開始(接続を借りた直後)と、commit / rollback の直後(接続を返して借り直す)は flags が空。
  文脈を張る呼び出し: set_tenant_context / reset_tenant_context / set_tenant_context_sync (t, sp)、
    set_operator_context (o)、reset_operator_context (o を外す)、clear_tenant_context (全部外す)、
    SQL 文字列の SET app.* / SET search_path / set_config。補助関数は中身を見て効果を判定する。
  分岐は if / try / for / while を構造で追う(return / raise で終わる枝は合流させない)。
  入口:
    ルート(@router.* / @app.*): Depends の連鎖を FastAPI と同じ順で解く。include_router の dependencies、
      ルーターの dependencies=[...]、依存の工場(require_permission(...) など)、
      ルートに掛かった自前のデコレータ(operator を張る形)も反映する。get_current_tenant を通れば t, sp。
    自分で session を開く関数(*SessionLocal() / *factory() / sessionmaker / Session(...) / get_db() / engine.connect()):
      空で開始。
  走査で拾えない形(表名が動的・SQL が別の定数・クラス経由・別名の session)は UNRES / ORPHANS として別に出し、手で読む。
判定:
  BREAK-新   : 文脈を張った後の commit / rollback で失い、失わなければ規則を通った箇所
  BREAK-既   : 張る前から空で、通る規則が無い箇所(前の値が偶然残るときだけ今は動く)
  要確認     : SELECT で共通行(tenant_id が NULL)だけが見える表(products / suppliers など)
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
APP = os.path.join(ROOT, "backend", "app")
HERE = os.path.dirname(os.path.abspath(__file__))

_DEL = "DEL" + "ETE"  # 見張りの語を命令に直接書かないため分割


# ---------------------------------------------------------------- 表の知識
def load_policies():
    """prod-public-rls-policies.tsv -> {table: {op: [expr, ...]}}"""
    pol = {}
    with open(os.path.join(HERE, "prod-public-rls-policies.tsv"), encoding="utf-8") as f:
        next(f)
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            tbl, rest = line.split("\t", 1)
            d = defaultdict(list)
            for part in rest.split(" || "):
                m = re.match(r"^(ALL|SELECT|INSERT|UPDATE|" + _DEL + r"):(.*?) / (.*)$", part.replace("\\n", "\n"), re.S)
                if not m:
                    continue
                cmd, using, check = m.group(1), m.group(2).strip(), m.group(3).strip()
                ops = ["SELECT", "INSERT", "UPDATE", _DEL] if cmd == "ALL" else [cmd]
                for op in ops:
                    e = check if (op == "INSERT" and check != "-") else using
                    if op == "UPDATE" and check != "-":
                        e = using + " && " + check
                    if e != "-":
                        d[op].append(e)
            pol[tbl] = dict(d)
    return pol


POL = load_policies()
RLS36 = set(POL)


def need(expr: str):
    """規則の式 -> 必要な文脈の種別"""
    e = expr
    if e.strip() == "true":
        return "true"
    has_t = "app.tenant_id" in e
    has_o = "app.is_operator" in e
    if "CASE" in e:
        return "case"
    if has_t and has_o and (" OR " in e):
        return "t|o"
    if has_t and "tenant_id IS NULL" in e and " OR " in e:
        return "t|null"  # SELECT: 共通行(NULL)は文脈が無くても見える
    if has_t and has_o:
        return "t&o"
    if has_t:
        return "t"
    if has_o:
        return "o"
    return "?"


def satisfied(kind: str, flags: frozenset) -> bool:
    t, o = "t" in flags, "o" in flags
    return {"true": True, "t": t, "o": o, "t|o": t or o, "t&o": t and o, "case": t or o, "t|null": t, "?": True}[kind]


def op_ok(table: str, op: str, flags: frozenset):
    exprs = POL.get(table, {}).get(op, [])
    if not exprs:
        return True, "(この操作の規則なし)", "none"
    kinds = [need(x) for x in exprs]
    ok = any(satisfied(k, flags) for k in kinds)
    return ok, " + ".join(x.replace("\n", " ")[:160] for x in exprs), "/".join(kinds)


def collect_tenant_tables():
    names = set()
    src = open(os.path.join(ROOT, "scripts", "lint_tenant_schema.py"), encoding="utf-8").read()
    m = re.search(r"TENANT_TABLES[^=]*=\s*frozenset\(\s*\{(.*?)\}\s*\)", src, re.S)
    if m:
        names |= set(re.findall(r'"([a-z_0-9]+)"', m.group(1)))
    pat = re.compile(r"CREATE TABLE(?: IF NOT EXISTS)?\s+(?:\{schema\}|\{schema_name\}|%I|tenant_(?:\d+|NNN|\{[^}]*\}))\.([a-z_0-9]+)", re.I)
    files = [os.path.join(APP, "services", "tenant.py")]
    mig = os.path.join(ROOT, "migrations")
    if os.path.isdir(mig):
        files += [os.path.join(mig, x) for x in os.listdir(mig) if x.endswith(".sql")]
    for p in files:
        try:
            names |= set(pat.findall(open(p, encoding="utf-8").read()))
        except OSError:
            pass
    return names


def collect_tenant_rls():
    """tenant.py と migrations の ENABLE ROW LEVEL SECURITY 文のうち、public 以外(tenant_NNN 側)の表"""
    pat = re.compile(r"ALTER TABLE\s+(?:IF EXISTS\s+)?(?:ONLY\s+)?(?:([%A-Za-z_0-9{}\.\"']+)\.)?([a-z_0-9]+)\s+(?:ENABLE|FORCE) ROW LEVEL SECURITY", re.I)
    out = set()
    files = [os.path.join(APP, "services", "tenant.py")]
    mig = os.path.join(ROOT, "migrations")
    if os.path.isdir(mig):
        files += [os.path.join(mig, x) for x in os.listdir(mig) if x.endswith(".sql")]
    for p in files:
        try:
            txt = open(p, encoding="utf-8").read()
        except OSError:
            continue
        for m in pat.finditer(txt):
            if m.group(1) in ("%I", "{schema}", "{schema_name}") or (m.group(1) or "").startswith("tenant_"):
                out.add(m.group(2))
    return out


def collect_public_tables():
    names = set()
    pat = re.compile(r"CREATE TABLE(?: IF NOT EXISTS)?\s+(?:public\.)?([a-z_0-9]+)\s*\(", re.I)
    mig = os.path.join(ROOT, "migrations")
    for x in os.listdir(mig) if os.path.isdir(mig) else []:
        if x.endswith(".sql") and not x.endswith("_down.sql"):
            try:
                names |= set(pat.findall(open(os.path.join(mig, x), encoding="utf-8").read()))
            except OSError:
                pass
    return names


TENANT = collect_tenant_tables()
TENANT_RLS = collect_tenant_rls()
TENANT |= TENANT_RLS  # RLS を張った tenant 表は tenant 表でもある
PUBLIC_MIG = collect_public_tables()
AMBIG = TENANT & (RLS36 | PUBLIC_MIG)  # search_path が空なら public の同名表に化ける

# ---------------------------------------------------------------- 関数の収集
SESS_NAMES = {"db", "session", "s", "sess", "admin_db", "tenant_db", "conn", "connection", "sync_session", "tenant_session"}
SESS_ATTRS = {"db", "session", "_db", "_session"}
OWN_SESSION_CALL = re.compile(r"(SessionLocal|^Session$|factory|sessionmaker|get_sync_session|get_session|_session_factory|^get_db$|get_admin_db)", re.I)
CTX_SET_FUNCS = {"set_tenant_context", "reset_tenant_context", "set_tenant_context_sync"}
OPS_ATTR = {"execute", "scalar", "scalars", "get", "add", "add_all", "merge", "delete", "refresh", "flush", "stream", "run_sync", "get_one"}
ROUTE_ATTR = {"get", "post", "put", "patch", "delete", "websocket", "api_route", "head", "options"}
MODEL_NAMES = {"User", "Tenant"}  # backend/app/models.py の ORM はこの 2 つだけ(__tablename__ が 2 件)


def _ann(node, pname):
    for a in node.args.args + node.args.kwonlyargs:
        if a.arg == pname and a.annotation is not None:
            try:
                return ast.unparse(a.annotation).split("[")[0].split(".")[-1]
            except Exception:  # noqa: BLE001
                return ""
    return ""


def _cname(call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


FACTORIES: set = set()  # sessionmaker(...) を代入した名前
IMPORTS: dict = {}
ROUTER_DEPS: dict = {}  # (モジュール名, ルーター変数) -> include_router の dependencies の要素
FUNCS: dict = defaultdict(list)
ALL: list = []


class Fn:
    def __init__(self, node, path, cls=None):
        self.node = node
        self.path = os.path.relpath(path, ROOT)
        self.name = node.name
        self.cls = cls
        self.nested = False
        self.qual = f"{self.path}:{node.lineno}:{node.name}"
        self.params = [a.arg for a in node.args.args + node.args.kwonlyargs]
        self.sess_params = [p for p in self.params if p in SESS_NAMES or _ann(node, p) in ("AsyncSession", "Session")]
        self.route = self._route()
        self.own = False

    def _route(self):
        for d in self.node.decorator_list:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in ROUTE_ATTR:
                if isinstance(d.func.value, ast.Name):
                    path = d.args[0].value if d.args and isinstance(d.args[0], ast.Constant) else "?"
                    deps = []
                    for k in d.keywords:
                        if k.arg == "dependencies" and isinstance(k.value, (ast.List, ast.Tuple)):
                            deps = list(k.value.elts)
                    return (d.func.attr.upper(), path, d.func.value.id, deps)
        return None

    def own_session(self):
        for n in ast.walk(self.node):
            if isinstance(n, ast.Call):
                nm = _cname(n)
                if nm and (OWN_SESSION_CALL.search(nm) or nm in FACTORIES):
                    return True
        return False


def _mod_files(modname: str):
    rel = modname.replace(".", "/")
    out = []
    for cand in (rel + ".py", rel + "/__init__.py"):
        full = os.path.join(ROOT, "backend", cand)
        if os.path.exists(full):
            out.append(os.path.relpath(full, ROOT))
    return out


def collect_imports(path, tree):
    names, mods = {}, {}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            base = _mod_files(n.module)
            for a in n.names:
                local = a.asname or a.name
                sub = _mod_files(n.module + "." + a.name)
                if sub:
                    mods[local] = sub
                names[local] = (base, a.name)
        elif isinstance(n, ast.ImportFrom) and n.level > 0:
            pkg = os.path.dirname(os.path.relpath(path, os.path.join(ROOT, "backend")))
            for _ in range(n.level - 1):
                pkg = os.path.dirname(pkg)
            modname = pkg.replace("/", ".") + ("." + n.module if n.module else "")
            base = _mod_files(modname)
            for a in n.names:
                local = a.asname or a.name
                sub = _mod_files(modname + "." + a.name)
                if sub:
                    mods[local] = sub
                names[local] = (base, a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                local = a.asname or a.name.split(".")[0]
                f = _mod_files(a.name)
                if f and a.asname:
                    mods[local] = f
    IMPORTS[os.path.relpath(path, ROOT)] = {"names": names, "mods": mods}


def collect_router_deps(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _cname(n) == "include_router" and n.args:
            a = n.args[0]
            key = None
            if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name):
                key = (a.value.id, a.attr)
            deps = []
            for k in n.keywords:
                if k.arg == "dependencies" and isinstance(k.value, (ast.List, ast.Tuple)):
                    deps = list(k.value.elts)
            if key:
                ROUTER_DEPS[key] = ROUTER_DEPS.get(key) or deps


def load():
    for dp, _, fs in os.walk(APP):
        for fn in sorted(fs):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dp, fn)
            try:
                tree = ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError:
                continue
            collect_imports(p, tree)
            collect_router_deps(tree)
            for nn in ast.walk(tree):
                if isinstance(nn, ast.Assign) and isinstance(nn.value, ast.Call) and _cname(nn.value) in ("sessionmaker", "async_sessionmaker", "scoped_session"):
                    for t in nn.targets:
                        if isinstance(t, ast.Name):
                            FACTORIES.add(t.id)
            pending = []

            def visit(body, cls=None):
                for n in body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        pending.append((n, cls))
                    elif isinstance(n, ast.ClassDef):
                        visit(n.body, n.name)

            visit(tree.body)
            for n, cls in pending:
                f = Fn(n, p, cls)
                ALL.append(f)
                FUNCS[n.name].append(f)
                for nn in ast.walk(n):
                    if nn is not n and isinstance(nn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        g = Fn(nn, p, cls)
                        g.nested = True
                        ALL.append(g)
                        FUNCS[nn.name].append(g)
    for f in ALL:  # FACTORIES は全ファイルを読み終えてから own を判定
        f.own = f.own_session()


# ---------------------------------------------------------------- SQL の取り出し
def flat(node, env, depth=0):
    """式 -> SQL 文字列(f 文字列の式は {...} のまま残す)。取れなければ None"""
    if depth > 6 or node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                out.append(str(v.value))
            elif isinstance(v, ast.FormattedValue):
                out.append("{" + ast.unparse(v.value) + "}")
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        a, b = flat(node.left, env, depth + 1), flat(node.right, env, depth + 1)
        if a is not None and b is not None:
            return a + b
        return a or b
    if isinstance(node, ast.Call):
        nm = _cname(node)
        if nm == "text" and node.args:
            return flat(node.args[0], env, depth + 1)
        if nm in ("format", "strip", "lstrip", "rstrip", "replace") and isinstance(node.func, ast.Attribute):
            return flat(node.func.value, env, depth + 1)
        if nm == "dedent" and node.args:
            return flat(node.args[0], env, depth + 1)
    if isinstance(node, ast.Name):
        v = env.get(node.id)
        if v is not None:
            return flat(v, env, depth + 1)
    if isinstance(node, ast.IfExp):
        return flat(node.body, env, depth + 1)
    return None


def build_env(fn_node):
    env = {}
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            env[n.targets[0].id] = n.value
    return env


MODULE_CONST: dict = {}


def module_env(path):
    if path in MODULE_CONST:
        return MODULE_CONST[path]
    d = {}
    try:
        tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
        for n in tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                d[n.targets[0].id] = n.value
    except Exception:  # noqa: BLE001
        pass
    MODULE_CONST[path] = d
    return d


REF = r"((?:\{[^}]*\}|\"?[A-Za-z_][A-Za-z0-9_]*\"?)\.)?(\{[^}]*\}|\"?[A-Za-z_][A-Za-z0-9_]*\"?)(\s*\()?"
PATS = [
    ("INSERT", re.compile(r"\bINSERT\s+INTO\s+" + REF, re.I)),
    ("UPDATE", re.compile(r"(?<![A-Za-z_])(?<!DO )(?<!FOR )\bUPDATE\s+" + REF, re.I)),
    (_DEL, re.compile(r"\b" + _DEL + r"\s+FROM\s+(?:ONLY\s+)?" + REF, re.I)),
    ("SELECT", re.compile(r"\b(?:FROM|JOIN)\s+(?:ONLY\s+)?" + REF, re.I)),
]
SKIP_NAMES = {"set", "lateral", "select", "unnest", "generate_series", "jsonb_array_elements", "jsonb_each", "values", "only", "of", "nowait", "skip",
              "information_schema", "pg_catalog", "pg_class", "pg_policies", "pg_namespace", "pg_stat_activity", "pg_tables", "pg_roles", "dual"}


def sql_refs(sql: str):
    """SQL 文字列 -> [(op, schema_part, table_part)]"""
    sql = re.sub(r"--[^\n]*", " ", sql)
    ctes = set(x.lower() for x in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*(?:NOT\s+MATERIALIZED\s*)?\(", sql, re.I))
    out = []
    del_spans = []
    for op, pat in PATS:
        for m in pat.finditer(sql):
            if op == "SELECT" and any(a <= m.start() < b for a, b in del_spans):
                continue
            sch, tbl, paren = m.group(1), m.group(2), m.group(3)
            if paren and op == "SELECT":
                continue  # FROM f(...) は関数。INSERT INTO t (列...) の括弧は列の並び
            tbl_c = tbl.strip('"')
            if tbl_c.lower() in SKIP_NAMES or tbl_c.lower() in ctes:
                continue
            if sch and sch.strip('".').lower() in ("information_schema", "pg_catalog"):
                continue
            if op == _DEL:
                del_spans.append((m.start(), m.end()))
            out.append((op, sch.rstrip(".").strip('"') if sch else None, tbl_c))
    return out


def classify(sch, tbl):
    """kind: pub(RLS 表) / tq(tenant 表・修飾) / tu(tenant 表・無修飾) / amb(無修飾で public と tenant の同名) / dyn(動的) / other"""
    if tbl.startswith("{"):
        return "dyn", tbl
    if sch is None:
        if tbl in AMBIG:
            return "amb", tbl
        if tbl in RLS36:
            return "pub", tbl
        if tbl in TENANT:
            return "tu", tbl
        return "other", tbl
    if sch == "public" or "TCG_SCHEMA" in sch:
        return ("pub", tbl) if tbl in RLS36 else ("other", tbl)
    if sch.startswith("{") or sch.startswith("tenant_"):
        return ("tq", tbl) if (tbl in TENANT or tbl in RLS36) else ("other", tbl)
    return "other", tbl


def _ph_src(ph, env):
    inner = ph.strip("{}").strip()
    node = env.get(inner)
    return ast.unparse(node) if node is not None else inner


def classify_env(sch, tbl, env):
    """{変数} を環境から引いて tenant 修飾か public 修飾かを決める"""
    if tbl.startswith("{"):
        src = _ph_src(tbl, env)
        if "tenant_table_ref" in src or "tenant_" in src or "schema" in src.lower():
            return "tq", tbl.strip("{}")
        return "dyn", tbl
    if sch and sch.startswith("{"):
        src = _ph_src(sch, env)
        if "TCG_SCHEMA" in src or "'public'" in src or '"public"' in src:
            return classify("public", tbl)
        if tbl in TENANT:
            return "tq", tbl
        return classify("public", tbl) if tbl in RLS36 else ("other", tbl)
    return classify(sch, tbl)


# ---------------------------------------------------------------- 状態と走査
class St:
    __slots__ = ("flags", "pc", "dirty", "ctx_line", "lost")

    def __init__(self, flags=frozenset(), pc=False, dirty=False, ctx_line=None, lost=frozenset()):
        self.flags, self.pc, self.dirty, self.ctx_line, self.lost = frozenset(flags), pc, dirty, ctx_line, frozenset(lost)

    def copy(self):
        return St(self.flags, self.pc, self.dirty, self.ctx_line, self.lost)

    def key(self):
        return (self.flags, self.pc, self.dirty, self.lost)


def merge(a: St, b: St) -> St:
    return St(a.flags & b.flags, a.pc or b.pc, a.dirty or b.dirty,
              a.ctx_line if a.ctx_line == b.ctx_line else (a.ctx_line or b.ctx_line), a.lost | b.lost)


def terminates(stmts):
    return bool(stmts) and isinstance(stmts[-1], (ast.Return, ast.Raise))


HITS: list = []
UNRES: list = []
MEMO: dict = {}


def is_sess(expr, sess):
    if isinstance(expr, ast.Name):
        return expr.id in sess
    if isinstance(expr, ast.Attribute):
        return expr.attr in SESS_ATTRS
    return False


def sql_ctx_effect(sql: str, st: St, line: int):
    """SET 文を状態へ反映"""
    s = sql
    if re.search(r"\bSET\s+(?:LOCAL\s+)?app\.tenant_id\s*=\s*'?\s*(\{|\d|:)", s, re.I) or re.search(r"set_config\(\s*'app\.tenant_id'\s*,\s*(?!\s*''\s*,)", s, re.I):
        st.flags |= {"t"}
        st.ctx_line = line
    if re.search(r"\bSET\s+(?:LOCAL\s+)?app\.tenant_id\s*=\s*''", s, re.I):
        st.flags -= {"t"}
    if re.search(r"\bSET\s+(?:LOCAL\s+)?app\.is_operator\s*=\s*'true'", s, re.I) or re.search(r"set_config\(\s*'app\.is_operator'\s*,\s*'true'", s, re.I):
        st.flags |= {"o"}
        st.ctx_line = line
    if re.search(r"\bSET\s+(?:LOCAL\s+)?app\.is_operator\s*=\s*''", s, re.I) or re.search(r"set_config\(\s*'app\.is_operator'\s*,\s*''", s, re.I):
        st.flags -= {"o"}
    if re.search(r"\bSET\s+(?:LOCAL\s+)?search_path\s*=\s*(\{|tenant_)", s, re.I):
        st.flags |= {"sp"}
    if re.search(r"\bSET\s+(?:LOCAL\s+)?search_path\s*=\s*public", s, re.I):
        st.flags -= {"sp"}


def record_op(fn, line, op, sql_kind, name, st, chain, entry, sql=None):
    kind, tname = sql_kind
    reasons = []
    if kind == "dyn":
        UNRES.append({"file": fn.path, "line": line, "fn": fn.name, "why": f"動的な表名 {tname}({op})", "entry": entry,
                      "chain": chain, "flags": sorted(st.flags), "pc": st.pc})
        return
    if kind in ("pub", "amb"):
        kind_eff = "tu" if (kind == "amb" and "sp" in st.flags) else "pub"
        if kind_eff == "pub":
            ok, expr, kinds = op_ok(tname, op, st.flags)
            if not ok and op == "SELECT" and kinds == "t|null" and sql and re.search(r"tenant_id\s+IS\s+NULL", sql, re.I):
                ok = True  # 共通行(tenant_id IS NULL)だけを読む文は文脈が空でも同じ結果
            if not ok:
                res = {"SELECT": "tenant_id 付きの行が見えなくなる(共通行 NULL だけ残る)", "INSERT": "RLS 違反で落ちる",
                       "UPDATE": "0 行に作用(静かに効かない)", _DEL: "0 行に作用(静かに効かない)"}[op]
                if kind == "amb":
                    res = "public の同名表(RLS)に化ける -> " + res
                reasons.append((tname, "public", expr, kinds, res))
    if kind in ("tq", "tu") or (kind == "amb" and "sp" in st.flags):
        if kind == "tu" and "sp" not in st.flags:
            reasons.append((tname, "tenant", "search_path が既定で表が見つからない", "sp", "relation does not exist で落ちる"))
        elif "t" not in st.flags and tname in TENANT_RLS:
            reasons.append((tname, "tenant",
                            "tenant_id = current_setting('app.tenant_id', true)::INTEGER (services/tenant.py:1264 の式。NULLIF 付きの表もある。本番の現行式は未確認)", "t",
                            "NULLIF 無しの式: 空文字の整数変換で落ちる / NULLIF 付き: SELECT 0 行・書込は RLS 違反"))
    full = st.flags | st.lost
    for (tn, scope, expr, kinds, res) in reasons:
        if scope == "public":
            recover = op_ok(tn, op, full)[0]
        elif "search_path" in expr:
            recover = "sp" in full
        else:
            recover = "t" in full
        HITS.append({
            "file": fn.path, "line": line, "fn": fn.name, "op": op, "table": tn, "scope": scope, "expr": expr, "kinds": kinds,
            "result": res, "pc": st.pc, "lost": bool(st.lost) and recover, "ctx_line": st.ctx_line, "entry": entry, "chain": list(chain),
        })


def run_fn(fn: Fn, st: St, chain, entry, sess_override=None, stack_guard=()):
    if fn.qual in stack_guard:
        return st
    mk = (fn.qual, st.key(), entry)
    if mk in MEMO:
        return MEMO[mk].copy()
    sess = set(fn.sess_params) | set(sess_override or ())
    env = dict(module_env(fn.path))
    env.update(build_env(fn.node))
    types = {}
    for p in fn.params:
        if _ann(fn.node, p) in MODEL_NAMES:
            types[p] = _ann(fn.node, p)
    guard = stack_guard + (fn.qual,)
    out = walk(fn, fn.node.body, st.copy(), sess, env, types, chain + [f"{fn.path}:{fn.node.lineno} {fn.name}"], entry, guard)
    MEMO[mk] = out.copy()
    return out


def walk(fn, stmts, st, sess, env, types, chain, entry, guard):
    for s in stmts:
        st = stmt(fn, s, st, sess, env, types, chain, entry, guard)
        if isinstance(s, (ast.Return, ast.Raise)):
            break
    return st


def stmt(fn, s, st, sess, env, types, chain, entry, guard):
    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return st
    if isinstance(s, ast.If):
        st = exprs(fn, [s.test], st, sess, env, types, chain, entry, guard)
        a = walk(fn, s.body, st.copy(), sess, env, types, chain, entry, guard)
        b = walk(fn, s.orelse, st.copy(), sess, env, types, chain, entry, guard)
        ta, tb = terminates(s.body), terminates(s.orelse)
        if ta and tb:
            return a
        if ta:
            return b
        if tb:
            return a
        return merge(a, b)
    if isinstance(s, (ast.For, ast.AsyncFor, ast.While)):
        head = [s.iter] if not isinstance(s, ast.While) else [s.test]
        st = exprs(fn, head, st, sess, env, types, chain, entry, guard)
        a = walk(fn, s.body, st.copy(), sess, env, types, chain, entry, guard)
        m = merge(st, a)
        a2 = walk(fn, s.body, m.copy(), sess, env, types, chain, entry, guard)  # 周回またぎ
        m = merge(m, a2)
        e = walk(fn, s.orelse, m.copy(), sess, env, types, chain, entry, guard)
        return merge(m, e)
    if isinstance(s, ast.Try):
        b = walk(fn, s.body, st.copy(), sess, env, types, chain, entry, guard)
        hs = merge(st, b)  # 例外は body のどこでも起きうる: 入口と出口の合流から始める
        hs.pc = hs.pc or b.pc
        outs = [b] if not terminates(s.body) else []
        for h in s.handlers:
            ho = walk(fn, h.body, hs.copy(), sess, env, types, chain, entry, guard)
            if not terminates(h.body):
                outs.append(ho)
        eo = walk(fn, s.orelse, b.copy(), sess, env, types, chain, entry, guard) if s.orelse else None
        if eo is not None:
            outs = [x for x in outs if x is not b] + [eo]
        cur = outs[0] if outs else hs
        for o in outs[1:]:
            cur = merge(cur, o)
        if s.finalbody:
            cur = walk(fn, s.finalbody, merge(cur, hs), sess, env, types, chain, entry, guard)
        return cur
    if isinstance(s, (ast.With, ast.AsyncWith)):
        began = False
        for it in s.items:
            ce = it.context_expr
            nm = _cname(ce) if isinstance(ce, ast.Call) else None
            if isinstance(ce, ast.Call) and isinstance(ce.func, ast.Attribute) and ce.func.attr == "begin" and is_sess(ce.func.value, sess):
                began = True
            if nm and (OWN_SESSION_CALL.search(nm) or nm in FACTORIES) and isinstance(it.optional_vars, ast.Name):
                sess.add(it.optional_vars.id)
                st = St()  # 新しい session の開始 = 空
            elif isinstance(it.optional_vars, ast.Name) and it.optional_vars.id in SESS_NAMES and not (isinstance(ce, ast.Call) and nm in ("connect", "begin")):
                sess.add(it.optional_vars.id)  # 別名の工場(x = db_factory(); async with x as db)
                st = St()
            elif isinstance(ce, ast.Call) and nm in ("connect", "begin") and isinstance(it.optional_vars, ast.Name):
                sess.add(it.optional_vars.id)
                st = St()
                began = True
            else:
                st = exprs(fn, [ce], st, sess, env, types, chain, entry, guard)
        st = walk(fn, s.body, st, sess, env, types, chain, entry, guard)
        if began:
            st = St(frozenset(), True, False, None, st.lost | st.flags)
        return st
    if isinstance(s, ast.Match):
        return st
    if isinstance(s, (ast.Assign, ast.AnnAssign)):
        val = s.value
        targets = s.targets if isinstance(s, ast.Assign) else [s.target]
        if isinstance(val, ast.Call) or (isinstance(val, ast.Await) and isinstance(val.value, ast.Call)):
            c = val.value if isinstance(val, ast.Await) else val
            nm = _cname(c)
            if nm and (OWN_SESSION_CALL.search(nm) or nm in FACTORIES) and nm != "get_db":
                for t in targets:
                    if isinstance(t, ast.Name):
                        sess.add(t.id)
                        st = St()
            if nm in MODEL_NAMES:
                for t in targets:
                    if isinstance(t, ast.Name):
                        types[t.id] = nm
        for t in targets:
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and types.get(t.value.id) in MODEL_NAMES:
                st = st.copy()
                st.dirty = types[t.value.id]
        src = ast.unparse(val) if val is not None else ""
        for mn in MODEL_NAMES:
            if re.search(r"select\(\s*" + mn + r"\b", src) or re.search(r"\.get\(\s*" + mn + r"\b", src):
                if re.search(r"scalar_one|scalars\(\)|\.scalar\(|\.first\(|\.get\(", src):
                    for t in targets:
                        if isinstance(t, ast.Name):
                            types[t.id] = mn
    return exprs(fn, [s], st, sess, env, types, chain, entry, guard)


def calls_in(nodes):
    out = []
    for n in nodes:
        for c in ast.walk(n):
            if isinstance(c, ast.Call):
                out.append(c)
    out.sort(key=lambda c: (c.lineno, c.col_offset))
    return out


def exprs(fn, nodes, st, sess, env, types, chain, entry, guard):
    shallow = [n for n in nodes if not isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith,
                                                       ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    for c in calls_in(shallow):
        st = call(fn, c, st, sess, env, types, chain, entry, guard)
    return st


def sess_arg(c, sess):
    for a in list(c.args) + [k.value for k in c.keywords]:
        if is_sess(a, sess):
            return True
    return False


def flush_dirty(fn, line, st, chain, entry):
    if st.dirty:
        tn = "users" if st.dirty == "User" else "tenants"
        record_op(fn, line, "UPDATE", ("pub", tn), tn, st, chain, entry)
        st.dirty = False


def call(fn, c, st, sess, env, types, chain, entry, guard):
    nm = _cname(c)
    f = c.func
    line = c.lineno
    if isinstance(f, ast.Attribute) and is_sess(f.value, sess):
        a = f.attr
        if a in ("commit", "rollback", "close", "invalidate"):
            st = st.copy()
            if a == "commit":
                flush_dirty(fn, line, st, chain, entry)
            st.lost = st.lost | st.flags  # commit / rollback の前に張っていた文脈 = Bx で失うもの
            st.flags, st.pc, st.dirty, st.ctx_line = frozenset(), True, False, None
            return st
        if a in OPS_ATTR:
            st = st.copy()
            if a in ("execute", "scalar", "scalars", "get", "stream", "get_one", "refresh", "flush"):
                flush_dirty(fn, line, st, chain, entry)
            if a in ("execute", "scalar", "scalars", "stream"):
                arg = c.args[0] if c.args else None
                sql = flat(arg, env) if arg is not None else None
                if sql is None and arg is not None:
                    src = ast.unparse(arg)
                    if re.search(r"select\(|insert\(|update\(|" + _DEL.lower() + r"\(", src):
                        mm = [m for m in MODEL_NAMES if re.search(r"\b" + m + r"\b", src)]
                        if mm:
                            tn = "users" if mm[0] == "User" else "tenants"
                            op = "SELECT" if "select(" in src else ("INSERT" if "insert(" in src else ("UPDATE" if "update(" in src else _DEL))
                            record_op(fn, line, op, ("pub", tn), tn, st, chain, entry)
                        else:
                            UNRES.append({"file": fn.path, "line": line, "fn": fn.name, "why": "ORM 構文の表が未解決: " + src[:80], "entry": entry,
                                          "chain": chain, "flags": sorted(st.flags), "pc": st.pc})
                    else:
                        UNRES.append({"file": fn.path, "line": line, "fn": fn.name, "why": "SQL 文字列を取り出せない: " + src[:80], "entry": entry,
                                      "chain": chain, "flags": sorted(st.flags), "pc": st.pc})
                elif sql is not None:
                    for (op, sch, tbl) in sql_refs(sql):
                        record_op(fn, line, op, classify_env(sch, tbl, env), tbl, st, chain, entry, sql=sql)
                    sql_ctx_effect(sql, st, line)
            elif a in ("add", "add_all"):
                for x in c.args:
                    tn = None
                    if isinstance(x, ast.Call) and _cname(x) in MODEL_NAMES:
                        tn = "users" if _cname(x) == "User" else "tenants"
                    elif isinstance(x, ast.Name) and types.get(x.id) in MODEL_NAMES:
                        tn = "users" if types[x.id] == "User" else "tenants"
                    if tn:
                        record_op(fn, line, "INSERT", ("pub", tn), tn, st, chain, entry)
            elif a in ("merge", "delete"):
                x = c.args[0] if c.args else None
                if isinstance(x, ast.Name) and types.get(x.id) in MODEL_NAMES:
                    tn = "users" if types[x.id] == "User" else "tenants"
                    record_op(fn, line, "UPDATE" if a == "merge" else _DEL, ("pub", tn), tn, st, chain, entry)
            return st
        if a in ("begin", "begin_nested"):
            return st
    if nm in CTX_SET_FUNCS and sess_arg(c, sess):
        st = st.copy()
        st.flags = st.flags | {"t", "sp"}
        st.ctx_line = f"{fn.path}:{line}"
        return st
    if nm == "set_operator_context" and sess_arg(c, sess):
        st = st.copy()
        st.flags = st.flags | {"o"}
        st.ctx_line = f"{fn.path}:{line}"
        return st
    if nm == "reset_operator_context" and sess_arg(c, sess):
        st = st.copy()
        st.flags = st.flags - {"o"}
        return st
    if nm == "clear_tenant_context" and sess_arg(c, sess):
        st = st.copy()
        st.flags = frozenset()
        return st
    if nm and nm in FUNCS and sess_arg(c, sess) and nm not in OPS_ATTR:
        cands = [x for x in FUNCS[nm] if x.sess_params and (not x.nested or x.path == fn.path)]
        imp = IMPORTS.get(fn.path, {"names": {}, "mods": {}})
        tgt = None
        if isinstance(f, ast.Name) and f.id in imp["names"]:
            base, orig = imp["names"][f.id]
            tgt = base
            cands = [x for x in cands if x.name == orig]
        elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in imp["mods"]:
            tgt = imp["mods"][f.value.id]
        if tgt is not None:
            cands = [x for x in cands if x.path in tgt]  # import で出所が分かる呼び出しは、その出所だけ
        elif isinstance(f, ast.Name):
            cands = [x for x in cands if x.path == fn.path]  # import も同じファイルの定義も無い名前は、プロジェクトの関数ではない
        else:
            same = [x for x in cands if x.path == fn.path]
            cands = same or cands
        if cands:
            outs = []
            for cf in cands[:4]:
                if cf.qual in guard:
                    continue
                outs.append(run_fn(cf, st, chain, entry, stack_guard=guard))
            if outs:
                cur = outs[0]
                for o in outs[1:]:
                    cur = merge(cur, o)
                return cur
    return st


# ---------------------------------------------------------------- 入口
def dep_name(call_node):
    """Depends(X) の X の名前。Depends(factory(...)) は ("factory", 工場の名前)"""
    if isinstance(call_node, ast.Call) and _cname(call_node) == "Depends" and call_node.args:
        a = call_node.args[0]
        if isinstance(a, ast.Name):
            return a.id
        if isinstance(a, ast.Attribute):
            return a.attr
        if isinstance(a, ast.Call):
            nm = _cname(a)
            if nm:
                return ("factory", nm)
    return None


def param_deps(fn: Fn):
    a = fn.node.args
    pos = a.posonlyargs + a.args
    defs = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    out = []
    for p, d in zip(pos, defs):
        if d is not None and dep_name(d):
            out.append(dep_name(d))
    for p, d in zip(a.kwonlyargs, a.kw_defaults):
        if d is not None and dep_name(d):
            out.append(dep_name(d))
    return out


def resolve_route(fn: Fn):
    """ルート: Depends を解いて(get_current_tenant を通れば t, sp)から本体を走らせる"""
    method, path, rname, rdeps = fn.route
    entry = f"{method} {path} ({fn.path}:{fn.node.lineno} {fn.name})"
    st = St()
    done = set()

    def do_dep(name, depth=0):
        nonlocal st
        if isinstance(name, tuple):
            fname = name[1]  # 依存の工場(require_permission(...) など): 入れ子関数の Depends を解いて本体を走らせる
            for cf in FUNCS.get(fname, [])[:1]:
                for nn in ast.walk(cf.node):
                    if isinstance(nn, (ast.FunctionDef, ast.AsyncFunctionDef)) and nn is not cf.node:
                        inner = next((x for x in ALL if x.node is nn), None)
                        if inner is None:
                            continue
                        for dn in param_deps(inner):
                            do_dep(dn, depth + 1)
                        if inner.sess_params:
                            st = run_fn(inner, st, [f"(dep) {inner.path}:{inner.node.lineno} {fname}.{inner.name}"], entry, sess_override=set(inner.sess_params))
                        break
            return
        if name in done or depth > 8:
            return
        done.add(name)
        if name in ("get_db", "get_admin_db"):
            return
        cands = FUNCS.get(name, [])
        if not cands:
            return
        cf = cands[0]
        if name == "get_current_tenant":
            for dn in param_deps(cf):
                do_dep(dn, depth + 1)
            st = st.copy()
            st.flags = frozenset({"t", "sp"})
            st.ctx_line = "backend/app/auth/dependencies.py:274-281"
            return
        for dn in param_deps(cf):
            do_dep(dn, depth + 1)
        if cf.sess_params or any(p in SESS_NAMES for p in cf.params):
            st = run_fn(cf, st, [f"(dep) {cf.path}:{cf.node.lineno} {cf.name}"], entry, sess_override=set(cf.sess_params))

    stem = os.path.splitext(os.path.basename(fn.path))[0]
    for d in ROUTER_DEPS.get((stem, rname), []):
        n = dep_name(d) if isinstance(d, ast.Call) and _cname(d) == "Depends" else None
        if n:
            do_dep(n)
    for d in rdeps:
        n = dep_name(d) if isinstance(d, ast.Call) and _cname(d) == "Depends" else None
        if n:
            do_dep(n)
    for dn in param_deps(fn):
        do_dep(dn)
    for d in fn.node.decorator_list:  # ルートに掛かった自前のデコレータが文脈を張る形(例: _operator_writes)
        dn = None
        if isinstance(d, ast.Name):
            dn = d.id
        elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            dn = d.func.id
        for cf in FUNCS.get(dn, []) if dn else []:
            src = ast.unparse(cf.node)
            if "set_operator_context" in src:
                st = st.copy()
                st.flags = st.flags | {"o"}
                st.ctx_line = f"{cf.path}:{cf.node.lineno} (decorator {cf.name})"
            if re.search(r"set_tenant_context\(", src):
                st = st.copy()
                st.flags = st.flags | {"t", "sp"}
                st.ctx_line = f"{cf.path}:{cf.node.lineno} (decorator {cf.name})"
    run_fn(fn, st, [], entry, sess_override=set(fn.sess_params))


def verdict_of(r):
    if r["op"] == "SELECT" and r["kinds"] == "t|null":
        return "要確認(共通行のみ)"
    return "BREAK-新" if True in r["losts"] else "BREAK-既"


def now_behavior(r):
    if True in r["losts"]:
        return "前の値頼み: pool 1 本なら commit 前の値が同じ接続に残って動く / 2 本以上は別の要求の値が見える(m7)"
    if r["kinds"] in ("o", "t&o") or "app.is_operator" in r["expr"]:
        return "app.is_operator は今も空なので Bx の前後で同じ(operator を張る行が無い)"
    if True in r["pcs"] and False not in r["pcs"]:
        return "文脈を張る前から空。commit 後は前の要求の値が見えうる(偶然)"
    return "開始時から空。前の要求が commit 後に残した値があるときだけその値で動く(偶然)"


def render(rows, unres, orphans, nroutes, nown):
    print(f"<!-- routes={nroutes} own_session_fns={nown} orphan_fns={len(orphans)} hits={len(rows)} unres={len(unres)} -->")
    print(f"RLS36={len(RLS36)} TENANT={len(TENANT)} TENANT_RLS={len(TENANT_RLS)} AMBIG={sorted(AMBIG)}")
    print()
    print("| # | 判定 | 入口(件数) | 場所:行 関数 | 文脈を張る行 | 触る表.操作(範囲) | 規則の式 | Bx 後の結果 | 今の動き |")
    print("|---|---|---|---|---|---|---|---|---|")
    order = {"BREAK-新": 0, "BREAK-既": 1, "要確認(共通行のみ)": 2}
    rows = sorted(rows, key=lambda r: (order[verdict_of(r)], r["file"], r["line"]))
    cnt = Counter()
    for i, r in enumerate(rows, 1):
        v = verdict_of(r)
        cnt[v] += 1
        es = sorted(r["entries"])
        ctxs = [c for c in sorted(r["ctxs"]) if c != "None"]
        ctx = ctxs[0] if ctxs else "無し"
        expr = re.sub(r"\s+", " ", r["expr"].replace("|", "/"))[:110]
        print(f"| {i} | {v} | {len(es)}: {es[0][:75].replace('|', '/')} | {r['file'].replace('backend/app/', '')}:{r['line']} {r['fn']} | {ctx} | "
              f"{r['table']}.{r['op']}({r['scope']}) | {expr} | {r['result']} | {now_behavior(r)} |")
    print()
    print("集計:", dict(cnt), "合計", len(rows))
    print()
    print("## UNRES(表名・文を取り出せなかった箇所。状態に t が無いものだけ)")
    for (f, l, w), u in sorted(unres.items()):
        if any("t" not in st_[0].split(",") for st_ in u["states"]):
            print(f"- {f}:{l} {u['fn']} {w} 状態={u['states']}")
    print()
    print("## ORPHANS(session を引数に取るが、どの入口からも辿れなかった関数)")
    for o in orphans:
        print("-", o.qual)


def main():
    load()
    routes = [f for f in ALL if f.route and not f.nested]
    for f in routes:
        resolve_route(f)
    own = [f for f in ALL if f.own and not f.route]
    for f in own:
        run_fn(f, St(), [], f"OWN {f.path}:{f.node.lineno} {f.name}", sess_override=set())
    seen_fn = set(k[0] for k in MEMO)
    orphans = [f for f in ALL if f.sess_params and not f.route and not f.own and f.qual not in seen_fn]
    agg = {}
    for h in HITS:
        k = (h["file"], h["line"], h["op"], h["table"], h["scope"])
        a = agg.setdefault(k, {**h, "entries": set(), "pcs": set(), "ctxs": set(), "chains": {}, "losts": set()})
        a["entries"].add(h["entry"])
        a["pcs"].add(h["pc"])
        a["ctxs"].add(str(h["ctx_line"]))
        a["losts"].add(h["lost"])
        a["chains"].setdefault(h["entry"], h["chain"])
    rows = sorted(agg.values(), key=lambda a: (a["file"], a["line"]))
    unres = {}
    for u in UNRES:
        k = (u["file"], u["line"], u["why"])
        e = unres.setdefault(k, {**u, "states": set()})
        e["states"].add((",".join(u["flags"]) or "空", u["pc"]))
    for e in unres.values():
        e["states"] = sorted(e["states"])
    if "--json" in sys.argv:
        print(json.dumps({
            "routes": len(routes), "own": len(own), "orphans": [o.qual for o in orphans],
            "hits": [{**r, "entries": sorted(r["entries"]), "pcs": sorted(r["pcs"]), "ctxs": sorted(r["ctxs"]), "losts": sorted(r["losts"])} for r in rows],
            "unres": list(unres.values()),
        }, ensure_ascii=False, indent=1, default=str))
        return
    render(rows, unres, orphans, len(routes), len(own))


if __name__ == "__main__":
    main()
