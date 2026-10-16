"""
見張り: DB 例外の中身（SQL 文・入力値・制約名）を HTTP 応答に入れない。

backend/app の *.py を AST で読み、except 節（型が IntegrityError / Exception /
BaseException / SQLAlchemyError / DBAPIError / StatementError のいずれかを含む、
または型なし）の中で、HTTPException(...) / JSONResponse(...) の detail / content の
式に except の変数名が現れたら失敗する。除外集合は持たない。

応答に出さない例外は app.routers._utils.log_hidden_error で backend のログにだけ残す。
設計: docs/handoff/s3-db-error-detail/design.md §5 T1
"""
from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_APP_ROOT = _REPO_ROOT / "backend" / "app"

_WATCHED_TYPES = {
    "IntegrityError",
    "Exception",
    "BaseException",
    "SQLAlchemyError",
    "DBAPIError",
    "StatementError",
}
_RESPONSE_CALLS = {"HTTPException", "JSONResponse"}
_RESPONSE_KEYWORDS = {"detail", "content"}


def _type_names(type_node: ast.expr | None) -> set[str]:
    if type_node is None:
        return set()
    names: set[str] = set()
    for sub in ast.walk(type_node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.add(sub.attr)
    return names


def _is_watched(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    return bool(_type_names(handler.type) & _WATCHED_TYPES)


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _uses_name(node: ast.AST, var: str) -> bool:
    return any(isinstance(n, ast.Name) and n.id == var for n in ast.walk(node))


def _find_violations() -> list[str]:
    found: list[str] = []
    for path in sorted(_APP_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(_REPO_ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for handler in ast.walk(tree):
            if not isinstance(handler, ast.ExceptHandler):
                continue
            if handler.name is None or not _is_watched(handler):
                continue
            for node in ast.walk(handler):
                if not isinstance(node, ast.Call):
                    continue
                if _call_name(node) not in _RESPONSE_CALLS:
                    continue
                for kw in node.keywords:
                    if kw.arg in _RESPONSE_KEYWORDS and _uses_name(kw.value, handler.name):
                        found.append(f"{rel}:{node.lineno} ({handler.name})")
    return sorted(set(found))


def test_no_exception_text_in_http_detail() -> None:
    found = _find_violations()
    assert not found, (
        f"例外の中身を応答に入れている箇所が {len(found)} 件あります。"
        "detail は固定文言にし、中身は app.routers._utils.log_hidden_error でログに残してください:\n"
        + "\n".join(found)
    )
