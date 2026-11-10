"""DB を使う試しの道具が set_idle_tx_limit( を呼んでいることの見張り（DB を使わない）。

設計: docs/handoff/replay-tx-release/design.md §14 C6'
範囲外: 別のモジュールの関数を通して接続を得る道具は見つけない（本番反映の前の点検に任せる）。
"""
from __future__ import annotations

import re
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_APP_ROOT = _BACKEND / "app"
_TOOLS_ROOT = _APP_ROOT / "tools"

_DB_PATTERNS = [re.compile(p) for p in (
    r"\b_get_sync_session\b",
    r"\bSession\(",
    r"\bSessionLocal\(",
    r"\bAsyncSessionLocal\(",
    r"\b_engine\b",
    r"\bcreate_engine\(",
    r"\bsessionmaker\(",
    r"\.connect\(",
    r"from app\.database import",
)]
_OUTSIDE_PATTERNS = [re.compile(p) for p in (
    r"from app\.tools",
    r"import app\.tools",
    r"from app import tools",
)]

EXCEPTIONS = {
    "reextract_v6_with_v102.py": (
        "書き込みを含み、投稿ごとに読み取りの後で取引を閉じる（:456）。"
        "共通の rollback を足すと書き込みを捨てうる。開いたままの握りは本番反映の前の点検が見つける"
    ),
}


def _uses_db(text: str) -> bool:
    return any(p.search(text) for p in _DB_PATTERNS)


def _tool_files(tools_root: Path):
    for path in sorted(tools_root.rglob("*.py")):
        rel = path.relative_to(tools_root).as_posix()
        if path.name == "__init__.py" or rel == "_tx_guard.py":
            continue
        yield rel, path


def find_unguarded(tools_root: Path, exceptions: dict) -> list[str]:
    found = []
    for rel, path in _tool_files(tools_root):
        if rel in exceptions:
            continue
        body = path.read_text(encoding="utf-8")
        if _uses_db(body) and "set_idle_tx_limit(" not in body:
            found.append(rel)
    return found


def find_stale_exceptions(tools_root: Path, exceptions: dict) -> list[str]:
    stale = []
    for rel in exceptions:
        path = tools_root / rel
        if not path.is_file() or not _uses_db(path.read_text(encoding="utf-8")):
            stale.append(rel)
    return stale


def find_outside_imports(app_root: Path, tools_root: Path) -> list[str]:
    found = []
    tools_resolved = tools_root.resolve()
    for path in sorted(app_root.rglob("*.py")):
        if tools_resolved in path.resolve().parents:
            continue
        body = path.read_text(encoding="utf-8")
        if any(p.search(body) for p in _OUTSIDE_PATTERNS):
            found.append(path.relative_to(app_root).as_posix())
    return found


def test_real_tree_has_no_unguarded_tools():
    found = find_unguarded(_TOOLS_ROOT, EXCEPTIONS)
    assert found == [], f"set_idle_tx_limit( を呼んでいない DB 道具: {found}"


def test_real_tree_has_no_stale_exceptions():
    found = find_stale_exceptions(_TOOLS_ROOT, EXCEPTIONS)
    assert found == [], f"古くなった例外表の行: {found}"


def test_real_tree_has_no_outside_imports_of_tools():
    found = find_outside_imports(_APP_ROOT, _TOOLS_ROOT)
    assert found == [], f"app/tools の外から app.tools を読み込むファイル: {found}"


def test_unguarded_detected_in_tmp_tree(tmp_path):
    (tmp_path / "tools" / "sub").mkdir(parents=True)
    (tmp_path / "tools" / "sub" / "x.py").write_text("_engine.connect()\n", encoding="utf-8")
    assert find_unguarded(tmp_path / "tools", {}) == ["sub/x.py"]


def test_outside_import_detected_in_tmp_tree(tmp_path):
    (tmp_path / "app" / "tools").mkdir(parents=True)
    (tmp_path / "app" / "tasks").mkdir(parents=True)
    (tmp_path / "app" / "tools" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "app" / "tasks" / "t.py").write_text("from app.tools import prompt_ab\n", encoding="utf-8")
    assert find_outside_imports(tmp_path / "app", tmp_path / "app" / "tools") == ["tasks/t.py"]


def test_word_boundary_in_db_detection(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "a.py").write_text("get_engine(\n", encoding="utf-8")
    assert find_unguarded(tools, {}) == []
    (tools / "b.py").write_text("SessionLocal(\n", encoding="utf-8")
    assert find_unguarded(tools, {}) == ["b.py"]
