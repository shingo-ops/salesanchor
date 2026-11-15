"""試験ファイルの読み込みのときに「今」を読む書き方を止める。

読み込みのときに決めた時刻は、試験全体が長くなるほど古くなる。時刻の境目を確かめる試験が時々落ちる
（2026-11-11〜13 に3回。docs/handoff/extraction-job-recovery/recon.md「追記（2026-11-13）」）。
読み込みのときに動くのは、一番外とクラスの本体（if/try/with/for の中も）・デコレータの引数・
関数と lambda の既定値。関数と lambda の本体は呼ばれたときに動くので見ない。
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent
_CLOCK_ATTRS = {"now", "utcnow", "today"}
_TIME_FUNCS = {
    "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns",
}


def _time_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """time の取り込み方を集める。(import time [as X] の名前, from time import time [as t] の名前)。"""
    modules = {"time"}
    funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "time":
                    modules.add(alias.asname or alias.name)
        if isinstance(node, ast.ImportFrom) and node.module == "time":
            for alias in node.names:
                if alias.name in _TIME_FUNCS:
                    funcs.add(alias.asname or alias.name)
    return modules, funcs


def _is_clock_call(node: ast.AST, time_names: tuple[set[str], set[str]]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    modules, funcs = time_names
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in _CLOCK_ATTRS:
            return True
        if func.attr in _TIME_FUNCS and isinstance(func.value, ast.Name) and func.value.id in modules:
            return True
    if isinstance(func, ast.Name) and func.id in funcs:
        return True
    return False


def _import_time_nodes(node: ast.AST):
    """読み込みのときに評価される式の木を返す。関数と lambda は本体を飛ばし、既定値とデコレータだけ見る。"""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        yield from node.decorator_list
        yield from node.args.defaults
        yield from (d for d in node.args.kw_defaults if d is not None)
        return
    if isinstance(node, ast.Lambda):
        yield from node.args.defaults
        yield from (d for d in node.args.kw_defaults if d is not None)
        return
    yield node


def _clock_lines(tree: ast.Module) -> list[int]:
    time_names = _time_names(tree)
    lines = []
    stack: list[ast.AST] = list(tree.body)
    while stack:
        cur = stack.pop()
        for part in _import_time_nodes(cur):
            if part is not cur:
                stack.append(part)
                continue
            if _is_clock_call(cur, time_names):
                lines.append(cur.lineno)
            stack.extend(ast.iter_child_nodes(cur))
    return sorted(set(lines))


def _findings() -> list[str]:
    found = []
    for path in sorted(TESTS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line in _clock_lines(tree):
            found.append(f"{path.relative_to(TESTS)}:{line}")
    return found


_SELF_CHECKS = [
    ("_NOW = datetime.now(timezone.utc)", True),
    ("T = time.time()", True),
    ("D = date.today() - timedelta(days=1)", True),
    ("from time import time as t\nX = t()", True),
    ("import time as tm\nX = tm.time()", True),
    ("X: float = time.monotonic()", True),
    ("if True:\n    N = datetime.now()", True),
    ("try:\n    N = datetime.now()\nexcept Exception:\n    pass", True),
    ("@pytest.mark.parametrize('v', [svc.now()])\ndef test_a(v):\n    pass", True),
    ("def f(t=datetime.now()):\n    pass", True),
    ("class C:\n    N = datetime.utcnow()", True),
    ("f = lambda t=datetime.now(): t", True),
    ("f = lambda: datetime.now()", False),
    ("def test_a():\n    n = datetime.now()", False),
    ("X = timedelta(minutes=5)", False),
    ("class C:\n    def m(self):\n        return time.time()", False),
]


def test_detector_catches_the_pattern():
    for source, expected in _SELF_CHECKS:
        assert bool(_clock_lines(ast.parse(source))) is expected, source


def test_no_clock_read_at_import_time():
    found = _findings()
    assert found == [], (
        "試験ファイルの読み込みのときに時刻を読んでいます。試験本体の中で読んでください"
        "（読み込み時の時刻は試験全体が長いほど古くなり、時刻の境目の試験が時々落ちます）: "
        + ", ".join(found)
    )
