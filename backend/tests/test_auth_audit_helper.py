"""自社ログインの監査記録が共通関数 `_record_auth_audit` を通ることの試験（便5 追補）。

SQLite でも動く。app/routers/auth.py の本文を ast で調べる。
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.routers.auth as auth_module

_AUTH_PY = Path(auth_module.__file__)


def _functions_calling(name: str) -> list[str]:
    tree = ast.parse(_AUTH_PY.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Name)
                and sub.func.id == name
            ):
                found.append(node.name)
                break
    return found


def test_record_audit_log_is_called_only_from_helper():
    assert _functions_calling("record_audit_log") == ["_record_auth_audit"]


@pytest.mark.asyncio
async def test_helper_sets_tenant_then_records_then_clears():
    calls: list[str] = []

    async def _set(*_a, **_k):
        calls.append("set")

    async def _rec(*_a, **_k):
        calls.append("record")

    async def _clear(*_a, **_k):
        calls.append("clear")

    with (
        patch.object(auth_module, "set_tenant_context", AsyncMock(side_effect=_set)),
        patch.object(auth_module, "record_audit_log", AsyncMock(side_effect=_rec)),
        patch.object(auth_module, "clear_tenant_context", AsyncMock(side_effect=_clear)),
    ):
        await auth_module._record_auth_audit(
            MagicMock(),
            tenant_id=1,
            user_id=2,
            action="create",
            table_name="webauthn_credentials",
            record_id=3,
            new_data={"event": "x"},
        )

    assert calls == ["set", "record", "clear"]
