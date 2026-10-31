"""守り手：閲覧者のトークンは、アプリの API に一切通らない（ADR-1019 段1・設計 D1）。

app.routes から APIRoute をすべて自動で列挙し、VIEWER_ROUTE_ALLOWLIST 以外の (method, path) を
閲覧者のトークンで叩いて、すべて 401 になることを確かめる。API を足すたびに検査の対象になる。
get_current_user は override しない。patch するのは _init_firebase・is_token_blacklisted・check_auth_rate_limit の3つだけ。
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.auth import viewer_tokens
from app.auth.viewer_allowlist import VIEWER_ROUTE_ALLOWLIST

_UUID = "00000000-0000-4000-8000-000000000001"
_PARAM = re.compile(r"\{([^}:]+)(?::[^}]*)?\}")

# トークンを見ない公開ルート。閲覧者のトークンで得られるものは、トークン無しと同じ。
# 認証を持たない既存ルート（2026-10-16 の実測 26 本）。閲覧者のトークンを見ないので 401 にならないが、
# トークンから得られる権限は無い。ここに無いルートが 401 以外を返したら失敗する（新しい認証なしルートの検知）。
# 足す・消すときは、そのルートがトークンを見ない公開ルートであることをレビューで確かめること。
_PUBLIC_NO_AUTH_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/"),
        ("GET", "/api/health"),
        ("GET", "/api/public/staff-avatars/{token}.webp"),
        ("GET", "/api/v1/discord/oauth/callback"),
        ("GET", "/api/v1/google-calendar/connect/callback"),
        ("GET", "/api/v1/integrations/google-drive/connect/callback"),
        ("GET", "/api/v1/integrations/paypal/cancel"),
        ("GET", "/api/v1/integrations/paypal/return"),
        ("GET", "/api/v1/meta/deletion-status"),
        ("GET", "/api/v1/public/register"),
        ("GET", "/api/v1/webhook/messenger"),
        ("GET", "/metrics"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/logout"),
        ("POST", "/api/v1/auth/passkey/login/options"),
        ("POST", "/api/v1/auth/passkey/login/verify"),
        ("POST", "/api/v1/auth/password-reset/confirm"),
        ("POST", "/api/v1/auth/password-reset/request"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/contact"),
        ("POST", "/api/v1/google-calendar/webhook"),
        ("POST", "/api/v1/integrations/paypal/webhook"),
        ("POST", "/api/v1/meta/data-deletion"),
        ("POST", "/api/v1/public/register"),
        ("POST", "/api/v1/public/register/address"),
        ("POST", "/api/v1/public/register/change-billing"),
        ("POST", "/api/v1/tcg/line-devices/start"),
        ("POST", "/api/v1/webhook/messenger"),
    }
)


@pytest.fixture(autouse=True)
def viewer_env(monkeypatch):
    monkeypatch.setenv("AUTH_VIEWER_JWT_SECRET", "v" * 48)


def _fill(path: str) -> str:
    def repl(m: re.Match) -> str:
        name = m.group(1).lower()
        return _UUID if "uuid" in name or name.endswith("_uuid") else "1"

    return _PARAM.sub(repl, path)


def _targets() -> list[tuple[str, str]]:
    from app.main import app

    found: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            if (method, route.path) in VIEWER_ROUTE_ALLOWLIST:
                continue
            found.add((method, route.path))
    return sorted(found)


def _patches():
    return (
        patch("app.auth.dependencies._init_firebase"),
        patch("app.auth.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)),
        patch("app.auth.dependencies.check_auth_rate_limit", new=AsyncMock(return_value=False)),
    )


async def test_viewer_token_gets_401_on_every_app_route():
    from app.main import app

    token, _ = viewer_tokens.create_viewer_access_token(1)
    targets = _targets()
    assert len(targets) > 0, "叩くルートが0本"
    print(f"viewer isolation: {len(targets)} routes checked")

    not_401: list[str] = []
    unexpected: list[str] = []
    p1, p2, p3 = _patches()
    with p1, p2, p3:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            for method, path in targets:
                resp = await http.request(method, _fill(path), headers={"Authorization": f"Bearer {token}"})
                if resp.status_code != 401:
                    not_401.append(f"{method} {path} -> {resp.status_code}")
                    print(f"public route: {method} {path} -> {resp.status_code}")
                    if (method, path) not in _PUBLIC_NO_AUTH_ROUTES:
                        unexpected.append(f"{method} {path} -> {resp.status_code}")
    print(f"viewer isolation: {len(targets) - len(not_401)} returned 401, {len(not_401)} pinned public routes")
    assert not unexpected, f"{len(unexpected)} / {len(targets)} routes did not return 401:\n" + "\n".join(unexpected)


async def test_viewer_token_still_401_after_passing_get_current_viewer():
    """get_current_viewer を一度通した後でも、同じトークンで既存の API は 401 のまま。"""
    from fastapi.security import HTTPAuthorizationCredentials

    from app.auth import viewer_dependencies
    from app.main import app

    token, _ = viewer_tokens.create_viewer_access_token(1)
    row = type(
        "Row",
        (),
        dict(
            id=1,
            email="v@example.com",
            status="active",
            password_must_change=False,
            password_changed_at=None,
            trial_expires_at=None,
        ),
    )()
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    p1, p2, p3 = _patches()
    with (
        p1,
        p2,
        p3,
        patch.object(viewer_dependencies, "is_token_blacklisted", new=AsyncMock(return_value=False)),
        patch.object(viewer_dependencies, "_load_viewer_row", new=AsyncMock(return_value=row)),
    ):
        viewer = await viewer_dependencies.get_current_viewer(cred, db=None)
        assert viewer["id"] == 1
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            resp = await http.get("/api/v1/leads", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
