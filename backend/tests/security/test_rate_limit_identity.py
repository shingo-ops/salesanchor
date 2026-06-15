from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers

from app.middleware import rate_limit


class DummyRequest:
    def __init__(self, headers: dict[str, str] | None = None, host: str = "203.0.113.10"):
        self.headers = Headers(headers or {})
        self.client = SimpleNamespace(host=host)


@pytest.mark.asyncio
async def test_no_authorization_uses_ip_bucket():
    request = DummyRequest(host="203.0.113.10")

    identifier, limit, window = await rate_limit._rate_limit_identity(request)

    assert identifier == "ip:203.0.113.10"
    assert limit == rate_limit.UNAUTHED_RATE_LIMIT
    assert window == rate_limit.UNAUTHED_WINDOW_SEC


@pytest.mark.asyncio
async def test_malformed_bearer_uses_ip_bucket():
    request = DummyRequest(headers={"Authorization": "Bearer "}, host="203.0.113.10")

    identifier, limit, window = await rate_limit._rate_limit_identity(request)

    assert identifier == "ip:203.0.113.10"
    assert limit == rate_limit.UNAUTHED_RATE_LIMIT
    assert window == rate_limit.UNAUTHED_WINDOW_SEC


@pytest.mark.asyncio
async def test_unverified_claim_like_token_does_not_create_user_bucket(monkeypatch):
    async def fake_cached_jwt(token: str):
        return None

    monkeypatch.setattr("app.cache.get_cached_jwt", fake_cached_jwt)
    # The token text pretends to carry an email claim, but cache does not recognize it.
    # Keep it deliberately non-JWT-shaped so secret scanners do not flag test data.
    fake_token = "unverified-claim-email-attacker-at-example-dot-com"
    request = DummyRequest(headers={"Authorization": f"Bearer {fake_token}"}, host="203.0.113.10")

    identifier, limit, window = await rate_limit._rate_limit_identity(request)

    assert identifier == "ip:203.0.113.10"
    assert limit == rate_limit.UNAUTHED_RATE_LIMIT
    assert window == rate_limit.UNAUTHED_WINDOW_SEC


@pytest.mark.asyncio
async def test_changing_fake_jwt_email_does_not_distribute_bucket(monkeypatch):
    async def fake_cached_jwt(token: str):
        return None

    monkeypatch.setattr("app.cache.get_cached_jwt", fake_cached_jwt)
    request_a = DummyRequest(
        headers={"Authorization": "Bearer header.email_a.signature"},
        host="203.0.113.10",
    )
    request_b = DummyRequest(
        headers={"Authorization": "Bearer header.email_b.signature"},
        host="203.0.113.10",
    )

    identity_a = await rate_limit._rate_limit_identity(request_a)
    identity_b = await rate_limit._rate_limit_identity(request_b)

    assert identity_a == identity_b
    assert identity_a[0] == "ip:203.0.113.10"


@pytest.mark.asyncio
async def test_verified_cached_jwt_uses_user_bucket(monkeypatch):
    async def fake_cached_jwt(token: str):
        return {"email": "verified@example.com"}

    monkeypatch.setattr("app.cache.get_cached_jwt", fake_cached_jwt)
    request = DummyRequest(headers={"Authorization": "Bearer verified-token"}, host="203.0.113.10")

    identifier, limit, window = await rate_limit._rate_limit_identity(request)

    assert identifier == "user:verified@example.com"
    assert limit == rate_limit.AUTHED_RATE_LIMIT
    assert window == rate_limit.AUTHED_WINDOW_SEC


@pytest.mark.asyncio
async def test_cache_lookup_exception_falls_back_to_ip_bucket(monkeypatch):
    async def exploding_cached_jwt(token: str):
        raise RuntimeError("cache boom")

    monkeypatch.setattr("app.cache.get_cached_jwt", exploding_cached_jwt)
    request = DummyRequest(headers={"Authorization": "Bearer any-token"}, host="203.0.113.10")

    identifier, limit, window = await rate_limit._rate_limit_identity(request)

    assert identifier == "ip:203.0.113.10"
    assert limit == rate_limit.UNAUTHED_RATE_LIMIT
    assert window == rate_limit.UNAUTHED_WINDOW_SEC
