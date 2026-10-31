#!/usr/bin/env python3
"""段 0b: 135 画面（SPEED_TARGETS）とファイルの対応表を作る（設計の根拠を誰でも再現できるようにする・読むだけ）。

使い方: リポジトリの根で `python3 docs/handoff/line-like-speed/screen-map.py`
出力: Markdown の表を標準出力へ。最後の数の行を標準エラーへ。
読むもの: tests/prod-check/page-speed-targets.ts・frontend/src/App.tsx・
frontend/src/pages/super-admin/AnalysisRulesPage.tsx・u1-count.py の結果。
"""
import pathlib
import re
import subprocess
import sys

SRC = pathlib.Path("frontend/src")
APP = SRC / "App.tsx"
RULES = SRC / "pages/super-admin/AnalysisRulesPage.tsx"
TARGETS = pathlib.Path("tests/prod-check/page-speed-targets.ts")
U1 = pathlib.Path("docs/handoff/line-like-speed/u1-count.py")


def app_routes():
    """App.tsx の <Route> を入れ子ごとたどり、(全体の道すじ, 部品名, Navigate 先, 行) を返す。"""
    text = APP.read_text(encoding="utf-8")
    imports = {m.group(1): "frontend/src/" + m.group(2) + ".tsx"
               for m in re.finditer(r'^import\s+(\w+)\s+from\s+"\./(pages/[^"]+)";', text, re.M)}
    routes, stack = [], []
    for m in re.finditer(r"<Route\b|</Route>", text):
        if m.group(0) == "</Route>":
            stack.pop()
            continue
        j, depth = m.end(), 0
        while True:
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == ">" and depth == 0:
                break
            j += 1
        tag = text[m.start():j + 1]
        pm = re.search(r'\bpath="([^"]*)"', tag)
        parent = next((p for p in reversed(stack) if p is not None), "")
        full = None
        if pm:
            p = pm.group(1)
            full = p if p.startswith("/") else parent.rstrip("/") + "/" + p
        em = re.search(r"element=\{\s*<(\w+)", tag)
        nav = re.search(r'<Navigate\s+to="([^"]+)"', tag)
        if full is not None:
            routes.append({"path": full, "elem": em.group(1) if em else None,
                           "nav": nav.group(1) if nav else None,
                           "line": text.count("\n", 0, m.start()) + 1})
        if not tag.rstrip(">").rstrip().endswith("/"):
            stack.append(full if full is not None else parent)
    return routes, imports


def find_route(routes, path):
    hits = [r for r in routes if r["path"] == path]
    if not hits:
        probe = re.sub(r":\w+", "X", path)
        hits = [r for r in routes
                if re.match("^" + re.sub(r":\w+", "[^/]+", r["path"]) + "$", probe)]
    return hits[0] if hits else None


def section_panels():
    """AnalysisRulesPage.tsx の activeSection ごとに描かれる部品のファイル（行つき）を返す。"""
    text = RULES.read_text(encoding="utf-8")
    base = RULES.parent
    imp = {}
    for m in re.finditer(r'^import\s+(?:(\w+)|\{([^}]*)\})\s+from\s+"(\.[^"]+)";', text, re.M):
        names = [m.group(1)] if m.group(1) else [n.strip() for n in m.group(2).split(",")]
        target = (base / m.group(3)).resolve().relative_to(pathlib.Path.cwd().resolve())
        for n in names:
            if n and not n.startswith("type "):
                imp[n] = f"{target}.tsx"
    local = {m.group(1): f"{RULES}:{text.count(chr(10), 0, m.start()) + 1}"
             for m in re.finditer(r"^function\s+(\w+)\s*\(", text, re.M)}
    out = {}
    marks = list(re.finditer(r'activeSection === "([\w-]+)" &&', text))
    for k, m in enumerate(marks):
        end = marks[k + 1].start() if k + 1 < len(marks) else len(text)
        line = text.count("\n", 0, m.start()) + 1
        comps = re.findall(r"<([A-Z]\w+)", text[m.end():end])
        files = [imp.get(c) or local.get(c) or f"{c}（読み込み元なし）" for c in comps]
        out[m.group(1)] = (f"AnalysisRulesPage.tsx:{line}", files)
    return out


def child_pages(path):
    """画面のファイルが読み込む、別の *Page.tsx（親の中で中身を描く部品）を行つきで返す。"""
    p = pathlib.Path(path)
    if not path or not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'^import\s+(?:\w+|\{[^}]*\})\s+from\s+"(\.{1,2}/[^"]*Page)";', text, re.M):
        target = (p.parent / m.group(1)).resolve().relative_to(pathlib.Path.cwd().resolve())
        out.append(f"{p.name}:{text.count(chr(10), 0, m.start()) + 1} で読む → {target}.tsx")
    return out


def u1_classes():
    res = subprocess.run([sys.executable, "-I", str(U1)], capture_output=True, text=True, check=True)
    return {row.split("\t")[0]: row.split("\t")[1] for row in res.stdout.splitlines() if "\t" in row}


def u1_of(cls, path):
    pre = "frontend/src/pages/"
    return cls.get(path[len(pre):], "—") if path.startswith(pre) else "—"


def main():
    routes, imports = app_routes()
    panels = section_panels()
    cls = u1_classes()
    src = TARGETS.read_text(encoding="utf-8")
    targets = re.findall(r'route: "([^"]*)", kind: "([^"]*)"(?:, to: "([^"]*)")?', src)
    print("| # | 画面の道すじ | 種類 | App.tsx の行 | ファイル | U1 | 中で描かれる部品・行き先 |")
    print("|---|---|---|---|---|---|---|")
    no_file = 0
    for n, (route, kind, to) in enumerate(targets, 1):
        r = find_route(routes, route.split("?")[0])
        f = imports.get(r["elem"], "") if r else ""
        if not f or not pathlib.Path(f).exists():
            no_file += 1
        inner = ""
        if kind == "section":
            key = route.split("section=")[1]
            if key in panels:
                where, files = panels[key]
                inner = f"{where} → " + "・".join(files)
            else:
                inner = "分岐なし（中身の場所に部品が描かれない）"
        elif kind == "redirect":
            d = find_route(routes, to)
            df = imports.get(d["elem"], "") if d else ""
            inner = f"行き先 {to} → {df or '見つからず'}"
        else:
            inner = "・".join(child_pages(f))
        line = f"App.tsx:{r['line']}" if r else "無い"
        print(f"| {n} | `{route}` | {kind or '固定'} | {line} | {f or '無い'} | {u1_of(cls, f)} | {inner} |")
    files = {imports.get(r["elem"]) for r in routes if r["elem"]}
    files |= {c.split(" → ")[1] for f in list(files) if f for c in child_pages(f)}
    pages = sorted(p for p in (SRC / "pages").rglob("*Page.tsx") if not p.name.endswith(".test.tsx"))
    absent = [str(p) for p in pages if str(p) not in files
              and not any(str(p) in fs for _, fs in panels.values())]
    print(f"# targets {len(targets)} no_file {no_file} pages {len(pages)} "
          f"pages_not_in_routes {len(absent)}: {' '.join(absent)}", file=sys.stderr)


if __name__ == "__main__":
    main()
