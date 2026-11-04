"""tenant_discord_config を読む・書く SQL が purpose を必ず指定していることの漏れ止め。

discord-server-management 便1b（設計 §4-1 改訂1）:
  主キーが (tenant_id, purpose) になったので、purpose を書かない SQL は
  顧客用（customer）と自社用（own）の行を取り違える。
  backend/app の全 .py を ast で読み、public.tenant_discord_config を含む
  文字列定数が purpose を含むことを確かめる。
"""
from __future__ import annotations

import ast
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent / "app"
_TABLE = "public.tenant_discord_config"
# §3-1 の 5 つ・§3-2〜§3-6 の 5 つ・§4 の 1 つ
_MIN_EXPECTED = 11


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """モジュール・関数・クラスの最初の文（説明文）の定数ノードの id を返す。"""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _collect() -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []
    for path in sorted(_APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        skip = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in skip
                and _TABLE in node.value
            ):
                found.append((str(path.relative_to(_APP_DIR.parent)), node.lineno, node.value))
    return found


def test_found_enough_statements() -> None:
    """探し方が壊れて 0 件で素通りしないこと。"""
    found = _collect()
    assert len(found) >= _MIN_EXPECTED, (
        f"{_TABLE} を含む文字列が {len(found)} 件しか見つからない（{_MIN_EXPECTED} 件以上のはず）"
    )


def test_every_statement_specifies_purpose() -> None:
    missing = [
        f"{rel}:{lineno}" for rel, lineno, value in _collect() if "purpose" not in value
    ]
    assert not missing, "purpose を指定していない SQL: " + ", ".join(missing)
