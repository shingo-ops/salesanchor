"""smoke 認証経路の最小権限化（ADR-1017）のテスト。

DB・Redis・Firebase には接続しない（すべてモック）。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.auth.dependencies import get_current_user

SMOKE_TOKEN = "smoke-test-token-aaaaaaaaaaaaaaaaaaaaaaaa"
SMOKE_EMAIL = "smoke-user@example.com"


def _db_returning(user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


async def _run(bearer, user, token=SMOKE_TOKEN, email=SMOKE_EMAIL):
    request = MagicMock()
    cred = MagicMock()
    cred.credentials = bearer
    with patch("app.auth.dependencies._init_firebase"), patch(
        "app.auth.dependencies._get_client_ip", return_value="127.0.0.1"
    ), patch("app.auth.dependencies._SMOKE_SERVICE_TOKEN", token), patch(
        "app.auth.dependencies._SMOKE_SERVICE_EMAIL", email
    ), patch(
        "app.auth.dependencies.is_token_blacklisted", AsyncMock(return_value=False)
    ), patch(
        "app.auth.dependencies.get_cached_jwt", AsyncMock(return_value=None)
    ), patch(
        "app.auth.dependencies.check_auth_rate_limit", AsyncMock(return_value=False)
    ), patch(
        "app.auth.dependencies.record_auth_failure", AsyncMock()
    ), patch(
        "app.auth.dependencies.firebase_auth.verify_id_token",
        side_effect=Exception("invalid"),
    ):
        return await get_current_user(request, cred, _db_returning(user))


def _user(is_super_admin):
    return SimpleNamespace(id=1, tenant_id=4, email=SMOKE_EMAIL, is_super_admin=is_super_admin)


async def test_smoke_token_resolving_to_super_admin_is_rejected_401():
    with pytest.raises(HTTPException) as exc:
        await _run(SMOKE_TOKEN, _user(True))
    assert exc.value.status_code == 401


async def test_smoke_token_non_ascii_bearer_is_401_not_500():
    with pytest.raises(HTTPException) as exc:
        await _run("トークン-非ASCII", _user(False))
    assert exc.value.status_code == 401


async def test_smoke_token_least_privilege_user_passes(caplog):
    user = _user(False)
    with caplog.at_level("INFO", logger="app.auth.dependencies"):
        result = await _run(SMOKE_TOKEN, user)
    assert result is user
    assert "smoke認証成立" in caplog.text
    assert SMOKE_TOKEN not in caplog.text


async def test_smoke_disabled_when_env_empty_falls_through_to_firebase():
    # token 空 → 不活性。Firebase 検証に入り（失敗して）401。
    with pytest.raises(HTTPException) as exc:
        await _run(SMOKE_TOKEN, _user(False), token="")
    assert exc.value.status_code == 401
    assert exc.value.detail == "無効な認証トークンです"


async def test_smoke_mismatched_token_falls_through_to_firebase():
    with pytest.raises(HTTPException) as exc:
        await _run("wrong-token", _user(False))
    assert exc.value.status_code == 401
    assert exc.value.detail == "無効な認証トークンです"
