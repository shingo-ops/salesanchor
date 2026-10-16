"""閲覧者のトークン・get_current_viewer・閲覧者の表（ADR-1019 段1）。"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth import self_tokens, viewer_dependencies, viewer_tokens
from tests.rls_bootstrap import _ensure_public_users
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

SECRET = "v" * 48
MIGRATION_NAME = "20261016_150000_add_viewer_accounts.sql"


@pytest.fixture(autouse=True)
def viewer_env(monkeypatch):
    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", SECRET)


# ── トークン ───────────────────────────────────────────────────


def test_token_shape():
    token, expires_at = viewer_tokens.create_viewer_access_token(7)
    claims = jwt.get_unverified_claims(token)
    assert claims["iss"] == "salesanchor-viewer"
    assert claims["sub"] == "viewer:7"
    assert isinstance(claims["iat"], int) and not isinstance(claims["iat"], bool)
    assert claims["exp"] - claims["iat"] == 43200
    assert "email" not in claims
    assert expires_at == datetime.fromtimestamp(claims["exp"], timezone.utc)
    assert viewer_tokens.decode_viewer_token(token)["sub"] == "viewer:7"


def test_empty_secret_fails_create_and_decode(monkeypatch):
    token, _ = viewer_tokens.create_viewer_access_token(1)
    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", "")
    with pytest.raises(JWTError):
        viewer_tokens.create_viewer_access_token(1)
    with pytest.raises(JWTError):
        viewer_tokens.decode_viewer_token(token)


def test_short_secret_fails_create_and_decode(monkeypatch):
    token, _ = viewer_tokens.create_viewer_access_token(1)
    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", "s" * 31)
    with pytest.raises(JWTError):
        viewer_tokens.create_viewer_access_token(1)
    with pytest.raises(JWTError):
        viewer_tokens.decode_viewer_token(token)


def test_same_secret_as_app_fails_create_and_decode(monkeypatch):
    token, _ = viewer_tokens.create_viewer_access_token(1)
    monkeypatch.setenv("AUTH_JWT_SECRET", SECRET)
    with pytest.raises(JWTError):
        viewer_tokens.create_viewer_access_token(1)
    with pytest.raises(JWTError):
        viewer_tokens.decode_viewer_token(token)


def test_app_token_rejected_by_decode_viewer_token(monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET", "a" * 48)
    app_token = self_tokens.create_access_token(1, "u@example.com", None)
    with pytest.raises(JWTError):
        viewer_tokens.decode_viewer_token(app_token)


def test_app_secret_does_not_verify_viewer_token():
    """アプリの鍵で署名した閲覧者の形のトークンは通らない。"""
    claims = {"iss": "salesanchor-viewer", "sub": "viewer:1", "iat": int(time.time()), "exp": int(time.time()) + 60}
    forged = jwt.encode(claims, "a" * 48, algorithm="HS256")
    with pytest.raises(JWTError):
        viewer_tokens.decode_viewer_token(forged)


# ── get_current_viewer（DB の読み出しは mock） ───────────────────


def _row(**kw):
    base = dict(
        id=1,
        email="v@example.com",
        status="active",
        password_must_change=False,
        password_changed_at=None,
        trial_expires_at=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _token_at(iat: int, viewer_id: int = 1, sub: str | None = None) -> str:
    claims = {
        "iss": viewer_tokens.VIEWER_ISSUER,
        "sub": sub or f"viewer:{viewer_id}",
        "iat": iat,
        "exp": iat + 43200,
    }
    return jwt.encode(claims, SECRET, algorithm="HS256")


async def _call(token: str, row, *, blacklisted: bool = False):
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with (
        patch.object(viewer_dependencies, "is_token_blacklisted", new=AsyncMock(return_value=blacklisted)),
        patch.object(viewer_dependencies, "_load_viewer_row", new=AsyncMock(return_value=row)),
    ):
        return await viewer_dependencies.get_current_viewer(cred, db=None)


async def _status_of(token: str, row, **kw) -> int:
    try:
        await _call(token, row, **kw)
    except HTTPException as exc:
        return exc.status_code
    return 200


async def test_iat_comparison_with_password_changed_at_fractional():
    changed = datetime(2026, 10, 16, 10, 0, 0, 700000, tzinfo=timezone.utc)
    base = int(changed.replace(microsecond=0).timestamp())
    row = _row(password_changed_at=changed)
    assert await _status_of(_token_at(base), row) == 200  # 10:00:00
    assert await _status_of(_token_at(base - 1), row) == 401  # 09:59:59


async def test_statuses():
    now = datetime.now(timezone.utc)
    token = _token_at(int(time.time()))
    ok = await _call(token, _row(status="active"))
    assert ok["id"] == 1 and ok["password_must_change"] is False
    assert await _status_of(token, _row(status="trial", trial_expires_at=now + timedelta(days=1))) == 200
    for status_value, detail in (
        ("pending", "viewer_pending"),
        ("verified", "viewer_pending"),
        ("suspended", "viewer_suspended"),
    ):
        with pytest.raises(HTTPException) as exc:
            await _call(token, _row(status=status_value))
        assert exc.value.status_code == 403 and exc.value.detail == detail
    with pytest.raises(HTTPException) as exc:
        await _call(token, _row(status="trial", trial_expires_at=now - timedelta(seconds=1)))
    assert exc.value.status_code == 403 and exc.value.detail == "viewer_trial_expired"


async def test_missing_row_blacklist_and_bad_tokens():
    token = _token_at(int(time.time()))
    assert await _status_of(token, None) == 401
    assert await _status_of(token, _row(), blacklisted=True) == 401
    assert await _status_of("not-a-jwt", _row()) == 401
    assert await _status_of(_token_at(int(time.time()), sub="viewer:abc"), _row()) == 401
    assert await _status_of(_token_at(int(time.time()), sub="1"), _row()) == 401


async def test_app_token_is_401_in_get_current_viewer(monkeypatch):
    monkeypatch.setenv("AUTH_JWT_SECRET", "a" * 48)
    app_token = self_tokens.create_access_token(1, "u@example.com", None)
    assert await _status_of(app_token, _row()) == 401


async def test_require_viewer_password_ok():
    ok = {"id": 1, "password_must_change": False}
    assert await viewer_dependencies.require_viewer_password_ok(ok) is ok
    with pytest.raises(HTTPException) as exc:
        await viewer_dependencies.require_viewer_password_ok({"id": 1, "password_must_change": True})
    assert exc.value.status_code == 403 and exc.value.detail == "password_change_required"


# ── PostgreSQL（1関数にまとめる。CI の共有メモリ不足を避けるため） ──────────


def test_viewer_tables_on_postgresql(request):
    from psycopg2 import errors

    if os.getenv("GITHUB_ACTIONS") != "true" or not os.getenv("RLS_ADMIN_DATABASE_URL"):
        pytest.skip("PostgreSQL fixture is CI-only (GITHUB_ACTIONS=true and RLS_ADMIN_DATABASE_URL)")
    conn, _, async_url = request.getfixturevalue("pg")
    cur = conn.cursor()

    # actor_user_id の FK 先 public.users は、既存の部品 tests/rls_bootstrap.py の _ensure_public_users で用意する
    async def _prepare_users():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with engine.begin() as aconn:
                await _ensure_public_users(aconn)
        finally:
            await engine.dispose()

    asyncio.run(_prepare_users())
    text_sql = (MIGRATIONS / MIGRATION_NAME).read_text()
    cur.execute(text_sql)
    cur.execute(text_sql)  # 2回目もエラーにならない（冪等）

    for table in ("viewer_accounts", "viewer_login_tokens", "viewer_login_events", "viewer_status_changes"):
        cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
        assert cur.fetchone()[0] is not None, table

    def rejected(stmt, params, exc_type):
        try:
            cur.execute(stmt, params)
        except exc_type:
            return True
        return False

    def insert_viewer(email, discord=None):
        cur.execute(
            "INSERT INTO public.viewer_accounts (email, line_name, status, discord_user_id) "
            "VALUES (%s, 'n', 'pending', %s) RETURNING id",
            (email, discord),
        )
        return cur.fetchone()[0]

    vid = insert_viewer("A@x.com")
    assert rejected(
        "INSERT INTO public.viewer_accounts (email, line_name, status) VALUES ('a@x.com', 'n', 'pending')",
        None,
        errors.UniqueViolation,
    )
    assert rejected(
        "INSERT INTO public.viewer_accounts (email, line_name, status) VALUES ('c@x.com', 'n', 'bogus')",
        None,
        errors.CheckViolation,
    )
    assert rejected(
        "INSERT INTO public.viewer_accounts (email, line_name, status, inventory_issue) "
        "VALUES ('d@x.com', 'n', 'pending', repeat('x', 1001))",
        None,
        errors.CheckViolation,
    )
    assert rejected(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, decode(repeat('ab', 31), 'hex'), 'signup_code', now())",
        (vid,),
        errors.CheckViolation,
    )
    assert rejected(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, decode(repeat('ab', 32), 'hex'), 'bogus', now())",
        (vid,),
        errors.CheckViolation,
    )
    assert rejected(
        "INSERT INTO public.viewer_login_events (viewer_id, event_type) VALUES (%s, 'bogus')",
        (vid,),
        errors.CheckViolation,
    )
    assert rejected(
        "INSERT INTO public.viewer_status_changes (viewer_id, action, actor) VALUES (%s, 'bogus', 'po')",
        (vid,),
        errors.CheckViolation,
    )
    assert rejected(
        "INSERT INTO public.viewer_status_changes (viewer_id, action, actor) VALUES (%s, 'suspend', 'bogus')",
        (vid,),
        errors.CheckViolation,
    )

    # discord_user_id の一意（NULL は2行入る）
    insert_viewer("n1@x.com")
    insert_viewer("n2@x.com")
    insert_viewer("d1@x.com", discord="111")
    assert rejected(
        "INSERT INTO public.viewer_accounts (email, line_name, status, discord_user_id) "
        "VALUES ('d2@x.com', 'n', 'pending', '111')",
        None,
        errors.UniqueViolation,
    )

    # 正しい値は入る
    cur.execute(
        "INSERT INTO public.viewer_login_tokens (viewer_account_id, token_sha256, purpose, expires_at) "
        "VALUES (%s, decode(repeat('ab', 32), 'hex'), 'signup_code', now())",
        (vid,),
    )
    cur.execute("INSERT INTO public.viewer_login_events (viewer_id, event_type) VALUES (%s, 'signup')", (vid,))
    cur.execute(
        "INSERT INTO public.viewer_status_changes (viewer_id, action, actor) VALUES (%s, 'start_trial', 'system')",
        (vid,),
    )

    # 閲覧者の行を消すと関連の3表の行も消える：外部キーの定義（ON DELETE CASCADE）を目録で確かめる
    for table in ("viewer_login_tokens", "viewer_login_events", "viewer_status_changes"):
        cur.execute(
            "SELECT confdeltype FROM pg_catalog.pg_constraint "
            "WHERE contype = 'f' AND confrelid = 'public.viewer_accounts'::regclass "
            "AND conrelid = %s::regclass",
            (f"public.{table}",),
        )
        rows = cur.fetchall()
        assert len(rows) == 1, f"{table}: FK count {len(rows)}"
        assert rows[0][0] == "c", f"{table}: confdeltype {rows[0][0]}"
