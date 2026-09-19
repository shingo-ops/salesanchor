"""
MIG-05 Task 3: tcg_mirror タスクのテスト。

重点:
  - MIRROR_SPREADSHEET_ID が固定値であることを確認
  - シート自動作成経路がコードに存在しないことを確認
  - TCG_SHEETS_SA_KEY_FILE 未設定時にスキップすることを確認
"""
from __future__ import annotations

import ast
import inspect
import os
import pathlib
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.tcg_mirror import (
    MIRROR_SPREADSHEET_ID,
    _assert_no_create_path,
    run_tcg_mirror_write,
)
from tcg_migration.scripts.write_mirror_once import (
    MIRROR_SPREADSHEET_ID as SCRIPT_MIRROR_ID,
)


# ──────────────────────────────────────────────────────────────────────────────
# MIRROR_SPREADSHEET_ID 固定値テスト
# ──────────────────────────────────────────────────────────────────────────────

EXPECTED_ID = "1IBIpge6Qz2arq93OHmRFnCGBMj2kVhrgEjtY8c5ecus"


def test_mirror_spreadsheet_id_is_fixed() -> None:
    """MIRROR_SPREADSHEET_ID がハードコードされた固定値である"""
    assert MIRROR_SPREADSHEET_ID == EXPECTED_ID


def test_script_mirror_id_matches_task() -> None:
    """write_mirror_once.py と tcg_mirror.py の ID が一致する"""
    assert SCRIPT_MIRROR_ID == MIRROR_SPREADSHEET_ID


# ──────────────────────────────────────────────────────────────────────────────
# シート自動作成経路の不在を AST で確認
# ──────────────────────────────────────────────────────────────────────────────

def _get_source(module_path: str) -> str:
    p = pathlib.Path(module_path)
    return p.read_text(encoding="utf-8")


def test_tcg_mirror_has_no_create_call() -> None:
    """
    app/tasks/tcg_mirror.py に gc.create() / spreadsheets().create() の
    呼び出しが存在しないことを AST で検証する。
    """
    import app.tasks.tcg_mirror as mod

    src = inspect.getsource(mod)
    tree = ast.parse(src)

    forbidden_calls = {"create"}
    found: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # gc.create(...) のような Attribute 呼び出し
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden_calls:
                    found.append(f"line {node.lineno}: {ast.unparse(node)}")

    assert not found, (
        "tcg_mirror.py にシート作成呼び出しが存在します:\n"
        + "\n".join(found)
    )


def test_write_mirror_once_has_no_create_call() -> None:
    """
    write_mirror_once.py に gc.create() 呼び出しが存在しないことを
    AST で検証する。
    """
    import tcg_migration.scripts.write_mirror_once as mod

    src = inspect.getsource(mod)
    tree = ast.parse(src)

    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "create" and "gc" in ast.unparse(node.func.value):
                    found.append(f"line {node.lineno}: {ast.unparse(node)}")

    assert not found, (
        "write_mirror_once.py に gc.create() 呼び出しが存在します:\n"
        + "\n".join(found)
    )


# ──────────────────────────────────────────────────────────────────────────────
# TCG_SHEETS_SA_KEY_FILE 未設定時スキップ
# ──────────────────────────────────────────────────────────────────────────────

def test_run_tcg_mirror_write_skips_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """TCG_SHEETS_SA_KEY_FILE が未設定の場合、書き出しをスキップして終了する"""
    monkeypatch.delenv("TCG_SHEETS_SA_KEY_FILE", raising=False)

    # DB / gspread には一切触れない
    with patch("app.tasks.tcg_mirror._build_client") as mock_build:
        run_tcg_mirror_write()
        mock_build.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# _assert_no_create_path はコントラクト関数（呼べることを確認）
# ──────────────────────────────────────────────────────────────────────────────

def test_assert_no_create_path_callable() -> None:
    """_assert_no_create_path が例外なく呼べる（コントラクト存在確認）"""
    _assert_no_create_path()  # raises なければ OK
